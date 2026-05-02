---
title: "Java 함수형 프로그래밍"
categories:
- JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

Java는 본래 순수 객체지향 언어지만, Java 8부터 람다와 Stream API를 통해 함수형 프로그래밍 패러다임을 적극 수용했습니다. 함수형 프로그래밍의 핵심 개념을 이해하고 Java에서 어떻게 적용하는지 깊이 있게 살펴봅니다.

> **비유로 이해하기**: 함수형 프로그래밍은 레시피와 같습니다. 명령형은 "팬을 달구고, 기름을 두르고, 재료를 넣고, 3분 동안 볶아라"처럼 과정을 단계별로 기술합니다. 함수형은 "이 재료들로 볶음 요리를 만들어라"처럼 목표만 선언합니다. 순수 함수는 "같은 재료 → 항상 같은 맛"이고, 불변성은 "원재료를 절대 변형하지 않고 새 요리를 만드는 것"입니다. 이 두 원칙이 지켜지면 요리를 병렬로 진행해도(병렬 스트림) 서로 간섭이 없습니다.

## 1. 함수형 프로그래밍이란?

### 선언적 vs 명령형

프로그래밍 패러다임의 두 축은 **명령형(Imperative)** 과 **선언적(Declarative)** 입니다.

<div class="mermaid">
graph LR
  subgraph "명령형 — 어떻게(How)"
    A["for (int i = 0; ...)"] --> B["if (조건) {"]
    B --> C["result.add(...)"]
  end
  subgraph "선언적(함수형) — 무엇을(What)"
    D["list.stream()"] --> E[".filter(조건)"]
    E --> F[".map(변환)"]
    F --> G[".collect(결과)"]
  end
</div>

```java
// 명령형 스타일 — 상태 변경, 반복 제어, 단계적 기술
public List<String> getExpensiveProductNames(List<Product> products) {
    List<String> result = new ArrayList<>();
    for (Product p : products) {
        if (p.getPrice() > 10000) {
            result.add(p.getName().toUpperCase());
        }
    }
    Collections.sort(result);
    return result;
}

// 선언적(함수형) 스타일 — 무엇을 할지만 기술, 어떻게는 라이브러리에 위임
public List<String> getExpensiveProductNames(List<Product> products) {
    return products.stream()
        .filter(p -> p.getPrice() > 10000)
        .map(p -> p.getName().toUpperCase())
        .sorted()
        .collect(Collectors.toList());
}
```

### 함수형 프로그래밍의 핵심 원칙

```
1. 순수 함수 (Pure Functions)
   - 같은 입력 → 항상 같은 출력
   - 부수효과(side effect) 없음

2. 불변성 (Immutability)
   - 데이터는 변경하지 않고 새 데이터를 만든다

3. 함수를 일급 시민으로 (First-Class Functions)
   - 함수를 값처럼 전달하고 반환할 수 있다

4. 참조 투명성 (Referential Transparency)
   - 표현식을 그 결과값으로 대체해도 프로그램 동작이 변하지 않음

5. 선언적 스타일
   - 제어 흐름보다 데이터 변환에 집중
```

---

## 2. 순수 함수 (Pure Function)

### 정의

순수 함수는 두 가지 조건을 만족합니다.
1. **동일 입력 → 동일 출력** (결정론적)
2. **부수효과 없음** (외부 상태를 읽거나 변경하지 않음)

```java
// 순수 함수 예시
public static int add(int a, int b) {
    return a + b;  // 항상 a+b, 외부 상태 없음
}

public static String toUpperCase(String s) {
    return s.toUpperCase();  // 항상 동일 결과, 외부 영향 없음
}

public static List<Integer> doubled(List<Integer> list) {
    return list.stream()
        .map(n -> n * 2)
        .collect(Collectors.toList());  // 새 리스트 반환, 원본 변경 없음
}
```

### 불순 함수(Impure Function)의 예

```java
// 불순 함수 1 — 외부 상태에 의존
private int multiplier = 2;
public int scale(int x) {
    return x * multiplier;  // multiplier가 바뀌면 결과도 달라짐 → 비결정론적
}

// 불순 함수 2 — 부수효과(외부 상태 변경)
private List<String> log = new ArrayList<>();
public String process(String input) {
    log.add(input);  // 외부 상태(log) 변경 → 부수효과!
    return input.toUpperCase();
}

// 불순 함수 3 — I/O (부수효과)
public String getCurrentUser() {
    return System.getProperty("user.name");  // 환경에 따라 결과 다름
}

// 불순 함수 4 — 예외 발생 가능 (부수효과)
public int divide(int a, int b) {
    return a / b;  // b=0이면 예외 — 순수하지 않음
}
```

### 참조 투명성 (Referential Transparency)

```java
// 참조 투명한 코드
int x = add(2, 3);       // add(2, 3)은 항상 5
int y = add(2, 3) + 1;   // 5 + 1 = 6
// → add(2, 3)을 5로 대체해도 프로그램 동작 동일

// 참조 투명하지 않은 코드
int counter = 0;
public int increment() { return ++counter; }  // 호출마다 다른 값
int a = increment();  // 1
int b = increment();  // 2
// → increment()를 1로 대체하면 동작이 달라짐 → 참조 투명성 깨짐
```

### 순수 함수의 이점

순수 함수가 왜 중요한지 네 가지 핵심 이점을 이해해야 합니다.

**테스트 용이성**: 순수 함수는 입력만 주면 항상 같은 출력이 나오므로, Mock 객체나 외부 환경 설정 없이 단위 테스트를 작성할 수 있습니다. `add(2, 3) == 5`가 항상 성립합니다.

**병렬화 안전**: 공유 상태가 없으므로 여러 스레드가 동시에 같은 함수를 실행해도 경쟁 조건(race condition)이 발생하지 않습니다. `parallelStream()`에서 람다를 안전하게 사용하려면 람다가 순수 함수여야 합니다.

