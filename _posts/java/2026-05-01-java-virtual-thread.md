---
title: "Java Virtual Thread(가상 스레드)"
categories:
- JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

> **비유로 먼저 이해하기**: 가상 스레드는 비행기 좌석과 같다. 비행기 엔진(OS 스레드)은 몇 개 없지만 좌석(가상 스레드)은 수백 개다. 승객(요청)이 좌석에 앉아 있는 동안 엔진이 교대로 각 좌석을 처리한다. OS 스레드 하나가 수천 개의 가상 스레드를 번갈아 실행하는 것도 같은 원리다.

Java 21에서 정식 도입된 Virtual Thread(가상 스레드)의 동작 원리, 아키텍처, 실전 사용법, 주의사항까지 완전히 정리합니다.

---

## 1. 왜 Virtual Thread가 필요한가?

### C10K 문제

C10K 문제는 1999년 Dan Kegel이 제기한 개념으로, 서버 한 대에서 동시에 10,000개의 클라이언트 연결을 처리하는 것이 당시 기술로 매우 어렵다는 문제였습니다. 현대에는 C10K를 넘어 C100K, C1M(100만 동시 연결)이 요구되는 환경까지 등장했습니다.

### 기존 Platform Thread의 한계

Java에서 전통적으로 사용하는 `Thread`(Platform Thread)는 OS 스레드와 1:1로 매핑됩니다.

```
Java Thread ──── OS Thread ──── CPU Core
    1               1
```

OS 스레드는 생성 비용과 유지 비용이 매우 큽니다.

| 항목 | 비용 |
|------|------|
| 스레드 스택 기본 크기 | 512KB ~ 1MB |
| 스레드 생성 시간 | 수십 ~ 수백 μs |
| 컨텍스트 스위칭 오버헤드 | 수 μs ~ 수십 μs |
| JVM 내 최대 실용 스레드 수 | 수천 ~ 수만 개 |

10,000개의 Thread를 생성하면 최소 10GB 이상의 메모리가 필요합니다. 대부분의 웹 서버는 요청 하나당 스레드 하나를 할당하는 **Thread-per-Request** 모델을 사용하는데, 이 모델은 I/O 대기 중에도 스레드를 점유합니다.

<div class="mermaid">
gantt
  title 요청 처리 타임라인 (Platform Thread - I/O 대기 중 블로킹)
  dateFormat X
  axisFormat %s

  section Thread-1
  처리        : 0, 3
  DB 대기(100ms) : crit, 3, 7
  마무리      : 7, 9

  section Thread-2
  처리        : 0, 2
  HTTP 대기(200ms) : crit, 2, 8
  마무리      : 8, 10

  section Thread-3
  처리        : 0, 2
  파일 I/O(50ms) : crit, 2, 5
  마무리      : 5, 7
</div>

### 비동기 프로그래밍의 복잡성

I/O 대기 문제를 해결하기 위해 Reactive(비동기) 프로그래밍이 등장했지만, 콜백 지옥, 디버깅 어려움, 코드 가독성 저하라는 새로운 문제를 낳았습니다.

```java
// Reactive 스타일 — 읽기 어렵고 디버깅 어려움
Mono.fromCallable(() -> findUser(id))
    .flatMap(user -> fetchOrders(user.getId()))
    .flatMap(orders -> calculateTotal(orders))
    .doOnError(e -> log.error("error", e))
    .subscribe(result -> sendResponse(result));
```

Virtual Thread는 **동기식 코드의 가독성**을 유지하면서 **비동기 수준의 확장성**을 제공하는 것이 핵심 목표입니다.

---

## 2. Platform Thread vs Virtual Thread 비교

### 메모리 사용량

<div class="mermaid">
graph TD
  subgraph PT["Platform Thread (OS Thread) — 1,000개 ≈ 500MB~1GB"]
    F1[Frame 1] --- F2[Frame 2] --- F3[Frame 3]
    NOTE1["Stack: 기본 512KB ~ 1MB (고정/동적 확장)"]
  end
  subgraph VT["Virtual Thread — 1,000,000개 ≈ 수백 MB"]
    CONT["Heap의 Continuation 객체 (수 KB, 필요 시 확장)"]
    NOTE2["mounted 상태에서만 carrier thread stack 사용"]
  end
</div>

| 항목 | Platform Thread | Virtual Thread |
|------|----------------|----------------|
| 스택 초기 크기 | 512KB ~ 1MB | 수 KB (동적) |
| 스레드 생성 비용 | 높음 (OS 호출) | 낮음 (JVM 내부) |
| 최대 동시 수 | 수천 ~ 수만 | 수백만 |
| 스레드 풀 필요 | 권장 | 불필요 |

### 컨텍스트 스위칭 비용

Platform Thread의 컨텍스트 스위칭은 OS 커널이 관여하므로 비용이 큽니다.

```
Platform Thread 컨텍스트 스위칭:
  User Space → Kernel Space 전환
  레지스터 저장/복원 (범용 레지스터, 부동소수점 레지스터)
  TLB(Translation Lookaside Buffer) 플러시 가능성
  비용: 수 μs ~ 수십 μs
```

