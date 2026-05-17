---
title: "Spring 면접 — DI/IoC 핵심 질문 (Q1~Q10)"
categories: INTERVIEW
tags: [Spring, 면접, DI,IoC,Bean,Component]
toc: true
toc_sticky: true
toc_label: 목차
---

## 1. DI / IoC 핵심 질문 (Q1 ~ Q10)

### Q1. IoC와 DI의 차이를 설명하세요

**모범 답변**

IoC(Inversion of Control)는 **제어의 역전** 원칙입니다. 전통적으로는 객체가 스스로 의존성을 생성하지만, IoC에서는 그 제어권을 컨테이너(Spring)에게 넘깁니다.

DI(Dependency Injection)는 IoC를 **구현하는 방법** 중 하나입니다. 컨테이너가 외부에서 의존성을 주입해 줍니다.

> **비유:** IoC는 "음식 주문을 내가 하지 않고 배달부에게 맡긴다"는 개념이고, DI는 "배달부가 문 앞까지 음식을 가져다준다"는 구체적 방법입니다.

**왜 이 질문을 하는가**

많은 지원자가 IoC = DI로 혼동합니다. 원칙과 구현의 차이를 아는지 확인합니다.

**흔한 실수**

"IoC 컨테이너가 DI를 해준다"로 끝내는 것. Service Locator 패턴도 IoC의 구현임을 모르는 경우가 많습니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** Service Locator 패턴과 DI의 차이는?

Service Locator는 객체가 레지스트리에서 직접 의존성을 찾아옵니다. DI는 외부에서 주입받습니다. DI가 더 테스트하기 쉽고, 의존성이 명시적으로 드러납니다.

**실무 연결:** 레거시 코드에서 `new` 키워드 남발 → IoC 도입 → 테스트 용이성 향상

</details>

---

### Q2. Spring Bean의 생명주기를 설명하세요

**모범 답변**

Bean 생명주기는 다음 순서로 진행됩니다.

```
컨테이너 시작
  → Bean 정의 로딩
  → Bean 인스턴스 생성
  → 의존성 주입
  → BeanPostProcessor (before) 실행
  → @PostConstruct 또는 InitializingBean.afterPropertiesSet()
  → BeanPostProcessor (after) 실행
  → Bean 사용
  → @PreDestroy 또는 DisposableBean.destroy()
  → 컨테이너 종료
```

> **비유:** 신입사원 입사 과정과 같습니다. 채용(인스턴스 생성) → 팀 배정(의존성 주입) → OJT(초기화) → 업무 수행(사용) → 퇴사 처리(소멸)

**왜 이 질문을 하는가**

초기화 로직 위치 선택(생성자 vs `@PostConstruct`)과 리소스 해제 타이밍을 제대로 아는지 확인합니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** `@PostConstruct`와 `InitializingBean`의 차이는?

`@PostConstruct`는 JSR-250 표준이라 Spring 비의존적입니다. `InitializingBean`은 Spring 인터페이스 구현이 필요해 결합도가 높습니다. 실무에서는 `@PostConstruct`를 권장합니다.

**꼬리질문:** 싱글톤 Bean에서 `@PostConstruct`가 여러 번 호출되나요?

아닙니다. 싱글톤은 컨테이너 시작 시 한 번만 초기화됩니다.

</details>

---

### Q3. @Autowired, @Resource, @Inject의 차이는?

**모범 답변**

| 애노테이션 | 출처 | 주입 우선순위 |
|---|---|---|
| `@Autowired` | Spring | 타입 → 이름 |
| `@Resource` | Java EE (JSR-250) | 이름 → 타입 |
| `@Inject` | Java EE (JSR-330) | 타입 → 이름 |

`@Autowired`는 Spring 전용이고, `@Resource`와 `@Inject`는 표준 스펙입니다. 동일 타입 Bean이 여러 개일 때 `@Qualifier`와 함께 사용합니다.

> **비유:** 편의점에서 물건 찾기 - `@Autowired`는 "음료 코너에서 콜라"(타입), `@Resource`는 "2번 선반 왼쪽 콜라"(이름) 방식

**왜 이 질문을 하는가**

Bean 충돌 상황(NoUniqueBeanDefinitionException) 해결 능력을 봅니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** 같은 타입 Bean이 2개일 때 해결 방법 3가지는?

