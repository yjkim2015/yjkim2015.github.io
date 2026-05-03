---
title: "브라우저 렌더링"
categories: FRONTEND
tags: [브라우저 렌더링, DOM, CSSOM, Reflow, Repaint, Critical Rendering Path, 이벤트 버블링]
toc: true
toc_sticky: true
toc_label: 목차
---

> **한 줄 요약**: 브라우저는 HTML/CSS/JS를 받아 DOM→CSSOM→렌더트리→Layout→Paint→Composite 6단계를 거쳐 화면에 픽셀을 그린다.

## 비유로 이해하기

웹 페이지가 화면에 나타나는 과정을 **건물 신축 공사**에 비유할 수 있습니다.

1. **설계도 받기** (HTML 수신): 건축 설계도(HTML)를 받습니다.
2. **뼈대 세우기** (DOM 생성): 철근과 콘크리트로 구조물(DOM 트리)을 올립니다.
3. **인테리어 설계** (CSSOM 생성): 색상·크기·배치 계획(CSSOM)을 수립합니다.
4. **배치도 작성** (렌더 트리): 실제로 보이는 요소만 선별한 도면(렌더 트리)을 만듭니다.
5. **면적 계산** (Layout/Reflow): 각 방의 면적·위치를 정확히 계산합니다.
6. **페인트 칠하기** (Paint/Repaint): 벽을 칠하고 마감재를 붙입니다.
7. **준공 검사** (Composite): 레이어별 결과를 합쳐 최종 건물(화면)을 완성합니다.

공사 중 벽 하나를 다시 칠하려면 (Repaint) 그 방만 작업하면 됩니다. 하지만 벽을 헐고 새로 세우면 (Reflow) 인접 구조물 전체에 영향이 미칩니다. **이것이 Reflow가 Repaint보다 훨씬 비싼 이유**입니다.

---

## 브라우저 렌더링 전체 파이프라인

```mermaid
flowchart TD
    subgraph "1️⃣ 파싱 단계"
        HTML["HTML 바이트 수신"] --> DOM["DOM 트리 생성"]
        CSS["CSS 바이트 수신"] --> CSSOM["CSSOM 트리 생성"]
        JS["JavaScript 파일"] --> EXEC["JS 엔진 실행\n(DOM/CSSOM 변경 가능)"]
    end

    subgraph "2️⃣ 렌더 트리 단계"
        DOM --> RT["렌더 트리 생성\n(보이는 노드만)"]
        CSSOM --> RT
        EXEC -->|DOM/CSSOM 수정| RT
    end

    subgraph "3️⃣ 레이아웃 단계"
        RT --> LAYOUT["Layout / Reflow\n위치·크기 계산"]
    end

    subgraph "4️⃣ 페인트 단계"
        LAYOUT --> PAINT["Paint / Repaint\n픽셀 채우기"]
    end

    subgraph "5️⃣ 합성 단계"
        PAINT --> COMPOSITE["Composite\n레이어 합성 (GPU)"]
        COMPOSITE --> SCREEN["🖥️ 화면 출력"]
    end

    style DOM fill:#e74c3c,color:#fff
    style CSSOM fill:#3498db,color:#fff
    style RT fill:#9b59b6,color:#fff
    style LAYOUT fill:#f39c12,color:#fff
    style PAINT fill:#2ecc71,color:#fff
    style COMPOSITE fill:#1abc9c,color:#fff
```

---

## DOM (Document Object Model)

### DOM이란?

HTML을 파싱하여 생성하는 **트리 구조의 객체 모델**입니다. 브라우저가 HTML 바이트를 읽어 문자 → 토큰 → 노드 → DOM 트리 순서로 변환합니다.

DOM은 단순한 HTML 파싱 결과물이 아닙니다. 자바스크립트가 `document.getElementById`, `querySelector` 등을 통해 접근·조작할 수 있는 **살아있는 인터페이스**입니다. DOM 노드 하나하나가 객체이며, 이 객체들이 트리 형태로 연결되어 있습니다.

