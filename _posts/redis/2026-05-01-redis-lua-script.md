---
title: "Redis Lua 스크립트 동작 원리와 활용"
categories:
- REDIS
toc: true
toc_sticky: true
toc_label: 목차
---

재고 감소 로직을 생각해보자. `GET`으로 재고를 읽고, 0보다 크면 `DECR`로 줄인다. 두 명령 사이에 다른 요청이 끼어들면 재고가 -1이 되는 순간이 생긴다. 이 틈을 없애는 것이 Lua 스크립트다. 두 명령을 하나의 원자적 단위로 묶어 Redis 서버 안에서 실행한다.

## Lua 스크립트란?

> **비유**: Lua 스크립트는 은행 창구에서 "잔액 확인 후 출금" 절차를 직원이 한 자리에서 처리하는 것과 같다. 잔액 확인과 출금 사이에 다른 고객이 끼어들 수 없다. 고객(클라이언트)이 두 번 왔다 갔다 할 필요 없이 직원(Redis 서버)이 내부에서 한 번에 처리한다.

Redis는 서버 측에서 **Lua 스크립트를 실행**하는 기능을 제공한다. Redis 2.6.0부터 내장되어 있으며, 별도 설치 없이 사용 가능하다.

---

## Redis에서 Lua를 쓰는 이유

### 원자성 보장

Redis 명령어는 하나씩은 원자적이지만, **여러 명령어를 조합할 때**는 그 사이에 다른 클라이언트가 끼어들 수 있다.

```
[Client A]  GET counter  →  값: 10
[Client B]  GET counter  →  값: 10   ← 끼어듦
[Client A]  SET counter 11
[Client B]  SET counter 11           ← 둘 다 11로 설정, 하나 손실
```

Lua 스크립트는 **Redis 서버에서 단일 명령어처럼 실행**되므로, 스크립트 전체가 원자적으로 처리된다.

### 왜 원자적인가 — 싱글 스레드 모델

Redis는 **싱글 스레드**로 명령어를 처리한다. Lua 스크립트가 실행되는 동안 다른 클라이언트의 명령어는 큐에서 대기한다.

```
명령어 큐:
[GET a] → [EVAL script] → [SET b] → [GET c]
                ↑
         이 스크립트 실행 중에는 다른 명령어 처리 없음
```

따라서 스크립트 내부 로직 전체가 **인터럽트 없이 실행**된다.

### INCR이 원자적인 이유

`INCR key`는 GET → 증가 → SET의 세 단계를 **하나의 명령어**로 실행한다. 싱글 스레드 모델에서 이 명령어 실행 중에 다른 명령어가 끼어들 수 없으므로 완전히 원자적이다.

```
INCR counter
= (내부적으로) GET counter → +1 → SET counter (원자적)
```

직접 GET → SET으로 구현하면 race condition이 생기지만, 단일 명령어 INCR은 안전하다.

---

## EVAL 명령어

```
EVAL script numkeys [key [key ...]] [arg [arg ...]]
```

| 파라미터 | 설명 |
|---------|------|
| `script` | Lua 스크립트 문자열 |
| `numkeys` | KEYS 배열에 전달할 키 개수 |
| `key` | Redis 키 목록 (KEYS 배열) |
| `arg` | 추가 인자 (ARGV 배열) |

### 기본 예시

```bash
# Redis CLI에서 실행
EVAL "return 'hello'" 0

EVAL "return redis.call('set', KEYS[1], ARGV[1])" 1 mykey myvalue

EVAL "return redis.call('get', KEYS[1])" 1 mykey
```

### Java (Spring Data Redis)에서 EVAL

```java
String script = "return redis.call('set', KEYS[1], ARGV[1])";

redisTemplate.execute(
    new DefaultRedisScript<>(script, String.class),
    List.of("mykey"),   // KEYS
    "myvalue"           // ARGV
);
```

---

## EVALSHA 명령어

