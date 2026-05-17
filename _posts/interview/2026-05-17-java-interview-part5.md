---
title: "Java 면접 — 예외처리 / Generics / 기타 (Q41~Q50)"
categories: INTERVIEW
tags: [Java, 면접, Exception, Generics, 직렬화, Record]
toc: true
toc_sticky: true
toc_label: 목차
---

## 5. 예외 처리 / Generics / 기타 (Q41 ~ Q50)

### Q41. Checked Exception과 Unchecked Exception의 차이는?

**모범 답변**

| 구분 | Checked Exception | Unchecked Exception |
|---|---|---|
| 상속 | Exception | RuntimeException |
| 컴파일 강제 | 예 (throws 선언 또는 catch 필수) | 아니오 |
| 용도 | 회복 가능한 예외 | 프로그래밍 오류 |
| 예시 | IOException, SQLException | NPE, IllegalArgumentException |

**논란:** Checked Exception이 복잡한 예외 처리를 강제하고 API 유연성을 낮춘다는 비판이 있습니다. Spring Framework 등 최신 라이브러리는 주로 Unchecked Exception을 사용합니다.

> **비유:** Checked Exception은 "이 길은 공사 중일 수 있습니다. 우회로를 준비하세요"라는 표지판. Unchecked는 예기치 않은 구덩이입니다.

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** 예외를 catch해서 로깅만 하고 다시 throw하는 패턴의 문제점은?

스택 트레이스가 중복으로 기록됩니다. 예외를 감싸서 던질 때 원인(cause)을 포함해야 합니다. `throw new ServiceException("message", e)` — e를 누락하면 원인 추적 불가.

</details>

---

### Q42. 제네릭의 상한/하한 경계 와일드카드란?

**모범 답변**

```java
// 상한 경계 <? extends T> — T 또는 T의 하위 타입 읽기 전용 (PECS: Producer)
public double sumList(List<? extends Number> list) {
    return list.stream().mapToDouble(Number::doubleValue).sum();
}

// 하한 경계 <? super T> — T 또는 T의 상위 타입 쓰기 가능 (PECS: Consumer)
public void addNumbers(List<? super Integer> list) {
    list.add(42);
}
```

**PECS 원칙:** Producer Extends, Consumer Super. 데이터를 읽으면(생산) `extends`, 쓰면(소비) `super`.

> **비유:** 상한 경계는 "포도주 종류 중 무엇이든 가져와"(특정 카테고리), 하한 경계는 "이 포도주를 담을 수 있는 컵이면 무엇이든"(담을 수 있는 것)

---

### Q43. 타입 소거(Type Erasure)란?

**모범 답변**

Java 제네릭은 컴파일 타임에만 존재하고, 바이트코드에서는 제거(소거)됩니다.

```java
List<String> strings = new ArrayList<>();
List<Integer> integers = new ArrayList<>();
// 런타임에는 둘 다 List — instanceof 불가
```

결과:
1. 런타임에 제네릭 타입 정보 없음
2. `List<String>` instanceof 체크 불가
3. 제네릭 배열 생성 불가 (`new T[]` 불가)
4. 하위 호환성 유지 (Java 5 이전 코드와 공존)

<details>
<summary>면접 포인트 펼치기</summary>

**꼬리질문:** 런타임에 제네릭 타입 정보를 얻으려면?

`TypeToken` (Guava) 또는 `ParameterizedTypeReference` (Spring) 같은 슈퍼 타입 토큰 패턴을 사용합니다. 익명 클래스를 통해 컴파일러가 타입 정보를 클래스 메타데이터에 남깁니다.

</details>

---

### Q44. String, StringBuilder, StringBuffer의 차이는?

**모범 답변**

| 클래스 | 불변 여부 | 스레드 안전 | 성능 |
|---|---|---|---|
| String | 불변 | 안전 | 반복 연결 시 낮음 |
| StringBuilder | 가변 | 안전하지 않음 | 단일 스레드 최고 |
| StringBuffer | 가변 | synchronized | 멀티 스레드 |

