---
title: "Spring Cloud Eureka"
categories: SPRING
tags: [Eureka, ServiceDiscovery, SpringCloud, LoadBalancing, MSA]
toc: true
toc_sticky: true
toc_label: 목차
date: 2026-05-01
---

마이크로서비스 환경에서 서비스들은 동적으로 생성·삭제·이동된다. IP와 포트를 하드코딩하면 배포할 때마다 설정을 바꿔야 한다. Spring Cloud Eureka는 이 문제를 해결하는 Service Discovery 솔루션이다. 서비스가 스스로 자신의 위치를 등록하고, 호출자는 이름으로 찾는다.

> **비유**: 넷플릭스 본사 전화번호부(Eureka Server)가 있다. 각 팀(마이크로서비스)이 출근하면 전화번호부에 자기 자리와 번호를 등록한다(자가 등록). 다른 팀이 연락하고 싶으면 전화번호부에서 이름으로 찾으면 된다(Service Discovery). 팀이 자리를 비우면 전화번호부에서 삭제된다(자가 해제).

---

## Service Discovery란?

전통적인 단일 서버 환경에서는 IP가 고정돼 있어 문제가 없었다. 하지만 MSA + 컨테이너 환경에서는 서비스 인스턴스가 수시로 바뀐다.

```
문제 상황:
Order Service → User Service 호출 시
  하드코딩: http://192.168.1.10:8080/users  ← 재배포 시 IP 변경되면 장애
  DNS: 변경 전파 지연 문제
  Service Discovery: http://user-service/users  ← 항상 최신 위치 참조
```

<div class="mermaid">
graph TD
    subgraph "Service Discovery 흐름"
        A[서비스 인스턴스 시작] -->|1. 자가 등록| B[Eureka Server]
        C[클라이언트 서비스] -->|2. 서비스 조회| B
        B -->|3. 인스턴스 목록 반환| C
        C -->|4. 직접 호출| D[대상 서비스]
        D -->|5. 주기적 Heartbeat| B
    end
</div>

---

## Eureka 아키텍처

### 구성 요소

| 구성 요소 | 역할 |
|---|---|
| Eureka Server | 서비스 레지스트리. 등록된 모든 인스턴스 정보 보관 |
| Eureka Client | 각 마이크로서비스에 내장. 등록·갱신·조회 담당 |
| Service Registry | 인스턴스 메타데이터(호스트, 포트, 상태) 저장소 |

<div class="mermaid">
graph LR
    subgraph "Eureka Server 클러스터"
        ES1[Eureka Server 1]
        ES2[Eureka Server 2]
        ES1 <-->|Peer Replication| ES2
    end

    subgraph "마이크로서비스들"
        OS[Order Service\nEureka Client]
        US[User Service\nEureka Client]
        PS[Product Service\nEureka Client]
    end

    OS -->|Register/Heartbeat| ES1
    US -->|Register/Heartbeat| ES2
    PS -->|Register/Heartbeat| ES1

    OS -->|Discover user-service| ES1
    ES1 -->|인스턴스 목록| OS
    OS -->|직접 HTTP 호출| US
</div>

---

## Eureka Server 구성

### 의존성

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-netflix-eureka-server</artifactId>
</dependency>
```

### 메인 클래스

```java
@SpringBootApplication
@EnableEurekaServer
public class EurekaServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(EurekaServerApplication.class, args);
    }
}
```

### application.yml (단독 실행 모드)

```yaml
server:
  port: 8761

spring:
  application:
    name: eureka-server

eureka:
  instance:
    hostname: localhost
  client:
    # 서버 자신은 레지스트리에 등록하지 않음
    register-with-eureka: false
    fetch-registry: false
    service-url:
      defaultZone: http://localhost:8761/eureka/
  server:
    # 개발 환경: 자가 보호 모드 비활성화
    enable-self-preservation: false
    # 만료된 인스턴스 정리 주기 (ms)
    eviction-interval-timer-in-ms: 5000
```

---

## Eureka Client 구성

### 의존성

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-netflix-eureka-client</artifactId>
</dependency>
```

### 메인 클래스

