---
title: "Java Object 클래스 완전 정리"
categories:
- JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

Java의 모든 클래스는 명시적으로 상속을 선언하지 않아도 `java.lang.Object`를 최상위 부모로 가집니다. Object 클래스가 제공하는 메서드들은 Java 객체 시스템의 근간을 이루며, 이를 올바르게 이해하고 오버라이딩하는 것은 Java 개발의 핵심입니다.

---

## 1. Object 클래스가 최상위 부모인 이유

### 단일 루트 계층 구조

Java는 **단일 루트 계층(Single Root Hierarchy)** 을 채택합니다. 모든 클래스가 Object를 상속하므로 다음이 보장됩니다.

```
Object
  ├── String
  ├── Integer
  ├── ArrayList
  ├── MyCustomClass
  └── ... (모든 클래스)
```

```java
// 명시적 선언 없어도 동일
class Foo { }
class Foo extends Object { }  // 컴파일러가 자동으로 추가
```

### 단일 루트가 주는 이점

| 이점 | 설명 |
|------|------|
| 다형성 기반 | `Object` 타입으로 모든 객체 참조 가능 |
| 공통 동작 보장 | toString, equals, hashCode 등 기본 구현 제공 |
| 제네릭 상한 | `<T>` 의 암묵적 상한이 Object |
| 리플렉션 | `getClass()` 를 통해 런타임 타입 정보 획득 |

```java
// 모든 객체를 Object로 다룰 수 있음
Object obj = new ArrayList<>();
Object obj2 = "Hello";
Object obj3 = 42;  // 오토박싱 → Integer → Object
```

### Object의 전체 메서드 목록

```java
public class Object {
    // 객체 정보
    public final Class<?> getClass()
    public String toString()

    // 동등성 / 해시
    public boolean equals(Object obj)
    public int hashCode()

    // 복사
    protected Object clone() throws CloneNotSupportedException

    // 스레드 동기화
    public final void wait() throws InterruptedException
    public final void wait(long timeoutMillis) throws InterruptedException
    public final void wait(long timeoutMillis, int nanos) throws InterruptedException
    public final void notify()
    public final void notifyAll()

    // GC 관련 (Java 9 deprecated)
    protected void finalize() throws Throwable
}
```

---

## 2. toString()

### 기본 동작

Object의 기본 `toString()`은 다음과 같이 구현되어 있습니다.

```java
// Object.toString() 기본 구현
public String toString() {
    return getClass().getName() + "@" + Integer.toHexString(hashCode());
}
```

```java
class Point {
    int x, y;
    Point(int x, int y) { this.x = x; this.y = y; }
}

Point p = new Point(3, 4);
System.out.println(p);  // Point@1b6d3586 (쓸모없는 출력)
```

### 오버라이딩 패턴

```java
class Point {
    int x, y;

    Point(int x, int y) {
        this.x = x;
        this.y = y;
    }

    @Override
    public String toString() {
        return "Point{x=" + x + ", y=" + y + "}";
    }
}

System.out.println(new Point(3, 4));  // Point{x=3, y=4}
```

### toString()이 자동 호출되는 상황

```java
Point p = new Point(3, 4);

// 모두 toString()을 암묵적으로 호출
System.out.println(p);           // println(Object)
String s = "좌표: " + p;        // 문자열 연결
String.format("p = %s", p);     // %s 포맷
log.info("point={}", p);        // 대부분의 로거
```

### 실무 패턴: Lombok, Record

```java
// Lombok
@ToString
class Point {
    int x, y;
}

// Java 16+ Record (toString 자동 생성)
record Point(int x, int y) { }
System.out.println(new Point(3, 4));  // Point[x=3, y=4]
```

---

## 3. equals()

### 동일성(Identity) vs 동등성(Equality)

```
동일성 (==)                동등성 (equals)
┌─────────────────┐        ┌─────────────────┐
│  같은 메모리    │        │  내용이 같은가? │
│  주소인가?      │        │  (논리적 동등)  │
└─────────────────┘        └─────────────────┘

String a = new String("hello");
String b = new String("hello");

a == b       → false  (다른 객체)
a.equals(b)  → true   (내용 동일)
```

### Object의 기본 equals()

```java
// Object 기본 구현 — 동일성과 동일
public boolean equals(Object obj) {
    return (this == obj);
}
```

