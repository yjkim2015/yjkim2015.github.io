---
title: 클래스와 멤버의 접근 권한을 최소화하라
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---

**어설프게 설계된 컴포넌트와 잘 설계된 컴포넌트의 가장 큰 차이는 바로 클래스 내부 데이터와 내부 구현 정보를 외부 컴포넌트로부터 얼마나 잘 숨겼느냐이다.**

잘 설계된 컴포넌트는 모든 내부 구현을 완벽히 숨겨, 구현과 API를 깔끔하게 분리한다.

<hr>
**💎 어 근데 나 이거 어디서 많이 본 내용 같은데?**

자바를 배운 사람이라면 위 내용을 보았을때 기억 저편에서 떠오르는 개념이 한가지 있을 것이다.

그렇다. 그것은 바로 <code>캡슐화</code>, <code>정보은닉</code>이라고 하는 개념이며 소프트웨어 설계의 근간이 되는 원리이다.

<br>

이번 시간은 캡슐화가 얼마나 중요한지에 대해 알아볼 차례이다.

**우선 캡슐화의 장점에 대해 알아보자.**

* **시스템 개발 속도를 높인다.** 여러 컴포넌트를 개발할 수 있기 때문이다.
* **시스템 관리 비용을 낮춘다.** 각 컴포넌트를 더 빨리 파악하여 디버깅할 수 있고, 다른 컴포넌트로 교체하는 부담도 적기 때문이다.
* **정보 은닉 자체가 성능을 높여주지는 않지만, 성능 최적화에 도움을 준다.**
  완성된 시스템을 프로파일링해 최적화할 컴포넌트를 정한 다음, 다른 컴포넌트에 영향을 주지 않고 해당 컴포넌트만 최적화할 수 있기 떄문이다.

* **소프트웨어 재사용성을 높인다.** 외부에 거의 의존하지 않고 독자적으로 동작할 수 있는 컴포넌트라면 그 컴포넌트와 함께 개발되지 않은 낯선 환경에서도 유용하게 쓰일 가능성이 크기 떄문이다.
* **큰 시스템을 제작하는 난이도를 낮춰준다.** 시스템 전체가 완성되지 않은 상태에서도 개별 컴포넌트의 동작을 검증할 수 있기 때문이다.

흠... 솔직히 잘 모르겠다  크게 와닿지는 않는다..

<hr>
**다음으로 정보 은닉의 기본 원칙에 대해 알아보자.**

#### 🔗 모든 클래스와 멤버의 접근성을 가능한 한 좁혀야 한다.

자바는 정보 은닉을 위한 다양한 장치를 제공하며, 그 중 접근 제어 메커니즘은 <code>클래스</code>, <code>인터페이스</code>, <code>멤버</code>의 접근성을 명시한다. 

각 요소의 접근성은 그 요소가 선언된 위치와 <code>접근 제한자[private, protected, default, public]</code>로 정해진다. **이 접근 제한자를 제대로 활용하는 것이 정보 은닉의 핵심이다.**

<hr>
**💎public 일 필요가 없는 클래스의 접근 수준을 package-private로 바꾸는것은 매우 중요해!**

**(가장 바깥이라는 의미의) 톱레벨 클래스와 인터페이스에 부여할 수 있는 접근 수준은**

<code>package-private[default]</code>와 <code>public</code> 두 가지이다. 
톱레벨 클래스나 인터페이스를 <code>public</code>으로 선언하면 공개 <code>API</code>가 되며, <code>package-private</code>으로 선언하면 해당 패키지 안에서만 이용할 수 있다. 
**패키지 외부에서 쓸 이유가 없다면 <code>package-private</code>으로 선언하자.**

<br>

<code>public</code>으로 선언한다면 <code>API</code>가 되므로 하위 호환을 위해 영원히 관리해줘야하는 반면, 
<code>package-private</code>으로 선언하면 <code>API</code>가 아닌 <span style="color:red;">내부구현</span>이 되어 언제든 수정할 수 있다.

