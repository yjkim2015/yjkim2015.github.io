---
title: "Java 중첩 클래스"
categories:
- JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

Java는 클래스 안에 클래스를 선언할 수 있습니다. 이를 중첩 클래스(Nested Class)라고 하며, 종류에 따라 동작 방식과 사용 목적이 크게 다릅니다. 잘못 사용하면 메모리 누수의 원인이 되기도 하므로, 각각의 특성을 정확히 이해하는 것이 중요합니다.

> **비유:** 중첩 클래스는 "건물 안의 방"입니다. Static 중첩 클래스는 건물과 독립적인 임대 사무실(열쇠만 있으면 누구든 출입)이고, 멤버 내부 클래스는 건물주 전용 방(건물주가 없으면 방 자체가 존재할 수 없음)입니다. 건물주 전용 방은 건물주가 이사 가도(GC 대상) 세입자(내부 클래스)가 열쇠를 쥐고 있으면 건물을 비울 수 없습니다(메모리 누수).

---

## 1. 중첩 클래스 종류 전체 구조

중첩 클래스의 가장 중요한 분류 기준은 **외부 클래스 인스턴스에 대한 참조를 보유하는가** 여부입니다. `static`으로 선언된 중첩 클래스는 외부 참조가 없어 독립적으로 생성 가능하고, 비static(inner) 클래스는 항상 외부 인스턴스를 참조합니다. 이 차이가 메모리 누수 가능성을 결정합니다.

```mermaid
graph TD
    A["중첩 클래스 (Nested Class)"] --> B["Static Nested Class\n정적 중첩 클래스"]
    A --> C["Inner Class\n내부 클래스"]
    C --> D["Member Inner Class\n멤버 내부 클래스"]
    C --> E["Local Inner Class\n지역 내부 클래스"]
    C --> F["Anonymous Class\n익명 클래스"]
    B --> B1["외부 인스턴스 참조 없음\n독립 생성 가능"]
    D --> D1["외부 인스턴스 참조 보유\nouter.new Inner() 문법"]
    E --> E1["메서드 내부에서만 선언"]
    F --> F1["이름 없는 즉석 구현"]
```

| 종류 | static | 외부 인스턴스 참조 | 선언 위치 |
|------|--------|-------------------|-----------|
| Static Nested Class | O | X | 클래스 멤버 |
| Member Inner Class | X | O | 클래스 멤버 |
| Local Inner Class | X | O | 메서드 내부 |
| Anonymous Class | X | O | 표현식 위치 |

---

## 2. Static 중첩 클래스 (Static Nested Class)

> **비유:** Static 중첩 클래스는 대형 마트 안에 입점한 독립 매장입니다. 마트(외부 클래스) 건물 안에 있지만, 마트 사장(외부 인스턴스)의 허락 없이도 스스로 영업할 수 있습니다. 마트의 공용 시설(static 멤버)은 이용하지만, 마트 사장의 개인 사무실(인스턴스 멤버)에는 출입할 수 없습니다.

### 동작 원리

`static`을 붙이면 외부 클래스의 인스턴스와 완전히 독립됩니다. 외부 클래스의 `static` 멤버에만 접근 가능하고, 인스턴스 멤버에는 접근할 수 없습니다. `Outer` 인스턴스 없이 `new Outer.StaticNested()`로 바로 생성합니다.

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

### 사용 시점

