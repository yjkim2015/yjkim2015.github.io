---
title: "Kafka 장애 시나리오 — 데이터 유실과 중복 처리"
categories:
- KAFKA
toc: true
toc_sticky: true
toc_label: 목차
---

## 들어가며

결제 완료 이벤트가 Kafka에 두 번 발행됐다. 컨슈머가 중복으로 처리해 고객에게 포인트가 두 배 적립됐다. 반대로 브로커 장애 순간에 발행된 메시지는 ACK 없이 사라졌고, 주문은 DB에만 남아 배달 시스템이 전혀 몰랐다. 이 두 시나리오는 Kafka를 쓰는 모든 팀이 반드시 이해하고 방어해야 할 극한 상황이다.

> **비유**: Kafka 장애는 우체국 화재와 같다. 편지가 불에 탔는지(유실), 복사본이 두 개 배달됐는지(중복), 어느 쪽이 더 나쁜지는 편지 내용(비즈니스 로직)에 달려 있다.

Kafka는 고가용성 분산 시스템이지만, 극한 상황에서는 예상치 못한 동작이 발생한다. 각 시나리오를 이해하고 방어 전략을 갖추는 것이 프로덕션 운영의 핵심이다.

---

## 시나리오 1: 브로커 장애 시 리더 선출과 데이터 유실

### 상황 설정

```mermaid
graph LR
    B1["Broker 1 (Leader)"] -->|복제| B2["Broker 2"]
    B1 -->|복제| B3["Broker 3"]
```

### 장애 발생과 데이터 유실 경로

```mermaid
graph LR
    P["Producer"] -->|"off99,100 전송"| B1["Broker1 Leader"]
    B1 -->|"ACK"| P
    B1 -->|"장애! 미복제"| B2["Broker2 off=98"]
    B2 -->|"99,100 유실"| LOST["영구 유실"]
```

### acks=all 설정 시 시나리오

```mermaid
graph LR
    P["Producer"] -->|"acks=all"| B1["Broker1 Leader"]
    B1 -->|"복제"| B2["Broker2"]
    B2 -->|"완료"| B1
    B1 -->|"ACK"| P
    B1 -->|"장애→B2 새리더"| SAFE["유실 없음"]
```

### Unclean Leader Election 위험

```mermaid
graph LR
    S["B1(ISR Leader,offs"]
    S --> U["unclean=true: B3를"]
    S --> C["unclean=false(권장):"]
```

### 방어 전략

```java
// Producer 설정
props.put(ProducerConfig.ACKS_CONFIG, "all");
props.put(ProducerConfig.RETRIES_CONFIG, Integer.MAX_VALUE);
props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);

// 브로커 설정 (server.properties)
// min.insync.replicas=2        ← 최소 2개 ISR 동기화 보장
// unclean.leader.election.enable=false  ← ISR 외 선출 금지
// default.replication.factor=3          ← 복제 3개
```

---

## 시나리오 2: Consumer 리밸런싱 중 중복 처리

### 리밸런싱 타이밍 문제

```mermaid
graph LR
    CA["Consumer A"]
    K["Kafka"]
    CB["Consumer C"]
    CA -->|"off50~52 poll"| K
    CA -->|"리밸런싱→off51 커밋"| K
    K -->|"P0 할당"| CB
    CB -->|"off52 중복처리!"| K
```

### 상세 타임라인

```mermaid
graph LR
    T0["t=0: A poll"]
    T1["t=1: off50 완료"]
    T2["t=2: off51 완료"]
    T3["t=3: off52 시작"]
    T5["t=5: 리밸런싱"]
    T6["t=6: C→P0 할당"]
    T7["t=7: off52 중복"]
    T0 --> T1 --> T2 --> T3 --> T5 --> T6 --> T7
```

### 해결 방법 1: ConsumerRebalanceListener 활용

