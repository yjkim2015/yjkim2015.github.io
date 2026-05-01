---
title: "Java 제네릭(Generics) 완전 정리"
categories:
- JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

Java 제네릭(Generics)은 클래스, 인터페이스, 메서드를 정의할 때 타입을 파라미터로 사용할 수 있게 해주는 기능입니다. Java 5(2004)에 도입되어 타입 안전성과 코드 재사용성을 동시에 달성하는 핵심 언어 기능으로 자리잡았습니다.

---

## 1. 제네릭이란? 왜 필요한가?

### 제네릭 도입 전: Object 캐스팅의 문제점

Java 5 이전에는 컬렉션이 `Object` 타입으로 모든 것을 저장했습니다.

```java
// Java 5 이전 — 제네릭 없는 코드
List list = new ArrayList();
list.add("Hello");
list.add(123);        // 컴파일 통과 — 실수를 잡을 수 없음
list.add(new User()); // 컴파일 통과

// 꺼낼 때 반드시 명시적 캐스팅 필요
String s = (String) list.get(0); // OK
String s2 = (String) list.get(1); // 런타임 ClassCastException 발생!
```

문제점은 세 가지입니다.

1. **ClassCastException 위험**: 잘못된 타입을 넣어도 컴파일러가 감지하지 못하고 런타임에서 터집니다.
2. **명시적 캐스팅 필수**: 꺼낼 때마다 `(String)` 같은 캐스팅 코드를 작성해야 합니다.
3. **의도 불명확**: 이 `List`가 어떤 타입을 담는지 코드만 봐서는 알 수 없습니다.

### 제네릭 도입 후: 타입 안전성 확보

```java
// Java 5 이후 — 제네릭 코드
List<String> list = new ArrayList<>();
list.add("Hello");
list.add(123);    // 컴파일 에러! — 실수를 컴파일 타임에 차단

String s = list.get(0); // 캐스팅 불필요
```

### 타입 안전성 (Type Safety)

제네릭의 핵심 이점은 **컴파일 타임 타입 체크**입니다. 잘못된 타입을 사용하면 프로그램이 실행되기 전에 오류를 발견할 수 있습니다.

```java
// 타입 안전한 컨테이너
List<Integer> numbers = new ArrayList<>();
numbers.add(1);
numbers.add(2);
// numbers.add("three"); // 컴파일 에러 — "three"는 Integer가 아님

int sum = 0;
for (int n : numbers) {  // 언박싱, 캐스팅 없이 바로 사용
    sum += n;
}
```

컴파일러가 타입을 보장하므로 런타임 `ClassCastException`이 원천적으로 차단됩니다.

---

## 2. 제네릭 클래스와 인터페이스

### 타입 파라미터 명명 관례

자바 커뮤니티에서 통용되는 단일 대문자 관례입니다.

| 파라미터 | 의미 | 주요 사용처 |
|---------|------|-----------|
| `T` | Type | 일반적인 타입 |
| `E` | Element | 컬렉션 원소 |
| `K` | Key | Map의 키 |
| `V` | Value | Map의 값 |
| `N` | Number | 숫자 타입 |
| `R` | Return | 반환 타입 |
| `S`, `U`, `V` | 추가 타입 | 두 번째, 세 번째 타입 파라미터 |

### 제네릭 클래스 정의와 사용

```java
// 제네릭 클래스 정의
public class Box<T> {
    private T value;

    public Box(T value) {
        this.value = value;
    }

    public T getValue() {
        return value;
    }

    public void setValue(T value) {
        this.value = value;
    }

    @Override
    public String toString() {
        return "Box[" + value + "]";
    }
}
```

```java
// 사용
Box<String> stringBox = new Box<>("Hello");
String s = stringBox.getValue(); // 캐스팅 불필요

Box<Integer> intBox = new Box<>(42);
int n = intBox.getValue(); // 자동 언박싱

Box<List<String>> listBox = new Box<>(new ArrayList<>());
// 타입 파라미터에 제네릭 타입도 사용 가능
```

**다이아몬드 연산자 (`<>`)**: Java 7부터 오른쪽의 타입 파라미터를 생략하고 `<>`만 써도 컴파일러가 추론합니다.

```java
// Java 7 이전
Box<String> box = new Box<String>("Hello");

// Java 7 이후 — 다이아몬드 연산자
Box<String> box = new Box<>("Hello");
```

### 다중 타입 파라미터

여러 타입 파라미터를 쉼표로 구분합니다.

```java
// 두 타입 파라미터를 가진 Pair 클래스
public class Pair<K, V> {
    private final K first;
    private final V second;

    public Pair(K first, V second) {
        this.first = first;
        this.second = second;
    }

    public K getFirst() { return first; }
    public V getSecond() { return second; }

    public static <K, V> Pair<K, V> of(K first, V second) {
        return new Pair<>(first, second);
    }

    @Override
    public String toString() {
        return "(" + first + ", " + second + ")";
    }
}
```

```java
// 사용
Pair<String, Integer> pair = Pair.of("나이", 30);
System.out.println(pair.getFirst());  // "나이"
System.out.println(pair.getSecond()); // 30

Pair<String, List<Integer>> complex = Pair.of("scores", List.of(90, 85, 92));
```

