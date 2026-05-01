---
title: "데이터베이스 파티셔닝"
categories:
- DB
toc: true
toc_sticky: true
toc_label: 목차
---

## 파티셔닝이란?

**파티셔닝(Partitioning)**은 하나의 큰 테이블을 물리적으로 여러 조각(파티션)으로 나누어 저장하되, 논리적으로는 하나의 테이블처럼 접근할 수 있게 하는 기법이다.

데이터베이스 입장에서 수억 건의 레코드를 단일 테이블에 저장하면 다음과 같은 문제가 발생한다.

- 풀 테이블 스캔 시 I/O가 폭증한다
- 인덱스 크기가 커져 B-Tree 깊이가 깊어지고 랜덤 I/O가 증가한다
- `DELETE` 기반 데이터 정리(아카이빙)가 느리다
- 백업/복구 단위를 세분화하기 어렵다

파티셔닝은 이 문제를 **"쿼리가 접근할 데이터 범위를 물리적으로 한정"**함으로써 해결한다.

```
단일 테이블 (1억 건)
┌──────────────────────────────────────────┐
│  id │ created_at │ region │ amount │ ... │
│  1  │ 2020-01-01 │  KR    │  5000  │ ... │
│  2  │ 2020-01-02 │  US    │  3000  │ ... │
│  …  │     …      │   …    │   …    │ ... │
│ 1억 │ 2024-12-31 │  JP    │  9000  │ ... │
└──────────────────────────────────────────┘
        ↓ 파티셔닝 적용

파티션 p2020          파티션 p2021
┌─────────────────┐   ┌─────────────────┐
│ 2020년 데이터   │   │ 2021년 데이터   │
│ (2500만 건)     │   │ (2500만 건)     │
└─────────────────┘   └─────────────────┘
파티션 p2022          파티션 p2023
┌─────────────────┐   ┌─────────────────┐
│ 2022년 데이터   │   │ 2023년 데이터   │
│ (2500만 건)     │   │ (2500만 건)     │
└─────────────────┘   └─────────────────┘
```

## 수평 파티셔닝 vs 수직 파티셔닝

### 수평 파티셔닝 (Horizontal Partitioning)

행(Row) 단위로 데이터를 분할한다. 같은 스키마를 가진 파티션들이 서로 다른 행 집합을 보유한다.

```
원본 테이블
┌────┬──────┬────────┐
│ id │ name │ salary │
├────┼──────┼────────┤
│  1 │ Kim  │  5000  │
│  2 │ Lee  │  3000  │
│  3 │ Park │  7000  │
│  4 │ Choi │  2000  │
└────┴──────┴────────┘

수평 분할 (id 기준)
파티션 A (id 1~2)    파티션 B (id 3~4)
┌────┬──────┬──────┐  ┌────┬──────┬──────┐
│ id │ name │ sal  │  │ id │ name │ sal  │
│  1 │ Kim  │ 5000 │  │  3 │ Park │ 7000 │
│  2 │ Lee  │ 3000 │  │  4 │ Choi │ 2000 │
└────┴──────┴──────┘  └────┴──────┴──────┘
```

MySQL의 `PARTITION BY` 문법이 지원하는 것이 바로 수평 파티셔닝이다.

### 수직 파티셔닝 (Vertical Partitioning)

열(Column) 단위로 데이터를 분할한다. 자주 조회되는 컬럼과 그렇지 않은 컬럼을 별도 테이블로 분리한다.

```
원본 테이블
┌────┬──────┬─────┬──────────────────────┬────────────────┐
│ id │ name │ age │ profile_image (BLOB) │ bio (TEXT)     │
└────┴──────┴─────┴──────────────────────┴────────────────┘

수직 분할
핫 테이블 (자주 조회)    콜드 테이블 (드물게 조회)
┌────┬──────┬─────┐       ┌────┬──────────────────────┬──────────────┐
│ id │ name │ age │       │ id │ profile_image (BLOB) │ bio (TEXT)   │
└────┴──────┴─────┘       └────┴──────────────────────┴──────────────┘
```

