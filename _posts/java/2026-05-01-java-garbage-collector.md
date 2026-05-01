---
title: "Java 가비지 컬렉터(GC) 완전 정리"
categories:
- JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

Java GC의 동작 원리부터 GC 종류별 아키텍처, 튜닝 옵션, 실무 선택 가이드까지 완전히 정리합니다.

---

## 1. GC란? 왜 필요한가?

Garbage Collection(GC)은 프로그램이 동적으로 할당한 메모리 중 더 이상 사용하지 않는 객체를 자동으로 탐지하고 회수하는 메커니즘입니다.

### 수동 메모리 관리의 문제

C/C++처럼 프로그래머가 직접 메모리를 해제하면 두 가지 치명적 버그가 발생합니다.

```
메모리 누수 (Memory Leak):
  ptr = malloc(100);
  // free(ptr) 깜빡 → 메모리 반환 안 됨 → 힙 고갈

댕글링 포인터 (Dangling Pointer):
  ptr = malloc(100);
  free(ptr);
  *ptr = 42; // 해제된 메모리 접근 → 정의되지 않은 동작
```

Java는 GC가 객체 회수를 책임지므로 개발자는 비즈니스 로직에만 집중할 수 있습니다. 단, GC가 동작하는 동안 발생하는 **Stop-the-World(STW)** 일시 정지가 애플리케이션 응답성에 영향을 미칩니다.

---

## 2. JVM 메모리 구조

### 전체 메모리 영역

```
┌──────────────────────────────────────────────────────────────┐
│                        JVM 메모리                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                      Heap                            │   │
│  │  ┌────────────────────────┐  ┌────────────────────┐  │   │
│  │  │    Young Generation    │  │  Old Generation    │  │   │
│  │  │  ┌──────┬─────┬──────┐ │  │  (Tenured Space)   │  │   │
│  │  │  │ Eden │ S0  │  S1  │ │  │                    │  │   │
│  │  │  └──────┴─────┴──────┘ │  │  오래 살아남은     │  │   │
│  │  │  (새 객체 할당 영역)    │  │  객체들            │  │   │
│  │  └────────────────────────┘  └────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────┐  ┌──────────────────────────────┐  │
│  │      Metaspace       │  │       Stack (스레드별)        │  │
│  │  클래스 메타데이터   │  │  ┌──────┐ ┌──────┐ ┌──────┐  │  │
│  │  메서드 정보         │  │  │T1    │ │T2    │ │T3    │  │  │
│  │  static 변수         │  │  │Stack │ │Stack │ │Stack │  │  │
│  │  (JVM 내부 → Native) │  │  └──────┘ └──────┘ └──────┘  │  │
│  └──────────────────────┘  └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
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

```
Mark 단계: GC Root에서 시작하여 참조 그래프를 탐색, 살아있는 객체에 표시
Sweep 단계: 표시되지 않은 객체를 메모리에서 해제

GC Root:
  - Stack의 지역 변수
  - static 변수
  - JNI 참조

Before Mark:
  [A]→[B]→[C]   [D]→[E]   [F]   [G]→[H]
   ↑
  Root

After Mark (살아있는 객체: A, B, C):
  [A*]→[B*]→[C*]   [D]→[E]   [F]   [G]→[H]

After Sweep:
  [A*]→[B*]→[C*]   [   ]     [ ]   [   ]
                     해제       해제    해제
```

**단점**: Sweep 후 메모리 단편화(Fragmentation) 발생. 큰 객체 할당 실패 가능.

### Mark-and-Compact

Mark-and-Sweep에 압축(Compact) 단계를 추가합니다.

```
After Compact:
  [A*][B*][C*][   ][   ][   ][   ][   ]
  ↑──────────── 사용 중 ────────↑── 빈 공간 ──┘

장점: 단편화 없음, 연속 메모리 할당 가능
단점: Compact 과정에서 객체 이동 → 참조 주소 갱신 필요 → STW 시간 길어짐
```

### Copying (복사 알고리즘)

메모리를 두 영역으로 나누어 사용 중인 절반의 살아있는 객체를 다른 절반으로 복사합니다.

```
From Space:  [A*][B ][C*][D ][E*]   (B, D는 가비지)
To Space:    [   ][   ][   ][   ][   ]