### 제네릭 인터페이스

```java
// 제네릭 인터페이스 정의
public interface Repository<T, ID> {
    T findById(ID id);
    List<T> findAll();
    T save(T entity);
    void delete(ID id);
}

// 구체 타입으로 구현
public class UserRepository implements Repository<User, Long> {
    @Override
    public User findById(Long id) { /* ... */ }

    @Override
    public List<User> findAll() { /* ... */ }

    @Override
    public User save(User user) { /* ... */ }

    @Override
    public void delete(Long id) { /* ... */ }
}

// 여전히 제네릭을 유지하며 구현
public class InMemoryRepository<T, ID> implements Repository<T, ID> {
    private final Map<ID, T> store = new HashMap<>();

    @Override
    public T findById(ID id) {
        return store.get(id);
    }

    @Override
    public List<T> findAll() {
        return new ArrayList<>(store.values());
    }

    @Override
    public T save(T entity) {
        // ID 추출 로직 필요 (실제로는 별도 처리)
        return entity;
    }

    @Override
    public void delete(ID id) {
        store.remove(id);
    }
}
```

---

## 3. 제네릭 메서드

### 정의 문법

타입 파라미터를 반환 타입 앞에 선언합니다.

```java
public class GenericUtils {

    // 제네릭 메서드: <T>를 반환 타입 앞에 선언
    public static <T> T identity(T value) {
        return value;
    }

    // 여러 타입 파라미터
    public static <K, V> Map<V, K> invertMap(Map<K, V> original) {
        Map<V, K> inverted = new HashMap<>();
        for (Map.Entry<K, V> entry : original.entrySet()) {
            inverted.put(entry.getValue(), entry.getKey());
        }
        return inverted;
    }

    // 배열을 리스트로 변환
    public static <T> List<T> arrayToList(T[] array) {
        return new ArrayList<>(Arrays.asList(array));
    }

    // 두 값 중 더 큰 값 반환 (Comparable 바운드)
    public static <T extends Comparable<T>> T max(T a, T b) {
        return a.compareTo(b) >= 0 ? a : b;
    }
}
```

### 타입 추론 (Type Inference)

컴파일러가 인수의 타입을 보고 타입 파라미터를 자동으로 추론합니다.

```java
// 명시적 타입 지정 (불필요)
String result1 = GenericUtils.<String>identity("hello");

// 타입 추론 — 컴파일러가 인수 "hello"를 보고 T=String으로 추론
String result2 = GenericUtils.identity("hello");

// 메서드 체이닝에서도 추론 가능
List<String> list = GenericUtils.arrayToList(new String[]{"a", "b", "c"});

// max 메서드 타입 추론
int bigger = GenericUtils.max(10, 20);       // T=Integer 추론
String later = GenericUtils.max("apple", "banana"); // T=String 추론
```

### 제네릭 클래스 vs 제네릭 메서드

```java
// 제네릭 클래스: 인스턴스 생성 시 타입 고정
Box<String> box = new Box<>("hello");
// box는 이제 String 전용, Integer를 넣을 수 없음

// 제네릭 메서드: 호출할 때마다 다른 타입 사용 가능
public static <T> void printTwice(T value) {
    System.out.println(value);
    System.out.println(value);
}

printTwice("hello");  // T=String
printTwice(42);       // T=Integer
printTwice(3.14);     // T=Double
```

제네릭 메서드는 특정 메서드에만 타입 파라미터가 필요할 때, 클래스 전체에 타입 파라미터를 붙이지 않고 사용하는 방식입니다. 유틸리티 클래스(`Collections`, `Arrays`)에서 주로 볼 수 있는 패턴입니다.

---

## 4. 타입 제한 (Bounded Type Parameters)

### 상한 제한 (Upper Bounded — extends)

`T extends 타입`으로 타입 파라미터가 특정 클래스/인터페이스의 서브타입이어야 함을 강제합니다.

```java
// Number의 서브타입만 허용 (Integer, Double, Long 등)
public static <T extends Number> double sum(List<T> list) {
    double total = 0;
    for (T element : list) {
        total += element.doubleValue(); // Number의 메서드 사용 가능
    }
    return total;
}
```

```java
// 사용
List<Integer> ints = List.of(1, 2, 3, 4, 5);
System.out.println(sum(ints)); // 15.0

List<Double> doubles = List.of(1.1, 2.2, 3.3);
System.out.println(sum(doubles)); // 6.6

// sum(List.of("a", "b")); // 컴파일 에러 — String은 Number 서브타입이 아님
```

상한 제한이 없으면 `T`는 `Object`로만 취급되어 `doubleValue()` 같은 메서드를 호출할 수 없습니다. `extends`로 바운드를 걸면 해당 타입의 메서드를 타입 안전하게 호출할 수 있습니다.

```java
// Comparable을 구현한 타입만 허용 — 정렬 가능한 원소의 최솟값 찾기
public static <T extends Comparable<T>> T min(List<T> list) {
    if (list.isEmpty()) throw new IllegalArgumentException("빈 리스트");
    T result = list.get(0);
    for (T element : list) {
        if (element.compareTo(result) < 0) {
            result = element;
        }
    }
    return result;
}
```