스크립트를 매번 전송하면 네트워크 오버헤드가 발생한다. **EVALSHA**는 스크립트를 서버에 캐싱하고 SHA1 해시로 호출한다.

```
EVALSHA sha1 numkeys [key [key ...]] [arg [arg ...]]
```

### 스크립트 캐싱 흐름

```
1. SCRIPT LOAD "return redis.call('get', KEYS[1])"
   → "e0e1f9fabfa9d353e4... " (SHA1 반환)

2. EVALSHA e0e1f9fabfa9d353e4... 1 mykey
   → 캐시된 스크립트 실행

3. SCRIPT EXISTS sha1  → [1] (존재) / [0] (없음)
4. SCRIPT FLUSH        → 모든 캐시 삭제
```

### Java에서 EVALSHA 패턴

```java
@Component
public class LuaScriptCache {

    private final StringRedisTemplate redisTemplate;
    private String scriptSha;

    // 애플리케이션 시작 시 스크립트 등록
    @PostConstruct
    public void loadScript() {
        String script = "return redis.call('get', KEYS[1])";
        scriptSha = redisTemplate.execute(
            (RedisCallback<String>) conn ->
                conn.scriptingCommands().scriptLoad(script.getBytes())
        );
    }

    public String get(String key) {
        return redisTemplate.execute(
            new DefaultRedisScript<>(/* sha 기반 */)
        );
    }
}
```

**실제로는 `DefaultRedisScript`가 SHA 캐싱을 내부적으로 처리한다.**

```java
// DefaultRedisScript는 최초 실행 시 EVALSHA를 시도하고,
// NOSCRIPT 에러 발생 시 자동으로 EVAL로 폴백한다
DefaultRedisScript<Long> redisScript = new DefaultRedisScript<>(scriptText, Long.class);
// 이후 호출부터는 자동으로 EVALSHA 사용
```

---

## Lua 문법 기초 (Redis 관점)

### 변수와 타입

```lua
-- 지역 변수 (local 필수 — 전역 변수 사용 금지)
local key = KEYS[1]
local value = ARGV[1]
local count = tonumber(ARGV[2])

-- 타입: nil, boolean, number, string, table
local flag = true
local arr = {1, 2, 3}        -- table (배열처럼 사용)
local obj = {a = 1, b = 2}  -- table (맵처럼 사용)
```

### 조건문

```lua
local val = redis.call('get', KEYS[1])

if val == false then          -- nil은 false로 처리
    return 0
elseif tonumber(val) > 100 then
    return 1
else
    return -1
end
```

### 반복문

```lua
-- 숫자 기반 반복
for i = 1, #KEYS do
    redis.call('del', KEYS[i])
end

-- 일반 while
local i = 0
while i < 10 do
    i = i + 1
end
```

### 함수 정의

```lua
local function increment(key, amount)
    local current = tonumber(redis.call('get', key)) or 0
    local new_value = current + amount
    redis.call('set', key, new_value)
    return new_value
end

return increment(KEYS[1], tonumber(ARGV[1]))
```

### 타입 변환

```lua
-- Redis는 모든 값을 string으로 반환
local count = tonumber(redis.call('get', KEYS[1]))  -- string → number
local str   = tostring(count + 1)                   -- number → string
```

---

## redis.call vs redis.pcall

### redis.call

명령어 실행 중 에러가 발생하면 **스크립트 전체가 중단**되고 에러를 반환한다.

```lua
-- WRONGTYPE 에러 시 스크립트 중단
local val = redis.call('incr', KEYS[1])  -- 키가 string이 아니면 에러
return val
```

### redis.pcall

에러를 **잡아서 처리**할 수 있다 (protected call).

```lua
local ok, err = pcall(function()
    return redis.pcall('incr', KEYS[1])
end)

-- 또는 직접 에러 테이블 확인
local result = redis.pcall('incr', KEYS[1])
if type(result) == 'table' and result.err then
    -- 에러 처리
    return {err = "increment failed: " .. result.err}
end
return result
```

