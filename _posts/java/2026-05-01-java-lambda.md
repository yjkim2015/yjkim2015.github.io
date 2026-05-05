---
title: "Java 람다(Lambda) 표현식"
categories:
- JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

Java 8에서 도입된 람다(Lambda) 표현식은 Java를 함수형 프로그래밍 언어로 진화시킨 핵심 기능입니다. 단순한 문법 설탕(syntactic sugar)처럼 보이지만, 그 내부 동작 원리부터 실전 활용까지 깊이 있게 이해해야 제대로 쓸 수 있습니다.

> **비유:** 람다는 "포스트잇에 적은 지시사항"입니다. 예전에는 누군가에게 일을 시키려면 정식 계약서(익명 클래스)를 써야 했지만, 람다는 포스트잇에 핵심 지시만 적어 건네는 것입니다. "이 리스트를 정렬해줘, 기준은 이름 순"이라고 포스트잇 한 장이면 됩니다.

## 1. 람다란? 왜 필요한가?

### 람다 이전의 세계

Java 8 이전에는 동작(behavior)을 파라미터로 전달하려면 익명 클래스(anonymous class)를 사용해야 했습니다.

```java
// Java 8 이전 — 익명 클래스로 동작 전달
List<String> names = Arrays.asList("Charlie", "Alice", "Bob");

Collections.sort(names, new Comparator<String>() {
    @Override
    public int compare(String a, String b) {
        return a.compareTo(b);
    }
});
```

이 코드의 문제점은 명확합니다. 실제로 하고 싶은 일은 `a.compareTo(b)` 한 줄인데, 그것을 감싸는 보일러플레이트(boilerplate) 코드가 6줄이나 됩니다.

### 람다로 개선

```java
// Java 8 이후 — 람다 표현식
List<String> names = Arrays.asList("Charlie", "Alice", "Bob");
Collections.sort(names, (a, b) -> a.compareTo(b));

// 더 나아가 메서드 레퍼런스로
Collections.sort(names, String::compareTo);
```

### 람다가 필요한 이유

람다는 **동작 파라미터화(behavior parameterization)** 패턴을 간결하게 표현하기 위해 도입되었습니다. "무엇을 할지(what)"를 "어떻게 할지(how)"와 분리하여, 동작 자체를 값처럼 다루는 것이 핵심 아이디어입니다.

```java
// 전략 패턴을 람다로 — 검증 로직을 동적으로 교체
public static List<String> filter(List<String> list, Predicate<String> condition) {
    List<String> result = new ArrayList<>();
    for (String s : list) {
        if (condition.test(s)) {
            result.add(s);
        }
    }
    return result;
}

// 호출 시 동작을 주입
List<String> longNames = filter(names, name -> name.length() > 5);
List<String> aNames   = filter(names, name -> name.startsWith("A"));
```

---

## 2. 함수형 인터페이스 (@FunctionalInterface)

> **비유:** 함수형 인터페이스는 "단 하나의 빈칸이 있는 양식"입니다. 이력서 양식에 "자기소개" 빈칸이 하나만 있으면 누구든 그 칸만 채우면 됩니다. 빈칸이 2개 이상이면 람다(포스트잇)로는 어느 칸을 채울지 모호해지므로, 반드시 빈칸(추상 메서드)이 하나여야 합니다.

### 정의

람다 표현식은 **함수형 인터페이스(functional interface)** 의 인스턴스입니다. 함수형 인터페이스란 **추상 메서드가 정확히 하나**인 인터페이스입니다. 컴파일러는 람다 표현식이 대입되는 타입(target type)을 보고 어떤 함수형 인터페이스의 구현인지 추론합니다.

```java
@FunctionalInterface
public interface Runnable {
    void run();  // 추상 메서드 1개
}

@FunctionalInterface
public interface Comparator<T> {
    int compare(T o1, T o2);  // 추상 메서드 1개
    // equals()는 Object의 메서드이므로 제외
    // default 메서드는 제외
}
```

### @FunctionalInterface 어노테이션

이 어노테이션은 컴파일러에게 "이 인터페이스는 함수형 인터페이스여야 한다"고 알립니다. 추상 메서드가 2개 이상이면 컴파일 에러가 발생합니다.

```java
@FunctionalInterface
public interface StringProcessor {
    String process(String input);

    // default 메서드는 허용 (추상 메서드 아님)
    default StringProcessor andThen(StringProcessor after) {
        return s -> after.process(this.process(s));
    }

    // static 메서드도 허용
    static StringProcessor identity() {
        return s -> s;
    }

    // Object의 메서드 오버라이드도 허용
    @Override
    String toString();  // 이건 추상 메서드로 카운트되지 않음
}
```