**메모이제이션**: 동일 입력에 항상 동일 출력이 보장되므로 결과를 캐시할 수 있습니다. 비용이 큰 계산 함수에 `ConcurrentHashMap`으로 캐시를 추가하면 중복 계산을 완전히 제거할 수 있습니다.

**추론 용이**: 코드 전체를 읽지 않아도 함수 시그니처와 입출력만으로 동작을 완전히 이해할 수 있습니다. 리팩토링 시 다른 코드에 미치는 영향을 예측하기 쉽습니다.

---

## 3. 불변성 (Immutability)

### 불변 객체 설계

```java
// 가변 객체 — 위험
public class MutablePoint {
    public int x, y;

    public void move(int dx, int dy) {
        this.x += dx;  // 원본 변경!
        this.y += dy;
    }
}

// 불변 객체 — 안전
public final class ImmutablePoint {
    private final int x;
    private final int y;

    public ImmutablePoint(int x, int y) {
        this.x = x;
        this.y = y;
    }

    // 상태 변경 대신 새 객체 반환
    public ImmutablePoint move(int dx, int dy) {
        return new ImmutablePoint(this.x + dx, this.y + dy);  // 새 객체
    }

    public int getX() { return x; }
    public int getY() { return y; }

    @Override
    public String toString() {
        return "Point(" + x + ", " + y + ")";
    }
}

// 사용
ImmutablePoint p1 = new ImmutablePoint(0, 0);
ImmutablePoint p2 = p1.move(3, 4);  // p1은 그대로, p2가 새 상태
System.out.println(p1);  // Point(0, 0)
System.out.println(p2);  // Point(3, 4)
```

### record — Java 16+의 불변 데이터 클래스

```java
// record는 불변성을 언어 차원에서 지원
public record Point(int x, int y) {
    // 자동 생성: final 필드, 생성자, getter, equals, hashCode, toString

    // 컴팩트 생성자 — 검증 추가 가능
    public Point {
        if (x < 0 || y < 0) throw new IllegalArgumentException("음수 좌표 불가");
    }

    // 인스턴스 메서드 — 새 record 반환
    public Point move(int dx, int dy) {
        return new Point(x + dx, y + dy);
    }

    // 정적 팩토리
    public static Point origin() {
        return new Point(0, 0);
    }
}

// record 사용
Point p1 = new Point(1, 2);
Point p2 = p1.move(3, 4);  // Point[x=4, y=6]

System.out.println(p1.x());  // 1 (accessor, not getter)
System.out.println(p1);      // Point[x=1, y=2]
```

### 불변 컬렉션

```java
// Java 9+ — List.of, Set.of, Map.of → 불변 컬렉션
List<String> immutableList = List.of("a", "b", "c");
// immutableList.add("d");  // UnsupportedOperationException

Set<Integer> immutableSet = Set.of(1, 2, 3);
Map<String, Integer> immutableMap = Map.of("one", 1, "two", 2);

// 불변 컬렉션에서 변경이 필요할 때 — 새 컬렉션 생성
List<String> added = Stream.concat(immutableList.stream(), Stream.of("d"))
    .collect(Collectors.toList());

// Collections.unmodifiable* — 기존 컬렉션을 불변 뷰로 감쌈 (원본 수정은 가능)
List<String> mutable = new ArrayList<>(Arrays.asList("a", "b"));
List<String> view = Collections.unmodifiableList(mutable);
// view.add("c");    // UnsupportedOperationException
mutable.add("c");  // 원본 수정은 가능 → view도 변경됨 (진정한 불변 아님)

// 진정한 불변 — List.copyOf (Java 10+)
List<String> trulyCopy = List.copyOf(mutable);  // 독립 복사본 + 불변
```

### 방어적 복사

```java
// 가변 필드가 있다면 방어적 복사로 불변성 보장
public final class Portfolio {
    private final List<String> stocks;

    public Portfolio(List<String> stocks) {
        this.stocks = List.copyOf(stocks);  // 방어적 복사 — 원본 변경으로부터 보호
    }

    public List<String> getStocks() {
        return List.copyOf(stocks);  // 반환 시도 방어적 복사
        // 또는 return Collections.unmodifiableList(stocks);
    }
}
```

---

## 4. 고차 함수 (Higher-Order Function)

고차 함수는 **함수를 파라미터로 받거나**, **함수를 반환하는** 함수입니다.

### 함수를 파라미터로 받기

```java
// filter는 Predicate(함수)를 파라미터로 받는 고차 함수
public static <T> List<T> filter(List<T> list, Predicate<T> predicate) {
    return list.stream()
        .filter(predicate)
        .collect(Collectors.toList());
}

// map은 Function(함수)를 파라미터로 받는 고차 함수
public static <T, R> List<R> map(List<T> list, Function<T, R> mapper) {
    return list.stream()
        .map(mapper)
        .collect(Collectors.toList());
}

// 사용
List<Integer> numbers = Arrays.asList(1, 2, 3, 4, 5, 6);
List<Integer> evens   = filter(numbers, n -> n % 2 == 0);   // [2, 4, 6]
List<String>  strings = map(numbers, Object::toString);     // ["1", "2", ...]
```

### 함수를 반환하기

```java
// 함수를 반환하는 고차 함수 — 동적으로 함수 생성
public static Predicate<Integer> greaterThan(int threshold) {
    return n -> n > threshold;  // 클로저: threshold 캡처
}

Predicate<Integer> gt5  = greaterThan(5);
Predicate<Integer> gt10 = greaterThan(10);

List<Integer> nums = Arrays.asList(3, 7, 12, 15, 2);
List<Integer> result1 = nums.stream().filter(gt5).collect(Collectors.toList());  // [7, 12, 15]
List<Integer> result2 = nums.stream().filter(gt10).collect(Collectors.toList()); // [12, 15]

// 검증 함수 팩토리
public static Predicate<String> hasMinLength(int min) {
    return s -> s != null && s.length() >= min;
}

public static Predicate<String> matchesPattern(String regex) {
    Pattern pattern = Pattern.compile(regex);  // 한 번만 컴파일
    return s -> pattern.matcher(s).matches();
}

Predicate<String> validEmail = hasMinLength(5).and(matchesPattern(".*@.*\\..*"));
```

