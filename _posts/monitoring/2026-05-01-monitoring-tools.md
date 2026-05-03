---
title: "모니터링 도구"
categories: MONITORING
tags: [Prometheus, Grafana, ELK, Datadog, Micrometer, SpringActuator]
toc: true
toc_sticky: true
toc_label: 목차
date: 2026-05-01
---

모니터링 시스템은 소프트웨어의 조종석이다. 시스템이 얼마나 잘 동작하고 있는지 측정하고(Metrics), 무슨 일이 일어났는지 기록하며(Logs), 요청이 어디를 거쳤는지 추적한다(Traces).

> **비유**: 비행기 조종석의 계기판과 같다. 고도계, 속도계, 연료계, 엔진 온도계 수십 개가 있고, 이상 징후가 발생하면 경보음이 울린다. 계기판 없이 비행하면 이미 추락 중에야 문제를 알게 된다.

---

## Observability 3대 요소

```mermaid
graph TD
    OBS["Observability\n(시스템 내부 상태를 외부에서 파악하는 능력)"]
    OBS --> METRICS["Metrics\n숫자로 측정\nCPU, TPS, 에러율"]
    OBS --> LOGS["Logs\n이벤트 기록\n오류 상세, 감사 추적"]
    OBS --> TRACES["Traces\n요청 흐름 추적\n분산 트레이싱"]

    METRICS --> PROM["Prometheus + Grafana"]
    LOGS --> ELK["ELK Stack / Loki"]
    TRACES --> JAEGER["Jaeger / Zipkin / Tempo"]
```

| 요소 | 핵심 질문 | 대표 도구 |
|------|---------|---------|
| Metrics | 지금 시스템이 얼마나 바쁜가? 느린가? | Prometheus, Datadog |
| Logs | 에러가 왜 발생했나? 무슨 일이 있었나? | ELK Stack, Loki |
| Traces | 어느 서비스에서 지연이 발생했나? | Jaeger, Zipkin, Tempo |

세 요소는 서로 보완한다. Metrics로 이상을 감지하고, Logs로 원인을 파악하며, Traces로 어느 서비스가 문제인지 추적한다.

---

## Prometheus + Grafana

가장 널리 쓰이는 오픈소스 메트릭 모니터링 스택이다.

### Prometheus 동작 원리

Prometheus는 **Pull 방식**으로 동작한다. 각 서비스가 메트릭 엔드포인트를 노출하면 Prometheus가 주기적으로 긁어간다(scrape). 서비스가 메트릭을 Push하는 방식(Datadog Agent)과 대비된다. Pull 방식은 Prometheus가 장애나도 서비스에는 영향이 없다는 장점이 있다.

```mermaid
sequenceDiagram
    participant APP as "Spring App\n(/actuator/prometheus)"
    participant PROM as "Prometheus Server"
    participant ALERT as "Alertmanager"
    participant GRAF as "Grafana"
    participant SLACK as "Slack"

    PROM->>APP: 1️⃣ Scrape (15초마다 Pull)
    APP-->>PROM: "메트릭 데이터 반환"
    PROM->>PROM: 2️⃣ TSDB에 시계열 저장
    GRAF->>PROM: 3️⃣ PromQL 쿼리
    PROM-->>GRAF: "데이터 반환"
    GRAF-->>GRAF: 4️⃣ 대시보드 렌더링
    PROM->>ALERT: 5️⃣ 알림 규칙 위반 감지
    ALERT->>SLACK: 6️⃣ Slack 알림 발송
```

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

  # Kubernetes 환경: Pod 어노테이션 기반 자동 디스커버리
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
        for: 2m          # 2분간 지속될 때만 알림 (일시적 스파이크 무시)
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

# P95 응답시간 (상위 5% 느린 요청의 응답시간)
histogram_quantile(0.95, rate(http_server_requests_seconds_bucket[5m]))

# 에러율 (5xx 응답 비율)
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

Spring Boot 애플리케이션의 메트릭을 Prometheus로 내보내는 설정이다. Micrometer는 메트릭 수집 추상화 계층으로, Prometheus 외에 Datadog, InfluxDB 등으로도 동일하게 전송할 수 있다.

