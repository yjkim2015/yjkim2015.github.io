---
title: "Redis Streams 완전 정복 — Kafka 없이 이벤트 스트리밍을 구현하는 법"
categories:
- REDIS
toc: true
toc_sticky: true
toc_label: 목차
---

> **한 줄 요약**: Redis Streams는 append-only log + Consumer Group + PEL(ACK 추적)을 결합하여, Kafka 없이도 at-least-once 이벤트 스트리밍을 단일 Redis로 구현하는 자료구조입니다.

---

## 1. Redis Streams란 무엇인가

### Append-only Log 구조

append-only log는 뒤에만 추가할 수 있고 기존 데이터를 수정하지 않습니다. Kafka의 파티션도 같은 구조입니다. 차이는 Kafka가 **디스크 기반 분산 시스템**인 반면, Redis Streams는 **인메모리 단일 프로세스** 내에서 동작한다는 점입니다.

```
Kafka 파티션(디스크):   [msg0][msg1][msg2][msg3] → 오프셋으로 위치 추적
Redis Streams(메모리):  [1715420001000-0][1715420001001-0] → Entry ID로 위치 추적
```

### Entry ID 설계

모든 메시지는 `<밀리초 타임스탬프>-<시퀀스 번호>` 형태의 고유 ID를 가집니다.

```
1715420001234-0   ← 해당 밀리초의 첫 번째 메시지
1715420001234-1   ← 같은 밀리초의 두 번째 메시지
```

1. **단조 증가 보장**: NTP drift로 시계가 뒤로 가도 Redis가 마지막 ID 이상으로 강제 발급합니다.
2. **시간 기반 범위 쿼리**: `XRANGE mystream 1715420000000-0 1715420010000-0`으로 특정 시간 구간 조회가 가능합니다.
3. **유일성 보장**: 여러 클라이언트가 동시에 XADD해도 Redis가 직렬화하므로 ID 충돌이 없습니다.

### 기존 자료구조의 한계

| 구조 | 치명적 한계 |
|------|-----------|
| **List (LPUSH/BRPOP)** | BRPOP이 메시지를 꺼내면서 **삭제** → 멀티 컨슈머 불가, ACK 없음 |
| **Pub/Sub** | 메모리에도 저장 안 함 → 히스토리 재생 불가, fire-and-forget |

**Streams가 해결하는 것**: 소비해도 삭제 안 됨, PEL로 ACK 추적, XRANGE로 과거 재생, MAXLEN으로 메모리 제어.

---

## 2. 핵심 명령어 동작원리

### XADD — 메시지 추가

```bash
XADD orders MAXLEN ~ 10000 * event ORDER_PLACED orderId 12345
```

내부 동작: ① Unix 밀리초 읽기 → ② 새 ID 발급 → ③ radix tree에 저장 → ④ 블로킹 대기 클라이언트 wakeup

**트리밍 옵션:**

| 옵션 | 의미 | 비용 |
|------|------|------|
| `MAXLEN 10000` | 정확히 10,000개 유지 | radix tree 노드 분할 필요, 비용 큼 |
| `MAXLEN ~ 10000` | 최소 10,000개 유지 (노드 경계에서 삭제) | O(1)에 가까움, **프로덕션 권장** |
| `MINID ~ <id>` | 해당 ID 이전 메시지 삭제 | 시간 기반 보존 정책에 사용 |

### XREAD — 단순 읽기

```bash
XREAD COUNT 10 BLOCK 5000 STREAMS orders $
```

`$`는 "이 명령 이후의 새 메시지만", `BLOCK 5000`은 최대 5초 대기. 내부적으로 XADD 시점에 event-driven으로 깨우므로 폴링보다 효율적입니다.

**한계**: 여러 컨슈머가 XREAD하면 **모든 컨슈머가 동일 메시지**를 받습니다(fan-out). 작업 분산이 필요하면 Consumer Group을 사용해야 합니다.

### XREADGROUP + Consumer Group

Consumer Group의 핵심:
1. 같은 그룹 내 컨슈머들은 **서로 다른 메시지**를 받습니다 (파티션 없는 파티셔닝)
2. **받은 것**과 **처리 완료**를 분리합니다 (PEL)

