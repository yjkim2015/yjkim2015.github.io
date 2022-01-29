---
title: 매개변수가 유효한지 검사하라 - Effective Java[49]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗 오류는 가능한 한 빨리 (발생한 곳에서) 잡아야한다는 일반 원칙의 한 사례

* 메서드와 생성자 대부분은 입력 **매개변수의 값이 특정 조건을 만족하기를 바란다.**

  * ex) 인덱스 값은 음수이면 안 되며,  객체 참조는 null이 아니어야 하는 식이다.

  

  * 이런 제약은 반드시 문서화해야 하며 메서드 몸체가 시작되기 전에 검사해야 한다.



* <span style="color:red;">오류를 발생한 즉시 잡지 못하면</span> 해당 오류를 감지하기 어려워지고, 감지하더라도 오류의 발생 지점을 찾기 어려워진다.



<hr>



##### 💎 매개변수 검사를 제대로 하지 못하면 생기는 몇 가지 문제

* **메서드 몸체가 실행되기 전에 매개변수를 확인한다면** 잘못된 값이 넘어왔을 때 **즉각적이고 깔끔한 방식으로 예외를 던질 수 있다.** 



* 매개변수 검사를 제대로 하지 못하면 다음과 같이 몇 가지 문제가 생길 수 있다.

  * 첫 번째, 메서드가 수행되는 **중간에 모호한 예외를 던지며 실패**할 수 있다.

    * <span style="color:red;">더 나쁜 상황</span>은 **메서드가 잘 수행되지만 잘못된 결과를 반환**할 때다.

    

    * <span style="color:red;">한층 더 나쁜 상황</span>은 메서드는 문제없이 수행됐지만, **어떤 객체를 이상한 상태로 만들어놓아서 미래의 알수 없는 시점에 이 메서드와는 관련 없는 오류를 낼 때다.**
      * 다시 말해 <span style="color:red;">매개변수 검사에 실패하면 실패 원자성을 어기는 결과</span>를 낳을 수 있다.



<hr>



##### 💎 public과 protected 메서드는 매개변수 값이 잘못됐을 때 던지는 예외를 문서화해야 한다

* @throws 자바독 태그를 사용하면 된다.

  * 보통은 **IllegalArgumentException**, **IndexOutOfBoundsException**, **NullPointerException** 중 하나가 될 것이다.

  

*  매개변수의 제약을 문서화한다면 <span style="color:red">그 제약을 어겼을 때 발생하는 예외도 함께 기술해야 한다.</span>

  * 이런 간단한 방법으로 **API 사용자가 제약을 지킬 가능성을 크게 높일 수 있다.**



<hr>



💎 **문서화의 전형적인 예**

```java
/**
* (현재 값 mod m) 값을 반환한다. 이 메서드는
* 항상 음이 아닌 BigInteger를 반환한다는 점에서 remainder 메서드와 다르다.
* 
* @param m 계수(양수여야 한다.)
* @return 현재 값 mod m
* @throws ArithmeticException m이 0보다 작거나 같으면 발생한다.
*/

public BigInteger mod(BigInteger m) {
    if (m.signum() <= 0) {
        throw new ArithmeticException("계수(m)는 양수여야 합니다. " + m);
    }
    ...
}
```

* 이 메서드는 **m**이 **null**이면 **m.signum()** 호출 때 **NullPointerException**을 던진다.

  * 그런데 "**m**이 **null** 일 때 **NullPointerException을 던진다"라는 말은** **메서드 설명 어디에도 없다.**
  * 그 이유는 **이 설명을 (개별 메서드가 아닌) BigInteger 클래스 수준에서 기술**했기 때문이다.

  

* **클래스 수준 주석**은 그 클래스의 모든 public 메서드에 적용되므로 각 메서드에 일일이 기술하는 것보다 **훨씬 깔끔한 방법이다.**

  * **@Nullable**이나 이와 비슷한 애너테이션을 사용해 **특정 매개변수는 null이 될 수 있다고 알려줄 수도 있지만,** <span style="color:red;">표준적인 방법은 아니다</span>. 그리고 같은 목적으로 사용 할 수 있는 애너테이션도 여러 가지다.

  

<hr>



💎 **자바 7에 추가된 java.util.Objects.requireNonNull 메서드는 유연하고 사용하기도 편하다.**

* 더 이상 null 검사를 수동으로 하지 않아도 된다.

 

* 원하는 예외 메시지도 지정할 수 있다.



* 또한 입력을 그대로 반환하므로 값을 사용하는 동시에 null 검사를 수행할 수 있다.











```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

