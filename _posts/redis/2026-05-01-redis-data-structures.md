---
title: "Redis 자료구조와 명령어"
categories:
- REDIS
toc: true
toc_sticky: true
toc_label: 목차
---

## 개요

Redis는 단순한 키-값 저장소가 아니라 **다양한 자료구조**를 네이티브로 지원한다. 각 자료구조는 특정 문제에 최적화된 명령어를 제공하며, 올바른 자료구조를 선택하는 것이 성능의 핵심이다.

| 자료구조 | 특징 | 주요 사용 사례 |
|---------|------|--------------|
| String | 범용 바이너리 안전 값 | 캐시, 카운터, 세션 |
| List | 순서 있는 연결 리스트 | 메시지 큐, 최근 항목 |
| Set | 중복 없는 집합 | 태그, 친구 목록, 좋아요 |
| Sorted Set | 점수 기반 정렬 집합 | 리더보드, 타임라인 |
| Hash | 필드-값 맵 | 객체 저장 |
| Bitmap | 비트 배열 | 출석체크, 플래그 |
| HyperLogLog | 확률적 유니크 카운터 | UV 집계 |
| Stream | 메시지 스트림 | 이벤트 로그, 이벤트 소싱 |
| Geospatial | 위치 좌표 인덱스 | 근처 매장 검색 |

---

## String

Redis에서 가장 기본적인 자료구조다. 텍스트, 정수, 부동소수점, 직렬화된 객체, 바이너리 데이터 등 **최대 512MB**까지 저장 가능하다.

### 주요 명령어

```bash
# 기본 저장/조회
SET key value
GET key
DEL key

# 조건부 저장
SETNX key value          # 키가 없을 때만 설정 (SET NX)
SET key value NX         # 동일한 동작
SET key value XX         # 키가 있을 때만 설정

# TTL과 함께 저장
SETEX key seconds value  # TTL(초) 설정
PSETEX key millis value  # TTL(밀리초) 설정
SET key value EX 60      # 동일한 동작
SET key value PX 60000

# 복수 키 처리
MSET key1 val1 key2 val2 key3 val3
MGET key1 key2 key3      # 여러 값 한번에 조회

# 숫자 연산
INCR key                 # +1 (원자적)
DECR key                 # -1 (원자적)
INCRBY key 5             # +5
DECRBY key 3             # -3
INCRBYFLOAT key 1.5      # 부동소수점 증가

# 문자열 조작
APPEND key "suffix"      # 값 뒤에 추가, 새 길이 반환
STRLEN key               # 값의 바이트 길이
GETRANGE key 0 3         # 부분 문자열 (0-indexed)
SETRANGE key 6 "world"   # 특정 위치부터 덮어쓰기

# 원자적 교환
GETSET key newvalue      # 이전 값 반환하고 새 값 설정 (deprecated)
GETDEL key               # 값 반환 후 삭제
GETEX key EX 60          # 값 반환 후 TTL 갱신
```

### INCR이 원자적인 이유

```bash
# 이렇게 하면 race condition 발생
GET counter  → 10
             ← 다른 클라이언트도 GET counter → 10
SET counter 11
             ← 다른 클라이언트 SET counter 11  # 둘 다 11, 하나 손실

# INCR은 Redis 싱글 스레드에서 하나의 명령어로 실행
INCR counter  # GET + 증가 + SET을 원자적으로 처리
```

Redis는 싱글 스레드로 명령어를 순차 처리하므로, `INCR`은 실행 도중 다른 명령어가 끼어들 수 없다.

### 시간복잡도

| 명령어 | 복잡도 |
|--------|--------|
| GET, SET, DEL | O(1) |
| MGET, MSET | O(N) |
| INCR, DECR | O(1) |
| APPEND | O(1) amortized |
| STRLEN | O(1) |

### 사용 사례