### 다중 바운드 (Multiple Bounds)

`&`로 여러 타입을 동시에 바운드할 수 있습니다. 클래스는 반드시 첫 번째에 위치해야 하며, 클래스는 최대 하나만 가능합니다.

```java
// Serializable과 Comparable을 모두 구현한 타입
public static <T extends Serializable & Comparable<T>> T clamp(
        T value, T min, T max) {
    if (value.compareTo(min) < 0) return min;
    if (value.compareTo(max) > 0) return max;
    return value;
}

// 인터페이스 두 개 (클래스 없음)
public interface Printable {
    void print();
}

public interface Saveable {
    void save();
}

public static <T extends Printable & Saveable> void processItem(T item) {
    item.print();
    item.save();
}
```

```java
// 클래스 + 인터페이스 조합 (클래스가 반드시 첫 번째)
public static <T extends AbstractEntity & Auditable & Serializable> void audit(T entity) {
    entity.setModifiedAt(LocalDateTime.now()); // AbstractEntity 메서드
    entity.recordChange();                      // Auditable 메서드
}
```

---

## 5. 와일드카드 (Wildcard)

와일드카드 `?`는 "알 수 없는 타입"을 나타냅니다. 타입 파라미터 `T`와 달리 와일드카드는 타입을 캡처하지 않습니다.

### 비한정 와일드카드 (Unbounded Wildcard — ?)

```java
// List<?>: 어떤 타입의 List든 받을 수 있음
public static void printList(List<?> list) {
    for (Object element : list) { // ?는 Object로만 취급
        System.out.println(element);
    }
}
```

```java
// 사용
printList(List.of(1, 2, 3));
printList(List.of("a", "b", "c"));
printList(List.of(1.1, 2.2, 3.3));
```

`List<?>`와 `List<Object>`의 차이점이 중요합니다.

```java
// List<Object>: Object의 하위타입 List를 받을 수 없음
public static void wrongPrint(List<Object> list) { }

// wrongPrint(new ArrayList<String>()); // 컴파일 에러!
// String은 Object의 서브타입이지만 List<String>은 List<Object>의 서브타입이 아님

// List<?>: 모든 타입의 List를 받을 수 있음
public static void correctPrint(List<?> list) { }

correctPrint(new ArrayList<String>()); // OK
correctPrint(new ArrayList<Integer>()); // OK
```

비한정 와일드카드로는 `null` 외에 원소를 추가할 수 없습니다. 컴파일러가 실제 타입을 알 수 없기 때문입니다.

```java
List<?> list = new ArrayList<String>();
// list.add("hello"); // 컴파일 에러 — ? 타입에 뭘 넣어야 할지 모름
list.add(null);        // null은 OK (모든 타입의 공통 값)
```

### 상한 와일드카드 (Upper Bounded Wildcard — ? extends T)

`? extends T`는 T이거나 T의 서브타입인 알 수 없는 타입을 의미합니다.

```java
// Number 또는 Number의 서브타입(Integer, Double 등)의 List를 읽기 전용으로 받음
public static double sumNumbers(List<? extends Number> list) {
    double total = 0;
    for (Number n : list) {      // ? extends Number이므로 Number로 읽을 수 있음
        total += n.doubleValue();
    }
    return total;
}
```

```java
// 사용
List<Integer> ints = List.of(1, 2, 3);
List<Double> doubles = List.of(1.5, 2.5, 3.5);
List<Number> numbers = List.of(1, 2.5, 3L);

sumNumbers(ints);    // OK
sumNumbers(doubles); // OK
sumNumbers(numbers); // OK
```

`? extends T`로 선언된 컬렉션에는 `null` 외의 원소를 추가할 수 없습니다. 실제 타입이 `Integer`인지 `Double`인지 알 수 없기 때문입니다.

```java
List<? extends Number> list = new ArrayList<Integer>();
// list.add(1);   // 컴파일 에러 — Integer? Double? 무엇을 넣어야?
// list.add(1.0); // 컴파일 에러
Number n = list.get(0); // 읽기는 OK — ? extends Number이니 최소한 Number
```

이 속성을 **공변성(Covariance)**이라고 합니다. `List<? extends Number>`는 `List<Integer>`, `List<Double>` 등의 서브타입을 모두 허용합니다.

### 하한 와일드카드 (Lower Bounded Wildcard — ? super T)

`? super T`는 T이거나 T의 슈퍼타입인 알 수 없는 타입을 의미합니다.

```java
// Integer 또는 Integer의 슈퍼타입(Number, Object) List에 쓰기 가능
public static void addIntegers(List<? super Integer> list) {
    list.add(1);   // OK — ? super Integer이므로 Integer를 추가 가능
    list.add(2);
    list.add(3);
    // Integer n = list.get(0); // 컴파일 에러 — 반환 타입이 ? super Integer, 즉 Object
    Object obj = list.get(0); // OK — Object로는 읽을 수 있음
}
```

