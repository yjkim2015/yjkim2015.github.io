---
title: "Redis Streams 완전 정복 — Kafka 없이 이벤트 스트리밍을 구현하는 법"
categories:
- REDIS
toc: true
toc_sticky: true
toc_label: 목차
---

> **한 줄 요약**: Redis Streams는 append-only log 구조와 Consumer Group 기반의 ACK 메커니즘을 제공하여, Kafka 없이도 at-least-once 이벤트 스트리밍을 단일 Redis 인스턴스로 구현할 수 있는 자료구조다.

---

## 1. Redis Streams란 무엇인가 — 개념부터 시작

### Append-only log 구조

Redis Streams를 이해하려면 먼저 "append-only log"가 무엇인지부터 알아야 한다.

일반적인 데이터베이스 테이블은 레코드를 갱신(UPDATE)하거나 삭제(DELETE)할 수 있다. 이에 반해 append-only log는 오직 뒤에만 데이터를 추가할 수 있고, 기존 항목을 수정하거나 삭제하지 않는다. 마치 법원 기록부처럼 — 한 번 적힌 내용은 절대 지워지지 않고, 새로운 사실은 항상 마지막 줄에 추가된다.

Kafka도 정확히 이 구조를 사용한다. Kafka의 파티션(partition)은 디스크에 기록되는 append-only log 파일이다. 프로듀서(producer)가 메시지를 쓰면 파티션 끝에 추가되고, 컨슈머(consumer)는 오프셋(offset)이라는 숫자로 "내가 어디까지 읽었는지" 위치를 추적한다.

Redis Streams도 동일한 철학을 따른다. 차이는 Kafka가 디스크 기반 분산 시스템인 반면, Redis Streams는 인메모리(in-memory) 단일(혹은 클러스터) Redis 프로세스 내에서 동작한다는 점이다.

```
Kafka 파티션(디스크):
[msg0][msg1][msg2][msg3][msg4] → 오프셋으로 위치 추적

Redis Streams(메모리):
[1715420001000-0][1715420001001-0][1715420001002-0] → Entry ID로 위치 추적
```

Kafka가 "디스크에 적는 대형 트럭"이라면, Redis Streams는 "메모리에 적는 스포츠카"다. 속도는 훨씬 빠르지만, 메모리 한계와 단일 키 용량 제한이 존재한다.

### Stream Entry ID의 구조

Redis Streams의 모든 메시지는 고유한 Entry ID를 가진다. 형식은 다음과 같다:

```
<밀리초 타임스탬프>-<시퀀스 번호>
예: 1715420001234-0
    1715420001234-1
    1715420001234-2
```

앞부분은 XADD가 실행된 순간의 Unix 타임스탬프(밀리초 단위)이고, 뒷부분은 같은 밀리초 내에서 여러 메시지가 추가될 때 충돌을 방지하는 자동 증가 시퀀스 번호다.

이 설계에는 중요한 이유가 있다.

첫째, **단조 증가(monotonically increasing) 보장**이다. Redis는 Entry ID가 항상 이전 ID보다 크도록 강제한다. 만약 서버 시계가 뒤로 가는 NTP drift가 발생해도, Redis는 마지막으로 생성한 ID의 타임스탬프 이상으로 새 ID를 발급한다. 이 덕분에 스트림은 항상 시간 순서로 정렬된 상태를 유지한다.

둘째, **시간 기반 범위 쿼리**가 가능하다. ID 자체가 타임스탬프를 포함하기 때문에 `XRANGE mystream 1715420000000-0 1715420010000-0` 처럼 특정 시간 구간의 메시지만 조회할 수 있다. Kafka에서 시간 기반 조회를 하려면 별도의 타임스탬프 인덱스를 관리해야 하는 것과 대비된다.

셋째, **분산 환경에서의 유일성**이다. 클러스터 모드에서 여러 클라이언트가 동시에 XADD를 호출해도, Redis 서버가 ID 발급을 직렬화(serialize)하므로 충돌이 발생하지 않는다.

직접 ID를 지정할 수도 있다: `XADD mystream 1715420001234-5 field value`. 이는 데이터 마이그레이션이나 이벤트 소싱에서 원본 타임스탬프를 보존할 때 사용한다.

### 기존 Redis 자료구조로는 왜 안 되는가

Redis에는 Streams 이전에도 메시지 전달에 사용할 수 있는 구조가 있었다. 하지만 각각 치명적인 한계가 있었다.

**Redis List (LPUSH/BRPOP) 의 한계:**

List는 큐(queue)처럼 사용할 수 있다. `LPUSH queue msg` 로 왼쪽에 추가하고, `BRPOP queue 0` 으로 오른쪽에서 블로킹 방식으로 꺼낸다.

문제 1: **메시지 소비가 파괴적(destructive)**이다. BRPOP은 List에서 메시지를 꺼내는 동시에 삭제한다. 한 번 소비된 메시지는 영원히 사라진다. 같은 메시지를 여러 서비스가 독립적으로 처리하는 멀티 컨슈머(fan-out) 패턴이 불가능하다.

문제 2: **ACK 메커니즘이 없다**. 컨슈머가 BRPOP으로 메시지를 가져간 뒤 처리 도중 프로세스가 죽으면, 그 메시지는 영원히 유실된다. "가져갔다"는 사실과 "처리 완료"를 구분할 방법이 없다.

문제 3: **여러 컨슈머가 동일 메시지를 처리할 수 없다**. 멀티 컨슈머를 구현하려면 각 컨슈머별로 별도 List를 만들고, 프로듀서가 모든 List에 복사해서 넣어야 한다. 이는 컨슈머 수가 늘어날수록 비례해서 XADD 횟수가 증가하는 O(n) 비용 구조다.

**Redis Pub/Sub 의 한계:**

Pub/Sub은 채널(channel)에 메시지를 발행(PUBLISH)하면, 그 순간 구독 중인 모든 클라이언트가 동시에 받는다.

문제 1: **영속성이 전혀 없다**. 메시지는 발행되는 순간에만 존재한다. 그 순간 구독하지 않은 컨슈머는 메시지를 받을 수 없다. 서버 재시작, 네트워크 단절, 컨슈머 재배포 시 메시지가 유실된다.

문제 2: **히스토리 재생이 불가능하다**. 과거 이벤트를 다시 읽거나, 새로운 서비스가 과거 데이터부터 따라잡는(catch-up) 것이 불가능하다.

문제 3: **at-least-once 보장이 없다**. 컨슈머가 메시지를 받았더라도 처리를 보장하는 메커니즘이 없다. fire-and-forget 방식이다.

**Redis Streams가 해결하는 것:**

Redis Streams는 이 모든 한계를 해결한다.

1. 메시지를 소비해도 스트림에서 삭제되지 않는다 — 여러 Consumer Group이 독립적으로 소비 가능
2. PEL(Pending Entry List)을 통한 ACK 메커니즘 — 컨슈머 장애 시 메시지 재처리 가능
3. 스트림은 영속적 — 구독자가 없는 순간에도 메시지가 저장됨
4. XRANGE로 과거 메시지 재생 가능
5. MAXLEN으로 메모리 사용량 제어 가능

---

## 2. 핵심 명령어 동작원리

### XADD — 메시지 추가

가장 기본적인 명령이다.

```bash
XADD stream-key [MAXLEN [~] count] [MINID [~] threshold] * field1 value1 field2 value2 ...
```

`*` 은 "ID를 자동으로 발급하라"는 의미다. 직접 지정하려면 `1715420001234-0` 처럼 쓴다.

**내부 동작 단계:**

1. Redis는 현재 Unix 시간(밀리초)을 읽는다.
2. 마지막으로 저장된 Entry ID의 타임스탬프와 비교한다. 현재 시간이 더 크면 `현재시간-0` 을 ID로 사용, 같으면 마지막 시퀀스+1을 사용.
3. 메시지 데이터(field-value 쌍)를 radix tree 기반의 내부 구조에 저장한다.
4. 해당 스트림을 XREAD/XREADGROUP으로 블로킹 대기 중인 클라이언트들에게 wakeup 시그널을 보낸다.

**MAXLEN 트리밍:**

```bash
XADD orders MAXLEN 10000 * event order_placed order_id 12345
```

`MAXLEN 10000` 은 스트림 길이를 10,000개로 제한한다. 새 메시지 추가 후 길이가 초과하면 가장 오래된 메시지부터 삭제한다.

정확한 트리밍(`MAXLEN 10000`)은 매번 트리 재구성이 필요해 비용이 크다. 그래서 `~` 근사 트리밍을 사용한다:

```bash
XADD orders MAXLEN ~ 10000 * event order_placed order_id 12345
```

`~` 는 "최소 10,000개는 유지하되, 정확히 10,000개일 필요는 없다"는 의미다. Redis의 내부 radix tree는 노드 단위로 데이터를 저장하는데, `~` 옵션은 노드 경계에서만 트리밍을 수행하여 CPU 비용을 대폭 줄인다. 실제로는 10,000~10,100개 사이의 메시지가 유지될 수 있다.

**MINID 트리밍:**

```bash
XADD orders MINID ~ 1715420000000-0 * event order_placed order_id 12345
```

길이가 아닌 ID(타임스탬프) 기준으로 트리밍한다. "이 ID보다 오래된 메시지는 삭제하라"는 의미다. 시간 기반 데이터 보존 정책(예: 7일치만 유지)에 사용한다.

### XREAD — 단순 읽기

```bash
XREAD [COUNT count] [BLOCK milliseconds] STREAMS stream-key [stream-key ...] id [id ...]
```

**non-blocking 모드:**

```bash
XREAD COUNT 10 STREAMS orders 1715420001234-0
```

`1715420001234-0` 이후의 메시지 최대 10개를 즉시 반환한다. 새 메시지가 없으면 nil을 반환한다.

처음부터 읽으려면 ID로 `0-0` (또는 `0`)을 사용한다:

```bash
XREAD COUNT 100 STREAMS orders 0
```

**blocking 모드:**

```bash
XREAD COUNT 10 BLOCK 5000 STREAMS orders $
```

`$` 는 "지금 이 순간 스트림의 마지막 ID"를 의미한다. 즉, 이 명령 실행 이후에 새로 추가되는 메시지만 받겠다는 뜻이다. `BLOCK 5000` 은 새 메시지가 없으면 최대 5,000밀리초 대기하다가 nil을 반환한다. `BLOCK 0` 은 무한 대기다.

**내부 동작:** Redis 서버는 블로킹 클라이언트 목록을 스트림 키마다 관리한다. XADD가 새 메시지를 추가하는 순간, 해당 스트림을 기다리는 모든 XREAD 클라이언트를 깨운다(event-driven wakeup). 따라서 폴링(polling) 방식보다 훨씬 효율적이다.

**XREAD의 한계:** 동일한 스트림을 여러 컨슈머 인스턴스가 XREAD로 읽으면, 모든 컨슈머가 동일한 메시지를 받는다(fan-out). 작업을 여러 컨슈머에 분산(load balancing)하려면 Consumer Group이 필요하다.

### XREADGROUP + Consumer Group — 핵심 메커니즘

Consumer Group은 하나의 스트림을 여러 컨슈머가 나눠서 처리할 수 있게 하는 메커니즘이다. 핵심 아이디어는 두 가지다:

1. 같은 그룹 내 컨슈머들은 서로 다른 메시지를 받는다 (파티셔닝 without partitions)
2. 컨슈머가 메시지를 받은 것과 처리를 완료한 것을 분리한다 (PEL)

**Consumer Group 생성:**

```bash
XGROUP CREATE orders processing-group $ MKSTREAM
```

`$` 는 "지금부터 새로 추가되는 메시지만 처리하겠다". `0` 을 쓰면 스트림 처음부터 처리한다. `MKSTREAM` 은 스트림이 없으면 자동 생성한다.

**XREADGROUP으로 메시지 읽기:**

```bash
XREADGROUP GROUP processing-group consumer-1 COUNT 10 BLOCK 5000 STREAMS orders >
```

`>` 가 핵심이다. "이 그룹에서 아직 어떤 컨슈머에게도 전달되지 않은 새 메시지를 달라"는 의미다.

**내부 동작 단계:**

1. Redis는 `processing-group` 의 `last-delivered-id` 를 확인한다.
2. `last-delivered-id` 이후의 새 메시지를 최대 COUNT개 찾는다.
3. 각 메시지를 `consumer-1` 에게 전달하면서, 동시에 PEL(Pending Entry List)에 해당 메시지를 기록한다. PEL 항목에는 Entry ID, 컨슈머 이름, 전달 시각, 전달 횟수가 저장된다.
4. `last-delivered-id` 를 마지막으로 전달한 ID로 업데이트한다.

이 구조 덕분에 `consumer-2` 가 동시에 동일 명령을 실행하면, `consumer-1` 이 이미 가져간 메시지는 받지 않는다. 메시지가 그룹 내에서 자동으로 분산된다.

**XACK — 처리 완료 확인:**

```bash
XACK orders processing-group 1715420001234-0
```

컨슈머가 메시지 처리를 완료했음을 Redis에 알린다. Redis는 PEL에서 해당 Entry ID를 제거한다. PEL에서 제거된 메시지는 더 이상 "처리 중" 상태가 아니므로, XCLAIM이나 XAUTOCLAIM의 대상이 되지 않는다.

**XCLAIM — 죽은 컨슈머의 메시지 강제 재할당:**

```bash
XCLAIM orders processing-group consumer-2 60000 1715420001234-0
```

`1715420001234-0` 메시지가 PEL에 들어간 지 60,000밀리초(1분) 이상 지났으면, 소유권을 `consumer-2` 로 이전한다. `consumer-1` 이 처리 도중 죽었을 때 다른 컨슈머가 이어받는 메커니즘이다.

**XAUTOCLAIM — 자동 재할당:**

```bash
XAUTOCLAIM orders processing-group consumer-2 60000 0-0 COUNT 10
```

`0-0` 이후의 PEL 항목 중 60,000밀리초 이상 경과한 것을 최대 10개 `consumer-2` 에게 자동으로 재할당한다. XCLAIM을 수동으로 반복 호출할 필요 없이 단일 명령으로 처리한다. Redis 6.2에서 추가됐다.

### Java + Lettuce 코드 예제

```java
// Spring Data Redis 설정
@Configuration
public class RedisStreamConfig {

    @Bean
    public RedisConnectionFactory redisConnectionFactory() {
        return new LettuceConnectionFactory("localhost", 6379);
    }

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new GenericJackson2JsonRedisSerializer());
        return template;
    }
}

// Producer — 메시지 추가
@Service
public class OrderEventProducer {

    private final StreamOperations<String, String, String> streamOps;
    private static final String STREAM_KEY = "orders";

    public OrderEventProducer(RedisTemplate<String, String> redisTemplate) {
        this.streamOps = redisTemplate.opsForStream();
    }

    public RecordId publishOrderPlaced(String orderId, String userId) {
        Map<String, String> fields = Map.of(
            "event", "ORDER_PLACED",
            "orderId", orderId,
            "userId", userId,
            "timestamp", String.valueOf(System.currentTimeMillis())
        );
        // XADD orders MAXLEN ~ 100000 * event ORDER_PLACED ...
        return streamOps.add(
            StreamRecords.newRecord()
                .in(STREAM_KEY)
                .ofMap(fields)
        );
    }
}

// Consumer Group 생성 (애플리케이션 시작 시 1회)
@Component
public class StreamGroupInitializer implements ApplicationRunner {

    private final RedisTemplate<String, String> redisTemplate;

    @Override
    public void run(ApplicationArguments args) {
        try {
            redisTemplate.opsForStream()
                .createGroup("orders", ReadOffset.latest(), "order-processing-group");
        } catch (RedisSystemException e) {
            // BUSYGROUP: 이미 존재하는 경우 무시
            if (!e.getMessage().contains("BUSYGROUP")) throw e;
        }
    }
}

// Consumer
@Service
public class OrderEventConsumer {

    private final RedisTemplate<String, String> redisTemplate;
    private final StreamOperations<String, String, String> streamOps;
    private static final String STREAM = "orders";
    private static final String GROUP = "order-processing-group";
    private final String consumerId = "consumer-" + UUID.randomUUID();

    @Scheduled(fixedDelay = 100)
    public void consume() {
        // XREADGROUP GROUP order-processing-group consumer-X COUNT 10 BLOCK 100 STREAMS orders >
        List<MapRecord<String, String, String>> records = streamOps.read(
            Consumer.from(GROUP, consumerId),
            StreamReadOptions.empty().count(10).block(Duration.ofMillis(100)),
            StreamOffset.create(STREAM, ReadOffset.lastConsumed()) // ">" 와 동일
        );

        if (records == null) return;

        for (MapRecord<String, String, String> record : records) {
            try {
                processOrder(record.getValue());
                // 처리 성공 시 ACK
                streamOps.acknowledge(STREAM, GROUP, record.getId());
            } catch (Exception e) {
                // ACK 하지 않으면 PEL에 남아 재처리 대상이 됨
                log.error("Failed to process record: {}", record.getId(), e);
            }
        }
    }

    private void processOrder(Map<String, String> fields) {
        String event = fields.get("event");
        String orderId = fields.get("orderId");
        // 실제 비즈니스 로직
    }
}
```

