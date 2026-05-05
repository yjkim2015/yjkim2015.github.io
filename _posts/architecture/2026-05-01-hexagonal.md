---
title: "헥사고날 아키텍처"
categories: ARCHITECTURE
tags: [Hexagonal Architecture, Port and Adapter, Clean Architecture, DDD]
toc: true
toc_sticky: true
toc_label: 목차
---

> **한 줄 요약**: 헥사고날 아키텍처는 비즈니스 로직을 외부 기술(DB, HTTP, 메시지 큐)로부터 완전히 격리하여, 기술 교체와 테스트를 쉽게 만드는 구조다.

## 비유로 시작하기

스마트폰을 생각해보세요. 스마트폰에는 USB-C, 이어폰 잭, Wi-Fi, Bluetooth 등 다양한 **포트(Port)**가 있습니다. 어떤 이어폰이든, 어떤 충전기든 규격만 맞으면 연결됩니다. 스마트폰 내부 회로(비즈니스 로직)는 외부 기기가 무엇인지 신경 쓰지 않습니다.

헥사고날 아키텍처는 정확히 이 개념입니다. **비즈니스 로직(Application Core)이 외부 세계(DB, HTTP, 메시지 큐)와 포트와 어댑터를 통해 연결**되며, 코어는 외부 기술에 전혀 의존하지 않습니다.

Alistair Cockburn이 2005년 제안했으며, "Ports and Adapters Architecture"라고도 불립니다.

---

## 왜 헥사고날 아키텍처가 필요한가?

### 전통적 레이어드 아키텍처의 문제

```
레이어드 아키텍처에서 흔히 발생하는 문제:

1. DB 교체가 불가능에 가까움
   Service → JpaRepository (직접 의존)
   → JPA를 MongoDB로 바꾸려면 Service 코드 전체 수정

2. 단위 테스트 시 DB 필요
   OrderService 테스트 → 실제 DB 필요 (느린 통합 테스트)
   → 테스트 실행에 수분 소요, CI/CD 병목

3. 외부 API 변경 시 비즈니스 로직 수정
   결제 로직 안에 Stripe SDK 직접 호출
   → 토스페이먼츠로 교체 시 비즈니스 로직까지 변경
```

### 헥사고날이 해결하는 방법

```
핵심 원칙: "비즈니스 로직은 외부 세계를 모른다"

Port(인터페이스)로 경계를 만들고,
Adapter(구현체)가 기술을 다룬다.
비즈니스 로직은 Port만 바라본다.

→ JPA → MongoDB 교체: Adapter만 새로 작성
→ 단위 테스트: Port를 Mock으로 대체 (DB 불필요)
→ 결제사 교체: PaymentGateway(Port) 구현체만 교체
```

---

## 핵심 구조

```mermaid
graph LR
    subgraph DRIVING["외부 세계 (Driving Side)"]
        HTTP["HTTP Client\nREST 요청"]
        CLI["CLI\n배치 작업"]
        TEST["Test\n단위/통합"]
    end

    subgraph CORE["Application Core (비즈니스 로직)"]
        direction TB
        IP["Inbound Port\nUseCase Interface\n(what을 정의)"]
        AS["Application Service\n(UseCase 구현)"]
        DOM["Domain Model\nEntity, VO, Aggregate"]
        OP["Outbound Port\nRepository Interface\n(what을 정의)"]
        IP --> AS
        AS --> DOM
        AS --> OP
    end

    subgraph DRIVEN["외부 세계 (Driven Side)"]
        DB[("Database\nMySQL/MongoDB")]
        MQ["Message Queue\nKafka/RabbitMQ"]
        EXT["External API\nPG사, 배송사"]
    end

    HTTP -->|"Inbound Adapter\n(Controller)"| IP
    CLI -->|"Inbound Adapter\n(BatchRunner)"| IP
    TEST -->|"Inbound Adapter\n(Test)"| IP
    OP -->|"Outbound Adapter\n(JpaRepository)"| DB
    OP -->|"Outbound Adapter\n(KafkaPublisher)"| MQ
    OP -->|"Outbound Adapter\n(StripeClient)"| EXT

    classDef core fill:#E8D5E8,stroke:#9B59B6,stroke-width:3px
    classDef port fill:#D5E8D4,stroke:#82B366,stroke-width:2px
    classDef adapter fill:#DAE8FC,stroke:#6C8EBF
    classDef external fill:#FFF2CC,stroke:#D6B656

    class AS,DOM core
    class IP,OP port
    class HTTP,CLI,TEST,DB,MQ,EXT external
```

