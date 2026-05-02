---
title: "알림 시스템 설계 — 푸시·SMS·이메일 통합 알림 플랫폼"
categories:
- SYSTEMDESIGN
toc: true
toc_sticky: true
toc_label: 목차
---

## 실생활 비유: 우체국 분류 센터

알림 시스템은 대형 우체국 분류 센터와 같습니다. 수천만 통의 편지(알림)가 들어오면, 종류별로 분류하고(SMS/이메일/푸시), 우선순위를 정하고(긴급/일반), 각 배달부(채널 서비스)에게 전달합니다. 배달 실패 시 재시도도 합니다. 이 모든 과정이 알림 시스템의 역할입니다.

---

## 1. 요구사항 분석

### 기능 요구사항

1. 푸시 알림 (iOS APNs, Android FCM)
2. SMS 문자 메시지
3. 이메일
4. 알림 우선순위 (긴급/일반)
5. 알림 중복 방지 (중복 발송 차단)
6. 전송 보장 (최소 1회 전달)
7. 사용자 수신 설정 (특정 채널 거부 가능)

### 비기능 요구사항

- **규모**: 일일 1000만건 모바일 푸시, 100만건 SMS, 500만건 이메일
- **지연**: 긴급 알림 10초 이내 전달
- **안정성**: 알림 유실 없음 (최소 1회 전달 보장)
- **확장성**: 트래픽 급증 처리

### 규모 추정

```
모바일 푸시: 10,000,000건/일 → 116 QPS (평균), 350 QPS (피크)
SMS:          1,000,000건/일 → 11.6 QPS
이메일:       5,000,000건/일 → 58 QPS

총 알림:    16,000,000건/일 → 약 185 QPS
피크 처리량: ~600 QPS
```

---

## 2. 전체 아키텍처

```mermaid
graph TD
    Sources[알림 발생 서비스들] --> API[알림 API 게이트웨이]

    subgraph Sources
        OrderSvc[주문 서비스]
        PaySvc[결제 서비스]
        MarketSvc[마케팅 서비스]
        SystemSvc[시스템 알림]
    end

    API --> Validator[유효성 검사<br/>+ 사용자 설정 확인]
    Validator --> Priority[우선순위 분류기]

    Priority --> Q_High[긴급 큐<br/>Kafka: high-priority]
    Priority --> Q_Normal[일반 큐<br/>Kafka: normal]

    Q_High --> Dispatcher[알림 디스패처]
    Q_Normal --> Dispatcher

    Dispatcher --> PushWorker[푸시 워커]
    Dispatcher --> SMSWorker[SMS 워커]
    Dispatcher --> EmailWorker[이메일 워커]

    PushWorker --> APNs[Apple APNs]
    PushWorker --> FCM[Google FCM]
    SMSWorker --> Twilio[Twilio]
    SMSWorker --> Nexmo[Nexmo/대체]
    EmailWorker --> SendGrid[SendGrid]
    EmailWorker --> SES[AWS SES]

    Dispatcher --> LogDB[(알림 로그 DB)]
    Dispatcher --> Redis[Redis<br/>중복 방지]
```

---

## 3. 알림 채널별 상세 흐름

### 모바일 푸시 알림

```mermaid
sequenceDiagram
    participant App as 서비스
    participant API as 알림 API
    participant Kafka as Kafka
    participant Worker as 푸시 워커
    participant APNs as Apple APNs
    participant FCM as Google FCM

    App->>API: POST /notify { userId, title, body, type }
    API->>API: 사용자 기기 정보 조회
    API->>API: 중복 알림 체크 (Redis)
    API->>Kafka: 메시지 발행
    API-->>App: 202 Accepted (비동기)

    Kafka->>Worker: 메시지 소비

    alt iOS 기기
        Worker->>APNs: HTTP/2 요청
        APNs-->>Worker: 200 OK
    else Android 기기
        Worker->>FCM: HTTP 요청
        FCM-->>Worker: success: 1
    end

    Worker->>LogDB: 전송 결과 기록
```

### SMS 발송

