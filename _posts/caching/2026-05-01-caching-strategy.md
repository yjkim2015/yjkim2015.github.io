---
title: "캐싱 전략"
categories:
- CACHING
toc: true
toc_sticky: true
toc_label: 목차
---

## 캐싱이란?

캐싱(Caching)은 자주 사용되는 데이터를 빠르게 접근 가능한 임시 저장소에 보관하여 응답 속도를 높이고 원본 데이터 소스의 부하를 줄이는 기법이다.

```
캐시 없음:
Client → [Application] → [DB] → 응답 (매번 DB 쿼리)
         100ms          200ms    총 300ms

캐시 있음:
Client → [Application] → [Cache] → 응답 (Cache Hit)
         100ms           1ms       총 101ms

                or

Client → [Application] → [Cache Miss] → [DB] → [Cache 저장] → 응답
         100ms           1ms             200ms   1ms            총 302ms (최초 1회)
```

### 캐시 핵심 용어

```
Cache Hit:   요청한 데이터가 캐시에 있음 → 빠른 응답
Cache Miss:  요청한 데이터가 캐시에 없음 → 원본 조회 필요
Cache Hit Ratio = Cache Hit 수 / 전체 요청 수 (높을수록 좋음)

Hot Data:  자주 접근되는 데이터 (캐싱 우선 대상)
Cold Data: 거의 접근되지 않는 데이터
Stale:     캐시 데이터가 원본과 다를 수 있는 상태 (만료됨)
Eviction:  캐시가 꽉 찼을 때 기존 항목 제거
TTL:       Time To Live, 캐시 유효 기간
```

---

## Cache-Aside (Lazy Loading)

가장 일반적인 캐싱 패턴이다. 애플리케이션이 직접 캐시와 DB를 모두 관리한다.

### 읽기 동작

```
1. 애플리케이션이 캐시 조회
2. Cache Hit → 캐시 데이터 반환 (종료)
3. Cache Miss → DB 조회
4. DB 결과를 캐시에 저장 (TTL 설정)
5. DB 결과 반환

┌──────────┐   조회   ┌───────┐  Miss  ┌────┐
│   App    │ ───────→ │ Cache │ ─────→ │ DB │
│          │ ←─────── │       │ ←───── │    │
└──────────┘   반환   └───────┘  저장  └────┘
```

### 구현 예시

```java
@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;
    private final RedisTemplate<String, User> redisTemplate;

    private static final Duration TTL = Duration.ofMinutes(30);

    public User getUser(Long userId) {
        String key = "user:" + userId;
        ValueOperations<String, User> ops = redisTemplate.opsForValue();

        // 1. 캐시 조회
        User cached = ops.get(key);
        if (cached != null) {
            return cached; // Cache Hit
        }

        // 2. Cache Miss → DB 조회
        User user = userRepository.findById(userId)
            .orElseThrow(() -> new UserNotFoundException(userId));

        // 3. 캐시 저장
        ops.set(key, user, TTL);

        return user;
    }

    // 데이터 변경 시 캐시 무효화
    @Transactional
    public void updateUser(Long userId, UserUpdateRequest request) {
        User user = userRepository.findById(userId)
            .orElseThrow(() -> new UserNotFoundException(userId));
        user.update(request);
        userRepository.save(user);

        // 캐시 삭제 (다음 조회 시 DB에서 최신 데이터 로드)
        redisTemplate.delete("user:" + userId);
    }
}
```

### 장단점과 적합한 상황

| 구분 | 내용 |
|------|------|
| **장점** | 실제 요청된 데이터만 캐싱 (효율적 메모리 사용) |
| **장점** | 캐시 장애가 전체 시스템에 영향 없음 (DB로 폴백) |
| **장점** | 구현 단순, 다양한 캐시 시스템과 호환 |
| **단점** | 최초 요청은 항상 Cache Miss (초기 지연) |
| **단점** | DB와 캐시 데이터 일시적 불일치 가능 |
| **단점** | 캐시 스탬피드 취약 |
| **적합** | 읽기 비율이 높은 워크로드 |
| **적합** | 데이터 접근 패턴이 불규칙한 경우 |

---

## Read-Through

