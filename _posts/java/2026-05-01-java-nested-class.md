---
title: "Java 중첩 클래스 완전 정리"
categories:
- JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

Java는 클래스 안에 클래스를 선언할 수 있습니다. 이를 중첩 클래스(Nested Class)라고 하며, 종류에 따라 동작 방식과 사용 목적이 크게 다릅니다. 잘못 사용하면 메모리 누수의 원인이 되기도 하므로, 각각의 특성을 정확히 이해하는 것이 중요합니다.

---

## 1. 중첩 클래스 종류 전체 구조

```
중첩 클래스 (Nested Class):
┌─────────────────────────────────────────────────────┐
│                  Nested Class                       │
│                                                     │
│  ┌──────────────────────┐  ┌───────────────────┐   │
│  │  Static Nested Class │  │   Inner Class     │   │
│  │  (정적 중첩 클래스)  │  │   (내부 클래스)   │   │
│  └──────────────────────┘  └─────────┬─────────┘   │
│                                      │              │
│                          ┌───────────┼───────────┐  │
│                          │           │           │  │
│                   Member Inner  Local Inner  Anonymous│
│                   (멤버 내부)  (지역 내부)  (익명)   │
└─────────────────────────────────────────────────────┘
```

| 종류 | static | 외부 인스턴스 참조 | 선언 위치 |
|------|--------|-------------------|-----------|
| Static Nested Class | O | X | 클래스 멤버 |
| Member Inner Class | X | O | 클래스 멤버 |
| Local Inner Class | X | O | 메서드 내부 |
| Anonymous Class | X | O | 표현식 위치 |

---

## 2. Static 중첩 클래스 (Static Nested Class)

### 특징

```java
public class Outer {
    private static String staticField = "static";
    private String instanceField = "instance";

    // static 중첩 클래스
    public static class StaticNested {
        public void show() {
            System.out.println(staticField);    // OK — static 멤버 접근 가능
            // System.out.println(instanceField); // 컴파일 에러! — 인스턴스 멤버 접근 불가
        }
    }
}

// 사용 — Outer 인스턴스 불필요
Outer.StaticNested nested = new Outer.StaticNested();
nested.show();
```

```
메모리 구조:
Outer 인스턴스 없이 독립적으로 생성 가능

StaticNested ──► (Outer의 인스턴스를 참조하지 않음)
```

### 사용 시점

```java
// 1. 외부 클래스와 논리적으로 연관되지만 독립적인 클래스
public class LinkedList<E> {
    // Node는 LinkedList의 구현 세부사항
    private static class Node<E> {
        E item;
        Node<E> next;
        Node<E> prev;

        Node(E element, Node<E> next, Node<E> prev) {
            this.item = element;
            this.next = next;
            this.prev = prev;
        }
    }
}

// 2. 빌더 패턴
public class Person {
    private final String name;
    private final int age;
    private final String email;

    private Person(Builder builder) {
        this.name  = builder.name;
        this.age   = builder.age;
        this.email = builder.email;
    }

    public static class Builder {
        private String name;
        private int age;
        private String email;

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder age(int age) {
            this.age = age;
            return this;
        }

        public Builder email(String email) {
            this.email = email;
            return this;
        }

        public Person build() {
            return new Person(this);
        }
    }
}

// 사용
Person person = new Person.Builder()
    .name("Alice")
    .age(30)
    .email("alice@example.com")
    .build();
```

---

## 3. 멤버 내부 클래스 (Member Inner Class)

### 특징

```java
public class Outer {
    private String name = "Outer";

    // 멤버 내부 클래스
    public class Inner {
        private String name = "Inner";

        public void show() {
            // 외부 클래스 인스턴스 멤버 접근 가능
            System.out.println(name);          // "Inner" — 자신의 필드
            System.out.println(Outer.this.name); // "Outer" — 외부 참조
        }
    }
}

// 사용 — Outer 인스턴스 필요!
Outer outer = new Outer();
Outer.Inner inner = outer.new Inner();  // 독특한 문법
inner.show();
```

```
메모리 구조:
Inner 인스턴스는 Outer 인스턴스에 대한 숨겨진 참조를 보유

┌─────────────────────┐
│  Outer 인스턴스     │
│  name = "Outer"     │
└─────────┬───────────┘
          ▲
          │ 숨겨진 참조 (this$0)
┌─────────┴───────────┐
│  Inner 인스턴스     │
│  name = "Inner"     │
│  this$0 ────────────┘
└─────────────────────┘
```

### 실제 컴파일 결과

```java
// 컴파일러가 생성하는 Inner 클래스 (대략)
class Outer$Inner {
    private String name;
    final Outer this$0;  // 외부 클래스 참조 — 메모리 누수 원인!

    Outer$Inner(Outer outer) {
        this.this$0 = outer;
        this.name = "Inner";
    }
}
```

### Outer.this 사용