```mermaid
sequenceDiagram
    participant Worker as SMS 워커
    participant Twilio as Twilio (1차)
    participant Nexmo as Nexmo (2차)
    participant DB as 로그 DB

    Worker->>Twilio: SMS 발송 요청
    alt Twilio 성공
        Twilio-->>Worker: 200 OK, messageId
        Worker->>DB: SUCCESS 기록
    else Twilio 실패 (3번 재시도 후)
        Worker->>Nexmo: 대체 공급자로 발송
        alt Nexmo 성공
            Nexmo-->>Worker: 200 OK
            Worker->>DB: SUCCESS (fallback) 기록
        else 모두 실패
            Worker->>DB: FAILED 기록
            Worker->>AlertTeam: 운영팀 알림
        end
    end
```

---

## 4. 중복 알림 방지

### 왜 중복이 발생하는가?

```mermaid
graph TD
    Problem[왜 중복 발생?]
    Problem --> R1[Kafka 재처리: 워커 장애 후 재시작]
    Problem --> R2[네트워크 타임아웃: 실제 전송됐지만 ACK 못 받음]
    Problem --> R3[여러 서비스가 같은 알림 요청]
    Problem --> R4[재시도 로직의 부작용]
```

### 멱등성 기반 중복 방지

```python
import hashlib
import time

class DeduplicationService:
    def __init__(self, redis, window_seconds=3600):
        self.redis = redis
        self.window = window_seconds

    def generate_key(self, user_id: str, event_type: str,
                     content_hash: str) -> str:
        """알림 고유 키 생성"""
        raw = f"{user_id}:{event_type}:{content_hash}"
        return f"dedup:{hashlib.md5(raw.encode()).hexdigest()}"

    def is_duplicate(self, user_id: str, event_type: str,
                     content: str) -> bool:
        """중복 여부 확인"""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        key = self.generate_key(user_id, event_type, content_hash)

        # SET NX (Not eXists): 키가 없을 때만 설정
        result = self.redis.set(key, "1", ex=self.window, nx=True)
        return result is None  # None이면 이미 존재 → 중복

    def mark_sent(self, notification_id: str):
        """전송 완료 표시 (DB에도 기록)"""
        self.redis.setex(f"sent:{notification_id}", self.window, "1")
```

**실전 예시:**
```python
def send_notification(user_id, event_type, title, body):
    dedup = DeduplicationService(redis)

    # 중복 체크
    if dedup.is_duplicate(user_id, event_type, f"{title}{body}"):
        logger.info(f"중복 알림 차단: user={user_id}, type={event_type}")
        return {"status": "skipped", "reason": "duplicate"}

    # 알림 전송
    notification_id = send_push(user_id, title, body)
    return {"status": "sent", "id": notification_id}
```

---

## 5. 사용자 알림 설정 (User Preferences)

```mermaid
graph TD
    Incoming[알림 요청] --> PrefCheck{사용자 설정 확인}

    PrefCheck --> GlobalOff{전체 수신 거부?}
    GlobalOff -->|Yes| Discard[폐기]
    GlobalOff -->|No| ChannelCheck{채널별 설정}

    ChannelCheck --> Push{푸시 허용?}
    ChannelCheck --> SMS{SMS 허용?}
    ChannelCheck --> Email{이메일 허용?}

    Push -->|Yes| PushQueue[푸시 큐]
    SMS -->|Yes| SMSQueue[SMS 큐]
    Email -->|Yes| EmailQueue[이메일 큐]

    Push -->|No| Skip1[건너뜀]
    SMS -->|No| Skip2[건너뜀]
    Email -->|No| Skip3[건너뜀]
```

**사용자 설정 스키마:**
```sql
CREATE TABLE user_notification_settings (
    user_id         BIGINT NOT NULL,
    push_enabled    BOOLEAN DEFAULT TRUE,
    sms_enabled     BOOLEAN DEFAULT TRUE,
    email_enabled   BOOLEAN DEFAULT TRUE,

    -- 알림 유형별 설정
    marketing_push  BOOLEAN DEFAULT TRUE,
    marketing_sms   BOOLEAN DEFAULT FALSE,  -- SMS 마케팅은 기본 거부
    marketing_email BOOLEAN DEFAULT TRUE,

    -- 방해 금지 시간
    quiet_hours_start TIME,    -- 예: 22:00
    quiet_hours_end   TIME,    -- 예: 08:00
    timezone          VARCHAR(50) DEFAULT 'Asia/Seoul',

    PRIMARY KEY (user_id)
);
```

