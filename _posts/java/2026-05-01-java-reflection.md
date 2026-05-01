---
title: "Java 리플렉션(Reflection) 완전 정리"
categories:
- JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

리플렉션은 런타임에 클래스 구조를 분석하고 동적으로 조작하는 강력한 기법입니다. Spring, JPA, Jackson, JUnit이 모두 이를 기반으로 동작합니다. 원리부터 실무 활용까지 상세히 정리합니다.

---

## 1. 리플렉션이란?

**리플렉션(Reflection)**은 프로그램이 실행 중(runtime)에 자기 자신의 구조를 조사하고 수정하는 능력입니다. 컴파일 타임에 알 수 없는 클래스, 메서드, 필드에 동적으로 접근할 수 있습니다.

```
일반 코드 흐름:
  소스코드(.java) ──컴파일──▶ 바이트코드(.class) ──JVM 로딩──▶ 실행

리플렉션:
  실행 중인 JVM ──▶ 클래스 메타데이터(Class 객체) ──▶ 구조 조회/수정
                    ↑
                 java.lang.Class
                 java.lang.reflect.*
```

### 왜 필요한가?

```
일반 코드:      컴파일 시점에 타입이 확정됨
                  Person p = new Person();  // 컴파일러가 Person을 앎
                  p.getName();              // 컴파일러가 getName()을 앎

리플렉션:       런타임에 타입을 결정
                  String className = config.get("class");
                  Class<?> clazz = Class.forName(className);  // 런타임에 로딩
                  Object obj = clazz.getDeclaredConstructor().newInstance();
                  // → 플러그인 시스템, DI 컨테이너, ORM, 직렬화 라이브러리 등에 필수
```

### 리플렉션이 쓰이는 곳

| 프레임워크/라이브러리 | 리플렉션 활용 |
|----------------------|--------------|
| Spring DI | `@Autowired` 필드에 의존성 주입 |
| Spring MVC | `@RequestMapping` 메서드 탐색 및 호출 |
| JPA (Hibernate) | 엔티티 필드 매핑, Proxy 생성 |
| Jackson | JSON ↔ Java 객체 변환 |
| JUnit | `@Test` 메서드 탐색 및 실행 |
| Lombok | 어노테이션 기반 코드 생성 (APT) |

---

## 2. Class 객체 획득

모든 리플렉션의 시작점은 `java.lang.Class` 객체입니다.

```java
// 방법 1: 클래스 리터럴 (.class) — 컴파일 타임에 결정, 가장 안전하고 빠름
Class<String> c1 = String.class;
Class<int[]> c2 = int[].class;
Class<Void> c3 = void.class;

// 방법 2: 인스턴스의 getClass() — 런타임에 실제 타입 반환
Object obj = "Hello";
Class<?> c4 = obj.getClass();  // String.class (다형성 적용)

String str = "World";
Class<? extends String> c5 = str.getClass();

// 방법 3: Class.forName() — 문자열로 클래스 로딩 (가장 동적)
Class<?> c6 = Class.forName("java.util.ArrayList");
Class<?> c7 = Class.forName("com.example.MyPlugin");  // 런타임 로딩

// 배열 클래스
Class<?> intArrayClass = Class.forName("[I");      // int[]
Class<?> strArrayClass = Class.forName("[Ljava.lang.String;");  // String[]

// 방법 4: ClassLoader 직접 사용
ClassLoader cl = Thread.currentThread().getContextClassLoader();
Class<?> c8 = cl.loadClass("com.example.SomeClass");

// Class 객체 비교
System.out.println(c1 == c4);   // true (같은 Class 객체)
System.out.println(c1 == c6);   // false (String vs ArrayList)
```

### 기본형과 래퍼 타입

```java
// 기본형과 래퍼 타입은 다른 Class 객체
Class<?> primitiveInt  = int.class;
Class<?> wrapperInt    = Integer.class;
System.out.println(primitiveInt == wrapperInt);  // false

// 기본형 타입 목록
Class<?>[] primitives = {
    byte.class, short.class, int.class, long.class,
    float.class, double.class, char.class, boolean.class, void.class
};

// 기본형 여부 확인
System.out.println(int.class.isPrimitive());     // true
System.out.println(Integer.class.isPrimitive()); // false
```

---

## 3. 클래스 정보 조회

