---
title: "Redis 분산 락 구현 — Lettuce, Redisson, Redlock"
categories:
- REDIS
toc: true
toc_sticky: true
toc_label: 목차
---

블랙프라이데이 자정, 한정판 운동화 1켤레에 5만 명이 동시 접속한다. 서버 20대가 동시에 "재고 1개 남음"을 확인하고 저마다 결제를 진행한다면? 한 사람만 사야 할 물건이 20명에게 팔린다. 분산 락은 "지금 이 자원은 내가 쓰고 있으니 기다려라"는 신호를 20대 서버 전체에 동시에 전달하는 메커니즘이다.

## 분산 락 개요

> **비유**: 분산 락은 공중화장실 문 걸쇠와 같다. 걸쇠(락)를 건 사람만 안에 있을 수 있고, 나올 때 반드시 열어줘야(해제) 다음 사람이 들어갈 수 있다. Redis라는 건물 관리인이 걸쇠 상태를 모든 사람에게 공개적으로 알려준다.

여러 서버(프로세스)가 동일한 공유 자원에 동시에 접근할 때, **오직 하나의 프로세스만 자원을 점유**하도록 보장하는 메커니즘이다. 단일 JVM 환경에서는 `synchronized`나 `ReentrantLock`으로 해결되지만, 멀티 인스턴스 환경에서는 외부 저장소 기반의 락이 필요하다.

Redis가 분산 락 저장소로 널리 쓰이는 이유:

| 특성 | 설명 |
|------|------|
| **싱글 스레드** | 명령어가 순차 실행되므로 race condition 없음 |
| **원자적 명령어** | `SET NX EX`, `EVAL`(Lua) 등으로 atomic 락 획득 가능 |
| **TTL 지원** | 락에 만료 시간을 설정하여 데드락 방지 |
| **고성능** | 인메모리 기반으로 지연시간이 매우 낮음 |

---

## Lettuce 기반 분산 락

Spring Boot 기본 Redis 클라이언트인 **Lettuce**를 사용한 직접 구현 방식이다.

### SET NX EX + Lua 구조

```
락 획득: SET key value NX EX ttl
락 해제: Lua 스크립트 (GET → 비교 → DEL 원자 실행)
```

### 락 획득 구현

```java
@Component
public class LettuceDistributedLock {

    private final StringRedisTemplate redisTemplate;

    public LettuceDistributedLock(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    /**
     * 락 획득 시도
     * @param lockKey  락 키
     * @param lockValue  고유 식별자 (UUID 권장)
     * @param ttlSeconds  TTL (초)
     * @return 락 획득 성공 여부
     */
    public boolean tryLock(String lockKey, String lockValue, long ttlSeconds) {
        Boolean result = redisTemplate.opsForValue()
            .setIfAbsent(lockKey, lockValue, ttlSeconds, TimeUnit.SECONDS);
        return Boolean.TRUE.equals(result);
    }

    /**
     * 락 해제 — Lua 스크립트로 원자 실행
     * GET → 값 비교 → DEL 을 하나의 명령으로 처리
     */
    public boolean releaseLock(String lockKey, String lockValue) {
        String script =
            "if redis.call('get', KEYS[1]) == ARGV[1] then " +
            "  return redis.call('del', KEYS[1]) " +
            "else " +
            "  return 0 " +
            "end";

        Long result = redisTemplate.execute(
            new DefaultRedisScript<>(script, Long.class),
            List.of(lockKey),
            lockValue
        );
        return Long.valueOf(1L).equals(result);
    }
}
```

### 사용 예시

```java
@Service
public class OrderService {

    private final LettuceDistributedLock lock;

    public void processOrder(Long orderId) {
        String lockKey = "order:lock:" + orderId;
        String lockValue = UUID.randomUUID().toString();

        boolean acquired = lock.tryLock(lockKey, lockValue, 30);
        if (!acquired) {
            throw new LockAcquisitionException("락 획득 실패: " + orderId);
        }

        try {
            // 임계 영역 로직
            doProcess(orderId);
        } finally {
            lock.releaseLock(lockKey, lockValue);
        }
    }
}
```

