---
title: "MySQL 실행 계획과 쿼리 튜닝 — EXPLAIN 한 줄로 10배 느린 쿼리를 찾아내는 법"
categories:
- DB
tags: [MySQL, EXPLAIN, 쿼리튜닝, 실행계획, 인덱스, 커버링인덱스, 슬로우쿼리, 옵티마이저힌트]
toc: true
toc_sticky: true
toc_label: 목차
---

쿼리가 느리다는 신고가 들어왔다. 로그를 보면 `SELECT` 하나가 3초를 넘기고 있다. 어디서 시간이 소비되는지 모른 채 인덱스를 마구 추가하거나, 쿼리를 감으로 바꾸는 것은 도박이다. MySQL의 `EXPLAIN`은 옵티마이저가 쿼리를 어떻게 실행할지 보여주는 설계도다. 이 설계도를 읽는 법을 익히면 3초 쿼리를 0.1초로 만드는 방법이 보인다.

---

## 슬로우 쿼리 로그: 문제 쿼리를 먼저 찾아라

튜닝 전에 어떤 쿼리가 느린지를 먼저 파악해야 한다. MySQL의 슬로우 쿼리 로그는 지정 시간 이상 걸린 쿼리를 파일에 기록한다.

```sql
-- 슬로우 쿼리 로그 활성화
SET GLOBAL slow_query_log = ON;
SET GLOBAL slow_query_log_file = '/var/log/mysql/slow.log';
SET GLOBAL long_query_time = 1;         -- 1초 이상 걸린 쿼리
SET GLOBAL log_queries_not_using_indexes = ON;  -- 인덱스 미사용 쿼리도 기록

-- 현재 설정 확인
SHOW VARIABLES LIKE 'slow_query%';
SHOW VARIABLES LIKE 'long_query_time';
```

`mysqldumpslow` 도구로 로그를 요약하면 가장 자주 나타나는 느린 쿼리 패턴을 빠르게 파악할 수 있다.

```bash
# 실행 시간 합계 기준 상위 10개 쿼리
mysqldumpslow -s t -t 10 /var/log/mysql/slow.log

# 실행 횟수 기준 상위 10개
mysqldumpslow -s c -t 10 /var/log/mysql/slow.log
```

`performance_schema`의 `events_statements_summary_by_digest`는 실행 중인 서버에서 실시간으로 쿼리별 통계를 제공한다.

```sql
SELECT
  DIGEST_TEXT,
  COUNT_STAR AS exec_count,
  ROUND(AVG_TIMER_WAIT / 1e9, 2) AS avg_ms,
  ROUND(SUM_TIMER_WAIT / 1e9, 2) AS total_ms
FROM performance_schema.events_statements_summary_by_digest
ORDER BY SUM_TIMER_WAIT DESC
LIMIT 10;
```

---

## EXPLAIN 출력 완전 해석

`EXPLAIN` 앞에 붙이는 것만으로 실행 계획을 볼 수 있다.

```sql
EXPLAIN SELECT o.id, o.amount, u.name
FROM orders o
JOIN users u ON o.user_id = u.id
WHERE o.status = 'pending'
  AND o.created_at > '2026-01-01';
```

출력의 각 컬럼이 무엇을 의미하는지 하나씩 살펴본다.

### type 컬럼: 접근 방식의 효율 등급

`type`은 옵티마이저가 테이블에 어떻게 접근하는지 나타낸다. 위에서 아래로 갈수록 비효율적이다.

| type | 의미 | 속도 |
|------|------|------|
| system | 행이 한 개뿐인 시스템 테이블 | 최고 |
| const | PRIMARY KEY 또는 UNIQUE로 단 한 행 접근 | 최고 |
| eq_ref | JOIN에서 PRIMARY/UNIQUE 키로 한 행씩 접근 | 매우 빠름 |
| ref | 비유니크 인덱스로 여러 행 접근 | 빠름 |
| range | 인덱스 범위 스캔 (`BETWEEN`, `>`, `IN`) | 보통 |
| index | 인덱스 전체 스캔 (테이블 풀 스캔보다는 낫지만 느림) | 느림 |
| ALL | 테이블 풀 스캔 — 반드시 개선해야 함 | 최악 |

`ALL`이 나오면 인덱스가 없거나 옵티마이저가 인덱스를 사용하지 않기로 결정한 것이다.

### key 컬럼: 실제 사용된 인덱스