```java
Class<?> clazz = ArrayList.class;

// 기본 정보
System.out.println(clazz.getName());            // java.util.ArrayList
System.out.println(clazz.getSimpleName());      // ArrayList
System.out.println(clazz.getCanonicalName());   // java.util.ArrayList
System.out.println(clazz.getPackageName());     // java.util

// 타입 분류
System.out.println(clazz.isInterface());        // false
System.out.println(clazz.isArray());            // false
System.out.println(clazz.isEnum());             // false
System.out.println(clazz.isRecord());           // false (Java 16+)
System.out.println(clazz.isAnnotation());       // false
System.out.println(clazz.isSynthetic());        // false (컴파일러 생성 여부)
System.out.println(clazz.isAnonymousClass());   // false
System.out.println(clazz.isLocalClass());       // false
System.out.println(clazz.isMemberClass());      // false

// 수정자 (Modifier)
int mod = clazz.getModifiers();
System.out.println(Modifier.isPublic(mod));     // true
System.out.println(Modifier.isAbstract(mod));   // false
System.out.println(Modifier.isFinal(mod));      // false
System.out.println(Modifier.toString(mod));     // "public"

// 슈퍼클래스 / 인터페이스
Class<?> superClass = clazz.getSuperclass();    // AbstractList.class
Class<?>[] interfaces = clazz.getInterfaces();  // [List, RandomAccess, Cloneable, Serializable]

for (Class<?> iface : interfaces) {
    System.out.println("구현 인터페이스: " + iface.getSimpleName());
}

// 제네릭 타입 정보
Type genericSuper = clazz.getGenericSuperclass();  // AbstractList<E>
Type[] genericInterfaces = clazz.getGenericInterfaces();

// 내부 클래스
Class<?>[] declaredClasses = clazz.getDeclaredClasses();

// 외부 클래스 (멤버 클래스일 때)
Class<?> enclosing = clazz.getEnclosingClass();
```

---

## 4. 필드 조회 및 접근

```java
public class Person {
    public String name;
    protected int age;
    private String email;
    static String company = "Java Corp";
}
```

```java
Class<?> clazz = Person.class;

// getFields()        → public 필드만 (상속 포함)
// getDeclaredFields() → 모든 접근 제어자 (선언된 클래스만)

Field[] publicFields   = clazz.getFields();           // name (상속된 public도 포함)
Field[] declaredFields = clazz.getDeclaredFields();    // name, age, email, company

for (Field f : declaredFields) {
    System.out.printf("필드: %-15s | 타입: %-20s | 수정자: %s%n",
            f.getName(), f.getType().getSimpleName(), Modifier.toString(f.getModifiers()));
}

// 특정 필드 접근
Field nameField  = clazz.getField("name");           // public 필드
Field emailField = clazz.getDeclaredField("email");  // private 필드

// 필드 메타데이터
System.out.println(emailField.getName());             // email
System.out.println(emailField.getType());             // class java.lang.String
System.out.println(emailField.getGenericType());      // class java.lang.String
System.out.println(Modifier.isPrivate(emailField.getModifiers()));  // true
```

---

## 5. 접근 제어 우회 (setAccessible)

```java
Person person = new Person();
person.name = "공개";  // public 필드: 직접 접근 가능

// private 필드 접근
Field emailField = Person.class.getDeclaredField("email");
emailField.setAccessible(true);  // 접근 제어 우회

// 값 읽기
emailField.set(person, "kim@example.com");  // 쓰기
String email = (String) emailField.get(person);  // 읽기
System.out.println("email: " + email);  // kim@example.com

// static 필드 접근 (인스턴스 대신 null 사용)
Field companyField = Person.class.getDeclaredField("company");
companyField.setAccessible(true);
String company = (String) companyField.get(null);  // static 필드
companyField.set(null, "New Company");

// 기본형 타입 전용 메서드 (언박싱 비용 절감)
// field.getInt(obj), field.getLong(obj), field.getDouble(obj) ...
```

### Java 9+ 모듈 시스템과 setAccessible

```java
// Java 9+ 에서 다른 모듈의 클래스에 접근 시 InaccessibleObjectException 발생 가능
// 해결: module-info.java에 opens 선언
// module com.example.myapp {
//     opens com.example.model to com.example.framework;
// }

// 또는 JVM 옵션 (임시 방편, 비권장)
// --add-opens java.base/java.lang=ALL-UNNAMED
```

---

## 6. 메서드 조회 및 호출

