---
title: "Java 가비지 컬렉터(GC)"
categories:
- JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

API 응답이 평소엔 10ms인데 가끔 500ms로 튄다. GC 로그를 보면 Stop-the-World가 발생한 시점과 정확히 일치한다. GC 동작 원리를 모르면 튜닝 방향을 잡을 수 없다.

> **비유로 먼저 이해하기**: GC는 쓰레기 수거 트럭과 같다. 아무도 참조하지 않는 객체(버려진 쓰레기)를 주기적으로 찾아 메모리(거리)를 치운다. 트럭이 수거하는 동안 일부 도로가 막히는 것(Stop-the-World)이 성능에 영향을 준다.

Java GC의 동작 원리부터 GC 종류별 아키텍처, 튜닝 옵션, 실무 선택 가이드까지 완전히 정리합니다.

---

## 1. GC란? 왜 필요한가?

Garbage Collection(GC)은 프로그램이 동적으로 할당한 메모리 중 더 이상 사용하지 않는 객체를 자동으로 탐지하고 회수하는 메커니즘입니다.

### 수동 메모리 관리의 문제

C/C++처럼 프로그래머가 직접 메모리를 해제하면 두 가지 치명적 버그가 발생합니다.

```mermaid
graph TD
    ML["메모리 누수 (Memory Leak)\nptr = malloc(100)\nfree(ptr) 깜빡 → 메모리 반환 안 됨 → 힙 고갈"]
    DP["댕글링 포인터 (Dangling Pointer)\nptr = malloc(100)\nfree(ptr)\n*ptr = 42 → 해제된 메모리 접근 → 정의되지 않은 동작"]
```

Java는 GC가 객체 회수를 책임지므로 개발자는 비즈니스 로직에만 집중할 수 있습니다. 단, GC가 동작하는 동안 발생하는 **Stop-the-World(STW)** 일시 정지가 애플리케이션 응답성에 영향을 미칩니다.

---

## 2. JVM 메모리 구조

### 전체 메모리 영역

```mermaid
graph TD
  subgraph JVM["JVM 메모리"]
    subgraph Heap
      subgraph Young["Young Generation"]
        Eden
        S0["Survivor S0"]
        S1["Survivor S1"]
      end
      subgraph Old["Old Generation (Tenured Space)"]
        OLD["오래 살아남은 객체들"]
      end
    end
    subgraph Meta["Metaspace (Native Memory)"]
      M1["클래스 메타데이터"]
      M2["메서드 정보"]
      M3["static 변수"]
    end
    subgraph Stacks["Stack (스레드별)"]
      ST1["T1 Stack"]
      ST2["T2 Stack"]
      ST3["T3 Stack"]
    end
  end
```

### 각 영역 설명

| 영역 | 위치 | 내용 | GC 대상 |
|------|------|------|---------|
| Eden | Heap/Young | 새로 생성된 객체 | Minor GC |
| Survivor S0/S1 | Heap/Young | Eden에서 살아남은 객체 | Minor GC |
| Old (Tenured) | Heap/Old | 오래 살아남은 객체 | Major/Full GC |
| Metaspace | Native Memory | 클래스 메타데이터 | Full GC |
| Stack | Thread별 | 지역 변수, 스택 프레임 | GC 대상 아님 |
| Code Cache | Native Memory | JIT 컴파일된 코드 | GC 대상 아님 |

### Metaspace (Java 8+)

Java 7까지는 클래스 정보를 Heap 내의 **PermGen(Permanent Generation)**에 저장했습니다. PermGen은 크기가 고정되어 있어 클래스가 많으면 `OutOfMemoryError: PermGen space` 오류가 자주 발생했습니다.

Java 8부터 PermGen을 폐지하고 **Metaspace**로 대체했습니다. Metaspace는 Native 메모리를 사용하며 필요에 따라 자동으로 확장됩니다.

```bash
# Metaspace 크기 제한 설정 (설정 없으면 무제한 확장)
-XX:MetaspaceSize=256m
-XX:MaxMetaspaceSize=512m
```

---

## 3. GC 기본 알고리즘

### Mark-and-Sweep

GC의 가장 기본적인 알고리즘입니다. 두 단계로 동작합니다.

```mermaid
graph TD
    subgraph "GC Root"
        ROOT["Stack 지역 변수 / static 변수 / JNI 참조"]
    end
    subgraph "Before Mark"
        A1["A"] --> B1["B"] --> C1["C"]
        D1["D"] --> E1["E"]
        F1["F"]
        G1["G"] --> H1["H"]
        ROOT --> A1
    end
    subgraph "After Mark (살아있는 객체: A, B, C)"
        A2["A*"] --> B2["B*"] --> C2["C*"]
        D2["D (미표시)"]
        E2["E (미표시)"]
        F2["F (미표시)"]
    end
    subgraph "After Sweep"
        A3["A*"] --> B3["B*"] --> C3["C*"]
        DEL1["해제"]
        DEL2["해제"]
        DEL3["해제"]
    end
```

**단점**: Sweep 후 메모리 단편화(Fragmentation) 발생. 큰 객체 할당 실패 가능.

### Mark-and-Compact

Mark-and-Sweep에 압축(Compact) 단계를 추가합니다.

```mermaid
graph LR
    subgraph "After Compact"
        U1["A*"] --- U2["B*"] --- U3["C*"] --- F1["빈"] --- F2["빈"] --- F3["빈"] --- F4["빈"] --- F5["빈"]
    end
    PRO["장점: 단편화 없음, 연속 메모리 할당 가능"]
    CON["단점: 객체 이동 → 참조 주소 갱신 필요 → STW 시간 길어짐"]
```

### Copying (복사 알고리즘)

메모리를 두 영역으로 나누어 사용 중인 절반의 살아있는 객체를 다른 절반으로 복사합니다.

