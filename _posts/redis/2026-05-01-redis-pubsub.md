---
title: "Redis Pub/Sub — 서버 여러 대가 같은 메시지를 받는 법"
categories:
- REDIS
tags: [Redis, Pub/Sub, 메시지 브로커, Spring Redis, Kafka 비교]
toc: true
toc_sticky: true
toc_label: 목차
---

채팅 서비스를 서버 3대로 운영한다고 가정하자. 사용자 A는 서버 1에 WebSocket으로 연결되어 있고, 사용자 B는 서버 2에 연결되어 있다. A가 B에게 메시지를 보내면 어떻게 되는가? 서버 1은 서버 2에 연결된 B에게 직접 WebSocket 메시지를 보낼 수 없다. 서버들 사이의 메시지를 중계할 무언가가 필요하다. Redis Pub/Sub이 그 역할이다.

## Pub/Sub이란?

> **비유**: FM 라디오와 같다. DJ(Publisher)가 특정 주파수(채널)로 방송을 보내면, 그 주파수에 주파수를 맞춘 청취자(Subscriber)들이 동시에 듣는다. DJ는 청취자가 몇 명인지 알 필요가 없다. 청취자가 라디오를 끄고 있을 때 방송된 내용은 다시 들을 수 없다. 방송은 나가는 순간 사라진다.

Redis Pub/Sub은 **메시지를 채널에 발행(Publish)하면 그 채널을 구독(Subscribe)한 모든 클라이언트에게 실시간으로 전달**하는 메시징 패턴이다.

```mermaid
sequenceDiagram
    participant P as Publisher
    participant R as Redis
    participant S1 as Subscriber1
    S1->>R: SUBSCRIBE chat:room1
    P->>R: PUBLISH chat:room1 "안녕"
    R-->>S1: "안녕" 전달
```

**핵심 특성**:
- **Fire and Forget**: 메시지를 저장하지 않는다. 구독자가 없어도, 구독자가 잠깐 다운되어도 메시지는 영원히 사라진다.
- **1:N 브로드캐스트**: 하나의 메시지가 모든 구독자에게 동시에 전달된다.
- **실시간**: 발행과 수신 사이의 지연이 수 밀리초 이내다.

---

## Redis CLI로 동작 확인

```bash
# 터미널 1: 구독
redis-cli
> SUBSCRIBE chat:room1
Reading messages... (press Ctrl-C to quit)
1) "subscribe"
2) "chat:room1"
3) (integer) 1   # 현재 구독 중인 채널 수

# 터미널 2: 발행
redis-cli
> PUBLISH chat:room1 "안녕하세요!"
(integer) 1   # 이 메시지를 받은 구독자 수

# 터미널 1에서 자동 수신:
1) "message"
2) "chat:room1"    # 채널 이름
3) "안녕하세요!"    # 메시지 내용
```

---

## 패턴 구독 (PSUBSCRIBE)

채널 이름에 와일드카드를 사용해 여러 채널을 한 번에 구독한다. "모든 채팅방의 메시지"를 하나의 구독자가 받아야 할 때 유용하다.

```bash
# chat: 으로 시작하는 모든 채널 구독
redis-cli PSUBSCRIBE "chat:*"

# 어떤 채팅방에 발행해도 수신됨
redis-cli PUBLISH chat:room1 "1번 방 메시지"
redis-cli PUBLISH chat:room99 "99번 방 메시지"

# 수신 메시지 형식 (패턴 구독은 pmessage)
1) "pmessage"
2) "chat:*"       # 매칭된 패턴
3) "chat:room1"   # 실제 채널 이름
4) "1번 방 메시지" # 내용
```

---

## Spring Boot에서 Pub/Sub 구현

### 설정

```java
@Configuration
public class RedisConfig {

    @Bean
    public RedisConnectionFactory redisConnectionFactory() {
        return new LettuceConnectionFactory(
            new RedisStandaloneConfiguration("localhost", 6379)
        );
    }

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new GenericJackson2JsonRedisSerializer());
        return template;
    }

    @Bean
    public RedisMessageListenerContainer redisMessageListenerContainer(
            RedisConnectionFactory factory,
            ChatMessageListener chatListener) {

        RedisMessageListenerContainer container = new RedisMessageListenerContainer();
        container.setConnectionFactory(factory);

        // 패턴 구독: chat: 로 시작하는 모든 채널
        container.addMessageListener(chatListener, new PatternTopic("chat:*"));
        // 단일 채널 구독
        container.addMessageListener(chatListener, new ChannelTopic("notification:global"));

        return container;
    }
}
```