```java
public class Calculator {
    public int add(int a, int b) { return a + b; }
    private double divide(double a, double b) { return a / b; }
    public static int square(int n) { return n * n; }
    public <T extends Number> T identity(T t) { return t; }
}
```

```java
Class<?> clazz = Calculator.class;

// getMethods()          → public 메서드 (상속 포함, Object 메서드도 포함)
// getDeclaredMethods()  → 모든 접근 제어자 (선언된 클래스만)

Method[] methods = clazz.getDeclaredMethods();
for (Method m : methods) {
    System.out.printf("메서드: %-15s | 반환: %-10s | 파라미터: %s%n",
            m.getName(),
            m.getReturnType().getSimpleName(),
            Arrays.stream(m.getParameterTypes())
                  .map(Class::getSimpleName)
                  .collect(Collectors.joining(", ")));
}

// 특정 메서드 조회 (이름 + 파라미터 타입)
Method addMethod    = clazz.getMethod("add", int.class, int.class);
Method divideMethod = clazz.getDeclaredMethod("divide", double.class, double.class);
Method squareMethod = clazz.getMethod("square", int.class);

// 메서드 메타데이터
System.out.println(addMethod.getReturnType());          // int
System.out.println(addMethod.getParameterCount());      // 2
System.out.println(Arrays.toString(addMethod.getExceptionTypes()));

// 메서드 호출 (invoke)
Calculator calc = new Calculator();

Object result1 = addMethod.invoke(calc, 3, 4);  // 인스턴스 메서드
System.out.println("3 + 4 = " + result1);       // 7

divideMethod.setAccessible(true);
Object result2 = divideMethod.invoke(calc, 10.0, 3.0);  // private 메서드
System.out.printf("10 / 3 = %.4f%n", result2);

Object result3 = squareMethod.invoke(null, 5);   // static 메서드: null 전달
System.out.println("5^2 = " + result3);         // 25

// 파라미터 상세 정보
for (Parameter param : addMethod.getParameters()) {
    System.out.printf("파라미터: %s, 타입: %s%n",
            param.getName(), param.getType().getSimpleName());
    // 주의: param.getName()은 컴파일 시 -parameters 옵션이 있어야 실제 이름 반환
    //       없으면 arg0, arg1 ... 반환
}
```

### 제네릭 타입 정보 조회

```java
// 런타임에 제네릭 타입 소거(Type Erasure)로 인해 타입 파라미터 정보가 사라짐
// 단, 선언부의 타입 파라미터는 ParameterizedType으로 조회 가능

public class Repository<T> {
    private List<T> items = new ArrayList<>();
    public List<String> getNames() { return List.of(); }
}

// 필드의 제네릭 타입
Field itemsField = Repository.class.getDeclaredField("items");
Type genericType = itemsField.getGenericType();  // java.util.List<T>
if (genericType instanceof ParameterizedType pt) {
    System.out.println("원시 타입: " + pt.getRawType());       // interface java.util.List
    System.out.println("타입 인수: " + Arrays.toString(pt.getActualTypeArguments())); // [T]
}

// 메서드 반환 타입의 제네릭
Method getNames = Repository.class.getMethod("getNames");
Type returnType = getNames.getGenericReturnType();  // java.util.List<java.lang.String>
if (returnType instanceof ParameterizedType pt) {
    Type[] typeArgs = pt.getActualTypeArguments();  // [class java.lang.String]
    System.out.println("반환 타입 인수: " + typeArgs[0]);  // class java.lang.String
}
```

---

## 7. 생성자 조회 및 동적 객체 생성

```java
public class Product {
    private String name;
    private int price;

    public Product() { this("기본", 0); }
    public Product(String name) { this(name, 0); }
    public Product(String name, int price) {
        this.name = name;
        this.price = price;
    }
}
```

```java
Class<?> clazz = Product.class;

// getConstructors()          → public 생성자만
// getDeclaredConstructors()  → 모든 접근 제어자

Constructor<?>[] constructors = clazz.getDeclaredConstructors();
for (Constructor<?> c : constructors) {
    System.out.println("생성자: " + Arrays.toString(c.getParameterTypes()));
}

// 기본 생성자로 생성 (Java 9+: getDeclaredConstructor() 권장)
Object p1 = clazz.getDeclaredConstructor().newInstance();

// 파라미터 있는 생성자
Constructor<?> twoArgCtor = clazz.getDeclaredConstructor(String.class, int.class);
Object p2 = twoArgCtor.newInstance("노트북", 1_500_000);

// private 생성자 접근 (싱글턴 패턴 우회 - 테스트 목적)
public class Singleton {
    private static final Singleton INSTANCE = new Singleton();
    private Singleton() {}
    public static Singleton getInstance() { return INSTANCE; }
}

Constructor<Singleton> ctor = Singleton.class.getDeclaredConstructor();
ctor.setAccessible(true);
Singleton s1 = ctor.newInstance();  // 새 인스턴스 강제 생성
Singleton s2 = Singleton.getInstance();
System.out.println(s1 == s2);  // false (주의: 이런 사용은 비권장)
```

