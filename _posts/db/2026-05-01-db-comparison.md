---
title: "데이터베이스 종류별 비교 분석 (MySQL vs PostgreSQL vs Oracle vs MariaDB vs SQL Server)"
categories:
- DB
toc: true
toc_sticky: true
toc_label: 목차
---

## 1. 개요

### 1.1 RDBMS 시장 현황

관계형 데이터베이스 관리 시스템(RDBMS)은 수십 년간 데이터 저장의 근간을 이루어 왔다. 2024년 기준 DB-Engines 랭킹 기준 상위 RDBMS는 Oracle, MySQL, SQL Server, PostgreSQL, MariaDB 순이다. NoSQL의 성장에도 불구하고 RDBMS는 여전히 전체 데이터베이스 시장의 60% 이상을 차지하며, 특히 금융, 제조, 공공 부문에서 압도적인 점유율을 유지한다.

클라우드 전환 이후 Amazon Aurora, Google Cloud SQL, Azure Database 등 매니지드 서비스가 급성장하면서 설치형(on-premise) RDBMS의 운영 부담이 크게 줄었고, 이로 인해 오픈소스 RDBMS(MySQL, PostgreSQL)의 채택률이 더욱 높아졌다.

### 1.2 각 DB의 역사와 라이선스

| 데이터베이스 | 최초 출시 | 개발사/관리 주체 | 라이선스 |
|---|---|---|---|
| **MySQL** | 1995 | Oracle Corporation | GPL v2 / 상용 이중 라이선스 |
| **PostgreSQL** | 1996 (Postgres 1986) | PostgreSQL Global Development Group | PostgreSQL License (BSD 계열) |
| **Oracle Database** | 1979 | Oracle Corporation | 상용 (Enterprise/Standard) |
| **MariaDB** | 2009 | MariaDB Foundation / MariaDB plc | GPL v2 |
| **SQL Server** | 1989 | Microsoft | 상용 (Express 무료 제한판 있음) |

**MySQL** 은 1995년 스웨덴의 MySQL AB가 개발하였고, 2008년 Sun Microsystems, 2010년 Oracle이 인수하였다. GPL v2 라이선스이지만 상용 라이선스를 별도 판매하는 이중 라이선스 구조이다.

**PostgreSQL** 은 UC Berkeley의 POSTGRES 프로젝트(1986)에서 출발하여 1996년 현재의 이름으로 공개되었다. BSD 계열의 PostgreSQL License로 배포되어 수정·재배포·상업적 이용이 매우 자유롭다.

**Oracle Database** 는 최초의 상용 RDBMS 중 하나로 Larry Ellison이 1977년 설립한 SDL(현 Oracle)이 개발하였다. 현재까지도 엔터프라이즈 시장에서 점유율 1위를 유지하며 가장 고가의 RDBMS이다.

**MariaDB** 는 Oracle의 MySQL 인수 이후 MySQL 공동 창업자 Monty Widenius가 MySQL 5.1을 fork하여 2009년 출시하였다. MySQL과 높은 호환성을 유지하면서 독자적인 스토리지 엔진(Aria, ColumnStore 등)을 추가하였다.

**SQL Server** 는 Microsoft가 Sybase와 공동 개발하여 1989년 출시하였다. 2016년부터 Linux 지원이 추가되었고, Azure SQL Database로 클라우드 서비스도 제공한다.

---

## 2. 아키텍처 비교

### 2.1 전체 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────────┐
│                    RDBMS 계층 구조 비교                              │
├─────────────┬─────────────┬─────────────┬─────────────┬────────────┤
│   MySQL     │ PostgreSQL  │   Oracle    │  MariaDB    │ SQL Server │
├─────────────┼─────────────┼─────────────┼─────────────┼────────────┤
│ Client Conn │ Client Conn │ Client Conn │ Client Conn │ Client Conn│
│ Thread Pool │ Process per │ Dedicated/  │ Thread Pool │ Thread Pool│
│             │ Connection  │ Shared Srv  │             │            │
├─────────────┼─────────────┼─────────────┼─────────────┼────────────┤
│ Query Cache │ Query Plan  │ Library     │ Query Cache │ Plan Cache │
│ (deprecated)│ Cache       │ Cache       │ (optional)  │            │
├─────────────┼─────────────┼─────────────┼─────────────┼────────────┤
│  Parser /   │  Parser /   │  Parser /   │  Parser /   │  Parser /  │
│  Optimizer  │  Optimizer  │  Optimizer  │  Optimizer  │  Optimizer │
├─────────────┼─────────────┼─────────────┼─────────────┼────────────┤
│  InnoDB /   │  Heap-based │  Tablespace │  InnoDB /   │  Extent-   │
│  MyISAM 등  │  Storage    │  Storage    │  Aria 등    │  based     │
│  (플러그인) │             │             │  (플러그인) │  Storage   │
├─────────────┼─────────────┼─────────────┼─────────────┼────────────┤
│ Buffer Pool │Shared Buffer│  SGA / PGA  │ Buffer Pool │Buffer Pool │
│             │             │ (Buffer     │             │            │
│             │             │  Cache)     │             │            │
└─────────────┴─────────────┴─────────────┴─────────────┴────────────┘
```

### 2.2 스토리지 엔진

#### InnoDB (MySQL / MariaDB)

InnoDB는 MySQL의 기본 스토리지 엔진으로 클러스터드 인덱스(Clustered Index)를 사용한다. Primary Key 순서로 데이터가 물리적으로 정렬되어 저장되며, 모든 Secondary Index는 Primary Key 값을 포함한다.

```
InnoDB 파일 구조:
┌──────────────────────────────────────────────┐
│  ibdata1 (System Tablespace)                 │
│  ├── Data Dictionary                         │
│  ├── Undo Logs (undo tablespace 분리 가능)   │
│  └── Double Write Buffer                     │
├──────────────────────────────────────────────┤
│  table.ibd (Per-Table Tablespace)            │
│  ├── Leaf Pages (실제 행 데이터)             │
│  └── Non-Leaf Pages (인덱스 노드)            │
├──────────────────────────────────────────────┤
│  ib_logfile0, ib_logfile1 (Redo Log)         │
└──────────────────────────────────────────────┘
```

#### PostgreSQL Heap 구조

PostgreSQL은 힙(Heap) 기반으로 데이터를 저장한다. 테이블 파일은 8KB 페이지(블록)로 구성되며, 인덱스와 테이블이 완전히 분리된 구조이다. MVCC를 위해 동일 테이블 내에 여러 버전의 튜플을 함께 저장한다.

```
PostgreSQL 파일 구조:
PGDATA/
├── base/
│   └── {db_oid}/
│       ├── {relation_oid}       ← 테이블 힙 파일
│       ├── {relation_oid}_fsm   ← Free Space Map
│       ├── {relation_oid}_vm    ← Visibility Map
│       └── {index_oid}          ← 인덱스 파일
├── pg_wal/                      ← WAL (Write-Ahead Log)
├── pg_undo/                     ← (없음, 힙 내 버전 관리)
└── global/                      ← 공유 시스템 카탈로그
```

#### Oracle Tablespace

Oracle은 테이블스페이스(Tablespace) → 세그먼트(Segment) → 익스텐트(Extent) → 데이터 블록(Data Block)의 4단계 계층 구조로 저장 공간을 관리한다.

```
Oracle 스토리지 계층:
Tablespace (논리)
└── Segment (테이블, 인덱스, Undo 등)
    └── Extent (연속된 블록 집합)
        └── Oracle Block (2KB~32KB, 기본 8KB)
            ├── Block Header
            ├── Table Directory
            ├── Row Directory
            └── Row Data (가변)
```

### 2.3 프로세스 모델

```
프로세스/스레드 모델 비교:

MySQL / MariaDB / SQL Server:
┌─────────────────────────────────────┐
│           메인 프로세스              │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐       │
│  │ T1 │ │ T2 │ │ T3 │ │ T4 │ ...  │  ← 연결당 스레드
│  └────┘ └────┘ └────┘ └────┘       │
│  (Thread Pool로 스레드 재사용 가능)  │
└─────────────────────────────────────┘
장점: 낮은 연결 오버헤드, 공유 메모리 효율적
단점: 한 스레드 문제가 전체 프로세스에 영향

