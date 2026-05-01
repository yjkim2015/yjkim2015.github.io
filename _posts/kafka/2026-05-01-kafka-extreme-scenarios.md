---
title: "Kafka 극한 시나리오 — 장애, 중복, 데이터 유실 완전 분석"
categories:
- KAFKA
toc: true
toc_sticky: true
toc_label: 목차
---

## 들어가며

Kafka는 고가용성 분산 시스템이지만, 극한 상황에서는 예상치 못한 동작이 발생한다. 각 시나리오를 이해하고 방어 전략을 갖추는 것이 프로덕션 운영의 핵심이다.

---

## 시나리오 1: 브로커 장애 시 리더 선출과 데이터 유실

### 상황 설정

```
초기 상태:
Broker 1 (Leader)   Broker 2 (Follower)   Broker 3 (Follower)
┌─────────────┐     ┌─────────────┐       ┌─────────────┐
│ P0 Leader   │     │ P0 Replica  │       │ P0 Replica  │
│ offset: 100 │────►│ offset: 98  │       │ offset: 95  │
└─────────────┘     └─────────────┘       └─────────────┘

ISR = {Broker1, Broker2, Broker3}
(모두 ISR에 포함, 단 복제 지연 있음)
```

### 장애 발생과 데이터 유실 경로

```
acks=1 설정 시:

1. Producer → Broker1에 offset 99, 100 전송 (ACK 수신)
2. Broker1 장애! (offset 99, 100은 팔로워에 미복제)
3. Controller: ISR 중 Broker2를 새 Leader로 선출
4. Broker2의 최신 offset = 98

결과:
┌─────────────────────────────────────────┐
│ offset 99, 100 영구 유실!               │
│ Producer는 ACK를 받았지만 데이터 없음   │
└─────────────────────────────────────────┘
```

### acks=all 설정 시 시나리오

```
acks=all + min.insync.replicas=2:

1. Producer → Broker1(Leader) 전송
2. Broker1 → Broker2, Broker3 복제 대기
3. 모든 ISR 복제 완료 후 ACK

Broker1 장애 시:
→ Broker2 또는 Broker3 중 하나가 새 Leader
→ 두 팔로워 모두 최신 데이터 보유
→ 데이터 유실 없음!

단, ISR이 {Broker1}만 남은 상태에서 min.insync.replicas=2:
→ Producer에게 NotEnoughReplicasException 발생
→ 쓰기 거부 (데이터 유실보다 가용성 포기)
```

### Unclean Leader Election 위험

```
극단적 시나리오:
Broker 1 (ISR, Leader, offset: 100) → 장애
Broker 2 (ISR, offset: 100)         → 장애
Broker 3 (ISR에서 제외됨, offset: 80) → 살아있음

unclean.leader.election.enable=true (기본값: false):
→ Broker3를 Leader로 선출 (ISR 아님)
→ offset 81~100 영구 유실!
→ 하지만 가용성은 유지됨

unclean.leader.election.enable=false (권장):
→ ISR 멤버가 복구될 때까지 해당 파티션 불가용
→ 데이터 무결성 우선
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

```
초기 상태:
Consumer A → [P0, P1]
Consumer B → [P2, P3]

Consumer A가 처리 중:
1. poll() → [msg_offset_50, msg_offset_51, msg_offset_52] 수신
2. msg_offset_50 처리 완료
3. msg_offset_51 처리 완료
4. msg_offset_52 처리 중...
   ↓
   리밸런싱 발생! (Consumer C 합류)
   ↓
5. Consumer A: P0 해제 (offset_51까지만 커밋)
6. Consumer C: P0 할당 받음 → offset_52부터 읽기 시작
7. Consumer C: msg_offset_52 처리 ← 중복 처리!
   (Consumer A도 처리했었음)
```

### 상세 타임라인

```
시간축:

t=0:  Consumer A: poll() → [off50, off51, off52, off53]
t=1:  Consumer A: off50 처리 완료
t=2:  Consumer A: off51 처리 완료
t=3:  Consumer A: off52 처리 시작 (무거운 작업, DB 저장)
t=5:  리밸런싱 시작 (Consumer C 합류)
t=5:  Consumer A: onPartitionsRevoked() 호출
      → 커밋: offset=52 (off51까지 처리 완료이므로 next=52)
t=6:  Consumer C: P0 할당
t=6:  Consumer C: poll() → [off52, off53, ...]
t=7:  Consumer C: off52 처리 ← 중복!
      (Consumer A가 처리 중이었거나 완료했을 수도 있음)
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

```
변경 전: 파티션 4개
키 "user-123" → hash("user-123") % 4 = 1 → Partition 1

파티션 6개로 증가:
키 "user-123" → hash("user-123") % 6 = 3 → Partition 3!

결과:
Partition 1: [user-123의 과거 메시지들]
Partition 3: [user-123의 새 메시지들]

순서 보장 파괴!
동일 키인데 서로 다른 파티션 = 병렬 처리 가능 = 순서 보장 불가
```

