---
title: "Java 컬렉션 프레임워크 완전 정리"
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---

Java 컬렉션 프레임워크(Java Collections Framework, JCF)는 데이터를 저장하고 조작하기 위한 통합된 아키텍처를 제공합니다. 인터페이스, 구현체, 알고리즘으로 구성되며, 실무에서 가장 자주 사용되는 핵심 API 중 하나입니다.

---

## 1. 컬렉션 프레임워크 전체 구조

### 인터페이스 계층도

```
java.lang.Iterable
    └── java.util.Collection
            ├── List (순서 O, 중복 O)
            │     ├── ArrayList
            │     ├── LinkedList
            │     ├── Vector
            │     └── CopyOnWriteArrayList
            │
            ├── Set (순서 X, 중복 X)
            │     ├── HashSet
            │     ├── LinkedHashSet
            │     ├── TreeSet          (SortedSet → NavigableSet)
            │     └── EnumSet
            │
            └── Queue (FIFO)
                  ├── PriorityQueue
                  ├── ArrayDeque       (Deque 구현)
                  ├── LinkedBlockingQueue
                  └── ArrayBlockingQueue

java.util.Map (Key-Value, 별도 계층)
    ├── HashMap
    ├── LinkedHashMap
    ├── TreeMap                        (SortedMap → NavigableMap)
    ├── ConcurrentHashMap
    ├── WeakHashMap
    └── Hashtable (레거시)
```

### 핵심 인터페이스 요약

| 인터페이스 | 특징 | 대표 구현체 |
|-----------|------|------------|
| `Collection` | 모든 컬렉션의 루트 | - |
| `List` | 인덱스 기반, 순서 보장, 중복 허용 | ArrayList, LinkedList |
| `Set` | 중복 불허, 순서 미보장(구현체마다 다름) | HashSet, TreeSet |
| `Queue` | FIFO 큐, offer/poll/peek | PriorityQueue, ArrayDeque |
| `Deque` | 양방향 큐 (Double Ended Queue) | ArrayDeque, LinkedList |
| `Map` | Key-Value 쌍, Key 중복 불허 | HashMap, TreeMap |

---

## 2. List 구현체

### 2-1. ArrayList

가장 많이 사용되는 List 구현체로, **내부적으로 Object 배열**을 사용합니다.

#### 내부 구조

```
ArrayList 내부 배열 (초기 capacity = 10)

index:  [0]   [1]   [2]   [3]   [4]   [5]   [6]   [7]   [8]   [9]
data:  ["A"] ["B"] ["C"] ["D"]  null  null  null  null  null  null
                                 ↑
                               size=4 (실제 원소 수)
                               capacity=10 (배열 크기)
```

#### 동적 확장 (grow)

배열이 꽉 차면 새로운 배열을 생성하고 기존 데이터를 복사합니다.

```
기존 배열 (capacity=10, 가득 참)
[0][1][2][3][4][5][6][7][8][9]

새 배열 생성 (capacity = oldCapacity + oldCapacity >> 1 = 15)
[0][1][2][3][4][5][6][7][8][9][10][11][12][13][14]
                                ← 복사 후 새 원소 추가 →
```

Java 소스 코드 (OpenJDK):
```java
private Object[] grow(int minCapacity) {
    int oldCapacity = elementData.length;
    if (oldCapacity > 0 || elementData != DEFAULTCAPACITY_EMPTY_ELEMENTDATA) {
        int newCapacity = ArraysSupport.newLength(oldCapacity,
                minCapacity - oldCapacity, /* minimum growth */
                oldCapacity >> 1           /* preferred growth: 1.5배 */);
        return elementData = Arrays.copyOf(elementData, newCapacity);
    } else {
        return elementData = new Object[Math.max(DEFAULT_CAPACITY, minCapacity)];
    }
}
```

#### 시간복잡도

| 연산 | 시간복잡도 | 설명 |
|------|-----------|------|
| `add(E e)` | O(1) amortized | 배열 끝에 추가. 확장 시 O(n)이지만 분할 상환 O(1) |
| `add(int i, E e)` | O(n) | i 이후 원소를 전부 한 칸 이동 |
| `get(int i)` | O(1) | 인덱스 직접 접근 |
| `remove(int i)` | O(n) | i 이후 원소를 한 칸 앞으로 이동 |
| `contains(Object o)` | O(n) | 순차 탐색 |
| `size()` | O(1) | 필드 참조 |

#### 코드 예제

```java
import java.util.ArrayList;
import java.util.List;

List<String> list = new ArrayList<>(16); // 초기 capacity 지정으로 resize 최소화
list.add("Apple");
list.add("Banana");
list.add(0, "Avocado"); // O(n): 앞 삽입은 비쌈

// 인덱스 접근 O(1)
String first = list.get(0); // "Avocado"

// 중간 삭제 O(n)
list.remove(1); // "Apple" 삭제, 이후 원소 이동

// 예측 가능한 크기라면 초기 capacity를 지정해 resize 비용 제거
List<String> optimized = new ArrayList<>(1000);
```

---

### 2-2. LinkedList

**이중 연결 리스트(Doubly Linked List)** 로 구현된 List이자 Deque입니다.

#### 내부 구조

```
head                                              tail
 ↓                                                 ↓
[prev=null | "A" | next] ↔ [prev | "B" | next] ↔ [prev | "C" | next=null]
```

