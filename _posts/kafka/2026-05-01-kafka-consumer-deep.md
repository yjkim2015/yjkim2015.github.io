---
title: "Kafka Consumer"
categories:
- KAFKA
toc: true
toc_sticky: true
toc_label: 목차
---

## Consumer Group

### Consumer Group이란?

여러 Consumer 인스턴스가 하나의 그룹으로 협력하여 토픽을 병렬 소비하는 단위다. 같은 그룹 내 Consumer들은 파티션을 나눠 가진다.

```
Topic: orders (파티션 3개)
┌────────────────────────────────────────────────┐
│          Consumer Group: order-processor        │
│                                                 │
│  Consumer A         Consumer B         Consumer C│
│  (P0 담당)          (P1 담당)          (P2 담당) │
└────────────────────────────────────────────────┘

같은 토픽을 다른 그룹이 독립적으로 소비 가능:
┌────────────────────────────────────────────────┐
│          Consumer Group: analytics              │
│                                                 │
│  Consumer D              Consumer E             │
│  (P0, P1 담당)           (P2 담당)              │
└────────────────────────────────────────────────┘
```

### Consumer Group 핵심 원칙

1. 한 파티션은 그룹 내 한 Consumer에만 할당된다
2. Consumer 수 > 파티션 수이면 일부 Consumer는 유휴 상태
3. Consumer 수 < 파티션 수이면 한 Consumer가 여러 파티션 담당
4. 다른 그룹 간에는 파티션을 공유하지 않고 독립 소비

```
파티션 3개, Consumer 5개인 경우:
Consumer A → P0
Consumer B → P1
Consumer C → P2
Consumer D → 유휴 (Idle)
Consumer E → 유휴 (Idle)

파티션 3개, Consumer 2개인 경우:
Consumer A → P0, P1
Consumer B → P2
```

---

## 파티션 할당 전략

### RangeAssignor (기본값)

토픽별로 파티션을 범위 단위로 할당한다.

```
토픽 A (파티션 6개), 토픽 B (파티션 6개), Consumer 3개

토픽 A: P0,P1 → C1 / P2,P3 → C2 / P4,P5 → C3
토픽 B: P0,P1 → C1 / P2,P3 → C2 / P4,P5 → C3

결과: C1이 A-P0, A-P1, B-P0, B-P1 담당 (4개)
     → 파티션 수가 Consumer 수로 나눠지지 않으면 특정 Consumer에 집중
```

### RoundRobinAssignor

모든 토픽의 파티션을 Consumer에게 순차적으로 배분한다.

```
토픽 A (P0~P2), 토픽 B (P0~P2), Consumer 3개

순서: A-P0, A-P1, A-P2, B-P0, B-P1, B-P2

C1: A-P0, B-P0
C2: A-P1, B-P1
C3: A-P2, B-P2

→ 균등한 분배, 여러 토픽 구독 시 유리
```

### StickyAssignor

리밸런싱 후에도 기존 할당을 최대한 유지하여 이동을 최소화한다.

```
리밸런싱 전: C1→{P0,P3}, C2→{P1,P4}, C3→{P2,P5}
C3 종료 후 리밸런싱:

RoundRobin: 전체 재배분 → C1,C2 할당이 바뀔 수 있음
Sticky:     C1→{P0,P3,P2} (기존 유지+P2 추가)
            C2→{P1,P4,P5} (기존 유지+P5 추가)
→ 캐시 재활용, 처리 중인 메시지 중단 최소화
```

### CooperativeStickyAssignor

Sticky와 같은 목표지만 Cooperative 방식으로 리밸런싱한다. 전체 Consumer를 멈추지 않고 영향받는 파티션만 재할당한다.

```java
// Consumer 설정
props.put(ConsumerConfig.PARTITION_ASSIGNMENT_STRATEGY_CONFIG,
    CooperativeStickyAssignor.class.getName());
```

---

## 리밸런싱

### Eager Rebalancing (기존 방식)

```
트리거: Consumer 추가/제거, 파티션 수 변경, 구독 토픽 변경

1. Group Coordinator가 리밸런싱 시작 알림
2. 모든 Consumer가 현재 파티션 반납 (Stop-the-World)
3. 모든 Consumer가 JoinGroup 요청 전송
4. Group Leader가 새 할당 계산
5. SyncGroup으로 새 할당 배포
6. 모든 Consumer가 새 파티션으로 작업 재시작

문제: 리밸런싱 동안 전체 그룹이 소비 중단
     대규모 그룹에서 수십 초 지연 가능
```

### Cooperative (Incremental) Rebalancing

```
1. 리밸런싱 시작 → Consumer들이 자신의 현재 할당 정보와 함께 JoinGroup
2. Group Leader가 필요한 변경사항만 계산
3. 반납이 필요한 파티션을 가진 Consumer만 해당 파티션 반납
4. 다시 JoinGroup → 새 파티션 할당
5. 나머지 Consumer들은 계속 소비

장점: 영향받지 않는 파티션은 소비 중단 없음
     대규모 그룹에서 리밸런싱 시간 대폭 감소
```

### 리밸런싱 최소화 설정

