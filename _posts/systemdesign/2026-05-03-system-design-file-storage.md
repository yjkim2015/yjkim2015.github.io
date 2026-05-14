---
title: "분산 파일 저장소 설계 — Google Drive를 직접 만들어보자"
categories:
- SYSTEMDESIGN
toc: true
toc_sticky: true
toc_label: 목차
---

> **한 줄 요약**: 분산 파일 저장소의 핵심은 파일을 4MB 블록으로 쪼개 SHA-256 해시로 중복을 제거하고, 메타데이터 DB로 블록 조각을 추적하며, SSE/WebSocket으로 여러 디바이스에 변경을 실시간 전파하는 것이다.

## 실제 문제: Google Drive는 어떻게 5억 명의 파일을 저장할까?

2023년 기준 Google Drive에 저장된 데이터는 약 **15엑사바이트(EB)**를 넘는다고 알려져 있습니다. 이는 지구상 모든 인류가 생산한 인쇄물의 10배에 달하는 양입니다. 매일 수백만 명이 파일을 올리고, 팀과 공유하고, 다른 기기에서 동기화합니다.

이 시스템을 직접 만들어야 한다고 상상해 보세요. 단순히 파일을 디스크에 저장하는 것처럼 보이지만, 실제로는 엄청난 복잡도가 숨어 있습니다:

- 10GB짜리 영상 파일을 업로드하다 와이파이가 끊기면?
- 팀원 두 명이 동시에 같은 문서를 수정하면?
- 랜섬웨어가 계정의 모든 파일을 암호화하면?
- 사용자 1000만 명이 같은 영상 파일을 각자 복사본으로 업로드하면?

이 질문들이 곧 분산 파일 저장소 설계의 본질입니다.

---

## 설계 의사결정 로드맵

### 결정 1: 저장 단위 — 파일 단위 vs 블록 단위

**문제**: 파일 단위로 저장하면 1GB 파일의 마지막 1KB만 수정해도 1GB 전체를 재업로드해야 하고, 중복 제거도 불가능하다.

| 후보 | 장점 | 단점 | 선택 이유 |
|------|------|------|-----------|
| 파일 단위 (S3 단순 업로드) | 구현 단순, 인프라 최소 | 수정 시 전체 재업로드, 중단 시 처음부터 재시작 | 소규모 MVP, 수정 빈도 낮은 경우 |
| **블록 단위 (4MB)** | 변경 블록만 재업로드, 병렬 전송, 재개 가능 | 메타데이터 DB 필요, 블록 조립 로직 | **프로덕션 표준 — Dropbox·Drive 동일** |
| 청크 스트리밍 (가변 크기) | 콘텐츠 기반 분할로 중복 제거율 향상 | 구현 복잡도 매우 높음 | 극한 중복 제거 최적화 필요 시 |

**우리의 선택: 4MB 고정 블록** — 이유: 메타데이터 행 수 관리 가능(1GB=256블록), 재전송 비용 수용 가능, Google Drive·Dropbox 실증 검증값.

---

### 결정 2: 중복 제거 — 파일 해시 vs 블록 해시

**문제**: 파일 전체 해시는 1바이트만 달라도 중복으로 인식하지 못한다. 블록 해시는 공통 부분을 재사용한다.

| 후보 | 장점 | 단점 | 선택 이유 |
|------|------|------|-----------|
| 파일 해시 (SHA-256 전체) | 구현 단순 | 1바이트 수정으로 전체 미인식, 중복 제거율 낮음 | 단순 파일 스토리지 |
| **블록 해시 (SHA-256 4MB 단위)** | 버전 간 공통 블록 재사용, 평균 40% 절감 | ref_count 관리, GC 잡 필요 | **표준 — 버전 관리와 시너지** |
| 내용 기반 가변 청크(CDC) | 중복 제거율 최고 | 구현 복잡, 청크 경계 계산 비용 | 극한 최적화 전용 |

**우리의 선택: 블록 단위 SHA-256 해시** — 이유: 버전 간 공통 블록 자동 재사용, ref_count로 GC 안전 처리, 충돌 내성 현실적으로 불가능(2^128 연산 필요).

---

### 결정 3: 충돌 해결 — LWW vs OT vs CRDT

**문제**: 두 사용자가 오프라인에서 같은 파일을 동시 수정하면 누구의 버전을 택할지 결정해야 한다. 잘못 선택하면 한 사용자의 작업이 조용히 사라진다.

| 후보 | 장점 | 단점 | 선택 이유 |
|------|------|------|-----------|
| **LWW (Last Writer Wins)** | 구현 단순, 오버헤드 없음 | 이전 편집자 작업 완전 소실 | **파일 단위 기본 — 버전 이력으로 복구 가능** |
| OT (Operational Transform) | 두 편집 모두 보존, 자동 병합 | 중앙 서버 필수, 구현 매우 복잡 | 실시간 공동 편집(Google Docs 방식) |
| CRDT | 중앙 서버 불필요, P2P 동기화 | 데이터 구조 복잡, 삭제 처리 까다로움 | 오프라인 우선 앱, Figma 방식 |
| 3-way merge | 공통 조상 기반 자동 병합 | 충돌 구간은 사용자 판단 필요 | 파일 시스템 + 실시간 협업 중간 |

**우리의 선택: LWW + 버전 이력 보존 + 3-way merge 시도** — 이유: 파일 단위 단순 충돌은 LWW, 충돌 발생 시 두 버전 모두 저장해 사용자 선택 제공. 실시간 편집은 OT로 별도 처리.

---

### 결정 4: 변경 알림 — Polling vs SSE vs WebSocket

**문제**: 노트북에서 수정한 파일이 스마트폰에 즉시 반영돼야 한다. Polling은 서버 낭비, WebSocket은 파일 알림에 과스펙이다.

| 후보 | 장점 | 단점 | 선택 이유 |
|------|------|------|-----------|
| Short Polling (5초마다) | 구현 가장 단순 | 빈 응답 95%, 서버 부하 극심 | 프로토타입 전용 |
| Long Polling | 구현 단순, 즉시성 일부 | 재연결 오버헤드, 서버 스레드 점유 | 간단한 알림 요구 |
| **SSE (Server-Sent Events)** | 단방향 충분, HTTP 인프라 재사용 | 단방향만 가능, HTTP/2 필요 시 멀티플렉싱 | **파일 변경 알림 표준** |
| WebSocket | 양방향 실시간 | 별도 핸드셰이크, LB 설정 변경 필요 | 실시간 공동 편집 시 필요 |

**우리의 선택: SSE** — 이유: 파일 알림은 서버→클라이언트 단방향으로 충분. 기존 HTTP 로드밸런서·프록시 재사용, 100만 동시 연결도 비동기 I/O로 처리 가능.

---

## 1. 요구사항 분석 및 규모 추정

### 기능 요구사항

1. 파일 업로드 / 다운로드 / 삭제
2. 폴더 계층 구조 지원
3. 파일 공유 (링크 공유, 권한별 접근: Owner/Editor/Viewer)
4. 파일 버전 관리 (이전 버전 복원)
5. 멀티 디바이스 자동 동기화
6. 오프라인 편집 후 온라인 시 병합

### 비기능 요구사항

- 가용성: **99.99%** (연간 52분 이하 다운타임)
- 내구성: **99.999999999% (eleven nines)** — 파일은 절대 유실되지 않음
- 일관성: 같은 파일을 두 디바이스에서 보면 동일한 내용이어야 함
- 지연시간: 파일 목록 조회 **100ms 미만**, 다운로드는 CDN 활용

### 규모 추정

```
DAU: 5,000만 명
평균 파일 크기: 500KB
일일 업로드: 200만 건

--- 저장 용량 ---
1인 평균 저장 용량: 15GB (Google Drive 무료 한도)
총 사용자 수: 5억 명 (MAU 기준)
총 저장 용량: 5억 × 15GB = 7.5EB

--- 트래픽 ---
일일 업로드 200만 건 × 500KB = 1TB/일
업로드 QPS: 200만 / 86,400 ≈ 23 QPS (평균)
피크 업로드 QPS: 23 × 5 = 115 QPS

다운로드는 업로드의 10배 가정:
다운로드 QPS ≈ 230 QPS (평균)
피크 다운로드 QPS ≈ 1,150 QPS

--- 블록 단위 분할 기준 ---
파일 1개 = 4MB 블록으로 분할
500KB 파일 → 1블록
1GB 파일 → 256블록
10GB 파일 → 2,560블록
```

