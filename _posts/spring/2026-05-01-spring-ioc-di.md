---
title: "Spring IoC와 DI"
categories:
- SPRING
toc: true
toc_sticky: true
toc_label: 목차
---

신입 때 이런 경험이 있을 것이다. 서비스 클래스 안에서 `new RateDiscountPolicy()`를 직접 써뒀는데, 기획이 바뀌어서 `FixDiscountPolicy`로 교체해야 하는 순간. 수십 개 파일을 열어 `new`를 바꿔야 했다. IoC와 DI는 이 문제를 해결하기 위해 태어난 개념이다.

---

## 1. IoC(Inversion of Control)란?

IoC는 **제어의 역전**을 의미한다. 전통적인 프로그래밍에서는 개발자가 직접 객체를 생성하고 의존 객체를 연결했다. IoC에서는 이 제어권이 프레임워크(Spring Container)로 넘어간다.

### 전통적 방식 vs IoC

```java
// 전통적 방식 - 개발자가 직접 제어
public class OrderService {
    private final DiscountPolicy discountPolicy;

    public OrderService() {
        // 개발자가 직접 구체 클래스를 선택하고 생성
        this.discountPolicy = new RateDiscountPolicy();
    }
}

// IoC 방식 - 컨테이너가 제어
public class OrderService {
    private final DiscountPolicy discountPolicy;

    // 어떤 구현체가 들어올지 모른다. 컨테이너가 결정한다.
    public OrderService(DiscountPolicy discountPolicy) {
        this.discountPolicy = discountPolicy;
    }
}
```

IoC의 핵심은 **"내가 사용할 객체를 내가 만들지 않는다"**는 것이다. 객체의 생성, 생명주기 관리, 의존성 연결을 컨테이너가 담당한다.

---

## 2. IoC 컨테이너 동작 원리

Spring IoC 컨테이너는 **Bean Definition**을 읽어서 Bean을 생성하고 관리한다.

<div class="mermaid">
graph TD
    A["Configuration 읽기<br>@Configuration+@Bean<br>@ComponentScan+@Component<br>XML legacy"] --> B["BeanDefinition 생성<br>클래스 정보, 스코프, 의존성 정보"]
    B --> C["Bean 인스턴스 생성<br>생성자 호출"]
    C --> D["의존성 주입<br>생성자/세터/필드 주입"]
    D --> E["초기화 콜백<br>@PostConstruct, InitializingBean"]
    E --> F["Bean 사용"]
    F --> G["소멸 콜백<br>@PreDestroy, DisposableBean"]

    style A fill:#e8f4f8
    style F fill:#e8f8e8
    style G fill:#f8e8e8
</div>

---

## 3. BeanFactory vs ApplicationContext

### BeanFactory

Spring 컨테이너의 최상위 인터페이스. Bean을 관리하고 조회하는 기본 기능을 제공한다.

```java
public interface BeanFactory {
    Object getBean(String name) throws BeansException;
    <T> T getBean(String name, Class<T> requiredType);
    <T> T getBean(Class<T> requiredType);
    boolean containsBean(String name);
    boolean isSingleton(String name);
    boolean isPrototype(String name);
    // ...
}
```

**특징**: 지연 로딩(Lazy Loading). `getBean()` 호출 시점에 Bean을 생성한다.

### ApplicationContext

BeanFactory를 상속받아 훨씬 많은 기능을 추가한 인터페이스.

```java
public interface ApplicationContext extends
    EnvironmentCapable,          // 환경 변수
    ListableBeanFactory,         // BeanFactory 확장
    HierarchicalBeanFactory,     // 부모 컨테이너 계층
    MessageSource,               // 국제화(i18n)
    ApplicationEventPublisher,   // 이벤트 발행
    ResourcePatternResolver {    // 리소스 조회
}
```

**특징**: 즉시 로딩(Eager Loading). 컨테이너 시작 시점에 모든 싱글톤 Bean을 미리 생성한다.

### 비교표

| 구분 | BeanFactory | ApplicationContext |
|------|-------------|-------------------|
| Bean 로딩 | Lazy (호출 시) | Eager (시작 시) |
| 국제화 | 미지원 | 지원 |
| 이벤트 발행 | 미지원 | 지원 |
| 환경 변수 | 미지원 | 지원 |
| 실무 사용 | 거의 안 함 | 항상 사용 |

