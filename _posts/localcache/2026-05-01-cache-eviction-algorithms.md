---
title: "캐시 교체(Eviction) 알고리즘 — LRU, LFU, TinyLFU, W-TinyLFU, ARC"
categories:
- LOCAL_CACHE
toc: true
toc_sticky: true
toc_label: 목차
---

## 캐시 교체(Eviction)란?

> 비유: 냉장고가 꽉 찼을 때 새 식재료를 넣으려면 오래된 것을 버려야 한다. 무엇을 버릴지 결정하는 규칙이 Eviction 알고리즘이다. "가장 오래된 것"을 버릴지, "가장 안 쓴 것"을 버릴지, "가장 덜 자주 쓴 것"을 버릴지에 따라 알고리즘이 달라진다.

캐시의 용량은 유한하다. 새 항목을 추가할 공간이 없을 때, **기존 항목 중 어떤 것을 버릴지** 결정하는 정책을 **Eviction 알고리즘**이라 한다.

<div class="mermaid">
graph LR
    FULL["캐시 (최대 3개 슬롯)<br/>A | B | C ← 꽉 참"]
    NEW["새 항목 D 추가 요청"]
    DECISION["어떤 항목을 버릴까?<br/>A? B? C?"]
    RESULT["D | B | C ← A를 버리고 D 추가 (LRU 기준)"]
    FULL --> NEW --> DECISION --> RESULT
</div>

좋은 Eviction 알고리즘은 **미래에 사용될 가능성이 낮은 항목**을 버린다. 이것이 핵심이다. 미래를 예측할 수 없으므로, 각 알고리즘은 **과거 접근 패턴**을 근거로 삼는다.

### 핵심 지표: 히트율(Hit Rate)

```
Hit Rate = Cache Hit 수 / 전체 요청 수

히트율 90% = 100번 요청 중 90번은 캐시에서 응답, 10번만 DB 조회
```

히트율이 1% 오르면 실제 부하는 크게 달라진다.

```
히트율 80% → DB 요청: 20%
히트율 90% → DB 요청: 10%  (DB 부하 50% 감소)
히트율 99% → DB 요청: 1%   (DB 부하 95% 감소)
```

---

## FIFO — First In, First Out

### 구조와 동작

가장 먼저 들어온 항목을 가장 먼저 버린다. Queue 자료구조를 사용한다.

```
초기 상태 (캐시 크기: 3)
┌─────────────────────────┐
│ 진입 순서: A → B → C   │
│ [A] [B] [C]             │
└─────────────────────────┘

새 항목 D 추가:
→ 가장 오래 전에 들어온 A를 제거
┌─────────────────────────┐
│ [B] [C] [D]             │
└─────────────────────────┘
```

### Java 구현 (LinkedList 기반)

```java
public class FifoCache<K, V> {
    private final int capacity;
    private final Queue<K> queue = new LinkedList<>();
    private final Map<K, V> map = new HashMap<>();

    public FifoCache(int capacity) {
        this.capacity = capacity;
    }

    public V get(K key) {
        return map.get(key);  // 순서 변경 없음
    }

    public void put(K key, V value) {
        if (map.containsKey(key)) {
            map.put(key, value);  // 값만 갱신, 순서 유지
            return;
        }
        if (map.size() >= capacity) {
            K oldest = queue.poll();   // 가장 오래된 키
            map.remove(oldest);        // 제거
        }
        queue.offer(key);
        map.put(key, value);
    }
}
```

### 한계: Belady's Anomaly

FIFO는 **캐시 크기를 늘려도 히트율이 오히려 낮아지는** Belady's Anomaly 현상이 발생할 수 있다. 또한 자주 사용되는 오래된 항목도 무조건 버리는 문제가 있다.

```
접근 패턴: A B C D A B E A B C D E
캐시 크기 3: 히트 횟수 = 0 (최악)
캐시 크기 4: 히트 횟수 = 2 (더 나쁠 수 있음)
```

### 적합한 사용 사례

- 접근 패턴이 완전히 랜덤한 경우
- 구현 단순성이 최우선인 경우
- 실무에서는 거의 사용하지 않음

---

## LRU — Least Recently Used

### 구조와 동작