각 노드(Node)는 이전/다음 노드의 참조와 데이터를 보관합니다:

```java
// LinkedList 내부 Node 클래스 (OpenJDK)
private static class Node<E> {
    E item;
    Node<E> next;
    Node<E> prev;

    Node(Node<E> prev, E element, Node<E> next) {
        this.item = element;
        this.next = next;
        this.prev = prev;
    }
}
```

#### 시간복잡도

| 연산 | 시간복잡도 | 설명 |
|------|-----------|------|
| `addFirst(E e)` / `addLast(E e)` | O(1) | head/tail 포인터만 변경 |
| `add(int i, E e)` | O(n) | i번째 노드까지 순차 탐색 후 삽입 |
| `get(int i)` | O(n) | i번째 노드까지 순차 탐색 |
| `remove(Object o)` | O(n) | 탐색 O(n) + 포인터 변경 O(1) |
| `removeFirst()` / `removeLast()` | O(1) | head/tail 포인터만 변경 |

#### ArrayList vs LinkedList 선택 기준

```java
// LinkedList가 유리한 경우: 양 끝 삽입/삭제가 빈번할 때
Deque<String> deque = new LinkedList<>();
deque.addFirst("first");  // O(1)
deque.addLast("last");    // O(1)
deque.removeFirst();      // O(1)

// ArrayList가 유리한 경우: 랜덤 접근, 순차 읽기
List<String> list = new ArrayList<>();
String val = list.get(500); // O(1) — LinkedList라면 O(n)
```

> **실무 팁**: 대부분의 경우 ArrayList가 빠릅니다. LinkedList는 캐시 지역성(cache locality)이 나쁘고, 노드마다 prev/next 포인터 오버헤드(객체 헤더 포함 약 24~32 bytes/node)가 있습니다. 큐/덱 목적이라면 `ArrayDeque`이 더 좋습니다.

---

### 2-3. Vector

`ArrayList`와 동일한 배열 기반 구조이지만, **모든 메서드에 `synchronized`** 가 붙어 있어 스레드 안전합니다.

```java
// Vector의 add 메서드 — 메서드 전체에 synchronized
public synchronized boolean add(E e) {
    modCount++;
    add(e, elementData, elementCount);
    return true;
}
```

단점: 단일 스레드 환경에서도 락을 획득해야 하므로 `ArrayList`보다 느립니다. **Java 1.0 시대 레거시 클래스**이므로 새 코드에서는 사용을 피하세요.

---

### 2-4. CopyOnWriteArrayList

**쓰기 시 배열 전체를 복사**하는 스레드 안전 List입니다. `java.util.concurrent` 패키지에 속합니다.

```
초기 상태:
  internal array → ["A", "B", "C"]
  readers ─────────────┘

add("D") 호출 시:
  1. lock 획득
  2. 새 배열 생성: ["A", "B", "C", "D"]
  3. 참조 교체: internal array → ["A", "B", "C", "D"]
  4. lock 해제
  기존 배열은 이미 참조 중인 reader가 끝날 때까지 유효

readers (동시 읽기) → 기존 배열 ["A", "B", "C"] (스냅샷)
new readers           → 새 배열  ["A", "B", "C", "D"]
```

```java
import java.util.concurrent.CopyOnWriteArrayList;

CopyOnWriteArrayList<String> cowList = new CopyOnWriteArrayList<>();
cowList.add("A");

// 읽기는 락 없음 — 매우 빠름
for (String s : cowList) {
    // 반복 중 다른 스레드가 add해도 ConcurrentModificationException 없음
    System.out.println(s);
}
```

| 특성 | CopyOnWriteArrayList | Collections.synchronizedList |
|------|---------------------|------------------------------|
| 읽기 성능 | 락 없음 (매우 빠름) | 매 읽기마다 락 |
| 쓰기 성능 | 배열 전체 복사 (느림) | 락만 획득 (상대적으로 빠름) |
| 반복 안전성 | 항상 안전 (스냅샷) | 수동으로 동기화 필요 |
| 적합한 상황 | 읽기 多, 쓰기 少 | 읽기/쓰기 균형 |

---

## 3. Set 구현체

### 3-1. HashSet

**내부적으로 `HashMap`을 사용**합니다. 원소를 HashMap의 Key로, dummy 값(`PRESENT`)을 Value로 저장합니다.

```java
// HashSet 내부 (OpenJDK)
private transient HashMap<E,Object> map;
private static final Object PRESENT = new Object();

public boolean add(E e) {
    return map.put(e, PRESENT) == null;
}
```

#### equals / hashCode 계약

HashSet의 중복 판단 과정:

```
add("Hello") 호출
    │
    ▼
hashCode() 계산 → 버킷 인덱스 결정
    │
    ▼
해당 버킷에 원소 있음?
    ├── NO  → 바로 저장 (중복 없음)
    └── YES → equals() 비교
                ├── true  → 중복! 저장 안 함
                └── false → 해시 충돌, 함께 저장
```

**계약(Contract)**:
- `a.equals(b)` 가 `true`이면 `a.hashCode() == b.hashCode()` 이어야 합니다.
- 역은 성립하지 않아도 됩니다 (해시 충돌 허용).