### Publisher

```java
@Service
@RequiredArgsConstructor
public class ChatPublisher {

    private final RedisTemplate<String, Object> redisTemplate;
    private final ObjectMapper objectMapper;

    public void publishMessage(String roomId, ChatMessage message) {
        String channel = "chat:" + roomId;
        try {
            // 메시지를 JSON 직렬화 후 발행
            // convertAndSend는 내부적으로 직렬화를 처리한다
            String messageJson = objectMapper.writeValueAsString(message);
            redisTemplate.convertAndSend(channel, messageJson);
        } catch (JsonProcessingException e) {
            throw new MessagePublishException("메시지 직렬화 실패", e);
        }
    }
}
```

### Subscriber

```java
@Component
@RequiredArgsConstructor
@Slf4j
public class ChatMessageListener implements MessageListener {

    private final ObjectMapper objectMapper;
    private final SimpMessagingTemplate webSocketTemplate;

    @Override
    public void onMessage(Message message, byte[] pattern) {
        String channel = new String(message.getChannel());
        String body    = new String(message.getBody());

        try {
            ChatMessage chatMessage = objectMapper.readValue(body, ChatMessage.class);

            // 채널명에서 roomId 추출: "chat:room1" → "room1"
            String roomId = channel.substring("chat:".length());

            // WebSocket으로 해당 방 사용자들에게 전달
            webSocketTemplate.convertAndSend("/topic/chat/" + roomId, chatMessage);

        } catch (JsonProcessingException e) {
            log.error("메시지 역직렬화 실패 — channel: {}, body: {}", channel, body, e);
        }
    }
}
```

---

## 주요 활용 패턴

### 1. 멀티 서버 채팅 — 가장 대표적인 사용 사례

서버가 여러 대일 때 각 서버의 WebSocket 사용자들에게 메시지를 전달하는 문제를 해결한다:

```mermaid
graph LR
    U1["사용자 A"] -->|"WebSocket"| SA["서버 1"]
    U2["사용자 B"] -->|"WebSocket"| SB["서버 2"]
    SA -->|"PUBLISH chat:room1"| R[("Redis")]
    R -->|"브로드캐스트"| SA
    R -->|"브로드캐스트"| SB
    SA -->|"WebSocket"| U3["같은 방 사용자 C"]
    SB -->|"WebSocket"| U2
```

사용자 A가 메시지를 보내면:
1. 서버 1이 Redis에 `PUBLISH chat:room1 메시지`
2. Redis가 `chat:room1` 구독자인 서버 1, 2, 3 모두에게 전달
3. 각 서버가 자신에 연결된 WebSocket 사용자들에게 전달

서버 수가 늘어도 코드 변경 없이 Redis Pub/Sub이 중계를 담당한다.

### 2. 캐시 무효화 브로드캐스트

상품 정보가 변경될 때 모든 서버의 로컬 캐시를 동시에 무효화한다:

```java
@Service
public class ProductService {

    @Transactional
    public void updateProduct(Long productId, UpdateProductRequest request) {
        // DB 업데이트
        Product product = productRepository.findById(productId).orElseThrow();
        product.update(request);

        // 모든 서버의 로컬 캐시 무효화 신호 발행
        // 이 메시지를 받은 모든 서버가 자신의 Caffeine/Guava 캐시를 지운다
        redisTemplate.convertAndSend("cache:invalidate",
            Map.of("type", "product", "id", productId));
    }
}

@Component
public class CacheInvalidationListener implements MessageListener {
    private final Cache localCache;  // Caffeine, Guava 등

    @Override
    public void onMessage(Message message, byte[] pattern) {
        Map<String, Object> data = parseJson(message.getBody());
        if ("product".equals(data.get("type"))) {
            // 이 서버의 로컬 캐시에서 해당 상품 제거
            localCache.invalidate("product:" + data.get("id"));
        }
    }
}
```

### 3. 실시간 알림

```java
// 주문 상태 변경 → 해당 사용자에게 실시간 알림
// 사용자별 채널에 발행 → 해당 사용자가 연결된 서버만 처리
redisTemplate.convertAndSend(
    "notification:user:" + userId,
    new OrderStatusChangedNotification(orderId, newStatus)
);
```

---

## 한계 — 쓰기 전에 알아야 할 것들

### 메시지 유실 (가장 중요)

Redis Pub/Sub은 **At-most-once** 전달 보장이다. 메시지가 한 번도 안 가거나 한 번 가거나, "최소 한 번"은 보장하지 않는다.