---

## 5. 커링 (Currying)

커링은 여러 파라미터를 받는 함수를 **파라미터 하나씩 받는 함수들의 체인**으로 변환하는 기법입니다.

```
f(a, b, c) → f(a)(b)(c)
```

### Java에서의 커링 구현

```java
// 일반 함수 (비커링)
BiFunction<Integer, Integer, Integer> add = (a, b) -> a + b;
int result = add.apply(3, 5);  // 8

// 커링된 함수
Function<Integer, Function<Integer, Integer>> curriedAdd = a -> b -> a + b;
Function<Integer, Integer> add3 = curriedAdd.apply(3);  // a=3 고정
int result2 = add3.apply(5);    // 8
int result3 = add3.apply(10);   // 13

// 3항 커링
Function<Integer, Function<Integer, Function<Integer, Integer>>> curriedSum =
    a -> b -> c -> a + b + c;

int sum = curriedSum.apply(1).apply(2).apply(3);  // 6

// 실용 예 — 로거 커링
Function<String, Function<String, String>> logger =
    level -> message -> String.format("[%s] %s", level, message);

Function<String, String> infoLogger  = logger.apply("INFO");
Function<String, String> errorLogger = logger.apply("ERROR");

System.out.println(infoLogger.apply("서버 시작"));    // [INFO] 서버 시작
System.out.println(errorLogger.apply("연결 실패"));  // [ERROR] 연결 실패
```

### 커링 유틸리티

```java
// BiFunction을 커링된 Function으로 변환하는 유틸리티
public static <A, B, R> Function<A, Function<B, R>> curry(BiFunction<A, B, R> f) {
    return a -> b -> f.apply(a, b);
}

// 커링 해제 — curried Function을 BiFunction으로 변환
public static <A, B, R> BiFunction<A, B, R> uncurry(Function<A, Function<B, R>> f) {
    return (a, b) -> f.apply(a).apply(b);
}

// 사용
BiFunction<String, String, String> concat = String::concat;
Function<String, Function<String, String>> curriedConcat = curry(concat);

Function<String, String> helloPrefix = curriedConcat.apply("Hello, ");
System.out.println(helloPrefix.apply("World"));  // Hello, World
System.out.println(helloPrefix.apply("Java"));   // Hello, Java
```

### 부분 적용 (Partial Application)

커링과 유사하지만 여러 파라미터 중 일부만 미리 적용합니다.

```java
// 부분 적용 유틸리티
public static <A, B, R> Function<B, R> partial(BiFunction<A, B, R> f, A a) {
    return b -> f.apply(a, b);
}

BiFunction<Integer, Integer, Integer> multiply = (a, b) -> a * b;
Function<Integer, Integer> triple = partial(multiply, 3);
Function<Integer, Integer> double_ = partial(multiply, 2);

System.out.println(triple.apply(5));   // 15
System.out.println(double_.apply(7));  // 14
```

---

## 6. 합성 (Composition)

함수 합성은 작은 함수들을 조합하여 더 복잡한 함수를 만드는 기법입니다.

```
수학적 표기: (g ∘ f)(x) = g(f(x))
Java: f.andThen(g)  또는  g.compose(f)
```

```java
// Function.andThen — f 후 g 실행
Function<String, String> trim    = String::trim;
Function<String, String> lower   = String::toLowerCase;
Function<String, String> exclaim = s -> s + "!";

// andThen: 왼쪽에서 오른쪽으로
Function<String, String> normalize = trim.andThen(lower).andThen(exclaim);
System.out.println(normalize.apply("  HELLO  "));  // "hello!"

// compose: 오른쪽에서 왼쪽으로 (수학적 순서)
Function<String, String> normalize2 = exclaim.compose(lower).compose(trim);
// trim → lower → exclaim (compose 역순)
System.out.println(normalize2.apply("  HELLO  "));  // "hello!"
```

### 함수 파이프라인 구성

```java
// 데이터 변환 파이프라인을 함수 합성으로 구성
public class Pipeline<T> {
    private final Function<T, T> function;

    private Pipeline(Function<T, T> function) {
        this.function = function;
    }

    public static <T> Pipeline<T> of(Function<T, T> function) {
        return new Pipeline<>(function);
    }

    public Pipeline<T> then(Function<T, T> next) {
        return new Pipeline<>(this.function.andThen(next));
    }

    public T apply(T input) {
        return function.apply(input);
    }
}

// 사용
Pipeline<String> textPipeline = Pipeline.of(String::trim)
    .then(String::toLowerCase)
    .then(s -> s.replaceAll("\\s+", "-"))
    .then(s -> s.replaceAll("[^a-z0-9-]", ""));

String slug = textPipeline.apply("  Hello World! Java 8  ");
System.out.println(slug);  // "hello-world-java-8"
```

### Predicate 합성

```java
// 복잡한 조건을 작은 Predicate 합성으로 표현
Predicate<String> notNull    = s -> s != null;
Predicate<String> notEmpty   = s -> !s.isEmpty();
Predicate<String> notBlank   = s -> !s.isBlank();
Predicate<String> maxLen100  = s -> s.length() <= 100;
Predicate<String> noScript   = s -> !s.contains("<script");

Predicate<String> validInput = notNull
    .and(notEmpty)
    .and(notBlank)
    .and(maxLen100)
    .and(noScript);

boolean isValid = validInput.test("Hello, World!");  // true
```

---

## 7. 모나드 패턴 — Optional이 모나드인 이유

### 모나드란?

모나드(Monad)는 함수형 프로그래밍의 핵심 패턴으로, **값을 컨텍스트에 감싸고(wrap)** 그 컨텍스트를 유지하면서 **변환(map)과 평탄화(flatMap)를 지원**하는 구조입니다.