복사 후:
From Space:  [   ][   ][   ][   ][   ]  (전체 비움)
To Space:    [A* ][C* ][E* ][   ][   ]  (살아있는 객체만 복사, 압축됨)
```

**장점**: 단편화 없음, 할당 속도 빠름(포인터 하나만 이동).
**단점**: 메모리 절반만 사용 가능.
Young Generation의 Eden ↔ Survivor 복사에 이 방식을 사용합니다.

### Reference Counting (Java 미사용)

각 객체에 참조 횟수를 저장하고 0이 되면 즉시 해제합니다. Python, Swift 등에서 사용하지만 Java는 채택하지 않았습니다.

```
이유: 순환 참조(Circular Reference) 처리 불가

A → B → C → A  (세 객체가 서로 참조)
외부 참조가 없어도 각 카운트가 1 이상 → 영원히 해제 불가
```

---

## 4. Generational GC 가설 — 약한 세대 가설

### 핵심 가설

**"대부분의 객체는 생성 직후 금방 죽는다(짧은 수명을 가진다)."**

실제 프로그램에서 객체 생존 패턴을 분석하면 다음 분포를 보입니다.

```
객체 수명 분포

많음 │*
     │**
     │***
     │****
     │*****
     │*******
     │**************
     │****************************
적음 └──────────────────────────────────────→ 수명(시간)
     짧음                              길음

→ 대부분의 객체는 생성 직후 회수됨
→ 살아남은 객체는 오래 생존하는 경향
```

이 가설을 바탕으로 메모리를 **Young Generation**과 **Old Generation**으로 분리합니다.

### Young Generation 구조

```
Young Generation
┌──────────────────────────────────────────────┐
│                                              │
│  ┌───────────────────┐  ┌──────┐  ┌──────┐  │
│  │      Eden         │  │  S0  │  │  S1  │  │
│  │  (새 객체 할당)   │  │(From)│  │(To)  │  │
│  │                   │  │      │  │      │  │
│  │  빠른 TLAB 할당   │  │      │  │      │  │
│  └───────────────────┘  └──────┘  └──────┘  │
│   (전체의 약 80%)         (각 10%)            │
└──────────────────────────────────────────────┘

TLAB: Thread-Local Allocation Buffer
  각 스레드가 Eden의 일부를 독점 사용 → 동기화 없이 빠른 할당
```

### Minor GC vs Major GC vs Full GC

```
Minor GC (Young GC):
  트리거: Eden 영역이 가득 찼을 때
  대상:   Young Generation만
  STW:    짧음 (수 ms ~ 수십 ms)
  빈도:   자주 발생

Major GC (Old GC):
  트리거: Old Generation이 가득 찼을 때
  대상:   Old Generation
  STW:    Minor GC보다 길음
  빈도:   드물게 발생

Full GC:
  트리거: 힙 전체 부족, System.gc() 호출, Metaspace 부족
  대상:   Young + Old + Metaspace
  STW:    가장 김 (수백 ms ~ 수 초)
  빈도:   가능한 한 피해야 함
```

### 객체 승격(Promotion) 과정

```
1단계: 새 객체 → Eden 할당
   Eden: [Obj-A][Obj-B][Obj-C][Obj-D][Obj-E] ... (가득 참)

2단계: Minor GC 발생
   살아있는 객체(A, C, E) → Survivor S0로 복사 (age = 1)
   Eden: 전체 비움
   S0:   [A(age=1)][C(age=1)][E(age=1)]

3단계: 다음 Minor GC
   살아있는 객체(A, E) → S1로 복사 (age = 2)
   B, C 등 죽은 객체: 회수
   S0: 비움
   S1: [A(age=2)][E(age=2)]

4단계: age가 임계값(-XX:MaxTenuringThreshold, 기본 15) 도달 시
   → Old Generation으로 승격(Promote)

