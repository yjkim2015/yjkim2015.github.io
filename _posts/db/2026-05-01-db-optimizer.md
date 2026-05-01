---
title: "MySQL 옵티마이저 동작 원리 완전 정리"
categories:
- DB
toc: true
toc_sticky: true
toc_label: 목차
---

MySQL이 SQL을 받아 결과를 돌려주기까지, 내부에서는 생각보다 많은 일이 일어납니다. 그 핵심에는 **옵티마이저(Optimizer)**가 있습니다. 같은 결과를 내는 쿼리라도 실행 방법은 수백 가지가 될 수 있고, 옵티마이저는 그중 가장 비용이 낮은 방법을 선택합니다. 이 글에서는 쿼리가 실행되는 전체 흐름부터 옵티마이저의 내부 동작, EXPLAIN 분석, 최적화 기법, 그리고 실무 튜닝 체크리스트까지 완전히 정리합니다.

---

## 1. 쿼리 실행 흐름 전체

MySQL에서 SQL 쿼리 하나가 결과로 돌아오기까지 다섯 단계를 거칩니다.

```
클라이언트
    │
    │  SQL 문자열
    ▼
┌─────────────────────────────────────────────────────┐
│                   MySQL Server                      │
│                                                     │
│  ┌──────────┐                                       │
│  │  Parser  │  ← 문법 파싱, AST 생성                │
│  └────┬─────┘                                       │
│       │  AST (Abstract Syntax Tree)                 │
│       ▼                                             │
│  ┌──────────────┐                                   │
│  │ Preprocessor │  ← 권한 확인, 테이블/컬럼 존재 검증 │
│  └──────┬───────┘                                   │
│         │  검증된 AST                               │
│         ▼                                           │
│  ┌───────────┐                                      │
│  │ Optimizer │  ← 비용 계산, 실행 계획 선택          │
│  └─────┬─────┘                                      │
│        │  실행 계획 (Execution Plan)                 │
│        ▼                                            │
│  ┌──────────────────┐                               │
│  │ Execution Engine │  ← 계획대로 Storage Engine 호출│
│  └────────┬─────────┘                               │
│           │  레코드 요청 / 반환                      │
│           ▼                                         │
│  ┌────────────────┐                                 │
│  │ Storage Engine │  ← InnoDB, MyISAM 등            │
│  │  (InnoDB)      │    실제 디스크 I/O 처리          │
│  └────────────────┘                                 │
└─────────────────────────────────────────────────────┘
    │
    │  결과셋
    ▼
클라이언트
```

### 1-1. Parser (파서)

SQL 문자열을 받아 문법적으로 올바른지 검사하고 **AST(Abstract Syntax Tree)**를 생성합니다.

- 토크나이징: `SELECT`, `*`, `FROM`, `users`, `WHERE`, `id`, `=`, `1` 로 분리
- 문법 오류 시 `ERROR 1064 (42000): You have an error in your SQL syntax...` 반환
- 이 단계에서는 테이블/컬럼이 실제로 존재하는지 확인하지 않습니다.

### 1-2. Preprocessor (전처리기)

AST를 받아 **의미론적 검증**을 수행합니다.

- 테이블, 컬럼, 함수가 실제로 존재하는지 확인
- 사용자의 접근 권한 검사
- `*` 를 실제 컬럼 목록으로 확장
- 뷰(View)를 실제 쿼리로 전개

### 1-3. Optimizer (옵티마이저)

이 글의 핵심 단계입니다. 검증된 AST를 받아 **가장 비용이 낮은 실행 계획**을 선택합니다. 자세한 내용은 이후 섹션에서 다룹니다.

### 1-4. Execution Engine (실행 엔진)

옵티마이저가 만든 실행 계획을 **스토리지 엔진 API를 호출**하며 실행합니다.

- 핸들러 API(handler API)를 통해 스토리지 엔진과 통신
- JOIN, 정렬, 집계 등 고수준 연산 처리
- 스토리지 엔진은 레코드 단위로 데이터를 올려줍니다.

### 1-5. Storage Engine (스토리지 엔진)

실제 데이터가 디스크에 어떻게 저장되고 읽히는지를 담당합니다.

- **InnoDB**: 트랜잭션, MVCC, 외래 키, 클러스터드 인덱스 지원 (기본값)
- **MyISAM**: 트랜잭션 없음, 풀텍스트 인덱스
- **Memory**: 인메모리 테이블

---

## 2. 옵티마이저란?

### 2-1. 비용 기반 옵티마이저 (Cost-Based Optimizer, CBO)

MySQL 5.x 이후 MySQL은 **CBO(Cost-Based Optimizer)**를 사용합니다. CBO는 가능한 실행 계획들을 열거하고, 각각의 예상 비용(cost)을 계산해 가장 낮은 비용의 계획을 선택합니다.

비용은 내부 단위로 표현되며, `mysql.server_cost`와 `mysql.engine_cost` 시스템 테이블에 저장됩니다.

```sql
-- 비용 단위 확인
SELECT * FROM mysql.server_cost;
SELECT * FROM mysql.engine_cost;
```

| 비용 항목 | 기본값 | 의미 |
|---|---|---|
| `row_evaluate_cost` | 0.1 | 레코드 하나 평가 비용 |
| `key_compare_cost` | 0.05 | 인덱스 키 비교 비용 |
| `memory_temptable_create_cost` | 1.0 | 인메모리 임시 테이블 생성 |
| `memory_temptable_row_cost` | 0.1 | 인메모리 임시 테이블 레코드 |
| `disk_temptable_create_cost` | 20.0 | 디스크 임시 테이블 생성 |
| `disk_temptable_row_cost` | 0.5 | 디스크 임시 테이블 레코드 |
| `io_block_read_cost` | 1.0 | 디스크 블록 읽기 |
| `memory_block_read_cost` | 0.25 | 버퍼풀에서 블록 읽기 |

### 2-2. 규칙 기반 옵티마이저 (RBO) vs CBO

| 구분 | RBO (Rule-Based Optimizer) | CBO (Cost-Based Optimizer) |
|---|---|---|
| 판단 기준 | 미리 정해진 규칙 | 통계 기반 비용 계산 |
| 통계 의존 | 없음 | 높음 |
| 유연성 | 낮음 | 높음 |
| 대표 DB | 과거 Oracle, 과거 MySQL | MySQL 5.x+, 현재 Oracle |
| 단점 | 데이터 분포 무시 | 통계 부정확 시 잘못된 계획 |

RBO는 "인덱스가 있으면 무조건 인덱스를 사용한다" 같은 고정 규칙을 따릅니다. 데이터가 100건이든 1억 건이든 규칙이 동일하게 적용되어 비효율적인 경우가 많습니다.

