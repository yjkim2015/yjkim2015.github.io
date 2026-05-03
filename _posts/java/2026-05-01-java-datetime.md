---
title: "Java 날짜와 시간 API (java.time)"
categories:
- JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

Java 8에서 도입된 `java.time` 패키지는 기존 `Date`와 `Calendar`의 고질적인 문제를 해결하고, 불변(Immutable) 설계와 직관적인 API를 제공합니다. 현대 Java 개발에서 날짜·시간 처리의 표준입니다.

---

## 1. Date, Calendar의 문제점

### java.util.Date의 문제

`Date` 클래스는 Java 1.0 시절에 만들어진 낡은 유물입니다. 연도를 1900 기준으로, 월을 0 기준으로 설계하는 바람에 직관과 완전히 반대로 동작합니다. 비유하자면, 은행 창구에 가서 "2026년 5월 1일 오세요"라고 말했는데 "126년 4번째 달 1일"로 해석하는 것과 같습니다.

```java
// Java 1.0 시절 Date — 거의 모든 메서드가 deprecated
Date date = new Date(2026, 5, 1);  // deprecated!
// 연도는 1900 기준, 월은 0 기준 → 직관에 어긋남
// 2026년 5월 1일을 만들려면:
Date date = new Date(126, 4, 1);  // 126=2026-1900, 4=5월-1

// 문제점
date.getYear()   // 126 (1900 기준)
date.getMonth()  // 4 (0 기준, 5월이 4)
```

### java.util.Calendar의 문제

`Calendar`는 `Date`의 문제를 개선하려 했지만 절반만 성공했습니다. 가장 치명적인 문제는 **가변(Mutable)** 설계입니다. 캘린더 객체를 여러 스레드에서 공유하면 한 스레드가 날짜를 바꾸는 순간 다른 스레드가 엉뚱한 날짜를 읽게 됩니다.

```java
Calendar cal = Calendar.getInstance();
cal.set(2026, Calendar.MAY, 1);  // 월 상수 제공하지만 여전히 불편

// 1. 가변(Mutable) — 스레드 안전 X
cal.set(Calendar.YEAR, 2027);  // 기존 객체 변경

// 2. 월이 0부터 시작 (여전히)
cal.get(Calendar.MONTH)  // 4 (5월)

// 3. 요일이 1부터 (일요일=1, 월요일=2, ...)
cal.get(Calendar.DAY_OF_WEEK)  // 헷갈림

// 4. 타입 안전 없음
cal.set(Calendar.MONTH, 99);  // 컴파일 에러 없음!

// 5. 시간대 처리 복잡
```

### 문제점 요약

```mermaid
graph TD
    A["Date / Calendar 7대 문제점"] --> B["1️⃣ 가변(Mutable) → 스레드 안전 X"]
    A --> C["2️⃣ 월이 0 기준 (1월=0) → 직관성 없음"]
    A --> D["3️⃣ 연도가 1900 기준 (Date)"]
    A --> E["4️⃣ 타입 안전 없음 (정수 상수)"]
    A --> F["5️⃣ 시간대 처리 어려움"]
    A --> G["6️⃣ 날짜 연산 불편"]
    A --> H["7️⃣ SimpleDateFormat 스레드 안전 X"]
```

**실무 실수:** `SimpleDateFormat`을 `static` 필드로 공유하면 멀티스레드 환경에서 날짜가 뒤섞이는 버그가 발생합니다. 재현도 어렵고 원인 파악도 늦어지는 대표적인 실무 함정입니다.

---

## 2. java.time 패키지 전체 구조

`java.time`의 설계 철학은 간단합니다. **"시간대 정보가 필요한가?"** 를 기준으로 클래스를 선택합니다. 시간대가 없으면 `Local*`, 시간대까지 포함하면 `Zoned*`, 절대 시각(UTC 기준 나노초)이 필요하면 `Instant`를 씁니다.

```mermaid
graph TD
    A["java.time 클래스 선택"] --> B["시간대 불필요"]
    A --> C["시간대 필요"]
    A --> D["기간/경과 측정"]
    B --> E["LocalDate: 날짜만 (2026-05-01)"]
    B --> F["LocalTime: 시간만 (14:30:00)"]
    B --> G["LocalDateTime: 날짜+시간"]
    C --> H["ZonedDateTime: 시간대 이름 포함"]
    C --> I["OffsetDateTime: UTC 오프셋 포함"]
    C --> J["Instant: 머신 타임(epoch 나노초)"]
    D --> K["Period: 날짜 기반 (년/월/일)"]
    D --> L["Duration: 시간 기반 (초/나노초)"]
```