```java
// 캐시
redisTemplate.opsForValue().set("user:" + id, json, 1, TimeUnit.HOURS);

// 카운터
redisTemplate.opsForValue().increment("page:view:" + pageId);

// 세션
redisTemplate.opsForValue().set("session:" + token, userId, 30, TimeUnit.MINUTES);

// 분산 락
Boolean acquired = redisTemplate.opsForValue()
    .setIfAbsent("lock:" + resource, uuid, 30, TimeUnit.SECONDS);
```

---

## List

순서가 있는 **이중 연결 리스트**다. 양쪽 끝에서의 삽입/삭제가 O(1)이며, 인덱스 접근은 O(N)이다. 최대 2^32 - 1개 원소를 저장할 수 있다.

### 주요 명령어

```bash
# 삽입
LPUSH key val1 val2      # 왼쪽(head)에 추가
RPUSH key val1 val2      # 오른쪽(tail)에 추가
LINSERT key BEFORE pivot val  # 특정 값 앞에 삽입
LINSERT key AFTER  pivot val  # 특정 값 뒤에 삽입

# 조회
LRANGE key 0 -1          # 전체 조회 (-1 = 마지막)
LRANGE key 0 9           # 처음 10개
LINDEX key 0             # 특정 인덱스 조회
LLEN key                 # 리스트 길이

# 삭제
LPOP key                 # 왼쪽에서 꺼내기
RPOP key                 # 오른쪽에서 꺼내기
LPOP key 3               # 왼쪽에서 3개 꺼내기 (Redis 6.2+)
LREM key 2 "value"       # "value" 2개 삭제 (음수면 오른쪽부터)
LTRIM key 0 99           # 처음 100개만 유지, 나머지 삭제

# 수정
LSET key index value     # 특정 인덱스 값 변경

# 블로킹 팝 (큐 패턴에서 핵심)
BLPOP key1 key2 timeout  # 값이 생길 때까지 대기
BRPOP key1 key2 timeout  # 오른쪽 블로킹 팝
BLMOVE src dst LEFT RIGHT timeout  # 블로킹 이동 (Redis 6.2+)

# 이동
LMOVE src dst LEFT RIGHT # 왼쪽에서 꺼내 오른쪽에 추가 (원자적)
RPOPLPUSH src dst        # LMOVE의 이전 버전
```

### 메시지 큐 패턴

```bash
# 생산자 (오른쪽에 추가)
RPUSH queue:orders "{\"orderId\": 123}"

# 소비자 (왼쪽에서 꺼내기, 블로킹)
BLPOP queue:orders 0     # 0 = 무한 대기
```

```java
// 생산자
redisTemplate.opsForList().rightPush("queue:orders", orderJson);

// 소비자 (스레드 블로킹)
List<String> result = redisTemplate.opsForList()
    .leftPop("queue:orders", Duration.ofSeconds(30));
```

**Reliable Queue 패턴 (처리 중 실패 대비):**

```bash
# 큐에서 꺼내면서 처리 중 목록으로 이동 (원자적)
LMOVE queue:orders processing LEFT RIGHT

# 처리 완료 후 processing에서 삭제
LREM processing 1 "{\"orderId\": 123}"

# 장애 복구: processing에 남은 항목을 재처리
LRANGE processing 0 -1
```

### 시간복잡도

| 명령어 | 복잡도 |
|--------|--------|
| LPUSH, RPUSH | O(1) |
| LPOP, RPOP | O(1) |
| LRANGE | O(S+N) |
| LINDEX | O(N) |
| LLEN | O(1) |
| LREM | O(N) |

---

## Set

**중복을 허용하지 않는 비정렬 집합**이다. 집합 연산(합집합, 교집합, 차집합)을 지원하며, 최대 2^32 - 1개 원소를 저장할 수 있다.

### 주요 명령어

