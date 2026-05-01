---
title: "분산 트랜잭션"
categories: SPRING
tags: [분산트랜잭션, 2PC, Saga, TCC, Outbox, 마이크로서비스]
toc: true
toc_sticky: true
toc_label: 목차
date: 2026-05-01
---

마이크로서비스 아키텍처에서는 단일 비즈니스 작업이 여러 서비스에 걸쳐 실행된다. 각 서비스는 독립적인 데이터베이스를 가지므로 전통적인 ACID 트랜잭션을 사용할 수 없다. 분산 트랜잭션은 이 문제를 해결하기 위한 다양한 패턴을 다룬다.

---

## 왜 분산 트랜잭션이 어려운가

### 단일 DB에서의 트랜잭션

```
BEGIN;
  INSERT INTO orders ...
  UPDATE inventory SET stock = stock - 1 ...
  INSERT INTO payments ...
COMMIT; -- 또는 ROLLBACK (원자적)
```

### 마이크로서비스에서의 문제

```
[Order Service] → INSERT orders (DB A)
[Inventory Service] → UPDATE inventory (DB B)
[Payment Service] → INSERT payments (DB C)

문제: 세 작업 중 하나가 실패하면?
- DB A는 커밋됨, DB B, C는 롤백 → 데이터 불일치
- 네트워크 장애로 응답을 못 받으면? → 커밋 여부 불명확
```

### CAP 정리

분산 시스템은 CAP(일관성, 가용성, 파티션 내성) 중 2개만 동시에 보장할 수 있다.

| 조합 | 특징 | 예시 |
|------|------|------|
| CP | 일관성 + 파티션 내성 | ZooKeeper, HBase |
| AP | 가용성 + 파티션 내성 | Cassandra, DynamoDB |
| CA | 일관성 + 가용성 | 단일 노드 DB |

마이크로서비스에서는 네트워크 파티션이 불가피하므로 **AP를 선택하고 최종 일관성(Eventual Consistency)**을 추구하는 것이 현실적이다.

---

## 2PC (Two-Phase Commit)

### 동작 방식

2PC는 분산 환경에서 강한 일관성(Strong Consistency)을 제공하려는 프로토콜이다. **코디네이터**가 모든 참여자를 조율한다.

```
Phase 1: Prepare (투표 단계)
  코디네이터 → 모든 참여자에게 "준비되었나?" 질문
  각 참여자  → 로컬 트랜잭션 준비 후 "Yes" 또는 "No" 응답

Phase 2: Commit/Rollback (결정 단계)
  모든 참여자가 "Yes" → 코디네이터가 Commit 명령
  하나라도 "No"      → 코디네이터가 Rollback 명령
```

```
[코디네이터]
    │── Prepare → [Order DB]   → Yes
    │── Prepare → [Inventory DB] → Yes
    │── Prepare → [Payment DB]  → Yes
    │
    │── Commit  → [Order DB]
    │── Commit  → [Inventory DB]
    └── Commit  → [Payment DB]
```

### 2PC의 문제점

**1. 동기 블로킹**
- Phase 1과 Phase 2 사이에 모든 참여자가 락을 보유한 채 대기
- 코디네이터 장애 시 참여자들이 무한 대기 가능

**2. 단일 실패 지점**
- 코디네이터가 장애나면 전체가 중단됨

**3. 성능 저하**
- 모든 서비스가 응답할 때까지 대기 → 지연 시간이 가장 느린 서비스에 종속

**4. 마이크로서비스와 맞지 않음**
- 각 서비스가 독립적으로 배포되고 장애가 발생할 수 있는 환경에서 강한 결합을 만듦

### 언제 사용하는가

- 동일 데이터베이스 내의 XA 트랜잭션 (여러 DB 벤더를 하나의 트랜잭션으로)
- 레거시 시스템 연동
- 강한 일관성이 반드시 필요하고 성능 저하를 감수할 수 있을 때

