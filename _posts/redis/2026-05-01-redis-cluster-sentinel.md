---
title: "Redis 배포 모드 — 싱글, 센티넬, 클러스터를 언제 써야 하는가"
categories:
- REDIS
toc: true
toc_sticky: true
toc_label: 목차
---

새벽 2시, 서비스가 죽었다는 알림이 온다. Redis 마스터 서버 한 대가 다운됐다. 재시작하려면 엔지니어가 일어나서 접속해야 한다. 복구까지 20분. 그 20분 동안 캐시가 없으니 DB에 쿼리가 몰리고, DB도 죽는다. 센티넬이 있었다면 30초 안에 자동으로 레플리카가 승격되어 서비스가 살아났을 것이다. **배포 모드 선택은 "언제 복구될 것인가"를 결정하는 인프라 설계다.**

## 세 가지 모드, 세 가지 상황

> **비유**: 싱글 모드는 혼자 일하는 자영업자다 — 주인이 아프면 가게가 닫힌다. 센티넬은 매니저가 있는 직원 구조다 — 주인이 쓰러져도 매니저가 대리를 세운다. 클러스터는 전국 프랜차이즈다 — 한 지점이 타도 다른 지점이 영업한다. 어느 구조를 선택할지는 "얼마나 크게, 얼마나 안정적으로 운영해야 하는가"에 달려 있다.

| 모드 | 자동 복구 | 수평 확장 | 최소 노드 | 적합 환경 |
|------|---------|---------|---------|---------|
| **싱글(Standalone)** | 없음 (수동) | 불가 | 1 | 개발, 테스트 |
| **센티넬(Sentinel)** | 있음 | 불가 (단일 마스터) | 4 (Sentinel 3 + Redis 1) | 운영, 수백 GB 이하 |
| **클러스터(Cluster)** | 있음 | 가능 | 6 (마스터 3 + 레플리카 3) | 대규모, TB급, 높은 처리량 |

---

## 싱글 모드 — 왜 운영 환경에서는 쓰면 안 되는가

싱글 모드는 Redis 프로세스 한 개가 전부다. 선택적으로 레플리카를 붙일 수 있지만, 마스터가 죽으면 사람이 직접 레플리카를 승격시켜야 한다.

```mermaid
graph LR
    C["Client"] --> M["Redis Master"]
    M -->|"비동기 복제 (선택)"| R["Redis Replica"]
```

### 왜 싱글 모드는 운영에 위험한가

마스터가 죽는 순간 **모든 쓰기가 실패**한다. 레플리카가 있어도 자동 승격이 없으므로:

1. 모니터링 알림이 울린다
2. 엔지니어가 잠에서 깨 접속한다
3. `REPLICAOF NO ONE`으로 레플리카를 수동 승격한다
4. 애플리케이션 설정의 Redis 주소를 바꾼다
5. 재배포한다

이 과정이 30분이면 서비스는 30분 죽는다. 새벽이면 1시간도 된다.

### 기본 설정 (redis.conf)

```conf
# 싱글 모드 기본 설정
bind 0.0.0.0
port 6379
daemonize yes

# 영속성 — 없으면 재시작 시 모든 데이터가 사라진다
save 900 1          # 900초 안에 1개 이상 변경 시 스냅샷
save 300 10
save 60 10000
appendonly yes      # AOF: 매 명령어를 로그로 기록
appendfsync everysec

# 메모리 한도 초과 시 퇴거 정책
maxmemory 2gb
maxmemory-policy allkeys-lru

logfile /var/log/redis/redis.log
```

### 레플리카 추가 (반쪽짜리 고가용성)

```conf
# 레플리카 서버의 redis.conf
replicaof 192.168.1.10 6379
replica-read-only yes   # 레플리카는 읽기 전용 — 실수로 쓰면 데이터 불일치 발생
```

레플리카를 붙이면 **읽기 분산**과 **데이터 백업**은 되지만, 자동 페일오버가 없으므로 여전히 수동 개입이 필요하다.

---

## 센티넬 모드 — 자동 페일오버의 실제 동작

