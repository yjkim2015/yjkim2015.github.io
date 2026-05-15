---
title: "Kotlin 스코프 함수와 위임 패턴 — let, run, apply, also, with 그리고 by lazy의 내부 동작"
categories:
- KOTLIN
tags: [Kotlin, 스코프함수, let, run, apply, also, with, 위임, by lazy, Delegates, 프로퍼티위임]
toc: true
toc_sticky: true
toc_label: 목차
---

Kotlin 코드베이스를 처음 읽을 때 가장 낯선 것이 두 가지다. 하나는 `?.let { }`, `apply { }`, `also { }` 같은 스코프 함수들이 뒤엉켜 있는 체이닝 코드고, 다른 하나는 `val token: String by lazy { ... }`처럼 `by` 키워드로 프로퍼티를 "누군가에게 맡기는" 위임 패턴이다. 두 개념은 Kotlin의 함수형 DNA와 언어 설계 철학이 집약된 곳이다. 이 글은 그 둘을 코드 + 비유 + 바이트코드 수준까지 해부한다.

---

## 비유 — 셰프와 주방 보조

스코프 함수를 이해하는 가장 직관적인 비유는 레스토랑 주방이다.

셰프(호출자)가 재료(객체)를 들고 있다고 하자. 셰프가 직접 손질할 수도 있고(일반 코드), 보조에게 맡길 수도 있다. "이 재료로 무언가 만들어서 결과물만 줘" — 이게 `let`이다. "이 재료 위에 양념 발라놔, 재료 그대로 돌려줘" — 이게 `apply`다. "뭘 하든 다 봐둬, 나중에 로그 남겨야 해" — 이게 `also`다. "이 재료가 있을 때만 요리해" — 이게 `?.let`의 null 안전 체이닝이다.

위임(delegation)은 다른 비유다. 아파트 관리사무소를 생각해보자. 거주자(클래스)는 주차 관리, 청소, 보안을 직접 하지 않는다. 각 전문 업체(위임 객체)에 맡기고 결과만 받는다. `by` 키워드는 "이 프로퍼티의 get/set 로직을 저 객체한테 위임한다"는 선언이다.

---

## 1. 스코프 함수 5개 완전 비교

### 수신 객체와 반환값 매트릭스

5개 함수는 딱 두 가지 축으로 분류된다. **람다 안에서 객체를 어떻게 참조하느냐(this vs it)**와 **무엇을 반환하느냐(람다 결과 vs 수신 객체)**다.

| 함수 | 수신 객체 참조 | 반환값 | 확장 함수 여부 |
|------|--------------|--------|--------------|
| `let` | `it` | 람다 결과 | O |
| `run` | `this` | 람다 결과 | O |
| `with` | `this` | 람다 결과 | X (일반 함수) |
| `apply` | `this` | 수신 객체 | O |
| `also` | `it` | 수신 객체 | O |

이 표가 전부다. 외우려 하지 말고, 아래 각 함수의 시그니처와 쓰임새를 보면 자연스럽게 체화된다.

### let — "이걸로 뭔가 계산해서 줘"

```kotlin
// 시그니처 (코틀린 표준 라이브러리)
public inline fun <T, R> T.let(block: (T) -> R): R = block(this)
```

`let`의 핵심은 **변환**이다. 어떤 값을 받아서 다른 값으로 바꿀 때 쓴다. 람다 파라미터는 `it`이고, 람다의 마지막 표현식이 반환된다.

```kotlin
// 가장 흔한 용도 1: null 안전 체이닝
val user: User? = findUser(id)
val displayName = user?.let { "${it.firstName} ${it.lastName}" } ?: "Unknown"

// 가장 흔한 용도 2: 긴 표현식을 지역 변수로 래핑
val result = heavyComputation()
    .let { it * 2 }
    .let { it.toString() }
    .let { "Result: $it" }

// 가장 흔한 용도 3: 임시 스코프로 변수 오염 방지
val token = run { /* token만 여기서 만들고 밖으로 안 새어나감 */ }
// 아래처럼 let으로도 가능
someConfig.let { config ->
    val processed = processConfig(config)
    validate(processed)
    processed.toDomain()
}
```

`?.let`은 Java의 `if (obj != null) { ... }` 패턴을 표현식으로 만든 것이다. 하지만 이 패턴을 남용하면 안 된다 — 중첩된 `?.let { ?.let { } }`은 가독성을 오히려 해친다. 두 단계 이상 중첩되면 `if` 블록이 더 명확하다.

### run — "이 문맥 안에서 계산해"

```kotlin
// 확장 함수 버전
public inline fun <T, R> T.run(block: T.() -> R): R = block()

// 비확장 함수 버전 (독립 실행)
public inline fun <R> run(block: () -> R): R = block()
```

