---
title: "Spring Resilience4j"
categories: SPRING
tags: [Resilience4j, CircuitBreaker, Retry, Bulkhead, RateLimiter, MSA]
toc: true
toc_sticky: true
toc_label: 목차
date: 2026-05-01
---

마이크로서비스 환경에서 외부 서비스 호출은 실패할 수 있다. 한 서비스의 장애가 연쇄적으로 전파돼 전체 시스템이 다운되는 "연쇄 장애(Cascading Failure)"가 가장 위험하다. Resilience4j는 이를 방어하는 경량 내결함성(Fault Tolerance) 라이브러리다.

> **비유**: 전기 두꺼비집(Circuit Breaker)을 생각하라. 과부하가 걸리면 자동으로 전기를 차단해 화재를 방지한다. Resilience4j는 서비스 호출에도 이 두꺼비집을 달아준다. 외부 서비스가 불안정하면 회로를 열어 요청을 차단하고, 일정 시간 후 조심스럽게 다시 연결을 시도한다.

---

## 의존성

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aop</artifactId>
</dependency>
<dependency>
    <groupId>io.github.resilience4j</groupId>
    <artifactId>resilience4j-spring-boot3</artifactId>
</dependency>
<!-- Actuator 메트릭 연동 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

---

## Circuit Breaker

### 개념과 상태 전이

<div class="mermaid">
stateDiagram-v2
    [*] --> CLOSED

    CLOSED --> OPEN : 실패율 임계치 초과\n(예: 50% 이상 실패)
    OPEN --> HALF_OPEN : 대기 시간 경과\n(예: 30초 후)
    HALF_OPEN --> CLOSED : 시험 요청 성공\n(예: 10회 중 8회 성공)
    HALF_OPEN --> OPEN : 시험 요청 실패

    CLOSED : CLOSED\n정상 동작\n모든 요청 통과
    OPEN : OPEN\n회로 차단\n즉시 fallback 반환
    HALF_OPEN : HALF_OPEN\n제한적 요청 허용\n회복 테스트 중
</div>

```
CLOSED: 정상 상태. 모든 요청 허용. 실패율 모니터링.
OPEN:   차단 상태. 모든 요청 즉시 거부 → fallback 실행.
        → 외부 서비스가 이미 불안정하므로 더 이상 요청하지 않음
        → 외부 서비스 회복 시간 확보
HALF-OPEN: 회복 테스트. 제한된 수의 요청만 허용.
           → 성공하면 CLOSED, 실패하면 다시 OPEN
```

### 설정

```yaml
resilience4j:
  circuitbreaker:
    instances:
      user-service:
        # 슬라이딩 윈도우 타입: COUNT_BASED(호출 수) / TIME_BASED(시간)
        sliding-window-type: COUNT_BASED
        # 슬라이딩 윈도우 크기: 최근 10회 호출 기준
        sliding-window-size: 10
        # OPEN 전환 실패율 임계치 (%)
        failure-rate-threshold: 50
        # OPEN → HALF_OPEN 대기 시간
        wait-duration-in-open-state: 30s
        # HALF_OPEN에서 허용할 시험 호출 수
        permitted-number-of-calls-in-half-open-state: 5
        # 슬라이딩 윈도우 시작에 필요한 최소 호출 수
        minimum-number-of-calls: 5
        # 느린 호출 임계치 (이 이상 걸리면 실패로 간주)
        slow-call-duration-threshold: 3s
        # 느린 호출 비율 임계치 (%)
        slow-call-rate-threshold: 80
        # 특정 예외는 무시 (실패 통계에 미포함)
        ignore-exceptions:
          - com.example.BusinessException
        # Circuit Breaker 이벤트 버퍼 크기
        event-consumer-buffer-size: 10
```

### 사용 예시

```java
@Service
public class OrderService {

    private final UserServiceClient userServiceClient;

    @CircuitBreaker(name = "user-service", fallbackMethod = "getUserFallback")
    public UserDto getUser(Long userId) {
        return userServiceClient.getUser(userId);
    }

    // fallback 메서드: 원래 메서드와 동일한 반환 타입, 마지막 파라미터에 Throwable 추가
    private UserDto getUserFallback(Long userId, Throwable throwable) {
        log.warn("Circuit breaker activated for userId: {}, reason: {}",
                 userId, throwable.getMessage());
        // 캐시된 기본값 반환 또는 기본 객체
        return UserDto.builder()
            .id(userId)
            .name("Unknown")
            .build();
    }
}
```

