---
title: "Spring Boot 프로젝트 생성"
categories: SPRING
tags: [SpringBoot, Gradle, Maven, Dependencies, SpringInitializr]
toc: true
toc_sticky: true
toc_label: 목차
date: 2021-04-27
---

Spring Boot는 복잡한 스프링 설정을 자동화해서 빠르게 프로젝트를 시작할 수 있게 해주는 프레임워크다. 과거에는 XML 설정 파일 작성, 서버 배포 설정, 라이브러리 버전 충돌 해결에 많은 시간을 쏟았지만, Spring Boot는 이 모든 것을 자동으로 처리해준다.

> **비유**: Spring Boot는 인테리어 패키지와 같다. 기본 구조(벽, 바닥, 전기)가 이미 갖춰진 집에 입주하는 것처럼, 프로젝트의 기본 설정이 이미 완성되어 있어서 비즈니스 로직 작성에만 집중할 수 있다.

---

## 1단계: Spring Boot가 해결하는 문제

### 과거 Spring 프로젝트의 어려움

```
기존 Spring 프로젝트 설정 순서:
1. 라이브러리 버전 직접 지정 (버전 충돌 빈번)
2. web.xml, applicationContext.xml, dispatcher-servlet.xml 작성
3. Tomcat 별도 설치 및 배포 설정
4. 첫 Hello World까지 수 시간 소요
```

### Spring Boot가 자동화하는 것

<div class="mermaid">
graph TD
    SB["Spring Boot"]
    SB --> AC["Auto Configuration\n@SpringBootApplication이 붙으면\n클래스패스 기반으로 설정 자동화"]
    SB --> SM["Starter 의존성\nspring-boot-starter-web 하나로\nSpring MVC + Tomcat + Jackson 모두 포함"]
    SB --> ES["내장 서버\nTomcat이 내장되어\njar 파일 하나로 실행 가능"]
    SB --> DP["기본값 자동 설정\napplication.yml로\n필요한 것만 오버라이드"]
</div>

---

## 2단계: 프로젝트 생성

### Spring Initializr 사용 (권장)