---

## 3. LocalDate, LocalTime, LocalDateTime

> **비유:** `LocalDate`는 벽에 걸린 달력입니다. "5월 1일"이라고 적혀 있을 뿐, 서울인지 뉴욕인지 신경 쓰지 않습니다. `LocalTime`은 벽시계이고, `LocalDateTime`은 달력과 벽시계를 나란히 놓은 것입니다. 시간대(시차) 정보가 없어서 "어느 나라 기준인지"는 모릅니다.

`LocalDate`는 시간대 개념이 없는 날짜만의 표현입니다. 내부적으로 연·월·일을 `int` 필드 3개로 저장하며, 모든 메서드는 새 객체를 반환합니다. 이 덕분에 다수의 스레드가 동일한 `LocalDate` 인스턴스를 공유해도 절대 안전합니다.

### LocalDate — 날짜만

```java
// 생성
LocalDate today = LocalDate.now();                    // 2026-05-01
LocalDate date  = LocalDate.of(2026, 5, 1);          // 2026-05-01
LocalDate date2 = LocalDate.of(2026, Month.MAY, 1);  // Month 상수 사용
LocalDate date3 = LocalDate.parse("2026-05-01");      // 파싱

// 정보 조회
today.getYear()        // 2026
today.getMonthValue()  // 5 (1 기준!)
today.getMonth()       // MAY (Month 열거형)
today.getDayOfMonth()  // 1
today.getDayOfWeek()   // FRIDAY (DayOfWeek 열거형)
today.getDayOfYear()   // 121
today.lengthOfMonth()  // 31 (5월)
today.isLeapYear()     // false

// 불변 연산 — 새 객체 반환
LocalDate tomorrow    = today.plusDays(1);     // 2026-05-02
LocalDate nextMonth   = today.plusMonths(1);   // 2026-06-01
LocalDate nextYear    = today.plusYears(1);    // 2027-05-01
LocalDate yesterday   = today.minusDays(1);    // 2026-04-30
LocalDate lastMonday  = today.with(DayOfWeek.MONDAY);  // 이번 주 월요일

// 비교
LocalDate d1 = LocalDate.of(2026, 1, 1);
LocalDate d2 = LocalDate.of(2026, 12, 31);
d1.isBefore(d2)   // true
d1.isAfter(d2)    // false
d1.isEqual(d2)    // false
d1.compareTo(d2)  // 음수
```

결과적으로 `today.plusDays(1)`은 `today`를 전혀 바꾸지 않고 새 `LocalDate`를 돌려줍니다. `today = today.plusDays(1);`처럼 **재할당**해야 변경된 날짜를 사용할 수 있습니다.

### LocalTime — 시간만

```java
// 생성
LocalTime now      = LocalTime.now();
LocalTime time     = LocalTime.of(14, 30);           // 14:30:00
LocalTime time2    = LocalTime.of(14, 30, 45);       // 14:30:45
LocalTime time3    = LocalTime.of(14, 30, 45, 123_000_000);  // 나노초 포함
LocalTime time4    = LocalTime.parse("14:30:45");

// 정보 조회
time.getHour()    // 14
time.getMinute()  // 30
time.getSecond()  // 45
time.getNano()    // 나노초

// 불변 연산
time.plusHours(2)     // 16:30:45
time.minusMinutes(30) // 14:00:45
time.plusSeconds(15)  // 14:31:00

// 상수
LocalTime.MIDNIGHT  // 00:00
LocalTime.NOON      // 12:00
LocalTime.MAX       // 23:59:59.999999999
LocalTime.MIN       // 00:00
```

### LocalDateTime — 날짜 + 시간

```java
// 생성
LocalDateTime now  = LocalDateTime.now();
LocalDateTime dt   = LocalDateTime.of(2026, 5, 1, 14, 30, 45);
LocalDateTime dt2  = LocalDateTime.of(LocalDate.now(), LocalTime.now());
LocalDateTime dt3  = LocalDateTime.parse("2026-05-01T14:30:45");

// 날짜/시간 분리
LocalDate date = dt.toLocalDate();
LocalTime time = dt.toLocalTime();

// 불변 연산
dt.plusDays(7).minusHours(2).withMinute(0)

// 비교
dt.isBefore(LocalDateTime.now())
dt.isAfter(LocalDateTime.now())
```

---

## 4. ZonedDateTime, OffsetDateTime, Instant