```properties
# heartbeat 관련 (session timeout 내에 heartbeat 전송)
session.timeout.ms=45000        # Consumer 장애 감지 시간 (기본 45초)
heartbeat.interval.ms=3000      # heartbeat 전송 주기 (session의 1/3 권장)

# poll 관련
max.poll.interval.ms=300000     # poll() 호출 간격 최대 허용 시간 (기본 5분)
                                # 처리 시간이 이를 초과하면 Consumer 장애로 판단
max.poll.records=500            # poll() 1회 반환 레코드 최대 수

# static group membership (리밸런싱 회피)
group.instance.id=consumer-1    # Consumer에 고정 ID 부여
                                # 재시작 시 리밸런싱 없이 기존 파티션 재할당
```

### Static Group Membership

```java
// Spring Kafka 설정
@Bean
public ConsumerFactory<String, String> consumerFactory() {
    Map<String, Object> props = new HashMap<>();
    props.put(ConsumerConfig.GROUP_ID_CONFIG, "order-processor");
    props.put(ConsumerConfig.GROUP_INSTANCE_ID_CONFIG, "consumer-pod-1"); // Pod 이름 등 고정값
    // ...
    return new DefaultKafkaConsumerFactory<>(props);
}
```

```
Static membership 효과:
Consumer 재시작 시 session.timeout.ms 안에 복귀하면
  → 리밸런싱 없이 기존 파티션 그대로 재할당
  → 롤링 배포 시 불필요한 리밸런싱 방지
```

---

## Offset 관리

### Offset 저장 위치

Kafka 0.9 이후 Consumer Offset은 `__consumer_offsets` 내부 토픽에 저장된다.

```
__consumer_offsets 토픽:
  Key: (group.id, topic, partition)
  Value: committed offset + metadata

예: ("order-processor", "orders", 0) → offset: 1500
```

### Auto Commit vs Manual Commit

**Auto Commit (enable.auto.commit=true)**

```java
props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, true);
props.put(ConsumerConfig.AUTO_COMMIT_INTERVAL_MS_CONFIG, 5000); // 5초마다 자동 커밋

// 문제: poll() 후 처리 중 Consumer 장애 시
//   → 처리 중인 메시지는 커밋 안 됨 → 재시작 시 재처리
//   → at-least-once 보장은 되지만 중복 처리 가능
```

**Manual Commit (Sync)**

```java
@KafkaListener(topics = "orders")
public void processOrder(ConsumerRecord<String, String> record,
                         Acknowledgment ack) {
    try {
        orderService.process(record.value());
        ack.acknowledge(); // 처리 완료 후 명시적 커밋
    } catch (Exception e) {
        // 커밋 안 함 → 재시작 시 재처리
        log.error("처리 실패", e);
        throw e;
    }
}

// ContainerFactory 설정
@Bean
public ConcurrentKafkaListenerContainerFactory<String, String> kafkaListenerContainerFactory() {
    ConcurrentKafkaListenerContainerFactory<String, String> factory =
        new ConcurrentKafkaListenerContainerFactory<>();
    factory.setAckMode(ContainerProperties.AckMode.MANUAL_IMMEDIATE);
    return factory;
}
```

**Manual Commit (Async)**

```java
consumer.commitAsync((offsets, exception) -> {
    if (exception != null) {
        log.error("Async commit failed for offsets {}", offsets, exception);
    }
});
// 장점: 처리량 높음 (블로킹 없음)
// 단점: 실패 시 재시도 순서 보장 어려움
```

### Offset 재설정

```bash
# 토픽의 처음부터 재처리
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group order-processor \
  --topic orders \
  --reset-offsets \
  --to-earliest \
  --execute

# 특정 offset으로 이동
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group order-processor \
  --topic orders \
  --reset-offsets \
  --to-offset 1000 \
  --execute

# 특정 시각 이후 메시지부터 재처리
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group order-processor \
  --topic orders \
  --reset-offsets \
  --to-datetime 2026-05-01T00:00:00.000 \
  --execute
```

---

## Consumer Lag

### Consumer Lag이란?

Producer가 쓴 최신 오프셋(Log End Offset)과 Consumer가 처리한 오프셋(Committed Offset)의 차이다.

```
Log End Offset (LEO): 10000
Committed Offset:     9500
Consumer Lag:         500
```

### Consumer Lag 원인

| 원인 | 설명 | 조치 |
|------|------|------|
| **처리 속도 부족** | 메시지 증가 속도 > Consumer 처리 속도 | Consumer 증설, 로직 최적화 |
| **처리 로직 느림** | DB 쿼리, 외부 API 호출 등 병목 | 배치 처리, 캐싱, 비동기 처리 |
| **GC 일시 정지** | JVM GC로 인한 처리 중단 | GC 튜닝, 힙 조정 |
| **리밸런싱 빈발** | 잦은 Consumer 추가/제거 | Static membership, 리밸런싱 설정 조정 |
| **네트워크 지연** | Consumer-Broker 간 네트워크 문제 | 네트워크 점검, 브로커 근접 배포 |

### Lag 모니터링