```java
// 잘못된 예: equals만 재정의하고 hashCode를 재정의하지 않음
class BadKey {
    String name;
    @Override
    public boolean equals(Object o) {
        return ((BadKey) o).name.equals(this.name);
    }
    // hashCode 미재정의 → Object의 기본 hashCode(메모리 주소 기반) 사용
    // equals는 같지만 hashCode가 달라 HashSet에 중복 저장됨!
}

Set<BadKey> set = new HashSet<>();
set.add(new BadKey("kim")); // hashCode = 1234
set.add(new BadKey("kim")); // hashCode = 5678 → 다른 버킷 → 중복 허용!
System.out.println(set.size()); // 2 (잘못된 결과)

// 올바른 예
class GoodKey {
    String name;
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof GoodKey)) return false;
        return name.equals(((GoodKey) o).name);
    }
    @Override
    public int hashCode() {
        return Objects.hash(name); // name 기반 hashCode
    }
}
```

#### 해시 충돌 처리 — 체이닝 → 트리화 (Java 8+)

```
Java 7 이하: 체이닝 (Linked List)

버킷[3]:  → [Node:"A"] → [Node:"X"] → [Node:"M"] → null
                          해시 충돌 시 연결 리스트로 연결

Java 8+: 충돌이 많으면 Red-Black Tree로 전환

버킷[3]:  → TreeNode (TREEIFY_THRESHOLD=8 초과 시)
                 ┌──────┴──────┐
              [Node]        [Node]
             ┌──┴──┐       ┌──┴──┐
           [Node] [Node] [Node] [Node]

장점: 최악의 경우 탐색 O(n) → O(log n)으로 개선
```

---

### 3-2. LinkedHashSet

`HashSet`을 상속하며, 내부적으로 **`LinkedHashMap`을 사용**해 **삽입 순서를 유지**합니다.

```java
Set<String> linked = new LinkedHashSet<>();
linked.add("Banana");
linked.add("Apple");
linked.add("Cherry");

System.out.println(linked); // [Banana, Apple, Cherry] — 삽입 순서 유지
// HashSet이라면: [Apple, Banana, Cherry] (순서 미보장)
```

내부적으로 이중 연결 리스트로 각 버킷의 원소들을 삽입 순서로 연결합니다.

```
Hash 버킷(빠른 조회):
  bucket[2] → "Banana"
  bucket[7] → "Apple"
  bucket[4] → "Cherry"

삽입 순서 연결 리스트(순서 유지):
  head ↔ [Banana] ↔ [Apple] ↔ [Cherry] ↔ tail
```

---

### 3-3. TreeSet

**Red-Black Tree** 기반의 `NavigableSet` 구현체입니다. 원소를 **항상 정렬된 상태**로 유지합니다.

#### Red-Black Tree 구조

```
        [5, BLACK]
       /           \
  [3, RED]       [7, RED]
  /      \       /      \
[1,BLK] [4,BLK][6,BLK] [9,BLK]

규칙:
1. 모든 노드는 RED 또는 BLACK
2. 루트는 항상 BLACK
3. RED 노드의 자식은 반드시 BLACK (RED 연속 불가)
4. 모든 경로의 BLACK 노드 수는 동일
→ 높이가 항상 O(log n) 보장
```

#### Comparable vs Comparator

```java
// 1. Comparable 구현 (자연 순서)
class Student implements Comparable<Student> {
    String name;
    int score;

    @Override
    public int compareTo(Student other) {
        return Integer.compare(this.score, other.score); // 점수 오름차순
    }
}

TreeSet<Student> byScore = new TreeSet<>();
byScore.add(new Student("Kim", 90));
byScore.add(new Student("Lee", 80));

// 2. Comparator 지정 (커스텀 순서)
TreeSet<String> byLength = new TreeSet<>(
    Comparator.comparingInt(String::length).thenComparing(Comparator.naturalOrder())
);
byLength.add("Banana");
byLength.add("Apple");
byLength.add("Fig");
System.out.println(byLength); // [Fig, Apple, Banana] — 길이 순
```

#### NavigableSet 범위 검색

```java
TreeSet<Integer> ts = new TreeSet<>(Set.of(1, 3, 5, 7, 9, 11));

System.out.println(ts.headSet(6));          // [1, 3, 5]      — 6 미만
System.out.println(ts.tailSet(6));          // [7, 9, 11]     — 6 이상
System.out.println(ts.subSet(3, 9));        // [3, 5, 7]      — [3, 9)
System.out.println(ts.floor(6));            // 5              — 6 이하 최대
System.out.println(ts.ceiling(6));          // 7              — 6 이상 최소
System.out.println(ts.higher(5));           // 7              — 5 초과 최소
System.out.println(ts.lower(5));            // 3              — 5 미만 최대
```

| 연산 | 시간복잡도 |
|------|-----------|
| `add`, `remove`, `contains` | O(log n) |
| `first`, `last` | O(log n) |
| `headSet`, `tailSet`, `subSet` | O(log n) (뷰 생성) |

---

### 3-4. EnumSet

**Enum 타입 전용** Set으로, 내부적으로 **비트 벡터(bit vector)** 를 사용합니다.

#### 왜 빠른가?

