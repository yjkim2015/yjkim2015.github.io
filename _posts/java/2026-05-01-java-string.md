---
title: "Java String"
categories:
- JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

Java에서 `String`은 가장 많이 사용되는 클래스이면서, 동시에 가장 많은 오해가 있는 클래스입니다. 불변성(Immutability), String Pool, 성능 최적화, 그리고 Java 11~17에서 추가된 메서드까지 완전히 정리합니다.

---

## 1. String이 불변(Immutable)인 이유

### 불변이란?

```java
String s = "Hello";
s.toUpperCase();         // 새로운 String 반환
System.out.println(s);  // "Hello" — s 자체는 변하지 않음

s = s.toUpperCase();    // 참조를 새 객체로 교체
System.out.println(s);  // "HELLO"
```

```
메모리 구조:
s ──────────────────► "Hello"   (변경 불가)
s (재할당 후) ───────► "HELLO"  (새 객체)
                       "Hello"  (GC 대상)
```

### 불변으로 설계한 이유

**1. String Pool 공유 가능**
```java
String a = "hello";
String b = "hello";
// 같은 객체를 공유해도 안전 — 변경 불가이므로
System.out.println(a == b);  // true (같은 Pool 객체)
```

**2. 스레드 안전 (Thread-Safe)**
```java
// 불변 객체는 동기화 없이 여러 스레드에서 공유 가능
String shared = "공유 문자열";
// 어떤 스레드도 shared를 변경할 수 없음
```

**3. 해시코드 캐싱**
```java
// String의 hashCode는 한 번만 계산하고 캐싱
// HashMap, HashSet의 키로 안전하게 사용 가능
private int hash; // 기본값 0, 처음 hashCode() 호출 시 계산
```

**4. 보안**
```java
// 파일 경로, URL, DB 연결 문자열이 중간에 변경되면 보안 위협
// 불변이므로 한 번 검증하면 안전
void openFile(String path) {
    validate(path);         // 검증
    // path가 변경될 수 없으므로 안전하게 사용
    Files.open(path);
}
```

### 내부 구현

```java
// Java 9 이후 String 내부 (compact strings)
public final class String {
    private final byte[] value;   // UTF-16 또는 Latin-1
    private final byte coder;     // LATIN1=0, UTF16=1
    private int hash;             // 캐싱된 hashCode
}
```

---

## 2. String Pool (intern) 동작 원리

### String Pool이란?

JVM Heap 내의 특별한 영역(Java 7+: Heap, 이전: PermGen)으로, 문자열 리터럴을 캐싱합니다.

```
JVM 메모리:
┌──────────────────────────────────────────┐
│                  Heap                    │
│  ┌─────────────────────────────────┐     │
│  │         String Pool             │     │
│  │  "hello" ◄──── 리터럴 자동 등록 │     │
│  │  "world"                        │     │
│  └─────────────────────────────────┘     │
│                                          │
│  new String("hello") ← Pool 밖 새 객체  │
└──────────────────────────────────────────┘
```

### 리터럴 vs new String()

```java
String a = "hello";              // Pool에서 가져옴
String b = "hello";              // Pool의 같은 객체
String c = new String("hello");  // Pool 밖 새 객체
String d = new String("hello");  // 또 다른 새 객체

System.out.println(a == b);  // true  (같은 Pool 객체)
System.out.println(a == c);  // false (다른 객체)
System.out.println(c == d);  // false (다른 객체)

System.out.println(a.equals(c));  // true (내용 동일)
```

### intern() 메서드

```java
String c = new String("hello");
String e = c.intern();  // Pool에서 "hello" 반환 (없으면 등록 후 반환)

System.out.println(a == e);  // true (Pool의 같은 객체)
```

### 컴파일 타임 상수 풀링