```java
// Spring JTA + XA 트랜잭션 (2PC)
@Configuration
public class XaDataSourceConfig {

    @Bean
    @Primary
    public XADataSource orderXaDataSource() {
        MysqlXADataSource ds = new MysqlXADataSource();
        ds.setUrl("jdbc:mysql://order-db:3306/orders");
        return ds;
    }

    @Bean
    public XADataSource inventoryXaDataSource() {
        MysqlXADataSource ds = new MysqlXADataSource();
        ds.setUrl("jdbc:mysql://inventory-db:3306/inventory");
        return ds;
    }
}

@Service
@Transactional  // JTA가 2PC로 여러 DB에 걸쳐 트랜잭션 처리
public class OrderService {
    public void placeOrder(OrderRequest request) {
        orderRepository.save(...);       // order DB
        inventoryRepository.update(...); // inventory DB
        // 2PC로 양쪽 모두 커밋 또는 롤백
    }
}
```

---

## 3PC (Three-Phase Commit)

2PC의 코디네이터 단일 실패 지점 문제를 개선한 프로토콜이다. Phase 1(CanCommit) → Phase 2(PreCommit) → Phase 3(Commit) 3단계로 나뉜다.

**한계**: 실제로는 네트워크 파티션 상황에서도 완벽하지 않고, 복잡도 대비 이점이 크지 않아 실무에서 거의 사용하지 않는다.

---

## Saga 패턴

Saga는 **각 서비스의 로컬 트랜잭션 + 실패 시 보상 트랜잭션(Compensating Transaction)**으로 분산 트랜잭션을 구현한다. 강한 일관성 대신 **최종 일관성**을 목표로 한다.

### 보상 트랜잭션이란

```
주문 생성 → 재고 차감 → 결제
              ↑ 결제 실패
재고 복원 (보상) ← 주문 취소 (보상)
```

각 단계가 실패하면 **이미 완료된 단계를 되돌리는** 보상 트랜잭션을 실행한다.

---

### Choreography (코레오그래피) Saga

중앙 오케스트레이터 없이 **이벤트를 통해 각 서비스가 자율적으로 참여**한다.

```
[Order Service]
  1. 주문 생성 → "OrderCreated" 이벤트 발행

[Inventory Service]
  2. "OrderCreated" 수신 → 재고 차감 → "InventoryReserved" 발행
  (실패 시) "InventoryReservationFailed" 발행

[Payment Service]
  3. "InventoryReserved" 수신 → 결제 처리 → "PaymentCompleted" 발행
  (실패 시) "PaymentFailed" 발행

[Order Service]
  4. "PaymentCompleted" 수신 → 주문 확정
  (실패 이벤트 수신 시) → 주문 취소 + 보상 이벤트 발행

[Inventory Service]
  5. 주문 취소 이벤트 수신 → 재고 복원 (보상)
```

**장점**: 느슨한 결합, 단순한 구현, 중앙 실패 지점 없음

**단점**: 전체 흐름 파악 어려움, 이벤트 추적 복잡, 테스트 어려움

---

### Orchestration (오케스트레이션) Saga

**중앙 오케스트레이터(Saga Orchestrator)**가 전체 흐름을 제어한다.

```
[Saga Orchestrator]
  1. Order Service에 "주문 생성" 명령
  2. 성공 응답 수신
  3. Inventory Service에 "재고 차감" 명령
  4. 성공 응답 수신
  5. Payment Service에 "결제 처리" 명령
  6. 실패 응답 수신
  7. Inventory Service에 "재고 복원" 명령 (보상)
  8. Order Service에 "주문 취소" 명령 (보상)
```

**장점**: 전체 흐름이 한곳에 집중 → 이해하고 모니터링하기 쉬움

**단점**: 오케스트레이터가 단일 실패 지점, 서비스 간 결합도 증가

**Spring State Machine으로 구현**
```java
@Component
@RequiredArgsConstructor
public class OrderSagaOrchestrator {

    private final OrderServiceClient orderServiceClient;
    private final InventoryServiceClient inventoryServiceClient;
    private final PaymentServiceClient paymentServiceClient;

    public SagaResult executeOrderSaga(OrderRequest request) {
        Long orderId = null;
        boolean inventoryReserved = false;

        try {
            // Step 1: 주문 생성
            orderId = orderServiceClient.createOrder(request);

            // Step 2: 재고 차감
            inventoryServiceClient.reserveInventory(request.productId(), request.quantity());
            inventoryReserved = true;

            // Step 3: 결제
            paymentServiceClient.processPayment(request.userId(), request.amount());

            return SagaResult.success(orderId);

        } catch (PaymentFailedException e) {
            // 보상: 재고 복원 + 주문 취소
            if (inventoryReserved) {
                inventoryServiceClient.releaseInventory(request.productId(), request.quantity());
            }
            if (orderId != null) {
                orderServiceClient.cancelOrder(orderId);
            }
            return SagaResult.failure("결제 실패");

        } catch (InventoryException e) {
            // 보상: 주문 취소
            if (orderId != null) {
                orderServiceClient.cancelOrder(orderId);
            }
            return SagaResult.failure("재고 부족");
        }
    }
}
```

