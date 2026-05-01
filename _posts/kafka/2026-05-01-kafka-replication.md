---
title: "Kafka 데이터 복제 메커니즘"
categories:
- KAFKA
toc: true
toc_sticky: true
toc_label: 목차
---

브로커 한 대가 갑자기 죽었다. 그 브로커에만 있던 메시지는 영영 사라지는가? Kafka는 처음부터 이 상황을 가정하고 설계됐다. 파티션을 여러 브로커에 복제해두고, 리더가 죽으면 팔로워 중 하나가 즉시 리더를 이어받는다.

> **비유**: 복제는 중요한 계약서를 원본 외에 사본 2부를 만들어 각기 다른 금고에 보관하는 것과 같다. 원본이 든 금고가 불에 타도 사본으로 업무를 이어갈 수 있다. ISR은 "사본이 원본과 동일하게 최신 상태인 금고"만 목록에 올리는 품질 관리 장치다.

## 복제의 목적

Kafka는 단일 브로커 장애에도 데이터를 잃지 않기 위해 파티션을 여러 브로커에 복제한다. 복제는 가용성과 내구성을 동시에 보장하는 핵심 메커니즘이다.

```
복제 팩터 3, 파티션 1개인 경우:

Broker 1 (Leader)     Broker 2 (Follower)     Broker 3 (Follower)
┌──────────────┐      ┌──────────────┐        ┌──────────────┐
│ Partition 0  │      │ Partition 0  │        │ Partition 0  │
│ msg0         │ ───→ │ msg0         │        │ msg0         │
│ msg1         │ ───→ │ msg1         │   ───→ │ msg1         │
│ msg2         │      │              │        │              │
│ (Leader)     │      │ (ISR)        │        │ (ISR)        │
└──────────────┘      └──────────────┘        └──────────────┘
   ↑ Producer/Consumer 요청 처리
```

---

## ISR (In-Sync Replicas)

### ISR이란?

Leader와 동기화 상태를 유지하는 Follower 집합이다. ISR에 포함된 브로커만이 Leader 승격 후보가 된다.

```
ISR = {Leader, Follower1, Follower2}
  → Leader 장애 시 Follower1 또는 Follower2가 새 Leader로 승격

ISR = {Leader}  (Follower들이 뒤처진 경우)
  → Leader 장애 시 데이터 유실 위험 (unclean leader election 설정에 따라 다름)
```

### ISR 판단 기준

Follower가 ISR에 포함되려면 다음 조건을 만족해야 한다.

```
replica.lag.time.max.ms (기본값: 30000ms = 30초)
  → Follower가 이 시간 이내에 Leader의 메시지를 fetch해야 ISR 유지
  → 30초 동안 fetch 요청이 없거나 너무 뒤처지면 ISR에서 제거
```

```
상태 변화:
Follower가 fetch 지연 → ISR 제거 (Out-of-Sync)
     ↓
Leader의 로그를 따라잡음 → ISR 재진입
```

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

모든 ISR 브로커에 복제 완료된 메시지의 최대 오프셋이다. Consumer는 HW 이하의 메시지만 읽을 수 있다.

```
Leader의 Log End Offset (LEO): 5
Follower1 LEO: 4
Follower2 LEO: 3

High Watermark = min(모든 ISR의 LEO) = 3

Consumer가 읽을 수 있는 최대 오프셋: 2 (offset 0~2까지)
```

```
              HW=3         LEO=5
               ↓             ↓
Leader:  [0][1][2][3][4]
Follower1:[0][1][2][3]
Follower2:[0][1][2]

Consumer는 offset 2까지만 읽기 가능
(모든 ISR에 복제된 메시지만 노출)
```

### HW와 데이터 유실 방지

HW 덕분에 Leader가 갑자기 장애 나도 Consumer에게 노출된 메시지는 반드시 다른 ISR에도 존재한다.

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

```
문제 시나리오 (Leader Epoch 이전):
1. Leader(A): offset 0,1 기록. Follower(B): offset 0만 복제
2. HW = 0
3. Follower(B)가 offset 1을 fetch하기 전에 Leader(A) 장애
4. Follower(B)가 새 Leader가 됨
5. 구 Leader(A) 재시작 → B에서 HW=0 수신
6. A가 자신의 offset 1을 HW 기준으로 잘라냄 (truncate)
7. B가 A보다 먼저 장애 → A가 다시 Leader
8. offset 1이 사라진 상태로 운영 → 데이터 유실
```

### Leader Epoch 동작

각 Leader 선출마다 단조 증가하는 Epoch 번호를 부여한다. Follower는 HW가 아닌 Leader Epoch를 기준으로 로그 일관성을 확인한다.

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