```
enum Day { MON, TUE, WED, THU, FRI, SAT, SUN }
            bit: 0    1    2    3    4    5    6

EnumSet.of(Day.MON, Day.WED, Day.FRI)
  → long 비트마스크: 0b0010101 = 21L

add(Day.SAT)    → bits |= (1L << SAT.ordinal())  → O(1)
remove(Day.MON) → bits &= ~(1L << MON.ordinal()) → O(1)
contains(Day.WED) → (bits & (1L << WED.ordinal())) != 0 → O(1)
```

- Enum 상수가 64개 이하 → `RegularEnumSet` (long 하나)
- 65개 이상 → `JumboEnumSet` (long 배열)

```java
import java.util.EnumSet;

enum Permission { READ, WRITE, EXECUTE, DELETE }

EnumSet<Permission> adminPerms = EnumSet.allOf(Permission.class);
EnumSet<Permission> readOnly   = EnumSet.of(Permission.READ);
EnumSet<Permission> noDelete   = EnumSet.complementOf(EnumSet.of(Permission.DELETE));

// 비트 연산 기반이라 모든 연산이 O(1)
adminPerms.containsAll(readOnly); // true
```

---

## 4. Map 구현체

### 4-1. HashMap

Java 컬렉션에서 가장 많이 사용되는 Map 구현체입니다.

#### 내부 해시 버킷 구조

```
HashMap 내부 (capacity=16, loadFactor=0.75)

buckets 배열:
  [0]  → null
  [1]  → [key="Alice", val=30] → null
  [2]  → null
  [3]  → [key="Bob", val=25] → [key="Carol", val=28] → null  (해시 충돌)
  [4]  → null
  ...
  [15] → null

put("Dave", 35):
  1. hash = hash("Dave") = 0x3a2f...
  2. index = hash & (capacity - 1) = hash & 15
  3. 해당 버킷에 연결 리스트/트리로 삽입
```

#### 초기 용량(initialCapacity)과 로드 팩터(loadFactor)

```java
// 기본값: capacity=16, loadFactor=0.75
HashMap<String, Integer> map = new HashMap<>();

// 리사이징 임계값: capacity × loadFactor = 16 × 0.75 = 12
// 원소가 12개를 초과하면 capacity를 2배(32)로 확장하고 rehashing
```

**리사이징 비용 예측이 가능하다면 초기 용량을 지정하세요:**

```java
// 1000개 원소를 저장할 예정이라면:
// capacity = ceil(1000 / 0.75) + 1 = 1335 → 다음 2의 거듭제곱 = 2048
int expectedSize = 1000;
int initialCapacity = (int) (expectedSize / 0.75) + 1;
HashMap<String, Integer> optimized = new HashMap<>(initialCapacity);
```

#### Java 8 트리화 (Treeify)

```java
// HashMap 상수
static final int TREEIFY_THRESHOLD = 8;   // 버킷 원소 8개 초과 시 트리화
static final int UNTREEIFY_THRESHOLD = 6; // 원소 6개 이하로 감소 시 복원
static final int MIN_TREEIFY_CAPACITY = 64; // 전체 capacity가 64 미만이면 트리화 대신 resize
```

```
충돌 7개: LinkedList 유지
  bucket[3] → N1 → N2 → N3 → N4 → N5 → N6 → N7

8번째 충돌 발생:
  capacity >= 64 이면 → TreeNode로 변환
  capacity < 64 이면  → capacity 2배 확장 (rehash로 분산)

트리화 후:
  bucket[3] → TreeNode (Red-Black Tree)
              최악의 경우 탐색: O(n) → O(log n)
```

#### 시간복잡도

| 연산 | 평균 | 최악 (모든 원소 같은 버킷) |
|------|------|--------------------------|
| `put` | O(1) | O(log n) [Java 8+, 트리화 후] |
| `get` | O(1) | O(log n) |
| `remove` | O(1) | O(log n) |
| `containsKey` | O(1) | O(log n) |

```java
Map<String, Integer> wordCount = new HashMap<>();
String[] words = {"apple", "banana", "apple", "cherry", "banana", "apple"};

for (String word : words) {
    wordCount.merge(word, 1, Integer::sum); // getOrDefault + put 보다 간결
}
System.out.println(wordCount); // {apple=3, banana=2, cherry=1}

// computeIfAbsent: 키 없을 때만 계산
Map<String, List<String>> groups = new HashMap<>();
groups.computeIfAbsent("fruits", k -> new ArrayList<>()).add("apple");
groups.computeIfAbsent("fruits", k -> new ArrayList<>()).add("banana");
// groups: {fruits=[apple, banana]}
```

---

### 4-2. LinkedHashMap — LRU 캐시 구현

`HashMap`을 상속하며, 이중 연결 리스트로 **삽입 순서** 또는 **접근 순서(accessOrder)**를 유지합니다.

```
LinkedHashMap (accessOrder=false, 삽입 순서):
  put("A") → put("B") → put("C")
  순서: A ↔ B ↔ C

LinkedHashMap (accessOrder=true, 접근 순서):
  put("A") → put("B") → put("C") → get("A")
  순서: B ↔ C ↔ A  (최근 접근이 tail로 이동)
```

#### LRU 캐시 구현

