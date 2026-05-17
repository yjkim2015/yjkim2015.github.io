---
title: "Spring 면접 — AOP 핵심 질문 (Q11~Q18)"
categories: INTERVIEW
tags: [Spring, 면접, AOP,Proxy,AspectJ]
toc: true
toc_sticky: true
toc_label: 목차
---

## 2. AOP 핵심 질문 (Q11 ~ Q18)

### Q11. AOP의 핵심 개념을 설명하세요

**모범 답변**

| 용어 | 설명 | 예시 |
|---|---|---|
| Aspect | 횡단 관심사 모듈 | 로깅, 트랜잭션 |
| JoinPoint | Advice가 실행될 수 있는 지점 | 메서드 실행 |
| Pointcut | JoinPoint 선택 표현식 | `execution(* com.example.service.*.*(..))` |
| Advice | 실제 실행 로직 | Before, After, Around |
| Weaving | Aspect 적용 과정 | 런타임(Spring), 컴파일타임(AspectJ) |

> **비유:** AOP는 고속도로 톨게이트와 같습니다. 어떤 차가 지나가든(JoinPoint) 톨게이트(Aspect)에서 통행료를 수납합니다. 어떤 차를 검사할지 선택하는 것이 Pointcut입니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** Spring AOP와 AspectJ의 차이는?

Spring AOP: 런타임 프록시 방식, 메서드 실행 JoinPoint만 지원, Spring Bean에만 적용
AspectJ: 컴파일타임/로드타임 위빙, 필드·생성자 등 다양한 JoinPoint, 모든 Java 객체에 적용

성능은 AspectJ가 우수하지만, Spring AOP가 설정이 훨씬 간단합니다.

</details>

---

### Q12. @Around Advice에서 ProceedingJoinPoint.proceed()를 안 부르면?

**모범 답변**

원본 메서드가 실행되지 않습니다. `proceed()`는 체인의 다음 단계(다음 Advice 또는 실제 메서드)를 실행합니다.

```java
@Around("execution(* com.example.service.*.*(..))")
public Object around(ProceedingJoinPoint pjp) throws Throwable {
    log.info("Before");
    Object result = pjp.proceed(); // 이게 없으면 실제 메서드 실행 안 됨
    log.info("After");
    return result;
}
```

`proceed()`를 호출하지 않으면 캐시 구현, 권한 체크 후 차단 등에 활용 가능합니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** Around에서 반환값을 바꿀 수 있나요?

예. `proceed()`의 결과 대신 다른 값을 반환하면 됩니다. 캐시 Aspect에서 캐시 히트 시 실제 메서드 호출 없이 캐시 값을 반환하는 방식으로 사용합니다.

</details>

---

### Q13. Spring AOP 프록시 방식 두 가지를 설명하세요

**모범 답변**

1. **JDK Dynamic Proxy**: 인터페이스 기반. 대상 클래스가 인터페이스를 구현할 때 사용. `java.lang.reflect.Proxy` 활용
2. **CGLIB Proxy**: 클래스 기반. 인터페이스가 없어도 서브클래싱으로 프록시 생성

Spring Boot 2.0부터 기본값이 CGLIB입니다(`spring.aop.proxy-target-class=true`).

> **비유:** JDK Proxy는 "통역사를 통해 소통" (인터페이스 필요), CGLIB는 "말투를 흉내내는 배우" (원본 클래스 상속)

**CGLIB 제약:** `final` 클래스나 `final` 메서드에는 적용 불가.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** 같은 클래스 내에서 메서드를 호출하면 AOP가 적용되나요?

적용되지 않습니다. 프록시를 거치지 않고 직접 호출하기 때문입니다. 이를 "Self-invocation 문제"라 합니다. 해결책: `AopContext.currentProxy()` 사용, 또는 AspectJ 사용.

</details>

---

### Q14. @Transactional이 AOP와 어떻게 연결되나요?

**모범 답변**

`@Transactional`은 AOP Around Advice로 구현됩니다. 메서드 호출 전 트랜잭션을 시작하고, 정상 종료 시 커밋, 예외 발생 시 롤백합니다.

```
클라이언트 → 프록시(트랜잭션 시작) → 실제 메서드 → 프록시(커밋/롤백)
```

Self-invocation 문제: 같은 클래스 내 메서드 A → B 호출 시 B의 `@Transactional`은 무시됩니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** @Transactional을 private 메서드에 붙이면?

동작하지 않습니다. 프록시는 public 메서드만 오버라이드 가능합니다. Spring은 경고하지만 예외를 던지지 않아 실수하기 쉽습니다.

</details>

---

### Q15~Q18. AOP 실전 시나리오 문제들

**Q15. 로깅 Aspect에서 메서드 파라미터를 출력하려면?**

```java
@Before("execution(* com.example.service.*.*(..))")
public void logArgs(JoinPoint jp) {
    log.info("Method: {}, Args: {}",
        jp.getSignature().getName(),
        Arrays.toString(jp.getArgs()));
}
```

**Q16. Pointcut 표현식 `execution(* com.example..*Service.*(..))`의 의미는?**

`com.example` 패키지 이하(`..`) 모든 클래스 중 이름이 `Service`로 끝나는 클래스의 모든 메서드(`*`)에 적용. 반환 타입 무관(`*`), 파라미터 무관(`..`).

**Q17. @annotation Pointcut 활용 예시는?**

커스텀 애노테이션을 만들어 해당 애노테이션이 붙은 메서드에만 Aspect 적용.

```java
@Pointcut("@annotation(com.example.annotation.Audit)")
public void auditMethods() {}
```

**Q18. Advice 실행 순서가 중요한 경우 어떻게 제어하나요?**

`@Order` 애노테이션으로 Aspect 우선순위를 지정합니다. 숫자가 낮을수록 먼저 실행됩니다.

---

---

## 다른 파트 보기

- [Part 1: DI/IoC (Q1~Q10)](/interview/spring-interview-part1/)
- [Part 2: AOP (Q11~Q18)](/interview/spring-interview-part2/)
- [Part 3: Transaction (Q19~Q27)](/interview/spring-interview-part3/)
- [Part 4: JPA (Q28~Q38)](/interview/spring-interview-part4/)
- [Part 5: Security (Q39~Q45)](/interview/spring-interview-part5/)
- [Part 6: WebFlux (Q46~Q50)](/interview/spring-interview-part6/)
