---
title: "JavaScript 핵심"
categories: FRONTEND
tags: [JavaScript, 실행컨텍스트, 이벤트루프, 클로저, 프로토타입, Promise, async-await]
toc: true
toc_sticky: true
toc_label: 목차
---

## 비유로 시작하기

JavaScript는 싱글 스레드 언어입니다. 레스토랑에 비유하면 **웨이터가 한 명**인 것과 같습니다. 그런데 이 웨이터는 손님이 주문하면 주방에 전달하고(비동기 작업 요청), 다른 손님을 응대하고(다른 코드 실행), 주방이 완성했을 때 다시 그 손님에게 갑니다(콜백/Promise 처리). 이것이 **이벤트 루프**입니다.

---

## 실행 컨텍스트 (Execution Context)

JavaScript 코드가 실행되는 **환경**입니다. 코드가 실행될 때 엔진은 실행 컨텍스트를 생성합니다.

### 구성요소

```
실행 컨텍스트 = {
  Variable Environment: 변수, 함수 선언 저장
  Lexical Environment: 스코프 체인 관리
  this Binding: this가 가리키는 객체
}
```

### 콜 스택 (Call Stack)

```javascript
function multiply(a, b) {
    return a * b;  // 3. multiply 실행 컨텍스트 (스택 최상단)
}

function square(n) {
    return multiply(n, n);  // 2. square 실행 컨텍스트
}

function printSquare(n) {
    const result = square(n);  // 1. printSquare 실행 컨텍스트
    console.log(result);
}

printSquare(5);

// 콜 스택 순서:
// [printSquare] → [printSquare, square] → [printSquare, square, multiply]
// → multiply 반환 → [printSquare, square] → square 반환 → [printSquare] → 반환
```

### 호이스팅 (Hoisting)

변수와 함수 선언이 실행 컨텍스트 생성 단계에서 **메모리에 미리 등록**됩니다.

```javascript
// 함수 선언식: 완전히 호이스팅
console.log(greet("Kim"));  // "Hello, Kim" (정상 작동)
function greet(name) {
    return `Hello, ${name}`;
}

// var: 선언만 호이스팅, 초기화는 undefined
console.log(x);  // undefined (에러 아님)
var x = 10;
console.log(x);  // 10

// let/const: 선언은 호이스팅되지만 TDZ(Temporal Dead Zone) 존재
console.log(y);  // ReferenceError: Cannot access 'y' before initialization
let y = 20;
```

---

## 이벤트 루프 (Event Loop)

JavaScript의 비동기 처리 메커니즘입니다.

<div class="mermaid">
graph TD
    CS[Call Stack<br>현재 실행 중인 코드]
    WA[Web APIs<br>setTimeout, fetch, DOM]
    CQ[Callback Queue<br>Task Queue<br>setTimeout 콜백]
    MQ[Microtask Queue<br>Promise.then, MutationObserver]
    EL[Event Loop]

    CS -->|비동기 요청| WA
    WA -->|완료 시| CQ
    WA -->|Promise 완료| MQ
    EL -->|Call Stack 비면| MQ
    EL -->|Microtask 없으면| CQ
    MQ --> CS
    CQ --> CS
</div>

```javascript
console.log('1');  // 동기

setTimeout(() => console.log('2'), 0);  // Task Queue

Promise.resolve().then(() => console.log('3'));  // Microtask Queue

console.log('4');  // 동기

// 출력 순서: 1 → 4 → 3 → 2
// 이유:
// - 동기 코드 먼저 (1, 4)
// - Microtask Queue 우선 (3)
// - Task Queue 마지막 (2)
```

**중요**: Microtask Queue(Promise)는 Task Queue(setTimeout)보다 항상 먼저 처리됩니다.

```javascript
// 실무 함정: 무한 Microtask
function recursivePromise() {
    Promise.resolve().then(recursivePromise);
    // Call Stack이 비어도 Microtask가 계속 추가됨 → UI 블로킹!
}
// 해결: setTimeout으로 Task Queue에 넣어 UI 업데이트 기회 제공
```

---

## this 바인딩

`this`는 **함수가 호출되는 방식**에 따라 결정됩니다.