`run`은 `let`과 반환값이 같지만 람다 내부에서 `this`로 수신 객체에 접근한다는 점이 다르다. `this`를 생략할 수 있으므로 객체의 멤버를 마치 내 것처럼 직접 쓸 수 있다.

```kotlin
// 객체 초기화 후 최종 값 계산
val result = StringBuilder().run {
    append("Hello")
    append(", ")
    append("World")
    toString()  // this.toString() — this 생략
}

// 비확장 버전: 블록을 표현식으로 감쌀 때
val configured = run {
    val base = loadBaseConfig()
    val override = loadOverrideConfig()
    base.merge(override)
}
```

`with`와 `run`(확장 버전)은 기능이 거의 같다. 차이는 null 안전 체이닝 가능 여부다. `run`은 확장 함수라 `obj?.run { }` 패턴이 가능하고, `with`는 불가능하다.

### with — "이 객체 기준으로 여러 작업해"

```kotlin
// 시그니처: 확장 함수가 아님
public inline fun <T, R> with(receiver: T, block: T.() -> R): R = receiver.block()
```

`with`는 이미 null이 아님을 확인한 객체에 여러 작업을 묶을 때 쓴다. 인자로 receiver를 직접 받기 때문에 체이닝 스타일보다 블록 스타일에 어울린다.

```kotlin
val person = Person("Alice", 30)

// with 사용: 여러 프로퍼티 읽기
val summary = with(person) {
    "이름: $name, 나이: $age, 성인: ${age >= 18}"
    // name, age 모두 this.name, this.age — this 생략
}

// 주의: with는 null 안전 체이닝 불가
// person?.with { } — 컴파일 에러
// 이럴 땐 run을 써야 한다
```

`with`는 원래 Java 시절 Builder 패턴을 흉내 낼 때 자주 썼지만, 현대 Kotlin에서는 `apply`에 밀렸다. 용도가 겹치는 함수들 중 가장 적게 쓰인다.

### apply — "이 객체 설정해서 돌려줘"

```kotlin
// 시그니처
public inline fun <T> T.apply(block: T.() -> Unit): T {
    block()
    return this
}
```

`apply`는 **빌더 패턴의 Kotlin 버전**이다. 객체를 설정하고 그 객체 자체를 반환한다. 람다 안에서 `this`가 수신 객체이고, 반환값은 항상 수신 객체다.

```kotlin
// 가장 대표적인 용도: 객체 초기화 블록
val paint = Paint().apply {
    color = Color.RED
    strokeWidth = 5f
    isAntiAlias = true
    style = Paint.Style.FILL
}

// AlertDialog.Builder 스타일
val dialog = AlertDialog.Builder(context).apply {
    setTitle("확인")
    setMessage("정말 삭제하시겠습니까?")
    setPositiveButton("삭제") { _, _ -> viewModel.delete() }
    setNegativeButton("취소", null)
}.create()

// 테스트에서 객체 준비
val testUser = User().apply {
    id = 1L
    name = "테스트 유저"
    email = "test@example.com"
    createdAt = LocalDateTime.now()
}
```

`apply`의 강점은 체이닝이다. 빌더 패턴처럼 `return this`를 반복 작성하지 않아도 된다. 단, `apply` 블록 안에서 값을 반환하는 계산은 하지 않는 것이 관례다 — 계산 결과가 필요하면 `run`을 쓴다.

### also — "이 객체를 건드리되, 중간에 뭔가 더 해"

```kotlin
// 시그니처
public inline fun <T> T.also(block: (T) -> Unit): T {
    block(this)
    return this
}
```

`also`는 `apply`와 반환값이 같다(수신 객체). 차이는 람다 안에서 `it`으로 접근한다는 것. 이 미묘한 차이가 쓰임새를 결정한다: `also`는 객체 자체를 건드리지 않는 **부수 효과(side effect)** 전용이다.

```kotlin
// 가장 흔한 용도: 로깅을 체인 중간에 끼워넣기
val user = userRepository.findById(id)
    .also { log.debug("조회된 유저: {}", it) }
    ?.also { auditLog.record("USER_READ", it.id) }
    ?.toDomain()

// 디버깅용 중간 출력
val processedList = rawData
    .filter { it.isValid() }
    .also { println("필터 후 개수: ${it.size}") }
    .map { it.transform() }
    .also { println("변환 후 개수: ${it.size}") }

// 체인을 끊지 않고 추가 작업
fun createUser(name: String): User =
    User(name = name)
        .also { userRepository.save(it) }
        .also { eventBus.publish(UserCreatedEvent(it.id)) }
```

`also`가 `it`을 쓰는 이유가 있다. `this`를 쓰면 외부 클래스의 `this`와 충돌할 수 있다. 로깅이나 부수 효과 코드는 보통 외부 컨텍스트의 서비스나 레포지토리를 쓰는데, `it`으로 명확하게 구분하면 코드 의도가 드러난다.

