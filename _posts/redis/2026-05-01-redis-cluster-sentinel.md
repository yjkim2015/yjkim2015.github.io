---
title: "Redis 배포 모드 — 싱글, 센티넬, 클러스터"
categories:
- REDIS
toc: true
toc_sticky: true
toc_label: 목차
---

개발 환경에서 잘 돌아가던 Redis가 프로덕션에서 새벽에 죽었다. 마스터 한 대뿐이었고, 자동 복구 수단도 없었다. 엔지니어가 잠에서 깨 수동으로 레플리카를 마스터로 승격시키기까지 20분이 걸렸다. 센티넬이 있었다면 30초 안에 자동으로 해결됐을 문제다.

## 개요

> **비유**: 싱글 모드는 혼자 일하는 자영업자, 센티넬은 매니저가 있는 직원, 클러스터는 여러 지점을 운영하는 프랜차이즈다. 규모와 안정성 요구에 따라 선택이 달라진다.

Redis는 운영 목적과 규모에 따라 세 가지 배포 모드를 제공한다.

| 모드 | 특징 | 적합 환경 |
|------|------|----------|
| **싱글(Standalone)** | 단일 노드, 간단한 구성 | 개발, 소규모 서비스 |
| **센티넬(Sentinel)** | 자동 페일오버, 고가용성 | 중규모, 단일 마스터 |
| **클러스터(Cluster)** | 수평 확장, 데이터 분산 | 대규모, 고처리량 |

---

## 싱글 모드 (Standalone)

### 구성

단일 Redis 프로세스로 동작한다. 선택적으로 레플리카(Replica)를 추가할 수 있지만, 페일오버는 수동으로 처리해야 한다.

<div class="mermaid">
graph LR
    C[Client] --> M[Redis Master]
    M -->|비동기 복제 선택 사항| R[Redis Replica]
</div>

### 기본 설정 (redis.conf)

```conf
# 바인딩 주소
bind 0.0.0.0

# 포트
port 6379

# 백그라운드 실행
daemonize yes

# 데이터 디렉토리
dir /var/lib/redis

# RDB 스냅샷 (초:변경횟수)
save 900 1
save 300 10
save 60 10000

# AOF 활성화
appendonly yes
appendfsync everysec

# 최대 메모리 설정
maxmemory 2gb
maxmemory-policy allkeys-lru

# 로그 파일
logfile /var/log/redis/redis.log
```

### 레플리카 설정

```conf
# 레플리카 서버에서 설정
replicaof 192.168.1.10 6379

# 레플리카 읽기 전용 (기본값)
replica-read-only yes
```

### 한계

| 한계 | 설명 |
|------|------|
| **단일 장애점** | 마스터가 죽으면 서비스 중단 |
| **수동 페일오버** | 레플리카 승격을 사람이 직접 수행 |
| **단일 노드 용량** | 서버 메모리 이상으로 데이터 확장 불가 |
| **쓰기 성능** | 단일 마스터가 모든 쓰기 처리 |

---

## 센티넬 모드 (Sentinel)

### 아키텍처

Sentinel은 Redis 마스터/레플리카를 **모니터링**하고, 마스터 장애 시 **자동으로 레플리카를 마스터로 승격**시키는 별도 프로세스다.

<div class="mermaid">
graph TD
    C[Client] --> SC[Sentinel 클러스터]
    SC --> M[Redis Master]
    M -->|복제| R1[Redis Replica 1]
    M -->|복제| R2[Redis Replica 2]
</div>

장애 발생:

<div class="mermaid">
sequenceDiagram
    participant S as Sentinel
    participant M as Redis Master
    participant R as Replica
    participant C as Client

    Note over M: 다운 💀
    S->>S: SDOWN 감지
    S->>S: 다른 Sentinel들과 quorum 합의
    S->>S: ODOWN 선언
    S->>R: REPLICAOF NO ONE (새 마스터로 승격)
    S-->>C: 새 마스터 주소 알림
</div>

**최소 구성:** Sentinel 3개 이상 (quorum 과반수 필요)

### SDOWN vs ODOWN

| 상태 | 의미 | 조건 |
|------|------|------|
| **SDOWN** (Subjectively Down) | 하나의 Sentinel이 마스터와 통신 실패 감지 | `down-after-milliseconds` 초과 |
| **ODOWN** (Objectively Down) | 과반수 Sentinel이 SDOWN에 동의 | quorum 수 이상 동의 |

ODOWN이 되어야 페일오버가 시작된다. 이를 통해 네트워크 일시 단절로 인한 오탐을 방지한다.

### Sentinel 설정