MySQL `PARTITION BY`는 수직 파티셔닝을 지원하지 않는다. 수직 파티셔닝은 스키마 설계 수준에서 테이블을 분리하는 방식으로 구현한다.

| 구분 | 수평 파티셔닝 | 수직 파티셔닝 |
|------|-------------|-------------|
| 분할 기준 | 행(Row) | 열(Column) |
| 스키마 | 동일 | 다름 |
| MySQL 지원 | `PARTITION BY` | 별도 테이블 설계 |
| 주 목적 | 대용량 데이터 범위 스캔 최적화 | I/O 감소, 캐시 효율 |

---

## MySQL 파티셔닝 종류

MySQL은 `PARTITION BY` 절로 다음 파티셔닝 방식을 지원한다.

### RANGE 파티셔닝

파티션 키의 **값 범위**를 기준으로 데이터를 나눈다. 날짜, 순번 등 연속적인 값에 적합하다.

#### 동작 원리

INSERT 시 MySQL이 파티션 키 값을 평가하여 해당 범위의 파티션에 행을 저장한다. SELECT 시에는 WHERE 조건의 파티션 키 값으로 접근할 파티션을 결정한다(파티션 프루닝).

```
RANGE 파티셔닝 내부 구조
파티션 정의: LESS THAN 값으로 경계 지정

p_2022: LESS THAN (2023)  →  2022년 이하 데이터
p_2023: LESS THAN (2024)  →  2023년 데이터
p_2024: LESS THAN (2025)  →  2024년 데이터
p_max:  LESS THAN MAXVALUE →  나머지

INSERT INTO orders(order_date, amount)
VALUES ('2023-06-15', 5000);
          │
          ▼
MySQL: 2023-06-15 → YEAR = 2023
       2023 < 2024 → p_2023 파티션에 저장
```

#### 날짜 기반 DDL 예시

```sql
CREATE TABLE orders (
    order_id    BIGINT       NOT NULL,
    order_date  DATE         NOT NULL,
    customer_id BIGINT       NOT NULL,
    amount      DECIMAL(12,2) NOT NULL,
    PRIMARY KEY (order_id, order_date)   -- 파티션 키는 PK에 포함 필수
)
PARTITION BY RANGE (YEAR(order_date)) (
    PARTITION p_2022 VALUES LESS THAN (2023),
    PARTITION p_2023 VALUES LESS THAN (2024),
    PARTITION p_2024 VALUES LESS THAN (2025),
    PARTITION p_2025 VALUES LESS THAN (2026),
    PARTITION p_max  VALUES LESS THAN MAXVALUE
);
```

월 단위로 더 세밀하게 분할할 때는 `RANGE COLUMNS`를 사용한다.

```sql
CREATE TABLE logs (
    log_id   BIGINT   NOT NULL,
    log_date DATE     NOT NULL,
    level    VARCHAR(10),
    message  TEXT,
    PRIMARY KEY (log_id, log_date)
)
PARTITION BY RANGE COLUMNS (log_date) (
    PARTITION p_2024_01 VALUES LESS THAN ('2024-02-01'),
    PARTITION p_2024_02 VALUES LESS THAN ('2024-03-01'),
    PARTITION p_2024_03 VALUES LESS THAN ('2024-04-01'),
    -- ...
    PARTITION p_max     VALUES LESS THAN MAXVALUE
);
```

#### 파티션 프루닝

```sql
-- 이 쿼리는 p_2023 파티션만 스캔한다
SELECT * FROM orders
WHERE order_date BETWEEN '2023-01-01' AND '2023-12-31';

-- EXPLAIN PARTITIONS로 확인
EXPLAIN SELECT * FROM orders
WHERE order_date BETWEEN '2023-01-01' AND '2023-12-31'\G

-- 결과 예시
-- partitions: p_2023   ← 한 파티션만 접근
-- type: range
```

---

### LIST 파티셔닝

파티션 키의 **값 목록**을 기준으로 데이터를 나눈다. 카테고리, 지역 코드, 상태값 등 열거 가능한 값에 적합하다.

#### 동작 원리