```java
// 사용
List<Integer> intList = new ArrayList<>();
List<Number> numList = new ArrayList<>();
List<Object> objList = new ArrayList<>();

addIntegers(intList); // OK — Integer super Integer
addIntegers(numList); // OK — Number super Integer
addIntegers(objList); // OK — Object super Integer

// List<Double>에는 Integer를 추가하는 게 맞지 않으므로:
// addIntegers(new ArrayList<Double>()); // 컴파일 에러
```

이 속성을 **반공변성(Contravariance)**이라고 합니다.

### PECS (Producer Extends, Consumer Super) 원칙

Effective Java에서 조슈아 블로크가 제시한 원칙입니다.

- **Producer (데이터를 생산/제공하는 쪽)** → `? extends T` 사용
- **Consumer (데이터를 소비/받아들이는 쪽)** → `? super T` 사용

```java
// PECS 적용 예시: src에서 읽어서 dest에 씀
public static <T> void copy(List<? extends T> src,   // Producer — extends
                             List<? super T> dest) {  // Consumer — super
    for (T element : src) {
        dest.add(element);
    }
}
```

```java
// 사용
List<Integer> integers = List.of(1, 2, 3);
List<Number> numbers = new ArrayList<>();

copy(integers, numbers); // OK — Integer는 Number를 extends, Number는 Integer를 super

// Collections.copy의 실제 시그니처도 PECS 원칙을 따름
// public static <T> void copy(List<? super T> dest, List<? extends T> src)
```

실무 예시를 통해 PECS를 확실히 이해해봅니다.

```java
public class Stack<E> {
    private List<E> elements = new ArrayList<>();

    // 여러 원소를 한꺼번에 push — src는 Producer (읽기만)
    public void pushAll(Iterable<? extends E> src) {
        for (E e : src) {
            elements.add(e);
        }
    }

    // 여러 원소를 한꺼번에 pop — dest는 Consumer (쓰기만)
    public void popAll(Collection<? super E> dest) {
        while (!elements.isEmpty()) {
            dest.add(elements.remove(elements.size() - 1));
        }
    }
}
```

```java
Stack<Number> stack = new Stack<>();

// pushAll: Integer는 Number를 extends하므로 OK
List<Integer> ints = List.of(1, 2, 3);
stack.pushAll(ints);

// popAll: Object는 Number를 super하므로 OK
List<Object> objects = new ArrayList<>();
stack.popAll(objects);
```

### 와일드카드 vs 타입 파라미터 선택 기준

```java
// 방법 1: 타입 파라미터 사용
public static <T> void swap(List<T> list, int i, int j) {
    T temp = list.get(i);
    list.set(i, list.get(j));
    list.set(j, temp);
}

// 방법 2: 와일드카드 사용 (이 경우 내부 헬퍼 메서드 필요)
public static void swap(List<?> list, int i, int j) {
    swapHelper(list, i, j); // 헬퍼로 타입 캡처
}

private static <T> void swapHelper(List<T> list, int i, int j) {
    T temp = list.get(i);
    list.set(i, list.get(j));
    list.set(j, temp);
}
```

선택 기준은 다음과 같습니다.

| 상황 | 권장 |
|------|------|
| 타입 파라미터가 메서드 내에서 두 번 이상 등장 (반환 타입, 다른 파라미터와 연결) | 타입 파라미터 `<T>` |
| 단순히 "어떤 타입이든 받겠다"는 의미 | 와일드카드 `?` |
| 반환 타입에는 | 와일드카드 사용 금지 (호출자가 불편) |
| 타입 간의 관계를 표현 | 타입 파라미터 `<T>` |

---

## 6. 타입 소거 (Type Erasure)

### 컴파일 타임 vs 런타임

제네릭 타입 정보는 **컴파일 타임에만 존재**하고, 바이트코드로 컴파일되면 제거됩니다. 이를 타입 소거라 합니다. Java는 기존 코드(제네릭 도입 전)와의 하위 호환성을 위해 이 방식을 선택했습니다.

```java
// 컴파일 전 소스 코드
List<String> stringList = new ArrayList<>();
stringList.add("hello");
String s = stringList.get(0);

List<Integer> intList = new ArrayList<>();
intList.add(42);
Integer n = intList.get(0);
```

```java
// 컴파일 후 바이트코드 (의사코드로 표현)
List stringList = new ArrayList();
stringList.add("hello");
String s = (String) stringList.get(0);  // 컴파일러가 캐스팅 삽입

List intList = new ArrayList();
intList.add(Integer.valueOf(42));
Integer n = (Integer) intList.get(0);   // 컴파일러가 캐스팅 삽입
```

런타임에 `List<String>`과 `List<Integer>`는 동일하게 `List`로 보입니다.

```java
List<String> stringList = new ArrayList<>();
List<Integer> intList = new ArrayList<>();

// 런타임에 동일한 클래스
System.out.println(stringList.getClass() == intList.getClass()); // true
System.out.println(stringList.getClass()); // class java.util.ArrayList
```

### 소거 후 바이트코드 변환 규칙

컴파일러는 타입 소거 시 다음 규칙을 적용합니다.