> **비유**: 센티넬은 24시간 교대 근무하는 경비원이다. 주 건물(마스터)에 문제가 생기면 경비원들이 투표를 거쳐 부건물(레플리카)을 주 건물로 승격시키고, 고객(클라이언트)에게 "이제 저쪽으로 가세요"라고 안내한다.

Sentinel은 Redis 마스터/레플리카를 **감시**하고, 마스터 장애 시 **자동으로 레플리카를 마스터로 승격**시키는 별도 프로세스다.

### 왜 Sentinel을 3개 이상 써야 하는가

Sentinel 1개면 그 Sentinel 자체가 죽었을 때 페일오버가 불가능해진다. 2개면 과반수(2/2)가 필요한데, 한 쪽이 죽으면 과반수 미달이다. **3개 이상, 홀수**로 배포해야 과반수 quorum이 안정적으로 작동한다.

```mermaid
graph LR
    S1["Sentinel 1"] --- S2["Sentinel 2"]
    S2 --- S3["Sentinel 3"]
    S3 --- S1
    S1 & S2 & S3 -->|"PING 감시"| M["Redis Master :6379"]
    S1 & S2 & S3 -->|"PING 감시"| R1["Replica 1 :6379"]
    S1 & S2 & S3 -->|"PING 감시"| R2["Replica 2 :6379"]
    M -->|"비동기 복제"| R1
    M -->|"비동기 복제"| R2
```

### 페일오버의 5단계

```mermaid
sequenceDiagram
    participant S1 as Sentinel1
    participant R1 as Replica1
    participant C as Client
    S1->>S1: SDOWN 선언
    Note over S1: ODOWN 선언
    S1->>R1: REPLICAOF NO ONE
    S1-->>C: 새 마스터 알림
```

**SDOWN vs ODOWN**:
- **SDOWN (Subjectively Down)**: 내 눈에만 죽어 보임. 네트워크 일시 단절일 수 있음.
- **ODOWN (Objectively Down)**: quorum 이상이 동의. 그제서야 페일오버 시작.

이 두 단계 구분이 없으면, 네트워크가 잠깐 튀는 것만으로 불필요한 페일오버가 발생한다.

### Sentinel 설정 파일

```conf
# sentinel.conf
port 26379
daemonize yes
logfile /var/log/redis/sentinel.log

# 모니터링할 마스터: 이름, IP, 포트, quorum 수
# quorum 2 = 최소 2개 Sentinel이 동의해야 ODOWN 선언
sentinel monitor mymaster 192.168.1.10 6379 2

# 5초 응답 없으면 SDOWN
sentinel down-after-milliseconds mymaster 5000

# 페일오버 최대 허용 시간 (이 안에 완료 안 되면 실패 처리)
sentinel failover-timeout mymaster 60000

# 페일오버 후 레플리카들이 새 마스터를 동시에 동기화하는 수
# 1로 낮게 설정 → 나머지 레플리카들은 순차 동기화 (읽기 가용성 유지)
sentinel parallel-syncs mymaster 1

# 마스터에 requirepass 설정된 경우
sentinel auth-pass mymaster mypassword
```

### 레플리카 선택 기준 (우선순위)

페일오버 시 어떤 레플리카를 마스터로 선택할지:

1. `replica-priority`가 가장 낮은 노드 (0이면 후보 제외)
2. 복제 offset이 가장 큰 노드 — 마스터 데이터를 가장 많이 받은 노드
3. Run ID가 사전순으로 가장 작은 노드 (tie-breaker)

**실무 팁**: 특정 레플리카를 "절대 마스터가 되어선 안 되는" 용도(백업 전용)로 쓰려면 `replica-priority 0`으로 설정한다.

### Spring Boot 센티넬 연결

```yaml
spring:
  data:
    redis:
      sentinel:
        master: mymaster          # sentinel.conf의 이름과 일치해야 함
        nodes:
          - 192.168.1.10:26379
          - 192.168.1.11:26379
          - 192.168.1.12:26379
        password: sentinelpassword
      password: redispassword
      lettuce:
        pool:
          max-active: 10
```

