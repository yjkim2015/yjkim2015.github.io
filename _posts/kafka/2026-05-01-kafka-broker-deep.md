---
title: "Kafka Broker"
categories:
- KAFKA
toc: true
toc_sticky: true
toc_label: 목차
---

## 브로커 아키텍처

### 브로커란?

Kafka 클러스터를 구성하는 개별 서버 노드다. 각 브로커는 파티션 데이터 저장, 클라이언트 요청 처리, 복제 참여를 담당한다.

```
Kafka Cluster
┌────────────────────────────────────────────────────────┐
│                                                        │
│  Broker 1 (id:1)    Broker 2 (id:2)    Broker 3 (id:3)│
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ orders-P0   │    │ orders-P1   │    │ orders-P2   │ │
│  │ (Leader)    │    │ (Leader)    │    │ (Leader)    │ │
│  │ orders-P1   │    │ orders-P2   │    │ orders-P0   │ │
│  │ (Follower)  │    │ (Follower)  │    │ (Follower)  │ │
│  │ orders-P2   │    │ orders-P0   │    │ orders-P1   │ │
│  │ (Follower)  │    │ (Follower)  │    │ (Follower)  │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│                                                        │
│              Controller: Broker 1                      │
└────────────────────────────────────────────────────────┘
                         │
              ZooKeeper / KRaft 클러스터
```

### 브로커 내부 컴포넌트

```
┌─────────────────────────────────────────────────────┐
│                    Kafka Broker                      │
│                                                      │
│  ┌──────────────┐   ┌──────────────┐                │
│  │ Network Layer│   │  API Layer   │                │
│  │ (Acceptor,   │ → │  (KafkaApis) │                │
│  │  Processor)  │   └──────────────┘                │
│  └──────────────┘          │                        │
│                            ▼                        │
│  ┌──────────────────────────────────────────────┐   │
│  │            Request Handler Pool              │   │
│  │        (num.io.threads 스레드 풀)             │   │
│  └──────────────────────────────────────────────┘   │
│                            │                        │
│          ┌─────────────────┼──────────────────┐     │
│          ▼                 ▼                  ▼     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │
│  │ ReplicaManager│  │ GroupCoord. │  │ LogManager│  │
│  │ (복제 관리)   │  │ (Consumer   │  │(파티션 로그│  │
│  │              │  │  그룹 관리)  │  │ 파일 관리) │  │
│  └──────────────┘  └──────────────┘  └──────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 로그 세그먼트

### 파티션 저장 구조

각 파티션은 디스크에 여러 세그먼트 파일로 저장된다.

```
/kafka-logs/orders-0/          (orders 토픽, 파티션 0)
├── 00000000000000000000.log   (세그먼트 파일: 메시지 본문)
├── 00000000000000000000.index (오프셋 → 파일 위치 인덱스)
├── 00000000000000000000.timeindex (타임스탬프 → 오프셋 인덱스)
├── 00000000000001048576.log   (다음 세그먼트: offset 1048576부터)
├── 00000000000001048576.index
├── 00000000000001048576.timeindex
└── leader-epoch-checkpoint
```

파일명의 숫자는 해당 세그먼트의 **시작 오프셋**이다.

### 세그먼트 전환 (Rolling)

```
새 세그먼트가 생성되는 조건:
log.segment.bytes=1073741824   # 1GB 초과 시 새 세그먼트
log.roll.hours=168             # 7일 경과 시 새 세그먼트
log.roll.jitter.hours=0        # 세그먼트 전환 시간 분산 (0이면 동시 전환)
```

### 메시지 조회 방식

```
Consumer가 offset 150000 요청:

1. 바이너리 서치로 세그먼트 파일 특정:
   00000000000000000000.log → offset 0~149999
   00000000000000150000.log → offset 150000~ (이 파일)

2. .index 파일에서 offset → 파일 내 byte 위치 조회 (희소 인덱스)
   offset 150000 → file position: 8192

3. .log 파일의 8192 위치부터 읽기 (Sequential I/O)
```

### 인덱스 구조 (희소 인덱스)

```
인덱스는 모든 메시지에 대해 생성되지 않음:

log.index.interval.bytes=4096  # 4KB마다 인덱스 항목 생성