### 직접 만드는 함수형 인터페이스

```java
// 예외를 던지는 함수형 인터페이스 — 표준 라이브러리에 없어서 자주 직접 만듦
@FunctionalInterface
public interface ThrowingSupplier<T> {
    T get() throws Exception;
}

// 사용
ThrowingSupplier<Connection> connSupplier = () -> DriverManager.getConnection(url);
```

---

## 3. 람다 문법

> **비유:** 람다 문법은 전보(telegram)와 같습니다. 전보는 글자 수를 줄이기 위해 불필요한 단어를 모두 생략합니다. `(a, b) -> a + b`는 "a와 b를 받아서 더한 값을 돌려준다"를 전보 스타일로 줄인 것입니다. 파라미터가 하나면 괄호도, 바디가 한 줄이면 중괄호와 return도 생략합니다.

### 기본 구조

```java
// (파라미터) -> { 바디 }

// 1. 파라미터 없음
Runnable r = () -> System.out.println("Hello");

// 2. 파라미터 1개 — 괄호 생략 가능
Consumer<String> c = s -> System.out.println(s);
Consumer<String> c2 = (s) -> System.out.println(s);  // 동일

// 3. 파라미터 2개 이상 — 괄호 필수
Comparator<String> comp = (a, b) -> a.compareTo(b);

// 4. 타입 명시 (선택)
Comparator<String> comp2 = (String a, String b) -> a.compareTo(b);

// 5. 바디가 단일 표현식 — 중괄호, return, 세미콜론 생략
Function<Integer, Integer> square = x -> x * x;

// 6. 바디가 여러 문장 — 중괄호 필수, return 명시
Function<Integer, Integer> process = x -> {
    int doubled = x * 2;
    int shifted = doubled + 1;
    return shifted;
};

// 7. void 반환 — 단일 표현식이어도 중괄호 없이 가능
Consumer<String> printer = s -> System.out.println(s);

// 8. 예외 처리 — 체크 예외는 선언 필요
@FunctionalInterface
interface IOAction {
    void perform() throws IOException;
}
IOAction readFile = () -> new FileReader("test.txt").read();
```

---

## 4. 타입 추론

> **비유:** 타입 추론은 "빈칸 채우기 시험"입니다. `Comparator<String> comp = (a, b) -> ...`라고 쓰면, 컴파일러는 왼쪽의 `Comparator<String>`이라는 문맥을 보고 "아, a와 b는 String이구나"라고 자동으로 빈칸을 채웁니다. 교사(컴파일러)가 문맥(target type)에서 정답을 추론하는 것입니다.

람다의 타입은 **대입되는 컨텍스트(target type)** 에서 추론됩니다. 컴파일러는 람다가 대입되는 함수형 인터페이스의 제네릭 타입 파라미터를 분석해 파라미터 타입과 반환 타입을 결정합니다.

```java
// 컴파일러가 Comparator<String>임을 알아서 T=String으로 추론
Comparator<String> comp = (a, b) -> a.compareTo(b);
//                         ↑  ↑
//                    String으로 자동 추론

// 메서드 파라미터에서 추론
List<String> names = Arrays.asList("B", "A", "C");
names.sort((a, b) -> a.compareTo(b));
//  sort(Comparator<? super String>) 시그니처에서 추론

// 제네릭 메서드에서 추론
<T> T firstOrDefault(List<T> list, Supplier<T> defaultSupplier) {
    return list.isEmpty() ? defaultSupplier.get() : list.get(0);
}

String result = firstOrDefault(names, () -> "default");
//                                         ↑ Supplier<String>으로 추론
```

### 타입 추론이 실패하는 경우

```java
// 모호한 경우 — 명시적 캐스팅 또는 타입 지정 필요
Object o = (Runnable) () -> System.out.println("hi");  // OK
Object o2 = () -> System.out.println("hi");  // 컴파일 에러: target type 불명확
```

---

## 5. 변수 캡처와 effectively final 제약

> **비유:** 변수 캡처는 "사진 찍기"입니다. 람다가 외부 변수를 캡처하면 그 순간의 값을 사진으로 찍어 간직합니다. 사진 속 풍경은 바뀌지 않으므로, 원본 풍경(변수)도 바뀌면 안 됩니다(effectively final). 만약 사진을 찍은 뒤 원본이 바뀌면 "사진과 실물이 다르다"는 혼란이 생기므로, Java는 아예 원본 변경을 금지합니다.

람다는 외부 스코프의 변수를 **캡처(capture)** 할 수 있습니다. 단, 중요한 제약이 있습니다.

