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

분산 추적의 핵심은 세 가지 식별자다.

- **TraceId**: 요청 전체를 식별하는 ID. 최초 진입점(API Gateway 등)에서 생성되고 모든 서비스에 전파된다. 하나의 비즈니스 트랜잭션 = 하나의 TraceId다.
- **SpanId**: 각 서비스(또는 작업 단위)를 식별하는 ID. 서비스마다 새로 생성된다.
- **ParentSpanId**: 호출자의 SpanId. 이를 통해 서비스 간 호출 계층 구조를 파악한다.

<div class="mermaid">
graph TD
    subgraph "TraceId: abc123 (하나의 주문 요청)"
        A["API Gateway\nSpanId: span1\nParent: 없음"]
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

TraceId가 있으면 각 서비스의 로그를 한 번에 조회할 수 있다.

```
[order-service]       [abc123, span2] 주문 처리 시작
[payment-service]     [abc123, span3] 결제 처리 시작 (200ms)
[inventory-service]   [abc123, span4] 재고 차감 (50ms)
[notification-service][abc123, span5] 알림 발송 (300ms)  ← 여기가 느리다!
```

---

## Spring Boot 3.x: Micrometer Tracing

Spring Boot 3.x에서는 Spring Cloud Sleuth가 **Micrometer Tracing**으로 대체됐다.

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

# Spring Boot 3.x
management:
  tracing:
    sampling:
      probability: 1.0  # 100% 샘플링 (운영: 0.1 ~ 0.3)
  zipkin:
    tracing:
      endpoint: http://localhost:9411/api/v2/spans
```

---

## TraceId/SpanId 전파 방식

HTTP 요청 헤더를 통해 TraceId가 서비스 간에 전파된다.

### 1️⃣ B3 Propagation (기본)

Zipkin이 만든 표준 헤더다.

```
X-B3-TraceId: abc123def456...    (64-bit 또는 128-bit hex)
X-B3-SpanId: 789xyz...           (64-bit hex)
X-B3-ParentSpanId: 456abc...
X-B3-Sampled: 1                  (1=추적, 0=미추적)
```

### 2️⃣ W3C TraceContext (최신 표준)

```
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
             버전-TraceId-ParentSpanId-플래그
```

### RestTemplate / WebClient 자동 전파

Sleuth/Micrometer Tracing은 `RestTemplate`, `WebClient`, `FeignClient`, `Kafka` 등에 자동으로 TraceId 헤더를 주입한다. 별도 설정 없이 TraceId가 전파된다.

```java
@Service
public class OrderService {

    private final RestTemplate restTemplate;

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

특정 작업(DB 쿼리, 외부 API 등)의 세부 처리 시간을 측정하려면 수동으로 Span을 생성한다.

```java
@Service
public class OrderService {

    private final Tracer tracer;

    public OrderResult createOrder(OrderRequest request) {
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

Sleuth/Micrometer Tracing은 MDC에 TraceId, SpanId를 자동으로 설정한다. logback 설정에서 `%X{traceId}`로 출력한다.

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
</configuration>
```

출력 예시:
```
2026-05-01 10:00:00.001 [http-nio-8080-exec-1] [abc123,span2] INFO  OrderService - 주문 처리 시작
2026-05-01 10:00:00.150 [http-nio-8080-exec-1] [abc123,span3] INFO  PaymentService - 결제 처리 완료
```

ELK 스택과 연동하면 `traceId`로 검색해서 여러 서비스에 흩어진 로그를 한 화면에서 조회할 수 있다.

---

## Zipkin 서버 구성

Zipkin은 분산 추적 데이터를 수집하고 시각화하는 서버다.

```bash
docker run -d -p 9411:9411 openzipkin/zipkin
```

### Zipkin UI 타임라인

Zipkin의 Gantt 차트로 각 서비스의 처리 시간과 순서를 한눈에 볼 수 있다.

<div class="mermaid">
gantt
    title "TraceId abc123 타임라인 (Zipkin Gantt 차트)"
    dateFormat x
    axisFormat %Lms

    section API Gateway
    "span1 - 라우팅"         :0, 10

    section Order Service
    "span2 - 주문 처리"      :10, 400

    section Payment Service
    "span3 - 결제 처리"      :15, 200

    section Inventory Service
    "span4 - 재고 차감"      :220, 60

    section Notification Service
    "span5 - 알림 발송"      :285, 300