### equals() 올바른 오버라이딩 — 5가지 규칙

Java 명세가 요구하는 `equals()` 계약(contract)입니다.

#### 규칙 1: 반사성 (Reflexivity)
```java
// x.equals(x) == true
Point p = new Point(1, 2);
assert p.equals(p);  // 항상 true
```

#### 규칙 2: 대칭성 (Symmetry)
```java
// x.equals(y) == y.equals(x)
Point a = new Point(1, 2);
Point b = new Point(1, 2);
assert a.equals(b) == b.equals(a);  // 항상 동일

// 위반 예시 (잘못된 구현)
class BadPoint {
    @Override
    public boolean equals(Object obj) {
        if (obj instanceof String) return toString().equals(obj);
        // Point와 String을 비교 — 대칭성 위반!
        return super.equals(obj);
    }
}
```

#### 규칙 3: 추이성 (Transitivity)
```java
// x.equals(y) && y.equals(z) → x.equals(z)
// 상속 시 추이성 위반이 발생하기 쉬움

class ColorPoint extends Point {
    Color color;

    @Override
    public boolean equals(Object obj) {
        if (!(obj instanceof Point)) return false;
        if (!(obj instanceof ColorPoint))
            return super.equals(obj);  // color 무시 — 추이성 위반 가능
        return super.equals(obj) && color == ((ColorPoint) obj).color;
    }
}
// 해결책: 상속 대신 컴포지션 사용
```

#### 규칙 4: 일관성 (Consistency)
```java
// 객체가 변하지 않는 한 equals()는 항상 같은 결과
// 가변 상태에 의존하지 말 것
```

#### 규칙 5: null 비교
```java
// x.equals(null) == false (예외 발생 X)
Point p = new Point(1, 2);
assert !p.equals(null);  // NullPointerException 아님
```

### 올바른 equals() 구현 템플릿

```java
class Point {
    private final int x;
    private final int y;

    public Point(int x, int y) {
        this.x = x;
        this.y = y;
    }

    @Override
    public boolean equals(Object obj) {
        // 1. 자기 자신 비교 (성능 최적화)
        if (this == obj) return true;

        // 2. null 체크 + 타입 체크
        if (!(obj instanceof Point)) return false;

        // 3. 타입 캐스팅
        Point other = (Point) obj;

        // 4. 핵심 필드 비교
        return this.x == other.x && this.y == other.y;
    }
}
```

### Java 14+ record — equals 자동 생성

```java
record Point(int x, int y) { }
// equals(), hashCode(), toString() 자동 생성
// 모든 필드를 기준으로 동등성 비교
```

---

## 4. hashCode()

### hashCode() 계약

1. **일관성**: 같은 실행 내에서 반복 호출 시 같은 값
2. **equals 연동**: `a.equals(b)` → `a.hashCode() == b.hashCode()` (역은 성립 안 해도 됨)
3. **충돌 최소화**: 다른 객체는 가급적 다른 해시코드 (성능)

```
equals()가 true  →  hashCode() 반드시 같아야 함
equals()가 false →  hashCode() 달라도 되지만, 같으면 성능 저하
```

### hashCode()와 HashMap의 관계

```
put(key, value) 과정:
┌────────────────────────────────────────────┐
│ 1. key.hashCode() 호출                     │
│ 2. 해시값으로 버킷(bucket) 인덱스 결정     │
│ 3. 해당 버킷에서 key.equals() 로 탐색      │
│ 4. 일치하면 value 저장/반환                │
└────────────────────────────────────────────┘

버킷 구조:
[0] → null
[1] → (key="A", val=1) → (key="B", val=2)  ← 해시 충돌 시 체이닝
[2] → (key="C", val=3)
...
```

```java
// hashCode를 오버라이딩하지 않으면 HashMap이 망가짐
class BadPoint {
    int x, y;

    @Override
    public boolean equals(Object obj) {
        if (!(obj instanceof BadPoint)) return false;
        BadPoint o = (BadPoint) obj;
        return x == o.x && y == o.y;
    }
    // hashCode 오버라이딩 안 함!
}

Map<BadPoint, String> map = new HashMap<>();
BadPoint p1 = new BadPoint(1, 2);
map.put(p1, "hello");

BadPoint p2 = new BadPoint(1, 2);  // p1과 equals는 true
map.get(p2);  // null 반환! hashCode가 달라 다른 버킷 탐색
```

