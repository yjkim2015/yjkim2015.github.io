---
title: "Kafka 핵심 개념 총정리 — 메시징 시스템부터 이벤트 스트리밍 플랫폼까지"
categories:
- KAFKA
toc: true
toc_sticky: true
toc_label: 목차
---

## Kafka란?

Apache Kafka는 LinkedIn에서 처음 개발되어 2011년 오픈소스로 공개된 **분산 이벤트 스트리밍 플랫폼**이다. 초기에는 단순한 메시지 큐로 사용되었지만, 현재는 단순 메시징을 넘어 실시간 데이터 파이프라인, 스트림 처리, 이벤트 소싱의 핵심 인프라로 자리잡았다.

### 전통적인 메시징 시스템 vs Kafka

| 구분 | 전통적인 메시지 큐 (RabbitMQ 등) | Kafka |
|------|----------------------------------|-------|
| **메시지 보관** | 소비 후 즉시 삭제 | 디스크에 보존 (설정 기간) |
| **소비 방식** | Push 기반 | Pull 기반 |
| **재처리** | 기본적으로 불가 | Offset 조정으로 재처리 가능 |
| **처리량** | 수만 TPS | 수백만 TPS |
| **순서 보장** | 큐 단위 | 파티션 단위 |
| **소비자 확장** | 큐 경쟁 소비 | Consumer Group으로 병렬 소비 |
| **주 용도** | 작업 큐, RPC | 이벤트 스트림, 로그 집계 |

Kafka의 핵심 설계 철학은 **"메시지를 로그처럼 취급"**하는 것이다. 메시지를 소비했다고 지우는 것이 아니라 로그 파일처럼 순서대로 append하고, 소비자가 자신의 위치(Offset)를 관리한다.

```
전통적인 메시지 큐:
Producer → [Queue] → Consumer (소비 후 삭제)

Kafka:
Producer → [Log: msg0, msg1, msg2, msg3, ...] → Consumer A (offset: 3)
                                               → Consumer B (offset: 1)
                                               → Consumer C (offset: 3)
각 소비자가 독립적으로 자신의 위치를 관리
```

---

## 핵심 구성요소

### Broker

Kafka 클러스터를 구성하는 **개별 서버 노드**다. 각 브로커는 고유한 ID를 가지며, 파티션의 데이터를 저장하고 클라이언트 요청을 처리한다.

```
Kafka Cluster
┌─────────────────────────────────────────────┐
│  Broker 1          Broker 2          Broker 3  │
│  (id: 1)           (id: 2)           (id: 3)   │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │Partition0│    │Partition1│    │Partition2│  │
│  │(Leader)  │    │(Leader)  │    │(Leader)  │  │
│  │Partition1│    │Partition2│    │Partition0│  │
│  │(Follower)│    │(Follower)│    │(Follower)│  │
│  └──────────┘    └──────────┘    └──────────┘  │
└─────────────────────────────────────────────┘
```

브로커의 주요 역할:
- 프로듀서로부터 메시지 수신 및 디스크 저장
- 컨슈머 요청에 메시지 전달
- 파티션 리더/팔로워 관리
- 다른 브로커와의 복제 조율

### Topic

메시지를 분류하는 **논리적 채널**이다. 데이터베이스의 테이블에 비유할 수 있다. 토픽 이름은 클러스터 내에서 유일해야 한다.

```
Topic: "order-events"
┌────────────────────────────────────────┐
│  Partition 0: [order#1] [order#5] ...  │
│  Partition 1: [order#2] [order#6] ...  │
│  Partition 2: [order#3] [order#7] ...  │
│  Partition 3: [order#4] [order#8] ...  │
└────────────────────────────────────────┘
```

### Partition

토픽을 구성하는 **물리적 저장 단위**다. 파티션은 Kafka 확장성의 핵심이다.

**파티션의 특성:**
- 각 파티션은 순서가 보장된 **불변 로그(immutable log)**
- 파티션 내에서만 순서 보장 (토픽 전체 순서 보장 불가)
- 각 파티션은 하나의 브로커에만 Leader가 존재
- 여러 브로커에 Replica가 분산 저장됨

```
Partition 0 (물리적 로그 파일):
Offset:  0        1        2        3        4
      ┌────────┬────────┬────────┬────────┬────────┐
      │ msg_A  │ msg_B  │ msg_C  │ msg_D  │ msg_E  │ → append only
      └────────┴────────┴────────┴────────┴────────┘
         ↑ 가장 오래된 메시지                ↑ 최신 메시지
```

