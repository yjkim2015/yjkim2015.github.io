---
title: "Java 래퍼 클래스와 오토박싱"
categories:
- JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

Java는 기본형(primitive type)과 참조형(reference type)이라는 두 가지 타입 체계를 가집니다. 이 둘 사이의 간극을 메우는 것이 래퍼 클래스(Wrapper Class)이며, 오토박싱(Auto-boxing)은 이 변환을 자동화한 Java 5의 핵심 기능입니다.

---

## 1. 기본형(primitive) vs 참조형(reference)

### 타입 체계 비교

```
Java 타입 시스템:
┌─────────────────────────────────────────────────┐
│              Java Types                         │
│                                                 │
│  기본형 (Primitive)    참조형 (Reference)        │
│  ┌───────────────┐    ┌────────────────────┐    │
│  │ byte          │    │ String             │    │
│  │ short         │    │ Integer            │    │
│  │ int           │    │ Double             │    │
│  │ long          │    │ List<T>            │    │
│  │ float         │    │ Object             │    │
│  │ double        │    │ 모든 클래스 인스턴스│    │
│  │ char          │    └────────────────────┘    │
│  │ boolean       │                              │
│  └───────────────┘                              │
└─────────────────────────────────────────────────┘
```

### 메모리 저장 방식

```
기본형 — 스택(Stack)에 직접 값 저장:
┌──────────────────┐
│  Stack           │
│  int i = 42;     │  [42]  ← 값 자체
│  double d = 3.14 │  [3.14]
└──────────────────┘

참조형 — 스택에 참조(주소), Heap에 객체:
┌──────────────────┐    ┌────────────────┐
│  Stack           │    │  Heap          │
│  Integer n ──────┼───►│  Integer{42}   │
└──────────────────┘    └────────────────┘
```

### 크기와 기본값

| 기본형 | 크기 | 기본값 | 래퍼 클래스 |
|--------|------|--------|-------------|
| `byte` | 1 byte | 0 | `Byte` |
| `short` | 2 bytes | 0 | `Short` |
| `int` | 4 bytes | 0 | `Integer` |
| `long` | 8 bytes | 0L | `Long` |
| `float` | 4 bytes | 0.0f | `Float` |
| `double` | 8 bytes | 0.0d | `Double` |
| `char` | 2 bytes | '\u0000' | `Character` |
| `boolean` | 1 bit (JVM 구현 의존) | false | `Boolean` |

---

## 2. 래퍼 클래스(Wrapper Class)

### 래퍼 클래스가 필요한 이유

```java
// 1. 제네릭은 참조형만 허용
List<int> list = new ArrayList<>();    // 컴파일 에러!
List<Integer> list = new ArrayList<>(); // OK

// 2. null을 표현해야 할 때
int score = null;      // 컴파일 에러!
Integer score = null;  // OK — 값 없음 표현 가능

// 3. Object가 필요한 곳 (다형성)
Object obj = 42;  // 오토박싱 → Integer

// 4. 유틸리티 메서드 활용
Integer.parseInt("42");
Integer.toBinaryString(255);
Integer.MAX_VALUE;
```

### 주요 래퍼 클래스 메서드

```java
// Integer
Integer.parseInt("42")          // String → int
Integer.valueOf("42")           // String → Integer
Integer.toString(42)            // int → String
Integer.toBinaryString(42)      // "101010"
Integer.toHexString(255)        // "ff"
Integer.toOctalString(8)        // "10"
Integer.MAX_VALUE               // 2147483647
Integer.MIN_VALUE               // -2147483648
Integer.bitCount(42)            // 1의 개수 (3)
Integer.reverse(42)             // 비트 역전
Integer.compare(a, b)           // 비교 (Java 7+)
Integer.sum(a, b)               // a + b (메서드 참조용)
Integer.max(a, b)               // 큰 값

// Double
Double.parseDouble("3.14")
Double.isNaN(Double.NaN)        // true
Double.isInfinite(1.0 / 0.0)   // true
Double.MAX_VALUE
Double.MIN_VALUE                // 양수 최솟값 (0에 가장 가까운)

// Character
Character.isDigit('5')          // true
Character.isLetter('A')         // true
Character.isLetterOrDigit('_')  // false
Character.isUpperCase('A')      // true
Character.toLowerCase('A')      // 'a'
Character.toUpperCase('a')      // 'A'

// Boolean
Boolean.parseBoolean("true")    // true
Boolean.parseBoolean("TRUE")    // true (대소문자 무시)
Boolean.parseBoolean("yes")     // false (true/false만 인식)
```