```java
@Service
public class SafeConsumerService {

    private final KafkaConsumer<String, OrderEvent> consumer;
    private final Map<TopicPartition, OffsetAndMetadata> pendingOffsets
        = new ConcurrentHashMap<>();

    public void startConsuming() {
        consumer.subscribe(List.of("order-events"), new ConsumerRebalanceListener() {

            @Override
            public void onPartitionsRevoked(Collection<TopicPartition> partitions) {
                // 리밸런싱 전: 처리 완료된 offset 즉시 커밋
                log.info("파티션 반환 전 커밋: {}", pendingOffsets);
                consumer.commitSync(pendingOffsets);
                pendingOffsets.clear();
            }

            @Override
            public void onPartitionsAssigned(Collection<TopicPartition> partitions) {
                log.info("새 파티션 할당: {}", partitions);
            }
        });

        while (true) {
            ConsumerRecords<String, OrderEvent> records =
                consumer.poll(Duration.ofMillis(100));

            for (ConsumerRecord<String, OrderEvent> record : records) {
                processOrder(record.value());
                // 처리 완료 offset 누적
                pendingOffsets.put(
                    new TopicPartition(record.topic(), record.partition()),
                    new OffsetAndMetadata(record.offset() + 1)
                );
            }

            consumer.commitAsync(pendingOffsets, (offsets, ex) -> {
                if (ex != null) log.error("비동기 커밋 실패", ex);
            });
        }
    }
}
```

### 해결 방법 2: 멱등성 처리 (Idempotent Consumer)

```java
@Service
public class IdempotentOrderService {

    private final OrderRepository orderRepository;
    private final ProcessedEventRepository processedEventRepo;

    @KafkaListener(topics = "order-events")
    @Transactional
    public void handleOrder(ConsumerRecord<String, OrderEvent> record) {
        String eventId = record.value().getEventId();

        // 이미 처리된 이벤트인지 확인
        if (processedEventRepo.existsByEventId(eventId)) {
            log.info("중복 이벤트 무시: {}", eventId);
            return;
        }

        // 처리
        orderRepository.save(record.value().toOrder());

        // 처리 완료 기록 (같은 트랜잭션)
        processedEventRepo.save(new ProcessedEvent(eventId));
        // → 처리 + 완료기록이 원자적으로 수행됨
    }
}
```

### 해결 방법 3: Cooperative Rebalancing

```java
// 리밸런싱 중 처리 중단을 최소화
props.put(ConsumerConfig.PARTITION_ASSIGNMENT_STRATEGY_CONFIG,
    CooperativeStickyAssignor.class.getName());
// → 이동하지 않는 파티션은 계속 처리
// → 중복 처리 시간 창이 줄어듦
```

---

## 시나리오 3: 파티션 수 변경 시 키 기반 라우팅 깨짐

### 문제 원리

```mermaid
graph LR
    K1["변경 전: user-123 → h"] --> K2["변경 후: user-123 → h"]
    K2 --> NOTE["동일 키가 다른 파티션 → 순서"]
```

### 실제 영향

```mermaid
graph LR
    B1["생성(P1)"] --> B2["수정(P1)"] --> B3["취소(P1)"]
    B3 --> B4["Consumer: 순서 보장"]
    A2["수정(P3)"] --> A5["Consumer2: 순서 깨짐"]
```

### 방어 전략

```java
// 전략 1: 충분히 큰 파티션 수로 처음부터 설계
// (파티션 줄이기는 불가, 늘리기만 가능)
// 예상 최대 처리량 기준으로 여유 있게 설정

// 전략 2: 파티션 변경 시 마이그레이션 계획
// Phase 1: 새 토픽 생성 (더 많은 파티션)
// Phase 2: 프로듀서를 새 토픽으로 전환
// Phase 3: 구 토픽 메시지 모두 소비 후 구 컨슈머 종료
// Phase 4: 구 토픽 삭제

// 전략 3: 커스텀 파티셔너로 파티션 수 변경 대응
public class StableHashPartitioner implements Partitioner {
    @Override
    public int partition(String topic, Object key, byte[] keyBytes,
                         Object value, byte[] valueBytes, Cluster cluster) {
        // 고정 해시 함수 사용 (파티션 수 변경 전후 동일 매핑 유지)
        // 단, 새 파티션으로의 라우팅은 의도적으로 제어
        int fixedPartitionCount = 4; // 논리적 파티션 수 고정
        int physicalPartitions = cluster.partitionCountForTopic(topic);
        int logicalPartition = Math.abs(murmur2(keyBytes)) % fixedPartitionCount;
        return logicalPartition % physicalPartitions;
    }
}
```