브라우저에서 [https://start.spring.io](https://start.spring.io)에 접속하거나, IntelliJ IDEA의 New Project > Spring Initializr를 사용한다.

```
설정 항목:
- Project:     Gradle - Groovy (Maven도 가능하지만 Gradle이 표준)
- Language:    Java
- Spring Boot: 3.x.x (최신 안정 버전)
- Group:       com.example
- Artifact:    hello-spring
- Packaging:   Jar
- Java:        17 (또는 21 LTS)
```

**의존성(Dependencies) 선택**

```
Spring Web        → REST API, Spring MVC, 내장 Tomcat
Thymeleaf         → 서버 사이드 템플릿 엔진 (SSR)
Spring Data JPA   → JPA/Hibernate 통합
H2 Database       → 인메모리 DB (개발/테스트용)
Lombok            → boilerplate 코드 자동 생성
```

### 생성된 프로젝트 구조

```
hello-spring/
├── src/
│   ├── main/
│   │   ├── java/
│   │   │   └── com/example/hellospringspring/
│   │   │       └── HelloSpringApplication.java  ← 진입점
│   │   └── resources/
│   │       ├── static/          ← 정적 파일 (HTML, CSS, JS, 이미지)
│   │       ├── templates/       ← Thymeleaf 템플릿
│   │       └── application.yml  ← 애플리케이션 설정
│   └── test/
│       └── java/                ← 테스트 코드
├── build.gradle                 ← 의존성 관리
└── gradlew                      ← Gradle Wrapper (설치 없이 빌드)
```

### build.gradle 분석

```groovy
plugins {
    id 'java'
    id 'org.springframework.boot' version '3.2.0'   // Spring Boot 플러그인
    id 'io.spring.dependency-management' version '1.1.4' // 의존성 버전 자동 관리
}

group = 'com.example'
version = '0.0.1-SNAPSHOT'

java {
    sourceCompatibility = '17'
}

dependencies {
    // Starter: 관련 라이브러리를 한 번에 묶어서 가져옴
    implementation 'org.springframework.boot:spring-boot-starter-web'
    // → spring-webmvc + spring-web + tomcat-embed + jackson 등 자동 포함

    implementation 'org.springframework.boot:spring-boot-starter-thymeleaf'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    runtimeOnly 'com.h2database:h2'
    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'

    testImplementation 'org.springframework.boot:spring-boot-starter-test'
}
```

**Gradle vs Maven 선택 기준**

| 항목 | Gradle | Maven |
|------|--------|-------|
| 빌드 속도 | 빠름 (증분 빌드, 캐시) | 느림 (전체 빌드) |
| 설정 방식 | Groovy/Kotlin DSL (코드) | XML (선언적) |
| 현재 트렌드 | Spring Boot 기본값 | 레거시 프로젝트에서 사용 |

---

## 3단계: 첫 실행

### 진입점 클래스

```java
package com.example.hellospringspring;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication // 3가지 어노테이션의 합성
// @SpringBootConfiguration: 이 클래스가 설정 클래스임을 표시
// @EnableAutoConfiguration: 클래스패스 기반으로 자동 설정 활성화
// @ComponentScan: 이 패키지부터 @Component, @Controller 등 스캔
public class HelloSpringApplication {

    public static void main(String[] args) {
        SpringApplication.run(HelloSpringApplication.class, args);
        // 내장 Tomcat 서버 시작 → 포트 8080 열림
    }
}
```

### 실행 방법

```bash
# 방법 1: IDE에서 직접 실행 (HelloSpringApplication.main())

# 방법 2: Gradle Wrapper로 실행
./gradlew bootRun

# 방법 3: jar 파일 빌드 후 실행
./gradlew build
java -jar build/libs/hello-spring-0.0.1-SNAPSHOT.jar
```

### 실행 로그 확인

```
  .   ____          _            __ _ _
 /\\ / ___'_ __ _ _(_)_ __  __ _ \ \ \ \
...
2024-01-01 12:00:00 INFO  o.s.b.w.e.tomcat.TomcatWebServer  :
  Tomcat started on port(s): 8080 (http) with context path ''
2024-01-01 12:00:00 INFO  c.e.h.HelloSpringApplication      :
  Started HelloSpringApplication in 1.234 seconds (process running for 1.567)
```

브라우저에서 `http://localhost:8080`을 열면 Whitelabel Error Page(404)가 나타나는데, 이는 정상이다. 아직 컨트롤러가 없어서 "/" 경로에 매핑된 핸들러가 없기 때문이다.

---

## 4단계: 동작 원리

### @SpringBootApplication 자동 설정

<div class="mermaid">
graph TD
    MAIN["1️⃣ main() 실행\nSpringApplication.run()"]
    SCAN["2️⃣ @ComponentScan\n패키지 내 @Component, @Controller,\n@Service, @Repository 스캔"]
    AUTO["3️⃣ @EnableAutoConfiguration\nspring.factories 파일 기반\n자동 설정 클래스 로드\n(DataSourceAutoConfiguration 등)"]
    CTX["4️⃣ ApplicationContext 생성\n스프링 컨테이너 초기화\nBean 등록 완료"]
    TOM["5️⃣ 내장 Tomcat 시작\nport 8080 열림"]

    MAIN --> SCAN --> AUTO --> CTX --> TOM
</div>

### application.yml 기본 설정

```yaml
server:
  port: 8080          # 포트 변경 가능

spring:
  application:
    name: hello-spring
  datasource:
    url: jdbc:h2:mem:testdb  # H2 인메모리 DB
    driver-class-name: org.h2.Driver
  jpa:
    hibernate:
      ddl-auto: create-drop  # 개발용: 시작 시 테이블 생성, 종료 시 삭제
    show-sql: true            # SQL 로그 출력
  h2:
    console:
      enabled: true           # H2 웹 콘솔 활성화 (localhost:8080/h2-console)
```

---

## 극한 시나리오

### 시나리오 1: 의존성 버전 충돌

```groovy
// 잘못된 코드: 버전을 직접 지정하면 BOM 관리와 충돌 가능
implementation 'com.fasterxml.jackson.core:jackson-databind:2.14.0' // 직접 지정 금지

// 올바른 코드: 버전 생략 → Spring Boot BOM이 호환 버전 자동 선택
implementation 'com.fasterxml.jackson.core:jackson-databind'
// io.spring.dependency-management 플러그인이 호환 버전 보장
```

### 시나리오 2: 포트 충돌

```
Error: Web server failed to start. Port 8080 was already in use.

해결책:
```

```yaml
# application.yml
server:
  port: 8081  # 다른 포트 사용
```

```bash
# 또는 실행 시 오버라이드
java -jar app.jar --server.port=8081
```

### 시나리오 3: @SpringBootApplication 위치 문제

```java
// 잘못된 위치: 패키지 최상위에 있지 않으면 하위 패키지 스캔 안됨
package com.example.hello.config; // 너무 깊은 위치

// 올바른 위치: 모든 하위 패키지를 아우르는 최상위 패키지
package com.example.hello;

@SpringBootApplication // com.example.hello.** 전체 스캔
public class HelloApplication { ... }
```

---

## 실무 체크리스트

```
□ Spring Boot 버전은 LTS 버전 사용 (예: 3.2.x)
□ Java 버전은 LTS 사용 (17 또는 21)
□ 의존성 버전 직접 지정 지양 (BOM 관리 활용)
□ @SpringBootApplication은 최상위 패키지에 위치
□ 운영/개발 프로파일 분리 (application-dev.yml, application-prod.yml)
□ build.gradle에 불필요한 의존성 추가 지양
```

---

```
참조 - 스프링 입문 - 코드로 배우는 스프링 부트, 웹 MVC, DB 접근 기술 By 김영한
```
