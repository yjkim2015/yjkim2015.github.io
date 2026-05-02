---
title: "시스템 디자인 기초 — 대규모 시스템 설계 완전 정복"
categories:
- SYSTEMDESIGN
toc: true
toc_sticky: true
toc_label: 목차
---

> **한 줄 요약**: 확장성·가용성·일관성은 서로 트레이드오프 관계이며, CAP/PACELC 정리가 분산 시스템 설계의 나침반이다.

## 왜 시스템 디자인 기초가 중요한가?

식당을 상상해 보세요. 주방장 한 명, 홀 직원 한 명일 때는 5명 손님을 완벽하게 처리합니다. 손님이 500명이 되면? 주방장 혼자서는 절대 감당 불가입니다. **주방장을 늘리거나(수평 확장)**, **더 좋은 장비를 사거나(수직 확장)**, **여러 지점을 내거나(분산)** 해야 합니다. 대규모 소프트웨어 시스템도 정확히 같은 문제를 겪습니다.

카카오, 네이버, 쿠팡이 수천만 명의 사용자를 어떻게 감당하는지, 그 설계 원칙을 이해하는 것이 **시스템 디자인**입니다. 면접에서도, 실무에서도 이 기초 개념들의 트레이드오프를 명확히 이해해야 올바른 아키텍처 결정을 내릴 수 있습니다.

---

## 1. 확장성 (Scalability)

### 확장성이란?

확장성은 **사용자가 늘어났을 때 시스템이 얼마나 잘 버티는가**를 의미합니다. 단순히 "많은 트래픽을 처리할 수 있는가"를 넘어, "어떻게 트래픽 증가에 대응하는가"에 대한 전략입니다.

#### 수직 확장 (Vertical Scaling) — Scale Up

더 강력한 단일 서버로 교체하는 방식입니다. AWS에서 EC2 t3.micro를 r5.32xlarge(128 vCPU, 1TB RAM)로 업그레이드하는 것이 대표적입니다.

```
[서버 A: CPU 4코어, RAM 16GB]
          ↓ 업그레이드
[서버 A: CPU 128코어, RAM 1TB]
```

**장점**: 구현이 단순하고, 애플리케이션 코드 변경이 불필요합니다. 서버 간 네트워크 지연이 없습니다.

**단점**: 하드웨어 스펙에 물리적 상한선이 존재합니다. 단일 장애점(SPOF)이 되어 서버 한 대 장애 시 전체 서비스가 중단됩니다. 고사양 서버일수록 비용이 기하급수적으로 증가합니다.

#### 수평 확장 (Horizontal Scaling) — Scale Out

동일한 서버 여러 대를 로드밸런서 뒤에 두는 방식입니다. 쿠팡, 네이버 같은 대형 서비스의 핵심 전략입니다.

```
[서버 A: CPU 4코어, RAM 16GB]
[서버 B: CPU 4코어, RAM 16GB]
[서버 C: CPU 4코어, RAM 16GB]
          ↕ 로드밸런서
        [사용자 트래픽]
```

**장점**: 이론상 무한 확장 가능합니다. 장애 내성이 향상되며, 범용 서버를 사용해 비용이 효율적입니다.

**단점**: 분산 시스템 복잡도가 증가합니다. 서버 간 상태(State) 공유 문제가 발생합니다. 네트워크 비용이 발생합니다.

<div class="mermaid">
graph TD
    A["1️⃣ 트래픽 증가 감지"] --> B{"2️⃣ 확장 전략 선택"}
    B --> C["3️⃣ 수직 확장\nScale Up"]
    B --> D["3️⃣ 수평 확장\nScale Out"]
    C --> E["더 큰 서버로 교체\n빠르지만 한계 존재"]
    D --> F["4️⃣ 로드밸런서 추가"]
    F --> G["서버 1"]
    F --> H["서버 2"]
    F --> I["서버 N\n무한 확장 가능"]

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class A,B client
    class C,D,F server
    class E,G,H,I db
</div>

### 확장성 측정 지표

| 지표 | 설명 | 실무 예시 |
|------|------|----------|
| TPS (Transactions Per Second) | 초당 처리 건수 | 결제 시스템: 1만 TPS |
| QPS (Queries Per Second) | 초당 쿼리 수 | 검색 서비스: 100만 QPS |
| P99 응답 시간 | 99번째 백분위 응답시간 | 쿠팡: P99 < 200ms |
| 처리량 (Throughput) | 단위 시간당 데이터 처리량 | Kafka: 1GB/s |

### 왜 이게 중요한가?

초기 스타트업은 수직 확장이 맞습니다. 복잡도 없이 빠르게 성장에 대응할 수 있습니다. 하지만 **특정 규모(보통 수십만 DAU)를 넘어서면 수직 확장의 비용이 수평 확장보다 훨씬 비싸지고, 단일 장애점 문제가 치명적**이 됩니다. 언제 전환할지 타이밍을 아는 것이 아키텍트의 핵심 역량입니다.

