---
title: "Java 스레드(Thread) — 동시성 프로그래밍"
categories:
- JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

주문 처리와 이메일 발송을 순차적으로 하면 사용자는 이메일이 발송될 때까지 기다려야 한다. 스레드를 분리하면 주문 처리 응답을 즉시 주고 이메일은 백그라운드에서 보낼 수 있다. 하지만 스레드를 잘못 다루면 데이터가 꼬인다.

> **비유로 먼저 이해하기**: 스레드는 주방의 요리사와 같다. 요리사가 한 명(단일 스레드)이면 한 번에 한 요리만 된다. 여러 명(멀티 스레드)이면 동시에 여러 요리를 할 수 있지만, 같은 재료(공유 자원)를 동시에 집으려 하면 충돌이 생긴다. 이 충돌을 막는 규칙이 동기화다.

Java 스레드와 동시성 프로그래밍의 핵심 개념부터 실무 패턴까지 완전히 정리합니다. 기본 개념, 동기화 메커니즘, java.util.concurrent 패키지, Virtual Thread까지 빠짐없이 다룹니다.

---

## 1. 스레드 기본 개념

### 프로세스 vs 스레드

**프로세스(Process)**는 운영체제로부터 자원을 할당받는 독립적인 실행 단위입니다. 각 프로세스는 독립된 메모리 공간(Code, Data, Stack, Heap)을 가집니다.

**스레드(Thread)**는 프로세스 내에서 실행되는 흐름의 단위입니다. 같은 프로세스의 스레드들은 Heap과 Code, Data 영역을 공유하며, 각자 독립적인 Stack과 PC(Program Counter)를 가집니다.

<div class="mermaid">
graph LR
  subgraph PA["프로세스 A (메모리 공유)"]
    A1[Code]
    A2[Data]
    A3[Heap]
    A4[Thread1 Stack]
    A5[Thread2 Stack]
    A6[Thread3 Stack]
  end
  subgraph PB["프로세스 B (메모리 격리)"]
    B1[Code]
    B2[Data]
    B3[Heap]
    B4[Thread1 Stack]
  end
</div>

| 구분 | 프로세스 | 스레드 |
|------|---------|--------|
| 메모리 | 독립 공간 | Heap/Code 공유 |
| 생성 비용 | 높음 | 낮음 |
| 컨텍스트 스위칭 | 느림 | 빠름 |
| 통신 방법 | IPC (소켓, 파이프) | 공유 메모리 직접 접근 |
| 격리성 | 완전 격리 | 동일 프로세스 내 |

### 커널 스레드 vs 유저 스레드

**커널 스레드(Kernel Thread)**는 OS가 직접 관리하는 스레드입니다. OS 스케줄러가 CPU 코어에 할당합니다. 생성/전환 비용이 비교적 크지만 진정한 병렬 실행이 가능합니다.

**유저 스레드(User Thread)**는 사용자 공간(User Space)에서 라이브러리가 관리하는 스레드입니다. OS는 유저 스레드의 존재를 모릅니다. 생성/전환 비용이 낮지만, 하나가 블로킹되면 전체가 블로킹될 수 있습니다.

**매핑 모델 3가지:**

<div class="mermaid">
graph LR
  subgraph M1["1:1 매핑 (Java Platform Thread)"]
    T1 --> KT1
    T2 --> KT2
    T3 --> KT3
  end
  subgraph M2["N:1 매핑 (한 T가 블로킹되면 전체 정지)"]
    U1[T1] --> KU1[KT1]
    U2[T2] --> KU1
    U3[T3] --> KU1
  end
  subgraph M3["M:N 매핑 (Java 21 Virtual Thread)"]
    VT1 --> KV1[KT1]
    VT2 --> KV1
    VT3 --> KV2[KT2]
    VT4 --> KV3[KT3]
  end
</div>

### JVM 스레드 모델 (1:1 매핑)

Java의 전통적인 Platform Thread는 OS 커널 스레드와 **1:1로 매핑**됩니다. `new Thread()`로 Java 스레드를 생성하면 OS 커널 스레드가 하나 만들어집니다.

<div class="mermaid">
graph TD
  subgraph JVM["JVM"]
    JT1[Java Thread 1] --> KT1[커널 스레드 1]
    JT2[Java Thread 2] --> KT2[커널 스레드 2]
    JT3[Java Thread 3] --> KT3[커널 스레드 3]
  end
  KT1 -->|JNI| OS
  KT2 -->|JNI| OS
  KT3 -->|JNI| OS
  subgraph OS["OS 스케줄러"]
    CPU1[CPU 코어 1]
    CPU2[CPU 코어 2]
  end
</div>

이 모델의 한계는 커널 스레드 생성 비용(약 1MB 스택 메모리)과 컨텍스트 스위칭 오버헤드입니다. 수만 개의 스레드를 동시에 만들기 어렵습니다.

### 스레드 생명주기

Java 스레드는 `java.lang.Thread.State` 열거형으로 6가지 상태를 가집니다.

<div class="mermaid">
stateDiagram-v2
  [*] --> NEW : new Thread()
  NEW --> RUNNABLE : start()
  RUNNABLE --> BLOCKED : synchronized 블록 진입 실패
  BLOCKED --> RUNNABLE : 락 획득
  RUNNABLE --> WAITING : wait() / join() / park()
  WAITING --> RUNNABLE : notify() / unpark()
  RUNNABLE --> TIMED_WAITING : sleep(n) / wait(n) / join(n)
  TIMED_WAITING --> RUNNABLE : 시간 경과 / notify()
  RUNNABLE --> TERMINATED : run() 완료 / 예외 발생
  NEW --> TERMINATED : 예외 발생
</div>

| 상태 | 설명 |
|------|------|
| `NEW` | `new Thread()` 생성 후 `start()` 전 |
| `RUNNABLE` | 실행 중이거나 CPU 할당 대기 중 |
| `BLOCKED` | synchronized 락 획득 대기 중 |
| `WAITING` | 다른 스레드의 통지를 무기한 대기 |
| `TIMED_WAITING` | 지정 시간 동안 대기 |
| `TERMINATED` | 실행 완료 또는 예외로 종료 |

```java
Thread thread = new Thread(() -> {
    System.out.println("state: " + Thread.currentThread().getState()); // RUNNABLE
});

System.out.println("before start: " + thread.getState()); // NEW
thread.start();
thread.join();
System.out.println("after join: " + thread.getState()); // TERMINATED
```

---

## 2. 스레드 생성 방법

### Thread 상속

`Thread` 클래스를 상속하고 `run()` 메서드를 오버라이드합니다.

```java
public class MyThread extends Thread {
    private final String name;

    public MyThread(String name) {
        super(name); // 스레드 이름 설정
        this.name = name;
    }

    @Override
    public void run() {
        System.out.printf("[%s] 실행 중, ID=%d%n",
                name, Thread.currentThread().getId());
        try {
            Thread.sleep(1000); // 1초 대기
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt(); // 인터럽트 플래그 복원
            System.out.println(name + " 인터럽트 발생");
        }
    }
}

// 사용
MyThread t1 = new MyThread("Worker-1");
MyThread t2 = new MyThread("Worker-2");
t1.start(); // start()는 반드시 호출, run()을 직접 호출하면 단일 스레드로 실행됨
t2.start();
t1.join(); // t1 완료 대기
t2.join(); // t2 완료 대기
System.out.println("모든 스레드 완료");
```

**단점:** Java는 단일 상속이므로 다른 클래스를 상속받고 있으면 사용 불가합니다.

### Runnable 구현

`Runnable` 인터페이스를 구현하는 방식으로 더 유연합니다.

```java
public class PrintTask implements Runnable {
    private final int taskId;

    public PrintTask(int taskId) {
        this.taskId = taskId;
    }

    @Override
    public void run() {
        System.out.printf("Task %d 실행 - Thread: %s%n",
                taskId, Thread.currentThread().getName());
    }
}

// 익명 클래스로 사용
Runnable r = new Runnable() {
    @Override
    public void run() {
        System.out.println("익명 클래스 실행");
    }
};

// 람다로 사용 (Java 8+)
Runnable lambda = () -> System.out.println("람다 실행");

Thread t = new Thread(lambda, "lambda-thread");
t.setDaemon(false);      // false: JVM 종료 시까지 실행 (기본값)
t.setPriority(Thread.NORM_PRIORITY); // 우선순위 1~10, 기본 5
t.start();
```

### Callable + Future

`Callable`은 `Runnable`과 달리 **결과값을 반환**하고 **체크드 예외를 던질** 수 있습니다.

```java
import java.util.concurrent.*;

Callable<Integer> task = () -> {
    System.out.println("Callable 실행 중...");
    Thread.sleep(2000);
    return 42; // 결과 반환
};

ExecutorService executor = Executors.newSingleThreadExecutor();
Future<Integer> future = executor.submit(task);

System.out.println("비동기 작업 제출 완료, 다른 작업 수행 가능");

try {
    // get()은 블로킹: 결과가 준비될 때까지 현재 스레드 대기
    Integer result = future.get(3, TimeUnit.SECONDS); // 타임아웃 설정
    System.out.println("결과: " + result);
} catch (TimeoutException e) {
    future.cancel(true); // 인터럽트로 취소
    System.out.println("타임아웃!");
} catch (ExecutionException e) {
    System.out.println("작업 내부 예외: " + e.getCause());
} catch (InterruptedException e) {
    Thread.currentThread().interrupt();
} finally {
    executor.shutdown();
}

// Future 상태 확인
// future.isDone()     - 완료 여부 (정상/예외/취소 모두 포함)
// future.isCancelled() - 취소 여부
// future.cancel(true)  - 실행 중이면 인터럽트, 대기 중이면 취소
```

