---
title: "분산 추적 (Sleuth + Zipkin)"
categories: SPRING
tags: [Sleuth, Zipkin, DistributedTracing, TraceId, SpanId, Micrometer]
toc: true
toc_sticky: true
toc_label: 목차
date: 2026-05-01
---

마이크로서비스 환경에서 주문 하나가 실패했다. Order Service → Payment Service → Inventory Service → Notification Service를 거치는데, 어디서 얼마나 걸렸는지 알 수가 없다. 분산 추적(Distributed Tracing)은 요청이 여러 서비스를 거치는 전체 여정을 단일 흐름으로 추적한다.

> **비유**: 국제 택배 추적 시스템과 같다. 발송(TraceId 생성) → 인천공항(Span1) → 도쿄공항(Span2) → 도착지 세관(Span3)까지 각 구간의 처리 시간과 상태가 기록된다. 하나의 운송장 번호(TraceId)로 전체 경로를 조회할 수 있다.

---

## 핵심 개념: TraceId / SpanId

```
TraceId: 요청 전체를 식별하는 ID. 최초 진입점에서 생성되고 모든 서비스에 전파됨.
SpanId:  각 서비스(또는 작업 단위)를 식별하는 ID. 서비스마다 새로 생성됨.
ParentSpanId: 호출자의 SpanId. 계층 구조를 구성함.
```

<div class="mermaid">
graph TD
    subgraph "TraceId: abc123"
        A["API Gateway\nSpanId: span1\nParent: -"]
        B["Order Service\nSpanId: span2\nParent: span1"]
        C["Payment Service\nSpanId: span3\nParent: span2"]
        D["Inventory Service\nSpanId: span4\nParent: span2"]
        E["Notification Service\nSpanId: span5\nParent: span2"]
    end

    A --> B
    B --> C
    B --> D
    B --> E
</div>

```
로그에서 TraceId로 전체 흐름 추적:
[order-service]  [abc123, span2] 주문 처리 시작
[payment-service][abc123, span3] 결제 처리 시작 (200ms)
[inventory-service][abc123, span4] 재고 차감 (50ms)
[notification-service][abc123, span5] 알림 발송 (300ms)  ← 여기가 느리다!
```

---

## Spring Boot 3.x: Micrometer Tracing

Spring Boot 3.x에서는 Spring Cloud Sleuth가 Micrometer Tracing으로 대체됐다.

### 의존성

```xml
<!-- Spring Boot 3.x -->
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-brave</artifactId>
</dependency>
<dependency>
    <groupId>io.zipkin.reporter2</groupId>
    <artifactId>zipkin-reporter-brave</artifactId>
</dependency>

<!-- Spring Boot 2.x (Sleuth 사용 시) -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-sleuth</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-sleuth-zipkin</artifactId>
</dependency>
```

### application.yml

```yaml
spring:
  application:
    name: order-service
  zipkin:
    base-url: http://localhost:9411  # Zipkin 서버 주소
  sleuth:  # Boot 2.x
    sampler:
      probability: 1.0  # 100% 샘플링 (운영: 0.1 ~ 0.3)

# Spring Boot 3.x
management:
  tracing:
    sampling:
      probability: 1.0  # 샘플링 비율
  zipkin:
    tracing:
      endpoint: http://localhost:9411/api/v2/spans
```

---

## Zipkin 서버 구성

### Docker로 빠르게 실행

```bash
docker run -d -p 9411:9411 openzipkin/zipkin
```

### Docker Compose

```yaml
version: '3.8'
services:
  zipkin:
    image: openzipkin/zipkin
    ports:
      - "9411:9411"
    environment:
      # 저장소 선택: mem(기본), mysql, elasticsearch
      - STORAGE_TYPE=elasticsearch
      - ES_HOSTS=elasticsearch:9200
    depends_on:
      - elasticsearch

  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
```

---

## TraceId/SpanId 전파 방식

HTTP 요청 헤더를 통해 전파된다.

### B3 Propagation (기본)

```
HTTP 헤더:
X-B3-TraceId: abc123def456...    (64-bit 또는 128-bit hex)
X-B3-SpanId: 789xyz...           (64-bit hex)
X-B3-ParentSpanId: 456abc...
X-B3-Sampled: 1                  (1=추적, 0=미추적)
X-B3-Flags: 1                    (디버그 모드)
```

### W3C TraceContext (표준)