인덱스 파일:
offset=0       → file_pos=0
offset=50      → file_pos=4096
offset=103     → file_pos=8192
...

조회: 이진 탐색으로 가장 가까운 인덱스 항목 찾은 후
      로그 파일에서 순차 스캔으로 정확한 offset 찾기
```

### 데이터 보존 정책

```properties
# 시간 기반
log.retention.hours=168          # 7일 보존 (기본값)
log.retention.ms=604800000       # ms 단위 (우선순위 높음)

# 크기 기반
log.retention.bytes=1073741824   # 파티션당 최대 1GB

# 정리 방식
log.cleanup.policy=delete        # 만료 세그먼트 삭제 (기본)
log.cleanup.policy=compact       # 키별 마지막 값만 유지
log.cleanup.policy=delete,compact # 두 가지 병행

# 삭제되지 않는 최소 보존 시간 (compact 사용 시)
log.retention.minutes=1440       # 최소 1일 보존 후 compaction
```

---

## 파티션 리더 선출

### 정상적인 리더 선출

```
토픽 생성 시 리더 분산 배치:
Broker1, Broker2, Broker3 각각 균등하게 리더 할당

파티션 0: Leader=Broker1, ISR=[1,2,3]
파티션 1: Leader=Broker2, ISR=[2,3,1]
파티션 2: Leader=Broker3, ISR=[3,1,2]
```

### 리더 장애 시 선출 과정

**ZooKeeper 기반 (기존):**

```
1. Broker2(Leader)가 ZooKeeper 세션 만료 (장애)
2. Controller(Broker1)가 ZooKeeper 이벤트로 감지
3. Controller가 ISR 목록에서 새 리더 선정
   ISR=[2,3,1] → Broker2 제외 → Broker3 선정
4. Controller가 ZooKeeper에 새 리더 정보 업데이트
5. Controller가 모든 브로커에게 LeaderAndIsr 요청 전송
6. Broker3이 리더 역할 시작
7. 브로커들이 Metadata 캐시 갱신
8. Producer/Consumer가 새 리더로 재연결
```

**KRaft 기반 (Kafka 3.x+):**

```
1. Broker2(Leader)가 Raft heartbeat 중단 (장애)
2. KRaft Controller 쿼럼이 감지 (ZooKeeper 불필요)
3. Active Controller가 새 리더 결정
4. 변경사항을 Raft 로그에 기록 (과반수 동의)
5. Broker들에게 새 리더 정보 브로드캐스트
6. 선출 완료 (ZooKeeper 대비 수십 ms 빠름)
```

### Preferred Leader 선출

각 파티션에는 최초 지정된 Preferred Leader가 있다. 장애 후 복구 시 Preferred Leader로 다시 리더를 이전한다.

```bash
# Preferred Leader 선출 트리거
kafka-leader-election.sh --bootstrap-server kafka:9092 \
  --election-type PREFERRED \
  --all-topic-partitions

# 설정으로 자동화
auto.leader.rebalance.enable=true           # 자동 Preferred Leader 복귀 (기본 true)
leader.imbalance.check.interval.seconds=300  # 5분마다 체크
leader.imbalance.per.broker.percentage=10    # 10% 이상 불균형 시 재조정
```

---

## Controller

### Controller의 역할

클러스터 내 단 하나의 브로커가 Controller 역할을 담당한다. 클러스터 관리의 핵심 두뇌다.

```
Controller 담당 업무:
1. 브로커 장애 감지 및 리더 재선출
2. 토픽/파티션 생성/삭제 처리
3. ISR 변경 사항 관리
4. 파티션 재할당 조정
5. 클러스터 Metadata 관리
```

### Controller 선출

**ZooKeeper 기반:**

```
모든 브로커가 ZooKeeper의 /controller 경로에 임시 노드(ephemeral node) 생성 경쟁
→ 먼저 생성한 브로커가 Controller

Controller 장애 시:
  ZooKeeper가 ephemeral node 삭제
  → 다른 브로커들이 /controller 노드 생성 경쟁
  → 새 Controller 선출