PostgreSQL:
┌────────────────────────────────────┐
│  postmaster (마스터 프로세스)       │
│    ↓ fork()                         │
│  ┌──────┐ ┌──────┐ ┌──────┐       │
│  │ Proc1│ │ Proc2│ │ Proc3│ ...   │  ← 연결당 프로세스
│  └──────┘ └──────┘ └──────┘       │
└────────────────────────────────────┘
장점: 프로세스 격리로 안정성 높음
단점: 연결 수 증가 시 메모리 사용 급증 → PgBouncer 권장

Oracle:
┌─────────────────────────────────────────┐
│  Dedicated Server Mode:                  │
│  클라이언트 1 → Server Process 1 (1:1)  │
│                                          │
│  Shared Server Mode (MTS):               │
│  클라이언트 N → Dispatcher → Shared Srv  │
│               ↓                          │
│          Request Queue                   │
│               ↓                          │
│          Shared Server 풀                │
└─────────────────────────────────────────┘
```

### 2.4 메모리 구조

#### MySQL Buffer Pool

```
MySQL InnoDB 메모리 구조:
┌─────────────────────────────────────────────┐
│              Buffer Pool                     │
│  ┌─────────────┬────────────────────────┐   │
│  │   New       │        Old             │   │
│  │ Sublist(5/8)│    Sublist(3/8)        │   │
│  │ (MRU end)   │    (LRU end)           │   │
│  └─────────────┴────────────────────────┘   │
│  ┌────────────────────────────────────────┐  │
│  │   Change Buffer (DML 변경 버퍼링)      │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │   Adaptive Hash Index                  │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │   Log Buffer (Redo Log 버퍼)           │  │
│  └────────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

- `innodb_buffer_pool_size`: 전체 메모리의 70~80% 권장
- 여러 인스턴스(innodb_buffer_pool_instances)로 분할하여 경합 감소 가능

#### PostgreSQL Shared Buffers

```
PostgreSQL 메모리 구조:
┌─────────────────────────────────────────────┐
│  Shared Memory (전체 프로세스 공유)          │
│  ┌────────────────────────────────────────┐  │
│  │   Shared Buffers (기본 128MB)          │  │
│  │   ← 전체 RAM의 25% 권장               │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │   WAL Buffers                          │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │   Lock Table, Proc Array               │  │
│  └────────────────────────────────────────┘  │
├─────────────────────────────────────────────┤
│  Per-Process Memory (프로세스별)             │
│  ┌────────────────────────────────────────┐  │
│  │   work_mem (정렬/해시 조인용)          │  │
│  │   maintenance_work_mem (VACUUM 등)     │  │
│  └────────────────────────────────────────┘  │
├─────────────────────────────────────────────┤
│  OS Page Cache (나머지 RAM)                  │
│  ← PostgreSQL은 OS 캐시를 적극 활용함       │
└─────────────────────────────────────────────┘
```

#### Oracle SGA / PGA

```
Oracle 메모리 구조:
┌──────────────────────────────────────────────────┐
│  SGA (System Global Area) — 인스턴스 전체 공유   │
│  ┌──────────────────────────────────────────────┐ │
│  │  Database Buffer Cache (데이터 블록 캐시)    │ │
│  ├──────────────────────────────────────────────┤ │
│  │  Shared Pool                                 │ │
│  │  ├── Library Cache (파싱된 SQL, PL/SQL)      │ │
│  │  └── Data Dictionary Cache (Row Cache)       │ │
│  ├──────────────────────────────────────────────┤ │
│  │  Redo Log Buffer                             │ │
│  ├──────────────────────────────────────────────┤ │
│  │  Large Pool (병렬 쿼리, RMAN 등)             │ │
│  ├──────────────────────────────────────────────┤ │
│  │  Java Pool, Streams Pool                     │ │
│  └──────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────┤
│  PGA (Program Global Area) — 서버 프로세스별     │
│  ┌──────────────────────────────────────────────┐ │
│  │  Sort Area, Hash Area                        │ │
│  │  Session Info, Cursor State                  │ │
│  └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

---

## 3. MVCC 구현 차이

MVCC(Multi-Version Concurrency Control)는 읽기와 쓰기가 서로를 차단하지 않도록 여러 버전의 데이터를 유지하는 방식이다.

### 3.1 MySQL/InnoDB — Undo Log 기반

InnoDB의 MVCC는 Undo Log를 참조하는 방식이다. 실제 테이블 페이지에는 최신 버전만 저장되고, 이전 버전은 Undo Log에 보관된다.

```
InnoDB MVCC 동작 원리:

테이블 페이지 (최신 데이터):
┌──────────────────────────────────────────┐
│ Row: id=1, name='Kim', DB_TRX_ID=100    │
│      DB_ROLL_PTR ──────────────────────►│──┐
└──────────────────────────────────────────┘  │
                                              │
Undo Log Segment:                            │
┌──────────────────────────────────────────┐ │
│ TRX_ID=100 이전 버전: name='Lee'  ◄──────┘ │
│ DB_ROLL_PTR ───────────────────────────►│──┐
└──────────────────────────────────────────┘  │
┌──────────────────────────────────────────┐  │
│ TRX_ID=90 이전 버전: name='Park'  ◄──────┘  │
└──────────────────────────────────────────┘

Read View (트랜잭션 시작 시 생성):
- 현재 활성 트랜잭션 목록 스냅샷
- 자신의 트랜잭션 ID보다 큰 TRX_ID는 무시
- Undo Chain을 역방향으로 따라가며 가시적 버전 탐색
```

**장점:**
- 최신 데이터가 테이블 페이지에 있어 현재 읽기 성능이 좋음
- Undo Log 파일 관리가 명확함

**단점:**
- 오래된 트랜잭션이 살아 있으면 Undo Log가 무한정 증가 가능
- Long-running transaction은 심각한 성능 저하 유발

### 3.2 PostgreSQL — Tuple Versioning

PostgreSQL은 Undo Log 없이 테이블 힙 자체에 모든 버전을 저장한다. 각 튜플(행)에 `xmin`/`xmax` 트랜잭션 ID를 기록하여 가시성을 판별한다.

```
PostgreSQL Tuple Versioning:

테이블 힙 페이지 (여러 버전 공존):
┌─────────────────────────────────────────────────────────┐
│ Page Header                                              │
├──────────┬──────────────────────────────────────────────┤
│ ItemID 1 │ Tuple: xmin=90, xmax=100, name='Park'        │
│          │ (TRX 100이 삭제/갱신 → 더 이상 유효하지 않음) │
├──────────┼──────────────────────────────────────────────┤
│ ItemID 2 │ Tuple: xmin=100, xmax=0(살아있음), name='Kim'│
│          │ (현재 유효한 버전)                            │
└──────────┴──────────────────────────────────────────────┘

가시성 규칙:
- xmin < 내 Snapshot XID AND xmax = 0  → 보임 (현재 유효)
- xmin < 내 Snapshot XID AND xmax > 내 Snapshot → 보임 (삭제됐지만 내 기준엔 유효)
- xmin >= 내 Snapshot XID             → 안 보임 (내 이후 삽입)
```

**VACUUM의 역할:**

오래된 버전 튜플(Dead Tuple)은 VACUUM이 회수할 때까지 디스크에 남는다. 이로 인해 테이블 파일이 비대해지는 "Table Bloat" 문제가 발생할 수 있다.

```
VACUUM 동작:
1. Dead Tuple 스캔 (xmax가 완료된 트랜잭션 ID인 튜플)
2. Visibility Map 업데이트
3. Free Space Map 업데이트
4. 필요 시 OS에 공간 반환 (VACUUM FULL만 실제 축소)