---

## 3. 오토박싱(Auto-boxing) / 언박싱(Unboxing)

### 동작 원리

```java
// 오토박싱 — 기본형 → 래퍼 클래스 (컴파일러가 자동 변환)
int i = 42;
Integer boxed = i;  // 컴파일러: Integer.valueOf(i)

// 언박싱 — 래퍼 클래스 → 기본형
Integer n = Integer.valueOf(42);
int unboxed = n;    // 컴파일러: n.intValue()
```

```
컴파일 전:                컴파일 후:
Integer n = 42;  ───►  Integer n = Integer.valueOf(42);
int i = n;       ───►  int i = n.intValue();
```

### 오토박싱이 일어나는 상황

```java
// 1. 대입
Integer a = 100;           // 박싱

// 2. 컬렉션에 추가
List<Integer> list = new ArrayList<>();
list.add(1);               // 박싱

// 3. 연산
Integer x = 10;
Integer y = 20;
int sum = x + y;           // 둘 다 언박싱 후 더하기

// 4. 메서드 호출 (파라미터 타입 불일치)
void process(Integer n) { ... }
process(42);               // 박싱

// 5. 조건문
Integer flag = getFlag();
if (flag == 1) { ... }    // flag 언박싱 후 비교
```

### NPE 함정

```java
// 언박싱 시 null이면 NPE!
Integer value = null;
int i = value;  // NullPointerException!

// 실수하기 쉬운 패턴
Map<String, Integer> map = new HashMap<>();
int count = map.get("key");  // key 없으면 null → 언박싱 → NPE!

// 안전한 코드
Integer count = map.get("key");
if (count != null) {
    int c = count;
}
// 또는
int count = map.getOrDefault("key", 0);
```

---

## 4. Integer 캐시 (-128 ~ 127)와 == 비교 함정

### Integer 캐시 동작

JVM은 `-128`부터 `127` 범위의 Integer 객체를 **미리 생성해 캐싱**합니다.

```java
// Java 소스 (Integer.valueOf 구현)
public static Integer valueOf(int i) {
    if (i >= IntegerCache.low && i <= IntegerCache.high)
        return IntegerCache.cache[i + (-IntegerCache.low)];
    return new Integer(i);
}
```

```java
// 캐시 범위 내 (-128 ~ 127) — 같은 객체 반환
Integer a = 127;
Integer b = 127;
System.out.println(a == b);   // true (캐시 객체)
System.out.println(a.equals(b)); // true

// 캐시 범위 초과 — 새 객체 생성
Integer c = 128;
Integer d = 128;
System.out.println(c == d);   // false! (다른 객체)
System.out.println(c.equals(d)); // true
```

```
캐시 구조:
IntegerCache.cache:
[0]  → Integer(-128)
[1]  → Integer(-127)
...
[127] → Integer(-1)
[128] → Integer(0)
...
[255] → Integer(127)

127  → 캐시에서 반환 (항상 같은 객체)
128  → new Integer(128) (항상 새 객체)
```

### 다른 래퍼 클래스의 캐시

```java
// Byte: 항상 캐시 (-128 ~ 127, 전체 범위)
// Short: -128 ~ 127 캐시
// Long: -128 ~ 127 캐시
// Character: 0 ~ 127 캐시
// Boolean: TRUE, FALSE 두 객체만 캐시
// Float, Double: 캐시 없음!

Boolean t1 = true;
Boolean t2 = true;
System.out.println(t1 == t2);  // true (Boolean.TRUE 캐시)
```

### == vs equals() 결론

```java
// 래퍼 클래스는 절대 == 으로 비교하지 말 것!
Integer a = 1000;
Integer b = 1000;
a == b      // 운이 좋으면 true, 아니면 false → 예측 불가
a.equals(b) // 항상 true → 항상 이것을 사용

// 기본형으로 비교
int x = a;
int y = b;
x == y  // 항상 true — 안전
```

### JVM 옵션으로 캐시 크기 조정 가능

```bash
# -XX:AutoBoxCacheMax=<size> 로 최대값 조정 가능
# 최소는 항상 -128
java -XX:AutoBoxCacheMax=1000 MyApp
```

---

## 5. 성능 주의사항

### 반복문에서의 박싱 비용

