---
title: "Kafka 데이터 복제 메커니즘"
categories:
- KAFKA
toc: true
toc_sticky: true
toc_label: 목차
---

브로커 한 대가 갑자기 죽었다. 그 브로커에만 있던 메시지는 영영 사라지는가? Kafka는 처음부터 이 상황을 가정하고 설계됐다. 파티션을 여러 브로커에 복제해두고, 리더가 죽으면 팔로워 중 하나가 즉시 리더를 이어받는다.

## 왜 이게 중요한가?

데이터 복제 메커니즘을 모르면 두 가지 위험에 빠진다. 첫째, `acks=1`로 설정한 채 운영하다 리더 장애 시 메시지가 유실된다. 둘째, ISR이 줄어든 상황에서 `min.insync.replicas` 조건을 모르고 쓰기를 계속하면 가용성과 내구성 중 하나를 무심코 포기하게 된다. 복제 원리를 이해하면 이 설정들이 왜 그렇게 동작하는지 자연스럽게 이해된다.

## 비유로 이해하기

> 복제는 중요한 계약서를 원본 외에 사본 2부를 만들어 각기 다른 금고에 보관하는 것과 같다. 원본이 든 금고가 불에 타도 사본으로 업무를 이어갈 수 있다. ISR은 "사본이 원본과 동일하게 최신 상태인 금고"만 목록에 올리는 품질 관리 장치다. 사본이 뒤처지면 ISR 목록에서 제외되고, 따라잡으면 다시 등재된다.

## 복제의 목적

Kafka는 단일 브로커 장애에도 데이터를 잃지 않기 위해 파티션을 여러 브로커에 복제한다. 복제는 가용성과 내구성을 동시에 보장하는 핵심 메커니즘이다.

```mermaid
graph LR
    PROD[Producer] -->|쓰기| L["Broker1 Leader"]
    L -->|복제| F1["Broker2 ISR"]
    L -->|복제| F2["Broker3 ISR"]
    CONS[Consumer] -->|읽기| L
```

Producer와 Consumer는 Leader와만 통신한다. Follower는 Leader로부터 데이터를 fetch하여 동기화한다.

---

## ISR (In-Sync Replicas)

### ISR이란?

Leader와 동기화 상태를 유지하는 Follower 집합이다. ISR에 포함된 브로커만이 Leader 승격 후보가 된다. ISR 목록이 곧 "믿을 수 있는 복제본 목록"이다.

```
ISR = {Leader, Follower1, Follower2}
  → Leader 장애 시 Follower1 또는 Follower2가 새 Leader로 승격

ISR = {Leader만 남음}  (Follower들이 뒤처진 경우)
  → Leader 장애 시 데이터 유실 위험
  → unclean.leader.election.enable 설정에 따라 동작이 달라짐
```

### ISR 판단 기준

```mermaid
sequenceDiagram
    ISR_포함->>ISR_제외: lag.time.max.ms 초과
    ISR_제외->>ISR_포함: Leader 로그 따라잡음
```

`replica.lag.time.max.ms` (기본값: 30000ms = 30초) 이내에 Follower가 Leader의 메시지를 fetch해야 ISR을 유지한다.

### ISR 확인 방법

```bash
# 파티션 상태 확인
kafka-topics.sh --bootstrap-server kafka:9092 \
  --describe --topic orders

# 출력 예시:
Topic: orders  Partition: 0  Leader: 1  Replicas: 1,2,3  Isr: 1,2,3
Topic: orders  Partition: 1  Leader: 2  Replicas: 2,3,1  Isr: 2,3
# Partition 1의 Broker 1이 ISR에서 빠진 상태
```

---

## High Watermark (HW)

### High Watermark란?

모든 ISR 브로커에 복제 완료된 메시지의 최대 오프셋이다. Consumer는 HW 이하의 메시지만 읽을 수 있다. 아직 일부 Follower에만 복제된 메시지는 Consumer에게 노출되지 않는다.