```mermaid
graph TD
    subgraph "복사 전"
        FROM1["From Space: A* | B(가비지) | C* | D(가비지) | E*"]
        TO1["To Space:   (비어 있음)"]
    end
    subgraph "복사 후"
        FROM2["From Space: (전체 비움)"]
        TO2["To Space:   A* | C* | E* | (빈) | (빈)  ← 압축됨"]
    end
    FROM1 -->|"살아있는 객체만 복사"| TO2
```

**장점**: 단편화 없음, 할당 속도 빠름(포인터 하나만 이동).
**단점**: 메모리 절반만 사용 가능.
Young Generation의 Eden ↔ Survivor 복사에 이 방식을 사용합니다.

### Reference Counting (Java 미사용)

각 객체에 참조 횟수를 저장하고 0이 되면 즉시 해제합니다. Python, Swift 등에서 사용하지만 Java는 채택하지 않았습니다.

```mermaid
graph LR
    A["A (count=1)"] --> B["B (count=1)"] --> C["C (count=1)"] --> A
    NOTE["외부 참조 없음에도 각 카운트 ≥ 1\n→ 영원히 해제 불가 (순환 참조)"]
```

---

## 4. Generational GC 가설 — 약한 세대 가설

### 핵심 가설

**"대부분의 객체는 생성 직후 금방 죽는다(짧은 수명을 가진다)."**

실제 프로그램에서 객체 생존 패턴을 분석하면 다음 분포를 보입니다.

```mermaid
graph LR
    subgraph "객체 수명 분포 (Weak Generational Hypothesis)"
        S["짧은 수명<br>(대다수 객체)"] -->|"수명 증가 → 객체 수 급감"| L["긴 수명<br>(소수 객체)"]
    end
    N1["대부분의 객체는 생성 직후 회수됨"]
    N2["살아남은 객체는 오래 생존하는 경향"]
```

이 가설을 바탕으로 메모리를 **Young Generation**과 **Old Generation**으로 분리합니다.

### Young Generation 구조

```mermaid
graph LR
    subgraph "Young Generation"
        Eden["Eden (전체의 약 80%)\n새 객체 할당\n빠른 TLAB 할당"]
        S0["S0 (Survivor From)\n약 10%"]
        S1["S1 (Survivor To)\n약 10%"]
    end
    TLAB["TLAB: Thread-Local Allocation Buffer\n각 스레드가 Eden의 일부를 독점 사용\n→ 동기화 없이 빠른 할당"]
    Eden --> S0
    S0 --> S1
```

### Minor GC vs Major GC vs Full GC

```mermaid
graph TD
    MinorGC["Minor GC (Young GC)\n트리거: Eden 영역이 가득 찼을 때\n대상: Young Generation만\nSTW: 짧음 (수 ms ~ 수십 ms)\n빈도: 자주 발생"]
    MajorGC["Major GC (Old GC)\n트리거: Old Generation이 가득 찼을 때\n대상: Old Generation\nSTW: Minor GC보다 길음\n빈도: 드물게 발생"]
    FullGC["Full GC\n트리거: 힙 전체 부족, System.gc(), Metaspace 부족\n대상: Young + Old + Metaspace\nSTW: 가장 김 (수백 ms ~ 수 초)\n빈도: 가능한 한 피해야 함"]

    MinorGC -->|"STW 짧음"| MajorGC
    MajorGC -->|"STW 더 김"| FullGC
```

### 객체 승격(Promotion) 과정

```mermaid
sequenceDiagram
    participant Eden
    participant S0 as Survivor S0
    participant S1 as Survivor S1
    participant Old as Old Generation

    Note over Eden: 1단계: 새 객체 할당 (A,B,C,D,E)
    Eden->>S0: 2단계: Minor GC - 살아있는 객체(A,C,E) 복사 (age=1)
    Note over Eden: Eden 전체 비움
    S0->>S1: 3단계: 다음 Minor GC - 살아있는 객체(A,E) 복사 (age=2)
    Note over S0: B,C 등 죽은 객체 회수
    S1->>Old: 4단계: age >= MaxTenuringThreshold(15) 도달 시 승격(Promote)
    Note over Old: 장수 객체들 보관
```

---

## 5. GC 종류별 상세 설명

### Serial GC

단일 스레드로 GC를 수행합니다. GC 동안 애플리케이션 스레드가 모두 멈춥니다.

```mermaid
gantt
    title Serial GC 동작 (단일 GC 스레드)
    dateFormat X
    axisFormat %s

    section App Thread 1
    실행중 : 0, 10
    STW(GC) : crit, 10, 16
    실행중 : 16, 26

    section App Thread 2
    실행중 : 0, 10
    STW(GC) : crit, 10, 16
    실행중 : 16, 26

    section App Thread 3
    실행중 : 0, 10
    STW(GC) : crit, 10, 16
    실행중 : 16, 26

    section GC Thread
    Mark→Sweep→Compact : active, 10, 16
```

```bash
# Serial GC 활성화
-XX:+UseSerialGC
```

| 항목 | 내용 |
|------|------|
| 적합 환경 | 단일 코어, 소규모 힙(~수백 MB), 클라이언트 앱 |
| 일시 정지 | 길음 |
| 처리량 | 낮음 |
| 메모리 오버헤드 | 최소 |

### Parallel GC (Throughput GC)

멀티 스레드로 Minor GC를 수행합니다. Java 8까지의 기본 GC였습니다.

```mermaid
gantt
    title Parallel GC 동작
    dateFormat X
    axisFormat %s

    section App Thread 1
    실행중 : 0, 10
    STW(GC) : crit, 10, 20
    실행중 : 20, 30

    section App Thread 2
    실행중 : 0, 10
    STW(GC) : crit, 10, 20
    실행중 : 20, 30

    section GC Thread 1
    병렬 GC 처리 : active, 10, 20

    section GC Thread 2
    병렬 GC 처리 : active, 10, 20

    section GC Thread 3
    병렬 GC 처리 : active, 10, 20

    section GC Thread 4
    병렬 GC 처리 : active, 10, 20
```