CBO는 실제 데이터 분포와 통계 정보를 바탕으로 최적 경로를 탐색합니다. MySQL의 현재 옵티마이저가 여기에 해당합니다.

---

## 3. 옵티마이저가 고려하는 비용 요소

### 3-1. I/O 비용 (디스크 읽기)

가장 큰 비용 요소입니다. 디스크에서 데이터를 읽는 행위는 메모리 접근보다 수십~수천 배 느립니다.

- **풀 테이블 스캔**: 테이블의 모든 데이터 페이지를 읽음
- **인덱스 스캔**: 인덱스 페이지 + 데이터 페이지(랜덤 I/O)
- **버퍼풀 히트**: 이미 메모리에 올라온 페이지는 I/O 없음

옵티마이저는 `innodb_buffer_pool_size` 대비 테이블 크기를 고려해 페이지가 버퍼풀에 있을 가능성도 추정합니다.

### 3-2. CPU 비용 (비교, 정렬)

- 레코드 조건 평가 (WHERE 절 비교 연산)
- 정렬 (ORDER BY, GROUP BY)
- 집계 함수 연산 (SUM, COUNT, AVG)
- 해시 테이블 생성 (Hash Join)

### 3-3. 통계 정보 (Statistics)

옵티마이저는 실제 데이터를 전부 읽지 않고, **통계 정보**를 바탕으로 비용을 추정합니다.

**테이블 통계:**

```sql
-- 테이블 통계 확인 (information_schema)
SELECT
    TABLE_NAME,
    TABLE_ROWS,       -- 추정 행 수
    AVG_ROW_LENGTH,   -- 평균 행 길이 (바이트)
    DATA_LENGTH,      -- 데이터 크기
    INDEX_LENGTH      -- 인덱스 크기
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'mydb';
```

**인덱스 통계:**

```sql
-- 인덱스 카디널리티 확인
SELECT
    TABLE_NAME,
    INDEX_NAME,
    COLUMN_NAME,
    CARDINALITY  -- 인덱스의 유니크 값 추정 수
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'mydb'
ORDER BY TABLE_NAME, INDEX_NAME;
```

**카디널리티(Cardinality)**는 인덱스의 선택도를 나타냅니다. `CARDINALITY / TABLE_ROWS`가 1에 가까울수록 선택도가 높아 인덱스 효과가 큽니다.

예: 100만 건 테이블에서
- `gender` 컬럼 (M/F 2가지): 카디널리티 ≈ 2 → 선택도 낮음 → 인덱스 효과 거의 없음
- `email` 컬럼 (거의 유니크): 카디널리티 ≈ 100만 → 선택도 높음 → 인덱스 매우 효과적

### 3-4. ANALYZE TABLE의 역할

통계 정보는 자동으로 갱신되지만, 대량 INSERT/DELETE/UPDATE 후에는 통계가 부정확해질 수 있습니다. 이때 `ANALYZE TABLE`을 실행해 통계를 재수집합니다.

```sql
-- 통계 재수집
ANALYZE TABLE users;
ANALYZE TABLE orders, products;  -- 여러 테이블 동시 가능
```

InnoDB는 샘플 페이지 수(`innodb_stats_sample_pages`, 기본 8)를 늘려 정확도를 높일 수 있습니다.

```sql
-- 영구적으로 더 많은 샘플 사용 (재시작 유지)
ALTER TABLE users STATS_SAMPLE_PAGES = 50;

-- 전역 설정
SET GLOBAL innodb_stats_sample_pages = 20;
```

**자동 통계 갱신 설정:**

```sql
-- 테이블 행의 10% 이상 변경 시 자동 재계산 (기본 ON)
SHOW VARIABLES LIKE 'innodb_stats_auto_recalc';
```

---

## 4. 실행 계획 (EXPLAIN) 완전 분석

`EXPLAIN`은 옵티마이저가 선택한 실행 계획을 보여주는 핵심 도구입니다.

```sql
EXPLAIN SELECT u.name, COUNT(o.id) AS order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at >= '2025-01-01'
GROUP BY u.id
ORDER BY order_count DESC
LIMIT 10;
```

출력 예시:

```
+----+-------------+-------+------------+-------+------------------+---------+---------+------------------+------+----------+----------------------------------------------+
| id | select_type | table | partitions | type  | possible_keys    | key     | key_len | ref              | rows | filtered | Extra                                        |
+----+-------------+-------+------------+-------+------------------+---------+---------+------------------+------+----------+----------------------------------------------+
|  1 | SIMPLE      | u     | NULL       | range | idx_created_at   | idx_created_at | 5 | NULL          | 1520 |   100.00 | Using index condition; Using temporary; Using filesort |
|  1 | SIMPLE      | o     | NULL       | ref   | idx_user_id      | idx_user_id    | 4 | mydb.u.id     |    3 |   100.00 | NULL                                         |
+----+-------------+-------+------------+-------+------------------+---------+---------+------------------+------+----------+----------------------------------------------+
```

### 4-1. 각 컬럼 상세 설명

**`id`**
- 쿼리 내 SELECT 구문의 순서 번호
- 숫자가 같으면 같은 쿼리 단계 (위에서 아래로 실행)
- 숫자가 다르면 서브쿼리 (큰 번호가 먼저 실행)

```sql
-- id 예시
EXPLAIN
SELECT * FROM users WHERE id IN (
    SELECT user_id FROM orders WHERE total > 10000  -- id=2 (먼저 실행)
);
-- id=1: users, id=2: orders (서브쿼리)
```

**`select_type`**

| 값 | 설명 |
|---|---|
| `SIMPLE` | 서브쿼리/UNION 없는 단순 SELECT |
| `PRIMARY` | 가장 바깥쪽 SELECT |
| `SUBQUERY` | FROM 절 외의 서브쿼리 |
| `DERIVED` | FROM 절의 서브쿼리 (파생 테이블) |
| `UNION` | UNION의 두 번째 이후 SELECT |
| `UNION RESULT` | UNION 결과를 담는 임시 테이블 |
| `DEPENDENT SUBQUERY` | 외부 쿼리에 의존하는 서브쿼리 |
| `MATERIALIZED` | Materialized 서브쿼리 |

**`table`**
- 접근하는 테이블명
- `<derivedN>`: id=N인 파생 테이블
- `<unionM,N>`: M,N번 UNION 결과

**`partitions`**
- 파티셔닝된 테이블에서 접근하는 파티션
- `NULL`이면 파티셔닝 없음

**`type`** — 가장 중요한 컬럼. 아래에서 상세 설명.

**`possible_keys`**
- 사용 가능한 인덱스 후보 목록
- `NULL`이면 인덱스를 쓸 수 없음

**`key`**
- 실제로 선택된 인덱스
- `NULL`이면 인덱스 미사용 (풀 테이블 스캔)