```
LIST 파티셔닝 구조

파티션 p_kr: IN ('KR', 'JP', 'CN')   → 아시아 데이터
파티션 p_eu: IN ('DE', 'FR', 'UK')   → 유럽 데이터
파티션 p_us: IN ('US', 'CA', 'MX')   → 북미 데이터

INSERT INTO sales(region_code, amount)
VALUES ('JP', 30000);
          │
          ▼
MySQL: 'JP' ∈ ('KR', 'JP', 'CN') → p_kr 파티션에 저장
```

#### DDL 예시

```sql
-- 지역 기반 파티셔닝
CREATE TABLE sales (
    sale_id     BIGINT        NOT NULL,
    region_code VARCHAR(5)    NOT NULL,
    sale_date   DATE          NOT NULL,
    amount      DECIMAL(12,2) NOT NULL,
    PRIMARY KEY (sale_id, region_code)
)
PARTITION BY LIST COLUMNS (region_code) (
    PARTITION p_asia VALUES IN ('KR', 'JP', 'CN', 'TW', 'SG'),
    PARTITION p_eu   VALUES IN ('DE', 'FR', 'GB', 'IT', 'ES'),
    PARTITION p_us   VALUES IN ('US', 'CA', 'MX', 'BR', 'AR')
);

-- 카테고리 기반 파티셔닝
CREATE TABLE products (
    product_id  INT          NOT NULL,
    category    INT          NOT NULL,
    name        VARCHAR(200) NOT NULL,
    price       DECIMAL(10,2),
    PRIMARY KEY (product_id, category)
)
PARTITION BY LIST (category) (
    PARTITION p_electronics VALUES IN (1, 2, 3),
    PARTITION p_clothing     VALUES IN (4, 5, 6),
    PARTITION p_food         VALUES IN (7, 8, 9)
);
```

목록에 없는 값이 INSERT되면 에러가 발생한다. `PARTITION p_others VALUES IN (...)` 같은 기본 파티션을 두거나, `IGNORE` 옵션을 고려해야 한다.

---

### HASH 파티셔닝

파티션 키에 해시 함수를 적용하여 **균등 분배**한다. 특정 범위나 목록 기반 접근보다 균형 잡힌 데이터 분포가 우선일 때 사용한다.

#### 동작 원리

```
HASH 파티셔닝 (파티션 수 = 4)

파티션 배정 공식: partition_num = MOD(partition_expr, num_partitions)

customer_id = 1  → MOD(1, 4) = 1 → p1
customer_id = 2  → MOD(2, 4) = 2 → p2
customer_id = 3  → MOD(3, 4) = 3 → p3
customer_id = 4  → MOD(4, 4) = 0 → p0
customer_id = 5  → MOD(5, 4) = 1 → p1
customer_id = 6  → MOD(6, 4) = 2 → p2

파티션 p0   파티션 p1   파티션 p2   파티션 p3
┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
│ id=4   │  │ id=1   │  │ id=2   │  │ id=3   │
│ id=8   │  │ id=5   │  │ id=6   │  │ id=7   │
│ id=12  │  │ id=9   │  │ id=10  │  │ id=11  │
└────────┘  └────────┘  └────────┘  └────────┘
```

#### DDL 예시

```sql
CREATE TABLE user_activities (
    activity_id BIGINT   NOT NULL,
    user_id     BIGINT   NOT NULL,
    activity    VARCHAR(50),
    created_at  DATETIME NOT NULL,
    PRIMARY KEY (activity_id, user_id)
)
PARTITION BY HASH (user_id)
PARTITIONS 8;   -- 파티션 수는 2의 거듭제곱 권장
```

`LINEAR HASH`를 사용하면 파티션 추가/삭제 시 재분배되는 데이터 양을 줄일 수 있지만 균등도가 다소 낮아진다.

```sql
PARTITION BY LINEAR HASH (user_id)
PARTITIONS 8;
```

HASH 파티셔닝의 단점은 **파티션 프루닝이 등호(=) 조건에만 동작**한다는 것이다. 범위 쿼리는 모든 파티션을 스캔한다.

---

### KEY 파티셔닝

HASH 파티셔닝과 유사하지만, **MySQL 내부 해시 함수**를 사용한다. 파티션 키로 정수 외 문자열, DATE 등도 사용할 수 있다.