```bash
# 그룹 생성 ($ = 지금부터, 0 = 처음부터)
XGROUP CREATE orders processing-group $ MKSTREAM

# 메시지 읽기 (> = 아직 전달 안 된 새 메시지)
XREADGROUP GROUP processing-group consumer-1 COUNT 10 BLOCK 5000 STREAMS orders >

# 처리 완료 확인 → PEL에서 제거
XACK orders processing-group 1715420001234-0

# 죽은 컨슈머의 메시지 재할당 (60초 이상 ACK 안 된 것)
XAUTOCLAIM orders processing-group consumer-2 60000 0-0 COUNT 10
```

### "0" vs ">" — 재시작 시 필수 패턴

| ID | 의미 | 용도 |
|----|------|------|
| `>` | 아직 전달 안 된 **새 메시지** | 정상 운영 중 |
| `0` | 이 컨슈머의 PEL에 있는 **미확인 메시지** | 재시작 후 미처리 건 재처리 |

**올바른 재시작 패턴**: 먼저 `0`으로 PEL 미처리 건을 소화한 뒤, PEL이 비면 `>`로 전환합니다.

```java
public void start() {
    // 1단계: PEL에 남은 미처리 메시지 재처리
    while (true) {
        List<MapRecord<...>> records = streamOps.read(
            Consumer.from(GROUP, consumerId),
            StreamReadOptions.empty().count(100),
            StreamOffset.create(STREAM, ReadOffset.from("0"))
        );
        if (records == null || records.isEmpty()) break;
        records.forEach(this::processAndAck);
    }

    // 2단계: 새 메시지 처리로 전환
    while (!Thread.currentThread().isInterrupted()) {
        List<MapRecord<...>> records = streamOps.read(
            Consumer.from(GROUP, consumerId),
            StreamReadOptions.empty().count(10).block(Duration.ofSeconds(1)),
            StreamOffset.create(STREAM, ReadOffset.lastConsumed())
        );
        if (records != null) records.forEach(this::processAndAck);
    }
}
```

---

## 3. 다른 메시지 큐와의 비교

### Redis Streams vs Kafka

| 기준 | Redis Streams | Kafka |
|------|--------------|-------|
| **저장** | 인메모리 (AOF로 디스크 백업) | 디스크 (순차 쓰기) |
| **파티셔닝** | 없음 — Consumer Group이 암묵적 분산 | 명시적 파티션, 키 기반 라우팅 |
| **리밸런싱** | 없음 | 자동 리밸런싱 (짧은 중단) |
| **처리량** | 수십만 TPS (단일 인스턴스) | 수백만 TPS (클러스터) |
| **지연시간** | <1ms | 1~50ms |
| **Exactly-once** | 미지원 (앱 레벨 멱등) | Transactions API 지원 |
| **수평 확장** | 앱 레벨 키 샤딩 필요 | 파티션 추가로 선형 확장 |

**Streams가 나은 경우**: 이미 Redis 사용 중, 소규모(수백만/일 이하), 지연시간 <1ms, 짧은 보존 기간

**Kafka가 압도적인 경우**: TB 단위 히스토리, 수백만 TPS, Exactly-once 필수, Kafka Streams/Flink 연동

### Redis Streams vs RabbitMQ

| 기준 | Redis Streams | RabbitMQ |
|------|--------------|----------|
| **라우팅** | 없음 — 앱이 키 결정 | Exchange 4종 (Direct/Topic/Fanout/Headers) |
| **ACK** | PEL에서 제거 (메시지는 유지) | Queue에서 삭제 |
| **DLQ** | 직접 구현 필요 | 네이티브 지원 |
| **우선순위 큐** | 없음 | 0~255 우선순위 지원 |

### Redis Streams vs AWS SQS

| 기준 | Redis Streams | AWS SQS |
|------|--------------|---------|
| **운영** | 직접 운영 (Sentinel/Cluster) | 완전 관리형 (99.9% SLA) |
| **순서** | 전역 보장 (단일 키) | Standard: 미보장, FIFO: 보장 |
| **비용** | 인스턴스 고정비 | 100만 요청당 $0.40~$0.50 |