```java
// 컴파일러가 자동으로 결합
String a = "hello";
String b = "hel" + "lo";  // 컴파일 타임에 "hello"로 결합
System.out.println(a == b);  // true

// 런타임 결합 — Pool 미적용
String prefix = "hel";
String c = prefix + "lo";  // 런타임 → new String
System.out.println(a == c);  // false

// final 변수는 컴파일 타임 상수
final String prefix2 = "hel";
String d = prefix2 + "lo";  // 컴파일 타임 → Pool 적용
System.out.println(a == d);  // true
```

---

## 3. String vs StringBuilder vs StringBuffer 성능 비교

### 특성 비교

| 항목 | String | StringBuilder | StringBuffer |
|------|--------|---------------|--------------|
| 불변성 | 불변 | 가변 | 가변 |
| 스레드 안전 | O (불변이므로) | X | O (synchronized) |
| 성능 | 연결 시 느림 | 빠름 | StringBuilder보다 느림 |
| 도입 버전 | Java 1.0 | Java 5 | Java 1.0 |

### 성능 차이 원리

```java
// String 연결 — 매번 새 객체 생성
String result = "";
for (int i = 0; i < 10000; i++) {
    result += i;  // 매 반복마다 새 String 생성 → O(n²)
}

// StringBuilder — 내부 버퍼 확장
StringBuilder sb = new StringBuilder();
for (int i = 0; i < 10000; i++) {
    sb.append(i);  // 버퍼에 추가 → O(n)
}
String result = sb.toString();
```

```
String 연결 (n번):
"" → "0" → "01" → "012" → ...
매번 새 배열 생성 + 복사 → O(1+2+3+...+n) = O(n²)

StringBuilder (n번):
[버퍼: ...........]
→ append → append → append
→ 필요 시 버퍼 2배 확장
→ O(n) amortized
```

### 컴파일러 최적화

```java
// Java 컴파일러는 + 연산을 자동으로 StringBuilder로 변환
String a = "Hello" + " " + "World";
// 컴파일 후:
String a = new StringBuilder().append("Hello").append(" ").append("World").toString();

// 단, 반복문 내에서는 매번 새 StringBuilder 생성
for (int i = 0; i < n; i++) {
    result += i;
    // 컴파일 후: result = new StringBuilder(result).append(i).toString();
    // 여전히 O(n²)!
}
```

### Java 9+ StringConcatFactory

```java
// Java 9부터 invokedynamic 기반 최적화
// 단순 연결은 StringBuilder보다 빠를 수 있음
// 하지만 반복문 내 연결은 여전히 StringBuilder 권장
```

### 사용 가이드라인

```java
// 1. 단순 리터럴 조합 → String 리터럴
String name = "Hello, " + userName + "!";

// 2. 반복문 내 연결 → StringBuilder
StringBuilder sb = new StringBuilder(capacity);
for (String s : list) {
    sb.append(s).append(", ");
}

// 3. 멀티스레드 공유 버퍼 → StringBuffer (드문 경우)
StringBuffer sharedBuffer = new StringBuffer();
```

---

## 4. 문자열 연결 성능 상세

### 벤치마크 비교 (JMH 기준)

```
연산 횟수: 100,000회
┌─────────────────────┬────────────────┐
│  방법               │  시간 (상대)   │
├─────────────────────┼────────────────┤
│ String + (반복)     │ 100x (기준)    │
│ concat() (반복)     │  80x           │
│ StringBuilder       │   1x (최적)    │
│ StringBuffer        │   1.2x         │
│ String.join()       │   1.5x (내부 SB│
└─────────────────────┴────────────────┘
```

### String.join() / Collectors.joining()

```java
// 구분자로 연결
String result = String.join(", ", "A", "B", "C");  // "A, B, C"

List<String> list = List.of("Apple", "Banana", "Cherry");
String joined = String.join(" | ", list);  // "Apple | Banana | Cherry"

// Stream에서
String csv = list.stream()
    .collect(Collectors.joining(", ", "[", "]"));
// "[Apple, Banana, Cherry]"
```

---

## 5. String 메서드 총정리

### 기본 메서드