캐시가 DB 앞에 위치하여 모든 읽기 요청이 캐시를 통과한다. Cache Miss 시 캐시 자체가 DB를 조회하고 저장한다.

### 동작

```
Client → Cache → (Miss) → DB
            ↑ Miss 시 캐시가 직접 DB 조회 후 저장
            ↓ Hit 시 캐시가 직접 응답

Cache-Aside와 차이:
  Cache-Aside: App이 Cache와 DB 모두 직접 관리
  Read-Through: App은 Cache만 바라봄, DB 접근은 캐시가 담당
```

### 구현 예시 (Spring Cache + 커스텀 로더)

```java
@Configuration
public class CacheConfig {

    @Bean
    public CacheManager cacheManager(RedisConnectionFactory factory) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(30))
            .serializeValuesWith(
                RedisSerializationContext.SerializationPair
                    .fromSerializer(new GenericJackson2JsonRedisSerializer()));

        return RedisCacheManager.builder(factory)
            .cacheDefaults(config)
            .build();
    }
}

@Service
public class ProductService {

    @Cacheable(value = "products", key = "#productId")
    public Product getProduct(Long productId) {
        // Cache Miss 시 이 메서드 실행 → 결과가 자동으로 캐시에 저장
        return productRepository.findById(productId)
            .orElseThrow(() -> new ProductNotFoundException(productId));
    }

    @CacheEvict(value = "products", key = "#productId")
    @Transactional
    public void updateProduct(Long productId, ProductUpdateRequest request) {
        // 캐시 무효화 후 DB 업데이트
        Product product = productRepository.findById(productId)
            .orElseThrow();
        product.update(request);
    }

    @CachePut(value = "products", key = "#result.id")
    @Transactional
    public Product createProduct(ProductCreateRequest request) {
        // 생성 후 즉시 캐시에도 저장
        return productRepository.save(Product.from(request));
    }
}
```

### 장단점

| 구분 | 내용 |
|------|------|
| **장점** | 애플리케이션 코드 단순 (캐싱 로직 분리) |
| **장점** | 항상 캐시를 통해 읽으므로 일관된 인터페이스 |
| **단점** | 캐시 제공자가 DB 접근 로직 내장 필요 |
| **단점** | 처음에는 Cache Miss 불가피 (캐시 웜업 필요) |

---

## Write-Through

데이터를 쓸 때 캐시와 DB에 **동시에** 저장한다. 캐시와 DB가 항상 동기화된다.

### 동작

```
Client → App → Cache → DB (동기 쓰기)
              ↗ 캐시에도 즉시 저장

장점: 읽기 시 항상 최신 데이터
단점: 쓰기 지연 증가 (Cache + DB 모두 완료 후 응답)
```

### 구현 예시

```java
@Service
@RequiredArgsConstructor
public class InventoryService {

    private final InventoryRepository inventoryRepository;
    private final RedisTemplate<String, Integer> redisTemplate;

    @Transactional
    public void updateStock(Long productId, int quantity) {
        // 1. DB 업데이트
        inventoryRepository.updateStock(productId, quantity);

        // 2. 캐시도 즉시 업데이트 (Write-Through)
        String key = "stock:" + productId;
        redisTemplate.opsForValue().set(key, quantity, Duration.ofHours(1));
    }

    public int getStock(Long productId) {
        String key = "stock:" + productId;
        Integer cached = redisTemplate.opsForValue().get(key);
        if (cached != null) return cached;

        int stock = inventoryRepository.findStockByProductId(productId);
        redisTemplate.opsForValue().set(key, stock, Duration.ofHours(1));
        return stock;
    }
}
```

### 장단점과 적합한 상황

| 구분 | 내용 |
|------|------|
| **장점** | 캐시와 DB 항상 일치 (강한 정합성) |
| **장점** | 읽기 시 항상 최신 데이터 보장 |
| **단점** | 쓰기 지연 증가 (캐시+DB 동시 쓰기) |
| **단점** | 읽히지 않는 데이터도 캐시에 저장 (메모리 낭비) |
| **적합** | 금융 잔액, 재고 등 정확성이 중요한 데이터 |
| **적합** | Write-Heavy보다는 Read-Heavy 데이터에 효과적 |