### CompletableFuture (Java 8+)

비동기 작업을 선언적으로 체이닝할 수 있는 강력한 클래스입니다.

```java
import java.util.concurrent.CompletableFuture;

// 기본 비동기 실행
CompletableFuture<String> future = CompletableFuture
        .supplyAsync(() -> {
            // ForkJoinPool.commonPool()에서 실행
            System.out.println("비동기 작업 시작");
            return "Hello";
        })
        .thenApply(result -> result + ", World")          // 변환
        .thenApply(String::toUpperCase)                   // 추가 변환
        .thenApply(result -> result + "!");               // 최종 변환

System.out.println(future.join()); // HELLO, WORLD!

// 커스텀 Executor 지정
ExecutorService customExecutor = Executors.newFixedThreadPool(4);

CompletableFuture<Void> pipeline = CompletableFuture
        .supplyAsync(() -> fetchUserData(1L), customExecutor)
        .thenApplyAsync(user -> processUser(user), customExecutor)
        .thenAcceptAsync(processed -> saveResult(processed), customExecutor)
        .exceptionally(ex -> {
            System.out.println("파이프라인 에러: " + ex.getMessage());
            return null;
        });

pipeline.join();
customExecutor.shutdown();
```

---

## 3. 동기화 (Synchronization)

### synchronized 키워드

**메서드 레벨 synchronized:**

```java
public class Counter {
    private int count = 0;

    // 인스턴스 메서드: this 객체 자체를 락으로 사용
    public synchronized void increment() {
        count++;
    }

    // 정적 메서드: Counter.class 객체를 락으로 사용
    public static synchronized void staticMethod() {
        // ...
    }

    public synchronized int getCount() {
        return count;
    }
}
```

**블록 레벨 synchronized (더 세밀한 제어):**

```java
public class FineGrainedCounter {
    private int readCount = 0;
    private int writeCount = 0;

    // 락 객체를 분리하여 읽기/쓰기 독립적으로 동기화
    private final Object readLock = new Object();
    private final Object writeLock = new Object();

    public void incrementRead() {
        synchronized (readLock) {
            readCount++;
        }
        // writeLock은 건드리지 않음 → 병렬성 향상
    }

    public void incrementWrite() {
        synchronized (writeLock) {
            writeCount++;
        }
    }

    public void both() {
        // 데드락 방지: 항상 동일 순서로 락 획득
        synchronized (readLock) {
            synchronized (writeLock) {
                readCount++;
                writeCount++;
            }
        }
    }
}
```

### 모니터 락 (Monitor Lock) 동작 원리

Java의 모든 객체는 내부적으로 **모니터(Monitor)**를 가집니다. 모니터는 뮤텍스 락 + 대기 큐로 구성됩니다.

<div class="mermaid">
graph TD
  subgraph Header["Object Header"]
    MW["Mark Word: 락 상태 정보\n(unlock / biased / thin / fat)"]
  end
  subgraph Monitor["Monitor (C++ ObjectMonitor)"]
    OW[owner: 현재 락 보유 스레드]
    CT[count: 재진입 횟수]
    ES[EntrySet: 락 대기 스레드들]
    WS[WaitSet: wait() 대기 스레드]
  end
  Header --> Monitor

  A([Thread A]) --> ME[monitorenter]
  ME --> CHK{owner == null?}
  CHK -->|YES| OWN["owner=A, count=1"]
  CHK -->|NO| ES2["EntrySet 추가 → BLOCKED"]

  A2([Thread A]) --> MX[monitorexit]
  MX --> DEC["count--"]
  DEC --> CHK2{count == 0?}
  CHK2 -->|YES| REL["owner=null, EntrySet 재경쟁"]
</div>

**재진입(Reentrant):** 같은 스레드가 이미 보유한 락을 다시 요청하면 count만 증가합니다.

```java
public class ReentrantExample {
    public synchronized void outer() {
        System.out.println("outer 진입 (count=1)");
        inner(); // 같은 스레드, 재진입 허용 (count=2)
    }

    public synchronized void inner() {
        System.out.println("inner 진입 (count=2)");
    } // monitorexit → count=1

    // outer 종료 시 count=0, 락 해제
}
```

### Object의 wait() / notify() / notifyAll()

`wait()`, `notify()`, `notifyAll()`은 **반드시 synchronized 블록 내에서** 호출해야 합니다.

```java
public class ProducerConsumer {
    private final Queue<Integer> queue = new LinkedList<>();
    private final int MAX_SIZE = 5;

    public synchronized void produce(int item) throws InterruptedException {
        while (queue.size() == MAX_SIZE) {
            System.out.println("큐 가득참, 생산자 대기");
            wait(); // 락을 해제하고 WaitSet으로 이동
        }
        queue.add(item);
        System.out.println("생산: " + item + ", 큐 크기: " + queue.size());
        notifyAll(); // WaitSet의 모든 스레드를 EntrySet으로 이동
    }

    public synchronized int consume() throws InterruptedException {
        while (queue.isEmpty()) {
            System.out.println("큐 비어있음, 소비자 대기");
            wait();
        }
        int item = queue.poll();
        System.out.println("소비: " + item + ", 큐 크기: " + queue.size());
        notifyAll();
        return item;
    }
}
```

**notify() vs notifyAll():**
- `notify()`: WaitSet에서 임의의 스레드 하나만 깨움 → starvation 위험
- `notifyAll()`: WaitSet의 모든 스레드 깨움 → 더 안전하지만 오버헤드 큼

### 가시성(Visibility) 문제와 volatile 키워드

멀티코어 환경에서 각 코어는 **CPU 캐시**를 가집니다. 한 스레드가 변수를 수정해도 다른 코어의 캐시에 즉시 반영되지 않을 수 있습니다.

<div class="mermaid">
graph TD
  subgraph Core1["CPU 코어 1 캐시"]
    F1["flag = true"]
  end
  subgraph Core2["CPU 코어 2 캐시"]
    F2["flag = false ← 코어 2는 업데이트를 못 봄!"]
  end
  MM["메인 메모리: flag = true"]
  Core1 <--> MM
  Core2 <--> MM
</div>

```java
// 문제: stop 플래그 변경이 다른 스레드에 보이지 않을 수 있음
private boolean stop = false; // 위험!

// 해결: volatile 선언
private volatile boolean stop = false;

// volatile은 가시성만 보장, 원자성은 보장하지 않음
private volatile int count = 0;
count++; // NOT atomic! (read-modify-write 세 단계)
// 원자성이 필요하면 AtomicInteger 또는 synchronized 사용
```

**volatile 사용 사례:**
```java
public class StopFlag {
    private volatile boolean running = true; // volatile 필수

    public void run() {
        while (running) {
            // 작업 수행
        }
        System.out.println("종료됨");
    }

    public void stop() {
        running = false; // 다른 스레드에서 호출
    }
}
```

### happens-before 관계

**happens-before**는 JMM(Java Memory Model)에서 정의한 메모리 가시성 보장 규칙입니다. A happens-before B라면 A의 모든 결과가 B에 보입니다.

주요 happens-before 규칙:
1. **Program Order Rule**: 같은 스레드 내 앞 코드 → 뒷 코드
2. **Monitor Lock Rule**: `unlock()` → 동일 모니터의 `lock()`
3. **Volatile Variable Rule**: volatile 쓰기 → 이후 volatile 읽기
4. **Thread Start Rule**: `Thread.start()` → 시작된 스레드의 모든 동작
5. **Thread Join Rule**: 스레드 종료 → `join()` 이후의 모든 동작
6. **Transitivity**: A → B이고 B → C이면 A → C

```java
int x = 0;
volatile boolean flag = false;

// Thread 1
x = 42;          // (1)
flag = true;     // (2) volatile 쓰기

// Thread 2
if (flag) {      // (3) volatile 읽기 → (2) happens-before (3)
    // x == 42 가 보장됨: (1) happens-before (2) happens-before (3)
    System.out.println(x); // 항상 42
}
```

---

## 4. java.util.concurrent 핵심

### ReentrantLock

`synchronized`보다 유연한 락입니다. 공정/비공정 선택, tryLock, Condition 사용이 가능합니다.

```java
import java.util.concurrent.locks.*;

public class ReentrantLockExample {
    // 공정 락(fair=true): 대기 순서 보장, 처리량 낮음
    // 비공정 락(fair=false): 순서 미보장, 처리량 높음 (기본값)
    private final ReentrantLock lock = new ReentrantLock(false);

    public void basicUsage() {
        lock.lock();
        try {
            // 임계 구역
        } finally {
            lock.unlock(); // 반드시 finally에서 해제
        }
    }

    public boolean tryLockUsage() {
        // 즉시 반환: 락 획득 실패 시 false
        if (lock.tryLock()) {
            try {
                return true;
            } finally {
                lock.unlock();
            }
        }
        return false; // 락 획득 실패
    }

    public boolean tryLockWithTimeout() throws InterruptedException {
        // 최대 1초 대기
        if (lock.tryLock(1, TimeUnit.SECONDS)) {
            try {
                return true;
            } finally {
                lock.unlock();
            }
        }
        return false;
    }

    // Condition: 특정 조건 기반 대기/신호
    private final Condition notFull = lock.newCondition();
    private final Condition notEmpty = lock.newCondition();
    private final Queue<Integer> queue = new ArrayDeque<>();
    private static final int MAX = 5;

    public void put(int item) throws InterruptedException {
        lock.lock();
        try {
            while (queue.size() == MAX) {
                notFull.await(); // wait()과 유사, 락 해제 후 대기
            }
            queue.add(item);
            notEmpty.signal(); // notify()와 유사, 하나만 깨움
        } finally {
            lock.unlock();
        }
    }

    public int take() throws InterruptedException {
        lock.lock();
        try {
            while (queue.isEmpty()) {
                notEmpty.await();
            }
            int item = queue.poll();
            notFull.signal();
            return item;
        } finally {
            lock.unlock();
        }
    }
}
```