---

## 6. 우선순위 큐 설계

```mermaid
graph TD
    Notif[알림 요청] --> Classify{우선순위 분류}

    Classify -->|P0: 긴급| Critical[긴급 큐<br/>결제 완료, 보안 알림<br/>즉시 처리]
    Classify -->|P1: 높음| High[높음 큐<br/>주문 상태, 배송 알림<br/>1분 이내]
    Classify -->|P2: 보통| Normal[보통 큐<br/>소셜 알림, 댓글<br/>5분 이내]
    Classify -->|P3: 낮음| Low[낮음 큐<br/>마케팅, 뉴스레터<br/>1시간 이내]

    subgraph 워커 할당
        Critical --> W_C[전용 워커 10개]
        High --> W_H[전용 워커 5개]
        Normal --> W_N[공유 워커 3개]
        Low --> W_L[공유 워커 2개]
    end
```

**Kafka 토픽 설계:**
```python
KAFKA_TOPICS = {
    'P0': 'notifications-critical',   # 파티션 20개
    'P1': 'notifications-high',        # 파티션 10개
    'P2': 'notifications-normal',      # 파티션 5개
    'P3': 'notifications-low',         # 파티션 3개
}

def publish_notification(notification: dict):
    priority = determine_priority(notification['type'])
    topic = KAFKA_TOPICS[priority]

    producer.send(
        topic,
        key=notification['user_id'].encode(),
        value=json.dumps(notification).encode()
    )
```

---

## 7. 재시도 전략 (Retry Strategy)

```mermaid
graph TD
    Send[알림 전송 시도]
    Send --> Success{성공?}
    Success -->|Yes| Done[완료 기록]
    Success -->|No| Retry{재시도 횟수?}

    Retry -->|1회| Wait1[1초 대기]
    Wait1 --> Send

    Retry -->|2회| Wait2[4초 대기]
    Wait2 --> Send

    Retry -->|3회| Wait3[16초 대기]
    Wait3 --> Send

    Retry -->|4회 초과| DLQ[Dead Letter Queue<br/>실패 큐]
    DLQ --> Alert[운영팀 알림]
    DLQ --> Manual[수동 처리]
```

**지수 백오프(Exponential Backoff) 구현:**
```python
import asyncio
import random

class RetryHandler:
    def __init__(self, max_retries=3, base_delay=1.0, max_delay=60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    async def execute_with_retry(self, func, *args):
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args)
            except (NetworkError, TimeoutError) as e:
                last_exception = e

                if attempt == self.max_retries:
                    break

                # 지수 백오프 + 지터(jitter)로 thundering herd 방지
                delay = min(
                    self.base_delay * (2 ** attempt) + random.uniform(0, 1),
                    self.max_delay
                )
                await asyncio.sleep(delay)

        # 모든 재시도 실패 → Dead Letter Queue
        await self.send_to_dlq(func, args, last_exception)
        raise last_exception
```

---

## 8. 전송 보장 패턴

### At-Least-Once (최소 1회 전달) 구현

```mermaid
sequenceDiagram
    participant Worker as 워커
    participant APNs as APNs
    participant DB as 로그 DB
    participant Kafka as Kafka

    Worker->>APNs: 알림 전송
    APNs-->>Worker: 200 OK

    Worker->>DB: 전송 성공 기록
    Worker->>Kafka: offset commit (처리 완료)

    Note over Worker: 만약 DB 기록 전에 워커 재시작되면?
    Worker->>APNs: 동일 알림 재전송 (중복!)
    Note over Worker: → 멱등성 키로 중복 방지 필요
```

**트랜잭셔널 아웃박스 패턴:**
```sql
-- 알림 발송 요청과 비즈니스 로직을 같은 트랜잭션으로
BEGIN TRANSACTION;

-- 1. 주문 상태 업데이트
UPDATE orders SET status = 'PAID' WHERE id = 12345;

-- 2. 알림 발송 예약 (같은 트랜잭션!)
INSERT INTO notification_outbox (
    user_id, type, payload, status, created_at
) VALUES (
    1001, 'ORDER_PAID',
    '{"orderId": 12345, "amount": 50000}',
    'PENDING', NOW()
);

COMMIT;

-- 별도 스케줄러가 PENDING 알림을 폴링하여 발송
-- 발송 성공 시 status = 'SENT'로 업데이트
```