**Redis 서버 설정 (redis.conf):**

```conf
# 마스터 서버
port 6379
bind 0.0.0.0

# 레플리카 서버
port 6379
replicaof 192.168.1.10 6379
```

**Sentinel 설정 (sentinel.conf):**

```conf
port 26379
daemonize yes
logfile /var/log/redis/sentinel.log

# 모니터링할 마스터 이름, 주소, 포트, quorum
# quorum: 페일오버를 선언하는 데 필요한 최소 Sentinel 수
sentinel monitor mymaster 192.168.1.10 6379 2

# 마스터와 통신 불가로 판단할 시간 (밀리초)
sentinel down-after-milliseconds mymaster 5000

# 페일오버 타임아웃
sentinel failover-timeout mymaster 60000

# 페일오버 후 동시에 마스터를 바라보게 할 레플리카 수
sentinel parallel-syncs mymaster 1

# 인증 (마스터에 requirepass 설정된 경우)
sentinel auth-pass mymaster mypassword
```

### Sentinel 클러스터 구성 예시

<div class="mermaid">
graph TD
    SV1["서버 1"]
    SV2["서버 2"]
    SV3["서버 3"]
    SV1 --> M["Redis Master :6379"]
    SV1 --> S1["Sentinel 1 :26379"]
    SV2 --> R1["Redis Replica :6379"]
    SV2 --> S2["Sentinel 2 :26379"]
    SV3 --> R2["Redis Replica :6379"]
    SV3 --> S3["Sentinel 3 :26379"]
    M -->|복제| R1
    M -->|복제| R2
</div>

### 자동 페일오버 흐름

<div class="mermaid">
sequenceDiagram
    participant S1 as Sentinel 1
    participant S2 as Sentinel 2/3
    participant M as Master
    participant R1 as 선택된 Replica
    participant R2 as 나머지 Replica
    participant C as Client

    S1->>M: PING (응답 없음)
    Note over S1: SDOWN 선언
    S1->>S2: 마스터 상태 공유
    Note over S2: quorum(2) 이상 동의
    Note over S1,S2: ODOWN 선언
    S1->>S2: 페일오버 리더 투표
    Note over S1: 리더 선출됨
    Note over S1: 레플리카 선택 (복제 지연, 우선순위, run ID 기준)
    S1->>R1: REPLICAOF NO ONE
    Note over R1: 새 마스터로 승격
    S1->>R2: 새 마스터를 바라보도록 재설정
    S1-->>C: 새 마스터 주소 알림
</div>

### Sentinel API 활용

```bash
# 마스터 주소 조회
redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster

# 마스터 정보
redis-cli -p 26379 SENTINEL masters

# 레플리카 목록
redis-cli -p 26379 SENTINEL replicas mymaster

# Sentinel 목록
redis-cli -p 26379 SENTINEL sentinels mymaster
```

---

## 클러스터 모드 (Cluster)

### 해시 슬롯과 데이터 분산

Redis Cluster는 **16384개의 해시 슬롯**을 사용해 데이터를 분산한다.

<div class="mermaid">
graph LR
    KEY[key] -->|CRC16 % 16384| SLOT[슬롯 번호]
    SLOT -->|0 ~ 5460| MA[마스터 A]
    SLOT -->|5461 ~ 10922| MB[마스터 B]
    SLOT -->|10923 ~ 16383| MC[마스터 C]
</div>

키를 저장할 때 슬롯 번호를 계산하고, 해당 슬롯을 담당하는 노드에 저장한다. 클라이언트가 잘못된 노드에 요청하면 `MOVED` 리다이렉션 응답을 받는다.

```bash
# 클라이언트가 노드 A에 요청
GET mykey

# 실제 슬롯은 노드 B에 있으면
-MOVED 7638 192.168.1.11:6379
# 클라이언트는 해당 노드로 재요청
```

### 클러스터 구성

**최소 구성:** 마스터 3개 + 레플리카 3개 (각 마스터당 1개 레플리카)

**redis.conf 설정:**

```conf
port 7000
cluster-enabled yes
cluster-config-file nodes-7000.conf   # 클러스터 상태 자동 저장 파일
cluster-node-timeout 5000             # 노드 장애 판단 시간 (밀리초)
appendonly yes
```

**클러스터 생성:**

```bash
# 6개 노드로 클러스터 생성 (마스터 3 + 레플리카 3)
redis-cli --cluster create \
  192.168.1.10:7000 \
  192.168.1.11:7001 \
  192.168.1.12:7002 \
  192.168.1.10:7003 \
  192.168.1.11:7004 \
  192.168.1.12:7005 \
  --cluster-replicas 1   # 마스터당 레플리카 1개
```

