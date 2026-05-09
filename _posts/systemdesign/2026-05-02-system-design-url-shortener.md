---
title: "URL 단축기 설계 — bit.ly가 7글자로 3.5조 개의 URL을 처리하는 방법"
categories:
- SYSTEMDESIGN
toc: true
toc_sticky: true
toc_label: 목차
---

트위터가 140자 제한이었던 시절, `https://www.example.com/very/long/path?campaign=summer&source=newsletter&medium=email` 같은 URL은 그 자체로 트윗 대부분을 차지했다. bit.ly는 이 문제를 7글자로 해결했다. 단순해 보이지만, 초당 10만 건의 리다이렉트를 100ms 이내에 처리하고 수십 TB의 데이터를 수년간 관리하는 시스템이다. **"짧게 만든다"는 단순한 기능 뒤에 어떤 설계가 숨어있는가.**

## 요구사항 분석

### 기능 요구사항

1. 긴 URL을 입력하면 짧은 URL 생성
2. 짧은 URL로 접속하면 원래 URL로 리다이렉트
3. 사용자 지정 단축 URL 지원 (선택)
4. 링크 만료 기간 설정 (선택)

### 비기능 요구사항 — 왜 이 숫자가 중요한가

```
읽기:쓰기 = 100:1   → 리다이렉트가 대부분, 캐시 전략이 핵심
리다이렉트 100ms 이내 → 사용자가 링크를 클릭했는데 느리면 이탈
99.99% 가용성       → 연간 52분. 이 서비스가 죽으면 모든 bit.ly 링크가 404가 됨
```

### 규모 추정

```
일일 새 URL 생성:   1억 건
읽기:쓰기 비율  = 100:1
일일 리다이렉트:   100억 건

쓰기 QPS  = 1억 / 86,400 ≈ 1,160 QPS
읽기 QPS  = 1,160 × 100  = 116,000 QPS
피크 QPS  = 116,000 × 3  ≈ 350,000 QPS

URL 하나 크기:
  shortCode: 7B, longURL: 100B, 메타데이터: 30B → 약 137B

10년 저장량:
  1억 × 365 × 10 × 137B ≈ 50TB
```

---

## 핵심 설계: 7자리 코드를 어떻게 만드는가

> **비유**: 도서관의 책 청구기호와 같다. 수십만 권의 책에 각각 짧은 고유 번호를 부여하고, 그 번호만 알면 정확한 위치를 찾아갈 수 있다. 번호는 짧아야 하고, 절대 중복되어선 안 된다.

7자리로 얼마나 많은 URL을 표현할 수 있는가? **문자 집합 선택**이 핵심이다.

| 방식 | 문자 수 | 7자리 공간 |
|------|--------|----------|
| 숫자만 (0-9) | 10 | 1,000만 |
| Base62 (0-9, a-z, A-Z) | 62 | **3.5조** |
| Base64 (+ +, /) | 64 | 4.4조 |

Base62를 선택하는 이유: URL에서 특수문자 없이 3.5조 공간 확보. 10년치 1억 개/일로는 3,650억 개가 필요한데 충분하다.

### Base62 인코딩 원리

숫자(고유 ID)를 62진법으로 변환하는 것이다:

```python
CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def encode(num: int) -> str:
    """고유 ID → Base62 문자열"""
    if num == 0:
        return CHARS[0]
    result = []
    while num > 0:
        result.append(CHARS[num % 62])
        num //= 62
    return ''.join(reversed(result))

# 12345 → "3D7"
# 복호화: '3'=3, 'D'=13, '7'=7
#   3×62² + 13×62 + 7
# = 3×3844 + 13×62 + 7
# = 11532 + 806 + 7 = 12345 ✓
```

### 고유 ID를 어떻게 만드는가 — Snowflake ID

Base62 인코딩은 "고유한 숫자"가 있어야 한다. 서버 20대가 동시에 같은 숫자를 생성하면 같은 단축 코드가 나온다. **Snowflake ID**가 이 문제를 해결한다:

```mermaid
graph LR
    subgraph "Snowflake ID 64비트 구조"
        T["41비트: 밀리초 타임스탬프<br>(약 69년치)"]
        M["10비트: 머신 ID<br>(1024대 서버)"]
        S["12비트: 시퀀스<br>(같은 ms에 4096개)"]
    end
    T --> ID["초당 409만 6천 개<br>고유 ID 생성"]
    M --> ID
    S --> ID
    ID --> BASE62["Base62 인코딩 → 7자리 코드"]
```