---

## Port와 Adapter 상세

### Port (포트) — 인터페이스

포트는 **인터페이스**입니다. "무엇을 할 수 있는가"만 정의하고, "어떻게 하는가"는 모릅니다.

| 종류 | 방향 | 역할 | 예시 |
|------|------|------|------|
| Inbound Port (Driving) | 외부 → Core | 외부가 애플리케이션을 호출하는 계약 | `PlaceOrderUseCase` |
| Outbound Port (Driven) | Core → 외부 | 애플리케이션이 외부를 호출하는 계약 | `OrderRepository`, `EventPublisher` |

### Adapter (어댑터) — 구현체

어댑터는 **포트의 구현체**입니다. 포트(인터페이스)를 실제 기술로 연결합니다.

| 종류 | 예시 |
|------|------|
| Inbound Adapter | `@RestController`, `@KafkaListener`, `@Scheduled`, `@GrpcService` |
| Outbound Adapter | `JpaOrderRepository`, `KafkaEventPublisher`, `StripePaymentAdapter` |

---

## 의존성 방향

헥사고날 아키텍처의 핵심 규칙:

> **모든 의존성은 Application Core를 향해야 한다**

```mermaid
graph LR
    WA["Web Adapter\n(Controller)"]
    IP["Inbound Port\n(UseCase Interface)"]
    AS["Application Service"]
    OP["Outbound Port\n(Repository Interface)"]
    DA["DB Adapter\n(JpaRepository)"]

    WA -->|"1️⃣ depends on"| IP
    IP -->|"2️⃣ implemented by"| AS
    AS -->|"3️⃣ depends on"| OP
    DA -->|"4️⃣ implements"| OP

    classDef core fill:#E8D5E8,stroke:#9B59B6,stroke-width:2px
    classDef port fill:#D5E8D4,stroke:#82B366
    classDef adapter fill:#DAE8FC,stroke:#6C8EBF

    class AS core
    class IP,OP port
    class WA,DA adapter
```

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
│   │       └── OrderRequest.java            (Web DTO)
│   └── out
│       ├── persistence
│       │   ├── OrderPersistenceAdapter.java (Outbound Adapter)
│       │   ├── OrderJpaRepository.java      (Spring Data JPA)
│       │   └── OrderEntity.java             (JPA Entity)
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
    ├── Order.java                           (Aggregate Root)
    ├── OrderItem.java                       (Entity)
    └── Money.java                           (Value Object)
```

### 1단계: Inbound Port (UseCase 인터페이스)

```java
// application/port/in/PlaceOrderUseCase.java
// "주문을 접수할 수 있다" - 외부에게 제공하는 기능 계약
public interface PlaceOrderUseCase {
    OrderId placeOrder(PlaceOrderCommand command);
}

// Command: Inbound Port의 입력 모델 (HTTP DTO와 분리)
// 자체 검증 로직 포함 - 항상 유효한 상태로 Application Service에 전달
public record PlaceOrderCommand(
    CustomerId customerId,
    List<OrderItemCommand> items
) {
    public PlaceOrderCommand {
        Objects.requireNonNull(customerId, "고객 ID는 필수입니다");
        if (items == null || items.isEmpty()) {
            throw new IllegalArgumentException("주문 항목은 최소 1개 이상이어야 합니다");
        }
    }
}
```

### 2단계: Application Service (UseCase 구현)

```java
// application/service/OrderService.java
// Application Core - 비즈니스 로직의 중심
// JPA, Kafka, HTTP 등 기술 의존성 없음 - 인터페이스만 사용
@Service
@RequiredArgsConstructor
@Transactional
public class OrderService implements PlaceOrderUseCase {

    private final OrderRepository orderRepository;     // Outbound Port (인터페이스)
    private final EventPublisher eventPublisher;       // Outbound Port (인터페이스)
    private final ProductRepository productRepository; // Outbound Port (인터페이스)