> **비유:** `Instant`는 세계 표준시(그리니치 천문대)에 걸린 원자시계입니다. 전 세계 어디서 보더라도 같은 순간을 가리킵니다. `ZonedDateTime`은 그 원자시계 옆에 "서울 +9시간", "뉴욕 -4시간" 같은 현지 시각 변환표를 붙여놓은 것입니다. `OffsetDateTime`은 변환표에서 도시 이름을 떼고 "+09:00"이라는 숫자만 남긴 것입니다.

### 시간대 처리 동작 원리

`Instant`는 1970-01-01T00:00:00Z(UTC)를 기준으로 경과한 초와 나노초를 저장합니다. 전 세계 어디서도 동일한 절대 시각을 나타냅니다. `ZonedDateTime`은 `Instant` + 지역 시간대(`ZoneId`)의 조합으로, 서울 14:30과 뉴욕 01:30이 사실 같은 순간임을 표현합니다.

```mermaid
sequenceDiagram
    participant I as Instant(UTC)
    participant S as ZonedDateTime(Seoul)
    participant N as ZonedDateTime(NewYork)
    Note over I: 2026-05-01T05:30:00Z
    I->>S: atZone(Asia/Seoul) → +09:00
    I->>N: atZone(America/New_York) → -04:00
    Note over S: 2026-05-01T14:30:00+09:00
    Note over N: 2026-05-01T01:30:00-04:00
```

### Instant — 머신 시간 (Unix epoch 기준)

```java
// 1970-01-01T00:00:00Z 기준 나노초
Instant now   = Instant.now();
Instant epoch = Instant.EPOCH;         // 1970-01-01T00:00:00Z
Instant future = Instant.now().plusSeconds(3600);

now.getEpochSecond()  // 초 (long)
now.getNano()         // 나노초 부분

// 타임스탬프 변환
long millis = now.toEpochMilli();
Instant fromMillis = Instant.ofEpochMilli(millis);

// Date 변환 (레거시 연동)
Date legacyDate = Date.from(now);
Instant fromDate = legacyDate.toInstant();
```

### ZoneId — 시간대

```java
// 시간대 목록
ZoneId.getAvailableZoneIds()  // 600개 이상

ZoneId seoul   = ZoneId.of("Asia/Seoul");
ZoneId utc     = ZoneId.of("UTC");
ZoneId tokyo   = ZoneId.of("Asia/Tokyo");
ZoneId ny      = ZoneId.of("America/New_York");
ZoneId system  = ZoneId.systemDefault();
```

### ZonedDateTime — 시간대 포함 날짜시간

```java
ZonedDateTime seoulTime = ZonedDateTime.now(ZoneId.of("Asia/Seoul"));
// 2026-05-01T14:30:45+09:00[Asia/Seoul]

ZonedDateTime utcTime = ZonedDateTime.now(ZoneId.of("UTC"));

// 시간대 변환
ZonedDateTime nyTime = seoulTime.withZoneSameInstant(ZoneId.of("America/New_York"));
// 같은 순간, 다른 시간대 표현

// 생성
ZonedDateTime zdt = ZonedDateTime.of(
    LocalDateTime.of(2026, 5, 1, 14, 30),
    ZoneId.of("Asia/Seoul")
);
```

### OffsetDateTime — UTC 오프셋 포함

```java
// ZoneId(시간대 이름) 없이 오프셋만 포함
OffsetDateTime odt = OffsetDateTime.now(ZoneOffset.of("+09:00"));
// 2026-05-01T14:30:45+09:00

// DB 저장 시 권장 (시간대 정치적 변경에 영향 없음)
OffsetDateTime forDb = ZonedDateTime.now().toOffsetDateTime();
```

### 시간대 처리 Best Practice

```java
// 1. 내부 처리는 Instant 또는 UTC
Instant eventTime = Instant.now();

// 2. 표시는 ZonedDateTime으로 변환
ZonedDateTime display = eventTime.atZone(ZoneId.of("Asia/Seoul"));

// 3. DB 저장은 UTC Instant 또는 OffsetDateTime
// TIMESTAMP WITH TIME ZONE 컬럼 권장

// 4. 사용자 입력은 명시적 시간대 포함
ZonedDateTime userInput = ZonedDateTime.parse("2026-05-01T14:30:00+09:00");
Instant stored = userInput.toInstant();  // UTC로 변환 후 저장
```

**극한 시나리오:** 글로벌 서비스에서 한국 사용자가 설정한 "매일 오전 9시 알림"을 서버가 `LocalDateTime`으로 저장했다가 서버를 AWS us-east-1로 이전하면 갑자기 오후 10시 알림으로 바뀝니다. 반드시 `ZonedDateTime`이나 `Instant + ZoneId` 조합으로 저장해야 합니다.

---

## 5. Period vs Duration