```bash
-XX:+UseParallelGC
-XX:ParallelGCThreads=8      # GC 스레드 수
-XX:GCTimeRatio=19           # GC 시간 비율 (1/(1+19) = 5% 목표)
-XX:MaxGCPauseMillis=200     # 최대 일시 정지 목표 (ms)
```

| 항목 | 내용 |
|------|------|
| 적합 환경 | 배치 처리, 대용량 데이터 처리 (응답 시간보다 처리량 중요) |
| 일시 정지 | 중간 (Serial보다 짧음) |
| 처리량 | 높음 |

### CMS (Concurrent Mark-Sweep) GC — Deprecated

애플리케이션 스레드와 GC 스레드가 **동시에(Concurrent)** 실행되어 STW를 최소화합니다. Java 9에서 Deprecated, Java 14에서 완전 제거되었습니다.

```mermaid
sequenceDiagram
    participant App as App Thread
    participant GC as GC Thread

    Note over App,GC: Phase 1: Initial Mark (STW — 짧음)
    App->>GC: STW 시작
    GC->>GC: GC Root 직접 참조 객체만 표시
    GC->>App: STW 종료

    Note over App,GC: Phase 2: Concurrent Mark (동시 실행)
    App->>App: 애플리케이션 실행 계속
    GC->>GC: Mark 탐색 (동시)

    Note over App,GC: Phase 3: Remark (STW — 중간)
    App->>GC: STW 시작
    GC->>GC: 동시 실행 중 변경된 참조 재확인
    GC->>App: STW 종료

    Note over App,GC: Phase 4: Concurrent Sweep (동시 실행)
    App->>App: 애플리케이션 실행 계속
    GC->>GC: Sweep (동시)
```

**CMS 단점**:
- Compact 미수행 → 단편화 심각 → 결국 Full GC (STW) 발생
- 높은 CPU 사용률 (GC 스레드가 CPU 지속 소비)
- Floating Garbage (동시 실행 중 발생한 새 가비지는 다음 사이클에 처리)

### G1 GC (Garbage First) — Java 9+ 기본

**Region 기반**으로 힙을 동일한 크기의 블록으로 나누어 관리합니다. 각 Region은 역할이 동적으로 변합니다.

```mermaid
graph TD
    subgraph "G1 GC 힙 구조 (2048개 Region)"
        R1["E (Eden)"]
        R2["E (Eden)"]
        R3["S (Survivor)"]
        R4["O (Old)"]
        R5["H (Humongous)"]
        R6["빈 Region"]
    end
    LEGEND["E: Eden Region\nS: Survivor Region\nO: Old Region\nH: Humongous Region (큰 객체)\n빈 Region: 언제든 역할 변경 가능"]
```

**G1 GC 동작 단계**:

```mermaid
graph TD
    YGC["1. Young GC (STW)\nEden+Survivor → 살아있는 객체를 새 Survivor/Old Region으로 복사\n회수된 Region → 비워서 재사용"]
    CMC["2. Concurrent Marking Cycle (동시)\n2-1. Initial Mark (STW): GC Root 직접 참조 표시\n2-2. Root Region Scan (동시): Survivor 참조 스캔\n2-3. Concurrent Mark (동시): 전체 힙 참조 탐색\n2-4. Remark (STW): SATB 처리\n2-5. Cleanup (STW+동시): 회수 가능 Region 목록 작성"]
    MGC["3. Mixed GC (STW)\nYoung Region + 회수 효율 높은 Old Region 선택 수집\nGarbage First: 가비지 비율 높은 Region 우선 처리"]

    YGC --> CMC --> MGC --> YGC
```

**Humongous 객체**:

```java
// Region 크기의 50% 이상인 객체는 Humongous Region에 배치
// Region 크기 = 힙 크기 / 2048 (1MB ~ 32MB)
// 예: 힙 4GB → Region 크기 2MB → 1MB 이상 객체가 Humongous

byte[] hugeArray = new byte[2 * 1024 * 1024]; // 2MB → Humongous

// Humongous 객체는 Old에 직접 할당 → Young GC로 회수 안 됨
// 짧게 사는 큰 객체는 GC 부담 증가 → 가능하면 분할
```

**G1 GC 주요 옵션**:

```bash
-XX:+UseG1GC                      # G1 활성화 (Java 9+는 기본값)
-XX:MaxGCPauseMillis=200          # 목표 최대 일시 정지 시간 (ms)
-XX:G1HeapRegionSize=16m          # Region 크기 (1~32MB, 2의 거듭제곱)
-XX:G1NewSizePercent=5            # Young Generation 최소 비율
-XX:G1MaxNewSizePercent=60        # Young Generation 최대 비율
-XX:G1MixedGCLiveThresholdPercent=85  # Mixed GC 포함 Old Region 기준
-XX:InitiatingHeapOccupancyPercent=45 # Concurrent Mark 시작 힙 점유율
```

**Remembered Set과 Card Table**:

```mermaid
graph TD
    subgraph "Old Region"
        CT["Card Table (512 byte 단위)\nCard0 | Card1 | Card2 | Card3\n각 Card에 dirty 비트 표시"]
        OLD_OBJ["Old 객체 → Young 객체 참조"]
    end
    subgraph "Young Region"
        RS["Remembered Set (RS)\nOld→Young 참조 기록"]
    end
    CT -->|"참조 발생 시 기록"| RS
    NOTE["Young GC 시 RS만 확인 → 전체 Old 스캔 불필요"]
    RS --> NOTE
```

### ZGC (Z Garbage Collector) — Java 15+ Production

목표: **최대 일시 정지 1ms 미만** (힙 크기와 무관).

```bash
-XX:+UseZGC
```

