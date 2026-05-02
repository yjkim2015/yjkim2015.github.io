---
title: "MDC(Mapped Diagnostic Context) — 분산 환경 로그 추적"
categories:
- SPRING
toc: true
toc_sticky: true
toc_label: 목차
---

새벽 2시에 운영 장애가 났다. 로그를 보니 에러와 정상 로그가 뒤섞여 어느 요청에서 터진 건지 찾을 수가 없다. MDC를 몰랐다면 이 상황에서 로그 전체를 시간순으로 읽어내려가야 한다.

> **비유로 먼저 이해하기**: MDC는 택배 송장번호와 같다. 물류 창고(서버)를 거치는 수백 개의 박스(요청) 중 내 박스를 추적하려면 고유 번호가 있어야 한다. traceId가 바로 그 송장번호다. 어느 서비스, 어느 스레드에서 찍힌 로그든 같은 번호로 한 줄로 이어진다. 다른 배달 기사에게(@Async) 일을 넘기면 송장번호를 복사해줘야(TaskDecorator) 추적이 이어진다.

멀티스레드 웹 서버에서는 수십 개의 요청이 동시에 처리된다. 이때 로그가 뒤섞이면 특정 요청의 전체 흐름을 추적하기가 매우 어렵다. MDC(Mapped Diagnostic Context)는 이 문제를 해결하는 표준 방법이다. SLF4J, Logback, Log4j2 모두 지원한다.

---

## 1. MDC란? 왜 필요한가?

### 문제 상황 — 로그가 뒤섞이는 멀티스레드 환경

MDC 없이는 로그가 다음처럼 뒤섞인다. 에러가 어느 사용자의 어느 요청에서 발생했는지 파악이 불가능하다.

```
[INFO ] OrderService - 주문 처리 시작
[INFO ] OrderService - 주문 처리 시작
[INFO ] PaymentService - 결제 요청
[ERROR] OrderService - 재고 부족
[INFO ] PaymentService - 결제 완료
[INFO ] OrderService - 주문 완료
```

MDC로 각 요청에 `traceId`를 부여하면 `traceId=a1b2c3d4`로 필터링해 해당 요청의 전체 흐름을 즉시 추적할 수 있다.

```
[INFO ] [traceId=a1b2c3d4] [userId=user123] OrderService - 주문 처리 시작
[INFO ] [traceId=e5f6g7h8] [userId=user456] OrderService - 주문 처리 시작
[INFO ] [traceId=a1b2c3d4] [userId=user123] PaymentService - 결제 요청
[ERROR] [traceId=a1b2c3d4] [userId=user123] OrderService - 재고 부족
[INFO ] [traceId=e5f6g7h8] [userId=user456] PaymentService - 결제 완료
```

### MDC의 동작 방식

MDC는 현재 실행 스레드에 키-값 쌍의 컨텍스트 정보를 저장하고, 로그 패턴에서 자동으로 출력하게 하는 기능이다. 핵심은 `ThreadLocal` 기반이라는 것이다. 각 스레드는 독립적인 MDC 맵을 가지며, 같은 JVM에서 실행되는 다른 스레드의 MDC에 영향을 주지 않는다.

<div class="mermaid">
graph LR
    subgraph "Thread-1 (요청 A)"
        M1["MDC Map: {traceId: 'a1b2', userId: 'user1'}"]
        L1["log.info() → traceId=a1b2 자동 포함"]
        M1 --> L1
    end
    subgraph "Thread-2 (요청 B)"
        M2["MDC Map: {traceId: 'c3d4', userId: 'user2'}"]
        L2["log.info() → traceId=c3d4 자동 포함"]
        M2 --> L2
    end
</div>

각 스레드가 독립적인 MDC 맵을 보유하므로, 동시에 처리되는 요청의 로그가 서로 섞이지 않는다.

---

## 2. MDC 내부 구현 (ThreadLocal 기반)

MDC는 내부적으로 `ThreadLocal<Map<String, String>>`으로 구현된다. 각 스레드마다 독립적인 Map이 유지되므로 스레드 간 간섭이 없다.

`ThreadLocal`의 핵심 특성은 스레드 풀에서 스레드가 재사용된다는 점이다. 요청 처리가 끝난 후 `MDC.clear()`를 호출하지 않으면, 스레드가 다음 요청에 재사용될 때 이전 요청의 MDC 값이 남아 있어 로그에 잘못된 정보가 출력된다. 이것이 `finally { MDC.clear(); }` 패턴이 필수인 이유다.

