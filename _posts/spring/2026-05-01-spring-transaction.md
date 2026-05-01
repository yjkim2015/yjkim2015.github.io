---
title: "Spring 트랜잭션 관리 완전 정리"
categories:
- SPRING
toc: true
toc_sticky: true
toc_label: 목차
---

## 1. 선언적 트랜잭션 (@Transactional)

Spring은 두 가지 트랜잭션 관리 방식을 제공한다.

| 방식 | 설명 | 실무 사용 |
|------|------|---------|
| 프로그래밍 방식 | `TransactionTemplate`, `PlatformTransactionManager` 직접 사용 | 거의 사용 안 함 |
| 선언적 방식 | `@Transactional` | 표준 |

### @Transactional 기본 사용

```java
@Service
public class OrderService {

    // 클래스 레벨: 모든 public 메서드에 적용
    @Transactional
    public class OrderService { ... }

    // 메서드 레벨: 해당 메서드에만 적용 (클래스 레벨보다 우선순위 높음)
    @Transactional(readOnly = true)
    public Order findOrder(Long id) {
        return orderRepository.findById(id).orElseThrow();
    }

    @Transactional
    public Order createOrder(OrderDto dto) {
        Order order = new Order(dto);
        return orderRepository.save(order);
    }
}
```

### @Transactional 주요 속성

```java
@Transactional(
    propagation = Propagation.REQUIRED,        // 전파 속성 (기본값)
    isolation = Isolation.DEFAULT,             // 격리 수준 (기본값: DB 설정 따름)
    timeout = 30,                              // 타임아웃 (초)
    readOnly = false,                          // 읽기 전용 여부
    rollbackFor = Exception.class,             // 이 예외 시 롤백
    noRollbackFor = BusinessException.class    // 이 예외는 롤백 안 함
)
public void someMethod() { ... }
```

### readOnly = true 의미

```java
@Transactional(readOnly = true)
public List<Order> getOrders() {
    return orderRepository.findAll();
}
```

- JPA: 영속성 컨텍스트의 변경 감지(Dirty Checking) 비활성화 → 스냅샷 저장 안 함 → 성능 향상
- DB: 일부 DB는 읽기 전용 트랜잭션을 최적화 처리 (MySQL: 잠금 없이 처리)
- 읽기 메서드에는 항상 `readOnly = true` 권장

---

## 2. 전파 속성 (Propagation)

전파 속성은 **이미 트랜잭션이 진행 중일 때 새로운 트랜잭션 메서드를 호출하면 어떻게 처리할지** 결정한다.

### REQUIRED (기본값)

<div class="mermaid">
sequenceDiagram
    participant C as 클라이언트
    participant TX1 as TX1 트랜잭션
    participant CO as createOrder()
    participant SL as saveLog()

    Note over C,SL: 상황 1 - 부모 트랜잭션 있음
    C->>TX1: TX1 시작
    TX1->>CO: 실행
    CO->>SL: 호출 (TX1에 참여)
    SL-->>CO: 완료
    CO-->>TX1: 완료
    TX1-->>C: TX1 커밋

    Note over C,SL: 상황 2 - 부모 트랜잭션 없음
    C->>SL: saveLog() 직접 호출
    SL->>SL: TX1 시작 → 커밋
    SL-->>C: 완료
</div>

```java
@Transactional  // REQUIRED (기본값)
public void createOrder(OrderDto dto) {
    orderRepository.save(new Order(dto));
    logService.saveLog("주문 생성"); // saveLog도 같은 TX1에 참여
    // saveLog에서 예외 → 전체 롤백
}

@Transactional  // REQUIRED
public void saveLog(String message) {
    logRepository.save(new Log(message));
}
```

**주의**: 자식(saveLog)에서 예외가 발생하면 부모(createOrder) TX도 롤백 마킹된다.

### REQUIRES_NEW

<div class="mermaid">
sequenceDiagram
    participant C as 클라이언트
    participant TX1 as TX1 (createOrder)
    participant TX2 as TX2 (saveLog - 독립)

    C->>TX1: TX1 시작
    TX1->>TX1: 작업 수행
    TX1->>TX2: saveLog() 호출 → TX2 시작 (TX1 일시 중단)
    TX2->>TX2: 작업 수행
    TX2-->>TX1: TX2 커밋 (TX1과 독립)
    TX1-->>C: TX1 커밋
