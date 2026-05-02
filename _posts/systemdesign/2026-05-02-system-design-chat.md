---
title: "채팅 시스템 설계 — 카카오톡을 직접 만들어보자"
categories:
- SYSTEMDESIGN
toc: true
toc_sticky: true
toc_label: 목차
---

## 실생활 비유: 우체국 vs 전화

기존 HTTP는 **우체국** 방식입니다. 편지를 보내면(요청) 답장이 올 때까지(응답) 기다려야 합니다. 하지만 채팅은 **전화** 방식이어야 합니다. 상대방이 말하면 즉시 내 귀에 들려야 하고, 내가 말하면 즉시 상대방에게 전달됩니다. 이 "실시간 양방향 통신"을 가능하게 하는 것이 **WebSocket**입니다.

---

## 1. 요구사항 분석

### 기능 요구사항

1. 1:1 채팅
2. 그룹 채팅 (최대 100명)
3. 온라인/오프라인 상태 표시
4. 메시지 전송 확인 (1체크: 전송, 2체크: 읽음)
5. 미디어 파일 전송 (이미지, 동영상)
6. 푸시 알림 (앱 백그라운드 시)

### 비기능 요구사항

- 지연시간: 메시지 전달 100ms 미만
- 가용성: 99.99%
- 일관성: 메시지 순서 보장
- 규모: 5억 DAU, 1인당 하루 40개 메시지

### 규모 추정

```
DAU: 5억명
메시지/일: 5억 × 40 = 200억건
메시지 QPS = 200억 / 86,400 ≈ 231,000 QPS
피크 QPS ≈ 700,000 QPS

메시지 크기: 평균 100B
일일 저장: 200억 × 100B = 2TB/일
5년 저장: 2TB × 365 × 5 ≈ 3.65PB
```

---

## 2. 핵심 기술: WebSocket

### HTTP Polling vs Long Polling vs WebSocket

```mermaid
sequenceDiagram
    participant C as 클라이언트
    participant S as 서버

    Note over C,S: Short Polling (매 3초마다 확인)
    loop 매 3초
        C->>S: 새 메시지 있어?
        S-->>C: 없음
    end

    Note over C,S: Long Polling (서버가 메시지 올 때까지 대기)
    C->>S: 새 메시지 있어? (대기...)
    Note over S: 30초 대기
    S-->>C: 메시지 왔어! [데이터]
    C->>S: 다시 대기...

    Note over C,S: WebSocket (진짜 양방향)
    C->>S: WebSocket 연결 요청 (HTTP Upgrade)
    S-->>C: 101 Switching Protocols
    Note over C,S: 지속 연결 유지
    S->>C: 새 메시지! [데이터]
    C->>S: 메시지 전송 [데이터]
    S->>C: 또 다른 메시지! [데이터]
```

| 방식 | 지연시간 | 서버 부하 | 실시간성 |
|------|---------|---------|---------|
| Short Polling | 높음(3초) | 매우 높음 | 낮음 |
| Long Polling | 중간 | 높음 | 중간 |
| WebSocket | 낮음(ms) | 낮음 | 높음 |
| SSE | 낮음 | 낮음 | 단방향 |

### WebSocket 핸드셰이크

```http
# 클라이언트 → 서버
GET /chat HTTP/1.1
Host: chat.example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13

# 서버 → 클라이언트
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

---

## 3. 전체 아키텍처

```mermaid
graph TD
    Mobile[모바일 앱] -->|WebSocket| LB[로드밸런서<br/>L4 TCP]
    Web[웹 브라우저] -->|WebSocket| LB

    LB --> CS1[채팅 서버 1<br/>WebSocket 처리]
    LB --> CS2[채팅 서버 2]
    LB --> CS3[채팅 서버 N]

    CS1 --> MQ[메시지 큐<br/>Kafka]
    CS2 --> MQ
    CS3 --> MQ

    CS1 --> Presence[Presence 서비스<br/>온라인 상태]
    CS1 --> UserSvc[사용자 서비스<br/>REST API]
    CS1 --> PushSvc[푸시 알림 서비스]

    MQ --> MsgWorker[메시지 처리 워커]
    MsgWorker --> MsgDB[(메시지 DB<br/>HBase/Cassandra)]
    MsgWorker --> Cache[Redis<br/>최근 메시지 캐시]

    Presence --> Redis_P[Redis<br/>온라인 상태 저장]
    UserSvc --> UserDB[(사용자 DB<br/>MySQL)]
    PushSvc --> APNs[Apple APNs]
    PushSvc --> FCM[Google FCM]