> 비유: 책상 위에 책을 쌓아둘 때, 가장 오래 손대지 않은 책을 맨 아래로 밀어내는 방식이다. 최근에 읽은 책일수록 위에 있다.

**가장 최근에 사용되지 않은** 항목을 버린다. "최근에 사용됐다면 곧 다시 사용될 가능성이 높다"는 **시간적 지역성(Temporal Locality)** 원리에 기반한다.

```
초기 상태 (최근 사용 순서: A → B → C, C가 가장 최근)
[LRU: A] ← ← ← ← ← [MRU: C]
  A    B    C

접근: B
[LRU: A] ← ← ← ← ← [MRU: B]
  A    C    B

새 항목 D 추가 (공간 없음):
→ LRU(A) 제거, D를 MRU 위치에 추가
[LRU: C] ← ← ← ← ← [MRU: D]
  C    B    D
```

### DoublyLinkedList + HashMap 구현

O(1) get과 put을 달성하는 표준 구현이다.

```java
public class LruCache<K, V> {
    private final int capacity;
    private final Map<K, Node<K, V>> map = new HashMap<>();
    private final Node<K, V> head = new Node<>(null, null); // dummy
    private final Node<K, V> tail = new Node<>(null, null); // dummy

    public LruCache(int capacity) {
        this.capacity = capacity;
        head.next = tail;
        tail.prev = head;
    }

    public V get(K key) {
        Node<K, V> node = map.get(key);
        if (node == null) return null;
        moveToFront(node);  // 접근 시 MRU로 이동
        return node.value;
    }

    public void put(K key, V value) {
        Node<K, V> node = map.get(key);
        if (node != null) {
            node.value = value;
            moveToFront(node);
            return;
        }
        if (map.size() >= capacity) {
            // LRU 제거 (tail.prev = 가장 오래된 항목)
            Node<K, V> lru = tail.prev;
            removeNode(lru);
            map.remove(lru.key);
        }
        Node<K, V> newNode = new Node<>(key, value);
        addToFront(newNode);
        map.put(key, newNode);
    }

    private void moveToFront(Node<K, V> node) {
        removeNode(node);
        addToFront(node);
    }

    private void removeNode(Node<K, V> node) {
        node.prev.next = node.next;
        node.next.prev = node.prev;
    }

    private void addToFront(Node<K, V> node) {
        node.next = head.next;
        node.prev = head;
        head.next.prev = node;
        head.next = node;
    }

    static class Node<K, V> {
        K key;
        V value;
        Node<K, V> prev, next;

        Node(K key, V value) {
            this.key = key;
            this.value = value;
        }
    }
}
```

### LRU의 시간 복잡도

| 연산 | 시간 복잡도 |
|------|-------------|
| get  | O(1)        |
| put  | O(1)        |
| evict| O(1)        |

### LRU의 한계: Cache Pollution (오염)

```
캐시 크기: 3, 자주 쓰이는 핵심 데이터: A, B, C
접근 패턴: A B C [스캔: D E F G H] A B C

스캔 이후 상태:
[LRU: F] ← G ← [MRU: H]

→ 핵심 데이터 A, B, C가 전부 밀려남!
→ 다음 A, B, C 접근은 전부 Cache Miss
```

한 번의 대량 스캔(Full Table Scan, Batch Job 등)이 캐시 전체를 오염시킬 수 있다. 이를 **Cache Pollution** 또는 **Scan Resistance 부재**라 한다.

---

## LFU — Least Frequently Used

### 구조와 동작

> 비유: 도서관에서 대출 횟수가 가장 적은 책을 폐기하는 방식이다. 자주 빌려가는 인기 책은 오래 보관된다. 단, 오래전 인기작이 지금도 반납 안 된다는 문제가 있다.

**사용 빈도가 가장 낮은** 항목을 버린다. "자주 사용된 항목은 앞으로도 자주 사용될 것"이라는 **빈도적 지역성(Frequency-based Locality)** 원리에 기반한다.

```
항목별 접근 빈도:
A: 10회  B: 3회  C: 7회  D: 1회

새 항목 E 추가 시 → D(1회) 제거
```

### HashMap + TreeMap 구현

