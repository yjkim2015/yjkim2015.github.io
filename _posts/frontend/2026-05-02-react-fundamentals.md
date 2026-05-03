---
title: "React 핵심 원리와 렌더링"
categories:
- FRONTEND
toc: true
toc_sticky: true
toc_label: 목차
---

## "전체를 다시 그리지 않는다"는 아이디어

IKEA 가구를 조립한 뒤 서랍 하나가 마음에 안 든다면, 가구 전체를 분해하고 다시 조립하지 않습니다. 그 서랍만 빼서 교체합니다. 당연한 이야기지만, 웹 개발에서는 오랫동안 이게 당연하지 않았습니다.

전통적인 방식은 데이터가 바뀌면 `innerHTML`로 HTML을 통째로 다시 그렸습니다. 빠르게 깜빡이거나, 입력 중인 텍스트가 날아가거나, 스크롤 위치가 초기화되는 문제가 생겼습니다.

React가 해결한 것이 바로 이것입니다. **"변경된 부분만 정확히 찾아서 최소한으로 업데이트한다."** 이것이 Virtual DOM의 핵심 아이디어입니다.

> 비유: 건물 관리자가 매일 아침 설계도(Virtual DOM)를 들고 건물을 돌면서 실제 건물과 다른 곳을 찾아 그 부분만 고칩니다. 건물 전체를 허물고 다시 짓지 않습니다.

---

## 1번 다이어그램 - React가 해결한 것

```mermaid
graph TD
    subgraph "전통적인 DOM 조작"
        A["상태 변경"] --> B["전체 HTML 재생성"]
        B --> C["DOM 전체 교체"]
        C --> D["느림, 깜빡임, 입력 초기화"]
    end

    subgraph "React 방식"
        E["상태 변경"] --> F["새 Virtual DOM 생성"]
        F --> G["이전 Virtual DOM과 비교 Diffing"]
        G --> H["변경된 부분만 실제 DOM 업데이트"]
        H --> I["빠름, 부드러움, 상태 유지"]
    end

    style D fill:#e74c3c,color:#fff
    style I fill:#2ecc71,color:#fff
```

---

## 2. Virtual DOM — 실제 DOM의 가벼운 복사본

Virtual DOM은 실제 DOM을 자바스크립트 객체로 표현한 것입니다. 실제 DOM을 직접 조작하는 것보다 훨씬 빠릅니다. 왜냐하면 실제 DOM은 레이아웃, 스타일 계산 등 많은 작업을 동반하지만 자바스크립트 객체는 그냥 메모리에 있기 때문입니다.

```javascript
// 실제 DOM (브라우저가 관리)
// <div class="container">
//   <h1>안녕하세요</h1>
//   <p>React 학습 중</p>
// </div>

// Virtual DOM (React가 내부적으로 관리하는 자바스크립트 객체)
const virtualDOM = {
  type: 'div',
  props: { className: 'container' },
  children: [
    { type: 'h1', props: {}, children: ['안녕하세요'] },
    { type: 'p', props: {}, children: ['React 학습 중'] }
  ]
};
```

### JSX는 createElement 호출로 변환됩니다

JSX는 HTML처럼 보이지만 자바스크립트입니다. 브라우저는 JSX를 직접 이해하지 못하므로, 빌드 단계에서 `React.createElement` 호출로 변환됩니다.

```jsx
// 개발자가 작성하는 JSX
const element = (
  <div className="container">
    <h1>안녕하세요</h1>
  </div>
);

// 빌드 후 실제로 실행되는 코드 (React 17 이전)
const element = React.createElement(
  'div',
  { className: 'container' },
  React.createElement('h1', null, '안녕하세요')
);
```

---

## 3. Reconciliation — 무엇이 바뀌었는지 찾기

상태가 변경되면 React는 새 Virtual DOM을 만들고, 이전 Virtual DOM과 비교해서 실제 DOM에서 무엇을 바꿔야 할지 계산합니다. 이 과정을 Reconciliation(재조정)이라고 합니다.

```mermaid
flowchart TD
    A["상태/props 변경"] --> B["새 Virtual DOM 트리 생성"]
    B --> C["Diffing 알고리즘 실행"]
    C --> D{"같은 타입?"}
    D -->|"예"| E["속성만 업데이트"]
    D -->|"아니오"| F["노드 제거 후 새로 생성"]
    E --> G["자식 노드 재귀 비교"]
    F --> G
    G --> H["실제 DOM 최소 업데이트"]

    style H fill:#2ecc71,color:#fff
```

### Diffing 규칙 1 — 타입이 다르면 전체 교체

```jsx
// 이전
<div><Counter /></div>

// 다음 — div가 span으로 바뀜
<span><Counter /></span>
// Counter는 언마운트 후 새로 마운트됨 → state 초기화!
```

이것을 모르면 컴포넌트가 갑자기 state를 잃어버리는 버그를 이해할 수 없습니다.

### Diffing 규칙 2 — key로 리스트 최적화

