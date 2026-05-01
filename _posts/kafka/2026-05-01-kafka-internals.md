---
title: "Kafka 동작 원리 딥다이브 — Producer부터 트랜잭션까지"
categories:
- KAFKA
toc: true
toc_sticky: true
toc_label: 목차
---

## Producer 내부 동작

### 전체 아키텍처

```
Application Thread                    Network Thread (I/O Thread)
┌────────────────────────┐            ┌─────────────────────────┐
│ producer.send(record)  │            │                         │
│         ↓              │            │                         │
│  Serializer            │            │                         │
│         ↓              │            │                         │
│  Partitioner           │            │                         │
│         ↓              │            │                         │
│  RecordAccumulator     │───batch───►│  Sender                 │
│  ┌─────┬─────┬─────┐  │  ready     │    ↓                    │
│  │ P0  │ P1  │ P2  │  │  batches   │  NetworkClient          │
│  │batch│batch│batch│  │            │    ↓                    │
│  └─────┴─────┴─────┘  │            │  Broker 1, 2, 3 ...     │
└────────────────────────┘            └─────────────────────────┘
```

### 배치(Batch) 처리

프로듀서는 메시지를 하나씩 보내지 않는다. 성능을 위해 **RecordAccumulator**에 배치로 모아서 전송한다.

```
RecordAccumulator (파티션별 deque):

Partition 0 deque:
┌──────────────────────────────────────┐
│  ProducerBatch 1 (꽉 참, 전송 대기)  │
│  [msg1][msg2][msg3]...[msg100]       │  ← batch.size 초과
├──────────────────────────────────────┤
│  ProducerBatch 2 (현재 채우는 중)    │
│  [msg101][msg102]                    │  ← 아직 채우는 중
└──────────────────────────────────────┘
```

배치 전송 트리거 조건:
- `batch.size`: 배치가 설정 크기에 도달 (기본 16KB)
- `linger.ms`: 설정 시간이 경과 (기본 0ms, 즉시 전송)

```java
// 처리량 최적화 설정
props.put(ProducerConfig.BATCH_SIZE_CONFIG, 65536);    // 64KB
props.put(ProducerConfig.LINGER_MS_CONFIG, 20);         // 20ms 대기
// → 20ms 동안 모은 메시지를 한 번에 전송
```

**linger.ms 효과:**

```
linger.ms=0 (기본):
t=0: msg1 → 즉시 전송
t=1: msg2 → 즉시 전송
t=2: msg3 → 즉시 전송
→ 네트워크 요청 3번

linger.ms=20:
t=0:  msg1 도착 → 대기
t=5:  msg2 도착 → 대기
t=18: msg3 도착 → 대기
t=20: 배치 전송 [msg1, msg2, msg3]
→ 네트워크 요청 1번 (처리량 3배, 지연 20ms 증가)
```

### 압축(Compression)

```java
props.put(ProducerConfig.COMPRESSION_TYPE_CONFIG, "snappy");
// none | gzip | snappy | lz4 | zstd
```

| 압축 알고리즘 | 압축률 | CPU 사용 | 속도 | 추천 |
|--------------|--------|----------|------|------|
| none | - | 없음 | 최고 | 네트워크 충분 시 |
| gzip | 높음 | 높음 | 느림 | 저장 공간 절약 우선 |
| snappy | 중간 | 낮음 | 빠름 | 범용 (Google 개발) |
| lz4 | 중간 | 매우 낮음 | 매우 빠름 | 고처리량 |
| zstd | 높음 | 중간 | 중간 | Kafka 2.1+ 추천 |

압축은 **배치 단위**로 적용된다. 배치가 클수록 압축 효율이 좋아진다.

### 파티셔닝 전략