---

## 2. 실전 선택 가이드

### 언제 어떤 함수를 쓰는가

복잡하게 생각할 필요 없다. 질문 두 가지로 결정된다.

**Q1. 람다 결과를 반환하고 싶은가, 수신 객체를 반환하고 싶은가?**
- 람다 결과 → `let`, `run`, `with`
- 수신 객체 → `apply`, `also`

**Q2. 람다 안에서 수신 객체를 `this`처럼 쓰고 싶은가, `it`으로 명시하고 싶은가?**
- `this` (멤버 직접 호출) → `run`, `with`, `apply`
- `it` (외부 파라미터처럼) → `let`, `also`

```kotlin
// 결정 트리로 보면:
//
// 객체 설정 후 객체 반환? → apply (this) / also (it, 부수효과)
// 객체로 계산 후 다른 값 반환?
//   null 안전 체이닝 필요? → let (it) / run (this)
//   이미 not-null 확인됨?  → with (this, 비확장)
```

### 실전 패턴 모음

```kotlin
// 패턴 1: null이면 기본값, null 아니면 변환
val name = user?.let { "${it.firstName} ${it.lastName}" } ?: "Guest"

// 패턴 2: 객체 생성 + 설정 한 줄에
val intent = Intent(context, DetailActivity::class.java).apply {
    putExtra("id", item.id)
    putExtra("title", item.title)
    flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
}

// 패턴 3: 체인 중간 로깅 (also)
return repository.findAll()
    .also { log.info("총 {}건 조회", it.size) }
    .filter { it.isActive }
    .map { it.toResponse() }

// 패턴 4: 복잡한 조건 계산을 스코프로 격리 (run)
val fee = run {
    val base = order.amount * 0.03
    val discount = if (user.isVip) base * 0.1 else 0.0
    val tax = (base - discount) * 0.1
    base - discount + tax
}

// 패턴 5: 여러 속성 읽기만 할 때 (with)
val label = with(product) {
    "$name ($category) — ${price.formatCurrency()}"
}
```

### 성능 관련 주의사항

5개 함수 모두 `inline` 키워드로 선언되어 있다. 컴파일 시점에 람다 코드가 호출 위치에 직접 삽입(인라이닝)되므로 람다 객체 생성 오버헤드가 없다. 일반 코드와 성능 차이가 전혀 없다.

```kotlin
// 이 코드는
val result = someObject.let { it.process() }

// 컴파일 후 실제로는 이렇게 동작 (람다 객체 없음)
val result = someObject.process()
```

---

## 3. 위임 패턴 (by keyword)

### 위임이란 무엇인가

객체지향에서 위임(Delegation)은 상속의 대안이다. 상속은 "나는 ~이다(is-a)"이고 위임은 "나는 ~를 갖고 있고, 그 일은 그 객체가 한다(has-a + forwarding)"다.

Kotlin의 `by` 키워드는 두 가지 맥락에서 쓰인다.

1. **클래스 위임**: 인터페이스 구현을 다른 객체에 위임
2. **프로퍼티 위임**: 프로퍼티의 get/set 로직을 위임 객체에 위임

```kotlin
// 클래스 위임 예시
interface Printer {
    fun print(text: String)
}

class ConsolePrinter : Printer {
    override fun print(text: String) = println(text)
}

// LoggingPrinter는 Printer를 직접 구현하지 않고 ConsolePrinter에 위임
class LoggingPrinter(private val delegate: Printer) : Printer by delegate {
    // print()는 delegate.print()로 자동 포워딩됨
    // 추가 동작이 필요하면 override로 재정의
}
```

클래스 위임을 쓰면 데코레이터 패턴을 보일러플레이트 없이 구현할 수 있다. Java에서는 인터페이스의 모든 메서드를 손으로 포워딩해야 했다.

### 프로퍼티 위임 구조

프로퍼티 위임의 본질은 `getValue`/`setValue` 연산자 오버로딩이다.

```kotlin
// 위임 프로퍼티의 계약 (ReadOnlyProperty / ReadWriteProperty)
interface ReadOnlyProperty<in ThisRef, out V> {
    operator fun getValue(thisRef: ThisRef, property: KProperty<*>): V
}

interface ReadWriteProperty<in ThisRef, V> : ReadOnlyProperty<ThisRef, V> {
    operator fun setValue(thisRef: ThisRef, property: KProperty<*>, value: V)
}
```

`val x: String by someDelegate`는 컴파일러가 `x`의 getter를 `someDelegate.getValue(this, ::x)`로, setter를 `someDelegate.setValue(this, ::x, value)`로 변환한다는 뜻이다.

---

## 4. 표준 위임 프로퍼티들

### lazy — 지연 초기화

```kotlin
val heavyResource: HeavyResource by lazy {
    HeavyResource.initialize()  // 처음 접근할 때 딱 한 번만 실행
}
```