`possible_keys`는 사용 가능한 인덱스 후보, `key`는 실제 선택된 인덱스다. `key`가 NULL이면 인덱스를 전혀 쓰지 않는다는 뜻이다.

### rows 컬럼: 예상 검사 행 수

옵티마이저가 결과를 얻기 위해 검사해야 한다고 추정하는 행 수다. 실제 반환 행 수와 비교해 차이가 크면 통계가 오래됐거나 인덱스 선택이 잘못된 것이다.

### Extra 컬럼: 성능에 직결되는 경고 신호

| Extra 값 | 의미 |
|----------|------|
| Using index | 커버링 인덱스 사용 — 테이블 접근 없음. 이상적 |
| Using where | WHERE 조건을 스토리지 엔진 반환 후 MySQL 레이어에서 필터링 |
| Using filesort | ORDER BY를 인덱스로 처리 못해 메모리/디스크 정렬 발생 |
| Using temporary | GROUP BY, ORDER BY 처리를 위해 임시 테이블 생성 |
| Using join buffer | 조인을 인덱스 없이 처리 (Block Nested Loop) |

`Using filesort`와 `Using temporary`가 함께 나오면 쿼리 개선이 시급하다.

---

## EXPLAIN ANALYZE: 실측 실행 계획

MySQL 8.0.18+에서 `EXPLAIN ANALYZE`는 실제로 쿼리를 실행하고 각 단계의 실측 시간과 행 수를 보여준다. 예측(estimated)과 실제(actual)를 동시에 볼 수 있어 통계 오차를 바로 확인할 수 있다.

```sql
EXPLAIN ANALYZE
SELECT o.id, o.amount, u.name
FROM orders o
JOIN users u ON o.user_id = u.id
WHERE o.status = 'pending'
  AND o.created_at > '2026-01-01';
```

출력 예시는 이렇게 생겼다.

```
-> Nested loop inner join  (cost=1234.56 rows=1000)
                           (actual time=0.523..45.231 rows=892 loops=1)
    -> Index range scan on o using idx_status_created  (cost=456.78 rows=1000)
                                                       (actual time=0.312..20.123 rows=892 loops=1)
    -> Single-row index lookup on u using PRIMARY (user_id=o.user_id)
                                                  (actual time=0.021..0.021 rows=1 loops=892)
```

`actual time=0.523..45.231`에서 첫 번째 숫자는 첫 행을 반환하는 데 걸린 시간, 두 번째는 마지막 행까지 걸린 시간(ms)이다.

`FORMAT=TREE` 옵션으로 트리 형태의 텍스트 출력을 얻거나 `FORMAT=JSON`으로 상세 메타데이터를 볼 수 있다.

```sql
EXPLAIN FORMAT=TREE
SELECT * FROM orders WHERE status = 'pending';

EXPLAIN FORMAT=JSON
SELECT * FROM orders WHERE status = 'pending';
```

---

## 인덱스 전략

### 복합 인덱스 컬럼 순서

복합 인덱스의 컬럼 순서는 쿼리 패턴에 맞게 설계해야 한다. 핵심 규칙은 **등호(=) 조건 컬럼을 앞에, 범위(>, BETWEEN) 조건 컬럼을 뒤에** 두는 것이다.

```sql
-- 나쁜 순서: 범위 조건이 앞에 있으면 뒤 컬럼을 인덱스로 활용 못함
CREATE INDEX idx_bad ON orders (created_at, status);

-- 좋은 순서: 등호 조건 먼저, 범위 조건 뒤에
CREATE INDEX idx_good ON orders (status, created_at);

-- 이 쿼리에 idx_good이 효율적으로 동작함
SELECT * FROM orders
WHERE status = 'pending'          -- 등호 조건
  AND created_at > '2026-01-01';  -- 범위 조건
```

인덱스는 왼쪽에서 오른쪽으로 사용된다. 첫 번째 컬럼을 건너뛰면 인덱스 자체를 쓸 수 없다.

```sql
-- idx_good(status, created_at)에서 status를 건너뛰면 인덱스 미사용
SELECT * FROM orders WHERE created_at > '2026-01-01';
-- type: ALL (풀 스캔)
```

### 커버링 인덱스: 테이블 접근을 없애는 기법

인덱스만으로 쿼리에 필요한 모든 컬럼을 공급할 수 있으면 테이블 데이터 파일에 접근할 필요가 없다. `Extra: Using index`가 이 상태를 나타낸다.

