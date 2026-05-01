---
title: "Kafka Outbox 패턴과 CDC"
categories:
- KAFKA
toc: true
toc_sticky: true
toc_label: 목차
---

## 왜 Outbox 패턴이 필요한가

마이크로서비스 환경에서 DB 저장과 메시지 발행을 동시에 보장하는 것은 어렵다. 아래 코드처럼 작성하면 언제든지 데이터 불일치가 발생할 수 있다.

```java
// 위험한 패턴 — DB 커밋 후 Kafka 발행 실패 가능
@Transactional
public void placeOrder(Order order) {
    orderRepository.save(order);     // DB 저장 성공
    kafkaTemplate.send("orders", order); // 발행 실패 시 불일치 발생
}
```

**두 가지 실패 시나리오:**

```
시나리오 1: DB 저장 성공 → Kafka 발행 실패
  결과: DB에는 주문 있음, 다른 서비스는 주문 모름 → 데이터 불일치

시나리오 2: Kafka 발행 성공 → DB 커밋 실패 (rollback)
  결과: DB에는 주문 없음, 다른 서비스는 주문 처리 시작 → 유령 이벤트
```

분산 트랜잭션(2PC)으로 해결하려 하면 성능 문제와 가용성 감소를 초래한다. Outbox 패턴은 이 문제를 **단일 DB 트랜잭션**으로 해결한다.

---

## Outbox 패턴 동작원리

### 핵심 아이디어

비즈니스 데이터와 발행할 이벤트를 **같은 DB 트랜잭션**으로 저장한다. 별도 프로세스가 Outbox 테이블을 읽어 Kafka로 발행한다.

```
┌─────────────────────────────────────────┐
│              Application                │
│                                         │
│  @Transactional                         │
│  ┌──────────────┐  ┌──────────────────┐ │
│  │ orders 테이블 │  │ outbox 테이블    │ │
│  │ INSERT order │  │ INSERT event     │ │
│  └──────────────┘  └──────────────────┘ │
│         ↑ 같은 트랜잭션 (원자적 보장)        │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│           Message Relay                 │
│  outbox 테이블 폴링 또는 CDC             │
│  → Kafka 발행 → outbox 레코드 삭제/마킹  │
└─────────────────────────────────────────┘
                 ↓
         Kafka Topic
```

### Outbox 테이블 스키마

```sql
CREATE TABLE outbox (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type  VARCHAR(255) NOT NULL,  -- 'Order', 'Payment' 등
    aggregate_id    VARCHAR(255) NOT NULL,  -- 엔티티 ID
    event_type      VARCHAR(255) NOT NULL,  -- 'OrderPlaced', 'OrderCancelled'
    payload         JSONB        NOT NULL,  -- 이벤트 본문
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    status          VARCHAR(20)  NOT NULL DEFAULT 'PENDING', -- PENDING / SENT
    sent_at         TIMESTAMP
);

CREATE INDEX idx_outbox_status_created ON outbox(status, created_at);
```

### Spring + JPA 구현

```java
@Entity
@Table(name = "outbox")
public class OutboxEvent {
    @Id
    private UUID id = UUID.randomUUID();
    private String aggregateType;
    private String aggregateId;
    private String eventType;
    @Column(columnDefinition = "jsonb")
    private String payload;
    private LocalDateTime createdAt = LocalDateTime.now();
    private String status = "PENDING";
    private LocalDateTime sentAt;
}

@Service
@RequiredArgsConstructor
public class OrderService {

    private final OrderRepository orderRepository;
    private final OutboxRepository outboxRepository;
    private final ObjectMapper objectMapper;

    @Transactional
    public void placeOrder(OrderCommand command) {
        // 1. 비즈니스 로직
        Order order = Order.create(command);
        orderRepository.save(order);

        // 2. 같은 트랜잭션 내 Outbox 저장
        OutboxEvent event = OutboxEvent.builder()
            .aggregateType("Order")
            .aggregateId(order.getId().toString())
            .eventType("OrderPlaced")
            .payload(objectMapper.writeValueAsString(new OrderPlacedEvent(order)))
            .build();
        outboxRepository.save(event);
        // 트랜잭션 커밋 시 두 INSERT가 원자적으로 반영됨
    }
}
```

### Message Relay (폴링 방식)

```java
@Component
@RequiredArgsConstructor
public class OutboxMessageRelay {

    private final OutboxRepository outboxRepository;
    private final KafkaTemplate<String, String> kafkaTemplate;

    @Scheduled(fixedDelay = 1000) // 1초마다 폴링
    @Transactional
    public void relay() {
        List<OutboxEvent> pending = outboxRepository
            .findTop100ByStatusOrderByCreatedAtAsc("PENDING");

        for (OutboxEvent event : pending) {
            try {
                String topic = resolveTopicName(event.getAggregateType());
                kafkaTemplate.send(topic, event.getAggregateId(), event.getPayload())
                    .get(5, TimeUnit.SECONDS); // 동기 대기

                event.markSent();
                outboxRepository.save(event);
            } catch (Exception e) {
                log.error("Outbox relay failed for event {}", event.getId(), e);
                // 실패 시 PENDING 유지 → 다음 폴링에 재시도
            }
        }
    }
}
```

