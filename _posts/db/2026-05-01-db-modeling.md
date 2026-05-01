---
title: "DB 모델링"
categories: DB
tags: [DB 모델링, ERD, 개념적 설계, 논리적 설계, 물리적 설계, 식별관계]
toc: true
toc_sticky: true
toc_label: 목차
---

## 비유로 시작하기

건물을 지을 때 세 단계가 있습니다. 먼저 건축가가 **개념 스케치**(어떤 건물을 지을지)를 그립니다. 그다음 **설계 도면**(방 배치, 크기)을 만듭니다. 마지막으로 **시공 도면**(콘크리트 두께, 배선 위치)을 작성합니다.

DB 모델링도 동일하게 세 단계로 진행됩니다.

---

## 모델링 3단계

<div class="mermaid">
graph LR
    A[개념적 모델링<br/>무엇을 저장할까?<br/>엔티티 식별] -->
    B[논리적 모델링<br/>어떻게 구조화할까?<br/>속성, 관계, 정규화] -->
    C[물리적 모델링<br/>어떻게 구현할까?<br/>테이블, 인덱스, 파티션]

    style A fill:#AED6F1
    style B fill:#A9DFBF
    style C fill:#F9E79F
</div>

---

## 개념적 모델링

**"무엇을 저장해야 하는가"**를 정의합니다. 기술적 세부사항 없이 비즈니스 관점에서 엔티티와 관계를 식별합니다.

### 이커머스 시스템 예시

```
엔티티 식별:
- 고객 (Customer)
- 상품 (Product)
- 카테고리 (Category)
- 주문 (Order)
- 리뷰 (Review)
- 장바구니 (Cart)

관계 식별:
- 고객은 여러 주문을 한다 (1:N)
- 주문에는 여러 상품이 포함된다 (N:M)
- 상품은 하나의 카테고리에 속한다 (N:1)
- 고객은 상품에 리뷰를 남긴다 (N:M)
```

---

## 논리적 모델링

**"어떤 속성을 가지고, 어떤 관계인가"**를 상세히 정의합니다. DBMS에 독립적입니다.

### ERD (Entity-Relationship Diagram)