### ReadWriteLock

읽기는 병렬로, 쓰기는 독점으로 처리합니다. 읽기가 많은 환경에서 성능을 크게 향상시킵니다.

```java
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

public class Cache<K, V> {
    private final Map<K, V> map = new HashMap<>();
    private final ReadWriteLock rwLock = new ReentrantReadWriteLock();
    private final Lock readLock = rwLock.readLock();
    private final Lock writeLock = rwLock.writeLock();

    public V get(K key) {
        readLock.lock(); // 여러 스레드 동시 읽기 가능
        try {
            return map.get(key);
        } finally {
            readLock.unlock();
        }
    }

    public void put(K key, V value) {
        writeLock.lock(); // 쓰기 시 모든 읽기/쓰기 차단
        try {
            map.put(key, value);
        } finally {
            writeLock.unlock();
        }
    }
}
```

**ReadWriteLock 동시성 규칙:**
- 읽기 락 ↔ 읽기 락: 동시 허용
- 읽기 락 ↔ 쓰기 락: 상호 배제
- 쓰기 락 ↔ 쓰기 락: 상호 배제

### StampedLock (Java 8)

낙관적 읽기(Optimistic Read)를 지원하여 ReadWriteLock보다 높은 처리량을 제공합니다.

```java
import java.util.concurrent.locks.StampedLock;

public class Point {
    private double x, y;
    private final StampedLock sl = new StampedLock();

    public void move(double deltaX, double deltaY) {
        long stamp = sl.writeLock(); // 쓰기 락
        try {
            x += deltaX;
            y += deltaY;
        } finally {
            sl.unlockWrite(stamp);
        }
    }

    public double distanceFromOrigin() {
        // 낙관적 읽기: 락을 획득하지 않고 읽기 시도
        long stamp = sl.tryOptimisticRead();
        double curX = x, curY = y;

        // 읽는 동안 쓰기 발생 여부 확인
        if (!sl.validate(stamp)) {
            // 쓰기가 발생했으므로 읽기 락으로 재시도
            stamp = sl.readLock();
            try {
                curX = x;
                curY = y;
            } finally {
                sl.unlockRead(stamp);
            }
        }
        return Math.sqrt(curX * curX + curY * curY);
    }
}
```

### Semaphore

지정된 수의 스레드만 동시에 접근할 수 있도록 제한합니다.

```java
import java.util.concurrent.Semaphore;

// 시나리오: DB 커넥션 풀 (최대 10개 동시 연결)
public class ConnectionPool {
    private final Semaphore semaphore = new Semaphore(10, true); // 공정
    private final Queue<Connection> pool = new ConcurrentLinkedQueue<>();

    public Connection acquire() throws InterruptedException {
        semaphore.acquire(); // permit 획득 (없으면 대기)
        return pool.poll();
    }

    public void release(Connection conn) {
        pool.offer(conn);
        semaphore.release(); // permit 반납
    }

    // 현재 사용 가능한 permit 수
    public int availablePermits() {
        return semaphore.availablePermits();
    }
}

// 간단한 예제: 동시 3개 스레드만 허용
Semaphore sem = new Semaphore(3);
for (int i = 0; i < 10; i++) {
    final int id = i;
    new Thread(() -> {
        try {
            sem.acquire();
            System.out.println("스레드 " + id + " 실행 중");
            Thread.sleep(1000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            sem.release();
        }
    }).start();
}
```

### CountDownLatch

일회성 카운트다운 래치입니다. 특정 수의 이벤트가 발생할 때까지 하나 이상의 스레드가 대기합니다.

```java
import java.util.concurrent.CountDownLatch;

// 시나리오: 여러 서비스 초기화 완료 후 메인 로직 시작
public class ServiceInitializer {
    private final CountDownLatch latch = new CountDownLatch(3);

    public void init() throws InterruptedException {
        // 3개의 서비스를 병렬 초기화
        new Thread(() -> {
            initDatabase();
            latch.countDown(); // 카운트 1 감소 (3→2)
        }).start();

        new Thread(() -> {
            initCache();
            latch.countDown(); // 카운트 1 감소 (2→1)
        }).start();

        new Thread(() -> {
            initMessageQueue();
            latch.countDown(); // 카운트 1 감소 (1→0)
        }).start();

        // 카운트가 0이 될 때까지 블로킹
        latch.await();
        System.out.println("모든 서비스 초기화 완료, 서버 시작!");
        // 참고: CountDownLatch는 재사용 불가 (일회성)
    }
}

// 시나리오: 모든 스레드 동시 출발 (레이스 시작 신호)
CountDownLatch startSignal = new CountDownLatch(1);
CountDownLatch doneSignal = new CountDownLatch(5);

for (int i = 0; i < 5; i++) {
    final int id = i;
    new Thread(() -> {
        try {
            startSignal.await(); // 시작 신호 대기
            System.out.println("스레드 " + id + " 출발!");
            doneSignal.countDown();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }).start();
}

Thread.sleep(1000);
startSignal.countDown(); // 동시 출발 신호
doneSignal.await();      // 모두 완료 대기
```

### CyclicBarrier

지정된 수의 스레드가 모두 배리어에 도달할 때까지 대기하고, 이후 모두 동시에 계속 진행합니다. **재사용 가능**합니다.

```java
import java.util.concurrent.CyclicBarrier;

// 시나리오: 분산 계산 - 각 단계마다 모든 스레드 동기화
public class ParallelMergeSort {
    private final CyclicBarrier barrier;

    public ParallelMergeSort(int numThreads) {
        // 배리어 도달 시 실행할 작업 (선택 사항)
        this.barrier = new CyclicBarrier(numThreads, () -> {
            System.out.println("=== 모든 스레드가 배리어 도달, 다음 단계 시작 ===");
        });
    }

    public void process(int threadId, int[] steps) {
        for (int step : steps) {
            System.out.printf("Thread %d: Step %d 처리 중%n", threadId, step);
            try {
                Thread.sleep(100);
                barrier.await(); // 다른 스레드들 대기
                // 여기서 모든 스레드가 동시에 재개됨
            } catch (InterruptedException | BrokenBarrierException e) {
                Thread.currentThread().interrupt();
            }
        }
    }
}
```

**CountDownLatch vs CyclicBarrier:**

| 특성 | CountDownLatch | CyclicBarrier |
|------|---------------|---------------|
| 재사용 | 불가 | 가능 (reset()) |
| 감소 주체 | 어떤 스레드든 countDown() | 배리어 참여 스레드 |
| 대기 대상 | 이벤트 N번 발생 | 스레드 N개 도달 |
| 배리어 액션 | 없음 | 선택적 Runnable |

### Phaser (Java 7)

`CyclicBarrier`와 `CountDownLatch`를 합친 유연한 동기화 도구입니다. 동적으로 참여자 수를 조절할 수 있습니다.

```java
import java.util.concurrent.Phaser;

// 시나리오: 동적 참여자 수를 가진 다단계 작업
public class PhaserExample {
    public static void main(String[] args) {
        Phaser phaser = new Phaser(1); // 1 = 메인 스레드

        for (int i = 0; i < 3; i++) {
            phaser.register(); // 참여자 추가 (동적)
            final int id = i;
            new Thread(() -> {
                System.out.printf("Phase 0: Worker %d 시작%n", id);
                phaser.arriveAndAwaitAdvance(); // Phase 0 완료 대기

                System.out.printf("Phase 1: Worker %d 시작%n", id);
                phaser.arriveAndAwaitAdvance(); // Phase 1 완료 대기

                System.out.printf("Worker %d 종료%n", id);
                phaser.arriveAndDeregister(); // 참여자 제거
            }).start();
        }

        // 메인 스레드도 각 Phase에 참여
        phaser.arriveAndAwaitAdvance(); // Phase 0
        System.out.println("메인: Phase 0 완료");
        phaser.arriveAndAwaitAdvance(); // Phase 1
        System.out.println("메인: Phase 1 완료");
        phaser.arriveAndDeregister();
    }
}
```

---

## 5. 스레드 풀 (ExecutorService)

### ThreadPoolExecutor 내부 구조

```java
new ThreadPoolExecutor(
    int corePoolSize,          // 기본 유지 스레드 수
    int maximumPoolSize,       // 최대 스레드 수
    long keepAliveTime,        // 초과 스레드 유휴 유지 시간
    TimeUnit unit,             // keepAliveTime 단위
    BlockingQueue<Runnable> workQueue, // 작업 대기 큐
    ThreadFactory threadFactory,       // 스레드 생성 팩토리
    RejectedExecutionHandler handler   // 거부 정책
);
```