Virtual Thread의 스케줄링은 JVM이 User Space에서 직접 처리합니다.

```
Virtual Thread 스위칭:
  Continuation 객체를 Heap에 저장/복원
  Carrier Thread에 다른 Virtual Thread mount
  비용: 수백 ns ~ 수 μs (OS 개입 없음)
```

### OS 스레드 매핑 차이

<div class="mermaid">
graph LR
  subgraph M1["Platform Thread 모델 (1:1)"]
    JT1[Java Thread 1] --> OST1[OS Thread 1]
    JT2[Java Thread 2] --> OST2[OS Thread 2]
    JT3[Java Thread 3] --> OST3[OS Thread 3]
  end
  subgraph M2["Virtual Thread 모델 (M:N)"]
    VT1[VThread 1] --> CT1[Carrier Thread 1]
    VT2[VThread 2] --> CT1
    VT3[VThread 3] --> CT1
    VT4[VThread 4] --> CT1
    VT5[VThread 5] --> CT1
    VT6[VThread 6] --> CT2[Carrier Thread 2]
    VT7[VThread 7] --> CT2
    CT1 --> OS1[OS Thread 1]
    CT2 --> OS2[OS Thread 2]
  end
</div>

---

## 3. Virtual Thread 아키텍처

### Carrier Thread (캐리어 스레드)

Carrier Thread는 Virtual Thread를 실제로 실행하는 Platform Thread입니다. JVM 내부의 `ForkJoinPool`이 Carrier Thread 풀을 관리하며, 기본 크기는 `Runtime.getRuntime().availableProcessors()`와 동일합니다.

```java
// Carrier Thread 수 확인 및 조정
// JVM 옵션: -Djdk.virtualThreadScheduler.parallelism=8
// JVM 옵션: -Djdk.virtualThreadScheduler.maxPoolSize=256
```

### ForkJoinPool 기반 스케줄러

Virtual Thread 스케줄러는 Work-Stealing 알고리즘을 사용하는 `ForkJoinPool`을 기반으로 합니다.

<div class="mermaid">
graph LR
  subgraph FJP["ForkJoinPool - Virtual Thread Scheduler"]
    subgraph C1["Carrier Thread 1"]
      VTa[VT-a]
      VTb[VT-b]
    end
    subgraph C2["Carrier Thread 2"]
      VTc[VT-c]
    end
    subgraph CN["Carrier Thread N"]
      EMPTY["(빈 큐)"]
    end
    CN -->|Work-Stealing| VTb
  end
</div>

### Mount / Unmount 동작

Virtual Thread가 블로킹 I/O를 만나면 Carrier Thread에서 **Unmount**되고, I/O가 완료되면 다시 **Mount**됩니다.

<div class="mermaid">
sequenceDiagram
  participant VA as VThread-A
  participant C1 as Carrier-1
  participant VB as VThread-B

  C1->>VA: Mount & 실행
  VA->>C1: 블로킹 I/O 호출 → Unmount (상태 Heap 저장)
  C1->>VB: VThread-B Mount & 실행
  Note over VA: I/O 완료 → 스케줄링 재등록
  C1->>VB: Unmount
  C1->>VA: Mount & 재개
</div>

상세 동작 순서:

```
1. VThread-A가 Carrier-1에 Mount되어 실행
   Carrier-1 Stack → VThread-A의 Continuation 실행

2. VThread-A가 InputStream.read() 같은 블로킹 I/O 호출
   JVM이 I/O를 비동기로 변환 (NIO + Poller 스레드 활용)

3. VThread-A Unmount
   Continuation 상태(스택 프레임, 로컬 변수)를 Heap에 저장
   Carrier-1이 자유로워짐

4. Carrier-1이 큐에서 다음 VThread-B를 꺼내 Mount

5. I/O 완료 신호 수신
   VThread-A를 ForkJoinPool 큐에 다시 등록

6. 여유 Carrier Thread가 VThread-A를 Mount하여 재개
   Heap에서 Continuation 복원 → 중단된 지점부터 계속 실행
```

### Continuation 개념

Continuation은 "실행 상태의 스냅샷"입니다. 특정 시점의 스택 프레임, 지역 변수, 프로그램 카운터를 Heap 객체로 저장하고 나중에 복원할 수 있습니다.

```java
// 개념적 이해를 위한 Continuation 동작 (실제 내부 구현 축약)
// JVM 내부의 jdk.internal.vm.Continuation 클래스가 처리

// Virtual Thread에서 블로킹 메서드 호출 시
void blockingOperation() {
    // 1단계: 이 시점까지의 스택 프레임을 Heap에 저장
    // 2단계: Carrier Thread 반환
    // -- 시간이 흐름 --
    // 3단계: 이벤트 완료 후 Heap에서 스택 복원
    // 4단계: 여기서부터 재개
    result = socket.read(buffer); // 블로킹 지점
    process(result);              // 재개 후 계속 실행
}
```

---

## 4. 사용법

### Thread.ofVirtual().start()