---

## 3. Consumer Group 심층 분석

### last-delivered-id 관리 메커니즘

Consumer Group은 Redis 내부적으로 다음 정보를 관리한다:

```
group-name: "order-processing-group"
last-delivered-id: "1715420005000-3"  ← 마지막으로 전달된 메시지 ID
pending-count: 7                       ← PEL에 있는 미확인 메시지 수
consumers:
  - name: "consumer-1"
    pending: 3
    last-active: 1715420005100
  - name: "consumer-2"
    pending: 4
    last-active: 1715420005200
```

XREADGROUP이 `>` 로 호출될 때마다 `last-delivered-id` 가 전진한다. 이 값은 스트림 내부에 메타데이터로 저장되므로, Redis를 재시작해도 유지된다 (AOF/RDB 영속성이 활성화된 경우).

### PEL(Pending Entry List)의 구조와 역할

PEL은 "전달했지만 아직 ACK 받지 못한 메시지들의 목록"이다. 메시지 유실을 방지하는 핵심 안전장치다.

PEL의 각 항목 구조:

```
Entry ID: 1715420001234-0
Consumer: consumer-1
Delivery Time: 1715420001300  (전달된 Unix 타임스탬프)
Delivery Count: 1             (전달 횟수 — XCLAIM 시 증가)
```

PEL이 없다면 어떤 일이 벌어질까? 컨슈머가 메시지를 받자마자 네트워크가 끊기거나 프로세스가 죽으면, 그 메시지는 영원히 처리되지 않은 채 사라진다. PEL은 "이 메시지는 아직 처리 완료 확인을 못 받았다"는 사실을 Redis가 기억하는 방법이다.

**PEL 크기 모니터링:**

```bash
XPENDING orders order-processing-group - + 10
```

결과:
```
1) 1) "1715420001234-0"
   2) "consumer-1"
   3) (integer) 75432  ← 마지막 전달로부터 경과 시간 (밀리초)
   4) (integer) 1      ← 전달 횟수
```

PEL이 계속 쌓이는 것은 컨슈머 장애나 처리 오류의 신호다. 프로덕션에서는 PEL 크기를 메트릭으로 모니터링해야 한다.

### XACK 처리 과정

```bash
XACK orders order-processing-group 1715420001234-0
```

내부 동작:
1. Redis는 PEL에서 `1715420001234-0` 을 찾는다.
2. 해당 항목을 PEL에서 제거한다.
3. 그룹의 `pending-count` 를 1 감소시킨다.
4. 해당 컨슈머의 `pending` 카운트를 1 감소시킨다.

중요한 점: XACK는 스트림 자체에서 메시지를 삭제하지 않는다. 메시지는 여전히 스트림에 남아있다. PEL에서만 제거된다. 따라서 다른 Consumer Group은 여전히 해당 메시지를 독립적으로 처리할 수 있다.

### XCLAIM/XAUTOCLAIM으로 죽은 컨슈머 처리

실제 프로덕션 환경에서 컨슈머가 갑자기 죽는 상황은 반드시 발생한다. Kubernetes Pod 종료, OOM Kill, 네트워크 파티션 등 다양한 원인이 있다.

```java
// 주기적으로 실행하는 재처리 로직 (별도 스레드 또는 스케줄러)
@Scheduled(fixedDelay = 30000) // 30초마다
public void reclaimStalePending() {
    // 60초(60000ms) 이상 ACK 받지 못한 메시지를 현재 컨슈머로 재할당
    // XAUTOCLAIM orders order-processing-group consumer-X 60000 0-0 COUNT 50
    PendingMessagesSummary pending = streamOps.pending(
        STREAM,
        Consumer.from(GROUP, consumerId)
    );

    if (pending.getTotalPendingMessages() == 0) return;

    // Lettuce 직접 사용
    RedisAsyncCommands<String, String> commands = /* lettuce connection */;
    commands.xautoclaim(STREAM, GROUP, consumerId,
        60000, // min-idle-time: 60초
        "0-0",  // start: 처음부터
        XAutoClaimArgs.Builder.count(50)
    );
}
```

**XAUTOCLAIM의 응답 구조:**

```
1) "1715420010000-0"  ← 다음 호출에서 시작할 cursor ID (0-0이면 끝)
2) [재할당된 메시지 목록]
3) [삭제된 Entry ID 목록 — 스트림에서 사라진 메시지들]
```

### 컨슈머 재시작 시 "0" vs ">" 차이

이것은 프로덕션에서 가장 자주 실수하는 부분이다.

**`>` (greater than):**

```bash
XREADGROUP GROUP order-processing-group consumer-1 COUNT 10 STREAMS orders >
```

"이 그룹에서 아직 전달되지 않은 새 메시지만 달라." 컨슈머가 처음 시작하거나, 정상 운영 중에 사용한다.

**`0` (또는 `0-0`):**

```bash
XREADGROUP GROUP order-processing-group consumer-1 COUNT 10 STREAMS orders 0
```

"이 컨슈머의 PEL에 있는 메시지(아직 ACK 안 된 메시지)를 달라." 컨슈머가 재시작했을 때, 이전에 가져갔지만 처리를 완료하지 못한 메시지를 다시 처리하기 위해 사용한다.

**올바른 컨슈머 재시작 패턴:**

```java
@Service
public class ResilientConsumer {

    public void start() {
        // 1단계: 재시작 후 PEL에 남은 미처리 메시지부터 처리
        processPendingMessages();

        // 2단계: 새 메시지 처리로 전환
        processNewMessages();
    }

    private void processPendingMessages() {
        String cursor = "0-0";
        while (true) {
            // XREADGROUP ... STREAMS orders 0
            List<MapRecord<...>> records = streamOps.read(
                Consumer.from(GROUP, consumerId),
                StreamReadOptions.empty().count(100),
                StreamOffset.create(STREAM, ReadOffset.from(cursor))
            );

            if (records == null || records.isEmpty()) break; // PEL 처리 완료

            for (MapRecord<...> record : records) {
                processAndAck(record);
                cursor = record.getId().getValue();
            }
        }
    }

    private void processNewMessages() {
        while (!Thread.currentThread().isInterrupted()) {
            // XREADGROUP ... STREAMS orders >
            List<MapRecord<...>> records = streamOps.read(
                Consumer.from(GROUP, consumerId),
                StreamReadOptions.empty().count(10).block(Duration.ofSeconds(1)),
                StreamOffset.create(STREAM, ReadOffset.lastConsumed())
            );
            if (records != null) {
                records.forEach(this::processAndAck);
            }
        }
    }
}
```

이 패턴을 따르지 않으면 두 가지 문제가 발생한다:
- `>` 만 사용하면: 재시작 전 PEL에 쌓인 메시지가 영원히 처리되지 않음 (메시지 유실)
- `0` 만 사용하면: PEL이 비어있을 때 빈 응답을 받고 무한 루프에 빠지거나, 새 메시지를 놓침

---

## 4. 다른 메시지 큐와의 상세 비교

### Redis Streams vs Kafka

**아키텍처 차이:**

Kafka는 분산 로그 스토리지 시스템이다. 메시지는 디스크에 기록되며, 브로커(broker) 클러스터가 데이터를 파티션 단위로 분산 저장한다. 메시지의 기본 보존 기간은 7일이며, 컨슈머가 메시지를 읽어도 데이터는 삭제되지 않는다. 수 TB의 이벤트 히스토리를 보관할 수 있다.

Redis Streams는 메모리에 저장된다. 기본적으로 영속성은 AOF/RDB 설정에 의존하며, 메모리 한계에 따라 MAXLEN으로 크기를 제한해야 한다. 단일 스트림의 크기는 가용 메모리 내로 제한된다.

**파티셔닝:**

Kafka의 파티셔닝은 명시적이다. 토픽(topic)에 N개의 파티션을 설정하고, 같은 키의 메시지는 항상 같은 파티션으로 라우팅된다. 파티션 수가 병렬처리의 상한이다.

Redis Streams는 암묵적 파티셔닝을 Consumer Group으로 구현한다. 단일 스트림 내에서 컨슈머들이 메시지를 나눠 가져간다. 키 기반 라우팅이 없으므로 같은 orderId의 이벤트가 서로 다른 컨슈머에게 전달될 수 있다 — 순서 보장이 필요하다면 이것이 문제가 된다.