```java
// SLF4J MDC API
import org.slf4j.MDC;

MDC.put("traceId", "a1b2c3d4");    // 값 저장
MDC.put("userId", "user123");

String traceId = MDC.get("traceId"); // 값 조회
MDC.remove("traceId");              // 특정 키 제거
MDC.clear();                        // 전체 초기화 (스레드 반환 전 필수)

Map<String, String> context = MDC.getCopyOfContextMap(); // 현재 맵 스냅샷 (비동기 전파용)
MDC.setContextMap(context);         // 맵 전체 설정 (비동기 스레드에서 복원용)
```

`getCopyOfContextMap()`은 현재 스레드의 MDC 상태를 복사한다. 이 스냅샷을 새 스레드에 전달하여 `setContextMap()`으로 복원하는 것이 비동기 MDC 전파의 핵심 메커니즘이다.

---

## 3. Logback/Log4j2에서의 MDC 설정

### logback-spring.xml 패턴 설정

`%X{키명}` 패턴으로 MDC 값을 로그에 포함시킨다. 로거가 로그를 출력할 때마다 현재 스레드의 MDC 맵에서 해당 키를 꺼내 자동으로 삽입한다. 개발자가 `log.info()` 호출 시 MDC 값을 직접 넣을 필요가 없다.

```xml
<!-- src/main/resources/logback-spring.xml -->
<configuration>
    <springProperty scope="context" name="appName" source="spring.application.name"/>

    <!-- 콘솔 출력 (개발 환경) -->
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>
                %d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level
                [traceId=%X{traceId:-NONE}]
                [userId=%X{userId:-ANONYMOUS}]
                %logger{36} - %msg%n
            </pattern>
            <charset>UTF-8</charset>
        </encoder>
    </appender>

    <!-- JSON 출력 (운영 환경 — ELK 연동) -->
    <appender name="FILE_JSON" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <file>logs/application.log</file>
        <rollingPolicy class="ch.qos.logback.core.rolling.TimeBasedRollingPolicy">
            <fileNamePattern>logs/application.%d{yyyy-MM-dd}.%i.log.gz</fileNamePattern>
            <maxHistory>30</maxHistory>
            <maxFileSize>100MB</maxFileSize>
        </rollingPolicy>
        <encoder class="net.logstash.logback.encoder.LogstashEncoder">
            <includeMdc>true</includeMdc>   <!-- MDC 값이 JSON 필드에 자동 포함 -->
            <customFields>{"app":"${appName}"}</customFields>
        </encoder>
    </appender>

    <springProfile name="dev">
        <root level="DEBUG"><appender-ref ref="CONSOLE"/></root>
    </springProfile>
    <springProfile name="prod">
        <root level="INFO"><appender-ref ref="FILE_JSON"/></root>
    </springProfile>
</configuration>
```

패턴 설명:
- `%X{traceId}` — MDC에서 traceId 값 출력, 없으면 빈 문자열
- `%X{traceId:-NONE}` — 없을 때 "NONE" 출력
- `%X` — MDC 전체 맵을 `{key=value, ...}` 형식으로 출력

---

## 4. Spring에서 MDC 활용

### Filter에서 traceId 주입

HTTP 요청이 진입하는 가장 앞단인 Filter에서 MDC를 설정한다. 이 Filter는 모든 요청에 대해 고유한 traceId를 만들거나, 상위 서비스에서 전달한 헤더에서 가져온다. Filter 체인이 끝나면 반드시 `finally` 블록에서 `MDC.clear()`를 호출하여 스레드를 오염시키지 않는다.

`@Order(Ordered.HIGHEST_PRECEDENCE)`로 이 Filter가 가장 먼저 실행되도록 한다. Spring Security Filter보다 먼저 traceId가 설정되어야 Security 관련 로그에도 traceId가 포함된다.

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE) // 가장 먼저 실행
public class MdcLoggingFilter implements Filter {

    private static final String TRACE_ID_HEADER = "X-Trace-Id";

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest httpRequest = (HttpServletRequest) request;

