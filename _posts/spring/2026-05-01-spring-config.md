---
title: "Spring Cloud Config"
categories: SPRING
tags: [SpringCloudConfig, ConfigServer, RefreshScope, GitConfig, MSA]
toc: true
toc_sticky: true
toc_label: 목차
date: 2026-05-01
---

100개의 마이크로서비스에 DB 비밀번호를 바꿔야 한다면? 각 서비스마다 설정 파일을 수정하고 재배포하면 수십 분이 걸린다. Spring Cloud Config는 모든 서비스의 설정을 한 곳에서 관리하고, 재배포 없이 런타임에 반영하는 중앙 집중 설정 관리 솔루션이다.

> **비유**: 대기업 인사팀(Config Server)이 회사 규정집(설정)을 관리한다. 각 부서(마이크로서비스)는 자체 규정집을 갖지 않고 인사팀에 물어본다. 규정이 바뀌면 인사팀만 수정하면 되고, 각 부서에 공지(refresh)를 보내면 새 규정이 즉시 적용된다.

---

## 중앙 집중 설정 관리의 필요성

```
기존 방식 문제점:
서비스 A: application.yml → DB 비밀번호 변경 → 재빌드 → 재배포
서비스 B: application.yml → DB 비밀번호 변경 → 재빌드 → 재배포
서비스 C: application.yml → DB 비밀번호 변경 → 재빌드 → 재배포
  ...100개 서비스 반복

Spring Cloud Config:
Config Server (Git) → 비밀번호 변경 → 클라이언트에 refresh 신호 → 즉시 반영
  → 재빌드/재배포 없음
```

<div class="mermaid">
graph TD
    subgraph "설정 저장소"
        GIT[Git Repository\n/config-repo]
    end

    subgraph "Config Server"
        CS[Spring Cloud Config Server\n:8888]
    end

    subgraph "마이크로서비스들"
        OS[Order Service]
        US[User Service]
        PS[Product Service]
    end

    GIT -->|설정 파일 읽기| CS
    CS -->|설정 제공| OS
    CS -->|설정 제공| US
    CS -->|설정 제공| PS
</div>

---

## Config Server 구성

### 의존성

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-config-server</artifactId>
</dependency>
```

### 메인 클래스

```java
@SpringBootApplication
@EnableConfigServer
public class ConfigServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(ConfigServerApplication.class, args);
    }
}
```

### application.yml (Git 기반)

```yaml
server:
  port: 8888

spring:
  application:
    name: config-server
  cloud:
    config:
      server:
        git:
          # 설정 파일이 저장된 Git 저장소
          uri: https://github.com/your-org/config-repo
          # 기본 브랜치
          default-label: main
          # 로컬 클론 경로
          basedir: /tmp/config-repo
          # 검색 경로 (하위 디렉토리 사용 시)
          search-paths: '{application}'
          # private repo 인증
          username: ${GIT_USERNAME}
          password: ${GIT_TOKEN}
          # 강제 pull (로컬 변경 무시)
          force-pull: true
          # 클론 실패 시 로컬 캐시 사용
          clone-on-start: true
```

---

## 설정 파일 구조 (Git 저장소)

Config Server는 파일명 패턴으로 설정을 분류한다.

```
config-repo/
├── application.yml              # 모든 서비스 공통 설정
├── application-prod.yml         # 모든 서비스 prod 환경 공통
├── order-service.yml            # order-service 전용 (모든 환경)
├── order-service-dev.yml        # order-service dev 환경
├── order-service-prod.yml       # order-service prod 환경
├── user-service.yml
└── user-service-prod.yml
```

### URL 패턴

```
/{application}/{profile}[/{label}]
/{application}-{profile}.yml
/{label}/{application}-{profile}.yml

예시:
GET http://localhost:8888/order-service/prod
GET http://localhost:8888/order-service/prod/main
GET http://localhost:8888/order-service-prod.yml
```

### 설정 우선순위 (높음 → 낮음)

```
1. {application}-{profile}.yml  (order-service-prod.yml)
2. {application}.yml            (order-service.yml)
3. application-{profile}.yml    (application-prod.yml)
4. application.yml              (전체 공통)
```

---

## Config Client 구성

### 의존성

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-config</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

### bootstrap.yml (스프링 부트 2.x)

```yaml
# bootstrap.yml: application.yml보다 먼저 로드됨
# Config Server에서 나머지 설정을 가져올 위치 지정
spring:
  application:
    name: order-service   # Config Server에서 찾을 파일명
  cloud:
    config:
      uri: http://localhost:8888
      profile: prod         # {application}-{profile}.yml 매핑
      label: main           # Git 브랜치/태그
      fail-fast: true       # Config Server 연결 실패 시 즉시 종료
      retry:
        max-attempts: 6
        initial-interval: 1000
        multiplier: 1.1
        max-interval: 2000