> **비유:** `Period`는 "3개월 후에 만나요"처럼 달력 위에서 손가락으로 칸을 세는 것입니다. 2월(28일)과 3월(31일)의 길이가 달라도 달력이 알아서 처리합니다. `Duration`은 스톱워치입니다. 버튼을 누른 순간부터 정확히 몇 초가 흘렀는지만 측정하며, 달력이 어떻게 생겼는지는 관심이 없습니다.

### 동작 원리 비교

`Period`는 달력(calendar) 기반입니다. "3개월 후"를 계산할 때 실제 달력을 따라가므로 윤년과 월의 일수 차이를 자동으로 반영합니다. `Duration`은 물리적 시간 기반입니다. "3시간 후"는 정확히 10800초 후입니다. 서머타임(DST)도 무시합니다.

### Period — 날짜 기반 기간 (년/월/일)

```java
// 생성
Period period = Period.of(1, 6, 15);    // 1년 6개월 15일
Period years  = Period.ofYears(2);
Period months = Period.ofMonths(3);
Period days   = Period.ofDays(10);
Period week   = Period.ofWeeks(2);      // 14일

// 두 날짜 사이의 기간
LocalDate start = LocalDate.of(2024, 1, 1);
LocalDate end   = LocalDate.of(2026, 5, 1);
Period between = Period.between(start, end);

between.getYears()   // 2
between.getMonths()  // 4
between.getDays()    // 0
between.toTotalMonths()  // 28

// 날짜에 적용
LocalDate future = start.plus(period);
LocalDate past   = end.minus(Period.ofMonths(6));
```

### Duration — 시간 기반 기간 (초/나노초)

```java
// 생성
Duration duration = Duration.ofHours(2).plusMinutes(30);
Duration d1 = Duration.of(90, ChronoUnit.MINUTES);
Duration d2 = Duration.ofDays(1);    // 86400초
Duration d3 = Duration.ofHours(24);
Duration d4 = Duration.ofMinutes(60);
Duration d5 = Duration.ofSeconds(3600);
Duration d6 = Duration.ofMillis(1000);
Duration d7 = Duration.ofNanos(1_000_000_000L);

// 두 시간 사이
LocalTime t1 = LocalTime.of(9, 0);
LocalTime t2 = LocalTime.of(17, 30);
Duration workDay = Duration.between(t1, t2);  // 8시간 30분

workDay.toHours()    // 8
workDay.toMinutes()  // 510
workDay.toSeconds()  // 30600

// Instant 사이 경과 시간
Instant start = Instant.now();
// ... 작업 ...
Instant end = Instant.now();
Duration elapsed = Duration.between(start, end);
System.out.println("소요 시간: " + elapsed.toMillis() + "ms");
```

### Period vs Duration 비교

```mermaid
graph LR
    A["기간 측정"] --> B["달력 기반 → Period"]
    A --> C["물리적 시간 기반 → Duration"]
    B --> D["단위: 년/월/일"]
    B --> E["대상: LocalDate"]
    B --> F["윤년 자동 반영 ✓"]
    C --> G["단위: 초/나노초"]
    C --> H["대상: LocalTime, Instant"]
    C --> I["DST 무시 (절대 초)"]
```

**비유:** Period는 "3개월 후 만나요"처럼 달력을 보고 세는 것이고, Duration은 스톱워치처럼 물리적 시간을 측정하는 것입니다.

---

## 6. DateTimeFormatter — 포맷팅/파싱

> **비유:** `DateTimeFormatter`는 통역사입니다. 컴퓨터가 이해하는 날짜 객체를 사람이 읽을 수 있는 문자열로 번역하고(`format`), 반대로 사람이 쓴 문자열을 컴퓨터 날짜 객체로 번역합니다(`parse`). `SimpleDateFormat`은 한 번에 한 사람만 통역할 수 있는 통역사이고(스레드 안전 X), `DateTimeFormatter`는 동시에 여러 사람을 통역할 수 있는 AI 통역기입니다(스레드 안전 O).

### 동작 원리

`DateTimeFormatter`는 불변(immutable) 객체입니다. `SimpleDateFormat`과 달리 내부 상태가 없어서 여러 스레드가 동시에 호출해도 안전합니다. 한 번 생성한 포맷터는 `static final`로 선언해 전체 애플리케이션에서 공유할 수 있습니다.

### 미리 정의된 포맷터