```sql
CREATE TABLE sessions (
    session_id  VARCHAR(64)  NOT NULL,
    user_id     BIGINT       NOT NULL,
    data        TEXT,
    expires_at  DATETIME     NOT NULL,
    PRIMARY KEY (session_id)
)
PARTITION BY KEY (session_id)
PARTITIONS 16;
```

파티션 키를 지정하지 않으면 PRIMARY KEY가 자동으로 파티션 키로 사용된다.

```sql
-- PK가 파티션 키 역할
CREATE TABLE events (
    event_id BIGINT NOT NULL AUTO_INCREMENT,
    name     VARCHAR(100),
    PRIMARY KEY (event_id)
)
PARTITION BY KEY()   -- event_id 자동 사용
PARTITIONS 4;
```

---

### 서브 파티셔닝 (복합 파티셔닝)

RANGE 또는 LIST 파티셔닝 위에 HASH 또는 KEY 서브 파티셔닝을 추가한다.

```
서브 파티셔닝 구조 (RANGE + HASH)

RANGE p_2023 ──┬── HASH subp0
               ├── HASH subp1
               ├── HASH subp2
               └── HASH subp3

RANGE p_2024 ──┬── HASH subp0
               ├── HASH subp1
               ├── HASH subp2
               └── HASH subp3
```

```sql
CREATE TABLE orders (
    order_id    BIGINT NOT NULL,
    order_date  DATE   NOT NULL,
    customer_id BIGINT NOT NULL,
    amount      DECIMAL(12,2),
    PRIMARY KEY (order_id, order_date, customer_id)
)
PARTITION BY RANGE (YEAR(order_date))
SUBPARTITION BY HASH (customer_id)
SUBPARTITIONS 4
(
    PARTITION p_2023 VALUES LESS THAN (2024),
    PARTITION p_2024 VALUES LESS THAN (2025),
    PARTITION p_2025 VALUES LESS THAN (2026)
);
-- 총 파티션 수: 3 × 4 = 12
```

---

## 파티셔닝과 인덱스 관계

### 로컬 인덱스 (Local Index)

MySQL 파티셔닝에서 기본적으로 모든 인덱스는 **로컬 인덱스**다. 각 파티션이 자신의 데이터에 대한 인덱스를 독립적으로 보유한다.

```
로컬 인덱스 구조

파티션 p_2023                  파티션 p_2024
┌─────────────────────────┐    ┌─────────────────────────┐
│ 데이터: 2023년 주문     │    │ 데이터: 2024년 주문     │
│ 인덱스: customer_id idx │    │ 인덱스: customer_id idx │
│  └ 2023년 데이터만 커버 │    │  └ 2024년 데이터만 커버 │
└─────────────────────────┘    └─────────────────────────┘
```

장점: 파티션 프루닝이 적용되면 해당 파티션의 인덱스만 탐색한다.
단점: 파티션 키가 WHERE 조건에 없으면 **모든 파티션의 인덱스를 탐색**해야 한다.

### 글로벌 인덱스 (Global Index)

MySQL은 글로벌 인덱스를 공식 지원하지 않는다. Oracle, PostgreSQL 등에서는 테이블 전체를 아우르는 글로벌 인덱스를 만들 수 있지만, MySQL에서는 파티션 키를 포함하지 않는 UNIQUE KEY 생성 자체가 불가능하다.

```sql
-- 에러 발생: 파티션 키(order_date)가 UNIQUE KEY에 없음
CREATE TABLE orders (
    order_id   BIGINT NOT NULL,
    order_date DATE   NOT NULL,
    UNIQUE KEY uq_order_id (order_id)   -- 불가!
)
PARTITION BY RANGE (YEAR(order_date)) (...);

-- 해결: 파티션 키를 UNIQUE KEY에 포함
UNIQUE KEY uq_order_id (order_id, order_date)   -- 가능
```

---

## 파티션 프루닝 동작 원리

파티션 프루닝(Partition Pruning)은 쿼리 실행 시 불필요한 파티션을 읽지 않도록 MySQL 옵티마이저가 스캔 대상 파티션을 사전에 결정하는 최적화다.