```java
@SpringBootApplication
@EnableDiscoveryClient  // 또는 생략 가능 (자동 감지)
public class OrderServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(OrderServiceApplication.class, args);
    }
}
```

### application.yml

```yaml
server:
  port: 8080

spring:
  application:
    name: order-service  # 레지스트리에 등록될 이름

eureka:
  instance:
    # 호스트명 대신 IP 사용 (컨테이너 환경에서 중요)
    prefer-ip-address: true
    # Heartbeat 전송 주기 (기본: 30초)
    lease-renewal-interval-in-seconds: 10
    # 이 시간 내 Heartbeat 없으면 만료 (기본: 90초)
    lease-expiration-duration-in-seconds: 30
    # 인스턴스 ID 커스텀 (같은 서비스 여러 인스턴스 구분)
    instance-id: ${spring.application.name}:${server.port}
  client:
    register-with-eureka: true
    fetch-registry: true
    service-url:
      defaultZone: http://localhost:8761/eureka/
    # 레지스트리 갱신 주기 (기본: 30초)
    registry-fetch-interval-seconds: 5
```

---

## 자가 등록 / 해제 흐름

<div class="mermaid">
sequenceDiagram
    participant S as 서비스 인스턴스
    participant E as Eureka Server

    S->>E: POST /eureka/apps/{appName} (Register)
    Note over E: 레지스트리에 인스턴스 추가
    E-->>S: 200 OK

    loop 매 10초 (lease-renewal-interval)
        S->>E: PUT /eureka/apps/{appName}/{instanceId} (Heartbeat)
        E-->>S: 200 OK
    end

    S->>E: DELETE /eureka/apps/{appName}/{instanceId} (Deregister)
    Note over E: 레지스트리에서 인스턴스 제거
    E-->>S: 200 OK
</div>

### 비정상 종료 시 처리

서비스가 graceful shutdown 없이 죽으면 `DELETE` 요청이 전송되지 않는다. Eureka Server는 `lease-expiration-duration-in-seconds` 시간(기본 90초) 내에 Heartbeat가 없으면 해당 인스턴스를 만료 처리한다.

```
시나리오: Order Service가 갑자기 죽음 (kill -9)
  t=0: Heartbeat 수신 중단
  t=30s: 마지막 Heartbeat 후 30초 경과 → 인스턴스 만료 표시
  t=60s: Eviction 주기에 레지스트리에서 제거
  → 클라이언트는 최대 약 60~120초간 죽은 인스턴스로 요청할 수 있음
  → 이를 보완하기 위해 Retry, Circuit Breaker와 함께 사용
```

---

## 헬스체크

### 기본 헬스체크

Eureka Client는 기본적으로 Heartbeat만으로 상태를 판단한다. 서비스가 응답은 하지만 DB 연결이 끊겼어도 `UP` 상태로 보일 수 있다.

### Actuator 기반 헬스체크 연동

```yaml
# application.yml
eureka:
  client:
    healthcheck:
      enabled: true  # Actuator /health 결과를 Eureka에 반영

management:
  endpoints:
    web:
      exposure:
        include: health, info
  endpoint:
    health:
      show-details: always
```

```xml
<!-- 의존성 추가 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

### 커스텀 헬스 인디케이터

```java
@Component
public class DatabaseHealthIndicator implements HealthIndicator {

    private final DataSource dataSource;

    public DatabaseHealthIndicator(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public Health health() {
        try (Connection conn = dataSource.getConnection()) {
            conn.isValid(1);
            return Health.up()
                .withDetail("database", "connected")
                .build();
        } catch (SQLException e) {
            // DB 연결 실패 시 Eureka 상태도 DOWN으로 전파
            return Health.down()
                .withDetail("database", "connection failed")
                .withException(e)
                .build();
        }
    }
}
```

---

## 로드밸런싱 (Spring Cloud LoadBalancer 연동)

Eureka에서 인스턴스 목록을 가져와 클라이언트 사이드 로드밸런싱을 수행한다.

### RestTemplate 방식

```java
@Configuration
public class RestTemplateConfig {

    @Bean
    @LoadBalanced  // 이 어노테이션 하나로 Eureka + 로드밸런싱 활성화
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}

@Service
public class OrderService {

    private final RestTemplate restTemplate;