**`key_len`**
- 사용된 인덱스의 바이트 수
- 복합 인덱스에서 몇 개 컬럼이 사용됐는지 추론 가능
- 예: `INT NOT NULL` = 4바이트, `VARCHAR(100) NOT NULL utf8mb4` = 400바이트

**`ref`**
- 인덱스와 비교되는 값 (상수, 컬럼, 함수)
- `const`: 상수와 비교 (`WHERE id = 1`)
- `mydb.u.id`: 다른 테이블의 컬럼과 비교 (JOIN)

**`rows`**
- 옵티마이저가 읽어야 한다고 추정하는 행 수
- 실제 값이 아닌 추정값 (통계 기반)
- 낮을수록 좋음

**`filtered`**
- 조건에 의해 필터링되고 남을 비율 (%)
- `rows * filtered / 100` = 실제로 상위 단계로 전달되는 예상 행 수
- 100%에 가까울수록 조건이 인덱스에 포함됨을 의미

**`Extra`** — 아래에서 상세 설명.

### 4-2. type 컬럼 상세 (성능 순서: 좋음 → 나쁨)

```
system > const > eq_ref > ref > fulltext > ref_or_null
       > index_merge > unique_subquery > index_subquery
       > range > index > ALL
```

**`system`**
- 테이블에 행이 정확히 1개 (시스템 테이블)
- 거의 볼 일 없음

**`const`**
- PRIMARY KEY 또는 UNIQUE KEY를 상수와 비교
- 결과가 최대 1건, 매우 빠름

```sql
-- type = const
EXPLAIN SELECT * FROM users WHERE id = 1;
-- id는 PK이므로 const
```

**`eq_ref`**
- JOIN 시 드리븐(driven) 테이블의 PK 또는 UNIQUE KEY로 JOIN
- JOIN되는 행마다 정확히 1건 매칭

```sql
-- type = eq_ref (orders의 user_id가 users의 PK와 JOIN)
EXPLAIN
SELECT * FROM orders o
JOIN users u ON o.user_id = u.id;
-- u 테이블: eq_ref
```

**`ref`**
- UNIQUE가 아닌 인덱스를 동등 조건으로 사용
- 여러 행이 매칭될 수 있음

```sql
-- idx_status가 일반 인덱스일 때
EXPLAIN SELECT * FROM orders WHERE status = 'pending';
-- type = ref
```

**`range`**
- 인덱스의 특정 범위만 스캔
- `BETWEEN`, `>`, `<`, `>=`, `<=`, `IN`, `LIKE 'abc%'` 등

```sql
EXPLAIN SELECT * FROM orders WHERE created_at BETWEEN '2025-01-01' AND '2025-12-31';
-- type = range
```

**`index`**
- 인덱스 전체를 스캔 (풀 인덱스 스캔)
- 데이터 파일은 읽지 않음 (커버링 인덱스) 또는 인덱스 순서로 전체 스캔
- `ALL`보다는 빠르지만 여전히 느림

```sql
-- idx_name이 있고 name만 SELECT할 경우 커버링 인덱스
EXPLAIN SELECT name FROM users ORDER BY name;
-- type = index (전체 인덱스 순회)
```

**`ALL`**
- 풀 테이블 스캔 (Full Table Scan)
- 가장 느림. 인덱스 없거나 선택도 낮을 때 발생
- 수백만 건 테이블에서 ALL은 큰 문제

```sql
EXPLAIN SELECT * FROM users WHERE YEAR(created_at) = 2025;
-- 함수 적용으로 인덱스 사용 불가 → type = ALL
```

**성능 기준점:**
- `system`, `const`, `eq_ref`, `ref`: 정상 범위
- `range`: 주의 (범위가 너무 넓으면 문제)
- `index`: 개선 여지 있음
- `ALL`: 반드시 검토 필요

### 4-3. Extra 컬럼 주요값

**`Using index` (긍정적)**
- **커버링 인덱스** 사용: 인덱스만으로 모든 컬럼을 제공
- 데이터 파일 접근 없음 → 매우 빠름

```sql
-- (user_id, status) 복합 인덱스가 있을 때
EXPLAIN SELECT user_id, status FROM orders WHERE user_id = 100;
-- Extra: Using index
```

**`Using where` (보통)**
- 스토리지 엔진에서 레코드를 가져온 후 서버 레이어에서 추가 필터링
- 인덱스로 걸러지지 않은 조건이 WHERE에 있음

**`Using temporary` (주의)**
- GROUP BY, ORDER BY, DISTINCT 처리를 위해 임시 테이블 생성
- 메모리 또는 디스크에 임시 테이블 생성 → 느림

```sql
-- GROUP BY 컬럼에 인덱스가 없으면 임시 테이블 발생
EXPLAIN SELECT status, COUNT(*) FROM orders GROUP BY status;
-- Extra: Using temporary; Using filesort
```

**`Using filesort` (주의)**
- ORDER BY를 인덱스가 아닌 별도 정렬 알고리즘으로 처리
- 인메모리 또는 디스크 정렬 발생

```sql
-- order_date에 인덱스 없으면
EXPLAIN SELECT * FROM orders ORDER BY order_date DESC LIMIT 10;
-- Extra: Using filesort
```

**`Using index condition` (긍정적)**
- **Index Condition Pushdown (ICP)** 사용
- 인덱스에서 조건을 먼저 평가해 불필요한 레코드 접근 줄임

**`Using join buffer (Block Nested Loop)` (주의)**
- JOIN 컬럼에 인덱스 없어 조인 버퍼 사용
- MySQL 8.0.18 미만: Block Nested Loop
- MySQL 8.0.18 이상: Hash Join으로 개선

**`Select tables optimized away` (긍정적)**
- MIN/MAX 등을 인덱스만으로 즉시 계산

```sql
EXPLAIN SELECT MAX(id) FROM users;
-- Extra: Select tables optimized away
```

**`Impossible WHERE` (특이)**
- 항상 거짓인 WHERE 조건: 결과가 0건
- 예: `WHERE 1 = 2`, `WHERE id IS NULL AND id IS NOT NULL`

### 4-4. EXPLAIN ANALYZE (MySQL 8.0+)

`EXPLAIN`은 **추정값**을 보여주지만, `EXPLAIN ANALYZE`는 쿼리를 **실제 실행**하고 실제 통계를 반환합니다.

```sql
EXPLAIN ANALYZE
SELECT u.name, COUNT(o.id)
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at >= '2025-01-01'
GROUP BY u.id;
```