```
HTTP 헤더:
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
             버전-TraceId-ParentSpanId-플래그
tracestate: key=value (벤더별 확장)
```

### RestTemplate 자동 전파

Spring Cloud Sleuth / Micrometer Tracing은 `RestTemplate`, `WebClient`, `FeignClient`, `Kafka` 등에 자동으로 헤더를 주입한다.

```java
// 별도 설정 없이 TraceId 자동 전파
@Service
public class OrderService {

    private final RestTemplate restTemplate;  // @LoadBalanced 또는 일반

    public PaymentResult processPayment(OrderRequest request) {
        // 내부적으로 X-B3-TraceId 등 헤더 자동 삽입
        return restTemplate.postForObject(
            "http://payment-service/payments",
            request,
            PaymentResult.class
        );
    }
}
```

### 수동 Span 생성

```java
@Service
public class OrderService {

    private final Tracer tracer;  // io.micrometer.tracing.Tracer

    public OrderResult createOrder(OrderRequest request) {
        // 커스텀 Span 생성 (DB 쿼리, 외부 API 등 세부 작업 추적)
        Span span = tracer.nextSpan().name("validate-order").start();

        try (Tracer.SpanInScope ws = tracer.withSpan(span)) {
            span.tag("order.type", request.getType());
            span.tag("order.amount", String.valueOf(request.getAmount()));

            validateOrder(request);

            return processOrder(request);
        } catch (Exception e) {
            span.error(e);
            throw e;
        } finally {
            span.end();
        }
    }
}
```

---

## 로그에 TraceId 자동 포함

Sleuth/Micrometer Tracing은 MDC(Mapped Diagnostic Context)에 TraceId, SpanId를 자동으로 설정한다.

### logback-spring.xml

```xml
<configuration>
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>
                %d{yyyy-MM-dd HH:mm:ss.SSS} [%thread]
                [%X{traceId},%X{spanId}]
                %-5level %logger{36} - %msg%n
            </pattern>
        </encoder>
    </appender>

    <root level="INFO">
        <appender-ref ref="CONSOLE"/>
    </root>
</configuration>
```

```
출력 예시:
2026-05-01 10:00:00.001 [http-nio-8080-exec-1] [abc123,span2] INFO  OrderService - 주문 처리 시작
2026-05-01 10:00:00.150 [http-nio-8080-exec-1] [abc123,span3] INFO  PaymentService - 결제 처리 완료
2026-05-01 10:00:00.200 [http-nio-8080-exec-1] [abc123,span2] INFO  OrderService - 주문 처리 완료
```

### ELK 스택 연동

```
Logstash:
  필드 파싱: traceId, spanId 추출
  → Elasticsearch에 인덱싱

Kibana:
  traceId로 전체 서비스 로그 필터링
  → 하나의 요청이 여러 서비스에서 남긴 로그를 한 화면에서 조회
```

---

## Zipkin UI 이해

```
http://localhost:9411/zipkin/

주요 기능:
1. 서비스 선택 → 최근 트레이스 목록 조회
2. 특정 TraceId 검색
3. Dependency Graph: 서비스 간 호출 관계 시각화
4. 슬로우 트레이스: 응답 시간 상위 N개 조회
5. 오류 트레이스: 실패한 요청만 필터링
```

<div class="mermaid">
gantt
    title TraceId abc123 타임라인 (Zipkin Gantt 차트)
    dateFormat x
    axisFormat %Lms

    section API Gateway
    span1 - 라우팅         :0, 10

    section Order Service
    span2 - 주문 처리      :10, 400

    section Payment Service
    span3 - 결제 처리      :15, 200

    section Inventory Service
    span4 - 재고 차감      :220, 60

    section Notification Service
    span5 - 알림 발송      :285, 300
</div>

---

## 샘플링 전략

모든 요청을 추적하면 비용과 성능 부담이 크다. 샘플링으로 일부만 추적한다.

```yaml
# 개발 환경: 100% 샘플링
management:
  tracing:
    sampling:
      probability: 1.0

# 운영 환경: 10% 샘플링 (트래픽에 따라 조정)
management:
  tracing:
    sampling:
      probability: 0.1
```

### 동적 샘플링 (커스텀)