</div>

```java
@Transactional
public void createOrder(OrderDto dto) {
    orderRepository.save(new Order(dto));
    logService.saveLog("주문 생성");
    // saveLog가 실패해도 createOrder는 커밋 가능
}

@Transactional(propagation = Propagation.REQUIRES_NEW)
public void saveLog(String message) {
    // TX1과 완전히 독립된 TX2
    logRepository.save(new Log(message));
    // 실패해도 TX1에 영향 없음
}
```

**용도**: 로그 저장처럼 주 트랜잭션 결과와 무관하게 반드시 저장해야 하는 경우.

### NESTED

<div class="mermaid">
sequenceDiagram
    participant C as 클라이언트
    participant TX1 as TX1 (createOrder)
    participant SP as Savepoint
    participant SL as saveLog()

    C->>TX1: TX1 시작
    TX1->>TX1: 작업 수행
    TX1->>SP: Savepoint 생성
    TX1->>SL: saveLog() 호출
    alt 성공
        SL-->>TX1: 완료
        TX1-->>C: TX1 커밋
    else 실패
        SL-->>SP: 예외 발생
        SP-->>TX1: Savepoint로 롤백 (saveLog만 롤백)
        TX1-->>C: TX1 계속 진행 후 커밋
    end
</div>

```java
@Transactional
public void createOrder(OrderDto dto) {
    orderRepository.save(new Order(dto));
    try {
        logService.saveLog("주문 생성");
    } catch (Exception e) {
        // saveLog만 롤백, createOrder는 계속 진행 가능
        log.warn("로그 저장 실패, 무시");
    }
}

@Transactional(propagation = Propagation.NESTED)
public void saveLog(String message) {
    logRepository.save(new Log(message));
}
```

**REQUIRES_NEW vs NESTED**:
- REQUIRES_NEW: 물리적으로 다른 DB 커넥션 사용
- NESTED: 같은 커넥션, Savepoint 활용 (JDBC에서만 지원, JPA와 잘 안 맞음)

### SUPPORTS

```java
@Transactional(propagation = Propagation.SUPPORTS)
public void readData() {
    // 부모 TX 있으면 참여, 없으면 TX 없이 실행
}
```

### NOT_SUPPORTED

```java
@Transactional(propagation = Propagation.NOT_SUPPORTED)
public void readData() {
    // 부모 TX 있으면 일시 중단, TX 없이 실행
}
```

### NEVER

```java
@Transactional(propagation = Propagation.NEVER)
public void readData() {
    // 트랜잭션이 있으면 예외 발생
    // 트랜잭션 없이 실행되어야 함을 강제
}
```

### MANDATORY

```java
@Transactional(propagation = Propagation.MANDATORY)
public void readData() {
    // 반드시 부모 트랜잭션이 있어야 함
    // 없으면 예외 발생
}
```

### 전파 속성 정리표

| 속성 | 부모 TX 있음 | 부모 TX 없음 |
|------|------------|------------|
| REQUIRED | 참여 | 새로 생성 |
| REQUIRES_NEW | 부모 중단, 새로 생성 | 새로 생성 |
| NESTED | 중첩 TX (Savepoint) | 새로 생성 |
| SUPPORTS | 참여 | TX 없이 실행 |
| NOT_SUPPORTED | 부모 중단, TX 없이 실행 | TX 없이 실행 |
| NEVER | 예외 | TX 없이 실행 |
| MANDATORY | 참여 | 예외 |

---

## 3. 격리 수준 (Isolation Level)

격리 수준은 **동시에 여러 트랜잭션이 실행될 때 데이터 정합성을 어떻게 보장할지** 결정한다.

### 발생 가능한 문제

```
[Dirty Read]
TX1이 수정 중(미커밋)인 데이터를 TX2가 읽음
TX1이 롤백하면 TX2는 존재하지 않는 데이터를 읽은 것

TX1: UPDATE price = 2000 (미커밋)
TX2: SELECT price → 2000 (Dirty Read!)
TX1: ROLLBACK
→ TX2가 읽은 2000은 유령 데이터

[Non-Repeatable Read]
같은 TX 내에서 같은 쿼리를 두 번 실행하면 결과가 다름

TX1: SELECT price → 1000
TX2: UPDATE price = 2000, COMMIT
TX1: SELECT price → 2000 (다른 결과!)

[Phantom Read]
같은 TX 내에서 같은 조건으로 조회 시 행의 수가 달라짐

TX1: SELECT COUNT(*) WHERE price > 1000 → 5건
TX2: INSERT price = 5000, COMMIT
TX1: SELECT COUNT(*) WHERE price > 1000 → 6건 (팬텀!)
```