### 스핀락 방식 (재시도)

Lettuce는 Pub/Sub 기반 대기를 제공하지 않으므로, 재시도가 필요하면 **스핀락**을 직접 구현해야 한다.

```java
public boolean tryLockWithRetry(String lockKey, String lockValue,
                                 long ttlSeconds, long waitMillis) throws InterruptedException {
    long deadline = System.currentTimeMillis() + waitMillis;

    while (System.currentTimeMillis() < deadline) {
        if (tryLock(lockKey, lockValue, ttlSeconds)) {
            return true;
        }
        // 100ms 대기 후 재시도 — CPU 낭비 발생
        Thread.sleep(100);
    }
    return false;
}
```

**문제점**: `Thread.sleep()` 간격 동안 CPU를 낭비하지는 않지만, 락 해제 이벤트를 즉시 감지하지 못해 지연이 발생한다. 이 문제를 Redisson은 Pub/Sub으로 해결한다.

---

## Redisson 분산 락

**Redisson**은 Redis 기반 Java 클라이언트로, 다양한 분산 동기화 프리미티브를 제공한다.

### 의존성 추가

```xml
<!-- Maven -->
<dependency>
    <groupId>org.redisson</groupId>
    <artifactId>redisson-spring-boot-starter</artifactId>
    <version>3.27.0</version>
</dependency>
```

```gradle
// Gradle
implementation 'org.redisson:redisson-spring-boot-starter:3.27.0'
```

### 기본 설정

```yaml
# application.yml
spring:
  redis:
    host: localhost
    port: 6379
```

```java
@Configuration
public class RedissonConfig {

    @Bean
    public RedissonClient redissonClient() {
        Config config = new Config();
        config.useSingleServer()
            .setAddress("redis://localhost:6379")
            .setConnectionMinimumIdleSize(1)
            .setConnectionPoolSize(10);
        return Redisson.create(config);
    }
}
```

---

## Redisson 락 종류

### 1. RLock — 기본 분산 락

가장 기본적인 분산 락이다. 재진입(reentrant) 가능하며, Watchdog이 TTL을 자동 연장한다.

```java
RLock lock = redissonClient.getLock("order:lock:" + orderId);

try {
    // waitTime: 락 대기 최대 시간, leaseTime: 락 보유 최대 시간
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

**leaseTime을 -1로 설정하면 Watchdog이 자동으로 TTL을 연장한다.**

```java
// leaseTime 생략 → Watchdog 활성화 (기본 30초마다 갱신)
lock.lock(); // 무기한 보유, Watchdog이 TTL 연장
```

**Watchdog 동작 원리:**
- 기본 TTL: 30초 (`lockWatchdogTimeout`)
- TTL의 1/3 시점마다 갱신 → 즉, 10초마다 30초로 리셋
- 락 해제(`unlock()`) 시 Watchdog 자동 중단

```java
// Watchdog 타임아웃 커스터마이즈
Config config = new Config();
config.setLockWatchdogTimeout(60000); // 60초
```

---

### 2. FairLock — 공정 락

락 획득 순서를 **요청 순서대로** 보장한다. 내부적으로 대기 큐를 Redis에 저장한다.

```java
RLock fairLock = redissonClient.getFairLock("fairLock:resource");

try {
    // 먼저 요청한 스레드가 먼저 락을 획득
    fairLock.lock();
    doWork();
} finally {
    fairLock.unlock();
}
```

**동작 원리:**
1. 락 획득 시도 시 대기 큐에 자신을 등록
2. 현재 락 보유자가 해제하면 큐의 첫 번째 대기자에게 알림
3. 순서 보장으로 **starvation 방지**

**단점:** 일반 RLock보다 오버헤드가 크고, 처리량이 낮다.

---

### 3. MultiLock — 복수 락 동시 획득

여러 자원에 대한 락을 **하나의 원자적 연산처럼** 획득한다.

```java
RLock lock1 = redissonClient.getLock("lock:resource1");
RLock lock2 = redissonClient.getLock("lock:resource2");
RLock lock3 = redissonClient.getLock("lock:resource3");

RLock multiLock = redissonClient.getMultiLock(lock1, lock2, lock3);

