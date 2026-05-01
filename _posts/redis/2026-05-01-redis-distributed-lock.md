---
title: "Redis 분산 락 기본 원리와 구현"
categories:
- REDIS
toc: true
toc_sticky: true
toc_label: 목차
---

쿠팡 타임세일, 1초에 10만 명이 몰린다. 재고는 딱 1개. 10만 명 중 정확히 1명만 구매에 성공해야 한다. 서버는 10대. 각 서버가 동시에 "재고 있음"을 확인하고 결제를 진행한다면 어떻게 될까?

단일 서버라면 `synchronized`로 해결된다. 하지만 서버가 10대면 JVM 락은 서버 안에서만 유효하다. 10대가 동시에 같은 재고를 잡는다. 이 문제를 해결하는 것이 **분산 락**이다.

## 분산 락이란?

> 분산 락은 화장실 열쇠와 같다. 열쇠를 가진 사람만 들어갈 수 있고, 나올 때 반드시 반납해야 한다. 열쇠는 하나뿐이라 동시에 두 명이 들어갈 수 없다.

여러 서버(프로세스)가 **동일한 공유 자원**에 동시에 접근할 때, 오직 하나의 프로세스만 자원을 점유하도록 보장하는 메커니즘이다.

단일 서버에서는 `synchronized`, `ReentrantLock` 등으로 해결되지만, **멀티 인스턴스 환경**에서는 JVM 밖의 외부 저장소가 필요하다. Redis가 가장 널리 쓰인다.

### 왜 Redis인가?

| 특성 | 설명 |
|------|------|
| **싱글 스레드** | 명령어가 순차 실행되므로 race condition 없음 |
| **원자적 명령어** | `SET NX`, `EVAL`(Lua) 등으로 atomic한 락 획득 가능 |
| **TTL 지원** | 락에 만료 시간을 설정하여 데드락 방지 |
| **고성능** | 인메모리 기반으로 지연시간이 매우 낮음 |

---

## 기본 구현: SET NX EX

```bash
SET resource_lock <unique_value> NX EX 30
```

- `NX` : 키가 존재하지 않을 때만 설정 (Not eXists)
- `EX 30` : 30초 후 자동 만료
- `unique_value` : UUID 등 고유값 — **본인이 건 락만 해제**하기 위함

### 락 획득

```java
String lockKey = "order:lock:" + orderId;
String lockValue = UUID.randomUUID().toString();

Boolean acquired = redisTemplate.opsForValue()
    .setIfAbsent(lockKey, lockValue, 30, TimeUnit.SECONDS);

if (Boolean.TRUE.equals(acquired)) {
    try {
        // 임계 영역 로직
        processOrder(orderId);
    } finally {
        // 락 해제
        releaseLock(lockKey, lockValue);
    }
}
```

### 락 해제 — 반드시 Lua 스크립트로

```java
private void releaseLock(String key, String value) {
    String script =
        "if redis.call('get', KEYS[1]) == ARGV[1] then " +
        "  return redis.call('del', KEYS[1]) " +
        "else " +
        "  return 0 " +
        "end";
    redisTemplate.execute(
        new DefaultRedisScript<>(script, Long.class),
        List.of(key), value
    );
}
```

**왜 Lua인가?**
`GET` → 비교 → `DEL`을 별도로 수행하면, GET과 DEL 사이에 다른 프로세스가 끼어들 수 있다. Lua 스크립트는 Redis에서 **원자적으로** 실행된다.

> **비유**: GET으로 "내 열쇠 맞나 확인" 하고 DEL로 "열쇠 반납" 하는 사이에, 다른 사람이 새 열쇠를 걸어버리면 남의 열쇠를 빼앗게 된다. Lua는 확인과 반납을 하나의 동작으로 묶어준다.

---

## Redisson 기반 구현

실무에서는 직접 구현보다 **Redisson** 라이브러리를 쓰는 것이 안전하다.

```java
RLock lock = redissonClient.getLock("order:lock:" + orderId);

try {
    // 10초 대기, 30초 후 자동 해제
    boolean acquired = lock.tryLock(10, 30, TimeUnit.SECONDS);
    if (acquired) {
        processOrder(orderId);
    }
} finally {
    if (lock.isHeldByCurrentThread()) {
        lock.unlock();
    }
}
```

### Redisson의 장점

- **Pub/Sub 기반 대기**: 스핀락이 아닌 이벤트 기반으로 CPU 낭비 없음
- **Watchdog**: 락 보유 중 자동으로 TTL 연장 (기본 30초마다)
- **재진입 가능**: 같은 스레드가 동일 락을 여러 번 획득 가능