Old Generation:
   [A(promoted)][E(promoted)] ... 장수 객체들
```

---

## 5. GC 종류별 상세 설명

### Serial GC

단일 스레드로 GC를 수행합니다. GC 동안 애플리케이션 스레드가 모두 멈춥니다.

```
Serial GC 동작:

[App Thread 1] ██████████|  GC  |██████████
[App Thread 2] ██████████|  GC  |██████████
[App Thread 3] ██████████|  GC  |██████████
[GC Thread]              |██████|

Mark → Sweep → Compact (단일 GC 스레드)
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

```
Parallel GC 동작:

[App Thread 1] ██████████|      GC       |████████
[App Thread 2] ██████████|      GC       |████████
[GC Thread 1]            |██████████████|
[GC Thread 2]            |██████████████|
[GC Thread 3]            |██████████████|
[GC Thread 4]            |██████████████|

복수의 GC 스레드가 병렬 처리 → STW는 있지만 단시간
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

```
CMS GC 단계:

Phase 1: Initial Mark (STW — 짧음)
  GC Root 직접 참조 객체만 표시

Phase 2: Concurrent Mark (동시)
  [App] ████████████████████████████████
  [GC]  ────────── Mark 탐색 ───────────
  → 애플리케이션과 동시 실행

Phase 3: Remark (STW — 중간)
  동시 실행 중 변경된 참조 재확인

Phase 4: Concurrent Sweep (동시)
  [App] ████████████████████████████████
  [GC]  ────────── Sweep ────────────────
  → 애플리케이션과 동시 실행
```

**CMS 단점**:
- Compact 미수행 → 단편화 심각 → 결국 Full GC (STW) 발생
- 높은 CPU 사용률 (GC 스레드가 CPU 지속 소비)
- Floating Garbage (동시 실행 중 발생한 새 가비지는 다음 사이클에 처리)

### G1 GC (Garbage First) — Java 9+ 기본

**Region 기반**으로 힙을 동일한 크기의 블록으로 나누어 관리합니다. 각 Region은 역할이 동적으로 변합니다.

```
G1 GC 힙 구조 (예: 2048개 Region)

┌───┬───┬───┬───┬───┬───┬───┬───┐
│ E │ E │ S │ O │ O │ E │ H │ E │
├───┼───┼───┼───┼───┼───┼───┼───┤
│ O │ O │ E │ E │ S │ O │ H │ O │
├───┼───┼───┼───┼───┼───┼───┼───┤
│ E │ S │ O │ O │ E │ O │ O │ E │
├───┼───┼───┼───┼───┼───┼───┼───┤
│ O │ E │ E │ O │ O │ S │ E │ O │
└───┴───┴───┴───┴───┴───┴───┴───┘

E: Eden Region
S: Survivor Region
O: Old Region
H: Humongous Region (큰 객체)
빈 Region: 언제든 역할 변경 가능
```

**G1 GC 동작 단계**:

```
1. Young GC (STW):
   Eden + Survivor Region → 살아있는 객체를 새 Survivor/Old Region으로 복사
   회수된 Region → 비워서 재사용

2. Concurrent Marking Cycle (동시):
   2-1. Initial Mark (STW — Young GC와 함께): GC Root 직접 참조 표시
   2-2. Root Region Scan (동시): Survivor Region 참조 스캔
   2-3. Concurrent Mark (동시): 전체 힙 참조 탐색
   2-4. Remark (STW): SATB(Snapshot-At-The-Beginning) 처리
   2-5. Cleanup (STW + 동시): 회수 가능 Region 목록 작성

3. Mixed GC (STW):
   Young Region + 회수 효율 높은 Old Region 선택적 수집
   → "Garbage First": 가비지 비율 높은 Region 우선 처리
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