> **비유:** 블록 분할은 마치 이사할 때 짐을 **이삿짐 박스**에 나눠 담는 것과 같습니다. 소파를 통째로 들고 좁은 계단을 오르는 대신, 분해해서 각 부품을 따로 옮기면 한 박스가 계단에서 떨어져도 나머지는 안전합니다. 파일도 마찬가지로 블록 단위로 관리하면 특정 블록만 재전송하면 됩니다.

---

## 2. 고수준 아키텍처

### 전체 구성 요소

```mermaid
graph LR
    A[Client] --> B[API서버]
    B --> C[메타DB]
    B --> D[블록스토리지]
    D --> E[CDN]
    E --> A
```

각 구성 요소의 역할은 다음과 같습니다:

1️⃣ **API 서버**: 파일 업로드/다운로드 요청 처리, 인증, 권한 검사, 청크 조율

2️⃣ **메타데이터 DB**: 파일명, 경로, 블록 목록, 버전, 공유 권한 등 파일의 "설명서" 저장

3️⃣ **블록 스토리지**: 실제 파일 데이터를 4MB 단위 블록으로 저장하는 오브젝트 스토리지 (AWS S3 호환)

4️⃣ **알림 서비스**: 파일 변경 이벤트를 다른 디바이스에 실시간 전파

5️⃣ **CDN**: 자주 다운로드되는 파일을 엣지 서버에 캐시해 지연시간 최소화

---

## 3. 파일 업로드 흐름 — 청크 업로드

### 왜 블록(Block) 단위 저장인가 — 파일 단위 저장의 한계

파일을 통째로 하나의 오브젝트로 저장하면 어떤 문제가 생길까요?

| 항목 | 파일 단위 저장 | 블록 단위 저장 |
|------|--------------|--------------|
| 수정 시 | 파일 전체를 다시 업로드 | 변경된 블록(4MB)만 재업로드 |
| 중복 제거 | 파일 전체가 달라야 중복 | **블록 단위로 SHA-256 비교**, 같은 블록 공유 |
| 네트워크 끊김 | 처음부터 재전송 | 받은 블록 이후부터 재개 |
| 다중 버전 | 매 버전마다 전체 저장 | 변경 블록만 추가, 나머지 재사용 |
| 병렬 업로드 | 불가능 | **블록별 병렬 전송** 가능 |

100MB 파일의 마지막 1MB만 수정했을 때: 파일 단위면 100MB 재업로드, 블록 단위면 4MB 1개만 재업로드. 대용량 동영상 편집 결과물을 자주 올리는 사용자라면 이 차이가 수십 배 트래픽 절감으로 이어집니다.

**왜 4MB인가**: 1KB면 블록 수가 너무 많아 메타데이터 DB 폭발(10GB = 1,048만 블록), 100MB면 재전송 비용이 너무 큼. 4MB는 Google Drive·Dropbox가 실무에서 검증한 균형점입니다.

### 왜 청크(Chunk) 업로드가 필요한가?

> **비유:** 대용량 파일을 통째로 업로드하는 것은 마치 **서울에서 부산까지 걸어서** 택배를 배달하는 것과 같습니다. 중간에 발목을 삐면 처음부터 다시 걸어야 합니다. 하지만 KTX를 타고 구간별로 나눠 이동하면, 한 구간에서 문제가 생겨도 그 구간만 다시 이동하면 됩니다.

10GB 파일을 한 번에 업로드할 경우, 9.9GB를 보내다가 네트워크가 끊기면 처음부터 다시 시작해야 합니다. 청크 업로드는 이를 방지합니다.

### 대용량 파일 업로드 병목 분석

10GB 파일 업로드 시 각 구간별 예상 지연 시간:

```
[클라이언트] → [로드밸런서] → [API 서버] → [S3]

클라이언트 → LB:       가정 100Mbps 가정 시 10GB = 800초 (13분)
LB → API 서버:         내부망 1Gbps, 오버헤드 무시
API 서버 (검증):        SHA-256 계산 — 10GB × 0.1ms/MB = 1초 (CPU)
API 서버 → S3 전송:    S3 멀티파트 병렬 전송, 병목 아님
S3 내구성 복제:        3 AZ 동기 복제 — 추가 100~200ms

병목 위치: 클라이언트 ↔ 서버 간 업로드 대역폭 (단연 1위)
두 번째 병목: API 서버를 경유하는 경우 서버 대역폭 포화
```

**왜 Presigned URL로 S3 직접 업로드인가**: API 서버를 경유하면 서버 인스턴스 1대의 네트워크 카드(보통 10Gbps)가 모든 업로드를 처리해야 합니다. 동시 업로드 100건 × 10GB면 1TB 데이터가 API 서버를 통과해야 합니다. Presigned URL은 클라이언트가 S3로 직접 업로드하므로 API 서버 대역폭 병목이 완전히 제거됩니다. S3는 AWS 내부적으로 수평 확장되어 사실상 무제한 대역폭을 제공합니다.

### 업로드 흐름 상세

```mermaid
graph LR
    A[클라이언트] -->|필요 블록 요청| B[청크 서버]
    B -->|PUT block| C[블록 스토어]
    B -->|complete| C
```

### 왜 SHA-256인가 — MD5·CRC32와 비교

블록을 식별하는 해시 함수 선택은 중복 제거의 정확성과 보안에 직결됩니다.

| 해시 함수 | 출력 크기 | 충돌 내성 | 속도 (1GB 기준) | 선택 여부 |
|-----------|-----------|-----------|----------------|-----------|
| CRC32 | 4바이트 | 매우 낮음 | 1~2초 | 무결성 검사 전용 |
| MD5 | 16바이트 | 낮음 (충돌 알려짐) | 3~5초 | **보안 용도 부적합** |
| SHA-1 | 20바이트 | 낮음 (2017년 충돌 실증) | 4~6초 | 폐기 권장 |
| SHA-256 | 32바이트 | **매우 높음** | 5~8초 | **선택** |

**왜 MD5가 안 되는가**: MD5는 다른 내용의 두 파일이 같은 해시를 갖도록 만드는 충돌(collision)이 실제로 가능합니다. 공격자가 악성 파일 A와 정상 파일 B를 같은 MD5 해시로 만들어 업로드하면, 서버는 "이미 있는 블록"으로 판단해 악성 파일 블록이 정상 파일로 제공될 수 있습니다. SHA-256은 현재 실용적 충돌 공격이 불가능합니다(2^128 이상의 연산 필요).

**속도 차이는 문제가 되지 않는가**: SHA-256이 MD5보다 2~3배 느리지만, 클라이언트 측에서 계산합니다. 현대 CPU는 SHA-256 하드웨어 가속(Intel SHA Extensions)을 지원해 4MB 블록 해시 계산에 1~2ms 수준입니다. 업로드 대역폭(수백ms~수초) 대비 무시할 수 있는 수준입니다.

### 중복 제거(Deduplication)의 마법

업로드 초기화 단계에서 클라이언트가 블록 해시 목록을 서버에 보내면, 서버는 **이미 저장된 블록은 재업로드하지 않아도 됩니다.** 이것이 블록 단위 중복 제거입니다.

예를 들어 회사 전체가 같은 100MB PowerPoint 템플릿을 각자 Drive에 저장하면, 첫 번째 사람만 실제로 업로드하고 나머지 999명은 해시 매핑만 추가하면 됩니다. 실제 스토리지 절감율은 **평균 40% 이상**으로 알려져 있습니다.

```python
# 클라이언트 측 블록 처리 의사 코드
def prepare_upload(file_path):
    blocks = []
    with open(file_path, 'rb') as f:
        while chunk := f.read(4 * 1024 * 1024):  # 4MB
            block_hash = hashlib.sha256(chunk).hexdigest()
            blocks.append({
                'hash': block_hash,
                'size': len(chunk),
                'data': chunk  # 메모리에 유지 (업로드 전까지)
            })
    return blocks

def upload_file(file_path):
    blocks = prepare_upload(file_path)
    hash_list = [b['hash'] for b in blocks]

    # 서버에 어떤 블록이 필요한지 확인
    response = api.post('/upload/init', {'hashes': hash_list})
    needed_hashes = set(response['needed'])

    # 필요한 블록만 업로드
    for block in blocks:
        if block['hash'] in needed_hashes:
            storage.put(f"/block/{block['hash']}", block['data'])

    # 파일 메타데이터 등록
    api.post('/upload/complete', {
        'name': file_path.name,
        'blocks': hash_list
    })
```

