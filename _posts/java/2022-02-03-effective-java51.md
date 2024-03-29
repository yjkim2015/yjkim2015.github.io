---
title: 메서드 시그니처를 신중히 설계하라 - Effective Java[51]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗  메서드 이름을 신중히 짓자

* <span style="color:red;">항상 표준 명명 규칙을 따라야 한다.</span>



* 이해할 수 있고, 같은 패키지에 속한 다른 이름들과 **일관되게 짓는 게 최우선 목표**다.

  * 그 다음 목표는 개발자 커뮤니티에서 널리 받아들여지는 이름을 사용하는 것이다.

  

* **긴 이름은 피하자.**

  * 애매하면 자바 라이브러리의 API 가이드를 참조하라.

  

  * 자바 라이브러리가 워낙 방대하나 보니 일관되지 않은 이름도 제법 많지만 대부분은 납득할 만한 수준이다.

  

<hr>


##### 🔗 편의 메서드를 너무 많이 만들지 말자.

* 모든 메서드는 각각 자신의 소임을 다해야 한다.

  * 메서드가 너무 많은 클래스는 익히고, 사용하고, 문서화하고, 테스트하고, 유지보수하기 어렵다.

  

* 인터페이스도 마찬가지다.

  * 메서드가 너무 많으면 이를 구현하는 사람과 사용하는 사람 모두를 고통스럽게 한다.

  

  * 클래스나 인터페이스는 자신의 각 기능을 완벽히 수행하는 메서드로 제공해야 한다.

  

  * **아주 자주 쓰일 경우에만 별도의 약칭 메서드**를 두기 바란다.

  

* **확신이 서지 않으면 만들지 말자.**



<hr>

##### 🔗 매개변수 목록은 짧게 유지하자.

* 4개 이하가 좋다.
  * 일단 4개가 넘어가면 매개변수를 전부 기억하기가 쉽지 않다.



* **같은 타입의 매개변수 여러 개가 연달아 나오는 경우**가 <span style="color:red;">특히 해롭다.</span>

  * 사용자가 매개변수 순서를 기억하기 어려울뿐더러, 실수로 순서를 바꿔 입력해도 그대로 컴파일되고 실행된다.

  

  * <span style="color:red;">단지 의도와 다르게 동작할 뿐이다.</span>

<hr>



##### 🔗 과하게 긴 매개변수 목록을 짧게 줄여주는 기술 세 가지

##### 💎첫 번째, 여러 메서드로 쪼갠다. 

* 쪼개진 메서드 각각은 원래 매개변수 목록의 부분집합을 받는다.



* 잘못하면 메서드가 너무 많아질 수 있지만, **직교성을 높여 오히려 메서드 수를 줄여주는 효과도 있다.**

  *  java.util.List 인터페이스가 좋은 예이다.  리스트에서 주어진 원소의 인덱스를 찾아야 하는데, 전체 리스트가 아니라 **지정된 범위의 부분리스트에서의 인덱스를 찾는다고 해보자.**

  

  * 이 기능을 하나의 메서드로 구현하려면 **'부분리스트의 시작', '부분리스트의 끝', '찾을 원소'까지 총 3개의 매개변수가 필요**하다.

  

  * <span style="color:red;">그런데</span> List는 그 대신 **부분리스트를 반환하는 subList 메서드**와 **주어진 원소의 인덱스를 알려주는 indexOf 메서드를 별개로 제공**한다.

  

  * subList가 반환한 부분리스트 역시 완벽한 List이므로 **두 메서드를 조합하면 원하는 목적을 이룰 수 있다.**

  

  * <span style="color:red;">결과적으로 강함과 유연함이 절묘하게 균형을 이룬 API가 만들어진 것이다.</span>



<hr>

##### 💎 두 번째, 매개변수 여러 개를 묶어주는 도우미 클래스를 만드는 것이다.

* 일반적으로 이런 도우미 클래스는 **정적 멤버 클래스로 둔다.**