DOM은 **동적으로 변경 가능**합니다. 자바스크립트로 노드를 추가·삭제·수정하면 브라우저는 렌더 트리를 다시 계산합니다. 이것이 React, Vue 같은 프레임워크가 Virtual DOM을 도입한 이유입니다. 실제 DOM 조작을 최소화하기 위해서입니다.

#### HTML → DOM 변환 과정

```mermaid
flowchart LR
    A["바이트\n3C 68 74 6D 6C 3E"] --> B["문자\n&lt;html&gt;&lt;body&gt;..."]
    B --> C["토큰\nStartTag: html\nStartTag: body"]
    C --> D["노드\nHTMLElement\nBodyElement"]
    D --> E["🌳 DOM 트리"]

    style A fill:#95a5a6,color:#fff
    style E fill:#e74c3c,color:#fff
```

```html
<!DOCTYPE html>
<html>
  <head>
    <title>My Page</title>
  </head>
  <body>
    <div id="container">
      <h1>Hello</h1>
      <p class="text">World</p>
    </div>
  </body>
</html>
```

```
DOM 트리:
document
└── html
    ├── head
    │   └── title "My Page"
    └── body
        └── div#container
            ├── h1 "Hello"
            └── p.text "World"
```

### HTML 파싱 중 JavaScript 만나면?

자바스크립트는 **파서 블로킹 리소스**입니다. `<script>` 태그를 만나면 HTML 파싱을 멈추고 JS를 다운로드·실행합니다. JS가 DOM을 변경할 수 있기 때문입니다.

```mermaid
sequenceDiagram
    participant PARSER as HTML 파서
    participant NETWORK as 네트워크
    participant JS as JS 엔진

    PARSER->>PARSER: 1️⃣ HTML 파싱 진행
    PARSER->>NETWORK: 2️⃣ script 태그 발견 → JS 다운로드 요청
    Note over PARSER: ⛔ 파싱 일시 중단!
    NETWORK-->>JS: 3️⃣ JS 파일 수신
    JS->>JS: 4️⃣ JS 실행 완료
    PARSER->>PARSER: 5️⃣ HTML 파싱 재개
```

```html
<!-- ❌ render-blocking: JS 실행 전까지 파싱 중단 -->
<script src="app.js"></script>

<!-- ✅ async: 다운로드는 병렬, 완료 즉시 실행 (순서 보장 X) -->
<script async src="analytics.js"></script>

<!-- ✅ defer: 다운로드는 병렬, HTML 파싱 완료 후 순서대로 실행 -->
<script defer src="app.js"></script>
```

#### 왜 이게 중요한가?

`<script>` 태그를 `<head>` 에 넣으면 HTML 파싱이 지연되어 흰 화면이 오래 지속됩니다. `defer`를 쓰면 병렬 다운로드 + 파싱 완료 후 실행이라 최적입니다. 외부 통계 스크립트처럼 실행 순서가 중요하지 않다면 `async`를 씁니다.

#### 실무에서 자주 하는 실수

```html
<!-- ❌ head에 defer/async 없이 배치 → 흰 화면 지연 -->
<head>
  <script src="heavy-library.js"></script>
</head>

<!-- ✅ defer 사용 또는 body 끝에 배치 -->
<head>
  <script defer src="app.js"></script>
</head>
```

#### 면접에서 이렇게 답하세요

> "`async`와 `defer`의 차이는 실행 시점입니다. `async`는 다운로드가 완료되는 즉시 실행하므로 DOM 파싱이 끝나기 전에 실행될 수 있고 순서가 보장되지 않습니다. `defer`는 DOM 파싱이 완전히 끝난 뒤 선언 순서대로 실행됩니다. 일반 앱 스크립트엔 `defer`, 독립적인 분석 스크립트엔 `async`가 적합합니다."

---

## CSSOM (CSS Object Model)

CSS를 파싱하여 생성하는 트리입니다. CSSOM은 **렌더 블로킹 리소스**입니다. CSSOM이 완성되기 전까지는 렌더 트리를 만들 수 없고, 렌더링이 시작되지 않습니다.