**선택 기준:**

| 상황 | 권장 |
|------|------|
| 에러가 나면 모두 롤백해야 할 때 | `redis.call` |
| 일부 실패를 허용하고 계속 진행해야 할 때 | `redis.pcall` |
| 에러 메시지를 로깅하고 싶을 때 | `redis.pcall` |

---

## KEYS vs ARGV

| 항목 | KEYS | ARGV |
|------|------|------|
| **목적** | Redis 키 이름 | 추가 인자 (값, 옵션 등) |
| **접근** | `KEYS[1]`, `KEYS[2]` ... | `ARGV[1]`, `ARGV[2]` ... |
| **인덱스** | 1부터 시작 (Lua 관례) | 1부터 시작 |
| **클러스터** | 키 슬롯 결정에 사용 | 라우팅에 미사용 |

**클러스터 환경에서 중요:** Redis Cluster는 KEYS의 키들이 모두 **같은 슬롯**에 있어야 한다. 다른 슬롯의 키에 접근하면 에러가 발생한다.

```lua
-- 올바른 사용
-- EVAL script 2 key1 key2 arg1 arg2
local key1 = KEYS[1]  -- "order:1"
local key2 = KEYS[2]  -- "stock:1"
local amount = ARGV[1]
local ttl = ARGV[2]
```

---

## 실무 패턴

### 1. 분산 락 해제

```lua
-- GET → 비교 → DEL 원자 실행
-- KEYS[1] = 락 키, ARGV[1] = 락 값(UUID)
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
```

```java
private static final DefaultRedisScript<Long> RELEASE_LOCK_SCRIPT;

static {
    RELEASE_LOCK_SCRIPT = new DefaultRedisScript<>();
    RELEASE_LOCK_SCRIPT.setScriptText(
        "if redis.call('get', KEYS[1]) == ARGV[1] then " +
        "  return redis.call('del', KEYS[1]) " +
        "else " +
        "  return 0 " +
        "end"
    );
    RELEASE_LOCK_SCRIPT.setResultType(Long.class);
}

public boolean releaseLock(String key, String value) {
    Long result = redisTemplate.execute(RELEASE_LOCK_SCRIPT, List.of(key), value);
    return Long.valueOf(1L).equals(result);
}
```

---

### 2. Rate Limiting (슬라이딩 윈도우)

```lua
-- KEYS[1] = rate_limit:{userId}
-- ARGV[1] = 현재 timestamp(ms), ARGV[2] = 윈도우 크기(ms), ARGV[3] = 최대 요청 수
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

-- 윈도우 밖의 요청 제거
redis.call('zremrangebyscore', key, 0, now - window)

-- 현재 요청 수 확인
local count = redis.call('zcard', key)

if count < limit then
    -- 현재 요청 추가
    redis.call('zadd', key, now, now)
    redis.call('pexpire', key, window)
    return 1  -- 허용
else
    return 0  -- 거부
end
```

```java
@Service
public class RateLimiter {

    private static final DefaultRedisScript<Long> RATE_LIMIT_SCRIPT;

    static {
        RATE_LIMIT_SCRIPT = new DefaultRedisScript<>();
        RATE_LIMIT_SCRIPT.setScriptText(
            "local key = KEYS[1]\n" +
            "local now = tonumber(ARGV[1])\n" +
            "local window = tonumber(ARGV[2])\n" +
            "local limit = tonumber(ARGV[3])\n" +
            "redis.call('zremrangebyscore', key, 0, now - window)\n" +
            "local count = redis.call('zcard', key)\n" +
            "if count < limit then\n" +
            "  redis.call('zadd', key, now, now)\n" +
            "  redis.call('pexpire', key, window)\n" +
            "  return 1\n" +
            "else\n" +
            "  return 0\n" +
            "end"
        );
        RATE_LIMIT_SCRIPT.setResultType(Long.class);
    }

    public boolean isAllowed(String userId) {
        String key = "rate_limit:" + userId;
        long now = System.currentTimeMillis();
        long window = 60_000L;  // 1분
        long limit = 100L;      // 최대 100회

        Long result = redisTemplate.execute(
            RATE_LIMIT_SCRIPT,
            List.of(key),
            String.valueOf(now),
            String.valueOf(window),
            String.valueOf(limit)
        );
        return Long.valueOf(1L).equals(result);
    }
}
```

