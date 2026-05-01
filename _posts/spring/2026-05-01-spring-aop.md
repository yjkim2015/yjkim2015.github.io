---
title: "Spring AOP 동작 원리"
categories:
- SPRING
toc: true
toc_sticky: true
toc_label: 목차
---

## 1. AOP란? (관심사 분리)

로그인 체크, 트랜잭션 시작/종료, 실행 시간 측정 — 이 코드가 서비스 50개에 똑같이 붙어 있다면? 하나를 고칠 때마다 50군데를 손봐야 한다. AOP는 이 반복을 끊는 방법이다.

> **비유로 먼저 이해하기**: AOP는 건물 CCTV와 같다. 각 방(서비스 클래스)마다 카메라를 설치하는 대신, 건물 입구 하나에 카메라를 달면 모든 출입을 감시할 수 있다. 로깅·트랜잭션·보안이 바로 그 입구 카메라 역할이다.

AOP(Aspect-Oriented Programming)는 **횡단 관심사(Cross-Cutting Concerns)**를 핵심 비즈니스 로직과 분리하는 프로그래밍 패러다임이다.

### 횡단 관심사의 문제

```java
// AOP 없이 로깅, 트랜잭션, 보안을 직접 구현
public class OrderService {
    public Order createOrder(OrderDto dto) {
        // 보안 체크
        SecurityContext.checkPermission("ORDER_CREATE");

        // 트랜잭션 시작
        Transaction tx = TransactionManager.begin();

        // 로깅
        log.info("createOrder 시작: {}", dto);
        long startTime = System.currentTimeMillis();

        try {
            // ↓ 실제 비즈니스 로직 (단 몇 줄)
            Order order = new Order(dto);
            orderRepository.save(order);
            // ↑ 여기까지가 핵심

            tx.commit();
            log.info("createOrder 완료: {}ms", System.currentTimeMillis() - startTime);
            return order;
        } catch (Exception e) {
            tx.rollback();
            log.error("createOrder 실패", e);
            throw e;
        }
    }
}
```

비즈니스 로직(주문 생성)은 2~3줄인데 나머지는 모두 부가 기능이다. 이런 코드가 수십 개 서비스에 반복된다.

### AOP로 분리

```java
// 핵심 로직만 남긴 서비스
@Service
public class OrderService {
    public Order createOrder(OrderDto dto) {
        Order order = new Order(dto);
        orderRepository.save(order);
        return order;
    }
}

// 부가 기능을 한 곳에 모음
@Aspect
@Component
public class LoggingAspect {
    @Around("execution(* com.example.service.*.*(..))")
    public Object logExecutionTime(ProceedingJoinPoint joinPoint) throws Throwable {
        long start = System.currentTimeMillis();
        Object result = joinPoint.proceed();
        log.info("{} 실행시간: {}ms",
            joinPoint.getSignature().getName(),
            System.currentTimeMillis() - start);
        return result;
    }
}
```

---

## 2. 핵심 용어

### Aspect

횡단 관심사를 모듈화한 것. Advice + Pointcut의 조합.

```java
@Aspect  // 이 클래스가 Aspect임을 선언
@Component
public class TransactionAspect {
    // Pointcut + Advice = Aspect
}
```

### Advice

Aspect가 언제 무엇을 할지 정의. 실제로 실행되는 코드.

| Advice 종류 | 어노테이션 | 실행 시점 |
|------------|-----------|---------|
| Before | `@Before` | 메서드 실행 전 |
| After Returning | `@AfterReturning` | 정상 반환 후 |
| After Throwing | `@AfterThrowing` | 예외 발생 후 |
| After | `@After` | 정상/예외 모두 (finally) |
| Around | `@Around` | 실행 전/후 모두 제어 |