> **실무 예시**: 배달의민족 주문 처리 서버가 10대 운영 중이다. 사용자가 주문 버튼을 두 번 눌렀을 때, 두 요청이 서로 다른 서버에 도달해도 Redisson 락 하나로 "첫 번째 요청만 처리"를 보장한다.

---

## Redlock 알고리즘

단일 Redis 인스턴스에 의존하면, 그 노드가 죽으면 락도 사라진다. **Redlock**은 Redis 창시자 Antirez가 제안한 분산 환경 알고리즘이다.

### 동작 방식

1. **N개(보통 5개)의 독립 Redis 마스터**를 준비한다
2. 클라이언트가 **모든 노드에 동시에** 락 획득을 시도한다
3. **과반수(N/2 + 1) 이상** 성공하고, 총 소요 시간이 TTL보다 짧으면 락 획득 성공
4. 실패 시 모든 노드에서 락을 해제한다

<div class="mermaid">
graph LR
    C[Client]
    C -->|SET NX| R1[Redis1: OK]
    C -->|SET NX| R2[Redis2: OK]
    C -->|SET NX| R3[Redis3: OK]
    C -->|SET NX| R4[Redis4: FAIL]
    C -->|SET NX| R5[Redis5: OK]
    R1 & R2 & R3 & R5 --> RESULT[4/5 성공 → 과반수 충족 → 락 획득 성공]
    style R4 fill:#f88,stroke:#c00
    style RESULT fill:#8f8,stroke:#080
</div>

> **비유**: 국회 의결처럼, 5명 중 3명 이상이 찬성해야 법안이 통과된다. 한 명이 결석해도 나머지 4명이 동의하면 유효하다.

### Redlock 논쟁

Martin Kleppmann(DDIA 저자)은 Redlock의 안전성에 의문을 제기했다:

- **GC pause**: 락 획득 후 긴 GC가 발생하면, TTL이 만료되어 다른 프로세스가 락을 획득할 수 있다
- **시계 점프**: NTP 동기화로 시스템 시계가 갑자기 뛰면 TTL 계산이 틀어진다

이에 대해 Antirez는 반박했지만, **완벽한 합의에는 이르지 못했다.**

---

## 극한 시나리오

### 시나리오 1: 락 보유 중 프로세스 죽음

**상황**: 서버 A가 락을 잡고 주문 처리 중에 갑자기 OOM으로 프로세스가 죽었다.

<div class="mermaid">
sequenceDiagram
    participant A as Process A
    participant B as Process B
    participant R as Redis

    A->>R: 락 획득 (SET NX EX)
    R-->>A: OK
    Note over A: 크래시 💀
    B->>R: 락 획득 시도
    R-->>B: FAIL (락 존재)
    Note over B: 대기... (TTL 만료 기다림)
    Note over R: TTL 만료 → 키 삭제
    B->>R: 락 획득 시도
    R-->>B: OK (락 획득 성공)
</div>

**증상**: 서버 B가 락을 획득하지 못하고 계속 대기한다.

**원인**: 서버 A가 락을 반납하지 못하고 죽었다.

**해결**: TTL이 자동으로 만료시킨다. **TTL이 없으면 영원히 데드락**이다. TTL은 반드시 설정해야 한다.

---

### 시나리오 2: 작업이 TTL보다 오래 걸림

**상황**: 쿠팡 대용량 주문 처리 중 외부 결제 API가 응답을 20초 늦게 줬다. 락 TTL은 15초였다.

<div class="mermaid">
sequenceDiagram
    participant A as Process A
    participant B as Process B
    participant R as Redis

    A->>R: 락 획득 (TTL=30s)
    R-->>A: OK
    Note over A: 작업 진행 중...
    Note over R: 30s 경과 → TTL 만료
    B->>R: 락 획득
    R-->>B: OK
    Note over B: 작업 진행 중...
    A->>R: DEL lock (작업 완료)
    Note over A,R: ⚠️ A가 B의 락을 삭제!
    Note over B: 락이 사라짐 → 위험!
</div>

**증상**: 두 서버가 동시에 같은 주문을 처리한다. 결제가 중복 발생한다.

**원인**: A가 자기 락이 아닌 B의 락을 삭제한다.

**해결 1**: Lua 스크립트로 `value` 비교 후 삭제 (위에서 설명)

**해결 2**: Watchdog으로 TTL 자동 연장 (Redisson)

**해결 3**: 작업 시간을 측정하여 TTL을 충분히 크게 설정

---

### 시나리오 3: Redis 마스터 장애 + Failover