```java
// 레플리카에서 읽기 분산 설정
@Bean
public LettuceClientConfigurationBuilderCustomizer lettuceCustomizer() {
    // REPLICA_PREFERRED: 레플리카 우선, 없으면 마스터
    // 읽기 부하를 레플리카로 분산하면서 페일오버 중에도 마스터에서 읽을 수 있다
    return builder -> builder.readFrom(ReadFrom.REPLICA_PREFERRED);
}
```

---

## 클러스터 모드 — 수평 확장의 작동 원리

> **비유**: Redis Cluster는 우체국 시스템과 같다. 우편번호(해시 슬롯)에 따라 서울 우체국(마스터 A), 부산 우체국(마스터 B), 대구 우체국(마스터 C)이 나눠 처리한다. 편지(데이터)는 우편번호를 보고 자동으로 올바른 우체국으로 라우팅된다.

단일 서버의 메모리 한계를 넘어서거나, 쓰기 처리량이 단일 마스터의 한계를 넘을 때 클러스터가 필요하다.

### 해시 슬롯: 데이터 분산의 핵심

Redis Cluster는 **16384개의 해시 슬롯**으로 키를 분산한다.

```mermaid
graph LR
    KEY["user:123"] -->|CRC16| SLOT["슬롯 계산"]
    SLOT -->|0~5460| MA["마스터 A"]
    SLOT -->|5461~10922| MB["마스터 B"]
    SLOT -->|10923~16383| MC["마스터 C"]
```

클라이언트가 잘못된 노드에 요청하면 `MOVED` 리다이렉션 응답이 온다:

```bash
GET user:123
# 이 키의 슬롯이 마스터 B에 있으면:
-MOVED 7638 192.168.1.11:7001
# 클라이언트는 해당 주소로 재요청한다
```

**클러스터 인식 클라이언트**(Lettuce, Jedis, Redisson)는 이 MOVED 리다이렉션을 자동으로 처리한다. 일반 클라이언트는 처리 못한다.

### 클러스터 생성 (최소 6노드)

```bash
# redis.conf — 각 노드에 설정
port 7000
cluster-enabled yes
cluster-config-file nodes-7000.conf  # 클러스터 상태 자동 저장
cluster-node-timeout 5000            # 5초 응답 없으면 PFAIL

appendonly yes
```

```bash
# 6노드로 클러스터 생성 (마스터 3 + 레플리카 3)
redis-cli --cluster create \
  192.168.1.10:7000 \
  192.168.1.11:7001 \
  192.168.1.12:7002 \
  192.168.1.10:7003 \
  192.168.1.11:7004 \
  192.168.1.12:7005 \
  --cluster-replicas 1   # 마스터 1개당 레플리카 1개
```

### 클러스터 페일오버 동작

센티넬과 달리 클러스터는 **노드들이 직접 투표**한다:

```mermaid
graph LR
    MB["MasterB"] -->|"MasterA FAIL 선언"| MB
    MC["MasterC"] -->|"동의"| MC
    RA["ReplicaA"] -->|"투표 요청"| MB
    RA -->|"투표 요청"| MC
    MB -->|"승인"| RA
    MC -->|"승인"| RA
    RA -->|"새 마스터 승격"| RA
```

---

## Multi-key 명령어 제약 — 클러스터의 가장 큰 함정

클러스터에서 가장 많이 당하는 함정이다. **여러 키를 한 명령어에서 다루면 에러가 난다.**

```bash
MSET user:1:name "김철수" user:2:name "이영희"
# → CROSSSLOT Keys in request don't hash to the same slot
# 이유: user:1과 user:2가 다른 슬롯에 배치될 수 있다
```

만약 이 제약을 무시하면? 클러스터에 배포하는 순간 기존에 잘 돌던 `MSET`, `SUNION`, `KEYS *`, Lua 스크립트가 모두 에러를 뿜는다.

### 해시 태그로 해결

키 이름의 `{...}` 안의 내용만으로 슬롯을 결정한다:

```bash
# {user:1} 부분만 슬롯 계산에 사용 → 두 키 모두 같은 슬롯
MSET {user:1}:name "김철수" {user:1}:email "kim@example.com"
MGET {user:1}:name {user:1}:email  # OK — 같은 슬롯

# 주의: 태그가 다르면 다른 슬롯
MSET {user:1}:name "김" {user:2}:name "이"  # 여전히 에러
```

