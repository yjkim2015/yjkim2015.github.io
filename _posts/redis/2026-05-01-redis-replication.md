---
title: "Redis 데이터 복제(Replication) 동작 원리"
categories:
- REDIS
toc: true
toc_sticky: true
toc_label: 목차
---

새벽 2시, 서비스가 갑자기 다운됐다는 알림이 온다. Redis 마스터 서버의 디스크가 고장났다. 데이터는? 서비스 재개까지 걸리는 시간은? 복제 없이 단일 Redis만 운영 중이었다면 모든 캐시 데이터가 날아가고 서비스는 멈춘다. 복제(Replication)는 바로 이런 상황에 대비하는 구조다.

## Redis 복제란?

> **비유**: 복제는 중요한 문서를 복사해 여러 금고에 나눠 보관하는 것과 같다. 본사 금고(마스터)가 털려도 지점 금고(레플리카)에 동일한 사본이 있어 업무를 이어갈 수 있다.

Redis 복제는 **마스터(Master)** 노드의 데이터를 하나 이상의 **레플리카(Replica)** 노드에 실시간으로 복사하는 기능이다.

<div class="mermaid">
graph LR
    C[Client]
    C -->|쓰기/읽기| M[Master]
    M -->|복제 읽기 전용| R1[Replica 1]
    M -->|복제 읽기 전용| R2[Replica 2]
    M -->|복제 읽기 전용| R3[Replica 3]
</div>

### 목적

| 목적 | 설명 |
|------|------|
| **고가용성** | 마스터 장애 시 레플리카가 승격 |
| **읽기 분산** | 읽기 요청을 레플리카로 분산 |
| **데이터 백업** | 레플리카에서 RDB 스냅샷 생성 (마스터 부하 없이) |

---

## 복제 설정

### 레플리카 설정

```bash
# redis.conf (레플리카 측)
replicaof 192.168.1.100 6379

# 또는 런타임에
REPLICAOF 192.168.1.100 6379
```

### 인증이 필요한 경우

```bash
# 레플리카 측 redis.conf
masterauth "your_password"
```

### 레플리카를 독립 마스터로 전환

```bash
REPLICAOF NO ONE
```

---

## 복제 동작 원리

### 1단계: 전체 동기화 (Full Sync)

레플리카가 **최초 연결** 시 또는 **재동기화가 불가능**할 때 수행된다.

<div class="mermaid">
sequenceDiagram
    participant Rep as Replica
    participant M as Master

    Rep->>M: PSYNC ? -1
    Note over M: 1. BGSAVE 실행 (RDB 스냅샷 생성)
    Note over M: 새 쓰기는 replication buffer에 저장
    M-->>Rep: RDB 파일 전송
    Note over Rep: 2. RDB 로딩 (기존 데이터 전부 삭제)
    M-->>Rep: replication buffer 전송
    Note over Rep: 3. buffer 명령어 적용
    Note over Rep,M: 동기화 완료!
</div>

**주의**: Full Sync 중 마스터는 **BGSAVE + 버퍼 유지**로 메모리를 추가 사용한다. 데이터가 크면 수 GB 단위로 메모리가 증가할 수 있다.

### 2단계: 부분 동기화 (Partial Sync)

연결이 잠시 끊겼다가 재연결되면, **끊긴 부분부터** 이어서 동기화한다.

<div class="mermaid">
sequenceDiagram
    participant Rep as Replica
    participant M as Master

    Note over M: replication backlog (원형 버퍼)<br>cmd1, cmd2, cmd3, cmd4, cmd5
    Rep->>M: PSYNC &lt;replid&gt; 12345 (offset 12345까지 받았음)
    Note over M: backlog에 offset 12345 이후 데이터 존재 확인
    M-->>Rep: cmd3, cmd4, cmd5 전송 (Partial Sync)
    Note over Rep,M: Partial Sync 성공!
</div>

**실패 조건**: 레플리카의 offset이 backlog에 없으면 (너무 오래 끊어짐) → **Full Sync로 폴백**

```bash
# backlog 크기 늘리기 (네트워크가 불안정한 환경)
repl-backlog-size 256mb
```

### 3단계: 명령어 전파 (Command Propagation)

동기화 완료 후, 마스터의 모든 쓰기 명령어가 **실시간으로** 레플리카에 전파된다.

<div class="mermaid">
sequenceDiagram
    participant C as Client
    participant M as Master
    participant R1 as Replica 1
    participant R2 as Replica 2
    participant R3 as Replica 3

    C->>M: SET user:1 "Kim"
    M-->>C: OK
    M->>R1: SET user:1 "Kim" (비동기)
    M->>R2: SET user:1 "Kim" (비동기)
    M->>R3: SET user:1 "Kim" (비동기)
</div>

**비동기**: 마스터는 레플리카의 응답을 **기다리지 않는다.** 따라서 레플리카는 항상 마스터보다 약간 뒤처질 수 있다.

---

## 복제 토폴로지

### 체인 복제

<div class="mermaid">
graph LR
    M[Master] --> RA[Replica A]
    RA --> RB[Replica B]
    RB --> RC[Replica C]
</div>

마스터의 부하를 줄일 수 있지만, 전파 지연이 길어진다.

### 스타 복제

<div class="mermaid">
graph LR
    M[Master] --> RA[Replica A]
    M --> RB[Replica B]
    M --> RC[Replica C]
</div>

지연이 짧지만, 마스터의 네트워크 부하가 레플리카 수에 비례한다.