```
복제 팩터 1:
  - 복제 없음, 단일 브로커 장애 시 데이터 유실
  - 개발/테스트 환경에만 사용

복제 팩터 2:
  - 브로커 1개 장애 허용
  - 운영 환경에 권장하지 않음 (동시 장애 시 위험)

복제 팩터 3 (권장):
  - 브로커 2개 동시 장애까지 허용
  - 대부분의 프로덕션 환경 기본값

복제 팩터 ≥ 4:
  - 금융/의료 등 고가용성 요구 환경
  - 저장 비용 증가
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

Producer의 `acks` 설정은 얼마나 많은 브로커의 확인을 기다릴지 결정한다.

### acks=0

```
Producer → Leader (확인 기다리지 않음)

장점: 최고 처리량, 최소 지연
단점: 데이터 유실 가능 (Leader가 받기 전 장애)
용도: 로그 집계, 메트릭 등 유실 허용 가능한 경우
```

### acks=1 (기본값)

```
Producer → Leader → (Leader만 확인) → ack 반환

장점: 빠른 응답, 적당한 내구성
단점: Leader가 Follower 복제 전 장애 시 유실
용도: 일반적인 메시징, 처리량 중요한 경우
```

### acks=all (-1과 동일)

```
Producer → Leader → ISR 전체 복제 완료 → ack 반환

장점: 데이터 유실 없음
단점: 지연 증가 (ISR 내 가장 느린 브로커 속도에 좌우됨)
용도: 금융 트랜잭션, 결제, 주문 등 중요 데이터
```

### min.insync.replicas와 조합

```
acks=all + min.insync.replicas=2 (권장 프로덕션 설정)

의미: ISR 중 최소 2개 브로커에 복제 완료 후 ack
     ISR이 2개 미만이면 Producer에 NotEnoughReplicasException 반환

broker.config:
  default.replication.factor=3
  min.insync.replicas=2

producer.config:
  acks=all
  retries=Integer.MAX_VALUE
  enable.idempotence=true
```

```
시나리오별 동작:
ISR = {Leader, F1, F2}: 정상, 복제 후 ack
ISR = {Leader, F1}:     min.insync=2이므로 정상
ISR = {Leader}:         min.insync=2 미충족 → 쓰기 거부
```

---

## Unclean Leader Election

### 개념

ISR에 포함되지 않은 Follower(Out-of-Sync)를 Leader로 선출하는 것이다.

```
상황: ISR = {Leader만 남음}, Leader 장애
      Out-of-Sync Follower만 살아있음

unclean.leader.election.enable=false (기본값):
  → 리더 없는 상태(unavailable)로 대기
  → ISR 브로커가 복구될 때까지 쓰기/읽기 불가
  → 데이터 유실 없음, 가용성 감소

unclean.leader.election.enable=true:
  → Out-of-Sync Follower를 Leader로 선출
  → 즉시 가용성 회복
  → 복제 안 된 메시지는 영구 유실
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

방어: flush.messages, flush.ms 설정 (성능 트레이드오프)
      또는 replication.factor=3으로 다른 브로커에서 복구
```

### 시나리오 3: 네트워크 파티션

```
1. 네트워크 파티션으로 Broker1(Leader)이 Broker2,3과 단절
2. Broker2가 새 Leader로 선출
3. Broker1은 자신이 Leader라고 생각하고 메시지 계속 수신
4. "Split Brain" 상태

방어: ZooKeeper/KRaft의 epoch 기반 Leader 검증
      Broker1은 epoch 불일치로 Leader 권한 상실
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
log.flush.interval.messages=10000    # 선택적
log.flush.interval.ms=1000          # 선택적

# Topic (중요 토픽)
replication.factor=3
min.insync.replicas=2
```

---

## 복제 성능 튜닝

### Follower fetch 설정

```properties
# Broker 설정 (Follower의 fetch 동작)
num.replica.fetchers=4          # 병렬 fetch 스레드 수 (기본 1)
replica.fetch.min.bytes=1       # 최소 fetch 바이트
replica.fetch.max.bytes=10MB    # 최대 fetch 바이트
replica.fetch.wait.max.ms=500   # fetch 대기 최대 시간
```

### 복제 지연 모니터링

```bash
# Kafka 내장 메트릭
kafka.server:type=ReplicaFetcherManager,name=MaxLag,clientId=Replica

# JMX를 통한 모니터링 (Prometheus JMX Exporter)
kafka_server_replicafetchermanager_maxlag  # ISR lag 최대값

# 파티션별 복제 상태 확인
kafka-topics.sh --bootstrap-server kafka:9092 \
  --describe --topic orders \
  --under-replicated-partitions  # 복제 지연 파티션만 출력

kafka-topics.sh --bootstrap-server kafka:9092 \
  --describe --topic orders \
  --unavailable-partitions       # Leader 없는 파티션 출력
```