### effectively final 규칙

```java
// OK — final 변수
final int threshold = 10;
Predicate<Integer> p = x -> x > threshold;

// OK — effectively final (변경되지 않으면 final과 동일 취급)
int threshold2 = 10;
Predicate<Integer> p2 = x -> x > threshold2;
// threshold2를 이후에 변경하면 컴파일 에러 발생

// 컴파일 에러 — 변경된 변수는 캡처 불가
int count = 0;
Runnable r = () -> System.out.println(count);  // count가 effectively final이면 OK
count++;  // 이 줄이 있으면 위의 람다도 컴파일 에러
```

### 왜 effectively final 제약이 있는가?

스택 변수는 메서드가 끝나면 사라지지만, 람다 인스턴스는 힙에서 더 오래 살 수 있습니다. 람다가 스택 변수를 직접 참조하면 메서드 종료 후 댕글링 참조가 발생합니다. 해결책은 **람다 생성 시점의 값을 복사(copy-by-value)** 하는 것입니다. 복사 후 원본이 바뀌면 복사본과 불일치가 생겨 혼란이 발생하므로, Java는 변경 자체를 금지합니다.

```mermaid
sequenceDiagram
    participant S as 스택(메서드)
    participant L as 람다(힙)
    S->>S: int count = 0 선언
    S->>L: 람다 생성 시 count 값(0) 복사
    S->>S: 메서드 종료 → count 소멸
    L->>L: 복사된 0은 여전히 유효
    Note over S,L: count를 변경하면 복사본과 불일치 → Java가 컴파일 에러로 차단
```

### 우회 방법 — 변경 가능한 컨테이너 사용

```java
// 1. 배열로 우회 (권장하지 않음 — 코드 의도 불명확)
int[] counter = {0};
Runnable r = () -> counter[0]++;

// 2. AtomicInteger 사용 (스레드 안전)
AtomicInteger atomicCounter = new AtomicInteger(0);
Runnable r2 = () -> atomicCounter.incrementAndGet();

// 3. 상태를 가진 클래스로 캡슐화
class Counter {
    int value = 0;
}
Counter c = new Counter();
Runnable r3 = () -> c.value++;
// c 자체는 effectively final (재할당 안 함), c.value는 가변
```

### 인스턴스 변수와 정적 변수는 자유롭게 캡처

```java
public class LambdaCapture {
    private int instanceVar = 100;
    private static int staticVar = 200;

    public Runnable createLambda() {
        // 인스턴스 변수 — this를 통해 접근, 제약 없음
        return () -> System.out.println(instanceVar++);  // OK

        // 정적 변수 — 제약 없음
        // return () -> System.out.println(staticVar++);  // OK
    }
}
```

---

## 6. 메서드 레퍼런스 (Method Reference)

> **비유:** 메서드 레퍼런스는 "전화번호부"입니다. 람다가 "이 사람한테 전화해서 이름을 물어봐"라고 직접 지시하는 것이라면, 메서드 레퍼런스는 전화번호부에서 해당 항목을 가리키며 "여기 봐"라고 하는 것입니다. `String::toUpperCase`는 "String 전화번호부에서 toUpperCase 항목을 찾아라"는 뜻입니다.

메서드 레퍼런스는 이미 이름이 있는 메서드를 람다 대신 참조하는 간결한 문법입니다. 컴파일러는 메서드 레퍼런스를 람다와 동일한 방식으로 처리합니다.

### 6.1 정적 메서드 참조 (Class::staticMethod)

```java
// 람다
Function<String, Integer> parser = s -> Integer.parseInt(s);
// 메서드 레퍼런스
Function<String, Integer> parser2 = Integer::parseInt;

// 활용
List<String> numberStrings = Arrays.asList("1", "2", "3");
List<Integer> numbers = numberStrings.stream()
    .map(Integer::parseInt)
    .collect(Collectors.toList());
```

### 6.2 특정 인스턴스의 메서드 참조 (instance::method)

```java
String prefix = "Hello, ";
// 람다
Function<String, String> greeter = name -> prefix.concat(name);
// 메서드 레퍼런스 — 특정 인스턴스(prefix)의 메서드
Function<String, String> greeter2 = prefix::concat;

// PrintStream 인스턴스의 println 참조
Consumer<String> consolePrinter = System.out::println;
//                                 ↑ System.out이 특정 인스턴스

List<String> list = Arrays.asList("A", "B", "C");
list.forEach(System.out::println);
```

### 6.3 임의 인스턴스의 메서드 참조 (Class::instanceMethod)

파라미터로 들어오는 인스턴스의 메서드를 참조합니다.

