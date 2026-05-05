---
title: "Spring Boot - 정적 컨텐츠, MVC 템플릿, API"
categories: SPRING
tags: [SpringBoot, StaticContent, MVC, Thymeleaf, API, ResponseBody, Jackson]
toc: true
toc_sticky: true
toc_label: 목차
date: 2021-05-22
---

Spring Boot에서 웹 요청에 응답하는 방식은 크게 세 가지다. 정적 파일을 그대로 내려주는 방식, 서버에서 HTML을 동적으로 생성하는 MVC 방식, JSON 데이터를 반환하는 API 방식이다. 각 방식이 언제 사용되는지, 내부에서 어떻게 동작하는지를 이해하는 것이 Spring Boot의 핵심이다.

> **비유**: 정적 컨텐츠는 냉동식품(미리 만들어진 것을 그대로), MVC 템플릿은 주문 즉석 조리(서버에서 데이터를 넣어 HTML 생성), API는 재료만 배달(JSON 데이터만 보내고 클라이언트가 화면 구성)이다.

---

## 1단계: 세 가지 응답 방식 비교

<div class="mermaid">
graph TD
    BR["브라우저 요청"]
    BR --> DS["DispatcherServlet"]
    DS --> Q1{"컨트롤러가\n처리 가능한가?"}
    Q1 -->|"없음"| STATIC["정적 컨텐츠\nresources/static/\n파일을 그대로 반환"]
    Q1 -->|"있음"| Q2{"@ResponseBody\n또는 @RestController?"}
    Q2 -->|"없음"| MVC["MVC + 템플릿 엔진\nViewResolver → Thymeleaf\nHTML 동적 생성 후 반환"]
    Q2 -->|"있음"| API["API 방식\nHttpMessageConverter\n객체 → JSON 변환 후 반환"]
</div>

---

## 2단계: 정적 컨텐츠 (Static Content)

정적 컨텐츠는 서버에서 아무런 가공 없이 파일 자체를 그대로 반환하는 방식이다.

### 동작 원리

<div class="mermaid">
sequenceDiagram
    participant B as "브라우저"
    participant DS as "DispatcherServlet"
    participant RC as "ResourceController (내장)"
    participant FS as "파일 시스템"

    B->>DS: 1️⃣ GET /hello-static.html
    DS->>DS: 2️⃣ 컨트롤러에서 /hello-static.html 매핑 찾기
    DS-->>DS: 3️⃣ 매핑 없음
    DS->>RC: 4️⃣ 정적 리소스 처리로 위임
    RC->>FS: 5️⃣ resources/static/hello-static.html 찾기
    FS-->>B: 6️⃣ 파일 내용 그대로 반환
</div>

```
정적 파일 위치:
src/main/resources/
├── static/
│   ├── index.html          → localhost:8080/
│   ├── hello-static.html   → localhost:8080/hello-static.html
│   ├── css/
│   │   └── style.css       → localhost:8080/css/style.css
│   └── js/
│       └── app.js          → localhost:8080/js/app.js
```

```html
<!-- src/main/resources/static/hello-static.html -->
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>정적 파일</title></head>
<body>
    <h1>이 파일은 서버에서 가공 없이 그대로 전달됩니다.</h1>
    <p>Thymeleaf 문법 ${data} 같은 것은 처리되지 않습니다.</p>
</body>
</html>
```

**핵심 요약**: 정적 컨텐츠는 이미지, CSS, JS처럼 서버 데이터가 필요 없는 고정된 파일에 사용한다. 서버 처리가 없어 가장 빠르다.

---

## 3단계: MVC와 템플릿 엔진

사용자에게 개인화된 화면을 보여주거나 서버 데이터를 HTML에 포함해야 할 때 사용한다.

### 동작 원리

<div class="mermaid">
sequenceDiagram
    participant B as "브라우저"
    participant DS as "DispatcherServlet"
    participant C as "HelloController"
    participant VR as "ViewResolver"
    participant TH as "Thymeleaf"

    B->>DS: 1️⃣ GET /hello-mvc?name=spring
    DS->>C: 2️⃣ helloMvc(name="spring", model)
    C->>C: 3️⃣ model.addAttribute("name", "spring")
    C-->>DS: 4️⃣ return "hello-template"
    DS->>VR: 5️⃣ "hello-template" 뷰 찾기
    VR->>TH: 6️⃣ templates/hello-template.html + model 데이터
    TH-->>B: 7️⃣ 완성된 HTML 반환
