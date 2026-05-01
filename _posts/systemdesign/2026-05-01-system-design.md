---
title: "시스템 디자인"
categories: SYSTEM_DESIGN
tags: [System Design, 확장성, CAP, 로드밸런서, CDN, 메시지큐, URL단축기]
toc: true
toc_sticky: true
toc_label: 목차
---

## 비유로 시작하기

수백만 명이 사용하는 카페를 설계한다고 생각해보세요. 처음엔 바리스타 한 명이 혼자 모든 것을 합니다. 손님이 늘어나면? 바리스타를 더 고용합니다(수평 확장). 큰 에스프레소 머신으로 바꿉니다(수직 확장). 음료를 미리 만들어 냉장고에 보관합니다(캐싱). 지점을 여러 곳에 냅니다(분산). 주문표를 사용합니다(메시지 큐).

시스템 디자인은 **대규모 트래픽을 처리하는 소프트웨어 시스템을 설계하는 방법론**입니다.

---

## 설계 프로세스

면접 및 실무에서 공통으로 사용되는 4단계 프로세스입니다.

```
1. 요구사항 명확화 (5분)
   - 기능 요구사항: 무엇을 해야 하나?
   - 비기능 요구사항: 얼마나 커야 하나? (MAU, TPS, 데이터 크기)

2. 규모 추정 (5분)
   - MAU 1억 명 → DAU 1000만 명 → TPS ~1200
   - 저장 데이터: 게시글 1억 개 × 평균 1KB = 100GB

3. 고수준 설계 (15분)
   - 핵심 컴포넌트 선정
   - 데이터 흐름 설계

4. 상세 설계 (25분)
   - 핵심 컴포넌트 깊이 설계
   - 병목 지점 해결
   - 트레이드오프 논의
```

---

## 확장성 (Scalability)

### 수직 확장 (Vertical Scaling, Scale-Up)

더 강력한 서버로 교체합니다.

```
4 Core, 16GB RAM → 32 Core, 256GB RAM
```

장점: 구현 단순, 설정 변경 없음
단점: 한계가 있음, 단일 장애점(SPOF), 비용이 지수적으로 증가

### 수평 확장 (Horizontal Scaling, Scale-Out)

서버 대수를 늘립니다.

```
서버 1대 → 서버 10대 → 서버 100대
```

장점: 이론적으로 무한 확장, 고가용성
단점: 상태 공유 문제, 데이터 일관성, 설계 복잡도 증가

<div class="mermaid">
graph TD
    CLIENT[클라이언트]
    LB[로드밸런서]
    S1[서버 1]
    S2[서버 2]
    S3[서버 3]
    CACHE[(Redis Cache)]
    DB[(DB Master)]
    DB_R1[(DB Replica 1)]
    DB_R2[(DB Replica 2)]

    CLIENT --> LB
    LB --> S1
    LB --> S2
    LB --> S3
    S1 --> CACHE
    S2 --> CACHE
    S3 --> CACHE
    S1 --> DB
    S2 --> DB
    S3 --> DB
    DB --> DB_R1
    DB --> DB_R2
    S1 -->|읽기| DB_R1
    S2 -->|읽기| DB_R2
</div>

---

## CAP 정리

분산 시스템에서 **일관성(Consistency), 가용성(Availability), 파티션 허용(Partition Tolerance)** 중 2가지만 보장 가능합니다.

<div class="mermaid">
graph TD
    C[Consistency<br>모든 노드가 같은 데이터]
    A[Availability<br>항상 응답 가능]
    P[Partition Tolerance<br>네트워크 분리 상황에서도 동작]

    CP[CP 시스템<br>HBase, Zookeeper, MongoDB]
    AP[AP 시스템<br>Cassandra, DynamoDB, CouchDB]
    CA[CA 시스템<br>단일 노드 RDBMS<br>분산 환경에서 불가능]

    C --> CP
    P --> CP
    A --> AP
    P --> AP
    C --> CA
    A --> CA
</div>

**현실**: 네트워크 파티션은 항상 발생할 수 있으므로 P는 필수입니다. 따라서 **CP vs AP 중 선택**이 실제 트레이드오프입니다.