**ZGC 핵심 기술**:

**1. Colored Pointer (색상 포인터)**

```mermaid
graph LR
    subgraph "일반 64비트 포인터"
        P1["0000 0000 ... 실제 주소 (42비트) ..."]
    end
    subgraph "ZGC Colored Pointer"
        P2["실제 주소 (42비트) | Finalizable | Remapped | Marked1 | Marked0"]
        META["상위 4비트를 GC 메타데이터로 활용\n→ 추가 메모리 없이 동시 처리 구현"]
    end
```

객체 주소 자체에 GC 상태를 저장하여 추가 메모리 없이 동시 처리를 구현합니다.

**2. Load Barrier (부하 장벽)**

```java
// 코드상 단순 참조 접근:
Object obj = someField;

// JIT 컴파일 후 (Load Barrier 삽입):
Object obj = someField;
if (obj의 포인터 색상이 현재 GC 뷰와 불일치) {
    obj = GC가 알고 있는 최신 주소로 수정; // 힙 이동 후 참조 갱신
}
```

Load Barrier가 모든 객체 참조 접근 시 동작하여 동시 이동(Concurrent Relocation) 중에도 올바른 주소를 보장합니다.

**ZGC 동작 단계**:

```mermaid
graph TD
    PMS["Pause Mark Start (STW &lt;1ms)\nGC Root 표시 시작"]
    CM["Concurrent Mark (동시)\n힙 전체 동시 표시"]
    PME["Pause Mark End (STW &lt;1ms)\n표시 완료 처리"]
    CPR["Concurrent Prepare for Reloc (동시)\n이동할 Region 선택"]
    PRS["Pause Relocate Start (STW &lt;1ms)\n이동 시작"]
    CR["Concurrent Relocate (동시)\n객체 동시 이동"]
    CRM["Concurrent Remap (동시)\n포인터 업데이트"]

    PMS --> CM --> PME --> CPR --> PRS --> CR --> CRM
```

**대용량 힙 지원**:

```bash
# ZGC는 TB 단위 힙도 지원
-Xmx16t   # 16 Terabytes
-XX:+UseZGC
```

**Generational ZGC (Java 21)**:

Java 21부터 ZGC도 Young/Old Generation을 분리하는 Generational 모드를 지원합니다.

```bash
-XX:+UseZGC -XX:+ZGenerational  # Java 21
# Java 23부터 Generational이 기본값
```

### Shenandoah GC

RedHat이 개발한 **동시 압축(Concurrent Compaction)** GC입니다.

```bash
-XX:+UseShenandoahGC
```

**ZGC와의 차이점**:

**Brooks Pointer (브룩스 포인터)**:

```mermaid
graph TD
    subgraph "Shenandoah 객체 레이아웃"
        BP["Brooks Pointer (간접 주소)\n← 헤더에 추가된 포인터"]
        OH["Object Header"]
        OF["Object Fields"]
        BP --> OH --> OF
    end
    OLD["Old Location"] -->|"Brooks Pointer가 New Location 가리킴"| NEW["New Location"]
    NOTE["모든 스레드가 old를 통해 new에 접근\n→ 동시 이동 가능\n→ 이후 점진적으로 직접 참조 업데이트"]
```

| 항목 | ZGC | Shenandoah |
|------|-----|------------|
| 개발사 | Oracle | RedHat |
| 포인터 기법 | Colored Pointer | Brooks Pointer |
| Load Barrier | 있음 | 있음 |
| 메모리 오버헤드 | 낮음 | 약간 높음 (헤더 추가) |
| 대용량 힙 | 매우 강함 | 강함 |
| OpenJDK 포함 | Java 15+ | Java 12+ |

---

## 6. GC 종류별 비교 표

| GC | 최대 일시 정지 | 처리량 | 메모리 오버헤드 | 구현 복잡도 | 적합 환경 |
|----|--------------|--------|--------------|-----------|---------|
| Serial | 초 단위 가능 | 낮음 | 최소 | 매우 낮음 | 단일 코어, 임베디드 |
| Parallel | 수십~수백 ms | 최고 | 낮음 | 낮음 | 배치, 과학 계산 |
| CMS | 수십 ms (Mark/Remark) | 높음 | 중간 | 높음 | (Deprecated, 사용 지양) |
| G1 | 수십~수백 ms (목표 설정) | 높음 | 중간 | 중간 | 범용, 4GB+ 힙 |
| ZGC | <1ms (목표) | 약간 낮음 | 약간 높음 | 높음 | 저지연, TB급 힙 |
| Shenandoah | <10ms (목표) | 약간 낮음 | 약간 높음 | 높음 | 저지연, 범용 |

---

## 7. GC 튜닝 핵심 옵션

### 힙 크기 설정

```bash
-Xms2g                  # 초기 힙 크기 2GB
-Xmx8g                  # 최대 힙 크기 8GB
# 실무 팁: Xms == Xmx로 설정 시 동적 조정 비용 제거
#           컨테이너에서는 MaxRAMPercentage 사용 권장
-XX:MaxRAMPercentage=75 # 컨테이너 메모리의 75%를 힙에 할당
```

### Young/Old 비율 조정

```bash
-XX:NewRatio=2          # Old:Young = 2:1 → Young이 힙의 1/3
-XX:NewSize=512m        # Young Generation 초기 크기
-XX:MaxNewSize=2g       # Young Generation 최대 크기
-XX:SurvivorRatio=8     # Eden:Survivor = 8:1:1 → Eden이 Young의 80%
```

### GC 종류 선택

```bash
-XX:+UseSerialGC        # Serial GC
-XX:+UseParallelGC      # Parallel GC
-XX:+UseG1GC            # G1 GC (Java 9+ 기본)
-XX:+UseZGC             # ZGC (Java 15+)
-XX:+UseShenandoahGC    # Shenandoah
```

### G1 GC 튜닝