```java
// 1. LinkedList 내부 Node — 논리적으로 연관되지만 독립적인 클래스
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

> **비유:** 멤버 내부 클래스는 부모님 집에 사는 성인 자녀입니다. 자녀(Inner)는 부모(Outer)의 냉장고(private 멤버)를 자유롭게 열 수 있지만, 부모 없이는 집 자체가 존재하지 않습니다. 문제는 자녀가 집 열쇠(`this$0`)를 쥐고 있는 한 부모가 이사(GC)를 갈 수 없다는 것입니다.

### 동작 원리

멤버 내부 클래스는 컴파일러가 자동으로 외부 클래스 인스턴스에 대한 숨겨진 참조(`this$0`)를 필드로 추가합니다. `Inner` 인스턴스를 생성하려면 반드시 `Outer` 인스턴스가 먼저 있어야 하고, `outer.new Inner()` 라는 독특한 문법을 사용합니다. 이 숨겨진 참조가 메모리 누수의 핵심 원인입니다.

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

### 컴파일러가 생성하는 실제 코드

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

> **비유:** 지역 내부 클래스는 회의실에서만 쓰는 임시 화이트보드입니다. 회의(메서드)가 끝나면 화이트보드(클래스)는 치워지고, 회의실 밖에서는 그 화이트보드를 볼 수도 없습니다. 화이트보드에 적힌 내용은 회의 시작 시 배포된 자료(effectively final 변수)만 참조할 수 있습니다.

### 동작 원리

메서드 내부에서 선언하는 클래스입니다. 해당 메서드 스코프 안에서만 사용할 수 있어 외부 공개 없이 특정 메서드 전용 로직을 캡슐화할 때 씁니다. 람다가 없던 시절에는 이 방식을 썼지만 현대에는 거의 사용하지 않습니다.

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

---

## 5. 익명 클래스 (Anonymous Class)

> **비유:** 익명 클래스는 일회용 마스크입니다. 특정 상황(메서드 호출)에서 한 번 쓰고 버릴 구현이 필요할 때, 정식 클래스(재사용 가능한 천 마스크)를 만들 필요 없이 즉석에서 만들어 사용합니다. 이름이 없으므로 다른 곳에서 재사용할 수 없습니다.

### 동작 원리

익명 클래스는 인터페이스나 추상 클래스를 즉석에서 구현하는 문법입니다. 컴파일러는 `Outer$1.class`, `Outer$2.class` 같은 별도 파일을 생성합니다. Java 8 이후로는 함수형 인터페이스(추상 메서드 1개)라면 람다로 대체하는 것이 권장됩니다.

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

> **비유:** 익명 클래스에서 람다로의 전환은 편지에서 문자 메시지로의 전환과 같습니다. 편지(익명 클래스)는 봉투(클래스 선언), 인사말(`@Override`), 본문(실제 로직), 마무리 인사(중괄호)가 모두 필요하지만, 문자(람다)는 핵심 내용 한 줄이면 됩니다. 단, 문자는 한 가지 용건(추상 메서드 1개)만 전달할 수 있습니다.

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

비static 내부 클래스 인스턴스가 외부 클래스 인스턴스보다 오래 살면 GC가 외부 클래스를 수거하지 못합니다. `Thread`나 `Handler` 같은 장수 객체가 내부 클래스 인스턴스를 보유할 때 특히 위험합니다.

```mermaid
graph TD
    A["Thread (GC Root)"] --> B["MyTask 인스턴스 (Runnable)"]
    B --> C["this$0 참조 (강참조)"]
    C --> D["MyActivity 인스턴스 (GC 불가!)"]
    D --> E["모든 필드, 뷰, 리소스..."]
    style D fill:#ff6b6b
    style E fill:#ff6b6b
```

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

**비유:** 멤버 내부 클래스는 집주인(외부 클래스)의 열쇠를 가진 세입자(내부 클래스)입니다. 세입자가 이사를 가지 않는 한(GC), 집주인도 집을 비울 수 없습니다(GC 불가). `WeakReference`는 열쇠를 종이에 적어두는 것과 같습니다. 집주인이 이미 집을 비웠다면(GC됨) 종이의 주소는 무효가 됩니다.

**극한 시나리오:** 안드로이드 앱에서 `Activity` 안에 `AsyncTask`(멤버 내부 클래스)를 생성한 뒤 화면을 회전시키면 새 `Activity`가 생성되는데, 백그라운드 작업이 끝날 때까지 이전 `Activity`가 GC되지 않아 `OutOfMemoryError`로 앱이 크래시됩니다.

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

<details class="extreme-scenario-details">
<summary class="extreme-scenario-summary">
<span class="extreme-scenario-icon">🔥</span>
<span class="extreme-scenario-label">극한 시나리오 — 클릭하여 펼치기</span>
<span class="extreme-scenario-toggle"></span>
</summary>
<div class="extreme-scenario-body">

<div class="extreme-scenario-content" markdown="1">

### 시나리오 1: 이벤트 리스너 누수 (100 TPS)

> **비유:** 호텔 객실 열쇠를 체크아웃 시 반납하지 않는 것과 같습니다. 열쇠(리스너)가 객실(Activity/컴포넌트)을 가리키고 있는 한, 호텔(JVM)은 그 객실을 다른 손님에게 내줄 수 없습니다.

- **문제:** GUI 애플리케이션에서 화면 전환마다 익명 클래스로 이벤트 리스너를 등록하지만 제거하지 않으면, 이전 화면의 모든 객체가 GC되지 않아 메모리가 선형적으로 증가합니다. 100 TPS 환경에서 1시간이면 수천 개의 좀비 리스너가 누적됩니다.
- **해결:** 리스너 등록과 제거를 `AutoCloseable` 패턴으로 쌍으로 묶고, `WeakReference` 기반 리스너 래퍼를 사용합니다. 또는 람다로 전환하되, 참조하는 외부 변수를 최소화합니다.
- **근거:** 멤버 내부 클래스의 `this$0` 참조는 강참조이므로 GC Root에서 도달 가능한 한 외부 클래스 전체가 수거 불가능합니다.

### 시나리오 2: 빌더 패턴 대규모 객체 생성 (10K TPS)

> **비유:** 자동차 조립 라인에서 주문서(Builder)를 작성한 뒤 완성차(Person)를 찍어내는 것입니다. Builder가 static이므로 조립 라인은 공장(외부 클래스) 가동 여부와 무관하게 독립 운영됩니다.

- **문제:** 초당 10,000개의 DTO를 생성하는 API 서버에서 Builder를 멤버 내부 클래스(non-static)로 만들면 매 Builder마다 외부 클래스 참조가 추가되어 객체 크기가 커지고 GC 압력이 증가합니다.
- **해결:** Builder는 반드시 `static` 중첩 클래스로 선언합니다. 외부 인스턴스를 참조할 필요가 전혀 없으므로 `static`이 정확한 선택입니다.
- **근거:** `static` 중첩 클래스는 `this$0` 참조가 없으므로 객체당 8바이트(참조 크기) 절약이며, GC 그래프가 단순해져 수거 속도가 빨라집니다.

### 시나리오 3: NIO Selector + 콜백 핸들러 (100K 동시 연결)

> **비유:** 10만 명이 동시에 전화를 거는 콜센터에서, 상담원(내부 클래스)이 고객 정보(외부 클래스)를 들고 있으면 상담이 끝나도 고객 카드를 폐기할 수 없습니다.

- **문제:** NIO 서버에서 연결별 핸들러를 멤버 내부 클래스로 구현하면 핸들러가 서버 전체 객체를 참조합니다. 연결이 비정상 종료되어 핸들러가 정리되지 않으면 서버 객체가 GC 불가능해지고, 100K 동시 연결 환경에서 메모리가 폭발합니다.
- **해결:** 핸들러를 `static` 중첩 클래스로 만들고, 필요한 의존성만 생성자로 주입합니다. 연결 종료 시 `SelectionKey.cancel()` + 핸들러 참조 null 처리를 반드시 수행합니다.
- **근거:** 외부 참조를 끊으면 개별 핸들러가 독립적으로 GC 가능해져 메모리 누수 체인이 형성되지 않습니다.

---
</div>
</div>
</details>

## 10. 실무에서 자주 하는 실수

### 실수 1: static으로 선언해야 할 중첩 클래스를 non-static으로 선언

```java
// 위험: Node는 외부 인스턴스가 전혀 불필요한데 non-static으로 선언
public class MyList<E> {
    class Node<E> {  // 매 Node마다 MyList 참조 보유 → 메모리 낭비
        E item;
        Node<E> next;
    }
}