```java
public class LfuCache<K, V> {
    private final int capacity;
    private final Map<K, V> valueMap = new HashMap<>();
    private final Map<K, Integer> countMap = new HashMap<>();
    // 빈도 → 해당 빈도의 키 목록 (LRU 순서 유지)
    private final TreeMap<Integer, LinkedHashSet<K>> freqMap = new TreeMap<>();
    private int minFreq = 0;

    public LfuCache(int capacity) {
        this.capacity = capacity;
    }

    public V get(K key) {
        if (!valueMap.containsKey(key)) return null;
        incrementCount(key);
        return valueMap.get(key);
    }

    public void put(K key, V value) {
        if (capacity <= 0) return;
        if (valueMap.containsKey(key)) {
            valueMap.put(key, value);
            incrementCount(key);
            return;
        }
        if (valueMap.size() >= capacity) {
            // 최소 빈도 키 중 가장 오래된 것 제거
            LinkedHashSet<K> minFreqKeys = freqMap.get(minFreq);
            K evictKey = minFreqKeys.iterator().next();
            minFreqKeys.remove(evictKey);
            if (minFreqKeys.isEmpty()) freqMap.remove(minFreq);
            valueMap.remove(evictKey);
            countMap.remove(evictKey);
        }
        valueMap.put(key, value);
        countMap.put(key, 1);
        freqMap.computeIfAbsent(1, k -> new LinkedHashSet<>()).add(key);
        minFreq = 1;
    }

    private void incrementCount(K key) {
        int count = countMap.get(key);
        countMap.put(key, count + 1);
        freqMap.get(count).remove(key);
        if (freqMap.get(count).isEmpty()) {
            freqMap.remove(count);
            if (minFreq == count) minFreq++;
        }
        freqMap.computeIfAbsent(count + 1, k -> new LinkedHashSet<>()).add(key);
    }
}
```

### LFU의 한계

**1. Cache Aging (노화 문제)**

```
과거에 자주 쓰였지만 이제는 쓰이지 않는 항목이 높은 빈도 카운트 때문에
오랫동안 캐시를 점유한다.

예시:
- 구 이벤트 상품 Z: 옛날에 10,000회 접근 → 빈도 10,000
- 신상품 W: 오늘 5회 접근 → 빈도 5
→ W가 먼저 추방됨. Z는 이제 전혀 쓰이지 않아도 캐시에 남음.
```

**2. 새 항목 불이익 (Low Frequency Penalty)**

새로 추가된 항목은 빈도가 1이므로 즉시 추방 대상이 된다. 처음 한 번 접근한 것이 향후 자주 쓰일 항목이어도 살아남기 어렵다.

---

## TinyLFU

### LFU의 문제를 해결하는 근사 빈도 카운팅

TinyLFU는 모든 키의 정확한 빈도를 저장하는 대신, **Count-Min Sketch**라는 확률적 자료구조로 **메모리 효율적**으로 빈도를 추정한다.

### Count-Min Sketch

```
Count-Min Sketch: w(열) × d(행) 행렬

       h1(k)  h2(k)  h3(k)  h4(k)
       ↓      ↓      ↓      ↓
Row 0: [3] [1] [4] [1] [5] [9] [2] [6]
Row 1: [2] [7] [1] [8] [2] [8] [1] [8]
Row 2: [1] [4] [1] [4] [2] [1] [3] [5]
Row 3: [6] [2] [6] [4] [3] [3] [8] [3]

키 k의 빈도 추정 = min(Row0[h1(k)], Row1[h2(k)], Row2[h3(k)], Row3[h4(k)])
```

- 각 키를 d개의 해시 함수로 d개 행의 서로 다른 위치에 기록
- **읽기**: d개 위치의 값 중 최솟값 = 빈도 추정 (항상 실제 이상)
- **쓰기**: d개 위치의 카운터를 모두 증가
- **공간**: 정확한 HashMap 대비 수백 배 적은 메모리 사용

```java
// 개념적 구현 (Caffeine 내부 유사 로직)
public class CountMinSketch {
    private final int width;
    private final int depth;
    private final long[][] table;

    public CountMinSketch(int width, int depth) {
        this.width = width;
        this.depth = depth;
        this.table = new long[depth][width];
    }

    public void increment(long key) {
        for (int i = 0; i < depth; i++) {
            int index = hash(key, i) % width;
            table[i][index]++;
        }
    }

    public long estimate(long key) {
        long min = Long.MAX_VALUE;
        for (int i = 0; i < depth; i++) {
            int index = hash(key, i) % width;
            min = Math.min(min, table[i][index]);
        }
        return min;
    }

    private int hash(long key, int seed) {
        // 각 행마다 다른 해시 함수 사용
        return Long.hashCode(key ^ (seed * 0x9e3779b97f4a7c15L));
    }
}
```