```sql
-- orders 테이블에 (status, created_at, amount) 복합 인덱스가 있다면
CREATE INDEX idx_covering ON orders (status, created_at, amount);

-- SELECT 컬럼이 인덱스 내에 모두 포함됨 → 커버링 인덱스
SELECT status, created_at, amount
FROM orders
WHERE status = 'pending';
-- Extra: Using index (테이블 접근 없음)

-- id가 PRIMARY KEY라면 InnoDB는 모든 인덱스에 PK를 자동 포함
-- 아래도 커버링 인덱스로 처리될 수 있음
SELECT id, status, created_at, amount FROM orders WHERE status = 'pending';
```

InnoDB는 세컨더리 인덱스 리프 노드에 항상 Primary Key 값을 저장한다. 따라서 SELECT에 PK를 포함해도 커버링 인덱스가 깨지지 않는다.

### 인덱스가 무시되는 경우

옵티마이저가 인덱스를 무시하는 대표적인 패턴들이다.

```sql
-- 1. 인덱스 컬럼에 함수 적용
-- 나쁨: 인덱스 미사용
SELECT * FROM orders WHERE YEAR(created_at) = 2026;
-- 좋음: 범위 조건으로 변환
SELECT * FROM orders WHERE created_at BETWEEN '2026-01-01' AND '2026-12-31';

-- 2. 암묵적 타입 변환
-- 나쁨: user_id가 INT인데 문자열로 비교 → 인덱스 미사용 가능
SELECT * FROM orders WHERE user_id = '123';
-- 좋음: 타입 일치
SELECT * FROM orders WHERE user_id = 123;

-- 3. LIKE 패턴이 와일드카드로 시작
-- 나쁨: 풀 스캔
SELECT * FROM products WHERE name LIKE '%phone%';
-- 좋음: 전방 일치는 인덱스 사용
SELECT * FROM products WHERE name LIKE 'phone%';

-- 4. OR 조건에서 한쪽에만 인덱스가 있을 때
-- 인덱스 없는 컬럼이 OR에 있으면 풀 스캔으로 떨어짐
SELECT * FROM orders WHERE status = 'pending' OR remark = 'urgent';
-- 해결: UNION ALL로 분리
SELECT * FROM orders WHERE status = 'pending'
UNION ALL
SELECT * FROM orders WHERE remark = 'urgent' AND status != 'pending';
```

---

## JOIN 최적화

### Nested Loop Join (NLJ)

MySQL의 기본 JOIN 알고리즘이다. 외부 테이블(드라이빙 테이블)에서 한 행씩 읽으며 내부 테이블(드리븐 테이블)에서 일치하는 행을 찾는다. 드리븐 테이블에 조인 조건 인덱스가 있어야 효율적이다.

```mermaid
graph LR
  DT[드라이빙 테이블] -->|각 행마다| DV[드리븐 테이블]
  DV -->|인덱스 탐색| R[결과]
```

드라이빙 테이블은 결과 집합이 작은 쪽이 유리하다. 옵티마이저가 자동 선택하지만, 통계가 부정확하면 잘못 선택할 수 있다.

### Hash Join (MySQL 8.0.18+)

조인 컬럼에 인덱스가 없을 때 MySQL 8.0.18부터 Hash Join을 사용한다. 작은 테이블로 해시 테이블을 만들고 큰 테이블을 스캔하며 해시 조회한다. 대용량 비인덱스 조인에서 BNL(Block Nested Loop)보다 훨씬 빠르다.

```sql
-- Hash Join 활성화 여부 확인
EXPLAIN FORMAT=TREE
SELECT * FROM orders o JOIN users u ON o.user_id = u.id;
-- "Hash join" 텍스트가 보이면 Hash Join 사용 중
```

### 드라이빙 테이블 강제 지정

옵티마이저가 잘못된 드라이빙 테이블을 선택했다고 확신할 때 `STRAIGHT_JOIN`으로 순서를 강제할 수 있다.

```sql
-- FROM 절의 첫 번째 테이블을 드라이빙으로 강제
SELECT STRAIGHT_JOIN o.id, u.name
FROM orders o
JOIN users u ON o.user_id = u.id
WHERE o.status = 'pending';
```

---

## 서브쿼리 vs JOIN

서브쿼리가 항상 나쁜 것은 아니지만, 상관 서브쿼리(correlated subquery)는 외부 쿼리 행마다 서브쿼리를 재실행하므로 성능이 급격히 저하된다.

