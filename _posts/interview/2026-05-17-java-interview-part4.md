---
title: "Java 면접 — Stream / Functional (Q34~Q40)"
categories: INTERVIEW
tags: [Java, 면접, Stream, Lambda, Functional, Optional]
toc: true
toc_sticky: true
toc_label: 목차
---

## 4. Stream / Functional (Q34 ~ Q40)

### Q34. Stream API와 for-loop의 차이는?

**모범 답변**

| 기준 | for-loop | Stream |
|---|---|---|
| 표현 방식 | 명령형(How) | 선언형(What) |
| 병렬 처리 | 직접 구현 | `parallelStream()` |
| 가독성 | 복잡한 중첩 시 낮음 | 파이프라인으로 높음 |
| 성능 | 단순 순회는 더 빠름 | 오버헤드 있음 |
| 재사용 | 불가 (소비 후 재사용 불가) | 불가 (최종 연산 후 종료) |

```java
// 명령형
List<String> names = new ArrayList<>();
for (Order order : orders) {
    if (order.getAmount() > 1000) {
        names.add(order.getCustomerName());
    }
}

// 선언형
List<String> names = orders.stream()
    .filter(o -> o.getAmount() > 1000)
    .map(Order::getCustomerName)
    .collect(Collectors.toList());
```

> **비유:** for-loop는 요리사가 재료를 직접 골라 다듬는 것, Stream은 "1000원 이상 주문만 고객명 뽑아줘"라는 주문서입니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** parallelStream()의 주의사항은?

1. ForkJoinPool.commonPool() 사용 — 공유 풀이라 다른 작업에 영향
2. 요소 순서 의존 로직이 있으면 결과 비결정적
3. I/O 집중 작업에는 비적합 (CPU 집중 작업에만 유리)
4. 작은 데이터셋에서는 오버헤드로 오히려 느림

</details>

---

### Q35. Optional의 올바른 사용법은?

**모범 답변**

`Optional`은 반환값이 없을 수 있음을 명시적으로 표현합니다. **null 대체가 목적이 아닙니다.**

**올바른 사용:**
```java
// 반환 타입으로 사용
public Optional<User> findById(Long id) { ... }

// 값 처리
user.ifPresent(u -> process(u));
String name = user.map(User::getName).orElse("Unknown");
String name = user.orElseThrow(() -> new UserNotFoundException(id));
```

**잘못된 사용:**
```java
// 필드로 사용 (직렬화 문제)
private Optional<String> name; // 안티패턴

// 메서드 파라미터로 사용
public void process(Optional<String> name) { ... } // 안티패턴

// isPresent() + get() 조합 (Optional 의미 퇴색)
if (user.isPresent()) { return user.get(); } // 안티패턴
```

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** `orElse`와 `orElseGet`의 차이는?

`orElse(value)`: 항상 value 표현식이 평가됩니다. `orElseGet(() -> value)`: Optional이 비어있을 때만 람다 실행됩니다. 생성 비용이 있는 기본값은 `orElseGet`을 사용해야 합니다.

</details>

---

### Q36. 람다와 익명 클래스의 차이는?

**모범 답변**

| 구분 | 익명 클래스 | 람다 |
|---|---|---|
| this 참조 | 익명 클래스 자신 | 외부 클래스 |
| 상태 | 인스턴스 변수 가능 | 없음 |
| 사용 가능 범위 | 모든 인터페이스/추상 클래스 | 함수형 인터페이스만 |
| 컴파일 | 별도 .class 파일 생성 | invokedynamic 사용 |

람다는 내부적으로 `invokedynamic` 명령어와 `LambdaMetafactory`를 사용하여 런타임에 메서드 핸들로 변환됩니다. 익명 클래스보다 메모리 효율이 높습니다.

---

### Q37. 메서드 참조(Method Reference) 4가지 유형은?

```java
// 1. 정적 메서드: ClassName::staticMethod
Function<String, Integer> f1 = Integer::parseInt;

// 2. 인스턴스 메서드 (특정 객체): instance::method
Consumer<String> f2 = System.out::println;

// 3. 인스턴스 메서드 (임의 객체): ClassName::instanceMethod
Function<String, String> f3 = String::toUpperCase;

// 4. 생성자: ClassName::new
Supplier<ArrayList<String>> f4 = ArrayList::new;
```

---

### Q38. Collectors 주요 메서드는?

```java
// 그룹화
Map<String, List<Order>> byStatus = orders.stream()
    .collect(Collectors.groupingBy(Order::getStatus));

// 파티셔닝
Map<Boolean, List<Order>> partitioned = orders.stream()
    .collect(Collectors.partitioningBy(o -> o.getAmount() > 1000));

// 문자열 조인
String names = orders.stream()
    .map(Order::getName)
    .collect(Collectors.joining(", ", "[", "]"));

// 통계
IntSummaryStatistics stats = orders.stream()
    .collect(Collectors.summarizingInt(Order::getAmount));
```

---

### Q39 ~ Q40. 함수형 심화

**Q39. Predicate, Function, Consumer, Supplier의 차이는?**

| 인터페이스 | 시그니처 | 용도 |
|---|---|---|
| `Predicate<T>` | T → boolean | 조건 검사 |
| `Function<T,R>` | T → R | 변환 |
| `Consumer<T>` | T → void | 소비 (부수 효과) |
| `Supplier<T>` | () → T | 생성/지연 제공 |

**Q40. Stream에서 reduce 사용법은?**

```java
// 합계
int sum = numbers.stream().reduce(0, Integer::sum);

// Optional 반환 (초기값 없음)
Optional<Integer> max = numbers.stream().reduce(Integer::max);

// 복잡한 accumulator
Map<String, Long> wordCount = words.stream()
    .collect(Collectors.groupingBy(w -> w, Collectors.counting()));
```

---


---

## 다른 파트 보기

- [Part 1: JVM 메모리 구조 (Q1~Q10)](/interview/java-interview-part1/)
- [Part 2: 동시성 (Q11~Q22)](/interview/java-interview-part2/)
- [Part 3: Collection 내부 구조 (Q23~Q33)](/interview/java-interview-part3/)
- [Part 4: Stream / Functional (Q34~Q40)](/interview/java-interview-part4/)
- [Part 5: 예외처리 / Generics (Q41~Q50)](/interview/java-interview-part5/)
