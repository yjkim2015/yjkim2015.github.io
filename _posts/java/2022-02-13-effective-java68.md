---
title: 일반적으로 통용되는 명명 규칙을 따르라 - Effective Java[68]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗 자바의 명명 규칙은 크게 철자와 문법, 두 범주로 나뉜다.

* **철자 규칙**은 패키지, 클래스, 인터페이스, 메서드, 필드,타입 변수의 이름을 다룬다.

  * **이 규칙들은** <span style="color:red;">특별한 이유가 없는 한 반드시 따라야 한다.</span>

  

  * **철자 규칙**이나 **문법 규칙**을 <span style="color:red;">어기면</span> 다른 프로그래머들이 그 코드를 읽기 번거로울 뿐 아니라 다른 뜻으로 오해할 수도 있고 그로 인해 **오류까지 발생할 수 있다.**



<hr>



##### 💎  패키지와 모듈 이름은 <span style="color:red;">각 요소를 점(.)으로 구분하여 계층적으로 짓는다.</span>

* 요소들은 **모두 소문자 알파벳 혹은 (드물게) 숫자로 이뤄진다.**

  * **조직 바깥에서도 사용될 패키지라면** <span style="color:red;">조직의 인터넷 도메인 이름을 역순으로 사용한다.</span>

  

  * ex) **edu.cmu, com.google, org.eff식이다.**



* <span style="color:red;">예외적으로</span> 표준 라이브러리와 선택적 패키지들은 각각 **java**와 **javax**로 시작한다.
  * 도메인 이름을 패키지 이름의 접두어로 변환하는 자세한 규칙은 자바 언어 명세에 적혀 있다.



<hr>



##### 💎 패키지 이름의 나머지는 해당 패키지를 설명하는 하나 이상의 요소로 이뤄진다.

* **각 요소는 일반적으로** <span style="color:red;">8자 이하의 짧은 단어로 한다.</span>



* utilities보다는 util처럼 <span style="color:red;">의미가 통하는 약어를 추천한다.</span>



* **여러 단어로 구성된 이름**이라면 **awt**처럼 <span style="color:red;">각 단어의 첫 글자만 따서 써도 좋다.</span>
  * **요소의 이름은** <span style="color:red;">보통 한 단어 혹은 약어로 이뤄진다.</span>



<hr>



💎 **인터넷 도메인 이름 뒤에 요소만 붙인 패키지가 많지만,** <span style="color:red;">많은 기능을 제공하는 경우엔 계층을 나눠 더 많은 요소로 구성해도 좋다.</span>

* 예를 들어 **java.util**은 **java.util.concurrent.atomic**과 같이 그 밑에 **수많은 패키지를 가지고 있다.**
  * 자바가 패키지 계층에 관해 언어 차원에서 지원하는 건 거의 없지만, 어쨋든 <span style="color:red;">이처럼 하부의 패키지를 하위 패키지(subpackage)라 부른다.</span>



<hr>



💎  **열거 타입과 애너테이션을 포함해 클래스와 인터페이스의 이름은** <span style="color:red;">하나 이상의 단어로 이뤄지며, 각단어는 대문자로 시작한다(List, FutherTask 등)</span>

*  **여러 단어의 첫 글자만 딴 약자나** max, min처럼 <span style="color:red;">널리 통용되는 줄임말을 제외하고는 단어를 줄여 쓰지 않도록 한다.</span>

  * **약자의 경우** 첫 글자만 대문자로 할지 전체를 대문자로 할지는 살짝 논란이 있다고 한다.

  

  * 전체를 대문자로 쓰는 프로그래머도 있지만, 그래도 **첫 글자만 대문자로 하는 쪽이 훨씬 많다.**
    * ex) **HttpUrl**처럼 여러 약자가 혼합된 경우라도 각 약자의 시작과 끝을 명확히 알 수 있기 때문이다.



<hr>



##### 💎 <span style="color:red;">메서드와 필드이름은 첫 글자를 소문자로 쓴다는 점만 빼면</span> 클래스 명명 규칙과 같다.

