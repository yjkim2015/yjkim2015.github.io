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

```
Date / Calendar 문제점:
┌────────────────────────────────────────────┐
│ 1. 가변(Mutable) → 스레드 안전 X           │
│ 2. 월이 0 기준 (1월=0) → 직관성 없음      │
│ 3. 연도가 1900 기준 (Date)                 │
│ 4. 타입 안전 없음 (정수 상수)              │
│ 5. 시간대 처리 어려움                      │
│ 6. 날짜 연산 불편                          │
│ 7. 포맷팅 API 분리 (SimpleDateFormat)      │
│    → SimpleDateFormat은 스레드 안전 X      │
└────────────────────────────────────────────┘
```

---

## 2. java.time 패키지 전체 구조

```
java.time 클래스 계층:
┌──────────────────────────────────────────────────────┐
│                   날짜/시간 클래스                    │
│                                                      │
│  날짜만        LocalDate       2026-05-01            │
│  시간만        LocalTime       14:30:00              │
│  날짜+시간     LocalDateTime   2026-05-01T14:30:00   │
│                                                      │
│  시간대 포함   ZonedDateTime   2026-05-01T14:30:00+09:00[Asia/Seoul]  │
│  오프셋 포함   OffsetDateTime  2026-05-01T14:30:00+09:00              │
│  머신 시간     Instant         1970-01-01T00:00:00Z 기준 나노초       │
│                                                      │
│  기간          Period          날짜 기반 (년/월/일)   │
│                Duration        시간 기반 (초/나노초)  │
│                                                      │
│  포맷          DateTimeFormatter                      │
│  시간대        ZoneId, ZoneOffset                    │
└──────────────────────────────────────────────────────┘
```

---

## 3. LocalDate, LocalTime, LocalDateTime

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

---

## 5. Period vs Duration

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

```
┌──────────────┬──────────────────┬──────────────────┐
│              │    Period        │    Duration      │
├──────────────┼──────────────────┼──────────────────┤
│ 단위         │ 년/월/일         │ 초/나노초        │
│ 사용 대상    │ LocalDate        │ LocalTime/Instant│
│ 윤년 고려    │ O                │ X (고정 초)      │
│ 서머타임 고려│ O (날짜 기반)    │ X (절대 초)      │
│ 적합한 상황  │ "3개월 후"       │ "3시간 후"       │
└──────────────┴──────────────────┴──────────────────┘
```

---

## 6. DateTimeFormatter — 포맷팅/파싱

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

```
패턴 문자:
y — 연도 (yyyy: 4자리, yy: 2자리)
M — 월 (MM: 숫자, MMM: 약자, MMMM: 전체)
d — 일 (dd: 2자리)
H — 시 (24시간, HH: 2자리)
h — 시 (12시간)
m — 분 (mm: 2자리)
s — 초 (ss: 2자리)
S — 밀리초 (SSS: 3자리)
E — 요일 (EEE: Mon, EEEE: Monday)
a — AM/PM
z — 시간대 이름 (KST)
Z — 시간대 오프셋 (+0900)
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

---

## 7. 시간대(ZoneId) 처리

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

### java.time이 불변인 이유

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

## 10. 전체 요약

```
java.time 선택 가이드:
┌────────────────┬──────────────────────────────────────┐
│  클래스        │  사용 시점                           │
├────────────────┼──────────────────────────────────────┤
│ LocalDate      │ 날짜만 (생일, 기념일)                │
│ LocalTime      │ 시간만 (업무 시간, 알람)             │
│ LocalDateTime  │ 시간대 불필요한 날짜시간             │
│ ZonedDateTime  │ 시간대 포함 (글로벌 서비스)          │
│ OffsetDateTime │ DB 저장, API 응답 (시간대 정보 포함) │
│ Instant        │ 로그, 이벤트 타임스탬프 (UTC 절대값) │
│ Period         │ 날짜 기반 기간 (D+30, 3개월 후)     │
│ Duration       │ 시간 기반 경과 (실행 시간, 타임아웃) │
└────────────────┴──────────────────────────────────────┘

핵심 원칙:
- Date/Calendar 신규 코드에서 사용 금지
- DateTimeFormatter는 static final로 공유
- DB 저장: UTC Instant 또는 OffsetDateTime
- 사용자 표시: ZonedDateTime + 시간대 변환
```
