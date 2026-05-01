---
title: "Spring @Async"
categories: SPRING
tags: [Spring, Async, TaskExecutor, MDC, ThreadPool]
toc: true
toc_sticky: true
toc_label: 목차
date: 2026-05-01
---

Spring의 `@Async`는 메서드를 별도 스레드에서 비동기로 실행하게 만드는 애노테이션이다. 단순히 붙이면 동작하는 것처럼 보이지만, 내부 동작과 주의사항을 모르면 예외가 무시되거나 MDC 컨텍스트가 사라지는 등 운영 장애로 이어질 수 있다.

> 비유: 카페 직원(메인 스레드)이 손님 주문을 받고 "커피는 바리스타(별도 스레드)에게 맡길게요"라고 한 뒤 다음 손님을 받는 것과 같다. 단, 바리스타가 실수해도 직원은 알 수 없으므로 별도 오류 처리가 필요하다.

---

## @Async 동작 원리

### 프록시 기반 동작

`@Async`는 Spring AOP 프록시를 통해 동작한다. `@EnableAsync`가 설정되면 Spring은 `@Async`가 붙은 메서드를 가진 빈을 프록시로 감싸고, 해당 메서드 호출을 가로채서 `TaskExecutor`에 위임한다.

<div class="mermaid">
graph LR
    A[호출자] --> B[프록시]
    B -->|별도 스레드 전환| C["TaskExecutor 스레드 풀"]
    C --> D[실제 메서드 실행]
</div>

**프록시 동작 방식**
```java
// 내부적으로 이런 식으로 동작함
public class UserServiceProxy extends UserService {

    @Override
    public void sendWelcomeEmail(Long userId) {
        taskExecutor.execute(() -> super.sendWelcomeEmail(userId)); // 별도 스레드
    }
}
```

### 동작하지 않는 경우

```java
@Service
public class UserService {

    // 잘못된 예 1: 같은 빈 내부에서 this로 호출 (프록시 우회)
    public void register(User user) {
        save(user);
        sendWelcomeEmail(user.getId()); // 프록시 거치지 않음 → @Async 무시
    }

    @Async
    public void sendWelcomeEmail(Long userId) {
        // 이 메서드는 동기로 실행됨
    }

    // 잘못된 예 2: private 메서드 (프록시가 오버라이드 불가)
    @Async
    private void privateAsyncMethod() {
        // @Async 동작 안 함
    }
}
```

**해결책: 빈을 분리한다**
```java
@Service
@RequiredArgsConstructor
public class UserService {

    private final EmailService emailService; // 별도 빈

    public void register(User user) {
        save(user);
        emailService.sendWelcomeEmail(user.getId()); // 프록시 통과 → @Async 동작
    }
}

@Service
public class EmailService {

    @Async
    public void sendWelcomeEmail(Long userId) {
        // 별도 스레드에서 실행
    }
}
```

---

## @EnableAsync 설정

```java
@Configuration
@EnableAsync
public class AsyncConfig implements AsyncConfigurer {

    @Override
    public Executor getAsyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(10);          // 기본 스레드 수
        executor.setMaxPoolSize(50);           // 최대 스레드 수
        executor.setQueueCapacity(500);        // 대기 큐 크기
        executor.setThreadNamePrefix("async-"); // 스레드 이름 접두사
        executor.setKeepAliveSeconds(60);      // 유휴 스레드 유지 시간
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.initialize();
        return executor;
    }

    @Override
    public AsyncUncaughtExceptionHandler getAsyncUncaughtExceptionHandler() {
        return new CustomAsyncExceptionHandler();
    }
}
```

---

## TaskExecutor

### 스레드 풀 동작 원리

<div class="mermaid">
graph TD
    REQ[요청 도착] --> C1{corePoolSize 미만?}
    C1 -->|YES| T1[새 스레드 생성]
    C1 -->|NO| C2{queueCapacity 여유?}
    C2 -->|YES| Q[queueCapacity에 넣음]
    C2 -->|NO| C3{maxPoolSize 미만?}
    C3 -->|YES| T2[maxPoolSize까지 새 스레드 생성]
    C3 -->|NO| REJ[RejectedExecutionHandler 실행]
    style REJ fill:#f88,stroke:#c00,color:#000
    style T1 fill:#8f8,stroke:#080,color:#000
    style T2 fill:#8f8,stroke:#080,color:#000
</div>

### ThreadPoolTaskExecutor 상세 설정

```java
@Bean(name = "emailTaskExecutor")
public ThreadPoolTaskExecutor emailTaskExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(5);
    executor.setMaxPoolSize(20);
    executor.setQueueCapacity(100);
    executor.setThreadNamePrefix("email-async-");
    executor.setKeepAliveSeconds(30);

    // 거부 정책
    // AbortPolicy (기본): RejectedExecutionException 발생
    // CallerRunsPolicy: 호출자 스레드에서 직접 실행 (요청 손실 없음)
    // DiscardPolicy: 조용히 버림
    // DiscardOldestPolicy: 가장 오래된 작업을 버리고 재시도
    executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());

    // 애플리케이션 종료 시 작업 완료 대기
    executor.setWaitForTasksToCompleteOnShutdown(true);
    executor.setAwaitTerminationSeconds(30);

    executor.initialize();
    return executor;
}
```