```java
LocalDate date = LocalDate.of(2026, 5, 1);

date.format(DateTimeFormatter.ISO_DATE)           // 2026-05-01
date.format(DateTimeFormatter.ISO_LOCAL_DATE)     // 2026-05-01
date.format(DateTimeFormatter.BASIC_ISO_DATE)     // 20260501
date.format(DateTimeFormatter.ISO_ORDINAL_DATE)   // 2026-121

LocalDateTime dt = LocalDateTime.now();
dt.format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)  // 2026-05-01T14:30:45
dt.format(DateTimeFormatter.ISO_DATE_TIME)
```

### 커스텀 포맷터

```java
// 포맷 패턴
DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy년 MM월 dd일 HH:mm:ss");
String formatted = LocalDateTime.now().format(formatter);
// "2026년 05월 01일 14:30:45"

// 파싱
LocalDateTime parsed = LocalDateTime.parse("2026년 05월 01일 14:30:45", formatter);

// 자주 쓰는 패턴
DateTimeFormatter.ofPattern("yyyy-MM-dd")           // 2026-05-01
DateTimeFormatter.ofPattern("yyyyMMdd")             // 20260501
DateTimeFormatter.ofPattern("yyyy/MM/dd HH:mm")     // 2026/05/01 14:30
DateTimeFormatter.ofPattern("dd-MMM-yyyy")          // 01-May-2026
DateTimeFormatter.ofPattern("E, dd MMM yyyy", Locale.ENGLISH)  // Fri, 01 May 2026
```

### 포맷 패턴 문자 참조

| 패턴 | 의미 | 예시 |
|------|------|------|
| `yyyy` | 4자리 연도 | 2026 |
| `MM` | 2자리 월 | 05 |
| `MMM` | 월 약자 | May |
| `dd` | 2자리 일 | 01 |
| `HH` | 24시간 | 14 |
| `hh` | 12시간 | 02 |
| `mm` | 분 | 30 |
| `ss` | 초 | 45 |
| `SSS` | 밀리초 | 123 |
| `EEEE` | 요일 전체 | Friday |
| `z` | 시간대 이름 | KST |
| `Z` | 오프셋 | +0900 |

### SimpleDateFormat vs DateTimeFormatter

```java
// SimpleDateFormat — 스레드 안전 X
SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd");
// 여러 스레드에서 공유하면 버그 발생!

// DateTimeFormatter — 불변, 스레드 안전 O
private static final DateTimeFormatter FORMATTER =
    DateTimeFormatter.ofPattern("yyyy-MM-dd");
// 안전하게 static으로 공유 가능
```

### 로케일 포맷터

```java
// 지역화 포맷
DateTimeFormatter koFormatter = DateTimeFormatter
    .ofLocalizedDate(FormatStyle.FULL)
    .withLocale(Locale.KOREAN);
LocalDate.now().format(koFormatter);  // 2026년 5월 1일 금요일

DateTimeFormatter enFormatter = DateTimeFormatter
    .ofLocalizedDate(FormatStyle.LONG)
    .withLocale(Locale.ENGLISH);
LocalDate.now().format(enFormatter);  // May 1, 2026
```

---

## 7. 시간대(ZoneId) 처리

> **비유:** 시간대는 같은 영화를 다른 상영관에서 동시에 상영하는 것과 같습니다. 서울 상영관에서는 "14:30 시작"이라고 적혀 있고, 뉴욕 상영관에서는 "01:30 시작"이라고 적혀 있지만 실제로는 같은 순간에 상영이 시작됩니다. `ZoneId`는 상영관 이름표이고, `Instant`는 "영화가 시작되는 절대적 순간"입니다.

### 한국 시간 처리

```java
ZoneId KOREA = ZoneId.of("Asia/Seoul");  // UTC+9, KST

// 현재 한국 시간
ZonedDateTime nowKorea = ZonedDateTime.now(KOREA);

// UTC → KST 변환
Instant utcInstant = Instant.now();
ZonedDateTime kst = utcInstant.atZone(KOREA);

// KST → UTC 변환
ZonedDateTime kstTime = ZonedDateTime.of(2026, 5, 1, 14, 30, 0, 0, KOREA);
Instant utc = kstTime.toInstant();
```

### 서머타임(DST) 처리

```java
ZoneId ny = ZoneId.of("America/New_York");

// ZonedDateTime은 DST 자동 처리
ZonedDateTime before = ZonedDateTime.of(2026, 3, 8, 1, 0, 0, 0, ny);
ZonedDateTime after = before.plusHours(1);
// DST 시작 시 2:00가 3:00로 이동 → 자동 처리

// Duration은 절대 초 기준 (DST 무시)
Duration d = Duration.ofHours(25);  // 항상 25*3600초
```

---

## 8. 불변 객체 설계와 날짜 API