```java
public class ScrollPane {
    private String scrollMode = "smooth";

    public class Adjustable {
        private String scrollMode = "step";

        public void scroll() {
            System.out.println(scrollMode);            // "step" (자신)
            System.out.println(ScrollPane.this.scrollMode); // "smooth" (외부)
        }
    }
}
```

---

## 4. 지역 내부 클래스 (Local Inner Class)

### 특징

```java
public class Outer {
    public void method() {
        final String localVar = "local";  // 사실상 final이어야 함 (effectively final)

        // 메서드 내부에서 클래스 선언
        class LocalInner {
            public void show() {
                System.out.println(localVar);  // 지역 변수 접근 가능
            }
        }

        LocalInner local = new LocalInner();
        local.show();
    }
}
```

### effectively final 규칙

```java
public void method() {
    int x = 10;
    // x = 20;  // 주석 해제 시 아래 익명/지역 내부 클래스에서 에러

    class Inner {
        void show() {
            System.out.println(x);  // x가 effectively final이어야 함
        }
    }
}
```

### 사용 시점

지역 내부 클래스는 드물게 사용됩니다. 해당 메서드 내에서만 쓰이며, 익명 클래스보다 이름이 필요할 때 사용합니다.

---

## 5. 익명 클래스 (Anonymous Class)

### 특징

```java
// 인터페이스나 추상 클래스를 즉석에서 구현
Runnable r = new Runnable() {
    @Override
    public void run() {
        System.out.println("익명 클래스 실행");
    }
};
r.run();

// 추상 클래스 익명 구현
abstract class Greeting {
    abstract void greet();
    void common() { System.out.println("공통 동작"); }
}

Greeting g = new Greeting() {
    @Override
    void greet() {
        System.out.println("안녕하세요!");
    }
};
g.greet();
g.common();
```

### 컴파일 결과

```
Outer.class
Outer$1.class  ← 익명 클래스 1번
Outer$2.class  ← 익명 클래스 2번
```

### 익명 클래스의 캡처

```java
String prefix = "Hello";  // effectively final

Runnable r = new Runnable() {
    @Override
    public void run() {
        System.out.println(prefix);  // 외부 변수 캡처
    }
};
```

---

## 6. 익명 클래스 → 람다 전환

### Java 8 이전 vs 이후

```java
// Java 8 이전 — 익명 클래스
List<String> list = Arrays.asList("banana", "apple", "cherry");
Collections.sort(list, new Comparator<String>() {
    @Override
    public int compare(String a, String b) {
        return a.compareTo(b);
    }
});

// Java 8+ — 람다 (함수형 인터페이스)
list.sort((a, b) -> a.compareTo(b));

// 메서드 참조
list.sort(String::compareTo);
```

### 람다로 전환 가능한 조건

```java
// 함수형 인터페이스(추상 메서드 1개)만 람다로 전환 가능

// O — 람다 가능 (메서드 1개)
Runnable r = () -> System.out.println("run");
Comparator<String> c = (a, b) -> a.compareTo(b);
Predicate<Integer> p = n -> n > 0;
Function<String, Integer> f = Integer::parseInt;

// X — 람다 불가 (추상 메서드 2개 이상)
abstract class TwoMethods {
    abstract void foo();
    abstract void bar();
}
// 위는 익명 클래스만 가능
```

### 익명 클래스 vs 람다 차이

```java
// 1. this 의미 다름
Runnable r1 = new Runnable() {
    public void run() {
        System.out.println(this);  // 익명 클래스 인스턴스
    }
};

Runnable r2 = () -> System.out.println(this);  // 외부 클래스 인스턴스!

// 2. 람다는 상태(필드)를 가질 수 없음
Runnable counter = new Runnable() {
    int count = 0;  // 가능
    public void run() { count++; }
};

// 람다에는 필드 선언 불가
Runnable lambdaCounter = () -> { /* count++ 불가 */ };

// 3. 익명 클래스는 여러 메서드 구현 가능
```

---

## 7. 메모리 누수 주의사항

### 내부 클래스의 외부 참조 문제

```java
// 위험한 패턴 — Activity / Fragment에서 자주 발생
public class MyActivity {
    private String data = "중요 데이터";

    // 멤버 내부 클래스 — Outer 인스턴스 강하게 참조
    class MyTask implements Runnable {
        @Override
        public void run() {
            // data 접근 시 MyActivity 참조 유지
            System.out.println(data);
        }
    }

    public void startTask() {
        // MyTask가 백그라운드 스레드에서 실행되면
        // 스레드가 살아있는 동안 MyActivity 전체가 GC 불가!
        new Thread(new MyTask()).start();
    }
}
```

```
메모리 누수 구조:
Thread (GC Root)
    └── MyTask 인스턴스 (Runnable)
            └── this$0 ──► MyActivity (GC 불가!)
                                └── 모든 필드, 뷰, 리소스...
```

