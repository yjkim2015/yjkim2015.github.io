---
title: "정규화와 반정규화"
categories: DB
tags: [정규화, 반정규화, 1NF, 2NF, 3NF, BCNF, 데이터베이스 설계]
toc: true
toc_sticky: true
toc_label: 목차
---

## 비유로 시작하기

이사할 때 짐 정리를 생각해보세요. 처음에는 모든 것을 한 상자에 넣으면 찾기 편합니다. 하지만 물건이 많아지면 카테고리별로 분류해야 합니다. 그런데 너무 세분화하면 "양말을 찾으려면 5개의 서랍을 확인해야 해" 문제가 생깁니다.

정규화는 **데이터베이스 테이블을 체계적으로 분리하여 데이터 중복을 제거하고 정합성을 높이는 과정**입니다. 반정규화는 **성능을 위해 의도적으로 중복을 허용**하는 것입니다.

---

## 정규화가 필요한 이유

정규화되지 않은 테이블의 문제점을 먼저 보겠습니다.

**비정규화 테이블 예시**:

| 주문ID | 고객ID | 고객명 | 고객이메일 | 상품ID | 상품명 | 가격 | 수량 |
|--------|--------|--------|-----------|--------|--------|------|------|
| 1 | 100 | 김철수 | kim@ex.com | P1 | 노트북 | 1000000 | 1 |
| 1 | 100 | 김철수 | kim@ex.com | P2 | 마우스 | 30000 | 2 |
| 2 | 200 | 이영희 | lee@ex.com | P1 | 노트북 | 1000000 | 1 |

**문제**:
- **삽입 이상**: 상품을 등록하려면 주문이 있어야 함
- **삭제 이상**: 주문 1을 삭제하면 고객 100의 이메일 정보가 사라짐
- **수정 이상**: 노트북 가격 변경 시 해당하는 모든 행을 수정해야 함 (일부만 수정되면 정합성 깨짐)

---

## 제1정규형 (1NF)

**규칙**: 모든 컬럼의 값이 원자값(Atomic)이어야 합니다. 즉, 하나의 셀에 여러 값이 없어야 합니다.

**1NF 위반 예시**:

| 주문ID | 고객명 | 상품목록 |
|--------|--------|---------|
| 1 | 김철수 | 노트북, 마우스, 키보드 |

**1NF 적용 후**:

| 주문ID | 고객명 | 상품 |
|--------|--------|------|
| 1 | 김철수 | 노트북 |
| 1 | 김철수 | 마우스 |
| 1 | 김철수 | 키보드 |

**또 다른 위반**: 전화번호를 하나의 컬럼에 여러 개 저장

```sql
-- 위반
tel VARCHAR(100) -- "010-1234-5678, 02-1234-5678"

-- 해결
CREATE TABLE customer_phones (
    customer_id BIGINT,
    phone_number VARCHAR(20),
    phone_type VARCHAR(10),  -- MOBILE, HOME, OFFICE
    PRIMARY KEY (customer_id, phone_number)
);
```

---

## 제2정규형 (2NF)

**규칙**: 1NF를 만족하면서, **부분 함수 종속을 제거**합니다. 복합 기본키에서 일부 키에만 종속되는 컬럼이 없어야 합니다.

**2NF 위반 예시** (기본키: 주문ID + 상품ID):

| 주문ID | 상품ID | 수량 | 상품명 | 고객ID |
|--------|--------|------|--------|--------|
| 1 | P1 | 2 | 노트북 | 100 |

- `수량`: (주문ID, 상품ID) 모두에 종속 → 완전 함수 종속 (OK)
- `상품명`: 상품ID에만 종속 → **부분 함수 종속** (위반)
- `고객ID`: 주문ID에만 종속 → **부분 함수 종속** (위반)

**2NF 적용 후**:

```sql
-- 주문 테이블 (주문ID → 고객ID)
CREATE TABLE orders (
    order_id BIGINT PRIMARY KEY,
    customer_id BIGINT
);

-- 주문상품 테이블 (주문ID + 상품ID → 수량)
CREATE TABLE order_items (
    order_id BIGINT,
    product_id BIGINT,
    quantity INT,
    PRIMARY KEY (order_id, product_id)
);

-- 상품 테이블 (상품ID → 상품명, 가격)
CREATE TABLE products (
    product_id BIGINT PRIMARY KEY,
    product_name VARCHAR(200),
    price DECIMAL(15, 2)
);
```

---

## 제3정규형 (3NF)

**규칙**: 2NF를 만족하면서, **이행 함수 종속을 제거**합니다. 기본키가 아닌 컬럼이 다른 비기본키 컬럼을 결정하면 안 됩니다.

**3NF 위반 예시**:

| 직원ID | 부서ID | 부서명 | 부서장 |
|--------|--------|--------|--------|
| E1 | D1 | 개발팀 | 박팀장 |
| E2 | D1 | 개발팀 | 박팀장 |

- 직원ID → 부서ID (OK)
- 부서ID → 부서명, 부서장
- 따라서: 직원ID → 부서ID → 부서명 (**이행 종속**, 위반)

**3NF 적용 후**:

```sql
CREATE TABLE employees (
    employee_id BIGINT PRIMARY KEY,
    name VARCHAR(100),
    department_id BIGINT
);

CREATE TABLE departments (
    department_id BIGINT PRIMARY KEY,
    department_name VARCHAR(100),
    manager VARCHAR(100)
);
```

---

## BCNF (Boyce-Codd Normal Form)

**규칙**: 3NF보다 강화. 모든 결정자가 후보키여야 합니다.