`by lazy`는 Kotlin에서 가장 많이 쓰이는 위임이다. 프로퍼티를 선언 시점에 초기화하지 않고, **처음 접근할 때** 초기화한다. 이후 접근은 캐시된 값을 반환한다.

실생활 비유: 사전(Dictionary). 책을 받는 순간 모든 페이지를 다 읽는 사람은 없다. 특정 단어를 찾을 때 그 페이지만 열어본다. `by lazy`는 프로퍼티가 그런 사전처럼 동작하게 만든다.

### observable — 값 변경 감지

```kotlin
import kotlin.properties.Delegates

var name: String by Delegates.observable("initial") { prop, old, new ->
    println("${prop.name}: '$old' → '$new'")
}

name = "Alice"  // 출력: name: 'initial' → 'Alice'
name = "Bob"    // 출력: name: 'Alice' → 'Bob'
```

`observable`은 값이 바뀔 때마다 콜백이 호출된다. Android에서 ViewModel의 상태 변경을 UI에 알리거나, 감사 로그(audit log)를 남길 때 유용하다. 이미 값이 바뀐 후 호출되므로 변경을 막을 수는 없다.

### vetoable — 조건부 변경

```kotlin
var age: Int by Delegates.vetoable(0) { _, _, new ->
    new >= 0  // false를 반환하면 값 변경이 거부됨
}

age = 25   // 허용 (25 >= 0)
age = -1   // 거부 — age는 여전히 25
println(age)  // 25
```

`vetoable`은 `observable`과 구조가 같지만 콜백이 Boolean을 반환한다. `false`를 반환하면 값 변경이 취소된다. 도메인 불변식(invariant)을 프로퍼티 레벨에서 강제할 때 쓴다.

### notNull — lateinit 대안

```kotlin
var userId: Int by Delegates.notNull<Int>()
// val은 안 됨 — var만 가능

// 초기화 전 접근 시 IllegalStateException
// lateinit var와 비슷하지만 primitive 타입에도 사용 가능
```

`lateinit var`는 nullable이 아닌 참조 타입(String, List 등)에만 쓸 수 있다. `Int`, `Long`, `Double` 같은 primitive 타입에는 `by Delegates.notNull()`이 대안이다.

### map 위임 — 동적 프로퍼티

```kotlin
class User(private val map: Map<String, Any?>) {
    val name: String by map
    val age: Int by map
    val email: String by map
}

val user = User(mapOf(
    "name" to "Alice",
    "age" to 30,
    "email" to "alice@example.com"
))
println(user.name)  // "Alice"
println(user.age)   // 30
```

`Map`을 위임 객체로 쓰면 JSON 파싱이나 설정 파일 로딩처럼 동적인 키-값 구조를 정적 타입 프로퍼티처럼 다룰 수 있다. `MutableMap`을 쓰면 var 프로퍼티에도 쓸 수 있다.

---

## 5. by lazy의 내부 동작

### LazyThreadSafetyMode

`lazy`는 세 가지 스레드 안전 모드를 지원한다.

```kotlin
// 1. SYNCHRONIZED (기본값) — 더블체크 락킹 사용
val safeResource by lazy { ExpensiveObject() }

// 2. PUBLICATION — CAS(Compare-And-Swap) 방식, 경쟁 시 여러 번 초기화 가능하지만 최초 공개된 값만 사용
val casResource by lazy(LazyThreadSafetyMode.PUBLICATION) { ExpensiveObject() }

// 3. NONE — 동기화 없음, 단일 스레드 환경에서만 사용
val unsafeResource by lazy(LazyThreadSafetyMode.NONE) { ExpensiveObject() }
```

기본값인 `SYNCHRONIZED`가 어떻게 동작하는지 보면 `by lazy`의 안전성 보장 원리를 알 수 있다.

### 더블체크 락킹(Double-Checked Locking)

`SYNCHRONIZED` 모드의 내부 구현은 고전적인 더블체크 락킹 패턴이다.

```kotlin
// Kotlin 표준 라이브러리의 SynchronizedLazyImpl (단순화)
private class SynchronizedLazyImpl<out T>(initializer: () -> T) : Lazy<T> {
    private var initializer: (() -> T)? = initializer
    @Volatile private var _value: Any? = UNINITIALIZED_VALUE

    override val value: T
        get() {
            val v1 = _value
            // 첫 번째 체크 — 락 없이 읽기 (대부분의 경우 여기서 반환)
            if (v1 !== UNINITIALIZED_VALUE) {
                @Suppress("UNCHECKED_CAST")
                return v1 as T
            }
            // 락 획득
            return synchronized(this) {
                val v2 = _value
                // 두 번째 체크 — 락 안에서 다시 확인 (경쟁 상황 방어)
                if (v2 !== UNINITIALIZED_VALUE) {
                    @Suppress("UNCHECKED_CAST")
                    v2 as T
                } else {
                    val typedValue = initializer!!()
                    _value = typedValue
                    initializer = null  // GC 허용
                    typedValue
                }
            }
        }
}
```