try {
    // 세 락을 모두 획득해야 진행
    multiLock.lock();
    doWork();
} finally {
    multiLock.unlock();
}
```

**사용 사례:** 계좌 이체 시 출금 계좌 + 입금 계좌 동시 락킹으로 데드락 없이 처리.

**내부 동작:**
- 모든 락을 순서대로 획득 시도
- 하나라도 실패하면 이미 획득한 락을 모두 해제 후 재시도
- 데드락 방지를 위해 랜덤 백오프 적용

---

### 4. RedLock — 다중 Redis 인스턴스 기반 락

**단일 Redis 인스턴스의 단일 장애점 문제**를 해결하기 위해 여러 독립 Redis 마스터에 걸쳐 락을 획득한다.

```java
RLock lock1 = redissonClient1.getLock("redlock:key"); // Redis #1
RLock lock2 = redissonClient2.getLock("redlock:key"); // Redis #2
RLock lock3 = redissonClient3.getLock("redlock:key"); // Redis #3
RLock lock4 = redissonClient4.getLock("redlock:key"); // Redis #4
RLock lock5 = redissonClient5.getLock("redlock:key"); // Redis #5

RLock redLock = redissonClient1.getRedLock(lock1, lock2, lock3, lock4, lock5);

try {
    boolean acquired = redLock.tryLock(10, 30, TimeUnit.SECONDS);
    if (acquired) {
        doCriticalWork();
    }
} finally {
    redLock.unlock();
}
```

**Redlock 알고리즘:**

```
1. 현재 시각 T1 기록
2. N개 Redis 마스터에 동시에 SET NX PX ttl 시도
3. N/2 + 1 이상 성공하고, 총 소요 시간 < TTL 이면 락 획득 성공
4. 유효 TTL = 초기 TTL - (현재시각 - T1) - 클럭 드리프트 보정값
5. 실패 시 모든 노드에서 락 해제
```

**Redlock 논쟁:**
- Martin Kleppmann: GC pause, 시계 점프 시 안전성 보장 불가
- Antirez(Redis 창시자): 실용적으로 충분하다고 반박
- **결론**: 완벽한 분산 합의가 필요하면 ZooKeeper/etcd 사용

---

### 5. ReadWriteLock — 읽기/쓰기 락

여러 스레드의 **동시 읽기를 허용**하고, 쓰기는 배타적으로 처리한다.

```java
RReadWriteLock rwLock = redissonClient.getReadWriteLock("rw:resource");

// 읽기 락 — 여러 스레드 동시 획득 가능
RLock readLock = rwLock.readLock();
readLock.lock();
try {
    return readData();
} finally {
    readLock.unlock();
}

// 쓰기 락 — 배타적, 다른 읽기/쓰기 락이 없을 때만 획득 가능
RLock writeLock = rwLock.writeLock();
writeLock.lock();
try {
    writeData();
} finally {
    writeLock.unlock();
}
```

**동작 규칙:**

| 요청 \ 현재 상태 | 읽기 락 보유 | 쓰기 락 보유 |
|-----------------|------------|------------|
| 읽기 락 요청 | 허용 | 대기 |
| 쓰기 락 요청 | 대기 | 대기 |

---

### 6. Semaphore — 허용 개수 제한

동시에 접근 가능한 **스레드 수를 제한**한다.

```java
RSemaphore semaphore = redissonClient.getSemaphore("semaphore:api");
semaphore.trySetPermits(10); // 최대 10개 허용

// 퍼밋 획득
boolean acquired = semaphore.tryAcquire(1, 5, TimeUnit.SECONDS);
try {
    callExternalApi();
} finally {
    semaphore.release();
}
```

**사용 사례:** 외부 API 동시 호출 수 제한, DB 커넥션 풀 제어.

---

### 7. CountDownLatch — 완료 대기

여러 작업이 **모두 완료될 때까지 대기**하는 분산 카운터다.

```java
RCountDownLatch latch = redissonClient.getCountDownLatch("latch:batch");
latch.trySetCount(3); // 3개 작업 완료 대기

// 워커 1, 2, 3 각각 완료 시
latch.countDown();

