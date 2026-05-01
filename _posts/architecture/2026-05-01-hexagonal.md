---
title: "헥사고날 아키텍처"
categories: ARCHITECTURE
tags: [Hexagonal Architecture, Port and Adapter, Clean Architecture, DDD]
toc: true
toc_sticky: true
toc_label: 목차
---

## 비유로 시작하기

스마트폰을 생각해보세요. 스마트폰에는 USB-C, 이어폰 잭, Wi-Fi, Bluetooth 등 다양한 **포트(Port)**가 있습니다. 어떤 이어폰이든, 어떤 충전기든 규격만 맞으면 연결됩니다. 스마트폰 내부 회로는 외부 기기가 무엇인지 신경 쓰지 않습니다.

헥사고날 아키텍처(Hexagonal Architecture)는 정확히 이 개념입니다. **비즈니스 로직(Application Core)이 외부 세계(DB, HTTP, 메시지 큐)와 포트와 어댑터를 통해 연결**되며, 코어는 외부 기술에 전혀 의존하지 않습니다.

Alistair Cockburn이 2005년 제안했으며, "Ports and Adapters Architecture"라고도 불립니다.

---

## 핵심 구조

<div class="mermaid">
graph LR
    subgraph EXT_LEFT["외부 세계"]
        HTTP[HTTP Client]
        CLI[CLI]
        TEST[Test]
    end
    subgraph Application Core
        IP[Inbound Port<br>UseCase Interface]
        AS[Application Service]
        OP[Outbound Port<br>Repository Interface]
        DOM[Domain Model]
        AS --> DOM
        IP --> AS
        AS --> OP
    end
    subgraph EXT_RIGHT["외부 세계"]
        DB[(Database)]
        MQ[Message Queue]
        EXT[External API]
    end

    HTTP -->|Inbound Adapter| IP
    CLI -->|Inbound Adapter| IP
    TEST -->|Inbound Adapter| IP
    OP -->|Outbound Adapter| DB
    OP -->|Outbound Adapter| MQ
    OP -->|Outbound Adapter| EXT
</div>

### Port (포트)

포트는 **인터페이스**입니다. 두 종류가 있습니다.

- **Inbound Port (Driving Port)**: 외부가 애플리케이션을 호출하는 인터페이스. `UseCase` 인터페이스
- **Outbound Port (Driven Port)**: 애플리케이션이 외부를 호출하는 인터페이스. `Repository`, `EventPublisher` 인터페이스

### Adapter (어댑터)

어댑터는 **포트의 구현체**입니다.

- **Inbound Adapter**: `@RestController`, `@KafkaListener`, `@Scheduled` — 외부 요청을 포트로 변환
- **Outbound Adapter**: `JpaOrderRepository`, `KafkaEventPublisher` — 포트를 실제 기술로 구현

---

## 의존성 방향

헥사고날 아키텍처의 핵심 규칙:

> **모든 의존성은 Application Core를 향해야 한다**

<div class="mermaid">
graph LR
    A[Web Adapter] -->|depends on| B[Inbound Port]
    B --> C[Application Service]
    C -->|depends on| D[Outbound Port]
    E[DB Adapter] -->|implements| D

    style C fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333
</div>

`Application Service`는 `JpaRepository`를 직접 알지 않습니다. `OrderRepository` 인터페이스(Outbound Port)만 압니다. JPA는 언제든 교체 가능합니다.

---

## Spring에서의 구현

### 패키지 구조

```
com.example.order
├── adapter
│   ├── in
│   │   └── web
│   │       ├── OrderController.java         (Inbound Adapter)
│   │       └── OrderRequest.java            (DTO)
│   └── out
│       ├── persistence
│       │   ├── OrderPersistenceAdapter.java (Outbound Adapter)
│       │   ├── OrderJpaRepository.java
│       │   └── OrderEntity.java
│       └── messaging
│           └── OrderEventPublisher.java     (Outbound Adapter)
├── application
│   ├── port
│   │   ├── in
│   │   │   └── PlaceOrderUseCase.java       (Inbound Port)
│   │   └── out
│   │       ├── OrderRepository.java         (Outbound Port)
│   │       └── EventPublisher.java          (Outbound Port)
│   └── service
│       └── OrderService.java               (Application Service)
└── domain
    ├── Order.java
    ├── OrderItem.java
    └── Money.java
```

### Inbound Port (UseCase)

```java
// application/port/in/PlaceOrderUseCase.java
public interface PlaceOrderUseCase {
    OrderId placeOrder(PlaceOrderCommand command);
}

// Command는 Inbound Port의 입력 모델 (DTO와 분리)
public record PlaceOrderCommand(
    CustomerId customerId,
    List<OrderItemCommand> items
) {
    // 자체 검증 로직 포함
    public PlaceOrderCommand {
        Objects.requireNonNull(customerId, "고객 ID는 필수입니다");
        if (items == null || items.isEmpty()) {
            throw new IllegalArgumentException("주문 항목은 최소 1개 이상이어야 합니다");
        }
    }
}
```

### Application Service

```java
// application/service/OrderService.java
@Service
@RequiredArgsConstructor
@Transactional
public class OrderService implements PlaceOrderUseCase {

    private final OrderRepository orderRepository;     // Outbound Port
    private final EventPublisher eventPublisher;       // Outbound Port
    private final ProductRepository productRepository; // Outbound Port

    @Override
    public OrderId placeOrder(PlaceOrderCommand command) {
        // 1. 도메인 로직
        List<OrderItem> items = command.items().stream()
            .map(item -> {
                Product product = productRepository.findById(item.productId())
                    .orElseThrow(() -> new ProductNotFoundException(item.productId()));
                return new OrderItem(product.getId(), product.getPrice(), item.quantity());
            })
            .toList();

        Order order = Order.create(command.customerId(), items);

        // 2. 영속화 (Outbound Port 호출)
        OrderId savedId = orderRepository.save(order);

        // 3. 이벤트 발행 (Outbound Port 호출)
        eventPublisher.publish(new OrderPlacedEvent(savedId, command.customerId()));

        return savedId;
    }
}
```