* **첫 단어가 약자라면** 단어 전체가 소문자여야 한다.



* **단, '상수 필드'는 예외다.**

  * **상수 필드를 구성하는 단어는** <span style="color:red;">모두 대문자로 쓰며 단어 사이는 밑줄로 구분한다</span>

    * ex) **VALUES**, **NEGATIVE_INFINTY**

    

  * <span style="color:red;">상수 필드는 값이 불변</span>인 **static final** 필드를 말한다.

    * 달리 말하면 **static final** 필드의 타입이 **기본 타입**이나 **불변 참조 타입**이라면 **상수 필드에 해당한다**

    

    * **static final** 필드이면서 가리키는 **객체가 불변**이라면 비록 **그 타입은 가변이라도 상수 필드다.**

  

* **이름에 밑줄을 사용하는 요소로는** <span style="color:red;">상수 필드가 유일하다는 사실을 기억해두자.</span>



<hr>



##### 💎 지역변수에도 다른 멤버와 비슷한 명명 규칙이 적용된다.

* 단, 약어를 써도 좋다.

  * 약어를 써도 **그 변수가 사용되는 문맥에서 의미를 쉽게 유추**할 수 있기 때문이다.

  

  * **입력 매개변수도 지역변수의 하나다.**

  

  * 하지만 메서드 설명 문서에까지 등장하는 만큼 **일반 지역변수보다는 신경을 써야 한다.**



<hr>



##### 💎 타입 매개변수 이름은 보통 한 문자로 표현한다.

* 대부분은 다음의 다섯 가지 중 하나다.

  * **임의의 타입엔 <span style="color:red;">T</span> **

  

  * **컬렉션 원소의 타입은 <span style="color:red;">E</span>**

  

  * **맵의 키와 값에는 <span style="color:red;">K와 V</span>**

  

  * **예외에는 <span style="color:red;">X</span>**

  

  * **메서드의 반환 타입에는 <span style="color:red;">R</span>**



* 그 외에 임의 타입의 시퀀스에는 T, U, V 혹은 T1, T2, T3를 사용한다.



<hr>



##### 💎 철자 규칙을 기억하기 쉽도록 정리한 표

| 식별자 타입         | 예                                                           |
| ------------------- | ------------------------------------------------------------ |
| 패키지와 모듈       | **org.junit.jupiter.api**, **com.google.common.collect**     |
| 클래스와 인터페이스 | **Stream**, **FuterTask**, **LinkedHashMap**, **HttpClient** |
| 메서드와 필드       | **remove**, **groupingBy**, **getCrc**                       |
| 상수 필드           | **MIN_VALUUE**, **NEGATIVE_INFINITY**                        |
| 지역변수            | **i**, **denom**, **houseNum**                               |
| 타입 매개변수       | **T**, **E**, **K**, **V**, **X**, **R**, **U**, **V**, **T1**, **T2** |



<hr>



##### 💎 문법 규칙은 철자 규칙과 비교하면 더 유연하고 논란도 많다.

* 패키지에 대한 규칙은 따로 없다.

  * <span style="color:red;">객체를 생성할 수 있는 클래스(열거 타입 포함)의 이름은</span> **보통 단수 명수나 명사구를 사용한다**

  

  * ex) **Thread**, **PriorityQueue**, **ChessPiece**

  

*  <span style="color:red;">객체를 생성할 수 없는 클래스의 이름은</span> **보통 복수형 명사로 짓는다**

  * ex) **Collectors**, **Collections**

  

* 인터페이스 이름은 클래스와 똑같이 짓거나 <span style="color:red;">able혹은 ible로 끝나는 형용사로 짓는다.</span>

  * ex) **Collections**, **Comparator**, **Runnable**, **Iterable**, **Accessible**

  

* **애너테이션은** 워낙 다용하게 활용되어 지배적인 규칙이 없이 명사, 동사, 전치사, 형용사가 **두루 쓰인다**
  * ex) **BindingAnnotation**, **Inject**, **ImplementedBy**, **Singleton**