1. 바운드가 없는 타입 파라미터 → `Object`로 대체
2. 상한 바운드가 있는 타입 파라미터 → 첫 번째 바운드 타입으로 대체

```java
// 원본
public class Box<T> {
    private T value;
    public T getValue() { return value; }
    public void setValue(T value) { this.value = value; }
}

// 소거 후 (T → Object)
public class Box {
    private Object value;
    public Object getValue() { return value; }
    public void setValue(Object value) { this.value = value; }
}
```

```java
// 원본 (바운드 있음)
public class NumericBox<T extends Number> {
    private T value;
    public double doubleValue() { return value.doubleValue(); }
}

// 소거 후 (T → Number, 첫 번째 바운드)
public class NumericBox {
    private Number value;
    public double doubleValue() { return value.doubleValue(); }
}
```

### Bridge 메서드

타입 소거로 인해 다형성이 깨질 수 있을 때 컴파일러가 자동으로 **Bridge 메서드**를 생성합니다.

```java
// 원본
public interface Comparable<T> {
    int compareTo(T o);
}

public class MyInteger implements Comparable<MyInteger> {
    private int value;

    @Override
    public int compareTo(MyInteger other) {
        return Integer.compare(this.value, other.value);
    }
}
```

```java
// 소거 후 컴파일러가 생성하는 코드
public class MyInteger implements Comparable {
    private int value;

    // 원본 메서드 (소거됨)
    public int compareTo(MyInteger other) {
        return Integer.compare(this.value, other.value);
    }

    // 컴파일러가 자동 생성한 Bridge 메서드 (다형성 유지)
    public int compareTo(Object other) { // Comparable.compareTo(Object) 구현
        return compareTo((MyInteger) other); // 캐스팅 후 위임
    }
}
```

`javap -c MyInteger.class`로 역어셈블하면 Bridge 메서드가 `ACC_BRIDGE`, `ACC_SYNTHETIC` 플래그와 함께 실제로 존재하는 것을 확인할 수 있습니다.

### 제네릭 배열 생성이 불가능한 이유

```java
// 컴파일 에러 — 제네릭 배열 생성 불가
List<String>[] stringLists = new List<String>[10]; // 컴파일 에러!
```

이것이 왜 위험한지 타입 소거와 함께 살펴봅니다.

```java
// 만약 허용된다면 발생하는 문제 (가상 시나리오)
List<String>[] stringLists = new List<String>[1]; // 가정
Object[] objects = stringLists;       // 배열은 공변이므로 OK
objects[0] = List.of(42);             // 런타임에 List<Integer> 삽입 — 배열은 타입 소거로 검사 못함
String s = stringLists[0].get(0);    // 런타임 ClassCastException!
```

배열은 런타임에 원소 타입을 검사하는 **reifiable 타입**이지만, 제네릭은 타입 소거로 런타임에 타입 정보가 없습니다. 이 충돌 때문에 제네릭 배열 생성을 금지합니다.

### instanceof 사용 불가 이유

```java
List<String> list = new ArrayList<>();

// 컴파일 에러 — 런타임에 타입 파라미터 정보가 없음
if (list instanceof List<String>) { } // 컴파일 에러!

// OK — 소거된 Raw 타입으로 instanceof 사용
if (list instanceof List) { }

// OK — 비한정 와일드카드는 허용 (Java 16 패턴 매칭 이전)
if (list instanceof List<?>) { }
```

런타임에는 `List<String>`과 `List<Integer>`를 구분할 방법이 없으므로 타입 파라미터를 포함한 `instanceof`는 의미가 없습니다.

---

## 7. 제네릭 제약사항

### 기본형 사용 불가 (int → Integer)

타입 파라미터는 참조 타입만 가능합니다. 기본형은 `Object`로 소거될 수 없기 때문입니다.

```java
List<int> list = new ArrayList<>();     // 컴파일 에러!
List<Integer> list = new ArrayList<>(); // OK — 래퍼 클래스 사용

Map<int, String> map = new HashMap<>();         // 컴파일 에러!
Map<Integer, String> map = new HashMap<>();     // OK
```

오토박싱/언박싱으로 실제 사용에서 불편함은 최소화됩니다.

```java
List<Integer> list = new ArrayList<>();
list.add(1);   // 오토박싱: int → Integer
int n = list.get(0); // 언박싱: Integer → int
```

### static 필드에 타입 파라미터 사용 불가

```java
public class Box<T> {
    private T value;          // OK — 인스턴스 필드

    // private static T sharedValue; // 컴파일 에러!
    // Box<String>.sharedValue와 Box<Integer>.sharedValue가 동일한 필드여야 하는데
    // T가 무엇인지 알 수 없음
}
```

`static` 필드는 모든 인스턴스가 공유하는데, `Box<String>`의 `T`와 `Box<Integer>`의 `T`가 다르므로 `static T` 필드는 의미가 없습니다.

### new T() 불가 — 타입 파라미터 인스턴스화 불가

```java
public class Creator<T> {
    public T create() {
        // return new T(); // 컴파일 에러! — 타입 소거로 T가 뭔지 모름
    }
}
```

