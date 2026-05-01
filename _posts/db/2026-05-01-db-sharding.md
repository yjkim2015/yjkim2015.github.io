---
title: "데이터베이스 샤딩 완전 정리"
categories:
- DB
toc: true
toc_sticky: true
toc_label: 목차
---

## 샤딩이란?

**샤딩(Sharding)**은 하나의 데이터셋을 여러 개의 독립적인 데이터베이스 서버(샤드, Shard)에 수평으로 분산하여 저장하는 기법이다. 파티셔닝이 단일 서버 내부에서 데이터를 물리적으로 나누는 것과 달리, 샤딩은 **서버 자체를 여러 대로 늘려** 저장 용량과 처리 능력을 선형으로 확장한다.

```
파티셔닝 vs 샤딩

파티셔닝 (단일 서버)
┌─────────────────────────────────────────┐
│  MySQL Server                           │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │Partition │ │Partition │ │Partition│ │
│  │   p0     │ │   p1     │ │   p2   │ │
│  └──────────┘ └──────────┘ └─────────┘ │
└─────────────────────────────────────────┘
        단일 서버의 CPU/메모리/디스크 공유

샤딩 (다중 서버)
┌────────────┐   ┌────────────┐   ┌────────────┐
│  Shard 0   │   │  Shard 1   │   │  Shard 2   │
│ MySQL #1   │   │ MySQL #2   │   │ MySQL #3   │
│            │   │            │   │            │
│ user 0~33% │   │user 33~66% │   │user 66~99% │
└────────────┘   └────────────┘   └────────────┘
  서버 자원 독립    서버 자원 독립    서버 자원 독립
```

### 파티셔닝과의 핵심 차이

| 항목 | 파티셔닝 | 샤딩 |
|------|---------|------|
| 분산 단위 | 단일 서버 내 파티션 | 별개의 서버(샤드) |
| 확장 방향 | 수직 확장 보완 | 수평 확장 |
| 투명성 | DB가 자동 처리 | 애플리케이션 또는 미들웨어가 처리 |
| 크로스 쿼리 | 옵티마이저가 처리 | 애플리케이션에서 수동 집계 |
| 외래키 | 제약 있음 | 실질적으로 불가 |
| 구현 복잡도 | 낮음 | 높음 |

---

## 왜 샤딩이 필요한가?

### 단일 DB 서버의 한계

```
단일 서버 한계 지점

쓰기 처리량:
MySQL 단일 서버 ≈ 수만 TPS (하드웨어 의존)
대형 서비스 요구 = 수십만 ~ 수백만 TPS

디스크:
단일 서버 SSD ≈ 수십 TB
수백 TB ~ 수 PB 데이터 → 불가능

메모리 (Buffer Pool):
데이터가 버퍼 풀을 초과 → 랜덤 I/O 폭증
수평 확장 없이는 해결 불가

연결 수:
MySQL max_connections ≈ 수천
대형 서비스 동시 연결 = 수십만 → 커넥션 풀 포화
```

수직 확장(Scale-Up)은 한계가 명확하고 비용이 지수적으로 증가한다. 샤딩은 수평 확장(Scale-Out)으로 이 문제를 해결한다.

### 샤딩 도입 시점 판단

```
의사결정 흐름

데이터 증가 / 성능 문제
        │
        ▼
인덱스 최적화, 쿼리 튜닝으로 해결 가능?
   YES → 해결
   NO  ↓
        ▼
읽기 복제(Read Replica) + 캐싱으로 해결 가능?
   YES → 해결 (샤딩 불필요)
   NO  ↓
        ▼
파티셔닝으로 해결 가능?
   YES → 해결 (샤딩 불필요)
   NO  ↓
        ▼
수직 확장으로 해결 가능? (비용 감수)
   YES → 해결 (한시적)
   NO  ↓
        ▼
샤딩 도입 검토
```

---

## 샤딩 전략

### Range-based Sharding

샤드 키의 값 범위를 기준으로 데이터를 분배한다.

```
Range-based Sharding (user_id 기준)

Shard 0: user_id 1       ~ 10,000,000
Shard 1: user_id 10,000,001 ~ 20,000,000
Shard 2: user_id 20,000,001 ~ 30,000,000
Shard 3: user_id 30,000,001 ~ MAXVALUE

user_id = 5,000,000  → Shard 0
user_id = 15,000,000 → Shard 1
user_id = 25,000,000 → Shard 2
```

**장점**

- 라우팅 로직이 단순하다
- 범위 쿼리가 특정 샤드 내에서 완결될 수 있다
- 샤드 간 경계가 명확하여 운영이 쉽다

**단점 — 핫스팟(Hot Spot) 문제**