```mermaid
graph LR
    RULE1["파티션 수는 처음부터 넉넉하게 설"]
    RULE2["불가피하게 변경 시:"]
    RULE1 --> RULE2
```

---

## 시나리오 4: 디스크 가득 참 시 동작

### 브로커 디스크 100% 상황

```mermaid
graph LR
    D["디스크 100%"] --> E1["쓰기 실패"]
    D --> E2["Producer Timeout"]
    D --> E3["ISR 축소"]
```

### 단계별 장애 확산

```mermaid
graph LR
    T0["t=0: 디스크 100% 도달"]
    T1["t=1: Partition 0 리"]
    T2["t=2: Producer 재시도"]
    T10["t=10: 재시도 소진 → Pro"]
    T15["t=15: Broker 2,3 팔"]
    T30["t=30: ISR = Broker"]
    T31["t=31: min.insync.r"]
    T0 --> T1 --> T2 --> T10 --> T15 --> T30 --> T31
```

### 방어 전략

```yaml
# 모니터링 알림 설정 (Prometheus + AlertManager)
groups:
  - name: kafka_disk
    rules:
      - alert: KafkaDiskUsageHigh
        expr: (node_filesystem_size_bytes - node_filesystem_free_bytes)
              / node_filesystem_size_bytes > 0.80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Kafka 브로커 디스크 80% 초과"

      - alert: KafkaDiskUsageCritical
        expr: (node_filesystem_size_bytes - node_filesystem_free_bytes)
              / node_filesystem_size_bytes > 0.90
        for: 1m
        labels:
          severity: critical
```

```properties
# 브로커 설정: 디스크 보호
log.retention.bytes=107374182400   # 파티션당 최대 100GB
log.retention.hours=72             # 3일 보관
log.segment.bytes=536870912        # 세그먼트 500MB (빠른 삭제 단위)

# 디스크 임계값 도달 시 자동 조치
# log.cleaner.enable=true          # 로그 컴팩션 활성화
```

```java
// 디스크 부족 시 자동 보존 기간 단축 (운영 자동화)
@Scheduled(fixedDelay = 60000)
public void adjustRetentionPolicy() {
    double diskUsage = getDiskUsagePercent();
    if (diskUsage > 0.85) {
        adminClient.alterConfigs(Map.of(
            new ConfigResource(ConfigResource.Type.TOPIC, "order-events"),
            new Config(List.of(
                new ConfigEntry("retention.ms", "86400000") // 1일로 단축
            ))
        ));
        log.warn("디스크 {}% → 보존 기간 1일로 단축", diskUsage * 100);
    }
}
```

---

## 시나리오 5: ISR 축소 → Unclean Leader Election

### ISR 점진적 축소 시나리오

```mermaid
graph LR
    S0["ISR=B1(Leader),B2,"] -->|"B3 lag 초과"| S1["ISR=B1,B2"]
    S1 -->|"B2 Full GC"| S2["ISR=B1만"]
    S2 -->|"B1 장애"| S4["ISR 비어있음"]
    S4 -->|"unclean=true"| UNCLEAN["B3 리더 선출"]
    S4 -->|"unclean=false"| CLEAN["파티션 불가용"]
```

### ISR 모니터링