```java
// 단순 Virtual Thread 생성 및 시작
Thread vt = Thread.ofVirtual().start(() -> {
    System.out.println("Virtual Thread 실행: " + Thread.currentThread());
    // Thread[#21,<unnamed>,5,<unnamed>] — isVirtual() == true
});
vt.join();

// 이름 지정
Thread named = Thread.ofVirtual()
    .name("my-virtual-thread")
    .start(() -> doWork());

// 생성만 하고 나중에 시작
Thread.Builder builder = Thread.ofVirtual().name("worker-", 0);
Thread t1 = builder.unstarted(() -> task1());
Thread t2 = builder.unstarted(() -> task2());
t1.start();
t2.start();
```

### Executors.newVirtualThreadPerTaskExecutor()

실무에서 가장 많이 사용하는 방식입니다. 작업마다 새로운 Virtual Thread를 생성합니다.

```java
// ExecutorService로 Virtual Thread 사용
try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
    // 1,000개 작업을 동시에 처리
    List<Future<String>> futures = new ArrayList<>();
    for (int i = 0; i < 1000; i++) {
        final int taskId = i;
        futures.add(executor.submit(() -> {
            // I/O 작업 (예: DB 조회, HTTP 호출)
            Thread.sleep(100); // 블로킹 — VThread는 Carrier 반환
            return "result-" + taskId;
        }));
    }
    for (Future<String> f : futures) {
        System.out.println(f.get());
    }
} // AutoCloseable — executor.close() 자동 호출, 모든 작업 완료 대기
```

### Thread.startVirtualThread()

간편한 정적 팩토리 메서드입니다.

```java
// 가장 간단한 방법
Thread vt = Thread.startVirtualThread(() -> {
    System.out.println("간단한 Virtual Thread");
});
```

### try-with-resources 패턴

`ExecutorService`는 Java 19부터 `AutoCloseable`을 구현합니다. `close()` 시 모든 작업이 완료될 때까지 대기하므로 안전하게 사용할 수 있습니다.

```java
// 구조적 동시성 패턴
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    var userFuture  = executor.submit(() -> fetchUser(userId));
    var orderFuture = executor.submit(() -> fetchOrders(userId));
    var stockFuture = executor.submit(() -> fetchStock(itemId));

    User  user   = userFuture.get();
    List<Order> orders = orderFuture.get();
    Stock stock  = stockFuture.get();

    return buildResponse(user, orders, stock);
}
// try 블록 종료 시 executor.close() → 모든 Future 완료 보장
```

### StructuredTaskScope (Java 21 Preview)

더 안전한 구조적 동시성을 위한 고수준 API입니다.

```java
import jdk.incubator.concurrent.StructuredTaskScope;

try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    var userTask  = scope.fork(() -> fetchUser(userId));
    var orderTask = scope.fork(() -> fetchOrders(userId));

    scope.join();           // 모든 작업 완료 대기
    scope.throwIfFailed();  // 실패한 작업이 있으면 예외 던짐

    return new Response(userTask.get(), orderTask.get());
}
```

---

## 5. Spring Boot 3.2+에서 Virtual Thread 적용

### 설정 한 줄로 활성화

```yaml
# application.yml
spring:
  threads:
    virtual:
      enabled: true
```

이 설정 하나로 다음이 자동 적용됩니다.

| 컴포넌트 | 적용 내용 |
|---------|----------|
| Tomcat | acceptor, worker 스레드를 Virtual Thread로 교체 |
| Undertow | XNIO worker를 Virtual Thread로 교체 |
| `@Async` | `AsyncTaskExecutor`를 Virtual Thread executor로 교체 |
| `@Scheduled` | Virtual Thread로 실행 |

### 수동 설정 (세밀한 제어)

```java
@Configuration
@EnableAsync
public class VirtualThreadConfig {

    // Tomcat에 Virtual Thread 적용
    @Bean
    public TomcatProtocolHandlerCustomizer<?> tomcatVirtualThread() {
        return handler -> handler.setExecutor(
            Executors.newVirtualThreadPerTaskExecutor()
        );
    }

    // @Async 작업에 Virtual Thread 적용
    @Bean
    public AsyncTaskExecutor applicationTaskExecutor() {
        return new TaskExecutorAdapter(
            Executors.newVirtualThreadPerTaskExecutor()
        );
    }

    // @Scheduled에 Virtual Thread 적용
    @Bean
    public TaskScheduler taskScheduler() {
        ThreadPoolTaskScheduler scheduler = new ThreadPoolTaskScheduler();
        scheduler.setVirtualThreadsEnabled(true);
        return scheduler;
    }
}
```

### Spring WebMVC에서의 처리량 비교

```
요청 처리 모델 비교 (DB 조회 100ms 포함 시)

[Platform Thread Pool (200개)]
RPS ≈ 200 / 0.1s = 2,000 req/s (최대)

[Virtual Thread]
RPS ≈ Carrier Thread 수 × (1 / 실제 CPU 사용 시간)
  = 8 × (1 / 0.005s) = 1,600 → 실제로는 DB 커넥션 풀이 병목
```

실제 병목은 스레드 수가 아니라 **DB 커넥션 풀**이 됩니다. Virtual Thread 도입 시 커넥션 풀 크기도 함께 검토해야 합니다.

---