---

## Write-Behind (Write-Back)

데이터를 캐시에만 먼저 쓰고, DB 동기화는 **나중에 비동기**로 처리한다.

### 동작

```
Client → App → Cache (즉시 응답)
                ↓ 비동기
               DB (나중에 배치 처리)

장점: 쓰기 성능 극대화
단점: 캐시 장애 시 캐시에만 있는 데이터 유실 위험
```

### 구현 예시

```java
@Component
@RequiredArgsConstructor
public class ViewCountService {

    private final RedisTemplate<String, Long> redisTemplate;
    private final ArticleRepository articleRepository;

    // 조회수 증가: Redis에만 즉시 기록
    public void incrementViewCount(Long articleId) {
        String key = "viewcount:" + articleId;
        redisTemplate.opsForValue().increment(key);
    }

    // 30초마다 Redis → DB 동기화
    @Scheduled(fixedDelay = 30000)
    public void flushViewCounts() {
        Set<String> keys = redisTemplate.keys("viewcount:*");
        if (keys == null || keys.isEmpty()) return;

        for (String key : keys) {
            Long count = redisTemplate.opsForValue().get(key);
            if (count == null || count == 0) continue;

            Long articleId = Long.parseLong(key.replace("viewcount:", ""));

            // DB 업데이트 후 캐시 초기화
            articleRepository.incrementViewCount(articleId, count);
            redisTemplate.opsForValue().set(key, 0L);
        }
    }
}
```

### 장단점과 적합한 상황

| 구분 | 내용 |
|------|------|
| **장점** | 쓰기 성능 극대화 (캐시 쓰기만큼 빠름) |
| **장점** | DB 부하 대폭 감소 (배치로 묶어서 처리) |
| **단점** | 캐시 장애 시 미동기화 데이터 유실 |
| **단점** | 구현 복잡도 높음 |
| **단점** | 캐시-DB 간 일시적 불일치 |
| **적합** | 조회수, 좋아요 수 등 빈번한 갱신이 필요한 데이터 |
| **적합** | 일부 유실이 허용되는 통계성 데이터 |

---

## Write-Around

쓰기 시 캐시를 **우회**하여 DB에만 저장한다. 읽기 시에만 캐시를 활용한다.

### 동작

```
쓰기: Client → App → DB (캐시 건너뜀)
읽기: Client → App → Cache → (Miss 시) DB → Cache 저장

목적: 한 번 쓰고 거의 읽지 않는 데이터로 캐시 오염 방지
```

### 구현 예시

```java
@Service
@RequiredArgsConstructor
public class LogService {

    private final LogRepository logRepository;
    private final RedisTemplate<String, Log> redisTemplate;

    // 로그 저장: 캐시 우회, DB에만 저장
    @Transactional
    public void saveLog(LogCreateRequest request) {
        logRepository.save(Log.from(request));
        // 캐시에 저장하지 않음 (Write-Around)
    }

    // 최근 로그 조회: 자주 조회되는 경우에만 캐싱
    public List<Log> getRecentLogs(Long userId, int limit) {
        String key = "recent-logs:" + userId;
        List<Log> cached = (List<Log>) redisTemplate.opsForValue().get(key);
        if (cached != null) return cached;

        List<Log> logs = logRepository.findRecentByUserId(userId, limit);
        redisTemplate.opsForValue().set(key, logs, Duration.ofMinutes(5));
        return logs;
    }
}
```

### 장단점

| 구분 | 내용 |
|------|------|
| **장점** | 일회성 데이터로 캐시 메모리 낭비 방지 |
| **장점** | 캐시는 실제 자주 읽히는 데이터만 보유 |
| **단점** | 쓰기 후 최초 읽기는 반드시 Cache Miss |
| **적합** | 로그, 이벤트 기록 등 쓰기 후 잘 읽지 않는 데이터 |

---

## Refresh-Ahead (Read-Ahead)

캐시 만료 **전**에 미리 데이터를 갱신하는 전략이다. TTL 만료로 인한 Cache Miss와 지연을 방지한다.

### 동작