### 해결 방법 1: Static Nested Class + WeakReference

```java
public class MyActivity {
    private String data = "중요 데이터";

    // static → 외부 참조 없음
    static class MyTask implements Runnable {
        private final WeakReference<MyActivity> activityRef;

        MyTask(MyActivity activity) {
            this.activityRef = new WeakReference<>(activity);
        }

        @Override
        public void run() {
            MyActivity activity = activityRef.get();
            if (activity != null) {  // null 체크 필수
                System.out.println(activity.data);
            }
            // activity가 GC되었으면 아무것도 안 함
        }
    }

    public void startTask() {
        new Thread(new MyTask(this)).start();
    }
}
```

### 해결 방법 2: 람다 캡처 주의

```java
public class EventSource {
    private final List<Runnable> listeners = new ArrayList<>();

    public void addListener(Runnable listener) {
        listeners.add(listener);
    }

    // 위험: this 전체를 캡처
    public void badRegister() {
        addListener(() -> processData(this.data));  // this 캡처 → 누수 가능
    }

    // 안전: 필요한 값만 캡처
    public void safeRegister() {
        String snapshot = this.data;  // 값만 복사
        addListener(() -> processData(snapshot));
    }
}
```

### 해결 방법 3: 명시적 제거

```java
// 리스너 등록 시 항상 제거 쌍을 고려
EventBus.register(this);
// ...
EventBus.unregister(this);  // 반드시 제거

// try-finally 또는 AutoCloseable 패턴
class MyComponent implements AutoCloseable {
    MyComponent() { EventBus.register(this); }

    @Override
    public void close() { EventBus.unregister(this); }
}
```

---

## 8. 실무 활용 패턴

### Iterator 패턴

```java
public class NumberRange implements Iterable<Integer> {
    private final int start;
    private final int end;

    public NumberRange(int start, int end) {
        this.start = start;
        this.end = end;
    }

    @Override
    public Iterator<Integer> iterator() {
        return new Iterator<Integer>() {
            private int current = start;

            @Override
            public boolean hasNext() { return current <= end; }

            @Override
            public Integer next() {
                if (!hasNext()) throw new NoSuchElementException();
                return current++;
            }
        };
    }
}

// 사용
for (int n : new NumberRange(1, 5)) {
    System.out.println(n);  // 1 2 3 4 5
}
```

### 이벤트 리스너 패턴

```java
// Java Swing 스타일 (레거시)
button.addActionListener(new ActionListener() {
    @Override
    public void actionPerformed(ActionEvent e) {
        System.out.println("클릭!");
    }
});

// 람다로 전환 (현대적)
button.addActionListener(e -> System.out.println("클릭!"));
```

### 테스트에서의 활용

```java
// 테스트 더블(Test Double) — 익명 클래스
interface UserRepository {
    User findById(long id);
}

UserRepository mockRepo = new UserRepository() {
    @Override
    public User findById(long id) {
        return new User(id, "Test User");  // 항상 테스트 데이터 반환
    }
};

// 현대적: Mockito 또는 람다
UserRepository mockRepo = id -> new User(id, "Test User");
```

### 팩토리 메서드와 익명 클래스

```java
public abstract class Template {
    public final void execute() {
        step1();
        step2();  // 추상 — 하위 구현
        step3();
    }

    protected abstract void step2();

    protected void step1() { System.out.println("Step 1"); }
    protected void step3() { System.out.println("Step 3"); }
}

// 즉석 구현
Template t = new Template() {
    @Override
    protected void step2() {
        System.out.println("커스텀 Step 2");
    }
};
t.execute();
```

---

## 9. 전체 요약

```
중첩 클래스 선택 가이드:
┌──────────────────────┬────────────────────────────────────┐
│  종류                │  사용 시점                         │
├──────────────────────┼────────────────────────────────────┤
│ Static Nested Class  │ 외부 인스턴스 불필요, 논리적 그룹화│
│                      │ 빌더, 노드 등 구현 세부 클래스     │
├──────────────────────┼────────────────────────────────────┤
│ Member Inner Class   │ 외부 클래스 인스턴스 접근 필요     │
│                      │ Iterator, 이벤트 핸들러 등         │
├──────────────────────┼────────────────────────────────────┤
│ Local Inner Class    │ 메서드 내 일회성, 이름이 필요할 때 │
│                      │ (드물게 사용)                      │
├──────────────────────┼────────────────────────────────────┤
│ Anonymous Class      │ 인터페이스 즉석 구현               │
│                      │ 함수형 인터페이스면 람다로 대체    │
└──────────────────────┴────────────────────────────────────┘

핵심 규칙:
1. 외부 인스턴스가 필요 없으면 → static 중첩 클래스 우선
2. 멤버 내부 클래스 + 백그라운드 작업 → 메모리 누수 주의
3. 함수형 인터페이스 → 람다로 교체
4. this$0 참조를 항상 인식하고 설계할 것
```