```java
@Aspect
@Component
public class LoggingAspect {

    // 메서드 실행 전
    @Before("execution(* com.example.service.*.*(..))")
    public void logBefore(JoinPoint joinPoint) {
        log.info("→ {} 호출", joinPoint.getSignature().getName());
    }

    // 정상 반환 후
    @AfterReturning(pointcut = "execution(* com.example.service.*.*(..))",
                    returning = "result")
    public void logAfterReturning(JoinPoint joinPoint, Object result) {
        log.info("← {} 반환: {}", joinPoint.getSignature().getName(), result);
    }

    // 예외 발생 후
    @AfterThrowing(pointcut = "execution(* com.example.service.*.*(..))",
                   throwing = "ex")
    public void logAfterThrowing(JoinPoint joinPoint, Exception ex) {
        log.error("✗ {} 예외: {}", joinPoint.getSignature().getName(), ex.getMessage());
    }

    // 가장 강력: 실행 전/후 모두 제어
    @Around("execution(* com.example.service.*.*(..))")
    public Object logAround(ProceedingJoinPoint joinPoint) throws Throwable {
        log.info("→ 시작");
        try {
            Object result = joinPoint.proceed(); // 실제 메서드 실행
            log.info("← 성공");
            return result;
        } catch (Exception e) {
            log.error("✗ 실패");
            throw e;
        }
    }
}
```

### Pointcut

Advice를 적용할 메서드를 선별하는 표현식.

```java
// execution 표현식 문법
// execution([접근제어자] 반환타입 [선언타입].메서드명(파라미터) [예외])

execution(* com.example.service.*.*(..))
//        ^  ^^^^^^^^^^^^^^^^^^^^^^^  ^^
//        |  패키지.클래스.메서드     파라미터(모두)
//        반환타입(모두)

// 자주 쓰는 패턴
@Pointcut("execution(* com.example.service..*(..))")  // service 하위 모든 메서드
@Pointcut("@annotation(org.springframework.transaction.annotation.Transactional)")  // 어노테이션 기반
@Pointcut("within(com.example.service.*)")  // 특정 패키지 내 모든 메서드
@Pointcut("bean(orderService)")  // 특정 Bean
```

```java
// Pointcut 재사용
@Aspect
@Component
public class MyAspect {

    @Pointcut("execution(* com.example.service.*.*(..))")
    public void serviceLayer() {}  // 빈 메서드, 이름만 사용

    @Pointcut("execution(* com.example.repository.*.*(..))")
    public void repositoryLayer() {}

    @Pointcut("serviceLayer() || repositoryLayer()")
    public void applicationLayer() {}

    @Before("applicationLayer()")
    public void log(JoinPoint joinPoint) { ... }
}
```

### JoinPoint

Advice가 적용될 수 있는 지점. Spring AOP에서는 **메서드 실행**만 JoinPoint다.

```java
@Before("execution(* com.example.service.*.*(..))")
public void before(JoinPoint joinPoint) {
    // JoinPoint에서 꺼낼 수 있는 정보
    String methodName = joinPoint.getSignature().getName();
    Object[] args = joinPoint.getArgs();
    Object target = joinPoint.getTarget();         // 실제 대상 객체
    Object proxy = joinPoint.getThis();            // 프록시 객체
    String className = joinPoint.getTarget().getClass().getName();
}
```

### Weaving

Aspect를 Target 객체에 적용하는 과정.

| Weaving 시점 | 설명 |
|-------------|------|
| Compile-time | 컴파일 시 바이트코드 조작 (AspectJ) |
| Load-time | 클래스 로딩 시 조작 (AspectJ LTW) |
| **Runtime** | 런타임 프록시 생성 (**Spring AOP**) |

---

## 3. Spring AOP vs AspectJ

| 구분 | Spring AOP | AspectJ |
|------|-----------|---------|
| Weaving | Runtime (프록시) | Compile/Load-time (바이트코드 조작) |
| 적용 대상 | Spring Bean의 메서드만 | 모든 Java 코드 (필드, 생성자 등) |
| 설정 복잡도 | 간단 | 복잡 (컴파일러/에이전트 필요) |
| 성능 | 약간 낮음 | 높음 (런타임 오버헤드 없음) |
| 실무 사용 | 대부분 상황에서 충분 | 필드 접근, Spring Bean 외 적용 필요 시 |

Spring AOP는 AspectJ의 어노테이션(`@Aspect`, `@Before` 등)을 차용하지만, 내부적으로는 **프록시 기반**으로 동작한다.

```java
// Spring AOP: AspectJ 어노테이션을 사용하지만 프록시로 동작
@EnableAspectJAutoProxy  // Spring Boot는 자동 활성화
@Configuration
public class AopConfig { }
```

---

## 4. 프록시 기반 AOP

Spring AOP의 핵심은 **프록시 패턴**이다. 실제 객체 대신 프록시 객체를 주입해서 부가 기능을 추가한다.