```mermaid
graph LR
    L["Leader LEO: 5"] --> HW["HW = 3"]
    F1["Follower1 LEO: 4"] --> HW
    F2["Follower2 LEO: 3"] --> HW
    style HW fill:#e67e22,color:#fff
```

### HW와 데이터 유실 방지

HW 덕분에 Leader가 갑자기 장애 나도 Consumer에게 이미 노출된 메시지는 반드시 다른 ISR에도 존재한다.

```
상황: Consumer가 offset 2까지 읽은 후 Leader(offset 4 기록) 장애

새 Leader로 Follower1 승격 (LEO: 3)
  → Consumer는 offset 2까지만 읽었으므로 문제없음
  → offset 3은 Follower1에 있으므로 다음 읽기 가능
  → offset 4는 유실 (HW=3이었으므로 Consumer에게 노출 안 됨)
```

---

## Leader Epoch

### Leader Epoch가 필요한 이유

Kafka 0.11 이전에는 HW만으로 복제 일관성을 보장했는데, 특정 장애 시나리오에서 데이터 불일치가 발생할 수 있었다.

```mermaid
sequenceDiagram
    Leader_A->>Follower_B: 장애→B 승격
    Leader_A->>Leader_A: 재시작→truncate
    Follower_B->>Leader_A: 장애→A 재승격
    Leader_A->>Leader_A: offset 1 유실!
```

### Leader Epoch 동작

각 Leader 선출마다 단조 증가하는 Epoch 번호를 부여한다. Follower는 HW가 아닌 Leader Epoch를 기준으로 로그 일관성을 확인하므로 위 시나리오의 데이터 유실을 방지한다.

```
Leader Epoch 0: Broker 1이 Leader (offset 0~5)
Leader Epoch 1: Broker 2가 새 Leader (offset 6~10)
Leader Epoch 2: Broker 1이 다시 Leader (offset 11~)

Broker 1이 재시작 시:
  "나의 마지막 Epoch는 0, offset 5였다"
  → 현재 Leader(Broker 2, Epoch 1)에게 질의
  → "Epoch 0은 offset 5까지" 확인
  → offset 5 이후를 안전하게 truncate
```

---

## 복제 팩터 설정

### 복제 팩터 선택 가이드

```mermaid
graph LR
    ENV{"환경"}
    DEV["팩터 1(개발)"]
    PROD["팩터 3(권장)"]
    CRITICAL["팩터 4+(금융)"]
    ENV -->|"개발"| DEV
    ENV -->|"프로덕션"| PROD
    ENV -->|"금융/의료"| CRITICAL
    style DEV fill:#e74c3c,color:#fff
    style PROD fill:#2ecc71,color:#fff
    style CRITICAL fill:#3498db,color:#fff
```

### 토픽 생성 시 복제 팩터 지정

```bash
kafka-topics.sh --bootstrap-server kafka:9092 \
  --create \
  --topic payments \
  --partitions 6 \
  --replication-factor 3

# min.insync.replicas 설정 (토픽 레벨)
kafka-configs.sh --bootstrap-server kafka:9092 \
  --entity-type topics \
  --entity-name payments \
  --alter \
  --add-config min.insync.replicas=2
```

---

## acks 설정

Producer의 `acks` 설정은 얼마나 많은 브로커의 확인을 기다릴지 결정한다. 이 설정이 내구성과 지연의 균형을 결정하는 핵심이다.

```mermaid
graph LR
    Z["acks=0: 확인 없음"]
    O["acks=1: Leader만 확인"]
    A["acks=all: ISR 전체 확인"]
    style Z fill:#e74c3c,color:#fff
    style A fill:#2ecc71,color:#fff
```

### min.insync.replicas와 조합

`acks=all`만으로는 충분하지 않다. ISR이 Leader 하나만 남은 경우에도 `acks=all`이 성공할 수 있기 때문이다. `min.insync.replicas`로 최소 복제 브로커 수를 강제한다.