```java
// Spring Data Redis에서 해시 태그 패턴
String userId = "1";
String nameKey    = "{user:" + userId + "}:name";
String emailKey   = "{user:" + userId + "}:email";
String sessionKey = "{user:" + userId + "}:session";

// 세 키 모두 {user:1} 기준으로 같은 슬롯 → MSET 가능
redisTemplate.opsForValue().multiSet(Map.of(
    nameKey, "김철수",
    emailKey, "kim@example.com"
));
```

**클러스터에서 제약이 있는 명령어들:**

| 명령어 | 제약 | 해결책 |
|--------|------|--------|
| `MSET`, `MGET` | 모든 키 같은 슬롯 | 해시 태그 |
| `SUNION`, `SINTER` | 모든 키 같은 슬롯 | 해시 태그 |
| `ZUNIONSTORE` | 모든 키 같은 슬롯 | 해시 태그 |
| `EVAL` (Lua) | KEYS의 모든 키 같은 슬롯 | 해시 태그 |
| `KEYS *` | 현재 노드만 반환 | 전 노드에 `SCAN` 실행 |

---

## 클러스터 운영

### 노드 추가 절차

```bash
# 1. 새 마스터 노드 추가 (슬롯 없는 상태로 참여)
redis-cli --cluster add-node \
  192.168.1.13:7006 \    # 새 노드
  192.168.1.10:7000      # 기존 클러스터 아무 노드

# 2. 리샤딩으로 슬롯 분배
redis-cli --cluster reshard 192.168.1.10:7000
# → 이동할 슬롯 수, 받을 노드 ID, 줄 노드 지정
```

리샤딩 중에도 서비스 중단 없이 진행된다. 슬롯 이동 중에는 `ASK` 리다이렉션으로 클라이언트가 임시 위치를 안내받는다.

### 클러스터 전체 다운 조건

한 마스터와 그 **모든 레플리카가 동시에 죽으면** 해당 슬롯에 접근 불가 → 기본 설정(`cluster-require-full-coverage yes`)에서는 클러스터 전체가 에러 상태가 된다.

```conf
# 일부 슬롯이 죽어도 나머지 슬롯은 서비스 유지하려면
cluster-require-full-coverage no
```

이 설정은 "일부 데이터가 안 되더라도 나머지는 살려야 한다"는 상황에만 사용한다.

### Spring Boot 클러스터 연결

```yaml
spring:
  data:
    redis:
      cluster:
        nodes:
          - 192.168.1.10:7000
          - 192.168.1.11:7001
          - 192.168.1.12:7002
          - 192.168.1.10:7003
          - 192.168.1.11:7004
          - 192.168.1.12:7005
        max-redirects: 3         # MOVED 리다이렉션 최대 횟수
      password: yourpassword
      lettuce:
        cluster:
          refresh:
            adaptive: true       # 페일오버 등 토폴로지 변경 시 자동 갱신
            period: 60s
        pool:
          max-active: 10
```

```java
@Bean
public LettuceClientConfigurationBuilderCustomizer lettuceCustomizer() {
    return builder -> builder
        .readFrom(ReadFrom.REPLICA_PREFERRED)  // 레플리카에서 읽기 분산
        .commandTimeout(Duration.ofSeconds(2));
}
```

---

## 모드 선택 가이드

```mermaid
graph LR
    START(["요구사항 분석"]) --> Q1{"데이터가 단일 서버<br>메모리에 들어가는가?"}
    Q1 -->|"NO (TB급)"| CLUSTER["클러스터 모드<br>— 수평 확장"]
    Q1 -->|"YES"| Q2{"운영 환경인가?<br>(마스터 장애 시 자동 복구 필요)"}
    Q2 -->|"YES"| SENTINEL["센티넬 모드<br>— 자동 페일오"]
    Q2 -->|"NO (개발/테스트)"| SINGLE["싱글 모드<br>— 간단, 빠른"]
    style CLUSTER fill:#88f,stroke:#00c,color:#000
    style SENTINEL fill:#8f8,stroke:#080,color:#000
    style SINGLE fill:#ff8,stroke:#880,color:#000
```