```java
import java.util.LinkedHashMap;
import java.util.Map;

public class LRUCache<K, V> extends LinkedHashMap<K, V> {
    private final int maxSize;

    public LRUCache(int maxSize) {
        // accessOrder=true: get/put 시 해당 항목을 tail(최근)으로 이동
        super(maxSize, 0.75f, true);
        this.maxSize = maxSize;
    }

    @Override
    protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
        // 크기 초과 시 가장 오래된(head) 항목 자동 제거
        return size() > maxSize;
    }
}

LRUCache<String, String> cache = new LRUCache<>(3);
cache.put("A", "val_A");
cache.put("B", "val_B");
cache.put("C", "val_C");
cache.get("A");           // A 접근 → A가 최근으로 이동: B ↔ C ↔ A
cache.put("D", "val_D"); // 용량 초과 → 가장 오래된 B 제거: C ↔ A ↔ D
System.out.println(cache.containsKey("B")); // false (evicted)
```

---

### 4-3. TreeMap

**Red-Black Tree** 기반 `NavigableMap`으로, Key를 항상 정렬된 상태로 유지합니다.

```java
TreeMap<String, Integer> scores = new TreeMap<>();
scores.put("Charlie", 85);
scores.put("Alice", 92);
scores.put("Bob", 78);

System.out.println(scores);              // {Alice=92, Bob=78, Charlie=85} — Key 오름차순
System.out.println(scores.firstKey());  // Alice
System.out.println(scores.lastKey());   // Charlie
System.out.println(scores.floorKey("Bz")); // Bob — "Bz" 이하 최대 Key
System.out.println(scores.ceilingKey("Bz")); // Charlie — "Bz" 이상 최소 Key

// 범위 조회
Map<String, Integer> sub = scores.subMap("Alice", "Charlie"); // [Alice, Charlie)
System.out.println(sub); // {Alice=92, Bob=78}

// 내림차순
NavigableMap<String, Integer> desc = scores.descendingMap();
System.out.println(desc); // {Charlie=85, Bob=78, Alice=92}
```

---

### 4-4. ConcurrentHashMap

멀티스레드 환경에서 안전한 Map입니다.

#### Java 7: 세그먼트 락(Segment Lock)

```
ConcurrentHashMap (Java 7)
  segments 배열 (기본 16개):
    [Segment-0] → 자체 ReentrantLock + 버킷 배열
    [Segment-1] → 자체 ReentrantLock + 버킷 배열
    ...
    [Segment-15] → 자체 ReentrantLock + 버킷 배열

  서로 다른 세그먼트에 속하는 put() 연산은 동시에 수행 가능
  최대 16개 스레드 동시 쓰기 가능
```

#### Java 8: CAS + synchronized (버킷 단위 락)

```
ConcurrentHashMap (Java 8+)
  단일 Node 배열 (버킷):
    [0]  → null (CAS로 첫 노드 삽입)
    [1]  → [Node] (synchronized(Node) 로 충돌 처리)
    ...

  1. 버킷이 비어있으면 → CAS (Compare-And-Swap) 로 락 없이 삽입
  2. 버킷에 원소 있으면 → 해당 버킷 head 노드에만 synchronized
     → 다른 버킷은 완전히 독립적으로 동작
```

```java
import java.util.concurrent.ConcurrentHashMap;

ConcurrentHashMap<String, Integer> map = new ConcurrentHashMap<>();

// 스레드 안전한 원자적 연산
map.put("count", 0);
map.compute("count", (k, v) -> v == null ? 1 : v + 1); // 원자적
map.merge("count", 1, Integer::sum);                    // 원자적

// putIfAbsent: 키 없을 때만 삽입 (원자적)
map.putIfAbsent("new_key", 100);

// 동시성 높은 집계
long total = map.reduceValues(1, v -> (long) v, Long::sum); // 병렬 집계
```

#### Hashtable vs Collections.synchronizedMap vs ConcurrentHashMap

| 특성 | Hashtable | synchronizedMap | ConcurrentHashMap |
|------|-----------|-----------------|-------------------|
| 락 범위 | 메서드 전체 | 메서드 전체 | 버킷 단위 |
| 동시 읽기 | 불가 | 불가 | 가능 (락 없음) |
| null Key/Value | 불허 | 허용 | 불허 |
| 성능 | 낮음 | 낮음 | 높음 |
| 추천 여부 | 레거시 | 비추천 | 권장 |

---

### 4-5. WeakHashMap

Key에 **약한 참조(WeakReference)** 를 사용하는 Map입니다.

```
일반 HashMap:
  map.put(key, value)
  key 객체를 map이 강하게 참조
  → GC가 key를 절대 수거하지 못함

WeakHashMap:
  map.put(key, value)
  key 객체를 WeakReference로 참조
  → key에 다른 강한 참조가 없으면 GC가 수거 가능
  → GC 수거 후 해당 Entry는 자동으로 map에서도 제거
```

```java
import java.util.WeakHashMap;

WeakHashMap<Object, String> cache = new WeakHashMap<>();

Object key1 = new Object();
Object key2 = new Object();
cache.put(key1, "value1");
cache.put(key2, "value2");

System.out.println(cache.size()); // 2

key1 = null; // key1에 대한 강한 참조 제거
System.gc();  // GC 힌트 (보장은 아님)

// GC 후 key1 Entry가 자동 제거될 수 있음
System.out.println(cache.size()); // 1 (또는 2, GC 타이밍에 따라)
```

**주요 사용 사례**: 메타데이터 캐시 (객체에 부가 정보를 붙이되, 객체가 사라지면 정보도 자동 제거).

---