---

### 3. 조건부 업데이트

```lua
-- 현재 값이 예상 값과 일치할 때만 업데이트 (Compare-And-Swap)
-- KEYS[1] = 키, ARGV[1] = 예상 값, ARGV[2] = 새 값
local current = redis.call('get', KEYS[1])
if current == ARGV[1] then
    redis.call('set', KEYS[1], ARGV[2])
    return 1  -- 성공
else
    return 0  -- 실패 (값이 다름)
end
```

```java
public boolean compareAndSet(String key, String expected, String newValue) {
    String script =
        "local current = redis.call('get', KEYS[1])\n" +
        "if current == ARGV[1] then\n" +
        "  redis.call('set', KEYS[1], ARGV[2])\n" +
        "  return 1\n" +
        "else\n" +
        "  return 0\n" +
        "end";

    Long result = redisTemplate.execute(
        new DefaultRedisScript<>(script, Long.class),
        List.of(key), expected, newValue
    );
    return Long.valueOf(1L).equals(result);
}
```

---

### 4. 원자적 재고 차감

```lua
-- KEYS[1] = stock:productId
-- ARGV[1] = 차감 수량
local stock = tonumber(redis.call('get', KEYS[1]))

if stock == nil then
    return -1  -- 상품 없음
end

if stock < tonumber(ARGV[1]) then
    return -2  -- 재고 부족
end

local remaining = redis.call('decrby', KEYS[1], ARGV[1])
return remaining  -- 남은 재고 반환
```

```java
public int decrementStock(Long productId, int quantity) {
    String script =
        "local stock = tonumber(redis.call('get', KEYS[1]))\n" +
        "if stock == nil then return -1 end\n" +
        "if stock < tonumber(ARGV[1]) then return -2 end\n" +
        "return redis.call('decrby', KEYS[1], ARGV[1])";

    Long result = redisTemplate.execute(
        new DefaultRedisScript<>(script, Long.class),
        List.of("stock:" + productId),
        String.valueOf(quantity)
    );

    if (result == null || result == -1) throw new ProductNotFoundException();
    if (result == -2) throw new InsufficientStockException();
    return result.intValue();
}
```

---

### 5. 복합 카운터 (일별 + 총계 동시 업데이트)

```lua
-- KEYS[1] = daily:count:{date}:{userId}
-- KEYS[2] = total:count:{userId}
-- ARGV[1] = TTL(초)
local daily = redis.call('incr', KEYS[1])
redis.call('expire', KEYS[1], tonumber(ARGV[1]))
local total = redis.call('incr', KEYS[2])
return {daily, total}
```

```java
public long[] incrementCounters(String userId, String date) {
    String script =
        "local daily = redis.call('incr', KEYS[1])\n" +
        "redis.call('expire', KEYS[1], tonumber(ARGV[1]))\n" +
        "local total = redis.call('incr', KEYS[2])\n" +
        "return {daily, total}";

    List<Long> result = redisTemplate.execute(
        new DefaultRedisScript<>(script, List.class),
        List.of("daily:" + date + ":" + userId, "total:" + userId),
        "86400"  // 1일 TTL
    );
    return new long[]{result.get(0), result.get(1)};
}
```

---

## 스크립트 캐싱

### 동작 흐름