```

### application.yml (스프링 부트 3.x)

```yaml
# 스프링 부트 3.x에서는 bootstrap.yml 대신 application.yml에 작성
spring:
  application:
    name: order-service
  config:
    import: "configserver:http://localhost:8888"
  cloud:
    config:
      profile: prod
```

---

## 런타임 설정 갱신 (@RefreshScope)

### @RefreshScope 사용

설정값을 런타임에 갱신하려면 해당 Bean에 `@RefreshScope`를 붙인다.

```java
@RestController
@RefreshScope  // POST /actuator/refresh 호출 시 이 Bean이 재생성됨
public class OrderController {

    @Value("${order.max-items:10}")
    private int maxItems;

    @Value("${order.discount-rate:0.0}")
    private double discountRate;

    @GetMapping("/config")
    public Map<String, Object> getConfig() {
        return Map.of(
            "maxItems", maxItems,
            "discountRate", discountRate
        );
    }
}
```

```java
// @ConfigurationProperties도 @RefreshScope 적용 가능
@Component
@RefreshScope
@ConfigurationProperties(prefix = "order")
public class OrderProperties {
    private int maxItems = 10;
    private double discountRate = 0.0;
    // getter/setter
}
```

### 수동 refresh

```bash
# Git에 설정 변경 후 커밋
git commit -m "change order.max-items to 20"
git push

# 특정 서비스 인스턴스에 refresh 요청
curl -X POST http://order-service:8080/actuator/refresh
```

### actuator 설정

```yaml
management:
  endpoints:
    web:
      exposure:
        include: refresh, bus-refresh, health, info
```

---

## Spring Cloud Bus (자동 전파)

개별 서비스 인스턴스마다 `POST /actuator/refresh`를 호출하면 인스턴스가 100개일 때 100번 호출해야 한다. Spring Cloud Bus는 메시지 브로커(RabbitMQ 또는 Kafka)를 통해 전체에 전파한다.

### 의존성

```xml
<!-- RabbitMQ 기반 -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-bus-amqp</artifactId>
</dependency>

<!-- Kafka 기반 -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-bus-kafka</artifactId>
</dependency>
```

<div class="mermaid">
sequenceDiagram
    participant DEV as 개발자
    participant GIT as Git
    participant CS as Config Server
    participant MQ as RabbitMQ/Kafka
    participant OS1 as Order Service #1
    participant OS2 as Order Service #2
    participant US as User Service

    DEV->>GIT: 설정 파일 변경 & push
    DEV->>CS: POST /actuator/bus-refresh
    CS->>MQ: RefreshRemoteApplicationEvent 발행
    MQ->>OS1: 이벤트 수신
    MQ->>OS2: 이벤트 수신
    MQ->>US: 이벤트 수신
    OS1->>CS: 새 설정 fetch
    OS2->>CS: 새 설정 fetch
    US->>CS: 새 설정 fetch
    Note over OS1,US: 재배포 없이 새 설정 적용
</div>

### Bus 설정

```yaml
spring:
  rabbitmq:
    host: localhost
    port: 5672
    username: guest
    password: guest
  cloud:
    bus:
      enabled: true
      refresh:
        enabled: true

management:
  endpoints:
    web:
      exposure:
        include: bus-refresh
```

### Webhook 자동화

```
GitHub Webhook 설정:
  URL: http://config-server:8888/monitor
  Content-Type: application/json
  Events: Push events

→ Git push 시 자동으로 Config Server에 알림
→ Config Server가 Bus에 refresh 이벤트 발행
→ 모든 클라이언트에 자동 전파
```

---

## 설정 암호화

민감한 정보(DB 비밀번호, API 키)는 평문으로 Git에 저장하면 안 된다. Config Server는 대칭키/비대칭키 암호화를 지원한다.

### 대칭키 암호화

```yaml
# Config Server application.yml
encrypt:
  key: my-secret-encryption-key-32chars
```

```bash
# 값 암호화
curl -X POST http://localhost:8888/encrypt -d "my-db-password"
# 결과: AQBxxx...암호화된문자열

# 값 복호화
curl -X POST http://localhost:8888/decrypt -d "AQBxxx..."
```

### 설정 파일에서 암호화값 사용

```yaml
# config-repo/order-service-prod.yml
spring:
  datasource:
    # {cipher} 접두사로 암호화된 값 표시
    password: '{cipher}AQBxxx...암호화된문자열'
    url: jdbc:mysql://prod-db:3306/orders
    username: order_user
