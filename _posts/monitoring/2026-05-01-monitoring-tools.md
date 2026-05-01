---
title: "모니터링 도구"
categories: MONITORING
tags: [Prometheus, Grafana, ELK, Datadog, Micrometer, Spring Actuator]
toc: true
toc_sticky: true
toc_label: 목차
---

## 비유로 시작하기

비행기 조종석을 생각해보세요. 고도계, 속도계, 연료계, 엔진 온도계 등 수십 개의 계기판이 있습니다. 조종사는 이 계기판들을 통해 비행기 상태를 실시간으로 파악하고, 이상 징후가 발생하면 경보음이 울립니다.

모니터링 시스템은 소프트웨어의 조종석입니다. **시스템이 얼마나 잘 동작하고 있는지를 측정하고(Metrics), 무슨 일이 일어났는지 기록하며(Logs), 요청이 어디를 거쳤는지 추적합니다(Traces).**

---

## Observability 3대 요소

<div class="mermaid">
graph TD
    OBS[Observability]
    OBS --> METRICS[Metrics<br>숫자로 측정 - CPU, TPS, 에러율]
    OBS --> LOGS[Logs<br>이벤트 기록 - 오류 상세, 감사]
    OBS --> TRACES[Traces<br>요청 흐름 추적 - 분산 트레이싱]

    METRICS --> PROM[Prometheus + Grafana]
    LOGS --> ELK[ELK Stack / Loki]
    TRACES --> JAEGER[Jaeger / Zipkin]
</div>

| 요소 | 질문 | 도구 |
|------|------|------|
| Metrics | 지금 시스템이 얼마나 바쁜가? | Prometheus, Datadog |
| Logs | 에러가 왜 발생했나? | ELK, Loki |
| Traces | 어느 서비스에서 지연이 발생했나? | Jaeger, Zipkin, Tempo |

---

## Prometheus + Grafana

가장 널리 쓰이는 오픈소스 메트릭 모니터링 스택입니다.

### Prometheus 동작 원리

<div class="mermaid">
sequenceDiagram
    participant APP as Spring App<br>/actuator/prometheus
    participant PROM as Prometheus Server
    participant ALERT as Alertmanager
    participant GRAF as Grafana
    participant SLACK as Slack

    PROM->>APP: Scrape (15초마다 Pull)
    APP-->>PROM: 메트릭 데이터
    PROM->>PROM: TSDB에 저장
    GRAF->>PROM: PromQL 쿼리
    PROM-->>GRAF: 데이터 반환
    GRAF-->>GRAF: 대시보드 렌더링
    PROM->>ALERT: 알림 규칙 위반
    ALERT->>SLACK: Slack 알림 발송
</div>

**Pull 방식**: Prometheus가 각 서비스에서 메트릭을 수집합니다. Push 방식(Datadog Agent)과 대비됩니다.

### Prometheus 설정

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]

scrape_configs:
  - job_name: 'spring-app'
    metrics_path: '/actuator/prometheus'
    static_configs:
      - targets: ['app1:8080', 'app2:8080']
    # Kubernetes 환경에서는 자동 디스커버리

  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
```

### 알림 규칙

```yaml
# alert_rules.yml
groups:
  - name: application
    rules:
      - alert: HighErrorRate
        expr: |
          rate(http_server_requests_seconds_count{status=~"5.."}[5m])
          / rate(http_server_requests_seconds_count[5m]) > 0.01
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "에러율 1% 초과"
          description: "{{ $labels.job }} 에러율: {{ $value | humanizePercentage }}"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(http_server_requests_seconds_bucket[5m])
          ) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 응답시간 2초 초과"

      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Pod 재시작 감지: {{ $labels.pod }}"
```

### PromQL 주요 쿼리

```promql
# 초당 요청 수 (TPS)
rate(http_server_requests_seconds_count[5m])

# P95 응답시간
histogram_quantile(0.95, rate(http_server_requests_seconds_bucket[5m]))

# 에러율
rate(http_server_requests_seconds_count{status=~"5.."}[5m])
/ rate(http_server_requests_seconds_count[5m])