### 실무에서 자주 하는 실수

수평 확장으로 전환할 때 **세션 공유 문제**를 간과합니다. 로컬 메모리에 세션을 저장하던 애플리케이션은 서버가 여러 대가 되는 순간 동일 사용자가 다른 서버에 접근하면 세션을 잃어버립니다. Redis 같은 분산 세션 저장소로 전환이 필수입니다.

---

## 2. 가용성 (Availability)

### 가용성이란?

**시스템이 정상적으로 작동하는 시간의 비율**입니다. 편의점이 24시간 365일 운영된다면 가용성 100%입니다. 하루 1시간만 닫아도 가용성 95.8%가 됩니다.

```
가용성(%) = (정상 운영 시간) / (전체 시간) × 100
```

### "나인(Nine)" 표기법 — 실제 다운타임 계산

| 표기 | 가용성 | 월 다운타임 | 연간 다운타임 |
|------|--------|------------|--------------|
| 2 Nines | 99% | 7.2시간 | 3.65일 |
| 3 Nines | 99.9% | 43.8분 | 8.76시간 |
| 4 Nines | 99.99% | 4.38분 | 52.6분 |
| 5 Nines | 99.999% | 26.3초 | 5.26분 |
| 6 Nines | 99.9999% | 2.63초 | 31.5초 |

> **핵심**: 금융·의료 시스템은 최소 4~5 Nines를 요구합니다. 4 Nines를 달성하려면 연간 배포 다운타임 포함 모든 장애가 52분 이내여야 합니다. 이를 위해 **블루/그린 배포**, **카나리 배포**가 필수입니다.

### MTBF와 MTTR — 가용성의 두 축

```
MTBF (Mean Time Between Failures): 평균 장애 간격
MTTR (Mean Time To Recovery): 평균 복구 시간

가용성 = MTBF / (MTBF + MTTR)
```

예시: MTBF = 100시간, MTTR = 1시간
- 가용성 = 100 / (100 + 1) = **99.01% (2 Nines)**

MTTR을 0.1시간으로 줄이면:
- 가용성 = 100 / (100 + 0.1) = **99.9% (3 Nines)**

**결론**: 가용성을 높이려면 MTBF(장애 빈도 줄이기)와 MTTR(복구 속도 올리기) 두 방향 모두 개선해야 합니다.

<div class="mermaid">
graph TD
    A["1️⃣ 고가용성 목표 설정"] --> B["2️⃣ 이중화 Redundancy"]
    A --> C["2️⃣ 장애 감지 Monitoring"]
    A --> D["2️⃣ 자동 복구 Auto Recovery"]
    B --> E["서버 이중화\n최소 2대 운영"]
    B --> F["DB 이중화\nMaster-Replica"]
    B --> G["네트워크 이중화\n이중 경로"]
    C --> H["3️⃣ 헬스체크\n30초 간격"]
    C --> I["알람 시스템\nPagerDuty/OpsGenie"]
    D --> J["Auto Scaling\n부하 따라 자동 증감"]
    D --> K["4️⃣ 자동 Failover\n장애 시 자동 전환"]

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class A client
    class B,C,D,E,F,G server
    class H,I,J,K db
</div>

### 면접 포인트

> "99.99% 가용성을 어떻게 달성하나요?" — 단순히 "이중화"라고 답하면 안 됩니다. **배포 전략(블루/그린), DB 페일오버 시간(보통 30~60초), 그 동안의 요청 처리 방법(큐잉/재시도)**까지 구체적으로 답해야 합니다.

---

## 3. 일관성 (Consistency)

### 일관성이란?

**모든 노드가 같은 시점에 같은 데이터를 보는 것**입니다. 은행 계좌에서 A가 100만원을 이체했을 때, 전 세계 어느 ATM에서 조회해도 즉시 잔액이 업데이트되어야 한다면 **강한 일관성**입니다. 반면 몇 초 후에 반영되어도 괜찮다면 **최종 일관성**입니다.

### 일관성 수준 — 강함에서 약함 순서

<div class="mermaid">
graph LR
    A["강한 일관성\nStrong"] --> B["순차적 일관성\nSequential"]
    B --> C["인과적 일관성\nCausal"]
    C --> D["최종 일관성\nEventual"]

    A -.->|"성능 낮음\n지연 높음"| E["저성능"]
    D -.->|"성능 높음\n지연 낮음"| F["고성능"]

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    class A,B client
    class C,D server
</div>

