---
title: "MySQL vs PostgreSQL — 2026년 기준 완전 비교 가이드"
categories: DB
tags: [MySQL, PostgreSQL, DB, 비교, MVCC, 인덱스, JSON]
toc: true
toc_sticky: true
toc_label: 목차
---

새 프로젝트의 데이터베이스를 선택해야 한다. MySQL vs PostgreSQL. 두 데이터베이스 모두 무료이고, 안정적이며, 대규모 프로덕션 환경에서 검증되었다. 그런데 왜 고민이 되는가? 내부 구현 방식이 근본적으로 다르고, 그 차이가 특정 워크로드에서 성능과 기능의 큰 격차를 만들기 때문이다. 이 포스트는 **2026년 기준 두 DB의 핵심 차이**를 깊이 있게 비교한다.

---

## 탄생 배경과 철학

MySQL은 1995년 스웨덴의 MySQL AB가 만들었다. 처음부터 **웹 애플리케이션의 빠른 읽기**에 최적화했다. LAMP 스택(Linux, Apache, MySQL, PHP)의 M이다. 단순함과 속도가 철학이다.

PostgreSQL은 1996년 UC Berkeley의 POSTGRES 프로젝트에서 출발했다. **SQL 표준 준수와 확장성**이 철학이다. 객체-관계형 DB(ORDBMS)를 목표로 설계되었다. 기업용 DB 기능을 오픈소스로 구현하겠다는 목표가 있었다.

> **비유**: MySQL은 빠른 패스트푸드 레스토랑이다. 표준 메뉴를 빠르게 제공하는 데 최적화되어 있다. PostgreSQL은 파인다이닝 레스토랑이다. 복잡한 요리(고급 SQL, 확장 타입)를 정확하게 만들 수 있고, 셰프(개발자)가 메뉴를 커스터마이징할 수 있다.

---

## 핵심 차이 한눈에 보기

| 항목 | MySQL (8.0+) | PostgreSQL (16+) |
|------|-------------|-----------------|
| MVCC 구현 | Undo 로그 기반 | 힙 튜플 기반 |
| 기본 스토리지 엔진 | InnoDB | 단일 엔진 |
| JSON 지원 | JSON 타입 (부분적) | JSONB (완전한 인덱싱) |
| 배열 타입 | 없음 | 네이티브 지원 |
| 파티셔닝 | 선언적 파티셔닝 | 선언적 + 더 유연한 옵션 |
| 복제 | 비동기 바이너리 로그 | 논리/물리 복제 모두 |
| CTE(WITH 절) | 8.0부터 지원 | 오래전부터 지원 + RECURSIVE |
| 윈도우 함수 | 8.0부터 지원 | 완전 지원, 더 풍부 |
| 전문 검색 | 기본 FTS | ts_vector, GIN 인덱스 |
| 지리정보 | 제한적 | PostGIS (업계 표준) |
| 확장 | 제한적 | 400+ 확장 (pg_extension) |
| 라이선스 | GPL v2 / 상용 | PostgreSQL License (BSD계열) |
| 클라우드 관리형 | RDS, Aurora MySQL | RDS, Aurora Postgres, AlloyDB |

---

## MVCC 구현 차이 — 가장 근본적인 차이

MVCC(Multi-Version Concurrency Control)는 동시성 제어의 핵심이다. 읽기와 쓰기가 서로를 블록하지 않는 방법이다.

### MySQL InnoDB의 Undo 로그 MVCC

```
현재 레코드: [user_id=1, name="김철수", age=30, txn_id=100]
                                                      ↓ UPDATE 발생
Undo 로그:  [user_id=1, name="김철수", age=29, txn_id=99]
            [user_id=1, name="김민준", age=29, txn_id=50]
```

MySQL은 **현재 버전을 페이지에 저장**하고, 이전 버전을 별도의 undo 로그에 유지한다. 오래된 트랜잭션이 이전 버전을 읽으려면 undo 로그를 체인처럼 따라간다.

장점: 테이블 페이지에는 항상 최신 데이터만 있어서 읽기가 빠르다. VACUUM이 필요 없다.

단점: 긴 트랜잭션이 있으면 undo 로그가 무한정 커진다. undo 로그 체인을 따라가는 읽기 비용 증가.