```bash
-XX:MaxGCPauseMillis=200         # 목표 최대 STW 시간
-XX:G1HeapRegionSize=16m         # Region 크기
-XX:InitiatingHeapOccupancyPercent=45  # Concurrent Cycle 시작 임계값
-XX:G1ReservePercent=10          # 승격 실패 방지용 예비 힙 비율
-XX:ConcGCThreads=4              # 동시 GC 스레드 수
```

### GC 로그 설정

```bash
# Java 9+ 권장 방식
-Xlog:gc*:file=gc.log:time,uptime,level,tags:filecount=5,filesize=20m

# 주요 태그
-Xlog:gc                    # 기본 GC 요약
-Xlog:gc*                   # 모든 GC 관련 로그
-Xlog:gc+heap               # 힙 사용량 포함
-Xlog:gc+age                # 객체 나이 분포

# Java 8 (구 방식)
-XX:+PrintGCDetails
-XX:+PrintGCDateStamps
-Xloggc:/var/log/app/gc.log
-XX:+UseGCLogFileRotation
-XX:NumberOfGCLogFiles=5
-XX:GCLogFileSize=20m
```

---

## 8. GC 로그 분석

### G1 GC 로그 읽기

```mermaid
graph TD
    LOG1["GC(42) Pause Young (Normal) G1 Evacuation Pause 512M→256M(2048M) 45.123ms"]
    A1["GC(42): 42번째 GC"]
    A2["Pause Young: Minor GC (Young Generation 수집)"]
    A3["Normal: 정상 Young GC"]
    A4["512M→256M(2048M): 힙 사용량 감소 (전체 2048MB)"]
    A5["45.123ms: STW 시간"]
    LOG1 --> A1
    LOG1 --> A2
    LOG1 --> A3
    LOG1 --> A4
    LOG1 --> A5
```

```mermaid
graph TD
    LOG2["GC(43) Pause Young (Concurrent Start)\nGC(43) Concurrent Mark Cycle 245ms\nGC(44) Pause Remark 8ms\nGC(45) Pause Cleanup 3ms\nGC(45) Pause Young (Mixed) 62ms"]
    B1["Concurrent Start: Concurrent Marking Cycle 시작"]
    B2["Mixed: Young + 일부 Old Region 수집"]
    LOG2 --> B1
    LOG2 --> B2
```

### ZGC 로그 읽기

```mermaid
graph TD
    ZLC["GC(10) 2048M(100%) → 256M(12%)"]
    Z1["Pause Mark Start: 0.021ms (STW — 매우 짧음)"]
    Z2["Concurrent Mark: 243ms (동시 실행)"]
    Z3["Pause Mark End: 0.018ms (STW)"]
    Z4["Concurrent Process: 12ms"]
    Z5["Pause Relocate Start: 0.019ms (STW)"]
    Z6["Concurrent Relocate: 85ms (동시 실행)"]

    ZLC --> Z1 --> Z2 --> Z3 --> Z4 --> Z5 --> Z6
```

### GC 분석 도구

**GCEasy (온라인)**:

```mermaid
graph LR
    UPLOAD["GC 로그 파일 업로드\nhttps://gceasy.io"] --> ANALYZE["자동 분석"]
    ANALYZE --> R1["GC 발생 빈도 및 패턴"]
    ANALYZE --> R2["STW 시간 분포"]
    ANALYZE --> R3["힙 사용량 추이"]
    ANALYZE --> R4["잠재적 메모리 누수 탐지"]
```

**GCViewer (로컬 도구)**:

```bash
java -jar gcviewer-1.36.jar gc.log
# 타임라인 그래프, 통계 제공
```

**JVM 내장 도구**:

```bash
# JVM 실행 중 GC 정보 확인
jstat -gcutil <pid> 1000    # 1초 간격으로 GC 통계 출력
jstat -gc <pid> 1000        # 힙 크기 및 GC 횟수/시간
jcmd <pid> GC.run           # GC 강제 실행
jcmd <pid> VM.native_memory # 네이티브 메모리 사용량
```

---

## 9. Stop-the-World 최소화 전략

### 1. 객체 수명 단축

```java
// 나쁜 예 — 불필요한 Long-lived 객체
public class Cache {
    private static final Map<String, byte[]> cache = new HashMap<>();
    // static Map에 byte[]를 계속 추가 → Old Generation 점유 증가
}

// 좋은 예 — 약한 참조 + 크기 제한
public class BoundedCache {
    private final Map<String, SoftReference<byte[]>> cache =
        new LinkedHashMap<>(100, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry e) {
                return size() > 100; // 최대 100개 유지
            }
        };
}
```

### 2. 힙 크기 적절히 설정

```mermaid
graph TD
    SMALL["힙이 너무 작음\nGC 빈도 증가 → Full GC 증가 → 전체 STW 시간 증가"]
    LARGE["힙이 너무 큼\nGC 당 STW 시간 증가 (더 많은 객체 스캔)\n불필요한 메모리 낭비"]
    OPT["권장: 실제 워킹셋의 2~3배 설정"]
    SMALL --> OPT
    LARGE --> OPT
```

### 3. 객체 풀링 (신중하게)

```java
// 대용량 임시 버퍼는 풀링으로 GC 부담 감소
public class BufferPool {
    private final Queue<byte[]> pool = new ConcurrentLinkedQueue<>();
    private static final int BUFFER_SIZE = 64 * 1024; // 64KB

    public byte[] acquire() {
        byte[] buf = pool.poll();
        return buf != null ? buf : new byte[BUFFER_SIZE];
    }

    public void release(byte[] buf) {
        // 풀 크기 제한 (메모리 누수 방지)
        if (pool.size() < 100) {
            pool.offer(buf);
        }
    }
}
```

### 4. 대용량 배열 처리 주의