### 실제 영향

```
주문 처리 시스템 예시:

파티션 증가 전:
order-123 생성  → P1 (offset 100)
order-123 수정  → P1 (offset 101)
order-123 취소  → P1 (offset 102)
→ Consumer가 P1만 처리하면 순서 보장

파티션 증가 후 (4→6):
order-123 생성  → P1 (이전에 저장됨)
order-123 수정  → P3 (라우팅 변경!)
order-123 취소  → P3

Consumer-1이 P1 처리: 생성만 보임
Consumer-2가 P3 처리: 수정 → 취소 (생성 없이 취소!)
→ 처리 불가 또는 데이터 불일치
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

```
권장 운영 원칙:
┌────────────────────────────────────────────┐
│ 파티션 수는 처음부터 넉넉하게 설정          │
│ (일반적으로 브로커 수의 2~4배)             │
│                                            │
│ 불가피하게 변경 시:                        │
│ 1. 키 기반 순서 보장 요구사항 재검토        │
│ 2. 새 토픽으로 마이그레이션                 │
│ 3. 컨슈머 멱등성 보장 후 변경              │
└────────────────────────────────────────────┘
```

---

## 시나리오 4: 디스크 가득 참 시 동작

### 브로커 디스크 100% 상황

```
디스크 사용량 증가:
80% → 90% → 95% → 99% → 100%

100% 도달 시:
┌──────────────────────────────────────────────────────┐
│ 1. 새 메시지 쓰기 실패                               │
│    → KafkaStorageException                            │
│    → 해당 파티션 리더가 오류 상태                    │
│                                                      │
│ 2. 프로듀서: TimeoutException / NotLeaderException   │
│                                                      │
│ 3. 컨슈머: 읽기는 가능하지만 lag 급증               │
│                                                      │
│ 4. 복제 중단: 팔로워가 리더를 따라잡지 못함          │
│    → ISR 축소                                        │
│    → acks=all이면 프로듀서 쓰기 더 느려짐            │
└──────────────────────────────────────────────────────┘
```

### 단계별 장애 확산

```
시간 흐름:

t=0:  디스크 100% 도달
t=1:  Partition 0 리더 (Broker 1): 쓰기 실패
t=2:  Producer: 재시도 시작
t=10: 재시도 소진 → ProducerException
t=15: Broker 2, 3 팔로워: 리더로부터 복제 못 받음
      → replica.lag.time.max.ms 초과 → ISR 제외
t=30: ISR = {Broker1} (리더만)
t=31: min.insync.replicas=2 설정 시
      → NotEnoughReplicasException 발생
      → 클러스터 쓰기 완전 불가!
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

```
초기: ISR = {B1(Leader), B2, B3}

Step 1: B3 네트워크 불안정
        replica.lag.time.max.ms=30s 경과
        → ISR = {B1, B2}

Step 2: B2 GC 멈춤 (Full GC 60초)
        → ISR = {B1}
        (리더만 ISR에 남음)

Step 3: min.insync.replicas=2 설정 시
        → 쓰기 거부! (가용성 ↓, 안전성 ↑)

Step 4: B1 (리더) 장애!
        ISR가 비어있음
        unclean.leader.election.enable=true:
        → B3 (ISR 아님, offset: 100 뒤처짐) 리더로 선출
        → 100개 메시지 영구 유실!

unclean.leader.election.enable=false:
        → 해당 파티션 완전 불가용
        → B1 또는 B2 복구 시까지 대기
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

```
Consumer Lag:
┌────────────────────────────────────────────────────────┐
│  Producer가 쓰는 속도 > Consumer가 읽는 속도            │
│                                                        │
│  Log End Offset (최신 메시지 위치):  ────────────────► │
│  Committed Offset (처리 완료 위치):  ──────►           │
│                                     ↑                  │
│                              Lag = 차이                │
└────────────────────────────────────────────────────────┘

현재 Lag: Log End Offset - Committed Offset
```

### Lag 폭증 원인별 분류

```
원인 1: Consumer 처리 속도 저하
┌───────────────────────────────────────────┐
│ - 외부 DB 응답 지연                        │
│ - GC 멈춤                                 │
│ - 처리 로직 CPU 집약적                    │
│ - 다운스트림 서비스 장애                  │
└───────────────────────────────────────────┘

원인 2: Producer 급격한 유입량 증가
┌───────────────────────────────────────────┐
│ - 트래픽 급증 (이벤트, 세일 등)           │
│ - 업스트림 서비스 배치 처리               │
│ - DDoS 또는 비정상 트래픽                 │
└───────────────────────────────────────────┘