> **비유:** 불변 객체는 인쇄된 달력입니다. 벽에 걸린 달력에 "5월 1일"이라고 인쇄되어 있으면 누가 펜으로 덧쓰더라도 원본 인쇄는 변하지 않습니다. 반면 가변 객체는 화이트보드 달력입니다. 누군가 지우개로 지우고 다시 쓰면 모든 사람이 바뀐 내용을 보게 됩니다.

### java.time이 불변인 이유

불변 설계의 핵심 이점은 **공유 안전성**입니다. 레스토랑 메뉴판처럼 모두가 볼 수 있지만 누구도 내용을 지울 수 없는 구조입니다. 어떤 코드가 `LocalDate`를 전달받아도 원본을 수정할 수 없으니 방어적 복사가 필요 없습니다.

```java
// 모든 수정 메서드는 새 객체 반환
LocalDate date = LocalDate.of(2026, 5, 1);
LocalDate modified = date.plusDays(10);  // date는 그대로

System.out.println(date);      // 2026-05-01 (변경 없음)
System.out.println(modified);  // 2026-05-11

// 스레드 안전: 여러 스레드가 같은 LocalDate 공유 가능
private static final LocalDate START_DATE = LocalDate.of(2026, 1, 1);
// 변경 불가이므로 안전하게 공유
```

### 날짜 유효성 검증

```java
// 잘못된 날짜 — 즉시 예외
LocalDate.of(2026, 2, 30);  // DateTimeException: Invalid date
LocalDate.of(2026, 13, 1);  // DateTimeException: Invalid month

// 안전한 파싱
try {
    LocalDate date = LocalDate.parse(input);
} catch (DateTimeParseException e) {
    // 처리
}
```

### 레거시 Date 연동

```java
// Date → LocalDateTime
Date legacyDate = new Date();
LocalDateTime ldt = legacyDate.toInstant()
    .atZone(ZoneId.systemDefault())
    .toLocalDateTime();

// LocalDateTime → Date
LocalDateTime ldt = LocalDateTime.now();
Date legacyDate = Date.from(ldt.atZone(ZoneId.systemDefault()).toInstant());

// Calendar → LocalDateTime
Calendar cal = Calendar.getInstance();
LocalDateTime ldt = cal.toInstant()
    .atZone(ZoneId.systemDefault())
    .toLocalDateTime();
```

---

## 9. 자주 쓰는 날짜 연산 모음

> **비유:** 날짜 연산 유틸리티는 스마트폰 캘린더 앱의 "빠른 이동" 기능입니다. "이번 달 마지막 날", "다음 금요일", "D-Day 계산" 등을 손가락 한 번으로 찾는 것처럼, `TemporalAdjusters`는 복잡한 달력 계산을 한 줄의 메서드 호출로 해결합니다.

```java
// 이번 달 첫날 / 마지막날
LocalDate firstDay = LocalDate.now().withDayOfMonth(1);
LocalDate lastDay  = LocalDate.now().with(TemporalAdjusters.lastDayOfMonth());

// 다음 달 첫날
LocalDate nextMonth = LocalDate.now().with(TemporalAdjusters.firstDayOfNextMonth());

// 이번 주 월요일
LocalDate monday = LocalDate.now().with(DayOfWeek.MONDAY);

// 다음 금요일
LocalDate nextFriday = LocalDate.now().with(TemporalAdjusters.next(DayOfWeek.FRIDAY));

// D-Day 계산
LocalDate target = LocalDate.of(2026, 12, 31);
long daysLeft = ChronoUnit.DAYS.between(LocalDate.now(), target);
System.out.println("D-" + daysLeft);

// 나이 계산
LocalDate birthday = LocalDate.of(1990, 8, 15);
int age = Period.between(birthday, LocalDate.now()).getYears();

// 두 날짜 사이 모든 날
LocalDate start = LocalDate.of(2026, 5, 1);
LocalDate end   = LocalDate.of(2026, 5, 7);
start.datesUntil(end).forEach(System.out::println);  // Java 9+
```

---

<details class="extreme-scenario-details" ontoggle="if(this.open){var ad=this.querySelector('.extreme-scenario-ad');if(ad&&!ad.dataset.loaded){ad.dataset.loaded='1';(adsbygoogle=window.adsbygoogle||[]).push({});}}">
<summary class="extreme-scenario-summary">
<span class="extreme-scenario-icon">🔥</span>
<span class="extreme-scenario-label">극한 시나리오 — 클릭하여 펼치기</span>
<span class="extreme-scenario-toggle"></span>
</summary>
<div class="extreme-scenario-body">
<div class="extreme-scenario-ad" style="text-align:center; margin-bottom:1.5em;">
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="ca-pub-7225106491387870"
     data-ad-slot="0000000000"
     data-ad-format="auto"
     data-full-width-responsive="true"></ins>