### 빈도 초기화 (Aging / Decay)

TinyLFU는 **주기적으로 모든 카운터를 절반으로 줄인다(Aging)**. 이를 통해 LFU의 Cache Aging 문제를 해결한다.

```
N번의 접근마다 전체 카운터 /= 2 수행

Before Aging:
구 항목 Z: 10,000  신 항목 W: 50

After Aging (N번마다):
구 항목 Z: 312     신 항목 W: 1   (약 5회 Aging 후)
→ Z의 과거 영향력이 점점 희석됨
```

---

## Window TinyLFU (W-TinyLFU) — Caffeine이 사용하는 알고리즘

> 비유: 신입사원(새 항목)은 수습 구역(Window Cache)에서 일단 기회를 받는다. 능력이 검증되면 핵심 인재(Protected)로 승진하고, 그렇지 않으면 퇴출(Eviction) 후보(Probation)로 내려간다.

W-TinyLFU는 Caffeine의 핵심 알고리즘으로, **LRU의 새 항목 친화성**과 **LFU의 빈도 기반 판단**을 결합한다.

### 전체 구조

<div class="mermaid">
graph TD
    NEW["새 항목 진입"] --> WC
    subgraph TOTAL["전체 캐시 공간"]
        WC["Window Cache (전체 1%)<br/>LRU 방식 · 새 항목 진입"]
        subgraph MAIN["Main Cache (전체 99%)"]
            PROT["Protected (Main의 80%)<br/>자주 쓰이는 항목"]
            PROB["Probation (Main의 20%)<br/>추방 후보 · LRU 방식"]
        end
    end
    WC -->|"TinyLFU Admission Filter 통과"| PROB
    PROB -->|"재접근 시 승진"| PROT
    PROT -->|"초과 시 강등"| PROB
    PROB -->|"추방 결정"| EVICT["Eviction"]
</div>

### 상세 동작 흐름

#### 1. 새 항목 진입

```
새 항목 X 접근 (Cache Miss)
         ↓
Window Cache에 진입 (LRU 방식)
         ↓
Window Cache 용량 초과?
    ↓ YES
Window LRU Victim(W) 선출
         ↓
TinyLFU Admission Filter 판정:
  estimate(W) > estimate(Main Probation LRU Victim(M))?
    ↓ YES           ↓ NO
  W → Main        W 제거
  M 제거          M 유지
```

#### 2. Main Cache 내부 승진/강등

```
Probation 항목이 접근되면:
  → Protected로 승진

Protected 항목이 초과되면:
  → 가장 오래된 Protected 항목이 Probation으로 강등

Probation 항목이 추방될 때:
  → TinyLFU가 Window Victim과 비교하여 생존 여부 결정
```

#### 3. 전체 흐름 다이어그램

```
요청 → 캐시 조회
    ├── Hit: 항목 반환 + TinyLFU 빈도 카운터 증가
    │         ├── Probation 항목이면 Protected로 승진
    │         └── Protected 항목이면 LRU 순서만 갱신
    │
    └── Miss: 데이터 소스에서 로드
              ↓
          Window Cache에 삽입
              ↓
          Window 용량 초과 시:
              TinyLFU가 Window Victim vs Main Victim 비교
              → 더 자주 쓰인 항목이 Main에 진입
```

### W-TinyLFU가 우수한 이유

**LRU의 Cache Pollution 방지**

```
스캔 데이터 D, E, F, G, H 접근:
→ Window Cache에는 들어오지만, 빈도가 낮아 TinyLFU Admission 통과 못 함
→ Main Cache의 핵심 데이터 A, B, C는 안전하게 유지
```

**LFU의 새 항목 불이익 해결**

```
새 항목 X: Window Cache에서 LRU 방식으로 일정 기간 보호
→ 빈도를 쌓을 기회 제공
→ 충분한 빈도가 생기면 Main Cache로 진입
```

**Aging으로 Cache Aging 해결**