    @Override
    public OrderId placeOrder(PlaceOrderCommand command) {
        // 1. 도메인 로직: 상품 조회 (어떻게 조회하는지는 모름)
        List<OrderItem> items = command.items().stream()
            .map(item -> {
                Product product = productRepository.findById(item.productId())
                    .orElseThrow(() -> new ProductNotFoundException(item.productId()));
                return new OrderItem(product.getId(), product.getPrice(), item.quantity());
            })
            .toList();

        // 2. 도메인 로직: 주문 생성 (Order Aggregate)
        Order order = Order.create(command.customerId(), items);

        // 3. 영속화 (DB가 무엇인지 모름 - Outbound Port 호출)
        OrderId savedId = orderRepository.save(order);

        // 4. 이벤트 발행 (Kafka인지 RabbitMQ인지 모름 - Outbound Port 호출)
        eventPublisher.publish(new OrderPlacedEvent(savedId, command.customerId()));

        return savedId;
    }
}
```

### 3단계: Inbound Adapter (Web Controller)

```java
// adapter/in/web/OrderController.java
// HTTP 요청을 Application Core로 전달하는 어댑터
@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
public class OrderController {

    // 중요: OrderService가 아닌 PlaceOrderUseCase(인터페이스)를 주입
    // OrderService 구현체가 바뀌어도 Controller는 변경 없음
    private final PlaceOrderUseCase placeOrderUseCase;

    @PostMapping
    public ResponseEntity<OrderResponse> placeOrder(
            @RequestBody @Valid OrderRequest request) {
        // HTTP DTO → Command 변환 (Adapter 책임)
        PlaceOrderCommand command = OrderRequestMapper.toCommand(request);
        OrderId orderId = placeOrderUseCase.placeOrder(command);
        return ResponseEntity.ok(new OrderResponse(orderId.getValue()));
    }
}
```

### 4단계: Outbound Adapter (Persistence)

```java
// adapter/out/persistence/OrderPersistenceAdapter.java
// OrderRepository(Port)를 JPA로 구현한 어댑터
@Component
@RequiredArgsConstructor
public class OrderPersistenceAdapter implements OrderRepository {

    private final OrderJpaRepository jpaRepository; // Spring Data JPA
    private final OrderMapper mapper;

    @Override
    public OrderId save(Order order) {
        // Domain Entity → JPA Entity 변환 후 저장
        OrderEntity entity = mapper.toEntity(order);
        OrderEntity saved = jpaRepository.save(entity);
        return new OrderId(saved.getId());
    }

    @Override
    public Optional<Order> findById(OrderId id) {
        return jpaRepository.findById(id.getValue())
            .map(mapper::toDomain);  // JPA Entity → Domain Entity 변환
    }
}
```

---

## 테스트 전략

헥사고날 아키텍처의 가장 큰 이점 중 하나는 **테스트 용이성**입니다.

```mermaid
graph TD
    subgraph "테스트 레벨"
        UT["단위 테스트\nApplication Service\nDB 불필요, Port Mock 사용\n빠름 (ms 단위)"]
        IT["통합 테스트\nAdapter 레벨\nDB/Kafka 실제 사용\n중간 속도"]
        E2E["E2E 테스트\nHTTP 요청 → DB 확인\n전체 플로우 검증\n느림"]
    end

    UT -->|"70%"| IT
    IT -->|"20%"| E2E

    classDef ut fill:#D5E8D4,stroke:#82B366
    classDef it fill:#FFF2CC,stroke:#D6B656
    classDef e2e fill:#F8CECC,stroke:#B85450

    class UT ut
    class IT it
    class E2E e2e
```

```java
// Application Service 단위 테스트 — DB, Kafka 불필요
// Port를 Mock으로 대체하여 순수 비즈니스 로직만 테스트
class OrderServiceTest {

    // Outbound Port를 Mock으로 대체 (JPA, Kafka 코드 실행 없음)
    private OrderRepository orderRepository = mock(OrderRepository.class);
    private EventPublisher eventPublisher = mock(EventPublisher.class);
    private ProductRepository productRepository = mock(ProductRepository.class);