```bash
# 추가/삭제
SADD key member1 member2   # 추가 (이미 있으면 무시)
SREM key member1 member2   # 삭제

# 조회
SMEMBERS key               # 전체 멤버 조회 (대용량 주의)
SCARD key                  # 원소 개수
SISMEMBER key member       # 멤버 존재 여부 (0/1)
SMISMEMBER key m1 m2       # 여러 멤버 존재 여부 (Redis 6.2+)
SRANDMEMBER key 3          # 랜덤 3개 반환 (삭제 안 함)
SPOP key 3                 # 랜덤 3개 꺼내기 (삭제)

# 집합 연산
SUNION key1 key2           # 합집합
SINTER key1 key2           # 교집합
SDIFF key1 key2            # 차집합 (key1 - key2)

# 집합 연산 결과 저장
SUNIONSTORE dest key1 key2
SINTERSTORE dest key1 key2
SDIFFSTORE dest key1 key2

# 이동
SMOVE src dst member       # src에서 꺼내 dst에 추가 (원자적)

# 스캔 (대용량 안전 조회)
SSCAN key cursor [MATCH pattern] [COUNT count]
```

### 사용 사례

```java
// 태그 관리
redisTemplate.opsForSet().add("article:1:tags", "java", "redis", "spring");
Set<String> tags = redisTemplate.opsForSet().members("article:1:tags");

// 좋아요 (중복 방지)
redisTemplate.opsForSet().add("post:1:likes", userId);
Long likeCount = redisTemplate.opsForSet().size("post:1:likes");

// 팔로워 목록의 교집합 (공통 팔로워)
Set<String> commonFollowers = redisTemplate.opsForSet()
    .intersect("user:1:followers", "user:2:followers");

// 온라인 사용자 관리
redisTemplate.opsForSet().add("online:users", userId);
redisTemplate.opsForSet().remove("online:users", userId);
Boolean isOnline = redisTemplate.opsForSet().isMember("online:users", userId);
```

### 시간복잡도

| 명령어 | 복잡도 |
|--------|--------|
| SADD, SREM | O(N) — N: 추가/삭제 개수 |
| SISMEMBER | O(1) |
| SMEMBERS | O(N) |
| SCARD | O(1) |
| SUNION, SINTER, SDIFF | O(N+M) |

---

## Sorted Set (ZSet)

각 원소에 **score(실수)**를 부여하여 score 기준으로 정렬된 집합이다. 내부적으로 skip list와 hash table을 함께 사용한다.

### 주요 명령어

```bash
# 추가/수정
ZADD key score member           # 추가 (이미 있으면 score 갱신)
ZADD key NX score member        # 없을 때만 추가
ZADD key XX score member        # 있을 때만 갱신
ZADD key GT score member        # 기존 score보다 클 때만 갱신 (Redis 6.2+)
ZADD key LT score member        # 기존 score보다 작을 때만 갱신

# 삭제
ZREM key member1 member2
ZREMRANGEBYRANK key 0 9         # 순위 범위로 삭제
ZREMRANGEBYSCORE key 0 100      # score 범위로 삭제

# score 조작
ZINCRBY key 10 member           # score +10
ZSCORE key member               # score 조회

# 순위 조회
ZRANK key member                # 오름차순 순위 (0부터)
ZREVRANK key member             # 내림차순 순위

# 범위 조회
ZRANGE key 0 -1                 # score 오름차순 전체
ZRANGE key 0 -1 WITHSCORES     # score 포함
ZRANGE key 0 -1 REV             # 내림차순 (Redis 6.2+)
ZREVRANGE key 0 9               # score 내림차순 상위 10개

# score 범위 조회
ZRANGEBYSCORE key 0 100         # score 0~100 오름차순
ZRANGEBYSCORE key -inf +inf     # 전체
ZREVRANGEBYSCORE key 100 0      # score 100~0 내림차순
ZRANGEBYLEX key "[a" "[z"       # 사전순 범위 (score가 같을 때)

# 집계
ZCARD key                       # 원소 개수
ZCOUNT key 0 100                # score 범위 내 원소 수

# 집합 연산
ZUNIONSTORE dest 2 key1 key2
ZINTERSTORE dest 2 key1 key2
ZDIFFSTORE dest 2 key1 key2     # (Redis 6.2+)

# 팝
ZPOPMIN key 3                   # score 최솟값 3개 꺼내기
ZPOPMAX key 3                   # score 최댓값 3개 꺼내기
BZPOPMIN key timeout            # 블로킹

# 스캔
ZSCAN key cursor [MATCH pattern] [COUNT count]
```