### 재개 가능 업로드(Resumable Upload)

네트워크 단절 시 클라이언트는 서버에 "어디까지 받았냐"를 물어볼 수 있습니다. 서버는 업로드 세션 상태를 유지해 이미 받은 블록 목록을 응답합니다. 클라이언트는 남은 블록만 재전송하면 됩니다.

```
GET /upload/{session_id}/status
→ { "received_blocks": ["hash1", "hash2", ...], "missing": ["hash7", ...] }
```

---

## 4. 파일 다운로드 흐름 — 블록 재조립

### 다운로드 순서

```mermaid
graph LR
    A[Client] -->|GET /file/id/metadata| B[API]
    B -->|블록목록+CDN URL| A
    A -->|GET hash 캐시히트| C[CDN]
    C -->|블록 반환 재조립| A
```

### CDN 활용 전략

자주 다운로드되는 파일(예: 공유된 영상, 인기 문서)은 CDN 엣지에 캐시됩니다. 블록 단위 저장의 장점이 여기서도 발휘됩니다. 같은 블록(동일 해시)이 여러 파일에 공유되면 CDN에 한 번만 올라가도 됩니다.

> **비유:** CDN은 마치 **동네 편의점**입니다. 자주 사는 물건(인기 파일 블록)은 편의점에 미리 갖다 놓고, 희귀한 물건만 창고(원본 스토리지)에서 가져옵니다. 고객(클라이언트)은 창고까지 갈 필요 없이 근처 편의점에서 바로 받을 수 있어 훨씬 빠릅니다.

---

## 5. 파일 동기화 — 충돌 해결 전략

### 동기화의 어려움

> **비유:** 두 사람이 동시에 같은 화이트보드에 서로 다른 내용을 적는다고 생각해보세요. 한 명이 "회의 날짜: 수요일"이라고 쓰는 동안 다른 사람이 "회의 날짜: 목요일"이라고 지우고 다시 씁니다. 누구의 내용이 맞을까요? 이것이 분산 시스템의 **충돌(Conflict)** 문제입니다.

### 전략 1: Last Writer Wins (LWW)

가장 단순한 전략입니다. 마지막으로 저장한 사람의 버전이 이깁니다. 타임스탬프를 비교해 나중 것을 채택합니다.

- **장점**: 구현 단순, 오버헤드 없음
- **단점**: 이전 편집자의 작업이 **완전히 소실**됨
- **사용처**: Dropbox 기본 동작, S3 오브젝트 덮어쓰기

```
파일 A - 사용자1 수정: 14:01:00 → "수요일"
파일 A - 사용자2 수정: 14:01:05 → "목요일"
결과: "목요일" 채택 (사용자1 작업 소실)
```

### 전략 2: Operational Transform (OT)

Google Docs가 사용하는 방식입니다. 두 편집 연산을 수학적으로 변환해 합칩니다.

- **장점**: 두 사람의 편집이 모두 보존됨
- **단점**: 구현 매우 복잡, 중앙 서버 필요
- **사용처**: Google Docs, Notion

```
사용자1: "Hello" → "Hello World" (위치 5에 " World" 삽입)
사용자2: "Hello" → "Hello!" (위치 5에 "!" 삽입)

OT 변환 결과:
사용자1의 연산을 사용자2 연산 이후로 조정:
→ "Hello! World" (두 삽입 모두 반영)
```

### 전략 3: CRDT (Conflict-free Replicated Data Type)

수학적으로 충돌이 발생하지 않도록 설계된 자료구조입니다. 중앙 서버 없이 P2P 동기화도 가능합니다.

- **장점**: 중앙 조율 서버 불필요, 오프라인 동기화 자연스럽게 처리
- **단점**: 데이터 구조 복잡, 특정 연산(삭제) 처리 까다로움
- **사용처**: Figma, Linear, Apple Notes

### Google Drive의 실제 선택

Google Drive는 파일 단위로는 **LWW + 버전 이력 보존**을 사용합니다. 즉, 충돌 시 두 버전 모두 저장하고 사용자에게 선택권을 줍니다. Google Docs (실시간 편집)은 OT를 사용합니다.

```mermaid
graph LR
    CONFLICT["충돌 감지"]
    LWW["단순 파일 충돌 → LWW + 버"]
    OT["실시간 텍스트 편집 → OT"]
    CRDT["오프라인 우선 앱 → CRDT"]
    CONFLICT --> LWW
    CONFLICT --> OT
    CONFLICT --> CRDT
```

---

## 6. 메타데이터 DB 설계

### 왜 메타데이터가 중요한가?

블록 스토리지에는 그냥 SHA-256 해시 이름으로 된 바이너리 덩어리들만 있습니다. **이 블록들이 어떤 파일인지, 어떤 순서로 조립해야 하는지, 누가 접근 가능한지**는 모두 메타데이터 DB가 알고 있습니다. 블록 스토리지가 창고라면, 메타데이터 DB는 창고 목록표입니다.

### 핵심 테이블 스키마

**users 테이블**
```sql
CREATE TABLE users (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    email       VARCHAR(255) UNIQUE NOT NULL,
    quota_bytes BIGINT NOT NULL DEFAULT 16106127360, -- 15GB
    used_bytes  BIGINT NOT NULL DEFAULT 0,
    created_at  DATETIME NOT NULL
);
```

**files 테이블**
```sql
CREATE TABLE files (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id     BIGINT NOT NULL,
    parent_id   BIGINT,           -- NULL이면 루트 폴더
    name        VARCHAR(512) NOT NULL,
    mime_type   VARCHAR(128),
    size_bytes  BIGINT NOT NULL DEFAULT 0,
    is_folder   BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  DATETIME NOT NULL,
    updated_at  DATETIME NOT NULL,
    INDEX idx_user_parent (user_id, parent_id),
    INDEX idx_updated (updated_at)
);
```

**file_versions 테이블**
```sql
CREATE TABLE file_versions (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    file_id     BIGINT NOT NULL,
    version_num INT NOT NULL,
    size_bytes  BIGINT NOT NULL,
    created_by  BIGINT NOT NULL,
    created_at  DATETIME NOT NULL,
    UNIQUE KEY uq_file_version (file_id, version_num)
);
```

**blocks 테이블**
```sql
CREATE TABLE blocks (
    hash        CHAR(64) PRIMARY KEY,  -- SHA-256 hex
    size_bytes  INT NOT NULL,
    ref_count   INT NOT NULL DEFAULT 0, -- 참조 카운트 (중복 제거 핵심)
    storage_key VARCHAR(512) NOT NULL,  -- S3 오브젝트 키
    created_at  DATETIME NOT NULL
);
```

**version_blocks 테이블 (파일 버전 ↔ 블록 매핑)**
```sql
CREATE TABLE version_blocks (
    version_id  BIGINT NOT NULL,
    block_seq   INT NOT NULL,     -- 블록 순서 (재조립에 사용)
    block_hash  CHAR(64) NOT NULL,
    PRIMARY KEY (version_id, block_seq),
    INDEX idx_hash (block_hash)
);
```

**shares 테이블**
```sql
CREATE TABLE shares (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    file_id     BIGINT NOT NULL,
    grantee_id  BIGINT,           -- NULL이면 링크 공유
    permission  ENUM('viewer','editor','owner') NOT NULL,
    token       VARCHAR(64),      -- 링크 공유 토큰
    expires_at  DATETIME,         -- 만료 시각
    created_at  DATETIME NOT NULL,
    INDEX idx_file (file_id),
    INDEX idx_token (token)
);
```

### 읽기 성능 최적화

파일 목록 조회(폴더 내 파일 나열)는 가장 빈번한 쿼리입니다. `(user_id, parent_id)` 복합 인덱스로 O(1) 수준으로 조회할 수 있습니다.

블록 조회는 해시 기반이라 PRIMARY KEY 조회이므로 별도 인덱스가 필요 없습니다.

---

