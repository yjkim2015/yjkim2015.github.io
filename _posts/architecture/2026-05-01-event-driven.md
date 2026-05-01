---
title: "이벤트 기반 아키텍처"
categories: ARCHITECTURE
tags: [EDA, EventDriven, EventSourcing, CQRS, EventStore, EventualConsistency]
toc: true
toc_sticky: true
toc_label: 목차
date: 2026-05-01
---

전통적인 시스템에서 서비스들은 서로를 직접 호출한다. Order Service가 Payment, Inventory, Notification을 직접 호출하면, 하나라도 다운되면 주문 자체가 실패한다. 이벤트 기반 아키텍처(EDA)는 서비스들이 이벤트를 통해 간접적으로 소통해 결합도를 낮춘다.

> **비유**: 라디오 방송국(Event Producer)이 뉴스(이벤트)를 송출하면, 각 가정(Event Consumer)이 독립적으로 라디오를 켜서 듣는다. 방송국은 누가 듣는지 모르고, 청취자가 늘어도 방송국은 변경이 없다. 청취자가 라디오를 꺼도(서비스 다운) 방송국은 계속 방송한다.

---

## EDA 핵심 개념

<div class="mermaid">
graph LR
    subgraph "Event Producer"
        OS[Order Service]
    end

    subgraph "Event Channel"
        EB[Event Bus\nKafka/RabbitMQ]
    end

    subgraph "Event Consumers"
        PS[Payment Service]
        IS[Inventory Service]
        NS[Notification Service]
        AS[Analytics Service]
    end

    OS -->|OrderCreated 이벤트 발행| EB
    EB -->|구독| PS
    EB -->|구독| IS
    EB -->|구독| NS
    EB -->|구독| AS
</div>

```
특징:
1. Producer는 Consumer를 모름 (느슨한 결합)
2. Consumer는 독립적으로 이벤트 처리 (확장 용이)
3. 새 Consumer 추가 = Producer 수정 없음
4. Consumer 다운 시 이벤트는 브로커에 보관 → 복구 후 처리
```

---

## 이벤트 설계

### 이벤트 명명 규칙

```
도메인 + 과거형 동사 (일어난 사실 표현)
✓ OrderCreated, PaymentCompleted, InventoryReserved
✗ CreateOrder, DoPayment (명령형 금지)

이벤트 = 불변의 사실 (과거에 일어난 일)
명령 = 의도 (미래에 할 일)
```

### 이벤트 구조

```java
// 이벤트는 불변 객체로 설계
public record OrderCreatedEvent(
    String eventId,           // 이벤트 고유 ID (멱등성 처리용)
    String eventType,         // "order.created"
    Instant occurredAt,       // 발생 시각 (과거)
    Long orderId,             // 집합체 ID
    Long userId,
    Long productId,
    int quantity,
    BigDecimal amount,
    String status             // 이벤트 발생 시점의 상태 스냅샷
) {
    public OrderCreatedEvent(Order order) {
        this(
            UUID.randomUUID().toString(),
            "order.created",
            Instant.now(),
            order.getId(),
            order.getUserId(),
            order.getProductId(),
            order.getQuantity(),
            order.getAmount(),
            order.getStatus().name()
        );
    }
}
```

### 이벤트 버전 관리

```java
// v1
public record OrderCreatedEvent(
    String eventId, Long orderId, Long userId, BigDecimal amount
) {}

// v2: 필드 추가 (하위 호환)
public record OrderCreatedEventV2(
    String eventId, Long orderId, Long userId, BigDecimal amount,
    String currency,    // 신규 필드
    String region       // 신규 필드
) {}

// Consumer: 모르는 필드는 무시 (관대한 파싱)
// Producer: 기존 Consumer가 처리할 수 있도록 필드 제거 금지
```

---

## Event Sourcing

### 개념

상태를 저장하는 대신, 상태를 변경하는 이벤트의 시퀀스를 저장한다.

```
전통적 방식:
  orders 테이블:
    id=1, status=SHIPPED, amount=50000, updatedAt=...
  → 현재 상태만 보임. 어떻게 이 상태가 됐는지 알 수 없음.

Event Sourcing:
  order_events 테이블:
    1, OrderCreated,   {amount: 50000, productId: 42}
    2, PaymentCharged, {amount: 50000, method: "card"}
    3, InventoryReserved, {productId: 42, qty: 1}
    4, OrderShipped,   {trackingNo: "KR123456"}
  → 전체 이력이 보임. 현재 상태 = 이벤트 재생 결과
```

