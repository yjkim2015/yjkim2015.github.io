---
title: "Spring Cloud Gateway 완전 정리 — 아키텍처, 필터, 라우팅, 실전 패턴"
categories:
- SPRING
toc: true
toc_sticky: true
toc_label: 목차
---

Spring Cloud Gateway는 마이크로서비스 아키텍처(MSA)에서 단일 진입점 역할을 하는 API Gateway입니다. Netty 기반 비동기-논블로킹 방식으로 동작하며, Route / Predicate / Filter 세 가지 핵심 개념을 중심으로 설계되어 있습니다. 이 글에서는 Spring Cloud Gateway의 필요성부터 아키텍처, 필터, 라우팅, 인증/인가, Rate Limiting, Circuit Breaker, 모니터링, 극한 시나리오, 실무 Best Practice까지 완전히 정리합니다.

---

## 1. API Gateway란? 왜 필요한가?

### MSA에서의 문제 — 클라이언트가 마이크로서비스를 직접 호출하면

모놀리식 아키텍처에서는 클라이언트가 단일 서버와 통신합니다. 하지만 MSA에서는 수십~수백 개의 서비스가 분산되어 있습니다. 클라이언트가 각 서비스를 직접 호출할 경우 다음 문제가 발생합니다.

```
[클라이언트]
    |
    |--- HTTP --> [주문 서비스 :8081]
    |--- HTTP --> [상품 서비스 :8082]
    |--- HTTP --> [회원 서비스 :8083]
    |--- HTTP --> [결제 서비스 :8084]
    |--- HTTP --> [배송 서비스 :8085]
```

**문제점 목록:**

1. **클라이언트 복잡도 증가** — 각 서비스의 주소, 포트, 프로토콜을 클라이언트가 모두 알아야 합니다.
2. **인증/인가 중복 구현** — 각 서비스마다 JWT 검증 로직을 반복합니다.
3. **CORS 처리 분산** — 모든 서비스에서 CORS 설정을 관리해야 합니다.
4. **로드밸런싱 불가** — 클라이언트는 서비스 인스턴스가 몇 개인지 알 수 없습니다.
5. **공통 관심사(Cross-Cutting Concern) 중복** — 로깅, 추적, Rate Limiting을 서비스마다 구현합니다.
6. **서비스 주소 노출** — 내부 서비스 IP/포트가 외부에 노출됩니다.

### API Gateway의 역할

```
[클라이언트]
    |
    v
[API Gateway] <--- 단일 진입점
    |
    |-- 인증/인가 (JWT 검증)
    |-- Rate Limiting (트래픽 제어)
    |-- 로드밸런싱 (lb://order-service)
    |-- 라우팅 (/order/** -> 주문 서비스)
    |-- 로깅/추적 (MDC, Zipkin)
    |-- Circuit Breaker (Resilience4j)
    |
    +---> [주문 서비스] (내부망)
    +---> [상품 서비스] (내부망)
    +---> [회원 서비스] (내부망)
    +---> [결제 서비스] (내부망)
```

API Gateway는 다음 역할을 담당합니다.

- **단일 진입점(Single Entry Point)**: 모든 외부 요청이 Gateway를 통과합니다.
- **인증/인가**: JWT 토큰 검증, OAuth2 처리를 중앙화합니다.
- **로드밸런싱**: 서비스 레지스트리(Eureka)와 연동하여 요청을 분산합니다.
- **라우팅**: URL 패턴, 헤더, 메서드 기반으로 요청을 적절한 서비스로 전달합니다.
- **공통 필터**: 로깅, 추적 ID 주입, 응답 변환을 한 곳에서 처리합니다.
- **트래픽 제어**: Rate Limiting, Circuit Breaker, Retry로 시스템을 보호합니다.

---

### Netflix Zuul → Spring Cloud Gateway 전환 이유

Netflix Zuul 1.x는 서블릿 기반 동기-블로킹 모델입니다. 각 요청마다 스레드를 점유하므로 대규모 동시 연결 처리에 한계가 있습니다.

| 항목 | Netflix Zuul 1.x | Netflix Zuul 2.x | Spring Cloud Gateway |
|---|---|---|---|
| 기반 | Servlet (블로킹) | Netty (비동기) | Netty (비동기) |
| 프로그래밍 모델 | 동기 | 비동기 | Reactive (WebFlux) |
| Spring Boot 통합 | 보통 | 복잡 | 완벽 |
| 유지보수 | Netflix 주도 | Netflix 주도 | Spring 팀 주도 |
| Spring Cloud 지원 | 공식 지원 | 미지원 | 공식 지원 |
| WebSocket | 제한적 | 지원 | 지원 |
| 성능 | 낮음 | 높음 | 높음 |

Zuul 2.x는 Netflix에서 공개했지만 Spring Cloud가 공식 통합을 지원하지 않아 실무에서 채택이 어렵습니다. Spring Cloud Gateway는 Spring 팀이 직접 개발하여 Spring Boot/Cloud 생태계와 완벽하게 통합됩니다.

---

### Spring Cloud Gateway vs Netflix Zuul vs Kong vs Nginx 비교

| 항목 | Spring Cloud Gateway | Netflix Zuul 1.x | Kong | Nginx |
|---|---|---|---|---|
| 언어 | Java (Spring) | Java (Netflix) | Lua (OpenResty) | C |
| 비동기 | 완전 비동기 | 동기 | 비동기 | 비동기 |
| 프로그래밍 | Java/Kotlin 코드 | Java 코드 | Lua 플러그인 | 설정 파일 |
| Spring 통합 | 완벽 | 보통 | 없음 | 없음 |
| 서비스 디스커버리 | Eureka/Consul | Eureka | DNS | 수동 |
| Rate Limiting | Redis 연동 | 미지원 (직접 구현) | 내장 | 플러그인 |
| Circuit Breaker | Resilience4j | 미지원 | 플러그인 | 없음 |
| 성능 | 높음 | 낮음 | 매우 높음 | 매우 높음 |
| 학습 비용 | 낮음 (Java) | 낮음 (Java) | 높음 (Lua) | 중간 |
| 적합 환경 | Spring MSA | 레거시 Spring | 언어 무관 대규모 | 정적/단순 프록시 |

**선택 기준:**
- Spring Boot 기반 MSA → Spring Cloud Gateway
- 언어 무관, 플러그인 생태계 필요 → Kong
- 단순 리버스 프록시, 최고 성능 → Nginx
- 기존 Netflix OSS 스택 → Zuul (신규 프로젝트에는 비권장)

---

## 2. 아키텍처

### Netty 기반 비동기/논블로킹

Spring Cloud Gateway는 Spring WebFlux 위에서 동작하며, 이는 곧 Netty 이벤트 루프 모델을 사용한다는 의미입니다.

```
[클라이언트 요청]
        |
        v
  [Netty Event Loop]
  (CPU 코어 수 스레드)
        |
        v
  [비동기 처리 파이프라인]
  (스레드 점유 없이 I/O 완료 이벤트 대기)
        |
        v
  [업스트림 서비스 응답]
        |
        v
  [클라이언트 응답]
```