```

---

## 4. 메시지 전송 흐름

### 1:1 채팅 메시지 흐름

```mermaid
sequenceDiagram
    participant A as 사용자A (서버1 연결)
    participant S1 as 채팅서버1
    participant Kafka as Kafka
    participant S2 as 채팅서버2
    participant B as 사용자B (서버2 연결)
    participant Push as 푸시서버
    participant DB as 메시지DB

    A->>S1: WS: {"to": "B", "msg": "안녕!"}
    S1->>S1: 메시지 ID 생성, 타임스탬프 추가
    S1->>Kafka: 메시지 발행 (topic: user-B)
    S1-->>A: ACK: 메시지 수신됨 (1체크)

    par 병렬 처리
        Kafka->>DB: 메시지 영구 저장
        Kafka->>S2: 사용자B에게 전달
    end

    alt B가 온라인 (서버2에 연결됨)
        S2->>B: WS: {"from": "A", "msg": "안녕!"}
        B-->>S2: ACK: 메시지 읽음
        S2->>S1: 읽음 확인 전달
        S1->>A: WS: 읽음 확인 (2체크)
    else B가 오프라인
        Kafka->>Push: 푸시 알림 요청
        Push->>FCM: FCM 발송
        FCM->>B: 푸시 알림
    end
```

### 다른 서버의 사용자에게 메시지 전달

```mermaid
graph TD
    Problem[문제: A가 서버1에 연결<br/>B가 서버2에 연결<br/>어떻게 전달?]

    Problem --> Sol1[방법1: 서버간 직접 통신]
    Problem --> Sol2[방법2: Pub/Sub Redis]
    Problem --> Sol3[방법3: 메시지 큐 Kafka]

    Sol1 --> D1[단점: N×N 연결 필요<br/>100대면 9900개 연결]
    Sol2 --> D2[Redis Pub/Sub<br/>채널 구독 방식<br/>적합: 소규모]
    Sol3 --> D3[Kafka<br/>내구성 + 확장성<br/>적합: 대규모]
```

---

## 5. 메시지 ID 설계

메시지 순서를 보장하고 정렬이 가능해야 합니다.

```mermaid
graph TD
    Req[메시지 ID 요구사항]
    Req --> R1[고유성: 전역 유일]
    Req --> R2[순서 정렬 가능]
    Req --> R3[생성 시간 포함]

    R1 --> Sol[Snowflake ID]
    R2 --> Sol
    R3 --> Sol

    Sol --> Bit[64비트 구조]
    Bit --> T[41비트: 타임스탬프ms]
    Bit --> M[10비트: 머신ID]
    Bit --> S[12비트: 시퀀스]
```

```java
public class MessageIdGenerator {
    private static final long EPOCH = 1609459200000L; // 2021-01-01
    private final long workerId;
    private long lastTimestamp = -1L;
    private long sequence = 0L;

    public synchronized long nextId() {
        long timestamp = System.currentTimeMillis() - EPOCH;

        if (timestamp == lastTimestamp) {
            sequence = (sequence + 1) & 0xFFF; // 12비트 최대 4095
            if (sequence == 0) {
                // 다음 밀리초까지 대기
                while (timestamp <= lastTimestamp) {
                    timestamp = System.currentTimeMillis() - EPOCH;
                }
            }
        } else {
            sequence = 0;
        }

        lastTimestamp = timestamp;
        return (timestamp << 22) | (workerId << 12) | sequence;
    }
}
```

---

## 6. 메시지 저장소 설계

### 왜 NoSQL인가?

```mermaid
graph TD
    Q[채팅 메시지 저장소 선택]
    Q --> RDBMS[RDBMS MySQL]
    Q --> NoSQL[NoSQL HBase/Cassandra]

    RDBMS --> P1[단점: 수십 PB 처리 어려움]
    RDBMS --> P2[단점: 수평 확장 복잡]
    RDBMS --> P3[장점: 복잡한 쿼리 가능]

    NoSQL --> A1[장점: 수평 확장 용이]
    NoSQL --> A2[장점: 대용량 쓰기 최적화]
    NoSQL --> A3[장점: 시간 기반 조회 최적화]
    NoSQL --> A4[단점: 복잡한 쿼리 제한]

    NoSQL --> Rec[추천: HBase 또는 Cassandra]
```

### HBase 스키마 설계

```
테이블: messages
RowKey: {channel_id}_{reversed_timestamp}
  → 역순 타임스탬프로 최신 메시지가 앞에 위치