`@Volatile`이 핵심이다. `_value`를 volatile로 선언하지 않으면 CPU 캐시 일관성 문제로 한 스레드에서 초기화한 값을 다른 스레드가 보지 못할 수 있다. volatile은 쓰기 연산 후 메모리 배리어(memory barrier)를 삽입해 모든 스레드가 최신 값을 보도록 강제한다.

더블체크 락킹의 흐름:
1. 첫 번째 체크: 락 없이 `_value`를 읽는다. 이미 초기화됐으면 바로 반환 — 대부분의 접근이 여기서 끝난다.
2. 락 획득: 초기화가 필요할 때만 synchronized 블록에 진입한다.
3. 두 번째 체크: 락을 기다리는 동안 다른 스레드가 초기화했을 수 있으므로 다시 확인한다.
4. 초기화 실행: 진짜 처음이면 initializer를 실행하고 결과를 저장한다.

이 패턴이 없으면? Thread A가 초기화를 절반 했을 때 Thread B가 접근해서 부분적으로 초기화된 객체를 얻는 "부분 초기화 문제"가 발생한다. Java에서 유명한 버그 중 하나다.

### PUBLICATION 모드의 차이

```kotlin
// PUBLICATION: 여러 스레드가 각자 초기화할 수 있지만
// 최초로 공개(publish)된 값만 사용됨
private class SafePublicationLazyImpl<out T>(initializer: () -> T) : Lazy<T> {
    @Volatile private var initializer: (() -> T)? = initializer
    @Volatile private var _value: Any? = UNINITIALIZED_VALUE

    override val value: T
        get() {
            val value = _value
            if (value !== UNINITIALIZED_VALUE) return value as T

            // 초기화를 시도
            val initializerValue = initializer
            if (initializerValue != null) {
                val newValue = initializerValue()
                // CAS: _value가 UNINITIALIZED_VALUE면 newValue로 교체
                // 실패해도 괜찮음 — 다른 스레드가 먼저 설정한 값을 그냥 씀
                VALUE_UPDATER.compareAndSet(this, UNINITIALIZED_VALUE, newValue)
            }
            return _value as T
        }
}
```

`PUBLICATION`은 초기화 함수가 순수 함수(같은 입력에 항상 같은 출력, 부수 효과 없음)일 때 선택한다. 초기화 함수가 DB 연결이나 파일 생성 같은 부수 효과를 포함하면 `SYNCHRONIZED`를 써야 한다.

---

## 6. 커스텀 위임 프로퍼티 만들기

### 기본 구조

```kotlin
import kotlin.reflect.KProperty

class StringDelegate(private val default: String = "") {
    private var value: String = default

    operator fun getValue(thisRef: Any?, property: KProperty<*>): String {
        println("${property.name} 읽기")
        return value
    }

    operator fun setValue(thisRef: Any?, property: KProperty<*>, value: String) {
        println("${property.name}: '$this.value' → '$value'")
        this.value = value
    }
}

class Config {
    var host: String by StringDelegate("localhost")
    var path: String by StringDelegate("/api")
}

val config = Config()
println(config.host)    // "host 읽기" 출력 후 "localhost" 반환
config.host = "prod.example.com"  // "host: 'localhost' → 'prod.example.com'" 출력
```

### 실용적인 커스텀 위임 예시: SharedPreferences 위임

Android 개발에서 `SharedPreferences`를 프로퍼티처럼 쓰는 고전적인 패턴이다.

```kotlin
class SharedPreferenceDelegate<T>(
    private val prefs: SharedPreferences,
    private val key: String,
    private val default: T
) {
    @Suppress("UNCHECKED_CAST")
    operator fun getValue(thisRef: Any?, property: KProperty<*>): T =
        when (default) {
            is String  -> prefs.getString(key, default) as T
            is Int     -> prefs.getInt(key, default) as T
            is Boolean -> prefs.getBoolean(key, default) as T
            is Float   -> prefs.getFloat(key, default) as T
            is Long    -> prefs.getLong(key, default) as T
            else       -> throw IllegalArgumentException("지원하지 않는 타입")
        }

    operator fun setValue(thisRef: Any?, property: KProperty<*>, value: T) {
        with(prefs.edit()) {
            when (value) {
                is String  -> putString(key, value)
                is Int     -> putInt(key, value)
                is Boolean -> putBoolean(key, value)
                is Float   -> putFloat(key, value)
                is Long    -> putLong(key, value)
            }
            apply()
        }
    }
}

// 확장 함수로 편의 API 제공
fun <T> SharedPreferences.delegate(key: String, default: T) =
    SharedPreferenceDelegate(this, key, default)

// 사용
class UserPreferences(prefs: SharedPreferences) {
    var isLoggedIn: Boolean by prefs.delegate("is_logged_in", false)
    var userId: String by prefs.delegate("user_id", "")
    var theme: String by prefs.delegate("theme", "light")
}
```