CSS 파싱은 HTML 파싱과 **병렬로 진행**됩니다. 그러나 렌더 트리 생성은 DOM과 CSSOM이 모두 준비된 후에야 시작됩니다.

```css
body { font-size: 16px; }
div  { color: blue; }
div p { font-size: 14px; }
```

```
CSSOM 트리:
body (font-size: 16px)
└── div (color: blue)
    └── p (font-size: 14px, color: blue [상속됨])
```

### CSS 선택자 성능: 오른쪽에서 왼쪽으로 평가

브라우저는 CSS 선택자를 **오른쪽에서 왼쪽** 방향으로 평가합니다. `body div p span`을 만나면 먼저 페이지의 모든 `span`을 찾고, 그 부모가 `p`인지, 또 그 부모가 `div`인지 역방향으로 탐색합니다.

```css
/* ❌ 느림: 모든 span을 찾아 역방향 체인 탐색 */
body div p span { color: red; }

/* ✅ 빠름: 클래스 직접 지정 */
.highlight-text { color: red; }
```

---

## 렌더 트리 (Render Tree)

DOM + CSSOM을 합쳐 **실제로 화면에 그려질 노드만** 포함한 트리입니다. 비시각적 노드는 제외됩니다.

```mermaid
flowchart TD
    subgraph "DOM 트리"
        DH[html]
        DB[body]
        DH1[h1: 안녕]
        DP[p: 단락]
        DS["span (display:none)"]
        DHEAD["head, script, meta"]
    end

    subgraph "렌더 트리 (보이는 것만)"
        RR[렌더 루트]
        RB[body]
        RH1["h1: 안녕"]
        RP["p: 단락"]
        EXCL1["❌ span 제외\n(display:none)"]
        EXCL2["❌ head/script/meta 제외"]
    end

    DH -->|포함| RR
    DB -->|포함| RB
    DH1 -->|포함| RH1
    DP -->|포함| RP
    DS -->|제외| EXCL1
    DHEAD -->|제외| EXCL2

    style EXCL1 fill:#e74c3c,color:#fff
    style EXCL2 fill:#e74c3c,color:#fff
```

| 요소/속성 | 렌더 트리 포함 여부 | 공간 차지 |
|---|---|---|
| `display: none` | ❌ 제외 | ❌ 없음 |
| `visibility: hidden` | ✅ 포함 | ✅ 있음 |
| `opacity: 0` | ✅ 포함 | ✅ 있음 |
| `<head>`, `<script>`, `<meta>` | ❌ 제외 | ❌ 없음 |
| HTML 주석 | ❌ 제외 | ❌ 없음 |

### 왜 이게 중요한가?

`display: none`은 DOM에는 있지만 렌더 트리에서 완전히 제거됩니다. 따라서 숨겨진 요소를 조작해도 Reflow가 발생하지 않습니다. 반면 `visibility: hidden`은 렌더 트리에 포함되어 공간을 차지하므로, 이 요소의 크기를 바꾸면 Reflow가 발생합니다.

---

## Reflow (Layout)

렌더 트리의 각 노드가 **화면의 어느 위치에, 얼마만한 크기로** 배치될지 픽셀 단위로 계산하는 단계입니다.

Reflow는 **계산 비용이 가장 큽니다**. 특정 요소의 크기가 바뀌면 부모·형제·자식 노드 모두에 영향을 줄 수 있기 때문입니다. 예를 들어 `<table>` 의 셀 하나가 바뀌면 테이블 전체가 다시 계산됩니다.

```mermaid
flowchart LR
    A["렌더 트리 노드"] --> B["뷰포트 크기 참조"]
    B --> C["박스 모델 계산\n(margin, padding, border, content)"]
    C --> D["위치 결정\n(절대/상대 좌표)"]
    D --> E["자식 노드 재귀 계산"]
    E --> F["✅ 레이아웃 완료\n(픽셀 단위 좌표)"]

    style F fill:#f39c12,color:#fff
```

### Reflow를 발생시키는 속성