    // new 로 직접 생성 - Spring Context 불필요 (테스트 속도 10배 빠름)
    private OrderService orderService = new OrderService(
        orderRepository, eventPublisher, productRepository
    );

    @Test
    void 주문_생성_성공() {
        // given: 상품이 존재하고 저장이 성공한다고 가정
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

        // then: 결과 검증 + 이벤트 발행 검증
        assertThat(result.getValue()).isEqualTo(100L);
        verify(eventPublisher).publish(any(OrderPlacedEvent.class));
    }

    @Test
    void 존재하지_않는_상품_주문_시_예외() {
        // given: 상품이 없음
        given(productRepository.findById(any())).willReturn(Optional.empty());

        PlaceOrderCommand command = new PlaceOrderCommand(
            CustomerId.of(1L),
            List.of(new OrderItemCommand(ProductId.of(999L), 1))
        );

        // when & then: 예외 발생 검증
        assertThatThrownBy(() -> orderService.placeOrder(command))
            .isInstanceOf(ProductNotFoundException.class);

        // 상품이 없으면 저장, 이벤트 발행 없어야 함
        verifyNoInteractions(orderRepository, eventPublisher);
    }
}
```

---

## DDD와의 관계

```mermaid
graph TD
    subgraph "DDD + 헥사고날 통합"
        subgraph "Domain Layer (헥사고날 Core 내부)"
            E["Entity\nOrder, OrderItem"]
            VO["Value Object\nMoney, Address"]
            AGG["Aggregate\nOrder Root"]
            DE["Domain Event\nOrderPlacedEvent"]
        end

        subgraph "Application Layer = Application Core"
            UC["UseCase\nApplication Service"]
            IP["Inbound Port\nPlaceOrderUseCase"]
            OP["Outbound Port\nOrderRepository"]
        end

        subgraph "Infrastructure (Adapter)"
            WA["Web Adapter\n@RestController"]
            PA["Persistence Adapter\nJpaRepository"]
            MA["Messaging Adapter\nKafkaPublisher"]
        end
    end

    WA -->|"HTTP 요청 전달"| IP
    IP -->|"구현"| UC
    UC -->|"도메인 로직 실행"| E
    UC -->|"인터페이스 호출"| OP
    PA -->|"구현"| OP
    MA -->|"구현"| OP

    classDef domain fill:#E8D5E8,stroke:#9B59B6
    classDef app fill:#D5E8D4,stroke:#82B366
    classDef infra fill:#DAE8FC,stroke:#6C8EBF

    class E,VO,AGG,DE domain
    class UC,IP,OP app
    class WA,PA,MA infra
```

- DDD의 **Domain Layer**가 헥사고날의 **Application Core** 내부에 위치
- DDD의 **Repository Interface**가 헥사고날의 **Outbound Port**
- DDD의 **Application Service**가 헥사고날의 **UseCase 구현체**

두 개념은 완벽하게 보완 관계입니다.

---

## 트래픽 시나리오별 분석

### 트래픽 적을 때 (100 TPS)

```
헥사고날 아키텍처 도입 여부 판단:
- 팀 5인 이하, 단순 CRUD 위주 → 레이어드 아키텍처 충분
- 도메인 복잡, 장기 프로젝트 → 헥사고날 투자 가치 있음

초기 비용: 인터페이스 + 어댑터 코드 추가 (약 30% 코드 증가)
장기 이익: DB 교체, 외부 API 변경 시 비용 대폭 절감
```

### 트래픽 높을 때 (10,000 TPS)

```
이 시점에서 헥사고날의 이점이 극대화:

시나리오: MySQL → Cassandra 전환 (쓰기 성능 개선 필요)
레이어드: Service 코드 전반 수정, 쿼리 재작성, 2~4주 작업
헥사고날: OrderPersistenceAdapter 교체만으로 완료, 1~2일 작업

시나리오: 특정 조회 경로만 Redis 캐싱 추가
레이어드: Service 로직에 캐싱 코드 침투
헥사고날: CachedOrderRepository(Outbound Adapter) 추가, 기존 코드 변경 없음
```

### 극한 시나리오 (100,000+ TPS)

```
이 규모에서 필수 전략:

1. ReadModel 분리 (CQRS)
   → 별도 QueryUseCase 인터페이스 + 전용 Adapter
   → 쓰기 Adapter (JPA) + 읽기 Adapter (Elasticsearch)