```java
// 람다
Function<String, String> toUpper = s -> s.toUpperCase();
// 메서드 레퍼런스 — String 타입의 어떤 인스턴스든 toUpperCase() 호출
Function<String, String> toUpper2 = String::toUpperCase;

// BiFunction으로 두 파라미터 중 첫 번째가 수신자
BiFunction<String, String, Boolean> startsWith = String::startsWith;
// 동일한 람다: (str, prefix) -> str.startsWith(prefix)

boolean result = startsWith.apply("Hello", "He");  // true
```

### 6.4 생성자 참조 (Class::new)

```java
// 람다
Supplier<ArrayList<String>> listMaker = () -> new ArrayList<>();
// 생성자 참조
Supplier<ArrayList<String>> listMaker2 = ArrayList::new;

// 파라미터가 있는 생성자
Function<String, StringBuilder> sbMaker = StringBuilder::new;
StringBuilder sb = sbMaker.apply("initial");

// 배열 생성자
IntFunction<int[]> arrayMaker = int[]::new;
int[] arr = arrayMaker.apply(10);  // new int[10]

// 실전 — Stream.toArray()에서 사용
String[] nameArr = names.stream().toArray(String[]::new);
```

### 메서드 레퍼런스 4종 요약

```mermaid
graph TD
    A["메서드 레퍼런스 4종"] --> B["1️⃣ Class::staticMethod\n정적 메서드 참조\nInteger::parseInt"]
    A --> C["2️⃣ instance::method\n특정 인스턴스 참조\nSystem.out::println"]
    A --> D["3️⃣ Class::instanceMethod\n임의 인스턴스 참조\nString::toUpperCase"]
    A --> E["4️⃣ Class::new\n생성자 참조\nArrayList::new"]
```

---

## 7. java.util.function 패키지 핵심 인터페이스

> **비유:** `java.util.function`은 "표준 규격 부품 카탈로그"입니다. `Function`은 변환기(입력을 출력으로 변환), `Consumer`는 분쇄기(입력을 소비하고 끝), `Supplier`는 자판기(아무것도 넣지 않아도 물건이 나옴), `Predicate`는 검문소(통과/차단을 판별)입니다. 표준 규격이므로 어디에든 끼워 맞출 수 있습니다.

Java 8은 자주 쓰이는 함수형 인터페이스를 `java.util.function` 패키지로 제공합니다.

### 7.1 Function&lt;T, R&gt;

T를 받아 R을 반환합니다.

```java
Function<String, Integer> length = String::length;
Function<Integer, String> intToStr = Object::toString;

// andThen — 두 함수를 합성: f.andThen(g) = g(f(x))
Function<String, String> process = length.andThen(intToStr);
String result = process.apply("hello");  // "5"

// compose — andThen의 역순: f.compose(g) = f(g(x))
Function<Integer, Integer> times2 = x -> x * 2;
Function<Integer, Integer> plus3  = x -> x + 3;
Function<Integer, Integer> times2ThenPlus3 = plus3.compose(times2);
// times2ThenPlus3.apply(4) = plus3(times2(4)) = plus3(8) = 11

// identity — 입력을 그대로 반환
Function<String, String> id = Function.identity();  // s -> s
```

### 7.2 Consumer&lt;T&gt;

T를 받아 아무것도 반환하지 않습니다 (소비).

```java
Consumer<String> printer = System.out::println;
Consumer<List<String>> listClearer = List::clear;

// andThen — 두 Consumer를 순서대로 실행
Consumer<String> printAndLog = printer.andThen(s -> log(s));
printAndLog.accept("Hello");  // 출력 후 로깅

// forEach에서 자주 사용
List<String> names = Arrays.asList("Alice", "Bob");
names.forEach(System.out::println);
```

### 7.3 Supplier&lt;T&gt;

아무것도 받지 않고 T를 반환합니다 (생산). 지연 계산(lazy evaluation)에 가장 많이 활용됩니다.

```java
Supplier<String> greeting = () -> "Hello, World!";
Supplier<List<String>> listFactory = ArrayList::new;
Supplier<LocalDate> today = LocalDate::now;

// 지연 계산(lazy evaluation)에 유용
public <T> T getOrCompute(T cached, Supplier<T> expensive) {
    return cached != null ? cached : expensive.get();
}

// Optional과 함께
String value = Optional.ofNullable(null)
    .orElseGet(() -> "computed default");  // Supplier 사용
```

### 7.4 Predicate&lt;T&gt;

T를 받아 boolean을 반환합니다.