**파티션 수 결정 기준:**
- 목표 처리량 / 단일 파티션 처리량
- 컨슈머 병렬 처리 수 (파티션 수 = 최대 컨슈머 수)
- 일반적으로 브로커 수의 배수로 설정

### Producer

토픽에 메시지를 **발행(publish)**하는 클라이언트다.

```java
// Spring Kafka Producer 예시
@Service
public class OrderProducer {

    private final KafkaTemplate<String, OrderEvent> kafkaTemplate;

    public void sendOrder(OrderEvent event) {
        // 키 지정 시 동일 키는 항상 같은 파티션으로
        kafkaTemplate.send("order-events", event.getOrderId(), event)
            .addCallback(
                result -> log.info("전송 성공: offset={}", result.getRecordMetadata().offset()),
                ex -> log.error("전송 실패", ex)
            );
    }
}
```

프로듀서의 파티션 결정 과정:
1. **키가 있는 경우**: `hash(key) % 파티션수` → 동일 키는 항상 같은 파티션
2. **키가 없는 경우**: RoundRobin 또는 Sticky Partitioner(기본값, 배치 효율 최적화)
3. **커스텀 Partitioner**: 직접 구현 가능

### Consumer

토픽에서 메시지를 **구독(consume)**하는 클라이언트다.

```java
// Spring Kafka Consumer 예시
@Service
public class OrderConsumer {

    @KafkaListener(topics = "order-events", groupId = "order-processing-group")
    public void handleOrder(ConsumerRecord<String, OrderEvent> record) {
        log.info("파티션={}, 오프셋={}, 메시지={}",
            record.partition(), record.offset(), record.value());
        processOrder(record.value());
    }
}
```

### Consumer Group

동일한 `group.id`를 공유하는 컨슈머들의 집합이다. **파티션은 그룹 내에서 하나의 컨슈머에게만 할당**된다.

```
Topic: "order-events" (파티션 4개)

Consumer Group A (order-processing):
┌─────────────────────────────────────────────┐
│  Consumer A1    Consumer A2    Consumer A3   │
│  [P0] [P1]      [P2]           [P3]         │
└─────────────────────────────────────────────┘
파티션 4개, 컨슈머 3개 → A1이 2개 담당

Consumer Group B (order-analytics):
┌─────────────────────────────────────────────┐
│  Consumer B1    Consumer B2                  │
│  [P0] [P1]      [P2] [P3]                   │
└─────────────────────────────────────────────┘
같은 토픽을 독립적으로 소비 (브로드캐스트 효과)
```

**중요한 규칙:**
- 파티션 수 > 컨슈머 수: 일부 컨슈머가 여러 파티션 담당
- 파티션 수 = 컨슈머 수: 1:1 할당 (이상적)
- 파티션 수 < 컨슈머 수: 일부 컨슈머는 유휴 상태 (낭비)

```
파티션 4개, 컨슈머 6개일 때:
Consumer 1 → P0
Consumer 2 → P1
Consumer 3 → P2
Consumer 4 → P3
Consumer 5 → 유휴 (idle)
Consumer 6 → 유휴 (idle)
```

---

## Offset 개념과 관리

Offset은 파티션 내에서 메시지의 **고유 위치 번호**다. 0부터 시작하며 단조 증가한다.

```
Partition 0:
┌────────┬────────┬────────┬────────┬────────┬────────┐
│offset=0│offset=1│offset=2│offset=3│offset=4│offset=5│
│ msg_A  │ msg_B  │ msg_C  │ msg_D  │ msg_E  │ msg_F  │
└────────┴────────┴────────┴────────┴────────┴────────┘
                                       ↑
                            Consumer committed offset = 4
                            (다음 poll 시 offset=4부터 시작)
```

### Offset 커밋 방식

**1. 자동 커밋 (Auto Commit)**
```java
// application.yml
spring:
  kafka:
    consumer:
      enable-auto-commit: true
      auto-commit-interval: 5000  # 5초마다 자동 커밋
```
- 간단하지만 메시지 손실 또는 중복 처리 위험 있음
- `poll()` 호출 시 이전 poll에서 받은 오프셋 커밋