### 리더보드 구현

```java
@Service
public class LeaderboardService {

    private static final String KEY = "leaderboard:game";

    // 점수 추가/갱신
    public void addScore(String userId, double score) {
        redisTemplate.opsForZSet().add(KEY, userId, score);
    }

    // 점수 증가
    public Double incrementScore(String userId, double delta) {
        return redisTemplate.opsForZSet().incrementScore(KEY, userId, delta);
    }

    // 상위 N명 조회
    public Set<ZSetOperations.TypedTuple<String>> getTopN(int n) {
        return redisTemplate.opsForZSet()
            .reverseRangeWithScores(KEY, 0, n - 1);
    }

    // 내 순위 조회 (0-indexed → +1)
    public Long getMyRank(String userId) {
        Long rank = redisTemplate.opsForZSet().reverseRank(KEY, userId);
        return rank != null ? rank + 1 : null;
    }

    // 내 점수 조회
    public Double getMyScore(String userId) {
        return redisTemplate.opsForZSet().score(KEY, userId);
    }
}
```

### 타임라인 (시간 기반 정렬)

```bash
# score에 Unix timestamp 사용
ZADD timeline:feed 1714567890 "post:123"
ZADD timeline:feed 1714567950 "post:124"

# 최신 10개 조회
ZREVRANGE timeline:feed 0 9 WITHSCORES

# 특정 시간 범위 조회
ZRANGEBYSCORE timeline:feed 1714560000 1714599999
```

### 시간복잡도

| 명령어 | 복잡도 |
|--------|--------|
| ZADD | O(log N) |
| ZREM | O(log N) |
| ZSCORE | O(1) |
| ZRANK | O(log N) |
| ZRANGE | O(log N + M) |
| ZCARD | O(1) |
| ZCOUNT | O(log N) |

---

## Hash

**필드-값 쌍의 맵**이다. 객체를 JSON으로 직렬화해 String에 저장하는 것과 달리, 개별 필드에 접근할 수 있다. 최대 2^32 - 1개 필드를 저장할 수 있다.

### 주요 명령어

```bash
# 저장
HSET key field value             # 단일 필드 설정
HSET key f1 v1 f2 v2 f3 v3     # 복수 필드 설정 (HMSET 대체)
HSETNX key field value           # 필드가 없을 때만 설정

# 조회
HGET key field                   # 단일 필드 조회
HMGET key field1 field2          # 복수 필드 조회
HGETALL key                      # 모든 필드-값 조회
HKEYS key                        # 모든 필드명
HVALS key                        # 모든 값
HLEN key                         # 필드 개수
HEXISTS key field                # 필드 존재 여부

# 삭제
HDEL key field1 field2

# 숫자 연산
HINCRBY key field 5              # 정수 증가
HINCRBYFLOAT key field 1.5       # 부동소수점 증가

# 스캔
HSCAN key cursor [MATCH pattern] [COUNT count]
```

### 객체 저장

```java
// 사용자 객체 저장
Map<String, String> userMap = new HashMap<>();
userMap.put("name", "김철수");
userMap.put("email", "kim@example.com");
userMap.put("age", "30");
redisTemplate.opsForHash().putAll("user:1", userMap);

// 단일 필드 조회
String name = (String) redisTemplate.opsForHash().get("user:1", "name");

// 복수 필드 조회
List<Object> values = redisTemplate.opsForHash()
    .multiGet("user:1", List.of("name", "email"));

// 전체 조회
Map<Object, Object> user = redisTemplate.opsForHash().entries("user:1");

// 필드 업데이트
redisTemplate.opsForHash().put("user:1", "age", "31");

// 숫자 필드 증가
redisTemplate.opsForHash().increment("user:1", "loginCount", 1);
```