만약 Snowflake 없이 UUID를 쓰면? UUID는 128비트라 Base62로 변환하면 22자리가 넘는다. "짧은" URL이 되지 않는다. 단순 AUTO_INCREMENT를 쓰면? 여러 서버에서 동시에 같은 번호가 나온다.

---

## 전체 아키텍처

```mermaid
graph TD
    Client["클라이언트"] --> LB["로드밸런서"]
    LB --> API["API 서버 (Auto Scaling)"]
    API --> Cache["Redis 클러스터<br>읽기 트래픽 90% 처리"]
    API --> IDService["Snowflake ID 서비스 (이중화)"]
    API --> DB_W["MySQL 마스터 (쓰기)"]
    DB_W --> DB_R["MySQL 레플리카 (읽기)"]
    API --> Kafka["Kafka (클릭 이벤트 비동기)"]
    Kafka --> Analytics["분석 파이프라인"]
```

---

## URL 단축 흐름 (쓰기)

```mermaid
sequenceDiagram
    participant C as Client
    participant API
    participant DB as MySQL
    C->>API: POST /shorten
    API->>DB: 중복 확인
    alt 존재
        DB-->>API: 기존 shortCode
    else 신규
        API->>DB: ID생성+Base62+INSERT
    end
    API-->>C: shortUrl
```

---

## URL 리다이렉트 흐름 (읽기) — 왜 캐시가 필수인가

읽기 QPS가 116,000이다. 이 모두를 DB에서 처리하면 MySQL이 즉시 과부하된다. **캐시 히트율 80%**가 목표다:

```mermaid
sequenceDiagram
    participant C as Browser
    participant API
    participant Cache as Redis
    C->>API: GET /W7e
    API->>Cache: GET W7e
    alt Hit(80%)
        Cache-->>C: 302 Redirect
    else Miss(20%)
        API->>API: DB조회+Cache SET
        API-->>C: 302 Redirect
    end
```

### 301 vs 302 — 왜 bit.ly는 302를 쓰는가

| 구분 | 301 (영구) | 302 (임시) |
|------|-----------|-----------|
| 브라우저 캐싱 | O — 다음엔 서버 안 거침 | X — 매번 서버 거침 |
| 서버 부하 | 낮음 | 높음 |
| 클릭 추적 | **불가** — 브라우저가 직접 이동 | **가능** — 매번 서버 거쳐감 |

bit.ly의 수익은 클릭 분석 데이터다. 몇 명이 어디서 어떤 기기로 클릭했는지를 알아야 광고주에게 팔 수 있다. 그래서 302를 쓴다. 순수히 부하 최소화가 목표라면 301이 낫다.

---

## 데이터베이스 설계

```sql
CREATE TABLE urls (
    id          BIGINT      NOT NULL AUTO_INCREMENT,
    short_code  VARCHAR(7)  NOT NULL,
    long_url    VARCHAR(2048) NOT NULL,
    user_id     BIGINT,
    created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at  DATETIME,
    PRIMARY KEY (id),
    UNIQUE KEY uk_short_code (short_code),   -- 단축 코드 중복 방지
    INDEX idx_long_url (long_url(255)),       -- 동일 URL 재요청 시 빠른 조회
    INDEX idx_expires_at (expires_at)         -- 만료 배치 작업용
);
```

왜 `long_url`에 인덱스를 걸지 않으면 안 되는가? 같은 긴 URL을 두 번 단축 요청할 때 기존 코드를 반환해야 한다. 인덱스 없으면 매번 풀 스캔이다.

---

## 캐시 크기 계산

파레토 법칙: 상위 20% URL이 트래픽 80%를 처리한다.

```
전체 URL 수 = 1억 × 0.2 (상위 20%) = 2,000만 건
URL 하나 캐시 크기 = 7B + 100B = 107B
필요 메모리 = 2,000만 × 107B ≈ 2.1GB

→ Redis 서버 1대 (16GB)로 충분
```

캐시가 없다면? DB에 초당 116,000 쿼리. MySQL 커넥션 풀이 즉시 고갈된다.

---

## 확장성 — 언제 샤딩이 필요한가