---

## 8. 어노테이션 처리

### 8.1 커스텀 어노테이션 정의

```java
import java.lang.annotation.*;

// @Retention: 어노테이션이 유지되는 시점
//   RetentionPolicy.SOURCE   → 컴파일 전까지 (Lombok)
//   RetentionPolicy.CLASS    → .class 파일까지 (기본값)
//   RetentionPolicy.RUNTIME  → 런타임까지 ← 리플렉션으로 읽으려면 이것
@Retention(RetentionPolicy.RUNTIME)

// @Target: 어노테이션 적용 대상
@Target({ElementType.TYPE, ElementType.METHOD, ElementType.FIELD})

// @Inherited: 자식 클래스에 상속
@Inherited

// @Documented: Javadoc에 포함
@Documented

public @interface Validate {
    String message() default "유효성 검사 실패";
    int minLength() default 1;
    int maxLength() default 255;
    boolean required() default true;
}

// 메서드용 어노테이션
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface LogExecution {
    String value() default "";
    boolean logArgs() default true;
    boolean logResult() default false;
}

// 필드용 어노테이션
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.FIELD)
public @interface Column {
    String name() default "";
    boolean nullable() default true;
    int length() default 255;
}
```

### 8.2 어노테이션 적용 및 리플렉션으로 처리

```java
@Validate(message = "사용자 정보 오류")
public class User {
    @Column(name = "user_name", nullable = false, length = 50)
    @Validate(minLength = 2, maxLength = 50)
    private String name;

    @Column(name = "user_email", nullable = false)
    private String email;

    private int age;

    @LogExecution(value = "save", logArgs = true, logResult = true)
    public boolean save() { return true; }
}
```

```java
// 어노테이션 읽기 및 처리기 구현
public class AnnotationProcessor {

    // 클래스 레벨 어노테이션
    public static void processClass(Class<?> clazz) {
        if (clazz.isAnnotationPresent(Validate.class)) {
            Validate v = clazz.getAnnotation(Validate.class);
            System.out.println("클래스 검증 메시지: " + v.message());
        }
    }

    // 필드 레벨 어노테이션으로 ORM 컬럼 매핑
    public static Map<String, String> getColumnMapping(Class<?> clazz) {
        Map<String, String> mapping = new LinkedHashMap<>();

        for (Field field : clazz.getDeclaredFields()) {
            Column column = field.getAnnotation(Column.class);
            if (column != null) {
                String columnName = column.name().isEmpty()
                        ? field.getName()
                        : column.name();
                mapping.put(field.getName(), columnName);
                System.out.printf("필드 %-10s → 컬럼 %-15s (nullable=%b, length=%d)%n",
                        field.getName(), columnName, column.nullable(), column.length());
            }
        }
        return mapping;
    }

    // 메서드 레벨 어노테이션으로 로깅 AOP 구현
    public static Object invokeWithLogging(Object target, String methodName, Object... args)
            throws Exception {
        Method method = target.getClass().getMethod(methodName);
        LogExecution log = method.getAnnotation(LogExecution.class);

        if (log != null) {
            System.out.printf("[LOG] %s 시작 (태그: %s)%n", methodName, log.value());
            if (log.logArgs()) {
                System.out.println("[LOG] 인수: " + Arrays.toString(args));
            }
        }

        Object result = method.invoke(target, args);

        if (log != null && log.logResult()) {
            System.out.println("[LOG] 결과: " + result);
        }

        return result;
    }

    public static void main(String[] args) throws Exception {
        processClass(User.class);
        getColumnMapping(User.class);

        User user = new User();
        invokeWithLogging(user, "save");
    }
}
```

### 8.3 어노테이션 기반 유효성 검사기