| 일관성 수준 | 설명 | 실무 사용 예 |
|------------|------|------------|
| 강한 일관성 | 모든 읽기에서 최신 쓰기 반환 | 금융 거래, 재고 관리 |
| 순차적 일관성 | 모든 노드가 같은 순서로 작업 관찰 | 분산 락, Zookeeper |
| 인과적 일관성 | 원인-결과 관계 보장 | SNS 댓글, 게시물 좋아요 |
| 최종 일관성 | 결국에는 동일한 값으로 수렴 | DNS, 쇼핑몰 조회수 |

### 왜 이게 중요한가?

일관성 수준을 잘못 선택하면 **데이터 손실**이나 **사용자 혼란**이 발생합니다. 쇼핑몰 재고를 최종 일관성으로 관리하면 "마지막 1개 남은 상품"을 여러 명이 동시에 구매하는 오버셀링이 발생합니다. 반대로 소셜 미디어 '좋아요' 수를 강한 일관성으로 처리하면 매 좋아요마다 분산 락을 잡아야 해 성능이 수십 배 저하됩니다.

---

## 4. CAP 정리

### CAP 정리란?

분산 시스템에서 **세 가지 속성 중 동시에 두 가지만 보장 가능**하다는 이론입니다 (Eric Brewer, 2000년).

- **C (Consistency)**: 모든 노드가 같은 데이터를 봄
- **A (Availability)**: 모든 요청이 응답을 받음 (에러 포함)
- **P (Partition Tolerance)**: 네트워크 분리가 발생해도 동작

<div class="mermaid">
graph TD
    CAP(("CAP 정리\n3개 중 2개만 가능"))
    C["일관성\nConsistency\n모든 노드 동일 데이터"]
    A["가용성\nAvailability\n모든 요청 응답"]
    P["분할 내성\nPartition Tolerance\n네트워크 장애 허용"]

    CAP --> C
    CAP --> A
    CAP --> P

    C --- CA["CA 시스템\nRDB 단일노드\n분산 아님"]
    C --- CP["CP 시스템\nHBase, Zookeeper\nMongoDB"]
    A --- CA
    A --- AP["AP 시스템\nCassandra, DynamoDB\nCouchDB"]
    P --- CP
    P --- AP

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class C client
    class A server
    class P,CA,CP,AP db
</div>

> **현실에서는**: 분산 시스템에서 네트워크 분할(P)은 불가피합니다. 따라서 실질적으로는 **CP vs AP 선택**입니다. CA는 단일 노드 RDBMS에만 해당합니다.

### 시스템별 CAP 위치

| 시스템 | CAP 분류 | 이유 |
|--------|---------|------|
| MySQL (단일 노드) | CA | 분산 아님, 네트워크 분할 없음 |
| MySQL Cluster | CP | 파티션 시 쓰기 거부 |
| Cassandra | AP | 파티션 시 오래된 데이터로 응답 |
| HBase | CP | HDFS 의존, 일관성 우선 |
| DynamoDB | AP (기본) | 최종 일관성이 기본값 |
| Redis Cluster | AP | 마스터 장애 시 가용성 우선 |
| Zookeeper | CP | 리더 선출로 일관성 보장 |
| etcd | CP | Raft 합의 알고리즘 |

### 실전 예시: 네트워크 분할 시 선택

```
[데이터센터 A] ----X---- [데이터센터 B]
    서버 1,2              서버 3,4

네트워크 장애 발생!

CP 선택 (예: Zookeeper):
  → 서버 3,4에 대한 요청 거부 (에러 반환)
  → 가용성 포기, 일관성 유지
  → 금융, 결제 시스템에 적합

AP 선택 (예: Cassandra):
  → 서버 3,4가 오래된 데이터로 응답
  → 일관성 포기, 가용성 유지
  → SNS, 쇼핑몰 상품 목록에 적합
```

### 면접 포인트

> "CAP에서 항상 P를 선택해야 하는 이유는?" — 분산 시스템에서 네트워크 장애는 피할 수 없습니다. AWS에서도 연간 수십 번의 네트워크 이슈가 발생합니다. P를 포기하면 분산 시스템을 만드는 의미가 없습니다. 따라서 실제 선택은 C와 A 사이입니다.

---

## 5. PACELC 정리 (CAP의 현실적 확장)

CAP은 장애 상황(Partition)만 다루지만, **평상시(Else)에도 일관성(Consistency)과 지연 시간(Latency) 사이의 트레이드오프**가 존재합니다. Daniel Abadi가 2012년에 제안한 모델입니다.

```
P → A 또는 C 선택 (장애 시)
E → L 또는 C 선택 (평상시)
```