수평 확장이 필요한 경우 Redis에서는 스트림을 여러 키로 직접 샤딩해야 한다: `orders:0`, `orders:1`, `orders:2` 처럼 애플리케이션 레벨에서 키를 분산한다.

**리밸런싱:**

Kafka는 컨슈머 그룹 리밸런싱이 자동으로 일어난다. 컨슈머가 추가/제거되면 Kafka가 파티션을 자동으로 재분배한다. 이 과정에서 짧은 처리 중단(stop-the-world rebalance)이 발생하는데, Kafka 2.4+ 의 Incremental Cooperative Rebalancing이 이를 개선했다.

Redis Streams는 리밸런싱 개념이 없다. 컨슈머가 추가돼도 기존 컨슈머의 처리에 영향이 없다. 신규 컨슈머는 그냥 `>` 로 새 메시지를 가져가기 시작하면 된다. 간단하지만, 워크로드가 불균등하게 분배될 수 있다.

**보존 정책:**

Kafka는 시간(기본 7일) 또는 크기 기준으로 자동 삭제한다. 로그 컴팩션(log compaction)을 활성화하면 동일 키의 최신 값만 유지하는 이벤트 소싱 패턴도 지원한다.

Redis Streams는 MAXLEN 또는 MINID를 통해 명시적으로 트리밍해야 한다. 자동 TTL 기능이 없으므로 운영자가 직접 관리해야 한다.

**처리량:**

Kafka는 단일 파티션 기준 수십만 TPS, 클러스터 기준 수백만 TPS를 달성할 수 있다. 디스크 순차 쓰기와 Zero-copy I/O를 활용해 처리량을 극대화한다.

Redis Streams는 단일 인스턴스 기준 수십만 TPS를 달성한다. Redis의 단일 스레드 이벤트 루프 특성상 Kafka 클러스터의 총 처리량에는 미치지 못하지만, 지연시간은 Kafka보다 월등히 낮다(sub-millisecond).

**순서 보장:**

Kafka는 파티션 내에서 순서가 엄격히 보장된다. 다른 파티션 간에는 순서 보장이 없다. 같은 키를 항상 같은 파티션으로 보내면, 같은 키의 메시지 순서는 전 세계에서 유일하게 정렬된다.

Redis Streams는 단일 스트림 내에서 Entry ID 순서로 전역 순서가 보장된다. 그러나 Consumer Group에서 여러 컨슈머가 처리하면 처리 완료 순서는 보장되지 않는다.

**Exactly-once 처리:**

Kafka는 Transactions API를 통해 Exactly-once Semantics(EOS)를 공식 지원한다. Producer Transaction + Consumer Atomic Offset Commit을 통해 정확히 한 번만 처리를 보장한다.

Redis Streams는 at-least-once만 공식 지원한다. Exactly-once를 구현하려면 애플리케이션 레벨의 중복 제거(idempotency) 로직이 필요하다. 예: 메시지 ID를 별도 Redis Set에 저장하여 중복 처리 감지.

**언제 Streams가 Kafka보다 나은가:**

- 이미 Redis를 인프라에서 사용 중이고 별도 Kafka 클러스터 운영 비용을 피하고 싶을 때
- 메시지 수가 수백만/일 이하인 소규모 서비스
- 지연시간이 1ms 이하로 요구될 때
- 간단한 이벤트 파이프라인 (복잡한 스트림 처리, Joins, Window 연산 불필요)
- 메시지 보존 기간이 짧아도 되는 경우 (알림, 실시간 피드 등)

**언제 Kafka가 압도적인가:**

- TB 단위의 이벤트 히스토리 보관이 필요할 때
- 수백만 TPS 이상의 처리량
- 여러 컨슈머 그룹이 독립적으로 동일 토픽을 처음부터 재생해야 할 때
- Kafka Streams, KSQL, Flink 같은 스트림 처리 프레임워크와 통합
- Exactly-once 보장이 필수인 금융 트랜잭션
- 컴플라이언스 목적으로 수년간의 이벤트 감사 로그 보존

### Redis Streams vs RabbitMQ

**프로토콜과 메시지 모델:**

RabbitMQ는 AMQP(Advanced Message Queuing Protocol) 기반이다. 메시지는 Producer → Exchange → Queue → Consumer 경로로 흐른다. Exchange는 메시지를 라우팅하는 규칙(binding key, routing key)을 기반으로 적절한 Queue로 전달한다.

Redis Streams는 RESP(Redis Serialization Protocol)를 사용한다. 메시지는 단순히 스트림 키에 append되고, Consumer Group이 라우팅을 담당한다. RabbitMQ의 복잡한 Exchange/Binding 계층이 없다.

**라우팅 표현력:**

RabbitMQ는 네 가지 Exchange 타입을 제공한다:
- Direct: 정확한 routing key 매칭
- Topic: 와일드카드 패턴 매칭 (`order.*.placed`, `#.failed`)
- Fanout: 모든 바인딩된 Queue에 복사
- Headers: 헤더 기반 라우팅

이는 매우 유연한 메시지 라우팅 토폴로지를 가능하게 한다. 예를 들어 `order.kr.placed` 는 한국 주문 처리 큐로, `order.*.placed` 는 글로벌 분석 큐로 동시에 라우팅할 수 있다.

Redis Streams는 이런 동적 라우팅이 없다. 라우팅 로직은 프로듀서가 어느 스트림 키에 쓸지를 결정하거나, 컨슈머가 어느 스트림을 읽을지를 결정하는 방식으로 애플리케이션 레벨에서 처리해야 한다.

**ACK 모델:**

RabbitMQ의 ACK는 채널(channel) 단위다. 컨슈머가 메시지를 받고 `basic.ack` 를 보내면 큐에서 삭제된다. `basic.nack` 또는 `basic.reject` 로 재큐(requeue)하거나 DLQ(Dead Letter Queue)로 이동시킬 수 있다.

Redis Streams의 XACK는 PEL에서 메시지를 제거하지만 스트림 자체에서는 삭제하지 않는다. RabbitMQ의 ACK는 즉시 메시지를 삭제하지만, Redis Streams는 MAXLEN 트리밍이 별도로 필요하다.

**Dead Letter Queue:**

RabbitMQ는 DLQ를 네이티브로 지원한다. 메시지가 maxRetry 횟수 초과, TTL 만료, Queue 용량 초과 시 자동으로 Dead Letter Exchange로 이동된다. 실패한 메시지의 별도 처리 파이프라인을 간단하게 구성할 수 있다.

Redis Streams는 DLQ 개념이 없다. 애플리케이션이 XPENDING으로 재시도 횟수(delivery count)를 확인하고, 임계값 초과 시 별도 스트림(예: `orders:dlq`)으로 직접 이동시켜야 한다.

```java
// Redis Streams에서 DLQ 패턴을 직접 구현
public void processWithDlq(MapRecord<String, String, String> record) {
    try {
        processOrder(record.getValue());
        streamOps.acknowledge(STREAM, GROUP, record.getId());
    } catch (Exception e) {
        // delivery count 확인
        PendingMessages pending = streamOps.pending(STREAM, GROUP,
            Range.closed(record.getId().getValue(), record.getId().getValue()), 1);

        long deliveryCount = pending.get(0).getTotalDeliveryCount();

        if (deliveryCount >= 3) {
            // DLQ로 이동
            streamOps.add(StreamRecords.newRecord()
                .in("orders:dlq")
                .ofMap(record.getValue()));
            streamOps.acknowledge(STREAM, GROUP, record.getId()); // 원래 스트림에서 제거
        }
        // 그렇지 않으면 ACK 하지 않아 PEL에 남겨 재시도
    }
}
```

**메시지 TTL과 우선순위 큐:**

RabbitMQ는 메시지 단위 TTL과 Queue 단위 TTL을 모두 지원한다. 또한 0~255 사이의 우선순위(priority)를 가진 Priority Queue를 지원한다.

Redis Streams는 메시지 단위 TTL이 없다. 우선순위 큐도 네이티브로 지원하지 않는다. 우선순위가 필요하면 `orders:high`, `orders:normal`, `orders:low` 처럼 별도 스트림을 운영하고 컨슈머가 순서대로 폴링하는 방식을 사용해야 한다.

**언제 RabbitMQ가 나은가:** 복잡한 라우팅 토폴로지, 네이티브 DLQ, 메시지 우선순위, AMQP 호환성이 필요한 경우.