```
N번 접근마다 Count-Min Sketch 전체 카운터를 절반으로 감소
→ 오래된 고빈도 항목의 과거 이력이 희석
→ 최근 트렌드를 더 잘 반영
```

---

## ARC — Adaptive Replacement Cache

### 구조

ARC는 **LRU와 LFU를 동적으로 균형 조정**하는 알고리즘이다. IBM 연구소에서 개발했으며, ZFS 파일시스템에서 사용한다.

```
ARC 내부 구조 (총 4개 목록):

┌─────────────────────────────────────────────────────────────────┐
│  T1 (최근 한 번 접근)  │  T2 (두 번 이상 접근)                │
│  LRU 방식              │  LFU+LRU 혼합                        │
├─────────────────────────────────────────────────────────────────┤
│  B1 (T1에서 추방된      │  B2 (T2에서 추방된                   │
│       항목의 Ghost)     │       항목의 Ghost)                   │
└─────────────────────────────────────────────────────────────────┘

실제 데이터: T1 + T2
Ghost 정보:  B1 + B2 (키만 보관, 값 없음)
```

### 동작 원리

```
새 항목 → T1에 진입 (LRU 방식)

T1 항목이 재접근 → T2로 승진 (LFU 특성)

T1이 가득 차서 항목 추방 → B1(Ghost)에 키 기록

T2가 가득 차서 항목 추방 → B2(Ghost)에 키 기록

B1의 Ghost가 히트됨 (T1 Miss 발생):
→ T1 비율 증가, T2 비율 감소 (최근성 중시 방향으로 적응)

B2의 Ghost가 히트됨 (T2 Miss 발생):
→ T2 비율 증가, T1 비율 감소 (빈도성 중시 방향으로 적응)
```

### ARC의 자기 적응 특성

```
워크로드가 바뀌면 ARC가 자동으로 균형을 조정:

순차 스캔 워크로드 → B2 Ghost 히트 증가 → T2(빈도) 비율 증가
랜덤 접근 워크로드 → B1 Ghost 히트 증가 → T1(최근) 비율 증가
```

### Java에서의 ARC

ARC는 특허 문제로 일부 환경에서 사용이 제한된다. Java 라이브러리에서는 W-TinyLFU(Caffeine)가 더 나은 성능을 보이므로, 실무에서는 ARC보다 Caffeine을 선택한다.

---

## TTL 기반 만료 vs 용량 기반 교체

캐시 항목이 제거되는 방식은 크게 두 가지다.

### TTL (Time To Live) — 시간 기반 만료

```
설정: expireAfterWrite = 10분

타임라인:
0분: 항목 A 저장
10분: A 만료 (접근 여부 무관)
10분 01초: A에 접근 → Cache Miss → DB 조회
```

#### expireAfterWrite vs expireAfterAccess

```
expireAfterWrite:
  저장 시점부터 N분 후 만료
  → 데이터 신선도 보장 (DB 변경 후 최대 N분 내 반영)

expireAfterAccess:
  마지막 접근 시점부터 N분 후 만료
  → 자주 쓰이는 항목은 오래 유지됨
  → 사용되지 않는 항목만 제거

예시 (10분 TTL):
expireAfterWrite:  [저장]──────10분──────[만료]
expireAfterAccess: [저장]──5분──[접근]──10분──[만료]
                                         ↑ 접근 시점부터 다시 10분
```

#### refreshAfterWrite — 만료 없는 백그라운드 갱신

```java
Caffeine.newBuilder()
    .refreshAfterWrite(5, TimeUnit.MINUTES)  // 5분마다 백그라운드 갱신
    .build(key -> loadFromDB(key));          // CacheLoader 필수

// 5분 후 접근:
// → 오래된 값 즉시 반환 (Cache Hit)
// → 백그라운드에서 새 값 로드 시작
// → 다음 접근 시 새 값 반환
```

### 용량 기반 교체 (Eviction)

```
설정: maximumSize = 1000

1001번째 항목 추가 시 → Eviction 알고리즘이 한 항목 제거
                         (TTL과 무관하게)
```

### TTL vs Eviction 조합 전략

