---
title: "브라우저 렌더링 과정 완전 정복"
categories:
- FRONTEND
toc: true
toc_sticky: true
toc_label: 목차
---

## 레스토랑 주방에서 요리가 나오기까지

URL을 입력하고 엔터를 누르는 순간, 브라우저는 엄청난 일을 시작합니다. 이를 레스토랑에 비유해 봅시다.

1. **주문서 받기** (HTML 파일 수신)
2. **재료 목록 만들기** (DOM, CSSOM 생성)
3. **요리 레시피 결합** (렌더 트리 생성)
4. **그릇 크기 결정** (레이아웃)
5. **음식 색깔 입히기** (페인트)
6. **접시에 담기** (컴포지팅)

이 6단계를 **Critical Rendering Path(CRP)**라고 합니다.

---

## 1. 전체 렌더링 파이프라인

```mermaid
flowchart LR
    HTML["HTML 파싱"] --> DOM["DOM 생성"]
    CSS["CSS 파싱"] --> CSSOM["CSSOM 생성"]
    DOM --> RT["렌더 트리<br/>Render Tree"]
    CSSOM --> RT
    RT --> L["레이아웃<br/>Layout/Reflow"]
    L --> P["페인트<br/>Paint"]
    P --> C["컴포지팅<br/>Compositing"]
    C --> SCREEN["화면 출력"]

    JS["JavaScript 실행"] -->|DOM/CSSOM 수정| DOM
    JS -->|DOM/CSSOM 수정| CSSOM

    style DOM fill:#e74c3c,color:#fff
    style CSSOM fill:#3498db,color:#fff
    style RT fill:#9b59b6,color:#fff
    style L fill:#f39c12,color:#fff
    style P fill:#2ecc71,color:#fff
    style C fill:#1abc9c,color:#fff
```

---

## 2. HTML 파싱과 DOM 생성

브라우저가 HTML을 받으면 바이트 → 문자 → 토큰 → 노드 → DOM의 과정을 거칩니다.

```mermaid
flowchart LR
    A["바이트<br/>0x3C 0x68 0x74..."] --> B["문자<br/>&lt;html&gt;&lt;body&gt;..."]
    B --> C["토큰<br/>StartTag: html<br/>StartTag: body"]
    C --> D["노드<br/>HTMLElement<br/>BodyElement"]
    D --> E["DOM 트리"]

    style A fill:#95a5a6,color:#fff
    style E fill:#e74c3c,color:#fff
```

### DOM 트리 구조

```html
<!DOCTYPE html>
<html>
  <head>
    <title>예제</title>
    <link rel="stylesheet" href="style.css">
  </head>
  <body>
    <h1>제목</h1>
    <p>단락</p>
  </body>
</html>
```

```mermaid
graph TD
    DOC[Document] --> HTML[html]
    HTML --> HEAD[head]
    HTML --> BODY[body]
    HEAD --> TITLE[title: 예제]
    HEAD --> LINK[link: style.css]
    BODY --> H1[h1: 제목]
    BODY --> P[p: 단락]

    style DOC fill:#e74c3c,color:#fff
    style HTML fill:#e74c3c,color:#fff
```

### 파싱 블로킹

```mermaid
sequenceDiagram
    participant PARSER as HTML 파서
    participant SCRIPT as script 태그
    participant NETWORK as 네트워크

    PARSER->>PARSER: HTML 파싱 진행
    PARSER->>SCRIPT: script 태그 발견!
    PARSER->>NETWORK: JS 파일 요청
    Note over PARSER: 파싱 일시 중단! (파서 블로킹)
    NETWORK-->>PARSER: JS 파일 수신
    PARSER->>PARSER: JS 실행 완료
    PARSER->>PARSER: HTML 파싱 재개
```

**해결책:**
```html
<!-- async: 다운로드 완료 즉시 실행 (파싱 중단) -->
<script async src="analytics.js"></script>

<!-- defer: 파싱 완료 후 실행 (권장) -->
<script defer src="app.js"></script>

<!-- body 끝에 배치: 파싱 완료 후 로드 -->
<body>
  ...
  <script src="app.js"></script>
</body>
```

---

## 3. CSS 파싱과 CSSOM 생성

CSS도 DOM과 유사한 과정으로 파싱되어 CSSOM(CSS Object Model) 트리를 만듭니다.

```css
body { font-size: 16px; }
p { color: blue; }
span { display: none; }
```