해결책은 `Class<T>` 또는 `Supplier<T>`를 전달받는 것입니다.

```java
// Class<T> 전달 방식
public class Creator<T> {
    private final Class<T> type;

    public Creator(Class<T> type) {
        this.type = type;
    }

    public T create() throws ReflectiveOperationException {
        return type.getDeclaredConstructor().newInstance();
    }
}

Creator<ArrayList> creator = new Creator<>(ArrayList.class);
ArrayList list = creator.create();
```

```java
// Supplier<T> 전달 방식 (권장 — 리플렉션 불필요)
public class Creator<T> {
    private final Supplier<T> factory;

    public Creator(Supplier<T> factory) {
        this.factory = factory;
    }

    public T create() {
        return factory.get();
    }
}

Creator<ArrayList<String>> creator = new Creator<>(ArrayList::new);
ArrayList<String> list = creator.create();
```

### 제네릭 배열 생성 불가

앞서 설명한 것처럼 `new T[]`는 허용되지 않습니다.

```java
public class GenericArray<T> {
    private T[] array;

    @SuppressWarnings("unchecked")
    public GenericArray(int size) {
        // array = new T[size]; // 컴파일 에러!
        array = (T[]) new Object[size]; // 흔히 쓰는 우회 방법 (비검사 경고 발생)
    }

    // 더 안전한 방법: Class<T>를 받아서 Array.newInstance 사용
    @SuppressWarnings("unchecked")
    public GenericArray(Class<T> type, int size) {
        array = (T[]) java.lang.reflect.Array.newInstance(type, size);
    }
}
```

### 예외 클래스에 제네릭 불가

```java
// 컴파일 에러 — 제네릭 예외 클래스 정의 불가
public class GenericException<T> extends Exception { } // 컴파일 에러!
public class GenericException<T> extends Throwable { } // 컴파일 에러!

// catch 절에 타입 파라미터 사용 불가
public <T extends Exception> void method() {
    try {
        // ...
    } catch (T e) { // 컴파일 에러!
    }
}

// throws 절에는 타입 파라미터 사용 가능
public <T extends Exception> void method() throws T { // OK
    // ...
}
```

예외는 런타임에 실제 타입이 중요한데 타입 소거로 그 정보가 없기 때문에 제네릭 예외 클래스 정의와 `catch`절 사용이 금지됩니다.

---

## 8. 재귀적 타입 바운드 (Recursive Type Bound)

### Comparable 패턴

타입이 자기 자신과 비교 가능한 경우 자주 등장합니다.

```java
// T는 T 자신과 Comparable해야 함
public static <T extends Comparable<T>> T max(List<T> list) {
    if (list.isEmpty()) throw new NoSuchElementException();
    T result = list.get(0);
    for (T e : list) {
        if (e.compareTo(result) > 0) {
            result = e;
        }
    }
    return result;
}
```

```java
// 사용
List<String> words = List.of("banana", "apple", "cherry");
System.out.println(max(words)); // "cherry"

List<Integer> nums = List.of(3, 1, 4, 1, 5, 9);
System.out.println(max(nums)); // 9
```

`T extends Comparable<T>`는 "T는 T 자신과 비교할 수 있어야 한다"는 재귀적 표현입니다. 실제로 `String`은 `Comparable<String>`, `Integer`는 `Comparable<Integer>`를 구현합니다.

더 유연하게 만들려면 하한 와일드카드와 결합합니다.

```java
// Comparable<? super T>: T 또는 T의 슈퍼타입과 비교 가능한 경우도 허용
public static <T extends Comparable<? super T>> T max(List<T> list) {
    // ...
}
```

이는 Collections.max()의 실제 시그니처입니다.

### 빌더 패턴에서의 활용

상속 계층에서 빌더 패턴을 구현할 때 재귀 타입 바운드가 유용합니다.

```java
// 추상 빌더: B는 자신의 서브타입이어야 함 (Self-referential)
public abstract class Animal {
    private final String name;
    private final int age;

    protected Animal(Builder<?> builder) {
        this.name = builder.name;
        this.age = builder.age;
    }

    public abstract static class Builder<B extends Builder<B>> {
        private String name;
        private int age;

        @SuppressWarnings("unchecked")
        public B name(String name) {
            this.name = name;
            return (B) this; // 실제 서브타입 반환
        }

        @SuppressWarnings("unchecked")
        public B age(int age) {
            this.age = age;
            return (B) this;
        }

        public abstract Animal build();
    }
}
```

```java
public class Dog extends Animal {
    private final String breed;

    private Dog(Builder builder) {
        super(builder);
        this.breed = builder.breed;
    }

    public static class Builder extends Animal.Builder<Builder> {
        private String breed;

        public Builder breed(String breed) {
            this.breed = breed;
            return this; // Builder 자신 반환
        }

        @Override
        public Dog build() {
            return new Dog(this);
        }
    }
}
```

```java
// 사용 — 메서드 체이닝이 올바른 타입을 반환
Dog dog = new Dog.Builder()
        .name("바둑이")  // Animal.Builder<Builder>.name() → Builder 반환
        .age(3)          // Animal.Builder<Builder>.age() → Builder 반환
        .breed("진돗개") // Dog.Builder.breed() → Builder 반환
        .build();
```