</div>
<div class="extreme-scenario-content" markdown="1">

### 시나리오 1: 글로벌 예약 시스템 (100 TPS)

> **비유:** 전 세계 지사가 하나의 회의실 예약 게시판을 공유하는 것과 같습니다. 서울 지사가 "오후 2시"라고 쓰고 뉴욕 지사가 "오후 2시"라고 쓰면 실제로는 14시간 차이가 나는 전혀 다른 시간입니다.

- **문제:** 서울, 도쿄, 뉴욕, 런던에서 동시에 예약 요청이 들어올 때 시간대를 `LocalDateTime`으로 저장하면 "서울 14:00"과 "뉴욕 14:00"이 같은 시간으로 저장됩니다.
- **해결:** 모든 예약을 `Instant`(UTC)로 변환하여 저장하고, 표시할 때만 사용자의 `ZoneId`로 변환합니다. DB 컬럼은 `TIMESTAMP WITH TIME ZONE`을 사용합니다.
- **근거:** UTC 단일 기준으로 통일하면 DST 전환, 시간대 정책 변경에도 데이터 정합성이 유지됩니다.

### 시나리오 2: 금융 거래 타임스탬프 (10K TPS)

> **비유:** 증권거래소의 주문 접수 도장과 같습니다. 밀리초 단위로 도장이 찍히는데, 도장 시계가 서로 다르면 "먼저 주문한 사람"을 판별할 수 없습니다.

- **문제:** 초당 10,000건의 거래가 발생할 때 `System.currentTimeMillis()`의 밀리초 해상도로는 같은 타임스탬프가 수십~수백 건 겹칩니다.
- **해결:** `Instant.now()`의 나노초 정밀도를 사용하고, NTP 동기화된 서버 시각 + 단조 증가 시퀀스를 조합하여 유일한 순서를 보장합니다.
- **근거:** `Instant`는 내부적으로 `epochSecond`(long) + `nanos`(int)를 저장하므로 이론상 나노초 단위 구분이 가능합니다.

### 시나리오 3: 대규모 배치 스케줄러 (100K 건/일)

> **비유:** 100만 명에게 생일 축하 문자를 보내는 자동 발송 시스템입니다. 시간대를 무시하면 한국 사용자에게 새벽 3시에 문자가 도착합니다.

- **문제:** 매일 10만 건의 예약 작업(알림, 정산, 보고서)이 각기 다른 시간대의 사용자를 대상으로 실행됩니다. DST 전환일에 1시간이 사라지거나 중복되면서 작업이 누락되거나 이중 실행됩니다.
- **해결:** 스케줄러 내부는 `ZonedDateTime`으로 "다음 실행 시각"을 계산하되, 실행 여부 판단은 `Instant` 비교로 합니다. DST 전환으로 건너뛴 시간대는 즉시 실행, 중복 시간대는 첫 번째만 실행하는 규칙을 명시합니다.
- **근거:** `ZonedDateTime.plusDays(1)`은 DST를 자동 반영하지만, `Duration.ofDays(1)`은 항상 86400초이므로 DST 전환일에 23시간 또는 25시간이 됩니다.

---
</div>
</div>
</details>

## 11. 실무에서 자주 하는 실수

### 실수 1: SimpleDateFormat을 static으로 공유

```java
// 위험: SimpleDateFormat은 내부 Calendar를 공유 → 스레드 안전 X
private static final SimpleDateFormat SDF = new SimpleDateFormat("yyyy-MM-dd");

// 해결: DateTimeFormatter는 불변이므로 static 공유 안전
private static final DateTimeFormatter DTF = DateTimeFormatter.ofPattern("yyyy-MM-dd");
```

### 실수 2: LocalDateTime으로 글로벌 시각 저장

```java
// 위험: 시간대 정보가 없어 서버 이전 시 시각이 틀어짐
LocalDateTime eventTime = LocalDateTime.now();  // 어느 나라 시간인지 불명

// 해결: Instant 또는 ZonedDateTime 사용
Instant eventTime = Instant.now();  // UTC 절대 시각
```

### 실수 3: plusDays(1)과 Duration.ofDays(1) 혼동