```javascript
// 이 속성들을 읽거나 변경하면 Reflow 발생
// ── 읽기만 해도 브라우저가 최신 레이아웃 값 계산 강제 ──
const w  = element.offsetWidth;     // Reflow 강제!
const h  = element.offsetHeight;    // Reflow 강제!
const cw = element.clientWidth;     // Reflow 강제!
const r  = element.getBoundingClientRect(); // Reflow 강제!

// ── 쓰기 ──
element.style.width    = '100px';   // Reflow
element.style.padding  = '10px';    // Reflow
element.style.margin   = '10px';    // Reflow
element.style.fontSize = '20px';    // Reflow
element.style.display  = 'flex';    // Reflow
```

### 실무에서 자주 하는 실수: Layout Thrashing

```javascript
// ❌ 나쁜 예: 읽기-쓰기 교차 → 매 반복마다 Reflow
const el1 = document.getElementById('el1');
const el2 = document.getElementById('el2');

el1.style.width = el2.offsetWidth + 'px';  // 읽기 → Reflow, 쓰기
el2.style.width = el1.offsetWidth + 'px';  // 읽기 → Reflow, 쓰기
// 총 2번 이상 Reflow 발생

// ✅ 좋은 예: 읽기 먼저, 쓰기 나중에
const width1 = el1.offsetWidth;  // 읽기 (Reflow 1번)
const width2 = el2.offsetWidth;  // 읽기 (캐시 사용)
el1.style.width = width2 + 'px'; // 쓰기
el2.style.width = width1 + 'px'; // 쓰기
// 총 1번 Reflow

// ✅ 더 나은 예: requestAnimationFrame으로 다음 프레임에 일괄 처리
requestAnimationFrame(() => {
    el1.style.width = width2 + 'px';
    el2.style.width = width1 + 'px';
});
```

---

## Repaint (Paint)

레이아웃 변경 없이 **색상, 배경, 테두리, 그림자** 등 시각적 스타일만 변경할 때 발생합니다.

Reflow보다 비용이 낮지만, Reflow가 일어나면 항상 Repaint도 따라옵니다.

```javascript
// Repaint만 발생 (Reflow 없음)
element.style.color           = 'red';
element.style.backgroundColor = 'blue';
element.style.borderColor     = 'green';
element.style.boxShadow       = '0 0 5px black';
element.style.visibility      = 'hidden'; // 레이아웃 그대로
```

### 성능 비용 순서

```mermaid
graph LR
    A["💸💸💸 Reflow\n크기·위치 변경"] --> B["💸💸 Repaint\n색상·배경 변경"] --> C["💸 Composite\ntransform·opacity"]

    style A fill:#e74c3c,color:#fff
    style B fill:#f39c12,color:#fff
    style C fill:#2ecc71,color:#fff
```

---

## GPU 합성 (Composite)

특정 CSS 속성은 CPU가 아닌 **GPU에서 처리**됩니다. Reflow도 Repaint도 없이 가장 빠릅니다.

```css
/* ✅ GPU 가속 속성 (Composite Only) */
transform: translate(10px, 10px);  /* 이동 - GPU */
transform: rotate(45deg);          /* 회전 - GPU */
transform: scale(1.5);             /* 확대 - GPU */
opacity:   0.5;                    /* 투명도 - GPU */

/* GPU 레이어 강제 생성 (꼭 필요할 때만) */
will-change: transform;
transform: translateZ(0);          /* 핵 (hack), 남용 금지 */
```

### 애니메이션 최적화 전/후

```css
/* ❌ 나쁜 예: left/top 변경 → Reflow 발생 */
.move-bad {
    left: 100px;       /* Reflow! */
    transition: left 0.3s;
}

/* ✅ 좋은 예: transform 사용 → GPU Composite만 */
.move-good {
    transform: translateX(100px);  /* GPU만 사용 */
    transition: transform 0.3s;
}
```

---

## Critical Rendering Path 최적화

첫 화면 렌더링을 빠르게 하는 전략입니다. 핵심은 **렌더 블로킹 리소스를 최소화**하는 것입니다.