```java
public class Validator {
    public static List<String> validate(Object obj) throws IllegalAccessException {
        List<String> errors = new ArrayList<>();
        Class<?> clazz = obj.getClass();

        for (Field field : clazz.getDeclaredFields()) {
            Validate v = field.getAnnotation(Validate.class);
            if (v == null) continue;

            field.setAccessible(true);
            Object value = field.get(obj);

            if (v.required() && value == null) {
                errors.add(field.getName() + ": 필수 항목입니다");
                continue;
            }

            if (value instanceof String s) {
                if (s.length() < v.minLength()) {
                    errors.add(field.getName() + ": 최소 " + v.minLength() + "자 이상이어야 합니다");
                }
                if (s.length() > v.maxLength()) {
                    errors.add(field.getName() + ": 최대 " + v.maxLength() + "자 이하여야 합니다");
                }
            }
        }
        return errors;
    }
}
```

---

## 9. 리플렉션의 성능 비용

```
성능 비교 (상대적 수치, JVM/JIT 최적화에 따라 다름):

직접 호출:              1x   (기준)
Method.invoke():       ~5x  (접근 검사 포함)
setAccessible 후 invoke: ~3x  (접근 검사 캐싱)
MethodHandle:          ~1.5x (JIT 최적화 가능)
```

### 성능 최적화 전략

```java
// 1. Method/Field 객체 캐싱 (매번 getDeclaredMethod 호출 금지)
public class ReflectionCache {
    private static final Map<String, Method> METHOD_CACHE = new ConcurrentHashMap<>();

    public static Method getCachedMethod(Class<?> clazz, String name, Class<?>... params)
            throws NoSuchMethodException {
        String key = clazz.getName() + "#" + name;
        return METHOD_CACHE.computeIfAbsent(key, k -> {
            try {
                Method m = clazz.getDeclaredMethod(name, params);
                m.setAccessible(true);  // 한 번만 설정
                return m;
            } catch (NoSuchMethodException e) {
                throw new RuntimeException(e);
            }
        });
    }
}

// 2. setAccessible(true)은 한 번만 호출 (매 invoke마다 하지 않음)
Method m = SomeClass.class.getDeclaredMethod("privateMethod");
m.setAccessible(true);  // 한 번만
for (int i = 0; i < 1_000_000; i++) {
    m.invoke(obj);  // 캐싱된 상태로 반복 호출
}

// 3. 생성자 인스턴스 생성도 캐싱
Constructor<?> ctor = MyClass.class.getDeclaredConstructor(String.class);
ctor.setAccessible(true);
// ctor를 재사용
```

### 성능 비용 발생 원인

```
리플렉션 호출 시 내부 동작:

Method.invoke(obj, args) 호출
  │
  ├─ 1. 접근 제어 검사 (setAccessible(false)이면 매번)
  ├─ 2. 가변인수 배열 생성 (Object... args)
  ├─ 3. 오토박싱 (기본형 인수: int → Integer)
  ├─ 4. 동적 디스패치 (JIT 인라이닝 불가)
  └─ 5. 예외 래핑 (InvocationTargetException)
```

---

## 10. 실무 활용 패턴

### 10.1 Spring DI 모방 — 필드 주입

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.FIELD)
public @interface Inject {}

public class SimpleContainer {
    private final Map<Class<?>, Object> registry = new HashMap<>();

    public <T> void register(Class<T> type, T instance) {
        registry.put(type, instance);
    }

    public <T> T createAndInject(Class<T> clazz) throws Exception {
        T instance = clazz.getDeclaredConstructor().newInstance();

        for (Field field : clazz.getDeclaredFields()) {
            if (field.isAnnotationPresent(Inject.class)) {
                Object dependency = registry.get(field.getType());
                if (dependency == null) {
                    throw new RuntimeException("의존성을 찾을 수 없습니다: " + field.getType());
                }
                field.setAccessible(true);
                field.set(instance, dependency);
                System.out.println("주입 완료: " + field.getName() + " ← " + dependency.getClass().getSimpleName());
            }
        }
        return instance;
    }
}

// 사용
public class UserService {
    @Inject
    private UserRepository userRepository;

    public String findUser(long id) {
        return userRepository.findById(id);
    }
}

// 등록 및 사용
SimpleContainer container = new SimpleContainer();
container.register(UserRepository.class, new UserRepository());
UserService service = container.createAndInject(UserService.class);
```

### 10.2 Jackson 모방 — JSON 직렬화

```java
public class SimpleJsonSerializer {