이 패턴 없이는 `SharedPreferences` 접근 코드가 앱 전체에 흩어진다. 위임 하나로 `prefs.getBoolean("is_logged_in", false)`를 `preferences.isLoggedIn`으로 바꿀 수 있다.

### provideDelegate — 위임 생성 시점에 개입

`provideDelegate`를 구현하면 프로퍼티가 클래스에 바인딩될 때(위임 인스턴스 생성 시점에) 로직을 실행할 수 있다.

```kotlin
class ValidatedDelegate<T>(private val value: T) {
    operator fun getValue(thisRef: Any?, property: KProperty<*>): T = value
}

class ValidatingDelegateProvider<T>(
    private val value: T,
    private val validator: (T) -> Boolean
) {
    operator fun provideDelegate(thisRef: Any?, property: KProperty<*>): ValidatedDelegate<T> {
        if (!validator(value)) {
            throw IllegalArgumentException(
                "프로퍼티 '${property.name}'의 초기값 '$value'가 유효하지 않음"
            )
        }
        return ValidatedDelegate(value)
    }
}

fun <T> validated(value: T, validator: (T) -> Boolean) =
    ValidatingDelegateProvider(value, validator)

// 사용
class Config {
    val port: Int by validated(8080) { it in 1024..65535 }
    val timeout: Int by validated(-1) { it > 0 }  // 객체 생성 시점에 예외 발생
}
```

`provideDelegate` 없이는 초기화 실패를 프로퍼티 접근 시점까지 발견하지 못한다. `provideDelegate`는 클래스 인스턴스화 시점에 즉시 검증할 수 있게 한다.

---

## 7. Java 디컴파일로 보는 실제 동작

Kotlin 코드가 JVM에서 어떻게 돌아가는지 이해하려면 Java 디컴파일 결과를 보는 게 가장 빠르다. IntelliJ에서 `Tools → Kotlin → Show Kotlin Bytecode → Decompile`로 확인할 수 있다.

### apply 디컴파일

```kotlin
// Kotlin
val sb = StringBuilder().apply {
    append("Hello")
    append(" World")
}
```

```java
// 디컴파일 결과 (인라이닝 후)
StringBuilder sb = new StringBuilder();
sb.append("Hello");
sb.append(" World");
// 람다 객체 생성 없음 — 완전히 인라이닝됨
```

### by lazy 디컴파일

```kotlin
// Kotlin
class Example {
    val computed: String by lazy { "expensive computation" }
}
```

```java
// 디컴파일 결과
public final class Example {
    // 위임 객체를 저장하는 backing field
    private final Lazy computed$delegate =
        LazyKt.lazy(() -> "expensive computation");

    public final String getComputed() {
        // getValue 호출로 변환됨
        return (String) computed$delegate.getValue();
    }
}
```

`by lazy`는 `Lazy<T>` 인터페이스 구현체를 backing field로 갖고, getter가 그 구현체의 `getValue()`를 호출하는 구조다. 프로퍼티 접근 `example.computed`는 실제로 `getComputed()`를 호출하고, `getComputed()`는 `Lazy.getValue()`를 통해 더블체크 락킹 로직에 진입한다.

### 커스텀 위임 디컴파일

```kotlin
// Kotlin
class Foo {
    var bar: String by StringDelegate()
}
```

```java
// 디컴파일 결과
public final class Foo {
    // 위임 객체 backing field
    private final StringDelegate bar$delegate = new StringDelegate();

    public final String getBar() {
        return bar$delegate.getValue(this, $$delegatedProperties[0]);
    }

    public final void setBar(String value) {
        bar$delegate.setValue(this, $$delegatedProperties[0], value);
    }

    // KProperty 메타데이터 배열
    private static final KProperty[] $$delegatedProperties = {
        Reflection.mutableProperty1(new MutablePropertyReference1Impl(Foo.class, "bar", ...))
    };
}
```

중요한 점: `KProperty` 배열은 클래스당 한 번 생성되는 정적(static) 배열이다. 위임 프로퍼티가 많다고 해도 메타데이터 오버헤드는 클래스 로딩 시 한 번뿐이다.

---

## 8. 극한 시나리오

### 시나리오 1: by lazy와 메모리 누수

```kotlin
// 위험한 코드 — Android Activity에서
class MainActivity : AppCompatActivity() {
    // Activity가 destroy될 때도 Lazy 홀더가 Activity 참조를 잡고 있을 수 있음
    val viewModel: MyViewModel by lazy {
        // viewModelStore는 Activity에 의존
        ViewModelProvider(this)[MyViewModel::class.java]
    }
}
```