autovacuum 파라미터:
autovacuum_vacuum_scale_factor = 0.2  (테이블의 20% 변경 시 트리거)
autovacuum_analyze_scale_factor = 0.1
```

**장점:**
- Undo Log 별도 관리 불필요
- 충돌 없는 높은 동시성

**단점:**
- VACUUM 부하, Table Bloat 위험
- WAL 볼륨 증가 (구버전 힙이 WAL에도 기록됨)

### 3.3 Oracle — Undo Tablespace 기반

Oracle은 별도의 Undo Tablespace에 이전 버전 데이터를 저장한다. 구조적으로는 InnoDB의 Undo Log와 유사하지만 Tablespace 단위로 관리되어 더 체계적이다.

```
Oracle MVCC 구조:

Data Block (현재 버전):
┌─────────────────────────────────────────┐
│ Row: id=1, name='Kim'                   │
│ ITL (Interested Transaction List) Entry │
│ ├── XID: 0x0001.0002.00000003           │
│ └── UBA: Undo Block Address ──────────►│──┐
└─────────────────────────────────────────┘  │
                                             │
Undo Tablespace:                            │
┌─────────────────────────────────────────┐  │
│ Undo Block                              │◄─┘
│ ├── 이전 값: name='Lee'                 │
│ └── 이전 UBA (더 오래된 버전으로의 링크)│
└─────────────────────────────────────────┘
```

**Consistent Read:**
Oracle에서 SELECT는 SCN(System Change Number) 기반으로 일관성을 보장한다. 쿼리 시작 시의 SCN을 기준으로, 그보다 늦게 커밋된 변경은 Undo에서 되돌려서 읽는다.

### 3.4 MVCC 방식 종합 비교

| 항목 | MySQL/InnoDB | PostgreSQL | Oracle |
|---|---|---|---|
| 이전 버전 저장 위치 | Undo Log Segment | 테이블 힙 내부 | Undo Tablespace |
| 현재 버전 위치 | 테이블 페이지 | 테이블 힙 | 테이블 블록 |
| 가비지 수집 | Purge Thread | VACUUM | Undo 자동 만료(UNDO_RETENTION) |
| Table Bloat 위험 | 낮음 | 높음 (VACUUM 필요) | 낮음 |
| Long-running 트랜잭션 영향 | Undo 증가 | Dead Tuple 누적 | Undo 부족 오류 가능 |
| 버전 이력 관리 | 자동 | 자동 (VACUUM 주기적) | UNDO_RETENTION 설정 |

---

## 4. 인덱스 차이

### 4.1 MySQL / InnoDB 인덱스

```
InnoDB B+Tree 구조 (Clustered Index):

         Root Node
        ┌──────────┐
        │ 10 │ 50  │
        └──┬──┬────┘
       ┌───┘  └──────┐
   Internal Node   Internal Node
  ┌─────────┐      ┌─────────┐
  │  5 │ 8  │      │ 30│ 40  │
  └──┬──┬───┘      └──┬──┬───┘
     │  └──┐          │  └──┐
  Leaf  Leaf       Leaf   Leaf
  ┌────┐ ┌────┐   ┌────┐  ┌────┐
  │행1 │ │행2 │   │행3 │  │행4 │  ← 실제 행 데이터 포함
  └────┘ └────┘   └────┘  └────┘
     ↔ Doubly Linked List (범위 스캔 효율적)
```

- **Clustered Index**: PK 순으로 물리적 정렬 → PK 범위 스캔 매우 효율적
- **Secondary Index**: `(Secondary Key, PK)` 저장 → 조회 시 PK로 Clustered Index 재탐색(Double Lookup)
- **Covering Index**: Secondary Index에 필요한 컬럼 모두 포함 시 Double Lookup 회피 가능

```sql
-- Covering Index 예시
CREATE INDEX idx_name_age ON users(name, age);
-- name, age만 SELECT하면 클러스터드 인덱스 재탐색 없이 처리
SELECT name, age FROM users WHERE name = 'Kim';
```

**지원 인덱스 타입:**

| 타입 | 엔진 | 용도 |
|---|---|---|
| B+Tree | InnoDB, MyISAM | 기본, 범위/동등 검색 |
| Hash | Memory | 동등 검색만 가능, 범위 불가 |
| Full-Text | InnoDB, MyISAM | 자연어 전문 검색 |
| Spatial (R-Tree) | InnoDB, MyISAM | 지리정보 검색 |

### 4.2 PostgreSQL 인덱스

PostgreSQL은 가장 다양한 인덱스 타입을 지원하며, 사용자 정의 인덱스 타입도 추가 가능하다.

```
PostgreSQL 인덱스 타입:

B-Tree (기본):
├── 동등, 범위, 정렬 지원
└── 모든 데이터 타입에 적용 가능

Hash:
├── 동등 검색 특화 (= 연산자만)
└── WAL 로깅 (9.x까지는 크래시 복구 불안정)

GiST (Generalized Search Tree):
├── PostGIS 지리 데이터, 전문 검색
├── 범위 타입, IP 주소, 기하 도형
└── 사용자 정의 데이터 타입 지원 가능

SP-GiST (Space-Partitioned GiST):
├── Quad-Tree, K-D Tree 구현
└── 비균등 분포 데이터에 적합

GIN (Generalized Inverted Index):
├── 배열, JSONB, 전문 검색(tsvector)
├── 복합 값(composite) 빠른 검색
└── 빌드 느림, 검색 빠름

BRIN (Block Range INdex):
├── 물리적으로 정렬된 대용량 테이블
├── 타임스탬프, 시퀀셜 ID 등
├── 매우 작은 인덱스 크기
└── 시계열 데이터에 최적
```

**Partial Index** (PostgreSQL 강점):
```sql
-- NULL이 아닌 활성 사용자만 인덱싱
CREATE INDEX idx_active_users ON users(email)
WHERE is_active = TRUE AND deleted_at IS NULL;
```

**Expression Index**:
```sql
-- 소문자 변환 결과를 인덱싱
CREATE INDEX idx_lower_email ON users(lower(email));
SELECT * FROM users WHERE lower(email) = 'kim@example.com'; -- 인덱스 사용
```

### 4.3 Oracle 인덱스

| 타입 | 설명 | 적합한 경우 |
|---|---|---|
| B-Tree | 기본 인덱스, 고 카디널리티 | 대부분의 일반 쿼리 |
| Bitmap | 낮은 카디널리티 컬럼 | DW/OLAP, 성별·상태 코드 등 |
| Function-Based | 표현식 결과를 인덱싱 | `UPPER(name)` 검색 |
| Reverse Key | B-Tree 키를 뒤집어 저장 | RAC 환경의 우측 편향 방지 |
| Composite | 다중 컬럼 | 복합 조건 쿼리 |
| Index-Organized Table (IOT) | 테이블 자체가 B-Tree | PK 기반 접근이 대부분인 경우 |

**Bitmap Index 예시:**
```sql
-- Oracle Bitmap Index
CREATE BITMAP INDEX idx_gender ON users(gender);
-- 내부적으로 각 값(M/F)에 대한 비트 벡터 생성
-- AND/OR 연산이 비트 연산으로 처리되어 매우 빠름
-- 단, DML 많은 OLTP에서는 Lock 경합 심함
```

### 4.4 인덱스 타입 비교 표

| 인덱스 타입 | MySQL | PostgreSQL | Oracle | MariaDB | SQL Server |
|---|---|---|---|---|---|
| B-Tree | ✓ | ✓ | ✓ | ✓ | ✓ |
| Hash | ✓(Memory) | ✓ | - | ✓(Memory) | - |
| Clustered | ✓(InnoDB PK) | - (별도 설정) | IOT | ✓(InnoDB PK) | ✓ |
| Bitmap | - | - | ✓ | - | ✓(CS) |
| GIN/GiST | - | ✓ | - | - | - |
| BRIN | - | ✓ | - | - | - |
| Spatial | ✓ | ✓(PostGIS) | ✓ | ✓ | ✓ |
| Full-Text | ✓ | ✓ | ✓ | ✓ | ✓ |
| Function-Based | ✓(Generated) | ✓(Expression) | ✓ | ✓ | ✓(Computed) |
| Partial | - | ✓ | - | - | ✓(Filtered) |

---

## 5. 트랜잭션 / 격리 수준

### 5.1 기본 격리 수준

| 데이터베이스 | 기본 격리 수준 | 이유 |
|---|---|---|
| MySQL/InnoDB | REPEATABLE READ | Gap Lock으로 Phantom Read 방지 |
| MariaDB | REPEATABLE READ | MySQL 호환 |
| PostgreSQL | READ COMMITTED | 일반적인 OLTP 성능/안전성 균형 |
| Oracle | READ COMMITTED | 오래된 기본값 유지 |
| SQL Server | READ COMMITTED | 기본; RCSI 활성화 시 성능 향상 |

### 5.2 격리 수준별 문제 현상

```
격리 수준 계층:
                 낮음 ←────────────────────────────────→ 높음
    READ UNCOMMITTED | READ COMMITTED | REPEATABLE READ | SERIALIZABLE
         ↓                  ↓                ↓                ↓
    Dirty Read 허용    Dirty Read 없음   Non-Repeatable   Phantom 없음
    Non-Repeatable     Non-Repeatable    Read 없음         완전 직렬화
    Read 허용          Read 허용         Phantom 허용
    Phantom 허용       Phantom 허용