    public static String toJson(Object obj) throws IllegalAccessException {
        if (obj == null) return "null";

        Class<?> clazz = obj.getClass();
        StringBuilder sb = new StringBuilder("{");
        boolean first = true;

        for (Field field : clazz.getDeclaredFields()) {
            if (Modifier.isStatic(field.getModifiers())) continue;
            field.setAccessible(true);

            if (!first) sb.append(", ");
            first = false;

            sb.append("\"").append(field.getName()).append("\": ");
            Object value = field.get(obj);

            if (value == null) {
                sb.append("null");
            } else if (value instanceof String) {
                sb.append("\"").append(value).append("\"");
            } else if (value instanceof Number || value instanceof Boolean) {
                sb.append(value);
            } else {
                sb.append(toJson(value));  // 중첩 객체 재귀 처리
            }
        }
        sb.append("}");
        return sb.toString();
    }
}

// 사용
public record Point(int x, int y) {}

Point p = new Point(3, 4);
System.out.println(SimpleJsonSerializer.toJson(p));
// {"x": 3, "y": 4}
```

### 10.3 JUnit 모방 — 테스트 실행기

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface Test {}

@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface BeforeEach {}

public class SimpleTestRunner {

    public static void run(Class<?> testClass) throws Exception {
        Object testInstance = testClass.getDeclaredConstructor().newInstance();

        // @BeforeEach 메서드 찾기
        Method beforeEach = Arrays.stream(testClass.getDeclaredMethods())
                .filter(m -> m.isAnnotationPresent(BeforeEach.class))
                .findFirst().orElse(null);

        // @Test 메서드 실행
        int passed = 0, failed = 0;
        for (Method method : testClass.getDeclaredMethods()) {
            if (!method.isAnnotationPresent(Test.class)) continue;

            try {
                if (beforeEach != null) beforeEach.invoke(testInstance);
                method.invoke(testInstance);
                System.out.println("[PASS] " + method.getName());
                passed++;
            } catch (InvocationTargetException e) {
                System.out.println("[FAIL] " + method.getName() + ": " + e.getCause().getMessage());
                failed++;
            }
        }
        System.out.printf("결과: %d 통과, %d 실패%n", passed, failed);
    }
}
```

---

## 11. 동적 프록시 — InvocationHandler

동적 프록시는 리플렉션을 이용해 런타임에 인터페이스 구현체를 생성합니다. Spring AOP의 핵심 원리입니다.

```
동적 프록시 구조:

Client ──▶ [Proxy 객체] ──▶ [InvocationHandler] ──▶ [실제 객체]
                              (부가 기능 처리)
  동일한 인터페이스를 구현하는 프록시가 런타임에 생성됨
```

```java
// 인터페이스 정의
public interface UserService {
    User findById(long id);
    void save(User user);
    void delete(long id);
}

// 실제 구현체
public class UserServiceImpl implements UserService {
    @Override public User findById(long id) { return new User(id, "김자바"); }
    @Override public void save(User user) { System.out.println("저장: " + user); }
    @Override public void delete(long id) { System.out.println("삭제: " + id); }
}

// 로깅 프록시
public class LoggingHandler implements InvocationHandler {
    private final Object target;  // 실제 객체

    public LoggingHandler(Object target) {
        this.target = target;
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        long start = System.currentTimeMillis();
        System.out.printf("[LOG] %s.%s() 호출 시작%n",
                target.getClass().getSimpleName(), method.getName());

        try {
            Object result = method.invoke(target, args);  // 실제 메서드 호출

            long elapsed = System.currentTimeMillis() - start;
            System.out.printf("[LOG] %s.%s() 완료 (%dms)%n",
                    target.getClass().getSimpleName(), method.getName(), elapsed);
            return result;
        } catch (InvocationTargetException e) {
            System.out.printf("[LOG] %s.%s() 예외: %s%n",
                    target.getClass().getSimpleName(), method.getName(), e.getCause().getMessage());
            throw e.getCause();
        }
    }
}

// 프록시 생성 및 사용
UserService realService = new UserServiceImpl();

UserService proxy = (UserService) Proxy.newProxyInstance(
        realService.getClass().getClassLoader(),   // 클래스 로더
        new Class<?>[] { UserService.class },      // 구현할 인터페이스
        new LoggingHandler(realService)            // 핸들러
);

// proxy는 UserService를 구현하지만 실제로는 LoggingHandler.invoke()가 호출됨
proxy.findById(1L);
proxy.save(new User(2L, "이자바"));
```