### 종합 비교

| 기능 | Streams | Kafka | RabbitMQ | SQS | Pub/Sub | List |
|------|---------|-------|----------|-----|---------|------|
| 영속성 | 메모리+AOF | 디스크 | 디스크 | 관리형 | 없음 | 메모리 |
| 순서 보장 | 전역 | 파티션 내 | Queue 내 | FIFO만 | 발행순 | FIFO |
| ACK | XACK+PEL | 오프셋 | basic.ack | Delete | 없음 | 없음 |
| 재생 | XRANGE | 오프셋 | 불가 | 불가 | 불가 | 불가 |
| Exactly-once | 미지원 | 지원 | 미지원 | 미지원 | 미지원 | 미지원 |
| 최대 TPS | 수십만 | 수백만 | 수만 | 무제한 | 수십만 | 수십만 |
| 지연시간 | <1ms | 1~5ms | 1~5ms | 수십ms | <1ms | <1ms |
| DLQ | 수동 | 수동 | 네이티브 | 네이티브 | 없음 | 없음 |

---

## 4. 실전 코드 — Java/Spring Boot

### Producer

```java
@Service
public class OrderEventProducer {

    private final StreamOperations<String, String, String> streamOps;

    public RecordId publish(String orderId, String event) {
        return streamOps.add(StreamRecords.newRecord()
            .in("orders")
            .ofMap(Map.of(
                "event", event,
                "orderId", orderId,
                "ts", String.valueOf(System.currentTimeMillis())
            )));
    }
}
```

### Consumer + DLQ 패턴

```java
@Service
public class OrderEventConsumer {

    private final StreamOperations<String, String, String> streamOps;
    private static final String STREAM = "orders";
    private static final String GROUP = "order-processing";
    private final String consumerId = "consumer-" + UUID.randomUUID();

    @Scheduled(fixedDelay = 100)
    public void consume() {
        List<MapRecord<String, String, String>> records = streamOps.read(
            Consumer.from(GROUP, consumerId),
            StreamReadOptions.empty().count(10).block(Duration.ofMillis(100)),
            StreamOffset.create(STREAM, ReadOffset.lastConsumed())
        );
        if (records == null) return;

        for (MapRecord<String, String, String> record : records) {
            try {
                processOrder(record.getValue());
                streamOps.acknowledge(STREAM, GROUP, record.getId());
            } catch (Exception e) {
                handleFailure(record, e);
            }
        }
    }

    private void handleFailure(MapRecord<String, String, String> record, Exception e) {
        PendingMessages pending = streamOps.pending(STREAM, GROUP,
            Range.closed(record.getId().getValue(), record.getId().getValue()), 1);

        if (pending.size() > 0 && pending.get(0).getTotalDeliveryCount() >= 3) {
            streamOps.add(StreamRecords.newRecord()
                .in("orders:dlq").ofMap(record.getValue()));
            streamOps.acknowledge(STREAM, GROUP, record.getId());
            log.error("DLQ 이동: {}", record.getId());
        }
        // 3회 미만이면 ACK 안 함 → PEL에 남아 XAUTOCLAIM 대상
    }
}
```

### 죽은 컨슈머 메시지 재할당

```java
@Scheduled(fixedDelay = 30_000)  // 30초마다
public void reclaimStale() {
    // 60초 이상 ACK 안 된 메시지를 현재 컨슈머로 재할당
    // min-idle-time 권장: 평균 처리시간 × 3
}
```

---

## 5. 운영 — 극한 시나리오

### 메모리 폭발

`MAXLEN`이 없으면 Redis 메모리가 차서 `OOM command not allowed` 에러와 함께 XADD가 거부됩니다.

**대응**: 항상 `MAXLEN ~`을 설정하되, **PEL에 있는 메시지보다 크게** 설정해야 합니다. MAXLEN이 PEL보다 작으면 처리 중인 메시지가 스트림에서 삭제되어 **좀비 PEL**이 생깁니다.

> 엔트리당 ~500B, 10만 개 = 50MB. PEL 엔트리당 ~100B. 생각보다 작지만 PEL 누수가 위험합니다.

### 컨슈머 장애와 PEL 누적