**동작 흐름:**

<div class="mermaid">
graph TD
  SUB([작업 제출 submit/execute]) --> CHK1{현재 스레드 수 &lt; corePoolSize?}
  CHK1 -->|YES| NEW1[새 스레드 생성]
  CHK1 -->|NO| CHK2{workQueue 가득 참?}
  CHK2 -->|NO| ENQUEUE[workQueue에 작업 추가]
  CHK2 -->|YES| CHK3{현재 스레드 수 &lt; maxPoolSize?}
  CHK3 -->|YES| NEW2[새 스레드 생성 - 초과 스레드]
  CHK3 -->|NO| REJ[RejectedExecutionHandler 실행]
</div>

**RejectedExecutionHandler 전략:**
- `AbortPolicy` (기본): `RejectedExecutionException` 던짐
- `CallerRunsPolicy`: 제출한 스레드가 직접 실행 (백프레셔 효과)
- `DiscardPolicy`: 조용히 무시
- `DiscardOldestPolicy`: 큐에서 가장 오래된 작업 제거 후 재시도

```java
// 실무 권장 ThreadPoolExecutor 설정
ThreadPoolExecutor executor = new ThreadPoolExecutor(
        4,                                      // corePoolSize
        8,                                      // maxPoolSize
        60L, TimeUnit.SECONDS,                  // keepAlive
        new LinkedBlockingQueue<>(1000),        // 유계 큐 (중요!)
        new ThreadFactory() {
            private final AtomicInteger idx = new AtomicInteger();
            @Override
            public Thread newThread(Runnable r) {
                Thread t = new Thread(r, "worker-" + idx.incrementAndGet());
                t.setDaemon(false);
                return t;
            }
        },
        new ThreadPoolExecutor.CallerRunsPolicy() // 거부 시 호출자 실행
);
```

### Executors 팩토리를 쓰면 안 되는 이유

```java
// 위험! newFixedThreadPool: 큐 크기 무제한 (Integer.MAX_VALUE)
// → 작업이 쌓이면 OOM 발생
ExecutorService bad1 = Executors.newFixedThreadPool(4);

// 위험! newCachedThreadPool: 스레드 수 무제한 (Integer.MAX_VALUE)
// → 폭발적인 요청에 스레드 수십만 개 생성 → OOM
ExecutorService bad2 = Executors.newCachedThreadPool();

// 위험! newSingleThreadExecutor: 큐 크기 무제한
// → OOM 위험
ExecutorService bad3 = Executors.newSingleThreadExecutor();
```

**실무에서는 항상 `ThreadPoolExecutor`를 직접 생성**하여 corePoolSize, maxPoolSize, 큐 크기를 명시적으로 지정하세요.

### ForkJoinPool — Work-Stealing 알고리즘

분할 정복(Divide & Conquer) 방식의 병렬 처리에 최적화된 스레드 풀입니다.

<div class="mermaid">
graph LR
  subgraph W1["Worker 1"]
    T1[Task 1]
    T2[Task 2]
    T3[Task 3]
  end
  subgraph W2["Worker 2"]
    T4[Task 4]
    T5[Task 5]
  end
  subgraph W3["Worker 3 (큐 비어있음)"]
    EMPTY[" "]
  end
  W3 -->|"Work-Stealing: Worker1 큐 뒤에서 훔침"| T3
</div>

```java
import java.util.concurrent.*;

// RecursiveTask: 결과 반환
class SumTask extends RecursiveTask<Long> {
    private final long[] array;
    private final int start, end;
    private static final int THRESHOLD = 1000;

    public SumTask(long[] array, int start, int end) {
        this.array = array;
        this.start = start;
        this.end = end;
    }

    @Override
    protected Long compute() {
        if (end - start <= THRESHOLD) {
            // 충분히 작으면 직접 계산
            long sum = 0;
            for (int i = start; i < end; i++) sum += array[i];
            return sum;
        }
        // 절반으로 분할
        int mid = (start + end) / 2;
        SumTask leftTask = new SumTask(array, start, mid);
        SumTask rightTask = new SumTask(array, mid, end);

        leftTask.fork(); // 비동기 실행 (다른 워커에게 위임)
        long rightResult = rightTask.compute(); // 현재 스레드에서 실행
        long leftResult = leftTask.join(); // 결과 대기

        return leftResult + rightResult;
    }
}

// 사용
ForkJoinPool pool = new ForkJoinPool(
        Runtime.getRuntime().availableProcessors()
);
long[] data = new long[10_000_000];
Arrays.fill(data, 1L);

Long sum = pool.invoke(new SumTask(data, 0, data.length));
System.out.println("합계: " + sum); // 10000000
```

**Java 8+ parallel stream은 내부적으로 ForkJoinPool.commonPool()을 사용:**
```java
long sum = LongStream.rangeClosed(1, 1_000_000)
        .parallel()
        .sum();
```

### 적정 스레드 수 계산

**CPU Bound 작업** (계산 위주, I/O 없음):
```
스레드 수 = CPU 코어 수 + 1
// +1: 페이지 폴트 등 일시 중단 시 다른 스레드가 CPU를 활용
```

**I/O Bound 작업** (DB 쿼리, HTTP 요청 등):
```
스레드 수 = CPU 코어 수 × (1 + 대기 시간 / 계산 시간)

예: CPU 8코어, 요청 처리 100ms 중 80ms가 DB 대기
스레드 수 = 8 × (1 + 80/20) = 8 × 5 = 40
```

```java
int cpuCores = Runtime.getRuntime().availableProcessors();
double blockingCoefficient = 0.8; // 80% I/O 대기

int ioThreads = (int) (cpuCores / (1 - blockingCoefficient));
// 8 / 0.2 = 40

System.out.println("CPU 코어: " + cpuCores);
System.out.println("I/O 작업 권장 스레드: " + ioThreads);
```

---

## 6. Atomic 클래스

### AtomicInteger, AtomicLong, AtomicReference

`synchronized` 없이도 스레드 안전한 원자적 연산을 제공합니다.

```java
import java.util.concurrent.atomic.*;

AtomicInteger counter = new AtomicInteger(0);

counter.get();                    // 현재값 읽기
counter.set(10);                  // 값 설정
counter.getAndIncrement();        // 반환 후 증가 (i++)
counter.incrementAndGet();        // 증가 후 반환 (++i)
counter.getAndAdd(5);             // 반환 후 5 추가
counter.addAndGet(5);             // 5 추가 후 반환
counter.compareAndSet(10, 20);    // 10이면 20으로 변경 (CAS)
counter.getAndUpdate(x -> x * 2); // 함수 적용 후 이전값 반환
counter.updateAndGet(x -> x * 2); // 함수 적용 후 새값 반환

// AtomicReference: 객체 참조를 원자적으로 변경
AtomicReference<String> ref = new AtomicReference<>("initial");
ref.compareAndSet("initial", "updated"); // 참조 비교는 ==
```

### CAS (Compare-And-Swap) 동작 원리

CAS는 "내가 마지막으로 읽은 값이 지금도 같다면 새 값으로 바꿔라"는 원자적 명령입니다. 락을 걸지 않고도 경쟁 조건을 해결하는 핵심 메커니즘으로, x86 CPU의 `CMPXCHG` 명령어로 하드웨어 레벨에서 보장됩니다.

> **비유로 이해하기**: 공유 문서를 동시에 수정하는 상황과 같습니다. "내가 읽었을 때 버전이 5였다면, 버전을 6으로 올리고 내용을 저장해라. 만약 이미 누군가 버전을 바꿨다면(5가 아니라면) 실패로 처리하고 다시 읽어라." CAS는 이 낙관적 동시성 제어(Optimistic Concurrency Control)를 CPU 명령어 하나로 수행합니다.

<div class="mermaid">
flowchart TD
  A["1. 현재값 읽기: val = memory[addr]"] --> B["2. 새값 계산: newVal = val + 1"]
  B --> C{"3. CAS(addr, val, newVal)\nmemory[addr] == val?"}
  C -->|"YES → 원자적으로 교체\nmemory[addr] = newVal"| D["성공 — return newVal"]
  C -->|"NO → 다른 스레드가 먼저 변경"| A
  D2["하드웨어: x86 CMPXCHG 명령어\n단일 CPU 사이클에서 원자적 실행"]
</div>

```java
// CAS를 사용한 lock-free 스택 구현
public class LockFreeStack<T> {
    private final AtomicReference<Node<T>> top = new AtomicReference<>();

    public void push(T item) {
        Node<T> newNode = new Node<>(item);
        Node<T> currentTop;
        do {
            currentTop = top.get();
            newNode.next = currentTop;
        } while (!top.compareAndSet(currentTop, newNode)); // CAS
    }

    public T pop() {
        Node<T> currentTop;
        Node<T> newTop;
        do {
            currentTop = top.get();
            if (currentTop == null) return null;
            newTop = currentTop.next;
        } while (!top.compareAndSet(currentTop, newTop)); // CAS
        return currentTop.item;
    }

    private static class Node<T> {
        T item;
        Node<T> next;
        Node(T item) { this.item = item; }
    }
}
```

### ABA 문제

CAS의 고전적인 취약점입니다. 값이 A→B→A로 바뀌었지만 CAS는 현재값이 A인 것만 보고 "변경 없음"으로 판단하는 문제입니다. 단순 카운터에서는 무해하지만, 연결 리스트나 포인터 기반 자료구조에서는 심각한 버그를 유발합니다.