## 5. Queue / Deque

### 5-1. PriorityQueue

**최소 힙(Min-Heap)** 으로 구현된 우선순위 큐입니다. `poll()`을 호출하면 항상 **가장 작은 원소**가 반환됩니다.

#### 힙 구조 (배열로 표현)

```
힙 배열:  [1, 3, 2, 7, 4, 5, 6]
인덱스:    0  1  2  3  4  5  6

트리로 시각화:
              1 (index 0)
            /   \
          3       2
        (1)      (2)
        / \      / \
       7   4    5   6
      (3) (4)  (5) (6)

부모 인덱스: (i-1) / 2
좌측 자식:  2*i + 1
우측 자식:  2*i + 2

규칙: 부모 ≤ 자식 (Min-Heap)
```

#### 주요 연산 시간복잡도

| 연산 | 시간복잡도 | 설명 |
|------|-----------|------|
| `offer(E e)` | O(log n) | 배열 끝에 삽입 후 sift-up |
| `poll()` | O(log n) | 루트 제거 후 sift-down |
| `peek()` | O(1) | 루트(최솟값) 조회만 |
| `contains(Object o)` | O(n) | 선형 탐색 |
| `remove(Object o)` | O(n) | 탐색 O(n) + sift O(log n) |

```java
import java.util.PriorityQueue;
import java.util.Collections;

// 기본: Min-Heap (오름차순)
PriorityQueue<Integer> minHeap = new PriorityQueue<>();
minHeap.offer(5);
minHeap.offer(1);
minHeap.offer(3);
System.out.println(minHeap.poll()); // 1 (최솟값)
System.out.println(minHeap.poll()); // 3

// Max-Heap (내림차순)
PriorityQueue<Integer> maxHeap = new PriorityQueue<>(Collections.reverseOrder());
maxHeap.offer(5);
maxHeap.offer(1);
maxHeap.offer(3);
System.out.println(maxHeap.poll()); // 5 (최댓값)

// 커스텀 우선순위: Task 처리 순서
record Task(String name, int priority) {}
PriorityQueue<Task> taskQueue = new PriorityQueue<>(
    Comparator.comparingInt(Task::priority)
);
taskQueue.offer(new Task("저우선", 10));
taskQueue.offer(new Task("고우선", 1));
taskQueue.offer(new Task("중우선", 5));
System.out.println(taskQueue.poll().name()); // "고우선"
```

---

### 5-2. ArrayDeque

**원형 배열(Circular Array)** 기반의 Deque(Double Ended Queue)입니다. Stack과 Queue 모두 대체 가능합니다.

#### 원형 배열 구조

```
capacity = 8, head = 3, tail = 6

index:  [0]   [1]   [2]   [3]   [4]   [5]   [6]   [7]
data:   null  null  null  ["A"] ["B"] ["C"] null  null
                           ↑                 ↑
                          head              tail

addFirst("Z"):
  head = (head - 1 + capacity) % capacity = 2
  elements[2] = "Z"

index:  [0]   [1]   [2]   [3]   [4]   [5]   [6]   [7]
data:   null  null  ["Z"] ["A"] ["B"] ["C"] null  null
                    ↑                        ↑
                   head                    tail

addLast("D"):
  elements[tail] = "D"
  tail = (tail + 1) % capacity = 7
```

```java
import java.util.ArrayDeque;
import java.util.Deque;

// Stack으로 사용 (LIFO)
Deque<String> stack = new ArrayDeque<>();
stack.push("first");    // addFirst()
stack.push("second");   // addFirst()
System.out.println(stack.pop()); // "second" (removeFirst())

// Queue로 사용 (FIFO)
Deque<String> queue = new ArrayDeque<>();
queue.offer("first");   // addLast()
queue.offer("second");  // addLast()
System.out.println(queue.poll()); // "first" (removeFirst())

// Stack 클래스보다 ArrayDeque를 권장하는 이유:
// - Stack은 Vector 상속 → 불필요한 synchronized 오버헤드
// - ArrayDeque는 synchronized 없음 → 단일 스레드에서 더 빠름
```

---

### 5-3. 블로킹 큐 (BlockingQueue) — 생산자-소비자 패턴

`BlockingQueue` 인터페이스는 스레드 간 안전한 데이터 교환을 위한 **블로킹 연산**을 제공합니다.

#### LinkedBlockingQueue

내부적으로 **연결 리스트** 사용. 생산자/소비자 각각 별도 Lock(putLock/takeLock)으로 동시성을 높입니다.

```java
import java.util.concurrent.LinkedBlockingQueue;

// 용량 제한 있는 큐
LinkedBlockingQueue<String> queue = new LinkedBlockingQueue<>(100);

// 생산자 스레드
Thread producer = new Thread(() -> {
    try {
        for (int i = 0; i < 200; i++) {
            queue.put("item-" + i); // 큐가 가득 차면 블로킹
        }
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    }
});

// 소비자 스레드
Thread consumer = new Thread(() -> {
    try {
        while (true) {
            String item = queue.take(); // 큐가 비면 블로킹
            System.out.println("처리: " + item);
        }
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    }
});
```

#### ArrayBlockingQueue

내부적으로 **고정 크기 배열** 사용. 단일 Lock 사용(LinkedBlockingQueue보다 처리량이 낮을 수 있음).