```sql
-- 나쁨: 상관 서브쿼리 — orders 행 수만큼 users 쿼리 반복 실행
SELECT o.id, o.amount,
  (SELECT u.name FROM users u WHERE u.id = o.user_id) AS user_name
FROM orders o
WHERE o.status = 'pending';

-- 좋음: JOIN으로 변환 — 한 번의 조인으로 처리
SELECT o.id, o.amount, u.name AS user_name
FROM orders o
JOIN users u ON o.user_id = u.id
WHERE o.status = 'pending';
```

`WHERE` 절의 `IN (SELECT ...)` 서브쿼리는 MySQL 5.6+에서 많이 개선됐지만, 대용량 결과를 반환하는 경우 여전히 `JOIN`으로 변환하는 것이 안전하다.

```sql
-- 나쁨: IN 서브쿼리가 대용량일 때
SELECT * FROM orders
WHERE user_id IN (SELECT id FROM users WHERE country = 'KR');

-- 좋음: EXISTS나 JOIN으로 변환
SELECT o.* FROM orders o
WHERE EXISTS (
  SELECT 1 FROM users u
  WHERE u.id = o.user_id AND u.country = 'KR'
);
-- 또는
SELECT o.* FROM orders o
JOIN users u ON o.user_id = u.id AND u.country = 'KR';
```

---

## 옵티마이저 힌트

통계 오류나 복잡한 쿼리에서 옵티마이저가 잘못된 계획을 선택할 때 힌트로 실행 계획을 유도할 수 있다.

```sql
-- 특정 인덱스 강제 사용
SELECT * FROM orders USE INDEX (idx_status_created)
WHERE status = 'pending';

-- 특정 인덱스 사용 금지
SELECT * FROM orders IGNORE INDEX (idx_status)
WHERE status = 'pending';

-- MySQL 8.0 힌트 문법 (권장 — 쿼리 구조 변경 없이 힌트 삽입)
SELECT /*+ INDEX(o idx_status_created) */ o.id, u.name
FROM orders o
JOIN users u ON o.user_id = u.id
WHERE o.status = 'pending';

-- Join 순서 힌트
SELECT /*+ JOIN_ORDER(u, o) */ o.id, u.name
FROM orders o
JOIN users u ON o.user_id = u.id;

-- Hash Join 강제
SELECT /*+ HASH_JOIN(o, u) */ o.id, u.name
FROM orders o
JOIN users u ON o.user_id = u.id;
```

힌트는 통계 업데이트나 인덱스 재설계 전 임시 조치로 사용하고, 장기적으로는 근본 원인(통계 갱신, 인덱스 추가)을 해결하는 것이 바람직하다.

---

## 파티션 프루닝

대용량 테이블에서 파티션을 사용하면 쿼리가 관련 파티션만 스캔한다. `EXPLAIN` 출력의 `partitions` 컬럼에서 실제 접근한 파티션을 확인할 수 있다.

```sql
-- 월별 RANGE 파티션 예시
CREATE TABLE orders_partitioned (
  id BIGINT NOT NULL,
  created_at DATE NOT NULL,
  amount DECIMAL(10,2),
  PRIMARY KEY (id, created_at)
)
PARTITION BY RANGE (YEAR(created_at) * 100 + MONTH(created_at)) (
  PARTITION p202601 VALUES LESS THAN (202602),
  PARTITION p202602 VALUES LESS THAN (202603),
  PARTITION p202603 VALUES LESS THAN (202604),
  PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- 파티션 프루닝 확인
EXPLAIN SELECT * FROM orders_partitioned
WHERE created_at BETWEEN '2026-01-01' AND '2026-01-31';
-- partitions: p202601 (다른 파티션은 접근하지 않음)
```

파티션 키가 WHERE 조건에 없으면 모든 파티션을 스캔한다. 파티션 컬럼은 반드시 조회 조건에 등장하도록 쿼리를 설계해야 한다.

---

## Spring JPA에서 쿼리 성능 확인

JPA를 쓰면 실제 실행되는 SQL이 숨겨지기 쉽다. 성능 확인을 위한 필수 설정들이다.

```yaml
# application.yml
spring:
  jpa:
    show-sql: true
    properties:
      hibernate:
        format_sql: true
        use_sql_comments: true
        generate_statistics: true  # 실행 통계 활성화

logging:
  level:
    org.hibernate.SQL: DEBUG
    org.hibernate.orm.jdbc.bind: TRACE         # 바인딩 파라미터 출력
    org.hibernate.stat: DEBUG                  # 통계 출력
```