```
은행 계좌 이체: CP 선택
- 일관성 최우선, 잠깐 응답 못해도 괜찮음

SNS 좋아요 수: AP 선택
- 잠깐 다른 수치가 보여도 괜찮음, 항상 응답해야 함
```

---

## 로드밸런서

트래픽을 여러 서버에 분산합니다.

### 알고리즘

| 알고리즘 | 설명 | 적합한 상황 |
|---------|------|-----------|
| Round Robin | 순서대로 분산 | 서버 성능이 동일할 때 |
| Weighted Round Robin | 성능 비율로 분산 | 서버 성능이 다를 때 |
| Least Connections | 연결 수 적은 서버 우선 | 처리 시간이 다양할 때 |
| IP Hash | 클라이언트 IP 기반 고정 | 세션 유지 필요할 때 |

### L4 vs L7

```
L4 (Transport Layer): TCP/UDP 기반 라우팅
  - 빠름, 패킷 내용 못 봄
  - 예: AWS NLB, HAProxy

L7 (Application Layer): HTTP 헤더/URL/쿠키 기반 라우팅
  - 콘텐츠 기반 라우팅 가능
  - 예: Nginx, AWS ALB
```

---

## CDN (Content Delivery Network)

전 세계 엣지 서버에 정적 콘텐츠를 캐싱하여 사용자와 물리적으로 가까운 서버에서 제공합니다.

<div class="mermaid">
sequenceDiagram
    participant USER as 한국 사용자
    participant CDN_KR as CDN 서울 엣지
    participant ORIGIN as Origin 서버 (미국)

    USER->>CDN_KR: 이미지 요청
    alt CDN 캐시 HIT
        CDN_KR-->>USER: 즉시 응답 (10ms)
    else CDN 캐시 MISS
        CDN_KR->>ORIGIN: 원본 요청
        ORIGIN-->>CDN_KR: 이미지 반환
        CDN_KR->>CDN_KR: 캐싱
        CDN_KR-->>USER: 응답 (200ms)
    end
</div>

정적 파일(이미지, JS, CSS), 동영상 스트리밍에 필수입니다. CloudFront, Akamai, Cloudflare가 대표적입니다.

---

## 메시지 큐

서비스 간 비동기 통신을 위한 **버퍼**입니다.

```
동기: 주문 서비스 → 직접 호출 → 이메일 서비스
  문제: 이메일 서비스 다운 시 주문 실패

비동기: 주문 서비스 → [Kafka] → 이메일 서비스
  장점: 이메일 서비스 다운되도 주문은 성공, 이메일은 나중에 처리
```

활용 패턴:
- **이벤트 기반 아키텍처**: 주문 완료 이벤트 → 결제/배송/알림 서비스
- **트래픽 스파이크 완충**: 초당 10만 요청 → 큐 → 서비스가 처리 가능한 속도로 소비
- **서비스 분리**: 결합도 낮추기

---

## DB 선택 기준

<div class="mermaid">
graph TD
    Q1{관계형 데이터?}
    Q2{고정 스키마?}
    Q3{ACID 필요?}
    Q4{대용량 비정형?}
    Q5{Key-Value?}
    Q6{그래프 데이터?}

    Q1 -->|Yes| Q2
    Q2 -->|Yes| Q3
    Q3 -->|Yes| RDBMS[MySQL/PostgreSQL]
    Q3 -->|No| Q4
    Q4 -->|비정형 문서| MONGO[MongoDB]
    Q5 -->|Yes| REDIS[Redis/DynamoDB]
    Q6 -->|Yes| NEO4J[Neo4j]
    Q1 -->|No| Q4
    Q4 -->|대용량 시계열| INFLUX[InfluxDB/Cassandra]
</div>

| 요구사항 | DB 선택 |
|---------|---------|
| 트랜잭션, 복잡한 쿼리 | MySQL, PostgreSQL |
| 빠른 Key-Value 조회 | Redis, DynamoDB |
| 유연한 스키마, 문서 | MongoDB |
| 대용량 시계열 | InfluxDB, Cassandra |
| 그래프/관계 탐색 | Neo4j |
| 전문 검색 | Elasticsearch |

---

## 캐싱 계층

