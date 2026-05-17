---
title: "Spring 면접 — Transaction 핵심 질문 (Q19~Q27)"
categories: INTERVIEW
tags: [Spring, 면접, Transaction,Propagation,Isolation]
toc: true
toc_sticky: true
toc_label: 목차
---

## 3. Transaction 핵심 질문 (Q19 ~ Q27)

### Q19. @Transactional의 propagation 옵션을 설명하세요

**모범 답변**

| Propagation | 설명 | 사용 시나리오 |
|---|---|---|
| REQUIRED (기본) | 기존 트랜잭션 사용, 없으면 생성 | 일반적인 서비스 메서드 |
| REQUIRES_NEW | 항상 새 트랜잭션 생성, 기존 일시 중단 | 감사 로그(실패해도 기록 유지) |
| NESTED | 중첩 트랜잭션(Savepoint) | 부분 롤백 필요 시 |
| SUPPORTS | 트랜잭션 있으면 참여, 없으면 비트랜잭션 | 읽기 전용 조회 |
| NOT_SUPPORTED | 트랜잭션 없이 실행, 기존 중단 | 트랜잭션 불필요한 외부 호출 |
| NEVER | 트랜잭션 있으면 예외 | 트랜잭션 금지 구간 |
| MANDATORY | 반드시 기존 트랜잭션 필요, 없으면 예외 | 서비스 내부 메서드 보호 |

> **비유:** `REQUIRED`는 택시 합승, `REQUIRES_NEW`는 별도 택시 호출, `NESTED`는 중간에 내렸다가 다시 탑승 가능한 정류장이 있는 버스

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** REQUIRES_NEW 사용 시 주의사항은?

부모 트랜잭션과 자식 트랜잭션이 별개이므로, 부모가 롤백해도 자식은 커밋됩니다. 이를 이용해 감사 로그를 별도 트랜잭션으로 저장합니다. 그러나 **데드락 위험**이 있습니다 — 같은 행을 두 트랜잭션이 접근할 때.

</details>

---

### Q20. @Transactional의 isolation level을 설명하세요

**모범 답변**

| Isolation Level | Dirty Read | Non-repeatable Read | Phantom Read |
|---|---|---|---|
| READ_UNCOMMITTED | 발생 | 발생 | 발생 |
| READ_COMMITTED | 방지 | 발생 | 발생 |
| REPEATABLE_READ | 방지 | 방지 | 발생 |
| SERIALIZABLE | 방지 | 방지 | 방지 |

- **Dirty Read**: 커밋 안 된 데이터 읽기
- **Non-repeatable Read**: 같은 쿼리 두 번 실행 시 결과 다름
- **Phantom Read**: 같은 조건 쿼리 시 행 개수 다름

실무에서는 DB 기본값(MySQL InnoDB: REPEATABLE_READ)을 사용하는 경우가 많습니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** MySQL InnoDB에서 REPEATABLE_READ가 Phantom Read를 방지하는 방법은?

MVCC(Multi-Version Concurrency Control)를 사용합니다. 트랜잭션 시작 시점의 스냅샷을 읽으므로, 다른 트랜잭션이 행을 추가해도 보이지 않습니다.

</details>

---

### Q21. @Transactional(readOnly=true)의 효과는?

**모범 답변**

1. **플러시 비활성화**: 영속성 컨텍스트의 변경 감지(dirty checking)를 건너뜀 → 성능 향상
2. **DB 옵티마이저 힌트**: 일부 DB는 읽기 전용 트랜잭션을 최적화
3. **읽기 전용 DB 라우팅**: 리플리케이션 환경에서 슬레이브 DB로 자동 라우팅 가능

```java
@Transactional(readOnly = true)
public List<Order> findAllOrders() {
    // 변경 감지 없음, 스냅샷 불필요
    return orderRepository.findAll();
}
```

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** readOnly=true인데 실수로 엔티티를 수정하면?

플러시가 발생하지 않으므로 DB에는 반영되지 않습니다. 예외가 발생하는 것이 아니라 조용히 무시됩니다. 이 점이 오히려 혼란을 줄 수 있습니다.

</details>

---

### Q22. 롤백 규칙 — checkedException은 롤백 안 되는 이유는?

**모범 답변**

Spring `@Transactional`의 기본 롤백 규칙:
- **RuntimeException, Error**: 자동 롤백
- **CheckedException**: 자동 롤백 안 됨 (커밋)

이유: EJB 설계 관례를 따른 것으로, CheckedException은 "예상 가능한 비즈니스 예외"로 간주하기 때문입니다.

```java
@Transactional(rollbackFor = Exception.class) // 모든 예외에 롤백
public void process() throws IOException { ... }

@Transactional(noRollbackFor = IllegalArgumentException.class)
public void process() { ... }
```

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** 트랜잭션 내에서 예외를 catch해서 처리하면 롤백이 일어나나요?

예외가 트랜잭션 경계 밖으로 나가지 않으면 롤백이 일어나지 않습니다. 단, `TransactionAspectSupport.currentTransactionStatus().setRollbackOnly()`를 호출하면 강제 롤백 마킹이 가능합니다.

</details>

---

### Q23 ~ Q27. Transaction 실전 문제

**Q23. 트랜잭션 경계와 영속성 컨텍스트 관계는?**

기본적으로 트랜잭션과 영속성 컨텍스트 생명주기가 일치합니다(OSIV 비활성 시). 트랜잭션 시작 = PC 생성, 트랜잭션 종료 = PC 플러시 및 종료.

**Q24. TransactionSynchronizationManager의 역할은?**

현재 스레드의 트랜잭션 관련 리소스(Connection, EntityManager 등)를 ThreadLocal로 관리합니다.

**Q25. 트랜잭션 없이 JPA를 사용하면?**

조회는 가능하지만 변경은 안 됩니다. `@Transactional` 없이 `save()` 호출 시 예외 발생.

**Q26. 분산 트랜잭션(Distributed Transaction)은 어떻게 처리하나요?**

2PC(Two-Phase Commit) 또는 Saga 패턴. 마이크로서비스에서는 Saga(Choreography/Orchestration)를 주로 사용합니다.

**Q27. 낙관적 잠금 vs 비관적 잠금은?**

- **낙관적**: `@Version` 필드 사용, 충돌 시 `OptimisticLockException`, 충돌 드문 환경
- **비관적**: `SELECT FOR UPDATE`, 충돌 잦은 환경, 데드락 위험

---

---

## 다른 파트 보기

- [Part 1: DI/IoC (Q1~Q10)](/interview/spring-interview-part1/)
- [Part 2: AOP (Q11~Q18)](/interview/spring-interview-part2/)
- [Part 3: Transaction (Q19~Q27)](/interview/spring-interview-part3/)
- [Part 4: JPA (Q28~Q38)](/interview/spring-interview-part4/)
- [Part 5: Security (Q39~Q45)](/interview/spring-interview-part5/)
- [Part 6: WebFlux (Q46~Q50)](/interview/spring-interview-part6/)
