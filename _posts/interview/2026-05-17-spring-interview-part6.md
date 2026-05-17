---
title: "Spring 면접 — WebFlux 심화 질문 (Q46~Q50)"
categories: INTERVIEW
tags: [Spring, 면접, WebFlux,Reactor,비동기]
toc: true
toc_sticky: true
toc_label: 목차
---

## 6. WebFlux / 기타 심화 질문 (Q46 ~ Q50)

### Q46. Spring MVC vs Spring WebFlux 선택 기준은?

**모범 답변**

| 기준 | Spring MVC | Spring WebFlux |
|---|---|---|
| 모델 | 동기 블로킹 | 비동기 논블로킹 |
| 스레드 | 요청당 1스레드 | 이벤트 루프 |
| 적합 환경 | 전통적 CRUD, DB 중심 | I/O 집중, 스트리밍, SSE |
| 학습 곡선 | 낮음 | 높음 (Reactor) |

> **비유:** MVC는 레스토랑에서 테이블마다 전담 웨이터 배정, WebFlux는 한 웨이터가 여러 테이블을 비동기로 서빙

**JPA(Blocking)와 WebFlux는 잘 맞지 않습니다.** R2DBC나 MongoDB Reactive 드라이버를 사용해야 합니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** WebFlux에서 블로킹 코드가 섞이면 어떤 문제가 생기나요?

이벤트 루프 스레드가 블로킹되어 전체 처리량이 급감합니다. 블로킹 코드는 `Schedulers.boundedElastic()`으로 별도 스레드풀에서 실행해야 합니다.

</details>

---

### Q47. Spring Boot Actuator의 주요 엔드포인트는?

주요 엔드포인트: `/health`(헬스체크), `/metrics`(메트릭), `/info`(앱 정보), `/env`(환경변수), `/beans`(Bean 목록), `/mappings`(URL 매핑), `/httptrace`(HTTP 이력).

프로덕션에서는 `/health`와 `/metrics`만 외부 노출하고, 나머지는 보안 처리합니다.

---

### Q48. Spring Cache 추상화를 설명하세요

`@Cacheable`, `@CachePut`, `@CacheEvict`로 선언적 캐싱. 구현체로 Caffeine, Redis, EhCache 등을 교체 가능합니다.

```java
@Cacheable(value = "products", key = "#id", unless = "#result == null")
public Product findById(Long id) { ... }

@CacheEvict(value = "products", key = "#product.id")
public void update(Product product) { ... }
```

---

### Q49. Spring Batch의 구성 요소는?

`Job` → `Step` → `ItemReader` → `ItemProcessor` → `ItemWriter`. `JobLauncher`가 `Job`을 실행하고, `JobRepository`가 실행 이력을 관리합니다. 대용량 데이터 처리에 적합하고 Chunk 기반 처리로 메모리를 효율화합니다.

---

### Q50. Spring Cloud와 마이크로서비스 패턴은?

주요 컴포넌트:
- **Gateway**: API Gateway (라우팅, 필터, Rate Limiting)
- **Eureka**: 서비스 디스커버리
- **Config**: 중앙화된 설정 관리
- **OpenFeign**: 선언적 HTTP 클라이언트
- **Resilience4j**: Circuit Breaker, Retry, Bulkhead

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** Circuit Breaker 패턴이 필요한 이유는?

연쇄 장애(Cascading Failure) 방지. 하나의 서비스 장애가 호출 대기로 인해 전체 시스템으로 전파되는 것을 차단합니다. CLOSED → OPEN → HALF_OPEN 상태로 자동 복구 시도합니다.

</details>

---

## 마무리 — 면접 전략

Spring 면접에서 좋은 점수를 받으려면:

1. **원리로 답하기**: "어떻게"보다 "왜"를 먼저 설명
2. **트레이드오프 언급**: 모든 기술에는 장단점이 있음을 인지
3. **실무 경험 연결**: "프로젝트에서 N+1 문제를 fetch join으로 해결했습니다"
4. **모른다면 솔직하게**: 아는 범위를 말하고 "추가로 학습하겠습니다"

이 50개 질문을 외우는 것이 목표가 아닙니다. 각 질문 뒤에 있는 **설계 의도**를 이해하는 것이 진짜 목표입니다.

---

## 다른 파트 보기

- [Part 1: DI/IoC (Q1~Q10)](/interview/spring-interview-part1/)
- [Part 2: AOP (Q11~Q18)](/interview/spring-interview-part2/)
- [Part 3: Transaction (Q19~Q27)](/interview/spring-interview-part3/)
- [Part 4: JPA (Q28~Q38)](/interview/spring-interview-part4/)
- [Part 5: Security (Q39~Q45)](/interview/spring-interview-part5/)
- [Part 6: WebFlux (Q46~Q50)](/interview/spring-interview-part6/)
