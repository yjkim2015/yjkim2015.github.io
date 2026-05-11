---
title: "장바구니 설계 — 로그인 전후 장바구니를 끊김 없이 합치는 법"
categories:
- SYSTEMDESIGN
toc: true
toc_sticky: true
toc_label: 목차
---

> **한 줄 요약**: 비로그인 임시 장바구니를 Redis에 보관하고, 로그인 시 병합 전략(수량 합산 vs 로그인 우선)으로 충돌을 해소하며, 재고는 결제 시점에만 잠그는 것이다.

## 실제 문제: 비로그인 장바구니 유실과 병합 충돌

올리브영 앱에서 립스틱 3개를 담고 회원가입을 하면 어떻게 될까요? 서버 내부에서는 쿠키 ID 기반 게스트 장바구니와 사용자 ID 기반 회원 장바구니가 충돌합니다.

- **문제 1 — 비로그인 장바구니 유실**: 로그인 순간 담아뒀던 상품이 사라집니다. 전환율(Conversion Rate) 직결 이슈입니다.
- **문제 2 — 병합 충돌**: 게스트로 A 상품 2개, 로그인 계정에 A 상품 1개가 있으면? 3개로 합산할지 2개로 덮어쓸지 규칙이 명확해야 합니다.
- **문제 3 — 재고 불일치**: 장바구니에 담는다고 재고가 예약되지 않아 결제 시 품절이 될 수 있습니다.
- **문제 4 — 가격 스냅샷 vs 실시간**: 담아둔 상품이 할인 행사에 들어갔을 때 어떤 가격으로 결제하는가?

---

## 설계 의사결정 로드맵

### 결정 1: 저장소 — 세션 vs Redis vs RDB

**문제**: 장바구니는 읽기·쓰기 모두 빈번하고 TTL이 있으며, 상품 페이지 이동마다 조회됩니다.

| 후보 | 장점 | 단점 | 언제 적합 |
|------|------|------|----------|
| 서버 세션 (메모리) | 구현 단순 | 서버 재시작 시 유실, 수평 확장 불가 | 단일 서버, 프로토타입 |
| Redis (인메모리 KV) | 고속 읽기쓰기, TTL 내장, Hash로 상품 단위 조작 | 장애 시 유실 가능 (AOF 설정 필요) | 활성·게스트 장바구니 |
| RDB (MySQL) | 영구 저장, 트랜잭션 보장 | 상품 추가/삭제마다 Row 조작, 높은 TPS 시 병목 | 로그인 회원 영구 저장 |

**우리의 선택: Redis (활성 장바구니) + RDB (로그인 회원 영구 저장) 이중 구조**
- 게스트 장바구니는 TTL 7일 Redis Hash로 저장합니다. `HSET cart:{guestId} {productId} {qty}`로 O(1) 조작이 가능합니다. 로그인 회원이 체크아웃하면 RDB에 영구 저장하고 Redis 캐시를 Write-Through로 동기화합니다.
- 안 하면: DAU 1,500만, 1인당 페이지뷰 10회면 초당 1,700 QPS가 장바구니 조회에 쏟아집니다. Redis 없이는 감당 불가합니다.

### 결정 2: 비로그인 장바구니 — 쿠키 vs 로컬스토리지 vs 서버 임시저장

**문제**: 로그인하지 않은 사용자의 장바구니를 클라이언트에 저장할 것인가, 서버에 저장할 것인가?

| 후보 | 장점 | 단점 | 언제 적합 |
|------|------|------|----------|
| 쿠키 (클라이언트) | 구현 단순 | 4KB 제한, 다른 기기에서 소실 | 상품 수 적은 단순 구현 |
| 로컬스토리지 (클라이언트) | 용량 충분, 빠름 | 다른 기기 연동 불가, 브라우저 삭제 시 유실 | SPA 환경 |
| 서버 임시저장 (Redis + guestId) | 기기 간 공유 가능, 병합 로직 일원화 | Redis 비용, guestId 관리 필요 | 전환율이 중요한 커머스 |

**우리의 선택: 서버 임시저장 (Redis) + guestId 쿠키**
- 쿠키에는 UUID guestId만 저장하고 실제 데이터는 Redis에 둡니다. 모바일에서 담고 PC에서 결제하는 크로스 디바이스 시나리오를 지원합니다.
- 안 하면: 로컬스토리지에만 저장하면 앱에서 담은 상품이 PC 웹에서 보이지 않습니다.