```

### 5.3 MySQL Gap Lock

MySQL REPEATABLE READ에서는 Gap Lock을 사용하여 Phantom Read를 방지한다. 이는 특정 범위에 삽입 자체를 막는 잠금이다.

```sql
-- 세션 1:
BEGIN;
SELECT * FROM orders WHERE amount BETWEEN 100 AND 200 FOR UPDATE;
-- Gap Lock: amount 100~200 구간에 삽입 불가 잠금

-- 세션 2 (블록됨):
INSERT INTO orders (amount) VALUES (150); -- 대기 (Gap Lock)
```

**Gap Lock 문제:**
- 데드락(Deadlock) 발생 가능성 증가
- 동시 삽입 성능 저하

**해결책:** 격리 수준을 READ COMMITTED로 낮추면 Gap Lock이 없어지지만 Phantom Read가 발생할 수 있다.

### 5.4 PostgreSQL SSI (Serializable Snapshot Isolation)

PostgreSQL은 SERIALIZABLE 격리 수준에서 SSI를 구현한다. 잠금 없이 의존성 그래프를 추적하여 직렬화 이상을 감지하면 한 트랜잭션을 롤백한다.

```
SSI 동작 예시 (Write Skew 방지):

트랜잭션 A: SELECT sum(balance) FROM accounts; -- 읽기
트랜잭션 B: SELECT sum(balance) FROM accounts; -- 읽기
트랜잭션 A: UPDATE accounts SET balance = balance - 100 WHERE id=1;
트랜잭션 B: UPDATE accounts SET balance = balance - 100 WHERE id=2;
트랜잭션 A: COMMIT;
트랜잭션 B: COMMIT; -- SSI가 의존성 사이클 감지 → 롤백

→ 실제 직렬화 이상이 감지된 경우만 롤백하므로 불필요한 잠금 없음
```

### 5.5 SQL Server RCSI

SQL Server는 기본적으로 잠금 기반이지만, Read Committed Snapshot Isolation(RCSI)을 활성화하면 tempdb에 버전을 저장하여 읽기-쓰기 충돌을 없앨 수 있다.

```sql
-- RCSI 활성화
ALTER DATABASE MyDB SET READ_COMMITTED_SNAPSHOT ON;
```

### 5.6 격리 수준 지원 비교

| 격리 수준 | MySQL | PostgreSQL | Oracle | MariaDB | SQL Server |
|---|---|---|---|---|---|
| READ UNCOMMITTED | ✓ | ✓(RC로 처리) | - | ✓ | ✓ |
| READ COMMITTED | ✓ | ✓ | ✓ | ✓ | ✓ |
| REPEATABLE READ | ✓(기본) | ✓ | - | ✓(기본) | ✓ |
| SERIALIZABLE | ✓(Lock 기반) | ✓(SSI) | ✓(Lock 기반) | ✓ | ✓ |
| Snapshot | - | ✓(기본 RR 동작) | ✓(별도 지원) | - | ✓(RCSI) |

---

## 6. 복제 방식

### 6.1 MySQL 복제

```
MySQL 복제 아키텍처:

비동기 복제 (기본):
┌──────────┐   Binary Log   ┌────────────┐
│  Source  │──────────────►│  Replica 1 │
│ (Master) │               └────────────┘
│          │──────────────►┌────────────┐
└──────────┘               │  Replica 2 │
  커밋 즉시 반환            └────────────┘
  (복제 완료 대기 안 함)

반동기 복제 (Semi-Sync):
┌──────────┐  Binlog + ACK  ┌────────────┐
│  Source  │◄──────────────│  Replica 1 │
│          │               └────────────┘
└──────────┘
  최소 1개 복제본의 수신 확인 후 커밋 반환

그룹 복제 (Group Replication / InnoDB Cluster):
┌──────────┐  Paxos 기반   ┌────────────┐
│  Node 1  │◄────────────►│   Node 2   │
│ (Primary)│               └────────────┘
└──────────┘                     ▲
      ▲                          │
      └──────────────────────────┘
               │  Node 3 │
   다수결 커밋 + 자동 장애조치 (Multi-Primary 또는 Single-Primary)
```

**MySQL 복제 포맷:**
- `STATEMENT`: SQL 문 그대로 기록 (비결정적 함수에서 불일치 위험)
- `ROW`: 변경된 행 데이터 기록 (안전하지만 볼륨 큼)
- `MIXED`: 기본은 STATEMENT, 비결정적인 경우 ROW 자동 전환

### 6.2 PostgreSQL 복제

```
PostgreSQL 스트리밍 복제:
┌─────────────┐  WAL Stream  ┌──────────────┐
│   Primary   │─────────────►│  Standby 1   │
│             │              │ (Hot Standby)│
│             │─────────────►└──────────────┘
└─────────────┘              ┌──────────────┐
                             │  Standby 2   │
                             │(읽기 전용 쿼리│
                             │  가능)       │
                             └──────────────┘

논리적 복제 (Logical Replication):
┌─────────────┐  변경 데이터  ┌──────────────┐
│  Publisher  │─────────────►│  Subscriber  │
│ (선택적     │  (행 단위)   │ (다른 스키마 │
│  테이블)    │              │  버전도 가능)│
└─────────────┘              └──────────────┘
용도: 버전 업그레이드, 특정 테이블만 복제, 이기종 DB 연동
```

**동기/비동기 제어:**
```sql
-- 동기 복제 설정 (Primary 커밋 전 Standby 확인)
synchronous_standby_names = 'standby1'
-- 또는 QUORUM 방식
synchronous_standby_names = 'FIRST 1 (s1, s2, s3)'
```

### 6.3 Oracle Data Guard / GoldenGate

```
Oracle Data Guard:
┌──────────┐  Redo Log     ┌──────────────┐
│ Primary  │──────────────►│  Standby DB  │
│   DB     │               │(Physical or  │
│          │               │  Logical)    │
└──────────┘               └──────────────┘

Physical Standby: Redo Apply (블록 단위 동일)
Logical Standby:  SQL Apply (SQL 변환 후 적용)
Active Data Guard: Standby를 읽기 전용으로 열어 사용 (추가 라이선스)