```java
// 1. 키 해시 파티셔닝 (DefaultPartitioner)
ProducerRecord<String, String> record =
    new ProducerRecord<>("order-events", "user-123", "order data");
// hash("user-123") % 파티션수 → 항상 같은 파티션

// 2. 명시적 파티션 지정
ProducerRecord<String, String> record =
    new ProducerRecord<>("order-events", 2, "user-123", "order data");
// 무조건 파티션 2

// 3. 커스텀 파티셔너
public class RegionPartitioner implements Partitioner {
    @Override
    public int partition(String topic, Object key, byte[] keyBytes,
                         Object value, byte[] valueBytes, Cluster cluster) {
        String region = ((OrderEvent) value).getRegion();
        List<PartitionInfo> partitions = cluster.partitionsForTopic(topic);
        int numPartitions = partitions.size();

        // 서울 → 앞쪽 파티션, 그 외 → 뒤쪽 파티션
        if ("SEOUL".equals(region)) {
            return Math.abs(key.hashCode()) % (numPartitions / 2);
        }
        return numPartitions / 2 + Math.abs(key.hashCode()) % (numPartitions / 2);
    }
}
```

**Sticky Partitioner (Kafka 2.4+, 현재 기본값):**

```
키 없는 메시지의 라운드로빈 문제:
msg1 → P0 (배치 즉시 전송)
msg2 → P1 (배치 즉시 전송)
msg3 → P2 (배치 즉시 전송)
→ 배치가 작아 압축 효율 저하, 네트워크 요청 증가

Sticky Partitioner:
msg1, msg2, msg3 → 모두 P0에 쌓음 (배치 꽉 찰 때까지)
배치 전송 후 → 다음 파티션으로 전환
→ 큰 배치 = 좋은 압축 효율
```

---

## Consumer 내부 동작

### Poll 루프

Kafka 컨슈머의 핵심은 **poll 루프**다. 컨슈머는 능동적으로 브로커에게 데이터를 요청(pull)한다.

```java
@Component
public class OrderConsumerService {

    private final KafkaConsumer<String, OrderEvent> consumer;

    public void startConsuming() {
        consumer.subscribe(List.of("order-events"));

        while (true) {
            // poll: 브로커에 메시지 요청
            ConsumerRecords<String, OrderEvent> records =
                consumer.poll(Duration.ofMillis(100));

            // 가져온 메시지 처리
            for (ConsumerRecord<String, OrderEvent> record : records) {
                processOrder(record.value());
            }

            // 오프셋 커밋 (처리 완료 표시)
            consumer.commitSync();
        }
    }
}
```

**poll() 동작 세부 과정:**

```
1. poll(timeout) 호출
   ↓
2. Fetcher가 각 파티션 리더에 FetchRequest 전송
   ↓
3. 브로커: High Watermark 이하의 메시지 반환
   ↓
4. Deserializer로 역직렬화
   ↓
5. ConsumerRecords 반환
   ↓
6. 다음 poll() 이전에 max.poll.interval.ms 초과하면 리밸런싱 트리거!
```

### Fetch 관련 설정

```properties
# 최소 fetch 크기 (데이터가 이 크기 이상 쌓일 때까지 대기)
fetch.min.bytes=1024         # 1KB

# 최대 대기 시간 (fetch.min.bytes 미달성 시에도 이 시간 후 반환)
fetch.max.wait.ms=500        # 500ms

# 파티션당 최대 fetch 크기
max.partition.fetch.bytes=1048576  # 1MB

# 한 번의 poll에서 반환할 최대 레코드 수
max.poll.records=500
```

**Fetch 동작 시각화:**

```
Consumer                         Broker
   │                               │
   │──── FetchRequest ────────────►│
   │     (min.bytes=1024)          │
   │                               │ 현재 데이터: 200 bytes
   │                               │ (1024 미만, 대기...)
   │                               │ 500ms 후 (max.wait.ms)
   │◄─── FetchResponse ────────────│
   │     (200 bytes 반환)          │
   │                               │
```

### Heartbeat와 세션 관리

```
Consumer                    Group Coordinator (Broker)
   │                               │
   │──── Heartbeat ───────────────►│ (주기적으로 "나 살아있어" 신호)
   │◄─── HeartbeatResponse ────────│
   │                               │
   │ [session.timeout.ms 동안 heartbeat 없으면]
   │                               │
   │                 (컨슈머 사망으로 판단)
   │                 (리밸런싱 시작!)
```