2. 다중 Outbound Adapter 전략
   → Primary: MySQL (쓰기)
   → Cache: Redis (읽기)
   → Search: Elasticsearch (검색)
   → 모두 OrderRepository Port 구현체로 구성

3. Saga Orchestrator도 Application Service로
   → Outbound Port로 각 서비스 클라이언트 추상화
   → 보상 트랜잭션도 비즈니스 로직으로 표현
```

---

## 레이어드 아키텍처와 비교

| 항목 | 레이어드 아키텍처 | 헥사고날 아키텍처 |
|------|-----------------|-----------------|
| 의존성 방향 | 위 → 아래 (단방향) | 모두 Core를 향해 (안쪽) |
| DB 교체 용이성 | 어려움 | 쉬움 (Adapter만 교체) |
| 단위 테스트 | DB 없이 하기 어려움 | 쉬움 (Port Mocking) |
| 외부 API 교체 | Service 코드 수정 필요 | Adapter만 교체 |
| 복잡도 | 낮음 | 높음 |
| 소규모 프로젝트 | 적합 | 과도할 수 있음 |
| 대규모/장수 프로젝트 | 유지보수 어려움 | 적합 |
| 코드량 | 적음 | 많음 (인터페이스 + 구현체) |

---

## 실무에서 자주 하는 실수

#### 실수 1: Port를 너무 세분화

```java
// 나쁜 예 - UseCase가 너무 쪼개짐
interface PlaceOrderUseCase { OrderId placeOrder(...); }
interface CancelOrderUseCase { void cancelOrder(...); }
interface UpdateOrderUseCase { void updateOrder(...); }
// → 클래스 파일 폭발, 오히려 관리 어려움

// 좋은 예 - 응집된 UseCase
interface OrderUseCase {
    OrderId placeOrder(PlaceOrderCommand cmd);
    void cancelOrder(CancelOrderCommand cmd);
    OrderDto getOrder(OrderId id);
}
```

#### 실수 2: Adapter에 비즈니스 로직 포함

```java
// 나쁜 예 - Controller에 비즈니스 로직
@PostMapping("/orders")
public ResponseEntity<?> placeOrder(@RequestBody OrderRequest request) {
    // 비즈니스 로직이 Adapter에 있음 - 헥사고날 위반
    if (request.getAmount() > 1_000_000) {
        throw new BadRequestException("100만원 초과 주문은 전화 확인 필요");
    }
    ...
}

// 좋은 예 - 비즈니스 로직은 Application Service에
@PostMapping("/orders")
public ResponseEntity<?> placeOrder(@RequestBody OrderRequest request) {
    // Adapter는 변환만
    PlaceOrderCommand command = mapper.toCommand(request);
    OrderId id = placeOrderUseCase.placeOrder(command);
    return ResponseEntity.ok(new OrderResponse(id));
}
```

#### 실수 3: Domain Model에서 Outbound Port 직접 호출

```java
// 나쁜 예 - Domain Model이 Repository를 알음
public class Order {
    @Autowired
    private ProductRepository productRepository; // 도메인이 인프라에 의존 - 금지!

    public void addItem(Long productId, int qty) {
        Product p = productRepository.findById(productId); // 도메인에서 DB 호출
    }
}

// 좋은 예 - Application Service에서 조율
public class OrderService implements PlaceOrderUseCase {
    private final ProductRepository productRepository; // Service가 Repository 호출

    public OrderId placeOrder(PlaceOrderCommand cmd) {
        Product product = productRepository.findById(cmd.productId()); // Service 책임
        order.addItem(product, cmd.quantity()); // Domain에는 이미 로딩된 객체 전달
    }
}
```

---

## 면접 포인트

#### Q. 헥사고날 아키텍처에서 Port와 Adapter의 차이는?

```
Port = 인터페이스 (계약). "무엇을"만 정의.
  Inbound Port: 외부가 Core를 호출하는 계약 (UseCase 인터페이스)
  Outbound Port: Core가 외부를 호출하는 계약 (Repository 인터페이스)