## 7. 버전 관리 — 스냅샷 vs 델타

### 스냅샷 방식

파일이 수정될 때마다 전체 블록 목록을 새 버전으로 저장합니다.

> **비유:** 스냅샷은 사진을 매번 새로 찍는 것과 같습니다. 변한 부분이 1%뿐이어도 100% 전체를 새로 찍습니다. 복원은 쉽지만(그냥 그 사진을 보면 됨), 저장 비용이 큽니다.

- **장점**: 특정 시점 복원이 즉시 가능, 구현 단순
- **단점**: 저장 비용이 높음 (블록 단위 중복 제거로 완화 가능)

### 델타 방식

변경된 블록만 저장하고, 버전 간 차이(diff)를 체인으로 연결합니다.

> **비유:** 델타는 일기를 쓸 때 "어제와 달라진 점만" 기록하는 것입니다. 저장 공간은 적지만, 5년 전 일기를 보려면 모든 변경 이력을 순차적으로 따라가야 합니다.

- **장점**: 저장 비용 대폭 절감
- **단점**: 특정 시점 복원 시 델타 체인 전체를 다시 계산해야 함

### Google Drive의 실제 접근

블록 단위 저장이 자연스럽게 델타 방식을 구현해줍니다. 파일이 수정되면 변경된 블록만 해시가 달라지고, 나머지 블록은 그대로 재사용됩니다.

```
v1: [hash_A, hash_B, hash_C, hash_D]
v2: [hash_A, hash_B, hash_E, hash_D]  ← hash_C만 hash_E로 교체
→ 실제로 새로 저장된 블록: hash_E 하나뿐
→ 나머지 3개 블록은 v1과 공유
```

### 버전 정책

무한정 모든 버전을 보존하면 저장 비용이 무한히 증가합니다. 실용적인 정책은 다음과 같습니다:

- 최근 30일: 모든 버전 보존
- 30일~1년: 일 단위 스냅샷만 보존 (시간별 삭제)
- 1년 이상: 월 단위 스냅샷만 보존

---

## 8. 알림 서비스 — 디바이스 간 변경 전파

### 왜 알림이 중요한가?

노트북에서 파일을 수정하면, 스마트폰의 Drive 앱에서도 변경된 버전이 보여야 합니다. 이것은 단순한 알림이 아니라 **분산 시스템의 이벤트 전파** 문제입니다.

### 방식 비교

```mermaid
graph LR
    A[ShortPolling] -->|낭비| E[비추천]
    B[LongPolling] -->|부하| F[보통]
    C[WebSocket] -->|과스펙| E
    D[SSE] -->|최적| G[추천]
```

### 왜 SSE인가 — WebSocket·Long Polling과 비교

| 방식 | 방향 | 연결 방식 | 서버 부하 | 선택 이유 |
|------|------|-----------|-----------|-----------|
| Short Polling | 클→서 반복 | HTTP 반복 요청 | 매우 높음 (빈 응답 95%) | 비추천 — 낭비 심함 |
| Long Polling | 클→서 유지 | HTTP 1건 유지 후 재연결 | 중간 | 구현 단순하나 재연결 오버헤드 |
| WebSocket | 양방향 | TCP 영구 연결 | 낮음 | **파일 알림은 단방향 — 과스펙** |
| SSE | 서→클 | HTTP/1.1 스트림 | 낮음 | **단방향으로 충분, HTTP 인프라 재사용** |

**왜 WebSocket이 과스펙인가**: 파일 변경 알림은 서버가 클라이언트에게 "파일 X가 바뀌었다"를 보내는 단방향 흐름입니다. 클라이언트가 파일을 수정한 사실은 별도 HTTP POST로 이미 전송합니다. WebSocket의 양방향 채널은 필요 없습니다. SSE는 일반 HTTP 연결로 동작하므로 기존 로드밸런서·프록시 인프라를 그대로 사용할 수 있습니다. WebSocket은 별도 업그레이드 핸드셰이크와 로드밸런서 설정 변경이 필요합니다.

**실제 컨넥션 수 비교**: DAU 5000만 중 동시 접속 100만 명 가정. Short Polling(5초 간격)이면 초당 20만 건의 빈 HTTP 요청. SSE는 100만 개의 장기 연결 유지로 서버 파일 디스크립터 100만 개 소모 — Go/Node.js의 비동기 I/O로 인스턴스 수십 대면 처리 가능.

### SSE(Server-Sent Events) 선택 이유

파일 변경 알림은 **서버 → 클라이언트** 단방향 이벤트입니다. 클라이언트가 서버에 "나도 변경했어"를 알리는 건 별도 HTTP 요청으로 처리합니다. 따라서 양방향 WebSocket은 과스펙이고, SSE가 더 적합합니다.

```
클라이언트 → 서버: HTTP 연결 유지 (SSE 구독)
서버 → 클라이언트: text/event-stream 형식으로 이벤트 푸시

이벤트 형식:
data: {"event":"file_updated","file_id":12345,"version":7}
data: {"event":"file_created","parent_id":100,"file_id":12346}
```

### Kafka를 통한 알림 파이프라인

```mermaid
graph LR
    API["API 서버"]
    KAFKA["Kafka 토픽"]
    NOTIF["알림 서비스"]
    CLIENT["각 디바이스"]
    API -->|"파일 변경 이벤트 발행"| KAFKA
    KAFKA -->|"구독"| NOTIF
    NOTIF -->|"SSE 스트림"| CLIENT
```

Kafka를 중간에 두면 API 서버와 알림 서비스가 분리되어, 트래픽 급증 시 알림 서비스만 독립적으로 스케일 아웃할 수 있습니다.

---

## 9. 저장소 계층 — Hot/Warm/Cold 자동 티어링

### 저장 비용의 현실

모든 파일을 SSD에 저장하면 성능은 최고지만 비용이 폭발합니다. 실제로 대부분의 파일은 업로드 후 30일이 지나면 거의 접근되지 않습니다. 저장 계층을 나눠 비용을 최적화해야 합니다.

> **비유:** 파일 티어링은 식당의 **메뉴 진열**과 같습니다. 가장 많이 팔리는 메뉴는 주방 바로 앞(Hot, SSD), 계절 메뉴는 냉장고(Warm, HDD), 작년 메뉴는 창고(Cold, Glacier). 손님(클라이언트)이 주문하면 어디서 가져오든 같은 음식이지만, 창고에서 가져오면 시간이 좀 더 걸립니다.

### 티어 정의

| 계층 | 스토리지 | 접근 시간 | 비용 | 대상 |
|------|----------|-----------|------|------|
| Hot | SSD (NVMe) | 1-10ms | 높음 | 최근 7일 내 접근 파일 |
| Warm | HDD (SATA) | 50-100ms | 중간 | 7일~6개월 |
| Cold | S3 Glacier | 분~시간 | 매우 낮음 | 6개월 이상 미접근 |

### 자동 티어링 구현

파일 접근 시 `last_accessed_at`을 업데이트하고, 주기적인 배치 잡이 오래된 파일을 하위 계층으로 이동합니다.

```python
# 일 1회 실행되는 티어링 배치 잡 (의사 코드)
def auto_tier_down():
    now = datetime.utcnow()

    # Warm으로 이동 (7일 이상 미접근)
    hot_to_warm = db.query("""
        SELECT block_hash FROM block_locations
        WHERE tier = 'hot' AND last_accessed_at < NOW() - INTERVAL 7 DAY
    """)
    for block in hot_to_warm:
        storage.copy(block.hash, from_tier='hot', to_tier='warm')
        db.update_tier(block.hash, 'warm')

    # Cold로 이동 (6개월 이상 미접근)
    warm_to_cold = db.query("""
        SELECT block_hash FROM block_locations
        WHERE tier = 'warm' AND last_accessed_at < NOW() - INTERVAL 180 DAY
    """)
    for block in warm_to_cold:
        storage.copy(block.hash, from_tier='warm', to_tier='cold')
        db.update_tier(block.hash, 'cold')
```

Cold 계층에서 파일을 요청하면 즉시 반환 대신 "복원 중" 상태를 알려주고, 몇 분 후 다운로드 준비가 되면 SSE로 알립니다.

---

## 10. 중복 제거(Deduplication) 심화

### 블록 레벨 중복 제거