        try {
            // 상위 서비스에서 전달된 traceId 사용, 없으면 신규 생성
            String traceId = Optional.ofNullable(httpRequest.getHeader(TRACE_ID_HEADER))
                .filter(StringUtils::hasText)
                .orElse(generateTraceId());

            MDC.put("traceId", traceId);
            MDC.put("requestId", UUID.randomUUID().toString());
            MDC.put("clientIp", getClientIp(httpRequest));
            MDC.put("requestUri", httpRequest.getRequestURI());
            MDC.put("requestMethod", httpRequest.getMethod());

            // 응답 헤더에도 traceId 포함 (클라이언트가 추적 가능)
            ((HttpServletResponse) response).setHeader(TRACE_ID_HEADER, traceId);

            chain.doFilter(request, response);

        } finally {
            MDC.clear(); // 반드시 정리 — 스레드 풀 오염 방지
        }
    }

    private String generateTraceId() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    }

    private String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (StringUtils.hasText(ip) && !"unknown".equalsIgnoreCase(ip)) {
            return ip.split(",")[0].trim(); // 프록시 체인에서 첫 번째 IP
        }
        return Optional.ofNullable(request.getHeader("X-Real-IP"))
            .orElse(request.getRemoteAddr());
    }
}
```

### 인증 후 userId 추가 (Spring Security 연동)

Security Filter 이후 인증 정보가 확정되면 userId를 MDC에 추가한다.

```java
@Component
public class MdcUserContextFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        try {
            Authentication auth = SecurityContextHolder.getContext().getAuthentication();
            if (auth != null && auth.isAuthenticated()
                    && !(auth instanceof AnonymousAuthenticationToken)) {
                MDC.put("userId", auth.getName());
            }
            filterChain.doFilter(request, response);
        } finally {
            MDC.remove("userId");
        }
    }
}
```

---

## 5. 비동기 환경에서의 MDC 전파

MDC는 `ThreadLocal` 기반이므로 `@Async`나 `CompletableFuture`처럼 새로운 스레드를 생성하면 MDC 값이 전달되지 않는다. 이것이 비동기 코드에서 가장 자주 발생하는 MDC 관련 버그다.

<div class="mermaid">
sequenceDiagram
    participant T1 as "요청 스레드 (MDC 있음)"
    participant T2 as "@Async 스레드 (MDC 없음)"
    T1->>T1: MDC.put('traceId', 'a1b2')
    T1->>T2: @Async 호출 (새 스레드 생성)
    Note over T2: MDC가 비어있음!<br>log.info() → traceId=NONE 출력
    T2-->>T1: CompletableFuture 반환
</div>

### TaskDecorator로 MDC 전파

`TaskDecorator`는 `ThreadPoolTaskExecutor`가 작업을 실행하기 직전에 호출되는 콜백이다. 작업이 시작될 때 부모 스레드의 MDC 스냅샷을 자식 스레드에 복원하고, 작업이 끝나면 정리한다. 이 설정 하나로 모든 `@Async` 메서드에 MDC 전파가 자동 적용된다.

```java
// MDC 전파 TaskDecorator
public class MdcTaskDecorator implements TaskDecorator {
    @Override
    public Runnable decorate(Runnable runnable) {
        // 부모 스레드의 MDC 스냅샷 캡처
        Map<String, String> mdcContext = MDC.getCopyOfContextMap();

        return () -> {
            try {
                // 자식 스레드에 MDC 복원
                if (mdcContext != null) MDC.setContextMap(mdcContext);
                runnable.run();
            } finally {
                MDC.clear(); // 자식 스레드 정리
            }
        };
    }
}

// ThreadPoolTaskExecutor에 적용
@Bean(name = "taskExecutor")
public Executor taskExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(10);
    executor.setMaxPoolSize(50);
    executor.setQueueCapacity(200);
    executor.setThreadNamePrefix("async-");
    executor.setTaskDecorator(new MdcTaskDecorator()); // MDC 자동 전파
    executor.initialize();
    return executor;
}
```

### CompletableFuture에서의 MDC 전파

`TaskDecorator` 대신 직접 전파하는 유틸리티 메서드를 사용할 수도 있다.

```java
// MDC를 전파하는 CompletableFuture 유틸리티
public static <T> CompletableFuture<T> supplyWithMdc(Supplier<T> supplier, Executor executor) {
    Map<String, String> mdcContext = MDC.getCopyOfContextMap();
    return CompletableFuture.supplyAsync(() -> {
        try {
            if (mdcContext != null) MDC.setContextMap(mdcContext);
            return supplier.get();
        } finally {
            MDC.clear();
        }
    }, executor);
}