```mermaid
graph TD
    CSSOM[CSSOM Root] --> BODY_CSS["body<br/>font-size: 16px"]
    CSSOM --> P_CSS["p<br/>color: blue<br/>(font-size: 16px 상속)"]
    CSSOM --> SPAN_CSS["span<br/>display: none<br/>(color: blue, font-size: 16px 상속)"]

    style CSSOM fill:#3498db,color:#fff
```

**중요**: CSS는 **렌더 블로킹 리소스**입니다. CSSOM이 완성되기 전까지 렌더 트리를 만들 수 없습니다.

---

## 4. 렌더 트리 (Render Tree) 생성

DOM + CSSOM을 결합하여 실제로 화면에 그려질 요소들의 트리를 만듭니다.

```mermaid
flowchart TD
    subgraph "DOM"
        D_HTML[html]
        D_BODY[body]
        D_H1[h1: 안녕]
        D_P[p: 단락]
        D_SPAN["span: 숨김<br/>(display: none)"]
    end

    subgraph "CSSOM"
        C_BODY["body: font-size 16px"]
        C_H1["h1: color red"]
        C_SPAN["span: display none"]
    end

    subgraph "렌더 트리"
        R_ROOT[Render Root]
        R_BODY[body]
        R_H1["h1: 안녕<br/>color: red"]
        R_P["p: 단락"]
        NOTE["span은 제외!<br/>(display: none)"]
    end

    D_HTML -->|결합| R_ROOT
    D_BODY -->|결합| R_BODY
    D_H1 -->|결합| R_H1
    D_P -->|결합| R_P
    D_SPAN -->|display:none| NOTE

    style NOTE fill:#e74c3c,color:#fff
    style R_ROOT fill:#9b59b6,color:#fff
```

### 렌더 트리에서 제외되는 요소

- `display: none` 설정된 요소
- `<head>`, `<script>`, `<meta>` 등 비시각적 요소
- HTML 주석

**주의**: `visibility: hidden`은 공간은 차지하지만 보이지 않음 → 렌더 트리에 포함됨

---

## 5. 레이아웃 (Layout / Reflow)

렌더 트리의 각 노드가 화면의 **어느 위치에, 얼마나 크게** 그려질지 계산합니다.

```mermaid
graph TD
    A[렌더 트리] --> B[뷰포트 크기 확인]
    B --> C[박스 모델 계산]
    C --> D[각 요소의 크기/위치 결정]
    D --> E["레이아웃 완료<br/>(픽셀 단위)"]

    style E fill:#f39c12,color:#fff
```

```javascript
// 레이아웃을 트리거하는 속성들
element.style.width = '100px';      // 리플로우
element.style.height = '200px';     // 리플로우
element.style.margin = '10px';      // 리플로우
element.style.padding = '5px';      // 리플로우
element.style.display = 'block';    // 리플로우

// 레이아웃 정보 읽기도 리플로우 발생
const width = element.offsetWidth;  // 리플로우!
const height = element.offsetHeight; // 리플로우!
```

---

## 6. 페인트 (Paint)

레이아웃 후 각 요소를 실제 픽셀로 그립니다. 여러 레이어로 나뉘어 그려집니다.

```mermaid
flowchart LR
    A[레이아웃 완료] --> B[페인트 순서 결정]
    B --> C[배경색 그리기]
    C --> D[테두리 그리기]
    D --> E[텍스트 그리기]
    E --> F[이미지 그리기]

    style F fill:#2ecc71,color:#fff
```

### 리페인트 vs 리플로우

| 작업 | 비용 | 트리거 조건 |
|------|------|------------|
| 리플로우 (Reflow) | 매우 높음 | 크기, 위치, 레이아웃 변경 |
| 리페인트 (Repaint) | 중간 | 색상, 배경, 그림자 변경 |
| 컴포지팅 | 낮음 | transform, opacity 변경 |

```javascript
// 비용 순서: 리플로우 > 리페인트 > 컴포지팅

// 비싼 작업 (리플로우)
element.style.width = '200px';
element.style.left = '10px';

// 중간 작업 (리페인트)
element.style.backgroundColor = 'red';
element.style.color = 'blue';

// 저렴한 작업 (컴포지팅만)
element.style.transform = 'translateX(10px)'; // GPU 가속!
element.style.opacity = '0.5'; // GPU 가속!
```

---

## 7. 컴포지팅 (Compositing)

여러 레이어를 합성하여 최종 화면을 만듭니다. GPU가 담당합니다.