<hr>

<code>멤버(필드, 메서드, 중첩 클래스, 중첩 인터페이스)</code>에 부여할 수 있는 접근 수준은 네 가지다.

접근 범위가 좁은 것부터 순서대로 살펴보자.

* **private** : 멤버를 선언한 톱레벨 클래스에서만 접근할 수 있다.
* **package-private [default]** : 멤버가 소속된 패키지 안의 모든 크래스에서 접근할 수 있다.
  접근 제한자를 명시하지 않았을때 적용되는 패키지 접근 수준이다
  (단, 인터페이스의 멤버는 기본적으로 public이 적용된다.)
* **protected**: package-private의 접근 범위를 포함하며, 이 멤버를 선언한 클래스의 하위 클래스에서도 접근할 수 있다(제약이 조금 따른다.)

* **public** : 모든 곳에서 접근할 수 있다.

<hr>

#### 🔗 protected 멤버의 수는 적을수록 좋아!

<code>public</code> 클래스에서는 멤버의 접근 수준을 <code>package-private</code>에서 <code>protected</code>로 바꾸는 순간 그 멤버에 접근할 수 있는 대상 범위가 엄청나게 넓어진다. <code>public</code> 클래스의 <code>protected</code> 멤버는 공개 API이므로 영원히 지원돼야 한다. **또한 내부 동작 방식을 API문서에 적어 사용자에게 공개해야 할 수도 있다.**

따라서 protected 멤버의 수는 적을수록 좋다.

<hr>

**💎상위 클래스의 메서드를 재정의할 때는 그 접근 수준을 상위 클래스에서보다 좁게 설정 할 수 없어!!**

**이 제약은 상위 클래스의 인스턴스는 하위 클래스의 인스턴스로 대체해 사용할 수 있어야 한다는 규칙(<span style="color:red;">SOLID 중 리스코프 치환 원칙</span>)을 지키기 위해 필요하다.**

이 규칙을 어기면 하위 클래스를 컴파일할 때 오류가 난다. 클래스가 인터페이스를 구현하는건 이 규칙의 특별한 예로 볼 수 있고, 이 때 클래스는 인터페이스가 정의한 모든 메소드를 public으로 선언해야 한다.

<hr>

#### 🔗 public 클래스의 인스턴스 필드는 되도록 public이 아니어야 해!!

**필드가 가변 객체를 참조하거나, <code>final</code>이 아닌 인스턴스 필드를 <code>public</code>으로 선언하면 그 필드에 담을 수 있는 값을 제한할 힘을 잃게 된다**.
<br>

그 필드와 관련된 모든 것은 불변식을 보장할 수 없게 된다는 뜻이다. 
여기에 더해, 필드가 수정 될 때 (락 흭득 같은) 다른 작업을 할 수 없게 되므로 **<code>public</code> 가변 필드를 갖는 클래스는 일반적으로 스레드 세이프 하지 않다.**

<br>
심지어 필드가 final이면서 불변 객체를 참조하더라도 문제는 여전히 남는다. 내부구현을 바꾸고 싶어도 그 public 필드를 없애는 방식으로는 리팩토링을 할 수가 없게 된다.



<hr>

**💎항상 예외는 존재 하는법!  해당 클래스가 표현하는 추상 개념을 완성하는데 꼭 필요한 구성요소로써의 상수라면 public static final 필드로 공개해도 좋아!**

관례상 이런 상수의 이름은 대문자 알파벳으로 쓰며, 각 단어 사이에 밑줄(_) 을 넣는다.

**이런 필드는 반드시 기본 타입 값이나 불변 객체를 참조해야 한다.**
[ 가변 객체 참조하면 큰일나!!  참조된 가변 객체는 수정 될 수 있단말야!! ]

<hr>

**💎클래스에서 public static final 배열 필드를 두거나 이 필드를 반환하는 접근자 메서드를 제공하면 안돼!!**