// 사용 예
public CompletableFuture<OrderResult> processOrderAsync(Order order) {
    return supplyWithMdc(() -> {
        log.info("비동기 주문 처리 — orderId: {}", order.getId());
        // traceId가 올바르게 출력됨
        return processOrder(order);
    }, taskExecutor);
}
```

### MdcUtil 유틸리티 클래스

try-with-resources 패턴을 지원하여 MDC 설정과 해제를 자동화할 수 있다.

```java
@Component
public class MdcUtil {

    // Runnable/Callable 래핑
    public static Runnable wrap(Runnable runnable) {
        Map<String, String> context = MDC.getCopyOfContextMap();
        return () -> {
            Map<String, String> previous = MDC.getCopyOfContextMap();
            try {
                if (context != null) MDC.setContextMap(context);
                else MDC.clear();
                runnable.run();
            } finally {
                if (previous != null) MDC.setContextMap(previous);
                else MDC.clear();
            }
        };
    }

    // try-with-resources 방식
    public static AutoCloseable putCloseable(String key, String value) {
        MDC.put(key, value);
        return () -> MDC.remove(key);
    }
}

// try-with-resources 활용 예
try (var ignored = MdcUtil.putCloseable("operationId", "ORDER_CREATE")) {
    log.info("주문 생성 시작"); // [operationId=ORDER_CREATE] 자동 포함
} // 블록 종료 시 자동으로 operationId 제거
```

---

## 6. 분산 시스템에서의 MDC

### Spring Cloud Sleuth / Micrometer Tracing

Spring Boot 3.x의 Micrometer Tracing은 OpenTelemetry/Brave와 통합하여 MDC에 `traceId`, `spanId`를 **자동으로** 주입한다. 별도의 Filter 없이도 분산 추적이 가능하다.

```xml
<!-- Spring Boot 3.x — Micrometer Tracing + Zipkin -->
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
      probability: 1.0  # 100% 샘플링 (운영 환경에서는 0.1로 조정)
  zipkin:
    tracing:
      endpoint: http://zipkin-server:9411/api/v2/spans

logging:
  pattern:
    level: "%5p [${spring.application.name:},%X{traceId:-},%X{spanId:-}]"
```

Micrometer Tracing이 자동으로 주입하는 MDC 키:
- `traceId` — 전체 요청 흐름의 고유 ID (서비스 경계를 넘어도 동일)
- `spanId` — 현재 작업 단위의 ID
- `parentId` — 상위 Span ID

### 서비스 간 traceId 전파

서비스 A에서 서비스 B로 HTTP 요청 시, MDC의 traceId를 헤더에 포함시켜 전달해야 B의 로그에서도 같은 traceId로 추적이 가능하다.

```java
// RestTemplate 인터셉터로 traceId 전파
@Component
public class MdcRestTemplateInterceptor implements ClientHttpRequestInterceptor {
    @Override
    public ClientHttpResponse intercept(HttpRequest request, byte[] body,
                                        ClientHttpRequestExecution execution) throws IOException {
        String traceId = MDC.get("traceId");
        if (StringUtils.hasText(traceId)) {
            request.getHeaders().add("X-Trace-Id", traceId);
        }
        return execution.execute(request, body);
    }
}

// WebClient 필터로 traceId 전파
@Bean
public WebClient webClient() {
    return WebClient.builder()
        .filter((request, next) -> {
            String traceId = MDC.get("traceId");
            ClientRequest modifiedRequest = ClientRequest.from(request)
                .header("X-Trace-Id", traceId != null ? traceId : "")
                .build();
            return next.exchange(modifiedRequest);
        })
        .build();
}
```

### Kafka Consumer에서의 MDC

Kafka Consumer는 별도 스레드에서 동작하므로, 메시지 헤더에서 traceId를 추출하여 MDC에 설정해야 한다.

```java
// Kafka 발행 시: MDC의 traceId를 메시지 헤더에 포함
public void publishOrderCreated(OrderEvent event) {
    ProducerRecord<String, OrderEvent> record =
        new ProducerRecord<>("order-events", event.getOrderId(), event);

    String traceId = MDC.get("traceId");
    if (traceId != null) {
        record.headers().add("X-Trace-Id", traceId.getBytes(StandardCharsets.UTF_8));
    }
    kafkaTemplate.send(record);
}