```
TTL = 60초, Refresh Factor = 0.8

t=0s:   캐시 저장
t=48s:  TTL의 80% 시점 → 백그라운드에서 미리 갱신
t=60s:  TTL 만료 전에 이미 새 데이터로 교체

요청이 t=50s에 오면:
  → 캐시 Hit (이미 t=48s에 갱신됨)
  → 지연 없음
```

### 구현 예시

```java
@Component
@RequiredArgsConstructor
public class ExchangeRateCache {

    private final RedisTemplate<String, BigDecimal> redisTemplate;
    private final ExchangeRateApiClient apiClient;

    private static final Duration TTL = Duration.ofMinutes(5);
    private static final double REFRESH_FACTOR = 0.8;

    public BigDecimal getRate(String currency) {
        String key = "rate:" + currency;
        BigDecimal rate = redisTemplate.opsForValue().get(key);

        if (rate == null) {
            // Cache Miss → 동기 갱신
            rate = refreshRate(currency);
        } else {
            // TTL의 80% 지점이면 비동기 갱신
            Long ttl = redisTemplate.getExpire(key, TimeUnit.SECONDS);
            long threshold = (long)(TTL.toSeconds() * (1 - REFRESH_FACTOR));
            if (ttl != null && ttl < threshold) {
                asyncRefresh(currency);
            }
        }

        return rate;
    }

    @Async
    public void asyncRefresh(String currency) {
        refreshRate(currency);
    }

    private BigDecimal refreshRate(String currency) {
        BigDecimal rate = apiClient.fetchRate(currency);
        redisTemplate.opsForValue().set("rate:" + currency, rate, TTL);
        return rate;
    }
}
```

### 장단점

| 구분 | 내용 |
|------|------|
| **장점** | Cache Miss로 인한 지연 거의 없음 |
| **장점** | TTL 만료 시점에 급격한 부하 방지 |
| **단점** | 불필요한 데이터도 미리 갱신 (리소스 낭비 가능) |
| **단점** | 갱신 타이밍 계산 로직 복잡 |
| **적합** | 환율, 주가 등 주기적으로 갱신되는 데이터 |
| **적합** | 지연에 민감한 실시간 서비스 |

---

## 패턴 비교 요약

| 패턴 | 쓰기 주체 | 읽기 주체 | 정합성 | 쓰기 성능 | 복잡도 |
|------|----------|----------|--------|-----------|--------|
| Cache-Aside | App | App | 낮음 | 보통 | 낮음 |
| Read-Through | App | Cache | 낮음 | 보통 | 중간 |
| Write-Through | App | Cache | 높음 | 낮음 | 중간 |
| Write-Behind | Cache | Cache | 낮음 | 높음 | 높음 |
| Write-Around | App(DB만) | App | 중간 | 높음 | 낮음 |
| Refresh-Ahead | Background | Cache | 중간 | - | 높음 |

---

## 데이터 정합성 문제

### 문제 1: Cache Invalidation 타이밍

```
잘못된 순서:
1. DB 업데이트 성공
2. 캐시 삭제 실패 → 구 데이터 계속 서빙

올바른 순서 (Cache-Aside):
1. 캐시 삭제 (먼저)
2. DB 업데이트

또는

DB 업데이트 후 캐시 삭제 실패 시 재시도 로직 필수:
  @Retryable(maxAttempts = 3, backoff = @Backoff(delay = 100))
  public void evictCache(String key) {
      redisTemplate.delete(key);
  }
```

### 문제 2: 동시성 문제 (Race Condition)

```
시나리오:
Thread A: DB 읽기 → (구 데이터) 캐시 저장
Thread B: DB 업데이트 → 캐시 삭제
Thread A: 삭제된 캐시에 구 데이터 저장 → 구 데이터로 오염!

해결:
1. 캐시 저장 시 버전 번호 또는 타임스탬프 포함
   → 새 버전 값이 있으면 덮어쓰지 않음
2. 분산 락 사용 (Redisson)
3. TTL을 짧게 설정하여 자연 만료 빠르게
```

### 문제 3: Double Delete 패턴