```
모나드의 3가지 핵심 요소:
1. 타입 생성자: M<T> (예: Optional<T>)
2. unit (return): T → M<T>  (예: Optional.of(value))
3. bind (flatMap): M<T> → (T → M<U>) → M<U>

모나드 법칙:
1. 왼쪽 항등원: unit(a).flatMap(f) == f(a)
2. 오른쪽 항등원: m.flatMap(unit) == m
3. 결합법칙: m.flatMap(f).flatMap(g) == m.flatMap(x -> f(x).flatMap(g))
```

### Optional이 모나드인 이유

```java
// Optional은 "null일 수도 있다"는 컨텍스트를 감싸는 모나드

// 1. unit — 값을 컨텍스트에 감쌈
Optional<String> wrapped = Optional.of("hello");

// 2. map — 컨텍스트 유지하며 변환
Optional<Integer> length = wrapped.map(String::length);  // Optional[5]

// 3. flatMap — 중첩 Optional 방지 (모나드의 bind)
Optional<String> name = Optional.of("Alice");
Optional<String> result = name.flatMap(n -> findUserByName(n))  // Optional<User>
                              .flatMap(user -> findAddressByUser(user))  // Optional<Address>
                              .map(Address::getCity);  // Optional<String>

// flatMap이 없다면 — 중첩 Optional 문제
Optional<Optional<User>> nested = name.map(n -> findUserByName(n));  // 중첩!
// flatMap이 자동으로 평탄화함

// 모나드 법칙 확인
// 왼쪽 항등원: Optional.of(x).flatMap(f) == f(x)
Function<String, Optional<Integer>> parseLength = s -> Optional.of(s.length());
Optional<Integer> left = Optional.of("hello").flatMap(parseLength);  // Optional[5]
Optional<Integer> fx   = parseLength.apply("hello");                 // Optional[5]
// left.equals(fx) == true

// 오른쪽 항등원: opt.flatMap(Optional::of) == opt
Optional<String> m = Optional.of("test");
Optional<String> right = m.flatMap(Optional::of);  // Optional["test"]
// m.equals(right) == true
```

### 다른 모나드 패턴

```java
// Stream도 모나드: flatMap이 핵심
Stream<Integer> monad = Stream.of("hello", "world")
    .flatMap(s -> s.chars().boxed());  // 각 문자를 스트림으로 변환 후 평탄화

// CompletableFuture도 모나드: thenCompose가 flatMap 역할
CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> "hello")
    .thenCompose(s -> CompletableFuture.supplyAsync(s::toUpperCase));
```

---

## 8. 함수형 에러 처리

### Optional — null 대신 사용

```java
// null 반환 대신 Optional 반환
public Optional<User> findUserById(long id) {
    return Optional.ofNullable(userRepository.findById(id));
}

// 체이닝으로 null 체크 없이 처리
String city = findUserById(42L)
    .map(User::getAddress)
    .map(Address::getCity)
    .orElse("Unknown City");

// 예외 대신 Optional
public Optional<Integer> parseInteger(String s) {
    try {
        return Optional.of(Integer.parseInt(s));
    } catch (NumberFormatException e) {
        return Optional.empty();
    }
}
```

### Either 패턴 — 성공/실패를 타입으로 표현

Java 표준 라이브러리에는 Either가 없지만, 직접 구현할 수 있습니다.

```java
// Either<L, R>: 왼쪽(Left)은 실패, 오른쪽(Right)은 성공
public sealed interface Either<L, R> permits Either.Left, Either.Right {

    record Left<L, R>(L value) implements Either<L, R> {}
    record Right<L, R>(R value) implements Either<L, R> {}

    static <L, R> Either<L, R> left(L value)  { return new Left<>(value); }
    static <L, R> Either<L, R> right(R value) { return new Right<>(value); }

    boolean isRight();
    boolean isLeft();

    <U> Either<L, U> map(Function<R, U> mapper);
    <U> Either<L, U> flatMap(Function<R, Either<L, U>> mapper);

    R getOrElse(R defaultValue);
    R getOrElseGet(Supplier<R> supplier);

    // 패턴 매칭으로 처리
    <U> U fold(Function<L, U> leftMapper, Function<R, U> rightMapper);
}

// 기본 구현
public sealed interface Either<L, R> permits Left, Right {

    static <L, R> Either<L, R> left(L value)  { return new Left<>(value); }
    static <L, R> Either<L, R> right(R value) { return new Right<>(value); }

    default boolean isRight() { return this instanceof Right; }
    default boolean isLeft()  { return this instanceof Left; }

    @SuppressWarnings("unchecked")
    default <U> Either<L, U> map(Function<R, U> mapper) {
        return isRight()
            ? Either.right(mapper.apply(((Right<L, R>) this).value()))
            : (Either<L, U>) this;
    }

    @SuppressWarnings("unchecked")
    default <U> Either<L, U> flatMap(Function<R, Either<L, U>> mapper) {
        return isRight()
            ? mapper.apply(((Right<L, R>) this).value())
            : (Either<L, U>) this;
    }

    default R getOrElse(R defaultValue) {
        return isRight() ? ((Right<L, R>) this).value() : defaultValue;
    }

    default <U> U fold(Function<L, U> leftMapper, Function<R, U> rightMapper) {
        return isRight()
            ? rightMapper.apply(((Right<L, R>) this).value())
            : leftMapper.apply(((Left<L, R>) this).value());
    }
}

record Left<L, R>(L value) implements Either<L, R> {}
record Right<L, R>(R value) implements Either<L, R> {}

// 사용 예
public Either<String, Integer> divide(int a, int b) {
    if (b == 0) return Either.left("Division by zero");
    return Either.right(a / b);
}

Either<String, Integer> result = divide(10, 2)
    .map(n -> n * 3)
    .flatMap(n -> n > 10 ? Either.right(n) : Either.left("Too small"));

String output = result.fold(
    error -> "Error: " + error,
    value -> "Result: " + value
);
System.out.println(output);  // Result: 15
```

### Try 패턴 — 예외를 값으로 처리