**상황**: 락을 저장한 Redis 마스터가 갑자기 죽었다. Sentinel이 레플리카를 마스터로 승격시켰다. 그 사이 서버 B가 새 마스터에서 락을 획득했다.

<div class="mermaid">
sequenceDiagram
    participant A as Process A
    participant M as Redis Master
    participant Rep as Replica
    participant B as Process B

    A->>M: 락 획득
    M-->>A: OK
    Note over M: 크래시 💀 (복제 전)
    Note over Rep: 마스터로 승격 (락 데이터 없음)
    B->>Rep: 락 획득
    Rep-->>B: OK
    Note over A,B: ⚠️ A, B 동시에 임계 영역 진입!
</div>

**증상**: 재고가 1개인데 두 명에게 동시에 결제가 완료된다.

**원인**: Redis 복제는 **비동기**이므로, 마스터가 죽기 전에 복제되지 않은 데이터는 유실된다.

**해결**:
- Redlock 사용 (과반수 기반)
- `WAIT` 명령어로 동기 복제 강제 (성능 저하 감수)
- 또는 **Zookeeper/etcd** 같은 CP 시스템 사용

---

### 시나리오 4: 네트워크 파티션

<div class="mermaid">
graph LR
    A[Process A] -. 네트워크 단절 ✕ .- R[Redis]
    B[Process B] -->|정상 통신| R
    style A fill:#fdd,stroke:#c00
</div>

**상황**: 서버 A는 락을 보유하고 작업 중이지만, Redis와 통신이 끊겼다. Watchdog이 TTL을 연장하지 못해 락이 만료됐다. 서버 B가 락을 획득했다.

**해결**:
- A는 작업 시작 전 **fencing token**(단조 증가 번호)을 발급받는다
- 공유 자원(DB 등)은 fencing token이 현재보다 큰 경우에만 쓰기를 허용한다

<div class="mermaid">
sequenceDiagram
    participant A as Process A
    participant B as Process B
    participant DB as 공유 DB

    A->>DB: 쓰기 시도 (fencing token=33)
    B->>DB: 쓰기 시도 (fencing token=34)
    DB-->>B: ✅ 허용 (token 34 > 현재 최대값)
    DB-->>A: ❌ 거부 (token 33 < 34)
</div>

> **비유**: 병원 대기표와 같다. 33번 대기표를 들고 들어가려는데, 이미 34번 환자가 들어가 있으면 33번은 입장이 거부된다.

---

### 시나리오 5: GC Stop-the-World

**상황**: 대용량 트래픽으로 JVM Full GC가 35초간 발생했다. 락 TTL이 30초였다.

<div class="mermaid">
sequenceDiagram
    participant A as Process A
    participant B as Process B
    participant R as Redis

    A->>R: 락 획득 (TTL=30s)
    R-->>A: OK
    Note over A: GC STW 발생 (30초 동안 멈춤)
    Note over R: TTL 만료 → 키 삭제
    B->>R: 락 획득
    R-->>B: OK
    Note over B: 작업 중...
    Note over A: GC 종료, 작업 재개
    Note over A,B: ⚠️ A와 B 동시에 임계 영역 진입!
</div>

**증상**: GC가 끝난 서버 A가 자신이 여전히 락을 보유하고 있다고 착각하고 작업을 이어간다.

**해결**:
- 락 획득 후 **남은 TTL을 확인**하고, 충분하지 않으면 작업을 포기
- Fencing token 패턴 적용
- G1GC/ZGC 등 STW가 짧은 GC 사용

---

## 분산 락 설계 체크리스트

| 항목 | 필수 여부 | 설명 |
|------|-----------|------|
| TTL 설정 | **필수** | 데드락 방지 |
| unique value + Lua 해제 | **필수** | 남의 락 삭제 방지 |
| 재시도 + 백오프 | 권장 | 일시적 실패 대응 |
| Watchdog (TTL 연장) | 권장 | 장시간 작업 대응 |
| Fencing token | 강력 권장 | 최종 방어선 |
| Redlock (다중 노드) | 선택 | 단일 장애점 제거 |
| 타임아웃 | **필수** | 락 대기 무한 차단 방지 |
| 멱등성 보장 | **필수** | 락 실패 시에도 안전한 로직 |

---

## 정리

분산 락은 **간단해 보이지만 극한 상황에서 깨지기 쉽다.** 핵심 원칙:

1. **TTL은 반드시** 설정하되, 작업 시간보다 충분히 길게
2. **해제는 반드시 Lua**로 — GET/DEL 분리 금지
3. **비동기 복제** 환경에서는 Redlock 또는 fencing token 필수
4. **완벽한 분산 락은 없다** — 최종 방어선은 항상 DB 레벨 멱등성
