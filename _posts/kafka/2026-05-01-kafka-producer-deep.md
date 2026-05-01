---
title: "Kafka Producer"
categories:
- KAFKA
toc: true
toc_sticky: true
toc_label: 목차
---

## Producer 내부 아키텍처

### 전체 흐름

```
Application
    │
    │ producer.send(record)
    ▼
┌─────────────────────────────────────────────────────┐
│                  KafkaProducer                       │
│                                                      │
│  Serializer → Partitioner → RecordAccumulator        │
│                                    │                 │
│                              배치 누적                │
│                                    │                 │
│                             Sender Thread            │
│                             (I/O 전담)               │
└─────────────────────────────────────────────────────┘
                                    │
                             NetworkClient
                                    │
                             Kafka Broker
```

### RecordAccumulator

Producer 스레드와 Sender 스레드 사이의 버퍼 역할을 한다. 각 TopicPartition마다 `Deque<ProducerBatch>`를 유지하여 메시지를 배치로 묶는다.

```
RecordAccumulator 내부:
┌─────────────────────────────────────────────┐
│                                             │
│  orders-P0: [batch1: msg0,msg1,msg2] [batch2: msg3] │
│  orders-P1: [batch1: msg4,msg5]             │
│  payments-P0: [batch1: msg6]                │
│                                             │
└─────────────────────────────────────────────┘
         ↑ Producer 스레드가 추가
         ↓ Sender 스레드가 가져가서 전송
```

**주요 설정:**

```properties
buffer.memory=33554432      # 전체 버퍼 메모리 (기본 32MB)
batch.size=16384            # 배치 최대 크기 (기본 16KB)
linger.ms=0                 # 배치 대기 시간 (기본 0ms, 즉시 전송)
max.block.ms=60000          # 버퍼 꽉 찼을 때 block 최대 시간
```

### Sender 스레드

RecordAccumulator에서 배치를 가져와 Kafka Broker로 전송하는 백그라운드 I/O 스레드다.

```
Sender 동작 사이클:
1. RecordAccumulator에서 전송 가능한 배치 수집
2. Metadata에서 각 파티션의 Leader 브로커 확인
3. 브로커별로 요청 묶기 (같은 브로커로 가는 배치 합산)
4. NetworkClient로 비동기 전송
5. 응답 수신 후 Future 완료 처리

in-flight 요청 수 제한:
max.in.flight.requests.per.connection=5  # 브로커당 동시 미확인 요청 수
```

---

## 배치와 압축

### 배치 전략

```
linger.ms=0 (기본):
  메시지 도착 즉시 전송 → 지연 최소, 처리량 낮음
  단일 메시지가 하나의 네트워크 요청 = 오버헤드 큼

linger.ms=10:
  10ms 대기 후 배치로 전송 → 지연 소폭 증가, 처리량 크게 향상
  같은 시간 내 도착한 메시지들이 하나의 배치

batch.size=65536 (64KB):
  배치가 64KB 차면 즉시 전송 (linger.ms 기다리지 않음)
```

```
처리량 최적화 설정:
linger.ms=20
batch.size=131072       # 128KB
compression.type=snappy
buffer.memory=67108864  # 64MB
```

### 압축

Producer에서 압축하면 네트워크 전송량과 브로커 저장 공간을 줄일 수 있다. Broker는 압축 해제 없이 그대로 저장하고 Consumer가 해제한다.

| 압축 알고리즘 | 압축률 | 속도 | CPU 사용 | 권장 상황 |
|--------------|--------|------|---------|-----------|
| none | 없음 | - | 없음 | 기본, 소량 데이터 |
| gzip | 높음 | 느림 | 높음 | 디스크 공간 최우선 |
| snappy | 중간 | 빠름 | 낮음 | 범용 (Google 권장) |
| lz4 | 중간 | 매우 빠름 | 낮음 | 처리량 최우선 |
| zstd | 높음 | 빠름 | 중간 | 고압축률+고성능 |

```properties
compression.type=snappy   # Producer 설정
```

---

## 파티셔닝

### 기본 파티셔닝 로직

```java
// Kafka 2.4+ 기본 파티셔너: StickyPartitioner
// 키가 없는 메시지: 배치가 찰 때까지 같은 파티션에 Sticky
// 키가 있는 메시지: murmur2 해시 기반으로 파티션 결정

// 키 기반 파티셔닝 (순서 보장):
ProducerRecord<String, String> record =
    new ProducerRecord<>("orders", orderId, orderJson);
// orderId가 같으면 항상 같은 파티션 → 순서 보장
```

### 커스텀 파티셔너