<div class="mermaid">
sequenceDiagram
  participant T1 as "스레드 1"
  participant MEM as "메모리"
  participant T2 as "스레드 2"
  T1->>MEM: "1. 값 읽기: A"
  T2->>MEM: "2. A → B 변경"
  T2->>MEM: "3. B → A 재변경"
  T1->>MEM: "4. CAS(A, newVal) — 값이 A이므로 성공!"
  Note over T1,MEM: "T1은 변경이 없었다고 착각\n실제로는 A→B→A로 두 번 변경됨"
</div>

**해결책: `AtomicStampedReference`** (버전 번호 추가)

```java
AtomicStampedReference<String> stampedRef =
        new AtomicStampedReference<>("A", 0);

// 읽기
int[] stampHolder = new int[1];
String value = stampedRef.get(stampHolder); // value="A", stamp=0

// CAS: 값과 스탬프 모두 일치해야 성공
boolean success = stampedRef.compareAndSet(
        "A", "B",   // 예상값, 새값
        0, 1        // 예상 스탬프, 새 스탬프
);
// 스탬프가 달라지므로 ABA 후에도 CAS 실패 → ABA 문제 해결
```

### LongAdder vs AtomicLong (고경합 환경)

<div class="mermaid">
graph LR
  subgraph AL["AtomicLong: 단일 셀 (모든 스레드 경쟁)"]
    CELL["count"]
    TA[Thread A] --> CELL
    TB[Thread B] --> CELL
    TC[Thread C] --> CELL
  end
  subgraph LA["LongAdder: Cell Striping (스레드별 다른 셀)"]
    C1["3"]
    C2["7"]
    C3["2"]
    C4["5"]
    T1[Thread1] --> C1
    T2[Thread2] --> C2
    T3[Thread3] --> C3
    T4[Thread4] --> C4
    C1 & C2 & C3 & C4 -->|"sum() = 17"| SUM["합계"]
  end
</div>

```java
LongAdder adder = new LongAdder();
adder.increment();          // +1
adder.add(5);               // +5
long total = adder.sum();   // 합산 (정확한 snapshot이 아닐 수 있음)
long reset = adder.sumThenReset(); // 합산 후 0으로 리셋

// 언제 무엇을 쓸까?
// AtomicLong: 경합 낮음, compareAndSet이 필요, 단일 최신값이 중요
// LongAdder:  경합 높음, 누적 카운터/통계, sum()의 일시적 부정확 허용 가능
```

---

## 7. 동시성 컬렉션

### ConcurrentHashMap 내부 구조 (Java 8)

Java 8의 `ConcurrentHashMap`은 세그먼트 락(Java 7 방식)을 버리고 **CAS + 버킷 단위 synchronized**를 사용합니다. 이 설계가 중요한 이유는 락의 범위가 버킷 하나로 좁혀지기 때문입니다. 16개 버킷이 있다면 최대 16개의 스레드가 서로 다른 버킷에 동시에 쓸 수 있습니다. Java 7의 세그먼트 락(기본 16개 세그먼트)에 비해 훨씬 세밀한 동시성 제어가 가능합니다.

> **비유로 이해하기**: Java 7 ConcurrentHashMap은 도서관을 16개 구역으로 나눠 각 구역마다 사서 한 명이 관리하는 구조였습니다. Java 8은 책 한 권(버킷 하나)마다 독립적인 잠금장치를 달아, 특정 책을 빌리는 동안 다른 책에는 전혀 영향을 주지 않도록 개선한 것입니다.

<div class="mermaid">
graph TD
  subgraph "ConcurrentHashMap 버킷 배열 (Node[] table)"
    B0["버킷 0\n비어있음\n→ CAS로 삽입"]
    B1["버킷 1\n노드 존재\n→ synchronized(버킷)"]
    B2["버킷 2\n비어있음\n→ CAS로 삽입"]
    B3["버킷 3\n8개 이상 충돌\n→ TreeNode(Red-Black Tree)"]
  end
  T1["스레드 A\nput(k1)"] -->|"1. CAS 시도"| B0
  T2["스레드 B\nput(k2)"] -->|"1. synchronized"| B1
  T3["스레드 C\nput(k3)"] -->|"1. CAS 시도"| B2
  NOTE["서로 다른 버킷 → 완전 병렬\n같은 버킷 → 버킷 단위 락"]
</div>

```java
ConcurrentHashMap<String, Integer> map = new ConcurrentHashMap<>();

// 기본 put/get은 스레드 안전
map.put("key", 1);
map.get("key");

// 원자적 연산
map.putIfAbsent("key", 2);     // 없을 때만 삽입
map.remove("key", 1);          // 값이 1일 때만 제거
map.replace("key", 1, 2);      // 1일 때만 2로 변경

// Java 8 compute 메서드들
map.compute("key", (k, v) ->
        v == null ? 1 : v + 1); // 없으면 1, 있으면 +1 (원자적)

map.merge("key", 1, Integer::sum); // 없으면 1, 있으면 합산 (원자적)

// 대량 작업 (Java 8+, 병렬 처리)
map.forEach(2, (k, v) ->
        System.out.println(k + "=" + v)); // 병렬 임계값 = 2

long count = map.reduceValues(2, v -> v.longValue(),
        Long::sum); // 값 합산

// 주의: size()는 정확하지 않을 수 있음 (추정값)
// 정확한 크기가 필요하면 mappingCount() 사용 (long 반환)
```

### CopyOnWriteArrayList

쓰기 시 전체 배열을 복사합니다. **읽기가 압도적으로 많고 쓰기가 드문** 경우에 적합합니다.

```java
CopyOnWriteArrayList<String> list = new CopyOnWriteArrayList<>();

// 쓰기: 내부 배열 전체 복사 후 추가 → 비용 큼
list.add("a");
list.set(0, "b");

// 읽기: 스냅샷 기반 → 락 없음, 매우 빠름
// iterator는 생성 시점의 스냅샷을 순회 → iterator 중 수정 가능
Iterator<String> it = list.iterator();
list.add("c"); // iterator에 영향 없음 (다른 배열 참조)

// 언제 사용?
// - 이벤트 리스너 목록
// - 구독자 목록
// - 설정 목록 (읽기 많음, 쓰기 드묾)
```

### BlockingQueue

생산자-소비자 패턴의 핵심입니다.

<div class="mermaid">
graph LR
  P([생산자]) -->|"put() - 큐 꽉 참 시 블로킹"| BQ["BlockingQueue\n작업 대기열"]
  BQ -->|"take() - 큐 비어있으면 블로킹"| C([소비자])
</div>

| 구현 클래스 | 특징 |
|------------|------|
| `ArrayBlockingQueue` | 배열 기반, 유계, 공정 옵션 |
| `LinkedBlockingQueue` | 연결 리스트 기반, 선택적 유계, 처리량 높음 |
| `SynchronousQueue` | 큐 크기 0, 직접 핸드오프 (생산자와 소비자 직접 연결) |
| `PriorityBlockingQueue` | 우선순위 기반, 무계 |
| `DelayQueue` | 지연 시간 후 꺼낼 수 있는 큐 |

**생산자-소비자 패턴:**

```java
import java.util.concurrent.*;

public class WorkQueue {
    private static final int CAPACITY = 100;
    private final BlockingQueue<Runnable> queue =
            new ArrayBlockingQueue<>(CAPACITY);

    // 생산자 스레드
    public void submit(Runnable task) throws InterruptedException {
        queue.put(task); // 큐 가득 차면 공간 생길 때까지 블로킹
        // offer(task, 1, TimeUnit.SECONDS): 타임아웃 버전
    }

    // 소비자 스레드
    public void startWorker() {
        new Thread(() -> {
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    Runnable task = queue.take(); // 큐 비어있으면 블로킹
                    task.run();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }, "worker").start();
    }
}
```

---

## 8. CompletableFuture 딥다이브

### 비동기 체이닝

```java
// 기본 생성 방법
CompletableFuture<Void> cf1 = CompletableFuture.runAsync(() -> {
    // 결과 없는 비동기 작업
});

CompletableFuture<String> cf2 = CompletableFuture.supplyAsync(() -> {
    return "결과값"; // 결과 있는 비동기 작업
});

// thenApply: 이전 결과를 변환 (Function<T,R>), 동일 스레드에서 실행
CompletableFuture<Integer> cf3 = cf2.thenApply(String::length);

// thenApplyAsync: 별도 스레드에서 변환
CompletableFuture<Integer> cf4 = cf2.thenApplyAsync(String::length);

// thenCompose: 결과로 새 CompletableFuture 생성 (flatMap과 유사)
CompletableFuture<String> userCf = CompletableFuture
        .supplyAsync(() -> fetchUserId())           // Long 반환
        .thenCompose(id -> fetchUserName(id));      // Long → CF<String>

// thenCombine: 두 CompletableFuture 결과를 합산
CompletableFuture<String> name = CompletableFuture.supplyAsync(() -> "Kim");
CompletableFuture<Integer> age = CompletableFuture.supplyAsync(() -> 30);

CompletableFuture<String> combined = name.thenCombine(age,
        (n, a) -> n + "(" + a + ")"); // "Kim(30)"

// thenAccept: 결과를 소비 (Consumer), 반환값 없음
cf2.thenAccept(result -> System.out.println("결과: " + result));

// thenRun: 이전 결과 무관하게 실행 (Runnable)
cf2.thenRun(() -> System.out.println("완료 후 실행"));
```