```
Old → Young 참조 추적 문제:
Young GC 시 Old Region도 GC Root로 스캔해야 하면 비용 증가

해결: Card Table + Remembered Set
┌─────────────────────────────────────────────────────┐
│  Old Region                                         │
│  ┌────┬────┬────┬────┐  Card Table (512 byte 단위)  │
│  │Card│Card│Card│Card│  각 Card에 dirty 비트 표시    │
│  └────┴────┴──┬─┴────┘                             │
│               │ Old 객체가 Young 객체 참조           │
└───────────────┼─────────────────────────────────────┘
                ↓
         Young Region의 Remembered Set에 기록
         → Young GC 시 RS만 확인하면 됨 (전체 Old 스캔 불필요)
```

### ZGC (Z Garbage Collector) — Java 15+ Production

목표: **최대 일시 정지 1ms 미만** (힙 크기와 무관).

```bash
-XX:+UseZGC
```

**ZGC 핵심 기술**:

**1. Colored Pointer (색상 포인터)**

```
일반 64비트 포인터:
  [0000 0000 ... 실제 주소 (42비트) ...]

ZGC 포인터:
  [0000 0000 ... 실제 주소 (42비트) ... | Finalizable | Remapped | Marked1 | Marked0]
                                           ↑ 상위 4비트를 메타데이터로 활용
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

```
모든 단계가 동시 실행 (STW는 극히 짧은 3번만)

Pause Mark Start (STW — <1ms): GC Root 표시 시작
Concurrent Mark:                힙 전체 동시 표시
Pause Mark End (STW — <1ms):   표시 완료 처리
Concurrent Prepare for Reloc:  이동할 Region 선택
Pause Relocate Start (STW — <1ms): 이동 시작
Concurrent Relocate:            객체 동시 이동
Concurrent Remap:               포인터 업데이트
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

```
Shenandoah 객체 레이아웃:
┌─────────────────────────────────┐
│  Brooks Pointer (간접 주소)      │ ← 헤더에 추가된 포인터
│  Object Header                  │
│  Object Fields                  │
└─────────────────────────────────┘

이동 시:
  Old Location의 Brooks Pointer → New Location 가리킴
  모든 스레드가 old를 통해 new에 접근 → 동시 이동 가능
  이후 점진적으로 직접 참조 업데이트
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

```
[2026-05-01T10:00:01.000+0900][1234ms][info][gc] GC(42) Pause Young (Normal) (G1 Evacuation Pause) 512M->256M(2048M) 45.123ms

분석:
  GC(42)             : 42번째 GC
  Pause Young        : Minor GC (Young Generation 수집)
  Normal             : 정상 Young GC (Concurrent Cycle 아님)
  G1 Evacuation Pause: G1의 Young GC 명칭
  512M->256M(2048M)  : 힙 512MB → 256MB (전체 2048MB)
  45.123ms           : STW 시간 45ms
```

```
[gc] GC(43) Pause Young (Concurrent Start) ... 52.000ms
[gc] GC(43) Concurrent Mark Cycle
[gc] GC(43) Concurrent Mark Cycle 245.000ms
[gc] GC(44) Pause Remark ... 8.000ms
[gc] GC(45) Pause Cleanup ... 3.000ms
[gc] GC(45) Pause Young (Mixed) ... 62.000ms

분석:
  Concurrent Start   : Concurrent Marking Cycle 시작
  Mixed              : Young + 일부 Old Region 수집
```

### ZGC 로그 읽기

```
[gc] GC(10) Garbage Collection (Warmup) 2048M(100%)->256M(12%)

[gc] GC(10) Pause Mark Start    0.021ms  ← STW (매우 짧음)
[gc] GC(10) Concurrent Mark    243.000ms ← 동시 실행
[gc] GC(10) Pause Mark End       0.018ms  ← STW
[gc] GC(10) Concurrent Process  12.000ms
[gc] GC(10) Pause Relocate Start 0.019ms  ← STW
[gc] GC(10) Concurrent Relocate 85.000ms  ← 동시 실행
```

### GC 분석 도구

**GCEasy (온라인)**:

```
https://gceasy.io
GC 로그 파일 업로드 → 자동 분석 → 권고사항 제공
주요 제공 정보:
  - GC 발생 빈도 및 패턴
  - STW 시간 분포
  - 힙 사용량 추이
  - 잠재적 메모리 누수 탐지
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

