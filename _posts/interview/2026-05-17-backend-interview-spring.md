---
title: "Spring 면접 질문 50선 — 시니어 면접에서 자주 나오는 핵심 질문과 모범 답변"
categories: INTERVIEW
tags: [Spring, 면접, Interview, DI, AOP, Transaction, JPA, Security]
toc: true
toc_sticky: true
toc_label: 목차
---

Spring 면접은 단순 암기로는 절대 통과할 수 없습니다. 면접관은 "Bean이 뭔가요?"를 물어볼 때 실은 **의존성 관리 철학을 이해하고 있는가**를 봅니다. 이 글은 시니어 면접에서 자주 나오는 질문 50개를 카테고리별로 정리하고, 면접관 관점에서 "왜 이 질문을 하는가"까지 분석했습니다.

---

## 카테고리별 바로가기

각 파트를 클릭하면 상세 질문과 모범 답변을 확인할 수 있습니다.

### [Part 1: DI / IoC 핵심 질문 (Q1 ~ Q10)](/interview/spring-interview-part1/)
- Bean 생명주기, 스코프, 의존성 주입 방식 차이
- @Component vs @Bean, 순환 참조 해결

### [Part 2: AOP 핵심 질문 (Q11 ~ Q18)](/interview/spring-interview-part2/)
- Proxy 동작 원리, JDK Dynamic Proxy vs CGLIB
- @Transactional이 AOP로 동작하는 메커니즘

### [Part 3: Transaction 핵심 질문 (Q19 ~ Q27)](/interview/spring-interview-part3/)
- Propagation, Isolation Level, 롤백 규칙
- 분산 트랜잭션, 실무 장애 사례

### [Part 4: JPA 핵심 질문 (Q28 ~ Q38)](/interview/spring-interview-part4/)
- N+1 문제, 영속성 컨텍스트, Lazy Loading
- 벌크 연산, QueryDSL, 2차 캐시

### [Part 5: Spring Security 핵심 질문 (Q39 ~ Q45)](/interview/spring-interview-part5/)
- Filter Chain, OAuth2, JWT 검증 플로우
- CORS, CSRF, 세션 관리

### [Part 6: WebFlux / 심화 질문 (Q46 ~ Q50)](/interview/spring-interview-part6/)
- Reactor, Mono/Flux, 배압(Backpressure)
- 블로킹 코드 혼용 시 위험성

---

## 면접 전략 팁

1. **깊이 우선**: 10개를 깊게 아는 게 50개를 얕게 아는 것보다 낫다
2. **실무 연결**: "프로젝트에서 이 문제를 이렇게 해결했다"를 항상 준비
3. **트레이드오프**: 정답보다 "왜 이 선택을 했는가"를 설명하는 능력
4. **꼬리질문 대비**: 각 답변의 "그러면 왜?"를 3단계까지 준비