    public OrderService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    public UserDto getUser(Long userId) {
        // IP:Port 대신 서비스 이름으로 호출
        // Spring Cloud LoadBalancer가 Eureka에서 인스턴스 목록 조회 후 선택
        return restTemplate.getForObject(
            "http://user-service/users/" + userId,
            UserDto.class
        );
    }
}
```

### WebClient 방식 (reactive)

```java
@Configuration
public class WebClientConfig {

    @Bean
    @LoadBalanced
    public WebClient.Builder webClientBuilder() {
        return WebClient.builder();
    }
}

@Service
public class OrderService {

    private final WebClient.Builder webClientBuilder;

    public Mono<UserDto> getUser(Long userId) {
        return webClientBuilder.build()
            .get()
            .uri("http://user-service/users/" + userId)
            .retrieve()
            .bodyToMono(UserDto.class);
    }
}
```

### FeignClient 방식

```java
@FeignClient(name = "user-service")  // Eureka 서비스 이름
public interface UserServiceClient {

    @GetMapping("/users/{userId}")
    UserDto getUser(@PathVariable Long userId);
}
```

---

## 자가 보호 모드 (Self-Preservation Mode)

Eureka Server의 중요한 특성이다. 네트워크 장애로 인해 Heartbeat가 일시적으로 감소했을 때, 멀쩡한 인스턴스를 대거 제거하지 않도록 보호한다.

```
동작 원리:
- 기대 Heartbeat 수 = 등록 인스턴스 수 × 2 × 0.85 (85% 임계치)
- 실제 Heartbeat < 기대 수 → 자가 보호 모드 진입
- 자가 보호 모드: 인스턴스 만료/제거 중단
- 이유: 네트워크 파티션 상황에서 잘못된 제거 방지 (AP 선택)
```

<div class="mermaid">
graph TD
    A[Heartbeat 감소 감지] --> B{실제 수신 < 85% 임계치?}
    B -->|Yes| C[자가 보호 모드 진입]
    B -->|No| D[정상 동작]
    C --> E[인스턴스 만료 중단]
    C --> F[레지스트리 유지]
    C --> G[경고: EMERGENCY! EUREKA MAY BE INCORRECTLY CLAIMING...]
    E --> H[네트워크 복구 후 자동 해제]
</div>

### 운영 환경 설정 권장사항

```yaml
# 운영 환경: 자가 보호 모드 활성화 (기본값)
eureka:
  server:
    enable-self-preservation: true

# 개발/테스트 환경: 빠른 인스턴스 정리를 위해 비활성화
eureka:
  server:
    enable-self-preservation: false
    eviction-interval-timer-in-ms: 3000
```

---

## Eureka Server 고가용성 (HA 구성)

단일 Eureka Server는 SPOF(Single Point of Failure)가 된다. 프로덕션에서는 최소 2개 이상의 Peer를 구성한다.

### Peer-to-Peer 복제

```yaml
# eureka-server-1 (포트 8761)
spring:
  application:
    name: eureka-server

eureka:
  instance:
    hostname: eureka-server-1
  client:
    register-with-eureka: true   # 피어에게 자신을 등록
    fetch-registry: true
    service-url:
      # 피어 서버 URL 지정 → 레지스트리 정보 동기화
      defaultZone: http://eureka-server-2:8762/eureka/

---
# eureka-server-2 (포트 8762)
eureka:
  instance:
    hostname: eureka-server-2
  client:
    service-url:
      defaultZone: http://eureka-server-1:8761/eureka/
```

```yaml
# 클라이언트: 두 서버 모두 등록
eureka:
  client:
    service-url:
      defaultZone: http://eureka-server-1:8761/eureka/,http://eureka-server-2:8762/eureka/
```

<div class="mermaid">
graph TD
    subgraph "HA Eureka 클러스터"
        ES1[Eureka Server 1\n:8761]
        ES2[Eureka Server 2\n:8762]
        ES1 <-->|Peer Replication| ES2
    end

    MS1[Order Service] -->|Register| ES1
    MS2[User Service] -->|Register| ES2
    MS3[Product Service] -->|Register| ES1

    ES1 -->|동기화| ES2
    MS1 -->|Discovery| ES1
    MS1 -.->|Fallback| ES2
</div>

---

## 클라이언트 사이드 캐시

Eureka Client는 서버에서 받은 레지스트리를 로컬에 캐시한다. 서버가 잠시 다운돼도 클라이언트는 캐시를 사용해 서비스 호출을 계속할 수 있다.

```
캐시 레이어:
Eureka Server
  ↓ 30초마다 fetch
Eureka Client 로컬 캐시 (readWriteCacheMap)
  ↓ 30초마다 동기화
클라이언트 읽기 캐시 (readOnlyCacheMap)
  ↓ 서비스 호출 시 참조
로드밸런서 (Spring Cloud LoadBalancer)
```

```yaml
eureka:
  client:
    # 레지스트리 갱신 주기 단축 (기본 30초, 개발 환경에서 5초로)
    registry-fetch-interval-seconds: 5
    # 초기 인스턴스 정보 복제 간격
    initial-instance-info-replication-interval-seconds: 5
```

---

## 극한 시나리오

### 시나리오 1: Eureka Server 전체 장애

```
상황: 두 Eureka Server 모두 다운
대응:
1. 클라이언트 로컬 캐시로 최대 수분간 서비스 호출 지속
2. 재시도 로직으로 일시적 오류 흡수
3. Eureka 재기동 후 자동 재등록
4. Circuit Breaker로 연쇄 장애 차단

핵심: Eureka는 AP(Available + Partition-tolerant) 시스템
  → 서버 다운 시 오래된 정보라도 계속 서빙
  → 일관성보다 가용성 우선
```

### 시나리오 2: 배포 시 Blue/Green

```java
// 배포 전 graceful shutdown: 인스턴스를 먼저 OUT_OF_SERVICE로 변경
// 새 트래픽 차단 후 기존 요청 처리 완료 후 종료

@RestController
public class ShutdownController {