### 여러 Executor 사용

```java
@Async("emailTaskExecutor")
public void sendEmail(String to, String body) {
    // emailTaskExecutor에서 실행
}

@Async("reportTaskExecutor")
public void generateReport(Long reportId) {
    // reportTaskExecutor에서 실행
}
```

### 반환 타입

```java
// 반환값 없음
@Async
public void sendNotification(Long userId) {
    // fire-and-forget
}

// Future 반환 (레거시)
@Async
public Future<String> processAsync() {
    return new AsyncResult<>("결과");
}

// CompletableFuture 반환 (권장)
@Async
public CompletableFuture<String> processAsync() {
    String result = doHeavyWork();
    return CompletableFuture.completedFuture(result);
}

// 호출자에서 결과 수집
CompletableFuture<String> future = service.processAsync();
String result = future.get(5, TimeUnit.SECONDS); // 타임아웃 설정 필수
```

---

## 예외 처리

### void 반환 메서드의 예외

`void` 반환 `@Async` 메서드에서 발생한 예외는 **호출자에게 전파되지 않는다**. 기본적으로 예외가 그냥 삼켜진다.

```java
@Async
public void riskyOperation() {
    throw new RuntimeException("예외 발생!"); // 호출자는 모름
}

// 호출자
service.riskyOperation(); // 예외가 발생해도 알 방법이 없음
```

**AsyncUncaughtExceptionHandler 등록**
```java
public class CustomAsyncExceptionHandler implements AsyncUncaughtExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(CustomAsyncExceptionHandler.class);

    @Override
    public void handleUncaughtException(Throwable ex, Method method, Object... params) {
        log.error("@Async 메서드 예외 발생. method={}, params={}",
            method.getName(), Arrays.toString(params), ex);

        // 알림 발송, 메트릭 수집 등
        alertService.sendAlert("비동기 작업 실패: " + method.getName());
    }
}

// AsyncConfig에서 등록
@Override
public AsyncUncaughtExceptionHandler getAsyncUncaughtExceptionHandler() {
    return new CustomAsyncExceptionHandler();
}
```

### CompletableFuture 반환 시 예외

```java
@Async
public CompletableFuture<String> processAsync() {
    try {
        String result = doWork();
        return CompletableFuture.completedFuture(result);
    } catch (Exception e) {
        return CompletableFuture.failedFuture(e); // 예외를 Future에 담아 반환
    }
}

// 호출자에서 처리
service.processAsync()
    .thenAccept(result -> log.info("성공: {}", result))
    .exceptionally(ex -> {
        log.error("실패", ex);
        return null;
    });
```

---

## MDC 전파

### 문제

`@Async`는 스레드를 전환하기 때문에 `MDC`(Mapped Diagnostic Context) 값이 새 스레드로 자동 전파되지 않는다.

```java
// 요청 스레드에서 MDC 설정
MDC.put("requestId", "abc-123");
MDC.put("userId", "42");

// @Async 메서드 호출 → 새 스레드에서 실행
emailService.sendEmail(userId); // 새 스레드에서 MDC 값이 없음
// 로그에서 requestId, userId가 공백으로 남음
```

### 해결: TaskDecorator

```java
public class MdcTaskDecorator implements TaskDecorator {

    @Override
    public Runnable decorate(Runnable runnable) {
        // 현재 스레드(호출자)의 MDC 값을 캡처
        Map<String, String> contextMap = MDC.getCopyOfContextMap();

        return () -> {
            try {
                // 새 스레드에 MDC 값 복원
                if (contextMap != null) {
                    MDC.setContextMap(contextMap);
                }
                runnable.run();
            } finally {
                // 스레드 풀 재사용 시 오염 방지
                MDC.clear();
            }
        };
    }
}
```

```java
@Bean
public ThreadPoolTaskExecutor taskExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(10);
    executor.setMaxPoolSize(50);
    executor.setQueueCapacity(500);
    executor.setTaskDecorator(new MdcTaskDecorator()); // MDC 전파 설정
    executor.initialize();
    return executor;
}
```

### Security Context 전파

Spring Security의 `SecurityContextHolder`도 같은 문제가 있다.

```java
public class SecurityMdcTaskDecorator implements TaskDecorator {

    @Override
    public Runnable decorate(Runnable runnable) {
        Map<String, String> mdcContext = MDC.getCopyOfContextMap();
        SecurityContext securityContext = SecurityContextHolder.getContext();

        return () -> {
            try {
                if (mdcContext != null) MDC.setContextMap(mdcContext);
                SecurityContextHolder.setContext(securityContext);
                runnable.run();
            } finally {
                MDC.clear();
                SecurityContextHolder.clearContext();
            }
        };
    }
}
```