<div class="mermaid">
graph LR
    subgraph "이벤트 저장소"
        E1[OrderCreated\nt=0]
        E2[PaymentCharged\nt=1]
        E3[InventoryReserved\nt=2]
        E4[OrderShipped\nt=3]
        E1 --> E2 --> E3 --> E4
    end

    subgraph "현재 상태 재구성"
        AGG[Order Aggregate\n이벤트 재생]
        E1 -->|apply| AGG
        E2 -->|apply| AGG
        E3 -->|apply| AGG
        E4 -->|apply| AGG
        AGG --> STATE[status=SHIPPED\namount=50000\n...]
    end
</div>

### 구현

```java
// Aggregate: 이벤트를 적용해 상태를 재구성
public class Order {

    private Long id;
    private OrderStatus status;
    private BigDecimal amount;
    private String trackingNo;

    private final List<DomainEvent> uncommittedEvents = new ArrayList<>();

    // 생성자 대신 팩토리 메서드
    public static Order create(CreateOrderCommand cmd) {
        Order order = new Order();
        order.apply(new OrderCreatedEvent(cmd));
        return order;
    }

    public void charge(BigDecimal amount) {
        if (status != OrderStatus.PENDING) {
            throw new IllegalStateException("결제 불가 상태: " + status);
        }
        apply(new PaymentChargedEvent(this.id, amount));
    }

    public void ship(String trackingNo) {
        apply(new OrderShippedEvent(this.id, trackingNo));
    }

    // 이벤트 적용 (상태 변경만, 사이드 이펙트 없음)
    private void apply(DomainEvent event) {
        handle(event);
        uncommittedEvents.add(event);
    }

    // 이벤트 재생 (저장소에서 복원 시)
    public void replayEvent(DomainEvent event) {
        handle(event);
    }

    private void handle(DomainEvent event) {
        switch (event) {
            case OrderCreatedEvent e -> {
                this.id = e.orderId();
                this.status = OrderStatus.PENDING;
                this.amount = e.amount();
            }
            case PaymentChargedEvent e -> {
                this.status = OrderStatus.PAID;
            }
            case OrderShippedEvent e -> {
                this.status = OrderStatus.SHIPPED;
                this.trackingNo = e.trackingNo();
            }
            default -> {}
        }
    }

    public List<DomainEvent> getUncommittedEvents() {
        return Collections.unmodifiableList(uncommittedEvents);
    }
}

// Event Store Repository
@Repository
public class OrderEventStoreRepository {

    private final EventStore eventStore;

    public void save(Order order) {
        List<DomainEvent> events = order.getUncommittedEvents();
        eventStore.append("order-" + order.getId(), events);
    }

    public Order findById(Long orderId) {
        List<DomainEvent> events = eventStore.load("order-" + orderId);

        if (events.isEmpty()) throw new OrderNotFoundException(orderId);

        Order order = new Order();
        events.forEach(order::replayEvent);
        return order;
    }
}
```

### 스냅샷

이벤트가 많아지면 재생 시간이 길어진다. 주기적으로 스냅샷을 저장해 성능을 최적화한다.

```java
// 1000개 이벤트마다 스냅샷 저장
public Order findById(Long orderId) {
    // 1. 가장 최근 스냅샷 로드
    Optional<OrderSnapshot> snapshot = snapshotRepository
        .findLatest(orderId);

    Order order;
    long startVersion;

    if (snapshot.isPresent()) {
        order = snapshot.get().toOrder();
        startVersion = snapshot.get().getVersion();
    } else {
        order = new Order();
        startVersion = 0;
    }

    // 2. 스냅샷 이후 이벤트만 재생
    List<DomainEvent> events = eventStore.load("order-" + orderId, startVersion);
    events.forEach(order::replayEvent);

    // 3. 1000개 이상 이벤트 쌓이면 새 스냅샷 저장
    if (events.size() > 1000) {
        snapshotRepository.save(OrderSnapshot.from(order));
    }

    return order;
}
```

---

