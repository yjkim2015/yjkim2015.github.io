---
title: "Spring Cloud Gateway"
categories: SPRING
tags: [SpringCloudGateway, APIGateway, LoadBalancing, RateLimiting, CircuitBreaker]
toc: true
toc_sticky: true
toc_label: 목차
date: 2026-05-01
---

Spring Cloud Gateway는 Spring 생태계의 API Gateway 솔루션이다. Netflix Zuul(블로킹)의 후계자로, Spring WebFlux(Reactor/Netty) 기반의 비동기 논블로킹 방식으로 동작한다. 라우팅, 필터링, 로드밸런싱, 인증, Rate Limiting, Circuit Breaker를 통합 제공한다.

> 비유: 대형 빌딩 로비의 안내 데스크와 같다. 방문객(요청)이 오면 신원 확인(인증), 출입 제한(Rate Limiting), 방문 기록(로깅) 후 각 부서(마이크로서비스)로 안내한다. 각 부서가 아닌 로비에서 모든 공통 절차를 처리한다.

---

## API Gateway 역할

<div class="mermaid">
graph TD
    C[Client] --> GW[API Gateway]
    GW --> A1[인증/인가 검사]
    GW --> A2[Rate Limiting]
    GW --> A3[요청 로깅/추적]
    GW --> A4[SSL 종료]
    GW --> A5[로드밸런싱]
    GW --> R[라우팅]
    R --> US[User Service]
    R --> OS[Order Service]
    R --> PS[Product Service]
    R --> PAY[Payment Service]
</div>

API Gateway가 없으면 각 서비스마다 인증, 로깅, Rate Limiting을 중복 구현해야 한다.

---

## 의존성 설정

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-gateway</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-loadbalancer</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-circuitbreaker-reactor-resilience4j</artifactId>
</dependency>
```

---

## Route / Predicate / Filter

### 3가지 핵심 개념

<div class="mermaid">
graph LR
    REQ[요청] --> P{Predicate 일치?}
    P -->|YES| F[Filter 체인 통과]
    P -->|NO| DROP[무시]
    F --> URI[목적지 URI로 전달]
</div>

### Route 설정 (YAML)

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: user-service
          uri: http://user-service:8081
          predicates:
            - Path=/api/users/**
          filters:
            - StripPrefix=1  # /api 제거 후 전달

        - id: order-service
          uri: lb://order-service  # 서비스 디스커버리 이름
          predicates:
            - Path=/api/orders/**
            - Method=GET,POST
          filters:
            - StripPrefix=1
            - AddRequestHeader=X-Gateway-Source, api-gateway
```

### Route 설정 (Java DSL)

```java
@Configuration
public class GatewayConfig {

    @Bean
    public RouteLocator routeLocator(RouteLocatorBuilder builder) {
        return builder.routes()
            .route("user-service", r -> r
                .path("/api/users/**")
                .filters(f -> f
                    .stripPrefix(1)
                    .addRequestHeader("X-Gateway-Source", "api-gateway")
                    .addResponseHeader("X-Response-Time", LocalDateTime.now().toString())
                )
                .uri("lb://user-service")
            )
            .route("order-service", r -> r
                .path("/api/orders/**")
                .and()
                .method(HttpMethod.GET, HttpMethod.POST)
                .filters(f -> f.stripPrefix(1))
                .uri("lb://order-service")
            )
            .build();
    }
}
```

---

## Predicate

요청이 특정 조건을 만족하는지 검사한다.

```yaml
predicates:
  - Path=/api/**                         # 경로 패턴
  - Method=GET,POST,PUT                  # HTTP 메서드
  - Header=X-Request-Id, \d+            # 헤더 값 (정규식)
  - Query=version, v\d+                  # 쿼리 파라미터
  - Host=**.example.com                  # 호스트
  - Cookie=sessionId, \w+               # 쿠키
  - RemoteAddr=192.168.1.1/24           # 원격 IP
  - Weight=group1, 80                    # 요청 무게 (A/B 테스트)
```

**카나리 배포 예시**
```yaml
routes:
  - id: product-service-v1
    uri: lb://product-service-v1
    predicates:
      - Path=/api/products/**
      - Weight=product, 90  # 90% 트래픽

  - id: product-service-v2
    uri: lb://product-service-v2
    predicates:
      - Path=/api/products/**
      - Weight=product, 10  # 10% 트래픽 (카나리)
```