```
acks=all + min.insync.replicas=2 (권장 프로덕션 설정)

의미: ISR 중 최소 2개 브로커에 복제 완료 후 ack
     ISR이 2개 미만이면 Producer에 NotEnoughReplicasException 반환

시나리오별 동작:
ISR = {Leader, F1, F2}: 정상, 복제 후 ack
ISR = {Leader, F1}:     min.insync=2이므로 정상
ISR = {Leader}:         min.insync=2 미충족 → 쓰기 거부
```

---

## Unclean Leader Election

### 개념

ISR에 포함되지 않은 Follower(Out-of-Sync)를 Leader로 선출하는 것이다. ISR이 모두 죽고 Out-of-Sync Follower만 살아있을 때 가용성과 내구성 중 하나를 선택해야 한다.

```mermaid
flowchart LR
    CRISIS["ISR = Leader만 남음"]
    F1["false: 리더 없이 대기"]
    F2["true: Out-of-Sync 선출"]
    CRISIS --> F1
    CRISIS --> F2
    style F1 fill:#3498db,color:#fff
    style F2 fill:#e74c3c,color:#fff
```

### 선택 기준

| 시스템 특성 | 권장 설정 |
|-------------|-----------|
| 금융, 주문, 결제 | `false` (데이터 유실 절대 불가) |
| 로그 집계, 메트릭 | `true` (가용성 우선) |
| 일반 서비스 이벤트 | `false` (기본값 유지) |

---

## 데이터 유실 시나리오와 방어

### 시나리오 1: acks=1 + Leader 장애

```
1. Producer가 offset 5를 Leader에 전송
2. Leader가 ack 반환 (Follower 복제 전)
3. Leader 장애, Follower가 Leader 승격 (Follower LEO: 4)
4. offset 5 유실 → Producer는 성공으로 알고 있음

방어: acks=all + min.insync.replicas=2
```

### 시나리오 2: 브로커 재시작 + 로그 손상

```
1. 브로커 비정상 종료 (kill -9)
2. 페이지 캐시에 있던 데이터 미플러시
3. 재시작 후 로그 일부 손상 또는 유실

방어: replication.factor=3으로 다른 브로커에서 복구
      (flush 설정은 성능 트레이드오프가 크므로 복제로 대체 권장)
```

### 시나리오 3: 네트워크 파티션 (Split Brain)

```
1. 네트워크 파티션으로 Broker1(Leader)이 Broker2,3과 단절
2. Broker2가 새 Leader로 선출
3. Broker1은 자신이 Leader라고 생각하고 메시지 계속 수신
4. "Split Brain" 상태

방어: ZooKeeper/KRaft의 epoch 기반 Leader 검증
      Broker1은 epoch 불일치로 Leader 권한 상실
      이후 Broker1이 클러스터에 재합류 시 불일치 로그 truncate
```

### 방어 설정 체크리스트

```properties
# Producer
acks=all
retries=2147483647
enable.idempotence=true
max.in.flight.requests.per.connection=5

# Broker
default.replication.factor=3
min.insync.replicas=2
unclean.leader.election.enable=false

# Topic (중요 토픽)
replication.factor=3
min.insync.replicas=2
```

---

## 복제 성능 튜닝

### Follower fetch 설정

```properties
# Broker 설정 (Follower의 fetch 동작)
num.replica.fetchers=4          # 병렬 fetch 스레드 수 (기본 1, 증가 권장)
replica.fetch.min.bytes=1       # 최소 fetch 바이트
replica.fetch.max.bytes=10485760 # 최대 fetch 바이트 (10MB)
replica.fetch.wait.max.ms=500   # fetch 대기 최대 시간
```

`num.replica.fetchers`를 1에서 4로 늘리면 복제 처리량이 크게 향상된다.

### 복제 지연 모니터링

```bash
# 복제 지연 파티션만 출력
kafka-topics.sh --bootstrap-server kafka:9092 \
  --describe --topic orders \
  --under-replicated-partitions

# Leader 없는 파티션 출력
kafka-topics.sh --bootstrap-server kafka:9092 \
  --describe --topic orders \
  --unavailable-partitions
```