```
파티션 프루닝 동작 흐름

SELECT * FROM orders
WHERE order_date BETWEEN '2024-01-01' AND '2024-06-30'
  AND customer_id = 1001;

         │
         ▼
1. 옵티마이저: WHERE 절에서 파티션 키 조건 추출
              order_date 범위 → YEAR(order_date) = 2024

2. 파티션 맵 조회:
   p_2022 → YEAR < 2023  ✗ 제외
   p_2023 → YEAR < 2024  ✗ 제외
   p_2024 → YEAR < 2025  ✓ 포함
   p_2025 → YEAR < 2026  ✗ 제외 (데이터 없음)
   p_max  → MAXVALUE      ✗ 제외

3. p_2024 파티션만 스캔
   → p_2024 내 customer_id 인덱스 탐색
   → 결과 반환

스캔한 데이터: 전체의 25% (1개/4개 파티션)
```

프루닝이 동작하지 않는 경우:

```sql
-- 파티션 키에 함수 적용 시 프루닝 불가
WHERE YEAR(order_date) = 2024       -- 프루닝 동작 (RANGE에서 YEAR() 사용 시 예외적으로 동작)
WHERE DATE_FORMAT(order_date, '%Y') = '2024'  -- 프루닝 불가

-- 서브쿼리로 파티션 키를 비교하면 런타임 프루닝
WHERE order_date = (SELECT MAX(order_date) FROM orders)  -- 실행 시점에 결정
```

---

## 파티셔닝 장단점

### 장점

| 항목 | 설명 |
|------|------|
| 쿼리 성능 | 파티션 프루닝으로 스캔 범위 축소 |
| 데이터 관리 | `ALTER TABLE DROP PARTITION`으로 수백만 건 즉시 삭제 (단순 DDL) |
| 병렬 처리 | 파티션별 병렬 쿼리 가능 |
| 백업/복구 | 파티션 단위 독립 백업 |
| 아카이빙 | 파티션 교체(EXCHANGE)로 아카이브 테이블로 이동 |

```sql
-- 2022년 데이터 즉시 삭제 (DELETE 없이 DDL로 처리 → 빠름)
ALTER TABLE orders DROP PARTITION p_2022;

-- 파티션 교체: p_2022 데이터를 archive_orders 테이블로 이동
ALTER TABLE orders EXCHANGE PARTITION p_2022 WITH TABLE archive_orders;
```

### 단점

| 항목 | 설명 |
|------|------|
| UNIQUE KEY 제약 | 파티션 키가 반드시 UNIQUE KEY에 포함 |
| 외래키 불가 | 파티션 테이블은 FOREIGN KEY 지원 안 함 |
| 크로스 파티션 쿼리 | 파티션 키 미포함 쿼리는 전체 파티션 스캔 |
| 파티션 수 제한 | MySQL 8.0 기준 최대 8192개 파티션 |
| 관리 복잡도 | 파티션 추가/분할 작업 필요 |
| 트랜잭션 | 일부 파티션 관련 DDL은 암묵적 커밋 유발 |

---

## 실무 설계 가이드

### 언제 파티셔닝을 도입하는가

일반적으로 다음 조건 중 하나 이상을 충족할 때 파티셔닝을 고려한다.

1. **단일 테이블 행 수가 5천만 건 이상**이고 성능 문제가 발생할 때
2. **시계열 데이터**에서 기간별 데이터 삭제/아카이빙이 빈번할 때
3. **쿼리의 95% 이상이 특정 기간이나 카테고리에 집중**될 때
4. 인덱스 크기가 버퍼 풀을 초과하여 랜덤 I/O가 급증할 때

파티셔닝을 적용하기 전에 먼저 인덱스 최적화, 쿼리 튜닝, 읽기 복제(Read Replica)를 검토해야 한다. 파티셔닝은 복잡도를 상당히 높이므로 마지막 수단에 가깝다.

### 파티션 키 선택 기준