```
핫스팟 발생 시나리오

신규 가입자는 항상 높은 user_id를 받음
→ Shard 3에 모든 신규 쓰기 집중
→ Shard 0, 1은 읽기 위주로 한산

시간 기반 Range-based의 경우:
→ 가장 최근 파티션이 항상 현재 쓰기를 독점
→ 나머지 샤드는 읽기만 처리

대응책:
- 샤드 프리스플릿(Pre-splitting): 미리 빈 샤드를 할당
- 핫 샤드 분할: 부하가 높은 샤드를 자동 감지 후 분할
```

### Hash-based Sharding

샤드 키에 해시 함수를 적용하여 샤드를 결정한다.

```
Hash-based Sharding

shard_id = hash(user_id) % num_shards

user_id = 1234,  hash(1234)  % 4 = 2  → Shard 2
user_id = 5678,  hash(5678)  % 4 = 0  → Shard 0
user_id = 9999,  hash(9999)  % 4 = 3  → Shard 3
user_id = 10001, hash(10001) % 4 = 1  → Shard 1

Shard 0    Shard 1    Shard 2    Shard 3
┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐
│균등   │  │균등   │  │균등   │  │균등   │
│분포   │  │분포   │  │분포   │  │분포   │
└───────┘  └───────┘  └───────┘  └───────┘
```

**장점**

- 데이터가 샤드에 균등하게 분포된다
- 핫스팟 문제가 적다

**단점 — 노드 추가/제거 시 대규모 재분배**

```
단순 모듈러 해싱의 치명적 단점

샤드 3개 → 4개로 증가 시:
  hash(x) % 3 → hash(x) % 4

기존 라우팅과 새 라우팅이 달라짐
→ 거의 모든 데이터가 잘못된 샤드에 위치
→ 전체 데이터 재분배 필요 (다운타임 또는 대규모 마이그레이션)
```

이 문제를 해결하는 것이 **Consistent Hashing**이다.

### Consistent Hashing

Consistent Hashing은 노드(샤드) 추가/제거 시 최소한의 데이터만 이동하도록 설계된 해시 기법이다.

#### 기본 원리

```
Consistent Hashing — 해시 링 (Hash Ring)

0                                          MAX
├──────────────────────────────────────────┤
│                    링(Ring)              │
└──────────────────────────────────────────┘

1. 해시 공간을 원형 링으로 표현 (0 ~ 2^32-1)
2. 각 샤드 노드를 해시하여 링 위에 배치
3. 각 키도 해시하여 링 위에 배치
4. 키는 링에서 시계 방향으로 가장 가까운 노드에 저장

         0
         │
    N3   │   N0
  ┌──────┼──────┐
  │  K2  │  K0  │
N2┤      ●      ├N1
  │  K3  │  K1  │
  └──────┼──────┘
         │
        MAX/2

K0 → N0 (시계 방향 가장 가까운 노드)
K1 → N1
K2 → N2 (또는 N3, 위치에 따라)
K3 → N3
```

#### 노드 추가 시 데이터 이동

```
기존 상태 (N0, N1, N2)
링에서: K_a → N0, K_b → N1, K_c → N2

새 노드 N3 추가 (N0와 N1 사이에 위치)
링에서: K_a → N0, K_b → N3 (변경!), K_c → N2

이동이 필요한 데이터: K_b만 (N1 → N3)
나머지: 변경 없음

단순 모듈러 해싱: 전체 데이터의 75% 이동
Consistent Hashing: 전체 데이터의 1/N만 이동
```

#### 가상 노드 (Virtual Nodes)

단순 Consistent Hashing은 노드 수가 적을 때 링 위의 배치가 불균등하여 특정 노드에 데이터가 집중될 수 있다. 이를 해결하기 위해 **가상 노드(Virtual Node, VNode)**를 사용한다.

```
가상 노드 구조

실제 노드 3개 (N0, N1, N2)
각 노드당 가상 노드 100개 할당

링 위 배치:
... N0_vn3 - N1_vn47 - N2_vn91 - N0_vn15 - N1_vn62 ...
   (모두 실제 노드 N0, N1, N2에 매핑됨)

효과:
- 링 위 분포가 균등해짐
- 노드별 부하가 균등해짐
- 노드 추가 시 전체 노드에서 균등하게 데이터를 받아옴

노드 성능 차이 반영:
- 고성능 서버: 200개 가상 노드 할당
- 저성능 서버: 100개 가상 노드 할당
→ 자동으로 부하가 성능 비율대로 분배
```

