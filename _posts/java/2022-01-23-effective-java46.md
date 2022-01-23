---
title: 스트림에서는 부작용 없는 함수를 사용하라 - Effective Java[46]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 스트림은 함수형 프로그래밍에 기초한 패러다임이다

* 스트림은 처음 봐서는 이해하기 어려울 수 있다.

  * 원하는 작업을 스트림 파이프 라인으로 표현하는 것조차 어려울지 모른다.

  

  * 성공하여 프로그램이 동작하더라도 장점이 무엇인지 쉽게 와 닿지 않을 수도 있다.



* 스트림은 그저 또 하나의 **API**가 아닌, 함수형 프로그래밍에 기초한 **패러다임**이기 때문이다.



* 스트림이 제공하는 표현력, 속도, 병렬성을 얻으려면 API는 말할 것도 없고 이 패러다임까지 함께 받아들여야 한다.



<hr>



##### 🔗 스트림 패러다임의 핵심 

*  **스트림 패러다임의 핵심**은 **계산을 일련의 변환으로 재구성** 하는 부분이다

  * 이때 각 변환 단계는 가능한 한 이전 단계의 결과를 받아 처리하는 **순수 함수**여야 한다.

  

  * **순수 함수**란 **오직 입력만이 결과에 영향을 주는 함수**를 말한다.

  

  * 다른 가변 상태를 참조하지 않고, 함수 스스로도 다른 상태를 변경하지 않는다.

  

  * 이렇게 하려면 스트림 연산에 건네는 함수 객체는 보두 부작용이 없어야 한다.

  

* 다음은 주위에서 종종 볼 수 있는 스트림 코드로, 텍스트 파일에서 단어별 수를 세어 빈도표로 만드는 일을 한다.

<br>



💎 **스트림 패러다임을 이해하지 못한 채 API만 사용했다 - 따라 하지 말 것!**

```java
Map<String, Long> freq = new HashMap<>();
try (Stream<String> words = new Scanner(file).tokens()) {
    words.forEach(word -> {
        freq.merge(word.toLowerCase(), 1L, Long::sum);
    })
}
```

* **위 코드는** 스트림, 람다, 메서드 참조를 사용했고, 결과도 옳지만 <span style="color:red;">절대 스트림 코드라 할 수 없다.</span>

  * 스트림 코드를 가장한 반복적 코드다.

  

  * 스트림 API의 이점을 살리지 못하여 같은 기능의 반복적 코드보다 길고, 읽기 어렵고, 유지보수에도 좋지 않다.

  

* 이 코드의 **모든 작업이 종단 연산인 forEach에서 일어나는데**, 이때 외부 상태(빈도표)를 수정하는 람다를 실행하면서 문제가 생긴다.

  * **forEach**가 그저 스트림이 수행한 연산 결과를 보여주는 일 이상을 하 것을 보니 나쁜 코드 일 것 같은 냄새가 난다.



<hr>



💎 **스트림을 제대로 활용해 빈도표를 초기화한다.**

```java
Map<String, Long> freq;
try (Stream<String> words = new Scanner(file).tokens()) {
    freq = words.collect(groupingBy(String::toLowerCase, counting()));
}
```

* 앞의 코드와 같은 일을 하지만, 이번엔 스트림 API를 제대로 사용했다.

  * 또한 짧고 명확하다.

  

  * **스트림의 forEach연산은** 종단 연산 중 기능이 가장 적고 **가장 '덜' 스트림답다.**

  

  * 대놓고 반복적이라서 병렬화할 수도 없다.

  

* **forEach 연산은 스트림 계산 결과를 보고할 때만 사용하고, 계산하는 데는 쓰지 말자.**



<hr>



##### 🔗 수집기 (collector)

* 스트림을 사용하려면 꼭 배워야하는 새로운 개념이다.

  * 수집기가 생성하는 객체는 일반적으로 컬렉션이며, 그래서 "**collector**"라는 이름을 쓴다.

  

  * 수집기를 사용하면 스트림의 원소를 손쉽게 컬렉션으로 모을 수 있다.



* 수집기는 다음과 같이 총 세 가지다.

  * toList() - 리스트를 반환

    

  * toSet() - 집합을 반환

  

  * toCollection(collectionFactory) - 프로그래머가 지정한 컬렉션타입 반환



<br>



💎 빈도표에서 가장 흔한 단어 10개를 뽑아내는 파이프라인

```java
List<String> topTen = freq.keySet().stream()
    .sorted(comparing(freq::get).reversed())
    .limit(10)
    .collect(toList());

//toList()는 Collectors의 메서드다.
//이처럼 Collectors의 멤버를 정적 임포트하여 쓰면 스트림 파이프라인 가독성이 좋아져,
//흔히들 이렇게 사용한다.
```