// 해결: static으로 선언
public class MyList<E> {
    static class Node<E> {  // 외부 참조 없음 → 메모리 절약
        E item;
        Node<E> next;
    }
}
```

### 실수 2: 직렬화 시 내부 클래스 포함

```java
// 위험: 멤버 내부 클래스를 Serializable로 만들면
// 외부 클래스 전체가 직렬화 대상이 됨
public class Outer implements Serializable {
    private transient Connection dbConn;  // 직렬화 불가 필드

    class Inner implements Serializable {
        // 직렬화 시 Outer(dbConn 포함)도 함께 직렬화 시도 → NotSerializableException
    }
}

// 해결: static 중첩 클래스로 변경
static class Inner implements Serializable {
    // 외부 참조 없으므로 독립 직렬화 가능
}
```

### 실수 3: 익명 클래스에서 this 혼동

```java
public class Button {
    private String label = "Submit";

    public void addListener() {
        ActionListener listener = new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                // this는 익명 클래스 인스턴스!
                System.out.println(this.toString());  // 익명 클래스의 toString()
                System.out.println(Button.this.label); // 외부 클래스 접근은 명시적으로
            }
        };
    }
}
```

### 실수 4: 콜백에서 외부 클래스 전체를 캡처

```java
// 위험: 람다가 this를 캡처하면 외부 클래스 전체가 생존
public class HeavyService {
    private byte[] cache = new byte[100_000_000];  // 100MB

    public Runnable createTask() {
        return () -> System.out.println(this.hashCode());
        // this 캡처 → 100MB cache도 GC 불가
    }
}

// 해결: 필요한 값만 지역 변수로 복사
public Runnable createTask() {
    int hash = this.hashCode();
    return () -> System.out.println(hash);
    // hash만 캡처 → HeavyService는 GC 가능
}
```

### 실수 5: 중첩 클래스에서 외부 클래스와 동일한 필드명 사용

```java
// 혼란: 내부/외부 클래스에 같은 이름의 필드
public class Outer {
    private int value = 10;

    class Inner {
        private int value = 20;