### 트랜잭션 프록시 예제

```java
public class TransactionHandler implements InvocationHandler {
    private final Object target;

    public TransactionHandler(Object target) { this.target = target; }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        System.out.println("[TX] 트랜잭션 시작");
        try {
            Object result = method.invoke(target, args);
            System.out.println("[TX] 트랜잭션 커밋");
            return result;
        } catch (InvocationTargetException e) {
            System.out.println("[TX] 트랜잭션 롤백: " + e.getCause().getMessage());
            throw e.getCause();
        }
    }
}

// 여러 핸들러 체이닝 (데코레이터 패턴)
UserService logProxy = (UserService) Proxy.newProxyInstance(
        UserService.class.getClassLoader(),
        new Class<?>[] { UserService.class },
        new LoggingHandler(
            Proxy.newProxyInstance(
                UserService.class.getClassLoader(),
                new Class<?>[] { UserService.class },
                new TransactionHandler(realService)
            )
        )
);
// 호출 순서: LoggingHandler → TransactionHandler → UserServiceImpl
```

### 동적 프록시 한계

```java
// Proxy.newProxyInstance는 인터페이스만 지원
// 클래스(구현체)를 직접 프록시하려면 CGLIB (Spring이 내부적으로 사용)

// CGLIB: 바이트코드 조작으로 클래스를 상속하는 프록시 생성
// → Spring의 @Transactional이 인터페이스 없어도 동작하는 이유
```

---

## 12. MethodHandle (Java 7+)

`MethodHandle`은 리플렉션보다 빠르고, JIT 컴파일러가 최적화할 수 있는 저수준 메서드 참조입니다.

```
성능:  직접 호출 ≒ MethodHandle >> Method.invoke()
JIT:   MethodHandle은 인라이닝 가능, Method.invoke()는 불가
```

```java
import java.lang.invoke.*;

MethodHandles.Lookup lookup = MethodHandles.lookup();

// 1. 인스턴스 메서드
MethodType addType = MethodType.methodType(int.class, int.class, int.class);
MethodHandle addHandle = lookup.findVirtual(Calculator.class, "add", addType);

Calculator calc = new Calculator();
int result = (int) addHandle.invoke(calc, 3, 4);  // 7
// 또는
int result2 = (int) addHandle.invokeExact(calc, 3, 4);  // 타입 정확히 일치해야 함

// 2. static 메서드
MethodHandle squareHandle = lookup.findStatic(
        Calculator.class, "square",
        MethodType.methodType(int.class, int.class));
int sq = (int) squareHandle.invoke(5);  // 25

// 3. 생성자
MethodHandle ctorHandle = lookup.findConstructor(
        Product.class,
        MethodType.methodType(void.class, String.class, int.class));
Product p = (Product) ctorHandle.invoke("노트북", 1_500_000);

// 4. 필드 접근
MethodHandle getNameHandle = lookup.findGetter(Person.class, "name", String.class);
MethodHandle setNameHandle = lookup.findSetter(Person.class, "name", String.class);

Person person = new Person();
setNameHandle.invoke(person, "김자바");
String name = (String) getNameHandle.invoke(person);

// 5. private 멤버 접근 (Java 9+ PrivateLookupIn)
MethodHandles.Lookup privateLookup =
        MethodHandles.privateLookupIn(Person.class, MethodHandles.lookup());
MethodHandle privateFieldHandle = privateLookup.findGetter(
        Person.class, "email", String.class);

// 6. MethodHandle 조합 (커링, 바인딩)
// 첫 번째 인수를 calc로 바인딩
MethodHandle boundAdd = addHandle.bindTo(calc);
int result3 = (int) boundAdd.invoke(10, 20);  // 30

// 7. asType으로 타입 변환
MethodHandle flexibleAdd = addHandle.asType(
        MethodType.methodType(Object.class, Object.class, int.class, int.class));
```

### MethodHandle vs Method.invoke 비교

```java
// Method.invoke — 범용, 느림, 오래된 API
Method m = Calculator.class.getMethod("add", int.class, int.class);
m.setAccessible(true);
Object r1 = m.invoke(calc, 3, 4);  // 오토박싱 발생

// MethodHandle — 빠름, JIT 최적화 가능
MethodHandle mh = lookup.findVirtual(Calculator.class, "add",
        MethodType.methodType(int.class, int.class, int.class));
int r2 = (int) mh.invokeExact(calc, 3, 4);  // 오토박싱 없음

// VarHandle (Java 9+) — 필드 접근의 원자적 연산
VarHandle vh = MethodHandles.lookup().findVarHandle(Person.class, "name", String.class);
vh.set(person, "새이름");
String current = (String) vh.get(person);
vh.compareAndSet(person, "새이름", "변경된이름");  // CAS 연산
```