## 6. Pinning (피닝) 문제

### 피닝이란?

Virtual Thread가 블로킹 상태에서도 Carrier Thread에서 Unmount되지 못하고 **고정(Pinned)**되는 현상입니다. 피닝이 발생하면 Virtual Thread의 장점이 사라지고 Carrier Thread를 점유하게 됩니다.

<div class="mermaid">
graph TD
  subgraph OK["정상 동작 (I/O 블로킹)"]
    V1[VThread] --> BIO[블로킹 I/O]
    BIO --> UM[Unmount]
    UM --> RET[Carrier Thread 반환]
    RET --> OV[다른 VThread 실행]
  end
  subgraph PIN["피닝 발생 (synchronized 내 블로킹)"]
    V2[VThread] --> SYN[synchronized 블록 진입]
    SYN --> BIO2[블로킹 I/O]
    BIO2 --> PINNED["Pinned! Carrier Thread 점유 유지\n→ 다른 VThread 실행 불가"]
  end
</div>

### synchronized 블록에서 피닝

```java
// 피닝 발생 — synchronized 블록 내 블로킹 호출
public class PinningExample {
    private final Object lock = new Object();

    public void badMethod() {
        synchronized (lock) {
            // 이 시점에서 Carrier Thread가 Pinned!
            String result = callExternalApi(); // 블로킹 HTTP 호출
            process(result);
        }
    }
}
```

### native 메서드 호출 시 피닝

```java
// JNI를 통한 native 메서드 호출 시에도 피닝 발생
public class NativePinning {
    static {
        System.loadLibrary("mylib");
    }

    public native String callNativeMethod(); // 피닝 발생
}
```

### ReentrantLock으로 대체

`synchronized` 대신 `ReentrantLock`을 사용하면 피닝을 방지할 수 있습니다. `ReentrantLock`은 JDK 내부적으로 Virtual Thread 친화적으로 구현되어 있습니다.

```java
// 피닝 방지 — ReentrantLock 사용
public class SafeVirtualThread {
    private final ReentrantLock lock = new ReentrantLock();

    public void goodMethod() {
        lock.lock();
        try {
            // Carrier Thread에서 Unmount 가능
            String result = callExternalApi(); // 블로킹 허용
            process(result);
        } finally {
            lock.unlock();
        }
    }
}
```

### 피닝 진단

```bash
# 피닝 발생 시 스택 트레이스 출력
java -Djdk.tracePinnedThreads=full MainClass

# 피닝 발생 시 짧은 스택만 출력
java -Djdk.tracePinnedThreads=short MainClass
```

피닝 발생 시 출력 예시:

```
Thread[#23,ForkJoinPool-1-worker-1,5,CarrierThreads]
    java/lang/Object.wait(Object.java) <== monitors:1
    com/example/PinningExample.badMethod(PinningExample.java:12)
    ...
```

### Java 24의 synchronized 개선

Java 24부터는 `synchronized` 블록도 피닝 없이 Virtual Thread를 Unmount할 수 있도록 개선이 진행 중입니다 (JEP 491: Synchronized Virtual Threads). 마이그레이션이 더 쉬워질 예정입니다.

---

## 7. ThreadLocal 이슈

### Virtual Thread에서 ThreadLocal 비용

`ThreadLocal`은 스레드별로 독립된 값을 저장하는 메커니즘입니다. 수백만 개의 Virtual Thread 각각에 `ThreadLocal` 값이 저장되면 메모리 문제가 발생할 수 있습니다.

```java
// 문제 코드 — 큰 객체를 ThreadLocal에 저장
private static final ThreadLocal<LargeBuffer> BUFFER =
    ThreadLocal.withInitial(() -> new LargeBuffer(1024 * 1024)); // 1MB

public void handleRequest() {
    // Virtual Thread 100만 개 × 1MB = 1TB 메모리!
    LargeBuffer buf = BUFFER.get();
    buf.process(data);
    // clear() 하지 않으면 GC 대상에서 오래 남음
}
```

해결 방법:

```java
// 1. 작업 완료 후 반드시 remove()
private static final ThreadLocal<Context> CONTEXT = new ThreadLocal<>();

public void handleRequest() {
    CONTEXT.set(new Context(requestId));
    try {
        doWork();
    } finally {
        CONTEXT.remove(); // 반드시 정리
    }
}

// 2. 경량 객체만 ThreadLocal에 저장
// 3. ScopedValue 사용 (아래 참고)
```

### ScopedValue (Java 21 Preview → Java 23 Final)

`ScopedValue`는 `ThreadLocal`의 대안으로 설계된 불변(immutable) 값 전달 메커니즘입니다. Virtual Thread와 구조적 동시성에 최적화되어 있습니다.

```java
// ScopedValue — Virtual Thread 친화적
public class RequestHandler {
    private static final ScopedValue<RequestContext> CONTEXT =
        ScopedValue.newInstance();

    public void handleRequest(RequestContext ctx) {
        ScopedValue.where(CONTEXT, ctx).run(() -> {
            processStep1();
            processStep2();
        });
        // run() 블록 종료 후 자동으로 값 해제
    }

    private void processStep1() {
        RequestContext ctx = CONTEXT.get(); // 어디서나 접근 가능
        log.info("Processing: {}", ctx.getId());
    }
}
```