```java
ZonedDateTime zdt = ZonedDateTime.of(2026, 3, 8, 1, 0, 0, 0, ZoneId.of("America/New_York"));

// 달력 기준 하루 (DST 반영 → 23시간일 수 있음)
ZonedDateTime next1 = zdt.plusDays(1);

// 물리적 24시간 (DST 무시 → 시각이 1시간 밀릴 수 있음)
ZonedDateTime next2 = zdt.plus(Duration.ofDays(1));
```

### 실수 4: 날짜 연산 결과를 재할당하지 않음

```java
LocalDate date = LocalDate.of(2026, 5, 1);
date.plusDays(10);  // 반환값 무시! date는 여전히 5월 1일
date = date.plusDays(10);  // 올바른 사용
```

### 실수 5: 월(Month)이 1 기준인데 0 기준으로 착각

```java
// Date/Calendar 습관으로 java.time에서도 0 기준 사용
LocalDate wrong = LocalDate.of(2026, 4, 1);   // 4월 (의도는 5월)
LocalDate right = LocalDate.of(2026, 5, 1);   // 5월
LocalDate safe  = LocalDate.of(2026, Month.MAY, 1);  // Month 상수로 실수 방지
```

---

## 12. 면접 포인트

### Q1: Date/Calendar 대신 java.time을 쓰는 이유는?

**A:** 세 가지입니다. 첫째, `java.time`은 불변(Immutable)이라 멀티스레드 환경에서 안전합니다. 둘째, 월이 1부터 시작하고 `Month` 열거형을 제공해 직관적입니다. 셋째, `DateTimeFormatter`가 스레드 안전하므로 `static final`로 공유할 수 있어 `SimpleDateFormat`의 동시성 버그를 원천 차단합니다.

### Q2: Instant와 LocalDateTime의 차이는?

**A:** `Instant`는 UTC 기준 절대 시각(epoch 초+나노초)으로 전 세계 어디서나 같은 순간을 나타냅니다. `LocalDateTime`은 시간대 정보가 없는 "벽시계 시각"으로, 서울 14:00과 뉴욕 14:00을 구분할 수 없습니다. DB 저장이나 서버 간 통신에는 `Instant`, 사용자 UI 표시에는 `ZonedDateTime`을 사용합니다.

### Q3: Period와 Duration의 차이는?

**A:** `Period`는 달력 기반(년/월/일)으로 "3개월 후"를 계산할 때 2월(28일)과 3월(31일)의 차이를 자동 반영합니다. `Duration`은 물리적 시간 기반(초/나노초)으로 정확히 N초 후를 계산하며 DST를 무시합니다. `LocalDate` 연산에는 `Period`, 성능 측정이나 `Instant` 연산에는 `Duration`을 사용합니다.

### Q4: ZonedDateTime에서 DST 전환 시 어떻게 동작하나요?

**A:** `ZonedDateTime.plusHours(1)`은 DST 전환을 자동 처리합니다. 예를 들어 미국 동부 시간 기준 3월 둘째 일요일 02:00에 시계가 03:00으로 점프하는데, `plusHours(1)`은 이를 반영하여 올바른 현지 시각을 반환합니다. 반면 `Duration.ofHours(1)`을 더하면 물리적 3600초만 더하므로 현지 시각이 예상과 다를 수 있습니다.

### Q5: DateTimeFormatter를 static final로 선언해도 안전한 이유는?

**A:** `DateTimeFormatter`는 내부 상태가 없는 불변 객체이기 때문입니다. `format()`과 `parse()` 호출 시 스레드 로컬 변수만 사용하므로 여러 스레드가 동시에 호출해도 간섭이 없습니다. 반면 `SimpleDateFormat`은 내부에 `Calendar` 인스턴스를 공유하므로 동시 호출 시 날짜가 뒤섞이는 버그가 발생합니다.

---

## 13. 전체 요약

```mermaid
graph TD
    A["상황"] --> B["날짜만 필요 → LocalDate"]
    A --> C["시간만 필요 → LocalTime"]
    A --> D["시간대 불필요 날짜+시간 → LocalDateTime"]
    A --> E["시간대 포함 글로벌 → ZonedDateTime"]
    A --> F["DB 저장 / API 응답 → OffsetDateTime"]
    A --> G["로그/타임스탬프 → Instant"]
    A --> H["날짜 기반 기간 → Period"]
    A --> I["시간 기반 경과 → Duration"]
```

**핵심 원칙 요약:**
- `Date`/`Calendar`는 신규 코드에서 사용 금지
- `DateTimeFormatter`는 `static final`로 공유
- DB 저장은 UTC `Instant` 또는 `OffsetDateTime`
- 사용자 표시는 `ZonedDateTime` + 시간대 변환
- `SimpleDateFormat` `static` 공유 절대 금지 (스레드 안전 X)