출력 예시:
```
-> Table scan on <temporary>  (actual time=5.123..5.456 rows=1520 loops=1)
    -> Aggregate using temporary table  (actual time=4.234..4.234 rows=1520 loops=1)
        -> Nested loop left join  (cost=2345.67 rows=4560) (actual time=0.123..3.456 rows=4560 loops=1)
            -> Filter: (u.created_at >= '2025-01-01')  (cost=456.78 rows=1520) (actual time=0.089..1.234 rows=1520 loops=1)
                -> Index range scan on u using idx_created_at  (cost=456.78 rows=1520) (actual time=0.089..0.789 rows=1520 loops=1)
            -> Index lookup on o using idx_user_id (user_id=u.id)  (cost=0.90 rows=3) (actual time=0.001..0.002 rows=3 loops=1520)
```

- `cost=X`: 옵티마이저 추정 비용
- `rows=X`: 옵티마이저 추정 행 수
- `actual time=X..Y`: 실제 첫 행..마지막 행 반환 시간 (밀리초)
- `actual rows=X`: 실제 반환된 행 수
- `loops=X`: 해당 단계 반복 횟수

추정(`rows`)과 실제(`actual rows`)의 차이가 크면 통계 부정확 신호입니다.

### 4-5. EXPLAIN FORMAT=JSON / TREE

**FORMAT=JSON**: 더 상세한 비용 정보 포함

```sql
EXPLAIN FORMAT=JSON
SELECT * FROM users WHERE id = 1\G
```

```json
{
  "query_block": {
    "select_id": 1,
    "cost_info": {
      "query_cost": "1.00"
    },
    "table": {
      "table_name": "users",
      "access_type": "const",
      "possible_keys": ["PRIMARY"],
      "key": "PRIMARY",
      "used_key_parts": ["id"],
      "key_length": "4",
      "ref": ["const"],
      "rows_examined_per_scan": 1,
      "rows_produced_per_join": 1,
      "filtered": "100.00",
      "cost_info": {
        "read_cost": "0.00",
        "eval_cost": "0.10",
        "prefix_cost": "0.00",
        "data_read_per_join": "184"
      },
      "used_columns": ["id", "name", "email", "created_at"]
    }
  }
}
```

**FORMAT=TREE** (MySQL 8.0.16+): 계층적 트리 구조로 표현

```sql
EXPLAIN FORMAT=TREE
SELECT * FROM users u JOIN orders o ON u.id = o.user_id WHERE u.id = 100\G
```

```
-> Nested loop inner join  (cost=4.25 rows=3)
    -> Rows fetched before execution  (cost=0.00 rows=1)
    -> Index lookup on o using idx_user_id (user_id=100)  (cost=3.26 rows=3)
```

---

## 5. 옵티마이저 최적화 기법

### 5-1. 서브쿼리 최적화

**Materialization (구체화)**

서브쿼리 결과를 임시 테이블에 저장해 반복 실행을 방지합니다.

```sql
-- 이 서브쿼리는 Materialization으로 처리될 수 있음
SELECT * FROM orders
WHERE user_id IN (
    SELECT id FROM users WHERE grade = 'VIP'
);
```

서브쿼리 결과를 한 번만 실행해 임시 테이블에 저장 → 임시 테이블에 자동 인덱스 생성 → 외부 쿼리가 인덱스로 조인.

**Semi-join 최적화**

`IN (subquery)` 또는 `EXISTS (subquery)` 패턴에서 중복 없이 매칭 여부만 확인합니다.

```
Semi-join 전략:
1. Duplicate Weedout: JOIN 후 중복 제거
2. FirstMatch: 첫 번째 매칭 후 즉시 중단
3. LooseScan: 인덱스 스캔 시 그룹별 첫 값만 사용
4. Materialization: 결과를 임시 테이블로 구체화
```

```sql
-- Semi-join이 적용되는 전형적 패턴
SELECT * FROM orders o
WHERE EXISTS (
    SELECT 1 FROM order_items oi WHERE oi.order_id = o.id AND oi.product_id = 100
);
```

### 5-2. JOIN 최적화

**Nested Loop Join (NLJ)**

가장 기본적인 JOIN 방법. 드라이빙 테이블의 각 행에 대해 드리븐 테이블을 탐색합니다.

```
for each row in driving_table:            -- 외부 루프
    for each row in driven_table:         -- 내부 루프
        if join_condition:
            output row
```

드리븐 테이블에 인덱스가 있어야 효율적. 없으면 BNL 또는 Hash Join으로 대체.

**Block Nested Loop (BNL) — MySQL 8.0.18 미만**

JOIN 컬럼에 인덱스 없을 때 사용. Join Buffer(기본 256KB)에 드라이빙 테이블 행들을 모아 블록 단위로 처리.

```sql
SHOW VARIABLES LIKE 'join_buffer_size';
SET SESSION join_buffer_size = 4 * 1024 * 1024;  -- 4MB로 증가
```

**Hash Join (MySQL 8.0.18+)**

BNL을 대체. 드라이빙 테이블로 해시 테이블 빌드 → 드리븐 테이블로 프로브.

```
Build phase:  드라이빙 테이블 행 → 해시 테이블 생성
Probe phase:  드리븐 테이블 각 행 → 해시 테이블 탐색
```

- 인덱스 없는 JOIN에서 BNL보다 훨씬 빠름
- 등치 JOIN(`=`)에서만 사용 가능
- `EXPLAIN` Extra에 `Using join buffer (hash join)` 표시

```sql
-- Hash Join 강제 사용 (MySQL 8.0.18+)
SELECT /*+ HASH_JOIN(u o) */ *
FROM users u JOIN orders o ON u.id = o.user_id;
```

**JOIN 순서 최적화**

옵티마이저는 테이블이 n개일 때 n! 가지 JOIN 순서 중 비용이 낮은 것을 선택합니다. 테이블이 많아지면 `optimizer_search_depth`로 탐색 깊이를 제한합니다.

```sql
SHOW VARIABLES LIKE 'optimizer_search_depth';
-- 기본값: 62 (실질적으로 최대 15~20개 테이블까지 완전 탐색)
```

### 5-3. Derived Table Merge (파생 테이블 병합)

FROM 절의 서브쿼리를 메인 쿼리로 병합해 불필요한 임시 테이블을 제거합니다.

```sql
-- 원래 쿼리
SELECT * FROM (
    SELECT id, name FROM users WHERE grade = 'VIP'
) AS vip_users
WHERE name LIKE 'Kim%';

-- 옵티마이저가 내부적으로 변환 (Merge)
SELECT id, name FROM users
WHERE grade = 'VIP' AND name LIKE 'Kim%';
```

`LIMIT`, `UNION`, `GROUP BY` 등이 포함된 서브쿼리는 병합되지 않습니다.

```sql
-- Merge 불가 (LIMIT 포함)
SELECT * FROM (
    SELECT * FROM users ORDER BY created_at LIMIT 100
) AS recent_users
WHERE grade = 'VIP';
```

### 5-4. Index Condition Pushdown (ICP)