Oracle GoldenGate (별도 제품):
┌─────────┐  CDC(변경 캡처)  ┌─────────────┐
│ Source  │────────────────►│   Target    │
│(Oracle/ │                 │(Oracle/비-  │
│비-Oracle│                 │Oracle DB)   │
└─────────┘                 └─────────────┘
용도: 이기종 DB 실시간 복제, 마이그레이션, 양방향 복제
```

### 6.4 복제 방식 비교

| 항목 | MySQL | PostgreSQL | Oracle | MariaDB | SQL Server |
|---|---|---|---|---|---|
| 기본 복제 방식 | Binlog (비동기) | WAL 스트리밍 | Data Guard | Binlog | Always On AG |
| 동기 복제 | Semi-Sync, Group Replication | synchronous_commit | Data Guard Sync | Semi-Sync | Synchronous Commit |
| 논리 복제 | Binlog (Row) | Logical Replication | LogMiner/GoldenGate | ✓ | Transactional Replication |
| 이기종 복제 | 제한적 | pglogical | GoldenGate | 제한적 | SSIS/외부 도구 |
| 자동 장애조치 | InnoDB Cluster/MHA | Patroni/Repmgr | Data Guard FSFO | Galera Cluster | Always On FCI |
| 지연 복제 | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## 7. JSON 지원

### 7.1 MySQL JSON 타입

MySQL 5.7부터 네이티브 JSON 타입을 지원한다. 내부적으로 Binary JSON 포맷으로 저장되어 부분 업데이트가 가능하다.

```sql
-- MySQL JSON 사용 예시
CREATE TABLE events (
    id INT PRIMARY KEY,
    data JSON
);

INSERT INTO events VALUES (1, '{"user": "Kim", "action": "login", "ts": 1234567890}');

-- JSON 경로 조회
SELECT data->>'$.user' AS user_name FROM events;
SELECT JSON_EXTRACT(data, '$.action') FROM events;

-- 부분 업데이트 (MySQL 8.0+)
UPDATE events SET data = JSON_SET(data, '$.action', 'logout') WHERE id = 1;

-- JSON 인덱스 (Generated Column 경유)
ALTER TABLE events
    ADD COLUMN user_name VARCHAR(100) GENERATED ALWAYS AS (data->>'$.user') STORED,
    ADD INDEX idx_user (user_name);
```

**MySQL JSON 한계:**
- JSON 컬럼 자체에 직접 인덱스 불가 (Generated Column 우회 필요)
- `CHECK` 제약으로 스키마 강제 불가 (저장 시 유효성만 검사)

### 7.2 PostgreSQL JSONB

PostgreSQL은 `json`(텍스트 저장)과 `jsonb`(바이너리 파싱 후 저장) 두 타입을 지원한다. 실무에서는 거의 항상 `jsonb`를 사용한다.

```sql
-- PostgreSQL JSONB 사용 예시
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    data JSONB
);

INSERT INTO events VALUES (1, '{"user": "Kim", "tags": ["auth", "web"]}');

-- 키 존재 여부
SELECT * FROM events WHERE data ? 'user';

-- 포함 여부 (Contains)
SELECT * FROM events WHERE data @> '{"user": "Kim"}';

-- 배열 원소 포함 여부
SELECT * FROM events WHERE data->'tags' ? 'auth';

-- GIN 인덱스 (JSON 내 모든 키/값 인덱싱)
CREATE INDEX idx_data_gin ON events USING GIN (data);

-- jsonpath 쿼리 (PostgreSQL 12+)
SELECT jsonb_path_query(data, '$.tags[*]') FROM events;
```

**JSONB 고급 기능:**

```sql
-- JSON Schema 검증 (PostgreSQL 16+)
SELECT jsonb_matches_schema(
    '{"type": "object", "properties": {"user": {"type": "string"}}}',
    '{"user": "Kim"}'
);

-- JSON 집계
SELECT jsonb_agg(data) FROM events;
SELECT jsonb_object_agg(id, data) FROM events;
```

### 7.3 JSON 지원 비교

| 기능 | MySQL | PostgreSQL | Oracle | MariaDB | SQL Server |
|---|---|---|---|---|---|
| 네이티브 JSON 타입 | ✓(5.7+) | ✓(json/jsonb) | ✓(21c 네이티브) | ✓ | ✓ |
| 바이너리 저장 | ✓ | ✓(jsonb) | ✓ | ✓ | ✓ |
| JSON 직접 인덱싱 | - (Generated Col) | ✓(GIN) | ✓(JSON Search) | - | ✓(Computed Col) |
| JSON 경로 쿼리 | JSON_EXTRACT | jsonpath | JSON_VALUE | JSON_EXTRACT | JSON_VALUE |
| JSON Schema 검증 | - | ✓(16+) | ✓ | - | - |
| JSON 집계 함수 | ✓ | ✓ | ✓ | ✓ | ✓ |
| JSON → 관계형 분해 | JSON_TABLE | json_to_recordset | JSON_TABLE | JSON_TABLE | OPENJSON |

---

## 8. 확장성 (Extensibility)

### 8.1 MySQL 확장성

MySQL의 핵심 확장 포인트는 스토리지 엔진 교체 가능성이다.

```
MySQL 스토리지 엔진 교체:
┌──────────────────────────────────────────────────┐
│  MySQL Server Layer (파서, 옵티마이저, 캐시 등)  │
├──────────────────────────────────────────────────┤
│  Storage Engine API (핸들러 인터페이스)           │
├──────────────┬───────────┬────────────┬──────────┤
│   InnoDB     │  MyISAM   │  Memory    │  NDB     │
│ (트랜잭션)   │ (읽기 속도)│ (인메모리) │(클러스터)│
└──────────────┴───────────┴────────────┴──────────┘
-- 테이블별로 엔진 선택 가능
CREATE TABLE fast_reads (id INT) ENGINE=MyISAM;
CREATE TABLE transactions (id INT) ENGINE=InnoDB;
```

**플러그인 시스템:**
- 인증 플러그인 (LDAP, Kerberos)
- 감사 플러그인
- UDF(User Defined Function) — C/C++로 작성

**한계:** 새로운 데이터 타입, 연산자, 인덱스 방법 추가 불가

### 8.2 PostgreSQL 확장 시스템

PostgreSQL의 Extension 시스템은 가장 강력하다. SQL만으로 새로운 타입, 연산자, 인덱스 접근법, 함수 언어를 추가할 수 있다.

```sql
-- Extension 설치 (예: PostGIS)
CREATE EXTENSION postgis;
CREATE EXTENSION pg_trgm;   -- 유사 문자열 검색
CREATE EXTENSION uuid-ossp; -- UUID 생성
CREATE EXTENSION tablefunc; -- crosstab, connectby
CREATE EXTENSION pg_stat_statements; -- 쿼리 통계

-- 커스텀 데이터 타입 예시
CREATE TYPE mood AS ENUM ('sad', 'ok', 'happy');
CREATE TABLE person (current_mood mood);

-- 커스텀 연산자
CREATE OPERATOR === (
    leftarg = integer,
    rightarg = integer,
    procedure = int4eq
);

-- 프로시저 언어 확장
CREATE EXTENSION plpython3u; -- Python으로 함수 작성
CREATE EXTENSION plv8;       -- JavaScript(V8)로 함수 작성

-- 커스텀 인덱스 접근 방법 (Access Method)
-- GiST, SP-GiST, GIN 프레임워크로 새 인덱스 타입 구현 가능
```

**주요 Extension 목록:**

| Extension | 기능 |
|---|---|
| PostGIS | 지리정보(GIS) 데이터 처리 |
| pg_trgm | 트라이그램 기반 유사 문자열 검색 |
| pgvector | 벡터 유사도 검색 (AI/ML 임베딩) |
| TimescaleDB | 시계열 데이터 최적화 |
| Citus | 분산 PostgreSQL (샤딩) |
| pg_partman | 파티션 자동 관리 |
| pgcrypto | 암호화 함수 |
| hstore | key-value 저장 |

### 8.3 Oracle 확장성

```
Oracle PL/SQL 생태계:
┌─────────────────────────────────────────────────────┐
│  PL/SQL (Oracle 전용 절차적 SQL 확장)               │
│  ├── Package, Procedure, Function, Trigger           │
│  ├── Object Types (OOP 스타일)                      │
│  ├── Collection Types (Nested Table, VARRAY)         │
│  └── Pipelined Table Function (스트리밍 처리)        │
├─────────────────────────────────────────────────────┤
│  Advanced Queuing (AQ)                               │
│  ├── 데이터베이스 내장 메시지 큐                     │
│  ├── 트랜잭션 보장 메시징                            │
│  └── Kafka 등 외부 시스템 연동                       │
├─────────────────────────────────────────────────────┤
│  Partitioning (별도 옵션)                            │
│  ├── Range, List, Hash, Composite                   │
│  ├── Interval Partitioning (자동 파티션 생성)        │
│  └── Reference Partitioning (FK 기반)               │
├─────────────────────────────────────────────────────┤
│  Oracle Text (전문 검색), Spatial, XML DB           │
└─────────────────────────────────────────────────────┘
```

---

## 9. 성능 특성

### 9.1 읽기 중심 워크로드

```
읽기 성능 특성 비교:

단순 PK 조회:
MySQL InnoDB  ████████████████░░░░  매우 빠름 (Clustered Index)
PostgreSQL    ███████████████░░░░░  빠름 (힙 + 인덱스)
Oracle        ████████████████████  매우 빠름 (버퍼 캐시)
SQL Server    ████████████████░░░░  빠름

복잡한 분석 쿼리:
MySQL         ███████████░░░░░░░░░  중간 (집계 함수 제한)
PostgreSQL    █████████████████░░░  강함 (병렬 쿼리, CTE, 윈도우 함수)
Oracle        ████████████████████  최강 (병렬 실행, Result Cache)
SQL Server    ████████████████████  강함 (OLAP, BI 최적화)
```

**PostgreSQL 병렬 쿼리 예시:**
```sql
-- 병렬 쿼리 설정
SET max_parallel_workers_per_gather = 4;

-- 대용량 집계 자동으로 병렬 처리
SELECT department, AVG(salary), COUNT(*)
FROM employees
GROUP BY department;
-- → Gather Node가 4개 worker 병렬 집계 후 머지
```

### 9.2 쓰기 중심 워크로드

```
쓰기 성능 특성:

단건 INSERT 처리량 (상대적):
MySQL InnoDB  ████████████████████  빠름 (WAL 순차 쓰기)
PostgreSQL    ████████████████░░░░  빠름 (WAL 순차 쓰기)
Oracle        ████████████████████  빠름 (Redo Log + Change Vector)
SQL Server    ████████████████████  빠름

대량 BULK INSERT:
MySQL         ████████████████████  빠름 (LOAD DATA INFILE)
PostgreSQL    ████████████████████  빠름 (COPY)
Oracle        ████████████████████  빠름 (SQL*Loader, Direct-Path)
SQL Server    ████████████████████  빠름 (BULK INSERT, bcp)
```

**성능에 영향을 미치는 주요 요소:**

| 요소 | MySQL | PostgreSQL | Oracle |
|---|---|---|---|
| WAL 동기화 | innodb_flush_log_at_trx_commit | synchronous_commit | log_buffer_size |
| 쓰기 지연 허용 | =2 (1초마다 flush) | =off (비동기) | ASYNC commit |
| 병렬 처리 | InnoDB Parallel DDL | max_parallel_workers | Parallel DML |
| Bulk Load | LOAD DATA INFILE | COPY | Direct Path Load |

### 9.3 동시성 처리

```
동시 쓰기 처리 비교 (같은 행 업데이트):

MySQL REPEATABLE READ:
T1: BEGIN; UPDATE row; -- 잠금 획득
T2: BEGIN; UPDATE row; -- 대기 (Row Lock)
T1: COMMIT;
T2: 잠금 획득 후 실행

PostgreSQL READ COMMITTED:
T1: BEGIN; UPDATE row; -- 최신 버전 잠금
T2: BEGIN; UPDATE row; -- T1 대기
T1: COMMIT;
T2: 최신 버전 재읽기 후 실행 (T1 결과 반영)

Oracle READ COMMITTED:
T1: BEGIN; UPDATE row; -- Row-level TX Lock
T2: BEGIN; UPDATE row; -- T1 대기
T1: COMMIT;
T2: 잠금 획득 (변경된 값 기준으로 재실행)
```

**동시 읽기-쓰기 (MVCC 효과):**

모든 MVCC 지원 DB(InnoDB, PostgreSQL, Oracle)에서 SELECT는 UPDATE를 기다리지 않는다. 이것이 전통적 잠금 방식(MyISAM) 대비 가장 큰 장점이다.

### 9.4 대용량 데이터 처리

| 기능 | MySQL | PostgreSQL | Oracle | SQL Server |
|---|---|---|---|---|
| 테이블 파티셔닝 | ✓(제한적) | ✓(선언적, 강력) | ✓(엔터프라이즈) | ✓ |
| 병렬 쿼리 | ✓(8.0+, 제한적) | ✓(강력) | ✓(최강) | ✓ |
| 병렬 DDL | ✓ | ✓ | ✓ | ✓ |
| 컬럼형 스토리지 | ✗ | - | ✓(In-Memory Col) | ✓(Columnstore) |
| 인메모리 테이블 | Memory 엔진 | - | ✓(In-Memory) | ✓(Hekaton) |

---

## 10. 운영 / 관리

### 10.1 백업 / 복구 방식

#### MySQL 백업

```
MySQL 백업 방법:

1. 논리 백업 (mysqldump):
mysqldump -u root -p --single-transaction --routines --triggers \
    --all-databases > backup.sql
# --single-transaction: InnoDB 일관성 보장
# 단점: 대용량에서 느림, 복구도 느림

2. 물리 백업 (Percona XtraBackup):
xtrabackup --backup --target-dir=/backup/
xtrabackup --prepare --target-dir=/backup/  # 복구 준비
xtrabackup --copy-back --target-dir=/backup/ # 복구
# 핫 백업 (서비스 중단 없음), 빠른 복구

3. Binary Log 기반 PITR (Point-In-Time Recovery):
mysqlbinlog --start-datetime="2026-05-01 12:00:00" \
            --stop-datetime="2026-05-01 13:00:00" \
            binlog.000001 | mysql -u root -p
```

#### PostgreSQL 백업

```
PostgreSQL 백업 방법:

1. pg_dump (논리 백업):
pg_dump -Fc -f backup.dump mydb   # 커스텀 포맷 (압축)
pg_restore -d mydb backup.dump    # 복구

2. pg_basebackup + WAL (물리 백업 + PITR):
# 베이스 백업
pg_basebackup -D /backup/base -Ft -z -Xs -P

# postgresql.conf 설정
archive_mode = on
archive_command = 'cp %p /archive/%f'

# PITR 복구 시 recovery.conf (또는 postgresql.conf):
restore_command = 'cp /archive/%f %p'
recovery_target_time = '2026-05-01 13:00:00'

3. pgBackRest / Barman (엔터프라이즈 백업 솔루션):
pgbackrest --stanza=mydb backup --type=full
pgbackrest --stanza=mydb restore
```

#### Oracle 백업

```
Oracle RMAN (Recovery Manager):
# 전체 백업
rman target /
RMAN> BACKUP DATABASE PLUS ARCHIVELOG;

# 증분 백업
RMAN> BACKUP INCREMENTAL LEVEL 0 DATABASE;
RMAN> BACKUP INCREMENTAL LEVEL 1 DATABASE;

# PITR 복구
RMAN> RECOVER DATABASE UNTIL TIME "TO_DATE('2026-05-01 13:00:00', 'YYYY-MM-DD HH24:MI:SS')";
RMAN> OPEN RESETLOGS;
```

### 10.2 모니터링 도구

| 도구 | 대상 DB | 설명 |
|---|---|---|
| **Performance Schema** | MySQL/MariaDB | 내장 진단 데이터, 쿼리 통계 |
| **sys schema** | MySQL | Performance Schema 뷰 모음 |
| **pg_stat_statements** | PostgreSQL | 쿼리별 실행 통계 Extension |
| **pg_activity** | PostgreSQL | top 유사 실시간 모니터링 |
| **pgBadger** | PostgreSQL | 로그 분석 리포트 |
| **AWR (Automatic Workload Repository)** | Oracle | 성능 스냅샷, Top SQL |
| **ASH (Active Session History)** | Oracle | 1초 단위 활성 세션 샘플링 |
| **Percona Monitoring and Management (PMM)** | MySQL/PG | 오픈소스 통합 모니터링 |
| **Prometheus + postgres_exporter** | PostgreSQL | 메트릭 수집·시각화 |
| **Datadog, New Relic** | 전체 | SaaS 통합 모니터링 |

```sql
-- PostgreSQL 핵심 모니터링 쿼리
-- 느린 쿼리 Top 10
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC LIMIT 10;