// 오케스트레이터에서 대기
latch.await(); // 3개 모두 countDown() 되면 진행
```

---

## Pub/Sub 기반 대기 vs 스핀락

Redisson의 가장 큰 장점 중 하나는 락 대기 방식이다.

### Lettuce (스핀락)

<div class="mermaid">
sequenceDiagram
    participant B as Thread B
    participant R as Redis

    B->>R: tryLock
    R-->>B: FAIL
    Note over B: sleep(100ms)
    B->>R: tryLock
    R-->>B: FAIL
    Note over B: sleep(100ms)
    B->>R: tryLock
    R-->>B: FAIL
    Note over B: sleep(100ms)
    B->>R: tryLock
    R-->>B: OK (성공)
</div>

- 불필요한 Redis 명령어 반복 실행
- 슬랙(sleep) 간격만큼 대기 지연 발생
- 많은 스레드가 경쟁 시 Redis에 부하

### Redisson (Pub/Sub)

<div class="mermaid">
sequenceDiagram
    participant A as Thread A
    participant R as Redis
    participant B as Thread B

    A->>R: 락 획득
    R-->>A: OK
    B->>R: tryLock
    R-->>B: FAIL
    B->>R: SUBSCRIBE redisson_lock__channel
    Note over B: 대기...
    Note over A: 작업 완료
    A->>R: unlock() + PUBLISH lockReleased
    R-->>B: 이벤트 수신
    B->>R: tryLock
    R-->>B: OK (즉시 성공)
</div>

- 락 해제 시 **즉시** 알림 수신
- 불필요한 Redis 명령어 없음
- 대기 스레드 수에 관계없이 Redis 부하 일정

**내부 채널명:** `redisson_lock__channel:{lockKey}`

---

## Watchdog TTL 자동 연장

Redisson은 leaseTime을 지정하지 않으면 **Watchdog**을 통해 락 TTL을 자동으로 연장한다.

<div class="mermaid">
sequenceDiagram
    participant App as Application
    participant WD as Watchdog
    participant R as Redis

    App->>R: lock() 획득 (TTL=30s)
    Note over WD: 갱신 주기: 10s (30s / 3)
    WD->>R: TTL 갱신 (10s 경과)
    Note over R: TTL 리셋 → 30s
    WD->>R: TTL 갱신 (20s 경과)
    Note over R: TTL 리셋 → 30s
    WD->>R: TTL 갱신 (30s 경과)
    Note over R: TTL 리셋 → 30s
    App->>R: unlock() → 키 삭제
    Note over WD: Watchdog 중단
</div>

**주의:** leaseTime을 명시적으로 설정하면 Watchdog이 비활성화된다.

```java
// Watchdog 활성화 (leaseTime 없음)
lock.lock();
lock.tryLock(10, TimeUnit.SECONDS); // waitTime만 지정

