---
title: "Spring Boot View 환경 설정"
categories: SPRING
tags: [SpringBoot, Thymeleaf, ViewResolver, MVC, Controller]
toc: true
toc_sticky: true
toc_label: 목차
date: 2021-05-19
---

Spring Boot에서 웹 요청이 들어왔을 때 어떤 화면을 보여줄지 결정하는 것이 View 환경 설정이다. 정적 파일을 그냥 내려주는 방식과, 서버에서 데이터를 조합해 동적으로 HTML을 생성하는 방식의 두 가지가 있다.

> **비유**: 정적 컨텐츠는 이미 인쇄된 책을 그대로 주는 것이고, 템플릿 엔진은 손님의 이름을 적어서 주는 맞춤 초대장을 만드는 것이다.

---

## 1단계: Welcome Page 만들기

Spring Boot는 `resources/static/index.html` 파일이 존재하면 자동으로 Welcome Page로 제공한다. 별도의 컨트롤러 설정이 필요 없다.

```
src/main/resources/
├── static/
│   └── index.html   ← 자동으로 localhost:8080/ 에 매핑
└── templates/
```

```html
<!-- src/main/resources/static/index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Hello Spring Boot</title>
    <meta charset="UTF-8">
</head>
<body>
    <h1>홈 페이지</h1>
    <p>Hello Spring Boot!</p>
    <a href="/hello">Hello 페이지로 이동</a>
</body>
</html>
```

브라우저에서 `http://localhost:8080`을 열면 index.html이 그대로 표시된다.

---

## 2단계: Thymeleaf 템플릿 엔진으로 동적 페이지

`/hello` 링크를 클릭하면 404 에러가 발생한다. 컨트롤러가 없기 때문이다. `/hello` 요청을 처리하는 컨트롤러와 Thymeleaf 템플릿을 만들어보자.

### 요청 처리 흐름

<div class="mermaid">
sequenceDiagram
    participant B as "브라우저"
    participant DS as "DispatcherServlet"
    participant C as "HelloController"
    participant VR as "ViewResolver"
    participant TH as "Thymeleaf (템플릿 엔진)"

    B->>DS: 1️⃣ GET /hello
    DS->>C: 2️⃣ @GetMapping("/hello") 메서드 호출
    C-->>DS: 3️⃣ Model에 데이터 추가\nreturn "hello" (뷰 이름)
    DS->>VR: 4️⃣ "hello" 뷰 찾기
    VR->>TH: 5️⃣ resources/templates/hello.html 렌더링
    TH-->>B: 6️⃣ 완성된 HTML 반환
</div>

### 컨트롤러 작성

```java
package com.example.hellospringspring.controller;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

@Controller // @Component 역할 + 웹 요청 처리 컴포넌트
public class HelloController {

    @GetMapping("/hello") // GET /hello 요청 처리
    public String hello(Model model) {
        // Model에 데이터를 담으면 템플릿에서 사용 가능
        model.addAttribute("data", "Hello Spring Boot!");
        return "hello"; // "hello" → resources/templates/hello.html 렌더링
    }

    @GetMapping("/hello-param")
    public String helloParam(@RequestParam(value = "name", defaultValue = "Guest") String name,
                              Model model) {
        model.addAttribute("name", name);
        return "hello-param"; // localhost:8080/hello-param?name=Kim
    }
}
```

### Thymeleaf 템플릿 작성

```html
<!-- src/main/resources/templates/hello.html -->
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head>
    <title>Hello</title>
    <meta charset="UTF-8">
</head>
<body>
    <p th:text="'안녕하세요. ' + ${data}">기본 텍스트</p>
    <!-- th:text: 서버에서 렌더링 시 이 속성 값으로 교체됨 -->
    <!-- ${data}: Model에 담긴 data 속성 값 출력 -->
</body>
</html>
```

```html
<!-- src/main/resources/templates/hello-param.html -->
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<body>
    <p th:text="'안녕하세요. ' + ${name} + '님!'">기본 텍스트</p>
</body>
</html>
```

### ViewResolver 동작 원리

```
컨트롤러에서 return "hello" 반환 시:

ViewResolver가 다음 경로로 파일을 찾는다:
  resources/templates/ + "hello" + .html
= resources/templates/hello.html

설정 (application.yml, 기본값이므로 보통 생략):
spring:
  thymeleaf:
    prefix: classpath:/templates/
    suffix: .html
```

---

## 3단계: Thymeleaf 주요 문법

### 기본 표현식