* 위 코드에서 어려운 부분은 sorted에 넘긴 비교자, 즉 comparing(freq::get).reversed()뿐이다.

  * comparing 메서드는 키 추출 함수를 받는 비교자 생성 메서드다.

  

  * 그리고 한정적 메서드 참조이자, 여기서 키 추출 함수로 쓰인 freq::get은 입력받은 단어를 빈도표에서 찾아 그 빈도를 반환한다.

  

  * 다음으로 가장 흔한 단어가 위로 오도록 역순으로 정렬한다.



<hr>



##### 🔗 Collectors 메서드



💎 **가장 간단한 맵 수집기 - toMap(keyMapper, valueMapper)**

* 스트림 원소를 키에 매핑하는 함수와 값에 매핑하는 함수를 인수로 받는다.



* toMap 수집기를 사용하여 문자열을 열거 타입 상수에 매핑

```java
private static final Map<String, Operation> stringToEnum = 
    Stream.of(values()).collect(toMap(Object::toString, e -> e));
```

* 이 간단한 **toMap** 형태는 **스트림의 각 원소가 고유한 키에 매핑**되어 있을 때 **적합하다.**
  * **스트림 원소 다수가 같은 키를 사용한다면** 파이프라인이 **IllegalStateException**을 던지며 종료될 것이다.



* 더 복잡한 형태의 **toMap**이나 **groupingBy**는 이런 충돌을 다루는 **다양한 전략을 제공**한다.

  * ex) **toMap**에 키 매퍼와 값 매퍼는 물론 **병합(merge) 함수까지 제공**할 수 있다.

  

  * 병합 함수의 형태는 BinaryOperator<U>이며, 여기서 U는 해당 맵의 값 타임이다.

  

  * 같은 키를 공유하는 값들은 이 병함 함수를 사용해 기존 값에 합쳐진다.
    * ex) 병합 함수가 곱셈이라면 키가 같은 모든 값을 곱한 결과를 얻는다.

<br>



💎 **각 키와 해당 키의 특정 원소를 연관 짓는 맵을 생성하는 수집기**

* 인수를 3개를 받는 **toMap**은 어떤 키와 그 키에 연관된 원소들 중 하나를 골라 연관 짓는 맵을 만들 때 유용하다.
  * ex) 다양한 음악가의 앨범들을 담은 스트림을 가지고, 음악가와 그 음악가의 베스트 앨범을 연관 짓고 싶다고 가정해보자.

```java
Map<Artist, Album> topHits = albums.collect(
    toMap(Album::artist, a->a, maxBy(comparing(Album::sales))));
```

* 위 코드에서 비교자로는 **BinaryOperator**에서 정적 임포트한 **maxBy**라는 **정적 팩터리 메소드를 사용**했다.

  * **maxBy**는 `Comparator<T>`를 입력받아 `BinaryOperator<T>`를 돌려준다.

  

  * 이 경우 비교자 생성 메서드인 **comparing**이 **maxBy**에 넘겨줄 비교자를 반환하는데, 자신의 키 추출 함수로는 **Album::sale**s를 받았다.

  

<br>



💎 **마지막에 쓴 값을 취하는 수집기**

* **인수가 3개인 toMap**은 충돌이 나면 **마지막 값을 취하는 수집기를 만들 때도 유용**하다.

  * 많은 스트림의 결과가 비결정적이다. 

  

  * 하지만 매핑 함수가 키 하나에 연결해준 값들이 모두 같을 때, 혹은 값이 다르더라도 모두 허용되는 값일 때 이렇게 동작하는 수집기가 필요하다.

```java
toMap<keyMapper, valueMapper, (oldVal, newVal) -> newVal)
```

* 세 번째이자 마지막 **toMap**은 네 번쨰 인수로 맵 팩터리를 받는다.
  * 이 인수로는 **EnumMap**이나 **TreeMap**처럼 원하는 특정 맵 구현체를 직접 지정할 수 있다.



* 위 세가지 **toMap**에는 **변종**이 있다.
  * **toConcurrentMap**은 병렬 실행된 후 결과로 **ConcurrentHashMap** 인스턴스를 생성한다.





<hr>



💎 **groupingBy 메서드**

* 이 메서드는 **입력으로 분류 함수(classifier)를 받고** **출력으로는** 원소들을 **카테고리별로 모아 놓은 맵을 담은 수집기를 반환**한다.

  * 분류 함수는 입력받은 원소가 속하는 카테고리를 반환한다.

  

  * 그리고 이 카테고리가 해당 원소의 맵 키로 쓰인다.

  

* 다중정의된 **groupingBy** 중 형태가 가장 간단한 것은 분류 함수 하나를 인수로 받아 맵을 반환한다.

  * 반환된 맵에 담긴 각각의 값은 해당 카테고리에 속하는 원소들을 모두 담은 리스트다.

```java
words.collect(groupingBy(word -> alphabetize(word)))
```