// Kafka 소비 시: 헤더에서 traceId 복원
@KafkaListener(topics = "order-events", groupId = "order-service")
public void consume(ConsumerRecord<String, OrderEvent> record) {
    Header traceIdHeader = record.headers().lastHeader("X-Trace-Id");
    String traceId = traceIdHeader != null
        ? new String(traceIdHeader.value(), StandardCharsets.UTF_8)
        : UUID.randomUUID().toString().substring(0, 16); // 신규 생성

    MDC.put("traceId", traceId);
    MDC.put("kafkaTopic", record.topic());

    try {
        log.info("Kafka 메시지 소비 — key: {}", record.key());
        processEvent(record.value());
    } finally {
        MDC.clear();
    }
}
```

---

## 7. MDC + JSON 로그 (ELK 스택 연동)

Kibana에서 `traceId`로 검색하려면 로그를 JSON 형식으로 출력해야 한다. `logstash-logback-encoder`를 사용하면 MDC 값이 JSON 필드에 자동으로 포함된다.

```xml
<appender name="JSON_CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
        <includeMdc>true</includeMdc>
        <customFields>{"service":"order-service","env":"prod"}</customFields>
        <!-- MDC 키를 JSON 필드명으로 매핑 -->
        <mdcKeyFieldName>traceId=trace_id</mdcKeyFieldName>
        <mdcKeyFieldName>userId=user_id</mdcKeyFieldName>
    </encoder>