```bash
# ISR 상태 확인
kafka-topics.sh --bootstrap-server kafka1:9092 \
  --describe --topic order-events

# 출력 예시:
Topic: order-events  Partition: 0  Leader: 1  Replicas: 1,2,3  Isr: 1,2
#                                                                       ↑
#                                                               Broker 3 빠짐!
```

```java
// ISR 축소 감지 및 알림
@Scheduled(fixedDelay = 30000)
public void checkISRHealth() {
    DescribeTopicsResult result = adminClient.describeTopics(
        List.of("order-events", "payment-events")
    );

    result.all().get().forEach((topic, desc) -> {
        desc.partitions().forEach(partition -> {
            int replicaCount = partition.replicas().size();
            int isrCount = partition.isr().size();

            if (isrCount < replicaCount) {
                alertService.sendAlert(String.format(
                    "ISR 축소! 토픽=%s 파티션=%d ISR=%d/%d",
                    topic, partition.partition(), isrCount, replicaCount
                ));
            }
        });
    });
}
```

### 방어 전략

```
ISR 축소 방지:
1. 브로커 JVM GC 튜닝 (G1GC 사용, pause time 최소화)
2. 네트워크 대역폭 충분히 확보
3. 브로커간 복제 전용 네트워크 분리
4. replica.lag.time.max.ms 현실적으로 설정

설정 조합:
unclean.leader.election.enable=false  ← 데이터 우선
min.insync.replicas=2                 ← 최소 2개 보장
default.replication.factor=3         ← 여유 복제본
```

---

## 시나리오 6: Consumer Lag 폭증 시 대응

### Lag 발생 원인과 탐지

```mermaid
graph LR
    LEO["Log End Offset"]
    CO["Committed Offset"]
    LAG["Lag=LEO-Offset"]
    CO -->|차이| LEO
    LEO --> LAG
    NOTE["Producer > Csmr"]
```

### Lag 폭증 원인별 분류

```mermaid
graph LR
    LAG["Lag 폭증 원인"] --> C1["Consumer 속도 저하"]
    LAG --> C2["Producer 유입 급증"]
    LAG --> C3["Consumer 감소"]
```

### Lag 모니터링 및 자동 스케일링

```java
// Lag 모니터링 서비스
@Service
public class KafkaLagMonitor {

    @Scheduled(fixedDelay = 10000)
    public void checkAndAlertLag() {
        Map<String, Map<TopicPartition, Long>> lagMap = calculateLag();

        lagMap.forEach((groupId, partitionLags) -> {
            long totalLag = partitionLags.values().stream()
                .mapToLong(Long::longValue).sum();

            // Prometheus 메트릭 노출
            meterRegistry.gauge("kafka.consumer.lag",
                Tags.of("group", groupId), totalLag);

            if (totalLag > 100_000) {
                log.warn("Consumer Group {} Lag 폭증: {}", groupId, totalLag);
                triggerAutoScaling(groupId, totalLag);
            }
        });
    }

    private Map<String, Map<TopicPartition, Long>> calculateLag() {
        // AdminClient로 Log End Offset 조회
        // ConsumerGroupDescription으로 Committed Offset 조회
        // 차이 계산
        ...
    }
}
```

```yaml
# Kubernetes HPA (Consumer Pod 자동 확장)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: order-consumer-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: order-consumer
  minReplicas: 2
  maxReplicas: 10  # 파티션 수 이상으로 늘려도 의미 없음
  metrics:
    - type: External
      external:
        metric:
          name: kafka_consumer_group_lag
          selector:
            matchLabels:
              group: order-processing-group
        target:
          type: AverageValue
          averageValue: "10000"  # 평균 lag이 10000 초과 시 스케일아웃
```

### 긴급 대응 절차

```mermaid
graph LR
    DETECT["Lag 폭증 감지"]
    S1["Step 1: 원인 파악 (5분"]
    S2["Step 2: 빠른 완화"]
    S3["Step 3: 근본 원인 해결"]
    S4["Step 4: Lag 해소 모니터"]
    DETECT --> S1 --> S2 --> S3 --> S4
```