* **어떤 동작을 수행하는 메서드의 이름은** <span style="color:red;">동사나 (목적어를 포함한) 동사구로 짓는다</span>
  * ex) **append**, **drawImage**



* **boolean 값을 반환하는 메서드라면** <span style="color:red;">보통 is나 (드물게) has로 시작</span>하고 **명사나 명사구, 혹은 형용사로 기능하는 아무 단어나 구로 끝나도록 짓는다.**
  * ex) **isDigit**, **isProbablePrime**, **isEmpty**, **isEnabled**, **hasSiblings**



* **반환 타입이 boolean이 아니거나 해당 인스턴스의 속성을 반환하는 메서드의 이름은** <span style="color:red;">보통 명사, 명사구, 혹은 get으로 시작하는 동사구로 짓는다</span>

  * ex) **size**, **hashCode**, **getTime**

  

  * 처음 두 형태를 사용한 코드의 가독성이 더 좋다.

```java
if (car.speed() > 2 * SPEED_LIMIT) {
    generateAudibleAlert("경찰 조심하세요오!!");
}
```

* **get**으로 시작하는 형태는 주로 **자바빈즈** 명세에 뿌리를 두고 있다.

  * **자바빈즈는 재사용을 위한 컴포넌트 아키텍처의 초기 버전 중 하나**로, 최근의 도구 중에도 이 명명 규칙을 따르는 경우가 제법 많다.

  

  * 따라서 이런 도구와 어우러지는 코드를 작성한다면 이 규칙을 따라도 상관없다.

  

  * <span style="color:red;">한편</span> 클래스가 한 **속성의 게터와 세터를 모두 제공할 때도 적합한 규칙이다.**
    * 이런 경우라면 보통 **getAttribute**와 **setAttribute** 형태의 이름을 갖게 될 것이다.





<hr>



##### 💎 꼭 언급해둬야 할 특별한 메서드 이름 몇 가지

* <span style="color:red;">객체의 타입을 바꿔서, 다른 타입의 또 다른 객체를 반환하는 인스턴스 메서드의 이름은</span> **보통 toType 형태로 짓는다**

  * ex) **toString**, **toArray**

  

* <span style="color:red;">객체의 내용을 다른 뷰로 보여주는 메서드의 이름은</span> **asType 형태로 짓는다**

  * ex) **asList**

  

* <span style="color:red;">객체의 값을 기본 타입 값으로 반환하는 메서드의 이름은</span> **보통 typevalue 형태로 짓는다.**

  * ex) **intValue**

  

* <span style="color:red;">정적 팩터리의 이름은</span> 다양하지만 **from**, **of**, **valueOf**, **instance**, **getInstance**, **newInstance**, **getType**, **newType**을 <span style="color:red;">흔히 사용한다.</span>



<hr>



##### 💎 필드 이름에 관한 문법 규칙은 클래스, 인터페이스, 메서드 이름에 비해 덜 명확하고 덜 중요하다

* **API 설계를 잘 했다면** <span style="color:red;">필드가 직접 노출될 일이 거의 없기 때문이다.</span>



* **boolean 타입의 필드 이름은** <span style="color:red;">보통 boolean 접근자 메서드에서 앞 단어를 뺀 형태다.</span>
  * ex) initialized, composite



* 다른 타입의 필드라면 명사나 명사구를 사용한다.

  * ex) height, digits, bodyStyle

  

* 지역 변수 이름도 필드와 비슷하게 지으면 되나, 조금 더 느슨하다.





<hr>



> 표준 명명 규칙을 체화하여 자연스럽게 베어 나오도록 하자.
>
> 철자 규칙은 직관적이라 모호한 부분이 적은 데 반해, 문법 규칙은 더 복잡하고 느슨하다.
>
> 
>
> 자바 언에 명세의 말을 인용하자면 "오랫동안 따라온 규칙과 충돌한다면 그 규칙을 맹종해서는 안 된다"
>
> 상식이 이끄는대로 따르자.








```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