인덱스 스캔 중 WHERE 조건을 스토리지 엔진 레이어에서 먼저 평가해 불필요한 레코드 읽기를 줄입니다.

```
ICP 없음:
  스토리지 엔진: 인덱스 범위 레코드 모두 읽어 서버에 전달
  서버 레이어: WHERE 조건 평가 후 필터링

ICP 있음:
  스토리지 엔진: 인덱스 읽는 중 WHERE 조건 미리 평가
                조건 통과한 레코드만 서버에 전달
```

```sql
-- 복합 인덱스 (last_name, first_name)이 있을 때
EXPLAIN SELECT * FROM users
WHERE last_name = 'Kim' AND first_name LIKE '%su';
-- Extra: Using index condition
```

ICP 활성화 여부 확인/변경:
```sql
SHOW VARIABLES LIKE 'optimizer_switch';
-- index_condition_pushdown=on 확인

SET optimizer_switch = 'index_condition_pushdown=off';  -- 비활성화 (테스트용)
```

### 5-5. Multi-Range Read (MRR)

랜덤 I/O를 순차 I/O로 전환해 성능을 향상시킵니다.

```
일반 인덱스 스캔:
  인덱스에서 PK 읽기 → PK로 데이터 파일 랜덤 접근 반복
  (인덱스 순서 ≠ 데이터 저장 순서 → 랜덤 I/O)

MRR:
  인덱스에서 PK 목록을 먼저 수집
  PK를 물리적 순서로 정렬
  정렬된 순서로 데이터 파일 접근 (준순차 I/O)
```

```sql
-- MRR 활성화 확인
SHOW VARIABLES LIKE 'optimizer_switch';
-- mrr=on, mrr_cost_based=on

EXPLAIN SELECT * FROM orders WHERE user_id BETWEEN 100 AND 200;
-- Extra: Using MRR (표시될 경우)
```

### 5-6. Batched Key Access (BKA)

MRR과 JOIN을 결합한 최적화. JOIN 시 드리븐 테이블 접근에 MRR 적용.

```sql
-- BKA 활성화 (기본값: off)
SET optimizer_switch = 'batched_key_access=on, mrr=on, mrr_cost_based=off';

EXPLAIN SELECT /*+ BKA(o) */ *
FROM users u JOIN orders o ON u.id = o.user_id
WHERE u.grade = 'VIP';
-- Extra: Using join buffer (Batched Key Access)
```

### 5-7. ORDER BY 최적화

**인덱스를 활용한 정렬 (filesort 없음)**

```sql
-- created_at에 인덱스가 있으면
SELECT * FROM orders WHERE user_id = 100 ORDER BY created_at;
-- Extra: (nothing) — 인덱스 순서로 결과 반환
```

복합 인덱스 `(user_id, created_at)`이 있으면 WHERE + ORDER BY 모두 인덱스로 처리됩니다.

**filesort가 발생하는 경우:**

```sql
-- 인덱스 없는 컬럼 정렬
SELECT * FROM orders ORDER BY total_amount;

-- WHERE와 ORDER BY 컬럼이 다른 인덱스
SELECT * FROM orders WHERE status = 'done' ORDER BY created_at;
-- (status), (created_at) 각각 인덱스 있어도 filesort 발생
-- 복합 인덱스 (status, created_at) 필요
```

**filesort 알고리즘:**

- **Single-pass**: SELECT 컬럼 + 정렬 컬럼을 sort buffer에 올려 정렬 후 직접 반환
- **Two-pass (이전 방식)**: 정렬 키 + PK만 정렬 → PK로 데이터 재접근

`sort_buffer_size`가 충분하면 메모리에서 처리, 부족하면 디스크 임시 파일 사용.

```sql
SHOW VARIABLES LIKE 'sort_buffer_size';  -- 기본 256KB
SET SESSION sort_buffer_size = 4 * 1024 * 1024;  -- 4MB
```

### 5-8. GROUP BY 최적화

**루스 인덱스 스캔 (Loose Index Scan)**

인덱스에서 각 그룹의 첫/마지막 값만 읽어 매우 빠르게 처리합니다.

```sql
-- (user_id, status) 복합 인덱스
EXPLAIN SELECT user_id, MIN(created_at), MAX(created_at)
FROM orders
GROUP BY user_id;
-- Extra: Using index for group-by (루스 인덱스 스캔)
```

**타이트 인덱스 스캔 (Tight Index Scan)**

인덱스의 모든 엔트리를 스캔하지만 데이터 파일 접근 없이 처리.

**임시 테이블 + filesort**

인덱스를 쓸 수 없을 때 발생. `Using temporary; Using filesort` 표시.

### 5-9. LIMIT 최적화

`LIMIT`은 충분한 행을 찾으면 즉시 중단할 수 있어 전체 처리를 피합니다.

```sql
-- LIMIT이 없으면 전체 정렬 후 반환
-- LIMIT이 있으면 상위 N개만 찾고 중단 가능
SELECT * FROM orders ORDER BY created_at DESC LIMIT 10;
```

단, `GROUP BY` + `HAVING` + `LIMIT`은 집계 후 LIMIT이 적용되므로 전체 처리 불가피.

**오프셋 문제 (Deep Pagination)**

```sql
-- 나쁨: OFFSET이 클수록 버려지는 행이 많아 점점 느려짐
SELECT * FROM orders ORDER BY id LIMIT 10 OFFSET 100000;

-- 좋음: Keyset Pagination (커서 기반)
SELECT * FROM orders WHERE id > 100000 ORDER BY id LIMIT 10;
```

### 5-10. IN 절 최적화

```sql
-- IN 절은 내부적으로 여러 동등 조건의 합으로 처리
SELECT * FROM orders WHERE status IN ('pending', 'processing', 'done');
-- 인덱스 있으면 range 스캔으로 처리

-- IN + 서브쿼리
SELECT * FROM users WHERE id IN (SELECT user_id FROM orders WHERE total > 100000);
-- Materialization 또는 Semi-join 적용
```

IN 절의 값이 매우 많으면 (수천 개) 쿼리 파싱 자체가 병목이 됩니다. 임시 테이블 + JOIN으로 대체를 고려하세요.

---

## 6. 옵티마이저 힌트

### 6-1. 인덱스 힌트

```sql
-- USE INDEX: 이 인덱스들 중에서 선택하도록 유도 (강제는 아님)
SELECT * FROM orders USE INDEX (idx_user_id, idx_status)
WHERE user_id = 100;

-- FORCE INDEX: 풀 테이블 스캔보다 인덱스를 강제 우선
SELECT * FROM orders FORCE INDEX (idx_created_at)
WHERE created_at >= '2025-01-01';

-- IGNORE INDEX: 이 인덱스는 사용하지 말 것
SELECT * FROM orders IGNORE INDEX (idx_status)
WHERE status = 'pending';

-- FOR ORDER BY: ORDER BY에만 힌트 적용
SELECT * FROM orders USE INDEX FOR ORDER BY (idx_created_at)
ORDER BY created_at;

-- FOR JOIN: JOIN에만 힌트 적용
SELECT * FROM orders o USE INDEX FOR JOIN (idx_user_id)
JOIN users u ON o.user_id = u.id;
```