<div class="mermaid">
graph TD
    A["1️⃣ 네트워크 분할 발생?"]
    A -->|"Yes — Partition"| B["2️⃣ P 상황"]
    A -->|"No — Else"| C["2️⃣ E 상황\n정상 운영"]

    B --> D["가용성 Availability 선택"]
    B --> E["일관성 Consistency 선택"]

    C --> F["지연시간 Latency 선택"]
    C --> G["일관성 Consistency 선택"]

    D --> H["PA/EL: Cassandra, DynamoDB\n가용성+속도 우선"]
    E --> I["PC/EC: Zookeeper, HBase\n일관성 우선"]
    F --> H
    G --> J["PC/EC: PostgreSQL\n정확성 우선"]

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class A,B,C client
    class D,E,F,G server
    class H,I,J db
</div>

| 시스템 | PACELC | 특징 |
|--------|--------|------|
| DynamoDB | PA/EL | 가용성+낮은 지연 기본값, 강한 일관성 옵션 추가 가능 |
| Cassandra | PA/EL | 조정 가능한 일관성(QUORUM 등) |
| MySQL | PC/EC | ACID 트랜잭션, 강한 일관성 |
| MongoDB | PC/EC | 기본값 강한 일관성 (writeConcern majority) |

### 왜 이게 중요한가?

CAP 정리만 알면 "장애 시"의 선택만 이해하지만, 실무에서는 **정상 운영 중 일관성과 속도 사이의 선택**이 훨씬 더 자주 발생합니다. DynamoDB에서 강한 일관성 읽기를 사용하면 지연이 2배 증가합니다. PACELC는 이 현실적 트레이드오프를 포착합니다.

---

## 6. 로드밸런싱 기초

### 로드밸런서란?

대형 마트의 계산대 안내원을 생각해 보세요. 손님들이 줄 서는 대신, 안내원이 각 계산대의 대기 상황을 보고 "3번 줄로 가세요"라고 안내합니다. 이것이 로드밸런서입니다.

<div class="mermaid">
graph TD
    subgraph "클라이언트 계층"
        U1["사용자 1"]
        U2["사용자 2"]
        U3["사용자 N"]
    end
    subgraph "로드밸런서 계층"
        LB["1️⃣ 로드밸런서\nNginx / AWS ALB"]
    end
    subgraph "서버 계층"
        S1["2️⃣ 서버 1\nCPU 30%"]
        S2["2️⃣ 서버 2\nCPU 80%"]
        S3["2️⃣ 서버 3\nCPU 15%"]
    end
    subgraph "데이터 계층"
        DB[("3️⃣ 데이터베이스")]
    end

    U1 --> LB
    U2 --> LB
    U3 --> LB
    LB --> S1
    LB --> S2
    LB --> S3
    S1 --> DB
    S2 --> DB
    S3 --> DB

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class U1,U2,U3 client
    class LB,S1,S2,S3 server
    class DB db
</div>

### 로드밸런싱 알고리즘 상세 비교

#### 1) 라운드 로빈 (Round Robin)
```
요청 순서: 1→서버A, 2→서버B, 3→서버C, 4→서버A, ...

장점: 단순, 균등 분배
단점: 서버 성능 차이 무시, 긴 처리 요청과 짧은 처리 요청 혼재 시 불균형
적합: 동일 스펙 서버, 동일 처리 시간 요청
```

#### 2) 가중치 라운드 로빈 (Weighted Round Robin)
```
서버A (가중치 5, CPU 32코어): 5번 요청
서버B (가중치 3, CPU 16코어): 3번 요청
서버C (가중치 2, CPU 8코어): 2번 요청

적합: 서버 스펙이 다른 이기종 환경
```

#### 3) 최소 연결 (Least Connections)
```
현재 상태:
서버A: 연결 100개
서버B: 연결 30개  ← 새 요청 배정
서버C: 연결 70개

적합: WebSocket 같은 장기 연결, 처리 시간이 다양한 작업
```

#### 4) IP 해시 (IP Hash)
```
클라이언트 IP → 해시 → 특정 서버 고정
192.168.1.1 → hash → 항상 서버A
192.168.1.2 → hash → 항상 서버B

적합: 세션 친화성(Sticky Session) 필요 시
주의: 특정 IP 대역 집중 시 서버 불균형
```

<div class="mermaid">
graph LR
    A["로드밸런싱\n알고리즘"]
    A --> B["Round Robin\n단순 순환"]
    A --> C["Weighted RR\n가중치 순환"]
    A --> D["Least Connections\n최소 연결"]
    A --> E["IP Hash\nIP 기반 고정"]

    B --> F["균등 서버 환경"]
    C --> G["이기종 서버 환경"]
    D --> H["WebSocket/긴 처리"]
    E --> I["세션 유지 필요"]

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class A client
    class B,C,D,E server
    class F,G,H,I db
</div>

---

## 7. 데이터베이스 확장

### 읽기 복제 (Read Replica)

대부분의 웹 서비스는 읽기:쓰기 비율이 **80:20 또는 90:10**입니다. 읽기 복제를 통해 읽기 부하를 분산합니다.

