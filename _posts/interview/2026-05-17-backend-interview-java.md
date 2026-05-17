---
title: "Java 면접 질문 50선 — JVM부터 동시성까지 완전 정복"
categories: INTERVIEW
tags: [Java, 면접, JVM, GC, 동시성, Collection, Stream, Memory]
toc: true
toc_sticky: true
toc_label: 목차
---

Java 면접에서 "HashMap의 시간복잡도가 뭔가요?" 같은 표면적 질문은 웜업일 뿐입니다. 진짜 합격을 가르는 건 "왜 O(1)이 아닐 수 있는가?", "해시 충돌이 심해지면 내부에서 어떻게 변하는가?" 같은 꼬리질문입니다. 이 글은 Java 면접 핵심 50문제를 파트별로 나누어 깊이 있게 다룹니다.

---

## 파트별 바로가기

### [Part 1: JVM 메모리 구조 (Q1 ~ Q10)](/interview/java-interview-part1/)
- Heap/Stack/Metaspace 구조, GC 알고리즘
- 메모리 누수 패턴, OOM 유형별 대응

### [Part 2: 동시성 (Q11 ~ Q22)](/interview/java-interview-part2/)
- synchronized vs ReentrantLock, volatile
- ConcurrentHashMap, ThreadPool, CompletableFuture

### [Part 3: Collection 내부 구조 (Q23 ~ Q33)](/interview/java-interview-part3/)
- HashMap 해시 충돌, Red-Black Tree 전환
- ArrayList vs LinkedList, TreeMap, PriorityQueue

### [Part 4: Stream / Functional (Q34 ~ Q40)](/interview/java-interview-part4/)
- Stream 내부 파이프라인, 병렬 스트림 주의점
- Lambda 캡처링, Optional 안티패턴

### [Part 5: 예외처리 / Generics / 기타 (Q41 ~ Q50)](/interview/java-interview-part5/)
- Checked vs Unchecked, try-with-resources
- Type Erasure, 와일드카드, Record, Sealed Class

---

## 면접 전략 팁

1. **원리부터**: "쓰는 법"이 아니라 "왜 이렇게 동작하는가"를 설명
2. **트레이드오프**: 모든 선택에는 대가가 있다는 관점
3. **실무 연결**: "실제 프로젝트에서 이런 문제를 만났고 이렇게 해결했다"
4. **숫자로 말하기**: "성능이 좋다"가 아니라 "처리량이 3배 증가했다"