```gradle
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-actuator'
    implementation 'io.micrometer:micrometer-registry-prometheus'
}
```

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health, info, prometheus, metrics
  endpoint:
    health:
      show-details: always
      probes:
        enabled: true  # liveness, readiness 엔드포인트 분리 (K8s probe용)
  metrics:
    tags:
      application: ${spring.application.name}
      environment: ${spring.profiles.active}
    distribution:
      percentiles-histogram:
        http.server.requests: true  # 히스토그램 활성화 (P95 계산에 필요)
      slo:
        http.server.requests: 100ms, 500ms, 1s, 2s
```

### 커스텀 메트릭

```java
@Component
@RequiredArgsConstructor
public class OrderMetrics {

    private final MeterRegistry registry;

    @PostConstruct
    public void init() {
        // Counter: 단조증가 카운터 (주문 수, 에러 수)
        Counter.builder("order.created.total")
            .description("생성된 주문 수")
            .tag("type", "all")
            .register(registry);

        // Timer: 처리 시간 측정 (분포 포함)
        Timer.builder("order.processing.duration")
            .description("주문 처리 시간")
            .publishPercentiles(0.5, 0.95, 0.99)
            .register(registry);

        // Gauge: 현재 상태를 반영하는 값 (람다로 실시간 제공)
        // register(registry) 호출 시 람다가 주기적으로 호출됨
    }

    public void registerPendingOrdersGauge(OrderRepository repository) {
        Gauge.builder("order.pending.count", repository,
                r -> r.countByStatus(OrderStatus.PENDING))
            .description("처리 대기 중인 주문 수")
            .register(registry);
    }
}
```

Counter는 단조 증가만 하므로 `rate()`로 초당 변화량을 계산한다. Gauge는 현재값을 바로 사용한다.

---

## ELK Stack

**E**lasticsearch + **L**ogstash + **K**ibana. 로그 수집, 저장, 시각화 스택이다.

```mermaid
graph LR
    APP["Spring App\n(Logback JSON 출력)"] -->|"JSON 로그"| FB["Filebeat\n(로그 파일 감시)"]
    FB -->|"전송"| LS["Logstash\n(파싱/필터링/변환)"]
    LS -->|"저장"| ES[("Elasticsearch\n(검색/저장)")]
    ES -->|"쿼리"| KI["Kibana\n(시각화/검색)"]
```

### Spring Logback JSON 설정

로그를 JSON으로 출력하면 Elasticsearch에 구조화된 형태로 저장되어 `traceId`, `userId` 등으로 필터링이 가능하다.

```xml
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

`traceId`가 있으면 ELK에서 검색해 해당 요청이 거친 모든 서비스의 로그를 한 화면에서 조회할 수 있다.

### Logstash 파이프라인

```ruby
input {
  beats { port => 5044 }
}

filter {
  json { source => "message" }

  if [level] == "ERROR" {
    mutate { add_tag => ["error"] }
  }

  geoip { source => "clientIp" }  # IP 지역 정보 추가
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "myapp-logs-%{+YYYY.MM.dd}"
    ilm_enabled => true
    ilm_rollover_alias => "myapp-logs"
    ilm_policy => "myapp-logs-policy"    # 오래된 인덱스 자동 삭제
  }
}
```

---

## Datadog

SaaS 형태의 통합 모니터링 플랫폼이다. Metrics/Logs/Traces를 하나의 플랫폼에서 제공한다.

**장점**:
- 설치가 매우 간단 (Agent 하나로 모든 것)
- UI/UX가 우수함
- APM(Application Performance Monitoring) 내장
- 이상 감지(Anomaly Detection) AI 내장

**단점**:
- 비용이 높음 (Host당 월 $15~$35)
- 데이터가 외부로 나감 (금융권 제약 가능성)

```java
// dd-java-agent 사용 — JVM 옵션만으로 자동 계측, 코드 변경 불필요
// -javaagent:/path/to/dd-java-agent.jar
// -Ddd.service=myapp
// -Ddd.env=production
// -Ddd.version=1.0.0
// -Ddd.logs.injection=true   // 로그에 traceId 자동 주입
```

---

## 4 Golden Signals (SRE 기준)