```java
// 에러 요청은 항상 추적, 정상 요청은 10%만 추적
@Bean
public Sampler customSampler() {
    return (traceContext, span) -> {
        // 특정 경로는 항상 추적
        String path = getCurrentRequestPath();
        if (path != null && path.startsWith("/api/payment")) {
            return SamplingFlags.SAMPLED;
        }
        // 나머지는 10% 확률
        return Math.random() < 0.1 ? SamplingFlags.SAMPLED : SamplingFlags.NOT_SAMPLED;
    };
}
```

---

## Kafka 트레이스 전파

```java
// Kafka Producer: 헤더에 TraceId 자동 삽입
@Service
public class OrderEventPublisher {

    private final KafkaTemplate<String, OrderEvent> kafkaTemplate;

    public void publishOrderCreated(OrderEvent event) {
        // Sleuth/Micrometer가 Kafka 헤더에 B3 헤더 자동 추가
        kafkaTemplate.send("order-events", event.getOrderId(), event);
    }
}

// Kafka Consumer: 헤더에서 TraceId 복원
@KafkaListener(topics = "order-events")
public void onOrderCreated(OrderEvent event, @Header KafkaHeaders headers) {
    // 메시지 헤더에서 TraceId 자동 복원 → 같은 TraceId로 Span 생성
    log.info("Processing order event: {}", event.getOrderId());
    // 로그에 자동으로 동일한 TraceId 포함됨
}
```

---

## Jaeger 연동 (Zipkin 대안)

```yaml
# OpenTelemetry Protocol (OTLP)로 Jaeger에 전송
management:
  otlp:
    tracing:
      endpoint: http://localhost:4318/v1/traces
```

```bash
# Jaeger All-in-One Docker 실행
docker run -d \
  -p 16686:16686 \   # Jaeger UI
  -p 4317:4317 \     # OTLP gRPC
  -p 4318:4318 \     # OTLP HTTP
  jaegertracing/all-in-one
```

---

## 극한 시나리오

### 시나리오 1: TraceId 유실

```
증상: 특정 서비스부터 TraceId가 없어짐
원인:
1. @Async 메서드: 새 스레드에서 MDC 유실
2. ThreadPoolExecutor: TraceContext 미전파
3. 비동기 라이브러리: Sleuth 미지원

해결책 (@Async):
@Configuration
public class AsyncConfig implements AsyncConfigurer {
    @Override
    public Executor getAsyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(10);
        executor.initialize();
        // Sleuth/Micrometer가 TraceContext를 새 스레드에 전파하도록 래핑
        return new LazyTraceExecutor(beanFactory, executor);
    }
}
```

### 시나리오 2: 추적 데이터 폭증

```
문제: 트래픽 급증 시 Zipkin 저장소 용량 초과
대응:
1. 샘플링 비율 동적 조정 (1.0 → 0.01)
2. 슬로우 쿼리/에러만 100% 추적, 정상은 1%
3. Zipkin 저장소를 Elasticsearch로 변경 + 보존 기간 설정
4. 비동기 전송: Zipkin Reporter의 큐 크기 조정

management:
  zipkin:
    tracing:
      connect-timeout: 1s
      read-timeout: 10s
```

### 시나리오 3: 분산 추적으로 병목 발견

```
시나리오: 주문 API가 평균 2초인데 원인 불명

Zipkin 분석:
  order-service: 10ms
  → payment-service: 1800ms  ← 여기!
    → payment-db 쿼리: 1750ms  ← DB 쿼리 문제

조치:
  payment-service DB 쿼리에 인덱스 추가
  → 쿼리 50ms로 단축
  → 전체 API 응답 250ms로 개선

핵심: 분산 추적 없이는 payment-service 내부 DB 쿼리까지
      추적하기 매우 어려웠을 것
```

---

## Spring Boot 2.x vs 3.x 마이그레이션

| 항목 | Spring Boot 2.x | Spring Boot 3.x |
|---|---|---|
| 라이브러리 | Spring Cloud Sleuth | Micrometer Tracing |
| 의존성 | `spring-cloud-starter-sleuth` | `micrometer-tracing-bridge-brave` |
| 설정 prefix | `spring.sleuth.*` | `management.tracing.*` |
| TraceId 로그 키 | `traceId`, `spanId` | `traceId`, `spanId` (동일) |
| Tracer Bean | `brave.Tracer` | `io.micrometer.tracing.Tracer` |
| 자동 구성 | Sleuth Auto-config | Micrometer Auto-config |