---

## 세 모드 종합 비교

| 항목 | 싱글 | 센티넬 | 클러스터 |
|------|------|--------|---------|
| 자동 페일오버 | 없음 | 있음 (30초 내) | 있음 (수십 초) |
| 수평 확장 | 불가 | 불가 | 가능 (마스터 추가) |
| 최소 노드 수 | 1 | Sentinel 3 + Redis 3 | 6 |
| Multi-key 명령어 | 자유 | 자유 | 해시 태그 필요 |
| 클라이언트 복잡도 | 낮음 | 중간 | 높음 |
| 운영 복잡도 | 낮음 | 중간 | 높음 |
| 쓰기 처리량 | 단일 마스터 | 단일 마스터 | 마스터 수에 비례 |

---

## 운영 주의사항 요약

**센티넬**:
- Sentinel 3개 이상, 홀수, **서로 다른 물리 서버**에 배포해야 한다. 같은 서버 2개가 죽으면 quorum이 깨진다.
- 페일오버 후 구 마스터가 재시작되면 자동으로 레플리카로 편입된다.
- 클라이언트는 Sentinel 주소로 연결하고, Sentinel이 현재 마스터 주소를 알려준다. Redis 주소를 직접 하드코딩하면 페일오버 후 연결이 끊긴다.

**클러스터**:
- 노드 추가 후 반드시 리샤딩으로 슬롯을 균등 분배해야 한다. 안 하면 새 노드는 빈 슬롯만 갖고 부하를 받지 못한다.
- `KEYS *`는 현재 노드의 키만 반환한다. 전체 키 순회가 필요하면 모든 노드에 `SCAN`을 실행해야 한다.
- Lua 스크립트에서 접근하는 모든 키는 KEYS 배열에 명시해야 한다. KEYS에 없으면 클러스터가 올바른 노드로 라우팅하지 못한다.

---

## 왜 Cluster인가? (vs Sentinel vs 단일 노드)

| 구성 | 목적 | 한계 |
|------|------|------|
| **단일 노드** | 개발/소규모 | 단일 장애점, 메모리 한계 |
| **Sentinel** | 고가용성(HA), 자동 failover | 수평 확장 불가, 여전히 단일 마스터 |
| **Cluster** | HA + 수평 확장(샤딩) | 크로스 슬롯 다중 키 명령 불가, 운영 복잡도 |

**실무 판단**: 메모리가 단일 노드 한계에 가깝거나 쓰기 처리량이 한계라면 Cluster. 메모리는 충분하지만 HA만 필요하면 Sentinel. AWS ElastiCache, GCP Memorystore는 내부적으로 이 구조를 관리형으로 제공한다.

---

## 실무에서 자주 하는 실수

**실수 1: Cluster에서 크로스 슬롯 명령 사용**
`MGET key1 key2`에서 두 키가 다른 슬롯에 있으면 `CROSSSLOT` 에러가 발생한다. 해시 태그(`{user}:profile`, `{user}:score`)로 같은 슬롯에 묶거나, 단일 키 명령으로 분리해야 한다.

**실수 2: Sentinel에서 클라이언트가 마스터 주소를 하드코딩**
failover 후 마스터가 바뀌어도 클라이언트가 이전 주소로 연결을 시도한다. Sentinel 주소를 설정하고 클라이언트가 Sentinel에 현재 마스터를 질의하도록 구성해야 한다(`Lettuce`, `Jedis` 모두 Sentinel 모드 지원).

**실수 3: 노드 추가 후 리샤딩 미실시**
새 노드는 빈 슬롯(0개)을 가지고 시작한다. 명시적으로 `redis-cli --cluster reshard`를 실행해 슬롯을 재분배하지 않으면 새 노드에 트래픽이 전혀 가지 않는다.

**실수 4: maxmemory 설정 없이 Cluster 운영**
각 노드에 `maxmemory`를 설정하지 않으면 메모리 부족 시 OS가 프로세스를 OOM Kill한다. Cluster 노드 수 × 노드 메모리의 70~80%를 `maxmemory`로 설정하고, `maxmemory-policy`를 워크로드에 맞게(`allkeys-lru` 등) 지정해야 한다.