실무에서는 항상 ApplicationContext를 사용한다. BeanFactory의 기능이 필요하면 ApplicationContext가 이미 상속하고 있으므로 그대로 사용하면 된다.

### 주요 구현체

```
ApplicationContext
├── AnnotationConfigApplicationContext   // Java 설정 (순수 Java, 테스트)
├── AnnotationConfigServletWebServerApplicationContext  // Spring Boot 웹
├── GenericXmlApplicationContext         // XML 설정
└── ClassPathXmlApplicationContext       // XML (클래스패스)
```

---

## 4. Bean 생명주기

<div class="mermaid">
graph TD
    S([Spring Container 시작]) --> A
    A["[1] Bean 인스턴스 생성<br>기본 생성자 또는 @Bean 팩토리 메서드 호출"]
    A --> B["[2] 의존성 주입 DI<br>생성자 주입은 1단계에서 동시 처리<br>세터/필드 주입은 이 단계에서 처리"]
    B --> C["[3] 초기화 콜백<br>@PostConstruct<br>InitializingBean.afterPropertiesSet()<br>@Bean(initMethod='init')"]
    C --> D["[4] Bean 사용 (애플리케이션 동작)"]
    D --> E["[5] 소멸 콜백 (Container 종료 시)<br>@PreDestroy<br>DisposableBean.destroy()<br>@Bean(destroyMethod='close')"]
    E --> END([Spring Container 종료])
</div>

### 코드 예제

```java
@Component
public class DatabaseConnectionPool implements InitializingBean, DisposableBean {

    private Connection connection;

    // [3] 초기화 콜백 - 의존성 주입 완료 후 호출
    @PostConstruct
    public void init() {
        System.out.println("@PostConstruct: DB 커넥션 풀 초기화");
        // 이 시점에는 모든 의존성이 주입된 상태
    }

    @Override
    public void afterPropertiesSet() throws Exception {
        System.out.println("InitializingBean: 추가 초기화 작업");
    }

    // [5] 소멸 콜백
    @PreDestroy
    public void cleanup() {
        System.out.println("@PreDestroy: DB 커넥션 풀 정리");
    }

    @Override
    public void destroy() throws Exception {
        System.out.println("DisposableBean: 커넥션 종료");
        if (connection != null) connection.close();
    }
}
```

**권장 방법**: `@PostConstruct` / `@PreDestroy` 사용. JSR-250 표준이라 Spring에 종속되지 않는다.

---

## 5. Bean Scope

### Singleton (기본값)

컨테이너당 인스턴스 하나. 가장 널리 사용된다.

```java
@Component
// @Scope("singleton") // 생략 가능, 기본값
public class UserService {
    // 컨테이너 전체에서 단 하나의 인스턴스
}
```

```
getBean("userService") ──→ [동일한 인스턴스 반환]
getBean("userService") ──→ [동일한 인스턴스 반환]
getBean("userService") ──→ [동일한 인스턴스 반환]
```

### Prototype

요청할 때마다 새 인스턴스 생성. 소멸 콜백을 컨테이너가 관리하지 않는다.

```java
@Component
@Scope("prototype")
public class ShoppingCart {
    private List<Item> items = new ArrayList<>();
    // 사용자마다 별도 인스턴스 필요
}
```

```
getBean("shoppingCart") ──→ [새 인스턴스 A]
getBean("shoppingCart") ──→ [새 인스턴스 B]
getBean("shoppingCart") ──→ [새 인스턴스 C]
```

### Singleton + Prototype 혼용 문제

Singleton Bean이 Prototype Bean을 주입받으면 문제가 발생한다.

```java
@Component
public class SingletonService {
    @Autowired
    private PrototypeBean prototypeBean; // 주입 시점에 딱 한 번만 생성됨!
    // 이후 prototypeBean은 항상 같은 인스턴스 → prototype 의미 없음
}
```

**해결책**: `ObjectProvider` 또는 `ApplicationContext` 사용

```java
@Component
public class SingletonService {
    @Autowired
    private ObjectProvider<PrototypeBean> prototypeBeanProvider;

    public void logic() {
        PrototypeBean prototypeBean = prototypeBeanProvider.getObject(); // 매번 새 인스턴스
        prototypeBean.doSomething();
    }
}
```