```

**KRaft (Kafka Raft Metadata mode):**

```
별도 KRaft Controller 노드 또는 브로커와 통합 모드로 실행
Raft 합의 알고리즘으로 Controller 선출 및 Metadata 관리
ZooKeeper 의존성 완전 제거

controller.quorum.voters=1@kafka1:9093,2@kafka2:9093,3@kafka3:9093
process.roles=broker,controller  # 브로커+컨트롤러 통합 모드
```

---

## KRaft

### ZooKeeper vs KRaft

| 구분 | ZooKeeper 기반 | KRaft |
|------|---------------|-------|
| **Metadata 저장** | ZooKeeper 외부 시스템 | Kafka 내부 Raft 로그 |
| **Controller 선출** | ZooKeeper ephemeral node | Raft 합의 |
| **확장성** | 파티션 수 수만 개 한계 | 수백만 파티션 지원 |
| **운영 복잡도** | ZooKeeper 별도 관리 | 단일 시스템 관리 |
| **장애 복구** | 수십 초 | 수 초 |
| **Kafka 버전** | 3.x까지 지원, 4.0에서 제거 | 2.8+ 지원, 3.3+에서 프로덕션 |

### KRaft 설정

```properties
# KRaft 모드 server.properties
process.roles=broker,controller          # broker 또는 controller 또는 둘 다
node.id=1
controller.quorum.voters=1@kafka1:9093,2@kafka2:9093,3@kafka3:9093
listeners=PLAINTEXT://kafka1:9092,CONTROLLER://kafka1:9093
inter.broker.listener.name=PLAINTEXT
controller.listener.names=CONTROLLER

# Cluster ID 생성 (최초 1회)
kafka-storage.sh random-uuid

# 스토리지 초기화
kafka-storage.sh format \
  --config /etc/kafka/server.properties \
  --cluster-id <UUID>
```

---

## 브로커 장애 시 동작

### 장애 감지

```
ZooKeeper 기반:
  - 브로커가 ZooKeeper에 heartbeat 전송 (zookeeper.session.timeout.ms)
  - 기본 18초 내 heartbeat 없으면 장애로 판단
  - ZooKeeper가 해당 브로커의 임시 노드 삭제

KRaft 기반:
  - 브로커가 Controller에 heartbeat 전송
  - 기본 9초(broker.session.timeout.ms) 내 없으면 장애로 판단
```

### 장애 시 순서

```
1. Controller가 장애 브로커 감지
2. 장애 브로커가 Leader인 파티션 목록 수집
3. 각 파티션의 ISR에서 새 Leader 선출
4. 새 Leader 정보를 모든 브로커에 전파 (LeaderAndIsr 요청)
5. ZooKeeper/KRaft에 새 Metadata 기록
6. Producer/Consumer가 Metadata 갱신 후 새 Leader로 연결
7. 장애 브로커 복구 후 ISR 재참여 (복제 따라잡기)
```

### 장애 브로커 복구 후 처리

```
브로커 재시작:
1. 로그 복구 (Log Recovery)
   - 마지막 checkpoint 이후 로그 일관성 확인
   - Leader Epoch 기반으로 불일치 로그 truncate
2. Controller에 재등록
3. 각 파티션의 Leader에게 fetch 시작
4. Leader의 LEO까지 따라잡으면 ISR 재진입
5. 필요시 Preferred Leader 복귀
```

---

## 파티션 증설 시 주의사항

### 파티션 추가 방법

```bash
# 파티션 수 늘리기 (6 → 9)
kafka-topics.sh --bootstrap-server kafka:9092 \
  --alter --topic orders \
  --partitions 9

주의사항:
1. 파티션 감소는 불가능 (증가만 가능)
2. 기존 메시지는 재배치되지 않음
3. 새 파티션에는 새 메시지만 들어감
```

### 키 기반 파티셔닝 영향

```
파티션 3개일 때:
  key="order-123" → murmur2(key) % 3 = 1 → Partition 1

파티션 9개로 증가 후:
  key="order-123" → murmur2(key) % 9 = 7 → Partition 7

결과: 같은 키가 다른 파티션으로 → 순서 보장 깨짐
      기존 데이터(P1)와 새 데이터(P7)가 분산됨