`ThreadLocal` vs `ScopedValue` 비교:

| 항목 | ThreadLocal | ScopedValue |
|------|------------|-------------|
| 가변성 | 가변 (set/get/remove) | 불변 (바인딩 후 변경 불가) |
| 생명주기 | 명시적 remove 필요 | 스코프 종료 시 자동 해제 |
| Virtual Thread 친화성 | 낮음 (메모리 누수 위험) | 높음 |
| 상속 | InheritableThreadLocal로 가능 | 구조적 동시성과 자연스럽게 통합 |

---

## 8. Virtual Thread가 적합하지 않은 경우

### CPU 바운드 작업

Virtual Thread는 I/O 대기 시간이 많은 **I/O 바운드** 작업에 최적화되어 있습니다. CPU를 지속적으로 사용하는 작업은 오히려 성능이 저하될 수 있습니다.

```java
// CPU 바운드 — Virtual Thread 부적합
public long computeFibonacci(int n) {
    // CPU를 계속 점유, Unmount 기회 없음
    // Carrier Thread 수(= CPU 코어 수)를 넘는 VThread를 생성해도
    // 병렬 처리 불가 → 오히려 스케줄링 오버헤드 발생
    if (n <= 1) return n;
    return computeFibonacci(n - 1) + computeFibonacci(n - 2);
}

// CPU 바운드는 Platform Thread + ForkJoinPool이 적합
ForkJoinPool pool = new ForkJoinPool(Runtime.getRuntime().availableProcessors());
pool.submit(() -> computeFibonacci(50));
```

### 이미 비동기(Reactor, Coroutine)를 사용 중인 경우

Project Reactor(WebFlux), Kotlin Coroutines 등 이미 비동기 프레임워크를 사용 중이라면 Virtual Thread로 전환할 실익이 없습니다.

```java
// 이미 비동기 — Virtual Thread 혼용 불필요
@GetMapping("/users")
public Flux<User> getUsers() {
    return userRepository.findAll() // Reactive 반환
        .filter(user -> user.isActive());
}
```

특히 `Flux`/`Mono` 파이프라인에 블로킹 코드를 작성하는 실수를 방지하기 위해 둘을 혼용하지 않는 것이 좋습니다.

---

## 9. Virtual Thread vs Kotlin Coroutines vs Project Reactor 비교

| 항목 | Virtual Thread | Kotlin Coroutines | Project Reactor |
|------|---------------|-------------------|-----------------|
| 언어 | Java | Kotlin | Java |
| 프로그래밍 모델 | 동기식 (블로킹 가능) | suspend 함수 | 선언형 파이프라인 |
| 학습 곡선 | 낮음 | 중간 | 높음 |
| 기존 코드 호환성 | 높음 (블로킹 코드 재사용) | 중간 | 낮음 (전면 재작성) |
| 디버깅 용이성 | 높음 (일반 스택 트레이스) | 중간 | 낮음 (연산자 체인) |
| CPU 바운드 성능 | 낮음 | 낮음 | 낮음 |
| I/O 바운드 처리량 | 매우 높음 | 매우 높음 | 매우 높음 |
| 메모리 효율 | 높음 | 높음 | 높음 |
| 피닝/차단 위험 | 있음 | 없음 (structured) | 없음 |
| JVM 통합 수준 | JVM 내장 | 라이브러리 | 라이브러리 |
| Spring 지원 | Spring Boot 3.2+ | Spring WebFlux | Spring WebFlux |

### 선택 가이드

```
새 프로젝트이고 Java를 사용 중이며 I/O 바운드 작업이 많다
  → Virtual Thread 채택

기존 동기식 Java 코드를 최소 변경으로 확장하고 싶다
  → Virtual Thread 채택

Kotlin을 사용 중이다
  → Kotlin Coroutines (이미 최적화됨)

반응형 스트림 처리, 배압(backpressure) 제어가 필요하다
  → Project Reactor

마이크로서비스 간 다수 I/O 호출 조합
  → Virtual Thread 또는 Kotlin Coroutines
```

---

## 10. 극한 시나리오

### 100만 동시 요청 처리

```java
// 100만 Virtual Thread 생성 테스트
public class MillionThreadTest {
    public static void main(String[] args) throws InterruptedException {
        int count = 1_000_000;
        CountDownLatch latch = new CountDownLatch(count);

        long start = System.currentTimeMillis();

        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < count; i++) {
                executor.submit(() -> {
                    try {
                        Thread.sleep(1000); // I/O 시뮬레이션
                    } finally {
                        latch.countDown();
                    }
                });
            }
        }

        latch.await();
        long elapsed = System.currentTimeMillis() - start;
        System.out.println("100만 VThread 완료: " + elapsed + "ms");
        // Platform Thread로는 불가능한 수치 — ~1,000ms 내외
    }
}
```

### DB 커넥션 풀 병목

Virtual Thread 수가 DB 커넥션 풀 크기를 크게 초과하면 풀 대기 시간이 병목이 됩니다.