```java
// N+1 문제 감지 — 통계로 쿼리 수 확인
@Autowired
private Statistics statistics;  // Hibernate Statistics

long beforeCount = statistics.getQueryExecutionCount();
List<Order> orders = orderRepository.findAll();  // N+1이 발생하면 쿼리가 폭발
long afterCount = statistics.getQueryExecutionCount();
log.info("실행된 쿼리 수: {}", afterCount - beforeCount);
```

N+1 문제는 JPQL의 `JOIN FETCH`나 `@EntityGraph`로 해결한다.

```java
// N+1 해결: JOIN FETCH
@Query("SELECT o FROM Order o JOIN FETCH o.user WHERE o.status = :status")
List<Order> findByStatusWithUser(@Param("status") String status);

// 또는 @EntityGraph
@EntityGraph(attributePaths = {"user"})
List<Order> findByStatus(String status);
```

**Datasource-proxy** 라이브러리를 사용하면 실행된 SQL 수와 슬로우 쿼리를 애플리케이션 레벨에서 모니터링할 수 있다.

---

## 통계 관리: 옵티마이저 판단의 기반

옵티마이저는 테이블 통계(행 수, 인덱스 분포)를 보고 실행 계획을 결정한다. 통계가 오래되면 실제와 다른 계획을 선택할 수 있다.

```sql
-- 테이블 통계 수동 갱신
ANALYZE TABLE orders;

-- InnoDB 통계 설정
SHOW VARIABLES LIKE 'innodb_stats%';

-- innodb_stats_persistent = ON (기본): 통계를 디스크에 저장
-- innodb_stats_auto_recalc = ON (기본): 행의 10% 변경 시 자동 재계산
-- innodb_stats_persistent_sample_pages: 샘플링 페이지 수 (기본 20, 크게 하면 정확하지만 느림)

-- 테이블별 샘플링 페이지 수 변경
ALTER TABLE orders STATS_SAMPLE_PAGES = 100;
ANALYZE TABLE orders;
```

---

## 극한 시나리오

### 시나리오 1: filesort + temporary 동시 발생

`GROUP BY`와 `ORDER BY`의 컬럼이 다르거나 인덱스를 활용할 수 없을 때 임시 테이블 생성과 파일 정렬이 동시에 발생한다. 수백만 행 테이블에서 이 조합은 쿼리 타임아웃을 유발한다.

```sql
-- 문제 쿼리 예시
SELECT user_id, COUNT(*) AS cnt, MAX(amount) AS max_amount
FROM orders
WHERE status = 'pending'
GROUP BY user_id
ORDER BY max_amount DESC;
-- Extra: Using where; Using temporary; Using filesort

-- 해결 전략 1: 커버링 인덱스로 GROUP BY 컬럼 제공
CREATE INDEX idx_status_user_amount ON orders (status, user_id, amount);
-- Using index for group-by 가 되면 임시 테이블 없이 처리

-- 해결 전략 2: GROUP BY 결과를 서브쿼리로 먼저 집계 후 정렬
SELECT user_id, cnt, max_amount
FROM (
  SELECT user_id, COUNT(*) AS cnt, MAX(amount) AS max_amount
  FROM orders
  WHERE status = 'pending'
  GROUP BY user_id
) AS sub
ORDER BY max_amount DESC;
-- 임시 테이블은 여전히 쓰지만 정렬 대상 집합이 작아짐

-- 해결 전략 3: sort_buffer_size 증가 (임시 방편)
SET SESSION sort_buffer_size = 32 * 1024 * 1024;  -- 32MB
```

### 시나리오 2: 옵티마이저가 풀 스캔을 선택하는 이유

인덱스가 존재하는데도 옵티마이저가 풀 스캔을 선택하는 경우가 있다. 선택도(Selectivity)가 낮을 때 발생한다. `status` 컬럼에 'pending', 'done' 두 값만 있고 90%가 'done'이라면, `status = 'done'` 조건으로 전체의 90%를 읽어야 한다. 이때 옵티마이저는 랜덤 I/O가 많은 인덱스 스캔보다 순차 풀 스캔이 더 빠르다고 판단한다.