```
TTL만 설정:
→ 메모리 무한 증가 가능 (항목이 만료되기 전 계속 추가)
→ 트래픽 급증 시 위험

최대 크기만 설정:
→ 오래된 데이터가 영구히 캐시에 남을 수 있음
→ 데이터 신선도 보장 불가

TTL + 최대 크기 (권장):
→ 크기 초과 시 Eviction + 시간 초과 시 만료
→ 두 가지 안전장치로 메모리 보호 + 신선도 보장
```

```java
// 권장 조합
Caffeine.newBuilder()
    .maximumSize(10_000)                      // 최대 10,000개
    .expireAfterWrite(10, TimeUnit.MINUTES)   // 10분 TTL
    .build();
```

---

## 각 알고리즘별 히트율 비교

### 실험 조건

- Zipf 분포 (현실적인 핫스팟 접근 패턴, α=1.0)
- 캐시 크기 = 전체 데이터의 10%
- 10,000,000회 접근

```
알고리즘          히트율    특징
─────────────────────────────────────────────
W-TinyLFU        ~93%     Caffeine 사용
ARC              ~91%     동적 자기 적응
TinyLFU (pure)   ~90%     순수 빈도 기반
LFU              ~88%     Cache Aging 문제 있음
LRU              ~85%     Cache Pollution 문제 있음
FIFO             ~78%     단순, 성능 낮음
Random           ~72%     랜덤 선택
```

### 워크로드 유형별 최적 알고리즘

```
워크로드 유형                  최적 알고리즘
─────────────────────────────────────────────
Zipf (핫스팟 집중)            W-TinyLFU (Caffeine)
Loop (순환 접근)              ARC
OLTP (혼합 접근)              W-TinyLFU
단순 LRU 친화적 워크로드      LRU
대용량 순차 스캔 포함         W-TinyLFU (스캔 저항성)
```

### 히트율 개선이 실제 성능에 미치는 영향

```
가정: DB 조회 = 10ms, 캐시 조회 = 0.1ms, 초당 1,000 요청

히트율 85% (LRU):
  Cache Hit:  850 req/s × 0.1ms = 85ms 총 처리 시간
  DB 조회:    150 req/s × 10ms  = 1,500ms 총 DB 처리
  평균 응답:  (85 + 1,500) / 1,000 = 1.585ms

히트율 93% (W-TinyLFU):
  Cache Hit:  930 req/s × 0.1ms = 93ms
  DB 조회:     70 req/s × 10ms  = 700ms
  평균 응답:  (93 + 700) / 1,000 = 0.793ms

→ DB 부하 53% 감소, 평균 응답 시간 50% 개선
```

---

## 실무 알고리즘 선택 가이드

### 결론 요약표

| 알고리즘 | 히트율 | 구현 복잡도 | 메모리 오버헤드 | 권장 상황 |
|----------|--------|-------------|-----------------|-----------|
| W-TinyLFU | 최상 | 낮음 (Caffeine 사용) | 낮음 | **대부분의 경우** |
| ARC | 상 | 중간 | 중간 | 워크로드 패턴이 자주 바뀌는 경우 |
| LRU | 중 | 낮음 | 낮음 | 시간적 지역성이 강한 경우 |
| LFU | 중 | 중간 | 중간 | 장기 빈도 패턴이 안정적인 경우 |
| FIFO | 낮음 | 매우 낮음 | 최소 | 구현 단순성이 절대 우선인 경우 |

### 실무 의사결정 트리

```
새 프로젝트에서 로컬 캐시 알고리즘 선택
              ↓
   Java/Spring 환경인가?
   ↓ YES              ↓ NO
Caffeine 사용       Redis / 플랫폼 기본값 사용
(W-TinyLFU)

Caffeine 사용 시 추가 고려:
              ↓
   캐시 크기 > JVM Heap의 30%?
   ↓ YES              ↓ NO
Ehcache Off-Heap   Caffeine Heap만으로 충분
   +  W-TinyLFU
   (Caffeine이 내부적으로 사용)

              ↓
   재시작 후 캐시 유지 필요?
   ↓ YES              ↓ NO
Ehcache Disk Tier   설정 완료
```

### Caffeine에서 알고리즘이 추상화되는 이유

실무에서 W-TinyLFU를 직접 구현할 필요는 없다. Caffeine을 사용하면 자동으로 적용된다.