```
시나리오: VThread 10,000개, DB 커넥션 풀 100개

VThread-1     ──→ [DB 커넥션 획득] → 처리 → 반환
VThread-2     ──→ [DB 커넥션 획득] → 처리 → 반환
...
VThread-100   ──→ [DB 커넥션 획득] → 처리 → 반환
VThread-101   ──→ [풀 대기... VThread는 Unmount → OK]
...
VThread-10000 ──→ [풀 대기... 큐잉]

결과: DB가 처리할 수 있는 속도 이상으로 요청이 쌓임
      → DB 과부하, 연결 타임아웃 위험
```

해결책:

```java
// Semaphore로 DB 작업 동시성 제한
public class DatabaseService {
    // DB 커넥션 풀 크기에 맞게 설정
    private final Semaphore semaphore = new Semaphore(100);

    public User findUser(long id) throws InterruptedException {
        semaphore.acquire(); // VThread는 여기서 Unmount (블로킹이지만 피닝 아님)
        try {
            return jdbcTemplate.queryForObject(
                "SELECT * FROM users WHERE id = ?", userRowMapper, id
            );
        } finally {
            semaphore.release();
        }
    }
}
```

HikariCP 설정 조정:

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 50   # Virtual Thread 수에 비해 작아도 됨
      connection-timeout: 3000 # 대기 타임아웃 설정 중요
      keepalive-time: 30000
```

### 피닝으로 인한 처리량 저하

```java
// 피닝이 처리량에 미치는 영향 측정
public class PinningBenchmark {

    // 피닝 발생 코드
    private synchronized String pinnedOperation() {
        try {
            Thread.sleep(10); // 피닝된 상태에서 10ms 블로킹
            return "result";
        } catch (InterruptedException e) {
            throw new RuntimeException(e);
        }
    }

    // 피닝 없는 코드
    private final ReentrantLock lock = new ReentrantLock();
    private String safeOperation() {
        lock.lock();
        try {
            Thread.sleep(10); // Carrier Thread 반환 가능
            return "result";
        } catch (InterruptedException e) {
            throw new RuntimeException(e);
        } finally {
            lock.unlock();
        }
    }
}

/*
벤치마크 결과 (Carrier Thread 8개, VThread 1,000개 기준):
  pinnedOperation():  ~1,250ms (직렬화됨 — 8개 carrier 포화)
  safeOperation():    ~125ms   (10배 차이 — carrier 효율적 재사용)
*/
```

---

## 11. 마이그레이션 가이드

### 단계별 마이그레이션

**Step 1: Java 21 업그레이드 및 의존성 확인**

```xml
<!-- pom.xml -->
<properties>
    <java.version>21</java.version>
</properties>

<!-- Spring Boot 3.2 이상 -->
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.2.0</version>
</parent>
```

**Step 2: 피닝 진단**

```bash
# 기존 코드에서 피닝 발생 지점 찾기
java -Djdk.tracePinnedThreads=full -jar app.jar

# synchronized 키워드 사용 현황 grep
grep -rn "synchronized" src/main/java/
```

**Step 3: synchronized → ReentrantLock 교체**

```java
// Before
public class OldService {
    public synchronized void process() {
        doBlockingWork();
    }
}

// After
public class NewService {
    private final ReentrantLock lock = new ReentrantLock();

    public void process() {
        lock.lock();
        try {
            doBlockingWork();
        } finally {
            lock.unlock();
        }
    }
}
```

**Step 4: ThreadLocal 점검**

```java
// Before — 누수 위험
private static final ThreadLocal<BigObject> LOCAL =
    ThreadLocal.withInitial(BigObject::new);

// After — 반드시 remove() 추가
private static final ThreadLocal<SmallContext> LOCAL = new ThreadLocal<>();

public void handle(Request req) {
    LOCAL.set(new SmallContext(req.getId()));
    try {
        doWork();
    } finally {
        LOCAL.remove(); // 필수
    }
}
```

**Step 5: Virtual Thread 활성화**

```yaml
# application.yml
spring:
  threads:
    virtual:
      enabled: true
```

**Step 6: 커넥션 풀 조정 및 부하 테스트**

```bash
# 부하 테스트 — Virtual Thread 적용 전후 비교
wrk -t4 -c1000 -d30s http://localhost:8080/api/users
```

### 마이그레이션 체크리스트

```
□ Java 21+ 업그레이드
□ Spring Boot 3.2+ 업그레이드
□ synchronized 블록 내 블로킹 코드 제거 또는 ReentrantLock 교체
□ JNI/native 메서드 사용 구간 파악 (피닝 불가피한 경우 격리)
□ ThreadLocal 사용 전수 확인 → remove() 추가
□ DB 커넥션 풀 크기 재조정
□ 외부 라이브러리의 synchronized 사용 여부 확인
□ 부하 테스트로 처리량 및 메모리 사용량 검증
□ -Djdk.tracePinnedThreads=full 로 피닝 없음 확인
```

---

## 12. 성능 벤치마크

### 처리량 비교 (I/O 바운드 작업 기준)

다음은 일반적인 벤치마크 수치입니다. 환경에 따라 다를 수 있습니다.

```
테스트 환경: 8코어 CPU, 16GB RAM, DB 응답 50ms
시나리오: HTTP API → DB 조회 → 응답 반환