```sql
-- 인덱스 선택도 확인
SELECT
  COUNT(DISTINCT status) / COUNT(*) AS selectivity
FROM orders;
-- 0.5 미만이면 선택도 낮음 → 인덱스 효과 미미

-- 해결: 선택도가 높은 다른 컬럼과 복합 인덱스 구성
-- status 단독보다 (user_id, status)처럼 선택도가 높은 컬럼과 조합
```

### 시나리오 3: 통계 오차로 인한 실행 계획 역전

대량 INSERT/DELETE 직후 통계가 갱신되기 전 상태에서 옵티마이저가 전혀 다른 실행 계획을 선택하는 경우다. `EXPLAIN`의 `rows` 예측이 실제와 100배 이상 차이나는 것을 보면 통계 오차를 의심한다.

```sql
-- 배치 작업 후 즉시 통계 갱신
ANALYZE TABLE orders;

-- 또는 auto-recalc 트리거 조건 이전에 수동 갱신 스케줄 추가
-- (DBA가 cron으로 ANALYZE TABLE 실행)

-- 특정 쿼리에 힌트로 임시 우회
SELECT /*+ INDEX(o idx_status_created) */ *
FROM orders o
WHERE o.status = 'pending';
```

---

## 쿼리 튜닝 체크리스트

실무에서 느린 쿼리를 받았을 때 검토하는 순서다.

1. 슬로우 쿼리 로그 또는 `performance_schema`에서 대상 쿼리 식별
2. `EXPLAIN`으로 type, key, rows, Extra 확인
3. `ALL` 또는 `index` type이면 인덱스 추가 또는 쿼리 변경 검토
4. `Using filesort` 또는 `Using temporary` 제거 방법 탐색
5. `EXPLAIN ANALYZE`로 예측과 실제 차이 확인 (통계 오차 여부)
6. 상관 서브쿼리 → JOIN 변환 검토
7. N+1 여부 확인 (JPA 사용 시)
8. `ANALYZE TABLE`로 통계 갱신 후 재확인
9. 옵티마이저 힌트는 최후 수단으로 사용

---

## 면접 포인트

### EXPLAIN의 type 컬럼에서 주의해야 할 값은 무엇인가

`ALL`은 풀 테이블 스캔으로 대용량 테이블에서 심각한 성능 저하를 유발한다. `index`는 인덱스를 전체 스캔하므로 테이블 스캔보다는 낫지만 여전히 느리다. `range` 이상을 목표로 한다. `const`와 `eq_ref`가 이상적이다.

### 커버링 인덱스란 무엇이며 어떻게 확인하는가

쿼리에 필요한 모든 컬럼이 인덱스 내에 포함되어 테이블 데이터 파일에 접근하지 않는 인덱스다. `EXPLAIN`의 `Extra` 컬럼에 `Using index`가 표시된다. InnoDB는 세컨더리 인덱스에 Primary Key를 자동 포함하므로 SELECT 절에 PK를 추가해도 커버링 인덱스를 유지할 수 있다.

### N+1 문제가 무엇이며 어떻게 해결하는가

연관 엔티티를 Lazy Loading으로 가져올 때, 컬렉션 요소 N개에 대해 N번의 추가 쿼리가 발생하는 문제다. JPQL의 `JOIN FETCH` 또는 `@EntityGraph`로 한 번의 쿼리에 연관 데이터를 함께 가져오도록 해결한다. `hibernate.generate_statistics`를 활성화해 실행 쿼리 수를 모니터링하면 N+1 여부를 빠르게 감지할 수 있다.

### 인덱스가 있는데도 옵티마이저가 풀 스캔을 선택하는 이유는 무엇인가

선택도(Selectivity)가 낮을 때 발생한다. 조건에 일치하는 행이 전체의 20~30% 이상이면 옵티마이저는 랜덤 I/O가 많은 인덱스 스캔보다 순차적인 풀 스캔을 선택한다. 통계 오차, 함수 적용, 타입 불일치, LIKE 패턴 선행 와일드카드도 인덱스를 무력화하는 원인이다.

### GROUP BY와 ORDER BY에서 filesort를 제거하는 방법은 무엇인가

GROUP BY와 ORDER BY 컬럼을 인덱스에 포함시켜 인덱스 순서대로 처리되도록 하면 filesort가 발생하지 않는다. GROUP BY만 있다면 커버링 인덱스를 구성해 `Using index for group-by`로 만드는 것이 가장 효과적이다. `sort_buffer_size` 증가는 메모리 내 정렬을 도와주지만 근본 해결책은 아니다.