### String vs Hash 비교

| 방식 | String (JSON) | Hash |
|------|--------------|------|
| 저장 | `SET user:1 {"name":"...","age":30}` | `HSET user:1 name "..." age 30` |
| 단일 필드 조회 | 전체 역직렬화 필요 | `HGET user:1 name` |
| 부분 업데이트 | 전체 덮어쓰기 | `HSET user:1 age 31` |
| 메모리 | 직렬화 오버헤드 | 필드 수가 적으면 ziplist로 최적화 |

**소규모 Hash(기본값: 128필드, 64바이트 이하)는 내부적으로 ziplist를 사용해 메모리를 효율적으로 사용한다.**

### 시간복잡도

| 명령어 | 복잡도 |
|--------|--------|
| HSET, HGET | O(1) |
| HMGET | O(N) |
| HGETALL | O(N) |
| HDEL | O(N) |
| HLEN | O(1) |

---

## Bitmap

String을 **비트 배열로 해석**한다. 최대 2^32비트(512MB)를 저장할 수 있으며, 대규모 불리언 데이터를 메모리 효율적으로 처리한다.

### 주요 명령어

```bash
# 비트 설정/조회
SETBIT key offset value      # offset 위치에 0/1 설정
GETBIT key offset            # offset 위치의 비트 조회

# 비트 카운트
BITCOUNT key                 # 1인 비트 개수
BITCOUNT key 0 3             # 바이트 범위 내 1 개수

# 비트 연산
BITOP AND dest key1 key2     # AND 연산 결과 저장
BITOP OR  dest key1 key2     # OR 연산
BITOP XOR dest key1 key2     # XOR 연산
BITOP NOT dest key           # NOT 연산

# 비트 위치 검색
BITPOS key 1                 # 첫 번째 1의 위치
BITPOS key 0                 # 첫 번째 0의 위치
BITPOS key 1 2               # 2번 바이트부터 검색

# 필드 단위 조작
BITFIELD key GET u8 0                    # 0번 위치에서 8비트 부호없는 정수 읽기
BITFIELD key SET u8 0 100               # 설정
BITFIELD key INCRBY u8 0 10            # 증가
```

### 출석 체크 구현

```java
// 키: attendance:{userId}:{year}:{month}
// offset: 일(day) - 1

// 출석 기록 (1일 = offset 0)
redisTemplate.opsForValue().setBit("attendance:user1:2026:05", 0, true);  // 1일
redisTemplate.opsForValue().setBit("attendance:user1:2026:05", 4, true);  // 5일

// 특정 날 출석 여부
Boolean attended = redisTemplate.opsForValue()
    .getBit("attendance:user1:2026:05", 0);

// 월 출석 일수
Long count = redisTemplate.execute(
    (RedisCallback<Long>) conn ->
        conn.stringCommands().bitCount("attendance:user1:2026:05".getBytes())
);
```

**메모리 효율:** 10만 명의 하루 출석 데이터 = 10만 비트 = 약 12KB

### 시간복잡도

| 명령어 | 복잡도 |
|--------|--------|
| SETBIT, GETBIT | O(1) |
| BITCOUNT | O(N) |
| BITOP | O(N) |
| BITPOS | O(N) |

---

## HyperLogLog

**확률적 알고리즘**을 사용해 집합의 원소 개수(cardinality)를 근사 추정한다. 최대 12KB의 고정 메모리로 2^64개 원소까지 추정 가능하며, 오차율은 약 0.81%다.

### 주요 명령어

