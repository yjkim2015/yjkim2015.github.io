---
title: "브라우저 렌더링"
categories: FRONTEND
tags: [브라우저 렌더링, DOM, CSSOM, Reflow, Repaint, Critical Rendering Path, 이벤트 버블링]
toc: true
toc_sticky: true
toc_label: 목차
---

## 비유로 시작하기

웹 페이지가 화면에 나타나는 과정을 집 짓기에 비유할 수 있습니다. HTML은 **건물의 뼈대(DOM)**를 만들고, CSS는 **인테리어와 색칠(CSSOM)**을 합니다. 두 정보를 합쳐 **실제로 보이는 모습(렌더 트리)**을 만들고, **각 요소의 위치와 크기를 계산(Layout/Reflow)**한 다음, **색을 칠합니다(Paint/Repaint)**. 마지막으로 **레이어를 합성(Composite)**하면 화면이 완성됩니다.

---

## 브라우저 렌더링 과정

<div class="mermaid">
graph LR
    HTML[HTML 파싱] --> DOM[DOM 트리]
    CSS[CSS 파싱] --> CSSOM[CSSOM 트리]
    DOM --> RT[렌더 트리<br>Render Tree]
    CSSOM --> RT
    RT --> LAYOUT[Layout<br>Reflow<br>위치/크기 계산]
    LAYOUT --> PAINT[Paint<br>Repaint<br>픽셀 채우기]
    PAINT --> COMPOSITE[Composite<br>레이어 합성]
    COMPOSITE --> SCREEN[화면 출력]
</div>

---

## DOM (Document Object Model)

HTML을 파싱하여 생성하는 **트리 구조의 객체 모델**입니다.

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

### HTML 파싱 중 JavaScript

```html
<!-- render-blocking: JS 실행 전까지 파싱 중단 -->
<script src="app.js"></script>

<!-- async: 다운로드는 병렬, 다운로드 완료 즉시 실행 (순서 보장 X) -->
<script async src="analytics.js"></script>

<!-- defer: 다운로드는 병렬, HTML 파싱 완료 후 실행 (순서 보장 O) -->
<script defer src="app.js"></script>
```

---

## CSSOM (CSS Object Model)

CSS를 파싱하여 생성하는 트리입니다. **render-blocking 리소스**입니다. CSSOM이 완성되기 전까지는 렌더링이 시작되지 않습니다.

```css
body { font-size: 16px; }
div { color: blue; }
div p { font-size: 14px; }
```

```
CSSOM 트리:
body (font-size: 16px)
└── div (color: blue)
    └── p (font-size: 14px, color: blue [상속])
```

**CSS 선택자 성능**: 오른쪽에서 왼쪽으로 평가합니다.

```css
/* 느림: body > div > p > span 순서로 역방향 탐색 */
body div p span { color: red; }

/* 빠름: 직접 클래스 지정 */
.highlight-text { color: red; }
```

---

## 렌더 트리 (Render Tree)

DOM + CSSOM을 합쳐 **실제로 화면에 그려질 노드만** 포함합니다.

- `display: none` → 렌더 트리에 포함 안 됨
- `visibility: hidden` → 렌더 트리에 포함됨 (공간 차지)
- `<head>`, `<script>` → 포함 안 됨

---

## Reflow (Layout)

렌더 트리의 각 노드가 **화면의 어느 위치에, 얼마만한 크기로** 배치될지 계산합니다.

### Reflow를 발생시키는 속성

```javascript
// 이 속성들을 읽거나 변경하면 Reflow 발생
element.offsetWidth    // 읽기만 해도 최신 값 계산 필요
element.offsetHeight
element.clientWidth
element.getBoundingClientRect()

element.style.width = '100px';    // width 변경
element.style.padding = '10px';  // padding 변경
element.style.margin = '10px';   // margin 변경
element.style.fontSize = '20px'; // fontSize 변경
```

Reflow는 비용이 큽니다. 부모 요소 변경이 자식 전체에 영향을 줄 수 있습니다.

---

## Repaint (Paint)

레이아웃 변경 없이 **색상, 배경, 테두리** 등 시각적 스타일만 변경할 때 발생합니다.

### Repaint만 발생시키는 속성

```javascript
element.style.color = 'red';
element.style.backgroundColor = 'blue';
element.style.borderColor = 'green';
element.style.visibility = 'hidden';  // 레이아웃 변경 없음
```

Reflow < Repaint 성능 비용이지만, 둘 다 최소화하는 것이 좋습니다.

---

## GPU 합성 (Composite)

특정 CSS 속성은 CPU가 아닌 **GPU에서 처리**됩니다. Reflow/Repaint 없이 가장 빠릅니다.

```css
/* GPU 가속 속성 (Composite Only) */
transform: translate(10px, 10px);  /* 이동 */
transform: rotate(45deg);          /* 회전 */
transform: scale(1.5);             /* 확대 */
opacity: 0.5;                      /* 투명도 */

/* GPU 레이어 강제 생성 (절약해서 사용) */
will-change: transform;
transform: translateZ(0);  /* 핵 (사용 자제) */
```