    private final EurekaClient eurekaClient;

    @PostMapping("/actuator/out-of-service")
    public void outOfService() {
        // Eureka에 OUT_OF_SERVICE 상태 등록 → 로드밸런서에서 제외
        eurekaClient.getApplicationInfoManager()
            .setInstanceStatus(InstanceStatus.OUT_OF_SERVICE);
    }
}
```

### 시나리오 3: 네트워크 파티션 (Split Brain)

```
상황: Eureka Server 1, 2가 서로 통신 불가
결과:
  Server 1: 자신에게 등록된 인스턴스만 알고 있음
  Server 2: 자신에게 등록된 인스턴스만 알고 있음
  → 각 서버가 서로 다른 레지스트리를 가짐

Eureka의 선택: AP (가용성 우선)
  → 불완전한 정보라도 서비스 계속 제공
  → 파티션 해소 후 자동 수렴

대안: Consul (CP), ZooKeeper (CP)
  → 일관성이 중요한 경우 선택
```

---

## 모니터링 엔드포인트

```
Eureka Dashboard: http://localhost:8761/
  → 등록된 모든 인스턴스, 상태, Heartbeat 현황

REST API:
  GET /eureka/apps                         전체 레지스트리
  GET /eureka/apps/{appName}               특정 앱 인스턴스 목록
  GET /eureka/apps/{appName}/{instanceId}  특정 인스턴스 정보
  PUT /eureka/apps/{appName}/{instanceId}/status?value=OUT_OF_SERVICE  상태 변경
```

```yaml
# 인스턴스 메타데이터 추가 (대시보드에 표시)
eureka:
  instance:
    metadata-map:
      version: "1.0.0"
      zone: "us-east-1a"
      profile: "production"
```

---

## Kubernetes 환경에서 Eureka

K8s 환경에서는 자체 Service Discovery(kube-dns, Service)가 있어 Eureka와 역할이 겹친다.

```
K8s 내부 통신: K8s Service (ClusterIP) 사용
  → 별도 Eureka 불필요

K8s 외부 또는 멀티 클러스터: Eureka 활용 가능
  → Spring Cloud Kubernetes로 대체도 가능

결론: K8s 단일 클러스터 → K8s Service 권장
      하이브리드(온프레미스 + 클라우드) → Eureka 유효
```