</div>

### 컨트롤러

```java
@Controller
public class HelloController {

    @GetMapping("/hello-mvc")
    public String helloMvc(@RequestParam("name") String name, Model model) {
        // 브라우저: localhost:8080/hello-mvc?name=spring
        model.addAttribute("name", name);
        return "hello-template"; // ViewResolver로 hello-template.html 찾음
    }
}
```

### 템플릿

```html
<!-- src/main/resources/templates/hello-template.html -->
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<body>
    <!-- th:text="${name}": 서버에서 ${name} 값으로 교체 -->
    <!-- "hello! empty": th 처리 전 화면에서 보이는 기본값 (Thymeleaf 자연 템플릿) -->
    <p th:text="'hello! ' + ${name}">hello! empty</p>
</body>
</html>
```

**Thymeleaf 자연 템플릿의 장점**: `th:text`가 있는 태그는 서버 처리 없이 파일로 열어도 기본값(`hello! empty`)이 표시된다. 디자이너와 협업할 때 서버 없이 HTML 파일을 직접 확인할 수 있다.

---

## 4단계: API 방식 — @ResponseBody

화면(HTML)이 아닌 데이터(JSON)만 반환하는 방식이다. 프론트엔드(React, Vue)와 분리된 백엔드 API 서버나 모바일 앱의 백엔드로 주로 사용한다.

### 문자열 반환

```java
@Controller
public class HelloController {

    @GetMapping("/hello-string")
    @ResponseBody // HTTP 응답 Body에 직접 반환값을 씀
    public String helloString(@RequestParam("name") String name) {
        return "hello " + name; // 문자열 그대로 반환 (HTML이 아닌 text/plain)
    }
}
// localhost:8080/hello-string?name=spring → 브라우저에 "hello spring" 텍스트 표시
```

### 객체 반환 (JSON)

```java
@Controller
public class HelloController {

    @GetMapping("/hello-api")
    @ResponseBody
    public Hello helloApi(@RequestParam("name") String name) {
        Hello hello = new Hello();
        hello.setName(name);
        return hello; // 객체 → Jackson이 JSON으로 자동 변환
    }

    static class Hello {
        private String name;
        // getter/setter 필수 (Jackson이 리플렉션으로 직렬화)
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
    }
}
// localhost:8080/hello-api?name=spring
// 응답: {"name":"spring"}
```

### @ResponseBody 동작 원리

<div class="mermaid">
graph TD
    CTRL["컨트롤러\nreturn Hello 객체"]
    CHECK{"반환 타입 확인"}
    CONV["HttpMessageConverter"]
    STR["StringHttpMessageConverter\n문자열 → text/plain"]
    JSON["MappingJackson2HttpMessageConverter\n객체 → application/json (JSON 변환)"]
    RESP["HTTP Response Body"]

    CTRL --> CHECK
    CHECK -->|"String"| STR
    CHECK -->|"객체"| JSON
    STR --> CONV
    JSON --> CONV
    CONV --> RESP
</div>

**핵심 요약**: `@ResponseBody`가 있으면 ViewResolver를 거치지 않는다. 대신 `HttpMessageConverter`가 반환값을 HTTP 응답 Body로 직접 변환한다. 문자열은 그대로, 객체는 Jackson 라이브러리가 JSON으로 변환한다.

### @RestController — @Controller + @ResponseBody 합성

실무에서 REST API를 만들 때는 `@RestController`를 사용한다.

```java
@RestController // @Controller + @ResponseBody 합성
@RequestMapping("/api")
public class MemberApiController {

    @GetMapping("/members/{id}")
    public MemberDto getMember(@PathVariable Long id) {
        return new MemberDto(id, "kim", 25);
        // 자동으로 JSON 변환: {"id":1,"name":"kim","age":25}
    }

    @PostMapping("/members")
    public MemberDto createMember(@RequestBody MemberDto dto) {
        // @RequestBody: JSON → 객체 변환 (역직렬화)
        return memberService.save(dto);
    }

    record MemberDto(Long id, String name, int age) {}
}
```