`UnderReplicatedPartitions` 지표가 0보다 크면 즉시 원인을 파악해야 한다. 네트워크 문제, 브로커 과부하, 디스크 I/O 포화가 주요 원인이다.

---


## 극한 시나리오

### 시나리오: ISR 축소 중 min.insync.replicas 위반

네트워크 지연이나 브로커 과부하로 Follower들이 ISR에서 탈락하면 쓰기가 거부된다. 이때 `min.insync.replicas`를 임시로 낮추거나 `unclean.leader.election`을 허용하는 결정이 필요하다.

```mermaid
flowchart LR
    A["ISR 탈락"]
    B["min.insync 미충족"]
    C["쓰기 거부"]
    D{"가용성 vs 내구성"}
    E["min.insync 감소"]
    F["브로커 복구 대기"]
    A --> B --> C --> D
    D -->|"가용성"| E
    D -->|"내구성"| F
    style C fill:#e74c3c,color:#fff
    style E fill:#e67e22,color:#fff
    style F fill:#2ecc71,color:#fff
```

금융/결제 시스템은 반드시 내구성을 우선해야 한다. 일시적 장애 허용보다 데이터 정확성이 더 중요하다.

---

## acks=all이면 안전하다는 착각

`acks=all`을 설정했다고 메시지 유실이 없다고 믿으면 안 된다. 이 설정은 생각보다 훨씬 쉽게 무력화된다.

**함정 1: min.insync.replicas=1이면 acks=all이 의미 없다**

```properties
# 이 조합은 사실상 acks=1과 동일하다
acks=all
min.insync.replicas=1   # ISR에 리더 하나만 있어도 쓰기 성공
```

리더 하나만 확인하면 되므로, 리더가 죽는 순간 아직 팔로워에 복제되지 않은 메시지는 유실된다. 브로커 로그에 성공으로 찍혔어도 데이터는 사라진다.

**함정 2: unclean.leader.election.enable=true면 복제 설정이 모두 무력화된다**

```bash
# 이 설정이 true이면
unclean.leader.election.enable=true

# 시나리오:
# 1. ISR = {Leader, F1, F2}
# 2. F1, F2가 과부하로 ISR에서 탈락
# 3. Leader 장애 발생
# 4. ISR 비어 있음 → Out-of-Sync인 F1이 리더로 선출됨
# 5. F1이 놓친 메시지는 영구 유실
# → acks=all + min.insync.replicas=2가 아무 의미 없었음
```

**함정 3: 네트워크 분할(Split Brain) 상황**

```
브로커1(리더)이 브로커2,3과 일시적으로 단절됨
→ 브로커2가 새 리더로 선출됨
→ 브로커1은 자신이 아직 리더라고 생각하고 프로듀서 요청을 받음
→ acks=all을 리턴했지만 해당 메시지는 브로커1에만 존재
→ 브로커1이 재합류하면 epoch 불일치로 이 메시지들이 truncate됨 → 유실
```

**최종 방어선: 설정 세 개가 모두 맞아야 한다**

```properties
# 프로듀서
acks=all
retries=2147483647
enable.idempotence=true

# 브로커 (이 두 줄이 핵심)
min.insync.replicas=2              # acks=all의 실질적 보장
unclean.leader.election.enable=false   # 데이터 있는 리더만 선출

# 컨슈머 측 방어
# 중복 처리 가능성은 항상 존재 → 멱등성 처리 필수
```

`acks=all`은 필요조건이지 충분조건이 아니다. `min.insync.replicas`와 `unclean` 설정을 함께 검토하지 않으면 운영 중 데이터가 사라진 뒤에야 이 사실을 알게 된다.

---

## 왜 Kafka 복제를 알아야 하는가?

`replication.factor`, `min.insync.replicas`, `acks`의 조합이 내구성과 가용성의 균형을 결정한다. 이 세 가지를 잘못 설정하면 브로커 한 대 장애에도 쓰기가 전부 차단되거나, 반대로 데이터가 유실된다. 복제 내부를 이해하면 ISR 축소 알림이 왔을 때 올바른 판단을 내릴 수 있다.