같은 해시를 가진 블록은 스토리지에 한 번만 저장됩니다. `blocks` 테이블의 `ref_count`가 이를 추적합니다.

```mermaid
graph LR
    F1["파일A v1"] --> H1["H1 ref=3"]
    F1 --> H2["H2 ref=3"]
    F2["파일B"] --> H1
    F2 --> H5["H5 ref=1"]
    F3["파일A v2"] --> H1
    F3 --> H7["H7 ref=1"]
```

### 파일 삭제 시 가비지 컬렉션

파일을 삭제하면 즉시 블록을 삭제하지 않습니다. `ref_count`를 줄이고, `ref_count = 0`인 블록을 주기적인 GC 잡이 실제 스토리지에서 삭제합니다.

```python
def delete_file_version(version_id):
    # 트랜잭션 내에서
    blocks = db.query("SELECT block_hash FROM version_blocks WHERE version_id = ?", version_id)
    for block_hash in blocks:
        db.execute("UPDATE blocks SET ref_count = ref_count - 1 WHERE hash = ?", block_hash)
    db.execute("DELETE FROM version_blocks WHERE version_id = ?", version_id)
    db.execute("DELETE FROM file_versions WHERE id = ?", version_id)
    # ref_count = 0인 블록은 GC 잡이 나중에 처리
```

### 절감 효과

실제 Google Drive 내부 데이터(추정)에 따르면:
- 개인 파일의 블록 중복률: **약 15-20%** (같은 사진 여러 폴더에 복사 등)
- 기업 환경(같은 회사 사람들이 공통 문서 많음): **약 40-60%**
- 전체 스토리지 절감: 평균 **40% 수준**

---

## 11. 보안 — E2E 암호화, 공유 링크, 권한 모델

### E2E(End-to-End) 암호화

서버는 파일 내용을 **읽을 수 없어야** 합니다. 진정한 E2E 암호화 구현 방식:

1️⃣ 클라이언트가 파일별 고유 **대칭키(AES-256)** 생성

2️⃣ 대칭키로 파일 암호화 후 업로드

3️⃣ 대칭키를 사용자의 **공개키(RSA-2048)**로 암호화해 서버에 저장

4️⃣ 다운로드 시 클라이언트가 자신의 **개인키**로 대칭키를 복호화 → 파일 복호화

```
서버가 저장하는 것: 암호화된 파일 블록 + 암호화된 대칭키
서버가 모르는 것: 실제 파일 내용, 대칭키 원문
→ 서버가 해킹당해도 파일 내용 노출 안 됨
```

**단점**: 비밀번호를 잊으면 파일 영구 복호화 불가능. Keybase, ProtonDrive가 이 방식을 사용합니다.

### 공유 링크 보안

링크 공유 시 `token`은 암호학적으로 안전한 난수여야 합니다. 짧은 토큰(6자리 등)은 브루트포스 공격에 취약합니다.

```sql
-- 보안 토큰 생성
token = base64url(random_bytes(32))  -- 43자, 충분히 예측 불가

-- 만료 시각 필수
expires_at = NOW() + INTERVAL 7 DAY

-- 접근 횟수 제한 (선택)
max_downloads = 10
download_count = 0
```

### 권한 모델 (Owner / Editor / Viewer)

```mermaid
graph LR
    OWNER["Owner"]
    EDITOR["Editor"]
    VIEWER["Viewer"]
    OWNER -->|"권한 위임"| EDITOR
    OWNER -->|"권한 위임"| VIEWER
    EDITOR -->|"제한적 공유"| VIEWER
```

| 권한 | 읽기 | 수정 | 삭제 | 공유 | 권한 변경 |
|------|------|------|------|------|-----------|
| Owner | O | O | O | O | O |
| Editor | O | O | X | O (Viewer만) | X |
| Viewer | O | X | X | X | X |

권한 조회는 모든 API 요청마다 발생하므로 Redis에 캐시합니다:

```
CACHE KEY: "perm:{file_id}:{user_id}"
CACHE VALUE: "viewer" / "editor" / "owner" / "none"
TTL: 5분 (권한 변경 시 즉시 무효화)
```

---

## 12. 극한 시나리오

### 시나리오 1: 10GB 파일 업로드 중 네트워크 끊김

**발생 상황**: 사용자가 큰 영상 파일을 업로드하다가 지하철 터널에 들어가 와이파이가 끊겼습니다.

**나쁜 설계**: 단일 HTTP POST로 전체 파일 전송 → 연결 끊기면 처음부터 재시작

**올바른 설계**:

1️⃣ 업로드 시작 시 서버가 `session_id` 발급 (유효기간 48시간)

2️⃣ 클라이언트는 블록 단위로 업로드하며 진행 상황을 로컬에 저장

3️⃣ 네트워크 재연결 시 서버에 `GET /upload/{session_id}/status` 요청

4️⃣ 서버가 받은 블록 목록 반환 → 클라이언트가 남은 블록만 재전송

5️⃣ 모든 블록 수신 완료 시 파일 레코드 생성

```
시간: 0분 — 2,560개 블록 중 0번부터 업로드 시작
시간: 15분 — 1,200번 블록 전송 중 연결 끊김
시간: 20분 — 재연결, 서버에 상태 조회
서버 응답: "1,199번까지 수신 완료, 1,200번부터 재전송하세요"
→ 전체의 53%를 버리지 않고 재활용
```

### 시나리오 2: 두 사람이 동시에 같은 문서를 오프라인 편집

**발생 상황**: Alice와 Bob이 비행기에서 오프라인으로 같은 보고서를 각자 수정했습니다. 착륙 후 둘 다 동기화를 시도합니다.

**나쁜 설계**: 마지막 동기화 요청이 이기고 이전 것을 덮어씀 → Alice나 Bob의 작업이 소실

**올바른 설계**:

1️⃣ 각 클라이언트는 오프라인 편집을 로컬 로그에 기록 (벡터 클록 포함)

2️⃣ 동기화 시 서버는 두 버전의 공통 조상(LCA, Lowest Common Ancestor)을 찾음

3️⃣ 3-way merge를 시도:
- 충돌 없는 변경: 자동 병합
- 충돌 발생: 두 버전을 모두 저장 후 사용자에게 선택 요청

4️⃣ 사용자 알림: "Alice와 Bob이 동시에 수정했습니다. 버전을 선택하세요"

```
공통 조상: v3 (비행기 탑승 전 마지막 동기화)
Alice 수정: 1페이지 수정
Bob 수정: 3페이지 수정
→ 1페이지와 3페이지 모두 다름: 3-way merge 성공, 자동 병합

Alice 수정: 2페이지 결론 → "매출 증가"
Bob 수정: 2페이지 결론 → "매출 감소"
→ 같은 위치 충돌: 두 버전 모두 보존, 사용자 판단 요청
```

### 시나리오 3: 랜섬웨어가 계정의 모든 파일을 암호화

**발생 상황**: 사용자 PC에 랜섬웨어가 감염되어 Drive 동기화 폴더의 모든 파일을 암호화한 후, 암호화된 파일을 Drive에 동기화했습니다.

**나쁜 설계**: 실시간 동기화 → 모든 파일이 암호화된 버전으로 덮어써지고 이전 버전은 삭제됨

**올바른 설계 (다층 방어)**:

1️⃣ **버전 이력 보존**: 최소 30일 이전 버전 자동 보관 → 감염 전 버전으로 롤백 가능

2️⃣ **이상 탐지**: 단시간에 대량 파일이 변경되면 자동 동기화 일시 중단

```python
def check_ransomware_pattern(user_id, changes_in_last_minute):
    # 1분에 100개 이상 파일이 변경되면 경고
    if len(changes_in_last_minute) > 100:
        suspend_sync(user_id)
        notify_user(user_id, "비정상적인 파일 변경이 감지되었습니다")
        return True

    # 엔트로피 기반 탐지: 암호화된 파일은 엔트로피가 높음
    for change in changes_in_last_minute:
        if calculate_entropy(change.new_blocks) > 7.9:  # 최대 8.0
            flag_for_review(change)
```

3️⃣ **격리된 스냅샷**: Cold 계층의 스냅샷은 read-only, 앱에서 직접 삭제 불가

4️⃣ **복구 절차**: 감염 시점 이전 버전을 대량 롤백하는 관리 도구 제공

---

## 13. 면접 포인트 5가지