```java
Predicate<String> isEmpty  = String::isEmpty;
Predicate<String> isNotEmpty = isEmpty.negate();         // 부정
Predicate<String> startsA  = s -> s.startsWith("A");
Predicate<String> longName = s -> s.length() > 5;

// and, or 조합
Predicate<String> startsAAndLong = startsA.and(longName);
Predicate<String> startsAOrEmpty = startsA.or(isEmpty);

// 필터링에서 자주 사용
List<String> names = Arrays.asList("Alice", "Bob", "Alexander", "");
List<String> filtered = names.stream()
    .filter(startsAAndLong)
    .collect(Collectors.toList());  // ["Alexander"]
```

### 7.5 UnaryOperator&lt;T&gt;, BinaryOperator&lt;T&gt;

입출력 타입이 동일한 Function/BiFunction의 특수화입니다.

```java
// UnaryOperator<T> extends Function<T, T>
UnaryOperator<String> trim = String::trim;
UnaryOperator<Integer> negate = x -> -x;

// List.replaceAll에서 사용
List<String> words = new ArrayList<>(Arrays.asList("  hello  ", "  world  "));
words.replaceAll(String::trim);  // ["hello", "world"]

// BinaryOperator<T> extends BiFunction<T, T, T>
BinaryOperator<Integer> add  = Integer::sum;
BinaryOperator<Integer> max  = Integer::max;

// reduce에서 사용
int sum = IntStream.rangeClosed(1, 10)
    .reduce(0, Integer::sum);  // 55
```

### 기본형 특수화 인터페이스

박싱/언박싱 오버헤드를 줄이기 위한 특수화 버전입니다. `int`, `long`, `double`을 직접 다루므로 `Integer` 객체를 생성하지 않습니다.

```java
// IntFunction<R>, LongFunction<R>, DoubleFunction<R>
IntFunction<String> intToStr = i -> String.valueOf(i);

// ToIntFunction<T>, ToLongFunction<T>, ToDoubleFunction<T>
ToIntFunction<String> strLen = String::length;

// IntUnaryOperator, LongUnaryOperator, DoubleUnaryOperator
IntUnaryOperator doubler = x -> x * 2;

// IntBinaryOperator, LongBinaryOperator, DoubleBinaryOperator
IntBinaryOperator add = (a, b) -> a + b;

// IntConsumer, LongConsumer, DoubleConsumer
IntConsumer printInt = System.out::println;

// IntSupplier, LongSupplier, DoubleSupplier
IntSupplier random = () -> (int)(Math.random() * 100);

// IntPredicate, LongPredicate, DoublePredicate
IntPredicate isPositive = x -> x > 0;
```

---

## 8. 람다 합성과 조합

> **비유:** 람다 합성은 공장의 조립 라인입니다. `trim`(세척) → `toLowerCase`(규격화) → `exclaim`(포장)처럼 각 공정을 독립된 모듈로 만들어 `andThen`으로 연결합니다. 공정 하나를 교체하거나 순서를 바꿔도 나머지 라인은 영향 없이 돌아갑니다.

### Function 합성

```java
Function<String, String> trim    = String::trim;
Function<String, String> lower   = String::toLowerCase;
Function<String, String> exclaim = s -> s + "!";

// andThen: 왼쪽 → 오른쪽
Function<String, String> normalize = trim.andThen(lower).andThen(exclaim);
normalize.apply("  Hello  ");  // "hello!"
```

### Predicate 조합

```java
Predicate<Integer> isPositive = x -> x > 0;
Predicate<Integer> isEven     = x -> x % 2 == 0;
Predicate<Integer> isSmall    = x -> x < 100;

// and — 모두 만족
Predicate<Integer> positiveEven = isPositive.and(isEven);

// or — 하나 이상 만족
Predicate<Integer> positiveOrSmall = isPositive.or(isSmall);

// negate — 부정
Predicate<Integer> isNegativeOrZero = isPositive.negate();

// 복잡한 조합
Predicate<Integer> complex = isPositive.and(isEven).and(isSmall.negate());
// 양수이고 짝수이고 100 이상인 수
```

### Consumer 체이닝

```java
Consumer<String> log    = s -> System.out.println("[LOG] " + s);
Consumer<String> audit  = s -> auditService.record(s);
Consumer<String> notify = s -> emailService.send(s);

// andThen으로 체이닝 — 순서대로 실행
Consumer<String> fullPipeline = log.andThen(audit).andThen(notify);
fullPipeline.accept("User login event");
```

---

## 9. 람다 vs 익명 클래스 차이