---

## 9. 알림 로그 및 분석

```mermaid
graph LR
    Notif[알림 발송] --> Log[알림 로그 DB]
    Log --> Dashboard[운영 대시보드]

    Dashboard --> M1[전송률 - Delivery Rate]
    Dashboard --> M2[열람률 - Open Rate]
    Dashboard --> M3[클릭률 - CTR]
    Dashboard --> M4[실패율 - Failure Rate]
    Dashboard --> M5[채널별 성능 비교]
```

**알림 로그 스키마:**
```sql
CREATE TABLE notification_logs (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    notification_id VARCHAR(64) NOT NULL,  -- 멱등성 키
    user_id         BIGINT NOT NULL,
    channel         ENUM('PUSH', 'SMS', 'EMAIL'),
    type            VARCHAR(50),           -- ORDER_PAID, DELIVERY_STARTED 등
    title           VARCHAR(255),
    status          ENUM('PENDING', 'SENT', 'DELIVERED', 'FAILED', 'SKIPPED'),
    provider        VARCHAR(50),           -- APNs, FCM, Twilio, SendGrid
    sent_at         DATETIME,
    delivered_at    DATETIME,
    error_message   TEXT,
    retry_count     INT DEFAULT 0,

    INDEX idx_user_id (user_id),
    INDEX idx_sent_at (sent_at),
    INDEX idx_status (status)
);
```

---

## 10. 이메일 발송 최적화

### SPF, DKIM, DMARC 설정 (스팸 방지)

```
SPF (Sender Policy Framework):
  → 우리 서버 IP만 이메일 발송 허용
  DNS TXT: "v=spf1 include:sendgrid.net ~all"

DKIM (DomainKeys Identified Mail):
  → 이메일에 디지털 서명
  수신 서버가 서명 검증 → 위조 방지

DMARC (Domain-based Message Authentication):
  → SPF/DKIM 실패 시 처리 방법 지시
  DNS TXT: "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com"
```

### 이메일 발송 속도 제한 (Throttling)

```python
class EmailThrottler:
    """이메일 발송 속도 제한 - ISP 차단 방지"""

    LIMITS = {
        'gmail.com': 50,    # 초당 50건
        'naver.com': 30,
        'daum.net': 20,
        'default': 100
    }

    async def send_batch(self, emails: list[dict]):
        # 도메인별로 그룹화
        by_domain = {}
        for email in emails:
            domain = email['to'].split('@')[1]
            by_domain.setdefault(domain, []).append(email)

        for domain, domain_emails in by_domain.items():
            limit = self.LIMITS.get(domain, self.LIMITS['default'])
            # 속도 제한 준수하며 발송
            for chunk in chunks(domain_emails, limit):
                await asyncio.gather(*[send_email(e) for e in chunk])
                await asyncio.sleep(1)  # 1초 대기
```

---

## 11. 방해 금지 시간 (Quiet Hours)

```python
from datetime import datetime, time
import pytz

def should_send_now(user_id: str, priority: str) -> bool:
    """방해 금지 시간 체크"""

    # 긴급 알림은 무조건 발송
    if priority == 'P0':
        return True

    settings = get_user_settings(user_id)
    if not settings.quiet_hours_start:
        return True

    user_tz = pytz.timezone(settings.timezone)
    user_now = datetime.now(user_tz).time()

    start = settings.quiet_hours_start  # 예: 22:00
    end = settings.quiet_hours_end      # 예: 08:00

    # 자정 넘어가는 경우 처리
    if start > end:
        # 22:00 ~ 다음날 08:00
        in_quiet = user_now >= start or user_now < end
    else:
        in_quiet = start <= user_now < end

    if in_quiet:
        # 방해 금지 해제 시간으로 스케줄링
        schedule_for_later(user_id, settings.quiet_hours_end)
        return False

    return True
```

---

## 12. 극한 시나리오: 1억명에게 동시 마케팅 알림

쿠팡이 블랙프라이데이 행사를 1억 명에게 동시에 알림 발송하는 경우를 설계합니다.