<div class="mermaid">
erDiagram
    CUSTOMER {
        bigint customer_id PK
        varchar name
        varchar email
        varchar phone
        datetime created_at
    }
    ORDER {
        bigint order_id PK
        bigint customer_id FK
        varchar status
        decimal total_amount
        datetime ordered_at
    }
    ORDER_ITEM {
        bigint order_item_id PK
        bigint order_id FK
        bigint product_id FK
        int quantity
        decimal unit_price
    }
    PRODUCT {
        bigint product_id PK
        bigint category_id FK
        varchar name
        decimal price
        int stock
    }
    CATEGORY {
        bigint category_id PK
        bigint parent_id FK
        varchar name
    }

    CUSTOMER ||--o{ ORDER : "places"
    ORDER ||--|{ ORDER_ITEM : "contains"
    PRODUCT ||--o{ ORDER_ITEM : "included in"
    CATEGORY ||--o{ PRODUCT : "has"
    CATEGORY ||--o{ CATEGORY : "parent of"
</div>

---

## 관계 유형

### 1:1 (일대일)

한 엔티티가 다른 엔티티 하나와만 연결됩니다.

```sql
-- 사용자와 사용자 프로필 (자주 조회되지 않는 정보 분리)
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at DATETIME NOT NULL
);

CREATE TABLE user_profiles (
    user_id BIGINT PRIMARY KEY,  -- FK이자 PK (식별 관계)
    bio TEXT,
    avatar_url VARCHAR(500),
    website VARCHAR(200),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

언제 분리하나:
- 조회 빈도가 다를 때 (users는 항상 조회, profiles는 마이페이지에서만)
- 보안상 민감 정보 분리 (주민번호, 결제정보)
- 선택적 정보 (없는 경우가 많을 때 NULL 컬럼보다 별도 테이블이 나음)

### 1:N (일대다)

가장 흔한 관계. 부모-자식 구조.

```sql
CREATE TABLE departments (
    dept_id BIGINT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE employees (
    emp_id BIGINT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    dept_id BIGINT NOT NULL,  -- FK: N 쪽에 FK 위치
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
);
```

### N:M (다대다)

반드시 **연결 테이블(Junction Table)**을 통해 구현합니다.

```sql
-- 학생과 수업의 N:M 관계
CREATE TABLE students (
    student_id BIGINT PRIMARY KEY,
    name VARCHAR(100)
);

CREATE TABLE courses (
    course_id BIGINT PRIMARY KEY,
    title VARCHAR(200)
);

-- 연결 테이블: 수강 (enrollment)
CREATE TABLE enrollments (
    student_id BIGINT,
    course_id BIGINT,
    enrolled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    grade CHAR(2),  -- 연결 테이블도 자체 속성을 가질 수 있음
    PRIMARY KEY (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);
```

---

## 식별 관계 vs 비식별 관계

### 식별 관계 (Identifying Relationship)

자식 엔티티의 기본키에 부모의 FK가 포함됩니다. 부모 없이 자식이 존재할 수 없습니다.

```sql
-- 주문 항목은 주문 없이 존재할 수 없음
CREATE TABLE order_items (
    order_id BIGINT,
    item_seq INT,  -- 주문 내 순서
    product_id BIGINT,
    quantity INT,
    PRIMARY KEY (order_id, item_seq),  -- 복합 PK에 부모 ID 포함
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);
```

장점: 데이터 무결성 강함, 부모 삭제 시 자식도 자동 삭제

### 비식별 관계 (Non-Identifying Relationship)

자식 엔티티가 자체 PK를 가집니다. 부모와 독립적으로 존재 가능합니다.

```sql
-- 주문과 배송: 배송은 주문과 독립적으로 관리
CREATE TABLE deliveries (
    delivery_id BIGINT PRIMARY KEY AUTO_INCREMENT,  -- 자체 PK
    order_id BIGINT NOT NULL,  -- FK만, PK에 미포함
    tracking_number VARCHAR(100),
    status VARCHAR(50),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);
```

실무에서는 **비식별 관계 + 대리키(Surrogate Key)**가 일반적으로 더 유연합니다.

---

## 물리적 모델링

**"실제 DBMS에서 어떻게 구현할까"**를 결정합니다. 인덱스, 파티션, 데이터 타입, 기본값을 정합니다.

### 물리적 설계 예시

```sql
CREATE TABLE orders (
    order_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '주문 ID',
    order_number VARCHAR(30) NOT NULL COMMENT '주문번호 (ORD-20260501-000001)',
    customer_id BIGINT UNSIGNED NOT NULL COMMENT '고객 ID',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '1:대기 2:결제완료 3:배송중 4:완료 5:취소',
    total_amount DECIMAL(15, 2) NOT NULL DEFAULT 0.00 COMMENT '총 금액',
    shipping_address JSON COMMENT '배송지 정보',
    ordered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '주문일시',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- 인덱스
    UNIQUE KEY uk_order_number (order_number),
    INDEX idx_customer_id (customer_id),
    INDEX idx_status_ordered_at (status, ordered_at),  -- 복합 인덱스
    INDEX idx_ordered_at (ordered_at)

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='주문 테이블'
  PARTITION BY RANGE (YEAR(ordered_at)) (
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p2026 VALUES LESS THAN (2027),
    PARTITION p_future VALUES LESS THAN MAXVALUE
  );
```

### 데이터 타입 선택 기준

| 데이터 | 권장 타입 | 이유 |
|--------|---------|------|
| PK | BIGINT UNSIGNED AUTO_INCREMENT | 충분한 범위, 부호 없음 |
| 금액 | DECIMAL(15,2) | 부동소수점 오류 없음 |
| 상태값 | TINYINT 또는 ENUM | 저장 공간 최소화 |
| 긴 텍스트 | TEXT | VARCHAR 최대 65535byte 제한 |
| JSON 데이터 | JSON | MySQL 5.7.8+ 기본 지원, 유효성 검증 |
| 날짜시간 | DATETIME | TIMESTAMP는 2038년 문제 |
| 이메일 | VARCHAR(255) | RFC 5321 최대 256자 |

---

## 계층형 구조 설계

카테고리처럼 트리 구조를 DB에 저장하는 방법입니다.

### 인접 목록 (Adjacency List) - 가장 단순

```sql
CREATE TABLE categories (
    category_id BIGINT PRIMARY KEY,
    parent_id BIGINT,  -- 루트는 NULL
    name VARCHAR(100),
    FOREIGN KEY (parent_id) REFERENCES categories(category_id)
);

-- 데이터 예시
INSERT INTO categories VALUES
(1, NULL, '전자제품'),
(2, 1, '컴퓨터'),
(3, 1, '스마트폰'),
(4, 2, '노트북'),
(5, 2, '데스크탑');

-- 특정 노드의 모든 하위 카테고리 조회 (재귀 CTE)
WITH RECURSIVE category_tree AS (
    SELECT category_id, parent_id, name, 0 AS depth
    FROM categories WHERE category_id = 1  -- 루트
    UNION ALL
    SELECT c.category_id, c.parent_id, c.name, ct.depth + 1
    FROM categories c
    JOIN category_tree ct ON c.parent_id = ct.category_id
)
SELECT * FROM category_tree ORDER BY depth, name;
```

### 클로저 테이블 (Closure Table) - 조회 성능 최적화

```sql
-- 모든 조상-자손 관계를 저장
CREATE TABLE category_closure (
    ancestor_id BIGINT,
    descendant_id BIGINT,
    depth INT,
    PRIMARY KEY (ancestor_id, descendant_id)
);

-- 특정 노드의 모든 하위 조회 (JOIN 한 번)
SELECT c.* FROM categories c
JOIN category_closure cc ON c.category_id = cc.descendant_id
WHERE cc.ancestor_id = 1 AND cc.depth > 0;
```

---

## 실무 설계 패턴

### Soft Delete (논리 삭제)

```sql
ALTER TABLE products
ADD COLUMN deleted_at DATETIME NULL DEFAULT NULL,
ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0;

-- 삭제 (실제 DELETE 없음)
UPDATE products SET deleted_at = NOW(), is_deleted = 1 WHERE product_id = 1;

-- 조회 (삭제된 것 제외)
SELECT * FROM products WHERE is_deleted = 0;

-- 인덱스 (조회 성능)
CREATE INDEX idx_is_deleted ON products (is_deleted);
```

### 이력 테이블 (Audit Table)

```sql
CREATE TABLE product_price_history (
    history_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_id BIGINT NOT NULL,
    old_price DECIMAL(15, 2),
    new_price DECIMAL(15, 2),
    changed_by BIGINT COMMENT '변경한 사용자 ID',
    changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_product_id (product_id)
);

-- 트리거로 자동 기록
CREATE TRIGGER product_price_audit
AFTER UPDATE ON products
FOR EACH ROW
BEGIN
    IF OLD.price != NEW.price THEN
        INSERT INTO product_price_history
            (product_id, old_price, new_price, changed_at)
        VALUES (NEW.product_id, OLD.price, NEW.price, NOW());
    END IF;
END;
```

---

## 극한 시나리오

### 시나리오: 대용량 주문 테이블 설계

MAU 1000만, 일 주문 100만 건 → 연간 3.6억 건

```sql
-- 파티션 + 아카이빙 전략
-- 1. 최근 1년: Hot 파티션 (SSD)
-- 2. 1~3년: Warm 파티션 (HDD)
-- 3. 3년 이상: Archive 테이블로 이동

-- 파티션 관리 (매년 새 파티션 추가)
ALTER TABLE orders ADD PARTITION (
    PARTITION p2027 VALUES LESS THAN (2028)
);

-- 오래된 파티션 아카이브
ALTER TABLE orders EXCHANGE PARTITION p2023
WITH TABLE orders_archive_2023;
```

### 시나리오: 조회 성능 병목 해결

```sql
-- 문제: 이 쿼리가 3초 걸림
SELECT * FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.status = 2 AND o.ordered_at > '2026-01-01'
ORDER BY o.ordered_at DESC LIMIT 20;

-- EXPLAIN 분석 → customer_id, status 인덱스 없음

-- 해결: 복합 인덱스 추가
CREATE INDEX idx_status_ordered_at ON orders (status, ordered_at);
-- 0.02초로 단축
```