**블로킹 vs 논블로킹 비교:**

```
[블로킹 (Zuul 1.x)]
Thread-1: 요청수신 → [DB 대기...........] → 응답  (스레드 점유)
Thread-2: 요청수신 → [API 대기.....] → 응답      (스레드 점유)
Thread-3: 요청수신 → [파일 대기........] → 응답   (스레드 점유)
1만 요청 = 1만 스레드 = ~10GB 메모리

[논블로킹 (Spring Cloud Gateway)]
Event Loop: 요청수신 → I/O 등록 → 다음요청 처리
           [I/O 완료 이벤트] → 응답 전송
4개 스레드로 1만 요청 처리 가능
```

---

### Route → Predicate → Filter 구조

Spring Cloud Gateway의 핵심 개념 세 가지입니다.

```
┌─────────────────────────────────────────────────────────┐
│                    Spring Cloud Gateway                  │
│                                                         │
│  Route (라우트)                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  ID: order-route                                │    │
│  │  URI: lb://order-service                        │    │
│  │                                                 │    │
│  │  Predicate (조건)          Filter (처리)         │    │
│  │  ┌──────────────────┐    ┌──────────────────┐  │    │
│  │  │ Path=/order/**   │    │ AddRequestHeader  │  │    │
│  │  │ Method=GET,POST  │ +  │ RewritePath      │  │    │
│  │  │ Header=X-Api-Key │    │ CircuitBreaker   │  │    │
│  │  └──────────────────┘    └──────────────────┘  │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

- **Route**: Gateway의 라우팅 단위. ID, 목적지 URI, Predicate 목록, Filter 목록으로 구성됩니다.
- **Predicate**: 요청이 특정 라우트에 해당하는지 판단하는 조건. `java.util.function.Predicate<ServerWebExchange>` 기반입니다.
- **Filter**: 요청/응답을 가로채어 변환하는 컴포넌트. Pre Filter(요청 전)와 Post Filter(응답 후)로 나뉩니다.

---

### HandlerMapping → WebHandler → Filter Chain 처리 흐름

```
HTTP 요청
    │
    ▼
┌─────────────────────────┐
│   HttpWebHandlerAdapter │  (Netty → WebFlux 진입점)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  RoutePredicateHandler  │  (라우트 매칭)
│  Mapping                │  모든 Route의 Predicate를
│                         │  순서대로 평가
└────────────┬────────────┘
             │ 매칭된 Route
             ▼
┌─────────────────────────┐
│  FilteringWebHandler    │  (필터 체인 구성)
│                         │  GlobalFilter + GatewayFilter
│                         │  order 값 기준 정렬
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Filter Chain          │
│                         │
│  [Pre Filters]          │  순서대로 실행
│   ↓ GlobalFilter 1      │  (낮은 order 먼저)
│   ↓ GlobalFilter 2      │
│   ↓ GatewayFilter A     │
│   ↓ GatewayFilter B     │
│                         │
│  [Proxied Request]      │  업스트림 서비스 호출
│   ↓                     │
│  [Post Filters]         │  역순으로 실행
│   ↑ GatewayFilter B     │  (높은 order 먼저)
│   ↑ GatewayFilter A     │
│   ↑ GlobalFilter 2      │
│   ↑ GlobalFilter 1      │
└────────────┬────────────┘
             │
             ▼
         HTTP 응답
