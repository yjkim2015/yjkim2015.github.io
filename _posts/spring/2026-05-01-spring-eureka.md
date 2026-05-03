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

하드코딩된 IP를 사용하면 재배포 시 IP가 변경될 때 장애가 발생한다. Service Discovery를 사용하면 서비스 이름으로 호출하므로 인스턴스 위치 변경에 자동으로 대응한다.

1️⃣ **자가 등록**: 서비스 인스턴스가 시작할 때 Eureka Server에 자신의 정보(IP, Port, 서비스명)를 등록한다
2️⃣ **서비스 조회**: 호출자가 Eureka Server에 서비스 이름으로 인스턴스 목록을 요청한다
3️⃣ **클라이언트 사이드 로드밸런싱**: 받은 인스턴스 목록 중 하나를 선택해 직접 호출한다
4️⃣ **Heartbeat**: 인스턴스가 살아있음을 주기적으로 알린다

```mermaid
sequenceDiagram
    participant S as "서비스 인스턴스"
    participant E as "Eureka Server"
    participant C as "클라이언트 서비스"

    S->>E: 1️⃣ POST /eureka/apps/{appName} (Register)
    Note over E: "레지스트리에 인스턴스 추가"
    loop "매 10초 (lease-renewal-interval)"
        S->>E: 2️⃣ PUT /eureka/apps/{appName}/{instanceId} (Heartbeat)
        E-->>S: 200 OK
    end
    C->>E: 3️⃣ 서비스 이름으로 인스턴스 목록 조회
    E-->>C: 인스턴스 목록 반환
    C->>S: 4️⃣ 직접 HTTP 호출
    S->>E: DELETE /eureka/apps/{appName}/{instanceId} (Deregister)
```

---

## Eureka 아키텍처

```mermaid
graph LR
    subgraph "Eureka Server 클러스터"
        ES1["Eureka Server 1"]
        ES2["Eureka Server 2"]
        ES1 <-->|"Peer Replication"| ES2
    end

    subgraph "마이크로서비스들"
        OS["Order Service\nEureka Client"]
        US["User Service\nEureka Client"]
        PS["Product Service\nEureka Client"]
    end

    OS -->|"Register/Heartbeat"| ES1
    US -->|"Register/Heartbeat"| ES2
    PS -->|"Register/Heartbeat"| ES1

    OS -->|"Discover user-service"| ES1
    ES1 -->|"인스턴스 목록"| OS
    OS -->|"직접 HTTP 호출"| US
```

---

## Eureka Server 구성

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-netflix-eureka-server</artifactId>
</dependency>
```

```java
@SpringBootApplication
@EnableEurekaServer
public class EurekaServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(EurekaServerApplication.class, args);
    }
}
```

```yaml
server:
  port: 8761

eureka:
  instance:
    hostname: localhost
  client:
    # 서버 자신은 레지스트리에 등록하지 않음
    register-with-eureka: false
    fetch-registry: false
  server:
    enable-self-preservation: false  # 개발 환경: 빠른 인스턴스 정리
    eviction-interval-timer-in-ms: 5000
```

---

## Eureka Client 구성

```yaml
server:
  port: 8080

spring:
  application:
    name: order-service  # 레지스트리에 등록될 이름

eureka:
  instance:
    prefer-ip-address: true  # 컨테이너 환경에서 중요
    lease-renewal-interval-in-seconds: 10   # Heartbeat 전송 주기
    lease-expiration-duration-in-seconds: 30 # 이 시간 내 Heartbeat 없으면 만료
    instance-id: ${spring.application.name}:${server.port}
  client:
    register-with-eureka: true
    fetch-registry: true
    service-url:
      defaultZone: http://localhost:8761/eureka/
    registry-fetch-interval-seconds: 5  # 레지스트리 갱신 주기
```

---

## 로드밸런싱 (Spring Cloud LoadBalancer 연동)

Eureka에서 인스턴스 목록을 가져와 클라이언트 사이드 로드밸런싱을 수행한다.

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

    public UserDto getUser(Long userId) {
        // IP:Port 대신 서비스 이름으로 호출
        return restTemplate.getForObject(
            "http://user-service/users/" + userId,  // Spring Cloud LoadBalancer가 실제 주소로 변환
            UserDto.class
        );
    }
}
```

```java
// FeignClient 방식
@FeignClient(name = "user-service")  // Eureka 서비스 이름
public interface UserServiceClient {

    @GetMapping("/users/{userId}")
    UserDto getUser(@PathVariable Long userId);
}
```