---

## 시나리오 7: 네트워크 파티션 시나리오

### Split-Brain 상황

```mermaid
graph LR
    B1["Broker 1"]
    B2["Broker 2 (Zone B)"]
    B3["Broker 3 (Zone B)"]
    B1 ---|네트워크 단절| B2
    Note1["Zone B에서 새 리더 선출"]
```

### Zombie Leader 문제

```mermaid
graph LR
    PA["Producer A"] -->|"쓰기 시도"| B1["Broker1(zombie)"]
    B1 -->|"Split Brain"| B2["Broker2"]
    B1 -->|"복구 후 메시지 폐기"| B1
```

### Kafka의 방어 메커니즘

```mermaid
graph LR
    B1["Broker1 epoch5"]
    C["Controller"]
    P["Producer"]
    B2["Broker2 epoch6"]
    B1 -->|"리더 확인"| C
    C -->|"구 리더 거절"| B1
    B1 -->|"NotLeaderException"| P
    P -->|"새 리더 조회"| C
    C -->|"Broker2 epoch6"| B2
```

### 네트워크 파티션 시나리오별 영향

```mermaid
graph LR
    SA1["Prdcr → Leader 단절"]
    SA2["acks=1: 쓰기 가능"]
    SA3["acks=all: ISR 감소 거"]
    SA1 --> SA2
    SA1 --> SA3
```

### 방어 전략

```properties
# 다중 AZ 배포 시 권장 설정

# 복제 설정
default.replication.factor=3      # AZ당 하나씩
min.insync.replicas=2             # 과반수

# 타임아웃 설정 (네트워크 복구 시간 고려)
replica.lag.time.max.ms=30000    # 30초
zookeeper.session.timeout.ms=18000
```

```java
// 클라이언트 메타데이터 갱신 설정
props.put(ProducerConfig.METADATA_MAX_AGE_CONFIG, 300000);    // 5분
props.put(ProducerConfig.RECONNECT_BACKOFF_MS_CONFIG, 50);
props.put(ProducerConfig.RECONNECT_BACKOFF_MAX_MS_CONFIG, 1000);
```

---

## 시나리오 8: Producer 타임아웃 + 재시도 시 중복

### 중복 발생 메커니즘

```mermaid
graph LR
    P["Producer(멱등성없음)"]
    B["Broker"]
    ACK["ACK 손실"]
    DUP["msg_A 중복저장"]
    P -->|"msg_A 전송"| B
    B -->|"저장→ACK"| ACK
    ACK -->|"타임아웃→재전송"| P
    P -->|"msg_A 재전송"| DUP
```

### 타임아웃 관련 설정들

```java
props.put(ProducerConfig.REQUEST_TIMEOUT_MS_CONFIG, 30000);    // 요청 타임아웃 30초
props.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG, 120000);  // 전체 전달 타임아웃 2분
props.put(ProducerConfig.RETRIES_CONFIG, 3);                    // 재시도 3회
props.put(ProducerConfig.RETRY_BACKOFF_MS_CONFIG, 100);        // 재시도 간격 100ms

// 재시도로 인한 순서 역전 방지
props.put(ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION, 5);
// → 멱등성 활성화 시: 최대 5개 동시 요청 허용 (순서 보장됨)
// → 멱등성 비활성화 시: 1로 설정해야 순서 보장
```

### 순서 역전 시나리오

```mermaid
graph LR
    P1["IN_FLIGHT=5"]
    B1["msg2→msg1 역전"]
    P2["IN_FLIGHT=1"]
    B2["msg1→msg2 보장"]
    P1 -->|"msg1실패→msg2→재시도"| B1
    P2 -->|"msg1→msg2 순서대로"| B2
```

### 완전한 해결: Idempotent Producer