### 6-2. 옵티마이저 힌트 (MySQL 8.0+ 권장)

주석 형태 `/*+ ... */`로 SELECT 직후에 삽입합니다.

```sql
-- 인덱스 사용 강제
SELECT /*+ INDEX(o idx_user_id) */ *
FROM orders o WHERE user_id = 100;

-- 인덱스 사용 금지
SELECT /*+ NO_INDEX(o idx_status) */ *
FROM orders o WHERE status = 'pending';

-- JOIN 순서 고정 (users를 드라이빙 테이블로)
SELECT /*+ LEADING(u o) */ *
FROM users u JOIN orders o ON u.id = o.user_id;

-- JOIN 알고리즘 지정
SELECT /*+ BNL(o) */ * FROM users u JOIN orders o ON u.id = o.user_id;
SELECT /*+ NO_BNL(o) */ * FROM users u JOIN orders o ON u.id = o.user_id;
SELECT /*+ HASH_JOIN(u o) */ * FROM users u JOIN orders o ON u.id = o.user_id;
SELECT /*+ NO_HASH_JOIN(u o) */ * FROM users u JOIN orders o ON u.id = o.user_id;

-- 서브쿼리 전략 지정
SELECT /*+ SEMIJOIN(@subq MATERIALIZATION) */ *
FROM users WHERE id IN (
    SELECT /*+ QB_NAME(subq) */ user_id FROM orders WHERE total > 10000
);

-- MRR 제어
SELECT /*+ MRR(o) */ * FROM orders o WHERE user_id BETWEEN 100 AND 200;
SELECT /*+ NO_MRR(o) */ * FROM orders o WHERE user_id BETWEEN 100 AND 200;

-- ICP 제어
SELECT /*+ NO_ICP(o) */ * FROM orders o WHERE user_id = 100 AND status LIKE 'p%';

-- 파생 테이블 병합 제어
SELECT /*+ MERGE(vip) */ * FROM (
    SELECT * FROM users WHERE grade = 'VIP'
) AS vip WHERE name LIKE 'Kim%';

SELECT /*+ NO_MERGE(vip) */ * FROM (
    SELECT * FROM users WHERE grade = 'VIP'
) AS vip WHERE name LIKE 'Kim%';

-- MAX_EXECUTION_TIME: 쿼리 타임아웃 (밀리초)
SELECT /*+ MAX_EXECUTION_TIME(3000) */ * FROM big_table;

-- SET_VAR: 해당 쿼리에만 변수 적용
SELECT /*+ SET_VAR(sort_buffer_size = 16777216) */ *
FROM orders ORDER BY total_amount;
```

### 6-3. STRAIGHT_JOIN

JOIN 순서를 SQL 작성 순서대로 강제합니다. `LEADING` 힌트보다 오래된 방법이지만 여전히 사용됩니다.

```sql
-- u → o 순서로 JOIN 강제
SELECT STRAIGHT_JOIN u.name, o.total
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.grade = 'VIP';
```

### 6-4. SQL_CALC_FOUND_ROWS 대안

과거에는 페이지네이션 총 건수를 구하기 위해 `SQL_CALC_FOUND_ROWS`를 사용했지만, MySQL 8.0부터 deprecated됩니다.

```sql
-- 구 방법 (deprecated)
SELECT SQL_CALC_FOUND_ROWS * FROM orders LIMIT 10;
SELECT FOUND_ROWS();

-- 권장 방법: 별도 COUNT 쿼리
SELECT COUNT(*) FROM orders WHERE status = 'pending';
SELECT * FROM orders WHERE status = 'pending' LIMIT 10 OFFSET 0;
```

---

## 7. 옵티마이저가 잘못된 실행 계획을 선택하는 경우

### 7-1. 통계 정보 부정확

대량의 데이터 변경 후 통계가 갱신되지 않으면 옵티마이저가 잘못된 cardinality를 참고합니다.

```sql
-- 증상: EXPLAIN의 rows 추정이 실제와 크게 다름
-- EXPLAIN ANALYZE의 estimated rows vs actual rows 차이가 10배 이상

-- 해결: 통계 재수집
ANALYZE TABLE orders;

-- 또는 innodb_stats_persistent_sample_pages 증가
ALTER TABLE orders STATS_SAMPLE_PAGES = 100;
```

### 7-2. 데이터 편향 (Skew)

특정 값이 극도로 많이 존재하는 경우 카디널리티 통계가 전체 평균이므로 부정확합니다.

```sql
-- 예: status 컬럼에 'done'이 99%, 'pending'이 1%
-- 인덱스 선택도가 낮아 보여 풀 스캔을 선택할 수 있음
-- 실제로는 'pending' 조건이면 인덱스가 훨씬 빠름

-- 증상 확인
SELECT status, COUNT(*) FROM orders GROUP BY status;

-- 해결: 힌트로 인덱스 강제
SELECT /*+ INDEX(o idx_status) */ * FROM orders o WHERE status = 'pending';
```

### 7-3. 파라미터 스니핑 유사 문제

MySQL은 prepared statement를 실행할 때 첫 번째 실행의 파라미터를 기준으로 실행 계획을 캐시합니다. 이후 다른 파라미터로 실행 시 캐시된 계획이 비효율적일 수 있습니다.

```sql
-- 첫 실행: status = 'done' (99%의 데이터) → 풀 스캔 계획 캐시
-- 두 번째 실행: status = 'pending' (1%의 데이터) → 캐시된 풀 스캔 사용 (비효율)

-- 해결: 세션 캐시 초기화 또는 NO_QUERY_CACHE
RESET QUERY CACHE;  -- MySQL 5.7 이하

-- 또는 쿼리 힌트로 매번 재계획
SELECT /*+ INDEX(o idx_status) */ * FROM orders o WHERE status = ?;
```

### 7-4. 함수/형변환으로 인한 인덱스 무력화

```sql
-- 나쁨: 컬럼에 함수 적용 → 인덱스 사용 불가
SELECT * FROM users WHERE YEAR(created_at) = 2025;
SELECT * FROM orders WHERE CAST(total AS CHAR) = '10000';
SELECT * FROM users WHERE LEFT(email, 5) = 'admin';

-- 좋음: 범위 조건으로 변환
SELECT * FROM users WHERE created_at >= '2025-01-01' AND created_at < '2026-01-01';
SELECT * FROM orders WHERE total = 10000;
SELECT * FROM users WHERE email LIKE 'admin%';
```