```java
// 나쁜 예 — 매 반복마다 박싱/언박싱
Long sum = 0L;
for (long i = 0; i < 1_000_000; i++) {
    sum += i;  // sum 언박싱 → 더하기 → 박싱 (반복!)
}
// 약 100만 번의 Long 객체 생성 → GC 부담

// 좋은 예 — 기본형 사용
long sum = 0L;
for (long i = 0; i < 1_000_000; i++) {
    sum += i;  // 기본형 덧셈만
}
```

### 객체 생성 비용 측정

```java
// JMH 벤치마크 결과 (대략적):
// 기본형 연산:     ~1ns
// 박싱된 Integer:  ~5-10ns (객체 생성 + GC 부담)
// 박싱 루프 1M:   기본형 루프 대비 약 6배 느림
```

### 컬렉션에서의 기본형 처리

```java
// 표준 컬렉션 — 박싱 필수
List<Integer> list = new ArrayList<>();
list.add(1); // 박싱

// 기본형 특화 스트림 사용
int[] arr = {1, 2, 3, 4, 5};
int sum = IntStream.of(arr).sum();     // 박싱 없음
int max = IntStream.of(arr).max().getAsInt();

// IntStream, LongStream, DoubleStream
IntStream.range(0, 100).forEach(i -> ...);   // 박싱 없음
IntStream.rangeClosed(1, 100).sum();          // 박싱 없음
```

### 외부 라이브러리: 기본형 컬렉션

```java
// Eclipse Collections (기본형 특화)
IntList intList = IntLists.mutable.of(1, 2, 3);

// Trove / Koloboke (기본형 Map/Set)
TIntIntMap map = new TIntIntHashMap();
map.put(1, 100);
int val = map.get(1);  // 박싱 없음
```

---

## 6. Optional과의 관계

### Optional은 래퍼 클래스의 null 문제를 해결

```java
// Integer null — 의미가 불명확
Integer score = null;  // 점수가 없는 건지, 0인지, 오류인지?

// Optional<Integer> — 의도 명확
Optional<Integer> score = Optional.empty();     // 점수 없음
Optional<Integer> score = Optional.of(95);      // 점수 있음
Optional<Integer> score = Optional.ofNullable(getScore()); // null 가능
```

### 기본형 Optional

```java
// 박싱 비용 없는 기본형 Optional (권장)
OptionalInt    optInt    = OptionalInt.of(42);
OptionalLong   optLong   = OptionalLong.of(100L);
OptionalDouble optDouble = OptionalDouble.of(3.14);

optInt.getAsInt();       // 42
optInt.isPresent();      // true
optInt.orElse(0);        // 42

// Optional<Integer> 보다 OptionalInt 선호 (성능)
OptionalInt result = IntStream.range(1, 100)
    .filter(i -> i % 7 == 0)
    .findFirst();
```

### Optional 활용 패턴

```java
// null 반환 대신 Optional 반환
public Optional<Integer> findScore(String userId) {
    Integer score = db.getScore(userId);
    return Optional.ofNullable(score);
}

// 사용 측
findScore("user123")
    .map(score -> score * 2)
    .filter(score -> score > 100)
    .ifPresent(score -> System.out.println("High score: " + score));

// orElse / orElseGet / orElseThrow
int score = findScore("user123").orElse(0);
int score = findScore("user123").orElseGet(() -> calculateDefault());
int score = findScore("user123").orElseThrow(() -> new RuntimeException("Not found"));
```

---

## 7. 전체 요약

```
래퍼 클래스 핵심 정리:
┌──────────────────────────────────────────────────────────┐
│  기본형 vs 참조형                                        │
│  - 기본형: 스택, 빠름, null 불가                         │
│  - 참조형: 힙, 느림, null 가능, 제네릭 사용 가능        │
│                                                          │
│  오토박싱                                                │
│  - 컴파일러가 Integer.valueOf() / intValue() 삽입        │
│  - null 언박싱 → NPE 주의                               │
│                                                          │
│  Integer 캐시 함정                                       │
│  - -128~127 범위는 == 우연히 동작                        │
│  - 항상 equals() 사용할 것                               │
│                                                          │
│  성능                                                    │
│  - 반복문 내 박싱 금지 → 기본형 사용                    │
│  - 스트림: IntStream / LongStream / DoubleStream 우선    │
│                                                          │
│  null 처리                                               │
│  - Optional / OptionalInt 활용                           │
└──────────────────────────────────────────────────────────┘
```