Java 컴파일러는 `"a" + "b" + "c"` 같은 리터럴 연결을 `StringBuilder`로 최적화합니다. 그러나 루프 내 String 연결은 최적화되지 않아 `StringBuilder`를 명시적으로 사용해야 합니다.

---

### Q45. equals와 hashCode 계약은?

**모범 답변**

1. `equals`가 true이면 `hashCode`도 같아야 함
2. `hashCode`가 같아도 `equals`는 false 가능 (충돌)
3. `equals`가 false이면 `hashCode`는 다를 수도, 같을 수도 있음

```java
@Override
public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof Order)) return false;
    Order order = (Order) o;
    return Objects.equals(id, order.id);
}

@Override
public int hashCode() {
    return Objects.hash(id);
}
```

**실무 주의:** JPA 엔티티의 equals/hashCode 구현 시 id 기반으로 하되, 신규 저장 전 id가 null인 경우를 처리해야 합니다.

---

### Q46 ~ Q50. Java 심화 / 최신 기능

**Q46. Java 17 주요 기능은?**

- **Sealed Class**: 상속 가능한 클래스를 명시적으로 제한 (`sealed`, `permits`)
- **Record**: 불변 데이터 클래스 간결하게 선언 (`record Point(int x, int y) {}`)
- **Pattern Matching for instanceof**: `if (obj instanceof String s)` — 캐스팅 불필요
- **Text Block**: 멀티라인 문자열 `""" ... """`

**Q47. Record의 사용 시나리오와 한계는?**

사용: DTO, Value Object, 설정 데이터. 한계: 불변 클래스라 JPA 엔티티로 사용 불가(JPA는 기본 생성자와 setter 필요). Lombok `@Data`와 비슷하지만 더 간결합니다.

**Q48. Java Virtual Thread(Project Loom)란?**

Java 21에서 정식 도입. JVM이 관리하는 경량 스레드. 수백만 개 생성 가능. 블로킹 I/O에서 OS 스레드를 점유하지 않음. Spring Boot 3.2+에서 `spring.threads.virtual.enabled=true`로 활성화.

**Q49. instanceof 패턴 매칭과 switch 패턴 매칭은?**

```java
// instanceof 패턴 매칭 (Java 16+)
if (shape instanceof Circle c) {
    return Math.PI * c.radius() * c.radius();
}

// switch 패턴 매칭 (Java 21+)
double area = switch (shape) {
    case Circle c -> Math.PI * c.radius() * c.radius();
    case Rectangle r -> r.width() * r.height();
    default -> throw new IllegalArgumentException();
};
```

**Q50. var (지역 변수 타입 추론)의 사용 가이드라인은?**

Java 10+에서 사용 가능. 사용 권장: 긴 제네릭 타입 (`var entries = map.entrySet()`), try-with-resources. 사용 비권장: 타입이 명확하지 않은 경우, `var result = getValue()` (반환 타입이 뭔지 모름). 람다 파라미터에 사용 불가.

---

## 마무리 — Java 면접 전략

Java 면접에서 차별화되는 방법:

1. **버전별 변화를 설명**: "Java 7까지는... Java 8에서... Java 21에서는..." 형식으로 역사적 맥락 제시
2. **내부 구현까지 설명**: "HashMap은 배열 + 연결 리스트 + 트리이고..."
3. **트레이드오프 언급**: 모든 선택에는 이유가 있음
4. **실제 프로젝트 경험 연결**: N+1, 메모리 누수, 데드락 등 실제 겪은 문제를 구체적으로

Java는 언어 자체보다 **JVM과 생태계를 이해하는가**가 시니어와 주니어를 가르는 기준입니다.

---

## 다른 파트 보기

- [Part 1: JVM 메모리 구조 (Q1~Q10)](/interview/java-interview-part1/)
- [Part 2: 동시성 (Q11~Q22)](/interview/java-interview-part2/)
- [Part 3: Collection 내부 구조 (Q23~Q33)](/interview/java-interview-part3/)
- [Part 4: Stream / Functional (Q34~Q40)](/interview/java-interview-part4/)
- [Part 5: 예외처리 / Generics (Q41~Q50)](/interview/java-interview-part5/)