길이가 0이 아닌 배열은 모두 <span style="color:red;">변경이 가능</span>하니 <span style="color:red;">주의</span>해야 한다. 이런 필드나 접근자를 제공한다면 클라이언트에서 그 배열의 내용을 수정할 수 있게 된다. 

다음의 코드를 통해 보안 허점을 살펴보자.

```java
public static final Thing[] VALUES = {...};
```

어떤 IDE가 생성하는 접근자는 private 배열 필드의 참조를 반환하여 이와 같은 문제를 일으키니 주의해야한다.



**💎해결책은 두가지가 있어 ! 클라이언트가 뭘 원하는지에 따라 사용해!!**

* **public 배열을 private으로 변경하고 public 불변 리스트를 추가하는 방법** 

```java
private static final Thing[] PRIVATE_VALUES = {...}
public static final List<Thing> VALUES =
	Collections.unmodifiableList(Arrays.asList(PRIVATE_VALUES));
```

* **public 배열을 private으로 만들고 그 복사본을 반환하는 public 메소드를 추가하는 방법(방어적 복사)**

```java
private static final Thing[] PRIVATE_VALUES = {...}
public static final Thing[] values() {
	return PRIVATE_VALUES.clone();
}
```



<hr>

#### 🔗 자바9 모듈 시스템의 도입

자바 9에서는 모듈 시스템이라는 개념이 도입되면서 두 가지 암묵적 접근 수준이 추가되었다. 패키지가 클래스들의 묶음이듯, 모듈은 패키지들의 묶음이다.

- 모듈은 자신에 속하는 패키지 중 공개(export)할 것들을 (관례상 module-info.java 파일에) 선언한다.
- protected 혹은 public 멤버라도 해당 패키지를 공개하지 않았다면 모듈 외부에서는 접근할 수 없다.
- 물론 모듈 안에서는 exports로 선언했는지 여부에 아무런 영향도 받지 않는다.

 <br>

모듈 시스템을 활용하면 클래스에 외부에 공개하지 않으면서도 같은 모듈을 이루는 패키지 사이에서는 자유롭게 공유할 수 있다. 위에서 이야기한 두 가지 암묵적 접근 수준은 바로 이 숨겨진 패키지 안에 있는 public 클래스의 public 혹은 protected 멤버와 관련이 있다.

- 이 암묵적 접근 수준들은 각각 public 수준과 protected 수준과 같으나, 그 효과가 모듈 내부로 한정되는 변종인 것이다.
- 이런 형태로 공유해야 하는 상황은 흔하지 않다. 그래야 하는 상황이 벌어지더라도 패키지들 사이에서 클래스들을 재배치하면 대부분 해결된다.

 <br>

앞서 다룬 4개의 기존 접근 수준과 달리, 모듈에 적용되는 새로운 두 접근 수준은 상당히 주의해서 사용해야 한다.

- 모듈의 JAR 파일을 자신의 모듈 경로가 아닌 애플리케이션의 클래스패스(classpath)에 두면 그 모듈 안의 모든 패키지는 마치 모듈이 없는 것처럼 행동한다.
- 즉, 모듈이 공개했는지 여부와 상관없이, public 클래스가 선언한 모든 public 혹은 protected 멤버를 모듈 밖에서도 접근할 수 있게 된다.
- 새로 등장한 이 접근 수준을 적극 활용한 예가 바로 JDK 그 자체다. 자바 라이브러리에서 공개하지 않은 패키지들은 해당 모듈 밖에서는 절대로 접근할 수 없다.

 



> 프로그램 요소의 접근성은 가능한 한 최소한으로 하라. 꼭 필요한 것만 골라 최소한의 public API를 설계하자.
>
> 그 외에는 클래스, 인터페이스, 멤버가 의도치 않게 API로 공개 되는 일이 없도록 해야 한다.
>
> public 클래스는 상수용 public static final 필드 외에는 어떠한 public 필드도 가져서는 안 된다.
>
> public static final 필드가 참조하는 객체가 불변인지 확인하자.



```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```