```sql
-- 나쁨: 묵시적 형변환 (컬럼 타입 ≠ 비교값 타입)
-- user_id가 INT인데 문자열로 비교 → 형변환 발생 → 인덱스 무력화
SELECT * FROM orders WHERE user_id = '100';

-- 좋음: 타입 일치
SELECT * FROM orders WHERE user_id = 100;
```

### 7-5. OR 조건으로 인한 인덱스 무력화

```sql
-- 나쁨: OR로 연결된 조건이 서로 다른 인덱스를 사용해야 할 때
SELECT * FROM orders WHERE user_id = 100 OR status = 'pending';

-- 좋음: UNION ALL로 분리 (각각 인덱스 활용)
SELECT * FROM orders WHERE user_id = 100
UNION ALL
SELECT * FROM orders WHERE status = 'pending' AND user_id != 100;
```

MySQL 8.0+는 Index Merge Optimization으로 OR 조건에서 두 인덱스를 합집합 방식으로 활용할 수 있습니다.

---

## 8. 슬로우 쿼리 분석 실무

### 8-1. slow_query_log 설정

```sql
-- 현재 설정 확인
SHOW VARIABLES LIKE 'slow_query%';
SHOW VARIABLES LIKE 'long_query_time';

-- 동적 활성화 (재시작 불필요)
SET GLOBAL slow_query_log = ON;
SET GLOBAL slow_query_log_file = '/var/log/mysql/slow.log';
SET GLOBAL long_query_time = 1;  -- 1초 이상 쿼리 기록

-- 인덱스 미사용 쿼리도 기록 (빠른 쿼리도 잡아냄)
SET GLOBAL log_queries_not_using_indexes = ON;

-- 관리용 명령도 기록
SET GLOBAL log_slow_admin_statements = ON;
```

`my.cnf`에 영구 설정:
```ini
[mysqld]
slow_query_log = ON
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1
log_queries_not_using_indexes = ON
log_slow_admin_statements = ON
```

슬로우 쿼리 로그 예시:
```
# Time: 2025-06-15T14:32:01.123456Z
# User@Host: app[app] @ localhost []  Id: 12345
# Query_time: 3.456789  Lock_time: 0.000123
# Rows_sent: 1  Rows_examined: 1234567
SET timestamp=1718458321;
SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at;
```

`Rows_examined / Rows_sent` 비율이 높을수록 비효율적인 쿼리입니다.

### 8-2. mysqldumpslow 내장 도구

```bash
# 가장 느린 쿼리 TOP 10
mysqldumpslow -s t -t 10 /var/log/mysql/slow.log

# 실행 횟수 기준 TOP 10
mysqldumpslow -s c -t 10 /var/log/mysql/slow.log

# 특정 패턴 필터
mysqldumpslow -g "SELECT.*orders" /var/log/mysql/slow.log
```

### 8-3. pt-query-digest 활용

Percona Toolkit의 강력한 슬로우 쿼리 분석 도구입니다.

```bash
# 설치
apt-get install percona-toolkit
# 또는
yum install percona-toolkit

# 기본 분석 (쿼리 패턴별 집계)
pt-query-digest /var/log/mysql/slow.log

# 최근 1시간치만 분석
pt-query-digest --since 3600 /var/log/mysql/slow.log

# 특정 데이터베이스만
pt-query-digest --filter '$event->{db} eq "mydb"' /var/log/mysql/slow.log

# 결과를 MySQL 테이블에 저장
pt-query-digest \
  --review h=localhost,D=percona,t=query_review \
  --history h=localhost,D=percona,t=query_history \
  /var/log/mysql/slow.log
```

pt-query-digest 출력 예시:
```
# Profile
# Rank Query ID           Response time Calls R/Call  V/M   Item
# ==== ================== ============= ===== ======= ===== ====
#    1 0xABC123...         45.6789 62.3%   123  0.3713  0.20 SELECT orders
#    2 0xDEF456...         12.3456 16.9%  4567  0.0027  0.01 SELECT users

# Query 1: 0.08 QPS, 0.03x concurrency, ID 0xABC123 at byte 12345
# Scores: V/M = 0.20
# Time range: 2025-06-15 10:00:01 to 2025-06-15 20:59:59
# Attribute    pct   total     min     max     avg     95%  stddev  median
# ============ === ======= ======= ======= ======= ======= ======= =======
# Count         62     123
# Exec time     62     46s   123ms      5s   373ms   1000ms   432ms   200ms
# Lock time      0    15ms       0     3ms   122us   123us    78us    76us
# Rows sent     34     123       1       1       1       1       0       1
# Rows examine  89  1.23M   9.12k  12.34k  10.24k  12.34k   1.23k  10.24k
# Query_time distribution
#   1us
#  10us
# 100us
#   1ms
#  10ms  ####
# 100ms  ##############################################
#    1s  ###
#  10s+
SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at\G
```

### 8-4. Performance Schema 활용

MySQL 5.6+에서 기본 활성화된 성능 모니터링 시스템입니다.

```sql
-- Performance Schema 활성화 확인
SHOW VARIABLES LIKE 'performance_schema';

-- 쿼리별 실행 통계 (sys 스키마 활용)
SELECT
    query,
    exec_count,
    total_latency,
    avg_latency,
    rows_examined_avg,
    rows_sent_avg,
    tmp_tables,
    tmp_disk_tables,
    full_scans
FROM sys.statement_analysis
ORDER BY total_latency DESC
LIMIT 20;

-- 현재 실행 중인 쿼리
SELECT * FROM sys.processlist WHERE command != 'Sleep';

-- 테이블별 I/O 통계
SELECT
    object_schema,
    object_name,
    count_read,
    sum_timer_read / 1e12 AS read_seconds,
    count_write,
    sum_timer_write / 1e12 AS write_seconds
FROM performance_schema.table_io_waits_summary_by_table
WHERE object_schema NOT IN ('performance_schema', 'mysql', 'sys')
ORDER BY sum_timer_read + sum_timer_write DESC
LIMIT 10;

-- 인덱스 사용 통계 (사용되지 않는 인덱스 찾기)
SELECT
    object_schema,
    object_name,
    index_name,
    count_read,
    count_write
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE object_schema = 'mydb'
  AND index_name IS NOT NULL
  AND count_read = 0  -- 한 번도 사용되지 않은 인덱스
ORDER BY object_name, index_name;

-- 사용되지 않는 인덱스 확인 (sys 스키마)
SELECT * FROM sys.schema_unused_indexes WHERE object_schema = 'mydb';

-- 중복 인덱스 확인
SELECT * FROM sys.schema_redundant_indexes WHERE table_schema = 'mydb';

-- 락 대기 분석
SELECT
    r.trx_id AS waiting_trx_id,
    r.trx_mysql_thread_id AS waiting_thread,
    r.trx_query AS waiting_query,
    b.trx_id AS blocking_trx_id,
    b.trx_mysql_thread_id AS blocking_thread,
    b.trx_query AS blocking_query
FROM information_schema.innodb_lock_waits w
JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id;
```