또는 `SecurityContextHolder`의 전략을 변경해서 자동 전파할 수 있다.

```java
@Bean
public MethodInvokingFactoryBean securityContextHolderStrategy() {
    MethodInvokingFactoryBean bean = new MethodInvokingFactoryBean();
    bean.setTargetClass(SecurityContextHolder.class);
    bean.setTargetMethod("setStrategyName");
    bean.setArguments(SecurityContextHolder.MODE_INHERITABLETHREADLOCAL);
    return bean;
}
```

---

## 트랜잭션과 @Async

`@Async` 메서드는 호출자의 트랜잭션을 **공유하지 않는다**. 새 스레드에서 실행되므로 트랜잭션 컨텍스트가 전파되지 않는다.

```java
@Service
@RequiredArgsConstructor
public class OrderService {

    private final OrderRepository orderRepository;
    private final NotificationService notificationService;

    @Transactional
    public void placeOrder(Order order) {
        orderRepository.save(order);
        // 여기서 호출해도 새 스레드에서 실행되므로 트랜잭션 공유 안 됨
        notificationService.sendOrderNotification(order.getId());
        // 만약 이 트랜잭션이 롤백되어도 알림은 이미 발송될 수 있음
    }
}

@Service
public class NotificationService {

    @Async
    @Transactional(propagation = Propagation.REQUIRES_NEW) // 새 트랜잭션 시작
    public void sendOrderNotification(Long orderId) {
        // 별도 트랜잭션으로 실행
    }
}
```

**주문 저장 후 알림 발송 보장이 필요하다면 Transactional Event Listener 사용**

```java
@Service
public class OrderService {

    @Transactional
    public void placeOrder(Order order) {
        orderRepository.save(order);
        applicationEventPublisher.publishEvent(new OrderPlacedEvent(order.getId()));
        // 트랜잭션 커밋 후 이벤트 처리 → 순서 보장
    }
}

@Component
public class OrderEventListener {

    @Async
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onOrderPlaced(OrderPlacedEvent event) {
        // 트랜잭션 커밋 후 비동기 실행
        notificationService.send(event.orderId());
    }
}
```

---

## 실무 패턴

### 비동기 처리 결과 수집

```java
@Service
public class DashboardService {

    @Async
    public CompletableFuture<Long> countActiveUsers() {
        return CompletableFuture.completedFuture(userRepository.countByStatus(ACTIVE));
    }

    @Async
    public CompletableFuture<Long> countTodayOrders() {
        return CompletableFuture.completedFuture(orderRepository.countToday());
    }

    @Async
    public CompletableFuture<BigDecimal> getTodayRevenue() {
        return CompletableFuture.completedFuture(orderRepository.sumRevenueToday());
    }
}

@Service
@RequiredArgsConstructor
public class ReportService {

    private final DashboardService dashboardService;

    public DashboardReport buildReport() throws ExecutionException, InterruptedException {
        // 3개 쿼리 병렬 실행
        CompletableFuture<Long> users = dashboardService.countActiveUsers();
        CompletableFuture<Long> orders = dashboardService.countTodayOrders();
        CompletableFuture<BigDecimal> revenue = dashboardService.getTodayRevenue();

        CompletableFuture.allOf(users, orders, revenue).join(); // 모두 완료 대기

        return new DashboardReport(users.get(), orders.get(), revenue.get());
    }
}
```

### 타임아웃 처리

```java
@Async
public CompletableFuture<String> callExternalApi(String param) {
    String result = externalApiClient.call(param);
    return CompletableFuture.completedFuture(result);
}

// 호출자에서 타임아웃 처리
CompletableFuture<String> future = service.callExternalApi("param");
try {
    String result = future.get(3, TimeUnit.SECONDS);
} catch (TimeoutException e) {
    future.cancel(true); // 취소 시도
    log.warn("API 호출 타임아웃");
} catch (ExecutionException e) {
    log.error("API 호출 실패", e.getCause());
}
```

---

## 체크리스트

```
@Async 사용 시 확인사항:

□ @EnableAsync 설정되어 있는가?
□ @Async 메서드가 public인가?
□ 같은 빈 내부에서 this로 호출하지 않는가?
□ ThreadPoolTaskExecutor를 직접 설정했는가? (기본값은 SimpleAsyncTaskExecutor)
□ void 메서드의 예외 처리를 위해 AsyncUncaughtExceptionHandler 등록했는가?
□ MDC 전파를 위해 TaskDecorator 적용했는가?
□ 트랜잭션 경계가 올바른가?
□ CompletableFuture 반환 시 타임아웃 설정이 있는가?
□ 애플리케이션 종료 시 작업 완료 대기 설정이 있는가?
```