---

## 5단계: 세 방식 선택 기준

| 방식 | 반환 타입 | 사용 시점 | 예시 |
|------|-----------|-----------|------|
| 정적 컨텐츠 | HTML/CSS/JS 파일 | 서버 데이터 불필요 | 회사 소개 페이지 |
| MVC 템플릿 | Thymeleaf HTML | 서버 데이터 포함한 HTML | 관리자 대시보드 |
| API (@ResponseBody) | JSON | 프론트엔드/모바일 백엔드 | REST API 서버 |

```
현재 개발 트렌드:
└─ API 방식이 주류
   ├─ 프론트엔드: React, Vue (JavaScript에서 JSON 받아 화면 구성)
   └─ 백엔드: @RestController로 JSON API만 제공

   MVC 템플릿 방식은:
   └─ 관리자 페이지, 내부 도구 등 서버사이드 렌더링이 필요한 경우
```

---

<details class="extreme-scenario-details">
<summary class="extreme-scenario-summary">
<span class="extreme-scenario-icon">🔥</span>
<span class="extreme-scenario-label">극한 시나리오 — 클릭하여 펼치기</span>
<span class="extreme-scenario-toggle"></span>
</summary>
<div class="extreme-scenario-body">

<div class="extreme-scenario-content" markdown="1">

### 시나리오 1: @ResponseBody 없이 객체 반환

```java
// 잘못된 코드: @ResponseBody 없이 객체 반환
@Controller
public class HelloController {
    @GetMapping("/hello-api")
    public Hello helloApi() {
        return new Hello("spring"); // String이 아니고 객체
    }
}
// 결과: Hello를 뷰 이름으로 해석 → ViewResolver가 Hello.html 찾음 → 404 에러
// 해결: @ResponseBody 추가 또는 @RestController 사용
```

### 시나리오 2: Jackson 직렬화 실패 — getter 없음

```java
// 잘못된 코드: getter 없음
static class Hello {
    private String name; // getter 없음
}
// 결과: JSON 직렬화 시 name 필드를 읽지 못해 {} 또는 예외

// 해결 방법:
// 방법 1: getter 추가
public String getName() { return name; }

// 방법 2: Lombok @Getter
@Getter
static class Hello { private String name; }

// 방법 3: record 사용 (Java 16+)
record Hello(String name) {} // 자동으로 getter(name()) 생성
```

### 시나리오 3: @RequestParam 누락 → 400 Bad Request

```java
@GetMapping("/hello-mvc")
public String helloMvc(@RequestParam("name") String name, Model model) {
    // required = true가 기본값 → name 파라미터 없으면 400 에러
    model.addAttribute("name", name);
    return "hello-template";
}
// localhost:8080/hello-mvc → 400 Bad Request

// 해결: defaultValue 또는 required=false 설정
@RequestParam(value = "name", defaultValue = "Guest") String name
// 또는
@RequestParam(value = "name", required = false) String name
```

### 시나리오 4: 정적 파일과 컨트롤러 경로 충돌

```
resources/static/hello.html 파일이 존재하면서
@GetMapping("/hello")도 존재할 때:

우선순위: 컨트롤러(@GetMapping)가 정적 파일보다 우선
→ 컨트롤러가 먼저 처리되어 정적 파일은 무시됨

주의: resources/static/ 아래 파일명이 컨트롤러 경로와 겹치지 않도록 관리
```

---
</div>
</div>
</details>

## 실무 체크리스트

```
□ REST API 백엔드라면 @RestController 사용 (매번 @ResponseBody 생략)
□ JSON 직렬화를 위해 DTO 클래스에 getter 필수 (또는 Lombok/record)
□ @RequestParam required=true(기본값) 인지 확인 — 필수 아니면 defaultValue 설정
□ 정적 파일 경로와 컨트롤러 경로 충돌 방지
□ 응답 데이터에 민감 정보(@JsonIgnore) 처리
□ API 응답은 표준 구조(code, message, data) 통일
```

---

```
참조 - 스프링 입문 - 코드로 배우는 스프링 부트, 웹 MVC, DB 접근 기술 By 김영한
```