```jsx
// key 없음 — 맨 앞에 추가하면?
['사과', '바나나', '딸기'].map(fruit => <li>{fruit}</li>);

// '포도'를 맨 앞에 추가하면 React는
// 사과→포도, 바나나→사과, 딸기→바나나, (새로)딸기 처럼 인식 → 비효율

// key 있음 — 정확하게 추가된 것만 처리
['사과', '바나나', '딸기'].map(fruit => <li key={fruit}>{fruit}</li>);
// '포도'를 맨 앞에 추가하면 포도만 새로 추가됐다고 정확히 인식
```

> 비유: 출석부에 이름 대신 번호만 있으면, 1번 자리에 새 학생이 오면 기존 학생들이 모두 자리를 바꾼 것처럼 처리됩니다. 이름(key)이 있으면 새 학생만 새 자리에 배정합니다.

---

## 4. React Fiber — 작업을 잘게 쪼개다

React 16에서 Fiber라는 새 재조정 엔진이 도입되었습니다. Fiber 이전에는 Virtual DOM 비교 작업이 동기적으로 진행되어 중단할 수 없었습니다. 큰 트리를 처리하다가 UI가 수백 밀리초 동안 멈추는 문제가 있었습니다.

> 비유: 기존 방식은 화물차 한 대에 모든 짐을 싣고 가는 것입니다. 짐이 많으면 출발까지 오래 기다려야 합니다. Fiber는 짐을 작은 택배로 나눠서 중요한 것부터 먼저 보냅니다.

```mermaid
graph TD
    subgraph "React 15 이전 Stack Reconciler"
        OLD["재귀적 동기 처리"]
        OLD --> BLOCK["중단 불가능"]
        BLOCK --> FREEZE["긴 작업 시 UI 멈춤"]
    end

    subgraph "React 16+ Fiber Reconciler"
        NEW["작업을 Fiber 단위로 분할"]
        NEW --> PAUSE["중단 재개 가능"]
        PAUSE --> PRIORITY["우선순위 기반 스케줄링"]
        PRIORITY --> SMOOTH["UI 부드러움 유지"]
    end

    style FREEZE fill:#e74c3c,color:#fff
    style SMOOTH fill:#2ecc71,color:#fff
```

Fiber는 두 단계로 나뉩니다. **Render Phase**는 비동기로 중단 가능하고, **Commit Phase**는 실제 DOM을 바꾸는 작업이라 동기적으로 한 번에 처리합니다.

---

## 5. JSX 심층 이해 — HTML이 아니다

JSX는 HTML처럼 보이지만 자바스크립트입니다. 몇 가지 중요한 차이가 있습니다.

```jsx
// 1. 하나의 루트 요소만 반환 가능
// 틀림
return (
  <h1>제목</h1>
  <p>단락</p>  // SyntaxError
);

// 맞음 — div로 감싸거나
return (
  <div>
    <h1>제목</h1>
    <p>단락</p>
  </div>
);

// 맞음 — Fragment 사용 (DOM에 요소 추가 없이)
return (
  <>
    <h1>제목</h1>
    <p>단락</p>
  </>
);

// 2. JavaScript 표현식은 중괄호로
const name = '홍길동';
const element = <h1>안녕하세요, {name}님</h1>;

// 3. class 대신 className
const el = <div className="container"></div>;

// 4. 이벤트는 camelCase
const btn = <button onClick={handleClick}>클릭</button>;

// 5. 조건부 렌더링
const content = (
  <div>
    {isLoggedIn ? <UserPanel /> : <LoginForm />}
    {hasError && <ErrorMessage />}
  </div>
);
```

---

## 6. Props와 단방향 데이터 흐름

React에서 데이터는 **항상 부모에서 자식으로만 흐릅니다.** 자식이 부모 데이터를 바꾸려면 부모가 내려준 콜백 함수를 호출해야 합니다.

> 비유: 회사 조직도처럼 위에서 아래로 지시가 내려옵니다. 직원이 결정을 바꾸고 싶으면 상사에게 보고(콜백 호출)해서 위에서 결정이 내려오게 합니다.

```mermaid
graph TD
    PARENT["부모 컴포넌트<br>state: { user, posts }"]
    CHILD1["자식1: UserCard<br>props: { user }"]
    CHILD2["자식2: PostList<br>props: { posts }"]
    GRANDCHILD["손자: PostItem<br>props: { post }"]

    PARENT -->|"props 전달"| CHILD1
    PARENT -->|"props 전달"| CHILD2
    CHILD2 -->|"props 전달"| GRANDCHILD

    CHILD1 -->|"이벤트 핸들러 호출"| PARENT
    GRANDCHILD -->|"콜백 호출"| CHILD2
    CHILD2 -->|"콜백 호출"| PARENT

    style PARENT fill:#e74c3c,color:#fff
    style CHILD1 fill:#3498db,color:#fff
    style CHILD2 fill:#3498db,color:#fff
    style GRANDCHILD fill:#2ecc71,color:#fff
```