### 격리 수준별 허용 문제

| 격리 수준 | Dirty Read | Non-Repeatable Read | Phantom Read |
|---------|-----------|---------------------|-------------|
| READ_UNCOMMITTED | 허용 | 허용 | 허용 |
| READ_COMMITTED | 방지 | 허용 | 허용 |
| REPEATABLE_READ | 방지 | 방지 | 허용 |
| SERIALIZABLE | 방지 | 방지 | 방지 |

격리 수준이 높을수록 정합성이 높지만 성능이 낮아진다.

### Spring 설정

```java
@Transactional(isolation = Isolation.READ_COMMITTED)  // MySQL InnoDB 기본값
public void someMethod() { ... }

@Transactional(isolation = Isolation.REPEATABLE_READ)  // MySQL InnoDB 실제 기본값
public void someMethod() { ... }

@Transactional(isolation = Isolation.DEFAULT)  // DB 기본 설정 따름 (Spring 기본값)
public void someMethod() { ... }
```

**실무**: 대부분 `DEFAULT`(DB 기본값)를 사용한다. MySQL InnoDB는 기본값이 `REPEATABLE_READ`이며, MVCC로 Phantom Read도 대부분 방지한다.

---

## 4. 롤백 규칙

### 기본 규칙

```
Unchecked Exception (RuntimeException, Error)
    → 자동 롤백

Checked Exception (Exception)
    → 자동 커밋 (롤백 안 됨!)
```

```java
@Transactional
public void createOrder() throws IOException {
    orderRepository.save(order);
    throw new IOException("파일 오류");  // Checked → 커밋됨!
}

@Transactional
public void createOrder() {
    orderRepository.save(order);
    throw new RuntimeException("런타임 오류");  // Unchecked → 롤백
}
```

### 커스텀 롤백 설정

```java
// Checked Exception도 롤백
@Transactional(rollbackFor = Exception.class)
public void createOrder() throws IOException {
    orderRepository.save(order);
    throw new IOException("이제 롤백됨");
}

// 특정 예외는 롤백 안 함
@Transactional(noRollbackFor = BusinessException.class)
public void createOrder() {
    orderRepository.save(order);
    throw new BusinessException("커밋됨");  // noRollbackFor → 커밋
}

// 여러 예외 지정
@Transactional(
    rollbackFor = {IOException.class, SQLException.class},
    noRollbackFor = {UserNotFoundException.class}
)
public void complexMethod() { ... }
```

### 커스텀 예외 설계

```java
// RuntimeException 상속 → 기본적으로 롤백
public class OrderException extends RuntimeException {
    public OrderException(String message) {
        super(message);
    }
}

// 롤백 안 되는 비즈니스 예외
@Transactional(noRollbackFor = DuplicateOrderException.class)
public void createOrder() {
    if (isDuplicate()) {
        throw new DuplicateOrderException("중복 주문");  // 롤백 안 함
    }
}
```

---

## 5. 트랜잭션 프록시 동작 원리

<div class="mermaid">
sequenceDiagram
    participant C as 클라이언트
    participant P as TransactionInterceptor (AOP Proxy)
    participant TM as PlatformTransactionManager
    participant S as 실제 OrderService

    C->>P: orderService.createOrder() 호출
    P->>TM: getTransaction() - 트랜잭션 시작 또는 기존 TX 참여
    P->>S: createOrder() 실행
    S->>S: DB 작업 수행 (같은 커넥션)
    S-->>P: 반환
    alt 정상 반환
        P->>TM: commit()
    else 예외 발생
        P->>P: rollbackFor 규칙 적용
        P->>TM: rollback()
    end
    P-->>C: 응답
</div>

### PlatformTransactionManager

Spring의 트랜잭션 추상화 인터페이스.

```java
public interface PlatformTransactionManager {
    TransactionStatus getTransaction(TransactionDefinition definition);
    void commit(TransactionStatus status);
    void rollback(TransactionStatus status);
}
```

구현체는 기술에 따라 자동 선택된다.