**2. 수동 커밋 (Manual Commit)**
```java
@KafkaListener(topics = "order-events", groupId = "order-group")
public void handleOrder(ConsumerRecord<String, OrderEvent> record,
                        Acknowledgment ack) {
    try {
        processOrder(record.value());
        ack.acknowledge();  // 처리 성공 후 명시적 커밋
    } catch (Exception e) {
        // 커밋하지 않으면 다음 poll 시 재처리
        log.error("처리 실패, 재처리 예정", e);
    }
}
```

### Offset 관리 위치

Kafka 0.9 이전: ZooKeeper에 저장
Kafka 0.9 이후: `__consumer_offsets` 내부 토픽에 저장

```
__consumer_offsets 토픽:
Key: [group_id, topic, partition]
Value: [offset, metadata, timestamp]

예시:
"order-group" + "order-events" + 0 → offset: 1234
"order-group" + "order-events" + 1 → offset: 1187
"order-group" + "order-events" + 2 → offset: 1203
```

### Offset 리셋 전략

```java
// application.yml
spring:
  kafka:
    consumer:
      auto-offset-reset: earliest  # earliest | latest | none
```

| 전략 | 설명 | 사용 시나리오 |
|------|------|--------------|
| `earliest` | 가장 오래된 메시지부터 | 새 그룹, 전체 재처리 |
| `latest` | 가장 최신 메시지부터 | 새 그룹, 현재부터 소비 |
| `none` | 오프셋 없으면 예외 | 명시적 관리 |

---

## ZooKeeper vs KRaft

### ZooKeeper 모드 (전통적 방식)

Kafka 2.x까지의 전통적 구성으로, ZooKeeper가 클러스터 메타데이터를 관리한다.

```
ZooKeeper Ensemble (3~5 노드)
┌────────┐    ┌────────┐    ┌────────┐
│  ZK 1  │    │  ZK 2  │    │  ZK 3  │
│(Leader)│◄──►│(Follow)│◄──►│(Follow)│
└────────┘    └────────┘    └────────┘
     ↑              ↑              ↑
     └──────────────┼──────────────┘
                    │ 클러스터 메타데이터
                    │ (브로커 목록, 파티션 리더, ISR 등)
     ┌──────────────┴──────────────┐
     ↓                             ↓
┌──────────┐                ┌──────────┐
│ Broker 1 │                │ Broker 2 │
└──────────┘                └──────────┘
```

ZooKeeper가 관리하는 정보:
- 브로커 등록/해제
- 컨트롤러 선출
- 파티션 리더 정보
- ACL 설정

**ZooKeeper 방식의 단점:**
- 별도 ZooKeeper 클러스터 운영 부담
- 메타데이터 동기화 지연
- 파티션 수 증가 시 ZooKeeper 부하 증가
- 운영 복잡도 (두 시스템 동시 관리)

### KRaft 모드 (Kafka 3.x+)

Kafka 2.8에서 Early Access, 3.3에서 Production Ready로 발표된 **ZooKeeper 없는 모드**다.

```
KRaft Cluster (Quorum Controller)

Controller Quorum (3 노드):
┌────────────┐    ┌────────────┐    ┌────────────┐
│ Controller1│    │ Controller2│    │ Controller3│
│ (Active)   │◄──►│ (Standby)  │◄──►│ (Standby)  │
│ + Broker   │    │ + Broker   │    │ + Broker   │
└────────────┘    └────────────┘    └────────────┘

메타데이터는 내부 토픽 __cluster_metadata 에 Raft 합의로 저장
```

**KRaft의 장점:**

| 항목 | ZooKeeper | KRaft |
|------|-----------|-------|
| 운영 복잡도 | 두 시스템 | 하나의 시스템 |
| 지원 파티션 수 | ~200,000 | 수백만 |
| 컨트롤러 failover | 수십 초 | 수 초 |
| 메타데이터 일관성 | 최종적 일관성 | 강한 일관성 |
| 설정 | 복잡 | 단순 |

```properties
# KRaft 설정 예시 (server.properties)
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@kafka1:9093,2@kafka2:9093,3@kafka3:9093
listeners=PLAINTEXT://:9092,CONTROLLER://:9093
```

---

## Kafka의 로그 구조

Kafka의 저장 구조는 **append-only log**를 기반으로 한다. 이것이 Kafka가 고성능을 달성하는 핵심 이유다.

### 물리적 파일 구조