```java
// Try<T>: 성공(Success) 또는 실패(Failure)
public sealed interface Try<T> permits Try.Success, Try.Failure {

    static <T> Try<T> of(Supplier<T> supplier) {
        try {
            return new Success<>(supplier.get());
        } catch (Exception e) {
            return new Failure<>(e);
        }
    }

    boolean isSuccess();
    T get() throws Exception;
    T getOrElse(T defaultValue);
    <U> Try<U> map(Function<T, U> mapper);
    <U> Try<U> flatMap(Function<T, Try<U>> mapper);
    Try<T> recover(Function<Exception, T> recovery);

    record Success<T>(T value) implements Try<T> {
        public boolean isSuccess() { return true; }
        public T get() { return value; }
        public T getOrElse(T defaultValue) { return value; }
        public <U> Try<U> map(Function<T, U> mapper) { return Try.of(() -> mapper.apply(value)); }
        public <U> Try<U> flatMap(Function<T, Try<U>> mapper) { return mapper.apply(value); }
        public Try<T> recover(Function<Exception, T> recovery) { return this; }
    }

    record Failure<T>(Exception exception) implements Try<T> {
        public boolean isSuccess() { return false; }
        public T get() throws Exception { throw exception; }
        public T getOrElse(T defaultValue) { return defaultValue; }
        @SuppressWarnings("unchecked")
        public <U> Try<U> map(Function<T, U> mapper) { return (Try<U>) this; }
        @SuppressWarnings("unchecked")
        public <U> Try<U> flatMap(Function<T, Try<U>> mapper) { return (Try<U>) this; }
        public Try<T> recover(Function<Exception, T> recovery) {
            return Try.of(() -> recovery.apply(exception));
        }
    }
}

// 사용
Try<Integer> result = Try.of(() -> Integer.parseInt("123"))
    .map(n -> n * 2)
    .flatMap(n -> Try.of(() -> 100 / n));

int value = result.getOrElse(0);  // 0 (안전하게 기본값 반환)

// 예외 복구
Try<Integer> recovered = Try.of(() -> Integer.parseInt("not-a-number"))
    .recover(e -> -1);  // 파싱 실패 시 -1 반환

System.out.println(recovered.getOrElse(0));  // -1
```

---

## 9. 재귀 vs 꼬리 재귀 (Java의 한계)

### 일반 재귀

```java
// 일반 재귀 — 스택 프레임 쌓임
public static long factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);  // 재귀 호출 후 곱셈 수행 필요 → 스택 프레임 유지
}

// factorial(5) 호출 스택:
// factorial(5) → 5 * factorial(4)
//                    factorial(4) → 4 * factorial(3)
//                                       factorial(3) → 3 * factorial(2)
//                                                          factorial(2) → 2 * factorial(1)
//                                                                             factorial(1) = 1
// 스택 깊이 = n → 큰 n에서 StackOverflowError
```

### 꼬리 재귀 (Tail Recursion)

재귀 호출이 함수의 **마지막 연산**이면 꼬리 재귀입니다. 꼬리 재귀는 이론적으로 스택 없이 루프로 최적화(TCO: Tail Call Optimization) 가능합니다.

```java
// 꼬리 재귀 스타일 — 누적자(accumulator) 사용
public static long factorialTail(int n, long acc) {
    if (n <= 1) return acc;
    return factorialTail(n - 1, n * acc);  // 재귀 호출이 마지막 연산
}

public static long factorial(int n) {
    return factorialTail(n, 1);
}

// factorialTail(5, 1) 스택 (이상적 TCO라면):
// factorialTail(5, 1) → factorialTail(4, 5)
// factorialTail(4, 5) → factorialTail(3, 20)
// factorialTail(3, 20) → factorialTail(2, 60)
// factorialTail(2, 60) → factorialTail(1, 120)
// factorialTail(1, 120) → 120
```

### Java의 한계 — TCO 미지원

```java
// Java는 꼬리 재귀 최적화(TCO)를 JVM 수준에서 지원하지 않음
// → 꼬리 재귀도 스택 오버플로우 발생 가능

// 대안 1: 반복문으로 직접 변환 (가장 실용적)
public static long factorialIterative(int n) {
    long result = 1;
    for (int i = 2; i <= n; i++) {
        result *= i;
    }
    return result;
}

// 대안 2: 트램폴린(Trampoline) 패턴 — 스택 없는 재귀 시뮬레이션
@FunctionalInterface
interface Trampoline<T> {
    T get();

    default boolean isComplete() { return true; }

    default T run() {
        Trampoline<T> step = this;
        while (!step.isComplete()) {
            step = ((ThunkTrampoline<T>) step).next();
        }
        return step.get();
    }

    static <T> Trampoline<T> done(T value) {
        return () -> value;
    }

    static <T> Trampoline<T> more(Supplier<Trampoline<T>> next) {
        return new ThunkTrampoline<>(next);
    }
}

class ThunkTrampoline<T> implements Trampoline<T> {
    private final Supplier<Trampoline<T>> thunk;

    ThunkTrampoline(Supplier<Trampoline<T>> thunk) { this.thunk = thunk; }

    @Override public T get() { return run(); }
    @Override public boolean isComplete() { return false; }
    public Trampoline<T> next() { return thunk.get(); }
}

// 트램폴린으로 스택 오버플로우 없이 재귀
public static Trampoline<Long> factorialTrampoline(int n, long acc) {
    if (n <= 1) return Trampoline.done(acc);
    return Trampoline.more(() -> factorialTrampoline(n - 1, n * acc));
}

long result = factorialTrampoline(100000, 1).run();  // StackOverflow 없음
```

---

## 10. 실무에서의 함수형 스타일

### 10.1 Stream + 람다 조합 패턴