```properties
# 하트비트 전송 주기 (session.timeout.ms의 1/3 권장)
heartbeat.interval.ms=3000       # 3초

# 이 시간 동안 heartbeat 없으면 컨슈머 제거
session.timeout.ms=45000         # 45초

# poll() 호출 간격이 이 시간 초과하면 컨슈머 제거
max.poll.interval.ms=300000      # 5분 (무거운 처리 시 늘릴 것)
```

**session.timeout.ms vs max.poll.interval.ms:**

```
session.timeout.ms:
→ Heartbeat 스레드 기준
→ 컨슈머 프로세스 자체가 죽었을 때 감지

max.poll.interval.ms:
→ poll() 호출 기준
→ 컨슈머가 살아있지만 처리가 너무 느릴 때 감지
→ 예: DB 저장에 10분 걸리는 경우
```

---

## 리밸런싱 상세

리밸런싱은 **파티션 할당을 재조정**하는 과정이다. 컨슈머 그룹에 멤버 변화가 생길 때 발생한다.

### 리밸런싱 트리거 조건

1. 새 컨슈머가 그룹에 합류
2. 기존 컨슈머가 종료/장애
3. session.timeout.ms 초과
4. max.poll.interval.ms 초과
5. 토픽 파티션 수 변경
6. 컨슈머가 구독 토픽 변경

### Eager Rebalancing (기존 방식)

```
초기 상태:
Consumer 1: [P0, P1]
Consumer 2: [P2, P3]

리밸런싱 시작 (새 Consumer 3 합류):

Phase 1 - Stop the World:
┌─────────────────────────────────────┐
│ 모든 컨슈머: 파티션 해제             │
│ Consumer 1: [] (처리 중단)          │ ← 모두 멈춤!
│ Consumer 2: [] (처리 중단)          │
│ Consumer 3: [] (대기)               │
└─────────────────────────────────────┘

Phase 2 - Reassignment:
Consumer 1: [P0, P1] 재할당
Consumer 2: [P2]     재할당
Consumer 3: [P3]     신규 할당
```

**문제점:**
- 리밸런싱 동안 **전체 컨슈머 그룹이 처리를 멈춤** (Stop-The-World)
- 컨슈머 수 × 파티션 수가 많을수록 리밸런싱 시간 증가
- 실시간 처리 지연 발생

### Cooperative/Incremental Rebalancing (Kafka 2.4+)

```
초기 상태:
Consumer 1: [P0, P1]
Consumer 2: [P2, P3]

리밸런싱 시작 (새 Consumer 3 합류):

Round 1 - 이동할 파티션만 해제:
Consumer 1: [P0, P1] (유지, 계속 처리!)
Consumer 2: [P2]     (유지, 계속 처리!)
Consumer 2: [P3]     (P3만 해제)
Consumer 3: []       (대기)

Round 2 - 해제된 파티션만 재할당:
Consumer 1: [P0, P1] (변화 없음)
Consumer 2: [P2]     (변화 없음)
Consumer 3: [P3]     (신규 할당)
```

**차이점:**
- 이동이 필요한 파티션만 해제하고 재할당
- 나머지 파티션은 계속 처리 (처리 중단 최소화)
- 라운드가 여러 번 필요하지만 전체 처리 지연 훨씬 감소

```java
// Cooperative Rebalancing 활성화
props.put(ConsumerConfig.PARTITION_ASSIGNMENT_STRATEGY_CONFIG,
    CooperativeStickyAssignor.class.getName());
```

### Group Coordinator와 리밸런싱 프로토콜

```
1. JoinGroup Request:
   모든 컨슈머 → Group Coordinator

2. Group Leader 선정:
   첫 번째로 JoinGroup을 보낸 컨슈머 = Leader

3. SyncGroup Request:
   Leader: 파티션 할당 계획 수립 후 전송
   나머지: 빈 SyncGroup 전송

4. SyncGroup Response:
   Coordinator → 각 컨슈머에게 자신의 파티션 할당 결과 전송

5. 처리 재개
```

---

## 메시지 전달 보장

### At-Most-Once (최대 한 번)