```java
// 멱등성 활성화 시
props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
// 자동으로:
// acks=all
// max.in.flight.requests.per.connection=5 (순서 보장하면서 성능도 유지)
// retries=Integer.MAX_VALUE

// 브로커는 PID + Sequence Number로 중복 감지:
// seq=1 저장 → seq=1 재수신 → "이미 처리됨" → 무시 (ACK 반환)
// seq=3 수신 후 seq=2 수신 → "seq 2 누락" → OutOfOrderSequenceException
```

### 재시도와 중복 처리 요약

```
상황별 권장 설정:

데이터 유실 절대 불허 (금융):
  acks=all
  enable.idempotence=true
  retries=MAX_INT
  transactional.id=unique-id  (EOS 필요 시)

고처리량 우선 (로그 수집):
  acks=1
  retries=3
  enable.idempotence=false
  compression.type=snappy

균형 (일반 서비스):
  acks=all
  enable.idempotence=true
  retries=10
  delivery.timeout.ms=120000
```

---


## 극한 시나리오

```
프로듀서 설정:
□ acks=all (데이터 무결성)
□ enable.idempotence=true (중복 방지)
□ retries=충분히 크게
□ delivery.timeout.ms > request.timeout.ms * retries

브로커 설정:
□ replication.factor >= 3
□ min.insync.replicas = replication.factor - 1
□ unclean.leader.election.enable=false
□ auto.leader.rebalance.enable=true
□ log.retention.bytes 설정 (디스크 보호)

컨슈머 설정:
□ enable.auto.commit=false (수동 커밋)
□ max.poll.interval.ms > 최대 처리 시간
□ CooperativeStickyAssignor 사용
□ ConsumerRebalanceListener 구현

토픽 설계:
□ 파티션 수를 처음부터 넉넉하게
□ 키 기반 순서 보장 요구사항 명확화
□ 컴팩션 vs 삭제 정책 결정

운영:
□ Consumer Lag 모니터링 및 알림
□ ISR 상태 모니터링
□ 디스크 사용량 80% 알림
□ 브로커 JVM 튜닝 (G1GC)
□ 네트워크 파티션 대비 다중 AZ 배포
```

---
## 시나리오별 빠른 참조

| 시나리오 | 핵심 위험 | 방어 방법 |
|----------|-----------|-----------|
| 브로커 장애 | 미복제 메시지 유실 | acks=all + min.insync.replicas=2 |
| 리밸런싱 중 중복 | offset 재처리 | ConsumerRebalanceListener + 멱등성 처리 |
| 파티션 수 변경 | 키 라우팅 깨짐 | 처음부터 충분한 파티션 수, 새 토픽 마이그레이션 |
| 디스크 풀 | 쓰기 완전 중단 | 80% 알림, 보존 기간 자동 조정 |
| ISR 축소 | Unclean 선출 위험 | unclean.leader.election=false, ISR 모니터링 |
| Consumer Lag 폭증 | 실시간성 파괴 | 자동 스케일링, Lag 알림 |
| 네트워크 파티션 | Split-Brain | Leader Epoch, 다중 AZ 배포 |
| 재시도 중복 | 메시지 중복 저장 | enable.idempotence=true |

---

## 왜 극한 시나리오를 알아야 하는가?

정상 동작만 아는 엔지니어는 장애 상황에서 대응이 느리다. "브로커 3대 중 2대가 동시에 죽으면?", "Consumer가 메시지를 처리하다 GC로 10분 멈추면?" 같은 극한 시나리오를 미리 생각해두면 설정값의 의미가 보이고 장애 복구 절차가 체계화된다.

---

## 실무에서 자주 하는 실수

**실수 1: 카오스 테스트 없이 운영 투입**
브로커 장애, 네트워크 파티션, Consumer 지연을 시뮬레이션하지 않은 채 운영한다. 첫 장애가 실제 운영에서 발생해 복구 절차를 그 자리에서 찾게 된다. Chaos Monkey, `tc` 명령으로 네트워크 지연을 주입해 주기적으로 장애 훈련을 수행해야 한다.