```sql
-- MySQL에서 긴 트랜잭션 감지
SELECT * FROM information_schema.INNODB_TRX
WHERE time_to_sec(timediff(now(), trx_started)) > 60;  -- 60초 이상 트랜잭션
```

### PostgreSQL의 힙 튜플 MVCC

```
테이블 페이지 (힙):
┌─────────────────────────────────────────┐
│ 튜플1: [김민준, 29, xmin=50, xmax=99]   │ ← 트랜잭션 99에서 삭제됨
│ 튜플2: [김철수, 29, xmin=99, xmax=100]  │ ← 트랜잭션 100에서 삭제됨
│ 튜플3: [김철수, 30, xmin=100, xmax=∞]  │ ← 현재 유효한 버전
└─────────────────────────────────────────┘
```

PostgreSQL은 **모든 버전을 같은 테이블 페이지에** 저장한다. 각 튜플에 `xmin`(생성 트랜잭션 ID)과 `xmax`(삭제 트랜잭션 ID)를 달아서 어떤 트랜잭션에게 보이는지 결정한다.

장점: 이전 버전 접근에 undo 로그 체인 탐색이 없다.

단점: 오래된 버전이 테이블 페이지를 차지한다. **VACUUM이 주기적으로 죽은 튜플을 정리**해야 한다.

```sql
-- PostgreSQL VACUUM 상태 확인
SELECT schemaname, tablename,
       n_dead_tup,     -- 죽은 튜플 수 (VACUUM 필요 지표)
       last_vacuum,
       last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
```

> **비유**: MySQL MVCC는 항상 최신판 책 한 권만 서가에 두고, 구판은 창고(undo 로그)에 보관한다. PostgreSQL은 모든 판을 서가에 꽂아두고, 각 책에 "언제부터 언제까지 유효"를 표시한다. PostgreSQL은 서가가 넘치면 청소(VACUUM)해야 한다.

---

## 인덱스 종류 비교

### MySQL의 인덱스

```sql
-- MySQL 주요 인덱스
CREATE INDEX idx_name ON users(name);                    -- B-Tree (기본)
CREATE FULLTEXT INDEX idx_content ON articles(content); -- 전문 검색
CREATE SPATIAL INDEX idx_location ON places(location);  -- 공간 인덱스

-- MySQL은 B-Tree가 사실상 전부
-- InnoDB 클러스터드 인덱스 (Primary Key = 실제 데이터 위치)
-- 세컨더리 인덱스는 PK 값을 가리킴 → PK 조회 추가 비용
```

### PostgreSQL의 풍부한 인덱스

```sql
-- PostgreSQL 인덱스 다양성
CREATE INDEX idx_name ON users(name);                  -- B-Tree (기본)
CREATE INDEX idx_tags ON posts USING GIN(tags);        -- GIN (배열, JSONB, FTS)
CREATE INDEX idx_location ON places USING GIST(location); -- GIST (지리, 범위)
CREATE INDEX idx_text ON articles USING BRIN(created_at); -- BRIN (시계열 대용량)
CREATE INDEX idx_hash ON sessions USING HASH(session_id); -- HASH (동등 비교만)

-- 부분 인덱스 — 특정 조건을 만족하는 행만 인덱싱
CREATE INDEX idx_active_users ON users(email)
WHERE status = 'ACTIVE';  -- status='ACTIVE'인 행만 인덱싱

-- 표현식 인덱스 — 함수 결과를 인덱싱
CREATE INDEX idx_lower_email ON users(lower(email));

-- PostgreSQL은 힙 기반 — 모든 인덱스가 힙 튜플을 가리킴
-- PK도 세컨더리 인덱스처럼 동작 (클러스터드 아님)
```

```sql
-- GIN 인덱스 활용 — 배열 검색
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT,
    tags TEXT[]
);

CREATE INDEX idx_tags ON products USING GIN(tags);

-- 배열에 특정 태그가 포함된 상품 검색 (GIN 인덱스 활용)
SELECT * FROM products WHERE tags @> ARRAY['전자제품', '할인'];

-- 전문 검색 + GIN
CREATE INDEX idx_fts ON articles USING GIN(to_tsvector('korean', content));
SELECT * FROM articles
WHERE to_tsvector('korean', content) @@ to_tsquery('korean', '데이터베이스');
```