```
Producer: acks=0
Consumer: 처리 전 offset 커밋

시나리오:
1. Consumer가 메시지 수신
2. Offset 커밋 (처리 완료로 기록)
3. 처리 중 Consumer 장애 ← 메시지 유실!
4. 재시작 시 커밋된 offset 이후부터 읽음
```

```java
// At-Most-Once 컨슈머 패턴
ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));
consumer.commitSync();  // 처리 전에 먼저 커밋!
for (ConsumerRecord<String, String> record : records) {
    process(record);   // 장애 시 유실
}
```

**사용 사례:** 로그 수집, 실시간 대시보드 (일부 데이터 손실 허용)

### At-Least-Once (최소 한 번)

```
Producer: acks=1 또는 all, retries > 0
Consumer: 처리 후 offset 커밋

시나리오:
1. Consumer가 메시지 수신 후 처리
2. Offset 커밋 전 Consumer 장애 ← 재시작 시 재처리!
3. 재시작 시 이전 offset부터 다시 읽음
4. 동일 메시지 중복 처리
```

```java
// At-Least-Once 컨슈머 패턴
ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));
for (ConsumerRecord<String, String> record : records) {
    process(record);   // 처리 후
}
consumer.commitSync();  // 커밋 (장애 시 재처리 발생)
```

**사용 사례:** 대부분의 경우, 멱등성 처리가 가능한 경우

### Exactly-Once (정확히 한 번)

```
Producer: idempotent + transactional
Consumer: read-process-write 트랜잭션

흐름:
Producer → Kafka (트랜잭션 begin)
         → Kafka 토픽에 쓰기
         → Consumer offset 커밋 (동일 트랜잭션)
         → Kafka (트랜잭션 commit)

실패 시: 트랜잭션 롤백 → 재시도
```

---

## 트랜잭션과 멱등성

### Idempotent Producer (멱등성 프로듀서)

동일 메시지를 여러 번 보내도 한 번만 저장되도록 보장한다.

```
문제 상황 (멱등성 없을 때):
Producer → msg(seq=1) → Broker (저장)
                      ← ACK
         ACK 손실!
Producer → msg(seq=1) 재전송 → Broker (중복 저장!) ← 문제!

해결 (멱등성 있을 때):
Producer (PID=100) → msg(seq=1) → Broker (저장, seq=1 기록)
                                ← ACK
                  ACK 손실!
Producer (PID=100) → msg(seq=1) 재전송 → Broker
                                       → "seq=1 이미 처리됨" → 중복 무시
                                ← ACK (정상 응답)
```

Broker는 각 프로듀서(PID)마다 최근 5개의 시퀀스 번호를 기억한다.

```java
// 멱등성 활성화 (Kafka 3.0+에서 기본값)
props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
// 자동으로 설정됨:
// acks=all
// retries=MAX_INT
// max.in.flight.requests.per.connection=5
```

**주의:** 멱등성은 **단일 파티션, 단일 세션** 내에서만 보장된다. 브로커 재시작 후 PID가 변경되면 보장 안 됨.

### Transactional Producer (트랜잭션)

여러 파티션에 걸친 원자적 쓰기를 보장한다.

```java
@Configuration
public class KafkaTransactionalConfig {

    @Bean
    public ProducerFactory<String, Object> transactionalProducerFactory() {
        Map<String, Object> config = new HashMap<>();
        config.put(ProducerConfig.TRANSACTIONAL_ID_CONFIG, "order-producer-1");
        // transactional.id 설정 시 idempotence 자동 활성화
        return new DefaultKafkaProducerFactory<>(config);
    }
}

@Service
public class OrderTransactionalService {

    private final KafkaTemplate<String, Object> kafkaTemplate;

    @Transactional
    public void processOrderWithTransaction(OrderEvent order) {
        kafkaTemplate.executeInTransaction(operations -> {
            // 원자적으로 두 토픽에 동시 발행
            operations.send("order-confirmed", order.getId(), order);
            operations.send("inventory-deduct", order.getProductId(), order);
            // 하나라도 실패하면 모두 롤백
            return null;
        });
    }
}
```

**트랜잭션 내부 동작:**