### Web Scope (웹 환경에서만 동작)

| Scope | 생명주기 |
|-------|---------|
| `request` | HTTP 요청 하나 동안 |
| `session` | HTTP 세션 동안 |
| `application` | 서블릿 컨텍스트 동안 (싱글톤과 유사) |
| `websocket` | WebSocket 세션 동안 |

```java
@Component
@Scope(value = "request", proxyMode = ScopedProxyMode.TARGET_CLASS)
public class MyLogger {
    private String requestURL;

    public void setRequestURL(String requestURL) {
        this.requestURL = requestURL;
    }

    public void log(String message) {
        System.out.println("[" + requestURL + "] " + message);
    }
}
```

`proxyMode = ScopedProxyMode.TARGET_CLASS`: 싱글톤 Bean에 주입될 때 프록시 객체로 감싸서 실제 요청 시 진짜 인스턴스에 위임한다.

---

## 6. DI(Dependency Injection) 방식 비교

### 생성자 주입 (Constructor Injection) — 권장

```java
@Service
public class OrderService {
    private final OrderRepository orderRepository;
    private final DiscountPolicy discountPolicy;

    @Autowired // 생성자가 하나면 생략 가능
    public OrderService(OrderRepository orderRepository,
                        DiscountPolicy discountPolicy) {
        this.orderRepository = orderRepository;
        this.discountPolicy = discountPolicy;
    }
}
```

**장점**:
- `final` 키워드 사용 가능 → 불변성 보장
- 테스트 시 의존성 명확하게 드러남
- 컴파일 시점에 누락된 의존성 발견
- 순환 참조를 시작 시점에 감지 (Spring Boot 2.6+)

### 세터 주입 (Setter Injection)

```java
@Service
public class OrderService {
    private OrderRepository orderRepository;

    @Autowired
    public void setOrderRepository(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }
}
```

**용도**: 선택적 의존성, 변경 가능한 의존성. 실무에서 거의 사용하지 않는다.

### 필드 주입 (Field Injection) — 비권장

```java
@Service
public class OrderService {
    @Autowired
    private OrderRepository orderRepository; // 테스트 불편, 숨겨진 의존성
}
```

**단점**:
- `final` 사용 불가 → 불변성 없음
- 테스트 시 Mock 주입이 까다로움 (reflection 필요)
- 의존성이 숨겨져 있어 SRP 위반을 눈치채기 어려움
- Spring 컨테이너 없이 사용 불가

### 왜 생성자 주입이 권장되는가?

```java
// 필드 주입 - 테스트 시 문제
class OrderServiceTest {
    @Test
    void test() {
        OrderService service = new OrderService();
        // orderRepository가 null! Spring 없이 생성하면 주입이 안 됨
        service.createOrder(...); // NullPointerException
    }
}

// 생성자 주입 - 테스트 용이
class OrderServiceTest {
    @Test
    void test() {
        OrderRepository mockRepo = mock(OrderRepository.class);
        DiscountPolicy mockPolicy = mock(DiscountPolicy.class);
        OrderService service = new OrderService(mockRepo, mockPolicy); // 명확
        service.createOrder(...); // 정상 동작
    }
}
```

---

## 7. @Autowired 동작 원리

`@Autowired`는 Spring이 Bean을 자동으로 찾아 주입하는 어노테이션이다.

### 매칭 순서

<div class="mermaid">
graph TD
    A["1. 타입Type으로 매칭 시도<br>ApplicationContext에서 해당 타입의 Bean 검색"] --> B{타입 매칭 Bean이 2개 이상?}
    B -->|"@Qualifier 있음"| C["@Qualifier 확인<br>@Qualifier('mainDiscountPolicy') Bean 선택"]
    B -->|"@Primary 있음"| D["@Primary 확인<br>@Primary가 붙은 Bean 선택"]
    B -->|"그 외"| E["필드명/파라미터명으로 매칭<br>변수명과 일치하는 Bean ID 선택"]
    C --> F[주입 완료]
    D --> F
    E --> F
</div>

### 예제