```java
public class OrderPriorityPartitioner implements Partitioner {

    @Override
    public int partition(String topic, Object key, byte[] keyBytes,
                         Object value, byte[] valueBytes, Cluster cluster) {
        int numPartitions = cluster.partitionCountForTopic(topic);

        // VIP 주문은 파티션 0으로 고정 (별도 Consumer가 전담 처리)
        if (value instanceof String && ((String) value).contains("\"vip\":true")) {
            return 0;
        }

        // 일반 주문은 나머지 파티션에 분산
        return (Utils.murmur2(keyBytes) & Integer.MAX_VALUE) % (numPartitions - 1) + 1;
    }

    @Override
    public void close() {}

    @Override
    public void configure(Map<String, ?> configs) {}
}

// 설정
props.put(ProducerConfig.PARTITIONER_CLASS_CONFIG,
    OrderPriorityPartitioner.class.getName());
```

---

## 멱등성 Producer

### 재시도로 인한 중복 문제

```
일반 Producer 재시도 시나리오:
1. Producer → Broker: msg1 전송
2. Broker: msg1 저장 성공
3. 네트워크 장애로 ack 미전달
4. Producer: timeout → 재시도
5. Producer → Broker: msg1 재전송
6. Broker: msg1 중복 저장
→ 메시지 중복!
```

### 멱등성 Producer 동작

```properties
enable.idempotence=true
# 자동으로 설정됨:
# acks=all
# max.in.flight.requests.per.connection=5 이하
# retries=Integer.MAX_VALUE
```

```
멱등성 메커니즘:
1. Producer 시작 시 PID (Producer ID) 발급받음
2. 각 메시지에 (PID, Sequence Number) 부여
3. Broker는 파티션별로 마지막 Sequence Number 추적
4. 중복 시퀀스가 오면 저장하지 않고 ack만 반환

Producer: (PID=42, Seq=5, msg1) 전송
Broker: 저장, 마지막 seq=5 기록
네트워크 장애 후 재시도: (PID=42, Seq=5, msg1) 재전송
Broker: seq=5 이미 처리됨 → 중복 무시, ack 반환
→ 중복 없이 exactly-once (파티션 내)
```

```
한계:
- 단일 파티션 내에서만 exactly-once 보장
- Producer 재시작 시 PID가 바뀌어 보장 범위 초기화
- 크로스 파티션 또는 크로스 토픽 exactly-once는 트랜잭션 필요
```

---

## 트랜잭션 Producer

### 트랜잭션이란?

여러 파티션 또는 여러 토픽에 걸쳐 원자적 쓰기를 보장한다. 모두 성공하거나 모두 실패한다.

```java
// 트랜잭션 설정
props.put(ProducerConfig.TRANSACTIONAL_ID_CONFIG, "order-service-producer-1");
props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);

KafkaProducer<String, String> producer = new KafkaProducer<>(props);
producer.initTransactions(); // 트랜잭션 초기화

// 트랜잭션 사용
producer.beginTransaction();
try {
    producer.send(new ProducerRecord<>("orders", orderId, orderJson));
    producer.send(new ProducerRecord<>("inventory-reservations", orderId, reservationJson));
    producer.send(new ProducerRecord<>("notifications", orderId, notificationJson));

    producer.commitTransaction(); // 3개 토픽 모두 원자적 커밋
} catch (Exception e) {
    producer.abortTransaction(); // 3개 토픽 모두 롤백
    throw e;
}
```

### Consumer-Producer 트랜잭션 (Read-Process-Write)

```java
// Kafka Streams가 내부적으로 사용하는 패턴
// Consumer에서 읽고, 처리하고, Producer로 쓰는 과정을 원자적으로

producer.beginTransaction();
try {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));

    for (ConsumerRecord<String, String> record : records) {
        String result = processRecord(record);
        producer.send(new ProducerRecord<>("output-topic", record.key(), result));
    }

    // Consumer Offset 커밋을 트랜잭션에 포함
    Map<TopicPartition, OffsetAndMetadata> offsets = getOffsets(records);
    producer.sendOffsetsToTransaction(offsets, consumer.groupMetadata());

    producer.commitTransaction();
} catch (Exception e) {
    producer.abortTransaction();
}
```

### Isolation Level

트랜잭션 메시지를 Consumer에서 읽는 방법은 `isolation.level` 설정으로 제어한다.

```properties
# Consumer 설정
isolation.level=read_committed   # 커밋된 트랜잭션 메시지만 읽음 (기본: read_uncommitted)
```

```
read_uncommitted (기본):
  진행 중인 트랜잭션 메시지도 즉시 읽음
  → 나중에 abort되면 이미 처리한 메시지가 유효하지 않을 수 있음

read_committed:
  commitTransaction() 완료된 메시지만 읽음
  → Last Stable Offset(LSO) 이하의 메시지만 노출
  → 처리량 소폭 감소, 정확한 exactly-once 보장
```

---