```
1. initTransactions():
   Producer → Transaction Coordinator(Broker)
   Coordinator: transactional.id에 PID + epoch 발급

2. beginTransaction():
   Producer 로컬 상태만 변경 (브로커 요청 없음)

3. send():
   Producer → 각 파티션 리더에 메시지 기록
   메시지는 uncommitted 상태로 저장

4. sendOffsetsToTransaction():
   Producer → Coordinator → Consumer Group Coordinator
   offset을 트랜잭션에 포함

5. commitTransaction():
   Producer → Coordinator
   Coordinator → 모든 관련 파티션에 COMMITTED 마커 전송
   컨슈머는 이제 메시지를 읽을 수 있음

실패 시:
   abortTransaction() → ABORTED 마커 전송
   컨슈머는 uncommitted 메시지 무시
```

### Exactly-Once Semantics (EOS) 전체 그림

```java
// Exactly-Once Consumer-Transform-Produce 패턴
@Service
public class ExactlyOnceProcessor {

    private final KafkaConsumer<String, InputEvent> consumer;
    private final KafkaProducer<String, OutputEvent> producer;

    public void process() {
        producer.initTransactions();
        consumer.subscribe(List.of("input-topic"));

        while (true) {
            ConsumerRecords<String, InputEvent> records =
                consumer.poll(Duration.ofMillis(100));

            if (records.isEmpty()) continue;

            producer.beginTransaction();
            try {
                // 1. 변환 처리
                for (ConsumerRecord<String, InputEvent> record : records) {
                    OutputEvent output = transform(record.value());
                    producer.send(new ProducerRecord<>("output-topic", output));
                }

                // 2. Consumer offset도 트랜잭션에 포함
                Map<TopicPartition, OffsetAndMetadata> offsets = new HashMap<>();
                for (TopicPartition partition : records.partitions()) {
                    long lastOffset = getLastOffset(records, partition);
                    offsets.put(partition, new OffsetAndMetadata(lastOffset + 1));
                }
                producer.sendOffsetsToTransaction(offsets, consumer.groupMetadata());

                // 3. 원자적 커밋 (출력 + 오프셋 동시)
                producer.commitTransaction();

            } catch (Exception e) {
                producer.abortTransaction();
                // 재처리를 위해 offset 리셋
                consumer.seekToBeginning(records.partitions());
            }
        }
    }
}
```

---

## 파티션 리더 선출

### 정상 상태

```
Partition 0:
┌──────────────────────────────────────────────────┐
│  Leader: Broker 1                                │
│  ISR: [Broker1, Broker2, Broker3]                │
│                                                  │
│  Broker1(Leader) ──복제──► Broker2(Follower)     │
│                  ──복제──► Broker3(Follower)     │
└──────────────────────────────────────────────────┘
```

### 리더 장애 시

```
Broker 1(Leader) 장애 발생!

1. Controller(또는 KRaft Active Controller) 감지
2. ISR 확인: [Broker2, Broker3] (Broker1 제외)
3. ISR 중 첫 번째 후보 선택 (Broker2)
4. Broker2를 새 Leader로 선출
5. 메타데이터 갱신 브로드캐스트

결과:
Partition 0:
┌──────────────────────────────────────────────────┐
│  Leader: Broker 2 (변경됨!)                      │
│  ISR: [Broker2, Broker3]                         │
└──────────────────────────────────────────────────┘
```

### 컨트롤러(Controller) 역할

ZooKeeper 모드에서는 클러스터 내 **하나의 브로커가 컨트롤러**로 선출된다.

```
컨트롤러 선출 (ZooKeeper 방식):
브로커들이 ZooKeeper의 /controller 노드 생성 시도
→ 먼저 생성한 브로커가 컨트롤러

컨트롤러 책임:
- 파티션 리더 선출
- ISR 변경 관리
- 브로커 등록/해제 감지
- 토픽/파티션 생성/삭제
```

```
컨트롤러 선출 (KRaft 방식):
Raft 합의 알고리즘으로 Active Controller 선출
→ 과반수(quorum) 투표로 결정
→ 안정적이고 빠른 failover
```

---

## 로그 컴팩션 동작 원리