### 올바른 hashCode() 구현

```java
class Point {
    private final int x;
    private final int y;

    @Override
    public int hashCode() {
        // Java 7+: Objects.hash() 활용 (간단하지만 약간 느림)
        return Objects.hash(x, y);
    }

    // 또는 직접 구현 (성능 중시)
    @Override
    public int hashCode() {
        int result = 17;           // 임의의 홀수 소수
        result = 31 * result + x;  // 31: 소수, 비트 시프트 최적화
        result = 31 * result + y;
        return result;
    }
}
```

### 해시 코드 캐싱 (불변 객체)

```java
// 불변 객체에서 해시코드 캐싱
class ImmutablePoint {
    private final int x;
    private final int y;
    private int hashCode;  // 기본값 0

    @Override
    public int hashCode() {
        int result = hashCode;
        if (result == 0) {
            result = Objects.hash(x, y);
            hashCode = result;
        }
        return result;
    }
}
```

---

## 5. clone()

### clone()의 기본 동작

```java
protected native Object clone() throws CloneNotSupportedException;
```

- `native` 메서드 — JVM이 직접 메모리 복사
- `Cloneable` 마커 인터페이스를 구현해야 사용 가능
- 구현하지 않으면 `CloneNotSupportedException` 발생

### 얕은 복사(Shallow Copy) vs 깊은 복사(Deep Copy)

```
얕은 복사:
┌──────────┐     ┌──────────┐
│ original │     │  clone   │
│  arr ────┼────►│  arr ────┼────► [1, 2, 3]  (같은 배열!)
└──────────┘     └──────────┘

깊은 복사:
┌──────────┐     ┌──────────┐
│ original │     │  clone   │
│  arr ────┼────►[1, 2, 3]  │  arr ────► [1, 2, 3]  (다른 배열)
└──────────┘     └──────────┘
```

```java
class ShallowExample implements Cloneable {
    int[] data;

    ShallowExample(int[] data) {
        this.data = data;
    }

    @Override
    public ShallowExample clone() {
        try {
            return (ShallowExample) super.clone();  // 얕은 복사
        } catch (CloneNotSupportedException e) {
            throw new AssertionError();
        }
    }
}

ShallowExample a = new ShallowExample(new int[]{1, 2, 3});
ShallowExample b = a.clone();
b.data[0] = 99;
System.out.println(a.data[0]);  // 99! — 같은 배열을 참조
```

```java
class DeepExample implements Cloneable {
    int[] data;

    @Override
    public DeepExample clone() {
        try {
            DeepExample clone = (DeepExample) super.clone();
            clone.data = data.clone();  // 배열도 복사 — 깊은 복사
            return clone;
        } catch (CloneNotSupportedException e) {
            throw new AssertionError();
        }
    }
}
```

### Cloneable의 문제점과 대안

```java
// clone()의 문제점
// 1. CloneNotSupportedException — checked 예외로 사용 불편
// 2. 얕은 복사 기본값 — 실수하기 쉬움
// 3. 생성자 없이 객체 생성 — 불변 보장 어려움
// 4. final 필드와 충돌

// 권장 대안 1: 복사 생성자(Copy Constructor)
class Point {
    int x, y;
    Point(int x, int y) { this.x = x; this.y = y; }

    // 복사 생성자
    Point(Point other) {
        this.x = other.x;
        this.y = other.y;
    }
}

// 권장 대안 2: 정적 팩토리 메서드
class Point {
    static Point copyOf(Point other) {
        return new Point(other.x, other.y);
    }
}

// 권장 대안 3: 방어적 복사(Defensive Copy)
class Period {
    private final Date start;
    private final Date end;

    // 입력 방어
    public Period(Date start, Date end) {
        this.start = new Date(start.getTime());  // 복사본 저장
        this.end   = new Date(end.getTime());
    }

    // 출력 방어
    public Date getStart() {
        return new Date(start.getTime());  // 복사본 반환
    }
}
```

---

## 6. getClass()

```java
public final Class<?> getClass()
```

런타임에 객체의 실제 타입을 반환합니다. `final`이므로 오버라이딩 불가.