### 애니메이션 최적화

```css
/* 나쁜 예: left/top 변경 → Reflow 발생 */
.move-bad {
    left: 100px;  /* Reflow! */
    transition: left 0.3s;
}

/* 좋은 예: transform 사용 → GPU Composite만 */
.move-good {
    transform: translateX(100px);  /* GPU만 사용 */
    transition: transform 0.3s;
}
```

---

## Critical Rendering Path 최적화

첫 화면 렌더링을 빠르게 하는 전략입니다.

### 1. render-blocking 리소스 최소화

```html
<!-- CSS: media 쿼리로 불필요한 블로킹 제거 -->
<link rel="stylesheet" href="main.css">
<link rel="stylesheet" href="print.css" media="print">  <!-- 인쇄 시만 블로킹 -->

<!-- JS: defer/async 사용 -->
<script defer src="app.js"></script>
```

### 2. CSS 인라인화 (Above-the-fold)

```html
<head>
    <!-- 첫 화면에 필요한 핵심 CSS만 인라인 -->
    <style>
        .hero { background: #333; color: white; padding: 20px; }
        .nav { display: flex; }
    </style>
    <!-- 나머지 CSS는 비동기 로드 -->
    <link rel="preload" href="full.css" as="style" onload="this.rel='stylesheet'">
</head>
```

### 3. Reflow 배치 처리

```javascript
// 나쁜 예: 읽기-쓰기 혼재 → 매번 Reflow
const el1 = document.getElementById('el1');
const el2 = document.getElementById('el2');

el1.style.width = el2.offsetWidth + 'px';  // 읽기 → Reflow
el2.style.width = el1.offsetWidth + 'px';  // 읽기 → Reflow

// 좋은 예: 읽기 먼저, 쓰기 나중에
const width1 = el1.offsetWidth;  // 읽기 (Reflow 1번)
const width2 = el2.offsetWidth;  // 읽기 (캐시 사용)
el1.style.width = width2 + 'px';  // 쓰기
el2.style.width = width1 + 'px';  // 쓰기

// 더 나은 예: requestAnimationFrame 사용
requestAnimationFrame(() => {
    el1.style.width = width2 + 'px';
    el2.style.width = width1 + 'px';
});
```

### 4. DocumentFragment로 일괄 DOM 조작

```javascript
// 나쁜 예: 루프마다 Reflow
const list = document.getElementById('list');
for (let i = 0; i < 1000; i++) {
    const li = document.createElement('li');
    li.textContent = `Item ${i}`;
    list.appendChild(li);  // 매번 Reflow!
}

// 좋은 예: Fragment에 모아서 한 번에 추가
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

<div class="mermaid">
graph TD
    WINDOW[window]
    DOC[document]
    BODY[body]
    DIV[div]
    BTN[button ← 클릭!]

    subgraph 캡처링 Phase 1
        WINDOW -->|1| DOC -->|2| BODY -->|3| DIV -->|4| BTN
    end
    subgraph 버블링 Phase 3
        BTN -->|5| DIV -->|6| BODY -->|7| DOC -->|8| WINDOW
    end
</div>

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

// 이벤트 위임 (Event Delegation)
// 자식 요소마다 리스너 추가 대신 부모에 하나만 추가
document.getElementById('todoList').addEventListener('click', (e) => {
    if (e.target.classList.contains('delete-btn')) {
        const item = e.target.closest('.todo-item');
        item.remove();
    }
    if (e.target.classList.contains('edit-btn')) {
        // 편집 처리
    }
});
```

---

## 극한 시나리오

### 시나리오: 리스트 1만 개 항목의 스크롤 성능 저하

**문제**: 10,000개 DOM 노드 → 렌더 트리 거대화 → 스크롤 시 Reflow 폭발

**해결: 가상 스크롤 (Virtual Scrolling)**

```javascript
class VirtualList {
    constructor(container, items, itemHeight = 50) {
        this.container = container;
        this.items = items;
        this.itemHeight = itemHeight;
        this.visibleCount = Math.ceil(container.clientHeight / itemHeight) + 2;

        this.render();
        container.addEventListener('scroll', () => this.render());
    }

    render() {
        const scrollTop = this.container.scrollTop;
        const startIndex = Math.floor(scrollTop / this.itemHeight);
        const endIndex = Math.min(startIndex + this.visibleCount, this.items.length);

        // 전체 높이 유지 (스크롤바 위치 정확하게)
        this.container.style.paddingTop = `${startIndex * this.itemHeight}px`;
        this.container.style.paddingBottom =
            `${(this.items.length - endIndex) * this.itemHeight}px`;

        // 보이는 항목만 렌더링
        this.container.innerHTML = this.items
            .slice(startIndex, endIndex)
            .map(item => `<div style="height:${this.itemHeight}px">${item}</div>`)
            .join('');
    }
}
// DOM 노드 수: 10,000개 → 20여 개로 감소
```