### 상태 모니터링

```bash
# Circuit Breaker 상태 조회
curl http://localhost:8080/actuator/circuitbreakers

# 상태 이벤트 스트림
curl http://localhost:8080/actuator/circuitbreakerevents/user-service
```

```json
{
  "circuitBreakerName": "user-service",
  "state": "CLOSED",
  "failureRate": "20.0%",
  "slowCallRate": "0.0%",
  "bufferedCalls": 10,
  "failedCalls": 2,
  "successfulCalls": 8
}
```

---

## Retry

### 개념

일시적 오류(네트워크 순단, DB 타임아웃)는 즉시 재시도하면 성공할 수 있다. Retry는 지정된 횟수만큼 자동으로 재시도한다.

### 설정

```yaml
resilience4j:
  retry:
    instances:
      payment-service:
        # 최대 재시도 횟수 (첫 시도 포함)
        max-attempts: 3
        # 재시도 간격
        wait-duration: 500ms
        # 지수 백오프 (재시도마다 대기 시간 증가)
        enable-exponential-backoff: true
        exponential-backoff-multiplier: 2
        # 최대 대기 시간 (지수 백오프 상한)
        exponential-max-wait-duration: 5s
        # 재시도할 예외 종류
        retry-exceptions:
          - java.io.IOException
          - java.util.concurrent.TimeoutException
        # 재시도하지 않을 예외 (비즈니스 예외 등)
        ignore-exceptions:
          - com.example.PaymentDeclinedException
```

### 사용 예시

```java
@Service
public class PaymentService {

    @Retry(name = "payment-service", fallbackMethod = "paymentFallback")
    @CircuitBreaker(name = "payment-service")  // Retry + Circuit Breaker 조합
    public PaymentResult processPayment(PaymentRequest request) {
        return paymentClient.process(request);
    }

    private PaymentResult paymentFallback(PaymentRequest request, Throwable t) {
        log.error("Payment failed after retries: {}", t.getMessage());
        // 결제 실패 처리: 대기열에 넣거나 오류 반환
        return PaymentResult.failed("결제 서비스가 일시적으로 불가합니다.");
    }
}
```

### Retry + Exponential Backoff 흐름

```
1회 시도 → 실패
500ms 대기
2회 시도 → 실패
1000ms 대기 (500 × 2)
3회 시도 → 실패
→ 최종 실패, fallback 실행

재시도마다 대기 시간이 증가 → 외부 서비스에 과부하를 주지 않음
Jitter 추가 권장: 여러 인스턴스가 동시에 재시도하는 Thunder Herd 방지
```

---

## Bulkhead

### 개념

한 서비스 호출이 스레드/세마포어를 독점해 다른 서비스 호출까지 막히는 상황을 방지한다.

> **비유**: 선박의 격벽(Bulkhead). 한 구획에 물이 들어와도 격벽이 다른 구획으로 번지는 것을 막는다.

### 스레드 풀 방식 (ThreadPoolBulkhead)

```yaml
resilience4j:
  thread-pool-bulkhead:
    instances:
      slow-external-api:
        # 스레드 풀 크기
        max-thread-pool-size: 10
        # 핵심 스레드 수
        core-thread-pool-size: 5
        # 대기 큐 용량
        queue-capacity: 20
        # 유휴 스레드 유지 시간
        keep-alive-duration: 20ms
```

### 세마포어 방식 (SemaphoreBulkhead)

```yaml
resilience4j:
  bulkhead:
    instances:
      inventory-service:
        # 동시 호출 허용 수
        max-concurrent-calls: 20
        # 포화 시 대기 시간 (0이면 즉시 거부)
        max-wait-duration: 100ms
```

```java
@Service
public class InventoryService {

    @Bulkhead(name = "inventory-service", type = Bulkhead.Type.SEMAPHORE)
    public InventoryDto getInventory(Long productId) {
        return inventoryClient.getInventory(productId);
    }

    @Bulkhead(name = "slow-external-api", type = Bulkhead.Type.THREADPOOL)
    @CircuitBreaker(name = "slow-external-api")
    public CompletableFuture<ExternalData> callSlowApi(String param) {
        return CompletableFuture.supplyAsync(() ->
            externalApiClient.getData(param)
        );
    }
}
```

---

## Rate Limiter

### 개념

단위 시간당 최대 요청 수를 제한한다. 외부 API 쿼터를 지키거나, 내부 서비스 보호에 사용한다.

### 설정