```java
// Read-Through + Write-Through 환경에서 안전한 무효화

@Transactional
public void updateUser(Long userId, UserUpdateRequest request) {
    // 1. 캐시 먼저 삭제
    redisTemplate.delete("user:" + userId);

    // 2. DB 업데이트
    userRepository.save(user);

    // 3. 트랜잭션 커밋 후 캐시 재삭제 (이벤트 기반)
    // TransactionalEventListener로 커밋 후 실행 보장
}

@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
public void onUserUpdated(UserUpdatedEvent event) {
    redisTemplate.delete("user:" + event.getUserId());
}
```

---

## 캐시 스탬피드 (Cache Stampede)

### 문제

많이 요청되는 캐시 키가 만료되는 순간, 수많은 요청이 동시에 Cache Miss → DB 쿼리 폭주 발생.

```
t=0: "popular-product:1" 캐시 만료
t=0~0.1s: 1000개 요청 동시 Cache Miss
→ 1000개 DB 쿼리 동시 발생 → DB 과부하 → 장애
```

### 해결책 1: 뮤텍스 락 (Mutex Lock)

```java
public Product getProduct(Long productId) {
    String key = "product:" + productId;
    Product cached = redisTemplate.opsForValue().get(key);
    if (cached != null) return cached;

    // 락 획득 시도 (한 스레드만 DB 조회)
    String lockKey = "lock:" + key;
    Boolean acquired = redisTemplate.opsForValue()
        .setIfAbsent(lockKey, "1", Duration.ofSeconds(5));

    if (Boolean.TRUE.equals(acquired)) {
        try {
            // 락 획득한 스레드만 DB 조회
            Product product = productRepository.findById(productId).orElseThrow();
            redisTemplate.opsForValue().set(key, product, Duration.ofMinutes(10));
            return product;
        } finally {
            redisTemplate.delete(lockKey);
        }
    } else {
        // 락 못 얻은 스레드는 잠깐 대기 후 캐시 재조회
        Thread.sleep(50);
        return getProduct(productId); // 재귀 또는 루프로 재시도
    }
}
```

### 해결책 2: 확률적 조기 만료 (Probabilistic Early Expiration)

```java
public Product getProduct(Long productId) {
    String key = "product:" + productId;
    CachedValue<Product> cached = redisTemplate.opsForValue().get(key);
    if (cached != null) {
        // 남은 TTL이 적을수록 높은 확률로 미리 갱신 (XFetch 알고리즘)
        long remainingTtl = redisTemplate.getExpire(key, TimeUnit.SECONDS);
        double delta = 1.0; // 튜닝 파라미터
        boolean shouldRefresh = Math.random() < (delta * Math.log(remainingTtl) / remainingTtl);
        if (!shouldRefresh) {
            return cached.getValue();
        }
    }

    Product product = productRepository.findById(productId).orElseThrow();
    redisTemplate.opsForValue().set(key, new CachedValue<>(product), Duration.ofMinutes(10));
    return product;
}
```

### 해결책 3: TTL 지터(Jitter) 추가

```java
// 모든 캐시가 같은 시각에 만료되지 않도록 TTL에 랜덤성 추가
Random random = new Random();
Duration ttl = Duration.ofMinutes(10).plusSeconds(random.nextInt(60));
redisTemplate.opsForValue().set(key, value, ttl);
```

---

## 캐시 웜업 (Cache Warmup)

서비스 시작 시 자주 사용되는 데이터를 미리 캐시에 로드한다.

```java
@Component
@RequiredArgsConstructor
public class CacheWarmup implements ApplicationRunner {

    private final ProductService productService;
    private final ProductRepository productRepository;

    @Override
    public void run(ApplicationArguments args) {
        log.info("캐시 웜업 시작");

        // 인기 상품 Top 100 미리 캐싱
        List<Long> popularProductIds = productRepository.findTop100PopularIds();
        popularProductIds.parallelStream().forEach(id -> {
            try {
                productService.getProduct(id); // 조회 시 캐시 저장
            } catch (Exception e) {
                log.warn("캐시 웜업 실패 - productId: {}", id, e);
            }
        });

        log.info("캐시 웜업 완료: {}개 상품", popularProductIds.size());
    }
}
```

---

## 다단계 캐시 (Multi-Level Cache)