[Platform Thread Pool (200 threads)]
  동시 사용자 200명:  RPS 3,800,  P99 응답 60ms
  동시 사용자 500명:  RPS 3,200,  P99 응답 180ms
  동시 사용자 1000명: RPS 2,100,  P99 응답 520ms  (스레드 포화)
  동시 사용자 2000명: RPS 1,400,  P99 응답 1,800ms (심각한 저하)

[Virtual Thread]
  동시 사용자 200명:  RPS 3,900,  P99 응답 55ms
  동시 사용자 500명:  RPS 9,200,  P99 응답 58ms
  동시 사용자 1000명: RPS 9,800,  P99 응답 62ms   (DB 풀이 병목)
  동시 사용자 2000명: RPS 9,500,  P99 응답 95ms
  동시 사용자 5000명: RPS 9,400,  P99 응답 180ms
```

### 메모리 사용량 비교

```
스레드 10,000개 생성 시 메모리 사용량:

Platform Thread:
  스택 메모리: 10,000 × 512KB = 5GB (최소)
  → 실제 생성 불가능 (OOM 또는 OS 제한)

Virtual Thread:
  초기 Continuation: 10,000 × ~2KB = ~20MB
  활성 상태(mounted): Carrier 수 × 스택 크기 = 8 × 512KB = 4MB
  → 총 ~24MB 수준
```

### 생성 속도 비교

```java
// 스레드 생성 속도 측정
long start = System.nanoTime();
for (int i = 0; i < 100_000; i++) {
    Thread.ofVirtual().start(() -> {}).join();
}
long elapsed = System.nanoTime() - start;

// Platform Thread: ~30초 (스레드 생성 + OS 호출 오버헤드)
// Virtual Thread:  ~2초  (JVM 내부 처리, 15배 빠름)
```

---

## 실무에서 자주 하는 실수

### 실수 1: synchronized 블록 안에서 블로킹 I/O 호출

Virtual Thread의 가장 흔한 함정입니다. `synchronized` 키워드는 Virtual Thread를 캐리어 스레드에 고정(pinning)시키므로, 블로킹 I/O와 함께 사용하면 플랫폼 스레드와 다를 바 없어집니다.

```java
// 나쁜 예: synchronized + 블로킹 I/O → 피닝 발생
public synchronized String fetchData() {
    return httpClient.get("https://api.example.com/data"); // 피닝!
}

// 좋은 예: ReentrantLock으로 교체
private final ReentrantLock lock = new ReentrantLock();

public String fetchData() {
    lock.lock();
    try {
        return httpClient.get("https://api.example.com/data"); // 피닝 없음
    } finally {
        lock.unlock();
    }
}
```

피닝 발생 여부는 `-Djdk.tracePinnedThreads=full` JVM 옵션으로 진단할 수 있습니다.

### 실수 2: CPU 바운드 작업에 Virtual Thread 적용

Virtual Thread는 I/O 대기 시간을 다른 Virtual Thread에게 양보하는 구조입니다. CPU를 쉬지 않고 사용하는 연산(암호화, 이미지 처리, 머신러닝 추론)에는 양보 기회가 없으므로 효과가 없습니다.

```java
// CPU 바운드 작업 → ForkJoinPool 또는 고정 크기 스레드풀 사용
ExecutorService cpuPool = Executors.newFixedThreadPool(
    Runtime.getRuntime().availableProcessors()
);

// I/O 바운드 작업 → Virtual Thread 사용
ExecutorService ioPool = Executors.newVirtualThreadPerTaskExecutor();
```

### 실수 3: DB 커넥션 풀 크기를 늘리지 않음

Virtual Thread를 도입하면 동시 요청 수가 수십 배 늘어납니다. 커넥션 풀 크기를 그대로 두면 풀 고갈로 오히려 성능이 저하됩니다.

```yaml
# application.yml - Virtual Thread 적용 시 커넥션 풀 재조정
spring:
  datasource:
    hikari:
      maximum-pool-size: 50   # 기존 10 → 50으로 증가
      connection-timeout: 3000
```

### 실수 4: ThreadLocal을 Virtual Thread마다 무거운 객체로 채움

Virtual Thread는 수백만 개가 동시에 존재할 수 있습니다. 각 Virtual Thread의 ThreadLocal에 큰 객체를 저장하면 메모리가 폭발합니다. Java 21+에서는 `ScopedValue`로 교체를 검토하세요.

```java
// 위험: Virtual Thread가 수백만 개라면 수백만 개의 UserContext 객체 생성
static ThreadLocal<UserContext> context = new ThreadLocal<>();

// 개선: ScopedValue 사용 (Java 21+)
static final ScopedValue<UserContext> CONTEXT = ScopedValue.newInstance();