## CQRS + Event Sourcing 결합

Event Sourcing은 CQRS와 함께 쓸 때 강력해진다.

<div class="mermaid">
graph TD
    subgraph "Command Side"
        CMD[Command] --> AGG[Order Aggregate]
        AGG --> ES[(Event Store\n이벤트 영구 저장)]
    end

    subgraph "이벤트 전파"
        ES -->|이벤트 발행| KB[Kafka]
    end

    subgraph "Query Side (Projection)"
        KB -->|소비| P1[Order Status Projection\n주문 상태 뷰]
        KB -->|소비| P2[Order List Projection\n목록 뷰]
        KB -->|소비| P3[Analytics Projection\n통계 뷰]
        P1 --> DB1[(Status DB\nMySQL)]
        P2 --> DB2[(List DB\nElasticsearch)]
        P3 --> DB3[(Analytics DB\nClickHouse)]
    end

    Q[Query] -->|빠른 조회| DB1
    Q2[Search Query] -->|전문 검색| DB2
</div>

---

## Eventual Consistency (최종 일관성)

EDA에서는 강한 일관성(Strong Consistency) 대신 최종 일관성을 수용한다.

```
강한 일관성:
  주문 생성 → 즉시 모든 시스템 반영
  → 분산 환경에서 달성 어려움, 성능 저하

최종 일관성:
  주문 생성 → 이벤트 발행 → 각 서비스가 비동기 처리
  → 잠시 후 모든 시스템 일관된 상태로 수렴
  → 그 사이의 불일치는 허용
```

```java
// 사용자 경험: 최종 일관성 숨기기

@RestController
public class OrderController {

    @PostMapping("/orders")
    public ResponseEntity<OrderResponse> createOrder(@RequestBody OrderRequest request) {
        Order order = orderService.create(request);  // 이벤트 발행

        // 즉시 반환 (Payment, Inventory 처리 완료 전)
        return ResponseEntity.accepted()
            .body(OrderResponse.builder()
                .orderId(order.getId())
                .status("PROCESSING")  // 처리 중 상태 표시
                .message("주문이 접수되었습니다. 처리 중입니다.")
                .pollUrl("/orders/" + order.getId() + "/status")
                .build());
    }

    @GetMapping("/orders/{orderId}/status")
    public OrderStatusResponse getStatus(@PathVariable Long orderId) {
        // 폴링 또는 SSE로 최종 상태 전달
        return orderQueryService.getStatus(orderId);
    }
}
```

---

## 이벤트 스토어 구현

### DB 기반 이벤트 스토어

```sql
CREATE TABLE event_store (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    stream_id   VARCHAR(255) NOT NULL,    -- "order-123"
    event_type  VARCHAR(255) NOT NULL,    -- "OrderCreated"
    version     BIGINT NOT NULL,          -- 스트림 내 순서
    payload     JSON NOT NULL,            -- 이벤트 데이터
    metadata    JSON,                     -- traceId, userId 등
    occurred_at TIMESTAMP(6) NOT NULL,
    UNIQUE KEY uq_stream_version (stream_id, version)
);
```

```java
@Repository
public class JdbcEventStore {

    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper;

    public void append(String streamId, List<DomainEvent> events) {
        // 낙관적 잠금: 동시 쓰기 충돌 방지
        long currentVersion = getCurrentVersion(streamId);

        for (int i = 0; i < events.size(); i++) {
            DomainEvent event = events.get(i);
            try {
                jdbc.update(
                    "INSERT INTO event_store (stream_id, event_type, version, payload, occurred_at) VALUES (?, ?, ?, ?, ?)",
                    streamId,
                    event.getClass().getSimpleName(),
                    currentVersion + i + 1,
                    objectMapper.writeValueAsString(event),
                    Instant.now()
                );
            } catch (DuplicateKeyException e) {
                throw new OptimisticLockException("동시 수정 충돌: " + streamId);
            } catch (JsonProcessingException e) {
                throw new RuntimeException(e);
            }
        }
    }

    public List<DomainEvent> load(String streamId, long fromVersion) {
        return jdbc.query(
            "SELECT event_type, payload FROM event_store WHERE stream_id = ? AND version > ? ORDER BY version",
            (rs, row) -> deserialize(rs.getString("event_type"), rs.getString("payload")),
            streamId, fromVersion
        );
    }
}
```