컬럼 패밀리: msg
  - msg:id       → 메시지 ID
  - msg:sender   → 발신자 ID
  - msg:type     → 메시지 타입 (text/image/video)
  - msg:content  → 내용
  - msg:status   → 전송/읽음 상태

예시 RowKey:
ch001_9999999999999  → 가장 최신 메시지 먼저
ch001_9999999999998
ch001_9999999999997
```

### 대화 목록 (최근 채팅방)

```sql
-- MySQL에 저장 (관계형 데이터에 적합)
CREATE TABLE conversations (
    id              BIGINT PRIMARY KEY,
    type            ENUM('direct', 'group'),
    created_at      DATETIME,
    last_message_id BIGINT,
    last_message_at DATETIME,
    INDEX idx_last_msg_at (last_message_at)
);

CREATE TABLE conversation_members (
    conversation_id BIGINT,
    user_id         BIGINT,
    joined_at       DATETIME,
    last_read_at    DATETIME,  -- 읽음 표시용
    PRIMARY KEY (conversation_id, user_id),
    INDEX idx_user_id (user_id)
);
```

---

## 7. 온라인 상태 서비스 (Presence)

### 온라인 상태 추적 방법

```mermaid
sequenceDiagram
    participant App as 모바일 앱
    participant WS as WebSocket 서버
    participant Redis as Redis

    Note over App,Redis: 연결 시
    App->>WS: WebSocket 연결
    WS->>Redis: SET presence:user123 "online" EX=30

    Note over App,Redis: 하트비트 (매 25초)
    loop 매 25초
        App->>WS: ping
        WS->>Redis: EXPIRE presence:user123 30
        WS-->>App: pong
    end

    Note over App,Redis: 연결 끊김
    WS->>Redis: DEL presence:user123
    Note right of Redis: 또는 TTL 30초 후 자동 만료
```

### 온라인 상태 전파

```python
class PresenceService:
    def __init__(self, redis, kafka):
        self.redis = redis
        self.kafka = kafka

    def set_online(self, user_id: str):
        """사용자 온라인 상태 설정"""
        self.redis.setex(f"presence:{user_id}", 30, "online")
        self._notify_friends(user_id, "online")

    def set_offline(self, user_id: str):
        """사용자 오프라인 상태 설정"""
        self.redis.delete(f"presence:{user_id}")
        self._notify_friends(user_id, "offline")

    def is_online(self, user_id: str) -> bool:
        return self.redis.exists(f"presence:{user_id}") > 0

    def _notify_friends(self, user_id: str, status: str):
        """친구들에게 상태 변경 알림 (Kafka 발행)"""
        friends = self._get_friends(user_id)
        for friend_id in friends:
            self.kafka.send('presence-events', {
                'user_id': user_id,
                'status': status,
                'notify_user_id': friend_id,
                'timestamp': time.time()
            })
```

> **주의**: 친구가 1000명이라면 온라인/오프라인 할 때마다 1000개의 이벤트가 발생합니다. **대규모 그룹의 경우 상태 전파를 제한**하거나 **클라이언트가 필요할 때만 조회**하는 방식을 사용합니다.

---

## 8. 그룹 채팅

### 그룹 메시지 전달 방식

```mermaid
graph TD
    A[그룹 메시지 전달 방식]
    A --> Fan[팬아웃 Fan-out on Write]
    A --> Pull[팬인 Fan-in on Read]

    Fan --> F1[메시지 저장 시 모든 멤버에게 복사]
    Fan --> F2[읽기 빠름]
    Fan --> F3[쓰기 비용: O멤버 수]

    Pull --> P1[메시지 1개만 저장]
    Pull --> P2[각 멤버가 읽을 때 조회]
    Pull --> P3[쓰기 빠름, 읽기 비용]

    F3 --> Q{멤버 수}
    Q -->|소규모 100명 이하| Fan
    Q -->|대규모 수천명 이상| Pull
```

### 그룹 채팅 메시지 흐름

```python
async def send_group_message(
    sender_id: str,
    group_id: str,
    content: str
) -> Message:
    # 1. 메시지 ID 생성
    msg_id = id_generator.next_id()

    # 2. 메시지 저장 (1개)
    message = Message(
        id=msg_id,
        sender_id=sender_id,
        group_id=group_id,
        content=content,
        created_at=datetime.now()
    )
    await message_store.save(message)

    # 3. 그룹 멤버 조회
    members = await group_service.get_members(group_id)

    # 4. 온라인 멤버에게 실시간 전달
    # 오프라인 멤버에게는 푸시 알림
    online_members = []
    offline_members = []

    for member_id in members:
        if presence_service.is_online(member_id):
            online_members.append(member_id)
        else:
            offline_members.append(member_id)

    # 온라인 멤버: WebSocket 전달
    await websocket_dispatcher.send_to_users(
        online_members,
        message.to_dict()
    )

    # 오프라인 멤버: 푸시 알림
    await push_service.send_batch(
        offline_members,
        f"{sender_id}: {content[:50]}"
    )

    return message