| 기술 | 구현체 |
|------|-------|
| JDBC | `DataSourceTransactionManager` |
| JPA | `JpaTransactionManager` |
| JTA (분산 TX) | `JtaTransactionManager` |

Spring Boot는 JPA 사용 시 자동으로 `JpaTransactionManager`를 등록한다.

### 트랜잭션 동기화

같은 트랜잭션 내에서 같은 DB 커넥션을 사용하기 위해 `TransactionSynchronizationManager`가 **ThreadLocal**로 커넥션을 관리한다.

<div class="mermaid">
graph TD
    subgraph "Thread A"
        TLA["ThreadLocal → Connection1"]
        OSA["OrderService.save()"]
        LSA["LogService.save()"]
        TLA --> OSA
        TLA --> LSA
        OSA -->|"Connection1 사용 같은 TX"| C1[(Connection1)]
        LSA -->|"Connection1 사용 같은 TX"| C1
    end
    subgraph "Thread B"
        TLB["ThreadLocal → Connection2"]
        OSB["OrderService.save()"]
        TLB --> OSB
        OSB -->|"Connection2 사용 독립"| C2[(Connection2)]
    end
</div>

---

## 6. 주의사항

### private 메서드

```java
@Service
public class OrderService {

    @Transactional  // 동작 안 함!
    private void createOrder() {
        // AOP 프록시는 private 메서드 오버라이드 불가
    }
}
```

**해결**: `public` 또는 `protected`으로 변경.

### Self-invocation (내부 호출)

```java
@Service
public class OrderService {

    public void process() {
        createOrder();  // this.createOrder() → 프록시 우회!
        // @Transactional 동작 안 함
    }

    @Transactional
    public void createOrder() { ... }
}
```

**해결**: 별도 Bean으로 분리.

```java
@Service
public class OrderService {
    @Autowired
    private OrderInternalService orderInternalService;

    public void process() {
        orderInternalService.createOrder();  // 프록시를 통해 호출 → TX 적용
    }
}

@Service
public class OrderInternalService {
    @Transactional
    public void createOrder() { ... }
}
```

### 예외 처리 주의

```java
@Transactional
public void createOrder() {
    try {
        orderRepository.save(order);
        throw new RuntimeException("오류");
    } catch (Exception e) {
        log.error("오류 발생", e);
        // 예외를 잡아서 처리 → 트랜잭션은 커밋됨!
        // 의도치 않은 커밋 주의
    }
}
```

예외를 내부에서 흡수하면 `@Transactional`이 예외를 감지하지 못해 커밋된다. 롤백이 필요하다면 예외를 다시 던지거나 `TransactionAspectSupport.currentTransactionStatus().setRollbackOnly()`를 호출한다.

```java
@Transactional
public void createOrder() {
    try {
        orderRepository.save(order);
        throw new RuntimeException("오류");
    } catch (Exception e) {
        log.error("오류 발생", e);
        TransactionAspectSupport.currentTransactionStatus().setRollbackOnly(); // 명시적 롤백 마킹
    }
}
```

### @Transactional과 테스트

```java
@SpringBootTest
class OrderServiceTest {

    @Test
    @Transactional  // 테스트 후 자동 롤백
    void createOrderTest() {
        orderService.createOrder(dto);
        // 테스트 종료 시 롤백 → DB 영향 없음
    }
}
```

테스트에 `@Transactional`을 붙이면 테스트 후 자동으로 롤백되어 DB를 깨끗하게 유지할 수 있다. 단, `REQUIRES_NEW`로 별도 TX에서 커밋된 데이터는 롤백되지 않는다.

---

## 정리

| 개념 | 핵심 |
|------|------|
| 선언적 트랜잭션 | `@Transactional` = AOP 기반 트랜잭션 관리 |
| readOnly | DirtyChecking 비활성화, 성능 향상 |
| REQUIRED | 기본값. 있으면 참여, 없으면 생성 |
| REQUIRES_NEW | 항상 새 TX. 독립적 커밋/롤백 |
| NESTED | Savepoint 기반 중첩 TX |
| Unchecked 예외 | 자동 롤백 |
| Checked 예외 | 기본 커밋 (rollbackFor 설정 필요) |
| Self-invocation | 프록시 우회 → TX 미적용 |
| private 메서드 | AOP 미적용 → TX 동작 안 함 |