```

```
안전한 파티션 증가 절차:
1. 영향받는 Consumer의 처리 로직이 순서에 의존하는지 확인
2. 의존하는 경우: 기존 데이터 소비 완료 후 파티션 증가
3. 의존하지 않는 경우: 즉시 증가 가능
4. 새 파티션에 기존 데이터 마이그레이션이 필요하면 별도 작업
```

### 파티션 재할당 (Partition Reassignment)

브로커를 추가했을 때 기존 파티션을 새 브로커에 재분산한다.

```bash
# 재할당 계획 생성
kafka-reassign-partitions.sh --bootstrap-server kafka:9092 \
  --broker-list "1,2,3,4" \
  --topics-to-move-json-file topics.json \
  --generate

# 재할당 실행
kafka-reassign-partitions.sh --bootstrap-server kafka:9092 \
  --reassignment-json-file reassignment.json \
  --execute

# 재할당 상태 확인
kafka-reassign-partitions.sh --bootstrap-server kafka:9092 \
  --reassignment-json-file reassignment.json \
  --verify
```

```
재할당 시 주의:
- 대용량 데이터 이동으로 네트워크/디스크 I/O 급증
- 운영 시간 외 또는 throttle 적용 권장

throttle 적용:
kafka-configs.sh --bootstrap-server kafka:9092 \
  --entity-type brokers \
  --entity-name 1 \
  --alter \
  --add-config leader.replication.throttled.rate=10485760  # 10MB/s
```

---

## 브로커 성능 튜닝

### OS 수준 설정

```bash
# 파일 디스크립터 한도
ulimit -n 100000
echo "kafka soft nofile 100000" >> /etc/security/limits.conf
echo "kafka hard nofile 100000" >> /etc/security/limits.conf

# 가상 메모리 (Kafka는 페이지 캐시를 적극 활용)
sysctl -w vm.swappiness=1             # 스왑 거의 사용 안 함
sysctl -w vm.dirty_background_ratio=5 # 백그라운드 플러시 시작 임계값
sysctl -w vm.dirty_ratio=80           # 동기 플러시 임계값

# 네트워크 버퍼
sysctl -w net.core.rmem_max=16777216
sysctl -w net.core.wmem_max=16777216
```

### 브로커 핵심 설정

```properties
# 스레드 설정
num.network.threads=8       # 네트워크 I/O 스레드 (CPU 코어 수 기준)
num.io.threads=16           # 디스크 I/O 스레드 (num.network.threads * 2 권장)
num.replica.fetchers=4      # 복제 fetch 스레드

# 로그 설정
log.dirs=/data/kafka-logs   # 여러 디스크: /data1/kafka,/data2/kafka
log.segment.bytes=1073741824
log.retention.hours=168

# 소켓 버퍼
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
```

### JVM 설정

```bash
# kafka-server-start.sh 수정 또는 KAFKA_HEAP_OPTS 환경변수
export KAFKA_HEAP_OPTS="-Xmx6g -Xms6g"

# G1GC 설정 (대용량 힙 권장)
export KAFKA_JVM_PERFORMANCE_OPTS="-server \
  -XX:+UseG1GC \
  -XX:MaxGCPauseMillis=20 \
  -XX:InitiatingHeapOccupancyPercent=35 \
  -XX:+ExplicitGCInvokesConcurrent \
  -Djava.awt.headless=true"
```

### 모니터링 핵심 지표

```
브로커 헬스:
  kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec     # 초당 수신 바이트
  kafka.server:type=BrokerTopicMetrics,name=BytesOutPerSec    # 초당 송신 바이트
  kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec  # 초당 메시지 수

요청 처리:
  kafka.network:type=RequestMetrics,name=TotalTimeMs,request=Produce  # Produce 지연
  kafka.network:type=RequestMetrics,name=TotalTimeMs,request=FetchConsumer
  kafka.network:type=RequestMetrics,name=RequestsPerSec

복제:
  kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions  # 복제 지연 파티션
  kafka.server:type=ReplicaManager,name=LeaderCount                # 이 브로커가 리더인 파티션 수
  kafka.controller:type=KafkaController,name=ActiveControllerCount  # 1이면 정상

디스크:
  kafka.log:type=LogFlushStats,name=LogFlushRateAndTimeMs  # 플러시 통계
```