### Inbound Adapter (Web)

```java
// adapter/in/web/OrderController.java
@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
public class OrderController {

    private final PlaceOrderUseCase placeOrderUseCase;  // Inbound Port 참조

    @PostMapping
    public ResponseEntity<OrderResponse> placeOrder(@RequestBody @Valid OrderRequest request) {
        PlaceOrderCommand command = OrderRequestMapper.toCommand(request);
        OrderId orderId = placeOrderUseCase.placeOrder(command);
        return ResponseEntity.ok(new OrderResponse(orderId.getValue()));
    }
}
```

컨트롤러는 `OrderService`를 직접 알지 않습니다. `PlaceOrderUseCase` 인터페이스만 압니다.

### Outbound Adapter (Persistence)

```java
// adapter/out/persistence/OrderPersistenceAdapter.java
@Component
@RequiredArgsConstructor
public class OrderPersistenceAdapter implements OrderRepository {

    private final OrderJpaRepository jpaRepository;
    private final OrderMapper mapper;

    @Override
    public OrderId save(Order order) {
        OrderEntity entity = mapper.toEntity(order);
        OrderEntity saved = jpaRepository.save(entity);
        return new OrderId(saved.getId());
    }

    @Override
    public Optional<Order> findById(OrderId id) {
        return jpaRepository.findById(id.getValue())
            .map(mapper::toDomain);
    }
}
```

---

## 테스트 전략

헥사고날 아키텍처의 가장 큰 이점 중 하나는 **테스트 용이성**입니다.

```java
// Application Service 단위 테스트 — DB 불필요
class OrderServiceTest {

    // Mock으로 Outbound Port 구현
    private OrderRepository orderRepository = mock(OrderRepository.class);
    private EventPublisher eventPublisher = mock(EventPublisher.class);
    private ProductRepository productRepository = mock(ProductRepository.class);

    private OrderService orderService = new OrderService(
        orderRepository, eventPublisher, productRepository
    );

    @Test
    void 주문_생성_성공() {
        // given
        given(productRepository.findById(any()))
            .willReturn(Optional.of(new Product(ProductId.of(1L), Money.of(10000))));
        given(orderRepository.save(any()))
            .willReturn(OrderId.of(100L));

        PlaceOrderCommand command = new PlaceOrderCommand(
            CustomerId.of(1L),
            List.of(new OrderItemCommand(ProductId.of(1L), 2))
        );

        // when
        OrderId result = orderService.placeOrder(command);

        // then
        assertThat(result.getValue()).isEqualTo(100L);
        verify(eventPublisher).publish(any(OrderPlacedEvent.class));
    }
}
```

---

## DDD와의 관계

<div class="mermaid">
graph TD
    subgraph DDD + Hexagonal
        subgraph Domain Layer
            E[Entity]
            VO[Value Object]
            AGG[Aggregate]
            DE[Domain Event]
        end
        subgraph Application Layer = Application Core
            UC[Use Case / Application Service]
            IP[Inbound Port]
            OP[Outbound Port]
        end
        subgraph Infrastructure
            WA[Web Adapter]
            PA[Persistence Adapter]
            MA[Messaging Adapter]
        end
    end

    WA --> IP
    IP --> UC
    UC --> E
    UC --> OP
    PA --> OP
    MA --> OP
</div>

- DDD의 **Domain Layer**가 헥사고날의 **Application Core** 내부에 위치
- DDD의 **Repository Interface**가 헥사고날의 **Outbound Port**
- DDD의 **Application Service**가 헥사고날의 **Use Case 구현체**

두 개념은 완벽하게 보완 관계입니다.

---

## 레이어드 아키텍처와 비교

| 항목 | 레이어드 아키텍처 | 헥사고날 아키텍처 |
|------|-----------------|-----------------|
| 의존성 방향 | 위 → 아래 (단방향) | 모두 Core를 향해 |
| DB 교체 용이성 | 어려움 | 쉬움 (Adapter만 교체) |
| 단위 테스트 | DB 없이 하기 어려움 | 쉬움 (Port Mocking) |
| 복잡도 | 낮음 | 높음 |
| 소규모 프로젝트 | 적합 | 과도할 수 있음 |
| 대규모/장수 프로젝트 | 유지보수 어려움 | 적합 |

---

## 극한 시나리오

### 시나리오: 결제 모듈을 Stripe에서 토스페이먼츠로 교체

헥사고날 아키텍처에서:

```java
// Outbound Port (변경 없음)
public interface PaymentGateway {
    PaymentResult charge(PaymentRequest request);
}

// 기존 Stripe Adapter → 제거
class StripePaymentAdapter implements PaymentGateway { ... }

// 새 TossPayments Adapter → 추가
class TossPaymentsAdapter implements PaymentGateway { ... }

// Application Service → 변경 없음
class PaymentService {
    private final PaymentGateway paymentGateway; // 인터페이스만 알고 있음
}
```

**Application Service, Domain 코드는 단 한 줄도 바꾸지 않아도 됩니다.**

레이어드 아키텍처였다면? 서비스 레이어 전반에 걸쳐 Stripe SDK 호출 코드가 퍼져 있어 대규모 수정이 필요합니다.