```java
Object obj = new ArrayList<String>();
Class<?> cls = obj.getClass();

System.out.println(cls.getName());        // java.util.ArrayList
System.out.println(cls.getSimpleName()); // ArrayList
System.out.println(cls.getSuperclass()); // class java.util.AbstractList

// instanceof vs getClass()
obj instanceof List      // true (다형성 고려)
obj.getClass() == List.class  // false! (정확한 타입만)
obj.getClass() == ArrayList.class  // true

// 리플렉션 활용
Method[] methods = cls.getDeclaredMethods();
Field[]  fields  = cls.getDeclaredFields();
```

### 타입 비교 시 주의

```java
// equals에서 타입 비교: instanceof vs getClass()

// instanceof — 하위 클래스 허용 (리스코프 치환 원칙 친화)
if (obj instanceof Point) { ... }

// getClass() — 정확히 같은 타입만 (대칭성 보장 쉬움)
if (obj.getClass() == getClass()) { ... }
```

---

## 7. finalize()

### Java 9에서 deprecated, Java 18에서 제거 예정

```java
// Object.finalize() — 절대 사용하지 말 것
@Deprecated(since="9")
protected void finalize() throws Throwable { }
```

### 문제점

```
finalize()의 문제점:
1. GC 호출 시점 보장 없음 — 언제 실행될지 모름
2. 성능 저하 — GC가 finalize 객체를 별도 큐에서 관리
3. 예외 무시 — finalize 내부 예외가 조용히 사라짐
4. 보안 취약점 — finalize 공격(finalizer attack) 가능
```

### 올바른 대안: AutoCloseable + try-with-resources

```java
// 리소스 해제는 AutoCloseable로
class Resource implements AutoCloseable {
    public Resource() {
        System.out.println("리소스 열림");
    }

    @Override
    public void close() {
        System.out.println("리소스 닫힘");
    }
}

// try-with-resources로 자동 close()
try (Resource r = new Resource()) {
    // 사용
}  // 자동으로 r.close() 호출
```

---

## 8. wait() / notify() / notifyAll()

### 스레드 협력 메커니즘

이 메서드들은 `synchronized` 블록 안에서만 호출할 수 있습니다.

```java
class SharedBuffer {
    private final Queue<Integer> buffer = new LinkedList<>();
    private final int MAX_SIZE = 10;

    // 생산자
    public synchronized void produce(int value) throws InterruptedException {
        while (buffer.size() == MAX_SIZE) {
            wait();  // 버퍼 가득 참 → 대기
        }
        buffer.add(value);
        notifyAll();  // 소비자 깨우기
    }

    // 소비자
    public synchronized int consume() throws InterruptedException {
        while (buffer.isEmpty()) {
            wait();  // 버퍼 비어 있음 → 대기
        }
        int value = buffer.poll();
        notifyAll();  // 생산자 깨우기
        return value;
    }
}
```

```
wait() 동작:
1. 현재 스레드가 monitor lock 해제
2. WAITING 상태로 전환
3. notify/notifyAll 또는 인터럽트 시 깨어남
4. 다시 lock 획득 후 재개

notify()   → 대기 중인 스레드 1개 임의 깨움
notifyAll() → 대기 중인 모든 스레드 깨움 (권장)
```

> 실무에서는 `java.util.concurrent` 패키지의 `Lock`, `Condition`, `BlockingQueue`를 우선 사용합니다.

---

## 9. 전체 요약

```
Object 메서드 오버라이딩 가이드:
┌─────────────┬──────────────────────────────────────────────┐
│  메서드     │  핵심 규칙                                   │
├─────────────┼──────────────────────────────────────────────┤
│ toString()  │ 항상 오버라이딩, 디버깅에 유용               │
│ equals()    │ 5가지 계약 준수, hashCode와 함께             │
│ hashCode()  │ equals와 일관성 필수, HashMap 정상 동작      │
│ clone()     │ Cloneable 필요, 복사 생성자 대안 권장        │
│ getClass()  │ final, 오버라이딩 불가, 리플렉션 활용        │
│ finalize()  │ 절대 사용 금지, AutoCloseable 사용           │
│ wait/notify │ synchronized 내부에서만, concurrent 패키지 선호│
└─────────────┴──────────────────────────────────────────────┘

황금 법칙:
equals()를 오버라이딩하면 반드시 hashCode()도 오버라이딩하라.
```