```
Consistent Hashing 전체 구조 다이어그램

                        0
                        │
          N0_vn1(350)   │   N0_vn2(50)
                    ┌───┴───┐
     N2_vn1(300)   ─┤       ├─   N1_vn1(100)
                    │  Ring │
     N2_vn2(250)   ─┤       ├─   N1_vn2(150)
                    └───┬───┘
          N1_vn3(200)   │   N2_vn3(200)
                        │
                       MAX

키 K: hash(K) = 120 → 시계 방향으로 N1_vn2(150) 도달 → Shard N1 저장
키 K: hash(K) = 280 → 시계 방향으로 N2_vn1(300) 도달 → Shard N2 저장
```

### Directory-based Sharding

별도의 **라우팅 테이블(Lookup Table)**에 각 키가 어느 샤드에 있는지 기록한다.

```
Directory-based Sharding 구조

클라이언트
    │
    ▼
┌──────────────────────────────┐
│  Shard Directory Service     │
│  (라우팅 테이블 보관)         │
│                              │
│  user_id range → shard       │
│  1 ~ 100만    → Shard A      │
│  100만 ~ 200만 → Shard B     │
│  VIP 사용자   → Shard C      │
│  기업 계정    → Shard D      │
└──────────────────────────────┘
    │              │
    ▼              ▼
 Shard A        Shard B
```

**장점**

- 샤딩 로직이 완전히 유연하다. 언제든지 라우팅 테이블을 변경하여 데이터를 재배치할 수 있다
- 특수 조건(VIP, 기업 계정 등)에 맞는 커스텀 배치가 가능하다

**단점**

- 라우팅 테이블이 단일 장애점(SPOF)이 된다
- 모든 쿼리에 라우팅 조회가 추가되므로 레이턴시가 증가한다
- 라우팅 서비스 자체를 HA 구성해야 한다

### Geographic Sharding

사용자의 지리적 위치를 기준으로 샤드를 배치한다.

```
Geographic Sharding

KR 사용자 → Seoul Region Shard
US 사용자 → US-East Region Shard
EU 사용자 → EU-West Region Shard (GDPR 데이터 현지화 요건 충족)

┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Seoul Shard  │   │ US-East Shard│   │ EU-West Shard│
│ (KR, JP, CN) │   │ (US, CA)     │   │ (DE, FR, GB) │
└──────────────┘   └──────────────┘   └──────────────┘
```

데이터 주권(Data Sovereignty) 규제 준수에 필수적이다.

---

## 샤드 키(Shard Key) 설계 원칙

샤드 키는 샤딩의 성패를 결정한다. 잘못된 샤드 키는 핫스팟, 크로스 샤드 쿼리 폭증, 재샤딩 비용 등을 초래한다.

```
좋은 샤드 키의 조건

1. 높은 카디널리티(Cardinality)
   - 값의 종류가 많아야 균등 분배 가능
   - BAD:  gender (M/F → 샤드 2개만 의미 있음)
   - GOOD: user_id (수천만 종류)

2. 균등한 데이터 분포
   - 특정 값에 데이터가 몰리지 않아야 함
   - BAD:  country_code (KR이 90% 이면 KR 샤드에 집중)
   - GOOD: hash(user_id)

3. 쿼리 패턴과의 정합성
   - 대부분의 쿼리가 샤드 키를 포함해야 크로스 샤드 쿼리 최소화
   - SNS 예시: 게시물은 user_id로 샤딩 → 사용자 피드 쿼리는 단일 샤드 완결

4. 변경 불가
   - 한번 할당된 샤드 키 값은 변경 불가 (변경 시 데이터 이동 필요)
   - user_id, UUID처럼 불변 식별자 사용

5. 조인 지역성(Join Locality)
   - 자주 함께 조회되는 데이터가 같은 샤드에 있어야 함
   - 예: orders와 order_items를 모두 customer_id로 샤딩
         → customer의 전체 주문 내역이 단일 샤드에 존재
```

---

## 크로스 샤드 쿼리 문제

샤딩의 가장 큰 단점은 여러 샤드에 걸친 쿼리가 복잡해진다는 것이다.

### JOIN 문제

```
단일 DB에서의 JOIN
SELECT u.name, o.amount
FROM users u
JOIN orders o ON u.user_id = o.user_id
WHERE o.created_at > '2024-01-01';
→ DB가 알아서 처리

샤딩 환경에서의 문제:
users  → Shard 0, 1, 2, 3 (user_id 기준 샤딩)
orders → Shard 0, 1, 2, 3 (user_id 기준 샤딩)

같은 user_id로 샤딩 → 같은 샤드에 위치 → JOIN 가능
다른 키로 샤딩   → 다른 샤드에 위치 → JOIN 불가

해결책:
1. 동일 샤드 키 사용: users와 orders 모두 user_id로 샤딩
2. 비정규화: orders에 user_name을 중복 저장
3. 애플리케이션 레벨 JOIN: 각 샤드에서 개별 조회 후 메모리에서 병합
4. 공유 차원 테이블: 작은 참조 테이블은 모든 샤드에 복제
```