```bash
PFADD key element1 element2    # 원소 추가
PFCOUNT key                    # 유니크 원소 수 추정
PFCOUNT key1 key2              # 합집합 카운트
PFMERGE dest key1 key2         # 병합 후 저장
```

### UV(Unique Visitor) 카운팅

```java
// 방문자 추가
String key = "uv:page:home:" + today;
redisTemplate.opsForHyperLogLog().add(key, userId);

// 유니크 방문자 수
Long uv = redisTemplate.opsForHyperLogLog().size(key);

// 여러 페이지 합산 UV
Long totalUv = redisTemplate.opsForHyperLogLog()
    .size("uv:page:home:2026-05-01", "uv:page:home:2026-05-02");
```

### Set vs HyperLogLog

| 항목 | Set | HyperLogLog |
|------|-----|-------------|
| 정확도 | 정확 | 약 0.81% 오차 |
| 메모리 | 원소 수에 비례 | 최대 12KB 고정 |
| 원소 조회 | 가능 | 불가능 |
| 적합 사례 | 원소 목록이 필요할 때 | 대규모 유니크 카운팅 |

---

## Stream

메시지의 **영속적 시퀀스**를 저장하는 자료구조다. Redis 5.0에서 도입되었으며, Kafka와 유사한 소비자 그룹 패턴을 지원한다.

### 주요 명령어

```bash
# 메시지 추가
XADD stream * field1 val1 field2 val2    # * = 자동 ID 생성
XADD stream 1714567890000-0 f1 v1        # 수동 ID 지정
XADD stream MAXLEN ~ 1000 * f1 v1        # 최대 1000개 유지 (근사 트림)

# 조회
XRANGE stream - +                         # 전체 조회 (오름차순)
XRANGE stream - + COUNT 10               # 최초 10개
XREVRANGE stream + - COUNT 10            # 최신 10개
XLEN stream                              # 메시지 수

# 개별/다중 스트림 읽기
XREAD COUNT 10 STREAMS stream 0          # ID 0부터 10개
XREAD COUNT 10 BLOCK 0 STREAMS stream $  # 새 메시지 블로킹 대기

# 소비자 그룹
XGROUP CREATE stream groupName $ MKSTREAM
XREADGROUP GROUP groupName consumer COUNT 10 STREAMS stream >  # 미전달 메시지
XACK stream groupName messageId          # 처리 완료 확인
XPENDING stream groupName - + 10         # 미확인 메시지 조회
XCLAIM stream groupName consumer 0 msgId # 메시지 소유권 이전

# 삭제/트림
XDEL stream messageId
XTRIM stream MAXLEN 1000
```

### 이벤트 스트리밍 구현

```java
// 이벤트 발행
Map<String, String> eventData = new HashMap<>();
eventData.put("orderId", "123");
eventData.put("status", "CREATED");
eventData.put("amount", "50000");

RecordId recordId = redisTemplate.opsForStream()
    .add("stream:orders", eventData);

// 소비자 그룹 생성
redisTemplate.opsForStream().createGroup("stream:orders", "order-service");

// 소비자 그룹으로 읽기
List<MapRecord<String, Object, Object>> records = redisTemplate.opsForStream()
    .read(Consumer.from("order-service", "consumer-1"),
          StreamReadOptions.empty().count(10),
          StreamOffset.create("stream:orders", ReadOffset.lastConsumed()));

// 처리 후 ACK
records.forEach(record -> {
    processOrder(record.getValue());
    redisTemplate.opsForStream().acknowledge("stream:orders", "order-service", record.getId());
});
```

### Kafka vs Redis Stream

| 항목 | Kafka | Redis Stream |
|------|-------|-------------|
| 영속성 | 디스크 기반, 장기 보관 | 메모리 기반, 별도 설정 필요 |
| 처리량 | 매우 높음 | 높음 |
| 소비자 그룹 | 지원 | 지원 |
| 메시지 재처리 | 오프셋으로 쉽게 가능 | 가능하지만 제한적 |
| 적합 사례 | 대규모 이벤트 파이프라인 | 애플리케이션 내 이벤트 처리 |