```yaml
resilience4j:
  ratelimiter:
    instances:
      external-api:
        # 갱신 주기 (이 기간마다 허용 횟수 리셋)
        limit-refresh-period: 1s
        # 주기당 허용 요청 수
        limit-for-period: 100
        # 허용 대기 시간 (초과 시 RateLimiterException)
        timeout-duration: 500ms
```

```java
@Service
public class ExternalApiService {

    @RateLimiter(name = "external-api", fallbackMethod = "rateLimitFallback")
    public ApiResponse callExternalApi(String query) {
        return externalApiClient.query(query);
    }

    private ApiResponse rateLimitFallback(String query, RequestNotPermitted ex) {
        log.warn("Rate limit exceeded for query: {}", query);
        return ApiResponse.rateLimited("요청이 너무 많습니다. 잠시 후 재시도하세요.");
    }
}
```

---

## TimeLimiter

### 개념

비동기 호출에 타임아웃을 적용한다. 응답이 느린 서비스가 스레드를 무한정 점유하지 못하도록 한다.

```yaml
resilience4j:
  timelimiter:
    instances:
      report-service:
        # 타임아웃 시간
        timeout-duration: 3s
        # 타임아웃 시 Future 취소 여부
        cancel-running-future: true
```

```java
@Service
public class ReportService {

    @TimeLimiter(name = "report-service", fallbackMethod = "reportFallback")
    @CircuitBreaker(name = "report-service")
    public CompletableFuture<Report> generateReport(ReportRequest request) {
        return CompletableFuture.supplyAsync(() ->
            reportClient.generate(request)  // 3초 초과 시 TimeoutException
        );
    }

    private CompletableFuture<Report> reportFallback(
            ReportRequest request, Throwable t) {
        log.warn("Report generation timed out: {}", t.getMessage());
        return CompletableFuture.completedFuture(
            Report.cached(request.getId())
        );
    }
}
```

---

## 어노테이션 우선순위 조합

여러 어노테이션을 함께 쓸 때 실행 순서가 중요하다.

```java
@Retry(name = "service")           // 4. 가장 바깥: 전체를 재시도
@CircuitBreaker(name = "service")  // 3. 회로 차단
@RateLimiter(name = "service")     // 2. 속도 제한
@Bulkhead(name = "service")        // 1. 가장 안쪽: 동시성 제어
public Result callService(Request request) {
    return client.call(request);
}
```

```
실행 순서 (안쪽 → 바깥쪽):
요청 → Bulkhead → RateLimiter → CircuitBreaker → Retry → 실제 호출
```

<div class="mermaid">
graph LR
    REQ[요청] --> BH[Bulkhead\n동시성 제한]
    BH --> RL[Rate Limiter\n속도 제한]
    RL --> CB[Circuit Breaker\n회로 차단]
    CB --> RT[Retry\n재시도]
    RT --> SVC[실제 서비스 호출]
    SVC -->|실패| RT
    RT -->|최대 재시도 초과| CB
    CB -->|실패율 임계치 초과| OPEN[OPEN 상태\nfallback 실행]
</div>

---

## 프로그래매틱 방식

어노테이션 없이 직접 제어할 수 있다.

```java
@Service
public class OrderService {

    private final CircuitBreakerRegistry circuitBreakerRegistry;
    private final RetryRegistry retryRegistry;

    public OrderService(CircuitBreakerRegistry cbRegistry,
                        RetryRegistry retryRegistry) {
        this.circuitBreakerRegistry = cbRegistry;
        this.retryRegistry = retryRegistry;
    }

    public OrderDto createOrder(OrderRequest request) {
        CircuitBreaker cb = circuitBreakerRegistry.circuitBreaker("inventory");
        Retry retry = retryRegistry.retry("inventory");

        // 데코레이터 패턴으로 조합
        Supplier<InventoryDto> inventorySupplier = CircuitBreaker
            .decorateSupplier(cb, () -> inventoryClient.check(request.getProductId()));

        Supplier<InventoryDto> retryableSupplier = Retry
            .decorateSupplier(retry, inventorySupplier);

        try {
            InventoryDto inventory = retryableSupplier.get();
            return processOrder(request, inventory);
        } catch (CallNotPermittedException e) {
            // Circuit Breaker OPEN 상태
            return OrderDto.queued(request);
        }
    }
}
```

---

## 이벤트 리스너

Circuit Breaker 상태 변화를 실시간으로 감지해 알림을 보낼 수 있다.