원인 3: Consumer 인스턴스 감소
┌───────────────────────────────────────────┐
│ - 배포 중 인스턴스 순차 종료              │
│ - OOM으로 인한 프로세스 종료              │
│ - 리밸런싱 중 처리 중단                   │
└───────────────────────────────────────────┘
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

```
Lag 폭증 감지 시 대응 순서:

Step 1: 원인 파악 (5분 이내)
  kafka-consumer-groups.sh --describe --group order-group
  → Lag이 특정 파티션에 집중? → 해당 파티션 처리 병목
  → 전체 파티션 균등? → 처리 속도 전반적 저하

Step 2: 빠른 완화
  - 처리 느린 컨슈머 재시작
  - max.poll.records 줄이기 (처리 단위 축소)
  - 컨슈머 인스턴스 추가 (파티션 수 미만까지)

Step 3: 근본 원인 해결
  - DB 인덱스 최적화
  - 다운스트림 서비스 복구
  - 처리 로직 비동기화

Step 4: Lag 해소 모니터링
  - 정상화까지 5분 간격 lag 추적
```

---

## 시나리오 7: 네트워크 파티션 시나리오

### Split-Brain 상황

```
정상 상태:
Broker 1 (Leader) ←→ Broker 2 ←→ Broker 3

네트워크 파티션 발생:
┌──────────────────┐      X      ┌──────────────────┐
│   Zone A         │  (단절)     │   Zone B         │
│   Broker 1       │────────────X│   Broker 2       │
│   (리더라고 생각) │             │   Broker 3       │
└──────────────────┘             └──────────────────┘

Zone B에서 새 리더 선출:
→ Broker 2 또는 3이 새 Leader로 선출
→ Broker 1도 여전히 자신이 Leader라고 생각 (zombie leader)
```

### Zombie Leader 문제

```
네트워크 분리 후:

Producer (Zone A) → Broker 1 (zombie) 에 쓰기
Producer (Zone B) → Broker 2 (new leader) 에 쓰기

두 리더 모두 쓰기 수락!

네트워크 복구 후:
Broker 1이 복구 → 새 리더(Broker 2)의 로그와 충돌
Broker 1의 독립적으로 쓴 메시지 폐기!
```

### Kafka의 방어 메커니즘

```
Epoch (Generation Number):

각 리더 선출마다 epoch 증가:
Broker 1: Leader epoch 5 (구 리더)
Broker 2: Leader epoch 6 (새 리더)

Broker 1이 쓰기 시도:
Producer → Broker 1 (epoch 5)
Broker 1 → 자신이 리더인지 ZooKeeper/Controller 확인
→ "당신은 구 리더(epoch 5), 현재 리더는 epoch 6"
→ NotLeaderOrFollowerException 반환!
→ Producer: 새 리더 메타데이터 갱신 후 재시도
```

### 네트워크 파티션 시나리오별 영향

```
시나리오 A: Producer와 Leader가 같은 Zone
Producer ──► Leader(격리됨) ──X──► Follower들
→ acks=1: 쓰기 가능, ISR 축소 위험
→ acks=all: ISR 멤버 감소로 쓰기 거부 가능

시나리오 B: Producer와 Leader가 다른 Zone
Producer ──X──► Leader(Zone A)
Producer ──► 새 Leader(Zone B)에 메타데이터 갱신 후 재연결

시나리오 C: 소수 Zone에 리더
Zone A (2브로커): 리더 보유
Zone B (1브로커): 팔로워만

min.insync.replicas=2 + acks=all:
→ Zone B 분리 시: Zone A에서 계속 쓰기 가능
→ Zone A 분리 시: Zone B 쓰기 불가 (가용성 포기, 안전성 유지)
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

```
멱등성 없는 Producer의 재시도:

1. Producer → msg(A) → Broker
2. Broker: 메시지 저장 완료
3. Broker → ACK 전송
4. 네트워크 지연으로 ACK 손실!
5. Producer: 타임아웃 → msg(A) 재전송
6. Broker: msg(A) 또 저장 (중복!)

                   ┌──────────────────────────────┐
Partition 0:       │ [A][B][A_dup][C]             │ ← A가 두 번!
                   └──────────────────────────────┘
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

```
MAX_IN_FLIGHT_REQUESTS=5, 멱등성 없음:

1. msg1 전송 (flight 중)
2. msg2 전송 (flight 중)
3. msg1 전송 실패 → 재시도 대기
4. msg2 전송 성공
5. msg1 재시도 성공
→ Partition: [msg2, msg1] ← 순서 역전!

MAX_IN_FLIGHT_REQUESTS=1:
1. msg1 전송 → 완료
2. msg2 전송 → 완료
→ Partition: [msg1, msg2] ← 순서 보장, 단 처리량 저하
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

## 극한 시나리오 종합 방어 체크리스트

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