```java
// Humongous 객체 발생 방지 (G1 GC 기준)
// G1 Region 크기(기본 자동 계산) > 객체 크기/2 이면 Humongous

// 나쁜 예 — 매 요청마다 큰 배열 생성
byte[] buffer = new byte[10 * 1024 * 1024]; // 10MB, Humongous!

// 좋은 예 — 청크 단위 처리
int chunkSize = 512 * 1024; // 512KB
for (int offset = 0; offset < totalSize; offset += chunkSize) {
    byte[] chunk = new byte[Math.min(chunkSize, totalSize - offset)];
    process(chunk, data, offset);
}
```

### 5. GC 친화적 자료구조

```java
// int[] vs List<Integer> 비교
int[] primitiveArray = new int[1_000_000];     // 4MB, GC 부담 최소
List<Integer> boxedList = new ArrayList<>(1_000_000); // ~16MB + 객체 오버헤드

// 대량 기본 타입 데이터는 배열 또는 primitive 특화 컬렉션 사용
// (Eclipse Collections, Trove, Koloboke 등)
```

---

## 10. 메모리 누수 패턴

### static 컬렉션

```java
// 메모리 누수 — static Map에 무한정 추가
public class EventRegistry {
    // static Map은 애플리케이션 생명주기 동안 유지
    private static final Map<String, List<Object>> handlers = new HashMap<>();

    public static void register(String event, Object handler) {
        handlers.computeIfAbsent(event, k -> new ArrayList<>()).add(handler);
        // remove() 없으면 영원히 쌓임
    }
}

// 해결: 명시적 remove 또는 WeakHashMap 사용
private static final Map<String, List<Object>> handlers = new WeakHashMap<>();
```

### 리스너/콜백 미해제

```java
// 메모리 누수 — 등록한 리스너를 해제하지 않음
public class MyService {
    public void start() {
        eventBus.subscribe("user.created", this::onUserCreated);
        // 서비스 종료 시 unsubscribe 안 하면
        // MyService 인스턴스가 GC 대상에서 제외됨
    }

    @PreDestroy
    public void stop() {
        eventBus.unsubscribe("user.created", this::onUserCreated); // 반드시 해제
    }
}
```

### ThreadLocal 미정리

```java
// 메모리 누수 — 스레드 풀에서 ThreadLocal 미정리
public class RequestFilter {
    private static final ThreadLocal<UserContext> CONTEXT = new ThreadLocal<>();

    public void doFilter(Request req, Response res, FilterChain chain) {
        CONTEXT.set(new UserContext(req.getUserId()));
        try {
            chain.doFilter(req, res);
        } finally {
            CONTEXT.remove(); // 반드시! 스레드 풀 스레드는 재사용되므로
        }
    }
}
```

### 클래스로더 누수

```java
// 메모리 누수 — 동적 클래스로더와 static 참조
public class PluginLoader {
    // static 컬렉션이 동적으로 로드된 클래스를 참조
    private static final List<Class<?>> loadedClasses = new ArrayList<>();

    public void loadPlugin(URL[] urls) {
        URLClassLoader loader = new URLClassLoader(urls);
        Class<?> pluginClass = loader.loadClass("com.example.Plugin");
        loadedClasses.add(pluginClass); // 클래스로더가 GC 불가 → Metaspace 누수

        // 해결: 플러그인 언로드 시 loadedClasses에서 제거 + loader.close()
    }
}
```

### 내부 클래스 참조

```java
// 메모리 누수 — 비정적 내부 클래스가 외부 클래스를 암묵적으로 참조
public class Outer {
    private final byte[] largeData = new byte[10 * 1024 * 1024]; // 10MB

    public Runnable createTask() {
        // 비정적 내부 클래스 → Outer 인스턴스에 대한 암묵적 참조 보유
        return new Runnable() {
            @Override
            public void run() {
                // largeData를 직접 사용하지 않아도 Outer가 GC 불가
            }
        };
    }
}

// 해결: static 내부 클래스 또는 람다 + 명시적 캡처
public Runnable createTask() {
    byte[] needed = this.largeData; // 필요한 것만 캡처
    return () -> process(needed);   // Outer 전체를 참조하지 않음
}
```

### 메모리 누수 진단 도구

```bash
# 힙 덤프 생성
jmap -dump:format=b,file=heap.hprof <pid>
# OOM 발생 시 자동 덤프
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/var/log/app/heap.hprof

# 힙 덤프 분석
# Eclipse MAT (Memory Analyzer Tool): https://eclipse.dev/mat/
# VisualVM: jvisualvm 명령

# 실시간 모니터링
jcmd <pid> VM.native_memory summary
jstat -gcutil <pid> 2000  # 2초 간격
```

---

## 11. 실무 GC 선택 가이드

### 워크로드별 추천

```mermaid
graph TD
    BATCH["배치 처리 / 데이터 파이프라인\n(처리량 최우선)\n→ Parallel GC\nCPU 최대 활용, STW 있어도 처리량 중요"]
    WEB["일반 웹 서비스 API\n(균형형, 힙 4GB~16GB)\n→ G1 GC (Java 9+ 기본)\n튜닝 옵션 풍부, 검증된 안정성"]
    LOWLAT["저지연 서비스\n(실시간 거래, 게임 서버, 힙 8GB+)\n→ ZGC\n&lt;1ms STW, 힙 크기 확장에도 지연 안정적"]
    SHEN["저지연 + 범용\n(ZGC보다 CPU 효율 우선)\n→ Shenandoah\nCPU 오버헤드 측면에서 ZGC와 다름"]
    MICRO["마이크로서비스 / 컨테이너\n(소규모, 힙 512MB 미만)\n→ Serial GC 또는 G1 GC\n초소형: -XX:+UseSerialGC\n또는 GraalVM Native Image"]
```

### 선택 플로우차트