```java
// 데이터 집계 — 부서별 평균 급여
record Employee(String name, String department, int salary) {}

List<Employee> employees = List.of(
    new Employee("Alice", "Engineering", 8000000),
    new Employee("Bob", "Engineering", 7000000),
    new Employee("Charlie", "Marketing", 6000000),
    new Employee("Dave", "Marketing", 5500000),
    new Employee("Eve", "Engineering", 9000000)
);

Map<String, Double> avgSalaryByDept = employees.stream()
    .collect(Collectors.groupingBy(
        Employee::department,
        Collectors.averagingInt(Employee::salary)
    ));
// {Engineering=8000000.0, Marketing=5750000.0}

// 최고 연봉자 찾기
Optional<Employee> topEarner = employees.stream()
    .max(Comparator.comparingInt(Employee::salary));

// 부서별 직원 수 및 총 급여
Map<String, IntSummaryStatistics> statsByDept = employees.stream()
    .collect(Collectors.groupingBy(
        Employee::department,
        Collectors.summarizingInt(Employee::salary)
    ));
```

### 10.2 전략 패턴을 람다로 대체

```java
// 전통적인 전략 패턴 — 인터페이스 + 구현 클래스들
interface SortStrategy {
    List<Integer> sort(List<Integer> list);
}

class AscendingSort implements SortStrategy {
    @Override
    public List<Integer> sort(List<Integer> list) {
        return list.stream().sorted().collect(Collectors.toList());
    }
}

class DescendingSort implements SortStrategy {
    @Override
    public List<Integer> sort(List<Integer> list) {
        return list.stream().sorted(Comparator.reverseOrder()).collect(Collectors.toList());
    }
}

// 람다로 대체 — 구현 클래스 불필요
UnaryOperator<List<Integer>> ascendingSort =
    list -> list.stream().sorted().collect(Collectors.toList());

UnaryOperator<List<Integer>> descendingSort =
    list -> list.stream().sorted(Comparator.reverseOrder()).collect(Collectors.toList());

// 런타임에 전략 선택
public List<Integer> processNumbers(List<Integer> numbers, UnaryOperator<List<Integer>> strategy) {
    return strategy.apply(numbers);
}

List<Integer> nums = Arrays.asList(3, 1, 4, 1, 5, 9, 2, 6);
List<Integer> asc  = processNumbers(nums, ascendingSort);
List<Integer> desc = processNumbers(nums, descendingSort);
```

### 10.3 팩토리 패턴을 Supplier로 대체

```java
// 전통적인 팩토리 패턴
interface ConnectionFactory {
    Connection createConnection();
}

class MySQLConnectionFactory implements ConnectionFactory {
    @Override
    public Connection createConnection() {
        return new MySQLConnection(host, port, db);
    }
}

// Supplier로 대체
Supplier<Connection> mysqlFactory  = () -> new MySQLConnection(host, port, db);
Supplier<Connection> postgresFactory = () -> new PostgresConnection(host, port, db);
Supplier<Connection> mockFactory   = () -> new MockConnection();

// 의존성 주입
class Repository {
    private final Supplier<Connection> connectionFactory;

    public Repository(Supplier<Connection> connectionFactory) {
        this.connectionFactory = connectionFactory;
    }

    public void query(String sql) {
        try (Connection conn = connectionFactory.get()) {
            // 쿼리 실행
        }
    }
}

// 테스트에서 교체
Repository prodRepo = new Repository(mysqlFactory);
Repository testRepo = new Repository(mockFactory);  // 간단히 교체
```

### 10.4 템플릿 메서드를 Function/Consumer로 대체

```java
// 전통적인 템플릿 메서드 패턴 — 상속 기반
abstract class DataProcessor {
    // 템플릿 메서드
    public final void process() {
        List<String> data = loadData();
        List<String> processed = transform(data);
        saveData(processed);
    }

    protected abstract List<String> loadData();
    protected abstract List<String> transform(List<String> data);
    protected abstract void saveData(List<String> data);
}

class UpperCaseProcessor extends DataProcessor {
    @Override protected List<String> loadData() { return fileService.load(); }
    @Override protected List<String> transform(List<String> data) {
        return data.stream().map(String::toUpperCase).collect(Collectors.toList());
    }
    @Override protected void saveData(List<String> data) { fileService.save(data); }
}

// 함수형으로 대체 — 상속 없이 컴포지션으로
public class DataProcessor {
    private final Supplier<List<String>> loader;
    private final UnaryOperator<List<String>> transformer;
    private final Consumer<List<String>> saver;

    public DataProcessor(
        Supplier<List<String>> loader,
        UnaryOperator<List<String>> transformer,
        Consumer<List<String>> saver
    ) {
        this.loader = loader;
        this.transformer = transformer;
        this.saver = saver;
    }

    public void process() {
        List<String> data = loader.get();
        List<String> processed = transformer.apply(data);
        saver.accept(processed);
    }
}

// 사용 — 구성 방식으로 다양한 조합
DataProcessor upperCase = new DataProcessor(
    fileService::load,
    data -> data.stream().map(String::toUpperCase).collect(Collectors.toList()),
    fileService::save
);

DataProcessor filtered = new DataProcessor(
    dbService::fetch,
    data -> data.stream().filter(s -> !s.isEmpty()).collect(Collectors.toList()),
    dbService::store
);
```

### 10.5 데코레이터 패턴을 함수 합성으로

```java
// 전통적 데코레이터는 클래스 계층 필요
// 함수 합성으로 간결하게 표현

Function<String, String> baseProcessor = s -> s.trim().toLowerCase();

// 데코레이터 함수들
Function<Function<String, String>, Function<String, String>> withLogging =
    fn -> s -> {
        System.out.println("입력: " + s);
        String result = fn.apply(s);
        System.out.println("출력: " + result);
        return result;
    };

Function<Function<String, String>, Function<String, String>> withTiming =
    fn -> s -> {
        long start = System.currentTimeMillis();
        String result = fn.apply(s);
        System.out.println("처리시간: " + (System.currentTimeMillis() - start) + "ms");
        return result;
    };

// 데코레이터 적용
Function<String, String> loggedProcessor = withLogging.apply(baseProcessor);
Function<String, String> timedAndLogged  = withTiming.apply(withLogging.apply(baseProcessor));
```

---

## 11. 객체지향 vs 함수형 — 어떻게 조화시킬 것인가

### 두 패러다임의 특성