### 1. "왜 블록을 4MB로 쪼개나요? 1KB나 100MB는 안 되나요?"

**답변 핵심**: 블록 크기는 **메타데이터 오버헤드 vs 재전송 비용의 트레이드오프**입니다.

- **너무 작게 (1KB)**: 블록 수가 폭발적 증가 → `version_blocks` 테이블에 수백만 행 → 메타데이터 DB 병목
- **너무 크게 (100MB)**: 네트워크 끊김 시 재전송 비용이 큼, 작은 파일 변경에도 전체 블록 재업로드
- **4MB**: Google Drive, Dropbox가 실제로 사용하는 값. 1GB 파일 = 256블록 (메타데이터 관리 가능), 재전송 비용도 수용 가능한 수준

### 2. "메타데이터 DB로 왜 MySQL인가요? NoSQL이 낫지 않나요?"

**답변 핵심**: 파일 시스템은 **폴더 계층 구조와 권한 검사**에 복잡한 조인이 필요합니다.

- 권한 체인 조회 (파일 → 부모 폴더 → 상위 폴더 순서로 권한 상속 확인)는 트랜잭션과 조인이 필수
- 블록의 `ref_count` 업데이트는 **ACID 트랜잭션** 없이는 경쟁 조건 발생
- 결론: 메타데이터는 MySQL, 실제 블록 데이터는 S3 (NoSQL의 장점) — **용도에 맞게 분리**

### 3. "중복 제거를 서버 사이드에서 하면 개인정보 문제가 있지 않나요?"

**답변 핵심**: **Client-side deduplication vs Server-side deduplication** 트레이드오프입니다.

- 서버 사이드: 블록을 받기 전에 해시만으로 "이미 있다"고 판단 → 악의적 사용자가 해시값만 알면 실제 파일을 업로드하지 않고도 다운로드 가능 (Proof-of-Ownership 문제)
- 해결책: 서버가 "해시가 있어도 이 사용자가 파일을 실제로 소유하는지" 별도 검증 후 중복 처리 (Challenge-Response)
- E2E 암호화 시 같은 파일도 사용자마다 다른 키로 암호화되어 해시가 달라짐 → 서버 사이드 중복 제거 불가

### 4. "파일 버전이 30개 쌓이면 어떻게 스토리지를 관리하나요?"

**답변 핵심**: **블록 공유 + 만료 정책**의 조합입니다.

- 버전 간 공통 블록은 공유되므로 실제 추가 저장 공간은 변경된 블록뿐
- 예: 10MB 문서를 30번 저장해도 매번 1%만 수정했다면 추가 저장: 10MB × 1% × 30 = 3MB
- 오래된 버전은 자동 삭제 정책으로 스토리지 상한 설정
- 유료 플랜은 더 많은 버전 이력 제공 (수익화 전략과 연결)

### 5. "동기화 클라이언트가 서버 변경을 어떻게 감지하나요? 폴링은 낭비 아닌가요?"

**답변 핵심**: **SSE + 델타 동기화**의 조합이 정답입니다.

- SSE 연결 유지 상태에서 서버가 "파일 ID X가 버전 7로 바뀌었다"는 이벤트만 푸시
- 클라이언트는 해당 파일의 메타데이터만 조회 → 변경된 블록 목록 확인 → 바뀐 블록만 다운로드
- 전체 폴더를 주기적으로 폴링하는 것 대비 트래픽을 **95% 이상 절감**
- 클라이언트가 오프라인 상태였다가 돌아오면 "마지막 동기화 이후 변경된 파일 목록" API로 일괄 처리

---

## 14. 실무에서 자주 하는 실수

### 실수 1: 파일 경로를 하드코딩

`/user/12345/documents/report.pdf` 방식으로 경로를 스토리지 키로 사용하면, 파일 이름 변경이나 폴더 이동 시 스토리지 객체를 실제로 이동해야 합니다. 블록 단위 저장에서는 경로와 스토리지 키를 분리해야 합니다. 경로는 메타데이터 DB에만 존재하고, 스토리지 키는 `SHA-256 해시`입니다.

### 실수 2: 버전 삭제 시 즉시 블록 삭제

여러 파일 버전이 같은 블록을 참조할 수 있습니다. 한 버전을 삭제할 때 즉시 블록을 지우면 다른 버전이 손상됩니다. 반드시 `ref_count` 기반 가비지 컬렉션을 사용해야 합니다.

### 실수 3: 공유 링크에 만료 시각 미설정

만료되지 않는 공유 링크는 한 번 유출되면 영구적으로 접근 가능합니다. 기본 만료는 7일로 설정하고, 사용자가 연장할 수 있도록 해야 합니다.

### 실수 4: 업로드 QPS와 다운로드 QPS를 같게 설계

다운로드는 업로드보다 10-50배 많습니다. 읽기 경로(CDN, 블록 스토리지 읽기 복제)를 쓰기 경로와 독립적으로 스케일 아웃해야 합니다.

### 실수 5: 메타데이터 DB를 단일 인스턴스로 운영

메타데이터 DB는 모든 파일 조회, 권한 확인, 블록 목록 조회의 단일 진입점입니다. 읽기 복제(Read Replica)를 두고, 핫 데이터(최근 파일, 공유 파일)는 Redis에 캐시해야 합니다.

---

### 꼭 직접 만들어야 하는가? — Build vs Buy

| 선택지 | 장점 | 단점 | 적합한 시점 |
|--------|------|------|-----------|
| Google Drive / Dropbox API | 사용자 파일을 그쪽에 저장, 인프라 불필요 | 파일 처리 파이프라인 커스텀 불가, 비즈니스 데이터 외부 의존 | Phase 1 |
| AWS S3 + CloudFront | 스토리지만 위임, 메타데이터는 자체 관리, 안정적 내구성 | 파일 변환·썸네일 등 추가 처리 서비스 별도 구성 필요 | Phase 1~3 |
| 직접 구축 (블록 스토리지 + 중복제거) | 완전한 제어, 대규모 중복제거로 비용 최적화 | 구현 복잡도 매우 높음, 전담 인프라 팀 필요 | Phase 3~4 |

**실무 판단 기준**: 파일 처리 파이프라인(변환/썸네일)이 핵심이거나, S3 비용이 월 $10K 초과 시 전환을 검토한다.

> 핵심: Phase 1에서 직접 구축하면 오버 엔지니어링이고, Phase 3에서 SaaS에 의존하면 비용 폭발이다. 현재 MAU에 맞는 선택을 하고, 병목이 실제로 발생할 때 전환한다.

---

## Day 1 → Scale 진화

### Phase 1: MAU 1만 — S3 직접 업로드 ($100/월)

파일을 S3에 통째로 업로드. 별도 블록 분할 없음. 메타데이터는 MySQL 단일 테이블. 동기화 없음(수동 다운로드). Presigned URL로 S3 직접 업로드해 서버 대역폭 절감.

```
구성: S3 + MySQL 1대 + API 서버 1대
한계: 수정 시 파일 전체 재업로드, 중단 시 처음부터 재시작, 멀티 디바이스 동기화 없음
```

### Phase 2: MAU 10만 — 메타데이터 DB + 블록 청크 ($500/월)

파일을 4MB 블록으로 분할, SHA-256 해시로 중복 제거. MySQL에 files/blocks/version_blocks 스키마. SSE로 다른 디바이스에 변경 알림 전송. 재개 가능 업로드 구현.

```
구성: S3 + MySQL (r6g.large) + Redis (SSE 연결 관리) + API 서버 3대
추가: 블록 단위 중복 제거(평균 40% 절감), 버전 이력 30일 보존
```

### Phase 3: MAU 500만 — CDC 동기화 + CDN + 티어링 ($3,000/월)

MySQL binlog CDC로 파일 변경 이벤트를 Kafka에 발행, 알림 서비스 분리. CloudFront CDN으로 인기 블록 엣지 캐싱. Hot/Warm/Cold 자동 티어링 배치 잡(7일/6개월). 읽기 복제본 추가.

```
구성: S3 + MySQL Primary/Replica + Kafka + CDN + Redis Cluster
추가: 티어링으로 스토리지 비용 60% 절감, CDN 히트율 70%+, 랜섬웨어 이상 탐지
```