> **비유:** 익명 클래스는 "1인 법인 설립"입니다. 법인(클래스)을 만들고, 사무실(this)을 빌리고, 대표(필드)를 세워야 합니다. 람다는 "프리랜서 계약"입니다. 법인 없이 본인(외부 클래스의 this)이 직접 계약하고, 사무실도 빌리지 않습니다(새 스코프 없음). 그래서 가볍고 빠르지만 자체 상태(필드)를 가질 수 없습니다.

람다와 익명 클래스는 겉으로 비슷해 보이지만 `this`의 의미, 스코프, 바이트코드 구현 방식이 모두 다릅니다.

### this의 의미 차이

```java
public class ThisExample {
    private String name = "outer";

    public void demonstrate() {
        // 익명 클래스 — this는 익명 클래스 인스턴스를 가리킴
        Runnable anon = new Runnable() {
            @Override
            public void run() {
                System.out.println(this.getClass().getSimpleName());
                // 출력: ThisExample$1 (익명 클래스)
            }
        };

        // 람다 — this는 람다를 감싸는 클래스(ThisExample)를 가리킴
        Runnable lambda = () -> {
            System.out.println(this.name);
            // 출력: outer (ThisExample의 name 필드)
            // this는 ThisExample 인스턴스를 참조
        };
    }
}
```

### 새 스코프 생성 여부

```java
public void scopeExample() {
    int x = 10;

    // 익명 클래스 — 새로운 스코프 생성
    Runnable anon = new Runnable() {
        int x = 20;  // OK — 외부 x와 다른 스코프
        @Override
        public void run() {
            System.out.println(x);  // 20 (내부 x)
        }
    };

    // 람다 — 스코프 생성 안 함
    Runnable lambda = () -> {
        // int x = 20;  // 컴파일 에러: 이미 x가 정의된 스코프
        System.out.println(x);  // 10 (외부 x)
    };
}
```

---

## 10. 람다의 내부 구현 — invokedynamic과 LambdaMetafactory

> **비유:** 람다의 내부 구현은 "주문 제작 공장"입니다. 익명 클래스는 미리 제품(`.class` 파일)을 찍어놓는 대량생산 방식이고, 람다는 첫 주문(최초 실행)이 들어올 때 `LambdaMetafactory`라는 주문 제작 공장이 제품을 만들어 캐싱합니다. 두 번째 주문부터는 캐시된 제품을 재사용하므로 공장을 다시 가동할 필요가 없습니다.

### invokedynamic 동작 원리

람다는 익명 클래스처럼 별도의 `.class` 파일을 생성하지 않습니다. 대신 Java 7에서 도입된 `invokedynamic` JVM 명령어를 사용합니다. 첫 번째 호출 시 `LambdaMetafactory`가 런타임에 함수형 인터페이스 구현 클래스를 동적으로 생성하고 캐싱합니다. 이후 호출에서는 캐시된 구현을 재사용하므로 클래스 로딩 비용이 없습니다.

```mermaid
sequenceDiagram
    participant C as 컴파일러
    participant JVM as JVM(런타임)
    participant LMF as LambdaMetafactory
    C->>C: 람다 바디를 private static 메서드로 추출
    C->>C: invokedynamic 명령어 삽입
    JVM->>LMF: 최초 실행 시 LambdaMetafactory.metafactory() 호출
    LMF->>JVM: 함수형 인터페이스 구현 클래스 동적 생성
    JVM->>JVM: CallSite 캐싱
    Note over JVM: 이후 호출은 캐시된 구현 직접 사용
```

### 캡처링 람다 vs 비캡처링 람다

```java
// 비캡처링 람다 (non-capturing) — 외부 변수를 캡처하지 않음
// → 매번 동일한 인스턴스 재사용 가능 (JVM 최적화)
Runnable r1 = () -> System.out.println("hello");
Runnable r2 = () -> System.out.println("hello");
// JVM에 따라 r1 == r2일 수 있음 (동일 인스턴스)

// 캡처링 람다 (capturing) — 외부 변수를 캡처
String message = "hello";
Runnable r3 = () -> System.out.println(message);
// 캡처된 값을 저장하는 새 인스턴스 생성 필요
// r3마다 다른 인스턴스
```

### 실제 성능 영향

```java
// 주의: 루프 내에서 람다 생성 — 캡처링이면 객체 생성 발생
for (int i = 0; i < 1000000; i++) {
    int captured = i;
    Runnable r = () -> System.out.println(captured);  // 매번 새 객체
    executor.submit(r);
}

// 비캡처링으로 개선하면 재사용 가능
Runnable constant = () -> System.out.println("done");  // 재사용
for (int i = 0; i < 1000000; i++) {
    executor.submit(constant);  // 동일 객체 재사용
}
```