# JVM Heap 사용률
jvm_memory_used_bytes{area="heap"} / jvm_memory_max_bytes{area="heap"}

# DB 커넥션 풀 사용률
hikaricp_connections_active / hikaricp_connections_max

# CPU 사용률 (컨테이너)
rate(container_cpu_usage_seconds_total[5m]) * 100
```

---

## Spring Actuator + Micrometer

Spring Boot 애플리케이션의 메트릭을 Prometheus로 내보내는 설정입니다.

### 의존성

```gradle
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-actuator'
    implementation 'io.micrometer:micrometer-registry-prometheus'
}
```

### 설정

```yaml
# application.yml
management:
  endpoints:
    web:
      exposure:
        include: health, info, prometheus, metrics
  endpoint:
    health:
      show-details: always
      probes:
        enabled: true  # liveness, readiness 분리
  metrics:
    tags:
      application: ${spring.application.name}
      environment: ${spring.profiles.active}
    distribution:
      percentiles-histogram:
        http.server.requests: true  # 히스토그램 활성화 (P95 계산용)
      slo:
        http.server.requests: 100ms, 500ms, 1s, 2s
```

### 커스텀 메트릭

```java
@Component
@RequiredArgsConstructor
public class OrderMetrics {

    private final MeterRegistry registry;
    private final Counter orderCreatedCounter;
    private final Counter orderCancelledCounter;
    private final Timer orderProcessingTimer;
    private final Gauge pendingOrdersGauge;

    @PostConstruct
    public void init() {
        orderCreatedCounter = Counter.builder("order.created.total")
            .description("생성된 주문 수")
            .tag("type", "all")
            .register(registry);

        orderCancelledCounter = Counter.builder("order.cancelled.total")
            .description("취소된 주문 수")
            .register(registry);

        orderProcessingTimer = Timer.builder("order.processing.duration")
            .description("주문 처리 시간")
            .publishPercentiles(0.5, 0.95, 0.99)
            .register(registry);
    }

    public void recordOrderCreated() {
        orderCreatedCounter.increment();
    }

    public void recordOrderProcessing(Runnable task) {
        orderProcessingTimer.record(task);
    }

    // 게이지: 현재 상태를 반영 (람다로 실시간 값 제공)
    public void registerPendingOrdersGauge(OrderRepository repository) {
        Gauge.builder("order.pending.count", repository, r -> r.countByStatus(OrderStatus.PENDING))
            .description("처리 대기 중인 주문 수")
            .register(registry);
    }
}
```

---

## ELK Stack

**E**lasticsearch + **L**ogstash + **K**ibana. 로그 수집, 저장, 시각화 스택입니다.

<div class="mermaid">
graph LR
    APP[Spring App<br>Logback] -->|JSON 로그| FB[Filebeat]
    FB -->|전송| LS[Logstash<br>파싱/필터링]
    LS -->|저장| ES[(Elasticsearch)]
    ES -->|쿼리| KI[Kibana<br>시각화/검색]
    SLACK[Slack] -.->|알림| KI
</div>

### Spring Logback JSON 설정

```xml
<!-- logback-spring.xml -->
<configuration>
    <appender name="JSON_CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder class="net.logstash.logback.encoder.LogstashEncoder">
            <includeMdcKeyName>traceId</includeMdcKeyName>
            <includeMdcKeyName>spanId</includeMdcKeyName>
            <includeMdcKeyName>userId</includeMdcKeyName>
            <customFields>{"application":"myapp","environment":"prod"}</customFields>
        </encoder>
    </appender>

    <root level="INFO">
        <appender-ref ref="JSON_CONSOLE"/>
    </root>