### 예외 처리

```java
CompletableFuture<String> cf = CompletableFuture
        .supplyAsync(() -> {
            if (Math.random() < 0.5) throw new RuntimeException("랜덤 실패");
            return "성공";
        })
        // exceptionally: 예외 발생 시 기본값 제공 (Function<Throwable, T>)
        .exceptionally(ex -> {
            System.out.println("예외 처리: " + ex.getMessage());
            return "기본값";
        });

// handle: 성공/실패 모두 처리 (BiFunction<T, Throwable, R>)
CompletableFuture<String> cf2 = CompletableFuture
        .supplyAsync(() -> "데이터")
        .handle((result, ex) -> {
            if (ex != null) {
                return "에러: " + ex.getMessage();
            }
            return "OK: " + result;
        });

// whenComplete: 결과/예외 소비, 값은 변환하지 않음
CompletableFuture<String> cf3 = CompletableFuture
        .supplyAsync(() -> "데이터")
        .whenComplete((result, ex) -> {
            // 로깅, 메트릭 수집 등 사이드 이펙트
            if (ex != null) log.error("실패", ex);
            else log.info("성공: {}", result);
        });
```

### allOf / anyOf

```java
CompletableFuture<String> cf1 = CompletableFuture.supplyAsync(() -> {
    sleep(1000); return "서비스A";
});
CompletableFuture<String> cf2 = CompletableFuture.supplyAsync(() -> {
    sleep(2000); return "서비스B";
});
CompletableFuture<String> cf3 = CompletableFuture.supplyAsync(() -> {
    sleep(500); return "서비스C";
});

// allOf: 모든 CF 완료 대기 (결과는 직접 get() 필요)
CompletableFuture<Void> all = CompletableFuture.allOf(cf1, cf2, cf3);
all.join(); // 2초 후 완료
String r1 = cf1.join(); // 이미 완료됨
String r2 = cf2.join();
String r3 = cf3.join();

// 결과를 리스트로 수집하는 패턴
List<CompletableFuture<String>> futures = List.of(cf1, cf2, cf3);
CompletableFuture<List<String>> allResults = CompletableFuture
        .allOf(futures.toArray(new CompletableFuture[0]))
        .thenApply(v -> futures.stream()
                .map(CompletableFuture::join)
                .collect(Collectors.toList()));

// anyOf: 가장 먼저 완료된 CF 반환 (0.5초 후 "서비스C" 반환)
CompletableFuture<Object> any = CompletableFuture.anyOf(cf1, cf2, cf3);
Object first = any.join(); // "서비스C"
```

### 커스텀 Executor 설정

```java
// I/O 작업용 스레드 풀
ExecutorService ioExecutor = new ThreadPoolExecutor(
        20, 100, 60L, TimeUnit.SECONDS,
        new LinkedBlockingQueue<>(1000),
        r -> new Thread(r, "io-worker"),
        new ThreadPoolExecutor.CallerRunsPolicy()
);

// 계산 작업용 스레드 풀
ExecutorService cpuExecutor = new ThreadPoolExecutor(
        Runtime.getRuntime().availableProcessors(),
        Runtime.getRuntime().availableProcessors(),
        0L, TimeUnit.SECONDS,
        new LinkedBlockingQueue<>(500)
);

// 실무 패턴: 외부 API 병렬 호출
List<Long> userIds = List.of(1L, 2L, 3L, 4L, 5L);

List<CompletableFuture<UserInfo>> futures = userIds.stream()
        .map(id -> CompletableFuture
                .supplyAsync(() -> callExternalApi(id), ioExecutor)
                .orTimeout(5, TimeUnit.SECONDS) // Java 9+
                .exceptionally(ex -> UserInfo.empty(id)))
        .collect(Collectors.toList());

List<UserInfo> results = futures.stream()
        .map(CompletableFuture::join)
        .collect(Collectors.toList());
```

---

## 9. Virtual Thread (Java 21+)

### Platform Thread vs Virtual Thread

```
Platform Thread (Java 21 이전):
  Java Thread → OS Kernel Thread → CPU 코어
  생성 비용: ~1MB 스택 메모리
  최대 수천 개 실용적

Virtual Thread (Java 21+):
  Virtual Thread → Carrier Thread (Platform Thread) → CPU 코어
  생성 비용: ~수 KB (힙 메모리)
  수백만 개 생성 가능
```

### 왜 필요한가? (C10K 문제)

기존 Platform Thread 방식에서 동시에 10,000개의 요청을 처리하려면 10,000개의 OS 스레드가 필요합니다. 각 스레드는 최소 1MB의 스택 메모리를 가지므로 **10GB**의 메모리가 필요합니다.

게다가 대부분의 요청은 DB 쿼리, HTTP 호출 등 **I/O 대기** 시간이 대부분입니다. OS 스레드가 I/O 대기 중에는 CPU를 사용하지 않지만 메모리를 점유하는 비효율이 발생합니다.

### 동작 원리 (캐리어 스레드 + 마운트/언마운트)

<div class="mermaid">
sequenceDiagram
  participant VT1 as VT1 (Virtual Thread)
  participant CT as Carrier Thread
  participant VT2 as VT2 (Virtual Thread)

  VT1->>CT: 마운트 & 실행
  VT1->>CT: I/O 대기 시작 → 언마운트 (힙에 상태 저장)
  CT->>VT2: VT2 마운트 & 실행
  Note over VT1: I/O 완료 → 스케줄링 대기열 재등록
  CT->>VT2: VT2 언마운트
  CT->>VT1: VT1 마운트 & 재개
</div>

### 사용법과 마이그레이션 가이드

```java
// 1. 직접 생성
Thread vThread = Thread.ofVirtual()
        .name("vt-", 0) // vt-0, vt-1, ...
        .start(() -> {
            System.out.println("Virtual Thread: "
                    + Thread.currentThread().isVirtual()); // true
        });

// 2. Factory로 생성
ThreadFactory factory = Thread.ofVirtual().factory();
Thread vt = factory.newThread(() -> System.out.println("VT"));

// 3. ExecutorService (가장 실용적)
try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
    // 요청마다 새 Virtual Thread 생성 (비용 매우 저렴)
    List<Future<String>> futures = new ArrayList<>();
    for (int i = 0; i < 10_000; i++) {
        final int id = i;
        futures.add(executor.submit(() -> processRequest(id)));
    }
    for (Future<String> f : futures) {
        System.out.println(f.get());
    }
} // try-with-resources: 자동 shutdown + awaitTermination

// 4. 스레드 속성 확인
Thread.currentThread().isVirtual(); // Virtual Thread 여부
```

**마이그레이션 체크리스트:**

```java
// 기존 코드 (Platform Thread 풀)
ExecutorService old = Executors.newFixedThreadPool(200);

// Virtual Thread로 마이그레이션
ExecutorService newExec = Executors.newVirtualThreadPerTaskExecutor();
// 스레드 풀 크기 제한 불필요: VT는 I/O 대기 중 Carrier 반환

// Spring Boot 3.2+ 설정
// application.properties:
// spring.threads.virtual.enabled=true
```

### synchronized 피닝(Pinning) 문제

Virtual Thread가 `synchronized` 블록 안에서 I/O 대기 시, Carrier Thread에서 **언마운트되지 못하고 고정(pinned)**됩니다.

```java
// 문제: synchronized 내부에서 블로킹 I/O → Carrier Thread 낭비
public synchronized String badMethod() {
    return httpClient.get(url); // 여기서 블로킹 → Carrier Thread 피닝!
}

// 해결책 1: ReentrantLock 사용 (피닝 없음)
private final ReentrantLock lock = new ReentrantLock();

public String goodMethod() {
    lock.lock();
    try {
        return httpClient.get(url); // VT 언마운트 가능
    } finally {
        lock.unlock();
    }
}

// 해결책 2: 블로킹 작업을 synchronized 외부로 이동
public String betterMethod() {
    String result = httpClient.get(url); // 블로킹 (VT 언마운트 가능)
    synchronized (this) {
        return processResult(result); // 빠른 CPU 작업만
    }
}

// 피닝 진단: JVM 플래그
// -Djdk.tracePinnedThreads=full
// → 피닝 발생 시 스택 트레이스 출력
```

**Virtual Thread 주의사항:**
- `ThreadLocal`: VT는 많이 생성되므로 무거운 ThreadLocal 값은 메모리 문제
- CPU Bound 작업: VT는 I/O Bound에 최적화, CPU Bound는 Platform Thread가 유리
- `synchronized` + 블로킹: 피닝 발생, `ReentrantLock`으로 교체

---

## 10. 데드락/라이브락/기아

### 데드락 조건 4가지

데드락은 다음 4가지 조건이 **모두** 충족될 때 발생합니다.

<div class="mermaid">
graph LR
  A([Thread A]) -->|"보유"| L1[락 1]
  A -->|"대기"| L2[락 2]
  B([Thread B]) -->|"보유"| L2
  B -->|"대기"| L1
</div>

**데드락 발생 예제:**