```jsx
// Props는 읽기 전용입니다
function UserCard({ user, onDelete }) {
  // user.name = '변경'; // 금지! Props를 직접 수정하면 안 됩니다
  // 왜냐하면 React가 변경을 감지하지 못해 렌더링이 안 됩니다

  return (
    <div className="card">
      <h2>{user.name}</h2>
      <p>{user.email}</p>
      <button onClick={() => onDelete(user.id)}>삭제</button>
    </div>
  );
}
```

---

## 7. 불변성 — React가 변경을 감지하는 방식

React는 **얕은 비교(Shallow Comparison)**로 상태 변경을 감지합니다. 같은 객체 참조면 바뀌지 않은 것으로 간주합니다. 그래서 배열이나 객체를 직접 수정하면 React가 변경을 감지하지 못합니다.

> 비유: 택배 시스템은 박스 겉면의 라벨(참조)만 확인합니다. 박스 안의 내용물(내부 데이터)을 바꿔도 라벨이 같으면 "같은 물건"으로 처리합니다. 새 박스(새 참조)에 담아야 "새 택배"로 인식합니다.

```jsx
const [users, setUsers] = useState([{ id: 1, name: '홍길동' }]);

// 잘못된 방법 — 직접 변형 (mutation)
users.push({ id: 2, name: '김철수' });
setUsers(users); // 같은 참조! React가 변경 감지 못함 → 리렌더링 안 됨

// 올바른 방법 — 새 배열 생성
setUsers([...users, { id: 2, name: '김철수' }]);
setUsers(prev => [...prev, { id: 2, name: '김철수' }]);

// 객체 업데이트
const [user, setUser] = useState({ name: '홍길동', age: 25 });

// 잘못됨
user.age = 26;
setUser(user); // 같은 참조 → 변경 감지 못함

// 올바름
setUser({ ...user, age: 26 }); // 새 객체 생성
setUser(prev => ({ ...prev, age: 26 }));
```

---

## 8번 다이어그램 - 렌더링 트리거

```mermaid
flowchart TD
    A["렌더링 트리거"] --> B["setState 호출"]
    A --> C["props 변경"]
    A --> D["부모 컴포넌트 리렌더링"]
    A --> E["Context 값 변경"]

    B --> G["렌더 함수 실행"]
    C --> G
    D --> G
    E --> G

    G --> H["Virtual DOM 생성"]
    H --> I["Diffing"]
    I --> J["필요한 경우만 DOM 업데이트"]

    style J fill:#2ecc71,color:#fff
```

### 불필요한 렌더링 방지

부모가 리렌더링되면 자식도 자동으로 리렌더링됩니다. `React.memo`를 쓰면 props가 바뀌지 않았을 때 자식 렌더링을 건너뜁니다.

```jsx
// React.memo: props가 같으면 렌더링 스킵
const ExpensiveComponent = React.memo(function({ data, onClick }) {
  console.log('렌더링!');
  return <div onClick={onClick}>{data}</div>;
});

// 주의: 얕은 비교이므로 배열/객체는 새 참조면 다르다고 판단
// { items: [1, 2] } vs { items: [1, 2] } → 다름 (새 참조)
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

```jsx
// 무한 루프 1: useEffect에 의존성 배열 없음
function BadComponent() {
  const [data, setData] = useState({});

  useEffect(() => {
    fetch('/api/data')
      .then(r => r.json())
      .then(setData); // setData 호출 → 리렌더링 → useEffect 재실행 → ...
  }); // 의존성 배열 없음!

  return <div>{data.name}</div>;
}

// 무한 루프 2: 렌더링 중 setState 호출
function AlsoBadComponent() {
  const [count, setCount] = useState(0);

  setCount(count + 1); // 렌더링 중 상태 변경 → 리렌더링 → 반복

  return <div>{count}</div>;
}

// 해결: useEffect에 의존성 배열 추가
useEffect(() => {
  fetch('/api/data').then(r => r.json()).then(setData);
}, []); // 빈 배열: 마운트 시 한 번만 실행
```

---
</div>
</div>
</details>

## 정리

```mermaid
mindmap
  root((React 핵심))
    Virtual DOM
      실제 DOM의 JS 표현
      변경 최소화
      성능 최적화
    Fiber
      작업 분할
      우선순위 처리
      중단 재개 가능
    컴포넌트
      함수형 권장
      Props 읽기 전용
      단방향 데이터
    렌더링
      상태 props 변경 시
      불변성 원칙
      React.memo 최적화
```

React의 핵심은 **선언적 UI** 패러다임입니다. "어떻게 DOM을 변경할지" 대신 "상태에 따라 UI가 어떻게 보여야 하는지"를 선언하면, React가 효율적으로 DOM을 업데이트합니다. 이 방식이 가능한 이유가 Virtual DOM과 Diffing 알고리즘입니다. 개념이 복잡해 보이지만 결국 "변경된 것만 최소로 업데이트한다"는 단순한 원칙에서 출발합니다.