### 클러스터 상태 확인

```bash
# 클러스터 정보
redis-cli -p 7000 cluster info

# 노드 목록 및 슬롯 분배
redis-cli -p 7000 cluster nodes

# 슬롯별 노드 확인
redis-cli -p 7000 cluster slots
```

### 리샤딩 (Resharding)

데이터를 재분배하거나 노드를 추가/제거할 때 슬롯을 이동한다.

```bash
# 리샤딩 실행
redis-cli --cluster reshard 192.168.1.10:7000

# 이동할 슬롯 수 입력
How many slots do you want to move (from 1 to 16384)? 1000

# 슬롯을 받을 노드 ID 입력
What is the receiving node ID? <node-id>

# 슬롯을 줄 노드 지정 (all 또는 특정 노드 ID)
Please enter all the source node IDs.
Type 'all' to use all nodes as source nodes for the hash slots.
Source node #1: all
```

**리샤딩 중에도 서비스 중단 없이 진행된다.** 슬롯 이동 시 `ASK` 리다이렉션으로 클라이언트가 정상 처리한다.

### 노드 추가

```bash
# 새 마스터 노드 추가
redis-cli --cluster add-node \
  192.168.1.13:7006 \    # 새 노드
  192.168.1.10:7000      # 기존 클러스터 노드

# 새 레플리카 노드 추가
redis-cli --cluster add-node \
  192.168.1.13:7007 \
  192.168.1.10:7000 \
  --cluster-slave \
  --cluster-master-id <master-node-id>

# 이후 리샤딩으로 슬롯 분배
```

### 노드 제거

```bash
# 제거 전 슬롯을 다른 노드로 이동 (리샤딩)
redis-cli --cluster reshard 192.168.1.10:7000

# 노드 제거
redis-cli --cluster del-node \
  192.168.1.10:7000 \
  <node-id-to-remove>
```

---

## 클러스터에서 Multi-key 명령어 제약

Redis Cluster에서는 **하나의 명령어에 포함된 모든 키가 같은 슬롯**에 있어야 한다.

```bash
# 에러 발생 — key1과 key2가 다른 슬롯에 있을 수 있음
MSET key1 val1 key2 val2
# → CROSSSLOT Keys in request don't hash to the same slot

SUNION set1 set2
LMOVE list1 list2 LEFT RIGHT
```

### 해시 태그로 해결

키 이름에 `{태그}` 형식을 사용하면, 슬롯 계산 시 `{}` 안의 내용만 사용한다.

```bash
# {user:1} 부분으로만 슬롯 결정 → 같은 슬롯에 배치
MSET {user:1}:name "김철수" {user:1}:email "kim@example.com"
HSET {user:1}:profile name "김철수"
SET {user:1}:session "token123"

# 이제 같은 슬롯이므로 사용 가능
MGET {user:1}:name {user:1}:email
```

```java
// Spring Data Redis에서 해시 태그 사용
String userId = "1";
String nameKey    = "{user:" + userId + "}:name";
String emailKey   = "{user:" + userId + "}:email";
String sessionKey = "{user:" + userId + "}:session";

// MSET 사용 가능 — 모두 같은 슬롯
redisTemplate.opsForValue().multiSet(Map.of(
    nameKey, "김철수",
    emailKey, "kim@example.com"
));
```

**제약이 있는 명령어:**

| 명령어 | 클러스터 제약 |
|--------|------------|
| MSET, MGET | 모든 키가 같은 슬롯 |
| SUNION, SINTER, SDIFF | 모든 키가 같은 슬롯 |
| ZUNIONSTORE, ZINTERSTORE | 모든 키가 같은 슬롯 |
| LMOVE, RPOPLPUSH | 모든 키가 같은 슬롯 |
| EVAL (Lua) | KEYS의 모든 키가 같은 슬롯 |

---

## 클러스터 복제와 페일오버

### 복제 구조

<div class="mermaid">
graph LR
    MA["마스터 A (슬롯 0~5460)"] <-->|비동기 복제| RA[레플리카 A]
    MB["마스터 B (슬롯 5461~10922)"] <-->|비동기 복제| RB[레플리카 B]
    MC["마스터 C (슬롯 10923~16383)"] <-->|비동기 복제| RC[레플리카 C]
</div>

### 자동 페일오버