```

**핵심 클래스:**

- `RoutePredicateHandlerMapping`: 들어온 요청에 매칭되는 Route를 찾습니다.
- `FilteringWebHandler`: 매칭된 Route의 필터 목록과 GlobalFilter를 합쳐 체인을 구성합니다.
- `NettyRoutingFilter`: 실제 업스트림 서비스로 HTTP 요청을 프록시합니다.
- `NettyWriteResponseFilter`: 업스트림 응답을 클라이언트에 씁니다.

---

## 3. Route 설정

### 의존성 추가

```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-gateway</artifactId>
</dependency>
```

```groovy
// build.gradle
implementation 'org.springframework.cloud:spring-cloud-starter-gateway'
```

> Spring Cloud Gateway는 WebFlux 기반이므로 `spring-boot-starter-web`(서블릿)과 함께 사용할 수 없습니다. 의존성 충돌이 발생합니다.

---

### application.yml 기반 설정

```yaml
spring:
  cloud:
    gateway:
      routes:
        # 주문 서비스 라우트
        - id: order-route
          uri: lb://order-service          # 로드밸런서 사용
          predicates:
            - Path=/api/orders/**          # 경로 매칭
            - Method=GET,POST              # HTTP 메서드
          filters:
            - StripPrefix=1               # /api 제거 후 전달
            - AddRequestHeader=X-Gateway-Source, spring-cloud-gateway

        # 상품 서비스 라우트
        - id: product-route
          uri: lb://product-service
          predicates:
            - Path=/api/products/**
            - Header=X-Api-Version, v2    # 헤더 조건
          filters:
            - RewritePath=/api/products/(?<segment>.*), /products/${segment}

        # 회원 서비스 라우트 (인증 불필요 경로)
        - id: member-public-route
          uri: lb://member-service
          predicates:
            - Path=/api/members/login, /api/members/register
            - Method=POST
          order: 1                        # 낮을수록 우선순위 높음

        # 회원 서비스 라우트 (인증 필요 경로)
        - id: member-auth-route
          uri: lb://member-service
          predicates:
            - Path=/api/members/**
          filters:
            - name: CircuitBreaker
              args:
                name: memberCircuitBreaker
                fallbackUri: forward:/fallback/member
          order: 2

      # 전역 기본 필터
      default-filters:
        - AddResponseHeader=X-Gateway-Version, 1.0
        - DedupeResponseHeader=Access-Control-Allow-Credentials Access-Control-Allow-Origin

      # CORS 전역 설정
      globalcors:
        cors-configurations:
          '[/**]':
            allowedOriginPatterns: "*"
            allowedMethods:
              - GET
              - POST
              - PUT
              - DELETE
              - OPTIONS
            allowedHeaders: "*"
            allowCredentials: true
            maxAge: 3600
```

---

### Java DSL (RouteLocatorBuilder)

코드로 라우트를 정의하면 동적 라우팅, 조건 분기, 재사용이 용이합니다.

```java
@Configuration
public class GatewayConfig {

    @Bean
    public RouteLocator customRouteLocator(RouteLocatorBuilder builder) {
        return builder.routes()

            // 주문 서비스 라우트
            .route("order-route", r -> r
                .path("/api/orders/**")
                .and()
                .method(HttpMethod.GET, HttpMethod.POST)
                .filters(f -> f
                    .stripPrefix(1)
                    .addRequestHeader("X-Gateway-Source", "spring-cloud-gateway")
                    .addResponseHeader("X-Route-Id", "order-route")
                    .circuitBreaker(c -> c
                        .setName("orderCB")
                        .setFallbackUri("forward:/fallback/order")
                    )
                )
                .uri("lb://order-service")
            )

            // 상품 서비스 — 경로 재작성
            .route("product-route", r -> r
                .path("/api/products/**")
                .filters(f -> f
                    .rewritePath("/api/products/(?<segment>.*)", "/products/${segment}")
                    .retry(config -> config
                        .setRetries(3)
                        .setMethods(HttpMethod.GET)
                        .setBackoff(Duration.ofMillis(100), Duration.ofSeconds(1), 2, true)
                    )
                )
                .uri("lb://product-service")
            )

            // 정적 파일 — 특정 호스트 기반 라우팅
            .route("static-route", r -> r
                .host("static.example.com")
                .uri("http://cdn.example.com")
            )

            .build();
    }
}
```

---

### Predicate 종류

**Path Predicate**

```yaml
predicates:
  - Path=/api/orders/{orderId}, /api/orders/**
```

```java
.path("/api/orders/{orderId}", "/api/orders/**")
```

**Host Predicate**

```yaml
predicates:
  - Host=**.example.com, api.example.org
```

**Method Predicate**

```yaml
predicates:
  - Method=GET, POST, PUT
```

**Header Predicate** — 정규표현식 지원

```yaml
predicates:
  - Header=X-Api-Key, \w{32}   # 32자 영숫자
```

**Query Predicate**

```yaml
predicates:
  - Query=page, \d+            # page 파라미터가 숫자
  - Query=version              # version 파라미터 존재 여부만 확인
```

**Cookie Predicate**

```yaml
predicates:
  - Cookie=session-id, .+
```

**Weight Predicate** — 카나리 배포

```yaml
routes:
  - id: service-v1
    uri: lb://service-v1
    predicates:
      - Weight=service-group, 90    # 90% 트래픽

  - id: service-v2
    uri: lb://service-v2
    predicates:
      - Weight=service-group, 10    # 10% 트래픽 (카나리)
```

**Between / Before / After Predicate** — 시간 기반

```yaml
predicates:
  - Between=2024-01-01T00:00:00+09:00[Asia/Seoul], 2024-12-31T23:59:59+09:00[Asia/Seoul]
```

**커스텀 Predicate**

```java
@Component
public class CustomHeaderRoutePredicateFactory
        extends AbstractRoutePredicateFactory<CustomHeaderRoutePredicateFactory.Config> {

    public CustomHeaderRoutePredicateFactory() {
        super(Config.class);
    }

    @Override
    public Predicate<ServerWebExchange> apply(Config config) {
        return exchange -> {
            String headerValue = exchange.getRequest()
                    .getHeaders()
                    .getFirst(config.getHeaderName());
            return config.getExpectedValue().equals(headerValue);
        };
    }

    @Override
    public List<String> shortcutFieldOrder() {
        return List.of("headerName", "expectedValue");
    }

    @Data
    public static class Config {
        private String headerName;
        private String expectedValue;
    }
}
```

```yaml
predicates:
  - CustomHeader=X-Internal-Token, secret123
```

---

## 4. Filter

필터는 요청과 응답을 가로채어 처리하는 핵심 컴포넌트입니다. 종류는 크게 두 가지입니다.

- **GatewayFilter**: 특정 라우트에만 적용됩니다.
- **GlobalFilter**: 모든 라우트에 적용됩니다.

### Pre / Post Filter 동작 순서

```
클라이언트 요청
      │
      ▼
[Pre Filter 실행 (order 오름차순)]
  GlobalFilter (order=-1) pre
  GlobalFilter (order=0) pre
  GatewayFilter A (order=1) pre
  GatewayFilter B (order=2) pre
      │
      ▼
[업스트림 서비스 호출]
      │
      ▼
[Post Filter 실행 (order 내림차순)]
  GatewayFilter B (order=2) post
  GatewayFilter A (order=1) post
  GlobalFilter (order=0) post
  GlobalFilter (order=-1) post
      │
      ▼
클라이언트 응답
```

Pre/Post는 명시적 구분이 아닌, `chain.filter(exchange)` 호출 전후로 결정됩니다.

---

### 내장 필터 (Built-in Filters)

**AddRequestHeader / AddResponseHeader**

```yaml
filters:
  - AddRequestHeader=X-Request-Id, {requestId}
  - AddResponseHeader=X-Response-Time, {responseTime}
```

**RemoveRequestHeader / RemoveResponseHeader**

```yaml
filters:
  - RemoveRequestHeader=Cookie
  - RemoveResponseHeader=X-Internal-Header
```

**RewritePath**

```yaml
filters:
  # /api/v1/orders/123 -> /orders/123
  - RewritePath=/api/v1/(?<segment>.*), /${segment}
```

**StripPrefix**

```yaml
filters:
  - StripPrefix=2
  # /api/v1/orders -> /orders (앞 2개 제거)
```

**PrefixPath**

```yaml
filters:
  - PrefixPath=/api
  # /orders -> /api/orders
```

**RedirectTo**

```yaml
filters:
  - RedirectTo=301, https://new.example.com
```

**SetPath**

```yaml
filters:
  - SetPath=/fixed-path/{segment}
```

**RequestRateLimiter**

```yaml
filters:
  - name: RequestRateLimiter
    args:
      redis-rate-limiter.replenishRate: 10    # 초당 토큰 충전
      redis-rate-limiter.burstCapacity: 20    # 최대 버스트
      redis-rate-limiter.requestedTokens: 1   # 요청당 소모 토큰
      key-resolver: "#{@ipKeyResolver}"
```

**CircuitBreaker**

```yaml
filters:
  - name: CircuitBreaker
    args:
      name: orderCircuitBreaker
      fallbackUri: forward:/fallback/order
      statusCodes:
        - 500
        - 503
```

**Retry**

```yaml
filters:
  - name: Retry
    args:
      retries: 3
      statuses: BAD_GATEWAY, SERVICE_UNAVAILABLE
      methods: GET
      backoff:
        firstBackoff: 100ms
        maxBackoff: 500ms
        factor: 2
        basedOnPreviousValue: false
```

**RequestSize**

```yaml
filters:
  - name: RequestSize
    args:
      maxSize: 5MB
```

**SaveSession** — Spring Session과 연동 시

```yaml
filters:
  - SaveSession
```

---

### 커스텀 필터 구현 (AbstractGatewayFilterFactory)

```java
@Component
@Slf4j
public class LoggingGatewayFilterFactory
        extends AbstractGatewayFilterFactory<LoggingGatewayFilterFactory.Config> {

    public LoggingGatewayFilterFactory() {
        super(Config.class);
    }

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            ServerHttpRequest request = exchange.getRequest();

            // Pre Filter: 요청 로깅
            String requestId = UUID.randomUUID().toString();
            long startTime = System.currentTimeMillis();

            log.info("[{}] {} {} - Pre Filter",
                requestId,
                request.getMethod(),
                request.getURI()
            );

            // 요청에 헤더 추가
            ServerHttpRequest modifiedRequest = request.mutate()
                .header("X-Request-Id", requestId)
                .build();

            ServerWebExchange modifiedExchange = exchange.mutate()
                .request(modifiedRequest)
                .build();

            // chain.filter() 이후는 Post Filter
            return chain.filter(modifiedExchange)
                .then(Mono.fromRunnable(() -> {
                    long duration = System.currentTimeMillis() - startTime;
                    ServerHttpResponse response = exchange.getResponse();

                    log.info("[{}] {} {} - Post Filter: status={}, duration={}ms",
                        requestId,
                        request.getMethod(),
                        request.getURI(),
                        response.getStatusCode(),
                        duration
                    );

                    // 응답 헤더 추가
                    response.getHeaders().add("X-Request-Id", requestId);
                    response.getHeaders().add("X-Response-Time", duration + "ms");
                }));
        };
    }

    @Override
    public List<String> shortcutFieldOrder() {
        return List.of("level");
    }

    @Data
    public static class Config {
        private String level = "INFO";  // 로그 레벨 설정
    }
}
```

```yaml
filters:
  - name: Logging
    args:
      level: DEBUG
```

---

### GlobalFilter 구현

GlobalFilter는 모든 라우트에 자동으로 적용됩니다. `Ordered` 인터페이스로 실행 순서를 지정합니다.

```java
@Component
@Slf4j
public class AuthenticationGlobalFilter implements GlobalFilter, Ordered {

    private static final String AUTHORIZATION_HEADER = "Authorization";
    private static final String BEARER_PREFIX = "Bearer ";

    // 인증 불필요 경로
    private static final List<String> WHITE_LIST = List.of(
        "/api/members/login",
        "/api/members/register",
        "/actuator/health"
    );

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();

        // 화이트리스트 경로는 통과
        if (isWhiteListed(path)) {
            return chain.filter(exchange);
        }

        String authHeader = exchange.getRequest()
            .getHeaders()
            .getFirst(AUTHORIZATION_HEADER);

        if (authHeader == null || !authHeader.startsWith(BEARER_PREFIX)) {
            return unauthorizedResponse(exchange);
        }

        String token = authHeader.substring(BEARER_PREFIX.length());

        return validateToken(token)
            .flatMap(claims -> {
                // 검증된 정보를 헤더에 추가
                ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
                    .header("X-User-Id", claims.getSubject())
                    .header("X-User-Role", claims.get("role", String.class))
                    .build();

                return chain.filter(exchange.mutate().request(mutatedRequest).build());
            })
            .onErrorResume(e -> {
                log.warn("Token validation failed: {}", e.getMessage());
                return unauthorizedResponse(exchange);
            });
    }

    private boolean isWhiteListed(String path) {
        return WHITE_LIST.stream().anyMatch(path::startsWith);
    }

    private Mono<Claims> validateToken(String token) {
        return Mono.fromCallable(() -> {
            // JWT 검증 로직
            return Jwts.parserBuilder()
                .setSigningKey(signingKey)
                .build()
                .parseClaimsJws(token)
                .getBody();
        });
    }

    private Mono<Void> unauthorizedResponse(ServerWebExchange exchange) {
        exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
        exchange.getResponse().getHeaders().add(
            HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE
        );
        String body = "{\"error\": \"Unauthorized\", \"message\": \"Invalid or missing token\"}";
        DataBuffer buffer = exchange.getResponse().bufferFactory()
            .wrap(body.getBytes(StandardCharsets.UTF_8));
        return exchange.getResponse().writeWith(Mono.just(buffer));
    }

    @Override
    public int getOrder() {
        return -100;  // 낮을수록 먼저 실행 (Pre Filter 기준)
    }
}
```

---

## 5. 로드밸런싱

### Spring Cloud LoadBalancer 연동

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-loadbalancer</artifactId>
</dependency>
```

`lb://` 프로토콜을 URI에 사용하면 Spring Cloud LoadBalancer가 서비스 레지스트리에서 인스턴스 목록을 가져와 라운드로빈(기본) 방식으로 분산합니다.

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-route
          uri: lb://order-service     # lb:// → LoadBalancer 사용
          predicates:
            - Path=/api/orders/**
```

```
Gateway → LoadBalancer → [order-service:8081]
                       → [order-service:8082]
                       → [order-service:8083]
```

---

### 로드밸런싱 전략 커스터마이징

기본 전략은 RoundRobin입니다. RandomLoadBalancer로 변경할 수 있습니다.

```java
@Configuration
@LoadBalancerClient(name = "order-service", configuration = OrderServiceLoadBalancerConfig.class)
public class LoadBalancerConfig {
}

public class OrderServiceLoadBalancerConfig {

    @Bean
    ReactorLoadBalancer<ServiceInstance> randomLoadBalancer(
            Environment environment,
            LoadBalancerClientFactory loadBalancerClientFactory) {
        String name = environment.getProperty(LoadBalancerClientFactory.PROPERTY_NAME);
        return new RandomLoadBalancer(
            loadBalancerClientFactory.getLazyProvider(name, ServiceInstanceListSupplier.class),
            name
        );
    }
}
```

---

### Eureka 서비스 디스커버리 연동

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-netflix-eureka-client</artifactId>
</dependency>
```

```yaml
eureka:
  client:
    service-url:
      defaultZone: http://eureka-server:8761/eureka/
  instance:
    prefer-ip-address: true

spring:
  cloud:
    gateway:
      discovery:
        locator:
          enabled: true              # Eureka에서 자동으로 라우트 생성
          lower-case-service-id: true
```

`discovery.locator.enabled: true`를 설정하면 Eureka에 등록된 모든 서비스에 대해 `/서비스명/**` 형태의 라우트가 자동 생성됩니다.

```
/order-service/** → lb://order-service
/product-service/** → lb://product-service
```

---

### Consul 서비스 디스커버리 연동

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-consul-discovery</artifactId>
</dependency>
```

```yaml
spring:
  cloud:
    consul:
      host: consul-server
      port: 8500
      discovery:
        service-name: api-gateway
        health-check-interval: 10s
```

---

## 6. 인증/인가

### JWT 토큰 검증 필터 구현

완성된 JWT 검증 필터 예시입니다.

```java
@Component
@Slf4j
public class JwtAuthenticationFilter implements GlobalFilter, Ordered {

    @Value("${jwt.secret}")
    private String jwtSecret;

    private Key signingKey;

    @PostConstruct
    public void init() {
        byte[] keyBytes = Base64.getDecoder().decode(jwtSecret);
        this.signingKey = Keys.hmacShaKeyFor(keyBytes);
    }

    // 인증 불필요 경로 목록
    private static final AntPathMatcher PATH_MATCHER = new AntPathMatcher();
    private static final List<String> EXCLUDE_PATHS = List.of(
        "/api/auth/**",
        "/api/public/**",
        "/actuator/health",
        "/actuator/info"
    );

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getPath().value();

        if (isExcluded(path)) {
            return chain.filter(exchange);
        }

        return Mono.justOrEmpty(
                exchange.getRequest().getHeaders().getFirst(HttpHeaders.AUTHORIZATION)
            )
            .filter(header -> header.startsWith("Bearer "))
            .map(header -> header.substring(7))
            .flatMap(this::parseToken)
            .flatMap(claims -> {
                ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
                    .header("X-User-Id", claims.getSubject())
                    .header("X-User-Email", claims.get("email", String.class))
                    .header("X-User-Role", claims.get("role", String.class))
                    .build();
                log.debug("Authenticated user: {}", claims.getSubject());
                return chain.filter(exchange.mutate().request(mutatedRequest).build());
            })
            .switchIfEmpty(Mono.defer(() -> sendError(exchange, HttpStatus.UNAUTHORIZED,
                "Missing or invalid Authorization header")))
            .onErrorResume(ExpiredJwtException.class, e ->
                sendError(exchange, HttpStatus.UNAUTHORIZED, "Token expired"))
            .onErrorResume(JwtException.class, e ->
                sendError(exchange, HttpStatus.UNAUTHORIZED, "Invalid token"));
    }

    private Mono<Claims> parseToken(String token) {
        return Mono.fromCallable(() ->
            Jwts.parserBuilder()
                .setSigningKey(signingKey)
                .build()
                .parseClaimsJws(token)
                .getBody()
        ).subscribeOn(Schedulers.boundedElastic());
        // JWT 파싱은 CPU-bound → boundedElastic 스케줄러 사용
    }

    private boolean isExcluded(String path) {
        return EXCLUDE_PATHS.stream()
            .anyMatch(pattern -> PATH_MATCHER.match(pattern, path));
    }

    private Mono<Void> sendError(ServerWebExchange exchange, HttpStatus status, String message) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(status);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);

        String body = String.format(
            "{\"status\":%d,\"error\":\"%s\",\"message\":\"%s\"}",
            status.value(), status.getReasonPhrase(), message
        );

        DataBuffer buffer = response.bufferFactory()
            .wrap(body.getBytes(StandardCharsets.UTF_8));
        return response.writeWith(Mono.just(buffer));
    }

    @Override
    public int getOrder() {
        return -200;
    }
}
```

---

### Spring Security + Gateway 연동

Spring Cloud Gateway는 WebFlux 기반이므로 **Reactive Spring Security**를 사용합니다.

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>
```

```java
@Configuration
@EnableWebFluxSecurity
public class SecurityConfig {

    @Bean
    public SecurityWebFilterChain springSecurityFilterChain(ServerHttpSecurity http) {
        return http
            .csrf(ServerHttpSecurity.CsrfSpec::disable)
            .httpBasic(ServerHttpSecurity.HttpBasicSpec::disable)
            .formLogin(ServerHttpSecurity.FormLoginSpec::disable)
            .authorizeExchange(exchanges -> exchanges
                .pathMatchers("/api/auth/**", "/actuator/health").permitAll()
                .pathMatchers(HttpMethod.GET, "/api/products/**").permitAll()
                .pathMatchers("/api/admin/**").hasRole("ADMIN")
                .anyExchange().authenticated()
            )
            .oauth2ResourceServer(oauth2 -> oauth2
                .jwt(jwt -> jwt.jwtDecoder(jwtDecoder()))
            )
            .build();
    }

    @Bean
    public ReactiveJwtDecoder jwtDecoder() {
        return NimbusReactiveJwtDecoder
            .withSecretKey(secretKey())
            .build();
    }

    private SecretKey secretKey() {
        byte[] keyBytes = Base64.getDecoder().decode(jwtSecret);
        return Keys.hmacShaKeyFor(keyBytes);
    }
}
```

---

### OAuth2 Resource Server

```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: https://auth.example.com
          # jwk-set-uri: https://auth.example.com/.well-known/jwks.json
```

```java
@Bean
public SecurityWebFilterChain springSecurityFilterChain(ServerHttpSecurity http) {
    return http
        .oauth2ResourceServer(oauth2 -> oauth2
            .jwt(jwt -> jwt
                .jwtAuthenticationConverter(jwtAuthenticationConverter())
            )
        )
        .build();
}

@Bean
public Converter<Jwt, Mono<AbstractAuthenticationToken>> jwtAuthenticationConverter() {
    JwtGrantedAuthoritiesConverter authoritiesConverter = new JwtGrantedAuthoritiesConverter();
    authoritiesConverter.setAuthorityPrefix("ROLE_");
    authoritiesConverter.setAuthoritiesClaimName("roles");

    ReactiveJwtAuthenticationConverterAdapter adapter =
        new ReactiveJwtAuthenticationConverterAdapter(
            new JwtAuthenticationConverter() {{
                setJwtGrantedAuthoritiesConverter(authoritiesConverter);
            }}
        );
    return adapter;
}
```

---

## 7. Rate Limiting

### RequestRateLimiter + Redis

Token Bucket 알고리즘 기반으로 Redis를 통해 분산 Rate Limiting을 구현합니다.

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis-reactive</artifactId>
</dependency>
```

```yaml
spring:
  data:
    redis:
      host: redis-server
      port: 6379

  cloud:
    gateway:
      routes:
        - id: order-route
          uri: lb://order-service
          predicates:
            - Path=/api/orders/**
          filters:
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 10    # 초당 10개 토큰 충전
                redis-rate-limiter.burstCapacity: 20    # 최대 버스트 20개
                redis-rate-limiter.requestedTokens: 1   # 요청당 1개 소모
                key-resolver: "#{@userKeyResolver}"     # KeyResolver 빈 참조
```

**Token Bucket 동작 원리:**

```
시간  → 0s  1s  2s  3s  4s  5s
토큰 충전 → +10  +10  +10  +10  +10  +10   (replenishRate=10)
버스트 용량: 20

버스트: 첫 2초 동안 20개 요청 즉시 허용 (용량 소진)
정상: 이후 초당 10개 요청만 허용
초과: 429 Too Many Requests 반환
```

---

### KeyResolver (IP별, 사용자별)

```java
@Configuration
public class RateLimiterConfig {

    // IP 기반 Rate Limiting
    @Bean
    public KeyResolver ipKeyResolver() {
        return exchange -> Mono.justOrEmpty(
            exchange.getRequest().getRemoteAddress()
        )
        .map(addr -> addr.getAddress().getHostAddress())
        .defaultIfEmpty("unknown");
    }

    // 사용자 ID 기반 Rate Limiting (JWT에서 추출)
    @Bean
    public KeyResolver userKeyResolver() {
        return exchange -> Mono.justOrEmpty(
            exchange.getRequest().getHeaders().getFirst("X-User-Id")
        )
        .defaultIfEmpty("anonymous");
    }

    // API 키 기반 Rate Limiting
    @Bean
    public KeyResolver apiKeyResolver() {
        return exchange -> Mono.justOrEmpty(
            exchange.getRequest().getHeaders().getFirst("X-Api-Key")
        )
        .switchIfEmpty(
            Mono.justOrEmpty(
                exchange.getRequest().getQueryParams().getFirst("api_key")
            )
        )
        .defaultIfEmpty("anonymous");
    }
}
```

**경로별 다른 Rate Limit 적용:**

```yaml
routes:
  # 일반 API: 초당 10 요청
  - id: api-standard
    uri: lb://api-service
    predicates:
      - Path=/api/standard/**
    filters:
      - name: RequestRateLimiter
        args:
          redis-rate-limiter.replenishRate: 10
          redis-rate-limiter.burstCapacity: 20
          key-resolver: "#{@userKeyResolver}"

  # 프리미엄 API: 초당 100 요청
  - id: api-premium
    uri: lb://api-service
    predicates:
      - Path=/api/premium/**
      - Header=X-Tier, premium
    filters:
      - name: RequestRateLimiter
        args:
          redis-rate-limiter.replenishRate: 100
          redis-rate-limiter.burstCapacity: 200
          key-resolver: "#{@userKeyResolver}"
```

**커스텀 RateLimiter 구현:**

```java
@Component
public class CustomRedisRateLimiter extends AbstractRateLimiter<CustomRedisRateLimiter.Config> {

    @Override
    public Mono<Response> isAllowed(String routeId, String id) {
        Config config = getConfig().getOrDefault(routeId, new Config());

        // 커스텀 토큰 버킷 로직
        String key = "rate_limiter:" + routeId + ":" + id;

        return redisTemplate.execute(rateLimiterScript, keys, args)
            .map(results -> {
                boolean allowed = ((Long) results.get(0)) == 1L;
                long remainingTokens = (Long) results.get(1);

                Map<String, String> headers = new HashMap<>();
                headers.put("X-RateLimit-Remaining", String.valueOf(remainingTokens));
                headers.put("X-RateLimit-Limit", String.valueOf(config.getReplenishRate()));

                return new Response(allowed, headers);
            });
    }

    @Data
    public static class Config {
        private int replenishRate = 10;
        private int burstCapacity = 20;
    }
}
```

---

## 8. Circuit Breaker

### Resilience4j 연동

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-circuitbreaker-reactor-resilience4j</artifactId>
</dependency>
```

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-route
          uri: lb://order-service
          predicates:
            - Path=/api/orders/**
          filters:
            - name: CircuitBreaker
              args:
                name: orderCircuitBreaker
                fallbackUri: forward:/fallback/order
                statusCodes:             # 이 상태코드를 실패로 간주
                  - 500
                  - 502
                  - 503
                  - 504

resilience4j:
  circuitbreaker:
    instances:
      orderCircuitBreaker:
        sliding-window-size: 10           # 최근 10번의 호출로 판단
        failure-rate-threshold: 50        # 50% 이상 실패 시 OPEN
        wait-duration-in-open-state: 10s  # OPEN 후 10초 대기
        permitted-number-of-calls-in-half-open-state: 3  # HALF-OPEN에서 3회 테스트
        minimum-number-of-calls: 5        # 최소 5회 호출 후 판단

  timelimiter:
    instances:
      orderCircuitBreaker:
        timeout-duration: 3s             # 3초 초과 시 실패 처리
```

---

### Circuit Breaker 상태 머신

```
        실패율 >= threshold
CLOSED ─────────────────────► OPEN
  ▲                              │
  │ 성공                         │ wait-duration 경과
  │                              ▼
  └──────────────────── HALF-OPEN
        성공 >= permitted calls
```

- **CLOSED**: 정상 상태. 모든 요청 허용.
- **OPEN**: 장애 상태. 모든 요청 즉시 실패 처리 (Fallback 실행).
- **HALF-OPEN**: 회복 시도. 제한된 수의 요청만 허용. 성공 시 CLOSED, 실패 시 OPEN으로 전환.

---

### 폴백 라우트 설정

```java
@RestController
@Slf4j
public class FallbackController {

    @GetMapping("/fallback/order")
    public Mono<ResponseEntity<Map<String, Object>>> orderFallback(ServerWebExchange exchange) {
        log.warn("Order service circuit breaker triggered");

        Map<String, Object> response = Map.of(
            "status", "SERVICE_UNAVAILABLE",
            "message", "주문 서비스가 일시적으로 사용 불가합니다. 잠시 후 다시 시도해주세요.",
            "timestamp", Instant.now().toString()
        );

        return Mono.just(ResponseEntity
            .status(HttpStatus.SERVICE_UNAVAILABLE)
            .contentType(MediaType.APPLICATION_JSON)
            .body(response)
        );
    }

    @GetMapping("/fallback/product")
    public Mono<ResponseEntity<Map<String, Object>>> productFallback() {
        Map<String, Object> response = Map.of(
            "status", "SERVICE_UNAVAILABLE",
            "message", "상품 서비스를 현재 이용할 수 없습니다.",
            "data", Collections.emptyList()  // 빈 목록 반환 (Graceful Degradation)
        );

        return Mono.just(ResponseEntity
            .status(HttpStatus.SERVICE_UNAVAILABLE)
            .body(response)
        );
    }
}
```

---

### Retry + Circuit Breaker 조합

```yaml
filters:
  # Retry 먼저 시도, 모두 실패하면 Circuit Breaker 동작
  - name: Retry
    args:
      retries: 2
      statuses: BAD_GATEWAY, SERVICE_UNAVAILABLE
      methods: GET
      backoff:
        firstBackoff: 50ms
        maxBackoff: 200ms
        factor: 2

  - name: CircuitBreaker
    args:
      name: orderCircuitBreaker
      fallbackUri: forward:/fallback/order
```

> 순서 주의: Retry가 CircuitBreaker보다 먼저 적용되도록 설정합니다. Circuit Breaker가 OPEN 상태일 때는 Retry 없이 즉시 Fallback으로 전환됩니다.

---

## 9. 모니터링

### Actuator Endpoints

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics, gateway, circuitbreakers, ratelimiters
  endpoint:
    health:
      show-details: always
    gateway:
      enabled: true
```

**주요 Gateway Actuator Endpoints:**

| Endpoint | 설명 |
|---|---|
| `GET /actuator/gateway/routes` | 등록된 모든 라우트 목록 |
| `GET /actuator/gateway/routes/{id}` | 특정 라우트 상세 정보 |
| `POST /actuator/gateway/routes/{id}` | 라우트 동적 추가 |
| `DELETE /actuator/gateway/routes/{id}` | 라우트 동적 삭제 |
| `POST /actuator/gateway/refresh` | 라우트 캐시 갱신 |
| `GET /actuator/gateway/globalfilters` | 전역 필터 목록 |
| `GET /actuator/gateway/routefilters` | 라우트 필터 팩토리 목록 |

---

### Micrometer 메트릭

Spring Cloud Gateway는 Micrometer를 통해 다음 메트릭을 자동으로 노출합니다.

```
# 라우트별 요청 수
spring.cloud.gateway.requests_total{routeId="order-route", outcome="SUCCESS"}

# 라우트별 응답 시간
spring.cloud.gateway.requests_seconds{routeId="order-route", outcome="SUCCESS"}

# Circuit Breaker 상태
resilience4j.circuitbreaker.state{name="orderCircuitBreaker", state="CLOSED"}

# Rate Limiter
spring.cloud.gateway.requests_total{routeId="order-route", outcome="FORWARD_ERROR"}
```

**Prometheus + Grafana 연동:**

```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

```yaml
management:
  metrics:
    export:
      prometheus:
        enabled: true
  endpoints:
    web:
      exposure:
        include: prometheus
```

---

### 요청/응답 로깅 필터

```java
@Component
@Slf4j
public class RequestLoggingGlobalFilter implements GlobalFilter, Ordered {

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String traceId = generateTraceId();

        // MDC에 추적 ID 설정 (WebFlux는 Context 사용)
        return chain.filter(exchange.mutate()
                .request(request.mutate()
                    .header("X-Trace-Id", traceId)
                    .build())
                .build())
            .contextWrite(Context.of("traceId", traceId))
            .doOnSubscribe(s ->
                log.info(">>> {} {} [traceId={}] headers={}",
                    request.getMethod(),
                    request.getURI(),
                    traceId,
                    sanitizeHeaders(request.getHeaders())
                )
            )
            .doOnSuccess(v -> {
                HttpStatus status = exchange.getResponse().getStatusCode();
                log.info("<<< {} {} [traceId={}] status={}",
                    request.getMethod(),
                    request.getURI(),
                    traceId,
                    status
                );
            })
            .doOnError(e ->
                log.error("!!! {} {} [traceId={}] error={}",
                    request.getMethod(),
                    request.getURI(),
                    traceId,
                    e.getMessage()
                )
            );
    }

    private String generateTraceId() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    }

    private Map<String, String> sanitizeHeaders(HttpHeaders headers) {
        Map<String, String> sanitized = new LinkedHashMap<>();
        headers.forEach((key, values) -> {
            if (!key.equalsIgnoreCase(HttpHeaders.AUTHORIZATION)) {
                sanitized.put(key, String.join(", ", values));
            } else {
                sanitized.put(key, "[REDACTED]");
            }
        });
        return sanitized;
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }
}
```

**Zipkin 분산 추적 연동:**

```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-brave</artifactId>
</dependency>
<dependency>
    <groupId>io.zipkin.reporter2</groupId>
    <artifactId>zipkin-reporter-brave</artifactId>
</dependency>
```

```yaml
management:
  tracing:
    sampling:
      probability: 1.0    # 100% 샘플링 (프로덕션은 0.1~0.5 권장)
  zipkin:
    tracing:
      endpoint: http://zipkin:9411/api/v2/spans
```

---

## 10. 극한 시나리오

### Gateway 자체 장애 시 — 다중 인스턴스, Health Check

API Gateway가 단일 인스턴스라면 SPOF(Single Point of Failure)가 됩니다.

```
                      [Load Balancer (L4/L7)]
                      /          |           \
              [Gateway-1]  [Gateway-2]  [Gateway-3]
                  ↑              ↑              ↑
              [Health Check: /actuator/health]
              실패 시 자동으로 제외
```

**필요한 설정:**

```yaml
# 상태 확인 상세 설정
management:
  endpoint:
    health:
      show-details: always
      probes:
        enabled: true          # liveness, readiness probe 활성화
  health:
    livenessstate:
      enabled: true
    readinessstate:
      enabled: true
    redis:
      enabled: true            # Redis 연결 상태 포함
    circuitbreakers:
      enabled: true

# Kubernetes Liveness/Readiness Probe 예시
# livenessProbe:
#   httpGet:
#     path: /actuator/health/liveness
#     port: 8080
# readinessProbe:
#   httpGet:
#     path: /actuator/health/readiness
#     port: 8080
```

**Graceful Shutdown 설정:**

```yaml
server:
  shutdown: graceful         # 진행 중인 요청 처리 후 종료

spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s   # 최대 30초 대기
```

---

### 하위 서비스 지연 전파 — Timeout + Circuit Breaker

하위 서비스가 느려지면 Gateway의 커넥션 풀이 고갈되어 전체 시스템이 마비될 수 있습니다.

```
상황: product-service 응답 시간 30초 (정상: 100ms)

[클라이언트 요청] → [Gateway] → [product-service: 30초 대기]
                                        │
                   연결이 모두 소진되면  │
                   다른 서비스도 영향    │
                                        ▼
                   [order-service 요청도 실패] ← 커넥션 풀 고갈
```

**방어 설정:**

```yaml
spring:
  cloud:
    gateway:
      httpclient:
        connect-timeout: 1000    # 연결 타임아웃 1초
        response-timeout: 5s     # 응답 타임아웃 5초

      routes:
        - id: product-route
          uri: lb://product-service
          predicates:
            - Path=/api/products/**
          filters:
            # 개별 라우트 타임아웃 (전역 설정 override)
            - name: RequestHeaderSize
            - name: CircuitBreaker
              args:
                name: productCB
                fallbackUri: forward:/fallback/product
            - name: Retry
              args:
                retries: 2
                statuses: GATEWAY_TIMEOUT, SERVICE_UNAVAILABLE

resilience4j:
  timelimiter:
    instances:
      productCB:
        timeout-duration: 3s    # Circuit Breaker 타임아웃
```

**Netty 커넥션 풀 설정:**

```yaml
spring:
  cloud:
    gateway:
      httpclient:
        pool:
          type: elastic           # 동적 커넥션 풀
          max-connections: 1000   # 최대 커넥션 수
          acquire-timeout: 2000   # 커넥션 획득 대기 시간
          max-idle-time: 30s      # 유휴 커넥션 유지 시간
          max-life-time: 60s      # 커넥션 최대 수명
```

---

### 메모리 누수 — WebFlux 스트림 미처리

WebFlux에서 Mono/Flux 스트림을 구독하지 않으면 메모리 누수가 발생합니다.

**잘못된 예시:**

```java
// 절대 하면 안 됨
@Override
public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
    // Mono를 반환하지 않고 사이드 이펙트만 실행 — subscribe()로 실행 후 잊어버림
    someAsyncOperation().subscribe();  // 메모리 누수 가능성
    return chain.filter(exchange);
}
```

**올바른 예시:**

```java
@Override
public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
    return someAsyncOperation()
        .then(chain.filter(exchange))   // 체인으로 연결
        .doOnError(e -> log.error("Filter error", e));
}
```

**요청 바디 읽기 시 주의사항:**

```java
// 요청 바디는 한 번만 읽을 수 있음 → 캐싱 필요
@Override
public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
    return DataBufferUtils.join(exchange.getRequest().getBody())
        .flatMap(dataBuffer -> {
            byte[] bytes = new byte[dataBuffer.readableByteCount()];
            dataBuffer.read(bytes);
            DataBufferUtils.release(dataBuffer);  // 반드시 해제!

            // 새로운 요청으로 교체
            ServerHttpRequest mutatedRequest = new ServerHttpRequestDecorator(exchange.getRequest()) {
                @Override
                public Flux<DataBuffer> getBody() {
                    return Flux.just(exchange.getResponse().bufferFactory().wrap(bytes));
                }
            };

            return chain.filter(exchange.mutate().request(mutatedRequest).build());
        });
}
```

---

### CORS 이슈

Gateway와 각 서비스 모두 CORS를 설정하면 헤더가 중복되어 브라우저가 오류를 발생시킵니다.

**증상:**

```
Access-Control-Allow-Origin: *, *    ← 중복 값 → 브라우저 거부
```

**해결책:**

```yaml
# Gateway에서 CORS 통합 관리
spring:
  cloud:
    gateway:
      globalcors:
        cors-configurations:
          '[/**]':
            allowedOriginPatterns:
              - "https://*.example.com"
              - "http://localhost:3000"
            allowedMethods: "*"
            allowedHeaders: "*"
            allowCredentials: true

      # 하위 서비스에서 중복된 CORS 헤더 제거
      default-filters:
        - DedupeResponseHeader=Access-Control-Allow-Credentials Access-Control-Allow-Origin
```

각 마이크로서비스에서는 CORS 설정을 제거하고, Gateway에서만 관리합니다.

---

## 11. 실무 Best Practice + 구성 예제

### 전체 구성 예제

```yaml
server:
  port: 8080
  shutdown: graceful

spring:
  application:
    name: api-gateway
  lifecycle:
    timeout-per-shutdown-phase: 30s

  data:
    redis:
      host: ${REDIS_HOST:localhost}
      port: ${REDIS_PORT:6379}

  cloud:
    gateway:
      # 전역 타임아웃
      httpclient:
        connect-timeout: 1000
        response-timeout: 10s
        pool:
          type: elastic
          max-connections: 2000
          acquire-timeout: 3000

      # 전역 필터
      default-filters:
        - AddResponseHeader=X-Gateway-Version, 1.0
        - DedupeResponseHeader=Access-Control-Allow-Credentials Access-Control-Allow-Origin

      # CORS
      globalcors:
        cors-configurations:
          '[/**]':
            allowedOriginPatterns:
              - "https://*.example.com"
            allowedMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
            allowedHeaders: "*"
            allowCredentials: true
            maxAge: 3600

      routes:
        # 인증 서비스 (인증 불필요)
        - id: auth-route
          uri: lb://auth-service
          predicates:
            - Path=/api/auth/**
          filters:
            - StripPrefix=1
          order: 1

        # 주문 서비스
        - id: order-route
          uri: lb://order-service
          predicates:
            - Path=/api/orders/**
          filters:
            - StripPrefix=1
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 20
                redis-rate-limiter.burstCapacity: 40
                key-resolver: "#{@userKeyResolver}"
            - name: CircuitBreaker
              args:
                name: orderCB
                fallbackUri: forward:/fallback/order
            - name: Retry
              args:
                retries: 2
                statuses: BAD_GATEWAY, SERVICE_UNAVAILABLE
                methods: GET
          order: 10

        # 상품 서비스 (공개 읽기)
        - id: product-read-route
          uri: lb://product-service
          predicates:
            - Path=/api/products/**
            - Method=GET
          filters:
            - StripPrefix=1
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 50
                redis-rate-limiter.burstCapacity: 100
                key-resolver: "#{@ipKeyResolver}"
            - AddResponseHeader=Cache-Control, public, max-age=60
          order: 10

        # Fallback 라우트
        - id: fallback-route
          uri: no://op
          predicates:
            - Path=/fallback/**
          order: 999

resilience4j:
  circuitbreaker:
    instances:
      orderCB:
        sliding-window-size: 10
        failure-rate-threshold: 50
        wait-duration-in-open-state: 15s
        permitted-number-of-calls-in-half-open-state: 3
        minimum-number-of-calls: 5
      productCB:
        sliding-window-size: 20
        failure-rate-threshold: 40
        wait-duration-in-open-state: 10s
  timelimiter:
    instances:
      orderCB:
        timeout-duration: 5s
      productCB:
        timeout-duration: 3s

management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics, prometheus, gateway
  endpoint:
    health:
      show-details: when-authorized
      probes:
        enabled: true
  metrics:
    tags:
      application: ${spring.application.name}
  tracing:
    sampling:
      probability: 0.1

logging:
  level:
    org.springframework.cloud.gateway: INFO
    reactor.netty: WARN
```

---

### Best Practice 체크리스트

**1. 라우트 설계**

- 라우트 ID는 명확하고 유일하게 설정합니다. (`order-route`, `product-read-route`)
- `order` 값으로 라우트 우선순위를 명시합니다. 특수 경로(공개 API)는 낮은 order로 먼저 매칭합니다.
- `StripPrefix`를 사용하여 Gateway 경로 접두사(`/api`)를 서비스에 전달하지 않습니다.

**2. 필터 설계**

- GlobalFilter에서 모든 인증을 처리하고 검증된 정보를 헤더로 전달합니다.
- 화이트리스트 경로는 GlobalFilter에서 명시적으로 처리합니다.
- 필터에서 블로킹 코드(`Thread.sleep()`, JDBC) 사용을 절대 금지합니다.
- 요청 바디 읽기 후 반드시 `DataBufferUtils.release()` 호출합니다.

**3. 보안**

- 인증 헤더(`Authorization`)는 로깅에서 반드시 마스킹합니다.
- 내부 서비스 정보가 담긴 헤더(`X-Internal-*`)는 외부 요청에서 제거합니다.
- HTTPS를 Gateway 앞단(L4/L7 LB)에서 종료하거나 Gateway에서 직접 TLS를 처리합니다.

**4. 성능**

- Redis Rate Limiter는 Redis 장애 시 요청을 허용(fail-open) 혹은 거부(fail-closed)할 정책을 결정합니다. 기본은 fail-open입니다.
- Netty 커넥션 풀은 업스트림 서비스 수와 예상 동시 요청 수를 기반으로 산정합니다.
- 프로덕션 환경에서 분산 추적 샘플링 비율은 5~10%로 설정합니다.

**5. 운영**

- `/actuator/gateway/routes` API를 통해 동적 라우트 갱신이 가능합니다. 재배포 없이 라우트를 변경할 수 있습니다.
- Circuit Breaker 상태를 Grafana 대시보드로 실시간 모니터링합니다.
- 카나리 배포 시 Weight Predicate로 트래픽을 점진적으로 전환합니다.

```java
// 운영 중 라우트 동적 추가 (RouteDefinitionWriter 활용)
@RestController
@RequiredArgsConstructor
public class GatewayAdminController {

    private final RouteDefinitionWriter routeDefinitionWriter;
    private final ApplicationEventPublisher publisher;

    @PostMapping("/admin/routes")
    public Mono<Void> addRoute(@RequestBody RouteDefinition routeDefinition) {
        return routeDefinitionWriter.save(Mono.just(routeDefinition))
            .doOnSuccess(v -> publisher.publishEvent(new RefreshRoutesEvent(this)));
    }

    @DeleteMapping("/admin/routes/{id}")
    public Mono<Void> deleteRoute(@PathVariable String id) {
        return routeDefinitionWriter.delete(Mono.just(id))
            .doOnSuccess(v -> publisher.publishEvent(new RefreshRoutesEvent(this)));
    }
}
```

---

Spring Cloud Gateway는 MSA 환경에서 인증, 트래픽 제어, 장애 격리, 라우팅을 한 곳에서 처리하는 강력한 도구입니다. Netty 비동기 모델 위에서 동작하므로 높은 처리량을 유지하면서도 WebFlux, Spring Security, Resilience4j 등 Spring 생태계와 자연스럽게 통합됩니다. 핵심은 GlobalFilter로 공통 관심사를 중앙화하고, Circuit Breaker와 Rate Limiter로 시스템을 보호하며, 다중 인스턴스 배포와 Graceful Shutdown으로 가용성을 확보하는 것입니다.