### 결정 3: 장바구니-재고 동기화 — 실시간 vs Lazy vs 결제 시점

**문제**: 사용자가 상품을 장바구니에 담을 때 재고를 예약(Lock)해야 하는가?

| 후보 | 장점 | 단점 | 언제 적합 |
|------|------|------|----------|
| 실시간 예약 (담을 때 Lock) | 결제 시 품절 없음 | 담고 이탈 시 재고 묶임, 전환율 하락 | 좌석·항공권 등 희소 재고 |
| Lazy 체크 (조회 때마다 표시) | 재고 묶임 없음 | 결제 시 품절 가능 | 재고 충분한 일반 상품 |
| 결제 시점 Hard Lock | 재고 묶임 없음 + 결제 직전 정확한 확인 | 결제 직전 품절 시 롤백 필요 | 대부분의 이커머스 |

**우리의 선택: Lazy 재고 표시 + 결제 시점 Hard Lock**
- 장바구니 단계에서는 재고 상태를 표시만 합니다. 결제 시점에 `SELECT ... FOR UPDATE`로 재고를 잠그고 부족 시 즉시 알립니다.
- 안 하면: 한정판 100켤레를 동시에 1만 명이 담으면 99,900명의 재고가 묶여 실제 구매 전환이 일어나지 않습니다.

### 결정 4: 가격 일관성 — 담을 때 가격 vs 조회 시 가격 vs 결제 시 가격

**문제**: 장바구니에 담은 후 가격이 변경됐을 때 어떤 가격으로 결제하는가?

| 후보 | 장점 | 단점 | 언제 적합 |
|------|------|------|----------|
| 담을 때 가격 고정 | 사용자 예측 가능 | 할인 행사 미반영 | 경매, 한시 특가 |
| 조회 시 실시간 가격 | 항상 최신 가격 | 페이지 이동마다 가격 변동으로 혼란 | 빠른 가격 변동 상품 |
| 결제 시점 최신 가격 | 최종 결제 가격 정확 | 결제 직전 가격 인상 시 사용자 놀람 | 대부분의 이커머스 표준 |

**우리의 선택: 조회 시 실시간 가격 표시 + 결제 시점 최신 가격 확정**
- 장바구니 조회 시 항상 현재 가격을 표시합니다. 결제 요청 시 가격이 변경됐으면 "가격이 변경되었습니다. 현재 가격으로 결제하시겠습니까?" 팝업으로 확인을 받습니다.
- 안 하면: 가격 스냅샷만 쓰면 3일 전 담은 상품의 50% 할인을 놓치고, CS 문의가 폭증합니다.

---

## 1. 요구사항 분석 및 규모 추정

### 기능 요구사항

1. **장바구니 CRUD**: 상품 추가, 수량 변경, 삭제, 전체 조회
2. **비로그인 장바구니**: 게스트 UUID 기반 임시 장바구니, 7일 TTL
3. **로그인 시 병합**: 게스트 → 회원 장바구니 자동 병합
4. **재고 상태 표시**: 조회 시 품절/품절임박 실시간 반영
5. **가격 최신화**: 조회 시 현재 가격 표시, 결제 시 가격 변경 알림
6. **저장 장바구니**: 나중에 사기 (위시리스트와 별개)

### 비기능 요구사항

- **가용성**: 99.99%
- **지연시간**: 장바구니 조회 P99 100ms 이하
- **내구성**: 로그인 회원 장바구니 유실 0
- **확장성**: 블랙프라이데이 평소 대비 10배 트래픽 처리

### 규모 추정

- DAU 1,500만 명
- 장바구니 조회: 사용자당 5회/일 → **초당 870 QPS**
- 장바구니 추가/수정: 사용자당 2회/일 → **초당 350 WPS**
- Redis 메모리: 게스트 600만 × 8개 × 50bytes = **약 2.4GB**
- RDB: 로그인 회원 900만 × 8개 = 7,200만 행 (~30GB)

---

## 2. 고수준 아키텍처

게스트는 번호표(guestId)로 임시 사물함(Redis)을 쓰고, 회원이 되면 영구 사물함(RDB)으로 짐을 옮기는 **물품 보관함** 구조입니다.

```mermaid
graph LR
    GW[API Gateway] --> CartSvc[Cart Service]
    CartSvc --> Redis[(Redis)]
    CartSvc --> MySQL[(MySQL)]
    CartSvc --> ProdSvc[Product Service]
    CartSvc --> Merge[병합큐 및 Worker]
    Merge --> MySQL
```