```
최초 호출:
  Client → EVALSHA sha1 → NOSCRIPT 에러
         → EVAL script   → 실행 + 서버에 캐시

이후 호출:
  Client → EVALSHA sha1 → 캐시 hit → 실행
```

`DefaultRedisScript`는 이 과정을 자동으로 처리한다.

### 서버 재시작 시 주의

Redis 서버가 재시작되면 **스크립트 캐시가 초기화**된다. `DefaultRedisScript`는 NOSCRIPT 에러 시 자동으로 EVAL로 폴백하므로 실용적으로는 문제가 없다.

**Redis Cluster에서** 스크립트는 명령어를 받은 노드에만 캐시된다. 다른 노드에서 EVALSHA를 호출하면 NOSCRIPT 에러가 발생할 수 있다.

---

## 디버깅

### redis-cli에서 테스트

```bash
# 직접 실행
redis-cli EVAL "return redis.call('get', KEYS[1])" 1 mykey

# 파일로 실행
redis-cli --eval /path/to/script.lua key1 key2 , arg1 arg2
# 쉼표(,) 앞이 KEYS, 뒤가 ARGV
```

### 로깅

```lua
-- redis.log로 서버 로그에 출력
redis.log(redis.LOG_WARNING, "처리 중: " .. KEYS[1])
redis.log(redis.LOG_NOTICE, "값: " .. tostring(ARGV[1]))

-- 로그 레벨: LOG_DEBUG, LOG_VERBOSE, LOG_NOTICE, LOG_WARNING
```

### 에러 메시지 반환

```lua
local result = redis.pcall('get', KEYS[1])
if type(result) == 'table' and result.err then
    return redis.error_reply("custom error: " .. result.err)
end
```

---

## 주의사항

| 항목 | 주의 내용 |
|------|----------|
| **실행 시간** | 스크립트 실행 중 Redis가 블로킹됨 — 빠르게 끝나야 함 |
| **전역 변수 금지** | 항상 `local` 사용. 전역 변수는 다음 스크립트에 영향 |
| **랜덤 함수 주의** | `math.random`은 복제 시 마스터/레플리카 결과 불일치 발생 가능 → `redis.call('time')` 사용 권장 |
| **무한 루프 금지** | `lua-time-limit`(기본 5000ms) 초과 시 스크립트 강제 종료 |
| **클러스터 제약** | KEYS 배열의 키가 모두 같은 슬롯에 있어야 함 (해시 태그 활용) |
| **KEYS 명시적 선언** | 클러스터 라우팅을 위해 접근하는 모든 키를 KEYS에 전달해야 함 |

### 클러스터에서 해시 태그 활용

```lua
-- {user:1} 해시 태그로 같은 슬롯에 배치
-- KEYS[1] = {user:1}:profile
-- KEYS[2] = {user:1}:session
-- → 같은 슬롯에 있으므로 클러스터에서 사용 가능
```

```java
// 해시 태그를 사용한 키 설계
String profileKey  = "{user:" + userId + "}:profile";
String sessionKey  = "{user:" + userId + "}:session";
// 두 키 모두 {user:userId} 부분으로 슬롯 결정 → 같은 노드에 배치
```

---

## 정리

| 항목 | 내용 |
|------|------|
| **원자성 근거** | Redis 싱글 스레드 모델 — 스크립트 실행 중 다른 명령어 없음 |
| **EVAL** | 스크립트 텍스트를 매번 전송 |
| **EVALSHA** | SHA1 해시로 캐시된 스크립트 호출 — 네트워크 절감 |
| **redis.call** | 에러 시 스크립트 전체 중단 |
| **redis.pcall** | 에러를 잡아 처리 가능 |
| **KEYS** | Redis 키 (클러스터 라우팅에 사용) |
| **ARGV** | 부가 인자 (값, 옵션 등) |
| **주요 사용처** | 분산 락 해제, Rate Limiting, 조건부 업데이트, 재고 차감 |