1. `@Qualifier("beanName")` 명시
2. `@Primary`로 우선 Bean 지정
3. 필드/파라미터 이름을 Bean 이름과 일치시키기

</details>

---

### Q4. 생성자 주입이 권장되는 이유는?

**모범 답변**

생성자 주입이 권장되는 이유는 세 가지입니다.

1. **불변성**: `final` 필드 선언 가능 → 의존성 변경 불가
2. **순환 참조 감지**: 컴파일 타임 또는 애플리케이션 시작 시점에 즉시 에러 발생
3. **테스트 용이성**: Spring 컨텍스트 없이 `new`로 직접 생성 가능

```java
@Service
public class OrderService {
    private final PaymentService paymentService; // final 가능

    public OrderService(PaymentService paymentService) {
        this.paymentService = paymentService;
    }
}
```

> **비유:** 집을 지을 때 기초 공사(생성자)에서 전기/수도를 연결하는 것. 나중에 벽 뚫어서 배선하는 것(필드 주입)보다 훨씬 안전합니다.

**왜 이 질문을 하는가**

Spring 공식 문서도 생성자 주입을 권장합니다. 이를 이유와 함께 설명할 수 있는지 봅니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** 순환 의존성이 생기면 어떻게 해결하나요?

1. 설계 재검토 — 순환 자체가 설계 문제 신호
2. `@Lazy` 주입으로 지연 로딩
3. 인터페이스 분리 또는 중간 서비스 도입

Spring Boot 2.6부터 순환 의존성 기본 차단됩니다.

</details>

---

### Q5. ApplicationContext와 BeanFactory의 차이는?

**모범 답변**

`BeanFactory`는 기본 IoC 컨테이너로 지연 초기화(Lazy)가 기본입니다. `ApplicationContext`는 `BeanFactory`를 확장하여 다음을 추가 제공합니다.

- 국제화(MessageSource)
- 이벤트 발행(ApplicationEventPublisher)
- 리소스 로딩(ResourceLoader)
- AOP 통합
- 즉시 초기화(Eager) - 시작 시 모든 싱글톤 Bean 생성

실무에서는 항상 `ApplicationContext`를 사용합니다.

> **비유:** `BeanFactory`는 기본 자동차, `ApplicationContext`는 내비게이션·열선시트·후방카메라가 장착된 풀옵션 자동차

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** Eager vs Lazy 초기화의 트레이드오프는?

Eager: 시작이 느리지만 실행 중 에러 없음 (Bean 설정 오류를 시작 시 발견)
Lazy: 시작이 빠르지만 첫 호출 시 지연 + 런타임 에러 위험

프로덕션에서는 Eager가 더 안전합니다.

</details>

---

### Q6. @Component, @Service, @Repository, @Controller의 차이는?

**모범 답변**

모두 `@Component`의 특수화(specialization)입니다. 기능적 차이는 거의 없지만 의미적 차이가 있습니다.

- `@Component`: 범용 컴포넌트
- `@Service`: 비즈니스 로직 레이어
- `@Repository`: 데이터 접근 레이어 — **추가 기능**: 데이터 접근 예외를 Spring `DataAccessException`으로 변환
- `@Controller`: MVC 웹 레이어 — 요청 매핑 기능 추가

`@Repository`만 실질적인 추가 동작(예외 변환)이 있습니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** @Repository의 예외 변환이 왜 중요한가요?

JDBC, JPA, MyBatis 등 각기 다른 DB 기술의 예외를 `DataAccessException` 계층으로 통일합니다. 상위 레이어에서 DB 기술에 무관하게 예외를 처리할 수 있습니다.

</details>

---

### Q7. @Configuration과 @Component의 차이는?

**모범 답변**

`@Configuration` 클래스는 CGLIB 프록시로 감싸집니다. 따라서 `@Bean` 메서드를 여러 번 호출해도 **항상 같은 싱글톤 인스턴스**를 반환합니다.

`@Component`에 `@Bean`을 선언하면(lite mode) 프록시 없이 일반 메서드 호출이 됩니다. 같은 `@Bean` 메서드를 두 번 호출하면 다른 인스턴스가 생성될 수 있습니다.