<div class="mermaid">
graph LR
    subgraph "객체지향 프로그래밍 (OOP)"
        O1["데이터 + 동작 = 객체"]
        O2["상태 변경 허용"]
        O3["상속으로 재사용"]
        O4["명령형 스타일"]
        O5["캡슐화로 복잡도 관리"]
        O6["is-a 관계"]
    end
    subgraph "함수형 프로그래밍 (FP)"
        F1["데이터와 함수는 분리"]
        F2["불변 데이터 선호"]
        F3["합성으로 재사용"]
        F4["선언적 스타일"]
        F5["순수 함수로 복잡도 관리"]
        F6["변환 파이프라인"]
    end
</div>

### Java에서의 조화 전략

```java
// 전략 1: 도메인 모델은 OOP, 처리 로직은 FP
// 도메인 객체 — OOP로 캡슐화
public class Order {
    private final String id;
    private final List<OrderItem> items;
    private OrderStatus status;

    // 도메인 로직은 객체 안에
    public boolean canCancel() {
        return status == OrderStatus.PENDING;
    }

    public Order cancel() {
        if (!canCancel()) throw new IllegalStateException("취소 불가");
        return new Order(id, items, OrderStatus.CANCELLED);
    }
}

// 처리 로직 — FP로 파이프라인
List<Order> orders = orderRepository.findAll();

Map<OrderStatus, Long> statusCount = orders.stream()
    .collect(Collectors.groupingBy(Order::getStatus, Collectors.counting()));

List<Order> cancellable = orders.stream()
    .filter(Order::canCancel)
    .collect(Collectors.toList());

// 전략 2: 인터페이스로 함수형 인터페이스 활용 — 하이브리드
@FunctionalInterface
interface OrderFilter {
    boolean test(Order order);

    default OrderFilter and(OrderFilter other) {
        return order -> this.test(order) && other.test(order);
    }

    static OrderFilter byStatus(OrderStatus status) {
        return order -> order.getStatus() == status;
    }
}

OrderFilter filter = OrderFilter.byStatus(OrderStatus.PENDING)
    .and(order -> order.getTotalAmount() > 100000);

List<Order> filtered = orders.stream()
    .filter(filter::test)
    .collect(Collectors.toList());
```

### 함수형 스타일 적용 가이드라인

함수형과 OOP 스타일은 배타적 관계가 아니라 상호 보완적입니다. Java에서는 두 패러다임을 함께 사용하는 것이 이상적입니다.

**함수형 스타일이 적합한 곳**: 데이터 변환/집계 파이프라인, 조건 필터링 로직, 이벤트 핸들러와 콜백, 컬렉션 처리, 유틸리티 메서드. 이런 곳에서는 `stream().filter().map().collect()` 패턴이 for 루프보다 의도를 더 명확하게 드러냅니다.

**OOP 스타일이 적합한 곳**: 도메인 모델(비즈니스 개념 표현), 상태를 가진 복잡한 객체, 인터페이스를 통한 다형성이 필요한 곳, 생명주기 관리(초기화, 소멸). `Order`, `Payment`, `User` 같은 도메인 엔티티는 OOP로 표현하는 것이 자연스럽습니다.

가장 좋은 실무 패턴은 "도메인 모델은 OOP, 데이터 파이프라인은 FP"입니다. `OrderService`가 `Order` 객체(OOP)를 받아 Stream API(FP)로 처리하는 방식이 그 예입니다.

### 안티패턴 피하기

```java
// 안티패턴 1 — 부수효과 있는 람다를 Stream에서 사용
List<String> externalList = new ArrayList<>();
names.stream()
    .filter(s -> { externalList.add(s); return s.length() > 3; })  // 부수효과!
    .collect(Collectors.toList());

// 올바른 방법
List<String> result = names.stream()
    .filter(s -> s.length() > 3)
    .collect(Collectors.toList());

// 안티패턴 2 — Optional을 null처럼 사용
Optional<String> opt = findName();
if (opt.isPresent()) {                  // null 체크와 동일한 패턴
    process(opt.get());
}

// 올바른 방법
findName().ifPresent(this::process);
// 또는
findName().map(this::transform).orElse("default");

// 안티패턴 3 — 중첩 람다로 가독성 저하
Function<Integer, Function<Integer, Function<Integer, Integer>>> f =
    a -> b -> c -> a + b + c;  // 너무 깊은 중첩 — 이름 붙인 메서드로 분리 권장

// 올바른 방법 — 적당히 나누고 이름 붙이기
private int sumThree(int a, int b, int c) { return a + b + c; }
// 또는 record나 클래스로 표현
```

---

## 실무에서 자주 하는 실수

**실수 1: 람다 안에서 외부 상태를 변경 (부수효과)**

```java
// 잘못된 코드 — 병렬 스트림에서 경쟁 조건 발생
List<String> collected = new ArrayList<>();
names.parallelStream()
    .filter(s -> s.length() > 3)
    .forEach(collected::add); // ArrayList는 스레드 안전하지 않음!

// 올바른 코드
List<String> collected = names.parallelStream()
    .filter(s -> s.length() > 3)
    .collect(Collectors.toList()); // Collector가 스레드 안전하게 처리
```

**실수 2: 람다 내부에서 checked 예외를 처리하지 않으려고 예외 삼키기**

```java
// 잘못된 코드 — 예외를 숨겨버림
List<String> lines = files.stream()
    .map(file -> {
        try {
            return Files.readString(file);
        } catch (IOException e) {
            return ""; // 오류를 빈 문자열로 숨김 — 디버깅 불가
        }
    })
    .collect(Collectors.toList());

// 올바른 코드 — 명시적 예외 처리 또는 래퍼 사용
@FunctionalInterface
interface ThrowingFunction<T, R> {
    R apply(T t) throws Exception;
    static <T, R> Function<T, R> wrap(ThrowingFunction<T, R> f) {
        return t -> {
            try { return f.apply(t); }
            catch (Exception e) { throw new RuntimeException(e); }
        };
    }
}

List<String> lines = files.stream()
    .map(ThrowingFunction.wrap(Files::readString))
    .collect(Collectors.toList());
```