---

## Geospatial

내부적으로 **Sorted Set**을 사용해 위치 좌표를 저장한다. 경도(-180~180), 위도(-85.05~85.05) 범위를 지원한다.

### 주요 명령어

```bash
# 위치 추가
GEOADD key longitude latitude member
GEOADD locations 127.0276 37.4979 "강남역"
GEOADD locations 126.9784 37.5662 "홍대입구"

# 거리 계산
GEODIST key member1 member2 [m|km|mi|ft]
GEODIST locations "강남역" "홍대입구" km

# 좌표 조회
GEOPOS key member1 member2

# 반경 내 검색 (Redis 6.2+에서 GEOSEARCH 권장)
GEOSEARCH key FROMMEMBER member BYRADIUS 5 km ASC COUNT 10
GEOSEARCH key FROMLONLAT 127.0 37.5 BYRADIUS 5 km ASC COUNT 10 WITHCOORD WITHDIST

# 결과 저장
GEOSEARCHSTORE dest key FROMMEMBER member BYRADIUS 5 km ASC
```

### 근처 매장 검색

```java
// 매장 등록
redisTemplate.opsForGeo()
    .add("stores", new Point(127.0276, 37.4979), "강남점");
redisTemplate.opsForGeo()
    .add("stores", new Point(126.9784, 37.5662), "홍대점");

// 현재 위치에서 5km 이내 매장 조회
GeoSearchCommandArgs args = GeoSearchCommandArgs.newGeoSearchArgs()
    .includeDistance()
    .includeCoordinates()
    .sortAscending()
    .limit(10);

GeoResults<RedisGeoCommands.GeoLocation<String>> results = redisTemplate.opsForGeo()
    .search("stores",
            new BoundingBox(new Point(127.0, 37.5), new Distance(5, Metrics.KILOMETERS)),
            args);

results.forEach(result -> {
    System.out.println(result.getContent().getName() + ": " + result.getDistance());
});

// 두 매장 간 거리
Distance distance = redisTemplate.opsForGeo()
    .distance("stores", "강남점", "홍대점", Metrics.KILOMETERS);
```

### 시간복잡도

| 명령어 | 복잡도 |
|--------|--------|
| GEOADD | O(log N) |
| GEODIST | O(log N) |
| GEOPOS | O(log N) |
| GEOSEARCH | O(N+log M) |

---

## 자료구조별 메모리 최적화

Redis는 소규모 자료구조에 대해 **컴팩트 인코딩**을 자동으로 적용한다.

| 자료구조 | 소규모 인코딩 | 임계값 |
|---------|------------|--------|
| Hash | listpack (구 ziplist) | 128 필드, 64바이트 |
| List | listpack | 128 원소, 64바이트 |
| Set | listpack / intset | 128 원소 |
| Sorted Set | listpack | 128 원소, 64바이트 |

임계값을 초과하면 각각 hashtable, quicklist, skiplist 등 일반 인코딩으로 전환된다.

```bash
# 인코딩 확인
OBJECT ENCODING key
# → listpack, skiplist, hashtable, intset 등
```

---

## 자료구조 선택 가이드

| 요구사항 | 권장 자료구조 |
|---------|------------|
| 단순 캐시, 카운터, 세션 | String |
| 메시지 큐, 최근 N개 목록 | List |
| 중복 없는 집합, 태그, 좋아요 | Set |
| 랭킹, 점수 기반 정렬 | Sorted Set |
| 객체 저장, 부분 업데이트 | Hash |
| 대규모 불리언 플래그, 출석 | Bitmap |
| 대규모 유니크 카운팅 (UV) | HyperLogLog |
| 이벤트 스트리밍, 메시지 로그 | Stream |
| 위치 기반 검색 | Geospatial |
