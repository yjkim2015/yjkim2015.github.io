---
title: "Spring 면접 — JPA 핵심 질문 (Q28~Q38)"
categories: INTERVIEW
tags: [Spring, 면접, JPA,N+1,영속성,Hibernate]
toc: true
toc_sticky: true
toc_label: 목차
---

## 4. JPA 핵심 질문 (Q28 ~ Q38)

### Q28. N+1 문제란 무엇이고 어떻게 해결하나요?

**모범 답변**

1건 조회 쿼리 이후 N개 연관 엔티티를 N번 추가 조회하는 문제입니다.

```java
// 문제 코드 - Order 목록 1번 + Order별 Member 조회 N번 = N+1 쿼리
List<Order> orders = orderRepository.findAll(); // 1번
orders.forEach(o -> o.getMember().getName()); // N번
```

**해결책:**

1. `JPQL fetch join`: `SELECT o FROM Order o JOIN FETCH o.member`
2. `@EntityGraph`: `@EntityGraph(attributePaths = {"member"})`
3. `@BatchSize`: 지연 로딩을 IN 쿼리로 묶음
4. DTO 프로젝션: 필요한 컬럼만 선택

> **비유:** N+1은 마트에서 계산할 때 물건 하나씩 바코드 찍는 대신, 카트째 한 번에 스캔하지 못하는 상황입니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** fetch join의 단점은?

1. 페이징과 함께 사용 시 경고 + 메모리에서 페이징 처리 (컬렉션 fetch join)
2. 2개 이상의 컬렉션을 동시에 fetch join 불가
3. 해결: `@BatchSize` 또는 DTO 조회

</details>

---

### Q29. 영속성 컨텍스트의 1차 캐시 동작 원리는?

**모범 답변**

영속성 컨텍스트는 `Map<@Id, Entity>` 형태의 1차 캐시를 가집니다. 같은 트랜잭션에서 같은 ID로 조회하면 DB를 거치지 않고 캐시에서 반환합니다.

```java
// 1번만 SELECT
Order order1 = em.find(Order.class, 1L);
Order order2 = em.find(Order.class, 1L); // 캐시 히트
System.out.println(order1 == order2); // true (동일 인스턴스)
```

**동일성 보장**: 같은 트랜잭션에서 같은 엔티티는 항상 같은 인스턴스입니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** JPQL 쿼리는 1차 캐시를 사용하나요?

JPQL은 항상 DB를 먼저 조회합니다. 조회 후 결과를 1차 캐시와 병합합니다. 같은 ID 엔티티가 있으면 DB 결과를 버리고 캐시의 인스턴스를 반환합니다.

</details>

---

### Q30. CascadeType과 orphanRemoval의 차이는?

**모범 답변**

`CascadeType.REMOVE`: 부모 삭제 시 자식도 삭제 (`em.remove(parent)` → 자식도 삭제)

`orphanRemoval=true`: 부모와의 **연관 관계가 끊어진** 자식을 자동 삭제

```java
parent.getChildren().remove(child); // orphanRemoval=true면 child DELETE 쿼리 발생
```

> **비유:** CascadeType.REMOVE는 사장이 퇴사할 때 직원도 해고, orphanRemoval은 팀장이 바뀌어 팀원이 소속 없어지면 자동 해고

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** CascadeType.ALL + orphanRemoval=true를 함께 쓰는 경우는?

완전한 소유 관계(부모 없이 자식이 독립 존재 불가)일 때 사용합니다. 예: `Order` → `OrderItem` (주문 없는 주문항목은 의미 없음)

</details>

---

### Q31. @OneToMany 기본 FetchType이 LAZY인 이유는?

**모범 답변**

컬렉션은 크기를 예측할 수 없기 때문입니다. EAGER로 설정 시 단순 조회에도 모든 자식 데이터를 로딩합니다. 100개 Order를 조회하면 모든 OrderItem까지 한꺼번에 로딩되어 메모리 폭발 위험이 있습니다.

`@ManyToOne`은 단일 엔티티라 EAGER가 기본이지만, 이것도 N+1 문제를 유발하므로 명시적으로 LAZY로 변경하는 것을 권장합니다.

---

### Q32. 변경 감지(Dirty Checking) 원리는?

**모범 답변**

JPA는 엔티티를 영속성 컨텍스트에 저장할 때 **스냅샷**(최초 상태 복사본)을 함께 보관합니다. 트랜잭션 커밋 시 현재 엔티티 상태와 스냅샷을 비교하여 변경된 필드만 UPDATE 쿼리를 생성합니다.

```java
@Transactional
public void updateOrderStatus(Long orderId) {
    Order order = orderRepository.findById(orderId).get();
    order.changeStatus(OrderStatus.COMPLETED); // setter 없이도 변경 감지
    // save() 호출 없이도 트랜잭션 종료 시 UPDATE 발생
}
```

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** @DynamicUpdate는 무엇인가요?

기본적으로 JPA는 변경 여부와 관계없이 모든 컬럼을 UPDATE합니다. `@DynamicUpdate`는 실제 변경된 컬럼만 UPDATE 쿼리에 포함합니다. 컬럼이 매우 많을 때 유용하지만, 쿼리 캐싱 효율이 떨어집니다.

</details>

---

### Q33 ~ Q38. JPA 심화 문제

**Q33. OSIV(Open Session In View) 패턴의 장단점은?**

장점: View에서도 지연 로딩 가능. 단점: 트랜잭션 종료 후에도 DB 커넥션 유지 → 커넥션 고갈 위험. Spring Boot 기본 활성화. 성능이 중요한 서비스에서는 비활성화 권장(`spring.jpa.open-in-view=false`).

**Q34. 프록시 초기화와 LazyInitializationException은?**

영속성 컨텍스트 종료 후 지연 로딩 시도 시 발생. 해결: 트랜잭션 안에서 초기화, fetch join, DTO 변환.

**Q35. Querydsl을 사용하는 이유는?**

타입 안전 동적 쿼리 생성. JPQL String 연결보다 컴파일 타임 오류 감지 가능.

**Q36. Spring Data JPA의 @Query와 Querydsl 선택 기준은?**

정적 쿼리: `@Query`. 동적 조건(검색 필터 등): Querydsl.

**Q37. 엔티티와 DTO를 분리해야 하는 이유는?**

엔티티는 영속성 컨텍스트와 연결됨. View에 노출 시 불필요한 연관 로딩, 순환 참조(JSON 직렬화 시) 위험. API 계약과 내부 도메인 모델 분리.

**Q38. JPA save()와 saveAndFlush()의 차이는?**

`save()`: 트랜잭션 종료 시 플러시. `saveAndFlush()`: 즉시 플러시하여 DB에 반영. 같은 트랜잭션 내에서 저장 후 즉시 조회할 때 사용.

---

---

## 다른 파트 보기

- [Part 1: DI/IoC (Q1~Q10)](/interview/spring-interview-part1/)
- [Part 2: AOP (Q11~Q18)](/interview/spring-interview-part2/)
- [Part 3: Transaction (Q19~Q27)](/interview/spring-interview-part3/)
- [Part 4: JPA (Q28~Q38)](/interview/spring-interview-part4/)
- [Part 5: Security (Q39~Q45)](/interview/spring-interview-part5/)
- [Part 6: WebFlux (Q46~Q50)](/interview/spring-interview-part6/)
