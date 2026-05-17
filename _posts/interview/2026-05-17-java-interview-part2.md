---
title: "Java 면접 — 동시성 핵심 질문 (Q11~Q22)"
categories: INTERVIEW
tags: [Java, 면접, 동시성, synchronized, volatile, Lock]
toc: true
toc_sticky: true
toc_label: 목차
---

## 2. 동시성 (Q11 ~ Q22)

### Q11. synchronized 키워드의 동작 원리는?

**모범 답변**

`synchronized`는 **모니터 락**(Monitor Lock)을 사용합니다. 모든 Java 객체는 내부에 모니터를 가집니다.

```java
// 인스턴스 메서드 — this 객체의 모니터 락
public synchronized void instanceMethod() { ... }

// 클래스 메서드 — Class 객체의 모니터 락
public static synchronized void staticMethod() { ... }

// 블록 — 명시적 락 객체
public void method() {
    synchronized (lockObject) { ... }
}
```

JVM 바이트코드에서 `MONITORENTER` / `MONITOREXIT` 명령어로 구현됩니다.

> **비유:** 모니터 락은 화장실 열쇠입니다. 들어갈 때 열쇠를 가져가고(MONITORENTER), 나올 때 반납합니다(MONITOREXIT). 다른 스레드는 열쇠가 돌아올 때까지 기다립니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** synchronized의 성능 문제를 어떻게 해결하나요?

1. `ReentrantLock`으로 교체 — tryLock(), 타임아웃, 공정성(fairness) 설정 가능
2. 락 범위 최소화 — 블록 동기화 사용
3. 읽기/쓰기 분리 — `ReadWriteLock` 사용 (읽기 동시, 쓰기 독점)
4. 낙관적 동기화 — `AtomicXxx` 클래스 사용

</details>

---

### Q12. volatile 키워드는 무엇을 보장하나요?

**모범 답변**

`volatile`은 두 가지를 보장합니다.

1. **가시성(Visibility)**: 한 스레드의 변경이 다른 스레드에 즉시 보임 (CPU 캐시 대신 메인 메모리에서 읽음)
2. **명령 재정렬 방지(Memory Barrier)**: JIT 컴파일러와 CPU가 명령어 순서를 바꾸지 못하도록 함

**보장하지 않는 것:** 원자성(Atomicity)

```java
volatile int count = 0;
count++; // 읽기-증가-쓰기 3단계 → 원자적 아님!
```

`count++`는 복합 연산이라 `synchronized` 또는 `AtomicInteger`가 필요합니다.

> **비유:** volatile은 공유 화이트보드와 같습니다. 누가 적어도 모두 바로 볼 수 있지만, 동시에 두 사람이 지우고 쓰면 충돌이 생깁니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** Double-Checked Locking 패턴에서 volatile이 필요한 이유는?

```java
private volatile static Singleton instance;

public static Singleton getInstance() {
    if (instance == null) {
        synchronized (Singleton.class) {
            if (instance == null) {
                instance = new Singleton(); // 3단계: 메모리 할당 → 초기화 → 참조 저장
            }
        }
    }
    return instance;
}
```

`volatile` 없이는 JIT가 순서를 바꿀 수 있습니다. "참조 저장 → 초기화" 순으로 재정렬되면 반쯤 초기화된 객체가 보일 수 있습니다.

</details>

---

### Q13. Java Memory Model(JMM)이란?

**모범 답변**

JMM은 멀티스레드 환경에서 변수의 읽기/쓰기 순서에 대한 규칙을 정의합니다. 핵심 개념: **happens-before** 관계.

A happens-before B이면 A의 결과가 B에게 보입니다.

주요 happens-before 규칙:
1. 프로그램 순서 규칙: 같은 스레드 내 앞선 코드 → 이후 코드
2. `volatile` 쓰기 → `volatile` 읽기
3. `synchronized` 릴리스 → 동일 모니터 획득
4. 스레드 시작(`Thread.start()`) → 스레드 코드 실행
5. 스레드 완료 → `Thread.join()` 반환

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** CPU 캐시와 메인 메모리 불일치 문제를 Java에서 어떻게 해결하나요?

`volatile`, `synchronized`, `Atomic` 클래스, `java.util.concurrent.locks` 패키지를 사용합니다. 이들은 내부적으로 메모리 배리어(Memory Barrier)를 삽입하여 캐시와 메인 메모리를 동기화합니다.

</details>

---

### Q14. ThreadLocal의 사용법과 주의사항은?

**모범 답변**

`ThreadLocal`은 스레드마다 독립적인 변수 저장소를 제공합니다.

```java
private static final ThreadLocal<DateFormat> dateFormat =
    ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyy-MM-dd"));

// 각 스레드가 자신만의 DateFormat 인스턴스 사용
public String format(Date date) {
    return dateFormat.get().format(date);
}
```

**주의사항:** 스레드 풀 환경에서 스레드가 재사용되므로, 사용 후 반드시 `remove()` 호출.

```java
try {
    threadLocal.set(value);
    // 처리
} finally {
    threadLocal.remove(); // 메모리 누수 방지
}
```

> **비유:** ThreadLocal은 개인 사물함입니다. 각 직원(스레드)이 자신만의 사물함을 가지고, 퇴근할 때(스레드 반환) 반드시 비워야 합니다.