10년 저장량이 50TB다. 단일 MySQL로는 한계가 있다. 단순 modulo 해싱(`hash % N`)은 샤드를 4개에서 5개로 늘리는 순간 대부분의 키가 다른 샤드로 이동한다. **Consistent Hashing**은 이 문제를 해결한다.

> **비유**: 0~360도 원형 링 위에 샤드와 키를 배치한다. 키는 시계 방향으로 가장 가까운 샤드에 할당된다. 샤드를 추가하면 그 샤드 바로 앞 구간의 키만 이동하면 된다. 전체 키의 `1/N`만 재배치된다.

```mermaid
graph LR
    API["API 서버"] --> CH["Consistent Hashing 링"]
    CH -->|"구간 A"| S1["샤드 1"]
    CH -->|"구간 B"| S2["샤드 2"]
    CH -->|"구간 C"| S3["샤드 3"]
    S4["샤드 4 추가\n→ 인접 구간만 이동"] -.->|"전체의 1/N만 재배치"| CH
```

**가상 노드(Virtual Nodes)**: 샤드 1대를 링 위에 100개의 가상 노드로 분산 배치한다. 샤드 간 데이터 불균형(핫스팟)을 방지하고, 샤드 추가·제거 시 부하가 여러 샤드에 고르게 분산된다.

```
modulo 해싱:        샤드 4→5개 증설 시 ~80% 키가 다른 샤드로 이동
Consistent Hashing: 샤드 4→5개 증설 시 ~20%(1/N)의 키만 이동
```

---

## Analytics 파이프라인 — 클릭 이후의 여정

Kafka로 클릭 이벤트를 보내는 것은 시작일 뿐이다. 실제로 "어떤 링크가 얼마나 클릭됐는가"를 실시간 대시보드와 일별·시간별 집계로 제공하는 전체 파이프라인이 필요하다.

```mermaid
graph TD
    Click["클릭 이벤트\n{shortCode, ip, ua, referer, ts}"] --> Kafka["Kafka\nclick-events 토픽"]
    Kafka --> Flink["Flink\n실시간 집계 (1분 윈도우)"]
    Kafka --> CH["ClickHouse\n원본 이벤트 저장"]
    Flink --> Redis["Redis\n실시간 카운터"]
    CH --> Dashboard["Grafana 대시보드\n실시간 + 히스토리"]
```

**ClickHouse — 클릭 분석 저장소**

ClickHouse는 컬럼형 OLAP DB로 수십억 건의 클릭 로그를 초당 수백만 행 삽입하면서 집계 쿼리도 초 단위로 처리한다. MySQL로 대용량 로그를 집계하면 수십 분이 걸리는 쿼리가 ClickHouse에선 수 초다.

```sql
-- 시간별 클릭 집계 (ClickHouse)
SELECT
    toStartOfHour(clicked_at)  AS hour,
    short_code,
    count()                    AS clicks,
    uniq(ip_masked)            AS unique_visitors
FROM click_events
WHERE short_code = 'W7e3p2K'
  AND clicked_at >= now() - INTERVAL 7 DAY
GROUP BY hour, short_code
ORDER BY hour DESC;
```

**일별/시간별 사전 집계**

원본 이벤트를 매번 집계하면 비용이 크다. Flink가 1분 단위로 집계한 결과를 별도 `click_stats` 테이블에 적재한다:

```sql
CREATE TABLE click_stats (
    short_code  VARCHAR(7)  NOT NULL,
    period      DATETIME    NOT NULL,   -- 1시간 단위 버킷
    granularity ENUM('hour','day') NOT NULL,
    clicks      BIGINT      NOT NULL,
    unique_ips  BIGINT      NOT NULL,
    PRIMARY KEY (short_code, period, granularity)
);
```

**실시간 대시보드**

- Redis에서 현재 시간 기준 최근 1분 클릭 수를 조회해 실시간 수치 표시
- ClickHouse에서 지난 30일 시계열을 쿼리해 차트 렌더링
- Grafana + ClickHouse 플러그인 조합이 실무에서 가장 널리 쓰인다

---

## URL 만료 처리

```mermaid
graph TD
    A["만료 처리 전략"] --> B["Lazy (요청 시 확인)"]
    A --> C["Eager (배치 정리)"]
    B --> B1["장점: 구현 단순"]
    B --> B2["단점: 만료된 행이 DB에 계속 존재"]
    C --> C1["장점: DB 용량 관리"]
    C --> C2["단점: 배치 부하"]
```