<div class="mermaid">
graph TD
    W["1️⃣ 쓰기 요청\nINSERT/UPDATE/DELETE"] --> M[("2️⃣ 마스터 DB\nPrimary")]
    M -->|"3️⃣ 비동기 복제"| R1[("레플리카 1")]
    M -->|"3️⃣ 비동기 복제"| R2[("레플리카 2")]
    M -->|"3️⃣ 비동기 복제"| R3[("레플리카 3")]

    R1 --> Q["4️⃣ 읽기 요청\nSELECT"]
    R2 --> Q
    R3 --> Q

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class W,Q client
    class M server
    class R1,R2,R3 db
</div>

**복제 지연(Replication Lag) 주의사항**: 비동기 복제 시 마스터에 쓴 데이터가 레플리카에 반영되는 데 수백 ms ~ 수 초가 걸릴 수 있습니다. "방금 저장한 데이터를 즉시 읽어야 하는" 경우(예: 회원가입 직후 프로필 조회)는 마스터에서 읽어야 합니다.

### 샤딩 (Sharding)

도서관 책을 이름순으로 A-G는 1층, H-N은 2층, O-Z는 3층에 배치하는 것과 같습니다. DB를 여러 조각(샤드)으로 나눠 각기 다른 서버에 저장합니다.

<div class="mermaid">
graph TD
    App["1️⃣ 애플리케이션"] --> SR["2️⃣ 샤드 라우터\n(어느 샤드로 보낼지 결정)"]
    SR --> S1[("3️⃣ 샤드 1\nUser ID 1~1000만")]
    SR --> S2[("3️⃣ 샤드 2\nUser ID 1001만~2000만")]
    SR --> S3[("3️⃣ 샤드 3\nUser ID 2001만~3000만")]

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class App client
    class SR server
    class S1,S2,S3 db
</div>

**샤딩 전략 비교:**

| 전략 | 방법 | 장점 | 단점 |
|------|------|------|------|
| 범위 기반 | ID 1-1000만 → 샤드1 | 범위 쿼리 효율적 | 핫스팟(최신 데이터 집중) |
| 해시 기반 | hash(ID) % N | 균등 분배 | 범위 쿼리 비효율, 리샤딩 어려움 |
| 디렉토리 기반 | 별도 매핑 테이블 | 유연한 재분배 | 매핑 테이블 병목, SPOF |
| 지리 기반 | 한국 사용자 → 한국 샤드 | 지연 최소화 | 데이터 불균형 가능 |

**샤딩의 단점**: 조인 쿼리가 불가능(여러 샤드에 걸친 JOIN 비효율), 샤드 재분배(리샤딩) 어려움, 트랜잭션 처리 복잡 등의 문제가 있습니다. **샤딩 전에 읽기 복제, 캐싱, 쿼리 최적화를 모두 시도한 후** 마지막 수단으로 선택해야 합니다.

---

## 8. 캐싱 (Caching)

### 캐시란?

자주 가는 편의점을 생각해보세요. 매번 창고에서 물건을 꺼내오는 것보다 진열대(캐시)에 미리 꺼내두면 훨씬 빠릅니다. DB 조회는 수십 ms, Redis 캐시 조회는 수십 µs로 **100~1000배 빠릅니다**.

<div class="mermaid">
graph LR
    A["1️⃣ 사용자 요청"] --> B{"2️⃣ 캐시 확인\nRedis"}
    B -->|"Cache Hit\n캐시 명중"| C["3️⃣ 캐시에서 즉시 반환\n수십 µs"]
    B -->|"Cache Miss\n캐시 미스"| D["3️⃣ DB 조회\n수십 ms"]
    D --> E["4️⃣ 캐시에 저장\nTTL 설정"]
    E --> F["5️⃣ 사용자에게 반환"]

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class A client
    class B,C,E,F server
    class D db
</div>

### 캐시 계층 구조

```
L1 캐시: CPU 레지스터/L1-L3 캐시 (나노초, 수십 MB)
L2 캐시: JVM Heap / 로컬 메모리 캐시 (마이크로초, 수 GB)
L3 캐시: 분산 캐시 Redis/Memcached (밀리초, 수십 TB)
L4 캐시: CDN 엣지 서버 (100ms~, 무한 확장)
```

### 캐시 전략 4가지

<div class="mermaid">
graph TD
    A["캐시 전략 선택"]
    A --> B["Cache-Aside\nLazy Loading"]
    A --> C["Write-Through"]
    A --> D["Write-Behind\nWrite-Back"]
    A --> E["Read-Through"]

    B --> F["앱이 직접 캐시 관리\n미스 시 DB 조회 후 저장\n가장 많이 사용"]
    C --> G["쓰기 시 캐시+DB 동시 업데이트\n일관성 높음\n쓰기 느림"]
    D --> H["캐시 먼저 쓰고 나중에 DB\n쓰기 매우 빠름\n장애 시 데이터 손실 위험"]
    E --> I["캐시가 DB 조회 대행\n코드 단순화\nCache-Aside와 유사"]

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class A client
    class B,C,D,E server
    class F,G,H,I db