### 집계 쿼리 문제

```java
// 전체 사용자 수 집계 — 크로스 샤드 집계
@Service
@RequiredArgsConstructor
public class UserStatsService {

    private final List<DataSource> shards; // 샤드별 DataSource 목록

    public long getTotalUserCount() {
        // 모든 샤드에서 COUNT 조회 후 합산
        return shards.parallelStream()
            .mapToLong(shard -> {
                try (Connection conn = shard.getConnection();
                     PreparedStatement ps = conn.prepareStatement(
                         "SELECT COUNT(*) FROM users")) {
                    ResultSet rs = ps.executeQuery();
                    rs.next();
                    return rs.getLong(1);
                } catch (SQLException e) {
                    throw new RuntimeException(e);
                }
            })
            .sum();
    }
}
```

대규모 집계는 각 샤드에서 병렬로 부분 집계 후 애플리케이션에서 합산하는 **Scatter-Gather** 패턴을 사용한다.

---

## 크로스 샤드 트랜잭션

단일 DB에서는 ACID 트랜잭션이 보장되지만, 샤딩 환경에서는 여러 샤드에 걸친 트랜잭션이 필요할 때 문제가 복잡해진다.

### 2PC (Two-Phase Commit)

```
2PC 동작 흐름

Transaction Coordinator (TC)
        │
        │ Phase 1: Prepare
        ├──────────────────→ Shard A: PREPARE (Tentative Write)
        ├──────────────────→ Shard B: PREPARE (Tentative Write)
        │
        │ 모든 샤드 OK 응답 시
        │ Phase 2: Commit
        ├──────────────────→ Shard A: COMMIT
        ├──────────────────→ Shard B: COMMIT

문제점:
- TC 장애 시 모든 샤드가 PREPARED 상태로 블로킹
- 레이턴시 증가 (2번의 네트워크 왕복)
- 가용성 저하: 하나의 샤드라도 응답 없으면 전체 블로킹
```

### Saga 패턴

2PC 대신 각 샤드에서 로컬 트랜잭션을 순차적으로 실행하고, 실패 시 이전 단계를 보상(Compensating Transaction)한다.

```
Saga 패턴 (Choreography 방식)

주문 생성 시나리오:
  Step 1: Order 샤드에 주문 생성 (order_status = PENDING)
  Step 2: Inventory 샤드에서 재고 차감
  Step 3: Payment 샤드에서 결제 처리
  Step 4: Order 샤드에서 주문 확정 (order_status = CONFIRMED)

실패 시 보상 트랜잭션:
  Step 3 실패 → Inventory 샤드 재고 복구 → Order 취소

장점: 가용성 높음, 블로킹 없음
단점: 최종 일관성 (Eventual Consistency), 보상 로직 복잡
```

```java
// Saga 패턴 예시 (Spring + 이벤트 기반)
@Service
@RequiredArgsConstructor
public class OrderSaga {

    private final OrderShardRepository orderRepo;
    private final InventoryShardRepository inventoryRepo;
    private final PaymentShardRepository paymentRepo;
    private final ApplicationEventPublisher eventPublisher;

    @Transactional  // Order 샤드 로컬 트랜잭션
    public Order createOrder(CreateOrderCommand cmd) {
        Order order = orderRepo.save(Order.pending(cmd));
        // 이벤트 발행 → Inventory 샤드에서 비동기 처리
        eventPublisher.publishEvent(new OrderCreatedEvent(order.getId(), cmd.items()));
        return order;
    }

    @EventListener
    @Transactional  // Inventory 샤드 로컬 트랜잭션
    public void handleOrderCreated(OrderCreatedEvent event) {
        try {
            inventoryRepo.decreaseStock(event.orderId(), event.items());
            eventPublisher.publishEvent(new StockReservedEvent(event.orderId()));
        } catch (InsufficientStockException e) {
            // 보상 트랜잭션: 주문 취소
            eventPublisher.publishEvent(new OrderCancelledEvent(event.orderId(), "재고 부족"));
        }
    }

    @EventListener
    @Transactional  // Order 샤드 보상 트랜잭션
    public void handleOrderCancelled(OrderCancelledEvent event) {
        orderRepo.updateStatus(event.orderId(), OrderStatus.CANCELLED, event.reason());
    }
}
```

---

## 리밸런싱 (샤드 분할/병합)

샤드가 증가하면서 데이터 재분배가 필요하다.

### 샤드 분할