```mermaid
graph TD
    START["애플리케이션 특성 분석"]
    Q1{"힙 크기가 1GB 미만?"}
    A1["Serial GC 또는 G1"]
    Q2{"처리량이 최우선인가?\n(배치, 분석)"}
    A2["Parallel GC"]
    Q3{"STW &lt; 100ms가 필수인가?"}
    A3["ZGC 또는 Shenandoah"]
    A4["G1 GC (기본 선택)\n-XX:MaxGCPauseMillis=200"]

    START --> Q1
    Q1 -->|YES| A1
    Q1 -->|NO| Q2
    Q2 -->|YES| A2
    Q2 -->|NO| Q3
    Q3 -->|YES| A3
    Q3 -->|NO| A4
```

### 컨테이너 환경 필수 설정

```bash
# Docker/Kubernetes 컨테이너에서 JVM 메모리 올바르게 인식
# Java 10+ 권장 설정
-XX:+UseContainerSupport          # 컨테이너 메모리 인식 (기본 활성화)
-XX:MaxRAMPercentage=75           # 컨테이너 메모리의 75%를 힙에 할당
-XX:InitialRAMPercentage=50       # 초기 힙 = 50%

# 예: 컨테이너 메모리 2GB → 최대 힙 1.5GB 자동 설정
```

### 프로파일링 기반 튜닝 절차

```mermaid
graph TD
    S1["1. 기본 설정으로 부하 테스트 실행\nwrk / JMeter / k6로 목표 TPS 부하 인가"]
    S2["2. GC 로그 수집\n-Xlog:gc*:file=gc.log:time,uptime:filecount=5,filesize=20m"]
    S3["3. GCEasy 또는 GCViewer로 분석\n- Full GC 발생 여부\n- Minor GC 빈도\n- Minor GC STW 시간\n- Old Generation 증가 추세"]
    S4["4. 파라미터 조정 → 재측정 반복"]
    S5["5. 안정화 후 운영 배포"]

    S1 --> S2 --> S3 --> S4 --> S5
    S4 -->|"목표 미달 시 반복"| S1
```

---

## 실무에서 자주 하는 실수

### 실수 1: GC 로그 없이 튜닝 시도

GC 문제를 추정으로 해결하려는 것이 가장 흔한 실수입니다. Full GC 발생 여부, STW 시간, Old Generation 증가 추세는 반드시 로그로 확인해야 합니다.

```bash
# GC 로그 활성화 (Java 9+)
java -Xlog:gc*:file=gc.log:time,uptime:filecount=5,filesize=20m \
     -XX:+HeapDumpOnOutOfMemoryError \
     -XX:HeapDumpPath=/var/log/app/heap.hprof \
     -jar app.jar
```

