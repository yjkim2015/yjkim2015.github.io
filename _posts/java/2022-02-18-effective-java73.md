---
title: 추상화 수준에 맞는 예외를 던지라 - Effective Java[73]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗 상위 계층에서는 저수준 예외를 잡아 자신의 추상화 수준에 맞는 예외로 바꿔 던져야 한다.

* 수행하려는 일과 관련 없어 보이는 예외가 튀어나오면 당황스러울 것이다.



1. 메서드가 저수준 예외를 처리하지 않고 **바깥으로 전파해버릴 때 종종 일어나는 일이다.**

   * 이것은 단순히 프로그래머를 당황시키는 데 그치지 않고, <span style="color:red;">내부 구현 방식을 드러내어 윗 레벨 API를 오염 시킨다.</span>

   

   * 다음 릴리스에서 구현 방식을 바꾸면 다른 예외가 튀어나와 기존 클라이언트 프로그램을 깨지게 할 수도 있는 것이다.

   

2. <span style="color:red;">이 문제를 피하려면</span> **상위 계층에서는 저수준 예외를 잡아 자신의 추상화 수준에 맞는 예외로 바꿔 던져야 한다.**

   * 이를 <span style="color:red;">예외 번역</span>이라 한다.




<hr>



##### 💎  예외 번역

```java
try {
    ... // 저수준 추상화를 이용한다.
} catch (LowerLevlException e) {
    // 추상화 수준에 맞게 번역한다.
    throw new HigherLevelException(...);
}
```



<br>



##### 💎 예외 번역 - AbstractSequentialList

* 아래의 예에서 수행한 예외 번역은 `List<E>` 인터페이스의 get 메서드 명세에 명시된 필수사항이다

```java
/**
* 이 리스트 안의 지정한 위치의 원소를 반환한다.
* @throws IndexOutOfBoundsException index가 범위 밖이라면,
*			즉 ({@code index < 0 || index >= sizeA()}) 이면 발생한다.
*/

public E get(int index) {
    ListIterator<E> i = listIterator(index);
    try {
		return i.next();
    } catch (NoSuchElementException e) {
        throw new IndexOutOfBoundsException("인덱스 : " + index);
    }
}
```

* **예외를 번역할 때, 저수준 예외가 디버깅에 도움이 된다면** <span style="color:red;">예외 연쇄를 사용하는게 좋다.</span>



* <span style="color:red;">예외 연쇄란</span> **문제의 근본 원인인 저수준 예외를 고수준 예외에 실어 보내는 방식이다.**
  * 그러면 **별도의 접근자 메서드(Throwable의 getCause 메서드)를 통해** <span style="color:red;">필요하면 언제든 저수준 예외를 꺼내 볼 수 있다.</span>



<hr>



##### 💎 예외 연쇄

```java
try {
    ... // 저수준 추상화를 이용한다.
} catch (LowerLevelException cause) {
    // 저수준 예외를 고수준 예외에 실어 보낸다. case
    throw new HigherLevelException(cause);
}
```

* 고수준 예외의 생성자는 **(예외 연쇄용으로 설계된) 상위 클래스의 생성자**에 이 '**원인**'을 건네주어, 최종적으로 **Throwable(throwable)** 생성자까지 건네지게 한다.



<br>

##### 💎 예외 연쇄용 생성자

```java
class HigherLevelException extends Exception {
    HigherLevelException(Throwable cause) {
        super(cause);
    }
}
```

* 대부분의 표준 예외는 **예외 연쇄용 생성자를 갖추고 있다.**



* 그렇지 않은 예외라도 **Throwable**의 **initCause** 메서드를 이용해 **'원인'을 직접 못박을 수 있다.**



* **예외연쇄는 문제의 원인을 (getCause 메서드로) 프로그램에서 접근**할 수 있게 해주며, **원인과 고수준 예외의 스택 추적 정보를 잘 통합**해준다.



<hr>



##### 🔗 무턱대고 예외를 전파하는 것 보다야 에외 번역이 우수한 방법이지만, 그렇다고 남용해서는 곤란하다.

* **가능하다면 저수준 메서드가 반드시 성공**하도록하여 아래 계층에서는 예외가 발생하지 않도록 하는 것이 **최선이다.**



* **때론 상위계층 메서드의 매개변수 값을 아래 계층 메서드로 건네기 전에 미리 검사하는 방법**으로 이 목적을 달성할 수 있다.



<hr>



##### 💎 아래 계층에서의 예외를 피할 수 없다면, 상위계층에서 그 예외를 조용히 처리하여 API 호출자에까지 전파하지 않는 방법이 있다.

* 차선책으로 **이 경우 발생한 예외는 java.util.logging 같은 적절한 로깅 기능을 활용하여 기록해두면 좋다.**



* 그렇게 해두면 <span style="color:red;">클라이언트 코드와 사용자에게 문제를 전파하지 않으면서도</span> **프로그래머가 로그를 분석해 추가 조치를 취할 수 있게 해준다.**





<hr>



> 아래 계층의 예외를 예방하거나 스스로 처리할 수 없고, 그 예외를 상위 계층에 그대로 노출하기 곤란하다면
>
> **예외 번역**을 사용하라.
>
> 
>
> 이때 **예외 연쇄**를 이용하면 상위 계층에는 맥락에 어울리는 고수준 예외를 던지면서 근본 원인도 함께 알려주어 오류를 분석하기에 좋다











```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