```java
String s = "Hello, World!";

// 길이 / 비어있는지
s.length()           // 13
s.isEmpty()          // false
s.isBlank()          // false (Java 11+, 공백만 있어도 true)

// 검색
s.charAt(0)          // 'H'
s.indexOf('o')       // 4 (첫 번째)
s.lastIndexOf('o')   // 8 (마지막)
s.contains("World")  // true
s.startsWith("Hello")// true
s.endsWith("!")      // true

// 추출
s.substring(7)       // "World!"
s.substring(7, 12)   // "World"

// 변환
s.toLowerCase()      // "hello, world!"
s.toUpperCase()      // "HELLO, WORLD!"
s.trim()             // 앞뒤 ASCII 공백 제거
s.strip()            // 앞뒤 유니코드 공백 제거 (Java 11+)
s.replace('l', 'r')  // "Herro, Worrd!"
s.replace("World", "Java")  // "Hello, Java!"

// 분리 / 결합
s.split(", ")        // ["Hello", "World!"]
String.join("-", "A", "B")  // "A-B"

// 변환
s.toCharArray()      // char[]
s.getBytes()         // byte[] (기본 charset)
String.valueOf(42)   // "42"
```

### Java 11 추가 메서드

```java
// isBlank() — 공백만 있으면 true
"   ".isBlank()   // true
"  a".isBlank()   // false

// strip() — 유니코드 공백 처리 (trim()보다 권장)
"\u2000Hello\u2000".strip()       // "Hello"
"\u2000Hello\u2000".trim()        // "\u2000Hello\u2000" (제거 안 됨)
"  Hello  ".stripLeading()        // "Hello  "
"  Hello  ".stripTrailing()       // "  Hello"

// lines() — 줄 단위 Stream
"line1\nline2\nline3".lines()
    .forEach(System.out::println);
// line1
// line2
// line3

// repeat() — 반복
"ab".repeat(3)  // "ababab"
```

### Java 12 추가 메서드

```java
// indent() — 들여쓰기 추가/제거
String text = "Hello\nWorld";
text.indent(4);
// "    Hello\n    World\n"

// transform() — 변환 함수 적용
String result = "  hello  "
    .transform(String::strip)
    .transform(String::toUpperCase);
// "HELLO"
```

### Java 15 추가 메서드

```java
// formatted() — String.format()의 인스턴스 버전
String msg = "Hello, %s! You are %d years old."
    .formatted("Alice", 30);
// "Hello, Alice! You are 30 years old."
```

### Java 16 추가 메서드

```java
// stripIndent() — 텍스트 블록 들여쓰기 제거
String html = "  <html>\n    <body>\n  </html>";
html.stripIndent();

// translateEscapes() — 이스케이프 시퀀스 해석
"Hello\\nWorld".translateEscapes();  // "Hello\nWorld"
```

---

## 6. 정규표현식과 String

### 기본 활용

```java
String email = "user@example.com";

// matches() — 전체 문자열이 패턴과 일치?
email.matches("[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}");  // true

// replaceAll() / replaceFirst()
String text = "Hello 123 World 456";
text.replaceAll("\\d+", "#");   // "Hello # World #"
text.replaceFirst("\\d+", "#"); // "Hello # World 456"

// split() 정규표현식
"a1b2c3".split("\\d");  // ["a", "b", "c"]
```

### Pattern / Matcher (고성능)

```java
import java.util.regex.*;

// 패턴 미리 컴파일 (반복 사용 시 필수)
Pattern pattern = Pattern.compile("\\d+");
Matcher matcher = pattern.matcher("abc123def456");

// 찾기
while (matcher.find()) {
    System.out.println(matcher.group());  // 123, 456
    System.out.println(matcher.start());  // 시작 인덱스
}

// 그룹 캡처
Pattern datePattern = Pattern.compile("(\\d{4})-(\\d{2})-(\\d{2})");
Matcher m = datePattern.matcher("2026-05-01");
if (m.matches()) {
    String year  = m.group(1);  // "2026"
    String month = m.group(2);  // "05"
    String day   = m.group(3);  // "01"
}
```

### 성능 주의사항