---

## 실무에서 자주 하는 실수

**실수 1: replication.factor=1로 운영 토픽 생성**
브로커 1대 장애 시 해당 파티션이 영구적으로 unavailable 상태가 된다. 운영 토픽은 최소 `replication.factor=3`으로 생성하고, 클러스터 수준 기본값(`default.replication.factor=3`)을 설정해야 한다.

**실수 2: min.insync.replicas=1로 내구성 보장 무효화**
`acks=all`로 설정해도 `min.insync.replicas=1`이면 리더만 확인하면 된다. 레플리카 없이도 쓰기가 성공해 실질적으로 `acks=1`과 동일하다. `min.insync.replicas=2`(replication.factor=3 환경)가 실무 표준이다.

**실수 3: ISR 축소 알림을 무시**
`UnderReplicatedPartitions` 메트릭이 0보다 크면 일부 레플리카가 ISR에서 제외된 것이다. 이 상태에서 리더 장애가 발생하면 데이터 유실 위험이 높다. ISR 축소를 즉시 알림으로 받고 원인(브로커 과부하, 네트워크 지연)을 파악해야 한다.

**실수 4: 레플리카 페치 설정 미튜닝으로 복제 지연**
`replica.fetch.max.bytes`, `num.replica.fetchers`가 기본값이면 대용량 트래픽에서 레플리카가 리더를 따라가지 못한다. ISR에서 반복적으로 제외됐다 복귀하는 패턴이 나타난다. `num.replica.fetchers`를 늘리고 `replica.fetch.max.bytes`를 조정한다.

**실수 5: Preferred Leader 복구를 자동화하지 않음**
브로커 재시작 후 파티션 리더가 원래 브로커(preferred leader)로 돌아오지 않아 특정 브로커에 리더가 집중된다. `auto.leader.rebalance.enable=true`(기본)로 설정하거나 `kafka-leader-election.sh --election-type PREFERRED`를 주기적으로 실행해야 한다.

---

## 면접 포인트

**Q1. replication.factor, min.insync.replicas, acks의 관계는?**
`replication.factor`는 복사본 수. `min.insync.replicas`는 `acks=all` 시 최소 확인 레플리카 수. `acks`는 프로듀서가 기다리는 확인 수준. 권장 조합: `replication.factor=3`, `min.insync.replicas=2`, `acks=all` — 브로커 1대 장애에도 쓰기 가능하고 데이터 유실 없음.

**Q2. ISR에서 레플리카가 제외되는 조건은?**
`replica.lag.time.max.ms`(기본 30초) 동안 리더의 LEO를 따라잡지 못하면 ISR에서 제외된다. 원인: ① 레플리카 브로커 과부하 ② 네트워크 지연 ③ GC pause. 제외된 레플리카가 다시 따라잡으면 자동으로 ISR에 복귀한다.

**Q3. Unclean Leader Election이란?**
ISR에 없는 레플리카(out-of-sync)가 리더로 선출되는 것이다. 서비스 가용성은 회복되지만 그 레플리카가 놓친 메시지는 영구 유실된다. `unclean.leader.election.enable=false`(기본)로 데이터 유실을 방지하되, 서비스 중단을 감수한다. 금융 시스템은 반드시 false를 유지해야 한다.

**Q4. Follower 레플리카가 리더로부터 데이터를 가져오는 방식은?**
Follower가 리더에게 Fetch Request를 보내 LEO 이후의 메시지를 가져온다(Pull 방식). 리더는 Follower의 Fetch offset을 추적해 ISR 포함 여부를 판단한다. `num.replica.fetchers` 스레드가 병렬로 여러 파티션을 페치한다.

**Q5. 복제 지연(Replica Lag)을 모니터링하는 방법은?**
`kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions` JMX 메트릭이 0보다 크면 복제 지연 파티션이 있다. `kafka-topics.sh --describe`로 파티션별 ISR 상태 확인. Prometheus kafka_exporter의 `kafka_topic_partition_under_replicated_partition` 메트릭으로 알림 설정.