```javascript
// 1. 일반 함수 호출: window (strict mode에서 undefined)
function show() {
    console.log(this);
}
show();  // window

// 2. 메서드 호출: 메서드를 소유한 객체
const obj = {
    name: 'Kim',
    greet() {
        console.log(this.name);
    }
};
obj.greet();  // 'Kim'

// 3. 생성자 함수: 새로 생성된 객체
function Person(name) {
    this.name = name;
}
const p = new Person('Lee');
console.log(p.name);  // 'Lee'

// 4. 화살표 함수: 상위 스코프의 this (렉시컬 this)
const timer = {
    count: 0,
    start() {
        setInterval(() => {
            this.count++;  // this = timer 객체 (상위 스코프)
            console.log(this.count);
        }, 1000);
    }
};

// 5. 명시적 바인딩: call, apply, bind
function greet(greeting) {
    return `${greeting}, ${this.name}`;
}
const user = { name: 'Park' };
console.log(greet.call(user, 'Hello'));     // 'Hello, Park'
console.log(greet.apply(user, ['Hi']));    // 'Hi, Park'
const boundGreet = greet.bind(user);
console.log(boundGreet('Hey'));            // 'Hey, Park'
```

---

## 클로저 (Closure)

**함수가 자신이 생성될 때의 렉시컬 환경을 기억**하는 것입니다.

```javascript
function makeCounter(initial = 0) {
    let count = initial;  // 외부에서 직접 접근 불가 (private)

    return {
        increment() { return ++count; },
        decrement() { return --count; },
        getCount() { return count; }
    };
}

const counter = makeCounter(10);
console.log(counter.increment());  // 11
console.log(counter.increment());  // 12
console.log(counter.decrement());  // 11
// count 변수는 외부에서 직접 수정 불가 → 캡슐화
```

### 실무 활용: 함수 팩토리

```javascript
// 다른 배율의 곱셈 함수 생성
function makeMultiplier(factor) {
    return (num) => num * factor;  // factor를 클로저로 기억
}

const double = makeMultiplier(2);
const triple = makeMultiplier(3);

console.log(double(5));   // 10
console.log(triple(5));   // 15

// 메모이제이션 (캐싱)
function memoize(fn) {
    const cache = {};
    return function(...args) {
        const key = JSON.stringify(args);
        if (cache[key] !== undefined) {
            console.log('캐시 히트:', key);
            return cache[key];
        }
        cache[key] = fn.apply(this, args);
        return cache[key];
    };
}

const expensiveCalc = memoize((n) => {
    // 복잡한 계산...
    return n * n;
});

expensiveCalc(10);  // 계산 실행
expensiveCalc(10);  // 캐시 히트
```

---

## 프로토타입 (Prototype)

JavaScript는 **프로토타입 기반 상속**을 사용합니다.

```javascript
// 모든 함수는 prototype 프로퍼티를 가짐
function Animal(name) {
    this.name = name;
}

// 프로토타입에 메서드 추가 (인스턴스가 공유)
Animal.prototype.speak = function() {
    return `${this.name}이 소리를 냅니다`;
};

const dog = new Animal('멍멍이');
console.log(dog.speak());  // "멍멍이이 소리를 냅니다"

// 프로토타입 체인
console.log(dog.hasOwnProperty('name'));  // true (자체 프로퍼티)
console.log(dog.hasOwnProperty('speak')); // false (프로토타입의 것)

// 프로토타입 체인: dog → Animal.prototype → Object.prototype → null
```

### Class 문법 (ES6+) - 프로토타입의 문법적 설탕

```javascript
class Animal {
    #name;  // Private field (ES2022)

    constructor(name) {
        this.#name = name;
    }

    speak() {
        return `${this.#name}이 소리를 냅니다`;
    }

    get name() { return this.#name; }

    static create(name) {  // 정적 메서드
        return new Animal(name);
    }
}

class Dog extends Animal {
    #breed;

    constructor(name, breed) {
        super(name);  // 부모 생성자 호출
        this.#breed = breed;
    }

    speak() {
        return `${super.speak()} - 멍멍!`;  // 부모 메서드 호출
    }

    get breed() { return this.#breed; }
}

const dog = new Dog('바둑이', '진도');
console.log(dog.speak());  // "바둑이이 소리를 냅니다 - 멍멍!"
```

---

## Promise / async-await

### Promise

비동기 작업의 **최종 완료 또는 실패**를 나타냅니다.

```javascript
// Promise 생성
function fetchUser(id) {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            if (id > 0) {
                resolve({ id, name: 'Kim' });  // 성공
            } else {
                reject(new Error('Invalid user ID'));  // 실패
            }
        }, 1000);
    });
}