```mermaid
sequenceDiagram
    participant P as "Publisher"
    participant R as "Redis"
    participant S as "Subscriber (잠깐 다운)"
    P->>R: PUBLISH news "중요한 소식"
    Note over S: 💀 잠깐 다운
    R-->>S: 전달 실패 (아무도 없음)
    Note over R: 메시지 영구 소멸
    Note over S: 재시작 후 구독 재개
    Note over S: 다운 중 메시지는<br>영원히 받을 수 없음
```

유실이 발생하는 상황:
- 구독자가 없을 때 발행된 메시지
- 구독자가 네트워크 문제로 잠깐 끊겼을 때
- Redis 서버 재시작

### 그 외 한계

| 한계 | 설명 |
|------|------|
| 메시지 이력 없음 | 구독 전에 발행된 메시지는 조회 불가 |
| ACK 없음 | 메시지가 실제로 처리됐는지 알 수 없음 |
| 순서 보장 없음 | 네트워크 문제 시 순서가 뒤바뀔 수 있음 |

---

## Redis Stream — Pub/Sub의 한계를 극복하는 대안

Redis 5.0+의 Stream은 Pub/Sub에 영속성과 소비자 그룹을 추가한 Kafka-lite다.

```bash
# 메시지 발행 (저장됨)
XADD mystream * event order_created orderId 12345

# 소비자 그룹 생성 (오프셋 기반)
XGROUP CREATE mystream mygroup $ MKSTREAM

# ACK 기반 소비 (처리 확인)
XREADGROUP GROUP mygroup consumer1 COUNT 10 STREAMS mystream >
XACK mystream mygroup <message-id>
```

---

## Kafka/RabbitMQ와 언제 무엇을 쓰는가

| 항목 | Redis Pub/Sub | Redis Stream | Apache Kafka | RabbitMQ |
|------|-------------|------------|------------|--------|
| 메시지 영속성 | 없음 | 있음 | 있음 (디스크) | 있음 |
| 전달 보장 | At-most-once | At-least-once | At-least-once | At-least-once |
| 메시지 재처리 | 불가 | 가능 (오프셋) | 가능 (오프셋) | 불가 (기본) |
| 복잡도 | 낮음 | 낮음 | 높음 | 보통 |
| 구독자 오프라인 | 메시지 유실 | 나중에 수신 | 나중에 수신 | 큐에 보관 |
| 처리량 | 매우 빠름 | 빠름 | 대용량 최적화 | 보통 |

**선택 기준**:
- 실시간 브로드캐스트, 약간의 유실 허용 → **Redis Pub/Sub** (채팅, 캐시 무효화)
- 유실 불가, 나중에 재처리 필요 → **Redis Stream** (소규모), **Kafka** (대규모)
- 작업 큐, 이메일 발송 → **RabbitMQ**

채팅 시스템이라면: Redis Pub/Sub으로 실시간 전달 + DB에도 저장해 이력 조회를 분리하는 방식이 실용적이다.

---

## 정리

| 항목 | 핵심 |
|------|------|
| 전달 보장 | At-most-once — 유실 가능 |
| 주요 용도 | 멀티 서버 채팅, 캐시 무효화, 실시간 알림 |
| 한계 | 메시지 저장 없음, ACK 없음, 구독 전 메시지 조회 불가 |
| 유실이 치명적이면 | Redis Stream 또는 Kafka로 전환 |

---

## 왜 Redis Pub/Sub인가? (vs Redis Stream vs Kafka)

| 방식 | 메시지 보존 | 소비자 그룹 | 오프셋 재처리 | 적합한 용도 |
|------|-------------|-------------|---------------|-------------|
| **Redis Pub/Sub** | 없음(휘발) | 없음(브로드캐스트) | 불가 | 실시간 알림, 캐시 무효화, 채팅 |
| **Redis Stream** | 있음(설정 가능) | 있음(Consumer Group) | 가능 | 경량 이벤트 큐, at-least-once 처리 |
| **Kafka** | 있음(장기) | 있음 | 가능(임의 오프셋) | 대용량, 이벤트 소싱, 감사 로그 |

**실무 판단**: 메시지 유실이 허용되고 실시간성이 중요하면 Pub/Sub. 유실 불가 + Redis만 쓰고 싶으면 Stream. 대용량·장기 보존·복잡한 소비자 관리가 필요하면 Kafka.

---

## 실무에서 자주 하는 실수

**실수 1: 유실되면 안 되는 이벤트에 Pub/Sub 사용**
결제 완료 이벤트, 재고 차감 이벤트를 Pub/Sub으로 발행한다. 구독자가 없거나 네트워크 순단이 발생하면 메시지가 영구 유실된다. 유실 불가 이벤트는 Redis Stream 또는 Kafka를 사용해야 한다.

