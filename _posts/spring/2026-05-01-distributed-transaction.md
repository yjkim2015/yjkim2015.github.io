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

> 비유: 여러 은행 계좌 간 이체와 같다. A 은행에서 출금하고 B 은행에 입금할 때 중간에 네트워크가 끊기면 출금만 되고 입금이 안 될 수 있다. 각 은행(서비스)이 독립적이라 한쪽이 실패해도 다른 쪽을 자동으로 되돌릴 수 없다.

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

<div class="mermaid">
graph LR
    OS["Order Service\nINSERT orders — DB A"]
    IS["Inventory Service\nUPDATE inventory — DB B"]
    PS["Payment Service\nINSERT payments — DB C"]
    FAIL["하나라도 실패하면?\nDB A 커밋됨, DB B·C 롤백\n→ 데이터 불일치"]
    OS --> IS --> PS --> FAIL
</div>

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

| 단계 | 동작 |
|------|------|
| Phase 1: Prepare (투표) | 코디네이터가 모든 참여자에게 "준비됐나?" 질문 → 각 참여자가 로컬 트랜잭션 준비 후 Yes/No 응답 |
| Phase 2: Commit/Rollback (결정) | 모든 참여자 Yes → Commit 명령 / 하나라도 No → Rollback 명령 |

<div class="mermaid">
sequenceDiagram
    participant CO as 코디네이터
    participant ODB as Order DB
    participant IDB as Inventory DB
    participant PDB as Payment DB

    Note over CO,PDB: Phase 1 - Prepare (투표)
    CO->>ODB: Prepare
    ODB-->>CO: Yes
    CO->>IDB: Prepare
    IDB-->>CO: Yes
    CO->>PDB: Prepare
    PDB-->>CO: Yes

    Note over CO,PDB: Phase 2 - Commit (결정)
    CO->>ODB: Commit
    CO->>IDB: Commit
    CO->>PDB: Commit
</div>

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

> 비유: 여행 예약과 같다. 항공권 예약 → 호텔 예약 → 렌터카 예약 중 렌터카가 실패하면, 이미 예약한 호텔과 항공권을 취소(보상)해야 한다.

<div class="mermaid">
graph LR
    A["주문 생성"] --> B["재고 차감"] --> C["결제"]
    C -->|결제 실패| D["주문 취소 보상"]
    D --> E["재고 복원 보상"]
</div>

각 단계가 실패하면 **이미 완료된 단계를 되돌리는** 보상 트랜잭션을 실행한다.

---

### Choreography (코레오그래피) Saga

중앙 오케스트레이터 없이 **이벤트를 통해 각 서비스가 자율적으로 참여**한다.

<div class="mermaid">
sequenceDiagram
    participant OS as Order Service
    participant IS as Inventory Service
    participant PS as Payment Service

    OS->>OS: 주문 생성
    OS-->>IS: OrderCreated 이벤트 발행
    IS->>IS: 재고 차감
    IS-->>PS: InventoryReserved 발행
    Note over IS: 실패 시 InventoryReservationFailed 발행
    PS->>PS: 결제 처리
    PS-->>OS: PaymentCompleted 발행
    Note over PS: 실패 시 PaymentFailed 발행
    OS->>OS: 주문 확정
    Note over OS: 실패 이벤트 수신 시 주문 취소 + 보상 이벤트 발행
    OS-->>IS: 주문 취소 이벤트
    IS->>IS: 재고 복원 (보상)
</div>

**장점**: 느슨한 결합, 단순한 구현, 중앙 실패 지점 없음

**단점**: 전체 흐름 파악 어려움, 이벤트 추적 복잡, 테스트 어려움

---

### Orchestration (오케스트레이션) Saga

**중앙 오케스트레이터(Saga Orchestrator)**가 전체 흐름을 제어한다.