### Phase 4: MAU 1억 이상 — 멀티 리전 + 글로벌 동기화 ($20,000+/월)

사용자 거주 리전에 데이터 저장(GDPR 준수). 리전 간 블록 복제는 변경된 블록만(델타 동기화). 글로벌 메타데이터는 분산 DB(CockroachDB/Spanner). E2E 암호화 기본 제공.

```
구성: 멀티 리전 S3 + 글로벌 분산 MySQL + 리전별 CDN + E2E 암호화 키 관리
추가: 리전별 데이터 레지던시, 크로스 리전 동기화 지연 < 30초, 99.999999999% 내구성
```

---

## 핵심 운영 메트릭 5개

| 메트릭 | 정상 | 경고 | 장애 | 의미 |
|--------|------|------|------|------|
| 업로드 성공률 | > 99.9% | 99~99.9% | < 99% | S3 가용성 또는 네트워크 문제 — 사용자 데이터 손실 위험 |
| 동기화 지연 (SSE 이벤트 → 클라이언트 반영) | < 3초 | 3~30초 | > 30초 | Kafka 적체 또는 알림 서비스 과부하 |
| 중복 제거율 | > 35% | 20~35% | < 20% | 블록 해시 계산 오류 또는 파일 패턴 변화 |
| 스토리지 비용/GB | 기준선 ±10% | +10~30% | +30% 이상 | 티어링 배치 실패 또는 GC 잡 중단으로 zombie 블록 누적 |
| API P99 응답시간 (메타데이터 조회) | < 50ms | 50~200ms | > 200ms | MySQL 슬로우 쿼리 또는 인덱스 누락 |

---

## 실제 장애 사례

### 사례 1: Dropbox 동기화 충돌 대규모 사고 (2014년)

**상황**: Dropbox가 데스크톱 클라이언트 버전을 업데이트하던 중, 특정 조건에서 로컬 파일과 서버 파일을 비교하는 로직에 버그가 발생했다. 수백만 명의 사용자 컴퓨터에서 정상 파일이 "서버 버전보다 오래됨"으로 잘못 판단되어 서버의 빈 파일 또는 이전 버전으로 덮어쓰기가 발생했다.

**원인**: 클라이언트가 파일 수정 시각(mtime)을 기준으로 "어느 쪽이 최신인가"를 판단하는 LWW 로직에서 타임존 처리 버그가 있었다. 일부 OS에서 mtime이 UTC가 아닌 로컬 타임으로 기록되어 비교 오류가 발생. 클라이언트 업데이트가 수백만 대에 동시 배포된 직후 수십만 건의 잘못된 덮어쓰기가 동시에 발생했다.

**해결**: 클라이언트 업데이트를 즉시 롤백. 버전 이력 시스템을 통해 대부분의 사용자 파일을 이전 버전으로 복구. 일부 버전 이력 보존 기간을 초과한 파일은 복구 불가. 이후 mtime 비교 대신 서버 측 벡터 클록 기반 충돌 감지로 전환.

**교훈**: LWW 로직에 타임스탬프를 사용할 때 타임존·클럭 스큐를 반드시 고려해야 한다. 클라이언트 업데이트는 1%→10%→100% 단계적 카나리 배포로 영향 범위를 제한해야 한다. 버전 이력은 충돌 복구의 최후 방어선이므로 보존 기간을 충분히 길게 설정해야 한다.

---

### 사례 2: GitHub 10시간 장애 — 스토리지 동기화 분기 (2018년)

**상황**: 2018년 10월 21일, GitHub이 미국 동부 데이터센터에서 네트워크 장비 교체 중 11초간 연결이 끊겼다. 이 11초 동안 MySQL 클러스터가 Primary-Primary 분기 상태(split-brain)에 빠졌다. 두 개의 MySQL 인스턴스가 각자 다른 쓰기를 받았고, 24시간 이상에 걸쳐 데이터를 복구하는 동안 GitHub은 대부분의 쓰기 기능을 정지했다. 전체 장애 시간은 약 10시간.

**원인**: Orchestrator(MySQL 페일오버 도구)가 11초 연결 끊김을 "Primary 장애"로 판단해 새 Primary를 자동 선출했다. 실제 Primary가 복구되자 두 Primary가 동시에 존재하는 split-brain 상태가 됐다. 파일 메타데이터와 Git 오브젝트 스토리지가 서로 다른 상태를 가리키게 됐다.

**해결**: 두 MySQL 상태를 비교해 분기 시점 이후의 쓰기를 수동으로 식별. 약 96초분의 커밋 데이터를 백업에서 복원. GitHub은 이후 Raft 기반 합의 알고리즘을 도입해 네트워크 순단이 자동 페일오버를 트리거하지 않도록 임계값을 높이고, 사람의 승인 없이는 Primary 전환이 일어나지 않도록 변경했다.

**교훈**: 자동 페일오버 임계값은 "정말 죽었을 때만 전환"되도록 충분히 길게 설정해야 한다. 11초 네트워크 순단은 실제로는 흔한 일이다. Split-brain 감지와 자동 차단 로직이 없으면 자동 페일오버가 오히려 장애를 악화시킨다. 데이터베이스 분기는 단순 재시작으로 복구되지 않으므로 정기적인 split-brain 시나리오 훈련이 필요하다.

---

## 실무에서 놓치기 쉬운 케이스

### 1. 대용량 파일 재개 가능 업로드 — 10GB 파일이 9.9GB에서 끊기면?

단일 HTTP PUT으로 10GB 파일을 올리면 네트워크 순단 한 번에 처음부터 다시 시작해야 한다. 모바일 환경이나 불안정한 인터넷에서는 업로드 자체가 불가능해진다.

S3 Multipart Upload 방식이 표준이다.

```
1단계: InitiateMultipartUpload
  → S3: POST /bucket/key?uploads
  → 응답: uploadId = "abc123"

2단계: 파트 업로드 (병렬 가능, 각 파트 최소 5MB)
  → PUT /bucket/key?partNumber=1&uploadId=abc123  (파트 1: 0~5GB)
  → PUT /bucket/key?partNumber=2&uploadId=abc123  (파트 2: 5~10GB)
  → 각 파트 업로드 성공 시 ETag 저장

3단계: CompleteMultipartUpload
  → POST /bucket/key?uploadId=abc123  (ETag 목록 포함)
  → S3가 파트를 합쳐 최종 파일 생성

재개 시: ListParts로 완료된 파트 조회 → 미완성 파트부터 재시작
```

클라이언트는 완료된 파트 번호와 ETag를 로컬(IndexedDB 또는 서버 DB)에 저장한다. 재접속 시 `ListParts`로 S3에 완료된 파트를 확인하고 남은 파트만 업로드한다. 7일 이상 완료되지 않은 Multipart Upload는 S3 Lifecycle Policy로 자동 삭제해 스토리지 비용을 막는다.

---

### 2. 공유 링크 유출 — "링크가 있으면 누구나"의 함정

Dropbox나 Google Drive의 "링크 있는 사람 모두 접근 가능" 옵션은 편리하지만, 링크가 SNS·이메일·Slack에 노출되면 의도치 않은 사람이 접근한다. 특히 기업 내부 문서가 공개 공유 링크로 유출되는 사고가 빈번하다.

```python
def generate_share_link(file_id, user_id, expires_hours=72):
    token = secrets.token_urlsafe(32)  # 암호학적으로 안전한 난수
    db.execute("""
        INSERT INTO share_links
          (token, file_id, created_by, expires_at, max_views)
        VALUES (%s, %s, %s, NOW() + INTERVAL %s HOUR, %s)
    """, (token, file_id, user_id, expires_hours, 100))

    return f"https://storage.example.com/share/{token}"

def access_share_link(token, requester_ip):
    link = db.fetchone("SELECT * FROM share_links WHERE token=%s", (token,))
    if not link or link["expires_at"] < now():
        raise Forbidden("링크가 만료됐거나 존재하지 않습니다")
    if link["view_count"] >= link["max_views"]:
        raise Forbidden("최대 조회 횟수를 초과했습니다")

    db.execute("UPDATE share_links SET view_count=view_count+1 WHERE token=%s", (token,))
    audit_log(token, requester_ip)  # 접근 기록 필수
    return get_file(link["file_id"])
```