이건 실제로는 안전하다 — `ViewModelProvider`가 적절히 처리하기 때문에. 진짜 위험한 패턴은 이것이다.

```kotlin
// 진짜 위험한 코드
object GlobalHolder {
    // Application보다 수명이 짧은 Context를 캡처
    val formattedDate: String by lazy {
        DateFormat.getDateTimeInstance().format(Date())
        // 이건 괜찮음. 하지만 아래처럼 Context를 캡처하면?
    }

    // Activity context를 singleton에 캡처하면 메모리 누수
    var cachedView: View? = null  // Activity.onDestroy 후에도 살아있음
}
```

`by lazy`의 initializer 람다가 외부 스코프의 참조를 캡처하는 경우, 그 참조의 수명이 해당 클래스의 수명보다 짧다면 메모리 누수가 발생한다. 특히 companion object나 object 싱글턴에 선언된 `by lazy`가 Activity나 Fragment 참조를 캡처할 때 위험하다.

```kotlin
// 해결책: WeakReference 사용
class CacheHolder(context: Context) {
    private val weakContext = WeakReference(context)
    val cache: Cache by lazy {
        val ctx = weakContext.get() ?: throw IllegalStateException("Context released")
        Cache.create(ctx.cacheDir)
    }
}
```

### 시나리오 2: 순환 참조로 인한 StackOverflow

```kotlin
// 컴파일은 되지만 런타임에 StackOverflowError
class A {
    val b: B by lazy { B(this) }
}

class B(val a: A) {
    val description: String by lazy {
        "B holds ${a.b.toString()}"  // a.b에 접근 → A의 lazy 재진입
    }
}

val a = A()
println(a.b.description)  // StackOverflowError!
```

`a.b`를 처음 접근하면 `B(a)`를 생성한다. `B.description`을 접근하면 `a.b`를 다시 접근한다. `a.b`의 lazy는 아직 초기화가 완료되지 않았는데(초기화 중) 다시 진입하려 하면 `SynchronizedLazyImpl`의 `synchronized(this)` 블록에서 데드락이 발생하거나, 재귀로 StackOverflow가 난다.

```kotlin
// 해결책: 순환 의존 제거 또는 지연 접근
class B(val a: A) {
    val description: String
        get() = "B holds ${a.b}"  // lazy 대신 매번 계산 (by lazy 제거)
}
```

### 시나리오 3: NONE 모드에서 멀티스레드

```kotlin
// 잘못된 코드 — 멀티스레드 환경에서 NONE 모드 사용
class ExpensiveService {
    val connection by lazy(LazyThreadSafetyMode.NONE) {
        DatabaseConnection.open()  // 네트워크 I/O
    }
}

// 동시에 두 스레드가 접근하면:
// Thread 1: connection 접근 → _value == UNINITIALIZED, 초기화 시작
// Thread 2: connection 접근 → _value == UNINITIALIZED (Thread 1 완료 전)
// → DatabaseConnection.open() 두 번 호출
// → 연결 하나 누수, 두 스레드가 서로 다른 connection 객체를 갖게 됨
```

`NONE`은 진짜 단일 스레드 환경(예: 안드로이드 메인 스레드에서만 접근하는 UI 관련 객체)이나 immutable 값의 캐싱에만 써야 한다.

### 시나리오 4: observable과 무한 루프

```kotlin
// 위험한 코드
var count: Int by Delegates.observable(0) { _, _, new ->
    count = new + 1  // observable 콜백 안에서 자기 자신을 수정
}
count = 1  // StackOverflowError
```

`observable` 콜백 안에서 같은 프로퍼티에 쓰면 콜백이 재귀적으로 호출되어 스택이 넘친다. 콜백은 반드시 부수 효과(로깅, UI 업데이트 등)에만 써야 하고, 같은 프로퍼티를 수정해서는 안 된다.

### 시나리오 5: 스코프 함수와 예외 전파

```kotlin
// let 체인에서 예외가 발생하면 어디서 잡히는가?
val result = try {
    user?.let { processUser(it) }  // processUser에서 RuntimeException 발생
         ?.let { sendEmail(it) }
         ?: "no user"
} catch (e: RuntimeException) {
    // let은 inline이므로 예외가 그냥 전파됨
    // try-catch가 정상적으로 잡음
    "error: ${e.message}"
}
```

`let`, `run`, `apply` 등 모든 스코프 함수는 `inline`이다. 람다 안의 예외는 포장(wrapping)되지 않고 그대로 전파된다. Java의 익명 클래스와 달리 `InvocationTargetException` 같은 래퍼가 생기지 않는다. 예외 처리 관점에서는 스코프 함수가 없는 코드와 동일하게 동작한다.