---

## 9. 실무 쿼리 튜닝 체크리스트

### 단계 1: 문제 식별

```
[ ] slow_query_log에서 Long_query_time 초과 쿼리 수집
[ ] Rows_examined / Rows_sent 비율 확인 (100 이상이면 비효율)
[ ] pt-query-digest로 총 실행 시간 TOP 쿼리 목록 추출
[ ] SHOW PROCESSLIST로 현재 실행 중인 슬로우 쿼리 확인
[ ] sys.statement_analysis에서 avg_latency, full_scans 확인
```

### 단계 2: EXPLAIN 분석

```
[ ] EXPLAIN으로 실행 계획 확인
[ ] type 컬럼에 ALL 또는 index 있는지 확인
[ ] Extra에 Using filesort, Using temporary 있는지 확인
[ ] rows * filtered/100 으로 실제 처리 행 수 추정
[ ] EXPLAIN ANALYZE로 추정치 vs 실제 차이 확인 (10배 이상이면 통계 문제)
[ ] key 컬럼이 NULL이면 인덱스 미사용 원인 분석
```

### 단계 3: 인덱스 검토

```
[ ] WHERE 절 컬럼에 인덱스 존재 여부 확인
[ ] 인덱스 컬럼에 함수/형변환 적용 여부 확인 (인덱스 무력화 원인)
[ ] 복합 인덱스 컬럼 순서 검토 (선택도 높은 컬럼을 앞에)
[ ] 커버링 인덱스 가능 여부 검토 (SELECT + WHERE + ORDER BY 컬럼 포함)
[ ] 사용되지 않는 인덱스 제거 (쓰기 성능 저하 방지)
[ ] ANALYZE TABLE로 통계 갱신 필요 여부 확인
```

### 단계 4: 쿼리 리팩토링

```
[ ] SELECT *를 필요한 컬럼만으로 줄이기
[ ] 서브쿼리를 JOIN으로 변환 또는 반대 검토
[ ] OR 조건을 UNION ALL로 분리 검토
[ ] IN 절의 값이 수백 개 이상이면 임시 테이블 + JOIN으로 대체
[ ] LIMIT 없는 쿼리에 LIMIT 추가
[ ] Deep Pagination을 Keyset Pagination으로 전환
[ ] GROUP BY / ORDER BY 컬럼과 인덱스 컬럼 일치 여부 확인
[ ] Derived Table이 불필요하게 임시 테이블 생성하는지 확인
```

### 단계 5: 인덱스 추가/변경

```sql
-- 인덱스 추가 (온라인, 락 없음 — MySQL 5.6+)
ALTER TABLE orders ADD INDEX idx_user_status (user_id, status), ALGORITHM=INPLACE, LOCK=NONE;

-- 복합 인덱스 컬럼 순서 결정 원칙
-- 1. 동등 조건(=) 컬럼을 범위 조건 컬럼보다 앞에
-- 2. 선택도 높은 컬럼을 앞에
-- 3. ORDER BY/GROUP BY 컬럼을 마지막에

-- 예: WHERE user_id = ? AND status = ? ORDER BY created_at
-- → INDEX (user_id, status, created_at)

-- 커버링 인덱스: SELECT 컬럼을 인덱스에 포함
-- 예: SELECT user_id, status, created_at FROM orders WHERE user_id = ?
-- → INDEX (user_id, status, created_at)  ← created_at도 인덱스에 포함
```

### 단계 6: 설정 튜닝

```sql
-- 정렬 버퍼 (filesort 성능)
SET GLOBAL sort_buffer_size = 4 * 1024 * 1024;  -- 4MB

-- JOIN 버퍼 (Hash Join 성능)
SET GLOBAL join_buffer_size = 4 * 1024 * 1024;  -- 4MB

-- 읽기 버퍼 (풀 테이블 스캔)
SET GLOBAL read_buffer_size = 4 * 1024 * 1024;  -- 4MB

-- InnoDB 버퍼풀 (가장 중요, 물리 메모리의 50~80%)
SET GLOBAL innodb_buffer_pool_size = 8 * 1024 * 1024 * 1024;  -- 8GB

-- 쿼리 캐시 (MySQL 5.7 이하, 8.0에서 제거됨)
-- 동시 쓰기가 많은 환경에서는 오히려 성능 저하 → 비활성화 권장
SET GLOBAL query_cache_type = OFF;
SET GLOBAL query_cache_size = 0;
```

### 단계 7: 힌트 적용 (최후 수단)

```sql
-- 통계 부정확으로 잘못된 인덱스 선택 시
SELECT /*+ INDEX(o idx_user_id) */ * FROM orders o WHERE user_id = 100;

-- JOIN 순서가 잘못됐을 때
SELECT /*+ LEADING(small_table large_table) */ ...

-- 특정 최적화 비활성화
SELECT /*+ NO_ICP(t) */ * FROM t WHERE ...;
```

### 단계 8: 아키텍처 검토

```
[ ] 읽기 부하 → 레플리카(Replica) 분산
[ ] 핫 테이블 → 파티셔닝 (Range, Hash, List)
[ ] 자주 조회되는 결과 → 애플리케이션 캐시 (Redis, Memcached)
[ ] 집계 쿼리 → 요약 테이블(Summary Table) 사전 계산
[ ] 대용량 배치 → OFF-PEAK 시간대 실행
[ ] 테이블 크기 > 수억 건 → 아카이빙 또는 샤딩 검토
```

---

## 참고: 주요 변수 요약

```sql
-- 현재 세션의 모든 관련 변수 확인
SHOW VARIABLES WHERE Variable_name IN (
    'innodb_buffer_pool_size',
    'innodb_stats_sample_pages',
    'innodb_stats_auto_recalc',
    'sort_buffer_size',
    'join_buffer_size',
    'read_buffer_size',
    'read_rnd_buffer_size',
    'tmp_table_size',
    'max_heap_table_size',
    'optimizer_search_depth',
    'optimizer_switch',
    'long_query_time',
    'slow_query_log',
    'log_queries_not_using_indexes'
);
```

옵티마이저를 완전히 이해하면 단순히 인덱스를 추가하는 것을 넘어, 데이터 분포와 실행 계획의 상관관계를 파악하고 쿼리와 스키마를 함께 설계할 수 있게 됩니다. `EXPLAIN ANALYZE`를 생활화하고, 슬로우 쿼리 로그를 정기적으로 검토하는 습관을 들이는 것이 MySQL 성능 관리의 핵심입니다.