```
힙이 너무 작음:
  GC 빈도 증가 → Full GC 증가 → 전체 STW 시간 증가

힙이 너무 큼:
  GC 당 STW 시간 증가 (더 많은 객체 스캔)
  불필요한 메모리 낭비

권장: 실제 워킹셋의 2~3배 설정
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

```
배치 처리 / 데이터 파이프라인 (처리량 최우선):
  → Parallel GC (-XX:+UseParallelGC)
  → 이유: CPU 최대 활용, STW 있어도 처리량이 중요

일반 웹 서비스 API (균형형, 힙 4GB~16GB):
  → G1 GC (-XX:+UseG1GC, Java 9+ 기본)
  → -XX:MaxGCPauseMillis=200 설정
  → 이유: 튜닝 옵션 풍부, 검증된 안정성

저지연 서비스 (실시간 거래, 게임 서버, 힙 8GB 이상):
  → ZGC (-XX:+UseZGC)
  → 이유: <1ms STW, 힙 크기 확장에도 지연 안정적

저지연 + 범용 (ZGC보다 CPU 효율 우선):
  → Shenandoah (-XX:+UseShenandoahGC)
  → 이유: ZGC와 유사하나 CPU 오버헤드 측면에서 다름

마이크로서비스 / 컨테이너 (소규모, 힙 512MB 미만):
  → Serial GC 또는 G1 GC
  → -XX:+UseSerialGC (초소형 컨테이너)
  → GraalVM Native Image (JVM GC 제거, 빠른 시작)
```

### 선택 플로우차트

```
애플리케이션 특성 분석
         │
         ▼
힙 크기가 1GB 미만?
  YES → Serial GC 또는 G1
  NO  ↓
         ▼
처리량이 최우선인가? (배치, 분석)
  YES → Parallel GC
  NO  ↓
         ▼
STW < 100ms가 필수인가?
  YES → ZGC 또는 Shenandoah
  NO  ↓
         ▼
→ G1 GC (기본 선택)
   -XX:MaxGCPauseMillis=200
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

```
1. 기본 설정으로 부하 테스트 실행
   wrk / JMeter / k6 등으로 목표 TPS 부하 인가

2. GC 로그 수집
   -Xlog:gc*:file=gc.log:time,uptime:filecount=5,filesize=20m

3. GCEasy 또는 GCViewer로 분석
   확인 항목:
     - Full GC 발생 여부 (있으면 힙 크기 조정 또는 메모리 누수 의심)
     - Minor GC 빈도 (너무 잦으면 Young Generation 크기 증가)
     - Minor GC STW 시간 (목표치 초과 시 Survivor 비율 조정)
     - Old Generation 증가 추세 (지속 증가 시 메모리 누수 의심)

4. 파라미터 조정 → 재측정 반복

5. 안정화 후 운영 배포
```

---

## 정리

```
GC 선택 요약

┌──────────────────────────────────────────────────────────────┐
│  처리량 최우선   │  Parallel GC  │ -XX:+UseParallelGC        │
│  범용 균형형     │  G1 GC        │ -XX:+UseG1GC (기본값)     │
│  저지연 필수     │  ZGC          │ -XX:+UseZGC               │
│  저지연 대안     │  Shenandoah   │ -XX:+UseShenandoahGC      │
│  소규모/임베디드 │  Serial GC    │ -XX:+UseSerialGC          │
└──────────────────────────────────────────────────────────────┘

GC 튜닝 3원칙:
  1. 측정 먼저 — GC 로그 없이 튜닝하지 않는다
  2. 한 번에 하나씩 — 파라미터 하나 변경 후 측정
  3. 힙 크기가 첫 번째 — Xmx 설정이 가장 큰 영향

메모리 누수 방지 체크리스트:
  □ static 컬렉션에 add() 후 remove() 쌍 확인
  □ 리스너/콜백 등록 후 해제 코드 확인
  □ ThreadLocal 사용 후 remove() 확인
  □ try-with-resources로 스트림/연결 자동 해제
  □ -XX:+HeapDumpOnOutOfMemoryError 항상 활성화
```