<div class="mermaid">
sequenceDiagram
    participant SO as Saga Orchestrator
    participant OS as Order Service
    participant IS as Inventory Service
    participant PS as Payment Service

    SO->>OS: 주문 생성 명령
    OS-->>SO: 성공 응답
    SO->>IS: 재고 차감 명령
    IS-->>SO: 성공 응답
    SO->>PS: 결제 처리 명령
    PS-->>SO: 실패 응답
    Note over SO: 보상 트랜잭션 시작
    SO->>IS: 재고 복원 명령 (보상)
    SO->>OS: 주문 취소 명령 (보상)
</div>

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

> 비유: 음식점 예약과 같다. Try(자리 임시 예약) → Confirm(당일 확정 입장) / Cancel(예약 취소). 자리를 실제로 점유하기 전에 먼저 확보해두고, 전체 조건이 맞으면 확정한다.

| 단계 | 동작 |
|------|------|
| Try | 리소스 예약 — 잠금/임시 차감 |
| Confirm | 예약 확정 — 실제 처리 |
| Cancel | 예약 취소 — 원상 복구 |

### 동작 흐름

<div class="mermaid">
sequenceDiagram
    participant CO as Coordinator
    participant OS as Order Service
    participant IS as Inventory Service
    participant PS as Payment Service

    Note over CO,PS: Phase 1 - Try (리소스 예약)
    CO->>OS: Try - 주문 초안 생성 (PENDING)
    CO->>IS: Try - 재고 10개 임시 차감 (reserved_qty += 10)
    CO->>PS: Try - 결제 금액 임시 잠금 (hold_amount = 50000)

    alt 모두 Try 성공
        Note over CO,PS: Phase 2 - Confirm (확정)
        CO->>OS: Confirm - 주문 확정 (CONFIRMED)
        CO->>IS: Confirm - 임시 차감 확정 (actual_qty -= 10)
        CO->>PS: Confirm - 잠금 금액 실제 차감
    else 하나라도 Try 실패
        Note over CO,PS: Phase 2 - Cancel (취소)
        CO->>OS: Cancel - 주문 초안 삭제
        CO->>IS: Cancel - 임시 차감 복원 (reserved_qty -= 10)
        CO->>PS: Cancel - 잠금 금액 해제
    end
</div>

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

<div class="mermaid">
graph TD
    subgraph OS["Order Service"]
        T["로컬 트랜잭션 (원자적)"]
        T --> OT[orders 테이블에 주문 저장]
        T --> OB[outbox 테이블에 이벤트 저장]
    end
    subgraph RELAY["Message Relay / Debezium"]
        P["outbox 폴링 또는 CDC 감시"]
        P --> PUB["Kafka/RabbitMQ에 미발행 이벤트 발행"]
        PUB --> DEL["outbox 레코드 삭제 또는 상태 변경"]
    end
    OB --> P
</div>

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

<div class="mermaid">
graph TD
    START([시작]) --> Q1{강한 일관성이 필요한가?}
    Q1 -->|YES| R1["같은 DB로 경계 재설계<br>또는 XA + 2PC"]
    Q1 -->|NO| Q2{최종 일관성으로 가능한가?}
    Q2 -->|YES| SAGA[Saga 패턴 선택]
    SAGA --> Q3{흐름이 단순한가?}
    Q3 -->|YES| CHOREO["Choreography<br>(이벤트 기반)"]
    Q3 -->|NO| ORCH["Orchestration<br>(중앙 오케스트레이터)"]
    SAGA --> Q4{이벤트 발행 원자성 필요?}
    Q4 -->|YES| OUTBOX[Outbox Pattern 적용]
    SAGA --> Q5{임시 데이터 외부 노출 불가?}
    Q5 -->|YES| TCC["TCC 패턴<br>(Try/Confirm/Cancel)"]
    OUTBOX --> BEST["실무 권장 조합<br>Saga + Kafka + Outbox"]
    style BEST fill:#8f8,stroke:#080,color:#000
    style R1 fill:#f88,stroke:#c00,color:#000
</div>

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