---

## 13. 리플렉션 사용 시 주의사항 정리

```
┌─────────────────────────────────────────────────────────────────┐
│                  리플렉션 주의사항                                │
│                                                                  │
│  1. 성능 비용                                                    │
│     → Method/Field/Constructor 객체 캐싱                        │
│     → setAccessible(true) 한 번만 호출                          │
│     → 고빈도 호출 시 MethodHandle 또는 코드 생성 고려           │
│                                                                  │
│  2. 타입 안전성 상실                                             │
│     → 컴파일 타임 오류 대신 런타임 예외 (ClassCastException,    │
│       IllegalArgumentException, InvocationTargetException)       │
│     → 충분한 테스트 필요                                         │
│                                                                  │
│  3. 캡슐화 훼손                                                  │
│     → private 접근은 설계 의도를 무시                           │
│     → 테스트 목적 외에는 최소한으로 사용                        │
│                                                                  │
│  4. 모듈 시스템 (Java 9+)                                        │
│     → 모듈 간 접근 시 InaccessibleObjectException               │
│     → module-info.java의 opens 선언 필요                        │
│                                                                  │
│  5. 보안                                                         │
│     → SecurityManager 환경에서 제한 가능                        │
│     → 신뢰할 수 없는 코드에 리플렉션 권한 부여 주의             │
│                                                                  │
│  6. GraalVM Native Image                                         │
│     → 리플렉션은 AOT 컴파일 시 정적 분석 불가                   │
│     → reflect-config.json으로 명시적 등록 필요                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 14. 전체 구조 요약

```
java.lang.reflect 패키지 핵심 클래스:

Class<T>
├── getName() / getSimpleName() / getCanonicalName()
├── getFields() / getDeclaredFields()          → Field[]
├── getMethods() / getDeclaredMethods()        → Method[]
├── getConstructors() / getDeclaredConstructors() → Constructor<?>[]
├── getAnnotations() / getDeclaredAnnotations() → Annotation[]
├── getSuperclass() / getInterfaces()
├── newInstance() (deprecated) → getDeclaredConstructor().newInstance()
└── isAnnotationPresent(), isInterface(), isArray(), ...

Field
├── get(obj) / set(obj, value)
├── getInt/Long/Double/...()
├── setAccessible(true)
└── getAnnotation(), getType(), getGenericType()

Method
├── invoke(obj, args...)
├── setAccessible(true)
├── getReturnType() / getGenericReturnType()
├── getParameterTypes() / getParameters()
└── getAnnotation(), getExceptionTypes()

Constructor<T>
├── newInstance(args...)
├── setAccessible(true)
└── getParameterTypes()

Proxy
└── newProxyInstance(classLoader, interfaces[], InvocationHandler)
    → 인터페이스 기반 동적 프록시 생성

java.lang.invoke 패키지 (Java 7+):

MethodHandles.Lookup
├── findVirtual()    → 인스턴스 메서드
├── findStatic()     → static 메서드
├── findConstructor() → 생성자
├── findGetter/Setter() → 필드
└── privateLookupIn() → private 접근 (Java 9+)

MethodHandle
├── invoke() / invokeExact()
├── bindTo()         → 부분 적용(커링)
└── asType()         → 타입 변환
```

---

## 핵심 정리

| 기능 | API | 주요 메서드 |
|------|-----|------------|
| 클래스 로딩 | `Class` | `forName()`, `.class`, `getClass()` |
| 필드 접근 | `Field` | `get()`, `set()`, `setAccessible()` |
| 메서드 호출 | `Method` | `invoke()`, `setAccessible()` |
| 객체 생성 | `Constructor` | `newInstance()` |
| 어노테이션 | `AnnotatedElement` | `getAnnotation()`, `isAnnotationPresent()` |
| 동적 프록시 | `Proxy` | `newProxyInstance()` |
| 고성능 접근 | `MethodHandle` | `invoke()`, `invokeExact()` |
| 원자적 필드 접근 | `VarHandle` | `get()`, `set()`, `compareAndSet()` |