```java
// 나쁜 예: 반복 호출 시마다 Pattern 컴파일
for (String s : list) {
    if (s.matches("\\d+")) { ... }  // 매번 Pattern.compile() 호출!
}

// 좋은 예: 미리 컴파일
private static final Pattern DIGIT_PATTERN = Pattern.compile("\\d+");

for (String s : list) {
    if (DIGIT_PATTERN.matcher(s).matches()) { ... }  // 재사용
}
```

---

## 7. 텍스트 블록 (Text Block, Java 13 Preview → Java 15 정식)

### 기본 문법

```java
// 기존 방식 — 가독성 나쁨
String json = "{\n" +
              "  \"name\": \"Alice\",\n" +
              "  \"age\": 30\n" +
              "}";

// 텍스트 블록 — 훨씬 읽기 쉬움
String json = """
        {
          "name": "Alice",
          "age": 30
        }
        """;
```

### 들여쓰기 규칙

```java
// 닫는 """ 위치가 들여쓰기 기준점
String text = """
        Hello
        World
        """;
// → "Hello\nWorld\n"  (공통 들여쓰기 8칸 제거)

String text2 = """
        Hello
        World
""";  // 닫는 """가 컬럼 0에 위치
// → "        Hello\n        World\n"  (들여쓰기 유지)
```

### 실용 예제

```java
// SQL
String sql = """
        SELECT u.id, u.name, o.total
        FROM users u
        JOIN orders o ON u.id = o.user_id
        WHERE u.active = true
          AND o.total > :minAmount
        ORDER BY o.total DESC
        """;

// HTML
String html = """
        <html>
            <body>
                <p>Hello, %s!</p>
            </body>
        </html>
        """.formatted(name);

// JSON
String json = """
        {
            "status": "ok",
            "message": "%s"
        }
        """.formatted(message);
```

### 이스케이프 처리

```java
// \n 줄 바꿈 억제 (긴 줄 가독성 유지)
String oneLine = """
        This is a very long line \
        that continues here.
        """;
// → "This is a very long line that continues here.\n"

// \s — 공백 유지 (후행 공백 보존)
String padded = """
        one  \s
        two  \s
        """;
```

---

## 8. String 관련 주요 패턴

### 문자열 → 기본형 변환

```java
int    i = Integer.parseInt("42");
double d = Double.parseDouble("3.14");
long   l = Long.parseLong("1234567890");
boolean b = Boolean.parseBoolean("true");

// 안전한 파싱
try {
    int val = Integer.parseInt(input);
} catch (NumberFormatException e) {
    // 처리
}
```

### 기본형 → 문자열

```java
String s1 = String.valueOf(42);      // "42"
String s2 = Integer.toString(42);    // "42"
String s3 = "" + 42;                 // "42" (권장하지 않음)
```

### 문자열 비교 함정

```java
// == 절대 사용 금지 (Pool 외부 객체)
String a = new String("hello");
String b = new String("hello");
a == b           // false
a.equals(b)      // true ← 항상 이것을 사용

// 대소문자 무시
a.equalsIgnoreCase("HELLO");  // true

// null 안전 비교 (NPE 방지)
"hello".equals(userInput);    // 리터럴을 앞에
Objects.equals(a, b);         // 둘 다 null-safe
```

---

## 9. 전체 요약

```
String 핵심 정리:
┌────────────────────────────────────────────────────────┐
│  불변성: 모든 메서드는 새 String 반환                  │
│  Pool:   리터럴은 자동으로 Pool에 등록, == 비교 주의   │
│  연결:   반복문에서 + 금지 → StringBuilder 사용        │
│  비교:   항상 equals(), == 절대 금지                   │
│  Java11: strip(), isBlank(), lines(), repeat() 활용    │
│  Java15: 텍스트 블록 """ 적극 활용                    │
└────────────────────────────────────────────────────────┘

선택 가이드:
단순 조합     → String 리터럴 + 텍스트 블록
반복 연결     → StringBuilder
스레드 공유   → StringBuffer (드문 경우)
패턴 검색     → Pattern.compile() 미리 컴파일
```