**실수 2: 구독자가 느려서 버퍼 오버플로우**
Redis 서버는 각 구독자에게 보낼 메시지를 버퍼링한다. 구독자가 처리 속도보다 메시지가 빠르게 들어오면 `client-output-buffer-limit pubsub`을 초과해 Redis가 강제로 구독 연결을 끊는다. 소비자 처리 속도를 높이거나 Stream으로 전환해야 한다.

**실수 3: 패턴 구독(PSUBSCRIBE) 과다 사용**
`PSUBSCRIBE event.*`처럼 와일드카드 구독을 남발하면 모든 메시지에 대해 패턴 매칭 연산이 발생한다. 구독자 수와 패턴 수에 비례해 CPU를 소비한다. 정확한 채널명을 사용하는 `SUBSCRIBE`가 성능상 유리하다.

**실수 4: Pub/Sub 채널을 상태 저장소로 오해**
채널에 발행된 메시지는 저장되지 않는다. 구독 시점 이전에 발행된 메시지는 조회 불가다. 이벤트 히스토리가 필요하면 별도 List나 Stream에 저장해야 한다.

**실수 5: 다중 Redis 노드 환경에서 Pub/Sub 동작 오해**
Redis Cluster에서 Pub/Sub 메시지는 전체 클러스터가 아닌 단일 노드에서만 전파된다. 여러 앱 서버가 서로 다른 클러스터 노드에 연결되어 있으면 일부 구독자가 메시지를 못 받는다. Cluster에서는 모든 노드에 PUBLISH하거나 Keyspace notification + Stream 조합을 사용해야 한다.

---

## 면접 포인트

**Q1. Redis Pub/Sub과 Redis Stream의 가장 큰 차이는?**
Pub/Sub은 Fire-and-forget 방식으로 메시지를 저장하지 않는다. 구독자가 없거나 오프라인이면 메시지가 유실된다. Stream은 메시지를 로그로 저장하고 Consumer Group이 ACK 기반으로 처리 확인을 한다. 재처리와 장애 복구가 가능하다.

**Q2. 캐시 무효화에 Pub/Sub을 어떻게 활용하는가?**
DB 변경 시 `PUBLISH cache:invalidate "user:123"` 발행 → 모든 앱 서버의 로컬 캐시 구독자가 메시지를 받아 해당 키를 로컬 캐시에서 제거한다. 메시지 유실 시 오래된 캐시가 TTL까지 살아있을 수 있지만, 캐시 무효화는 유실 허용이 가능한 유스케이스다.

**Q3. SUBSCRIBE 상태에서 다른 명령을 실행할 수 있는가?**
`SUBSCRIBE` 상태의 연결은 `SUBSCRIBE`, `UNSUBSCRIBE`, `PSUBSCRIBE`, `PUNSUBSCRIBE`, `PING`, `RESET`, `QUIT` 명령만 허용된다. 일반 GET/SET은 불가하다. 따라서 Pub/Sub 전용 연결을 별도로 관리해야 한다.

**Q4. Keyspace Notification이란?**
Redis 내부 이벤트(SET, DEL, EXPIRE 등)를 자동으로 특정 채널에 발행하는 기능이다. `notify-keyspace-events`로 활성화한다. TTL 만료 이벤트(`__keyevent@0__:expired`)를 구독해 만료된 키에 후속 처리를 하는 패턴에서 활용한다.

**Q5. 실시간 채팅 구현 시 Redis Pub/Sub의 한계는?**
① 메시지 저장 없음 — 접속 전 메시지 조회 불가 → 별도 히스토리 DB 필요 ② 대화 상대 오프라인 시 메시지 유실 → 푸시 알림 + 저장 필요 ③ 대규모 채널(수십만 구독자)에서 메모리/CPU 부담. 실무에서는 Pub/Sub을 실시간 전달에만 쓰고, 히스토리는 RDBMS나 MongoDB에 따로 저장한다.

---
## 극한 시나리오

### 시나리오 1: 멀티 인스턴스 캐시 무효화 — 10대 서버 L1 캐시 동기화

상품 가격이 변경됩니다. 10대 서버 각각의 로컬(L1) 캐시를 즉시 무효화해야 합니다.