```
좋은 파티션 키의 조건

1. 쿼리의 WHERE 조건에 항상 포함되는 컬럼
   → 프루닝이 실제로 동작해야 의미가 있음

2. 데이터를 균등하게 분포시키는 컬럼
   → 특정 파티션에 핫스팟이 없어야 함

3. 변경되지 않는 컬럼
   → UPDATE로 파티션 키가 바뀌면 파티션 간 행 이동 발생

4. PRIMARY KEY 또는 UNIQUE KEY에 포함 가능한 컬럼
   → MySQL 제약으로 필수

나쁜 파티션 키 예시
- NULL 값이 많은 컬럼 (모두 p_max로 몰림)
- 카디널리티가 낮고 쿼리 필터로 사용되지 않는 컬럼
- UPDATE가 잦은 컬럼
```

---

## DDL 예제

### CREATE PARTITION

```sql
-- 월별 RANGE 파티셔닝 (이벤트 로그)
CREATE TABLE event_logs (
    log_id      BIGINT AUTO_INCREMENT NOT NULL,
    event_type  VARCHAR(50)           NOT NULL,
    payload     JSON,
    created_at  DATETIME              NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (log_id, created_at)
)
ENGINE = InnoDB
PARTITION BY RANGE (TO_DAYS(created_at)) (
    PARTITION p_2024_01 VALUES LESS THAN (TO_DAYS('2024-02-01')),
    PARTITION p_2024_02 VALUES LESS THAN (TO_DAYS('2024-03-01')),
    PARTITION p_2024_03 VALUES LESS THAN (TO_DAYS('2024-04-01')),
    PARTITION p_future   VALUES LESS THAN MAXVALUE
);
```

### ALTER PARTITION — 파티션 추가

```sql
-- p_future를 분리하고 새 파티션 추가
ALTER TABLE event_logs REORGANIZE PARTITION p_future INTO (
    PARTITION p_2024_04 VALUES LESS THAN (TO_DAYS('2024-05-01')),
    PARTITION p_2024_05 VALUES LESS THAN (TO_DAYS('2024-06-01')),
    PARTITION p_future  VALUES LESS THAN MAXVALUE
);
```

### ALTER PARTITION — 파티션 분할

```sql
-- 기존 파티션을 더 세분화
ALTER TABLE orders REORGANIZE PARTITION p_2024 INTO (
    PARTITION p_2024_h1 VALUES LESS THAN (TO_DAYS('2024-07-01')),
    PARTITION p_2024_h2 VALUES LESS THAN (TO_DAYS('2025-01-01'))
);
```

### ALTER PARTITION — 파티션 병합

```sql
-- 여러 파티션을 하나로 합치기
ALTER TABLE orders REORGANIZE PARTITION p_2022, p_2023 INTO (
    PARTITION p_2022_2023 VALUES LESS THAN (2024)
);
```

### DROP PARTITION

```sql
-- 오래된 데이터 파티션 삭제 (즉시 DDL, DELETE보다 훨씬 빠름)
ALTER TABLE event_logs DROP PARTITION p_2024_01;
```

### 파티션 정보 조회

```sql
-- 파티션별 행 수, 데이터 크기 확인
SELECT
    partition_name,
    table_rows,
    ROUND(data_length / 1024 / 1024, 2) AS data_mb,
    ROUND(index_length / 1024 / 1024, 2) AS index_mb
FROM information_schema.partitions
WHERE table_schema = 'mydb'
  AND table_name   = 'orders'
ORDER BY partition_ordinal_position;
```

---

## 주의사항

### UNIQUE KEY 제약

모든 UNIQUE KEY(PRIMARY KEY 포함)는 파티션 키 컬럼을 반드시 포함해야 한다. 이 제약으로 인해 비즈니스 로직상 PK가 될 수 있는 컬럼(예: UUID, order_number)을 단독 PK로 설정하기 어렵다.

```sql
-- 실무 패턴: order_number 유니크하게 유지하면서 파티셔닝
CREATE TABLE orders (
    order_id     BIGINT AUTO_INCREMENT NOT NULL,
    order_number VARCHAR(30)           NOT NULL,
    order_date   DATE                  NOT NULL,
    amount       DECIMAL(12,2),
    PRIMARY KEY (order_id, order_date),           -- 파티션 키 포함
    UNIQUE KEY uq_order_number (order_number, order_date)  -- 파티션 키 포함 필수
)
PARTITION BY RANGE (YEAR(order_date)) (...);

-- order_number만으로는 글로벌 유니크 보장 불가 → 애플리케이션에서 중복 검사 필요
```