GCEasy(https://gceasy.io) 또는 GCViewer로 로그를 분석하면 Full GC 빈도, 평균 STW 시간, 힙 사용 패턴을 시각적으로 파악할 수 있습니다.

### 실수 2: Xmx만 크게 설정하면 해결된다는 믿음

힙을 크게 잡으면 GC 빈도는 줄지만, Full GC 한 번의 STW 시간이 길어집니다. 8GB 힙에서 Full GC가 발생하면 수 초~수십 초 STW가 발생할 수 있습니다.

```bash
# 나쁜 예: 무작정 힙만 크게
java -Xmx16g -jar app.jar

# 좋은 예: 힙 크기 + GC 알고리즘 함께 조정
java -Xmx8g \
     -XX:+UseZGC \          # 저지연 GC로 STW를 ms 수준으로 제한
     -XX:MaxGCPauseMillis=50 \
     -jar app.jar
```

### 실수 3: static 컬렉션에 객체를 넣고 빼지 않음

static 필드에 저장된 컬렉션은 GC Root로부터 항상 도달 가능하므로 절대 수거되지 않습니다. 캐시처럼 사용하다가 메모리 누수의 주범이 됩니다.

```java
// 위험: static Map에 넣기만 하고 제거하지 않음
public class SessionManager {
    private static final Map<String, Session> sessions = new HashMap<>();

    public void addSession(String id, Session session) {
        sessions.put(id, session); // 세션이 만료돼도 Map에 남아있음
    }
    // remove() 없음 → 메모리 누수
}

// 개선: WeakHashMap 또는 만료 기반 캐시
private static final Map<String, Session> sessions =
    Collections.synchronizedMap(new WeakHashMap<>());
// 또는 Caffeine 캐시로 TTL 설정
```

### 실수 4: finalize() 또는 Cleaner를 잘못 사용

`finalize()`는 GC가 실행할 시점을 보장하지 않으며 성능 문제를 유발합니다. Java 9부터 deprecated이며, Java 18부터는 제거 예정입니다.

```java
// 나쁜 예: finalize() 사용
@Override
protected void finalize() throws Throwable {
    connection.close(); // GC 타이밍 불확실, 성능 저하
}

// 좋은 예: try-with-resources 또는 Cleaner
public class Resource implements AutoCloseable {
    @Override
    public void close() {
        connection.close(); // 명시적 호출 보장
    }
}

try (Resource r = new Resource()) {
    r.use();
} // 자동으로 close() 호출
```

### 실수 5: Young Generation 비율을 기본값에서 건드리지 않음

단명 객체(요청 처리 중 생성되는 DTO, 임시 문자열)가 많은 서버 애플리케이션에서 Young Generation이 너무 작으면 Minor GC가 과도하게 발생합니다.

```bash
# Young Generation 비율 조정
java -Xmx8g \
     -XX:NewRatio=2 \        # Young:Old = 1:2 (Young = 약 2.7GB)
     -XX:SurvivorRatio=8 \   # Eden:Survivor = 8:1:1
     -XX:+UseG1GC \
     -jar app.jar

# G1GC에서는 Region 크기로 제어
java -Xmx8g \
     -XX:+UseG1GC \
     -XX:G1HeapRegionSize=16m \  # 대형 객체(Humongous) 임계값 상향
     -jar app.jar
```

---

## 극한 시나리오

### 100 TPS — G1GC 기본 설정으로 충분

초당 100건의 요청은 기본 G1GC 설정으로 충분히 처리됩니다. 추가 튜닝보다 메모리 누수 여부 모니터링이 더 중요합니다.

```bash
# 100 TPS: 기본 설정 + 모니터링만 추가
java -Xms2g -Xmx4g \
     -XX:+UseG1GC \
     -XX:+HeapDumpOnOutOfMemoryError \
     -Xlog:gc*:file=gc.log:time,uptime \
     -jar app.jar
```

Heap 사용량이 시간이 지나도 일정 수준에서 안정화되는지 확인합니다. 점진적으로 증가한다면 메모리 누수를 의심해야 합니다.

### 10,000 TPS — STW 최소화가 핵심

초당 10,000건에서 100ms STW가 발생하면 해당 시간 동안 1,000건의 요청이 지연됩니다. STW를 50ms 이하로 제한하는 것이 목표입니다.

```bash
# 10K TPS: G1GC + STW 목표 설정
java -Xms8g -Xmx8g \          # Min=Max로 힙 크기 고정 (리사이징 STW 방지)
     -XX:+UseG1GC \
     -XX:MaxGCPauseMillis=50 \ # STW 목표 50ms
     -XX:G1HeapOccupancyPercent=45 \ # Old GC 트리거 임계값 낮춤
     -XX:G1NewSizePercent=20 \
     -XX:G1MaxNewSizePercent=40 \
     -jar app.jar
```

```java
// 객체 생성 최소화: 요청당 임시 객체를 줄여 GC 압력 감소
// 나쁜 예: 매 요청마다 새 StringBuilder
public String buildResponse(List<Item> items) {
    String result = "";
    for (Item item : items) {
        result += item.toString(); // 매 반복마다 String 객체 생성
    }
    return result;
}

// 좋은 예: StringBuilder 재사용 패턴 또는 ThreadLocal
private static final ThreadLocal<StringBuilder> SB =
    ThreadLocal.withInitial(StringBuilder::new);

public String buildResponse(List<Item> items) {
    StringBuilder sb = SB.get();
    sb.setLength(0); // 재사용
    items.forEach(item -> sb.append(item.toString()));
    return sb.toString();
}
```

### 100,000 TPS — ZGC + 힙 외 메모리 전략

초당 100,000건에서는 GC STW가 수십 ms만 되어도 서비스에 영향을 줍니다. ZGC 또는 Shenandoah로 STW를 1~2ms 이하로 줄이고, Off-heap 메모리 활용을 검토합니다.

```bash
# 100K TPS: ZGC로 STW 최소화
java -Xms32g -Xmx32g \
     -XX:+UseZGC \
     -XX:SoftMaxHeapSize=28g \     # 힙 28GB 초과 시 적극적 GC
     -XX:ConcGCThreads=4 \        # 동시 GC 스레드 수
     -XX:+ZGenerational \         # Java 21+: Generational ZGC
     -jar app.jar
```

```java
// Off-heap 캐시: DirectByteBuffer로 GC 대상 외 메모리 사용
public class OffHeapCache {
    // GC가 관리하지 않는 네이티브 메모리에 캐시 저장
    private final ByteBuffer buffer = ByteBuffer.allocateDirect(1024 * 1024 * 512); // 512MB

    public void put(int offset, byte[] data) {
        buffer.position(offset);
        buffer.put(data); // GC 압력 없음
    }
}
```

```mermaid
graph TD
    subgraph "100K TPS GC 전략"
        Z["ZGC / Generational ZGC\n-XX:+UseZGC -XX:+ZGenerational"]
        OH["Off-heap 캐시\nDirectByteBuffer / Chronicle Map"]
        OBJ["객체 풀링\nApache Commons Pool"]
        VAL["Value Objects 최소화\nrecord 대신 primitive"]
        MON["실시간 모니터링\nJFR + Prometheus GC 메트릭"]
    end

    Z -->|"STW 1ms 이하"| MON
    OH -->|"GC 압력 감소"| MON
    OBJ -->|"할당 빈도 감소"| MON
    VAL -->|"Young GC 감소"| MON
```

100K TPS에서는 GC 튜닝 이전에 애플리케이션 코드에서 불필요한 객체 생성을 줄이는 것이 선행되어야 합니다. JFR(Java Flight Recorder)로 어느 코드가 가장 많은 객체를 생성하는지 프로파일링한 후 최적화하는 순서가 효과적입니다.

---

## 정리

```mermaid
graph TD
    subgraph "GC 선택 요약"
        PAR["처리량 최우선 → Parallel GC\n-XX:+UseParallelGC"]
        G1["범용 균형형 → G1 GC\n-XX:+UseG1GC (기본값)"]
        ZGC["저지연 필수 → ZGC\n-XX:+UseZGC"]
        SHN["저지연 대안 → Shenandoah\n-XX:+UseShenandoahGC"]
        SER["소규모/임베디드 → Serial GC\n-XX:+UseSerialGC"]
    end
    subgraph "GC 튜닝 3원칙"
        P1["1. 측정 먼저 — GC 로그 없이 튜닝하지 않는다"]
        P2["2. 한 번에 하나씩 — 파라미터 하나 변경 후 측정"]
        P3["3. 힙 크기가 첫 번째 — Xmx 설정이 가장 큰 영향"]
    end
    subgraph "메모리 누수 방지 체크리스트"
        C1["static 컬렉션에 add() 후 remove() 쌍 확인"]
        C2["리스너/콜백 등록 후 해제 코드 확인"]
        C3["ThreadLocal 사용 후 remove() 확인"]
        C4["try-with-resources로 스트림/연결 자동 해제"]
        C5["-XX:+HeapDumpOnOutOfMemoryError 항상 활성화"]
    end
```