```

### 비대칭키 암호화 (RSA)

```bash
# 키쌍 생성
keytool -genkeypair -alias config-server-key \
  -keyalg RSA -keysize 4096 \
  -sigalg SHA256withRSA \
  -dname "CN=Config Server,OU=IT" \
  -keypass mypassword \
  -keystore server.jks \
  -storepass mypassword
```

```yaml
# application.yml
encrypt:
  keyStore:
    location: classpath:server.jks
    password: mypassword
    alias: config-server-key
    secret: mypassword
```

---

## 다양한 백엔드

Git 외에도 다양한 설정 저장소를 지원한다.

### 로컬 파일시스템 (개발 환경)

```yaml
spring:
  cloud:
    config:
      server:
        native:
          search-locations:
            - file:///opt/config
            - classpath:/config
  profiles:
    active: native
```

### Vault (HashiCorp)

```yaml
spring:
  cloud:
    config:
      server:
        vault:
          host: localhost
          port: 8200
          scheme: http
          backend: secret
          default-key: application
```

### AWS Parameter Store

```yaml
spring:
  cloud:
    config:
      server:
        awsParameterStore:
          region: ap-northeast-2
          prefix: /config
```

---

## 극한 시나리오

### 시나리오 1: Config Server 장애

```
문제: Config Server 다운 → 클라이언트 재시작 불가
  → spring.cloud.config.fail-fast=true 설정 시 기동 중단

대응 전략:
1. Config Server 다중화 (로드밸런서 뒤에 2개 이상)
2. 클라이언트 retry 설정
3. 최후 수단: spring.cloud.config.fail-fast=false + 로컬 application.yml 폴백

retry 설정:
spring:
  cloud:
    config:
      fail-fast: true
      retry:
        max-attempts: 10
        initial-interval: 1000
        multiplier: 1.5
        max-interval: 5000
```

### 시나리오 2: 설정 변경 롤백

```bash
# Git 기반이라 롤백이 간단
git revert HEAD
git push

# 또는 특정 커밋으로 복구
git reset --hard {commit-hash}
git push --force

# Bus refresh로 전파
curl -X POST http://config-server:8888/actuator/bus-refresh
```

### 시나리오 3: 환경별 설정 오염 방지

```yaml
# config-repo 구조 권장 패턴
config-repo/
├── shared/
│   └── application.yml        # 진짜 공통 설정만
├── services/
│   ├── order-service/
│   │   ├── application.yml    # dev 기본값
│   │   ├── application-staging.yml
│   │   └── application-prod.yml
│   └── user-service/
│       └── ...
└── secrets/
    └── application-prod.yml   # 암호화된 민감 정보만

# prod 설정에 실수로 dev DB 연결 방지:
# → 환경별 디렉토리 분리 + PR 리뷰 필수
```

### 시나리오 4: @RefreshScope 사용 불가 영역

```java
// @RefreshScope는 Spring Bean에만 적용됨
// 다음은 refresh 불가:
// 1. DataSource (커넥션 풀 재생성 문제)
// 2. @Scheduled (초기화 시점에 값 고정)
// 3. static 필드

// 해결책: 런타임에 동적으로 값을 읽는 구조

@Service
public class OrderService {

    // 나쁜 예: 시작 시점에 주입되어 refresh 안됨
    // @Value("${order.fee-rate}")
    // private double feeRate;

    // 좋은 예: 매번 Environment에서 읽음
    @Autowired
    private Environment environment;

    public double getFeeRate() {
        return Double.parseDouble(
            environment.getProperty("order.fee-rate", "0.03")
        );
    }
}
```

---

## Config Server 보안

Config Server 자체는 민감한 정보를 제공하므로 반드시 보안을 적용해야 한다.

```yaml
# Config Server에 Basic Auth 적용
spring:
  security:
    user:
      name: config-admin
      password: ${CONFIG_SERVER_PASSWORD}

# 클라이언트 설정
spring:
  cloud:
    config:
      uri: http://localhost:8888
      username: config-admin
      password: ${CONFIG_SERVER_PASSWORD}
```

```
추가 보안 권장사항:
1. Config Server는 내부 네트워크에만 노출 (인터넷 직접 접근 차단)
2. mTLS로 클라이언트 인증
3. Git 토큰 최소 권한 (read-only)
4. 감사 로그: 누가 언제 어떤 설정을 변경했는지 Git history로 추적
5. 암호화되지 않은 민감 정보는 절대 Git에 커밋 금지
```