```
샤드 분할 과정 (Shard 0 → Shard 0a, 0b)

Before:
Shard 0: user_id 1 ~ 10,000,000

After:
Shard 0a: user_id 1 ~ 5,000,000
Shard 0b: user_id 5,000,001 ~ 10,000,000

무중단 분할 절차:
1. Shard 0의 복제본(Replica)에서 Shard 0b용 데이터 복사 시작
2. Shard 0에서 Shard 0b로 바이너리 로그 실시간 동기화 (CDC)
3. 동기화 완료 후 라우터에서 해당 user_id 범위를 Shard 0b로 전환
4. Shard 0에서 불필요한 데이터 삭제
```

### Consistent Hashing에서의 리밸런싱

```
노드 추가 시 데이터 이동

Before (N0, N1, N2):
K_a → N0
K_b → N1
K_c → N2

After (N0, N1, N2, N3 추가 — N1과 N2 사이에 위치):
K_a → N0  (변화 없음)
K_b → N1  (변화 없음)
K_c → N3  (N2 → N3으로 이동! 해당 데이터만 N2에서 N3으로 복사)
        ↑
        이 데이터만 이동 (전체의 약 1/4)
```

---

## 실무 아키텍처

### 애플리케이션 레벨 샤딩

```java
// 샤드 라우터 구현
@Component
public class ShardRouter {

    private final List<DataSource> shards;
    private final int shardCount;

    public ShardRouter(List<DataSource> shards) {
        this.shards = shards;
        this.shardCount = shards.size();
    }

    public DataSource getShardFor(long shardKey) {
        int shardIndex = (int) (Math.abs(shardKey) % shardCount);
        return shards.get(shardIndex);
    }

    public DataSource getShardFor(String shardKey) {
        int hash = Math.abs(shardKey.hashCode());
        return shards.get(hash % shardCount);
    }

    // 전체 샤드에 분산 실행 (Scatter-Gather)
    public <T> List<T> executeOnAllShards(Function<DataSource, List<T>> query) {
        return shards.parallelStream()
            .flatMap(shard -> query.apply(shard).stream())
            .collect(Collectors.toList());
    }
}

// 샤딩된 Repository
@Repository
@RequiredArgsConstructor
public class ShardedUserRepository {

    private final ShardRouter shardRouter;

    public User findById(long userId) {
        DataSource shard = shardRouter.getShardFor(userId);
        return new JdbcTemplate(shard)
            .queryForObject(
                "SELECT * FROM users WHERE user_id = ?",
                USER_ROW_MAPPER, userId);
    }

    public void save(User user) {
        DataSource shard = shardRouter.getShardFor(user.getUserId());
        new JdbcTemplate(shard)
            .update("INSERT INTO users (user_id, name, email) VALUES (?, ?, ?)",
                user.getUserId(), user.getName(), user.getEmail());
    }

    // 크로스 샤드 집계
    public long countAll() {
        return shardRouter.executeOnAllShards(shard ->
            List.of(new JdbcTemplate(shard)
                .queryForObject("SELECT COUNT(*) FROM users", Long.class)))
            .stream().mapToLong(Long::longValue).sum();
    }
}
```

### 미들웨어 샤딩

애플리케이션 코드 변경 없이 미들웨어가 샤딩을 처리한다.

#### Vitess

YouTube에서 MySQL 스케일링을 위해 개발한 오픈소스 미들웨어다.

```
Vitess 아키텍처

Application
    │ MySQL 프로토콜
    ▼
┌─────────────────────┐
│   VTGate (프록시)   │ ← 라우팅 결정, 크로스 샤드 쿼리 처리
└─────────────────────┘
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│VTTablet│ │VTTablet│ ← 각 MySQL 인스턴스 관리
│Shard 0 │ │Shard 1 │
│MySQL   │ │MySQL   │
└────────┘ └────────┘

특징:
- 크로스 샤드 JOIN을 VTGate에서 처리
- 온라인 스키마 변경 지원 (gh-ost 통합)
- Kubernetes 친화적 운영
```

#### ProxySQL

```
ProxySQL 라우팅 규칙 예시

# 샤드 키 기반 라우팅 규칙 (SQL 파싱)
INSERT INTO mysql_query_rules
  (rule_id, active, match_pattern, destination_hostgroup, apply)
VALUES
  (1, 1, '^SELECT.*WHERE user_id BETWEEN 1 AND 10000000', 10, 1),
  (2, 1, '^SELECT.*WHERE user_id BETWEEN 10000001 AND 20000000', 20, 1);
```

### 미들웨어 vs 애플리케이션 레벨 비교

| 항목 | 애플리케이션 레벨 | 미들웨어 (Vitess/ProxySQL) |
|------|----------------|--------------------------|
| 구현 복잡도 | 높음 | 낮음 (코드 변경 최소) |
| 유연성 | 매우 높음 | 미들웨어 기능에 종속 |
| 크로스 샤드 쿼리 | 직접 구현 | 미들웨어가 처리 |
| 성능 | 직접 최적화 가능 | 미들웨어 오버헤드 |
| 운영 복잡도 | 낮음 | 높음 (미들웨어 관리) |
| 트랜잭션 | 직접 제어 | 제한적 |