```
문제:
- 1억건 푸시 알림을 얼마나 빨리 보낼 수 있나?
- APNs/FCM의 처리 한계는?
- 서버가 버틸 수 있나?
```

```mermaid
graph TD
    Marketing[마케팅팀: 1억명에게 발송]
    Marketing --> Segmentation[사용자 세그먼테이션<br/>DB에서 대상 추출]
    Segmentation --> Batching[배치 분할<br/>1000명씩 10만 배치]
    Batching --> Kafka[Kafka에 순차 발행<br/>초당 1만건]
    Kafka --> Workers[100개 워커 병렬 처리]
    Workers --> APNs[APNs: 초당 1만건]
    Workers --> FCM[FCM: 초당 1만건]

    subgraph 타임라인
        T1[0분: 발송 시작]
        T2[10분: 전체의 6% 발송]
        T3[2시간 46분: 완료!]
    end
```

**대량 발송 스케줄러:**
```python
class BulkNotificationScheduler:
    def __init__(self, kafka_producer, workers=100):
        self.kafka = kafka_producer
        self.workers = workers
        self.rate_limit = 10000  # 초당 최대 1만건

    async def send_bulk_campaign(
        self,
        campaign_id: str,
        user_ids: list[str],
        notification: dict
    ):
        total = len(user_ids)
        batch_size = 1000

        for i, batch in enumerate(chunks(user_ids, batch_size)):
            for user_id in batch:
                await self.kafka.send(
                    'notifications-low',
                    {
                        'campaign_id': campaign_id,
                        'user_id': user_id,
                        **notification
                    }
                )

            # 속도 제한: 초당 1만건
            sent = (i + 1) * batch_size
            elapsed = time.time() - start_time
            expected = sent / self.rate_limit
            if elapsed < expected:
                await asyncio.sleep(expected - elapsed)

            # 진행률 보고
            if i % 100 == 0:
                logger.info(f"캠페인 {campaign_id}: {sent}/{total} 발행 완료")
```

---

## 완성된 알림 시스템 아키텍처

```mermaid
graph TD
    Services[마이크로서비스들] --> APIGateway[알림 API 게이트웨이]

    APIGateway --> PrefCheck[사용자 설정 확인<br/>Redis 캐시]
    APIGateway --> Dedup[중복 방지<br/>Redis SET NX]
    APIGateway --> Validator[유효성 검사]

    Validator --> P0[Kafka: critical]
    Validator --> P1[Kafka: high]
    Validator --> P2[Kafka: normal]
    Validator --> P3[Kafka: low]

    P0 --> PushWorker[푸시 워커 10개]
    P1 --> PushWorker
    P0 --> SMSWorker[SMS 워커 5개]
    P1 --> SMSWorker
    P2 --> EmailWorker[이메일 워커 10개]
    P3 --> EmailWorker

    PushWorker --> APNs
    PushWorker --> FCM
    SMSWorker --> Twilio
    SMSWorker --> Nexmo
    EmailWorker --> SendGrid
    EmailWorker --> SES

    PushWorker --> DLQ[Dead Letter Queue]
    SMSWorker --> DLQ
    EmailWorker --> DLQ

    DLQ --> RetryWorker[재시도 워커]
    RetryWorker --> Alert[운영 알림]

    subgraph 저장 및 분석
        LogDB[(알림 로그 DB)]
        Analytics[분석 대시보드]
    end

    PushWorker --> LogDB
    SMSWorker --> LogDB
    EmailWorker --> LogDB
    LogDB --> Analytics
```

---

## 핵심 설계 결정 요약

| 결정 사항 | 선택 | 이유 |
|----------|------|------|
| 메시지 큐 | Kafka | 내구성 + 우선순위 토픽 분리 |
| 중복 방지 | Redis SET NX | 원자적 중복 체크 |
| 재시도 | 지수 백오프 + DLQ | 안정적 재처리 |
| 전송 보장 | Outbox 패턴 | 비즈니스 로직과 원자적 처리 |
| 우선순위 | 별도 Kafka 토픽 | 긴급 알림 병목 없음 |
| 대량 발송 | 배치 + 속도제한 | APNs/FCM 차단 방지 |