---

## 면접 포인트

### let과 run의 차이점은 무엇인가

두 함수의 반환값은 동일하다(람다의 마지막 표현식). 차이는 람다 안에서 수신 객체를 참조하는 방법이다. `let`은 `it`으로 파라미터처럼 접근하고, `run`은 `this`(생략 가능)로 멤버를 직접 호출한다. 실전 구분 기준: 객체의 멤버를 많이 호출해야 한다면 `run`(타이핑 감소), 객체를 하나의 값으로 변환하거나 null 체크와 함께 쓴다면 `let`이 의도를 더 명확히 드러낸다.

### apply와 also의 차이점은 무엇인가

둘 다 수신 객체를 반환한다는 점에서 같다. 차이는 람다 파라미터다. `apply`는 `this`로 수신 객체의 멤버를 직접 호출한다 — 객체 설정/초기화 블록에 적합하다. `also`는 `it`으로 접근한다 — 객체 자체를 건드리지 않는 부수 효과(로깅, 감사 기록 등)를 체인에 끼워 넣을 때 적합하다. 의미론적으로도 다르다: `apply`는 "이 객체에 이런 설정을 적용해"고, `also`는 "이 객체를 쓰면서 이것도 해"다.

### by lazy의 스레드 안전성을 설명하라

기본 모드인 `SYNCHRONIZED`는 더블체크 락킹 패턴으로 스레드 안전을 보장한다. `_value` 필드를 `@Volatile`로 선언해 CPU 캐시 일관성 문제를 방지하고, 첫 번째 체크(락 없이)와 두 번째 체크(락 안에서)를 통해 경쟁 조건을 방어한다. 초기화 후에는 synchronized 블록에 진입하지 않으므로 성능 저하가 없다. 단일 스레드 환경에서는 `LazyThreadSafetyMode.NONE`으로 동기화 오버헤드를 완전히 제거할 수 있다.

### 위임 프로퍼티는 내부적으로 어떻게 동작하는가

컴파일러가 프로퍼티의 getter/setter를 위임 객체의 `getValue`/`setValue` 호출로 변환한다. 위임 객체는 해당 클래스의 backing field로 저장된다. `KProperty` 메타데이터 배열은 클래스당 한 번 생성되는 정적 배열이므로 런타임 오버헤드는 최소화된다. `provideDelegate` 연산자를 구현하면 위임 객체 생성 시점(클래스 초기화 시점)에 추가 로직을 실행할 수 있다.

### 클래스 위임(by)과 상속의 차이는 무엇인가

상속은 `is-a` 관계로, 부모 클래스의 구현이 자식에 그대로 상속되며 부모-자식 간 강한 결합이 생긴다. 위임은 `has-a` 관계로, 내부에 구현 객체를 갖고 인터페이스 메서드를 포워딩한다. 결합이 느슨해 런타임에 위임 객체를 교체할 수 있다. Kotlin의 `by` 키워드는 인터페이스의 모든 메서드를 자동 포워딩하는 보일러플레이트를 제거한다. 원하는 메서드만 `override`로 재정의할 수 있다. Effective Java의 "상속보다 구성(Composition over Inheritance)" 원칙을 언어 레벨에서 지원하는 것이다.

### observable과 vetoable의 차이점은 무엇인가

`observable`은 값이 변경된 **후** 콜백이 호출된다. 콜백의 반환값은 없으며(Unit), 변경을 막을 수 없다. 로깅, 이벤트 발행, UI 업데이트에 적합하다. `vetoable`은 값이 변경되기 **전** 콜백이 호출된다. 콜백이 `Boolean`을 반환하며, `false`를 반환하면 변경이 취소되고 기존 값이 유지된다. 도메인 불변식 강제, 입력 유효성 검사에 적합하다.

---

## 정리

스코프 함수 5개를 한 문장으로 압축하면:

- `let` — 변환, null 안전 체이닝, `it`으로 접근, 람다 결과 반환
- `run` — 계산 블록, `this`로 접근, 람다 결과 반환
- `with` — 비확장 함수, `this`로 접근, 람다 결과 반환
- `apply` — 객체 설정, `this`로 접근, 수신 객체 반환
- `also` — 부수 효과, `it`으로 접근, 수신 객체 반환

위임 패턴의 핵심은 `getValue`/`setValue` 연산자다. `by lazy`는 더블체크 락킹으로 스레드 안전을 보장한다. 커스텀 위임은 `SharedPreferences`, DB 접근, 검증 로직 등을 프로퍼티 수준으로 끌어올려 코드 중복을 제거한다.

두 개념 모두 `inline` 함수와 컴파일러 코드 생성을 통해 런타임 오버헤드 없이 동작한다. 추상화 비용이 0에 가깝다는 게 Kotlin 언어 설계의 핵심 강점 중 하나다.