* **groupingBy**가 반환하는 **수집기가 리스트 외의 값을 갖는 맵을 생성하게 하려면**, 분류 함수와 함께 **다운스트림(downstream) 수집기도 명시**해야 한다.

  * **다운스트림 수집기의 역할**은 해당 카테고리의 **모든 원소를 담은 스트림으로부터 값을 생성하는 일**이다.

  

  * 이 매개변수를 사용하는 **가장 간단한 방법은 toSet()을 넘기는 것**이다.

  

  * 그러면 **groupingBy**는 **원소들의 리스트가 아닌 집합(Set)을 값으로 갖는 맵을 만들어낸다.**



* **toSet()** **대신 toCollection(collectionFactory)**를 건네는 방법도 있다.

  * 이렇게 하면 **리스트나 집합 대신 컬렉션을 값으로 갖는 맵을 생성**한다.

  

  * **원하는 컬렉션 타입을 선택**할 수 있다는 **유연성은 덤**이다.

  

  * 다운스트림 수집기로 **counting()을 건네는 방법**도 있다.
    * 이렇게 하면 각 카테고리(키)를 해당 카테고리에 속하는 원소의 개수와 매핑한 맵을 얻는다.

```java
Map<String, Long> freq = words
    .collect(groupingBy(String::toLowerCase, counting()));
```



* **groupingBy의 세 번째 버전**은 다운스트림 수집기에 더해 **맵 팩터리도 지정**할 수 있게 해준다.

  * 참고로 이 메서드는 **점층적 인수 목록 패턴에 어긋난다**.
    * 즉, **mapFactory** 매개변수가 **downStream** 매개변수보다 앞에 놓인다.

  

  * 이 버전의 **groupingBy**를 사용하면 맵과 그 안에 담긴 컬렉션의 타입을 모두 지정할 수 있다.
    * ex) 값이 TreeSet인 TreeMap을 반환하는 수집기를 만들 수 있다.



<hr>



💎 **groupingBy의 사촌 partitioningBy**

* 분류 함수 자리에 프레디키트(predicate)를 받고 키가 Boolean인 맵을 반환한다.



* 프레디키트에 더해 다운스트림 수집기까지 입력받는 버전도 다중정의되어 있다.



<hr>



💎 **다운스트림 수집기 전용**  

* **counting** 메서드가 **반환하는 수집기는 다운스트림 수집기 전용**이다.
  * Stream의 count 메서드를 직접 사용하여 같은 기능을 수행할 수 있으니 collect(counting()) 형태로 사용할 일은 전혀 없다.
  * Collections에는 이런 속성의 메서드가 16개나 더있다.
    * ex) summing,averaging, summarizing 으로 시작하며, 각각 int, long, double 스트림용으로 하나씩 존재한다.
  * 다중정의된 reducing 메서드들, filtering, mapping, flatMapping, collectingAndThen 메서드가 있다.
    * 대부분 프로그래머는 이들의 존재를 모르고 있어도 상관없다.



<hr>



💎  **Collectors에 정의되어 있지만 수집과는 관련이 없는 메서드**

* **minBy**와 **maxBy**는 인수로 받은 비교자를 이용해 **스트림에서 값이 가장 작은 혹은 가장 큰 원소를 찾아 반환**한다.

  * **Stream** 인터페이스의 **min**과 **max** 메서드를 살짝 일반화 한 것이자, **java.util.function.BinaryOperator**의 **minBy**와 **maxBy** 메서드가 반환하는 이진 연산자의 수집기 버전이다.

  

* **joining** 메서드는 (문자열 등의) **CharSequence** 인스턴스의 **스트림에만 적용**할 수 있다.

  * 이 중 매개변수가 없는 **joining**은 단순히 원소들을 **연결하는 수집기를 반환**한다.

  

  * 한편 인수 하나짜리 **joining**은 **CharSequence** 타입의 구분문자(**delimiter**)를 매개변수로 받는다.
    * 연결 부위에 이 구분문자를 삽입하는데, 예컨대 구분문자로 쉼표(,)를 입력하면 CSV 형태의 문자열을 만들어 준다.

  

  * 인수 3개짜리 **joining**은 구분문자에 더해 접두문자와 접미문자도 받는다.
    * ex) 접두, 구분, 접미문자를 각각 **'[,'** , **','**, **']'** 로 지정하여 얻은 수집기는 [came, saw, conquered] 처럼 마치 컬렉션을 출력한 듯한 문자열을 생성한다.



<hr>



> 스트림 파이프라인 프로그래밍의 핵심은 **부작용 없는 함수 객체에 있다.**
>
> 스트림뿐 아니라 스트림 관련 객체에 건네지는 모든 함수 객체가 부작용이 없어야 한다.
>
> 
>
> **종단 연산 중 forEach는 스트림이 수행한 계산 결과를 보고할 때만 이용해야 한다.**
>
> **계산 자체에는 이용하지 말자.**
>
> 
>
> 스트림을 올바로 사용하려면 수집기를 잘 알아둬야 한다.
>
> **가장 중요한 수집기 팩터리는 toList, toSet, toMap, groupingBy, joining이다.**





```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