```java
import java.util.concurrent.ArrayBlockingQueue;

// 반드시 초기 용량 지정 필요 (고정 크기)
ArrayBlockingQueue<Integer> queue = new ArrayBlockingQueue<>(50);

// offer: 즉시 반환 (타임아웃 버전도 있음)
boolean added = queue.offer(42);                          // 가득 차면 false
boolean addedWithTimeout = queue.offer(42, 1, TimeUnit.SECONDS); // 1초 대기

// poll: 즉시 반환 (타임아웃 버전도 있음)
Integer val = queue.poll();                               // 비었으면 null
Integer valWithTimeout = queue.poll(1, TimeUnit.SECONDS); // 1초 대기
```

#### BlockingQueue 메서드 비교

| 동작 | 예외 발생 | 특수 값 반환 | 블로킹 | 타임아웃 |
|------|----------|------------|--------|--------|
| 삽입 | `add(e)` | `offer(e)` | `put(e)` | `offer(e, t, unit)` |
| 제거 | `remove()` | `poll()` | `take()` | `poll(t, unit)` |
| 조회 | `element()` | `peek()` | - | - |

---

## 6. 시간복잡도 총정리 표

### List

| 구현체 | add(끝) | add(중간) | get(index) | remove(index) | contains |
|--------|---------|----------|-----------|--------------|---------|
| ArrayList | O(1)* | O(n) | O(1) | O(n) | O(n) |
| LinkedList | O(1) | O(n) | O(n) | O(n) | O(n) |
| CopyOnWriteArrayList | O(n) | O(n) | O(1) | O(n) | O(n) |

*amortized (분할 상환)

### Set

| 구현체 | add | remove | contains | 순서 |
|--------|-----|--------|---------|------|
| HashSet | O(1)* | O(1)* | O(1)* | X |
| LinkedHashSet | O(1)* | O(1)* | O(1)* | 삽입 순서 |
| TreeSet | O(log n) | O(log n) | O(log n) | 정렬 순서 |
| EnumSet | O(1) | O(1) | O(1) | Enum 선언 순서 |

*평균 (최악 O(log n), Java 8+ 트리화)

### Map

| 구현체 | put | get | remove | containsKey | 순서 |
|--------|-----|-----|--------|------------|------|
| HashMap | O(1)* | O(1)* | O(1)* | O(1)* | X |
| LinkedHashMap | O(1)* | O(1)* | O(1)* | O(1)* | 삽입/접근 순서 |
| TreeMap | O(log n) | O(log n) | O(log n) | O(log n) | Key 정렬 |
| ConcurrentHashMap | O(1)* | O(1)* | O(1)* | O(1)* | X |
| WeakHashMap | O(1)* | O(1)* | O(1)* | O(1)* | X |

### Queue / Deque

| 구현체 | offer | poll | peek | contains |
|--------|-------|------|------|---------|
| PriorityQueue | O(log n) | O(log n) | O(1) | O(n) |
| ArrayDeque | O(1)* | O(1) | O(1) | O(n) |
| LinkedBlockingQueue | O(1) | O(1) | O(1) | O(n) |
| ArrayBlockingQueue | O(1) | O(1) | O(1) | O(n) |

---

## 7. 동시성 컬렉션 정리

### Collections.synchronizedXxx vs Concurrent 계열

```java
// 방법 1: Collections.synchronizedXxx 래퍼
List<String>  syncList = Collections.synchronizedList(new ArrayList<>());
Map<String, Integer> syncMap = Collections.synchronizedMap(new HashMap<>());

// 반복 시 반드시 수동 동기화 필요!
synchronized (syncList) {
    Iterator<String> it = syncList.iterator();
    while (it.hasNext()) {
        System.out.println(it.next());
    }
}

// 방법 2: Concurrent 계열 (권장)
import java.util.concurrent.*;

ConcurrentHashMap<String, Integer> concMap = new ConcurrentHashMap<>();
CopyOnWriteArrayList<String> cowList = new CopyOnWriteArrayList<>();
ConcurrentLinkedQueue<String> clQueue = new ConcurrentLinkedQueue<>();

// Concurrent 계열은 반복 중 수동 동기화 불필요 (약한 일관성 보장)
for (String s : cowList) {
    System.out.println(s); // 안전
}
```

### 동시성 컬렉션 선택 가이드

| 상황 | 권장 컬렉션 |
|------|------------|
| 멀티스레드 Map | `ConcurrentHashMap` |
| 읽기 多, 쓰기 少 List | `CopyOnWriteArrayList` |
| 생산자-소비자 큐 (유계) | `ArrayBlockingQueue` |
| 생산자-소비자 큐 (무계) | `LinkedBlockingQueue` |
| 동시성 단순 큐 | `ConcurrentLinkedQueue` |
| 동시성 덱 | `ConcurrentLinkedDeque` |
| 동시성 우선순위 큐 | `PriorityBlockingQueue` |

---

## 8. 실무 선택 가이드

### List 선택

```
순서가 중요한 데이터를 저장하고 싶다
         │
         ▼
  랜덤 접근(get)이 많은가?
  ├── YES → ArrayList (캐시 지역성 좋음, 대부분의 경우)
  └── NO  → 양 끝 삽입/삭제만 하는가?
                ├── YES → ArrayDeque (큐/덱 목적)
                └── NO  → ArrayList (LinkedList보다 실제로 빠른 경우 많음)
```