ScopedValue.where(CONTEXT, userCtx).run(() -> {
    processRequest(); // 자동으로 스코프 종료 시 해제
});
```

### 실수 5: Thread.sleep()을 루프 안에서 호출하면 안 된다는 잘못된 믿음

기존 플랫폼 스레드에서 `Thread.sleep()`은 OS 스레드를 점유하는 낭비였습니다. Virtual Thread에서는 `sleep()` 호출 시 캐리어 스레드를 반납하고 대기하므로 자유롭게 사용해도 됩니다.

```java
// Virtual Thread에서는 sleep이 비싸지 않음
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (int i = 0; i < 10_000; i++) {
        executor.submit(() -> {
            Thread.sleep(1000); // 캐리어 스레드 반납, 다른 VThread 실행
            process();
        });
    }
}
```

---

## 극한 시나리오

### 100 TPS — 기존 방식으로 충분

초당 100건의 요청은 기존 플랫폼 스레드 풀(50~100개)로 처리 가능합니다. 이 단계에서 Virtual Thread를 도입하면 오히려 디버깅 복잡도만 늘어납니다.

```java
// 100 TPS: 기존 방식 유지
@Bean
public ExecutorService taskExecutor() {
    return Executors.newFixedThreadPool(50);
}
```

### 10,000 TPS — Virtual Thread 전환 효과 극대화

초당 10,000건 이상에서 각 요청이 외부 API를 2~3회 호출한다면, 동시 I/O 대기 수가 수만 건에 달합니다. 플랫폼 스레드로는 OOM 또는 스레드 기아가 발생합니다.

```java
// Spring Boot 3.2+ 한 줄 설정
// application.yml
spring:
  threads:
    virtual:
      enabled: true

// 또는 직접 설정
@Bean
public TomcatProtocolHandlerCustomizer<?> virtualThreadCustomizer() {
    return handler -> handler.setExecutor(
        Executors.newVirtualThreadPerTaskExecutor()
    );
}
```

이 설정만으로 동시 처리 스레드가 사실상 무제한이 되며, 각 요청의 I/O 대기 중에 캐리어 스레드를 반납하여 다른 요청을 처리합니다.

### 100,000 TPS — 구조적 병목 해소

Virtual Thread를 도입해도 초당 100,000건에서는 DB, 캐시, 외부 API가 병목이 됩니다. 각 레이어의 동시성 한계를 명확히 해야 합니다.

```java
// 100K TPS 구조: Virtual Thread + 세마포어로 하위 서비스 보호
public class RateLimitedService {
    // DB 커넥션 풀 한계를 세마포어로 반영
    private final Semaphore dbSemaphore = new Semaphore(200);
    // 외부 API rate limit 반영
    private final Semaphore apiSemaphore = new Semaphore(500);

    public Response process(Request req) throws InterruptedException {
        dbSemaphore.acquire();
        try {
            String dbResult = database.query(req.id()); // Virtual Thread가 대기 중 캐리어 반납
            apiSemaphore.acquire();
            try {
                String apiResult = externalApi.call(dbResult);
                return new Response(apiResult);
            } finally {
                apiSemaphore.release();
            }
        } finally {
            dbSemaphore.release();
        }
    }
}
```

<div class="mermaid">
graph TD
    subgraph "100K TPS Virtual Thread 아키텍처"
        VT["Virtual Thread\n(수십만 개 동시 존재)"]
        CT["캐리어 스레드\n(CPU 코어 수만큼)"]
        SEM["Semaphore\n(하위 서비스 보호)"]
        DB["DB 커넥션 풀\n(200개)"]
        API["외부 API\n(500 동시)"]
        CACHE["Redis 캐시\n(커넥션 풀 100개)"]
    end

    VT -->|"I/O 대기 시 반납"| CT
    VT --> SEM
    SEM --> DB
    SEM --> API
    VT --> CACHE
</div>

Virtual Thread 자체는 무제한에 가깝게 생성할 수 있지만, 실제 처리량은 가장 느린 하위 서비스의 처리 능력에 의해 결정됩니다. 세마포어로 역압력(back-pressure)을 구현하면 하위 서비스를 보호하면서 최대 처리량을 유지할 수 있습니다.

---

## 정리

Virtual Thread는 Java 생태계에서 동시성 프로그래밍의 패러다임을 바꾸는 기술입니다.

```
Virtual Thread 핵심 요약

장점:
  ✔ 동기식 코드 스타일 유지 → 가독성, 디버깅 용이
  ✔ I/O 바운드 처리량 대폭 향상 (기존 대비 수 배 ~ 수십 배)
  ✔ 메모리 효율 극대화 (수백만 VThread 동시 운영 가능)
  ✔ 기존 Java 코드 최소 변경으로 마이그레이션

주의사항:
  ✘ synchronized 내 블로킹 → 피닝 발생 → ReentrantLock으로 교체
  ✘ CPU 바운드 작업에는 효과 없음
  ✘ ThreadLocal 대량 사용 시 메모리 주의 → ScopedValue 검토
  ✘ DB 커넥션 풀 크기 반드시 재조정

적용 권장:
  → 웹 서버, API 게이트웨이, 마이크로서비스 간 통신
  → 다수의 외부 API 호출을 병렬로 수행하는 서비스
  → Spring Boot 3.2+에서 spring.threads.virtual.enabled=true 한 줄로 시작
```