```java
// Bean이 두 개 등록된 경우
@Component
public class FixDiscountPolicy implements DiscountPolicy { ... }

@Component
@Primary  // 우선순위 부여
public class RateDiscountPolicy implements DiscountPolicy { ... }

@Service
public class OrderService {
    private final DiscountPolicy discountPolicy;

    @Autowired
    public OrderService(DiscountPolicy discountPolicy) {
        // @Primary가 붙은 RateDiscountPolicy가 주입됨
        this.discountPolicy = discountPolicy;
    }
}
```

```java
// @Qualifier 사용
@Component
@Qualifier("mainPolicy")
public class RateDiscountPolicy implements DiscountPolicy { ... }

@Service
public class OrderService {
    @Autowired
    public OrderService(@Qualifier("mainPolicy") DiscountPolicy discountPolicy) {
        this.discountPolicy = discountPolicy;
    }
}
```

**@Primary vs @Qualifier**: @Qualifier가 더 세밀한 제어이므로 우선순위가 높다.

### 모든 Bean 주입받기

```java
@Service
public class DiscountService {
    private final Map<String, DiscountPolicy> policyMap;
    private final List<DiscountPolicy> policies;

    @Autowired
    public DiscountService(Map<String, DiscountPolicy> policyMap,
                           List<DiscountPolicy> policies) {
        this.policyMap = policyMap;   // {"fixDiscountPolicy": ..., "rateDiscountPolicy": ...}
        this.policies = policies;      // [FixDiscountPolicy, RateDiscountPolicy]
    }

    public int discount(String policyCode, int price) {
        DiscountPolicy policy = policyMap.get(policyCode);
        return policy.discount(price);
    }
}
```

---

## 8. 순환 참조 문제와 해결

### 순환 참조란?

```
A → B → C → A  (순환!)

@Service
public class A {
    @Autowired B b;  // A는 B가 필요
}

@Service
public class B {
    @Autowired C c;  // B는 C가 필요
}

@Service
public class C {
    @Autowired A a;  // C는 A가 필요 → 순환!
}
```

### Spring Boot 2.6+ 기본 동작

Spring Boot 2.6부터 생성자 주입의 순환 참조는 **시작 시점에 예외 발생**한다.

```
***************************
APPLICATION FAILED TO START
***************************
The dependencies of some of the beans in the application context
form a cycle:

a → b → c → a
```

세터/필드 주입은 Bean 생성 후 주입하므로 런타임까지 발견이 늦어질 수 있다.

### 해결 방법

**방법 1: 설계 변경 (가장 좋은 방법)**

순환 참조는 대부분 **설계 문제**다. 공통 기능을 별도 컴포넌트로 추출한다.

```java
// 순환 참조 발생
// UserService ↔ OrderService

// 해결: 공통 기능을 별도 서비스로 분리
@Service
public class CommonService {
    // UserService와 OrderService가 공통으로 필요한 기능
}

@Service
public class UserService {
    @Autowired CommonService commonService;
}

@Service
public class OrderService {
    @Autowired CommonService commonService;
}
```

**방법 2: @Lazy**

```java
@Service
public class A {
    private final B b;

    @Autowired
    public A(@Lazy B b) {  // B를 실제 사용 시점까지 지연 로딩
        this.b = b;
    }
}
```

**방법 3: application.properties 설정 (임시방편, 비권장)**

```properties
spring.main.allow-circular-references=true
```

이 옵션은 임시 해결책이며, 순환 참조의 근본 원인을 해결해야 한다.

---

## 정리

| 개념 | 핵심 |
|------|------|
| IoC | 객체 생성/관리 제어권을 컨테이너에 위임 |
| BeanFactory | 기본 Bean 관리, Lazy Loading |
| ApplicationContext | BeanFactory 확장, Eager Loading, 실무 표준 |
| Bean 생명주기 | 생성 → DI → 초기화(@PostConstruct) → 사용 → 소멸(@PreDestroy) |
| Singleton | 컨테이너당 1개 인스턴스, 기본값 |
| Prototype | 요청마다 새 인스턴스 |
| 생성자 주입 | final 보장, 테스트 용이, 순환참조 조기 발견 → 권장 |
| @Autowired | 타입 → @Qualifier → @Primary → 필드명 순으로 매칭 |
| 순환 참조 | 설계 문제, 컴포넌트 분리로 해결 |
