---
title: 예외는 진짜 예외 상황에만 사용하라 - Effective Java[69]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗 예외를 사용한 반목문의 해악

* 언젠가 운이 없다면 다음과 같은 코드와 마주칠지도 모른다.

<br>

##### 💎 예외를 완전히 잘못 사용한 예 - 따라하지 말 것!

```java
try {
    int i = 0;
    while(true) {
        range[i++].climb();
    }catch (ArrayIndexOutOfBoundsException e) {
        
    }
}
```

* 위 코드는 배열의 원소를 순회하는데, 직관적이지 않을 뿐 더러 아주 끔찍한 방식으로 하고 있다.
  * 무한루프를 돌다가 배열의 끝에 도달해 **ArrayIndexOutOfBoundsException**이 발생하면 끝을 내는 것이다.



* 아래와 같이 **표준적인 관용구**대로 작성했다면 모든 자바 프로그래머가 곧바로 이해했을 것이다.

```java
for (Mountain m : range) {
    m.climb();
}
```



<hr>



##### 💎 굳이 예외를 써서 루프를 종료한 이유를 추측해보자

* Maybe... Something... 잘못된 추론을 근거로 성능을 높여보려 한 것일것일것이다.

  * **JVM**은 배열에 접근할 때마다 경계를 넘지 않는지 검사하는데, 일반적인 반복문도 배열 경계에 도달하면 종료한다.

  

  * **따라서** 이 검사를 반복문에도 명시하면 같은 일이 중복되므로 하나를 생략한 것이다.



* <span style="color:red;">하지만</span>, **세 가지 면**에서 <span style="color:red;">잘못된 추론</span>이다.

  * **첫 번째**, <span style="color:red;">예외는 예외 상황에 쓸 용도로 설계</span>되었으므로 **JVM 구현자 입장에서는 명확한 검사만큼 빠르게 만들어야 할 동기가 약하다**(최적화에 별로 신경 쓰지 않았을 가능성이 크다).

  

  * **두번째**, 코드를 try-catch 블록 안에 넣으면 JVM이 적용할 수 있는 최적화가 제한된다.

  

  * **세 번째**, 배열을 순회하는 표준 관용구는 앞서 걱정한 중복 검사를 수행하지 않는다. 
    * JMV이 알아서 최적화해 없애준다.



* **실상은 예외를 사용한 쪽이** <span style="color:red;">표준 관용구보다 훨씬 느리다.</span>



<hr>


##### 💎 예외를 사용한 반복문의 해악은 코드르 헷갈리게하고 성능을 떨어뜨리는데서 끝나지 않는다.

* <span style="color:red;">심지어 제대로 동작하지 않을 수도 있다.</span>
  * 반복문 안에 버그가 숨어 있다면 흐름 제어에 쓰인 예외가 이 버그를 숨겨 디버깅을 훨씬 어렵게 할 것이다.



* 반복문의 몸체에서 호출한 메서드가 내부에서 관련 없는 배열을 사용하다가 **ArrayIndexOutOfBoundsException**을 일으켰다고 가정해보자.

  * **표준 관용구였다면** 이 버그는 예외를 잡지 않고 (스택 추적 정보를 남기고) 해당 스레드를 즉각 종료시킬 것이다.

  

  * <span style="color:red;">반면</span>, **예외를 사용한 반복문은** 버그 때문에 발생한 **엉뚱한 예외를 정상적인 반복문 종료 상황으로 오해**하고 넘어간다.



<hr>



##### 🔗 절대로 예외는 일상적인 제어 흐름용으로 쓰여선 안 된다.

* 더 일반화해 이야기하면 **표준적이고 쉽게 이해되는 관용구를 사용하고**, <span style="color:red;">성능 개선을 목적으로 과하게 머리를 쓴 기법은 자제하라.</span>

  * 실제로 성능이 좋아지더라도 자바 플랫폼이 꾸준히 개선되고 있으니 최적화로 얻은 상대적인 성능 우위가 오래가지 않을 수 있다.

  

  * <span style="color:red;">반면</span> 과하게 영리한 기법에 **숨겨진 미묘한 버그의 폐해**와 **어려워진 유지보수 문제**는 **계속 이어질 것이다.**



<hr>



##### 💎 잘 설계된 API라면 클라이언트가 정상적인 제어 흐름에서 예외를 사용할 일이 없게 해야 한다.

* **특정 상태에서만 호출할 수 있는** <span style="color:red;">'상태 의존적' 메서드</span>를 제공하는 클래스는  <span style="color:red;">'상태 검사' 메서드</span>도 **함께 제공해야 한다.**

  * **Iterator** 인터페이스의 **next**와 **hasNext**가 각각 **상태 의존적 메서드**와 **상태 검사 메서드**에 해당한다.

  

  * **별도의 상태 검사 메서드** 덕분에 다음과 같은 표준 for 관용구를 사용할 수 있다
    * (**for-each**도 내부적으로 **hasNext**를 사용한다.)

```java
for (Iterator<Foo> i = collection.iterator(); i.hasNext(); ) {
    Foo foo = i.next();
    ...
}
```

* <span style="color:red;">Iterator가 hasNext를 제공하지 않았다면</span> 아래와 같이 그 일을 클라이언트가 대신해야만 했다.



```java
//컬렉션을 이런 식으로 순회하지 말 것!
try {
	Iterator<Foo> i = collection.iterator();
    while(true) {
        Foo foo = i.next();
        ...
    }
    catch (NoSuchElementExpceiton e) {
        
    }
}
```

* 위 코드 처럼 **반복문에 예외를 사용하면** 장황하고 헷갈리며 속도도 느리고, 엉뚱한 곳에서 발생한 버그를 숨기기도 한다.



<hr>



##### 💎 상태 검사 메서드 대신 사용할 수 있는 선택지도 있다.

* <span style="color:red;">올바르지 않은 상태일 때</span> **빈 옵셔널 혹은 null 같은 특수한 값을 반환하는 방법이다.**



<hr>



##### 💎 상태 검사 메서드, 옵셔널, 특정 값 중 하나를 선택하는 지침

* <span style="color:red;">외부 동기화 없이 여러 스레드가 동시에 접근할 수 있거나 외부 요인으로 상태가 변할 수 있다면</span> **옵셔널이나 특정 값을 사용한다.**
  * 상태 검사 메서드와 상태 의존적 메서드 호출 사이에 **객체의 상태가 변할 수 있기 때문이다.**



* <span style="color:red;">성능이 중요한 상황에서 상태 검사 메서드가 상태 의존적 메서드의 작업 일부를 중복 수행한다면 </span>**옵셔널이나 특정 값을 선택한다.**



* <span style="color:red;">다른 모든 경우엔</span> **상태 검사 메서드 방식이 조금 더 낫다고 할 수 있다.**

  * 가독성이 살짝 더 좋고, 잘못 사용했을 때 발견하기가 쉽다.

  

  * **상태 검사 메서드 호출을 깜빡 잊었다면** <span style="color:red;">상태 의존적 메서드가 예외를 던져 버그를 확실히 드러낼 것이다.</span>

  

  * <span style="color:red;">반면</span> 특정 값은 검사하지 않고 지나쳐도 발견하기가 어렵다.(옵셔널에는 해당하지 않는 문제다.)



<hr>



> 예외는 예외 상황에서 쓸 의도로 설계되었다.
>
> 정상적인 제어 흐름에서 사용해서는 안 되며, 이를 프로그래머에게 강요하는 API를 만들어서도 안 된다.








```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