**언제 Redis Streams가 나은가:** 이미 Redis 인프라가 있고, 라우팅이 단순하며, 지연시간이 중요한 경우.

### Redis Streams vs AWS SQS

**관리형 vs 자체 운영:**

SQS는 완전 관리형 서비스다. 서버 관리, 패치, 가용성 관리가 필요 없다. 99.9% 가용성 SLA를 AWS가 보장한다.

Redis Streams는 직접 Redis 인스턴스를 운영해야 한다. Redis Sentinel이나 Redis Cluster로 고가용성을 구성하고, 모니터링, 백업, 장애 대응을 직접 해야 한다. ElastiCache for Redis를 사용하면 관리 부담이 줄지만 SQS만큼 hands-off는 아니다.

**FIFO 보장:**

SQS Standard Queue는 순서를 보장하지 않는다. "Best-effort ordering"이라고 명시되어 있다. 순서가 필요하면 SQS FIFO Queue를 사용하지만, 처리량이 3,000 TPS(배치 사용 시)로 제한된다.

Redis Streams는 단일 스트림 내에서 Entry ID 기준 순서가 항상 보장된다.

**가시성 타임아웃 vs PEL:**

SQS의 핵심 메커니즘은 가시성 타임아웃(Visibility Timeout)이다. 컨슈머가 메시지를 가져가면 해당 메시지가 일정 시간 동안 다른 컨슈머에게 보이지 않는다(invisible). 타임아웃 내에 삭제(delete)하지 않으면 메시지가 다시 visible 상태가 되어 다른 컨슈머가 가져갈 수 있다.

Redis Streams의 PEL과 개념이 유사하지만, SQS는 메시지를 Queue에서 잠깐 숨기는 방식이고, Redis는 별도 목록(PEL)으로 추적하는 방식이다. SQS는 타임아웃 내에 재처리가 가능하고, Redis는 XCLAIM/XAUTOCLAIM으로 명시적으로 재할당해야 한다.

**비용:**

SQS는 요청 수 기반 과금이다. 100만 요청당 $0.40 (Standard), $0.50 (FIFO). 소규모에서는 저렴하지만, 초당 수만 건의 메시지를 처리하면 비용이 빠르게 증가한다.

Redis Streams는 Redis 인스턴스 비용만 든다. 처리량이 많을수록 단위 비용이 낮아진다.

**처리량:**

SQS Standard는 거의 무제한 처리량이 가능하다. FIFO는 메시지 그룹 당 300 TPS로 제한된다.

Redis Streams는 단일 인스턴스 기준 수십만 TPS지만, 메모리 한계가 있다.

### Redis Streams vs Redis Pub/Sub

이 비교는 "같은 Redis 위에서 무엇을 선택할 것인가"의 문제다.

**영속성:**

Pub/Sub은 메모리에도 저장하지 않는다. PUBLISH 순간에만 존재하고, 해당 순간 연결된 구독자에게만 전달된다. 구독자가 오프라인이거나 연결이 끊기면 그 메시지는 영원히 사라진다.

Redis Streams는 메모리에 append된다. AOF 설정 시 디스크에도 동기화된다. 구독자 없이도 메시지가 유지된다.

**히스토리 재생:**

Pub/Sub은 과거 메시지를 재생할 수 없다. 새로 배포된 서비스가 "놓친 이벤트"를 따라잡는 것이 불가능하다.

Streams는 XRANGE로 원하는 시점부터 재생할 수 있다. 새 Consumer Group을 `0` ID부터 시작하면 스트림 전체를 처음부터 읽을 수 있다.

**전달 보장:**

Pub/Sub은 fire-and-forget이다. 전달 보장이 없다. 구독자가 메시지를 받았는지 알 방법이 없다.

Streams는 PEL + XACK를 통한 at-least-once 보장이다. 처리 완료가 확인될 때까지 메시지가 추적된다.

**멀티 컨슈머:**

Pub/Sub은 모든 구독자에게 동일 메시지를 전달한다 (fan-out). 각 구독자가 독립적으로 처리한다.

Streams의 Consumer Group은 그룹 내에서 분산처리(load balancing)를 한다. 다른 그룹들은 독립적으로 처리한다 (inter-group fan-out + intra-group load balancing).

**언제 Pub/Sub이 적합한가:** 채팅 메시지, 실시간 주가 스트리밍처럼 "놓쳐도 되는" 고빈도 이벤트에서 Pub/Sub이 단순하고 빠르다.

### Redis Streams vs Redis List (LPUSH/BRPOP)

**멀티 컨슈머 처리:**

List는 각 메시지가 정확히 한 명의 컨슈머에게만 전달된다. 여러 컨슈머가 같은 메시지를 처리하게 하려면 각 컨슈머마다 별도 List를 만들고 프로듀서가 모든 List에 복사해야 한다. 이것은 O(n) 쓰기 증폭이다.

Streams는 여러 Consumer Group이 동일 스트림을 독립적으로 읽는다. 메시지는 한 번만 쓰면 된다.

**ACK 없음 vs PEL:**

List의 BRPOP은 꺼내는 동시에 삭제한다. 컨슈머가 BRPOP 직후 죽으면 메시지는 유실된다.

Redis Streams의 PEL은 이를 방지한다. 처리 완료(XACK) 전까지 메시지가 PEL에 유지된다.

**메타데이터:**

List에는 메시지에 타임스탬프, 순서 ID 같은 메타데이터가 없다. 필요하면 메시지 페이로드에 직접 포함해야 한다.

Streams의 Entry ID는 자동으로 타임스탬프를 포함한다.

**언제 List를 사용하는가:** 단순한 단일 컨슈머 큐, at-most-once 전달로 충분한 경우, 코드 단순성이 중요한 경우.

### 종합 비교 테이블

| 기능 | Redis Streams | Kafka | RabbitMQ | AWS SQS | Redis Pub/Sub | Redis List | AWS Kinesis |
|------|--------------|-------|----------|---------|--------------|------------|-------------|
| **영속성** | 인메모리+AOF | 디스크 | 디스크 | 관리형 | 없음 | 인메모리 | 디스크 |
| **메시지 보존** | MAXLEN/MINID | 시간/크기 기반 | ACK 전까지 | ACK 전까지 | 없음 | BLPOP 시 삭제 | 24h~365d |
| **순서 보장** | 전역(단일 키) | 파티션 내 | Queue 내 | FIFO만 | 발행 순서 | LIFO/FIFO | 샤드 내 |
| **ACK 메커니즘** | XACK + PEL | 오프셋 커밋 | basic.ack | DeleteMessage | 없음 | 없음 | CheckpointSeq |
| **Consumer Group** | 있음 | 있음 | Exchange/Binding | 없음(단순) | 없음 | 없음 | 있음 |
| **멀티 컨슈머 fan-out** | 그룹별 독립 | 그룹별 독립 | Exchange 복사 | 별도 큐 필요 | 모든 구독자 | 불가 | 그룹별 독립 |
| **재생(replay)** | XRANGE | 오프셋 지정 | 불가 | 불가 | 불가 | 불가 | 기간 내 가능 |
| **Exactly-once** | 미지원 | 지원(Tx) | 미지원 | 미지원 | 미지원 | 미지원 | 미지원 |
| **최대 처리량** | ~수십만TPS | ~수백만TPS | ~수만TPS | 거의 무제한 | ~수십만TPS | ~수십만TPS | ~수십만TPS |
| **지연시간** | <1ms | 1~5ms | 1~5ms | 수~수십ms | <1ms | <1ms | 수십ms |
| **운영 복잡도** | 낮음 | 높음 | 중간 | 없음 | 낮음 | 낮음 | 없음 |
| **DLQ 지원** | 직접 구현 | 없음(수동) | 네이티브 | 네이티브 | 없음 | 없음 | 없음 |
| **비용 모델** | 인스턴스 고정 | 인스턴스 고정 | 인스턴스 고정 | 요청당 과금 | 인스턴스 고정 | 인스턴스 고정 | 샤드+요청 |

---

## 5. 실전 아키텍처 패턴

### 이벤트 소싱 with Streams

이벤트 소싱(Event Sourcing)은 상태(state)가 아닌 이벤트(event)의 시퀀스로 데이터를 저장하는 패턴이다. Redis Streams의 append-only 특성은 이 패턴과 자연스럽게 맞아떨어진다.

```
graph LR
    A[Command Handler] --> B[orders:events]
    B --> C[Order Aggregate]
    B --> D[Read Model Updater]
    D --> E[orders:readmodel]
```