-- 블로킹 쿼리 확인
SELECT pid, wait_event_type, wait_event, query
FROM pg_stat_activity
WHERE wait_event_type = 'Lock';

-- 테이블별 Dead Tuple 현황
SELECT schemaname, relname, n_live_tup, n_dead_tup,
       last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;
```

### 10.3 업그레이드 편의성

| 데이터베이스 | 마이너 업그레이드 | 메이저 업그레이드 | 다운타임 |
|---|---|---|---|
| **MySQL** | In-place 가능 | In-place(5.7→8.0), 복잡 | 필요 (최소화 가능) |
| **PostgreSQL** | In-place 가능 | pg_upgrade 도구 필요 | pg_upgrade는 빠름 |
| **Oracle** | In-place 가능 | DBUA(DB Upgrade Assistant) | 최소화 기법 다양 |
| **MariaDB** | In-place 가능 | mysql_upgrade 실행 | 필요 |
| **SQL Server** | In-place 가능 | In-place 가능 | 상대적으로 편리 |

**PostgreSQL 무중단 업그레이드 전략 (논리 복제 활용):**
```
1. 신규 버전 서버 준비
2. 논리적 복제(Logical Replication)로 실시간 데이터 동기화
3. 레플리케이션 지연이 0에 가까워지면 트래픽 전환
4. 전환 후 구버전 서버 종료
→ 다운타임 수 초~분 수준
```

---

## 11. 비용

### 11.1 라이선스 비용

| 데이터베이스 | 무료 에디션 | 유료 에디션 | 연간 비용(개략) |
|---|---|---|---|
| **MySQL** | Community Edition(GPL) | MySQL Enterprise | $10,000~/년 |
| **PostgreSQL** | 완전 무료 (PostgreSQL License) | - (지원 계약 별도) | $0 |
| **Oracle** | Express Edition(XE, 제한적) | Standard One/Enterprise | $10,000~$50,000+/CPU |
| **MariaDB** | Community Edition(GPL) | MariaDB Enterprise | $7,000~/년 |
| **SQL Server** | Developer(비상용)/Express(제한) | Standard/Enterprise | $1,418~$15,123/코어 |

**Oracle Enterprise 주요 유료 옵션:**

| 옵션 | 기능 | 추가 비용 |
|---|---|---|
| Partitioning | 테이블 파티셔닝 | $11,500/Named User |
| Advanced Compression | 압축 스토리지 | $11,500/Named User |
| Active Data Guard | Standby 읽기 + PITR | $11,500/Named User |
| Real Application Clusters | RAC 클러스터링 | $23,000/Named User |
| Diagnostics & Tuning Pack | AWR, ASH, SQL Tuning Advisor | $11,500/Named User |

### 11.2 클라우드 매니지드 서비스

```
클라우드 비용 비교 (AWS 기준, db.r6g.large 4vCPU/32GB 예시):

RDS MySQL:           $0.48/h  →  약 $350/월
RDS PostgreSQL:      $0.48/h  →  약 $350/월
RDS Oracle SE2:      $0.94/h  →  약 $680/월
RDS SQL Server SE:   $0.94/h  →  약 $680/월
Aurora MySQL:        $0.48/h  →  약 $350/월 + 스토리지
Aurora PostgreSQL:   $0.48/h  →  약 $350/월 + 스토리지
```

**Aurora의 특징:**
- MySQL/PostgreSQL 호환 API
- 스토리지가 6개 복사본 자동 분산 (3 AZ)
- 최대 15개 읽기 전용 복제본
- 기존 RDS 대비 최대 5배(MySQL), 3배(PostgreSQL) 성능 향상 주장

**클라우드 매니지드 서비스 비교:**

| 클라우드 | MySQL | PostgreSQL | Oracle | SQL Server |
|---|---|---|---|---|
| AWS | RDS MySQL, Aurora MySQL | RDS PG, Aurora PG | RDS Oracle | RDS SQL Server |
| GCP | Cloud SQL MySQL | Cloud SQL PG, AlloyDB | - | Cloud SQL SQL Server |
| Azure | Azure Database for MySQL | Azure Database for PG | Oracle on Azure | Azure SQL Database |

---

## 12. 실무 선택 가이드

### 12.1 선택 기준 플로우차트

```
데이터베이스 선택 의사결정:

시작
│
├─ 예산이 제한적인가?
│   YES → 오픈소스 고려
│   │      ├─ MySQL 호환성이 필요한가?
│   │      │   YES → MariaDB
│   │      │   NO  → 복잡한 쿼리/분석 필요?
│   │      │           YES → PostgreSQL
│   │      │           NO  → MySQL
│   │
│   NO → 상용 라이선스 OK
│          ├─ Microsoft 생태계(.NET, Azure)?
│          │   YES → SQL Server
│          │   NO  → 엔터프라이즈/금융/규정 준수?
│                      YES → Oracle
│                      NO  → PostgreSQL or MySQL
│
└─ 클라우드 네이티브 우선?
    YES → Aurora (MySQL/PG 호환)
    NO  → 온프레미스 기준 위 선택
```

### 12.2 워크로드별 추천

#### 스타트업 / 소규모 서비스

**추천: PostgreSQL 또는 MySQL**

```
PostgreSQL 선택 이유:
✓ 완전 무료, 제한 없는 라이선스
✓ 강력한 기능 (JSON, 윈도우 함수, CTE, 확장)
✓ 데이터 정합성 (더 엄격한 SQL 표준 준수)
✓ 필요 시 확장 가능 (PostGIS, pgvector 등)

MySQL 선택 이유:
✓ 더 많은 레퍼런스, 튜토리얼
✓ 단순 CRUD 앱에서 충분
✓ 호스팅 업체 지원 광범위
✓ Aurora MySQL로 마이그레이션 용이
```

#### 복잡한 쿼리 / 분석 (OLAP 혼합)

**추천: PostgreSQL**

```
PostgreSQL 강점:
- 고급 윈도우 함수 (LEAD, LAG, NTILE, PERCENT_RANK)
- CTE(WITH 절) 최적화
- 병렬 쿼리 (Parallel Seq Scan, Hash Join)
- 파티션 프루닝
- 강력한 Full-Text Search
- GIN 인덱스 (배열, JSONB 검색)
- 커스텀 집계 함수

예시 쿼리 (PostgreSQL 강점):
WITH monthly_sales AS (
    SELECT
        date_trunc('month', created_at) AS month,
        SUM(amount) AS total,
        LAG(SUM(amount)) OVER (ORDER BY date_trunc('month', created_at)) AS prev_month
    FROM orders
    GROUP BY 1
)
SELECT month, total,
       ROUND((total - prev_month) / prev_month * 100, 2) AS growth_pct
FROM monthly_sales;
```

#### 엔터프라이즈 / 금융권

**추천: Oracle Database**

```
Oracle 선택 이유:
✓ 수십 년간의 엔터프라이즈 검증
✓ Data Guard를 통한 무중단 고가용성
✓ RAC (Real Application Clusters) 스케일아웃
✓ 정밀한 보안/감사 (Fine-Grained Auditing)
✓ 규정 준수 (SOX, PCI-DSS, HIPAA)
✓ 강력한 PL/SQL 생태계
✓ Oracle 지원 SLA 보장

고려사항:
△ 매우 높은 라이선스 비용
△ Oracle 전문 DBA 인력 필요
△ 벤더 종속(Vendor Lock-in) 위험
```

#### .NET / Microsoft 환경

**추천: SQL Server**

```
SQL Server 선택 이유:
✓ Azure 통합 (Azure SQL, Azure Synapse)
✓ .NET Entity Framework, ADO.NET 완벽 지원
✓ SSRS, SSAS, SSIS 통합 (BI 스택)
✓ Always On Availability Groups
✓ T-SQL의 강력한 기능
✓ Visual Studio / SQL Server Management Studio