---

## 극한 시나리오 대응

### 핫 샤드 발생 시 대응

```
핫 샤드 감지 및 대응 절차

1. 감지
   - 모니터링: 샤드별 QPS, CPU, 디스크 I/O, 레이턴시 추적
   - 임계치: 특정 샤드 CPU > 70%, 타 샤드 평균의 2배 이상

2. 단기 대응 (즉각)
   핫 샤드에 Read Replica 추가
   → 읽기 쿼리를 Replica로 분산

3. 중기 대응
   핫 샤드를 2개로 분할 (Range 재정의 또는 새 해시 버킷 할당)
   → Consistent Hashing이라면 해당 샤드의 가상 노드 수 감소

4. 근본 원인 분석
   - 샤드 키 선택 오류 → 재샤딩 검토
   - 특정 사용자(Celebrity Problem) → 해당 사용자 별도 처리
   - 쿼리 패턴 문제 → 캐싱 레이어 추가

Celebrity Problem 해결:
  인플루언서(팔로워 1000만 명)의 게시물 → 조회 폭발
  → 해당 사용자의 데이터를 전용 샤드에 격리
  → 또는 CDN/캐시 레이어로 DB 부하 차단
```

### 샤드 장애 시 가용성

```
샤드 장애 대응 아키텍처

각 샤드는 Primary-Replica 구성
┌──────────────────────────────────┐
│  Shard 0                         │
│  ┌─────────┐     ┌─────────────┐ │
│  │Primary  │────▶│ Replica x2  │ │
│  │(쓰기)   │     │(읽기 + 대기)│ │
│  └─────────┘     └─────────────┘ │
└──────────────────────────────────┘

Primary 장애 시:
1. MHA / Orchestrator가 Primary 장애 감지 (수 초)
2. 자동 Failover: Replica → Primary 승격
3. 라우터가 새 Primary 주소로 연결 업데이트
4. 짧은 다운타임(수 초~수십 초) 후 정상화

RPO(Recovery Point Objective): 복제 지연만큼의 데이터 손실 가능
RTO(Recovery Time Objective): 자동 Failover 기준 30초~2분
```

### 다운타임 없는 샤드 추가 마이그레이션

```
무중단 리샤딩 절차 (Shard 4개 → 8개)

Phase 1: 이중 쓰기 시작
  - 라우터: 모든 쓰기를 기존 샤드 + 새 샤드 양쪽에 기록
  - 읽기: 여전히 기존 샤드에서만 수행

Phase 2: 데이터 백필 (Backfill)
  - 기존 데이터를 새 샤드 배치로 복사 (CDC 또는 배치 스크립트)
  - 복사 중에도 이중 쓰기로 새 데이터 동기화 유지

Phase 3: 검증
  - 기존 샤드와 새 샤드의 데이터 일관성 검증
  - 행 수, 체크섬 비교

Phase 4: 읽기 전환
  - 읽기 트래픽을 새 샤드로 점진적으로 이전 (10% → 50% → 100%)
  - 문제 발생 시 즉시 롤백 가능

Phase 5: 이중 쓰기 종료
  - 쓰기도 새 샤드 구성으로 완전 전환
  - 기존 샤드의 이중 쓰기 중단

Phase 6: 기존 샤드 정리
  - 이전 샤드에서 이미 이전된 데이터 삭제
```

---

## 글로벌 유니크 ID 생성

샤딩 환경에서는 각 샤드가 독립적인 `AUTO_INCREMENT`를 사용하므로 ID 충돌이 발생한다. 전역적으로 유니크한 ID가 필요하다.

### Snowflake ID

Twitter가 개발한 64비트 분산 ID 생성 알고리즘이다.

```
Snowflake ID 구조 (64비트)

┌─────────────────────────────────────────────────────────────────┐
│ 0 │        41비트 타임스탬프        │ 10비트 워커ID │ 12비트 시퀀스 │
└─────────────────────────────────────────────────────────────────┘
  │              │                        │              │
  │              ▼                        ▼              ▼
  │  밀리초 단위 epoch 이후 경과 시간  데이터센터+서버  같은 밀리초 내 순번
  │  (2^41ms ≈ 69년 사용 가능)        (최대 1024대)   (최대 4096/ms)
  ▼
부호 비트 (항상 0, 양수 보장)

특징:
- DB 없이 각 서버가 독립적으로 생성 (네트워크 왕복 없음)
- 시간순 정렬 가능 (앞 41비트가 타임스탬프)
- 초당 400만 개 이상 생성 가능
```