| 컴포넌트 | 역할 |
|---------|------|
| **API Gateway** | guestId 쿠키 주입, 인증 토큰 검증. 비로그인 요청에도 guestId 없으면 UUID 발급해 쿠키에 삽입 |
| **Cart Service** | Redis Write-Through 캐시를 통해 조회 성능 보장 |
| **Redis Hash** | `cart:{userId}` 또는 `cart:guest:{guestId}` 키로 상품 ID → 수량 매핑 저장 |
| **MySQL** | 로그인 회원의 영구 장바구니. Redis 장애 시에도 데이터 유실 없음 |
| **Product Service** | 가격·재고 조회. Cart Service가 조회 시 호출 |
| **Merge Worker** | 로그인 이벤트를 Kafka로 수신해 비동기 병합. 동기 처리 시 로그인 응답 지연 방지 |

**로그인 시 게스트 장바구니 병합 흐름**

```mermaid
sequenceDiagram
    participant U as 사용자
    participant CS as Cart Service
    participant R as Redis
    U->>CS: 로그인 완료
    CS->>R: 게스트 장바구니 조회
    R-->>CS: guestId 항목 반환
    CS->>R: 회원 장바구니에 수량 합산
    CS->>R: 게스트 키 삭제
    CS-->>U: 병합 완료
```

**결제 시 재고 Hard Lock 흐름**

```mermaid
sequenceDiagram
    participant U as 사용자
    participant CS as Cart Service
    participant IS as 재고 DB
    U->>CS: 결제 요청
    CS->>IS: SELECT FOR UPDATE (productId 오름차순)
    IS-->>CS: 재고 확인
    CS->>IS: 재고 차감 확정
    CS-->>U: 주문 생성 완료
```

---

## 3. 핵심 컴포넌트 상세 설계

### Redis 스키마 설계

**방법 A — 전체를 JSON String으로 저장:**
```
cart:user:12345 → '{"items":[{"productId":"P001","qty":2},...]}'
```
단점: 상품 1개 수량 변경에도 전체 JSON을 덮어써야 하고, 동시 수정 시 Lost Update 발생.

**방법 B — Hash로 상품 단위 저장 (선택):**
```
cart:user:12345 → Hash { "P001": "2", "P002": "1", "P003": "3" }
```
`HSET cart:user:12345 P001 3`으로 상품 단위 원자적 수정, `HINCRBY`로 수량 증감도 원자적입니다. 상품 메타데이터(가격·이름)는 조회 시 Product Service에서 가져옵니다.

**TTL 전략:**
```
게스트 장바구니: TTL = 7일 (마지막 활동 기준 갱신)
로그인 회원 Redis 캐시: TTL = 24시간 (RDB가 원본)
```

### 병합 알고리즘 (Guest → Login)

```java
@Service
public class CartMergeService {

    // 병합 전략: 수량 합산 (양쪽에 같은 상품이 있으면 더함)
    // Redis Lua 스크립트로 guestKey 읽기 + userKey 병합 + guestKey 삭제를 원자적으로 실행해
    // 멀티 디바이스 동시 로그인 시 이중 합산을 방지합니다.
    public void mergeGuestCartToUser(String guestId, Long userId) {
        String guestKey = "cart:guest:" + guestId;
        String userKey  = "cart:user:" + userId;

        Map<String, String> guestItems = redisTemplate.opsForHash().entries(guestKey);
        if (guestItems.isEmpty()) return;

        for (Map.Entry<String, String> entry : guestItems.entrySet()) {
            int guestQty = Integer.parseInt(entry.getValue());
            redisTemplate.opsForHash().increment(userKey, entry.getKey(), guestQty);
        }

        // 최대 수량 상한 적용 (상품당 99개 제한)
        Map<String, String> merged = redisTemplate.opsForHash().entries(userKey);
        for (Map.Entry<String, String> entry : merged.entrySet()) {
            if (Integer.parseInt(entry.getValue()) > 99)
                redisTemplate.opsForHash().put(userKey, entry.getKey(), "99");
        }

        redisTemplate.delete(guestKey);
        cartEventPublisher.publishMergeCompleted(userId);  // RDB 동기화 (비동기)
    }
}
```

수량 합산을 선택한 이유: 게스트 2개 + 로그인 계정 1개일 때 사용자는 최소 3개를 원한다고 볼 수 있습니다. 강제 덮어쓰기보다 직접 수정하는 것이 낫습니다. SSG닷컴과 올리브영이 이 방식을 씁니다.