<div class="mermaid">
graph TD
    A[클라이언트] -->|"getBean('orderService')"| B["Proxy Object<br>Spring이 자동 생성"]
    B -->|"joinPoint.proceed()"| C["Real OrderService<br>실제 Bean"]
</div>

### JDK Dynamic Proxy

인터페이스가 있을 때 사용. `java.lang.reflect.Proxy`를 활용해 런타임에 인터페이스 구현체를 생성.

```java
// 인터페이스 존재
public interface OrderService {
    Order createOrder(OrderDto dto);
}

@Service
public class OrderServiceImpl implements OrderService {
    public Order createOrder(OrderDto dto) { ... }
}

// Spring이 생성하는 JDK 동적 프록시 (개념)
public class OrderServiceProxy implements OrderService {
    private final OrderService target;
    private final List<MethodInterceptor> interceptors;

    public Order createOrder(OrderDto dto) {
        // Before Advice 실행
        // target.createOrder(dto) 호출
        // After Advice 실행
    }
}
```

**제약**: 인터페이스를 통해서만 접근 가능. 구체 클래스 타입으로 주입받으면 오류.

```java
// 오류 발생: JDK 프록시는 인터페이스 구현체
@Autowired
private OrderServiceImpl orderService; // ClassCastException!

// 정상: 인터페이스 타입으로 주입
@Autowired
private OrderService orderService; // OK
```

### CGLIB (Code Generation Library)

인터페이스가 없거나 구체 클래스로 주입받을 때 사용. 바이트코드 조작으로 **서브클래스**를 생성.

```java
// 인터페이스 없는 클래스에도 적용
@Service
public class PaymentService {
    public void pay(int amount) { ... }
}

// CGLIB이 생성하는 프록시 (개념)
public class PaymentService$$EnhancerBySpringCGLIB extends PaymentService {
    @Override
    public void pay(int amount) {
        // Advice 실행
        super.pay(amount);
        // Advice 실행
    }
}
```

**제약**: `final` 클래스/메서드에 적용 불가.

### Spring Boot의 기본값

Spring Boot 2.0+부터는 **CGLIB을 기본**으로 사용한다.

```properties
# application.properties
spring.aop.proxy-target-class=true  # 기본값: CGLIB 사용
# false로 변경 시 인터페이스 있으면 JDK Dynamic Proxy 사용
```

<div class="mermaid">
graph TD
    A[AOP 적용 대상인가?] --> B{인터페이스가 있는가?}
    B -->|NO| E[CGLIB 프록시 생성]
    B -->|YES| C{"spring.aop.proxy-target-class=true?<br>기본값"}
    C -->|YES| E
    C -->|NO| D[JDK Dynamic Proxy 생성]
</div>

---

## 5. @Transactional의 AOP 동작 원리

`@Transactional`은 Spring AOP의 대표적인 활용 사례다.

<div class="mermaid">
sequenceDiagram
    participant C as 클라이언트
    participant P as TransactionInterceptor (Proxy)
    participant S as 실제 OrderService

    C->>P: orderService.createOrder(dto)
    P->>P: 1. TransactionManager.getTransaction() - 트랜잭션 시작
    P->>S: 2. joinPoint.proceed()
    S-->>P: 반환
    alt 정상
        P->>P: 3-a. TransactionManager.commit()
    else 예외
        P->>P: 3-b. TransactionManager.rollback()
    end
    P-->>C: 응답
</div>

```java
@Service
public class OrderService {

    @Transactional  // → AOP 프록시가 트랜잭션 처리
    public Order createOrder(OrderDto dto) {
        // 이 메서드 실행 전: 트랜잭션 시작
        Order order = orderRepository.save(new Order(dto));
        notificationService.notify(order);
        return order;
        // 정상 반환: commit / 예외 발생: rollback
    }
}
```

---

## 6. AOP가 동작하지 않는 케이스

### Self-Invocation (내부 호출)

가장 흔한 함정이다.

```java
@Service
public class OrderService {

    @Transactional
    public void createOrder(OrderDto dto) {
        // ...
        this.sendNotification(dto);  // ← 문제!
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void sendNotification(OrderDto dto) {
        // REQUIRES_NEW가 적용되지 않음!
        // this는 프록시가 아닌 실제 객체
    }
}
```