**실무 실수:** 캡처링 람다를 100만 번 생성하면 100만 개의 객체가 GC 압력을 만듭니다. 루프 내부에 람다가 있고 외부 변수를 캡처하고 있다면 람다를 루프 밖으로 빼거나 캡처를 제거하는 것이 좋습니다.

---

<details class="extreme-scenario-details">
<summary class="extreme-scenario-summary">
<span class="extreme-scenario-icon">🔥</span>
<span class="extreme-scenario-label">극한 시나리오 — 클릭하여 펼치기</span>
<span class="extreme-scenario-toggle"></span>
</summary>
<div class="extreme-scenario-body">

<div class="extreme-scenario-content" markdown="1">

### 시나리오 1: 이벤트 필터링 파이프라인 (100 TPS)

> **비유:** 공항 보안 검색대입니다. 1차(금속 탐지) → 2차(X-ray) → 3차(수동 검사)로 이어지는 검문을 `Predicate.and().and()`로 체이닝합니다. 각 검문 단계를 독립 모듈로 교체할 수 있습니다.

- **문제:** 실시간 로그 이벤트를 레벨·모듈·키워드 조합으로 필터링하는데, 조건이 10가지 이상이면 if-else가 수십 줄로 늘어납니다.
- **해결:** `Predicate<LogEvent>`를 리스트로 관리하고, `reduce(Predicate::and)`로 합성합니다. 런타임에 조건을 추가·제거할 수 있어 재배포 없이 필터를 변경합니다.
- **근거:** Predicate 합성은 short-circuit 평가를 지원하므로 첫 번째 조건에서 false가 나오면 나머지를 건너뜁니다.

### 시나리오 2: 대규모 Stream 파이프라인 (10K TPS)

> **비유:** 컨베이어 벨트 위의 택배 분류 센터입니다. `filter`(불량 제거) → `map`(라벨 부착) → `collect`(상자 적재)를 한 번의 순회로 처리합니다. 벨트를 여러 줄(parallelStream)로 늘리면 처리량이 배로 늘어나지만, 줄끼리 부딪히지 않도록 주의해야 합니다.

- **문제:** 초당 10,000건의 주문 데이터를 `parallelStream`으로 처리하는데, 공유 상태를 가진 람다(캡처링 람다)가 있어 경쟁 조건이 발생합니다.
- **해결:** 람다 내부에서 공유 상태를 제거하고, `Collector`의 combiner에서만 합산합니다. 불가피한 경우 `AtomicLong` 또는 `LongAdder`를 사용합니다.
- **근거:** `parallelStream`의 ForkJoinPool은 기본 스레드 수가 `Runtime.availableProcessors() - 1`이므로 CPU 바운드 작업에서만 효과적이고, I/O 바운드 람다는 오히려 느려집니다.

### 시나리오 3: 캡처링 람다 대량 생성 (100K TPS)

> **비유:** 100만 장의 사진을 찍는 것과 같습니다. 비캡처링 람다는 같은 풍경을 가리키는 포스터 한 장(재사용)이지만, 캡처링 람다는 매번 새 사진을 인화하는 것(객체 생성)입니다.

- **문제:** 루프 내에서 외부 변수를 캡처하는 람다를 100만 번 생성하면 100만 개의 객체가 Young GC를 빈번하게 유발합니다.
- **해결:** 람다를 루프 밖으로 추출하여 비캡처링으로 전환하거나, 캡처할 값을 메서드 파라미터로 전달합니다. 불가능하면 람다 대신 재사용 가능한 전략 객체를 사용합니다.
- **근거:** 비캡처링 람다는 JVM이 싱글톤 인스턴스로 최적화하므로 GC 대상이 되지 않습니다.

---
</div>
</div>
</details>

## 12. 실무에서 자주 하는 실수

### 실수 1: 람다 안에서 체크 예외를 던지려고 함

```java
// 컴파일 에러: Function의 apply()는 체크 예외를 선언하지 않음
Function<String, String> reader = path -> new String(Files.readAllBytes(Paths.get(path)));

// 해결 1: try-catch 감싸기
Function<String, String> reader = path -> {
    try { return new String(Files.readAllBytes(Paths.get(path))); }
    catch (IOException e) { throw new UncheckedIOException(e); }
};

// 해결 2: 예외를 던지는 커스텀 함수형 인터페이스 정의
@FunctionalInterface
interface ThrowingFunction<T, R> { R apply(T t) throws Exception; }
```

### 실수 2: parallelStream에서 공유 상태 변경