```java
// 가격 변경 시 Pub/Sub으로 전체 서버 L1 캐시 무효화
@Service
@RequiredArgsConstructor
public class ProductCacheInvalidationService {
    private final RedisTemplate<String, String> redisTemplate;
    private final Cache<Long, Product> localCache;  // Caffeine L1 캐시

    // 발행: 가격 변경 이벤트
    public void invalidateProduct(Long productId) {
        // L2(Redis) 무효화
        redisTemplate.delete("product:" + productId);
        // 전체 서버 L1 무효화 요청 발행
        redisTemplate.convertAndSend("cache:invalidate:product", productId.toString());
        // 발행 레이턴시: < 1ms
    }

    // 구독: 모든 서버 인스턴스에서 실행
    @Bean
    public MessageListenerAdapter cacheInvalidationListener() {
        return new MessageListenerAdapter(new MessageListener() {
            @Override
            public void onMessage(Message message, byte[] pattern) {
                Long productId = Long.parseLong(new String(message.getBody()));
                localCache.invalidate(productId);
                log.debug("L1 캐시 무효화: productId={}", productId);
            }
        });
    }
}
// 결과: 가격 변경 후 < 5ms 내 전체 10대 서버의 L1 캐시 무효화
// DB 불일치 기간 0.1초 미만 (Pub/Sub 전파 시간)
```

**Pub/Sub 없이 처리할 경우:**
- L1 TTL(30초) 만료를 기다려야 함 → 최대 30초간 잘못된 가격 표시
- 가격 인하 지연 표시는 사용자 신뢰 훼손, 가격 인상 지연 표시는 손해

### 시나리오 2: 실시간 채팅 — Redis Pub/Sub으로 WebSocket 서버 간 메시지 라우팅

```
문제: 사용자 A(서버1 WebSocket 연결), 사용자 B(서버2 WebSocket 연결)
사용자 A가 B에게 메시지 전송 → 서버1이 서버2에게 전달해야 함
```

```java
@Component
@RequiredArgsConstructor
public class ChatMessageBroker {
    private final RedisTemplate<String, ChatMessage> redisTemplate;
    private final WebSocketSessionRegistry sessionRegistry;

    // 메시지 발송: 어느 서버에 B가 연결됐는지 몰라도 됨
    public void sendMessage(ChatMessage message) {
        // 채팅방 채널에 발행
        redisTemplate.convertAndSend("chat:room:" + message.getRoomId(), message);
        // 모든 서버가 구독 중이므로 B가 연결된 서버가 수신
    }

    // 구독: 모든 서버에서 실행, 자신에게 연결된 사용자에게만 전달
    @RedisListener(topic = "chat:room:*")
    public void onChatMessage(ChatMessage message, String channel) {
        String roomId = channel.replace("chat:room:", "");
        // 이 서버에 연결된 해당 채팅방 사용자에게만 WebSocket 전송
        sessionRegistry.getSessionsInRoom(roomId)
            .forEach(session -> session.sendMessage(message));
    }
}
// 수치: 채팅방당 구독자 수에 무관하게 O(1) 발행
// 단, 수신자가 오프라인이면 메시지 유실 (Pub/Sub 특성)
```

### 시나리오 3: Redis Pub/Sub 메시지 유실 — 구독자가 없을 때

```
시나리오: 서버 배포로 구독자가 30초간 없음
이 동안 발행된 알림 메시지 100건 → 전부 유실
재연결 후 구독자가 없으므로 수신 불가
```

**Redis Stream으로 전환 (메시지 영속성 보장):**
```java
// Pub/Sub 대신 Stream 사용 (Consumer Group으로 정확히 한 번 처리)
@Service
public class ReliableNotificationService {

    // 발행: Stream에 영속
    public void publish(Notification notification) {
        redisTemplate.opsForStream().add(
            StreamRecords.newRecord()
                .ofObject(notification)
                .withStreamKey("notifications")
        );
        // 메시지가 Redis Stream에 저장됨 → 구독자 없어도 유실 없음
    }

    // 소비: Consumer Group으로 정확히 한 번 처리
    @Scheduled(fixedDelay = 100)
    public void consumeNotifications() {
        List<MapRecord<String, Object, Object>> messages =
            redisTemplate.opsForStream().read(
                Consumer.from("notification-service", "instance-1"),
                StreamReadOptions.empty().count(100),
                StreamOffset.create("notifications", ReadOffset.lastConsumed())
            );
        messages.forEach(record -> {
            processNotification(record);
            redisTemplate.opsForStream().acknowledge("notifications",
                "notification-service", record.getId());  // 처리 확인
        });
    }
}
// Pub/Sub: 발행 즉시 구독자에게 전달, 영속 없음
// Stream: DB처럼 영속, Consumer Group으로 중복 없이 처리, 재처리 가능
```