</appender>
```

출력 JSON 예시:

```json
{
  "@timestamp": "2026-05-01T10:23:45.123Z",
  "level": "INFO",
  "logger_name": "com.example.OrderService",
  "message": "주문 처리 시작",
  "service": "order-service",
  "trace_id": "a1b2c3d4e5f60001",
  "user_id": "user123",
  "clientIp": "192.168.1.1",
  "requestUri": "/api/orders"
}
```

Kibana에서 `trace_id: "a1b2c3d4e5f60001"` 단 하나의 쿼리로 해당 요청이 거쳐간 모든 서비스의 로그를 한 번에 조회할 수 있다.

---

## 8. 전체 MDC 생명주기 흐름

<div class="mermaid">
sequenceDiagram
    participant C as "클라이언트"
    participant F as "1️⃣ MdcLoggingFilter"
    participant S as "2️⃣ SecurityFilter"
    participant B as "3️⃣ Controller→Service→Repository"
    participant A as "4️⃣ @Async 스레드"

    C->>F: "HTTP 요청 진입"
    Note over F: "MDC.put('traceId', UUID)<br>MDC.put('clientIp', ip)<br>MDC.put('requestUri', uri)"
    F->>S: "필터 체인 전달"
    Note over S: "MDC.put('userId', user)<br>(같은 스레드이므로 MDC 유효)"
    S->>B: "비즈니스 로직 진입"
    Note over B: "log.info('주문 처리')<br>→ MDC 값 자동 포함"
    B-->>A: "@Async 호출"
    Note over A: "TaskDecorator 없으면<br>MDC 전파 안 됨!"
    B->>F: "응답 반환"
    Note over F: "finally: MDC.clear()<br>스레드 풀 오염 방지"
    F->>C: "HTTP 응답 (X-Trace-Id 헤더 포함)"
</div>

---

## 9. 극한 시나리오

### 시나리오 1: @Async 전파 누락으로 traceId 소실

주문 처리 후 알림 발송을 `@Async`로 처리했는데, 알림 실패 로그에 traceId가 없어 어느 주문의 알림인지 추적 불가 상태가 된다. 원인은 `@Async`가 스레드 풀의 새 스레드에서 실행되어 부모의 ThreadLocal이 복사되지 않기 때문이다.

`ThreadPoolTaskExecutor`에 `MdcTaskDecorator`를 설정하면 해결된다. 이미 배포된 서비스라면 `@Async` 메서드 내부에서 직접 `MDC.setContextMap(capturedContext)`를 호출하는 임시 해결책도 가능하다.

### 시나리오 2: 스레드 풀 오염으로 다른 사용자 정보 노출

`finally { MDC.clear(); }`를 빠뜨리면 스레드 풀의 스레드가 재사용될 때 이전 요청의 userId, traceId가 그대로 남는다. 다음 요청의 로그에 이전 요청의 사용자 정보가 출력되는 보안 문제가 발생한다.

이 버그는 재현이 어렵다. 스레드 재사용 순서에 따라 랜덤하게 나타나기 때문이다. 반드시 Filter의 `finally` 블록에서 `MDC.clear()`를 호출해야 한다.

### 시나리오 3: Kafka 메시지 체인에서 traceId 단절

서비스 A → Kafka → 서비스 B 흐름에서 서비스 A의 traceId가 Kafka 메시지 헤더에 포함되지 않으면, 서비스 B의 로그는 별도 traceId를 생성한다. 장애 발생 시 A와 B의 로그를 연결할 수 없다.

Producer에서 `record.headers().add("X-Trace-Id", traceId.getBytes())`로 헤더를 추가하고, Consumer에서 헤더를 읽어 `MDC.put("traceId", traceId)`로 복원하면 전체 흐름이 연결된다.

---

## 10. 실무에서 자주 하는 실수

### 실수 1: MDC.clear() 미호출

가장 흔하고 위험한 실수다. Filter의 `finally` 블록에서 `MDC.clear()`를 빠뜨리면 스레드 풀 오염이 발생한다. 예외가 발생해도 `finally`는 실행되므로 반드시 `finally` 블록에 넣어야 한다.

### 실수 2: @Async에서 MDC 전파 없이 사용

`@Async` 메서드에서 `log.info()`를 호출할 때 traceId가 빈 값으로 출력된다. `ThreadPoolTaskExecutor`에 `MdcTaskDecorator`를 설정하지 않았기 때문이다. 이 설정은 프로젝트 초기에 한 번 해두면 모든 `@Async`에 자동 적용된다.

### 실수 3: 민감 정보를 MDC에 저장

비밀번호, 카드번호, 주민등록번호 등을 MDC에 저장하면 로그 파일에 그대로 기록된다. MDC에는 식별자(ID, traceId)만 저장하고, 민감 정보는 절대 저장하지 않아야 한다.

### 실수 4: 과도한 MDC 키로 로그 볼륨 증가

모든 비즈니스 데이터를 MDC에 저장하면 모든 로그 라인에 해당 데이터가 포함되어 로그 볼륨이 급증한다. traceId, userId, requestUri, clientIp 정도의 필수 컨텍스트만 MDC에 저장하고, 나머지는 로그 메시지에 직접 포함시킨다.

### 실수 5: Virtual Thread에서의 MDC 동작 오해

Java 21의 Virtual Thread도 `ThreadLocal`을 지원하므로 MDC가 동일하게 동작한다. 단, Virtual Thread는 실행 중 Carrier Thread를 바꿀 수 있으므로, `ThreadLocal`을 사용하는 MDC는 Carrier Thread가 바뀌어도 Virtual Thread에 묶여 있어 안전하다. `ScopedValue`(Java 21+)로 전환하면 더 명시적인 전파가 가능하지만 아직 실험적 API다.

---

## 정리

MDC는 구현 비용 대비 로그 추적 품질을 크게 높이는 효과적인 도구다. 핵심 규칙 세 가지만 지키면 분산 시스템에서도 요청 단위 로그 추적을 손쉽게 구현할 수 있다.

첫째, Filter에서 traceId를 주입하고 반드시 `finally { MDC.clear(); }`를 호출한다. 둘째, `@Async`, `CompletableFuture`, Kafka Consumer에서 반드시 MDC를 전파한다. 셋째, 서비스 간 HTTP 호출 시 `X-Trace-Id` 헤더로 traceId를 전달한다. 이 세 가지를 지키면 새벽 2시 장애에서도 traceId 하나로 전체 흐름을 즉시 추적할 수 있다.

| 항목 | 주의사항 |
|---|---|
| MDC.clear() 필수 | 스레드 풀에서 이전 요청 값 오염 방지 |
| 비동기 MDC 전파 | @Async, CompletableFuture에서 TaskDecorator 또는 수동 전파 |
| Kafka/MQ 전파 | 메시지 헤더로 명시적 traceId 전파 필요 |
| 민감 정보 금지 | 비밀번호, 카드번호 등 절대 MDC에 저장 금지 |
| 과도한 MDC 키 | 불필요한 키-값은 로그 볼륨만 증가 |