Adapter = 구현체. "어떻게"를 정의.
  Inbound Adapter: HTTP/Kafka/CLI 요청을 Port로 변환 (Controller)
  Outbound Adapter: Port를 실제 기술로 구현 (JpaRepository, KafkaPublisher)
```

#### Q. 레이어드 아키텍처와 가장 큰 차이점은?

```
레이어드: Service → Repository (직접 의존)
  → DB 교체 시 Service 수정 필요
  → DB 없이 Service 단위 테스트 불가

헥사고날: Service → Port(인터페이스) ← Adapter(구현체)
  → DB 교체: 새 Adapter만 작성
  → Service 단위 테스트: Port를 Mock으로 대체 (DB 불필요)

핵심: 의존성 역전(DIP) - Service가 Repository를 알지 않고,
      Repository가 Port(인터페이스)를 구현
```

#### Q. 언제 헥사고날 아키텍처를 선택해야 하나?

```
선택 기준:
✓ 외부 시스템(DB, 결제사, 메시지 큐)이 변경될 가능성 있음
✓ 비즈니스 로직이 복잡하고 단위 테스트 커버리지가 중요
✓ 팀이 크고 장기 운영 프로젝트
✓ DDD와 함께 적용할 때

피해야 할 경우:
✗ 간단한 CRUD 앱 (복잡도 대비 이점 없음)
✗ 팀 규모 2~3인 스타트업 MVP
✗ 단기 프로젝트
```

---

<details class="extreme-scenario-details">
<summary class="extreme-scenario-summary">
<span class="extreme-scenario-icon">🔥</span>
<span class="extreme-scenario-label">극한 시나리오 — 클릭하여 펼치기</span>
<span class="extreme-scenario-toggle"></span>
</summary>
<div class="extreme-scenario-body">

<div class="extreme-scenario-content" markdown="1">

헥사고날 아키텍처에서 Stripe → 토스페이먼츠 교체:

```java
// Outbound Port (변경 없음 - 비즈니스 계약은 그대로)
public interface PaymentGateway {
    PaymentResult charge(PaymentRequest request);
    PaymentResult refund(String transactionId, Money amount);
}

// 기존 Stripe Adapter → 제거
class StripePaymentAdapter implements PaymentGateway {
    // Stripe SDK 코드...
}

// 새 TossPayments Adapter → 추가
class TossPaymentsAdapter implements PaymentGateway {
    private final TossPaymentsClient client;

    @Override
    public PaymentResult charge(PaymentRequest request) {
        // 토스페이먼츠 API 호출 로직
        TossResponse response = client.confirmPayment(
            request.getPaymentKey(), request.getAmount().getValue());
        return PaymentResult.success(response.getTransactionId());
    }
}

// Application Service → 단 한 줄도 변경 없음
class PaymentService {
    private final PaymentGateway paymentGateway; // Port만 앎

    public void processPayment(Order order) {
        PaymentResult result = paymentGateway.charge(
            new PaymentRequest(order.getId(), order.getTotalAmount()));
        // ...
    }
}
```

**Application Service, Domain 코드는 단 한 줄도 바꾸지 않아도 됩니다.**

레이어드 아키텍처였다면? 서비스 레이어 전반에 걸쳐 Stripe SDK 호출 코드가 퍼져 있어 대규모 수정이 필요합니다.

---
</div>
</div>
</details>

## 핵심 포인트 정리

```
1. 목적: 비즈니스 로직을 외부 기술(DB, HTTP, MQ)로부터 완전 격리
   → 기술이 바뀌어도 비즈니스 로직 불변

2. 핵심 규칙: 모든 의존성은 Application Core를 향한다
   → Web Adapter → Inbound Port → Application Service
   → Application Service → Outbound Port ← DB Adapter

3. Port = 인터페이스 (계약), Adapter = 구현체 (기술)
   → Inbound Port: UseCase 인터페이스
   → Outbound Port: Repository, EventPublisher 인터페이스

4. 테스트 이점
   → Application Service: Port를 Mock으로 교체 → DB 없이 단위 테스트
   → Adapter: 실제 DB/Kafka 사용하는 통합 테스트

5. DDD와 찰떡궁합
   → DDD Domain Layer = 헥사고날 Application Core 내부
   → DDD Repository Interface = 헥사고날 Outbound Port
```