```java
// 이 설정만으로 W-TinyLFU가 자동 적용됨
Cache<String, Product> cache = Caffeine.newBuilder()
    .maximumSize(10_000)
    .expireAfterWrite(10, TimeUnit.MINUTES)
    .build();
```

알고리즘의 동작 원리를 이해하는 것은:
1. **캐시 크기 설정** 시 근거 있는 결정을 내리기 위해
2. **히트율 저하** 시 원인을 분석하기 위해
3. **특수한 워크로드** (스캔, 배치 등)에서 캐시 오염을 예방하기 위해

중요하다.

---

## 알고리즘별 동작 비교 — 같은 접근 패턴으로 시뮬레이션

### 접근 패턴

캐시 크기 3, 접근 순서: `A B C D A B C D A A B`

### FIFO

```
접근: A B C | D A B C D A A B
진입: A B C  D A B C D A A B

Step  접근  캐시상태     결과
1     A    [A]          Miss
2     B    [A,B]        Miss
3     C    [A,B,C]      Miss
4     D    [B,C,D]      Miss (A 제거)
5     A    [C,D,A]      Miss (B 제거)
6     B    [D,A,B]      Miss (C 제거)
7     C    [A,B,C]      Miss (D 제거)
8     D    [B,C,D]      Miss (A 제거)
9     A    [C,D,A]      Miss (B 제거)
10    A    [C,D,A]      Hit
11    B    [D,A,B]      Miss (C 제거)

Hit: 1/11 = 9%
```

### LRU

```
Step  접근  캐시상태(MRU→LRU)  결과
1     A    [A]                Miss
2     B    [B,A]              Miss
3     C    [C,B,A]            Miss
4     D    [D,C,B]            Miss (A 제거)
5     A    [A,D,C]            Miss (B 제거)
6     B    [B,A,D]            Miss (C 제거)
7     C    [C,B,A]            Miss (D 제거)
8     D    [D,C,B]            Miss (A 제거)
9     A    [A,D,C]            Miss (B 제거)
10    A    [A,D,C]            Hit
11    B    [B,A,D]            Miss (C 제거)

Hit: 1/11 = 9%  ← 이 패턴(순환)에서 LRU는 FIFO와 동일
```

### LFU

```
Step  접근  캐시상태(항목:빈도)  결과
1     A    {A:1}               Miss
2     B    {A:1,B:1}           Miss
3     C    {A:1,B:1,C:1}       Miss
4     D    {B:1,C:1,D:1}       Miss (A 제거, 빈도 동일 시 먼저 들어온 것)
5     A    {B:1,C:1,A:1}       Miss (D 제거)
6     B    {C:1,A:1,B:2}       Hit  ← B가 이미 캐시에
   → 아니다, B가 없음 → Miss  {A:1,B:1,C:1} 중 C 제거 → {A:1,B:2}
   실제: B가 있으므로 Hit. 재계산:
   Step 4: D → 빈도 최소(A:1,B:1,C:1) 중 최초진입 A 제거 → {B:1,C:1,D:1}
   Step 5: A → 최소빈도 중 최초진입 B 제거 → {C:1,D:1,A:1}
   Step 6: B → 최소빈도 중 최초진입 C 제거 → {D:1,A:1,B:1}
   Step 7: C → 최소빈도 중 최초진입 D 제거 → {A:1,B:1,C:1}
   Step 8: D → 최소빈도 중 최초진입 A 제거 → {B:1,C:1,D:1}
   Step 9: A → 최소빈도 중 최초진입 B 제거 → {C:1,D:1,A:1}
   Step10: A → Hit! → {C:1,D:1,A:2}
   Step11: B → 최소빈도(C:1) 제거 → {D:1,A:2,B:1}

Hit: 1/11 = 9%  ← 순환 패턴에서 LFU도 좋지 않음
```

### 결론: 순환 접근 패턴의 어려움

위 시뮬레이션처럼 **캐시 크기보다 데이터 종류가 딱 하나 많은 순환 패턴**은 어떤 알고리즘도 히트율을 높이기 어렵다. 이 경우 캐시 크기를 늘리는 것이 유일한 해결책이다.

W-TinyLFU는 이런 극단적 패턴에서는 다른 알고리즘과 비슷하지만, **Zipf 분포**처럼 현실적인 핫스팟이 있는 패턴에서 압도적인 성능을 보인다.