---

## TCC (Try-Confirm-Cancel)

TCC는 각 서비스의 비즈니스 로직을 Try / Confirm / Cancel 3단계로 분리한다.

```
Try:     리소스 예약 (잠금/임시 차감)
Confirm: 예약 확정 (실제 처리)
Cancel:  예약 취소 (원상 복구)
```

### 동작 흐름

```
[Phase 1: Try]
  Order Service:     주문 초안 생성 (status=PENDING)
  Inventory Service: 재고 10개 임시 차감 (reserved_qty += 10)
  Payment Service:   결제 금액 임시 잠금 (hold_amount = 50000)

[Phase 2: Confirm (모두 Try 성공)]
  Order Service:     주문 확정 (status=CONFIRMED)
  Inventory Service: 임시 차감 확정 (actual_qty -= 10)
  Payment Service:   잠금 금액 실제 차감

[Phase 2: Cancel (하나라도 Try 실패)]
  Order Service:     주문 초안 삭제
  Inventory Service: 임시 차감 복원 (reserved_qty -= 10)
  Payment Service:   잠금 금액 해제
```

### 구현 예시

```java
// Inventory Service - TCC 인터페이스
@Service
public class InventoryTccService {

    // Try: 재고 임시 차감
    @Transactional
    public String tryReserve(Long productId, int quantity) {
        Product product = productRepository.findByIdWithLock(productId);

        if (product.getAvailableStock() < quantity) {
            throw new InsufficientStockException();
        }

        // 가용 재고 감소, 예약 재고 증가
        product.reserve(quantity);

        String reservationId = UUID.randomUUID().toString();
        Reservation reservation = new Reservation(reservationId, productId, quantity, ReservationStatus.PENDING);
        reservationRepository.save(reservation);

        return reservationId;
    }

    // Confirm: 예약 확정
    @Transactional
    public void confirm(String reservationId) {
        Reservation reservation = reservationRepository.findById(reservationId).orElseThrow();
        reservation.confirm();
        // 예약 재고를 실제 차감으로 전환
        Product product = productRepository.findById(reservation.getProductId()).orElseThrow();
        product.confirmReservation(reservation.getQuantity());
    }

    // Cancel: 예약 취소
    @Transactional
    public void cancel(String reservationId) {
        Reservation reservation = reservationRepository.findById(reservationId).orElse(null);
        if (reservation == null || reservation.isCancelled()) return; // 멱등성 보장

        reservation.cancel();
        Product product = productRepository.findById(reservation.getProductId()).orElseThrow();
        product.releaseReservation(reservation.getQuantity());
    }
}
```

**TCC vs Saga 비교**

| 항목 | TCC | Saga |
|------|-----|------|
| 일관성 수준 | 준강한 일관성 | 최종 일관성 |
| 데이터 가시성 | 임시 상태 외부 노출 안 함 | 중간 상태 노출될 수 있음 |
| 구현 복잡도 | 높음 (Try/Confirm/Cancel 분리) | 중간 |
| 성능 | 2PC보다 좋음 | 좋음 |
| 실패 복구 | Confirm/Cancel | 보상 트랜잭션 |

---

## Outbox Pattern

Saga와 이벤트 기반 아키텍처에서 **"서비스 로컬 DB에 저장 + 이벤트 발행"의 원자성**을 보장하는 패턴이다.

### 문제

```java
@Transactional
public void placeOrder(OrderRequest request) {
    Order order = orderRepository.save(Order.from(request)); // DB 저장 성공
    eventPublisher.publish(new OrderCreatedEvent(order));    // 이벤트 발행 실패?
    // DB는 커밋됐는데 이벤트가 안 나감 → 재고가 차감 안 됨 → 불일치
}
```

### Outbox 패턴 해결책

```
[Order Service DB]
  orders 테이블: 주문 저장
  outbox 테이블: 발행할 이벤트 저장
  → 하나의 로컬 트랜잭션으로 함께 저장 (원자적)

[Message Relay / Debezium]
  outbox 테이블을 주기적으로 폴링 또는 CDC로 감시
  → 미발행 이벤트를 Kafka/RabbitMQ에 발행
  → 성공 시 outbox 레코드 삭제 또는 상태 변경
```