---

## JSON 지원 — PostgreSQL의 압도적 우위

### MySQL의 JSON

```sql
-- MySQL JSON — 기본 지원
CREATE TABLE events (
    id BIGINT PRIMARY KEY,
    data JSON
);

INSERT INTO events VALUES (1, '{"userId": 1001, "action": "purchase", "amount": 50000}');

-- JSON 값 추출
SELECT data->>'$.userId' AS user_id,
       data->>'$.amount' AS amount
FROM events
WHERE JSON_EXTRACT(data, '$.action') = 'purchase';

-- JSON 인덱스 — 가상 컬럼 필요
ALTER TABLE events ADD COLUMN user_id BIGINT
    GENERATED ALWAYS AS (data->>'$.userId') STORED;
CREATE INDEX idx_user_id ON events(user_id);
```

MySQL JSON은 사용할 수 있지만, 인덱스 생성이 번거롭고 쿼리 문법이 직관적이지 않다.

### PostgreSQL의 JSONB

```sql
-- PostgreSQL JSONB — 바이너리 저장, 완전한 인덱싱
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    data JSONB
);

INSERT INTO events VALUES (DEFAULT, '{"userId": 1001, "action": "purchase", "amount": 50000}');

-- 직관적인 연산자
SELECT data->>'userId' AS user_id,
       data->>'amount' AS amount
FROM events
WHERE data->>'action' = 'purchase'
  AND (data->>'amount')::INT > 10000;

-- GIN 인덱스로 전체 JSONB 인덱싱
CREATE INDEX idx_events_data ON events USING GIN(data);

-- JSONB 특정 경로 인덱스
CREATE INDEX idx_user_id ON events((data->>'userId'));

-- JSONB 포함 검사 (인덱스 활용)
SELECT * FROM events WHERE data @> '{"action": "purchase"}';

-- JSONB 집계와 변환
SELECT jsonb_agg(data) FILTER (WHERE data->>'action' = 'purchase')
FROM events;
```

> **비유**: MySQL JSON은 봉투에 든 편지다. 꺼내서 읽을 수는 있지만, 봉투째 검색하려면 모두 열어봐야 한다. PostgreSQL JSONB는 내용이 데이터베이스화된 파일 캐비닛이다. 내용 그대로 검색하고 인덱싱할 수 있다.

---

## 파티셔닝

### MySQL 파티셔닝

```sql
-- MySQL 파티셔닝 — RANGE, LIST, HASH, KEY
CREATE TABLE orders (
    id BIGINT,
    order_date DATE,
    amount DECIMAL(10,2),
    PRIMARY KEY (id, order_date)  -- 파티션 키가 PK에 포함돼야 함
)
PARTITION BY RANGE (YEAR(order_date)) (
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p2026 VALUES LESS THAN (2027),
    PARTITION pmax  VALUES LESS THAN MAXVALUE
);

-- MySQL 파티션 제거 (오래된 데이터 삭제 — 매우 빠름)
ALTER TABLE orders DROP PARTITION p2024;
```

MySQL 파티셔닝의 제약: 파티션 키가 반드시 Primary Key에 포함되어야 한다. 파티션 간 JOIN이 제한적이다.

### PostgreSQL 파티셔닝

```sql
-- PostgreSQL 선언적 파티셔닝 (10+)
CREATE TABLE orders (
    id BIGSERIAL,
    order_date DATE NOT NULL,
    amount DECIMAL(10,2)
) PARTITION BY RANGE (order_date);

-- 파티션 생성
CREATE TABLE orders_2024 PARTITION OF orders
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE orders_2025 PARTITION OF orders
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

-- 파티션에 인덱스 자동 적용
CREATE INDEX ON orders(order_date);  -- 모든 파티션에 자동 생성

-- 파티션 분리 (데이터 보존)
ALTER TABLE orders DETACH PARTITION orders_2024;

-- 파티션 정리 정보
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(tablename::text))
FROM pg_tables
WHERE tablename LIKE 'orders_%';
```

PostgreSQL은 List, Range, Hash 파티셔닝을 지원하고, 파티션 프루닝(Partition Pruning)이 더 정교하다.

---

## 복제 아키텍처

### MySQL 복제