SQL Server 고유 기능:
- Columnstore Index (OLAP 최적화)
- In-Memory OLTP (Hekaton)
- R/Python 인-데이터베이스 실행
- Stretch Database (Azure 오프로딩)
```

#### MySQL 호환 + 커뮤니티

**추천: MariaDB**

```
MariaDB 선택 이유:
✓ MySQL 5.x 대비 성능 개선 (특히 읽기)
✓ 완전한 GPL 오픈소스 (Oracle 의존성 없음)
✓ Galera Cluster (동기 멀티마스터)
✓ Aria 스토리지 엔진 (MyISAM 개선판)
✓ ColumnStore (분석용 컬럼 스토리지)
✓ 독자적인 기능 선행 도입

MySQL과의 비호환 사항:
△ MySQL 8.0+ 일부 기능 미지원
△ JSON 함수 일부 차이
△ 인증 플러그인 차이
```

---

## 13. 종합 비교 표

### 13.1 핵심 기능 비교

| 기능 | MySQL 8.0 | PostgreSQL 16 | Oracle 21c | MariaDB 10.11 | SQL Server 2022 |
|---|---|---|---|---|---|
| **라이선스** | GPL/상용 | PostgreSQL(BSD) | 상용 | GPL | 상용 |
| **ACID 지원** | ✓(InnoDB) | ✓ | ✓ | ✓(InnoDB) | ✓ |
| **기본 격리수준** | REPEATABLE READ | READ COMMITTED | READ COMMITTED | REPEATABLE READ | READ COMMITTED |
| **MVCC** | Undo Log | Tuple Version | Undo Tablespace | Undo Log | MSSQL Versioning |
| **기본 스토리지** | InnoDB | 힙(Heap) | 테이블스페이스 | InnoDB/Aria | Extent 기반 |
| **클러스터드 인덱스** | ✓(PK) | 별도 설정 | IOT | ✓(PK) | ✓ |
| **파티셔닝** | ✓(제한) | ✓(강력) | ✓(옵션 유료) | ✓ | ✓ |
| **외래키** | ✓(InnoDB) | ✓ | ✓ | ✓(InnoDB) | ✓ |
| **CHECK 제약** | ✓(8.0.16+) | ✓ | ✓ | ✓ | ✓ |
| **윈도우 함수** | ✓(8.0+) | ✓ | ✓ | ✓(10.2+) | ✓ |
| **CTE (WITH)** | ✓(8.0+) | ✓ | ✓ | ✓(10.2+) | ✓ |
| **재귀 CTE** | ✓(8.0+) | ✓ | ✓ | ✓(10.2+) | ✓ |
| **전문 검색** | ✓(기본) | ✓(tsvector/GIN) | ✓(Oracle Text) | ✓ | ✓ |
| **JSON 지원** | ✓ | ✓(JSONB+GIN) | ✓(21c 네이티브) | ✓ | ✓ |
| **XML 지원** | ✓ | ✓ | ✓(XMLType) | ✓ | ✓ |
| **GIS/공간 데이터** | ✓ | ✓(PostGIS 강력) | ✓(Oracle Spatial) | ✓ | ✓ |
| **병렬 쿼리** | ✓(제한) | ✓(강력) | ✓(최강) | ✓(제한) | ✓ |

### 13.2 고가용성 / 복제 비교

| 기능 | MySQL | PostgreSQL | Oracle | MariaDB | SQL Server |
|---|---|---|---|---|---|
| **스트리밍 복제** | Binlog | WAL | Data Guard | Binlog | Always On |
| **동기 복제** | Semi-Sync/Group | sync_commit | DG Sync | Semi-Sync/Galera | Sync Commit |
| **자동 Failover** | InnoDB Cluster | Patroni/Repmgr | DG + Observer | Galera/MHA | Always On FCI |
| **읽기 분산** | 복제본 | Hot Standby | Active DG | 복제본 | Readable Secondary |
| **멀티마스터** | Group Replication | BDR (3rd party) | RAC | Galera | - |
| **논리 복제** | Binlog Row | Logical Rep | GoldenGate | Binlog Row | Transactional Rep |

### 13.3 개발 / SQL 표준 준수 비교

| 기능 | MySQL | PostgreSQL | Oracle | MariaDB | SQL Server |
|---|---|---|---|---|---|
| **SQL 표준 준수도** | 중간 | 높음 | 높음 | 중간 | 중간 |
| **저장 프로시저** | ✓ | ✓(PL/pgSQL) | ✓(PL/SQL) | ✓ | ✓(T-SQL) |
| **트리거** | ✓ | ✓(강력) | ✓(강력) | ✓ | ✓ |
| **사용자 정의 함수** | ✓ | ✓(다국어) | ✓ | ✓ | ✓ |
| **이벤트 스케줄러** | ✓ | pgAgent | DBMS_SCHEDULER | ✓ | SQL Agent |
| **연결 풀링** | MySQL Router | PgBouncer | UCP/Connection Pool | MaxScale | 내장 |
| **EXPLAIN 상세도** | 중간 | 높음 (EXPLAIN ANALYZE) | 높음 (Autotrace) | 중간 | 높음 |
| **DDL 트랜잭션** | - (자동 커밋) | ✓ | - (자동 커밋) | - | ✓ |

### 13.4 PostgreSQL만의 고유 강점 정리

```
PostgreSQL 고유/우위 기능:

인덱스:    GIN, GiST, SP-GiST, BRIN, Partial Index, Expression Index
타입:      배열, hstore, 범위타입(range), 복합타입, 도메인
확장:      Extension 시스템 (PostGIS, pgvector, TimescaleDB 등)
SQL:       Table Inheritance, LATERAL 조인, FILTER 절
동시성:    SSI (Serializable Snapshot Isolation)
복제:      논리적 복제 내장 (추가 비용 없음)
언어:      PL/pgSQL, PL/Python, PL/Perl, PL/v8 (JavaScript)
운영:      DDL 트랜잭션 (마이그레이션 롤백 가능)
개방성:    완전 오픈소스, 커스텀 타입/연산자/집계 함수 추가 가능
```

### 13.5 운영 복잡도 비교

| 항목 | MySQL | PostgreSQL | Oracle | MariaDB | SQL Server |
|---|---|---|---|---|---|
| **초기 설정 난이도** | 낮음 | 낮음-중간 | 높음 | 낮음 | 낮음-중간 |
| **튜닝 파라미터 수** | 중간 | 중간 | 매우 많음 | 중간 | 많음 |
| **DBA 전문성 요구** | 낮음-중간 | 중간 | 높음 | 낮음-중간 | 중간-높음 |
| **문서/커뮤니티** | 풍부 | 풍부 | 공식 문서 최강 | 중간 | 풍부 |
| **인력 수급** | 매우 쉬움 | 쉬움 | 전문 DBA 필요 | 쉬움 | 중간 |
| **클라우드 지원** | 광범위 | 광범위 | 제한적 | 일부 | Azure 중심 |

---

## 정리

RDBMS 선택에서 "최고의 데이터베이스"는 존재하지 않는다. 워크로드, 팀 역량, 예산, 생태계를 종합적으로 고려해야 한다.

- **PostgreSQL**: 기능, 표준 준수, 확장성, 비용 모든 면에서 균형 잡힌 선택. 신규 프로젝트라면 우선 고려.
- **MySQL**: 단순 웹 앱, 레거시 호환, 광범위한 호스팅 지원 시 유효.
- **Oracle**: 고가용성, 엔터프라이즈 지원, 레거시 PL/SQL 자산이 중요한 대기업/금융.
- **MariaDB**: MySQL 대체를 원하지만 Oracle 의존성을 피하고 싶을 때.
- **SQL Server**: Microsoft 생태계, Azure, .NET 환경에서 가장 자연스러운 선택.

클라우드 시대에는 Aurora(MySQL/PostgreSQL 호환)나 AlloyDB(PostgreSQL 호환)도 충분히 실용적인 대안이다. 스타트업이라면 PostgreSQL + RDS/Cloud SQL로 시작하여 성장에 따라 Aurora나 Citus(분산 PostgreSQL)로 전환하는 경로를 추천한다.