```java
public class DeadlockExample {
    private final Object lock1 = new Object();
    private final Object lock2 = new Object();

    // Thread A: lock1 획득 후 lock2 획득 시도
    public void methodA() {
        synchronized (lock1) {
            System.out.println("Thread A: lock1 획득");
            try { Thread.sleep(100); } catch (InterruptedException e) {}
            synchronized (lock2) { // Thread B가 lock2 보유 중 → 대기
                System.out.println("Thread A: lock2 획득");
            }
        }
    }

    // Thread B: lock2 획득 후 lock1 획득 시도
    public void methodB() {
        synchronized (lock2) {
            System.out.println("Thread B: lock2 획득");
            try { Thread.sleep(100); } catch (InterruptedException e) {}
            synchronized (lock1) { // Thread A가 lock1 보유 중 → 대기
                System.out.println("Thread B: lock1 획득"); // 영원히 미도달
            }
        }
    }
}
```

### 데드락 탐지

**jstack 사용:**
```bash
# PID 확인
jps -l

# 스레드 덤프 생성
jstack <PID>

# 출력 예시:
# Found one Java-level deadlock:
# =============================
# "Thread-A": waiting to lock monitor 0x00007f...
#   which is held by "Thread-B"
# "Thread-B": waiting to lock monitor 0x00007f...
#   which is held by "Thread-A"
```

**ThreadMXBean으로 프로그래밍적 탐지:**
```java
import java.lang.management.*;

ThreadMXBean mxBean = ManagementFactory.getThreadMXBean();

// 데드락 탐지 (synchronized만)
long[] deadlocked = mxBean.findMonitorDeadlockedThreads();

// 데드락 탐지 (synchronized + j.u.c 락)
long[] allDeadlocked = mxBean.findDeadlockedThreads();

if (allDeadlocked != null) {
    ThreadInfo[] infos = mxBean.getThreadInfo(allDeadlocked, true, true);
    for (ThreadInfo info : infos) {
        System.out.println("데드락 스레드: " + info.getThreadName());
        System.out.println("대기 중인 락: " + info.getLockName());
        System.out.println("락 보유자: " + info.getLockOwnerName());
    }
}
```

### 데드락 회피 전략

**전략 1: 락 순서 고정 (Lock Ordering)**

```java
// 항상 System.identityHashCode() 순서로 락 획득
public void safeTransfer(Account from, Account to, int amount) {
    int fromHash = System.identityHashCode(from);
    int toHash = System.identityHashCode(to);

    Object first = fromHash < toHash ? from : to;
    Object second = fromHash < toHash ? to : from;

    synchronized (first) {
        synchronized (second) {
            from.debit(amount);
            to.credit(amount);
        }
    }
}
```

**전략 2: tryLock 타임아웃 (Lock Timeout)**

```java
public boolean transferWithTimeout(Account from, Account to, int amount)
        throws InterruptedException {
    long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(1);

    while (true) {
        if (from.lock.tryLock()) {
            try {
                if (to.lock.tryLock()) {
                    try {
                        from.debit(amount);
                        to.credit(amount);
                        return true;
                    } finally {
                        to.lock.unlock();
                    }
                }
            } finally {
                from.lock.unlock();
            }
        }

        if (System.nanoTime() > deadline) {
            return false; // 타임아웃: 데드락 회피
        }

        Thread.sleep(ThreadLocalRandom.current().nextInt(10)); // 백오프
    }
}
```

### 라이브락 / 기아 상태

**라이브락(Livelock):** 스레드들이 서로 양보하다가 아무도 진행하지 못하는 상태. 데드락과 달리 스레드는 계속 동작 중.

```java
// 라이브락 예: 두 사람이 복도에서 같은 방향으로 비키는 상황
public class Livelock {
    volatile boolean moveLeft = true;

    public void person1() {
        while (true) {
            if (!moveLeft) { // 상대방이 왼쪽으로 갔으면
                System.out.println("Person1 통과");
                break;
            }
            System.out.println("Person1: 오른쪽으로 이동");
            moveLeft = false; // 오른쪽으로 이동
        }
    }

    public void person2() {
        while (true) {
            if (moveLeft) { // 상대방이 오른쪽으로 갔으면
                System.out.println("Person2 통과");
                break;
            }
            System.out.println("Person2: 왼쪽으로 이동");
            moveLeft = true; // 왼쪽으로 이동
            // 두 사람이 계속 같은 방향으로 비킴!
        }
    }
}
// 해결: 랜덤 백오프 또는 우선순위 부여
```

**기아(Starvation):** 특정 스레드가 오랫동안 또는 영원히 자원을 할당받지 못하는 상태.

```java
// 기아 발생 원인:
// 1. 비공정 락: 높은 우선순위 스레드가 계속 선점
// 2. synchronized: 락 대기 순서 보장 없음

// 해결: 공정 락 사용
ReentrantLock fairLock = new ReentrantLock(true); // fair=true
// 대기 순서대로 락 할당 (FIFO)

// 또는 스레드 우선순위 조정 (주의: OS 의존적)
Thread t = new Thread(task);
t.setPriority(Thread.MAX_PRIORITY); // 10 (비추천: 이식성 없음)
```

---

## 11. ThreadLocal

### 동작 원리 (Thread 내부 ThreadLocalMap)

각 `Thread` 객체는 내부에 `ThreadLocal.ThreadLocalMap`을 가집니다. `ThreadLocal`은 해당 맵의 키 역할을 합니다.

<div class="mermaid">
graph TD
  subgraph TA["Thread A"]
    subgraph MA["ThreadLocalMap"]
      KA1["threadLocalA (WeakRef)"] --> VA1["값: 사용자A"]
      KA2["threadLocalB (WeakRef)"] --> VA2["값: connectionA"]
    end
  end
  subgraph TB["Thread B"]
    subgraph MB["ThreadLocalMap"]
      KB1["threadLocalA (WeakRef)"] --> VB1["값: 사용자B"]
      KB2["threadLocalB (WeakRef)"] --> VB2["값: connectionB"]
    end
  end
  NOTE["동일한 ThreadLocal 객체지만 각 스레드에서 독립적인 값 유지"]
</div>

```java
// ThreadLocal 사용
public class UserContext {
    private static final ThreadLocal<String> currentUser =
            ThreadLocal.withInitial(() -> "anonymous");

    public static String getUser() {
        return currentUser.get();
    }

    public static void setUser(String user) {
        currentUser.set(user);
    }

    public static void clearUser() {
        currentUser.remove(); // 반드시 명시적으로 제거
    }
}

// 사용 예
UserContext.setUser("kim");
try {
    processRequest(); // 같은 스레드 내 어디서든 kim 반환
} finally {
    UserContext.clearUser(); // 스레드 풀 환경에서 필수!
}
```

### 메모리 누수 주의사항

ThreadLocal의 메모리 누수는 스레드 풀 환경에서 특히 위험합니다. 스레드 풀의 스레드는 재사용되므로 `remove()`를 호출하지 않으면 이전 요청의 데이터가 다음 요청에서 그대로 보입니다. 이는 메모리 누수뿐만 아니라 **보안 취약점**이 됩니다(다른 사용자의 인증 정보가 노출될 수 있음).

<div class="mermaid">
graph TD
  subgraph "ThreadLocalMap 엔트리 구조"
    KEY["KEY: WeakReference&lt;ThreadLocal&gt;"]
    VAL["VALUE: Object (강한 참조)"]
    KEY --- VAL
  end
  subgraph "누수 발생 시나리오"
    TL["ThreadLocal 변수 = null"]
    TL -->|"WeakRef → GC가 KEY 수거"| GC["KEY = null"]
    GC -->|"하지만 VALUE는 강한 참조"| LEAK["VALUE 메모리 누수!"]
  end
  subgraph "스레드 풀 보안 문제"
    REQ1["요청 1: userId=kim, set()"]
    POOL["스레드 재사용"]
    REQ2["요청 2: remove() 없으면 userId=kim 그대로 노출!"]
    REQ1 --> POOL --> REQ2
  end
</div>

스레드 풀에서의 올바른 패턴은 반드시 `try-finally`로 `remove()`를 보장하는 것입니다.

```java
// 올바른 사용 패턴 (서블릿 필터 예)
public class SecurityFilter implements Filter {
    private static final ThreadLocal<User> userHolder = new ThreadLocal<>();

    @Override
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain)
            throws IOException, ServletException {
        try {
            User user = authenticate(req); // 인증
            userHolder.set(user);          // 현재 스레드에 저장
            chain.doFilter(req, res);       // 다운스트림 처리
        } finally {
            userHolder.remove();           // 반드시 제거!
        }
    }

    public static User getCurrentUser() {
        return userHolder.get();
    }
}
```

### InheritableThreadLocal

부모 스레드의 값을 자식 스레드에 상속합니다.

```java
InheritableThreadLocal<String> itl = new InheritableThreadLocal<>();

itl.set("부모 값");

Thread child = new Thread(() -> {
    System.out.println(itl.get()); // "부모 값" 출력
    itl.set("자식 값");            // 자식에서 변경해도 부모에 영향 없음
});
child.start();

// 주의: 스레드 풀에서는 스레드 생성 시점에만 상속 → 이후 재사용 시 부모 값 반영 안 됨
// 해결: Transmittable ThreadLocal (TTL) 라이브러리 사용
```

### 실무 활용 (MDC, SecurityContext, 트랜잭션)