### 장바구니 상품 추가 (상한 체크)

```java
private static final int MAX_CART_ITEMS = 200;

public void addToCart(String cartKey, String productId, int quantity) {
    long currentSize = redisTemplate.opsForHash().size(cartKey);
    if (currentSize >= MAX_CART_ITEMS)
        throw new CartLimitExceededException("장바구니는 최대 200개 상품까지 담을 수 있습니다.");

    redisTemplate.opsForHash().increment(cartKey, productId, quantity);
}
```

### 장바구니 조회 API (재고·가격 통합)

```java
@GetMapping("/cart")
public CartResponse getCart(
        @AuthenticationPrincipal Long userId,
        @CookieValue(required = false) String guestId) {

    String cartKey = userId != null
            ? "cart:user:" + userId
            : "cart:guest:" + guestId;

    Map<String, String> rawItems = redisTemplate.opsForHash().entries(cartKey);
    if (rawItems.isEmpty()) return CartResponse.empty();

    // Product Service 일괄 조회 — N+1 방지
    Map<String, ProductInfo> productMap =
        productService.getProductsBulk(new ArrayList<>(rawItems.keySet()));

    List<CartItem> items = rawItems.keySet().stream()
        .map(pid -> {
            ProductInfo info = productMap.get(pid);
            int qty = Integer.parseInt(rawItems.get(pid));
            return CartItem.builder()
                .productId(pid).name(info.getName()).quantity(qty)
                .currentPrice(info.getCurrentPrice())
                .stockStatus(info.getStockStatus())
                .isAvailable(info.getStock() > 0)
                .build();
        })
        .collect(Collectors.toList());

    return CartResponse.of(items);
}
```

### RDB 스키마

```sql
CREATE TABLE cart_items (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id     BIGINT       NOT NULL,
    product_id  VARCHAR(64)  NOT NULL,
    quantity    INT          NOT NULL DEFAULT 1,
    added_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_product (user_id, product_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB;

-- 담을 당시 가격 기록 (감사·분석용)
CREATE TABLE cart_price_snapshots (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id      BIGINT         NOT NULL,
    product_id   VARCHAR(64)    NOT NULL,
    price_at_add DECIMAL(12,2)  NOT NULL,
    added_at     DATETIME       NOT NULL,
    INDEX idx_user_added (user_id, added_at)
) ENGINE=InnoDB;
```

`UNIQUE KEY uq_user_product`는 같은 사용자가 같은 상품을 중복 INSERT할 때 자동으로 막습니다.

### 결제 시 재고 Hard Lock

```java
@Transactional
public OrderResult checkout(Long userId, List<String> productIds) {
    Map<String, Integer> cartItems = getCartItems(userId);

    // 데드락 방지: productId 오름차순으로 항상 동일 순서로 락
    List<String> sortedIds = productIds.stream().sorted().collect(Collectors.toList());

    for (String productId : sortedIds) {
        Stock stock = stockRepository.findByProductIdForUpdate(productId);
        int required = cartItems.get(productId);
        if (stock.getAvailable() < required)
            throw new OutOfStockException(productId, stock.getAvailable(), required);
        stock.reserve(required);
    }

    validatePrices(cartItems);
    return orderService.createOrder(userId, cartItems);
}
```

항상 `productId` 오름차순으로 락을 잡아야 교착 상태를 방지합니다. Thread 1이 A→B, Thread 2가 B→A 순서로 잡으면 교착이 발생합니다.

---

## 4. 장애 시나리오와 대응

### Redis 전체 장애

- **게스트 장바구니**: Redis가 원본이므로 완전 유실. "일시적으로 담기 기능을 사용할 수 없습니다" 배너 표시가 복잡한 복구 로직보다 낫습니다.
- **로그인 회원**: RDB에 원본이 있어 Fallback 가능합니다.

```java
public Map<String, String> getCartItems(String cartKey, Long userId) {
    try {
        return redisTemplate.opsForHash().entries(cartKey);
    } catch (RedisConnectionException e) {
        if (userId != null) {
            return cartRepository.findByUserId(userId).stream()
                .collect(Collectors.toMap(
                    CartItem::getProductId,
                    item -> String.valueOf(item.getQuantity())));
        }
        return Collections.emptyMap();
    }
}
```

### 블랙프라이데이: 동시 10만 명이 장바구니 담기