```

---

## 9. 읽음 확인 (Read Receipt)

```mermaid
graph TD
    Status[메시지 상태]
    Status --> S1["⏳ 전송 중 (sending)"]
    Status --> S2["✓ 전송됨 (sent) - 서버 수신"]
    Status --> S3["✓✓ 전달됨 (delivered) - 기기 수신"]
    Status --> S4["✓✓ 읽음 (read) - 파란색 체크"]
```

**읽음 상태 저장:**
```python
# 메시지별 읽음 상태 (소규모 그룹)
message_read_status = {
    "msg_id": "12345",
    "read_by": {
        "user_A": "2024-01-01T10:00:00",
        "user_B": "2024-01-01T10:01:00",
        # user_C는 아직 미읽음
    }
}

# 사용자별 마지막 읽은 메시지 ID (대규모 그룹)
# conversation_members 테이블의 last_read_at 활용
def get_unread_count(user_id: str, group_id: str) -> int:
    last_read = db.get_last_read(user_id, group_id)
    return db.count_messages_after(group_id, last_read)
```

---

## 10. 미디어 파일 전송

```mermaid
sequenceDiagram
    participant App as 앱
    participant API as API 서버
    participant S3 as S3
    participant CDN as CloudFront CDN

    App->>API: 업로드 URL 요청
    API->>S3: Presigned URL 생성
    S3-->>API: Presigned URL
    API-->>App: Presigned URL 반환

    App->>S3: 파일 직접 업로드 (서버 경유 없음!)
    S3-->>App: 업로드 완료

    App->>API: 메시지 전송 { type: "image", url: "s3://..." }
    API->>API: 썸네일 생성 요청 (Lambda)
    API-->>App: 메시지 전송 완료

    Note over App,CDN: 수신자가 이미지 볼 때
    App->>CDN: 이미지 요청
    CDN->>S3: (캐시 미스 시)
    CDN-->>App: 이미지 응답
```

**파일 크기 제한 및 처리:**
```python
FILE_LIMITS = {
    'image': 20 * 1024 * 1024,   # 20MB
    'video': 200 * 1024 * 1024,  # 200MB
    'document': 100 * 1024 * 1024 # 100MB
}

async def process_media_upload(
    file_type: str,
    file_size: int,
    user_tier: str
) -> str:
    # 크기 제한 확인
    if file_size > FILE_LIMITS.get(file_type, 0):
        raise FileTooLargeError()

    # Presigned URL 생성 (15분 유효)
    key = f"chat/{uuid4()}/{file_type}"
    url = s3.generate_presigned_url(
        'put_object',
        Params={'Bucket': 'chat-media', 'Key': key},
        ExpiresIn=900
    )

    return url
```

---

## 11. 푸시 알림

```mermaid
graph TD
    Offline[오프라인 사용자에게 메시지]
    Offline --> PushSvc[푸시 알림 서비스]

    PushSvc --> Device{기기 OS}
    Device -->|iOS| APNs[Apple APNs]
    Device -->|Android| FCM[Google FCM]
    Device -->|Web| WebPush[Web Push Protocol]

    APNs --> iPhone[iPhone]
    FCM --> Android[Android 기기]
    WebPush --> Browser[웹 브라우저]
```

**푸시 알림 구현:**
```java
@Service
public class PushNotificationService {

    private final FirebaseMessaging fcm;
    private final ApnsClient apns;

    public void sendPush(String userId, String title, String body) {
        UserDevice device = userDeviceRepository.findByUserId(userId);

        if (device == null) return;

        switch (device.getOs()) {
            case ANDROID -> sendFcm(device.getToken(), title, body);
            case IOS -> sendApns(device.getToken(), title, body);
        }
    }