```java
// Snowflake ID 생성기 구현
@Component
public class SnowflakeIdGenerator {

    private static final long EPOCH = 1609459200000L; // 2021-01-01T00:00:00Z
    private static final long WORKER_ID_BITS  = 10L;
    private static final long SEQUENCE_BITS   = 12L;
    private static final long MAX_WORKER_ID   = ~(-1L << WORKER_ID_BITS);  // 1023
    private static final long MAX_SEQUENCE    = ~(-1L << SEQUENCE_BITS);   // 4095
    private static final long WORKER_SHIFT    = SEQUENCE_BITS;             // 12
    private static final long TIMESTAMP_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS; // 22

    private final long workerId;
    private long lastTimestamp = -1L;
    private long sequence      = 0L;

    public SnowflakeIdGenerator(@Value("${app.worker-id}") long workerId) {
        if (workerId > MAX_WORKER_ID || workerId < 0) {
            throw new IllegalArgumentException("Worker ID must be between 0 and " + MAX_WORKER_ID);
        }
        this.workerId = workerId;
    }

    public synchronized long nextId() {
        long now = System.currentTimeMillis();

        if (now < lastTimestamp) {
            throw new RuntimeException("Clock moved backwards");
        }

        if (now == lastTimestamp) {
            sequence = (sequence + 1) & MAX_SEQUENCE;
            if (sequence == 0) {
                // 같은 밀리초 내 시퀀스 소진 → 다음 밀리초 대기
                now = waitNextMillis(lastTimestamp);
            }
        } else {
            sequence = 0L;
        }

        lastTimestamp = now;

        return ((now - EPOCH) << TIMESTAMP_SHIFT)
             | (workerId       << WORKER_SHIFT)
             | sequence;
    }

    private long waitNextMillis(long lastTs) {
        long ts = System.currentTimeMillis();
        while (ts <= lastTs) ts = System.currentTimeMillis();
        return ts;
    }
}
```

### UUID v4 vs Snowflake 비교

```
UUID v4
장점: 구현 단순, 라이브러리 내장
단점: 128비트 (저장 공간), 랜덤 순서 (인덱스 단편화 심각)
      → INSERT마다 B-Tree 중간 삽입 → 페이지 분할 → 성능 저하

Snowflake
장점: 64비트, 시간순 정렬 (순차 삽입 → 인덱스 단편화 최소)
단점: 워커 ID 관리 필요, 시계 동기화 의존 (NTP)

UUID v7 (RFC 9562, 최신)
장점: 128비트이지만 앞 48비트가 타임스탬프 → 시간순 정렬
     Snowflake 대비 구현 단순, 라이브러리 지원 증가 중
단점: 128비트 저장 공간
```

---

## 샤딩 vs 읽기 복제 vs 캐싱 — 의사결정 트리

```
성능/확장성 문제 발생
          │
          ▼
    읽기 과부하?
    (읽기:쓰기 = 9:1 이상)
          │
    YES   │   NO
    ──────┼──────
    │              │
    ▼              ▼
 캐싱 적용    쓰기 과부하?
 (Redis 등)        │
    │         YES  │  NO
    │         ─────┼─────
    │         │         │
    │         ▼         ▼
    │     데이터 크기  레이턴시 문제?
    │     TB 수준?         │
    │         │       YES  │  NO
    │    YES  │  NO   ─────┼─────
    │    ─────┼──     │         │
    │    │       │    ▼         ▼
    │    ▼       ▼  인덱스/쿼리  수직 확장
    │  샤딩    파티셔닝  최적화    검토
    │  고려    고려
    │
    ▼
캐싱으로 부족?
(캐시 히트율 < 80%)
    │
    ▼
읽기 복제(Read Replica) 추가
    │
    ▼
여전히 부족?
(Replica 5대 이상에도 부족)
    │
    ▼
샤딩 도입 검토
```

### 각 전략의 적합한 상황