공유 링크는 만료 시각, 최대 조회 횟수, 특정 도메인(회사 이메일) 제한 중 하나 이상을 적용해야 한다. 기업용 서비스에서는 공유 링크 생성 자체를 관리자가 비활성화할 수 있는 정책 설정이 필수다.

---

### 3. 바이러스 파일 스캐닝 — 악성코드가 업로드되면 다른 사용자에게 전파된다

파일 저장소는 악성코드 유포 경로로 자주 악용된다. 업로드된 ZIP 파일 안에 랜섬웨어 실행 파일이 들어 있거나, PDF에 자바스크립트 익스플로잇이 숨겨져 있을 수 있다.

```
업로드 파이프라인:
  클라이언트 → API Gateway → S3 임시 버킷(quarantine/)
                                    ↓
                          ClamAV / VirusTotal API 스캔 (비동기)
                                    ↓
                    ┌───────────────┴───────────────┐
                  정상                            악성 탐지
                    ↓                                ↓
            S3 정식 버킷으로 이동           quarantine/ 유지 + 알림
            메타데이터 DB 업데이트          파일 소유자에게 경고 이메일
            사용자에게 업로드 완료 알림      보안팀 Slack 알림
```

스캔 완료 전까지 파일은 `quarantine/` 버킷에 격리된다. 사용자에게는 "업로드 중" 상태로 표시하고, 스캔 완료(보통 5~30초) 후 접근 가능 상태로 전환한다. 대용량 파일은 스캔 시간이 수 분 이상 걸릴 수 있으므로 Kafka를 통한 비동기 처리가 필수다. SHA-256 해시 기반 캐시를 두면 동일 파일은 재스캔 없이 이전 결과를 재사용할 수 있다.

---

## 마무리: 설계의 핵심 원칙

분산 파일 저장소 설계에서 배울 수 있는 세 가지 핵심 원칙을 정리합니다.

첫째, **데이터를 콘텐츠 기반으로 식별하라(Content-Addressable Storage)**. 파일 이름이나 경로 대신 내용의 해시를 주소로 사용하면, 중복 제거·무결성 검증·캐시 최적화가 자연스럽게 따라옵니다.

둘째, **메타데이터와 실제 데이터를 분리하라**. 조회 패턴이 다른 두 종류의 데이터를 같은 저장소에 넣으면 둘 다 최적화하기 어렵습니다. 메타데이터는 RDBMS, 블록은 오브젝트 스토리지로 역할을 명확히 분리해야 합니다.

셋째, **실패를 가정하고 설계하라**. 네트워크는 끊어지고, 동시 편집은 충돌하고, 랜섬웨어는 존재합니다. 이 모든 상황에서 데이터를 보호하려면 재개 가능 업로드, 버전 이력, 이상 탐지가 선택이 아닌 필수입니다.

---
## 실무에서 자주 하는 실수

**실수 1: 업로드 완료 전 메타데이터 먼저 커밋**
파일 업로드를 시작하자마자 DB에 `status=uploading`으로 메타데이터를 저장하고, 업로드 중 클라이언트 연결이 끊기면 고아 레코드가 남습니다. 이 상태에서 동일 파일명으로 재업로드하면 중복 처리 로직이 없으면 두 개의 레코드가 생깁니다. 올바른 흐름: S3 멀티파트 업로드 `CompleteMultipartUpload` 성공 후 DB 커밋. 업로드 실패 시 S3 Lifecycle Rule로 미완성 파트 24시간 후 자동 삭제.

```java
// 업로드 완료 후 메타데이터 저장 (원자성 보장)
public FileMetadata completeUpload(String uploadId, List<CompletedPart> parts) {
    // 1. S3 멀티파트 완료
    s3Client.completeMultipartUpload(
        CompleteMultipartUploadRequest.builder()
            .bucket(bucket).key(uploadId)
            .multipartUpload(b -> b.parts(parts))
            .build()
    );
    // 2. S3 성공 확인 후에만 DB 저장
    return metadataRepository.save(new FileMetadata(uploadId, FileStatus.COMPLETED));
}
```

**실수 2: 블록 해시를 MD5로 계산해 중복 판별**
MD5는 해시 충돌이 실제로 발생할 수 있어 두 다른 블록이 같은 해시를 가질 수 있습니다. 결과적으로 A 사용자의 파일 블록이 B 사용자 파일에 사용됩니다. SHA-256 사용이 기본이며, 2025년 기준으로 충돌 공격이 이론적으로도 가능하지 않습니다. 블록 크기 4MB 기준 SHA-256 계산 비용은 CPU ~2ms로 무시 가능합니다.

**실수 3: 동기화 이벤트를 Polling으로 처리**
클라이언트가 2초마다 `/changes?since=timestamp`를 폴링하면, 10만 명 동시 접속 시 초당 5만 건의 DB 쿼리가 발생합니다. Dropbox 초기 아키텍처의 실제 병목이었습니다. WebSocket 또는 SSE(Server-Sent Events)로 서버 푸시 방식을 사용하고, 변경 이벤트를 Redis Pub/Sub 또는 Kafka로 분산해야 합니다.

**실수 4: 파일 버전을 전체 복사로 저장**
1GB 파일의 1KB만 수정해도 새 버전을 전체 1GB로 저장하면 버전 10개 = 10GB. Delta 방식(변경된 블록만 저장)이 필수입니다. 블록 단위 저장의 핵심 장점이 바로 이 Delta 업데이트입니다. 버전 복원 시에는 해당 버전의 블록 목록을 조회해 재조합합니다.

---
## 면접 포인트

### Q1. 대용량 파일 업로드 시 Presigned URL을 쓰는 이유는?
클라이언트 → 앱서버 → S3 경로는 앱서버가 파일 데이터를 중계해 불필요한 네트워크 이중 전송과 앱서버 메모리 사용이 발생합니다. Presigned URL을 사용하면 클라이언트가 S3로 직접 업로드하므로 앱서버 부하 제거. 10GB 파일 업로드 시 앱서버 메모리 절감 효과는 직접적입니다. URL 만료 시간은 업로드 예상 시간 + 여유분(예: 4GB 파일은 15분 TTL)으로 설정합니다.

### Q2. 청크 크기를 얼마로 설정하는가?
너무 작으면(1MB) HTTP 요청 오버헤드가 증가합니다. 너무 크면(100MB) 재시도 시 손실 데이터가 커집니다. 실무 권장값: 4~8MB. AWS S3 멀티파트 최소값은 5MB입니다. 네트워크 대역폭이 낮은 모바일 환경에서는 1MB로 동적 조정하는 것이 UX에 유리합니다.

### Q3. 파일 공유 권한 설계는?
행 레벨 권한(Row-Level Security)이 기본입니다. `file_permissions(file_id, user_id, permission_level)` 테이블에 읽기/쓰기/소유자를 저장하고, 링크 공유는 별도 `share_tokens(token, file_id, expires_at, permission)` 테이블로 관리합니다. 폴더 권한은 하위 항목에 상속되므로, 조회 시 부모 체인을 순회해야 합니다. 재귀 쿼리 또는 경로 열거(Materialized Path) 패턴을 사용합니다.

### Q4. 파일 삭제 후 스토리지 회수는 어떻게 하는가?
파일 삭제 즉시 S3에서 블록을 삭제하면 같은 블록을 공유하는 다른 사용자 파일이 손상됩니다. 레퍼런스 카운팅이 필요합니다. `block_references(block_hash, ref_count)` 테이블에서 `ref_count`가 0이 될 때 S3 삭제 작업을 Kafka에 발행하고 비동기로 처리합니다. Soft Delete → ref_count 감소 → 0이면 S3 삭제 예약 → 24시간 후 실제 삭제(복구 기간 확보).

### Q5. 동시 편집 충돌 해결 전략은?
Google Docs는 OT(Operational Transformation)를 사용하지만 구현이 매우 복잡합니다. Dropbox 같은 파일 기반 시스템은 LWW(Last-Write-Wins)와 충돌 복사본 생성을 조합합니다. 서버 타임스탬프 기준으로 나중 쓰기가 승리하고, 기존 버전은 `file_conflict_copy_2026-05-07.docx`로 저장됩니다. 사용자가 수동 병합합니다. 실시간 협업이 필요하면 CRDT(Conflict-Free Replicated Data Type) 기반 라이브러리(Yjs, Automerge)를 사용합니다.