```
[Primary] → 바이너리 로그 (binlog) → [Replica]
```

```sql
-- MySQL 복제 설정 (Primary)
-- my.cnf
[mysqld]
server-id = 1
log_bin = /var/log/mysql/mysql-bin.log
binlog_format = ROW  -- 행 기반 (가장 안전)

-- Replica에서 복제 시작
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST='primary-host',
    SOURCE_USER='replicator',
    SOURCE_PASSWORD='password',
    SOURCE_AUTO_POSITION=1;  -- GTID 기반 자동 위치
START REPLICA;

-- 복제 지연 확인
SHOW REPLICA STATUS\G
-- Seconds_Behind_Source: 복제 지연(초)
```

MySQL 복제는 기본적으로 비동기다. `semi-synchronous` 플러그인으로 하나의 Replica가 수신 확인할 때까지 대기할 수 있다.

### PostgreSQL 복제

```bash
# postgresql.conf (Primary)
wal_level = replica          # 복제용 WAL 레벨
max_wal_senders = 10         # 최대 복제 연결 수
synchronous_commit = on      # 동기 복제 여부
```

```bash
# 물리 복제 — 바이트 수준 동일 복사
pg_basebackup -h primary-host -U replicator -D /var/lib/postgresql/data -P -R

# postgresql.conf (Replica)
# recovery.conf (또는 standby.signal 파일 생성)
primary_conninfo = 'host=primary-host user=replicator'
```

```sql
-- 논리 복제 — 특정 테이블만 복제, 이기종 버전 간 가능
-- Primary에서 발행자(Publication) 생성
CREATE PUBLICATION my_pub FOR TABLE users, orders;

-- Replica에서 구독자(Subscription) 생성
CREATE SUBSCRIPTION my_sub
    CONNECTION 'host=primary-host dbname=mydb user=replicator'
    PUBLICATION my_pub;

-- 복제 지연 확인
SELECT application_name,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;
```

PostgreSQL 논리 복제는 MySQL에서 PostgreSQL로 마이그레이션하거나, 특정 테이블만 다른 시스템에 복제할 때 유용하다.

---

## 성능 비교

### 단순 읽기 — MySQL의 강점

```sql
-- 단순 PK 조회: MySQL이 유리
SELECT * FROM users WHERE id = 1001;
-- MySQL InnoDB 클러스터드 인덱스: PK = 데이터 위치
-- PostgreSQL: PK 인덱스 → 힙 페이지 추가 접근

-- 단순 SELECT: MySQL이 약간 빠름
-- 인덱스 효율이 동등할 때 MySQL이 5-15% 빠른 경향
```

### 복잡한 쿼리 — PostgreSQL의 강점

```sql
-- 복잡한 집계와 윈도우 함수
SELECT
    user_id,
    order_date,
    amount,
    SUM(amount) OVER (PARTITION BY user_id ORDER BY order_date
                      ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_7day,
    RANK() OVER (PARTITION BY DATE_TRUNC('month', order_date)
                 ORDER BY amount DESC) AS monthly_rank,
    LAG(amount, 1) OVER (PARTITION BY user_id ORDER BY order_date) AS prev_amount
FROM orders;
-- PostgreSQL이 복잡한 실행 계획 최적화에 강점
```

```sql
-- CTE와 재귀 쿼리 (조직도, 트리 구조)
WITH RECURSIVE org_chart AS (
    SELECT id, name, parent_id, 0 AS depth
    FROM employees WHERE parent_id IS NULL

    UNION ALL

    SELECT e.id, e.name, e.parent_id, oc.depth + 1
    FROM employees e
    JOIN org_chart oc ON e.parent_id = oc.id
)
SELECT * FROM org_chart ORDER BY depth, name;
-- PostgreSQL에서 자연스러운 문법, MySQL 8.0에서도 지원하나 최적화 차이
```

---

## 확장 생태계

### MySQL 확장

MySQL은 스토리지 엔진 플러그인 방식이다.

```sql
-- MySQL 스토리지 엔진 확인
SHOW ENGINES;
-- InnoDB (기본), MyISAM, MEMORY, CSV 등

-- 플러그인 목록
SHOW PLUGINS;
```

### PostgreSQL 확장