<div class="mermaid">
sequenceDiagram
    participant MA as 마스터 A
    participant MB as 마스터 B/C
    participant RA as 레플리카 A

    Note over MA: cluster-node-timeout 동안 응답 없음
    Note over MB: 마스터 A → PFAIL 상태로 표시
    MB->>MB: 과반수 마스터 PFAIL 동의 → FAIL 선언
    RA->>MB: 페일오버 투표 요청
    MB-->>RA: 투표 승인 (과반수)
    Note over RA: 새 마스터로 승격
    Note over RA: 슬롯 0~5460 담당 인계
</div>

### 페일오버 후 복구

```bash
# 다운된 마스터를 재시작하면 자동으로 레플리카로 참여
# 수동으로 마스터로 복귀시키려면
redis-cli -p 7003 cluster failover
```

### 클러스터 전체 다운 조건

한 마스터와 그 **모든 레플리카가 동시에 죽으면** 해당 슬롯에 접근 불가 → 클러스터 전체가 에러 상태가 된다.

```conf
# 일부 슬롯이 죽어도 나머지로 계속 서비스하려면
cluster-require-full-coverage no  # 기본값: yes
```

---

## 세 모드 비교 표

| 항목 | 싱글 | 센티넬 | 클러스터 |
|------|------|--------|---------|
| **고가용성** | 없음 | 있음 (자동 페일오버) | 있음 (자동 페일오버) |
| **수평 확장** | 불가 | 불가 (단일 마스터) | 가능 (다중 마스터) |
| **데이터 분산** | 단일 노드 | 단일 마스터 | 16384 슬롯 분산 |
| **최소 노드 수** | 1 | 3 (Sentinel) + 1 (Redis) | 6 (마스터 3 + 레플리카 3) |
| **Multi-key 명령어** | 제한 없음 | 제한 없음 | 해시 태그 필요 |
| **Lua 스크립트** | 제한 없음 | 제한 없음 | 단일 슬롯 제약 |
| **클라이언트 복잡도** | 낮음 | 중간 (Sentinel URL) | 높음 (클러스터 클라이언트) |
| **운영 복잡도** | 낮음 | 중간 | 높음 |
| **페일오버 시간** | 수동 | 수십 초 | 수십 초 |
| **읽기 스케일** | 레플리카로 가능 | 레플리카로 가능 | 각 마스터의 레플리카 |
| **적합 환경** | 개발, 테스트 | 단일 마스터 운영 | 대규모, 고처리량 |

---

## Spring Boot 연결 설정

### 싱글 모드

```yaml
spring:
  data:
    redis:
      host: localhost
      port: 6379
      password: yourpassword
      timeout: 2000ms
      lettuce:
        pool:
          max-active: 10
          max-idle: 10
          min-idle: 1
          max-wait: 1000ms
```

```java
@Configuration
public class RedisConfig {

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new GenericJackson2JsonRedisSerializer());
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setHashValueSerializer(new GenericJackson2JsonRedisSerializer());
        return template;
    }
}
```

---

### 센티넬 모드

```yaml
spring:
  data:
    redis:
      sentinel:
        master: mymaster                # sentinel.conf의 이름과 일치
        nodes:
          - 192.168.1.10:26379
          - 192.168.1.11:26379
          - 192.168.1.12:26379
        password: sentinelpassword      # Sentinel 인증 (설정된 경우)
      password: redispassword           # Redis 서버 인증
      lettuce:
        pool:
          max-active: 10
```

```java
// 읽기 전략 설정 (레플리카에서 읽기)
@Bean
public LettuceClientConfigurationBuilderCustomizer lettuceCustomizer() {
    return builder -> builder.readFrom(ReadFrom.REPLICA_PREFERRED);
}
```

**읽기 전략 옵션:**

| 전략 | 설명 |
|------|------|
| `MASTER` | 항상 마스터에서 읽기 (기본값) |
| `MASTER_PREFERRED` | 마스터 우선, 불가 시 레플리카 |
| `REPLICA` | 항상 레플리카에서 읽기 |
| `REPLICA_PREFERRED` | 레플리카 우선, 불가 시 마스터 |
| `NEAREST` | 가장 낮은 지연 노드 |

---

### 클러스터 모드

```yaml
spring:
  data:
    redis:
      cluster:
        nodes:
          - 192.168.1.10:7000
          - 192.168.1.10:7003
          - 192.168.1.11:7001
          - 192.168.1.11:7004
          - 192.168.1.12:7002
          - 192.168.1.12:7005
        max-redirects: 3              # MOVED 리다이렉션 최대 횟수
      password: yourpassword
      lettuce:
        cluster:
          refresh:
            adaptive: true            # 토폴로지 변경 시 자동 갱신
            period: 60s               # 주기적 토폴로지 갱신
        pool:
          max-active: 10
```