```mermaid
flowchart TD
    subgraph "최적화 전략"
        A["1️⃣ render-blocking CSS 최소화\n(media 쿼리 활용)"]
        B["2️⃣ Critical CSS 인라인\n(above-the-fold)"]
        C["3️⃣ JS defer/async 처리"]
        D["4️⃣ Reflow 배치 처리\n(읽기→쓰기 분리)"]
        E["5️⃣ DocumentFragment 사용\n(DOM 일괄 조작)"]
        F["6️⃣ 리소스 힌트\n(preload, preconnect)"]
    end
    A --> B --> C --> D --> E --> F

    style A fill:#3498db,color:#fff
    style B fill:#2ecc71,color:#fff
    style C fill:#f39c12,color:#fff
```

### 1. render-blocking 리소스 최소화

```html
<!-- ✅ CSS: media 쿼리로 불필요한 블로킹 제거 -->
<link rel="stylesheet" href="main.css">
<link rel="stylesheet" href="print.css" media="print">
<link rel="stylesheet" href="mobile.css" media="(max-width: 768px)">

<!-- ✅ JS: defer/async 사용 -->
<script defer src="app.js"></script>
<script async src="analytics.js"></script>
```

### 2. Critical CSS 인라인화 (Above-the-fold)

첫 화면에 필요한 CSS만 `<style>` 태그로 인라인 삽입하고, 나머지는 비동기 로드합니다.

```html
<head>
    <!-- ✅ 첫 화면에 필요한 핵심 CSS만 인라인 -->
    <style>
        .hero { background: #333; color: white; padding: 20px; }
        .nav  { display: flex; justify-content: space-between; }
    </style>
    <!-- ✅ 나머지 CSS는 비동기 로드 (preload → rel 변경) -->
    <link rel="preload" href="full.css" as="style" onload="this.rel='stylesheet'">
</head>
```

### 3. Reflow 배치 처리

```javascript
// ❌ 나쁜 예: 루프 안에서 읽기-쓰기 교차 → N번 Reflow
const items = document.querySelectorAll('.item');
for (const el of items) {
    const w = el.offsetWidth;    // 읽기 → Reflow 강제
    el.style.width = w * 2 + 'px'; // 쓰기 → 레이아웃 무효화
}

// ✅ 좋은 예: 읽기 먼저, 쓰기 나중에 → 1번 Reflow
const widths = [...items].map(el => el.offsetWidth); // 읽기 일괄
items.forEach((el, i) => { el.style.width = widths[i] * 2 + 'px'; }); // 쓰기 일괄
```

### 4. DocumentFragment로 일괄 DOM 조작

```javascript
// ❌ 나쁜 예: 루프마다 DOM 수정 → 반복 Reflow
const list = document.getElementById('list');
for (let i = 0; i < 1000; i++) {
    const li = document.createElement('li');
    li.textContent = `Item ${i}`;
    list.appendChild(li);  // 매번 Reflow!
}

// ✅ 좋은 예: Fragment에 모아서 한 번에 추가 → 1번 Reflow
const fragment = document.createDocumentFragment();
for (let i = 0; i < 1000; i++) {
    const li = document.createElement('li');
    li.textContent = `Item ${i}`;
    fragment.appendChild(li);
}
list.appendChild(fragment);  // Reflow 1번만
```

---

## 이벤트 버블링과 캡처링

이벤트가 DOM 트리를 통해 전파되는 방식입니다.

```mermaid
sequenceDiagram
    participant WIN as window
    participant DOC as document
    participant BODY as body
    participant DIV as div
    participant BTN as button (클릭!)

    Note over WIN,BTN: 1️⃣ 캡처링 단계 (위 → 아래)
    WIN  ->>  DOC:  이벤트 전파
    DOC  ->>  BODY: 이벤트 전파
    BODY ->>  DIV:  이벤트 전파
    DIV  ->>  BTN:  이벤트 도착 → 타깃 단계

    Note over WIN,BTN: 3️⃣ 버블링 단계 (아래 → 위)
    BTN  ->>  DIV:  버블링
    DIV  ->>  BODY: 버블링
    BODY ->>  DOC:  버블링
    DOC  ->>  WIN:  버블링
```