```sql
-- PostgreSQL 확장 설치
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID 생성
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- 암호화
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- 삼중자 유사도 검색
CREATE EXTENSION IF NOT EXISTS "hstore";         -- 키-값 타입
CREATE EXTENSION IF NOT EXISTS "timescaledb";    -- 시계열 DB
CREATE EXTENSION IF NOT EXISTS "postgis";        -- 지리정보 (업계 표준)
CREATE EXTENSION IF NOT EXISTS "pg_vector";      -- 벡터 검색 (AI/ML)

-- 확장 활용: pg_trgm으로 LIKE 검색 인덱싱
CREATE INDEX idx_trgm ON users USING GIN(name gin_trgm_ops);
SELECT * FROM users WHERE name LIKE '%철수%';  -- 인덱스 활용 가능
```

특히 `pgvector`는 AI/ML 워크로드에서 주목받고 있다. 벡터 임베딩을 저장하고 ANN(근사 최근접 이웃) 검색을 수행한다.

```sql
-- pgvector — 벡터 유사도 검색
CREATE EXTENSION vector;

CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT,
    embedding VECTOR(1536)  -- OpenAI text-embedding-ada-002
);

CREATE INDEX ON documents USING ivfflat(embedding vector_cosine_ops)
    WITH (lists = 100);

-- 가장 유사한 문서 5개 검색
SELECT id, content,
       1 - (embedding <=> '[0.1, 0.2, ...]') AS similarity
FROM documents
ORDER BY embedding <=> '[0.1, 0.2, ...]'
LIMIT 5;
```

---

## 라이선스와 클라우드 지원

### MySQL 라이선스

MySQL은 GPL v2로 배포된다. 오픈소스 애플리케이션에서 무료지만, 상용 배포 시 Oracle 상용 라이선스가 필요할 수 있다. MariaDB(커뮤니티 포크)는 순수 GPL로 대안이 된다.

AWS Aurora MySQL은 MySQL 호환 엔진으로 쿼리 성능을 5배 향상했다고 주장한다.

### PostgreSQL 라이선스

PostgreSQL License는 BSD/MIT 계열의 매우 자유로운 라이선스다. 상용 제품에 포함해도 소스 공개 의무가 없다. 이 덕분에 Citus(분산 PostgreSQL), TimescaleDB, AlloyDB(Google) 같은 상용 확장판이 활발하다.

```
클라우드 관리형 DB 지원:
MySQL:      AWS RDS MySQL, AWS Aurora MySQL, Cloud SQL MySQL, Azure Database for MySQL
PostgreSQL: AWS RDS PostgreSQL, AWS Aurora PostgreSQL, Cloud SQL PostgreSQL,
            Azure Database for PostgreSQL, Google AlloyDB, Neon (서버리스)
```

PostgreSQL 기반 클라우드 서비스가 더 다양하고, 특히 서버리스(Neon, PlanetScale Postgres 기반)에서 활발하다.

---

## 실무 선택 기준

### MySQL이 유리한 경우

```sql
-- 1. 단순 CRUD 중심 웹 애플리케이션
--    WordPress, 소규모 이커머스, CMS

-- 2. 팀이 MySQL에 익숙한 경우

-- 3. 레거시 시스템과의 호환성

-- 4. 읽기 처리량이 최우선인 경우
--    단순 PK 조회, 인덱스 스캔이 대부분

-- 5. AWS Aurora MySQL을 활용하는 경우
--    자동 스케일링 스토리지, 6-way 복제
```

### PostgreSQL이 유리한 경우

```sql
-- 1. 복잡한 쿼리, 분석 워크로드
--    윈도우 함수, CTE, 재귀 쿼리를 자주 사용

-- 2. JSONB를 적극 활용하는 경우
--    반정형 데이터, 이벤트 소싱, EAV 패턴

-- 3. 지리정보 처리
--    PostGIS가 필요한 배달, 부동산, 물류 서비스

-- 4. AI/ML 워크로드
--    pgvector로 벡터 검색, RAG 시스템 구축

-- 5. 강한 데이터 무결성이 필요한 경우
--    금융, 의료 시스템 — PostgreSQL의 ACID가 더 엄격

-- 6. 확장 가능한 스키마
--    커스텀 타입, 연산자, 인덱스 접근 방법이 필요
```