**실수 3: Optional을 null 체크 코드처럼 사용**

```java
// 잘못된 코드 — Optional의 의도를 무시
Optional<User> opt = findUser(id);
if (opt.isPresent()) {
    User user = opt.get(); // Optional을 null 체크처럼 사용 — 의미 없음
    process(user);
}

// 올바른 코드 — 함수형 체이닝
findUser(id)
    .map(User::getEmail)
    .filter(email -> email.endsWith("@company.com"))
    .ifPresentOrElse(
        email -> sendNotification(email),
        () -> log.warn("사용자 없음: {}", id)
    );
```

**실수 4: 메서드 참조와 람다를 혼용해 가독성 저하**

```java
// 일관성 없는 코드
list.stream()
    .filter(s -> s != null)          // null 체크는 메서드 참조로
    .map(s -> s.toUpperCase())        // 메서드 참조로 가능
    .sorted((a, b) -> a.compareTo(b)) // Comparator.naturalOrder()로 가능
    .collect(Collectors.toList());

// 일관된 코드
list.stream()
    .filter(Objects::nonNull)
    .map(String::toUpperCase)
    .sorted(Comparator.naturalOrder())
    .collect(Collectors.toList());
```

---

## 극한 시나리오: 트래픽 규모별 함수형 패턴

### 100 TPS (소규모 서비스)

순수 함수와 불변 객체를 습관화하세요. 단순 `stream().filter().map().collect()` 패턴으로 충분합니다. 성능보다 코드 명확성을 우선합니다.

```java
// 100 TPS: 가독성 우선 함수형 스타일
List<OrderSummary> summaries = orders.stream()
    .filter(order -> order.getStatus() == OrderStatus.COMPLETED)
    .map(order -> new OrderSummary(order.getId(), order.getTotalAmount()))
    .sorted(Comparator.comparing(OrderSummary::totalAmount).reversed())
    .collect(Collectors.toList());
```

### 10,000 TPS (중규모 서비스)

메모이제이션으로 반복 계산을 제거하고, 함수 합성으로 재사용성을 높입니다. `Function.andThen()`과 `Predicate.and()`를 적극 활용합니다.

```java
// 10K TPS: 메모이제이션으로 비용 큰 계산 캐싱
private final Map<Long, UserTier> tierCache = new ConcurrentHashMap<>();

private final Function<Long, UserTier> calculateTier =
    userId -> tierCache.computeIfAbsent(userId, this::expensiveTierCalculation);

// 함수 합성으로 검증 파이프라인 구축
Predicate<Order> validOrder = isNotNull()
    .and(hasValidAmount())
    .and(hasValidCustomer())
    .and(isNotDuplicate());

// 재사용 가능한 변환 함수 조합
Function<Order, OrderDto> toDto = Order::toDto;
Function<OrderDto, EnrichedOrderDto> enrich = this::enrichWithUserInfo;
Function<Order, EnrichedOrderDto> fullTransform = toDto.andThen(enrich);

List<EnrichedOrderDto> result = orders.stream()
    .filter(validOrder)
    .map(fullTransform)
    .collect(Collectors.toList());
```

### 100,000 TPS (대규모 서비스)

이 규모에서는 함수형 패턴 자체보다 **데이터 처리 아키텍처**가 핵심입니다. 단일 JVM에서 Stream으로 처리하는 것의 한계를 인식하고, 불변 객체와 순수 함수 기반의 설계가 분산 처리로 전환할 때 가장 큰 이점을 발휘합니다.

```java
// 100K TPS: 배치 처리 + 함수형 파이프라인
// 순수 함수로 정의된 변환 로직은 Kafka Streams, Flink 등으로 이식 용이

// 변환 로직을 순수 함수로 분리 → 단위 테스트 용이, 분산 처리 이식 가능
public static final Function<RawEvent, ProcessedEvent> PROCESS_EVENT =
    raw -> new ProcessedEvent(
        raw.getId(),
        raw.getTimestamp(),
        categorize(raw.getType()),
        normalize(raw.getPayload())
    );

// 배치 단위 처리 (청크 사이즈 조절로 GC 압박 완화)
int chunkSize = 1000;
List<List<RawEvent>> chunks = partition(rawEvents, chunkSize);

List<ProcessedEvent> results = chunks.parallelStream() // 청크 레벨 병렬화
    .flatMap(chunk -> chunk.stream().map(PROCESS_EVENT))
    .collect(Collectors.toList());
```

함수형 프로그래밍의 진짜 가치는 트래픽이 늘수록 드러납니다. **순수 함수는 테스트하기 쉽고, 불변 객체는 공유해도 안전하고, 선언적 파이프라인은 병렬화하기 쉽습니다.** 이 세 가지 원칙이 대규모 시스템의 안정성과 확장성을 뒷받침합니다.

---

## 정리 요약

| 개념 | 핵심 | Java 도구 |
|------|------|-----------|
| 순수 함수 | 같은 입력 = 같은 출력, 부수효과 없음 | 람다, 메서드 참조 |
| 불변성 | 상태 변경 대신 새 값 생성 | record, List.of(), String |
| 고차 함수 | 함수를 파라미터/반환값으로 | Function, Predicate, Supplier |
| 커링 | 다항 함수를 단항 체인으로 | Function&lt;A, Function&lt;B, R&gt;&gt; |
| 함수 합성 | 작은 함수를 조합해 복잡한 함수 구성 | andThen(), compose(), and(), or() |
| 선언적 파이프라인 | 무엇을 할지만 기술 | Stream API |
| null 안전 처리 | Optional 모나드 | Optional.map(), flatMap(), orElse() |

**핵심 원칙**: 람다 안에서 외부 상태를 변경하지 마세요. Optional.get()보다 map/ifPresent를 쓰세요. Java는 꼬리 재귀 최적화(TCO)를 지원하지 않으므로 깊은 재귀는 반복문으로 대체하세요.