**실수 5: min-replicas-to-write 미설정으로 데이터 유실**
기본값에서는 레플리카 없이도 쓰기가 허용된다. 마스터 장애 직전의 쓰기가 레플리카에 복제되기 전에 유실될 수 있다. `min-replicas-to-write 1`로 최소 1개 레플리카 확인 후 쓰기를 완료하도록 설정한다.

---

## 면접 포인트

**Q1. Redis Cluster의 슬롯 분배 방식은?**
총 16,384개 슬롯을 노드 수로 균등 분배한다. 키는 `CRC16(key) % 16384`로 슬롯을 결정한다. 해시 태그가 있으면(`{tag}`) 태그 부분만 해싱해 같은 슬롯에 배치할 수 있다. 클라이언트는 클러스터 토폴로지를 캐시하고 `MOVED` 응답 시 리다이렉트한다.

**Q2. Sentinel의 failover 과정은?**
① Sentinel들이 마스터에 주기적으로 PING — 응답 없으면 주관적 다운(SDOWN) ② 정족수(quorum) 이상 Sentinel이 동의하면 객관적 다운(ODOWN) ③ Sentinel 중 하나가 리더로 선출(Raft 유사) ④ ISR 중 가장 최신 레플리카를 새 마스터로 승격 ⑤ 클라이언트에 새 마스터 주소 통보.

**Q3. Cluster에서 Lua 스크립트 사용 시 주의점은?**
스크립트에서 접근하는 모든 키는 `KEYS` 배열에 선언해야 하며, 같은 슬롯에 있어야 한다. 다른 슬롯의 키를 스크립트 내에서 접근하면 `CROSSSLOT` 에러가 발생한다. 해시 태그로 관련 키를 같은 슬롯에 배치하는 설계가 선행되어야 한다.

**Q4. Cluster에서 장애 노드 복구 절차는?**
① `CLUSTER NODES`로 현재 상태 확인 ② 장애 노드 재시작 시 자동으로 슬롯 재연결 ③ 레플리카가 없어 슬롯이 유실된 경우 `CLUSTER RESET` 후 재가입 ④ `redis-cli --cluster check`로 슬롯 커버리지 검증. 레플리카를 각 마스터에 반드시 1개 이상 유지해야 한다.

**Q5. ElastiCache Cluster와 자체 구축 Redis Cluster의 차이는?**
ElastiCache는 노드 교체, 패치, 모니터링, 자동 failover를 AWS가 관리한다. 자체 구축 대비 운영 부담이 크게 줄지만, 특정 설정(`CONFIG` 명령) 제한, 커스텀 모듈 불가, 비용이 단점이다. 트래픽이 크거나 특수 Redis 모듈(RedisJSON, RedisSearch)이 필요하면 자체 구축을 검토한다.

---
## 극한 시나리오

### 시나리오 1: Redis Cluster 노드 장애 — 슬롯이 유실되는 순간

6노드 클러스터(마스터 3 + 레플리카 3)에서 마스터 1개와 그 레플리카가 동시에 장애납니다.

**무슨 일이 발생하는가:**
- 해당 마스터가 담당하는 슬롯(약 5,461개)에 대한 모든 요청이 `CLUSTERDOWN` 에러 반환
- 레플리카도 없으므로 자동 복구 불가
- 전체 클러스터가 정상 동작하지 않음 (기본값: 하나의 슬롯이라도 커버되지 않으면 클러스터 다운)

```bash
# 실제 장애 시 클러스터 상태 확인
redis-cli -c CLUSTER INFO
# cluster_state: fail  ← 이 상태면 쓰기/읽기 모두 불가

# 슬롯 커버리지 확인
redis-cli -c CLUSTER NODES | grep -v connected
```

**예방 설정:**
```bash
# redis.conf: 슬롯 일부 미커버 시에도 가용 슬롯은 계속 서빙
cluster-require-full-coverage no  # 기본값 yes → 반드시 no로 변경

# 효과: 5,461개 슬롯 장애 시 나머지 10,923개 슬롯은 정상 서비스
# 결제·인증 키가 정상 슬롯에 있다면 계속 처리 가능
```