        void print() {
            System.out.println(value);            // 20 (Inner.value)
            System.out.println(this.value);        // 20 (Inner.value)
            System.out.println(Outer.this.value);  // 10 (Outer.value)
            // 이름 충돌로 Outer.this 없이는 외부 value에 접근 불가
        }
    }
}
// 해결: 필드명을 구분하거나, static 중첩 클래스로 전환하여 외부 접근 자체를 차단
```

---

## 11. 면접 포인트

### Q1: Static 중첩 클래스와 멤버 내부 클래스의 차이는?

**A:** 핵심 차이는 외부 클래스 인스턴스에 대한 참조 보유 여부입니다. Static 중첩 클래스는 외부 참조가 없어 `new Outer.StaticNested()`로 독립 생성 가능하고, 외부의 static 멤버만 접근합니다. 멤버 내부 클래스는 컴파일러가 `this$0` 필드를 자동 추가하여 외부 인스턴스를 강참조하므로 `outer.new Inner()`로만 생성 가능하고, 외부의 모든 멤버에 접근합니다. 이 차이 때문에 멤버 내부 클래스는 메모리 누수 위험이 있습니다.

### Q2: 멤버 내부 클래스가 메모리 누수를 일으키는 원리는?

**A:** 멤버 내부 클래스는 컴파일 시 `this$0`라는 외부 클래스 참조 필드가 자동 추가됩니다. 내부 클래스 인스턴스가 GC Root에서 도달 가능한 곳(Thread, static 컬렉션 등)에 보관되면, `this$0`를 따라 외부 클래스 전체와 그 필드들이 GC 불가능해집니다. 해결책은 static 중첩 클래스 + `WeakReference` 조합이거나, 필요한 데이터만 복사하여 캡처하는 것입니다.

### Q3: 익명 클래스와 람다의 차이점 3가지는?

**A:** 첫째, `this` 의미가 다릅니다. 익명 클래스의 `this`는 익명 클래스 인스턴스, 람다의 `this`는 감싸는 외부 클래스입니다. 둘째, 익명 클래스는 새 스코프를 생성하여 외부와 같은 이름의 변수를 선언할 수 있지만, 람다는 감싸는 스코프를 그대로 사용하므로 변수명 충돌 시 컴파일 에러입니다. 셋째, 내부 구현이 다릅니다. 익명 클래스는 별도 `.class` 파일을 생성하고, 람다는 `invokedynamic` + `LambdaMetafactory`로 런타임에 동적 생성합니다.

### Q4: 중첩 클래스를 사용하는 이유는?

**A:** 세 가지 이점이 있습니다. 첫째, 캡슐화입니다. 외부에 노출할 필요 없는 구현 세부사항(예: `LinkedList`의 `Node`)을 숨깁니다. 둘째, 논리적 그룹핑입니다. 빌더 패턴처럼 특정 클래스와 밀접한 보조 클래스를 내부에 배치하여 코드 응집도를 높입니다. 셋째, 외부 멤버 접근입니다. 멤버 내부 클래스는 외부의 private 멤버에 자유롭게 접근할 수 있어 Iterator 같은 패턴에 유용합니다.

### Q5: Effective Java에서 "멤버 클래스는 되도록 static으로 만들라"고 하는 이유는?

**A:** non-static 멤버 클래스는 인스턴스마다 외부 참조(`this$0`)를 숨겨진 필드로 보유합니다. 이는 세 가지 비용을 수반합니다. 첫째, 참조 저장에 추가 메모리(8바이트)가 듭니다. 둘째, 외부 인스턴스의 GC를 방해하여 메모리 누수를 일으킬 수 있습니다. 셋째, 직렬화 시 외부 클래스까지 함께 직렬화되어 예상치 못한 예외가 발생합니다. 외부 인스턴스 접근이 실제로 필요한 경우가 아니라면 항상 `static`을 붙여야 합니다.

---

## 12. 전체 요약

```mermaid
graph TD
    A["중첩 클래스 선택 가이드"] --> B["외부 인스턴스 불필요?"]
    B -->|"Yes"| C["Static Nested Class\n빌더, 노드 등 구현 세부 클래스"]
    B -->|"No"| D["Inner Class 계열"]
    D --> E["이름이 필요한가?"]
    E -->|"Yes, 메서드 내"| F["Local Inner Class\n(거의 사용 안 함)"]
    E -->|"Yes, 멤버"| G["Member Inner Class\nIterator, 이벤트 핸들러 등"]
    E -->|"No"| H["함수형 인터페이스인가?"]
    H -->|"Yes (메서드 1개)"| I["람다로 대체"]
    H -->|"No (메서드 여러개)"| J["Anonymous Class"]
```

**핵심 규칙:**
1. 외부 인스턴스가 필요 없으면 → static 중첩 클래스 우선 선택
2. 멤버 내부 클래스 + 백그라운드 작업 → 메모리 누수 반드시 확인
3. 함수형 인터페이스 → 람다로 교체
4. `this$0` 참조를 항상 인식하고 설계할 것