```
전략별 적합 상황 정리

┌──────────────────────────────────────────────────────────────────┐
│ 캐싱 (Redis, Memcached)                                          │
│  - 동일 데이터 반복 읽기 (캐시 히트율 높음)                      │
│  - 읽기 레이턴시 민감                                             │
│  - 데이터 갱신이 드문 경우                                        │
│  - 구현 비용: 낮음 / 일관성: 최종 일관성                         │
├──────────────────────────────────────────────────────────────────┤
│ 읽기 복제 (Read Replica)                                          │
│  - 읽기 트래픽이 쓰기의 수 배 이상                               │
│  - 리포트/분석 쿼리 분리                                          │
│  - 지리적 읽기 분산                                               │
│  - 구현 비용: 낮음 / 일관성: 복제 지연 허용                      │
├──────────────────────────────────────────────────────────────────┤
│ 파티셔닝                                                          │
│  - 시계열 데이터, 기간별 아카이빙                                  │
│  - 단일 서버 내 대용량 테이블 관리                               │
│  - 구현 비용: 낮음~중간 / DB 투명 처리                           │
├──────────────────────────────────────────────────────────────────┤
│ 샤딩                                                              │
│  - 단일 서버 쓰기 한계 도달                                       │
│  - 데이터 크기가 단일 서버 한계 초과 (수십 TB 이상)              │
│  - 수평 확장이 반드시 필요한 경우                                 │
│  - 구현 비용: 매우 높음 / 복잡도: 매우 높음                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## Spring 애플리케이션 샤딩 통합 예시

### AbstractRoutingDataSource 활용

```java
// 샤드 컨텍스트 홀더
public class ShardContextHolder {
    private static final ThreadLocal<Integer> SHARD_KEY = new ThreadLocal<>();

    public static void setShardKey(int shardKey) { SHARD_KEY.set(shardKey); }
    public static Integer getShardKey()          { return SHARD_KEY.get(); }
    public static void clear()                   { SHARD_KEY.remove(); }
}

// 라우팅 DataSource
@Configuration
public class ShardDataSourceConfig {

    @Bean
    public DataSource routingDataSource(
            @Qualifier("shard0") DataSource shard0,
            @Qualifier("shard1") DataSource shard1,
            @Qualifier("shard2") DataSource shard2,
            @Qualifier("shard3") DataSource shard3) {

        Map<Object, Object> targetDataSources = new HashMap<>();
        targetDataSources.put(0, shard0);
        targetDataSources.put(1, shard1);
        targetDataSources.put(2, shard2);
        targetDataSources.put(3, shard3);

        AbstractRoutingDataSource routing = new AbstractRoutingDataSource() {
            @Override
            protected Object determineCurrentLookupKey() {
                Integer shardKey = ShardContextHolder.getShardKey();
                if (shardKey == null) {
                    throw new IllegalStateException("샤드 키가 설정되지 않았습니다.");
                }
                return Math.abs(shardKey) % 4;  // 4개 샤드
            }
        };
        routing.setTargetDataSources(targetDataSources);
        routing.setDefaultTargetDataSource(shard0);
        return routing;
    }
}

// 샤딩 AOP — @Sharded 어노테이션으로 자동 샤드 선택
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Sharded {
    String keyExpression(); // SpEL 표현식
}

@Aspect
@Component
@RequiredArgsConstructor
public class ShardingAspect {

    private final ExpressionParser parser = new SpelExpressionParser();

    @Around("@annotation(sharded)")
    public Object routeToShard(ProceedingJoinPoint pjp, Sharded sharded) throws Throwable {
        // SpEL로 메서드 인자에서 샤드 키 추출
        MethodSignature sig = (MethodSignature) pjp.getSignature();
        EvaluationContext ctx = new StandardEvaluationContext();
        String[] paramNames = sig.getParameterNames();
        Object[] args = pjp.getArgs();
        for (int i = 0; i < paramNames.length; i++) {
            ctx.setVariable(paramNames[i], args[i]);
        }
        Integer shardKey = parser.parseExpression(sharded.keyExpression())
                                 .getValue(ctx, Integer.class);
        ShardContextHolder.setShardKey(shardKey);
        try {
            return pjp.proceed();
        } finally {
            ShardContextHolder.clear();
        }
    }
}

// 사용 예시
@Service
public class UserService {

    @Sharded(keyExpression = "#userId")
    public User getUser(long userId) {
        return userRepository.findById(userId);  // 자동으로 올바른 샤드에 연결
    }

    @Sharded(keyExpression = "#user.userId")
    public User createUser(User user) {
        return userRepository.save(user);
    }
}
```

---

## 정리

샤딩은 강력하지만 운영 복잡도가 극단적으로 높아지는 기법이다. 도입 전 반드시 다음 순서를 확인해야 한다.

1. **쿼리/인덱스 최적화** — 가장 먼저, 비용 없이 수십 배 성능 향상 가능
2. **캐싱** — Redis로 읽기 부하의 80~90%를 흡수
3. **읽기 복제** — 쓰기는 Primary, 읽기는 Replica로 분산
4. **파티셔닝** — 단일 서버 내 대용량 테이블 관리
5. **수직 확장** — 더 큰 서버로 교체 (한시적 해결)
6. **샤딩** — 위 모든 방법이 한계에 도달했을 때

샤딩을 선택했다면 Consistent Hashing으로 리밸런싱 비용을 최소화하고, 샤드 키를 신중하게 설계하고, 크로스 샤드 트랜잭션을 Saga 패턴으로 처리하는 것이 실무에서 검증된 조합이다.