재귀 타입 바운드 없이 `Animal.Builder`의 `name()`, `age()`가 `Animal.Builder`를 반환하면, `Dog.Builder`를 사용하다 `name()`을 호출하면 `Dog.Builder`가 아닌 `Animal.Builder`가 반환되어 이후 `breed()` 호출이 불가합니다.

---

## 9. 실무 활용 패턴

### 제네릭 DAO/Repository 패턴

데이터 접근 계층에서 공통 CRUD 로직을 재사용하는 패턴입니다.

```java
// 엔티티 기반 인터페이스
public interface CrudRepository<T, ID> {
    T save(T entity);
    Optional<T> findById(ID id);
    List<T> findAll();
    void deleteById(ID id);
    boolean existsById(ID id);
    long count();
}
```

```java
// 추상 구현 — JPA를 사용하는 공통 로직
public abstract class AbstractJpaRepository<T, ID> implements CrudRepository<T, ID> {
    private final EntityManager em;
    private final Class<T> entityClass;

    @SuppressWarnings("unchecked")
    protected AbstractJpaRepository(EntityManager em) {
        this.em = em;
        // 리플렉션으로 실제 타입 파라미터 추출 (슈퍼클래스의 제네릭 타입 인수)
        ParameterizedType type =
            (ParameterizedType) getClass().getGenericSuperclass();
        this.entityClass = (Class<T>) type.getActualTypeArguments()[0];
    }

    @Override
    public T save(T entity) {
        em.persist(entity);
        return entity;
    }

    @Override
    public Optional<T> findById(ID id) {
        return Optional.ofNullable(em.find(entityClass, id));
    }

    @Override
    public List<T> findAll() {
        String jpql = "SELECT e FROM " + entityClass.getSimpleName() + " e";
        return em.createQuery(jpql, entityClass).getResultList();
    }

    @Override
    public void deleteById(ID id) {
        findById(id).ifPresent(em::remove);
    }

    @Override
    public boolean existsById(ID id) {
        return findById(id).isPresent();
    }

    @Override
    public long count() {
        String jpql = "SELECT COUNT(e) FROM " + entityClass.getSimpleName() + " e";
        return em.createQuery(jpql, Long.class).getSingleResult();
    }
}
```

```java
// 구체 Repository — 엔티티별 특수 로직만 추가
@Repository
public class UserRepository extends AbstractJpaRepository<User, Long> {
    public UserRepository(EntityManager em) {
        super(em);
    }

    // 공통 CRUD는 상속, 도메인 특화 메서드만 추가
    public Optional<User> findByEmail(String email) {
        return em.createQuery(
                "SELECT u FROM User u WHERE u.email = :email", User.class)
                .setParameter("email", email)
                .getResultStream()
                .findFirst();
    }

    public List<User> findActiveUsers() {
        return em.createQuery(
                "SELECT u FROM User u WHERE u.active = true", User.class)
                .getResultList();
    }
}
```

### 제네릭 응답 래퍼 (ApiResponse\<T\>)

REST API 응답을 일관된 포맷으로 감싸는 패턴입니다.

```java
// 제네릭 응답 래퍼
public class ApiResponse<T> {
    private final boolean success;
    private final T data;
    private final String message;
    private final String errorCode;
    private final LocalDateTime timestamp;

    private ApiResponse(boolean success, T data, String message, String errorCode) {
        this.success = success;
        this.data = data;
        this.message = message;
        this.errorCode = errorCode;
        this.timestamp = LocalDateTime.now();
    }

    // 성공 응답 팩토리 메서드
    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(true, data, null, null);
    }

    public static <T> ApiResponse<T> success(T data, String message) {
        return new ApiResponse<>(true, data, message, null);
    }

    // 실패 응답 팩토리 메서드
    public static <T> ApiResponse<T> failure(String message, String errorCode) {
        return new ApiResponse<>(false, null, message, errorCode);
    }

    // 페이지네이션 래퍼
    public static <T> ApiResponse<PagedResult<T>> paged(
            List<T> content, int page, int size, long totalElements) {
        PagedResult<T> paged = new PagedResult<>(content, page, size, totalElements);
        return success(paged);
    }

    // getters...
    public boolean isSuccess() { return success; }
    public T getData() { return data; }
    public String getMessage() { return message; }
    public String getErrorCode() { return errorCode; }
    public LocalDateTime getTimestamp() { return timestamp; }
}
```

```java
// 페이지네이션 결과 래퍼
public class PagedResult<T> {
    private final List<T> content;
    private final int page;
    private final int size;
    private final long totalElements;
    private final int totalPages;

    public PagedResult(List<T> content, int page, int size, long totalElements) {
        this.content = content;
        this.page = page;
        this.size = size;
        this.totalElements = totalElements;
        this.totalPages = (int) Math.ceil((double) totalElements / size);
    }

    // getters...
    public List<T> getContent() { return content; }
    public int getPage() { return page; }
    public int getSize() { return size; }
    public long getTotalElements() { return totalElements; }
    public int getTotalPages() { return totalPages; }
    public boolean hasNext() { return page < totalPages - 1; }
    public boolean hasPrevious() { return page > 0; }
}
```