```java
// 주문 이벤트 소싱 예시
@Service
public class OrderEventStore {

    private static final String STREAM_PREFIX = "order:events:";
    private final StreamOperations<String, String, String> streamOps;

    // 이벤트 저장
    public RecordId appendEvent(String orderId, String eventType, Map<String, String> payload) {
        String streamKey = STREAM_PREFIX + orderId;
        Map<String, String> fields = new HashMap<>(payload);
        fields.put("eventType", eventType);
        fields.put("version", String.valueOf(System.currentTimeMillis()));

        return streamOps.add(StreamRecords.newRecord()
            .in(streamKey)
            .ofMap(fields));
    }

    // 이벤트 재생으로 현재 상태 복원
    public OrderAggregate replayOrder(String orderId) {
        String streamKey = STREAM_PREFIX + orderId;
        OrderAggregate aggregate = new OrderAggregate(orderId);

        // XRANGE order:events:12345 - +
        List<MapRecord<String, String, String>> events = streamOps.range(
            streamKey,
            Range.unbounded()
        );

        if (events != null) {
            events.forEach(event -> aggregate.apply(event.getValue()));
        }

        return aggregate;
    }
}

// 주문 Aggregate
public class OrderAggregate {
    private String orderId;
    private OrderStatus status;
    private BigDecimal totalAmount;
    private List<OrderItem> items = new ArrayList<>();

    public void apply(Map<String, String> event) {
        switch (event.get("eventType")) {
            case "ORDER_PLACED" -> {
                this.status = OrderStatus.PLACED;
                this.totalAmount = new BigDecimal(event.get("amount"));
            }
            case "PAYMENT_CONFIRMED" -> this.status = OrderStatus.PAID;
            case "SHIPPED" -> this.status = OrderStatus.SHIPPED;
            case "DELIVERED" -> this.status = OrderStatus.DELIVERED;
            case "CANCELLED" -> this.status = OrderStatus.CANCELLED;
        }
    }
}
```

### CQRS 읽기 모델 업데이트

CQRS(Command Query Responsibility Segregation)에서 쓰기 모델(이벤트 스토어)과 읽기 모델(Query용 Projection)을 분리한다. Redis Streams가 두 모델을 연결하는 이벤트 버스 역할을 한다.

```
graph LR
    A[Write API] --> B[Event Stream]
    B --> C[Projection Worker]
    C --> D[Read DB]
    E[Read API] --> D
```

```java
// Projection Worker — 이벤트를 읽기 모델로 변환
@Service
public class OrderProjectionWorker {

    private final StreamOperations<String, String, String> streamOps;
    private final OrderReadRepository readRepository;
    private static final String STREAM = "order:global:events";
    private static final String GROUP = "projection-group";

    @Scheduled(fixedDelay = 50)
    public void project() {
        List<MapRecord<String, String, String>> events = streamOps.read(
            Consumer.from(GROUP, "projection-worker-1"),
            StreamReadOptions.empty().count(100).block(Duration.ofMillis(50)),
            StreamOffset.create(STREAM, ReadOffset.lastConsumed())
        );

        if (events == null) return;

        for (MapRecord<String, String, String> event : events) {
            Map<String, String> fields = event.getValue();
            updateReadModel(fields);
            streamOps.acknowledge(STREAM, GROUP, event.getId());
        }
    }

    private void updateReadModel(Map<String, String> fields) {
        String eventType = fields.get("eventType");
        String orderId = fields.get("orderId");

        switch (eventType) {
            case "ORDER_PLACED" -> readRepository.createOrderView(
                orderId,
                fields.get("userId"),
                new BigDecimal(fields.get("amount"))
            );
            case "PAYMENT_CONFIRMED" -> readRepository.updateStatus(orderId, "PAID");
            case "SHIPPED" -> readRepository.updateStatus(orderId, "SHIPPED");
        }
    }
}
```

### 주문 이벤트 파이프라인 (이커머스)

실제 이커머스에서는 주문 하나가 여러 서비스에서 독립적으로 처리되어야 한다: 결제, 재고, 배송, 알림, 분석.

```
graph LR
    A[Order Service] --> B[orders:events]
    B --> C[Payment Group]
    B --> D[Inventory Group]
    B --> E[Notification Group]
    B --> F[Analytics Group]
```

각 Consumer Group은 완전히 독립적으로 동작한다. 결제 서비스가 느려도 알림 서비스에 영향을 주지 않는다. 각 그룹은 자신의 `last-delivered-id` 를 가지므로, 특정 그룹만 재처리(replay)도 가능하다.

```java
// 주문 서비스 — 이벤트 발행
@Service
@Transactional
public class OrderService {

    private final OrderRepository orderRepo;
    private final OrderEventProducer eventProducer;

    public Order placeOrder(PlaceOrderCommand cmd) {
        // 1. 주문 저장 (DB 트랜잭션)
        Order order = orderRepo.save(new Order(cmd));

        // 2. 이벤트 발행 (DB 커밋 후)
        // Transactional Outbox 패턴을 써야 원자성 보장 — 여기선 단순화
        eventProducer.publishOrderPlaced(order.getId(), order.getUserId(),
            order.getTotalAmount().toString());

        return order;
    }
}
```

**Transactional Outbox 패턴 주의:** DB 트랜잭션과 Redis XADD는 원자적으로 실행되지 않는다. DB는 커밋됐지만 Redis XADD가 실패하면 이벤트가 유실된다. 프로덕션에서는 DB에 outbox 테이블을 두고, 별도 프로세스가 outbox 레코드를 읽어 Redis에 발행하는 패턴이 안전하다.

### 실시간 알림 시스템

```java
@Service
public class NotificationConsumer {

    private final StreamOperations<String, String, String> streamOps;
    private final PushNotificationService pushService;
    private static final String STREAM = "orders:events";
    private static final String GROUP = "notification-group";

    @Scheduled(fixedDelay = 100)
    public void consumeAndNotify() {
        List<MapRecord<String, String, String>> records = streamOps.read(
            Consumer.from(GROUP, "notif-worker-" + instanceId()),
            StreamReadOptions.empty().count(50).block(Duration.ofMillis(100)),
            StreamOffset.create(STREAM, ReadOffset.lastConsumed())
        );

        if (records == null) return;

        // 배치 처리로 푸시 알림 발송
        List<PushMessage> messages = records.stream()
            .filter(r -> "ORDER_PLACED".equals(r.getValue().get("event")))
            .map(r -> new PushMessage(
                r.getValue().get("userId"),
                "주문이 접수되었습니다: " + r.getValue().get("orderId")
            ))
            .collect(Collectors.toList());

        if (!messages.isEmpty()) {
            pushService.sendBatch(messages);
        }

        // 전체 배치 ACK
        RecordId[] ids = records.stream()
            .map(MapRecord::getId)
            .toArray(RecordId[]::new);
        streamOps.acknowledge(STREAM, GROUP, ids);
    }
}
```

---

## 6. 운영 — 극한 시나리오와 대응

### 메모리 폭발: maxlen 전략과 트리밍 비용

**시나리오:** 프로덕션 이커머스에서 블랙프라이데이 트래픽이 몰려 초당 10만 건의 주문 이벤트가 발생한다. MAXLEN 없이 운영하면 어떻게 되는가?

Redis 메모리가 꽉 차면 `maxmemory-policy` 에 따라 동작한다. `noeviction` 정책이면 XADD가 `OOM command not allowed when used memory > 'maxmemory'` 에러를 반환하며 새 메시지 추가가 거부된다. 시스템이 사실상 멈춘다.

**대응 전략:**

1. **근사 트리밍 + 여유 MAXLEN:** 예상 최대 PEL 크기의 2배 이상으로 MAXLEN 설정. PEL에 있는 메시지는 삭제되면 안 되므로, MAXLEN이 너무 작으면 아직 처리 중인 메시지가 스트림에서 삭제되는 문제가 발생한다.

2. **MINID 기반 시간 트리밍:** 처리 완료가 보장된 시간 이전의 메시지만 삭제.

```java
// 매 분 실행되는 트리밍 작업
@Scheduled(cron = "0 * * * * *")
public void trimStream() {
    // 30분 전 타임스탬프
    long cutoffMs = System.currentTimeMillis() - Duration.ofMinutes(30).toMillis();
    String minId = cutoffMs + "-0";

    // XTRIM orders MINID ~ <30분전타임스탬프>-0
    redisTemplate.execute((RedisCallback<Object>) connection -> {
        connection.execute("XTRIM", "orders".getBytes(),
            "MINID".getBytes(), "~".getBytes(), minId.getBytes());
        return null;
    });
}
```