---

## 자가 보호 모드 (Self-Preservation Mode)

Eureka Server의 중요한 특성이다. 네트워크 장애로 인해 Heartbeat가 일시적으로 감소했을 때, 멀쩡한 인스턴스를 대거 제거하지 않도록 보호한다.

기대 Heartbeat 수보다 실제 수신량이 85% 미만이 되면 자가 보호 모드에 진입한다. 이 모드에서는 인스턴스 만료/제거가 중단된다. 네트워크가 복구되면 자동으로 해제된다.

```mermaid
graph TD
    A["Heartbeat 감소 감지"] --> B{"실제 수신 < 85% 임계치?"}
    B -->|"Yes"| C["자가 보호 모드 진입"]
    B -->|"No"| D["정상 동작"]
    C --> E["인스턴스 만료 중단"]
    C --> F["레지스트리 현상 유지"]
    C --> G["경고 메시지 표시"]
    E --> H["네트워크 복구 후 자동 해제"]
```

이는 Eureka가 AP(Available + Partition-tolerant) 시스템임을 보여준다. 네트워크 파티션 상황에서 일관성보다 가용성을 선택한다.

---

## Eureka Server 고가용성 (HA 구성)

단일 Eureka Server는 SPOF가 된다. 프로덕션에서는 최소 2개 이상의 Peer를 구성한다.

```yaml
# eureka-server-1 (포트 8761)
eureka:
  instance:
    hostname: eureka-server-1
  client:
    register-with-eureka: true   # 피어에게 자신을 등록
    fetch-registry: true
    service-url:
      defaultZone: http://eureka-server-2:8762/eureka/  # 피어 서버 지정

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

```mermaid
graph TD
    subgraph "HA Eureka 클러스터"
        ES1["Eureka Server 1\n:8761"]
        ES2["Eureka Server 2\n:8762"]
        ES1 <-->|"Peer Replication"| ES2
    end

    MS1["Order Service"] -->|"Register"| ES1
    MS2["User Service"] -->|"Register"| ES2
    MS3["Product Service"] -->|"Register"| ES1

    MS1 -->|"Discovery"| ES1
    MS1 -.->|"Fallback"| ES2
```

---

## 클라이언트 사이드 캐시

Eureka Client는 서버에서 받은 레지스트리를 로컬에 캐시한다. 서버가 잠시 다운돼도 클라이언트는 캐시로 서비스 호출을 계속할 수 있다.

```
캐시 레이어:
Eureka Server
  ↓ 5초마다 fetch (설정값)
Eureka Client 로컬 캐시
  ↓ 서비스 호출 시 참조
로드밸런서 (Spring Cloud LoadBalancer)
```

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

### 시나리오 1: Eureka Server 전체 장애

Eureka는 AP 시스템이다. 서버가 모두 다운돼도 클라이언트는 로컬 캐시로 수분간 서비스 호출을 계속할 수 있다. Eureka가 재기동하면 클라이언트가 자동으로 재등록한다.

Circuit Breaker와 Retry를 함께 사용하면 일시적 오류를 흡수할 수 있다.

### 시나리오 2: 배포 시 Graceful Shutdown

```java
// 배포 전 인스턴스를 OUT_OF_SERVICE로 변경 → 새 트래픽 차단 후 기존 요청 처리 완료
@PostMapping("/actuator/out-of-service")
public void outOfService() {
    eurekaClient.getApplicationInfoManager()
        .setInstanceStatus(InstanceStatus.OUT_OF_SERVICE);
}
```

### 시나리오 3: 네트워크 파티션 (Split Brain)

두 Eureka Server가 서로 통신 불가 상태가 되면 각자 다른 레지스트리를 갖게 된다. Eureka는 AP를 선택하므로 불완전한 정보라도 서비스를 계속 제공한다. 파티션이 해소되면 자동으로 수렴한다.

일관성이 중요한 경우 Consul(CP), ZooKeeper(CP)를 대안으로 고려할 수 있다.

---
</div>
</div>
</details>

## Kubernetes 환경에서 Eureka

K8s 내부 통신에는 K8s Service(ClusterIP)가 자체 Service Discovery를 제공한다. 단일 K8s 클러스터에서는 Eureka 없이 K8s Service를 사용하는 것이 권장된다. 하이브리드(온프레미스 + 클라우드) 또는 멀티 클러스터 환경에서는 Eureka가 여전히 유효하다.