### L1 (로컬 캐시) + L2 (Redis) 구조

```
Client → App
              → L1 캐시 (JVM 내 메모리, 수 나노초)
              → L2 캐시 (Redis, 수 밀리초)
              → DB (수십~수백 밀리초)

L1 Hit: 가장 빠름, 네트워크 없음
L1 Miss → L2 Hit: Redis 네트워크 왕복
L2 Miss → DB Hit: DB 쿼리
```

### Spring Boot + Caffeine (L1) + Redis (L2)

```java
@Configuration
public class MultiLevelCacheConfig {

    // L1: Caffeine 로컬 캐시
    @Bean
    public Cache<Long, Product> localCache() {
        return Caffeine.newBuilder()
            .maximumSize(1000)           // 최대 1000개 항목
            .expireAfterWrite(1, TimeUnit.MINUTES)  // 1분 TTL
            .recordStats()
            .build();
    }
}

@Service
@RequiredArgsConstructor
public class ProductService {

    private final Cache<Long, Product> localCache;          // L1
    private final RedisTemplate<String, Product> redis;     // L2
    private final ProductRepository repository;             // DB

    public Product getProduct(Long productId) {
        // L1 조회
        Product product = localCache.getIfPresent(productId);
        if (product != null) {
            return product;
        }

        // L2 조회
        product = redis.opsForValue().get("product:" + productId);
        if (product != null) {
            localCache.put(productId, product);  // L1 저장
            return product;
        }

        // DB 조회
        product = repository.findById(productId).orElseThrow();
        redis.opsForValue().set("product:" + productId, product, Duration.ofMinutes(10)); // L2 저장
        localCache.put(productId, product);  // L1 저장

        return product;
    }
}
```

### 다단계 캐시 주의사항

```
문제: L1 캐시 일관성
  - 여러 애플리케이션 인스턴스가 각자 L1 캐시를 가짐
  - DB 업데이트 시 모든 인스턴스의 L1 캐시 무효화 어려움

해결: Redis Pub/Sub을 이용한 캐시 무효화 이벤트 브로드캐스트

// 캐시 무효화 시
redisTemplate.convertAndSend("cache-invalidation", "product:" + productId);

// 각 인스턴스에서 구독
@Component
public class CacheInvalidationListener implements MessageListener {
    @Override
    public void onMessage(Message message, byte[] pattern) {
        String key = new String(message.getBody());
        String productId = key.replace("product:", "");
        localCache.invalidate(Long.parseLong(productId));
    }
}
```

### L1 vs L2 데이터 분리 전략

```
L1 (로컬, 소용량, 짧은 TTL):
  - 초당 수천 번 이상 읽히는 핫 데이터
  - 크기가 작은 참조 데이터 (코드 테이블, 설정값)
  - 실시간성보다 속도가 중요한 경우

L2 (Redis, 대용량, 긴 TTL):
  - 수 MB 크기의 중형 오브젝트
  - 인스턴스 간 공유가 필요한 세션 데이터
  - 캐시 일관성이 중요한 데이터
```

---

## 캐시 Eviction 정책

| 정책 | 설명 | 적합한 상황 |
|------|------|------------|
| LRU (Least Recently Used) | 가장 오래 사용 안 한 항목 제거 | 최근 접근 데이터 중요 |
| LFU (Least Frequently Used) | 사용 빈도가 가장 낮은 항목 제거 | 인기 데이터 유지 |
| FIFO | 가장 먼저 들어온 항목 제거 | 시간 순서 중요 |
| Random | 무작위 제거 | 단순, 예측 불가 |
| TTL | 만료 시간 기준 제거 | 시간 기반 유효성 |

```
Redis maxmemory-policy 설정:
allkeys-lru:      모든 키 중 LRU 제거
volatile-lru:     TTL 있는 키 중 LRU 제거
allkeys-lfu:      모든 키 중 LFU 제거 (Redis 4.0+)
volatile-ttl:     TTL이 짧은 키부터 제거
noeviction:       메모리 꽉 차면 에러 반환 (기본값)

설정 예시 (redis.conf):
maxmemory 4gb
maxmemory-policy allkeys-lru
```