```bash
# CLI로 Consumer Lag 확인
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group order-processor \
  --describe

# 출력:
# GROUP           TOPIC  PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
# order-processor orders 0          9500            10000           500
# order-processor orders 1          8000            8000            0
# order-processor orders 2          7500            7500            0
```

**Burrow** (LinkedIn이 만든 Kafka Consumer Lag 모니터링 도구)

```yaml
# burrow 설정 예시
kafka:
  local:
    class-name: kafka
    brokers:
      - kafka1:9092
      - kafka2:9092
consumer:
  local:
    class-name: kafka
    cluster: local
    group-blacklist: "^(console-consumer-|python-kafka-consumer-|quick-).*$"
```

**Prometheus + Kafka Exporter**

```
kafka_consumergroup_lag{
  consumergroup="order-processor",
  topic="orders",
  partition="0"
} 500
```

---

## Consumer 증설 시 주의사항

### 파티션 수 확인 먼저

```
토픽 파티션 수: 3
현재 Consumer: 3개

Consumer 추가해도 파티션은 3개뿐
→ 추가 Consumer는 유휴 상태

해결: 파티션 수 먼저 늘리고 Consumer 증설
     (파티션 감소는 불가, 증가만 가능)
```

### 파티션 증가 시 키 기반 순서 보장 깨짐

```bash
kafka-topics.sh --bootstrap-server kafka:9092 \
  --alter --topic orders \
  --partitions 6
```

```
주의: 키 기반 파티셔닝을 사용 중이라면
      파티션 증가 후 같은 키가 다른 파티션으로 갈 수 있음
      순서 보장이 필요한 경우 파티션 증가 시점 신중히 결정
```

### 증설 시 리밸런싱 영향

```
Consumer 3→4로 증가:
  리밸런싱 발생 (Eager: 전체 소비 일시 중단)
  CooperativeStickyAssignor 사용 시 영향 최소화

권장:
  1. CooperativeStickyAssignor 사용
  2. Static Group Membership으로 빠른 재참여 보장
  3. 트래픽 적은 시간대에 증설
```

---

## 장애 시나리오

### 시나리오 1: Consumer 처리 중 장애

```
상황: Consumer가 메시지 처리 중 크래시
      자동 커밋 활성화, 커밋 전 장애 발생

결과: 재시작 후 마지막 커밋 오프셋부터 재처리
      → 중복 처리 가능 (at-least-once)

방어:
  1. 멱등성 있는 소비자 로직 작성
  2. 처리 완료 후 수동 커밋 (MANUAL_IMMEDIATE)
  3. Transactional Outbox로 정확히-한번(exactly-once) 구현
```

### 시나리오 2: 독성 메시지 (Poison Pill)

```
상황: 특정 메시지를 처리할 때마다 예외 발생
      재시도를 반복하며 Consumer Lag 누적

해결:
  1. 재시도 횟수 제한
  2. Dead Letter Topic(DLT)으로 전송
  3. 오류 메시지 스킵 후 모니터링
```

```java
@Bean
public DefaultErrorHandler errorHandler(KafkaTemplate<String, String> template) {
    // DLT로 전송
    DeadLetterPublishingRecoverer recoverer =
        new DeadLetterPublishingRecoverer(template,
            (r, e) -> new TopicPartition(r.topic() + ".DLT", r.partition()));

    // 3번 재시도 후 DLT로
    FixedBackOff backOff = new FixedBackOff(1000L, 3L);

    return new DefaultErrorHandler(recoverer, backOff);
}
```

### 시나리오 3: Consumer Group Lag 급증

```
원인 파악 순서:
1. Consumer 인스턴스 수 확인 (그룹에서 이탈한 Consumer 있는지)
2. 처리 로직 응답 시간 확인 (외부 시스템 지연)
3. GC 로그 확인 (Full GC 빈발)
4. 리밸런싱 로그 확인 (리밸런싱 과도 발생)
5. 브로커 메트릭 확인 (I/O, 네트워크)

즉각 조치:
- 파티션 수 늘리고 Consumer 증설
- 처리 로직 비동기화 (비즈니스 로직을 별도 스레드풀)
- 배치 처리 활성화 (max.poll.records 증가)
```

---

## 모니터링 핵심 지표

```
Consumer 헬스:
  kafka_consumer_fetch_rate                    # fetch 요청 속도
  kafka_consumer_records_consumed_rate         # 초당 소비 메시지 수
  kafka_consumer_records_lag_max               # 최대 Consumer Lag

리밸런싱:
  kafka_consumer_rebalance_rate_per_second     # 리밸런싱 빈도
  kafka_consumer_last_rebalance_seconds_ago    # 마지막 리밸런싱 시간

처리 성능:
  kafka_consumer_commit_rate                   # 오프셋 커밋 속도
  kafka_consumer_fetch_throttle_time_avg       # fetch 쓰로틀링 시간
```

```yaml
# Grafana 대시보드용 주요 패널
- Consumer Lag per Partition (그룹별, 파티션별 Lag)
- Consumer Instance Count per Group
- Rebalancing Events Timeline
- Records Consumed Rate vs Records Produced Rate
```