### EventStoreDB (전용 솔루션)

```java
// EventStoreDB 클라이언트 사용
EventStoreDBClient client = EventStoreDBClient.create(settings);

// 이벤트 추가
EventData event = EventData.builderAsJson(
    "OrderCreated",
    new OrderCreatedEvent(order)
).build();

client.appendToStream("order-" + orderId, event).get();

// 이벤트 읽기
ReadStreamOptions options = ReadStreamOptions.get()
    .fromRevision(StreamRevision.START)
    .forwards();

ReadResult result = client.readStream("order-" + orderId, options).get();
result.getEvents().forEach(resolvedEvent -> {
    // 이벤트 역직렬화 및 재생
});
```

---

## 극한 시나리오

### 시나리오 1: 이벤트 유실

```
문제: Kafka 메시지 유실 → Consumer가 이벤트를 받지 못함

방어:
1. Transactional Outbox Pattern:
   - DB 트랜잭션과 이벤트 저장을 원자적으로
   - Outbox 테이블 → CDC → Kafka (유실 불가)

2. Kafka 설정:
   acks=all: 모든 ISR에 저장 후 ack
   min.insync.replicas=2: 최소 2개 브로커 동기화
   enable.auto.commit=false: 수동 커밋

3. Dead Letter Queue: 처리 실패 이벤트 별도 저장 → 재처리
```

### 시나리오 2: 이벤트 중복 처리 (Exactly-Once)

```java
// 멱등성 Consumer: 같은 이벤트를 여러번 처리해도 결과 동일
@KafkaListener(topics = "order.created")
public void onOrderCreated(OrderCreatedEvent event) {
    // 이미 처리한 이벤트인지 확인
    if (processedEventRepository.exists(event.eventId())) {
        log.info("중복 이벤트 무시: {}", event.eventId());
        return;
    }

    // 처리 + 처리 완료 기록을 하나의 트랜잭션으로
    transactionTemplate.execute(status -> {
        paymentService.initiate(event);
        processedEventRepository.save(event.eventId());
        return null;
    });
}
```

### 시나리오 3: 이벤트 순서 보장

```
문제: Kafka 파티션이 여러 개면 이벤트 순서가 뒤바뀔 수 있음

해결:
1. 같은 집합체(Order)의 이벤트는 같은 파티션으로
   → 파티션 키 = orderId

kafkaTemplate.send(
    new ProducerRecord<>("order-events", orderId.toString(), event)
);

2. 이벤트에 version(sequence number) 포함
   → Consumer가 순서 검증 후 처리

3. Consumer에서 낙관적 잠금
   → version 불일치 시 재처리 큐에 넣음
```

### 시나리오 4: Event Sourcing 이벤트 수정 (과거 변경 불가)

```
문제: 개인정보(이메일) 포함 이벤트를 GDPR로 삭제해야 함
      이벤트는 불변이므로 삭제 불가

해결책:
1. Crypto-shredding: 암호화 키를 사용자별로 관리
   → GDPR 요청 시 키만 삭제 → 이벤트 데이터는 복호화 불가

2. 개인정보를 이벤트 payload에 포함하지 않음
   → 이벤트: userId만 포함
   → 실제 개인정보는 별도 User Service에서 조회 (포인터 방식)

3. 별도 보상 이벤트 발행:
   UserDataDeletedEvent → Projection에서 개인정보 제거
```

---

## EDA vs 요청/응답 비교

| 항목 | 요청/응답 (REST/gRPC) | 이벤트 기반 (EDA) |
|---|---|---|
| 결합도 | 강함 (직접 호출) | 약함 (이벤트 브로커 통해) |
| 응답 방식 | 동기 (즉시 응답) | 비동기 (최종 일관성) |
| 확장성 | 수신자 수에 비례 | 브로커가 분산 처리 |
| 장애 전파 | 수신자 장애 → 발신자 영향 | 수신자 장애 → 이벤트 보관 |
| 디버깅 | 단순 (콜 스택) | 복잡 (분산 추적 필요) |
| 데이터 일관성 | 강한 일관성 가능 | 최종 일관성 |
| 적합한 경우 | 실시간 응답 필요 | 대용량, 느슨한 결합 필요 |