### Set 선택

```
중복 없는 컬렉션이 필요하다
         │
         ▼
  정렬이 필요한가?
  ├── YES → TreeSet (정렬 + 범위 검색 필요)
  └── NO  → 삽입 순서 보존이 필요한가?
                ├── YES → LinkedHashSet
                └── NO  → Enum 타입인가?
                              ├── YES → EnumSet (가장 빠름)
                              └── NO  → HashSet (기본)
```

### Map 선택

```
Key-Value 저장이 필요하다
         │
         ▼
  멀티스레드 환경인가?
  ├── YES → ConcurrentHashMap
  └── NO  → Key 정렬이 필요한가?
                ├── YES → TreeMap
                └── NO  → 순서 보존이 필요한가?
                              ├── YES → LinkedHashMap
                              │          (accessOrder=true이면 LRU 캐시)
                              └── NO  → Key가 Enum인가?
                                            ├── YES → EnumMap (비트 벡터 기반, 빠름)
                                            └── NO  → HashMap (기본)
```

### 상황별 선택 예제

```java
// 1. 대용량 데이터 순차 처리 → ArrayList
List<Record> records = new ArrayList<>(100_000);
// 이유: 연속 메모리 → CPU 캐시 적중률 높음

// 2. 이력 순서 보존 로그 → LinkedHashMap
Map<String, String> auditLog = new LinkedHashMap<>();
auditLog.put("2026-01-01", "로그인");
auditLog.put("2026-01-02", "수정");
// 삽입 순서대로 이터레이션 보장

// 3. 멤버십 체크 (수백만 건) → HashSet
Set<Long> blockedUserIds = new HashSet<>(1_000_000);
boolean isBlocked = blockedUserIds.contains(userId); // O(1)

// 4. IP 대역 범위 검색 → TreeMap
TreeMap<String, String> ipRoutes = new TreeMap<>();
ipRoutes.put("10.0.0.0", "route_A");
ipRoutes.put("192.168.0.0", "route_B");
String route = ipRoutes.floorEntry("10.0.1.5").getValue(); // 범위 매칭

// 5. 스레드 풀 작업 큐 → ArrayBlockingQueue
BlockingQueue<Runnable> workQueue = new ArrayBlockingQueue<>(200);
ThreadPoolExecutor pool = new ThreadPoolExecutor(
    4, 8, 60L, TimeUnit.SECONDS, workQueue
);

// 6. 권한 집합 → EnumSet
EnumSet<Permission> userPerms = EnumSet.of(Permission.READ, Permission.WRITE);
if (userPerms.contains(Permission.DELETE)) { /* ... */ }

// 7. 캐시 (메모리 민감) → WeakHashMap
WeakHashMap<Object, CachedData> cache = new WeakHashMap<>();
// 키 객체가 GC되면 캐시 항목도 자동 제거

// 8. 이벤트 리스너 목록 (읽기 多) → CopyOnWriteArrayList
CopyOnWriteArrayList<EventListener> listeners = new CopyOnWriteArrayList<>();
// 리스너 등록/해제는 드물고 이벤트 발생(읽기)은 빈번
```

### 컬렉션 사용 시 자주 하는 실수

```java
// 실수 1: for 루프 안에서 List.remove()
// → ConcurrentModificationException 발생
List<String> list = new ArrayList<>(Arrays.asList("A", "B", "C"));
for (String s : list) {
    if (s.equals("B")) list.remove(s); // 위험!
}
// 올바른 방법: Iterator 또는 removeIf
list.removeIf(s -> s.equals("B")); // Java 8+

// 실수 2: HashMap에 가변 객체를 Key로 사용
Map<List<Integer>, String> map = new HashMap<>();
List<Integer> key = new ArrayList<>(List.of(1, 2, 3));
map.put(key, "value");
key.add(4); // key 변경 → hashCode 변경 → map에서 찾을 수 없음!
map.get(key); // null 반환

// 실수 3: Arrays.asList() 결과에 add/remove
List<String> fixed = Arrays.asList("A", "B", "C");
fixed.add("D"); // UnsupportedOperationException!
// 올바른 방법:
List<String> mutable = new ArrayList<>(Arrays.asList("A", "B", "C"));

// 실수 4: HashMap null 처리 누락
Map<String, Integer> map2 = new HashMap<>();
int count = map2.get("key"); // NullPointerException! (auto-unboxing)
// 올바른 방법:
int count2 = map2.getOrDefault("key", 0);
```

---

## 요약

Java 컬렉션 프레임워크는 **인터페이스-구현체 분리 원칙**을 따르므로, 변수 타입은 인터페이스(`List`, `Map`, `Set`)로 선언하고 구현체는 필요에 따라 교체하는 것이 좋은 설계입니다.

```java
// 좋은 예: 인터페이스로 선언
List<String> list = new ArrayList<>();
Map<String, Integer> map = new HashMap<>();
Set<String> set = new HashSet<>();

// 나쁜 예: 구현체로 선언 (불필요한 결합도)
ArrayList<String> list2 = new ArrayList<>(); // 피하세요
```

성능 최적화가 필요하다면 **초기 capacity 지정**, **적절한 구현체 선택**, **불필요한 박싱/언박싱 제거** 순서로 접근하는 것을 권장합니다.