<div class="mermaid">
graph LR
    C[클라이언트] --> P[Proxy]
    P --> R["실제 OrderService.createOrder()"]
    R -->|"this.sendNotification() - 프록시 우회!"| N["실제 OrderService.sendNotification()<br>AOP 적용 안 됨"]

    style N fill:#ffe0e0
    style R fill:#fff8e0
</div>

**해결책 1: 빈 분리**

```java
@Service
public class OrderService {
    @Autowired
    private NotificationService notificationService; // 별도 Bean

    @Transactional
    public void createOrder(OrderDto dto) {
        notificationService.sendNotification(dto); // 프록시를 통해 호출
    }
}

@Service
public class NotificationService {
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void sendNotification(OrderDto dto) { ... }
}
```

**해결책 2: ApplicationContext에서 자기 자신 꺼내기 (비권장)**

```java
@Service
public class OrderService implements ApplicationContextAware {
    private ApplicationContext applicationContext;

    @Transactional
    public void createOrder(OrderDto dto) {
        OrderService self = applicationContext.getBean(OrderService.class);
        self.sendNotification(dto); // 프록시를 통해 호출
    }
}
```

### private 메서드

```java
@Service
public class OrderService {

    @Transactional
    private void createOrder() {  // private → AOP 적용 안 됨
        // ...
    }
}
```

CGLIB은 서브클래스를 생성하는데 `private` 메서드는 오버라이드 불가. JDK 프록시도 인터페이스에 `private`을 선언할 수 없으므로 동일.

### final 클래스/메서드

```java
@Service
public final class OrderService {  // final → CGLIB 프록시 생성 불가
    @Transactional
    public void createOrder() { ... }
}
```

### Spring Bean이 아닌 경우

```java
// new로 직접 생성한 객체는 AOP 적용 안 됨
OrderService orderService = new OrderService();
orderService.createOrder(); // @Transactional 동작 안 함
```

---

## 7. Advice 실행 순서

여러 Aspect가 같은 JoinPoint에 적용될 때 순서를 제어해야 한다.

```java
@Aspect
@Component
@Order(1)  // 숫자가 낮을수록 먼저 실행
public class SecurityAspect {
    @Around("execution(* com.example.service.*.*(..))")
    public Object check(ProceedingJoinPoint pjp) throws Throwable {
        // 보안 검사
        return pjp.proceed();
    }
}

@Aspect
@Component
@Order(2)
public class TransactionAspect {
    @Around("execution(* com.example.service.*.*(..))")
    public Object transaction(ProceedingJoinPoint pjp) throws Throwable {
        // 트랜잭션 관리
        return pjp.proceed();
    }
}

@Aspect
@Component
@Order(3)
public class LoggingAspect {
    @Around("execution(* com.example.service.*.*(..))")
    public Object log(ProceedingJoinPoint pjp) throws Throwable {
        // 로깅
        return pjp.proceed();
    }
}
```

<div class="mermaid">
sequenceDiagram
    participant C as 클라이언트
    participant SA as SecurityAspect (Order 1)
    participant TA as TransactionAspect (Order 2)
    participant LA as LoggingAspect (Order 3)
    participant M as 실제 메서드

    C->>SA: 호출
    SA->>TA: before()
    TA->>LA: before()
    LA->>M: 실행
    M-->>LA: 반환
    LA-->>TA: after()
    TA-->>SA: after()
    SA-->>C: 반환
</div>

---

## 정리

| 개념 | 핵심 |
|------|------|
| AOP | 횡단 관심사(로깅, 트랜잭션 등)를 핵심 로직과 분리 |
| Aspect | Advice + Pointcut의 모듈 |
| Advice | 실제 실행 코드 (Before/After/Around 등) |
| Pointcut | Advice 적용 대상 선별 표현식 |
| JoinPoint | Advice가 적용되는 지점 (Spring: 메서드 실행) |
| Weaving | Aspect를 Target에 적용하는 과정 |
| Spring AOP | 런타임 프록시 기반, Bean 메서드에만 적용 |
| JDK Proxy | 인터페이스 기반, Spring Boot 기본값(CGLIB 우선) |
| CGLIB | 서브클래스 생성, final 불가 |
| Self-invocation | 내부 this 호출은 프록시 우회 → AOP 미적용 |