```mermaid
flowchart TD
    subgraph "레이어 구성"
        L1["레이어 1: 배경"]
        L2["레이어 2: 텍스트"]
        L3["레이어 3: 이미지"]
        L4["레이어 4: 오버레이"]
    end

    L1 --> COMP[컴포지터 스레드]
    L2 --> COMP
    L3 --> COMP
    L4 --> COMP
    COMP --> SCREEN["최종 화면"]

    style COMP fill:#1abc9c,color:#fff
    style SCREEN fill:#2ecc71,color:#fff
```

### 레이어 생성 조건

```css
/* 새 레이어를 생성하는 CSS 속성들 */
.new-layer {
  transform: translateZ(0);     /* GPU 레이어 */
  will-change: transform;        /* 미리 레이어 생성 힌트 */
  position: fixed;               /* 고정 레이어 */
  opacity: 0.5 + animation;      /* 애니메이션 시 레이어 */
}
```

---

## 8. Reflow와 Repaint 최적화

### 강제 동기 레이아웃 (Layout Thrashing)

```javascript
// 나쁜 코드 - 레이아웃 쓰래싱
const elements = document.querySelectorAll('.item');

for (const el of elements) {
  const width = el.offsetWidth; // 읽기 → 리플로우 발생
  el.style.width = `${width * 2}px`; // 쓰기 → 레이아웃 무효화
  // 다음 반복의 읽기가 다시 리플로우 발생...
}
```

```mermaid
sequenceDiagram
    participant JS as JavaScript
    participant LAYOUT as 레이아웃 엔진

    loop 각 요소마다
        JS->>LAYOUT: offsetWidth 읽기 (리플로우 강제)
        LAYOUT-->>JS: 값 반환
        JS->>LAYOUT: style.width 쓰기 (레이아웃 무효화)
    end

    Note over LAYOUT: 100개 요소 = 100번 리플로우!
```

```javascript
// 좋은 코드 - 읽기/쓰기 분리
const elements = document.querySelectorAll('.item');

// 1단계: 모든 값 읽기
const widths = [...elements].map(el => el.offsetWidth);

// 2단계: 모든 값 쓰기
elements.forEach((el, i) => {
  el.style.width = `${widths[i] * 2}px`;
});
```

### requestAnimationFrame 활용

```javascript
// 레이아웃 쓰래싱 완전 방지
function updateElements() {
  requestAnimationFrame(() => {
    // 렌더링 직전에 한 번에 처리
    const widths = [...elements].map(el => el.offsetWidth);
    elements.forEach((el, i) => {
      el.style.width = `${widths[i] * 2}px`;
    });
  });
}
```

---

## 9. Critical Rendering Path 최적화

### 렌더 블로킹 리소스 제거

```html
<!-- 나쁜 예: 렌더 블로킹 CSS -->
<head>
  <link rel="stylesheet" href="all-styles.css"> <!-- 모든 CSS 로드 대기 -->
</head>

<!-- 좋은 예: 중요한 CSS만 인라인 -->
<head>
  <style>
    /* 위에 보이는 영역(above the fold)의 핵심 스타일만 */
    body { margin: 0; font-family: sans-serif; }
    .header { background: #333; color: white; }
  </style>
  <!-- 나머지 CSS는 비동기 로드 -->
  <link rel="preload" href="styles.css" as="style" onload="this.rel='stylesheet'">
</head>
```

### 리소스 힌트

```html
<!-- preconnect: 도메인에 미리 연결 -->
<link rel="preconnect" href="https://fonts.googleapis.com">

<!-- preload: 곧 필요한 리소스 미리 로드 -->
<link rel="preload" href="hero-image.jpg" as="image">
<link rel="preload" href="font.woff2" as="font" crossorigin>

<!-- prefetch: 다음 페이지에 필요한 리소스 미리 가져오기 -->
<link rel="prefetch" href="/next-page.html">
```

---

## 10. 성능 측정 - 브라우저 타이밍 API

```javascript
// Navigation Timing API
const timing = performance.timing;

// 주요 지표 계산
const pageLoad = timing.loadEventEnd - timing.navigationStart;
const domReady = timing.domContentLoadedEventEnd - timing.navigationStart;
const firstByte = timing.responseStart - timing.navigationStart;
const htmlParse = timing.domInteractive - timing.responseStart;

console.log({
  'Page Load': pageLoad + 'ms',
  'DOM Ready': domReady + 'ms',
  'First Byte (TTFB)': firstByte + 'ms',
  'HTML Parse': htmlParse + 'ms'
});
```