```javascript
// 버블링 (기본): 자식 → 부모 방향
document.getElementById('parent').addEventListener('click', (e) => {
    console.log('부모 클릭');
});
document.getElementById('child').addEventListener('click', (e) => {
    console.log('자식 클릭');
    e.stopPropagation();  // 버블링 중단
});

// 캡처링: 부모 → 자식 방향 (세 번째 인자 true)
document.getElementById('parent').addEventListener('click', (e) => {
    console.log('부모 (캡처링)');
}, true);

// ✅ 이벤트 위임 (Event Delegation)
// 자식 요소마다 리스너 추가 대신 부모에 하나만 추가 → 메모리 절약
document.getElementById('todoList').addEventListener('click', (e) => {
    if (e.target.classList.contains('delete-btn')) {
        e.target.closest('.todo-item').remove();
    }
});
```

### 왜 이벤트 위임이 중요한가?

리스트 항목이 100개라면 이벤트 리스너도 100개가 필요합니다. 이벤트 위임을 사용하면 부모에 단 1개만 등록하면 됩니다. 동적으로 추가되는 요소에도 자동 적용됩니다.

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

**문제**: 10,000개 DOM 노드 → 렌더 트리 거대화 → 스크롤 시 Reflow 폭발 → 프레임 드랍

**해결: 가상 스크롤 (Virtual Scrolling)**

보이는 영역의 항목만 DOM에 렌더링하고, 스크롤 위치에 따라 동적으로 교체합니다.

```javascript
class VirtualList {
    constructor(container, items, itemHeight = 50) {
        this.container   = container;
        this.items       = items;
        this.itemHeight  = itemHeight;
        this.visibleCount = Math.ceil(container.clientHeight / itemHeight) + 2;

        this.render();
        container.addEventListener('scroll', () => this.render());
    }

    render() {
        const scrollTop  = this.container.scrollTop;
        const startIndex = Math.floor(scrollTop / this.itemHeight);
        const endIndex   = Math.min(startIndex + this.visibleCount, this.items.length);

        // 전체 높이 유지 (스크롤바 위치 정확하게)
        this.container.style.paddingTop    = `${startIndex * this.itemHeight}px`;
        this.container.style.paddingBottom =
            `${(this.items.length - endIndex) * this.itemHeight}px`;

        // 보이는 항목만 렌더링
        this.container.innerHTML = this.items
            .slice(startIndex, endIndex)
            .map(item => `<div style="height:${this.itemHeight}px">${item}</div>`)
            .join('');
    }
}
// DOM 노드 수: 10,000개 → 20여 개로 감소 → 60fps 달성 가능
```

---
</div>
</div>
</details>

## 핵심 포인트 정리

| 단계 | 역할 | 트리거 |
|------|------|--------|
| DOM 생성 | HTML 파싱 → 노드 트리 | HTML 수신 |
| CSSOM 생성 | CSS 파싱 → 스타일 트리 | CSS 수신 |
| 렌더 트리 | DOM + CSSOM → 보이는 노드 | 둘 다 준비 후 |
| Layout (Reflow) | 위치·크기 계산 | 레이아웃 속성 변경 |
| Paint (Repaint) | 픽셀 채우기 | 색상·배경 변경 |
| Composite | GPU 레이어 합성 | transform·opacity 변경 |

- **Reflow > Repaint > Composite** 순서로 성능 비용이 큽니다.
- `transform`과 `opacity`는 GPU로 처리되어 Reflow/Repaint 없이 부드럽게 동작합니다.
- `will-change: transform`은 레이어를 미리 생성하지만 남용하면 VRAM 낭비입니다.
- 읽기(`offsetWidth`)와 쓰기(`style.width`) 를 교차하면 Layout Thrashing이 발생합니다.
- `DocumentFragment`로 DOM 조작을 일괄 처리하면 Reflow 횟수를 줄일 수 있습니다.