```java
// Controller에서 사용
@RestController
@RequestMapping("/api/users")
public class UserController {

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<UserDto>> getUser(@PathVariable Long id) {
        UserDto user = userService.findById(id);
        return ResponseEntity.ok(ApiResponse.success(user));
    }

    @GetMapping
    public ResponseEntity<ApiResponse<PagedResult<UserDto>>> getUsers(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        List<UserDto> users = userService.findAll(page, size);
        long total = userService.count();
        return ResponseEntity.ok(ApiResponse.paged(users, page, size, total));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<UserDto>> createUser(
            @RequestBody CreateUserRequest request) {
        try {
            UserDto created = userService.create(request);
            return ResponseEntity.status(HttpStatus.CREATED)
                    .body(ApiResponse.success(created, "사용자가 생성되었습니다."));
        } catch (DuplicateEmailException e) {
            return ResponseEntity.status(HttpStatus.CONFLICT)
                    .body(ApiResponse.failure("이미 존재하는 이메일입니다.", "USER_EMAIL_DUPLICATE"));
        }
    }
}
```

### 타입 안전한 이기종 컨테이너 (Typesafe Heterogeneous Container)

Effective Java 아이템 33에서 소개된 패턴입니다. 서로 다른 타입의 값을 하나의 컨테이너에 타입 안전하게 저장합니다.

```java
// 이기종 컨테이너: 키가 Class<T>, 값이 T
public class TypesafeContainer {
    private final Map<Class<?>, Object> container = new HashMap<>();

    // 타입 안전하게 저장
    public <T> void put(Class<T> type, T value) {
        container.put(Objects.requireNonNull(type), value);
    }

    // 타입 안전하게 조회
    public <T> T get(Class<T> type) {
        return type.cast(container.get(type)); // Class.cast()로 안전하게 캐스팅
    }

    public <T> Optional<T> getOptional(Class<T> type) {
        return Optional.ofNullable(get(type));
    }

    public <T> boolean contains(Class<T> type) {
        return container.containsKey(type);
    }

    public <T> void remove(Class<T> type) {
        container.remove(type);
    }
}
```

```java
// 사용
TypesafeContainer container = new TypesafeContainer();

container.put(String.class, "hello");
container.put(Integer.class, 42);
container.put(Double.class, 3.14);
container.put(LocalDate.class, LocalDate.now());

String s = container.get(String.class);    // "hello" — 캐스팅 불필요
int n = container.get(Integer.class);      // 42
double d = container.get(Double.class);    // 3.14
LocalDate date = container.get(LocalDate.class);

// 다른 타입을 get하면 null 반환 (ClassCastException 없음)
Long l = container.get(Long.class); // null
```

이 패턴의 핵심은 `Class<T>` 자체가 타입 토큰(Type Token)으로 키 역할을 하면서 값의 타입 정보를 보장한다는 점입니다.

```java
// 한계: 런타임 타입 토큰 — List<String>.class는 존재하지 않음
// container.put(List<String>.class, ...); // 컴파일 에러!

// 슈퍼 타입 토큰으로 해결 (Guava TypeToken 또는 직접 구현)
// 익명 클래스의 제네릭 슈퍼클래스 정보는 런타임에도 접근 가능
public abstract class TypeToken<T> {
    private final Type type;

    protected TypeToken() {
        ParameterizedType superClass = (ParameterizedType) getClass().getGenericSuperclass();
        this.type = superClass.getActualTypeArguments()[0];
    }

    public Type getType() { return type; }
}

// 사용
TypeToken<List<String>> token = new TypeToken<List<String>>() {};
System.out.println(token.getType()); // java.util.List<java.lang.String>
```

---

## 정리

제네릭을 올바르게 사용하면 다음 이점을 얻습니다.

| 항목 | 내용 |
|------|------|
| **타입 안전성** | 컴파일 타임에 타입 오류를 차단하여 런타임 `ClassCastException` 방지 |
| **캐스팅 제거** | 컬렉션에서 꺼낼 때 명시적 캐스팅 불필요 |
| **코드 재사용** | 하나의 클래스/메서드로 여러 타입 처리 가능 |
| **가독성** | 코드의 의도와 타입 관계가 명확히 드러남 |

핵심 규칙을 정리하면 다음과 같습니다.

- **PECS**: 데이터를 읽으면 `extends`, 쓰면 `super`
- **타입 소거**: 제네릭 정보는 런타임에 없음. `instanceof`와 배열 생성에 주의
- **new T() 불가**: `Supplier<T>` 또는 `Class<T>`를 주입받아 해결
- **기본형 불가**: 래퍼 클래스(`Integer`, `Double` 등)로 대체
- **반환 타입에 와일드카드 금지**: 호출자가 불편해짐
- **재귀 타입 바운드**: 자기 자신과 비교/체이닝이 필요할 때 `T extends Comparable<T>` 패턴 활용