```
/kafka-logs/
└── order-events-0/          ← 토픽명-파티션번호
    ├── 00000000000000000000.log    ← 실제 메시지 데이터 (segment)
    ├── 00000000000000000000.index  ← offset → 파일 위치 인덱스
    ├── 00000000000000000000.timeindex ← timestamp → offset 인덱스
    ├── 00000000000001000000.log    ← 다음 세그먼트 (1000000번 offset부터)
    ├── 00000000000001000000.index
    └── 00000000000001000000.timeindex
```

파일명의 숫자는 해당 세그먼트의 **첫 번째 offset**이다.

### Segment

파티션 로그는 여러 **세그먼트(Segment)**로 나뉜다.

```
Partition 0 로그 (세그먼트 분할):

세그먼트 1: offset 0 ~ 999,999
┌──────────────────────────────────────┐
│  .log: [msg0][msg1]...[msg999999]    │
│  .index: offset→position 매핑        │
└──────────────────────────────────────┘

세그먼트 2: offset 1,000,000 ~ (현재 active)
┌──────────────────────────────────────┐
│  .log: [msg1000000]...[최신msg]      │ ← active segment (쓰기 중)
│  .index: offset→position 매핑        │
└──────────────────────────────────────┘
```

세그먼트 롤오버 조건:
- `log.segment.bytes`: 세그먼트 크기 초과 (기본 1GB)
- `log.roll.ms`: 최대 보관 시간 초과 (기본 7일)

### Append-Only 쓰기 성능

```
일반 랜덤 쓰기:
Disk: [seek→write] [seek→write] [seek→write]  ← 매번 헤드 이동

Kafka append-only:
Disk: [────────────────sequential write───────────────→]  ← 헤드 이동 없음
```

Kafka가 빠른 이유:
1. **Sequential I/O**: 순차 쓰기는 랜덤 쓰기보다 수십 배 빠름
2. **OS Page Cache 활용**: 커널이 자동으로 캐싱
3. **Zero-Copy**: `sendfile()` 시스템 콜로 커널 → 소켓 직접 전송 (데이터 복사 없음)
4. **배치 처리**: 여러 메시지를 묶어 한 번에 처리

### Index를 통한 빠른 검색

```
.index 파일 (희소 인덱스, sparse index):
offset 0    → position 0
offset 100  → position 4800
offset 200  → position 9600
...

특정 offset 조회:
1. index에서 가장 가까운 작은 offset 찾기 (이진 탐색)
2. 해당 position으로 .log 파일 seek
3. 순차 스캔으로 정확한 메시지 위치 찾기
```

### 로그 보관 정책

```properties
# 시간 기반 (기본 7일)
log.retention.hours=168

# 크기 기반
log.retention.bytes=1073741824  # 1GB

# 세그먼트 크기
log.segment.bytes=1073741824    # 1GB
```

삭제 방식:
- `delete`: 보관 기간 지난 세그먼트 삭제 (기본값)
- `compact`: 동일 키의 오래된 메시지 제거, 최신 값만 유지 (로그 컴팩션)

---

## ISR (In-Sync Replicas)

ISR은 리더 파티션과 **동기화 상태가 최신인 팔로워 집합**이다.

### ISR 동작 원리

```
Partition 0 복제 구조:

Leader (Broker 1)         Follower (Broker 2)       Follower (Broker 3)
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ offset: 0,1,2,3 │──────►│ offset: 0,1,2,3 │       │ offset: 0,1,2   │
│ (최신)           │       │ (최신, ISR에 포함)│       │ (1개 뒤처짐)    │
└─────────────────┘       └─────────────────┘       └─────────────────┘

ISR = {Broker1(Leader), Broker2}
Broker3는 뒤처져서 ISR에서 제외됨
```

팔로워가 ISR에서 제외되는 조건:
- `replica.lag.time.max.ms` (기본 30초) 동안 리더에서 fetch 요청이 없거나
- 복제가 너무 뒤처진 경우

### HW (High Watermark)

**컨슈머가 읽을 수 있는 최대 offset**이다. ISR의 모든 복제본이 복제 완료한 offset까지만 컨슈머에게 노출된다.

```
Leader Partition:
offset: 0  1  2  3  4  5
        ▓  ▓  ▓  ▓  ▓  ▓   ← 리더에 기록됨

Follower 1: offset 0~4 복제 완료
Follower 2: offset 0~3 복제 완료

High Watermark = 3 (모든 ISR이 복제한 최대 offset)
Consumer는 offset 3까지만 읽을 수 있음
offset 4, 5는 아직 컨슈머에게 불가시
```

---

## acks 설정과 트레이드오프

`acks`는 프로듀서가 메시지 전송 성공을 판단하는 기준이다.