// Watchdog 비활성화 (leaseTime 명시)
lock.tryLock(10, 30, TimeUnit.SECONDS); // 30초 후 강제 해제
```

---

## Lettuce vs Redisson 비교

| 항목 | Lettuce (직접 구현) | Redisson |
|------|-------------------|----------|
| **설정 복잡도** | 낮음 (Spring Boot 기본) | 중간 (추가 의존성) |
| **락 대기 방식** | 스핀락 (폴링) | Pub/Sub (이벤트) |
| **Watchdog** | 없음 (직접 구현 필요) | 내장 |
| **재진입 지원** | 없음 (직접 구현 필요) | 기본 지원 |
| **락 종류** | 단일 (SET NX) | RLock, FairLock, MultiLock, RedLock, RW, Semaphore, Latch |
| **Redis 부하** | 스핀락 시 높음 | 이벤트 기반으로 낮음 |
| **TTL 연장** | 직접 구현 필요 | Watchdog 자동 처리 |
| **클러스터 지원** | 기본 지원 | 기본 지원 |
| **Redlock** | 직접 구현 필요 | 내장 (`getRedLock`) |
| **코드량** | 많음 | 적음 |
| **성능** | 단순 락은 약간 빠름 | 다양한 시나리오에서 안정적 |
| **적합 환경** | 단순한 락, 최소 의존성 | 복잡한 동기화, 프로덕션 |

---

## 분산 환경 문제 시나리오와 해결

### 시나리오 1: 락 보유 중 프로세스 크래시

<div class="mermaid">
sequenceDiagram
    participant A as Process A
    participant B as Process B
    participant R as Redis

    A->>R: 락 획득 (TTL=30s)
    R-->>A: OK
    Note over A: 크래시
    Note over R: TTL 만료 (30s 후) → 키 삭제
    B->>R: 락 획득
    R-->>B: OK
</div>

**해결:** TTL이 반드시 설정되어 있어야 한다. TTL 없이 키만 남으면 데드락이다.

---

### 시나리오 2: 작업 시간이 TTL 초과

<div class="mermaid">
sequenceDiagram
    participant A as Process A
    participant B as Process B
    participant R as Redis

    A->>R: 락 획득 (TTL=30s)
    R-->>A: OK
    Note over A: 작업 시작
    Note over R: 30s 경과 → TTL 만료
    B->>R: 락 획득
    R-->>B: OK
    Note over B: 작업 시작
    A->>R: DEL lock (작업 완료)
    Note over A,R: ⚠️ B의 락을 삭제!
</div>

**해결 1:** Lua 스크립트로 자신의 value인지 확인 후 삭제

```lua
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
```

**해결 2:** Redisson Watchdog으로 TTL 자동 연장

**해결 3:** 작업 시작 전 남은 TTL 확인

```java
Long ttl = redisTemplate.getExpire(lockKey, TimeUnit.MILLISECONDS);
if (ttl != null && ttl < MINIMUM_WORK_TIME_MS) {
    throw new LockExpiredException("락 TTL 부족, 작업 포기");
}
```

---

### 시나리오 3: 비동기 복제 중 마스터 장애

<div class="mermaid">
sequenceDiagram
    participant A as Process A
    participant M as Master
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

**해결 1:** Redlock (과반수 노드에 락)

**해결 2:** `WAIT` 명령으로 동기 복제 강제

```java
// 락 획득 후 복제 확인
redisTemplate.execute((RedisCallback<Long>) conn ->
    conn.wait(1, 100)); // 레플리카 1개 이상, 100ms 내 동기화 확인
```

**해결 3:** ZooKeeper/etcd (CP 시스템) 사용

---

### 시나리오 4: GC Stop-the-World

<div class="mermaid">
sequenceDiagram
    participant A as Process A
    participant B as Process B
    participant R as Redis

    A->>R: 락 획득 (TTL=30s)
    R-->>A: OK
    Note over A: GC STW 시작 (5s 경과)
    Note over R: 30s 경과 → TTL 만료
    B->>R: 락 획득
    R-->>B: OK
    Note over B: 작업 시작
    Note over A: GC 종료 (35s) → 락 이미 만료
    Note over A: 작업 재개
    Note over A,B: ⚠️ A, B 동시에 임계 영역 진입!
</div>

**해결:** Fencing Token 패턴

```java
// 락 획득 시 단조 증가 토큰 발급
long fencingToken = redisTemplate.opsForValue()
    .increment("fencing:token:resource");

// 공유 자원(DB)에서 토큰 검증
UPDATE shared_resource
SET data = ?, last_token = ?
WHERE id = ? AND last_token < ?  -- 오래된 토큰이면 무시
```

---

## 정리

1. **간단한 락**이 필요하면 Lettuce + SET NX EX + Lua 해제로 충분하다.
2. **프로덕션 환경**에서는 Redisson을 사용해 Watchdog, Pub/Sub 대기, 재진입을 자동으로 얻는다.
3. **단일 Redis 노드**는 마스터 장애 시 락이 유실될 수 있다. 고가용성이 필요하면 Redlock을 검토한다.
4. **Watchdog**은 leaseTime을 지정하지 않을 때만 활성화된다.
5. **락 해제는 반드시 Lua 스크립트**로 — GET/DEL을 분리하면 race condition이 생긴다.
6. **완벽한 분산 락은 없다.** 최종 방어선은 DB 레벨 멱등성과 Fencing Token이다.