```java
@Component
public class CircuitBreakerEventListener {

    private final CircuitBreakerRegistry circuitBreakerRegistry;
    private final AlertService alertService;

    @PostConstruct
    public void subscribeEvents() {
        CircuitBreaker cb = circuitBreakerRegistry.circuitBreaker("user-service");

        cb.getEventPublisher()
            .onStateTransition(event -> {
                log.warn("Circuit Breaker state changed: {} -> {}",
                    event.getStateTransition().getFromState(),
                    event.getStateTransition().getToState());

                if (event.getStateTransition().getToState() == CircuitBreaker.State.OPEN) {
                    // Slack/PagerDuty 알림 발송
                    alertService.sendAlert("Circuit Breaker OPEN: user-service");
                }
            })
            .onFailureRateExceeded(event ->
                log.error("Failure rate exceeded: {}%", event.getFailureRate())
            )
            .onSlowCallRateExceeded(event ->
                log.warn("Slow call rate exceeded: {}%", event.getSlowCallRate())
            );
    }
}
```

---

## 극한 시나리오

### 시나리오 1: 연쇄 장애 (Cascading Failure) 방어

```
상황: Payment Service가 느려짐 (3초 응답)
  Circuit Breaker 없이:
    Order Service → Payment 호출 스레드 점유
    → Order Service 스레드 풀 고갈
    → Order Service도 응답 불가
    → API Gateway도 타임아웃
    → 전체 시스템 다운

  Circuit Breaker + Bulkhead 있을 때:
    Payment Service 느려짐
    → TimeLimiter로 3초 후 타임아웃
    → Circuit Breaker: 실패율 50% 초과 → OPEN
    → 이후 Payment 요청은 즉시 fallback 반환
    → Order Service 스레드 해방 → 정상 동작 유지
    → 30초 후 HALF_OPEN → Payment 회복 테스트
```

### 시나리오 2: Circuit Breaker 튜닝

```
문제: Circuit Breaker가 너무 민감해 자주 OPEN됨
증상: 일시적 오류에도 서킷이 열려 정상 요청도 차단

튜닝 방법:
1. minimum-number-of-calls 늘리기 (최소 30회 이상 관찰)
2. failure-rate-threshold 높이기 (50% → 70%)
3. slow-call-duration-threshold 늘리기 (1s → 5s)
4. wait-duration-in-open-state 조정 (30s → 60s)

문제: Circuit Breaker가 너무 둔감해 장애가 전파됨
튜닝 방법:
1. sliding-window-size 줄이기
2. failure-rate-threshold 낮추기
3. minimum-number-of-calls 줄이기
```

### 시나리오 3: Fallback 전략 설계

```java
// 계층적 fallback 전략
@CircuitBreaker(name = "product-service", fallbackMethod = "getProductFromCache")
public ProductDto getProduct(Long productId) {
    return productServiceClient.getProduct(productId);
}

// 1차 fallback: 캐시에서 조회
private ProductDto getProductFromCache(Long productId, Exception e) {
    return productCache.get(productId)
        .orElseGet(() -> getProductFromDB(productId, e));
}

// 2차 fallback: DB에서 직접 조회
private ProductDto getProductFromDB(Long productId, Exception e) {
    try {
        return productRepository.findById(productId)
            .map(ProductDto::fromEntity)
            .orElseGet(() -> getProductDefault(productId, e));
    } catch (Exception dbException) {
        return getProductDefault(productId, dbException);
    }
}

// 3차 fallback: 기본값 반환
private ProductDto getProductDefault(Long productId, Exception e) {
    log.error("All fallbacks exhausted for productId: {}", productId, e);
    return ProductDto.unavailable(productId);
}
```

---

## Actuator 메트릭 및 모니터링

```yaml
management:
  health:
    circuitbreakers:
      enabled: true
  endpoints:
    web:
      exposure:
        include: health, metrics, circuitbreakers, retries
  metrics:
    tags:
      application: ${spring.application.name}
```

```
주요 메트릭 (Prometheus/Grafana):
resilience4j_circuitbreaker_state              Circuit Breaker 상태 (0=CLOSED, 1=OPEN, 2=HALF_OPEN)
resilience4j_circuitbreaker_failure_rate       실패율
resilience4j_circuitbreaker_calls_total        총 호출 수
resilience4j_retry_calls_total                 재시도 호출 수
resilience4j_bulkhead_available_concurrent_calls  사용 가능한 동시 호출 슬롯
resilience4j_ratelimiter_available_permissions    남은 요청 허용 수
```