</div>

### 캐시 무효화 (Cache Invalidation)

> "컴퓨터 과학에서 어려운 문제는 두 가지: 캐시 무효화와 이름 짓기" — Phil Karlton

**TTL (Time To Live) 기반**:
```java
// Redis에서 1시간 TTL 설정
redisTemplate.opsForValue().set("user:" + userId, userData, Duration.ofHours(1));
```

**이벤트 기반 무효화**:
```java
// DB 업데이트 시 캐시 즉시 삭제
@Transactional
public void updateUser(Long userId, UserRequest req) {
    userRepository.save(req.toEntity(userId));
    redisTemplate.delete("user:" + userId);  // 캐시 즉시 무효화
}
```

### 실무에서 자주 하는 실수

**캐시 스탬피드(Cache Stampede)**: 인기 캐시 키가 만료되는 순간 수백 개의 요청이 동시에 DB를 조회하는 문제. **Mutex Lock 또는 Probabilistic Early Expiration** 기법으로 해결합니다.

**캐시 오염(Cache Pollution)**: 거의 쓰이지 않는 데이터가 캐시를 차지하는 문제. **LRU(Least Recently Used) 정책**으로 해결합니다.

---

## 9. CDN (Content Delivery Network)

### CDN이란?

원본 서버(서울)에서 모든 요청을 처리하면 미국 사용자는 150ms, 유럽 사용자는 200ms의 지연이 발생합니다. CDN은 전 세계에 엣지 서버를 두고 콘텐츠를 캐싱해 **지리적 지연을 10~30ms로 줄입니다**.

<div class="mermaid">
graph TD
    Origin["원본 서버\n서울 (Origin)"]
    subgraph "CDN 엣지 네트워크"
        CDN_NY["CDN 엣지\n뉴욕 (10ms)"]
        CDN_LA["CDN 엣지\nLA (8ms)"]
        CDN_London["CDN 엣지\n런던 (12ms)"]
        CDN_Tokyo["CDN 엣지\n도쿄 (15ms)"]
    end

    U_US["미국 사용자"] -->|"1️⃣ 요청"| CDN_NY
    U_UK["영국 사용자"] -->|"1️⃣ 요청"| CDN_London
    U_JP["일본 사용자"] -->|"1️⃣ 요청"| CDN_Tokyo

    CDN_NY -->|"2️⃣ 캐시 미스 시만"| Origin
    CDN_London -->|"2️⃣ 캐시 미스 시만"| Origin
    CDN_Tokyo -->|"2️⃣ 캐시 미스 시만"| Origin

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class U_US,U_UK,U_JP client
    class CDN_NY,CDN_LA,CDN_London,CDN_Tokyo server
    class Origin db
</div>

**CDN에 적합한 콘텐츠**: 정적 파일(이미지, CSS, JS, 폰트), 동영상 스트리밍, 다운로드 파일

**CDN에 부적합한 콘텐츠**: 사용자별 맞춤 데이터, 실시간 재고/가격 정보, API 응답(캐시 일관성 문제)

---

## 10. 메시지 큐 (Message Queue)

### 메시지 큐란?

식당에서 홀 직원이 주문을 받아 주방 주문통에 넣는 방식을 생각해 보세요. 주방이 아무리 바빠도 홀 직원은 주문을 계속 받을 수 있습니다. **생산자(Producer)와 소비자(Consumer)를 비동기로 분리**하는 것이 핵심입니다.

<div class="mermaid">
graph LR
    subgraph "생산자 계층"
        P1["1️⃣ 주문 서비스"]
        P2["1️⃣ 결제 서비스"]
        P3["1️⃣ 배송 서비스"]
    end
    subgraph "메시지 큐"
        MQ["2️⃣ Kafka / RabbitMQ\n메시지 버퍼"]
    end
    subgraph "소비자 계층"
        C1["3️⃣ 이메일 발송"]
        C2["3️⃣ 재고 업데이트"]
        C3["3️⃣ 통계 집계"]
    end

    P1 --> MQ
    P2 --> MQ
    P3 --> MQ
    MQ --> C1
    MQ --> C2
    MQ --> C3

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class P1,P2,P3 client
    class MQ server
    class C1,C2,C3 db
</div>

**메시지 큐 사용 이유:**

1. **비동기 처리**: 주문 완료 후 이메일 발송을 동기로 처리하면 이메일 서버 장애가 주문 실패로 이어집니다. 큐를 사용하면 주문은 즉시 완료되고 이메일은 나중에 처리됩니다.