```mermaid
gantt
    title 브라우저 렌더링 타임라인
    dateFormat X
    axisFormat %Lms

    section 네트워크
    DNS 조회 :0, 50
    TCP 연결 :50, 100
    TTFB (첫 바이트) :100, 200

    section HTML 파싱
    HTML 수신 및 파싱 :200, 400
    CSS 다운로드 :250, 350
    JS 다운로드/실행 :300, 450

    section 렌더링
    DOM 생성 :200, 420
    CSSOM 생성 :350, 420
    렌더 트리 :420, 450
    레이아웃 :450, 480
    페인트 :480, 520
    컴포지팅 :520, 540
```

---

## 11. Core Web Vitals

구글이 정의한 웹 성능 핵심 지표입니다.

```mermaid
graph TD
    CWV["Core Web Vitals"] --> LCP["LCP<br/>Largest Contentful Paint<br/>주요 콘텐츠 로드 시간<br/>목표: 2.5초 이하"]
    CWV --> INP["INP<br/>Interaction to Next Paint<br/>인터랙션 응답 속도<br/>목표: 200ms 이하"]
    CWV --> CLS["CLS<br/>Cumulative Layout Shift<br/>레이아웃 안정성<br/>목표: 0.1 이하"]

    style LCP fill:#2ecc71,color:#fff
    style INP fill:#3498db,color:#fff
    style CLS fill:#e74c3c,color:#fff
```

```javascript
// Web Vitals 측정
import { getLCP, getINP, getCLS } from 'web-vitals';

getLCP((metric) => {
  console.log('LCP:', metric.value, 'ms');
  // 2500ms 이하: Good, 4000ms 이하: Needs Improvement, 그 이상: Poor
});

getCLS((metric) => {
  console.log('CLS:', metric.value);
  // 0.1 이하: Good, 0.25 이하: Needs Improvement, 그 이상: Poor
});
```

---

## 12. 극한 시나리오 - 무한 리플로우 루프

```javascript
// 이런 코드는 브라우저를 멈춥니다
function infiniteReflow() {
  // ResizeObserver 콜백에서 크기를 변경하면
  // 다시 Resize 이벤트를 트리거 → 무한 루프!
  const observer = new ResizeObserver((entries) => {
    for (const entry of entries) {
      // 이 안에서 크기를 변경하면 안 됨
      entry.target.style.width = entry.contentRect.width + 'px';
    }
  });
  observer.observe(element);
}

// 올바른 방법
const observer = new ResizeObserver((entries) => {
  requestAnimationFrame(() => {
    for (const entry of entries) {
      // rAF 안에서 변경 → 다음 프레임에 처리
      entry.target.style.width = entry.contentRect.width + 'px';
    }
  });
});
```

---

## 13. 최적화 체크리스트

```mermaid
mindmap
  root((렌더링 최적화))
    CSS 최적화
      중요 CSS 인라인
      미디어 쿼리 분리 로드
      CSS 선택자 단순화
    JavaScript 최적화
      defer/async 속성
      코드 스플리팅
      Tree Shaking
    이미지 최적화
      WebP/AVIF 형식
      lazy loading
      적절한 사이즈
    레이아웃 최적화
      읽기/쓰기 일괄처리
      transform 사용
      will-change 힌트
    측정 도구
      Chrome DevTools
      Lighthouse
      WebPageTest
```

### 실전 체크리스트

```javascript
// 1. CSS 속성 선택
// 나쁨: 리플로우 유발
element.style.left = '10px';
// 좋음: 컴포지팅만
element.style.transform = 'translateX(10px)';

// 2. 복수 스타일 변경
// 나쁨: 여러 번 리플로우
element.style.width = '100px';
element.style.height = '200px';
element.style.margin = '10px';

// 좋음: 클래스로 한 번에 변경
element.classList.add('resized');

// 3. 문서 조각 사용
// 나쁨: 매번 DOM 업데이트
for (const item of items) {
  document.body.appendChild(createItem(item)); // N번 리플로우
}

// 좋음: DocumentFragment 사용
const fragment = document.createDocumentFragment();
for (const item of items) {
  fragment.appendChild(createItem(item));
}
document.body.appendChild(fragment); // 1번 리플로우
```

브라우저 렌더링을 이해하면 성능 문제의 근본 원인을 파악하고 효과적으로 해결할 수 있습니다. 모든 최적화의 핵심은 **불필요한 레이아웃과 페인트를 줄이는 것**입니다.