Google SRE에서 정의한 서비스 품질의 핵심 4가지 신호다. 이 네 가지를 모니터링하면 대부분의 장애를 조기에 감지할 수 있다.

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
  예) 가용성 >= 99.9%, P95 응답시간 <= 500ms

SLA (Service Level Agreement): 고객과의 계약
  예) 가용성 < 99.9% 시 서비스 크레딧 제공
```

SLO는 SLA보다 약간 엄격하게 설정해야 한다. SLO를 위반하지 않아야 SLA 위반을 방지할 수 있다.

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
  → Slack #alerts
```

알림이 너무 많으면 중요한 알림도 무시하게 된다(Alert Fatigue). P0~P2로 분류해 각 수준에 맞는 채널과 대응 시간을 정해야 한다.

---

<details class="extreme-scenario-details" ontoggle="if(this.open){var ad=this.querySelector('.extreme-scenario-ad');if(ad&&!ad.dataset.loaded){ad.dataset.loaded='1';(adsbygoogle=window.adsbygoogle||[]).push({});}}">
<summary class="extreme-scenario-summary">
<span class="extreme-scenario-icon">🔥</span>
<span class="extreme-scenario-label">극한 시나리오 — 클릭하여 펼치기</span>
<span class="extreme-scenario-toggle"></span>
</summary>
<div class="extreme-scenario-body">
<div class="extreme-scenario-ad" style="text-align:center; margin-bottom:1.5em;">
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="ca-pub-7225106491387870"
     data-ad-slot="0000000000"
     data-ad-format="auto"
     data-full-width-responsive="true"></ins>
</div>
<div class="extreme-scenario-content" markdown="1">

### 시나리오 1: 메트릭은 정상인데 사용자 불만 폭발

HTTP 200 응답률 99.9%이지만 결제 성공률이 60%인 경우다. 기술 메트릭만 보고 비즈니스 메트릭을 놓친 것이다.

```promql
# 기술 메트릭 (정상처럼 보임): HTTP 200 응답률 99.9%
rate(http_requests_total{status="200"}[5m]) / rate(http_requests_total[5m])

# 비즈니스 메트릭 (실제 문제): 결제 성공률 60%
rate(payment_success_total[5m]) / rate(payment_attempt_total[5m])
```

HTTP 200이어도 결제 로직 내부에서 비즈니스 실패가 발생할 수 있다. 비즈니스 메트릭을 반드시 커스텀 메트릭으로 추가해야 한다.

### 시나리오 2: 로그 스토리지 폭발 — 한 달 3TB

```
원인: 모든 요청에 DEBUG 로그 출력, 로그 보존 정책 없음

해결:
1. 로그 레벨 조정: 프로덕션은 WARN 이상만
2. 샘플링: 정상 요청의 1%만 DEBUG 로깅
3. ILM (Index Lifecycle Management):
   - 7일: Hot (자주 조회)
   - 30일: Cold (드물게 조회)
   - 30일 후: 삭제
4. 중요도별 보존 기간 분리:
   - ERROR 로그: 90일
   - INFO 로그: 7일
```

### 시나리오 3: Prometheus 스토리지 부족

기본 보존 기간(15일)과 스크레이프 간격(15초), 메트릭 수에 따라 스토리지가 빠르게 찬다.

```yaml
# prometheus 실행 시 보존 기간 및 스토리지 제한
--storage.tsdb.retention.time=30d
--storage.tsdb.retention.size=50GB
```

장기 저장이 필요하면 Thanos 또는 Cortex로 원격 스토리지에 적재한다.

### 시나리오 4: 알림 폭풍 (Alert Storm)

한 서비스 장애로 수십 개 알림이 동시에 발생하면 핵심 알림을 놓친다. Alertmanager의 그룹핑과 억제(Inhibit) 규칙으로 연쇄 알림을 방지한다.

```yaml
# alertmanager.yml — 같은 서비스 알림을 5분간 모아서 한 번에 발송
route:
  group_by: ['alertname', 'job']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

inhibit_rules:
  # 서비스 다운 알림이 있으면 그 서비스의 레이턴시 알림은 억제
  - source_match:
      alertname: 'ServiceDown'
    target_match:
      alertname: 'HighLatency'
    equal: ['job']
```
</div>
</div>
</details>