```html
<!-- 변수 출력 -->
<p th:text="${data}">기본값</p>

<!-- URL 링크 -->
<a th:href="@{/hello(name=${name})}">링크</a>
<!-- 결과: /hello?name=Kim -->

<!-- 조건부 출력 -->
<p th:if="${user != null}" th:text="${user.name}">이름</p>
<p th:unless="${user != null}">로그인이 필요합니다</p>

<!-- 반복 처리 -->
<ul>
    <li th:each="item : ${items}" th:text="${item.name}">상품명</li>
</ul>

<!-- 인라인 표현식 -->
<p>안녕하세요 [[${name}]]님!</p>
<!-- ${name}이 "Kim"이면 → "안녕하세요 Kim님!" -->
```

### 레이아웃 템플릿 (공통 헤더/푸터)

```html
<!-- src/main/resources/templates/layout/base.html -->
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org"
      xmlns:layout="http://www.ultraq.net.nz/thymeleaf/layout">
<head>
    <meta charset="UTF-8">
    <title>My App</title>
</head>
<body>
    <header>공통 헤더</header>
    <div layout:fragment="content">
        <!-- 각 페이지의 컨텐츠가 여기에 삽입됨 -->
    </div>
    <footer>공통 푸터</footer>
</body>
</html>

<!-- 개별 페이지에서 레이아웃 적용 -->
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org"
      xmlns:layout="http://www.ultraq.net.nz/thymeleaf/layout"
      layout:decorate="~{layout/base}">
<div layout:fragment="content">
    <h1>이 페이지만의 컨텐츠</h1>
</div>
</html>
```

---

## 4단계: 개발 편의 도구

### spring-boot-devtools — 서버 재시작 없이 변경 반영

```groovy
// build.gradle
dependencies {
    developmentOnly 'org.springframework.boot:spring-boot-devtools'
}
```

```yaml
# application.yml
spring:
  devtools:
    restart:
      enabled: true  # Java 코드 변경 시 자동 재시작
    livereload:
      enabled: true  # HTML/CSS 변경 시 브라우저 자동 새로고침
```

**동작 방식**: devtools는 클래스패스 파일이 변경되면 애플리케이션을 자동으로 재시작한다. 전체 재시작보다 훨씬 빠른 것은 2개의 ClassLoader를 사용하기 때문이다. 변하지 않는 라이브러리는 base classloader로, 개발 중인 코드는 restart classloader로 로드한다. 재시작 시 restart classloader만 새로 로드한다.

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

### 시나리오 1: 뷰 이름 대신 전체 경로 반환

```java
// 잘못된 코드: 확장자 포함
@GetMapping("/hello")
public String hello(Model model) {
    return "hello.html"; // 잘못됨 — 파일을 찾지 못함
    // ViewResolver는 prefix + viewName + suffix 조합
    // prefix = classpath:/templates/
    // suffix = .html (이미 포함되어 있음)
    // → 실제 경로: classpath:/templates/hello.html.html → 404
}

// 올바른 코드
public String hello(Model model) {
    return "hello"; // 확장자 없이 뷰 이름만 반환
}
```

### 시나리오 2: XSS 취약점 — th:text vs th:utext

```html
<!-- 가정: data = "<script>alert('XSS')</script>" -->

<!-- th:text: HTML 이스케이프 적용 (안전) -->
<p th:text="${data}"></p>
<!-- 렌더링 결과: &lt;script&gt;alert('XSS')&lt;/script&gt; -->

<!-- th:utext: HTML 이스케이프 없음 (위험!) -->
<p th:utext="${data}"></p>
<!-- 렌더링 결과: <script>alert('XSS')</script> → XSS 공격 가능 -->

<!-- 실무: 사용자 입력 데이터는 반드시 th:text 사용 -->
<!-- th:utext는 신뢰할 수 있는 HTML만 사용 -->
```

### 시나리오 3: Model 데이터 누락

```java
// 잘못된 코드: Model에 데이터를 넣지 않음
@GetMapping("/hello")
public String hello() {
    // model.addAttribute("data", "...") 누락
    return "hello";
}
// 템플릿에서 ${data} 접근 → null 출력 또는 예외 발생
```

```java
// 올바른 코드: 항상 필요한 데이터를 Model에 담기
@GetMapping("/hello")
public String hello(Model model) {
    model.addAttribute("data", service.getData()); // null 가능성도 처리
    return "hello";
}
```

---
</div>
</div>
</details>

## 실무 체크리스트

```
□ 사용자 입력 데이터 출력 시 th:text 사용 (XSS 방지)
□ th:utext는 신뢰할 수 있는 시스템 데이터에만 사용
□ 컨트롤러 return 값에 .html 확장자 포함 금지
□ 공통 레이아웃(헤더/푸터)은 Thymeleaf Layout Dialect 활용
□ 개발 환경에서 spring-boot-devtools 적용 (빠른 피드백 루프)
□ application-dev.yml, application-prod.yml로 환경별 설정 분리
```

---

```
참조 - 스프링 입문 - 코드로 배우는 스프링 부트, 웹 MVC, DB 접근 기술 By 김영한
```