</configuration>
```

출력 결과:
```json
{
  "@timestamp": "2026-05-01T10:00:00.000Z",
  "level": "ERROR",
  "message": "주문 처리 실패",
  "logger": "com.example.OrderService",
  "traceId": "abc123def456",
  "spanId": "789xyz",
  "userId": "user-42",
  "application": "myapp",
  "environment": "prod",
  "exception": "com.example.OrderNotFoundException: Order not found: 12345"
}
```

### Logstash 파이프라인

```ruby
# logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  json {
    source => "message"
  }

  # 에러 로그 태깅
  if [level] == "ERROR" {
    mutate {
      add_tag => ["error"]
    }
  }

  # IP 지역 정보 추가
  geoip {
    source => "clientIp"
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "myapp-logs-%{+YYYY.MM.dd}"
    ilm_enabled => true
    ilm_rollover_alias => "myapp-logs"
    ilm_policy => "myapp-logs-policy"
  }
}
```

---

## Datadog

**SaaS 형태의 통합 모니터링** 플랫폼. 메트릭/로그/트레이싱을 하나의 플랫폼에서 제공합니다.

장점:
- 설치가 매우 간단 (Agent 하나로 모든 것)
- UI/UX가 우수함
- APM(Application Performance Monitoring) 내장
- 이상 감지(Anomaly Detection) AI 내장

단점:
- 비용이 높음 (Host당 월 $15~$35)
- 데이터가 외부로 나감 (금융권 제약)

```yaml
# Kubernetes Datadog Agent
apiVersion: v1
kind: ConfigMap
metadata:
  name: datadog-config
data:
  datadog.yaml: |
    api_key: YOUR_API_KEY
    logs_enabled: true
    apm_config:
      enabled: true
    process_config:
      enabled: true
```

```java
// Spring Boot Datadog 통합 (dd-java-agent 사용)
// JVM 옵션 추가만으로 자동 계측
// -javaagent:/path/to/dd-java-agent.jar
// -Ddd.service=myapp
// -Ddd.env=production
// -Ddd.version=1.0.0
// -Ddd.logs.injection=true
```

---

## 모니터링 전략

### 4 Golden Signals (SRE 기준)

| 신호 | 설명 | 예시 메트릭 |
|------|------|------------|
| Latency | 요청 처리 시간 | P50, P95, P99 응답시간 |
| Traffic | 요청량 | TPS (초당 트랜잭션 수) |
| Errors | 오류율 | 5xx 응답 비율 |
| Saturation | 자원 포화도 | CPU, 메모리, 커넥션 풀 |

### SLI / SLO / SLA

```
SLI (Service Level Indicator): 측정 지표
  예) 지난 30일간 가용성 = 성공 요청 수 / 전체 요청 수 = 99.95%

SLO (Service Level Objective): 내부 목표
  예) 가용성 ≥ 99.9%, P95 응답시간 ≤ 500ms

SLA (Service Level Agreement): 고객과의 계약
  예) 가용성 < 99.9% 시 서비스 크레딧 제공
```

### 알림 전략 (Alert Fatigue 방지)

```
P0 (즉시 대응, 24시간):
  - 서비스 완전 다운
  - 에러율 > 5%
  → PagerDuty / 전화

P1 (1시간 내 대응):
  - P95 응답시간 > 2초
  - DB 커넥션 풀 90% 이상
  → Slack #incidents

P2 (다음 근무일):
  - 디스크 80% 초과
  - 배포 실패
  → Slack #alerts (채널)
```

---

## 극한 시나리오

### 시나리오: 메트릭은 정상인데 사용자 불만 폭발

**원인**: 비즈니스 메트릭 없이 기술 메트릭만 모니터링

```promql
# 기술 메트릭 (정상): HTTP 200 응답률 99.9%
rate(http_requests_total{status="200"}[5m]) / rate(http_requests_total[5m])

# 비즈니스 메트릭 (이상): 결제 성공률 60%
rate(payment_success_total[5m]) / rate(payment_attempt_total[5m])
```

HTTP 200이어도 결제 로직 내부에서 실패할 수 있습니다. **비즈니스 메트릭**을 반드시 추가하세요.

### 시나리오: 로그 스토리지 폭발

일일 로그 100GB 발생 → 한 달 3TB → 비용 폭발

```
해결책:
1. Log Level 조정: INFO → WARN (프로덕션)
2. 샘플링: 정상 요청의 1%만 DEBUG 로깅
3. ILM (Index Lifecycle Management): 7일 → 콜드 → 30일 후 삭제
4. 중요도별 보존 기간 분리: ERROR 90일, INFO 7일
```