### 폴링 방식의 한계

| 문제 | 설명 |
|------|------|
| **지연** | 폴링 주기만큼 발행 지연 발생 |
| **DB 부하** | 주기적 SELECT/UPDATE로 DB 부하 증가 |
| **확장 어려움** | 다중 인스턴스 배포 시 중복 처리 위험 |

이를 해결하는 것이 **CDC(Change Data Capture)** 방식이다.

---

## CDC (Change Data Capture)

### CDC란?

DB의 변경 이력(binlog, WAL 등)을 실시간으로 캡처하여 다른 시스템에 전달하는 기술이다. 애플리케이션 코드 변경 없이 DB 레벨에서 변경사항을 스트리밍한다.

```
┌──────────────┐    binlog/WAL    ┌──────────────┐    ┌───────────┐
│  MySQL /     │ ─────────────→  │   Debezium   │ →  │   Kafka   │
│  PostgreSQL  │                 │  Connector   │    │   Topic   │
└──────────────┘                 └──────────────┘    └───────────┘
```

### DB별 CDC 메커니즘

**MySQL — Binary Log (binlog)**
```
binlog 활성화 필요:
[mysqld]
log_bin = mysql-bin
binlog_format = ROW        # STATEMENT 아닌 ROW 필수
binlog_row_image = FULL    # 변경 전후 전체 행 기록
server_id = 1
```

**PostgreSQL — Write-Ahead Log (WAL)**
```
postgresql.conf:
wal_level = logical         # logical replication 활성화
max_replication_slots = 10
max_wal_senders = 10

논리적 복제 슬롯 생성:
SELECT pg_create_logical_replication_slot('debezium_slot', 'pgoutput');
```

---

## Debezium CDC 구현

### Debezium 아키텍처

```
┌──────────────────────────────────────────────────────────┐
│                    Kafka Connect                         │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Debezium Connector                  │    │
│  │                                                  │    │
│  │  ┌──────────────┐    ┌────────────────────────┐ │    │
│  │  │ binlog/WAL   │    │   Event Transformation  │ │    │
│  │  │   Reader     │ →  │   (SMT 적용 가능)       │ │    │
│  │  └──────────────┘    └────────────────────────┘ │    │
│  └─────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
           ↑                          ↓
      MySQL/PostgreSQL           Kafka Topic
```

### Debezium Connector 설정 (MySQL)

```json
{
  "name": "order-outbox-connector",
  "config": {
    "connector.class": "io.debezium.connector.mysql.MySqlConnector",
    "database.hostname": "mysql",
    "database.port": "3306",
    "database.user": "debezium",
    "database.password": "dbz",
    "database.server.id": "184054",
    "database.server.name": "orderdb",
    "database.include.list": "orderservice",
    "table.include.list": "orderservice.outbox",
    "database.history.kafka.bootstrap.servers": "kafka:9092",
    "database.history.kafka.topic": "schema-changes.orderdb",

    "transforms": "outbox",
    "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter",
    "transforms.outbox.table.field.event.id": "id",
    "transforms.outbox.table.field.event.key": "aggregate_id",
    "transforms.outbox.table.field.event.type": "event_type",
    "transforms.outbox.table.field.event.payload": "payload",
    "transforms.outbox.route.by.field": "aggregate_type",
    "transforms.outbox.route.topic.replacement": "outbox.${routedByValue}"
  }
}
```

### Debezium이 생성하는 이벤트 구조

```json
{
  "before": null,
  "after": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "aggregate_type": "Order",
    "aggregate_id": "12345",
    "event_type": "OrderPlaced",
    "payload": "{\"orderId\":\"12345\",\"amount\":50000}",
    "created_at": "2026-05-01T10:00:00",
    "status": "PENDING"
  },
  "op": "c",       // c=create, u=update, d=delete, r=read(snapshot)
  "ts_ms": 1746097200000,
  "source": {
    "db": "orderservice",
    "table": "outbox",
    "server_id": 184054,
    "pos": 123456789
  }
}
```

### EventRouter SMT (Single Message Transformation)

Debezium의 Outbox EventRouter SMT는 outbox 테이블의 INSERT 이벤트를 받아 `aggregate_type` 컬럼 값을 기반으로 자동으로 라우팅한다.

```
outbox INSERT (aggregate_type='Order')
  → Kafka topic: outbox.Order

outbox INSERT (aggregate_type='Payment')
  → Kafka topic: outbox.Payment
```

---

## Outbox vs CDC 비교