* 특히 잇따른 매개변수 몇 개를 <span style="color:red;">독립된 하나의 개념으로 볼 수 있을 때 추천하는 기법이다.</span>

  * ex) 카드 게임을 클래스로 만든다고 해보자.

  

  * 그러면 메서드를 호출할 때 카드의 숫자(rank)와 무늬(suit)를 뜻하는 **두 매개변수를 항상 같은 순서로 전달할 것이다.**

    

  * <span style="color:red;">따라서</span> 이 둘을 묶는 도우미 클래스를 만들어 하나의 매개변수로 주고받으면 **API**는 물론 클래스 내부 구현도 깔끔해질 것이다.



<hr>

##### 💎 세 번째, 객체 생성에 사용한 빌더 패턴을 메서드 호출에 응용

* 이 기법은 **매개변수가 많을 때**, <span style="color:red;">특히 그 중 일부는 생략해도 괜찮을 때 도움이 된다.</span>



* <span style="color:red;">먼저 모든 매개변수를 하나로 추상화한 객체를 정의하고</span>, 클라이언트에서 이 객체의 세터(setter) 메서드를 호출해 필요한 값을 설정하게 하는 것이다.

  * 이때 각 세터 메서드는 **매개변수 하나 혹은 서로 연관된 몇 개만 설정**하게 한다.

  

  * 클라이언트는 먼저 필요한 매개변수를 다 설정한 다음, execute 메서드를 호출해 앞서 설정한 매개변수들의 유효성을 검사한다.

  

  * 마지막으로, 설정이 완료된 객체를 넘겨 원하는 계산을 수행한다.



<hr>



##### 🔗 매개변수의 타입으로는 클래스보다는 인터페이스가 더 낫다

* **매개변수로 적합한 인터페이스가 있다면 (이를 구현한 클래스가 아닌) 그 인터페이스를 직접 사용하자.**

  * ex) 메서드에 HashMap을 넘길 일은 전혀 없다. 

  

  * 대신 Map을 사용하자. 그러면 HashMap뿐 아니라 TreeMap, ConcurrentHashMap, TreeMap의 부분맵 등 어떤 Map 구현체도 인수로 건넬 수 있다.

  

  * 심지어 아직 존재하지 않는 Map도 가능하다.

  

* **인터페이스 대신 클래스를 사용하면 클라이언트에게 특정 구현체만 사용하도록 제한하는 꼴이며**, 혹시라도 입력 데이터가 다른 형태로 존재한다면 명시한 특정 구현체의 객체로 옮겨 담느라 비싼 복사 비용을 치러야 한다.



<hr>



##### 🔗 boolean보다는 원소 2개짜리 열거 타입이 낫다

* 메서드 이름상 boolean을 받아야 의미가 더 명확할 때는 예외다.



* 열거 타입을 사용하면 **코드를 읽고 쓰기가 더 쉬워진다.**

  * 나중에 선택지를 추가하기도 쉽다.

  

  * 예를들어 다음은 화씨온도(Fahrenheit)와 섭씨온도(Celsius)를 원소로 정의한 열거 타입이다.

    ```java
    public enum TemperatureScale {FAHRENHEIT, CELSIUS}
    ```

  * 온도계 클래스의 정적 팩터리 메서드가 이 열거 타입을 입력받아 적합한 온도계 인스턴스를 생성해준다고 해보자.

  

  * 확실히 **Therometer.newInstance(true)**보다는 **Thermometer.newInstance(TemperatureScale.CELSIUS)**가 <span style="color:red;">하는 일을 훨씬 명확히 알려준다.</span>

  

  * 나중에 캘빈온도도 지원해야 한다면, **Thermometer**에 또 다른 정적 메서드를 추가할 필요 없이 **TemperatureScale** 열거 타입에 캘빈온도(**KELVIN**)를 추가하면 된다.

  

  * <span style="color:red;">또한</span>, 온도 단위에 대한 의존성을 **개별 열거 타입 상수의 메서드 안으로 리팩터링해 넣을 수도 있다.** 
    * ex) double 값을 받아 섭씨온도로 변환해주는 메서드를 열거 타입 상수 각각에 정의해 둘수도 있다.



```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