---

## 극한 시나리오

### 시나리오 1: VACUUM 폭발 — 트랜잭션 ID 고갈

PostgreSQL에서 가장 유명한 장애 시나리오. 트랜잭션 ID(XID)는 32비트 정수로 약 21억 개다. 순환식이라 오래된 트랜잭션이 "새것"처럼 보이는 문제가 발생한다.

```sql
-- XID 고갈 모니터링
SELECT datname,
       age(datfrozenxid) AS xid_age,
       2000000000 - age(datfrozenxid) AS remaining_xids
FROM pg_database
ORDER BY xid_age DESC;

-- xid_age가 2억을 넘으면 경고, 15억을 넘으면 비상
```

```bash
# VACUUM FREEZE — XID를 FrozenXID로 교체하여 고갈 방지
# autovacuum이 정상 작동하면 자동으로 처리
vacuumdb --freeze --all --analyze

# postgresql.conf
autovacuum_freeze_max_age = 200000000  # 기본값: 2억
```

MySQL에는 이런 문제가 없다. undo 로그 기반이라 XID 고갈이 없다.

### 시나리오 2: 대규모 UPDATE — Bloat 문제

PostgreSQL에서 전체 테이블 대규모 UPDATE.

```sql
-- 1000만 행 UPDATE
UPDATE orders SET status = 'ARCHIVED' WHERE created_at < '2024-01-01';
-- 결과: 테이블 크기 2배 증가! (죽은 튜플이 쌓임)
```

PostgreSQL은 UPDATE를 "구 버전 삭제 + 새 버전 삽입"으로 처리한다. 구 버전이 죽은 튜플로 남아 테이블을 부풀린다(Bloat).

```sql
-- 테이블 Bloat 확인
SELECT tablename,
       pg_size_pretty(pg_total_relation_size(tablename::text)) AS total_size,
       pg_size_pretty(pg_total_relation_size(tablename::text) -
                      pg_relation_size(tablename::text)) AS toast_and_index
FROM pg_tables WHERE schemaname = 'public';

-- 해결책: VACUUM FULL (잠금 필요) 또는 pg_repack (무중단)
-- pg_repack 확장으로 서비스 중단 없이 테이블 재구성
```

MySQL은 InnoDB가 undo 로그를 별도 관리하므로 이 문제가 없다.

### 시나리오 3: MySQL ENUM 지옥

```sql
-- MySQL ENUM — 한번 정하면 변경이 고통
CREATE TABLE orders (
    status ENUM('PENDING', 'PAID', 'SHIPPED', 'DELIVERED', 'CANCELLED')
);

-- 새 상태 추가 — 전체 테이블 재구성 (테이블 잠금!)
ALTER TABLE orders MODIFY status
    ENUM('PENDING', 'PAID', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'REFUNDED');
-- orders 테이블이 1억 행이면 수 시간 소요
```

```sql
-- PostgreSQL에서의 올바른 패턴
-- 방법 1: CHECK CONSTRAINT (유연함)
ALTER TABLE orders
    ADD CONSTRAINT chk_status
    CHECK (status IN ('PENDING', 'PAID', 'SHIPPED', 'DELIVERED', 'CANCELLED'));

-- 새 상태 추가 — 제약 조건만 변경 (즉시)
ALTER TABLE orders DROP CONSTRAINT chk_status;
ALTER TABLE orders
    ADD CONSTRAINT chk_status
    CHECK (status IN ('PENDING', 'PAID', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'REFUNDED'));

-- 방법 2: PostgreSQL ENUM (타입으로 관리)
CREATE TYPE order_status AS ENUM ('PENDING', 'PAID', 'SHIPPED');
ALTER TYPE order_status ADD VALUE 'REFUNDED';  -- 무중단으로 값 추가 가능
```

---

## 면접 포인트

### Q. MySQL InnoDB와 PostgreSQL의 MVCC 구현 차이는?

MySQL InnoDB는 현재 데이터를 테이블 페이지에 저장하고, 이전 버전을 별도의 undo 로그에 유지합니다. 이전 버전이 필요한 트랜잭션은 undo 로그 체인을 따라갑니다. VACUUM이 필요 없지만, 긴 트랜잭션이 있으면 undo 로그가 무한정 커질 수 있습니다. PostgreSQL은 모든 버전을 같은 테이블 페이지에 저장하고, 각 튜플에 xmin/xmax로 가시성을 표시합니다. 죽은 튜플을 주기적으로 정리하는 VACUUM이 필수입니다.