    private void sendFcm(String token, String title, String body) {
        Message message = Message.builder()
            .setToken(token)
            .setNotification(Notification.builder()
                .setTitle(title)
                .setBody(body)
                .build())
            .putData("click_action", "OPEN_CHAT")
            .build();

        try {
            fcm.send(message);
        } catch (FirebaseMessagingException e) {
            if (e.getMessagingErrorCode() == MessagingErrorCode.UNREGISTERED) {
                // 기기 토큰 만료 → DB에서 삭제
                userDeviceRepository.deleteByToken(token);
            }
        }
    }
}
```

---

## 12. 서비스 확장 전략

### 채팅 서버 수평 확장

```mermaid
graph TD
    Problem[문제: 수평 확장 시<br/>사용자가 어느 서버에 연결됐는지?]

    Problem --> Sol[ZooKeeper / Redis<br/>사용자-서버 매핑 저장]

    Sol --> S1[채팅 서버 1<br/>A~F 사용자]
    Sol --> S2[채팅 서버 2<br/>G~N 사용자]
    Sol --> S3[채팅 서버 3<br/>O~Z 사용자]

    S1 -->|메시지 라우팅| MQ[Kafka]
    S2 --> MQ
    S3 --> MQ

    MQ --> S1
    MQ --> S2
    MQ --> S3
```

**사용자-서버 매핑:**
```python
class UserServerMapping:
    def __init__(self, redis):
        self.redis = redis

    def register(self, user_id: str, server_id: str):
        """사용자가 어느 서버에 연결됐는지 등록"""
        self.redis.setex(f"ws_server:{user_id}", 3600, server_id)

    def get_server(self, user_id: str) -> str | None:
        """사용자의 연결 서버 조회"""
        return self.redis.get(f"ws_server:{user_id}")

    def deregister(self, user_id: str):
        """연결 끊김 시 제거"""
        self.redis.delete(f"ws_server:{user_id}")
```

---

## 13. 극한 시나리오: 카카오 대규모 장애 상황

2022년 카카오 데이터센터 화재로 카카오톡이 수 시간 다운됐습니다. 어떻게 방지할 수 있었을까요?

```mermaid
graph TD
    subgraph DC1 [데이터센터 1 - 판교]
        WS1[WebSocket 서버]
        DB1[(메시지 DB)]
        Cache1[Redis]
    end

    subgraph DC2 [데이터센터 2 - 다른 지역]
        WS2[WebSocket 서버]
        DB2[(메시지 DB - 복제)]
        Cache2[Redis]
    end

    LB[글로벌 로드밸런서] --> DC1
    LB --> DC2

    DB1 -->|실시간 복제| DB2

    DC1 -->|장애!| Failover[자동 장애조치]
    Failover --> DC2

    User[사용자] --> LB
```

**멀티 데이터센터 설계 요소:**
1. **Active-Active**: 두 DC가 동시에 트래픽 처리
2. **데이터 복제**: 메시지 DB 실시간 양방향 복제
3. **DNS 장애조치**: 하나의 DC 장애 시 DNS가 다른 DC로 라우팅
4. **메시지 큐 이중화**: Kafka 멀티 클러스터

---

## 14. 완성된 채팅 아키텍처

```mermaid
graph TD
    Users[모바일/웹 클라이언트] --> GLB[글로벌 로드밸런서]
    GLB --> WS_LB[WebSocket 로드밸런서<br/>L4 TCP]

    WS_LB --> WS1[채팅 서버 1]
    WS_LB --> WS2[채팅 서버 2]
    WS_LB --> WS3[채팅 서버 N]

    WS1 --> Presence[Presence 서비스]
    WS1 --> MQ[Kafka 클러스터]
    WS1 --> UserSvc[사용자/그룹 서비스]

    Presence --> Redis_P[Redis<br/>온라인 상태]
    MQ --> MsgWorker[메시지 저장 워커]
    MsgWorker --> HBase[(HBase<br/>메시지 저장)]

    MQ --> PushWorker[푸시 알림 워커]
    PushWorker --> APNs[APNs]
    PushWorker --> FCM[FCM]

    UserSvc --> MySQL[(MySQL<br/>사용자/그룹 정보)]

    WS1 --> Redis_WS[Redis<br/>사용자-서버 매핑]

    subgraph 미디어
        S3[(S3 저장소)]
        CDN[CloudFront CDN]
    end
```

---

## 핵심 설계 결정 요약

| 결정 사항 | 선택 | 이유 |
|----------|------|------|
| 실시간 통신 | WebSocket | 양방향 저지연 |
| 메시지 라우팅 | Kafka | 내구성 + 확장성 |
| 메시지 저장 | HBase | 대용량 쓰기 최적화 |
| 온라인 상태 | Redis TTL | 빠른 읽기/쓰기 |
| 미디어 저장 | S3 + CDN | 비용 효율 + 글로벌 배포 |
| 푸시 알림 | APNs + FCM | 플랫폼 표준 |
| 사용자-서버 매핑 | Redis | 빠른 조회 |