**실수 2: min.insync.replicas 설정을 replication.factor와 동일하게 설정**
`replication.factor=3`, `min.insync.replicas=3`이면 브로커 1대 장애 시 ISR이 2개로 줄어 모든 쓰기가 차단된다. `min.insync.replicas=2`(과반수)로 설정해야 브로커 1대 장애에서도 쓰기가 가능하다.

**실수 3: 메시지 크기 한계를 고려하지 않은 설계**
기본 `message.max.bytes=1MB`를 초과하는 페이로드를 전송하다 `RecordTooLargeException`이 발생한다. 브로커와 프로듀서·컨슈머 모두 일관되게 설정해야 하며, 대용량 바이너리는 S3에 저장하고 Kafka에는 참조 URL만 전송하는 패턴을 권장한다.

**실수 4: 오프셋 리셋 시 downstream 영향 미고려**
`--reset-offsets --to-earliest`로 오프셋을 재설정하면 모든 과거 메시지를 재처리한다. 멱등성이 없는 downstream(이메일 발송, 결제 처리)이면 중복 처리가 발생한다. 오프셋 리셋 전에 downstream의 멱등성 보장 여부를 반드시 확인해야 한다.

**실수 5: Consumer Group이 오랫동안 비활성 상태**
Consumer Group이 `offsets.retention.minutes`(기본 7일) 동안 비활성이면 오프셋 정보가 삭제된다. 재시작 시 `auto.offset.reset` 정책에 따라 earliest나 latest부터 처리해 예상치 못한 메시지 유실 또는 재처리가 발생한다.

---

## 면접 포인트

**Q1. 브로커 과반수 장애 시 Kafka의 동작은?**
`min.insync.replicas`를 충족하지 못하면 프로듀서의 쓰기가 `NotEnoughReplicasException`으로 실패한다. ISR이 없으면 해당 파티션이 unavailable 상태가 된다. `unclean.leader.election.enable=false`(기본)이면 ISR에 없는 레플리카가 리더가 되지 않아 데이터 유실을 방지하지만 서비스는 중단된다.

**Q2. Split-Brain 상황에서 Kafka는 어떻게 처리하는가?**
네트워크 파티션으로 브로커가 두 그룹으로 나뉘면 KRaft(또는 ZooKeeper)의 과반수를 확보한 쪽만 클러스터 운영을 계속한다. 소수 쪽 브로커는 컨트롤러를 잃고 쓰기를 거부한다. 각 AZ에 균등하게 브로커를 배치하고 홀수 개(최소 3개)를 유지해야 한다.

**Q3. Consumer Lag이 폭증하는 원인과 대응은?**
원인: ① 프로듀서 처리량 급증 ② Consumer 처리 지연(DB 슬로우쿼리, 외부 API 지연) ③ Consumer 수 < 파티션 수. 즉시 대응: Consumer 인스턴스 추가(파티션 수 한도), 처리 로직 최적화. 근본 대응: 파티션 수 증가(재할당 필요), 처리 병목 제거.

**Q4. Kafka의 메시지 순서 보장 범위는?**
파티션 내에서만 순서가 보장된다. 토픽 전체 순서는 보장되지 않는다. 순서가 중요한 이벤트(사용자 행동 순서)는 같은 키로 전송해 같은 파티션에 배치한다. 글로벌 순서가 필요하면 파티션을 1개로 설정하지만 처리량 확장이 불가능해진다.

**Q5. Kafka를 DB 대신 사용할 수 있는가?**
이벤트 로그로서의 Kafka는 immutable append-only 저장소다. 임의 조회(특정 키로 최신 값 조회)가 필요하면 Log Compaction + Kafka Streams의 KTable이나 별도 DB로 materialized view를 구성해야 한다. Kafka는 데이터 파이프라인과 이벤트 스트리밍에 최적화되어 있고 일반 DB를 대체하지 않는다.