---

## Filter

요청/응답을 변환하거나 횡단 관심사를 처리한다.

### 내장 필터

```yaml
filters:
  - StripPrefix=1                    # 경로 앞부분 제거 (/api/users → /users)
  - PrefixPath=/v1                   # 경로 앞에 추가 (/users → /v1/users)
  - RewritePath=/api/(?<seg>.*), /$\{seg}  # 경로 재작성
  - AddRequestHeader=X-Source, gateway
  - AddResponseHeader=X-Frame-Options, DENY
  - RemoveRequestHeader=Cookie
  - Retry=3                          # 재시도
  - RedirectTo=302, https://example.com
```

### 커스텀 글로벌 필터

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class RequestLoggingFilter implements GlobalFilter {

    private static final Logger log = LoggerFactory.getLogger(RequestLoggingFilter.class);

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String requestId = UUID.randomUUID().toString();
        long startTime = System.currentTimeMillis();

        log.info("[{}] {} {}", requestId, request.getMethod(), request.getPath());

        return chain.filter(exchange.mutate()
            .request(request.mutate()
                .header("X-Request-Id", requestId)
                .build())
            .build()
        ).then(Mono.fromRunnable(() -> {
            long duration = System.currentTimeMillis() - startTime;
            log.info("[{}] {} {}ms", requestId, exchange.getResponse().getStatusCode(), duration);
        }));
    }
}
```

### 커스텀 인증 필터

```java
@Component
public class AuthenticationGatewayFilterFactory
        extends AbstractGatewayFilterFactory<AuthenticationGatewayFilterFactory.Config> {

    private final JwtTokenProvider jwtTokenProvider;

    public AuthenticationGatewayFilterFactory(JwtTokenProvider jwtTokenProvider) {
        super(Config.class);
        this.jwtTokenProvider = jwtTokenProvider;
    }

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            ServerHttpRequest request = exchange.getRequest();
            String token = extractToken(request);

            if (token == null) {
                return unauthorizedResponse(exchange);
            }

            try {
                Claims claims = jwtTokenProvider.validateAndGetClaims(token);
                ServerHttpRequest modifiedRequest = request.mutate()
                    .header("X-User-Id", claims.getSubject())
                    .header("X-User-Role", claims.get("role", String.class))
                    .build();
                return chain.filter(exchange.mutate().request(modifiedRequest).build());
            } catch (JwtException e) {
                return unauthorizedResponse(exchange);
            }
        };
    }

    private String extractToken(ServerHttpRequest request) {
        String authHeader = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (StringUtils.hasText(authHeader) && authHeader.startsWith("Bearer ")) {
            return authHeader.substring(7);
        }
        return null;
    }

    private Mono<Void> unauthorizedResponse(ServerWebExchange exchange) {
        exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
        return exchange.getResponse().setComplete();
    }

    public static class Config {}
}
```

**라우트에 적용**
```yaml
routes:
  - id: order-service
    uri: lb://order-service
    predicates:
      - Path=/api/orders/**
    filters:
      - Authentication
      - StripPrefix=1
```

---

## 로드밸런싱

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: user-service
          uri: lb://user-service  # lb:// 프로토콜로 서비스 디스커버리 사용
          predicates:
            - Path=/api/users/**
```

**정적 인스턴스 목록 (디스커버리 없이)**
```java
@Configuration
public class LoadBalancerConfig {

    @Bean
    public ServiceInstanceListSupplier serviceInstanceListSupplier() {
        return ServiceInstanceListSupplier.fixed("user-service")
            .instance("localhost", 8081)
            .instance("localhost", 8082)
            .instance("localhost", 8083)
            .build();
    }
}
```

---

## 인증 (OAuth2 / JWT)

### JWT 기반 흐름

<div class="mermaid">
graph LR
    C[Client] --> GW[Gateway]
    GW --> V{JWT 검증}
    V -->|성공| H[X-User-Id 헤더 주입]
    H --> SVC[하위 서비스]
    V -->|실패| U[401 Unauthorized]
    SVC -.->|JWT 직접 검증 불필요| SVC
</div>

### OAuth2 리소스 서버 설정

```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          jwk-set-uri: http://auth-server/.well-known/jwks.json
```

```java
@Configuration
@EnableWebFluxSecurity
public class SecurityConfig {

    @Bean
    public SecurityWebFilterChain securityFilterChain(ServerHttpSecurity http) {
        return http
            .csrf(ServerHttpSecurity.CsrfSpec::disable)
            .authorizeExchange(exchanges -> exchanges
                .pathMatchers("/api/auth/**", "/api/public/**").permitAll()
                .anyExchange().authenticated()
            )
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
            .build();
    }
}
```

---

## Rate Limiting

### Redis 기반 Token Bucket

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis-reactive</artifactId>
</dependency>
```

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: user-service
          uri: lb://user-service
          predicates:
            - Path=/api/users/**
          filters:
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 10    # 초당 10개 토큰 보충
                redis-rate-limiter.burstCapacity: 20    # 최대 버스트 20개
                redis-rate-limiter.requestedTokens: 1
                key-resolver: "#{@userKeyResolver}"
```

```java
@Configuration
public class RateLimitConfig {

    // 사용자별 Rate Limiting
    @Bean
    public KeyResolver userKeyResolver() {
        return exchange -> {
            String userId = exchange.getRequest().getHeaders().getFirst("X-User-Id");
            if (userId != null) {
                return Mono.just(userId);
            }
            // 미인증 사용자는 IP 기반
            return Mono.just(
                Objects.requireNonNull(exchange.getRequest().getRemoteAddress())
                    .getAddress().getHostAddress()
            );
        };
    }

    // API 경로별 Rate Limiting
    @Bean
    public KeyResolver pathKeyResolver() {
        return exchange -> Mono.just(exchange.getRequest().getPath().value());
    }
}
```

---

## Circuit Breaker

### Resilience4j 연동

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-service
          uri: lb://order-service
          predicates:
            - Path=/api/orders/**
          filters:
            - name: CircuitBreaker
              args:
                name: orderServiceCB
                fallbackUri: forward:/fallback/orders
            - name: Retry
              args:
                retries: 3
                statuses: BAD_GATEWAY, SERVICE_UNAVAILABLE
                methods: GET
                backoff:
                  firstBackoff: 100ms
                  maxBackoff: 500ms
                  factor: 2

resilience4j:
  circuitbreaker:
    instances:
      orderServiceCB:
        slidingWindowSize: 10
        minimumNumberOfCalls: 5
        failureRateThreshold: 50
        waitDurationInOpenState: 5s
        permittedNumberOfCallsInHalfOpenState: 3
```

**Fallback 컨트롤러**
```java
@RestController
@RequestMapping("/fallback")
public class FallbackController {

    @GetMapping("/orders")
    public ResponseEntity<Map<String, String>> orderFallback() {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
            .body(Map.of(
                "error", "ORDER_SERVICE_UNAVAILABLE",
                "message", "주문 서비스가 일시적으로 사용 불가합니다. 잠시 후 다시 시도해주세요."
            ));
    }
}
```

---

## 전체 설정 예시

```yaml
spring:
  cloud:
    gateway:
      default-filters:
        - AddResponseHeader=X-Gateway-Version, 1.0

      globalcors:
        cors-configurations:
          '[/**]':
            allowedOrigins: "https://app.example.com"
            allowedMethods: [GET, POST, PUT, DELETE, OPTIONS]
            allowedHeaders: "*"
            allowCredentials: true
            maxAge: 3600

      routes:
        - id: user-service
          uri: lb://user-service
          predicates:
            - Path=/api/users/**
          filters:
            - Authentication
            - StripPrefix=1
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 20
                redis-rate-limiter.burstCapacity: 40
                key-resolver: "#{@userKeyResolver}"
            - name: CircuitBreaker
              args:
                name: userServiceCB
                fallbackUri: forward:/fallback/users

        - id: public-api
          uri: lb://public-service
          predicates:
            - Path=/api/public/**
          filters:
            - StripPrefix=1
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 5
                redis-rate-limiter.burstCapacity: 10
                key-resolver: "#{@pathKeyResolver}"
```

---

## 마치며

Spring Cloud Gateway는 마이크로서비스 아키텍처에서 단일 진입점 역할을 하며, 인증·로깅·Rate Limiting·Circuit Breaker를 각 서비스에서 분리해 관리할 수 있게 한다. WebFlux 기반이라 높은 동시 처리에 적합하지만, 커스텀 필터 작성 시 리액티브 프로그래밍 모델을 반드시 이해해야 한다.