### 외래키 불가

파티션 테이블은 FOREIGN KEY CONSTRAINT를 지원하지 않는다. 참조 무결성은 애플리케이션 레벨에서 관리해야 한다.

```sql
-- 에러 발생
ALTER TABLE order_items
ADD CONSTRAINT fk_order
FOREIGN KEY (order_id) REFERENCES orders(order_id);  -- orders가 파티션 테이블이면 불가
```

### 파티션 수 제한

MySQL 8.0은 테이블당 최대 8192개의 파티션(서브 파티션 포함)을 지원한다. 월별 파티셔닝을 30년간 유지하면 360개로 제한 내에 들어오지만, 일별 파티셔닝을 10년간 유지하면 3650개가 된다. 서브 파티셔닝이 추가되면 금방 한계에 도달할 수 있으므로 설계 시 파티션 수 증가 속도를 고려해야 한다.

### NULL 값 처리

RANGE 파티셔닝에서 파티션 키가 NULL이면 가장 작은 파티션에 저장된다. LIST 파티셔닝에서는 NULL을 명시적으로 처리하지 않으면 INSERT 에러가 발생한다. HASH/KEY 파티셔닝에서 NULL은 0으로 처리된다.

```sql
-- LIST 파티셔닝에서 NULL 처리
PARTITION p_unknown VALUES IN (NULL, 'UNKNOWN')
```

---

## Spring/Java 연동 예시

파티셔닝은 데이터베이스 내부에서 투명하게 동작하므로 JPA나 MyBatis 코드에 대부분 변경이 없다. 단, 파티션 프루닝이 실제로 동작하는지 확인하는 것이 중요하다.

```java
// JPA Repository — 파티션 프루닝이 동작하려면 파티션 키를 WHERE에 포함
@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {

    // 좋은 예: order_date(파티션 키)를 조건에 포함 → 프루닝 동작
    List<Order> findByCustomerIdAndOrderDateBetween(
        Long customerId, LocalDate from, LocalDate to);

    // 나쁜 예: 파티션 키 미포함 → 전체 파티션 스캔
    List<Order> findByCustomerId(Long customerId);
}

// MyBatis — 네이티브 쿼리에서 파티션 키 명시
@Mapper
public interface OrderMapper {
    @Select("""
        SELECT * FROM orders
        WHERE order_date BETWEEN #{from} AND #{to}
          AND customer_id = #{customerId}
        ORDER BY order_date DESC
        LIMIT #{limit}
        """)
    List<Order> findOrders(@Param("customerId") Long customerId,
                           @Param("from") LocalDate from,
                           @Param("to") LocalDate to,
                           @Param("limit") int limit);
}
```

```java
// 파티션 관리 스케줄러 예시 (월별 파티션 자동 생성)
@Component
@RequiredArgsConstructor
public class PartitionManager {

    private final JdbcTemplate jdbcTemplate;

    // 매월 1일 다음 달 파티션 생성
    @Scheduled(cron = "0 0 0 1 * *")
    public void addNextMonthPartition() {
        LocalDate nextMonth = LocalDate.now().plusMonths(1);
        LocalDate boundary  = nextMonth.plusMonths(1).withDayOfMonth(1);

        String partitionName = "p_" + nextMonth.format(DateTimeFormatter.ofPattern("yyyy_MM"));
        String boundaryStr   = boundary.toString();

        // MAXVALUE 파티션을 새 파티션으로 분리
        String sql = """
            ALTER TABLE event_logs REORGANIZE PARTITION p_future INTO (
                PARTITION %s VALUES LESS THAN (TO_DAYS('%s')),
                PARTITION p_future VALUES LESS THAN MAXVALUE
            )
            """.formatted(partitionName, boundaryStr);

        jdbcTemplate.execute(sql);
        log.info("파티션 생성 완료: {}", partitionName);
    }
}
```