### acks=0 (Fire and Forget)

```
Producer ──메시지 전송──► Leader Broker
Producer ◄─ 응답 없음 ─── (확인 안 함)

처리 흐름:
Producer → 전송 → 즉시 다음 메시지로
```

- **성능**: 최고 (응답 대기 없음)
- **안정성**: 최저 (브로커 장애 시 메시지 유실)
- **사용 사례**: 로그 수집, 메트릭 (일부 손실 허용)

### acks=1 (Leader Acknowledgment)

```
Producer ──메시지 전송──► Leader Broker (디스크에 기록)
Producer ◄──── ACK ──── Leader Broker
              (팔로워 복제 완료 확인 안 함)
```

- **성능**: 중간
- **안정성**: 중간 (리더 기록 후 팔로워 복제 전 장애 시 유실)
- **사용 사례**: 일반적인 경우

### acks=all (또는 acks=-1, ISR Acknowledgment)

```
Producer ──메시지 전송──► Leader Broker (디스크에 기록)
                          Leader ──복제──► Follower 1 (완료)
                          Leader ──복제──► Follower 2 (완료)
Producer ◄──── ACK ────── Leader Broker
              (모든 ISR 복제 완료 후 응답)
```

- **성능**: 가장 낮음 (모든 ISR 복제 대기)
- **안정성**: 최고 (ISR 전체 장애 없으면 유실 없음)
- **사용 사례**: 금융 거래, 주문 처리

```java
// Producer 설정
@Configuration
public class KafkaProducerConfig {

    @Bean
    public ProducerFactory<String, Object> producerFactory() {
        Map<String, Object> config = new HashMap<>();
        config.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "kafka1:9092,kafka2:9092");
        config.put(ProducerConfig.ACKS_CONFIG, "all");                    // 안전성 최우선
        config.put(ProducerConfig.RETRIES_CONFIG, 3);                     // 재시도 3회
        config.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);       // 멱등성 활성화
        config.put(ProducerConfig.MIN_INSYNC_REPLICAS_CONFIG, 2);        // 최소 2개 ISR 동기화
        config.put(ProducerConfig.COMPRESSION_TYPE_CONFIG, "snappy");     // 압축
        config.put(ProducerConfig.BATCH_SIZE_CONFIG, 16384);              // 배치 크기 16KB
        config.put(ProducerConfig.LINGER_MS_CONFIG, 5);                   // 최대 5ms 대기
        return new DefaultKafkaProducerFactory<>(config);
    }
}
```

### acks 설정 비교 요약

```
acks=0:
Producer → Broker
         ↑ 유실 가능
         성능: ★★★★★  안정성: ★☆☆☆☆

acks=1:
Producer → Leader(저장) → ACK
                     ↑ 팔로워 복제 전 리더 다운 시 유실
         성능: ★★★★☆  안정성: ★★★☆☆

acks=all:
Producer → Leader(저장) → Follower(저장) → ACK
                                       ↑ ISR 전체 장애만 유실
         성능: ★★☆☆☆  안정성: ★★★★★
```

### min.insync.replicas와의 관계

`acks=all`만으로는 부족하다. ISR이 리더 하나만 남아도 `acks=all`은 성공한다.

```properties
# 브로커 설정
min.insync.replicas=2  # ISR이 2개 미만이면 쓰기 거부

# 조합의 의미:
# acks=all + min.insync.replicas=2
# → 리더 포함 최소 2개의 브로커에 복제 완료해야 ACK
# → ISR이 1개(리더만)이면 NotEnoughReplicasException 발생
```

---

## 정리

| 개념 | 핵심 한 줄 요약 |
|------|----------------|
| Broker | Kafka 클러스터의 물리적 서버 노드 |
| Topic | 메시지를 분류하는 논리적 채널 |
| Partition | 토픽의 물리적 저장 단위, 순서 보장 및 확장성의 핵심 |
| Producer | 메시지를 발행하는 클라이언트 |
| Consumer | 메시지를 구독하는 클라이언트 |
| Consumer Group | 파티션을 분담하여 병렬 소비하는 컨슈머 집합 |
| Offset | 파티션 내 메시지의 고유 위치 번호 |
| ISR | 리더와 동기화된 팔로워 집합 |
| acks | 프로듀서의 메시지 전송 확인 기준 |
| KRaft | ZooKeeper 없이 Kafka 자체 Raft 합의로 메타데이터 관리 |