2. **부하 완충(Load Leveling)**: 피크 타임에 초당 10만 건 요청이 와도 소비자가 처리 가능한 속도로 처리합니다. 큐가 버퍼 역할을 합니다.

3. **내결함성**: 소비자가 장애 나도 메시지는 큐에 보존됩니다. 복구 후 처리를 재개할 수 있습니다.

---

## 11. 마이크로서비스 아키텍처 기초

### 모놀리스 vs 마이크로서비스

<div class="mermaid">
graph TD
    subgraph "모놀리스 아키텍처"
        M["하나의 큰 JAR/WAR\n사용자 + 주문 + 결제 + 배송\n모두 한 프로세스"]
    end

    subgraph "마이크로서비스 아키텍처"
        US["사용자 서비스\nPort: 8081"]
        OS["주문 서비스\nPort: 8082"]
        PS["결제 서비스\nPort: 8083"]
        DS["배송 서비스\nPort: 8084"]
    end

    US -->|"HTTP/gRPC"| OS
    OS -->|"HTTP/gRPC"| PS
    PS -->|"이벤트 발행"| DS

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class M client
    class US,OS server
    class PS,DS db
</div>

| 특성 | 모놀리스 | 마이크로서비스 |
|------|---------|--------------|
| 배포 | 전체 재배포 (위험도 높음) | 개별 독립 배포 |
| 확장 | 전체 스케일 아웃 | 필요한 서비스만 확장 |
| 장애 범위 | 전체 서비스 영향 | 서비스 격리 (Circuit Breaker) |
| 복잡도 | 코드는 단순 | 분산 트랜잭션, 네트워크 장애 대응 |
| 초기 개발 속도 | 빠름 | 느림 (인프라 셋업) |
| 팀 규모 | 소규모 (5~15명) | 대규모 (서비스당 2 Pizza 팀) |

---

## 12. 통합 아키텍처 — 실제 대규모 시스템

<div class="mermaid">
graph TD
    User["1️⃣ 사용자"] --> DNS["DNS"]
    DNS --> CDN["CDN\n정적 파일 95% 처리"]
    DNS --> LB["2️⃣ 로드밸런서\nAWS ALB"]

    LB --> WS1["3️⃣ 웹 서버 1"]
    LB --> WS2["3️⃣ 웹 서버 2"]
    LB --> WS3["3️⃣ 웹 서버 N"]

    WS1 --> Cache["4️⃣ Redis 클러스터\n캐시 계층"]
    WS2 --> Cache
    WS3 --> Cache

    WS1 --> MQ["5️⃣ Kafka\n비동기 처리"]
    WS2 --> MQ
    WS3 --> MQ

    WS1 --> MasterDB[("6️⃣ 마스터 DB\n쓰기 전용")]
    MasterDB --> R1[("레플리카 1")]
    MasterDB --> R2[("레플리카 2")]
    WS1 --> R1

    MQ --> Worker1["7️⃣ 워커 서버 1"]
    MQ --> Worker2["7️⃣ 워커 서버 2"]
    Worker1 --> Storage["S3 오브젝트\n스토리지"]
    Worker2 --> Search["Elasticsearch\n검색 서버"]

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class User,DNS client
    class LB,WS1,WS2,WS3,Cache,MQ,Worker1,Worker2,CDN server
    class MasterDB,R1,R2,Storage,Search db
</div>

---

## 13. 시스템 설계 면접 4단계 프레임워크

<div class="mermaid">
graph TD
    Step1["1️⃣ 요구사항 명확화\n5분"] --> Step2["2️⃣ 규모 추정\n5분"]
    Step2 --> Step3["3️⃣ 고수준 설계\n20-25분"]
    Step3 --> Step4["4️⃣ 상세 설계 + 개선\n15분"]

    Step1 --> Q1["기능 요구사항: 무엇을 만드나?\n비기능: 얼마나 빠르게? 얼마나 크게?\n제약: 기술 스택 제한?"]
    Step2 --> Q2["DAU/MAU 추정\nQPS 계산\n저장소 용량 계산"]
    Step3 --> Q3["고수준 아키텍처 다이어그램\n핵심 컴포넌트\n데이터 흐름"]
    Step4 --> Q4["병목 구간 해결\n확장성 방안\n장애 처리 전략"]

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class Step1,Step2 client
    class Step3,Step4 server
    class Q1,Q2,Q3,Q4 db
</div>

### 규모 추정 공식

```
QPS = DAU × 일일 평균 요청 / 86,400초
피크 QPS = QPS × 3  (피크는 평균의 2~3배)

저장소 = DAU × 데이터 크기 × 365일 × 보관 연수
```