로그 컴팩션은 동일 키의 오래된 메시지를 제거하고 **가장 최신 값만 유지**하는 메커니즘이다.

### 사용 사례

```
사용자 프로필 변경 이벤트:
t=1: key="user-1", value={"name":"김철수", "email":"a@a.com"}
t=2: key="user-1", value={"name":"김철수", "email":"b@b.com"}  ← 이메일 변경
t=3: key="user-2", value={"name":"이영희", "email":"c@c.com"}
t=4: key="user-1", value={"name":"김철수", "email":"c@c.com"}  ← 이메일 또 변경

컴팩션 후:
key="user-1" → {"name":"김철수", "email":"c@c.com"}  (최신값만)
key="user-2" → {"name":"이영희", "email":"c@c.com"}  (유일값)
```

### 컴팩션 동작 과정

```
파티션 로그:
┌──────────────────────────────────────────────────────────┐
│ Clean 영역          │ Dirty 영역 (컴팩션 대상)           │
│ (이미 컴팩션됨)     │                                    │
│ [k1:v1][k2:v2]     │ [k1:v3][k3:v1][k2:v4][k1:v5]      │
└──────────────────────────────────────────────────────────┘

Log Cleaner 스레드 동작:
1. Dirty 영역 스캔 → 각 키의 최신 offset 파악
   k1 → offset에서 최신: v5
   k3 → v1
   k2 → v4

2. 새 세그먼트 생성:
   [k1:v5][k3:v1][k2:v4]  (k1의 v3 제거)

3. 오래된 세그먼트 교체
```

```
컴팩션 전:
offset: 0     1     2     3     4     5     6
key:   [k1]  [k2]  [k1]  [k3]  [k2]  [k1]  [k3]
value: [v1]  [v1]  [v2]  [v1]  [v2]  [v3]  [v2]

컴팩션 후 (오래된 버전 제거):
offset: 2     4     5     6
key:   [k1]  [k2]  [k1]  [k3]    ← offset은 변하지 않음!
value: [v2]  [v2]  [v3]  [v2]
```

**주의:** 컴팩션 후에도 offset은 변하지 않는다. 일부 offset이 없는 sparse log가 된다.

### 삭제 마커 (Tombstone)

```java
// 키를 완전히 삭제하려면 null 값 전송
producer.send(new ProducerRecord<>("user-profile", "user-1", null));
// → tombstone 레코드 생성
// → 컴팩션 시 해당 키의 모든 레코드 삭제
```

```
Tombstone 처리:
[k1:v1] [k1:v2] [k1:null] ← tombstone
              ↓ 컴팩션
              (k1 관련 모든 레코드 삭제)
              (tombstone도 일정 시간 후 삭제)
```

### 컴팩션 설정

```properties
# 토픽 레벨 설정
log.cleanup.policy=compact          # delete | compact | compact,delete
log.min.cleanable.dirty.ratio=0.5  # dirty 비율 50% 초과 시 컴팩션
log.segment.delete.delay.ms=60000  # 컴팩션 후 이전 세그먼트 삭제 대기
delete.retention.ms=86400000       # tombstone 보관 기간 (1일)
```

---

## 정리

| 동작 | 핵심 메커니즘 |
|------|--------------|
| Producer 배치 | RecordAccumulator + linger.ms로 메시지 모아서 전송 |
| 파티셔닝 | 키 해시 또는 Sticky (키 없을 때) |
| Consumer poll | Pull 기반, heartbeat로 생존 확인 |
| 리밸런싱 | Eager(전체 중단) vs Cooperative(최소 중단) |
| At-Most-Once | 처리 전 커밋 → 손실 가능 |
| At-Least-Once | 처리 후 커밋 → 중복 가능 |
| Exactly-Once | 멱등성 + 트랜잭션 → 중복·손실 없음 |
| 멱등성 | PID + Seq번호로 브로커 측 중복 감지 |
| 트랜잭션 | 여러 파티션 원자적 쓰기, offset도 트랜잭션 포함 |
| 리더 선출 | ISR 중 첫 번째 후보 선출, Controller가 조율 |
| 로그 컴팩션 | 동일 키 최신값만 유지, offset은 불변 |