실무에서는 **두 가지 조합**: 요청 시 만료 확인(즉시 응답)  + 새벽 배치 정리(DB 정리).

```python
def redirect(short_code: str):
    url = db.query("SELECT long_url, expires_at FROM urls WHERE short_code = ?", short_code)
    if not url:
        raise NotFoundError()
    if url.expires_at and url.expires_at < datetime.now():
        raise GoneError()  # 410 Gone — 영구 삭제된 리소스
    return RedirectResponse(url.long_url, status_code=302)
```

---


## 극한 시나리오

유명 방송에서 bit.ly 링크가 노출되면 순간 트래픽이 평상시 100배가 된다.

```mermaid
graph TD
    Traffic["순간 초당 50만 요청"] --> CDN["CDN Edge<br>301 캐싱된 경우 바로 처리"]
    Traffic --> LB["Auto Scaling<br>서버 자동 증설"]
    LB --> LocalCache["각 서버 로컬 캐시<br>(Caffeine) — Redis도 우회"]
    LB --> Redis["Redis 클러스터<br>캐시 히트 99%"]
    Redis --> DB["DB 조회 극소화"]
```

**Hot URL 사전 감지:**

```python
def record_access(short_code: str):
    redis.zincrby("hot_urls", 1, short_code)  # 클릭마다 점수 증가

# 매 5분마다 상위 1000개를 서버 로컬 메모리에 pre-loading
@scheduler.every(minutes=5)
def preload_hot_urls():
    for short_code, _ in redis.zrevrange("hot_urls", 0, 999, withscores=True):
        local_cache[short_code] = db.get(short_code)
```

이 패턴이 없으면? Redis에도 초당 50만 요청이 몰린다. Redis는 빠르지만 무한하지 않다.

---

## 보안 고려사항

> **비유**: 우편함에 주소를 써두면 누구나 편지를 넣을 수 있듯, URL 단축기는 악성 링크를 "정상처럼 보이게" 위장하는 도구로 악용될 수 있다.

**악성 URL 차단 — Google Safe Browsing API**

단축 URL 생성 시 원본 URL을 Google Safe Browsing API에 조회해 피싱·멀웨어 배포 사이트 여부를 확인한다. 악성으로 판정되면 생성을 거부하고, 이미 생성된 링크가 뒤늦게 악성으로 분류되면 즉시 404로 전환한다.

```python
def is_safe_url(long_url: str) -> bool:
    resp = requests.post(SAFE_BROWSING_API, json={
        "client": {"clientId": "myapp"},
        "threatInfo": {"threatTypes": ["MALWARE", "SOCIAL_ENGINEERING"],
                       "urlList": [{"url": long_url}]}
    })
    return len(resp.json().get("matches", [])) == 0
```

**커스텀 단축코드 충돌 처리**

사용자 지정 코드(`bit.ly/mybrand`)는 DB UNIQUE 제약으로 충돌을 차단한다. 단, 예약어(`api`, `admin`, `health` 등)와 기존 자동 생성 코드 공간이 겹치지 않도록 커스텀 코드 네임스페이스를 분리 관리한다.

**클릭 데이터 프라이버시**

클릭 이벤트(IP, User-Agent, 리퍼러)는 분석 목적으로 수집되지만 개인 식별이 가능하다. IP는 저장 전 마지막 옥텟을 마스킹(1.2.3.x)하고, GDPR 삭제권 요청 시 해당 사용자의 클릭 로그를 90일 이내에 삭제하는 파이프라인을 갖춘다.

---
## 설계 결정 요약

| 결정 | 선택 | 이유 |
|------|------|------|
| 코드 생성 | Snowflake + Base62 | 분산 환경 충돌 없음, 7자리 3.5조 공간 |
| 리다이렉트 | 302 (임시) | 클릭 추적 가능 |
| 캐시 | Redis Cluster | 읽기 116k QPS를 DB에서 분리 |
| DB | Aurora MySQL | ACID + 읽기 레플리카 |
| 클릭 추적 | Kafka 비동기 | 리다이렉트 응답 시간에 영향 없음 |
| 샤딩 | Consistent Hashing | 샤드 추가 시 재배치 최소화 |