3. **트리밍 비용 이해:** `MAXLEN` (정확) 트리밍은 radix tree의 leftmost 노드들을 제거하는 작업이다. 한 노드에 여러 엔트리가 압축 저장되어 있어 정확한 경계에서 자르려면 노드를 분할해야 한다. `~` 근사 트리밍은 노드 경계에서만 자르므로 O(1)에 가깝다. 프로덕션에서는 항상 `~` 를 사용하라.

### 컨슈머 장애: PEL 누적과 XAUTOCLAIM 타이밍

**시나리오:** 50개의 컨슈머 인스턴스 중 5개가 OOM으로 갑자기 죽었다. 각 인스턴스가 평균 20개의 메시지를 처리 중이었다면, 100개의 메시지가 PEL에 영원히 남게 된다.

**증상 탐지:**

```bash
XPENDING orders order-processing-group - + 10
```

delivery_count가 3 이상이거나 idle time이 수 분 이상인 항목이 쌓이면 컨슈머 장애 신호다.

**XAUTOCLAIM 타이밍 설정:**

min-idle-time을 너무 짧게 설정하면 정상 처리 중인 메시지를 다른 컨슈머가 빼앗아 중복 처리가 발생한다. 너무 길면 장애 복구가 늦어진다.

권장 공식: `min-idle-time > 평균 메시지 처리 시간 × 3`

처리 시간이 500ms라면 min-idle-time은 1,500ms 이상.

```java
@Scheduled(fixedDelay = 10000) // 10초마다
public void claimStalePending() {
    long minIdleTime = 30_000L; // 30초 이상 방치된 메시지만

    // XAUTOCLAIM orders order-processing-group worker-1 30000 0-0 COUNT 100
    // Lettuce 직접 사용
    StatefulRedisConnection<String, String> conn = redisClient.connect();
    RedisCommands<String, String> commands = conn.sync();

    List<Object> result = commands.xautoclaim(
        "orders",
        XAutoClaimArgs.Builder
            .minIdleTime(minIdleTime)
            .count(100),
        "order-processing-group",
        consumerId,
        "0-0"
    );
}
```

### Redis 재시작 시 데이터 보존

Redis는 기본적으로 메모리 데이터베이스다. 재시작하면 모든 데이터가 사라진다 — Streams 포함.

**AOF(Append Only File):**

```
appendonly yes
appendfsync everysec  # 1초마다 디스크에 동기화 (최대 1초치 데이터 유실 가능)
```

모든 쓰기 명령을 파일에 기록한다. 재시작 시 파일을 재실행하여 데이터 복구. XADD도 AOF에 기록되므로 Streams 데이터가 보존된다.

`appendfsync always` 는 모든 명령을 즉시 디스크에 쓰므로 안전하지만 성능이 크게 저하된다. `everysec` 가 성능과 안전성의 균형점이다.

**RDB(Redis Database Snapshot):**

```
save 900 1    # 900초 내 1개 이상 변경 시 스냅샷
save 300 10   # 300초 내 10개 이상 변경 시 스냅샷
```

특정 시점의 메모리 스냅샷을 덤프한다. 스냅샷 간격 내 데이터는 유실될 수 있다.

**권장 설정 (Streams 운영):** AOF + RDB 혼용. AOF가 주 복구 수단, RDB가 빠른 재시작용 스냅샷.

```
appendonly yes
appendfsync everysec
save 60 10000
```

### 클러스터 모드에서 Stream 키 샤딩 주의사항

Redis Cluster는 키를 16,384개의 슬롯(slot)으로 분산한다. 슬롯은 `CRC16(key) % 16384` 로 결정된다. 문제는 단일 명령이 여러 키에 걸쳐 있으면 CROSSSLOT 에러가 발생한다는 점이다.

XREADGROUP에서 단일 명령으로 여러 스트림을 동시에 읽으려면:

```bash
XREADGROUP GROUP g consumer-1 STREAMS stream1 stream2 > >
```

`stream1` 과 `stream2` 가 다른 슬롯에 있으면 에러가 발생한다.

**해결책 — Hash Tags 사용:**

중괄호 `{}` 안의 문자열만 해싱한다. 같은 `{}` 내용을 가진 키는 항상 같은 슬롯에 저장된다.

```
orders:{shard0}:events
orders:{shard1}:events
orders:{shard2}:events
```

단일 명령으로 읽으려는 스트림들은 같은 Hash Tag를 사용해야 한다.

**클러스터에서 Consumer Group 제약:**

Consumer Group은 단일 키(스트림) 단위로 생성된다. Kafka처럼 토픽 수준에서 전체 파티션을 그룹으로 묶는 기능이 없다. 애플리케이션이 각 샤드 키마다 그룹을 생성하고, 각 샤드를 독립적으로 컨슘해야 한다.

### 메시지 순서 역전이 발생하는 케이스

Redis Streams 자체는 단일 스트림 내에서 순서를 보장한다. 하지만 다음 경우에 처리 순서가 역전될 수 있다:

1. **Consumer Group 내 병렬 처리:** `consumer-1` 이 msg-1을 받고, `consumer-2` 가 msg-2를 받았다. `consumer-2` 가 먼저 처리를 완료하면 DB에는 msg-2 결과가 먼저 반영된다. 이벤트 ID(Entry ID)를 포함한 낙관적 잠금(optimistic locking)으로 처리해야 한다.

2. **XCLAIM 후 재처리:** 처리 중이던 `consumer-1` 이 죽어서 `consumer-2` 가 XCLAIM으로 가져갔다. 한편 `consumer-1` 이 재시작하여 새 메시지를 계속 처리 중이다. 이제 구 메시지와 신 메시지의 처리가 뒤섞일 수 있다.

3. **여러 스트림 키 사용 시:** `orders:0`, `orders:1` 두 샤드에서 같은 userId의 이벤트가 서로 다른 컨슈머에 의해 처리될 때 순서 보장이 없다.

### Backpressure 처리

컨슈머보다 프로듀서가 훨씬 빠른 상황에서 스트림이 무한히 커지는 것을 방지해야 한다.

```java
// 프로듀서 레벨 Backpressure
@Service
public class BackpressureAwareProducer {

    private final RedisTemplate<String, String> redisTemplate;
    private static final long MAX_PENDING_MESSAGES = 10_000L;
    private static final String STREAM = "orders";
    private static final String GROUP = "order-processing-group";

    public RecordId publishWithBackpressure(Map<String, String> fields) throws InterruptedException {
        // PEL 크기 확인
        PendingMessagesSummary pending = redisTemplate.opsForStream()
            .pending(STREAM, GROUP);

        if (pending.getTotalPendingMessages() > MAX_PENDING_MESSAGES) {
            // 백프레셔: 컨슈머가 따라올 때까지 대기
            log.warn("Backpressure triggered: {} pending messages", pending.getTotalPendingMessages());
            Thread.sleep(100); // 또는 예외를 던져 호출자에게 전파
            // 실제로는 Circuit Breaker 패턴 권장
        }

        return redisTemplate.opsForStream()
            .add(StreamRecords.newRecord().in(STREAM).ofMap(fields));
    }
}
```

---

## 7. 성능 벤치마크

### XADD/XREAD 처리량

단일 Redis 인스턴스(Redis 7.x, 8코어 서버, 32GB RAM) 기준 벤치마크 결과(이론치):

| 명령 | 파이프라인 없음 | 파이프라인(100개) | 비고 |
|------|---------------|-------------------|------|
| XADD | ~100,000 TPS | ~800,000 TPS | 필드 3개 기준 |
| XREAD | ~80,000 TPS | ~600,000 TPS | COUNT 1 기준 |
| XREADGROUP | ~70,000 TPS | ~500,000 TPS | PEL 업데이트 오버헤드 |
| XACK | ~120,000 TPS | ~900,000 TPS | PEL 삭제 |

**Redis Pipeline이 성능을 극대화하는 이유:** 기본적으로 Redis 명령 하나당 네트워크 왕복(RTT)이 1번 발생한다. Pipeline은 여러 명령을 한 번의 네트워크 요청으로 묶어 보낸다. 100개를 파이프라인으로 보내면 RTT가 1/100로 줄어든다.

### Kafka 대비 지연시간 비교

| 지표 | Redis Streams | Kafka (단일 파티션) | Kafka (클러스터, 복제) |
|------|--------------|--------------------|-----------------------|
| P50 지연시간 | <0.5ms | 1~3ms | 5~10ms |
| P99 지연시간 | <2ms | 5~20ms | 20~50ms |
| P99.9 지연시간 | <10ms | 50~100ms | 100~500ms |
| 엔드투엔드 (발행→수신) | <1ms | 5~50ms | 10~100ms |