| 구분 | Outbox (폴링) | Outbox + CDC (Debezium) | 직접 CDC |
|------|--------------|------------------------|---------|
| **지연** | 폴링 주기 (수백ms~수초) | 수십ms | 수십ms |
| **DB 부하** | 추가 쿼리 부하 | binlog 읽기 (낮음) | binlog 읽기 |
| **코드 변경** | 필요 (Outbox 저장 로직) | 필요 (Outbox 저장 로직) | 불필요 |
| **이벤트 스키마** | 명시적 설계 가능 | 명시적 설계 가능 | DB 스키마 의존 |
| **멱등성** | 직접 구현 필요 | Kafka at-least-once | Kafka at-least-once |
| **운영 복잡도** | 낮음 | 중간 (Kafka Connect 필요) | 중간 |
| **장애 내성** | 폴링 실패 시 재시도 | Connector 재시작으로 복구 | 복구 가능 |
| **구조적 결합도** | DB 테이블 의존 | DB 테이블 의존 | DB 스키마 강결합 |

### 언제 무엇을 선택할까

```
소규모 서비스, 낮은 처리량
  → Outbox 폴링 방식 (단순하고 충분)

대규모 서비스, 낮은 레이턴시 요구
  → Outbox + Debezium CDC

레거시 DB, 코드 변경 불가
  → 직접 CDC (주의: 이벤트 스키마 통제 어려움)
```

---

## 분산 트랜잭션과의 관계

### 2PC (Two-Phase Commit) 문제

```
Phase 1 (Prepare):
  Coordinator → DB: "커밋 준비됐나?"
  Coordinator → Kafka: "커밋 준비됐나?"

Phase 2 (Commit):
  Coordinator → DB: "커밋"
  Coordinator → Kafka: "커밋"

문제:
  - Coordinator 장애 시 시스템 전체 블로킹
  - Kafka는 2PC를 지원하지 않음 (XA 트랜잭션 미지원)
  - 성능 저하 (모든 참여자 대기)
```

### Saga 패턴과 Outbox

Outbox는 Saga 패턴과 자연스럽게 조합된다. 각 서비스가 자신의 트랜잭션을 완료하고 다음 서비스를 위한 이벤트를 Outbox에 저장한다.

```
주문 서비스                재고 서비스              결제 서비스
     │                          │                       │
     │ OrderPlaced 이벤트        │                       │
     │ (Outbox→Kafka)           │                       │
     │ ─────────────────────→   │                       │
     │                          │ StockReserved 이벤트   │
     │                          │ (Outbox→Kafka)        │
     │                          │ ──────────────────→   │
     │                          │                       │ PaymentCompleted
     │                          │                       │ (Outbox→Kafka)
```

보상 트랜잭션(Compensating Transaction)도 같은 방식으로 Outbox를 통해 발행한다.

---

## 실무 고려사항

### Outbox 테이블 정리 전략

Outbox 테이블은 지속적으로 쌓이므로 주기적 정리가 필요하다.

```sql
-- 24시간 이전 SENT 레코드 삭제
DELETE FROM outbox
WHERE status = 'SENT'
  AND sent_at < NOW() - INTERVAL '24 hours'
LIMIT 10000;
```

```java
@Scheduled(cron = "0 0 * * * *") // 매 시간
@Transactional
public void cleanupOutbox() {
    int deleted = outboxRepository.deleteByStatusAndSentAtBefore(
        "SENT",
        LocalDateTime.now().minusHours(24)
    );
    log.info("Outbox cleanup: {} records deleted", deleted);
}
```

### 멱등성 처리

Outbox 방식은 at-least-once 보장이다. 컨슈머는 반드시 멱등성을 구현해야 한다.

```java
@KafkaListener(topics = "outbox.Order")
@Transactional
public void handleOrderEvent(ConsumerRecord<String, String> record) {
    String eventId = record.headers()
        .lastHeader("debezium.event.id")
        .value().toString();

    // 이미 처리한 이벤트인지 확인
    if (processedEventRepository.existsByEventId(eventId)) {
        log.info("Duplicate event ignored: {}", eventId);
        return;
    }

    // 비즈니스 처리
    processOrder(record.value());

    // 처리 완료 기록
    processedEventRepository.save(new ProcessedEvent(eventId));
}
```

### 순서 보장

Outbox에서 같은 `aggregate_id`를 Kafka 메시지 키로 사용하면 같은 파티션으로 라우팅되어 순서가 보장된다.

```java
kafkaTemplate.send(
    topic,
    event.getAggregateId(),  // 파티셔닝 키 = aggregate_id
    event.getPayload()
);
```

### 모니터링 지표

```
# Prometheus 메트릭 예시
outbox_pending_count         # 미발행 이벤트 수 (높으면 relay 문제)
outbox_relay_duration_ms     # 릴레이 처리 시간
outbox_relay_failure_total   # 릴레이 실패 횟수
debezium_connector_status    # CDC 커넥터 상태
```

```sql
-- Outbox lag 모니터링 쿼리
SELECT
    COUNT(*) AS pending_count,
    MIN(created_at) AS oldest_pending,
    EXTRACT(EPOCH FROM (NOW() - MIN(created_at))) AS lag_seconds
FROM outbox
WHERE status = 'PENDING';
```