---

### Q15. AtomicInteger와 synchronized의 차이는?

**모범 답변**

`AtomicInteger`는 **CAS(Compare-And-Swap)** 하드웨어 명령어를 사용합니다. 락 없이 원자적 연산이 가능합니다.

```java
AtomicInteger count = new AtomicInteger(0);
count.incrementAndGet(); // CAS로 원자적 증가
count.compareAndSet(1, 2); // 현재값이 1이면 2로 변경
```

**CAS 동작:** 메모리 값 읽기 → 원하는 값으로 교환 → 교환 시점에 메모리 값이 읽은 값과 같으면 성공, 다르면 재시도.

**선택 기준:**
- 단순 카운터, 플래그: `AtomicXxx` (락 오버헤드 없음)
- 복잡한 복합 연산: `synchronized` 또는 `ReentrantLock`

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** CAS의 ABA 문제란?

값 A → B → A로 변경됐는데, CAS는 A임을 확인하고 성공합니다. 중간에 변경이 있었음을 감지 못합니다. 해결: `AtomicStampedReference`로 버전 번호(stamp)를 함께 비교.

</details>

---

### Q16. ExecutorService의 스레드 풀 설정 가이드라인은?

**모범 답변**

`ThreadPoolExecutor` 핵심 파라미터:

| 파라미터 | 설명 |
|---|---|
| corePoolSize | 기본 스레드 수 |
| maximumPoolSize | 최대 스레드 수 |
| keepAliveTime | 유휴 스레드 대기 시간 |
| workQueue | 작업 대기 큐 |
| RejectedExecutionHandler | 큐 포화 시 처리 정책 |

**작업 유형별 스레드 수 가이드:**
- CPU 집중: `Runtime.getRuntime().availableProcessors() + 1`
- I/O 집중: CPU 수 × (1 + 대기시간/처리시간)

```java
ExecutorService executor = new ThreadPoolExecutor(
    4,                       // core
    8,                       // max
    60L, TimeUnit.SECONDS,   // keepAlive
    new ArrayBlockingQueue<>(100), // 유계 큐 권장
    new ThreadPoolExecutor.CallerRunsPolicy() // 포화 시 호출자가 직접 실행
);
```

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** `Executors.newFixedThreadPool`이 프로덕션에서 위험한 이유는?

내부적으로 `LinkedBlockingQueue` (무제한 큐)를 사용합니다. 큐가 무제한으로 쌓여 `OutOfMemoryError` 위험이 있습니다. 직접 `ThreadPoolExecutor`를 생성하여 유계 큐를 사용하는 것을 권장합니다.

</details>

---

### Q17 ~ Q22. 동시성 심화 문제

**Q17. CountDownLatch vs CyclicBarrier의 차이는?**

`CountDownLatch`: 1회용. N개 이벤트 완료까지 기다림. 예: 초기화 완료 대기.
`CyclicBarrier`: 재사용 가능. N개 스레드 모두 도착할 때까지 대기 후 동시 시작. 예: 일괄 처리 단계 동기화.

**Q18. ReentrantLock의 공정성(Fairness)이란?**

`new ReentrantLock(true)`: 대기 중인 스레드 중 가장 오래 기다린 스레드에게 락 부여. 기아(Starvation) 방지. 성능은 약간 낮습니다.

**Q19. 데드락 발생 조건 4가지는?**

1. 상호 배제 (Mutual Exclusion)
2. 점유 대기 (Hold and Wait)
3. 비선점 (No Preemption)
4. 순환 대기 (Circular Wait)

해결: 락 획득 순서 고정, 타임아웃 적용(`tryLock`), 락 필요성 재검토.

**Q20. CompletableFuture의 장점은?**

비동기 작업 체이닝(`thenApply`, `thenCompose`), 조합(`allOf`, `anyOf`), 예외 처리(`exceptionally`, `handle`). `Future`보다 유연한 비동기 프로그래밍.

**Q21. `ForkJoinPool`은 언제 사용하나요?**

분할 정복(Divide and Conquer) 문제에 적합합니다. 작업을 재귀적으로 분할하여 병렬 처리. `parallelStream()`의 기반 풀이기도 합니다. CPU 집중 병렬 처리에 활용합니다.

**Q22. Semaphore의 사용 시나리오는?**

동시 접근 수를 제한할 때 사용합니다. 예: DB 커넥션 풀 제한, API Rate Limiting, 파일 동시 접근 제한.

```java
Semaphore semaphore = new Semaphore(10); // 최대 10개 동시 접근
semaphore.acquire();
try { /* DB 접근 */ } finally { semaphore.release(); }
```

---


---

## 다른 파트 보기

- [Part 1: JVM 메모리 구조 (Q1~Q10)](/interview/java-interview-part1/)
- [Part 2: 동시성 (Q11~Q22)](/interview/java-interview-part2/)
- [Part 3: Collection 내부 구조 (Q23~Q33)](/interview/java-interview-part3/)
- [Part 4: Stream / Functional (Q34~Q40)](/interview/java-interview-part4/)
- [Part 5: 예외처리 / Generics (Q41~Q50)](/interview/java-interview-part5/)