// Promise 체이닝
fetchUser(1)
    .then(user => {
        console.log(user);  // { id: 1, name: 'Kim' }
        return fetchUserOrders(user.id);  // 다음 비동기 작업
    })
    .then(orders => console.log(orders))
    .catch(err => console.error('에러:', err.message))
    .finally(() => console.log('항상 실행'));

// Promise.all: 병렬 실행, 모두 완료 대기
const [user, posts, comments] = await Promise.all([
    fetchUser(1),
    fetchPosts(1),
    fetchComments(1)
]);

// Promise.allSettled: 일부 실패해도 전체 결과 반환
const results = await Promise.allSettled([
    fetchUser(1),
    fetchUser(-1),  // 실패
]);
// [{ status: 'fulfilled', value: {...} }, { status: 'rejected', reason: Error }]

// Promise.race: 가장 먼저 완료된 것 반환 (타임아웃 구현에 활용)
const result = await Promise.race([
    fetchData(),
    new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 5000))
]);
```

### async/await

Promise를 동기 코드처럼 작성하는 문법입니다.

```javascript
async function getOrderDetails(orderId) {
    try {
        const order = await fetchOrder(orderId);           // 순차 실행
        const user = await fetchUser(order.customerId);    // 순차 실행

        // 독립적인 요청은 병렬로
        const [items, shipping] = await Promise.all([
            fetchOrderItems(orderId),
            fetchShippingInfo(orderId)
        ]);

        return { order, user, items, shipping };
    } catch (error) {
        if (error instanceof OrderNotFoundException) {
            throw error;  // 다시 던지기
        }
        throw new Error(`주문 상세 조회 실패: ${error.message}`);
    }
}
```

---

## var / let / const

| 항목 | var | let | const |
|------|-----|-----|-------|
| 스코프 | 함수 스코프 | 블록 스코프 | 블록 스코프 |
| 호이스팅 | O (undefined) | O (TDZ) | O (TDZ) |
| 재선언 | 가능 | 불가 | 불가 |
| 재할당 | 가능 | 가능 | 불가 |
| 전역 객체 등록 | 등록됨 | 등록 안 됨 | 등록 안 됨 |

```javascript
// var의 함수 스코프 함정
for (var i = 0; i < 3; i++) {
    setTimeout(() => console.log(i), 100);
}
// 출력: 3, 3, 3 (클로저가 같은 i를 참조)

// let으로 해결 (블록 스코프: 루프마다 새로운 i)
for (let i = 0; i < 3; i++) {
    setTimeout(() => console.log(i), 100);
}
// 출력: 0, 1, 2
```

---

## 극한 시나리오

### 시나리오: Promise Hell (콜백 지옥의 Promise 버전)

```javascript
// 나쁜 예: 중첩 then
fetchUser(1)
    .then(user => {
        fetchOrders(user.id)
            .then(orders => {
                fetchOrderItems(orders[0].id)
                    .then(items => { /* 더 깊어짐... */ });
            });
    });

// 좋은 예: 체이닝 또는 async/await
async function loadData() {
    const user = await fetchUser(1);
    const orders = await fetchOrders(user.id);
    const items = await fetchOrderItems(orders[0].id);
    return { user, orders, items };
}
```

### 시나리오: 메모리 누수 (클로저 + 이벤트 리스너)

```javascript
// 누수 발생
function setupPage() {
    const largeData = new Array(1000000).fill('data');  // 대용량 데이터

    document.getElementById('btn').addEventListener('click', () => {
        console.log(largeData.length);  // largeData를 클로저로 참조
    });
    // 버튼이 DOM에서 제거되어도 largeData는 GC 안 됨
}

// 해결: 정리(cleanup) 함수 반환
function setupPage() {
    const largeData = new Array(1000000).fill('data');

    const handler = () => console.log(largeData.length);
    document.getElementById('btn').addEventListener('click', handler);

    return () => {
        document.getElementById('btn').removeEventListener('click', handler);
        // largeData도 GC 가능해짐
    };
}
const cleanup = setupPage();
// 나중에
cleanup();
```