```java
@Configuration
public class AppConfig {
    @Bean
    public DataSource dataSource() { return new HikariDataSource(); }

    @Bean
    public JdbcTemplate jdbcTemplate() {
        return new JdbcTemplate(dataSource()); // 같은 dataSource 반환 보장
    }
}
```

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** proxyBeanMethods=false는 언제 사용하나요?

Bean 간 의존이 없고 시작 성능이 중요할 때 `@Configuration(proxyBeanMethods = false)`를 사용합니다. Spring Boot Auto-configuration에서 많이 사용됩니다.

</details>

---

### Q8. Bean Scope의 종류와 사용 시점은?

**모범 답변**

| Scope | 설명 | 사용 시점 |
|---|---|---|
| singleton | 컨테이너당 1개 (기본값) | 상태 없는 서비스, Repository |
| prototype | 요청마다 새 인스턴스 | 상태를 가지는 객체 |
| request | HTTP 요청당 1개 | 웹 환경, 요청 컨텍스트 |
| session | HTTP 세션당 1개 | 로그인 사용자 정보 |
| application | ServletContext당 1개 | 앱 전역 공유 데이터 |

> **비유:** 싱글톤은 사무실 복합기(모두 공유), 프로토타입은 개인 노트(사람마다 새것), 리퀘스트는 점심 주문서(한 끼마다 새로 작성)

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** 싱글톤 Bean에 프로토타입 Bean을 주입하면 무슨 문제가 생기나요?

싱글톤은 한 번 생성되므로 주입된 프로토타입도 한 번만 생성됩니다. 해결책: `ApplicationContext.getBean()`, `ObjectProvider<T>`, `@Lookup` 메서드 주입

</details>

---

### Q9. Spring에서 싱글톤 Bean은 Thread-safe한가요?

**모범 답변**

싱글톤 자체는 Thread-safe하지 않습니다. Spring은 싱글톤 인스턴스를 관리하지만 그 안의 상태(field)에 대한 동기화는 개발자 책임입니다.

**안전한 패턴:** 상태 없는(stateless) Bean 설계

```java
@Service
public class OrderService {
    // 상태 없음 → Thread-safe
    public Order process(OrderRequest request) {
        // 지역 변수만 사용
    }
}
```

**위험한 패턴:** 인스턴스 변수에 요청 데이터 저장

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** 상태가 필요하면 어떻게 하나요?

1. 메서드 파라미터로 전달
2. ThreadLocal 사용 (요청 범위 데이터)
3. 프로토타입 스코프 Bean 사용
4. `synchronized` 또는 동시성 컬렉션 활용

</details>

---

### Q10. @Value와 @ConfigurationProperties의 차이는?

**모범 답변**

`@Value`는 단일 값 주입에 적합하고 SpEL을 지원합니다. `@ConfigurationProperties`는 관련 설정을 그룹화하여 타입 안전하게 바인딩합니다.

```java
// @Value 방식
@Value("${payment.timeout:5000}")
private int timeout;

// @ConfigurationProperties 방식
@ConfigurationProperties(prefix = "payment")
public class PaymentProperties {
    private int timeout = 5000;
    private String apiKey;
    // getter/setter
}
```

`@ConfigurationProperties`가 IDE 자동완성, 타입 검증, 문서화 측면에서 우수합니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** @ConfigurationProperties에서 검증은 어떻게 하나요?

`@Validated`와 Bean Validation 애노테이션을 함께 사용합니다.

```java
@ConfigurationProperties(prefix = "payment")
@Validated
public class PaymentProperties {
    @Min(1000) @Max(30000)
    private int timeout;
    @NotBlank
    private String apiKey;
}
```

</details>

---

---

## 다른 파트 보기

- [Part 1: DI/IoC (Q1~Q10)](/interview/spring-interview-part1/)
- [Part 2: AOP (Q11~Q18)](/interview/spring-interview-part2/)
- [Part 3: Transaction (Q19~Q27)](/interview/spring-interview-part3/)
- [Part 4: JPA (Q28~Q38)](/interview/spring-interview-part4/)
- [Part 5: Security (Q39~Q45)](/interview/spring-interview-part5/)
- [Part 6: WebFlux (Q46~Q50)](/interview/spring-interview-part6/)