**BCNF 위반 예시**:

| 학생 | 과목 | 교수 |
|------|------|------|
| 홍길동 | 데이터베이스 | 김교수 |
| 홍길동 | 알고리즘 | 이교수 |

- 기본키: (학생, 과목)
- 교수 → 과목 (교수는 하나의 과목만 담당)
- 교수는 후보키가 아닌데 과목을 결정 → 위반

```sql
-- BCNF 분해
CREATE TABLE professor_course (
    professor VARCHAR(100) PRIMARY KEY,
    course VARCHAR(100)
);

CREATE TABLE student_professor (
    student VARCHAR(100),
    professor VARCHAR(100),
    PRIMARY KEY (student, professor)
);
```

---

## 4NF, 5NF

**4NF**: 다치 종속(Multi-valued Dependency) 제거
**5NF**: 조인 종속(Join Dependency) 제거

실무에서는 3NF 또는 BCNF까지 적용하는 경우가 대부분입니다.

---

## 반정규화 (Denormalization)

### 반정규화가 필요한 이유

정규화된 테이블은 JOIN이 많아져 성능이 저하될 수 있습니다.

```sql
-- 정규화된 상태: 주문 목록 조회
SELECT o.order_id, c.customer_name, c.email,
       p.product_name, oi.quantity, p.price
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.customer_id = 100;
-- 4개 테이블 JOIN → 대용량에서 느림
```

### 반정규화 기법

#### 1. 컬럼 중복 (Column Duplication)

```sql
-- order_items에 product_name, price 복사
ALTER TABLE order_items
ADD COLUMN product_name VARCHAR(200),
ADD COLUMN unit_price DECIMAL(15, 2);

-- 이제 JOIN 없이 조회 가능
SELECT order_id, product_name, unit_price, quantity
FROM order_items
WHERE order_id = 1;
```

주문 시점의 가격이 상품 가격 변경에 영향받지 않는다는 **비즈니스 요구사항**도 충족합니다.

#### 2. 집계 컬럼 추가 (Derived Column)

```sql
-- orders 테이블에 총 금액 미리 계산
ALTER TABLE orders
ADD COLUMN total_amount DECIMAL(15, 2);

-- 주문 생성 시 집계값 함께 저장
-- (매 조회마다 SUM() 계산 불필요)
```

#### 3. 테이블 합치기 (Table Merging)

자주 JOIN되는 1:1 관계 테이블을 합칩니다.

```sql
-- 분리된 경우
SELECT u.id, u.name, up.avatar_url, up.bio
FROM users u
JOIN user_profiles up ON u.id = up.user_id;

-- 합친 경우 (1:1 관계이므로)
SELECT id, name, avatar_url, bio
FROM users;
```

#### 4. 이력 테이블 (Summary Table)

통계/집계용 별도 테이블을 만들어 주기적으로 집계합니다.

```sql
-- 매일 집계하는 요약 테이블
CREATE TABLE daily_sales_summary (
    date DATE PRIMARY KEY,
    total_orders INT,
    total_revenue DECIMAL(20, 2),
    avg_order_value DECIMAL(15, 2)
);

-- 대시보드에서 수억 건 orders 테이블 집계 대신 이 테이블 조회
SELECT * FROM daily_sales_summary
WHERE date BETWEEN '2026-01-01' AND '2026-01-31';
```

---

## 성능 vs 정합성 트레이드오프

<div class="mermaid">
graph LR
    NORM[정규화] -->|더 많은 JOIN| SLOW_READ[느린 읽기]
    NORM -->|데이터 중복 없음| CONSIST[데이터 정합성 높음]
    NORM -->|쓰기 1곳만| FAST_WRITE[빠른 쓰기]

    DENORM[반정규화] -->|JOIN 감소| FAST_READ[빠른 읽기]
    DENORM -->|중복 데이터| INCONSIST[정합성 관리 필요]
    DENORM -->|여러 곳 동기화| SLOW_WRITE[느린/복잡한 쓰기]
</div>

---

## 실무 판단 기준

```
정규화 유지:
✓ 데이터 정합성이 최우선 (금융, 의료)
✓ 쓰기 작업이 많음 (트랜잭션 시스템)
✓ 데이터 변경이 자주 발생
✓ 시스템이 복잡하지 않아 JOIN 비용 감당 가능

반정규화 적용:
✓ 읽기 성능이 중요 (대시보드, 리포트)
✓ 읽기:쓰기 비율이 100:1 이상
✓ 특정 쿼리가 성능 병목임이 측정됨
✓ 데이터 동기화 로직을 관리할 수 있음

황금 규칙:
"먼저 정규화하고, 성능 문제가 측정되면 반정규화하라"
성능 문제 없이 미리 반정규화하는 것은 조기 최적화의 오류
```

---

## 극한 시나리오

### 시나리오: 반정규화 후 데이터 불일치

```
문제:
- orders 테이블에 customer_name 복사 (반정규화)
- 고객이 이름을 변경
- orders 테이블의 이름은 갱신하지 않음

결과: DB에 같은 고객이 두 가지 이름으로 존재

해결책 1: 트리거로 자동 동기화
CREATE TRIGGER update_customer_name
AFTER UPDATE ON customers
FOR EACH ROW
UPDATE orders SET customer_name = NEW.name
WHERE customer_id = NEW.id;

해결책 2: 이벤트 기반 동기화 (주문 시점 이름은 변경 안 함)
→ 사실 주문 시점의 고객명이 맞을 수 있음 (법적 기록)
→ 반정규화 전에 비즈니스 요구사항을 명확히 해야 함
```