**실전 예시: 트위터 유사 시스템**
```
DAU: 1억명
트윗 비율: 10% (1000만명이 하루 1개)
읽기:쓰기 = 100:1

쓰기 QPS = 10,000,000 / 86,400 ≈ 115 QPS
읽기 QPS = 115 × 100 = 11,500 QPS
피크 QPS = 11,500 × 3 = 34,500 QPS

트윗 크기 = 300B (텍스트) + 이미지 링크
텍스트 일일 저장 = 10,000,000 × 300B ≈ 3GB/일
5년 저장 = 3GB × 365 × 5 ≈ 5.5TB (텍스트만)
미디어 포함 시: × 100배 = 550TB
```

---

## 14. 극한 시나리오: 넷플릭스 트래픽 — 인터넷의 15% 처리법

넷플릭스는 피크 시간에 인터넷 전체 트래픽의 15%를 차지합니다. 구체적으로 초당 수 TB의 데이터를 전 세계에 전달합니다. 어떻게 가능할까요?

<div class="mermaid">
graph TD
    User["1억 5천만 구독자\n동시 2000만 스트리밍"] --> OCA["1️⃣ 오픈 커넥트\n어플라이언스 (OCA)\nISP에 직접 설치\n15,000+ 서버"]

    OCA -->|"캐시 없는 콘텐츠"| AWS["2️⃣ AWS 백엔드\n멀티 리전"]

    subgraph "AWS 서비스들"
        Auth["인증 서비스\n수억건 세션"]
        Recommend["추천 엔진\nML 모델 1000개+"]
        Transcode["트랜스코딩\n4K/1080p/720p/480p"]
        Billing["결제 서비스"]
    end

    AWS --> Auth
    AWS --> Recommend
    AWS --> Transcode

    subgraph "데이터 계층"
        Cassandra[("Cassandra\n시청 기록\n수백 TB")]
        MySQL[("MySQL\n결제 정보")]
        ES[("Elasticsearch\n콘텐츠 검색")]
        S3[("S3\n원본 영상\nExabyte 단위")]
    end

    Auth --> MySQL
    Recommend --> Cassandra
    Transcode --> S3

    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef server fill:#e8f5e9,stroke:#388e3c
    classDef db fill:#fff3e0,stroke:#f57c00
    class User client
    class OCA,AWS,Auth,Recommend,Transcode,Billing server
    class Cassandra,MySQL,ES,S3 db
</div>

### 넷플릭스의 5가지 핵심 설계 결정

1. **오픈 커넥트(OCA) — CDN을 직접 만들다**: 상업 CDN 대신 ISP(통신사)에 직접 서버를 설치. 트래픽의 95%를 OCA에서 처리해 원본 서버 부하를 1/20로 줄였습니다.

2. **마이크로서비스 700개+**: 각 팀이 독립적으로 배포. 카탈로그 업데이트가 결제 시스템에 영향을 주지 않습니다.

3. **Chaos Engineering**: Chaos Monkey로 무작위 서버를 의도적으로 죽여 장애 내성 검증. "장애가 발생해도 괜찮은 시스템"이 목표입니다.

4. **멀티 AZ/리전**: AWS 3개 이상 가용 영역 동시 운영. 한 리전 전체 장애 시 자동으로 다른 리전으로 페일오버합니다.

5. **Circuit Breaker**: 추천 서비스가 느려져도 재생은 계속됩니다. 추천 대신 기본 콘텐츠를 보여주는 폴백(Fallback)이 동작합니다.

---

## 핵심 포인트 정리

| 개념 | 핵심 트레이드오프 | 언제 선택 | 주의사항 |
|------|-----------------|---------|---------|
| 수직 확장 | 단순 vs 한계 존재 | 초기, 빠른 성장 대응 | SPOF 위험 |
| 수평 확장 | 무한 확장 vs 복잡도 | 대규모 트래픽 | 상태 공유 문제 |
| 읽기 복제 | 읽기 성능 vs 복제 지연 | 읽기 80%+ | 마스터 읽기 케이스 명시 |
| 샤딩 | 수평 DB 확장 vs 조인 불가 | 수십 TB+ | 마지막 수단 |
| 캐시 | 속도 vs 일관성 | 읽기 많은 시스템 | TTL 설정, 캐시 스탬피드 |
| CDN | 지연 감소 vs 무효화 어려움 | 글로벌 서비스 | 동적 콘텐츠 부적합 |
| 메시지 큐 | 비동기 처리 vs 복잡도 | 느린 작업, 트래픽 급증 | 중복 처리 대비 |
| CAP | C vs A (장애 시) | 시스템 특성에 따라 | 실제론 CP vs AP |

> **시스템 디자인의 황금률**: 완벽한 시스템은 없습니다. 어떤 것을 얻으면 다른 것을 잃습니다. **현재 요구사항에 맞는 적절한 트레이드오프를 선택하고, 그 이유를 명확히 설명하는 것**이 최선입니다.