Redis Streams의 낮은 지연시간은 메모리 액세스와 단일 프로세스 내 처리에서 온다. Kafka는 디스크 I/O와 네트워크 복제(ISR replication)로 인한 추가 지연이 발생한다.

**단, 지연시간 중심 비교는 사용 케이스를 잘못 보는 것이다.** Kafka는 지연시간보다 처리량, 내구성, 확장성이 강점이다. 같은 기준으로 비교하는 것은 스포츠카와 화물트럭을 0-100km 가속으로 비교하는 것과 같다.

### 메모리 사용량 추정

Redis Streams의 메모리 사용량은 필드 수, 필드 값 크기, 스트림 길이에 따라 달라진다. 내부적으로 Listpack(작은 스트림)과 Radix Tree(큰 스트림)로 저장된다.

엔트리 하나당 대략:
- 기본 오버헤드: 약 50~80 바이트
- 필드당 추가: 필드명 길이 + 값 길이 + 약 20 바이트

실제 예시: 필드 5개, 총 값 크기 200바이트인 엔트리 → 약 400~500 바이트

엔트리 100만 개 = 약 400~500 MB

PEL 엔트리 하나당: 약 70~100 바이트 추가

**용량 계획 공식:**

```
필요 메모리 = (스트림 엔트리 수 × 평균 엔트리 크기)
            + (PEL 크기 × 100 바이트)
            + (Consumer Group 메타데이터)
            × 1.2  (Redis 내부 오버헤드 20%)
```

1초당 10,000개, MAXLEN=100,000개, 엔트리 크기 500B 기준:
```
100,000 × 500B = 50MB (스트림)
+ 최대 PEL (초당 처리 시간 × 메시지 수 = 10,000 × 0.5s = 5,000개 × 100B = 0.5MB)
= 약 60MB × 1.2 = 72MB
```

생각보다 작다. 메모리 관리가 까다로운 것은 PEL 누수다. 컨슈머가 죽고 XAUTOCLAIM이 없으면 PEL이 계속 쌓인다.

---

## 8. 면접 포인트 — Q&A

**Q1. Redis Streams와 Kafka의 가장 큰 차이는 무엇인가?**

A: 가장 근본적인 차이는 저장 매체(메모리 vs 디스크)와 확장 단위다. Kafka는 파티션이라는 독립적인 확장 단위가 있어 클러스터 수평 확장이 자연스럽다. Redis Streams는 단일 키가 단일 인스턴스에 바인딩되어 수평 확장이 불가능하며 애플리케이션 레벨에서 샤딩해야 한다. 또한 Kafka는 디스크 기반이라 수 TB의 데이터를 장기간 보관할 수 있고, Transactions API로 Exactly-once를 지원한다. Redis Streams는 메모리 한계와 at-least-once 제약이 있지만, 지연시간이 1ms 미만으로 훨씬 낮다.

**Q2. PEL이 무엇이고 왜 중요한가?**

A: PEL(Pending Entry List)은 Consumer Group에서 컨슈머에게 전달됐지만 아직 XACK로 확인되지 않은 메시지들의 목록이다. 각 항목은 Entry ID, 컨슈머 이름, 전달 시각, 전달 횟수를 기록한다. PEL이 중요한 이유는 at-least-once 보장의 핵심이기 때문이다. 컨슈머가 메시지를 받고 처리 중 죽으면, PEL에 남아있는 항목을 XCLAIM/XAUTOCLAIM으로 다른 컨슈머가 가져가 재처리할 수 있다. PEL 없이는 메시지 유실이 불가피하다.

**Q3. `>` 와 `0` 의 차이를 설명하라.**

A: XREADGROUP에서 `>` 는 "이 그룹에서 아직 전달되지 않은 새 메시지"를 요청한다. `0` (또는 특정 ID)은 "이 컨슈머의 PEL에서 해당 ID 이후의 미확인 메시지"를 요청한다. 컨슈머 재시작 시 먼저 `0` 으로 PEL의 미처리 메시지를 재처리한 뒤, PEL이 비면 `>` 로 전환하여 새 메시지를 처리해야 한다. 이 패턴을 지키지 않으면 이전 미처리 메시지가 영원히 PEL에 남거나(유실 위험), 새 메시지를 처리하지 못한다.

**Q4. Redis Streams로 Exactly-once를 구현할 수 있는가?**

A: Redis Streams 자체는 at-least-once만 보장한다. Exactly-once를 구현하려면 애플리케이션 레벨의 idempotency가 필요하다. 가장 일반적인 방법은 처리한 Entry ID를 Redis Set에 저장하고, 중복 Entry ID가 들어오면 건너뛰는 것이다. 단, 이 중복 체크와 실제 처리를 원자적으로 실행하려면 Lua Script나 Redis Transactions(MULTI/EXEC)를 사용해야 한다. 완전한 Exactly-once가 필요하다면 Kafka Transactions API를 사용하는 것이 더 적합하다.

**Q5. Consumer Group에서 리밸런싱이 없으면 불균등 처리 문제를 어떻게 해결하나?**

A: Redis Streams의 Consumer Group은 메시지를 요청 순서(XREADGROUP 호출 순서)로 분배한다. 처리 속도가 빠른 컨슈머가 더 많은 메시지를 가져가는 자연스러운 load balancing이 된다. 불균등이 문제가 되는 경우는 특정 메시지의 처리 시간이 매우 길어 PEL을 독점할 때다. 이 경우 XAUTOCLAIM을 통해 타임아웃된 메시지를 다른 컨슈머로 이전하면 된다. 또한 XPENDING으로 각 컨슈머의 PEL 크기를 모니터링하고, 특정 컨슈머에 쏠리면 해당 컨슈머를 재시작하거나 컨슈머 수를 늘리는 것이 현실적인 방법이다.

**Q6. MAXLEN이 PEL보다 작아지면 무슨 일이 발생하나?**

A: 이것이 가장 위험한 운영 실수 중 하나다. MAXLEN 트리밍으로 스트림에서 오래된 메시지가 삭제됐는데, 해당 메시지가 아직 PEL에 있는 경우를 생각해보자. XCLAIM이나 XAUTOCLAIM으로 메시지를 재처리하려 해도, 스트림에서 이미 삭제된 메시지는 반환되지 않는다. PEL에는 항목이 남아있지만 실제 메시지를 읽을 수 없게 된다. XAUTOCLAIM의 세 번째 반환값(deleted entries)에 이런 항목들이 표시된다. 결국 해당 메시지는 영원히 처리되지 않는 좀비 PEL 항목이 된다. 이를 방지하려면 MAXLEN은 항상 "현재 PEL 크기 + 예상 처리량 × 처리 시간" 보다 충분히 크게 설정해야 한다.

**Q7. Redis Cluster 환경에서 XREADGROUP으로 여러 스트림을 한 번에 읽을 수 있는가?**

A: 단일 XREADGROUP 명령으로 여러 스트림을 읽으려면 모든 스트림 키가 동일한 Redis 슬롯에 있어야 한다. Hash Tag `{}` 를 사용하면 같은 슬롯에 강제 배치할 수 있다: `orders:{region-kr}:events`, `payments:{region-kr}:events` 처럼. 다른 슬롯의 스트림을 함께 읽으려면 각 스트림마다 별도 명령을 보내거나, 애플리케이션 레벨에서 여러 스레드가 각 샤드를 담당하는 구조를 사용해야 한다.

---

## 마치며

Redis Streams는 "이미 Redis를 쓰고 있는데 Kafka를 추가하기엔 비용과 운영 복잡도가 너무 크다"는 실무 현장의 니즈에서 태어난 자료구조다. 단순한 메시지 큐 이상으로, append-only log + Consumer Group + PEL의 조합은 at-least-once 이벤트 스트리밍을 단일 Redis 인스턴스로 구현한다.

Kafka, RabbitMQ, SQS 모두 Redis Streams로 대체할 수 없는 케이스가 있다. 핵심은 각 시스템의 강점과 약점을 정확히 알고, 사용 사례에 맞는 도구를 선택하는 것이다. 수 TB의 장기 보관이 필요하면 Kafka, 복잡한 라우팅이 필요하면 RabbitMQ, 운영 부담 없는 관리형이 필요하면 SQS, 그리고 이미 Redis 인프라 위에서 낮은 지연시간의 이벤트 파이프라인이 필요하면 Redis Streams가 정답이다.