### Q. PostgreSQL의 VACUUM이 중요한 이유는?

PostgreSQL MVCC 특성상 UPDATE와 DELETE 시 이전 버전 튜플이 페이지에 남습니다(죽은 튜플). VACUUM이 이를 정리하지 않으면 테이블 크기가 계속 증가하고(Bloat), 인덱스 스캔 효율이 떨어집니다. 또한 트랜잭션 ID(XID)가 32비트이므로 주기적으로 VACUUM FREEZE를 통해 XID를 고정하지 않으면 약 21억 트랜잭션 후 XID 고갈이 발생합니다. autovacuum이 정상 동작하면 자동으로 처리되지만, 대규모 테이블이나 대량 DML 후에는 수동 VACUUM이 필요할 수 있습니다.

### Q. MySQL 클러스터드 인덱스와 PostgreSQL 힙 구조의 차이는?

MySQL InnoDB는 Primary Key가 클러스터드 인덱스입니다. 테이블 데이터가 PK 순서로 물리적으로 정렬되어 저장됩니다. PK로 조회할 때 인덱스가 곧 데이터이므로 추가 I/O가 없습니다. 세컨더리 인덱스는 PK 값을 저장하므로 세컨더리 → PK → 데이터의 두 단계 조회가 필요합니다. PostgreSQL은 모든 인덱스가 힙 페이지의 물리적 위치(CTID)를 가리킵니다. 어떤 인덱스로 조회해도 같은 구조이지만, 인덱스 → 힙 페이지 방문이 항상 발생합니다.

### Q. PostgreSQL JSONB가 MySQL JSON보다 강력한 이유는?

JSONB는 바이너리 형태로 저장되어 파싱이 빠릅니다. 또한 GIN 인덱스로 JSONB 전체를 인덱싱하거나, 특정 경로의 값을 인덱싱할 수 있습니다. `@>` 연산자로 포함 관계를 인덱스로 검색할 수 있습니다. MySQL JSON은 가상 컬럼을 만들어야만 인덱싱이 가능하고, 쿼리 문법이 복잡합니다. PostgreSQL JSONB는 집계 함수(`jsonb_agg`), 경로 조회(`#>>`), 포함 연산자(`@>`, `<@`)가 풍부하여 반정형 데이터 처리에 훨씬 강력합니다.

### Q. 어떤 상황에서 MySQL, 어떤 상황에서 PostgreSQL을 선택하겠는가?

MySQL은 단순 CRUD 중심의 웹 서비스, 팀이 MySQL에 익숙한 경우, 읽기 처리량이 최우선인 경우에 적합합니다. 특히 AWS Aurora MySQL처럼 클라우드 최적화 버전을 쓴다면 더 유리합니다. PostgreSQL은 복잡한 쿼리와 분석 워크로드, JSONB 적극 활용, 지리정보 처리(PostGIS), AI/ML 벡터 검색(pgvector), 강한 데이터 무결성이 필요한 금융/의료 도메인에서 선택합니다. 신규 프로젝트라면 저는 기능적 우위와 라이선스 자유도 때문에 PostgreSQL을 기본으로 고려합니다.

---

## 결론

두 데이터베이스 모두 2026년에도 강력한 선택지다. MySQL 8.0은 JSON, CTE, 윈도우 함수를 지원하며 많이 발전했다. PostgreSQL은 pgvector, TimescaleDB 등 확장으로 더 넓은 사용 영역을 커버한다.

**MySQL**: 단순함, 성숙한 생태계, 읽기 처리량, Oracle/AWS Aurora 지원이 필요할 때.

**PostgreSQL**: 복잡한 쿼리, JSON/배열, 지리정보, 벡터 검색, 확장성, 엄격한 SQL 표준 준수가 필요할 때.

새로 시작한다면 PostgreSQL의 기능적 풍부함과 자유로운 라이선스가 대부분의 상황에서 유리하다. 레거시 MySQL 시스템은 마이그레이션 비용을 충분히 계산하고 이전을 결정하라.