---

## 비동기 복제의 한계

### 데이터 유실 시나리오

<div class="mermaid">
sequenceDiagram
    participant C as Client
    participant M as Master
    participant Rep as Replica

    C->>M: SET key value
    M-->>C: OK
    M--)Rep: 전파 시도 (비동기)...
    Note over M: 크래시 💀
    Note over Rep: 승격 → 새 마스터 (key 없음!)
    Note over C,Rep: 클라이언트는 OK 받았지만 데이터 유실!
</div>

### WAIT 명령어 — 동기 복제 흉내

```bash
SET important:data "critical"
WAIT 2 5000
# 최소 2개 레플리카가 확인할 때까지 최대 5초 대기
# 반환값: 확인한 레플리카 수
```

**주의**: `WAIT`는 강한 일관성을 **보장하지 않는다.** 레플리카가 받았다는 확인(ACK)이지, 디스크에 썼다는 보장이 아니다. 그래도 유실 확률은 크게 줄어든다.

---

## Sentinel — 자동 장애 조치

수동으로 레플리카를 승격시키는 것은 비현실적이다. **Redis Sentinel**이 자동으로 처리한다.

<div class="mermaid">
graph TD
    S1[Sentinel 1] --- S2[Sentinel 2]
    S2 --- S3[Sentinel 3]
    S3 --- S1
    S1 & S2 & S3 -->|감시| M[Master]
    S1 & S2 & S3 -->|감시| R1[Replica 1]
    S1 & S2 & S3 -->|감시| R2[Replica 2]
    M -->|복제| R1
    M -->|복제| R2
</div>

### 동작 과정

1. **모니터링**: Sentinel이 마스터에 주기적으로 PING
2. **주관적 다운(SDOWN)**: 한 Sentinel이 응답 없음 감지
3. **객관적 다운(ODOWN)**: 과반수 Sentinel이 동의
4. **Failover**: 레플리카 중 하나를 마스터로 승격
5. **재설정**: 나머지 레플리카가 새 마스터를 바라보도록 설정

### 레플리카 선택 기준 (우선순위)

1. `replica-priority` 값이 가장 낮은 노드
2. 복제 offset이 가장 큰 노드 (가장 최신 데이터)
3. Run ID가 사전순으로 가장 작은 노드

---

## Redis Cluster에서의 복제

Redis Cluster는 **샤딩 + 복제**를 결합한다.

<div class="mermaid">
graph LR
    MA["Master A (슬롯 0~5460)"] --> RA[Replica A']
    MB["Master B (슬롯 5461~10922)"] --> RB[Replica B']
    MC["Master C (슬롯 10923~16383)"] --> RC[Replica C']
</div>

- 각 마스터가 해시 슬롯의 일부를 담당
- 마스터 장애 시 해당 레플리카가 자동 승격
- **과반수 마스터가 죽으면** 클러스터 전체가 멈춤

---

## 복제 모니터링

### INFO replication

```bash
INFO replication
```

```
role:master
connected_slaves:2
slave0:ip=10.0.0.2,port=6379,state=online,offset=123456,lag=0
slave1:ip=10.0.0.3,port=6379,state=online,offset=123450,lag=1
master_repl_offset:123456
repl_backlog_active:1
repl_backlog_size:1048576
```

### 핵심 지표

| 지표 | 의미 | 경고 기준 |
|------|------|-----------|
| `lag` | 레플리카 지연 (초) | > 1초면 주의 |
| `master_repl_offset - slave_offset` | 바이트 단위 지연 | 지속 증가 시 문제 |
| `state` | 연결 상태 | `online`이 아니면 문제 |
| `repl_backlog_size` | 부분 동기화 버퍼 | 너무 작으면 Full Sync 빈발 |

---

## 실무 설정 권장

```bash
# redis.conf (마스터)
repl-backlog-size 256mb          # 네트워크 불안정 대비
repl-backlog-ttl 3600            # 레플리카 없어도 1시간 유지
min-replicas-to-write 1          # 최소 1개 레플리카 연결 시만 쓰기 허용
min-replicas-max-lag 10          # 레플리카 지연 10초 이내

# redis.conf (레플리카)
replica-read-only yes            # 레플리카 쓰기 방지
replica-serve-stale-data yes     # 동기화 중에도 (오래된) 데이터 제공
```

### min-replicas-to-write

마스터가 혼자 남으면 쓰기를 거부하여, **장애 시 데이터 유실 범위**를 제한한다.

<div class="mermaid">
graph LR
    subgraph 정상
        M1[Master] <-->|연결| R1[Replica]
        M1 --> W1[쓰기 허용]
    end
    subgraph 장애
        M2[Master] -. 연결 끊김 ✕ .- R2[Replica]
        M2 --> W2[쓰기 거부 - 유실 방지]
    end
    style W1 fill:#8f8,stroke:#080
    style W2 fill:#f88,stroke:#c00
</div>

---

## 정리

| 항목 | 핵심 |
|------|------|
| 복제 방식 | 비동기 (기본), WAIT로 준동기 가능 |
| 초기 동기화 | Full Sync (RDB 전송) |
| 재연결 | Partial Sync (backlog 활용) |
| 장애 조치 | Sentinel (자동 failover) |
| 데이터 유실 | 비동기 복제 특성상 불가피 → WAIT, min-replicas로 완화 |
| Cluster | 샤딩 + 복제 결합, 해시 슬롯 기반 |