MySQL Write-Through가 10만 건 INSERT/UPDATE를 동시에 처리하면 병목이 됩니다. 이벤트 트래픽 시 Write-Back(비동기)으로 전환합니다.

```
1. Redis 즉시 업데이트 (응답 반환)
2. Kafka로 cart.updated 이벤트 발행
3. MySQL Worker가 비동기로 RDB 반영 (배치 INSERT ON DUPLICATE KEY UPDATE)
```

### 병합 중 서버 재시작

Kafka로 병합 이벤트를 처리해 멱등성을 보장합니다.

```
1. 로그인 이벤트 → Kafka cart.merge 토픽 발행
2. Merge Worker: Redis 게스트 → 회원 병합
3. RDB에 병합 완료 기록 (merge_log 테이블)
4. Kafka 커밋
서버 재시작 시: 미커밋 메시지 재처리 → merge_log로 중복 병합 방지
```

---

## 5. 확장 포인트

**위시리스트 분리**: 장바구니(TTL 7일, 단기 구매 의도)와 위시리스트(TTL 없음, 장기 관심)는 저장 목적이 다릅니다. 별도 `wish_items` 테이블로 분리하고 "위시리스트에서 장바구니로 이동" API를 제공합니다.

**그룹 장바구니**: 여러 사람이 하나의 장바구니를 공유하는 기능. 키를 `cart:group:{groupId}`로 하고 각 상품에 담은 사람의 userId를 메타데이터로 추가합니다. 동시 수정 충돌은 Redis Lua Script로 처리합니다.

**멀티 셀러 장바구니**: `cart_items`에 `seller_id`를 추가하고 결제 시 셀러별 주문 그룹으로 분리합니다.

---

## 면접 포인트

### 면접 포인트 1️⃣ "Redis 장애 시 게스트 장바구니가 유실되어도 괜찮은가?"

비즈니스 트레이드오프의 문제입니다. 게스트의 60~70%가 결제 없이 이탈한다는 점을 감안하면, 모든 게스트 장바구니를 RDB에도 저장하는 것은 비용 대비 효과가 낮습니다. Redis Cluster + AOF persistence로 구성하면 단일 노드 장애에서 유실 위험을 거의 없앨 수 있습니다.

### 면접 포인트 2️⃣ "병합 전략에서 수량 합산 vs 로그인 우선 중 어떤 것이 맞는가?"

- 정답은 없고 **제품 방향성**에 달려 있습니다.
- 올리브영처럼 "최근 담은 것을 존중" → 게스트 우선
- 쿠팡처럼 "장기 고객의 위시를 존중" → 로그인 우선
- **수량 합산**이 가장 보수적이고 데이터 유실이 없어 기본값으로 적합. 단, 수량 상한(99개) 반드시 적용

### 면접 포인트 3️⃣ "결제 시 재고 Hard Lock의 데드락을 어떻게 방지하는가?"

항상 동일한 순서(productId 오름차순)로 락을 잡습니다. Thread 1이 A→B, Thread 2가 B→A 순서로 잡으면 교착이 발생합니다. 정렬된 순서로 잡으면 두 스레드 모두 A를 먼저 시도하므로 하나만 진행하고 나머지는 대기합니다. MySQL InnoDB의 `innodb_lock_wait_timeout`을 5초로 설정해 교착 발생 시 자동 롤백 안전망도 함께 구성합니다.

### 면접 포인트 4️⃣ "장바구니 조회 QPS가 매우 높을 때 Product Service 호출을 어떻게 줄이는가?"

두 가지를 조합합니다.

- **Local Cache(Caffeine, TTL 30초)**: Cart Service 내부 캐시로 반복 호출 흡수
- **인기 상품 Top 1000 별도 캐싱**: 가격·재고를 Cart Service Redis에 보관

이 두 가지로 Product Service 호출의 90%를 줄일 수 있습니다. 단, 품절 이벤트는 즉시 캐시 무효화가 필요합니다.

### 면접 포인트 5️⃣ "가격이 결제 직전에 인상됐을 때 사용자에게 어떻게 알리는가?"

결제 요청(POST /orders)에서 장바구니 각 상품 가격을 스냅샷과 비교합니다. 가격이 상승한 상품이 있으면 `HTTP 409 Conflict`와 함께 변경된 상품 목록과 새 가격을 반환합니다. 프론트엔드는 "가격이 변경되었습니다. 새 가격으로 계속 진행하시겠습니까?" 다이얼로그를 표시합니다. 가격이 하락한 경우에는 조용히 최신 가격을 적용합니다.