**복구 절차:**
```bash
# 1. 새 노드 추가
redis-cli --cluster add-node new-node:6379 existing-node:6379

# 2. 장애 슬롯을 새 노드에 수동 할당
redis-cli --cluster reshard existing-node:6379

# 3. 클러스터 상태 검증
redis-cli --cluster check existing-node:6379
```

### 시나리오 2: Sentinel Quorum 부족 — Split Brain 발생

Sentinel 3개 중 1개가 네트워크 파티션으로 격리됩니다. 격리된 Sentinel이 마스터를 SDOWN으로 판정합니다.

**상황:**
- Sentinel A, B: 마스터 정상 연결 → ODOWN 판정 안 함
- Sentinel C(격리): 마스터 연결 불가 → SDOWN 판정, 단독으로 failover 시도

**결과:**
- Quorum(2) 미충족으로 실제 failover 발생하지 않음 (정상 동작)
- 그러나 Sentinel이 2개(`quorum=2`)인 환경에서는 1개 격리만으로 failover 발생 → Split Brain

```bash
# sentinel.conf: quorum은 반드시 과반수로 설정
sentinel monitor mymaster 127.0.0.1 6379 2  # Sentinel 3개 → quorum=2 (과반수)

# Sentinel 홀수 개 유지 필수 (짝수는 split-brain 위험)
# Sentinel 2개: quorum=2 → 1개 장애 시 failover 불가 (가용성 저하)
# Sentinel 3개: quorum=2 → 1개 장애 허용 (권장)
# Sentinel 5개: quorum=3 → 2개 장애 허용 (고가용성)
```

### 시나리오 3: 클러스터 운영 중 핫 슬롯 — 단일 노드 CPU 100%

특정 게임 이벤트에서 동일 해시 태그를 가진 키에 초당 20만 건이 집중됩니다.

```
상황: game:event:{season1}:* 키가 모두 같은 슬롯(해시 태그 "season1")
→ 단일 마스터 노드에 20만 QPS 집중
→ 해당 노드 CPU 100%, 응답 지연 급증
→ 나머지 5개 노드는 여유 있음
```

```java
// 잘못된 설계: 하나의 해시 태그에 모든 데이터 집중
String key = "game:event:{season1}:" + userId;  // 모두 같은 슬롯

// 올바른 설계: 버킷으로 슬롯 분산
int bucket = (int)(userId % 16);  // 16개 버킷
String key = "game:event:{season1_" + bucket + "}:" + userId;
// season1_0 ~ season1_15가 서로 다른 슬롯에 배치
// 20만 QPS → 16개 슬롯으로 분산 → 노드당 약 1.25만 QPS

// 조회 시 모든 버킷 합산 필요
public long getTotalEventCount() {
    return IntStream.range(0, 16)
        .mapToLong(b -> {
            String key = "game:event:count:{season1_" + b + "}";
            Long count = redisTemplate.opsForValue().get(key);
            return count != null ? count : 0L;
        })
        .sum();
}
```

---

## 왜 이 구성인가

**Redis Cluster와 Sentinel을 선택하는 이유는 단일 Redis 인스턴스가 SPOF(단일 장애점)이기 때문이다.**

| 구성 | 적합 상황 | 한계 |
|------|----------|------|
| Standalone | 개발/테스트, 장애 허용 가능 | SPOF, 스케일아웃 불가 |
| Sentinel | 자동 페일오버 필요, 데이터 분산 불필요 | 수평 확장 불가, 파티셔닝 없음 |
| Cluster | 대용량 데이터, 높은 처리량, 자동 샤딩 | 다중 키 연산 제한, 운영 복잡도 |

Sentinel은 마스터 장애 감지 시 자동으로 슬레이브를 마스터로 승격시켜 가용성을 유지한다. 데이터가 수십 GB를 초과하거나 쓰기 처리량이 단일 노드 한계에 도달하면 Cluster로 전환해 수평 확장한다.