```java
@Configuration
public class RedisClusterConfig {

    // 클러스터에서도 레플리카 읽기 설정
    @Bean
    public LettuceClientConfigurationBuilderCustomizer lettuceCustomizer() {
        return builder -> builder
            .readFrom(ReadFrom.REPLICA_PREFERRED)
            .commandTimeout(Duration.ofSeconds(2));
    }

    // 클러스터 토폴로지 갱신 설정
    @Bean
    public ClusterTopologyRefreshOptions clusterTopologyRefreshOptions() {
        return ClusterTopologyRefreshOptions.builder()
            .enableAdaptiveRefreshTrigger(
                RefreshTrigger.MOVED_REDIRECT,
                RefreshTrigger.PERSISTENT_RECONNECTS
            )
            .adaptiveRefreshTriggersTimeout(Duration.ofSeconds(30))
            .build();
    }
}
```

---

### Redisson 연결 설정

```yaml
# application.yml (Redisson Spring Boot Starter)
spring:
  redis:
    redisson:
      config: |
        # 싱글 모드
        singleServerConfig:
          address: "redis://localhost:6379"

        # 센티넬 모드
        sentinelServersConfig:
          masterName: mymaster
          sentinelAddresses:
            - "redis://192.168.1.10:26379"
            - "redis://192.168.1.11:26379"
            - "redis://192.168.1.12:26379"

        # 클러스터 모드
        clusterServersConfig:
          nodeAddresses:
            - "redis://192.168.1.10:7000"
            - "redis://192.168.1.11:7001"
            - "redis://192.168.1.12:7002"
```

```java
// 코드로 설정
@Bean
public RedissonClient redissonClient() {
    Config config = new Config();

    // 싱글
    config.useSingleServer().setAddress("redis://localhost:6379");

    // 센티넬
    config.useSentinelServers()
        .setMasterName("mymaster")
        .addSentinelAddress(
            "redis://192.168.1.10:26379",
            "redis://192.168.1.11:26379",
            "redis://192.168.1.12:26379"
        );

    // 클러스터
    config.useClusterServers()
        .addNodeAddress(
            "redis://192.168.1.10:7000",
            "redis://192.168.1.11:7001",
            "redis://192.168.1.12:7002"
        );

    return Redisson.create(config);
}
```

---

## 모드 선택 가이드

<div class="mermaid">
graph TD
    START([요구사항 분석]) --> Q1{데이터가 단일 서버<br/>메모리에 충분히 들어가는가?}
    Q1 -->|NO| CLUSTER[클러스터 모드<br/>수평 확장 필요]
    Q1 -->|YES| Q2{마스터 장애 시<br/>자동 복구가 필요한가?}
    Q2 -->|YES| SENTINEL1[센티넬 모드]
    Q2 -->|NO| Q3{개발/테스트<br/>환경인가?}
    Q3 -->|YES| SINGLE[싱글 모드]
    Q3 -->|NO| SENTINEL2[센티넬 모드<br/>운영 환경 권장]
    style CLUSTER fill:#88f,stroke:#00c,color:#000
    style SENTINEL1 fill:#8f8,stroke:#080,color:#000
    style SENTINEL2 fill:#8f8,stroke:#080,color:#000
    style SINGLE fill:#ff8,stroke:#880,color:#000
</div>

**실무 권장:**
- 개발/테스트: 싱글 모드
- 운영 (수백 GB 이하): 센티넬 모드
- 운영 (TB급, 높은 처리량): 클러스터 모드

---

## 운영 주의사항

### 센티넬

- Sentinel을 **최소 3개** 홀수로 배포해야 quorum을 만족시킬 수 있다.
- Sentinel을 마스터/레플리카와 **다른 물리 서버**에 배포해야 네트워크 분리 상황에서 올바르게 동작한다.
- 페일오버 후 구 마스터가 돌아오면 **자동으로 레플리카로 편입**된다.

### 클러스터

- 노드 추가 후 반드시 **리샤딩**으로 슬롯을 균등 분배해야 한다.
- `cluster-require-full-coverage yes` (기본값)이면 일부 슬롯이 죽을 때 클러스터 전체가 에러 상태가 된다. 부분 서비스를 허용하려면 `no`로 변경한다.
- 클러스터 환경에서 `KEYS *`는 **현재 노드의 키만** 반환한다. 전체 키를 순회하려면 모든 노드에 `SCAN`을 실행해야 한다.
- 클라이언트는 **클러스터 인식 클라이언트**(Lettuce, Jedis, Redisson)를 사용해야 한다. 일반 클라이언트는 `MOVED` 리다이렉션을 처리하지 못한다.