## Producer 행(Hang) 원인과 대응

### 원인 1: 버퍼 꽉 참

```
증상: producer.send()가 max.block.ms 동안 블로킹 후 BufferExhaustedException

원인:
  - Sender 스레드가 브로커에 전송하는 속도 < 메시지 생성 속도
  - 브로커 장애로 전송 불가 → 버퍼 지속 누적

해결:
  buffer.memory 증가 (기본 32MB → 64MB+)
  linger.ms 줄여 더 자주 전송
  브로커 장애 확인
  max.block.ms를 줄여 빠른 실패(fail-fast) 처리
```

### 원인 2: Metadata 조회 실패

```
증상: Producer 시작 시 또는 리더 변경 후 메시지 전송 지연/실패

원인:
  - 브로커 연결 불가 → Metadata 조회 실패
  - Leader 선출 중인 파티션에 쓰기 시도

설정:
  metadata.max.age.ms=300000      # Metadata 캐시 갱신 주기
  max.block.ms=60000              # Metadata 조회 대기 최대 시간
  request.timeout.ms=30000        # 요청 타임아웃
  reconnect.backoff.ms=50         # 재연결 시도 간격
  reconnect.backoff.max.ms=1000   # 재연결 최대 대기
```

### 원인 3: in-flight 요청 과다

```
증상: 처리량은 높은데 지연 증가

원인: 브로커가 요청 처리보다 느리게 응답
     → in-flight 요청 누적 → 버퍼 소진

해결:
  max.in.flight.requests.per.connection=1~5 (멱등성 활성화 시 5 이하 필수)
  acks=1로 변경 (내구성 트레이드오프)
```

---

## 재시도 중복 방지

### 재시도 설정

```properties
retries=2147483647                  # 사실상 무한 재시도
retry.backoff.ms=100                # 재시도 간격 (기본 100ms)
delivery.timeout.ms=120000          # 전체 전송 타임아웃 (기본 2분)
                                    # retries를 넘더라도 이 시간 내에만 재시도
```

### 재시도 중복 방지 전략

```
전략 1: 멱등성 Producer (단순, 단일 파티션)
  enable.idempotence=true
  → Broker가 시퀀스 번호로 중복 감지

전략 2: 트랜잭션 Producer (크로스 파티션/토픽)
  transactional.id=unique-id
  → 트랜잭션 단위로 원자적 처리

전략 3: 애플리케이션 레벨 멱등 키
  메시지에 고유 ID 포함 → Consumer가 중복 체크
  → Kafka 설정 무관하게 항상 사용 가능

전략 4: Outbox 패턴
  DB 트랜잭션으로 발행 보장 → Relay가 중복 없이 전송
```

### 멱등성 + 트랜잭션 조합

```java
@Configuration
public class KafkaProducerConfig {

    @Bean
    public ProducerFactory<String, String> producerFactory() {
        Map<String, Object> props = new HashMap<>();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "kafka:9092");
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class);

        // 멱등성
        props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);

        // 트랜잭션 (서비스 인스턴스별 고유 ID)
        String hostname = System.getenv("HOSTNAME");
        props.put(ProducerConfig.TRANSACTIONAL_ID_CONFIG, "order-svc-" + hostname);

        // 내구성
        props.put(ProducerConfig.ACKS_CONFIG, "all");
        props.put(ProducerConfig.RETRIES_CONFIG, Integer.MAX_VALUE);
        props.put(ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION, 5);

        // 배치 성능
        props.put(ProducerConfig.LINGER_MS_CONFIG, 5);
        props.put(ProducerConfig.BATCH_SIZE_CONFIG, 65536);
        props.put(ProducerConfig.COMPRESSION_TYPE_CONFIG, "snappy");

        return new DefaultKafkaProducerFactory<>(props);
    }
}
```

---

## 성능 튜닝 요약

| 목표 | 설정 | 값 |
|------|------|-----|
| 처리량 최대화 | `linger.ms` | 20~50 |
| 처리량 최대화 | `batch.size` | 65536~131072 |
| 처리량 최대화 | `compression.type` | snappy / lz4 |
| 처리량 최대화 | `buffer.memory` | 64MB+ |
| 지연 최소화 | `linger.ms` | 0~5 |
| 지연 최소화 | `batch.size` | 작게 |
| 내구성 최대화 | `acks` | all |
| 내구성 최대화 | `enable.idempotence` | true |
| 내구성 최대화 | `min.insync.replicas` | 2 |

```
처리량 vs 지연 트레이드오프:
linger.ms=0:  지연 낮음, 처리량 낮음
linger.ms=50: 지연 높음, 처리량 높음

실무 권장:
  - 실시간 처리 필요: linger.ms=0~5
  - 대량 데이터 파이프라인: linger.ms=20~100
```