**탐지**: `XPENDING orders group - + 10`으로 idle time이 수 분 이상인 항목 모니터링.

**복구**: XAUTOCLAIM의 min-idle-time을 `평균 처리시간 × 3` 이상으로 설정. 너무 짧으면 정상 처리 중인 메시지를 빼앗아 중복 처리됩니다.

### Redis 재시작 시 데이터 보존

```
appendonly yes
appendfsync everysec    # 최대 1초 유실 가능
save 60 10000           # RDB 스냅샷 병행
```

Consumer Group 메타데이터(last-delivered-id, PEL)도 AOF에 보존됩니다.

### 클러스터 모드 주의사항

- 여러 스트림을 한 명령에 읽으려면 **같은 슬롯**이어야 합니다. Hash Tag로 강제 배치: `orders:{shard0}:events`
- Consumer Group은 **키 단위**입니다. 샤드별로 그룹을 따로 생성해야 합니다.

### 순서 역전이 발생하는 케이스

1. Consumer Group 내 병렬 처리 → consumer-2가 consumer-1보다 먼저 완료
2. XCLAIM 후 구/신 메시지 처리가 뒤섞임
3. 여러 스트림 키 사용 시 같은 userId 이벤트가 다른 컨슈머에서 처리

순서가 중요하면 같은 키의 이벤트를 같은 스트림에 넣고 단일 컨슈머로 처리하거나, Entry ID 기반 낙관적 락을 사용합니다.

---

## 6. 성능 벤치마크

단일 Redis 7.x 인스턴스 (8코어, 32GB) 기준:

| 명령 | 단건 | 파이프라인(100) |
|------|------|----------------|
| XADD | ~100K TPS | ~800K TPS |
| XREAD | ~80K TPS | ~600K TPS |
| XREADGROUP | ~70K TPS | ~500K TPS |
| XACK | ~120K TPS | ~900K TPS |

| 지표 | Redis Streams | Kafka (복제) |
|------|--------------|-------------|
| P50 | <0.5ms | 5~10ms |
| P99 | <2ms | 20~50ms |
| P99.9 | <10ms | 100~500ms |

> 지연시간만 비교하면 Streams가 압도적이지만, Kafka의 강점은 처리량·내구성·확장성입니다.

---

## 면접 포인트

<details>
<summary><strong>Q. Kafka와의 가장 큰 차이?</strong></summary>

저장 매체(메모리 vs 디스크)와 확장 단위입니다. Kafka는 파티션이라는 독립 확장 단위가 있어 클러스터 수평 확장이 자연스럽고, Exactly-once를 지원합니다. Streams는 단일 키가 단일 인스턴스에 바인딩되어 앱 레벨 샤딩이 필요하며, at-least-once만 보장합니다.

</details>

<details>
<summary><strong>Q. PEL이 왜 중요한가?</strong></summary>

at-least-once 보장의 핵심입니다. 컨슈머가 메시지를 받고 죽으면 PEL에 남아있어 XAUTOCLAIM으로 다른 컨슈머가 재처리할 수 있습니다. PEL 없이는 메시지 유실이 불가피합니다.

</details>

<details>
<summary><strong>Q. `>` 와 `0` 차이?</strong></summary>

`>`는 새 메시지, `0`은 PEL의 미확인 메시지입니다. 재시작 시 `0` → `>` 순서로 전환해야 미처리 건이 유실되지 않습니다.

</details>

<details>
<summary><strong>Q. MAXLEN이 PEL보다 작으면?</strong></summary>

가장 위험한 운영 실수입니다. 스트림에서 삭제된 메시지가 PEL에만 남아 좀비 항목이 됩니다. XCLAIM/XAUTOCLAIM으로 재처리하려 해도 실제 데이터가 없어 영원히 처리 불가합니다.

</details>

<details>
<summary><strong>Q. Exactly-once 구현 가능?</strong></summary>

Streams 자체는 at-least-once만 지원합니다. 처리한 Entry ID를 Redis Set에 저장하고 Lua Script로 중복 체크하면 앱 레벨 멱등을 구현할 수 있지만, 완전한 Exactly-once가 필요하면 Kafka Transactions API가 적합합니다.

</details>