```java
@Entity
@Table(name = "outbox_events")
public class OutboxEvent {
    @Id
    private String id;
    private String aggregateType;  // "Order"
    private String aggregateId;    // orderId
    private String eventType;      // "OrderCreated"
    private String payload;        // JSON
    private LocalDateTime createdAt;
    private boolean published;
}

@Service
@RequiredArgsConstructor
public class OrderService {

    private final OrderRepository orderRepository;
    private final OutboxEventRepository outboxEventRepository;
    private final ObjectMapper objectMapper;

    @Transactional
    public Order placeOrder(OrderRequest request) {
        Order order = orderRepository.save(Order.from(request));

        // 같은 트랜잭션에서 outbox 저장 → 원자적
        OutboxEvent outboxEvent = OutboxEvent.builder()
            .id(UUID.randomUUID().toString())
            .aggregateType("Order")
            .aggregateId(String.valueOf(order.getId()))
            .eventType("OrderCreated")
            .payload(objectMapper.writeValueAsString(new OrderCreatedEvent(order)))
            .createdAt(LocalDateTime.now())
            .published(false)
            .build();

        outboxEventRepository.save(outboxEvent);
        return order;
    }
}

// Relay: outbox를 폴링해서 Kafka에 발행
@Component
@RequiredArgsConstructor
public class OutboxEventRelay {

    private final OutboxEventRepository outboxEventRepository;
    private final KafkaTemplate<String, String> kafkaTemplate;

    @Scheduled(fixedDelay = 1000)
    @Transactional
    public void relay() {
        List<OutboxEvent> events = outboxEventRepository.findByPublishedFalse();
        for (OutboxEvent event : events) {
            kafkaTemplate.send(event.getEventType(), event.getAggregateId(), event.getPayload());
            event.setPublished(true);
        }
    }
}
```

**Debezium CDC 방식 (권장)**
```yaml
# Debezium Source Connector 설정
{
  "name": "order-outbox-connector",
  "config": {
    "connector.class": "io.debezium.connector.mysql.MySqlConnector",
    "database.hostname": "order-db",
    "database.include.list": "orders",
    "table.include.list": "orders.outbox_events",
    "transforms": "outbox",
    "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter"
  }
}
```

---

## 실무 선택 가이드

```
[강한 일관성이 필요한가?]
  YES → 같은 DB를 사용하도록 서비스 경계 재설계 고려
         또는 XA + 2PC (성능 저하 감수)

[최종 일관성으로 가능한가?]
  YES → Saga 패턴 선택

[Saga 선택 기준]
  서비스 수가 적고 흐름이 단순  → Choreography (이벤트 기반)
  흐름이 복잡하고 가시성 필요   → Orchestration

[이벤트 발행 원자성 필요]
  YES → Outbox Pattern 반드시 적용

[임시 데이터 외부 노출 불가]
  YES → TCC 패턴 (Try로 격리, Confirm으로 확정)

[실무 가장 많이 쓰는 조합]
  Saga(Choreography) + Kafka + Outbox Pattern
  또는
  Saga(Orchestration) + Kafka + Outbox Pattern
```

### 패턴별 특성 비교

| 항목 | 2PC | Saga Choreography | Saga Orchestration | TCC |
|------|-----|-------------------|--------------------|-----|
| 일관성 | 강한 | 최종 | 최종 | 준강한 |
| 가용성 | 낮음 | 높음 | 높음 | 중간 |
| 복잡도 | 낮음 | 중간 | 중간 | 높음 |
| 성능 | 낮음 | 높음 | 높음 | 중간 |
| 디버깅 | 쉬움 | 어려움 | 중간 | 중간 |
| 서비스 결합도 | 높음 | 낮음 | 중간 | 중간 |

---

## 마치며

분산 트랜잭션에는 완벽한 해결책이 없다. 각 패턴은 일관성, 가용성, 복잡도 사이의 트레이드오프를 갖는다. 실무에서는 대부분 **Saga + Outbox Pattern** 조합을 사용한다. 강한 일관성이 진짜 필요한지 다시 검토하고, 가능하면 서비스 경계를 재설계해 단일 트랜잭션으로 처리할 수 있도록 하는 것이 최선이다.