```java
// 위험: 여러 스레드가 동시에 results에 추가 → 데이터 유실
List<String> results = new ArrayList<>();
stream.parallel().forEach(s -> results.add(s.toUpperCase()));

// 해결: collect 사용 (스레드 안전한 합산)
List<String> results = stream.parallel()
    .map(String::toUpperCase)
    .collect(Collectors.toList());
```

### 실수 3: 람다에서 this를 잘못 사용

```java
public class Handler {
    private String name = "handler";

    public Runnable getTask() {
        return () -> System.out.println(this.name);
        // this는 Handler 인스턴스 (익명 클래스와 다름!)
    }
}
```

### 실수 4: 지나치게 긴 람다

```java
// 안티패턴: 10줄 이상의 람다는 가독성 저하
list.stream().map(item -> {
    // 15줄의 복잡한 변환 로직...
    return result;
}).collect(toList());

// 해결: 메서드 추출 후 메서드 레퍼런스 사용
list.stream().map(this::transformItem).collect(toList());
```

### 실수 5: 불필요한 람다 (메서드 레퍼런스로 대체 가능)

```java
// 불필요한 감싸기
list.forEach(s -> System.out.println(s));

// 간결하게 메서드 레퍼런스
list.forEach(System.out::println);
```

---

## 13. 면접 포인트

### Q1: 람다 표현식이란 무엇이고, 익명 클래스와 어떻게 다른가요?

**A:** 람다는 함수형 인터페이스의 인스턴스를 간결하게 표현하는 문법입니다. 익명 클래스와 세 가지 차이가 있습니다. 첫째, `this`가 외부 클래스를 가리킵니다(익명 클래스는 자신). 둘째, 새 스코프를 생성하지 않으므로 외부 변수와 이름이 충돌합니다. 셋째, 내부적으로 `invokedynamic`을 사용하므로 별도 `.class` 파일이 생성되지 않습니다.

### Q2: effectively final 제약이 있는 이유는?

**A:** 람다는 지역 변수를 값으로 복사(copy-by-value)합니다. 메서드가 끝나면 스택 변수는 사라지지만 람다는 힙에서 살아있으므로, 복사 후 원본이 변경되면 복사본과 불일치가 생깁니다. Java는 이 혼란을 방지하기 위해 캡처되는 변수의 변경 자체를 컴파일 타임에 금지합니다.

### Q3: invokedynamic과 LambdaMetafactory의 역할은?

**A:** 컴파일러는 람다 바디를 `private static` 메서드로 추출하고 `invokedynamic` 명령어를 삽입합니다. 최초 실행 시 JVM이 `LambdaMetafactory.metafactory()`를 호출해 함수형 인터페이스 구현 클래스를 동적으로 생성하고 `CallSite`에 캐싱합니다. 이후 호출은 캐시된 구현을 직접 사용하므로 익명 클래스보다 클래스 로딩 비용이 적습니다.

### Q4: 캡처링 람다와 비캡처링 람다의 성능 차이는?

**A:** 비캡처링 람다(외부 변수 미참조)는 JVM이 동일 인스턴스를 재사용할 수 있어 객체 생성이 발생하지 않습니다. 캡처링 람다는 캡처된 값을 저장하기 위해 매번 새 인스턴스를 생성하므로 GC 압력이 발생합니다. 루프 내 캡처링 람다가 성능 병목이면 루프 밖으로 추출하거나 캡처를 제거하는 것이 좋습니다.

### Q5: Function.andThen()과 compose()의 차이는?

**A:** `f.andThen(g)`는 `g(f(x))`로 왼쪽에서 오른쪽 순서로 실행합니다. `f.compose(g)`는 `f(g(x))`로 오른쪽에서 왼쪽 순서입니다. `andThen`은 파이프라인의 자연스러운 흐름을 표현할 때, `compose`는 수학적 함수 합성을 표현할 때 사용합니다.

---

## 정리 요약

```mermaid
graph TD
    A["람다 핵심 포인트"] --> B["1️⃣ 함수형 인터페이스의 인스턴스\n추상 메서드 1개인 인터페이스"]
    A --> C["2️⃣ 타입 추론\n대입 컨텍스트에서 타입 결정"]
    A --> D["3️⃣ effectively final\n캡처한 지역 변수는 변경 불가"]
    A --> E["4️⃣ this\n람다 안의 this는 감싸는 클래스를 가리킴"]
    A --> F["5️⃣ 메서드 레퍼런스\n이름 있는 메서드를 람다로 참조"]
    A --> G["6️⃣ java.util.function\n43개의 표준 함수형 인터페이스"]
    A --> H["7️⃣ 내부 구현\ninvokedynamic + LambdaMetafactory"]
    A --> I["8️⃣ 성능\n비캡처링 람다는 재사용 최적화 가능"]
```