**SLF4J MDC (Mapped Diagnostic Context):**
```java
// 요청마다 고유 ID를 로그에 자동 포함
MDC.put("requestId", UUID.randomUUID().toString());
MDC.put("userId", currentUser.getId());

try {
    log.info("서비스 시작"); // [requestId=abc123, userId=kim] 서비스 시작
    doService();
} finally {
    MDC.clear(); // 내부적으로 ThreadLocal 사용
}

// logback.xml 설정
// <pattern>%d [%X{requestId}] [%X{userId}] %-5level %msg%n</pattern>
```

**Spring Security - SecurityContextHolder:**
```java
// Spring Security는 SecurityContext를 ThreadLocal에 저장
Authentication auth = SecurityContextHolder.getContext().getAuthentication();
String username = auth.getName();

// Virtual Thread 사용 시: ThreadLocal → ScopedValue 고려 필요
// Spring Security 6.x: 자동으로 Virtual Thread 대응
```

**Spring Transaction - TransactionSynchronizationManager:**
```java
// Spring은 현재 트랜잭션 정보를 ThreadLocal에 저장
// @Transactional이 동작하는 원리
boolean hasTransaction = TransactionSynchronizationManager
        .isActualTransactionActive();

// 같은 스레드 내에서만 트랜잭션 전파 가능한 이유
// → 다른 스레드는 다른 ThreadLocal → 다른 커넥션/트랜잭션
```

---

## 실무에서 자주 하는 실수

**실수 1: run()을 직접 호출해 단일 스레드로 실행**

```java
// 잘못된 코드 — 새 스레드가 생성되지 않고 현재 스레드에서 실행됨
Thread t = new Thread(() -> System.out.println("작업"));
t.run(); // 새 스레드 없이 현재 스레드에서 실행!

// 올바른 코드
t.start(); // OS에게 새 스레드 생성 요청
```

`run()`은 단순히 `Runnable`의 메서드를 호출하는 것이고, `start()`가 OS에 커널 스레드 생성을 요청합니다. `run()`을 직접 호출하면 병렬 실행이 전혀 일어나지 않고 모든 작업이 순차적으로 실행됩니다.

**실수 2: synchronized 없이 공유 변수 접근**

```java
// 위험한 코드 — 결과가 1000이 아닐 수 있음
int count = 0;
List<Thread> threads = new ArrayList<>();
for (int i = 0; i < 1000; i++) {
    threads.add(new Thread(() -> count++)); // count++은 원자적 연산이 아님!
}
threads.forEach(Thread::start);
threads.forEach(t -> { try { t.join(); } catch (InterruptedException e) {} });
System.out.println(count); // 1000보다 작은 값이 출력될 수 있음

// 올바른 코드
AtomicInteger count = new AtomicInteger(0);
// 또는 synchronized 사용
```

`count++`은 읽기-수정-쓰기의 세 단계 연산입니다. 여러 스레드가 동시에 읽기 단계를 수행하면 같은 값을 두 번 증가시키는 경쟁 조건(race condition)이 발생합니다.

**실수 3: Executors 팩토리의 무제한 큐/스레드 사용**

```java
// 위험! — 큐 크기가 Integer.MAX_VALUE로 무제한
ExecutorService executor = Executors.newFixedThreadPool(10);
// 작업이 계속 쌓이면 OutOfMemoryError 발생

// 올바른 코드 — 명시적 유계 큐 설정
ExecutorService executor = new ThreadPoolExecutor(
    10, 20, 60L, TimeUnit.SECONDS,
    new LinkedBlockingQueue<>(1000), // 최대 1000개
    new ThreadPoolExecutor.CallerRunsPolicy() // 꽉 차면 호출자 스레드가 직접 실행
);
```

**실수 4: InterruptedException 무시**

```java
// 잘못된 코드 — 인터럽트 신호 소멸
try {
    Thread.sleep(1000);
} catch (InterruptedException e) {
    // 아무것도 하지 않음 → 인터럽트 플래그가 사라짐
}

// 올바른 코드 1 — 인터럽트 플래그 복원
try {
    Thread.sleep(1000);
} catch (InterruptedException e) {
    Thread.currentThread().interrupt(); // 반드시 복원
    return; // 또는 적절한 종료 처리
}

// 올바른 코드 2 — 예외를 상위로 전파
public void task() throws InterruptedException {
    Thread.sleep(1000);
}
```

`InterruptedException`을 catch하면 인터럽트 플래그가 지워집니다. 복원하지 않으면 스레드 종료 요청을 감지하지 못해 스레드 풀 종료 시 무한 대기가 발생할 수 있습니다.

**실수 5: synchronized와 ReentrantLock 혼용으로 데드락**

```java
// 위험한 코드 — synchronized와 ReentrantLock은 서로 모름
Object syncLock = new Object();
ReentrantLock reentrantLock = new ReentrantLock();

// Thread A
synchronized (syncLock) {
    reentrantLock.lock(); // 데드락 가능
}

// Thread B
reentrantLock.lock();
synchronized (syncLock) { // 데드락 가능
}

// 올바른 코드 — 프로젝트에서 하나만 선택해 일관되게 사용
```

---

## 극한 시나리오: 트래픽 규모별 동시성 전략

### 100 TPS (소규모 서비스)

단일 서버에서 `synchronized` 또는 `ReentrantLock`으로 충분합니다. 동시 요청이 적으므로 락 경쟁이 거의 없어 성능 문제가 발생하지 않습니다. 코드 단순성을 우선시하세요.

```java
// 100 TPS: 단순 synchronized로 충분
public class OrderService {
    private int pendingCount = 0;

    public synchronized void addOrder(Order order) {
        pendingCount++;
        // 처리 로직
    }
}
```

### 10,000 TPS (중규모 서비스)

락 경쟁이 시작되고 `synchronized`의 성능 한계가 보입니다. 읽기/쓰기 비율을 분석해 `ReadWriteLock` 또는 `StampedLock`을 도입하고, 카운터는 `LongAdder`로 교체하며, `ConcurrentHashMap`의 원자적 연산(`compute`, `merge`)을 활용해야 합니다.

```java
// 10K TPS: 읽기 많은 캐시에 StampedLock 적용
public class ProductCache {
    private final StampedLock lock = new StampedLock();
    private final Map<Long, Product> cache = new HashMap<>();

    public Product get(Long id) {
        long stamp = lock.tryOptimisticRead(); // 낙관적 읽기: 락 없음
        Product p = cache.get(id);
        if (!lock.validate(stamp)) { // 쓰기 발생 여부 확인
            stamp = lock.readLock();
            try { p = cache.get(id); }
            finally { lock.unlockRead(stamp); }
        }
        return p;
    }
}

// 고경합 카운터: LongAdder가 AtomicLong보다 3~10배 빠름
LongAdder requestCount = new LongAdder();
requestCount.increment(); // 스레드별 독립 셀에 기록
long total = requestCount.sum(); // 집계
```

### 100,000 TPS (대규모 서비스)

이 규모에서는 단일 JVM의 락 기반 동기화가 병목이 됩니다. lock-free 알고리즘, Virtual Thread, 그리고 비동기 처리가 필수입니다.

```java
// 100K TPS: Virtual Thread + 비동기 파이프라인
// Spring Boot 3.2+ application.properties:
// spring.threads.virtual.enabled=true

// 직접 구현 시 Virtual Thread per request
try (ExecutorService exec = Executors.newVirtualThreadPerTaskExecutor()) {
    List<Future<Response>> futures = requests.stream()
        .map(req -> exec.submit(() -> processRequest(req)))
        .collect(Collectors.toList());
    // I/O 대기 중 Virtual Thread가 Carrier 해제 → OS 스레드 낭비 없음
}

// lock-free 자료구조로 공유 상태 최소화
ConcurrentHashMap<String, LongAdder> metrics = new ConcurrentHashMap<>();
metrics.computeIfAbsent("api.calls", k -> new LongAdder()).increment();

// 핵심 원칙: 공유 가변 상태를 최소화하고, 공유가 불가피하면 lock-free 연산 사용
```

100K TPS 이상에서는 단일 JVM의 한계를 넘어 **메시지 큐(Kafka, RabbitMQ)** 와 **분산 캐시(Redis)** 로 상태를 외부화하는 아키텍처가 필요합니다.

---

## 정리

Java 스레드와 동시성 프로그래밍의 핵심을 표로 정리합니다.

| 목적 | 권장 도구 |
|------|----------|
| 단순 비동기 작업 | `CompletableFuture.supplyAsync()` |
| 결과 반환 비동기 | `ExecutorService.submit(Callable)` |
| 상호 배제 | `synchronized` 또는 `ReentrantLock` |
| 읽기 많은 캐시 | `ReadWriteLock` 또는 `StampedLock` |
| 원자적 카운터 | `AtomicInteger` / `LongAdder` (고경합) |
| 스레드 안전 Map | `ConcurrentHashMap` |
| 생산자-소비자 | `BlockingQueue` (LinkedBlocking/ArrayBlocking) |
| 일회성 대기 | `CountDownLatch` |
| 반복 동기화 | `CyclicBarrier` |
| 접근 수 제한 | `Semaphore` |
| 스레드별 상태 | `ThreadLocal` (반드시 remove()) |
| 대규모 I/O 처리 | `Virtual Thread` (Java 21+) |
| 분할 정복 병렬화 | `ForkJoinPool` + `RecursiveTask` |

동시성 프로그래밍의 황금률: **공유 가변 상태를 최소화하라.** 공유가 필요하다면 불변 객체, 동시성 컬렉션, 적절한 동기화 도구를 사용하고, 반드시 리소스를 올바르게 해제하세요.