```
캐싱 계층 (가까울수록 빠름):

Client Cache → CDN → API Gateway Cache → Application Cache (Redis) → DB
```

### 캐싱 전략

```
Cache-Aside (Look-Aside): 앱이 캐시 확인 → 미스 시 DB 조회 → 캐시 저장
  장점: 실제 읽은 데이터만 캐싱
  단점: 첫 요청은 항상 느림 (Cold Start)

Write-Through: 쓰기 시 캐시와 DB 동시 업데이트
  장점: 캐시 항상 최신
  단점: 쓰기 지연

Write-Back: 캐시만 쓰고 나중에 DB 동기화
  장점: 쓰기 빠름
  단점: 데이터 유실 위험
```

---

## 실전 설계 예제

### URL 단축 서비스 (bit.ly)

**요구사항**:
- 긴 URL을 짧은 URL로 변환
- DAU 100만, URL 생성 10만/일, 조회 1000만/일 (읽기:쓰기 = 100:1)

**핵심 설계**:

```
단축 URL 생성 알고리즘:
1. 원본 URL을 DB에 저장 → 자동 증가 ID 발급 (예: 12345678)
2. ID를 Base62 인코딩: 12345678 → "dnh75"
3. 짧은 URL: https://short.ly/dnh75

Base62 = 0-9, a-z, A-Z (62자)
6자리 Base62 = 62^6 ≈ 568억 개 URL 수용
```

<div class="mermaid">
graph TD
    CLIENT[클라이언트]
    LB[로드밸런서]
    API[API 서버]
    CACHE[(Redis Cache<br>단축URL → 원본URL)]
    DB[(MySQL<br>id, short_url, original_url)]
    CDN[CDN]

    CLIENT -->|POST /shorten| LB
    LB --> API
    API -->|저장| DB
    DB -->|ID 반환| API
    API -->|Base62 인코딩| API

    CLIENT -->|GET /dnh75| CDN
    CDN -->|캐시 미스| LB
    LB --> API
    API -->|캐시 조회| CACHE
    CACHE -->|캐시 미스| DB
    DB -->|원본 URL| API
    API -->|302 Redirect| CLIENT
</div>

### 채팅 시스템

**핵심 문제**: 어떻게 실시간으로 메시지를 전달할까?

```
폴링(Polling): 클라이언트가 주기적으로 새 메시지 확인
  문제: 불필요한 요청, 실시간성 부족

Long Polling: 응답 없으면 연결 유지, 메시지 오면 응답
  문제: 연결 자원 낭비

WebSocket: 양방향 지속 연결
  장점: 진짜 실시간, 효율적
  적합: 채팅에 최적
```

```
메시지 저장 설계:
- 최근 메시지: Redis (빠른 조회)
- 영구 저장: Cassandra (파티션 키=채널ID, 정렬 키=타임스탬프)
  → 특정 채널의 최근 메시지를 시간순으로 빠르게 조회
```

### 뉴스피드 (Twitter/Instagram)

**두 가지 모델**:

```
Fan-out on Write (Push 모델):
  글 작성 시 팔로워 전원의 피드에 미리 저장
  장점: 읽기 빠름
  단점: 팔로워 100만 명 → 글 하나에 100만 건 쓰기 (유명인 문제)

Fan-out on Read (Pull 모델):
  읽을 때 팔로잉 목록 조회 → 각각의 최신 글 수집
  장점: 쓰기 빠름
  단점: 읽기 느림

실무 (하이브리드):
  일반 사용자: Push 모델
  유명인 (팔로워 100만+): Pull 모델
```

---

## 극한 시나리오

### 시나리오: 갑작스러운 10배 트래픽 (셀럽 포스팅)

```
준비:
1. HPA로 자동 스케일아웃 (CPU 70% → Pod 추가)
2. DB Read Replica로 읽기 분산
3. CDN 캐싱으로 정적 콘텐츠 오프로드
4. 핫 데이터 Redis 캐싱

최후 방어선:
5. 서킷 브레이커: 백엔드 과부하 시 빠른 실패 반환
6. Rate Limiting: IP당 초당 100 요청 제한
7. 큐잉: 처리 가능한 속도로 조절
```
