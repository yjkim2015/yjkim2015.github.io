---
title: 옵셔널 반환은 신중히하라 - Effective Java[55]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗  자바 8 이전 메서드가 특정 조건에서 값을 반환 할 수 없을 때 취할 수 있는 선택 두 가지

* **첫 번째**는 예외를던지는 것이다.



* **두 번째**는 반환 타입이 객체 참조라면 null을 반환하는 것이다.



* <span style="color:red;">두 방법 모두 허점이 있다.</span>

  * 예외는 진짜 예외적인 상황에서만 사용해야 한다**(예외를 생성할 때 스택 추적 전체를 캡쳐하므로 비용도 만만치 않다)**

  

  * null을 반환하면 이런 문제가 생기지 않지만, 그 나름의 문제가 있다.

    * null을 반환할 수 있는 메서드를 호출할 때는, (null이 반환될 일이 절대 없다고 확신하지 않는 한) **별도의 null 처리 코드를 추가해야 한다.**

    

    * null 처리를 무시하고 반환된 null 값을 어딘가에 저장해두면 언젠가 **NullPointerException 이 발생 할 수 있다.**
      * 그것도 근본적인 원인, 즉 null을 반환하게 한 실제 원인과는 전혀 상관없는 코드에서 말이다.



<hr>



##### 🔗 자바 8버전 또 하나의 선택지가 생겼다 : `Optional<T>`

* `Optional<T>`는 **null**이 아닌 **T타입 참조를 하나 담거나, 혹은 아무것도 담지 않을 수 있다.**

  * 아무것도 담지 않은 옵셔널은 '비었다'고 말한다.

  

  * 반대로 어떤 값을 담은 옵셔널은 '비지 않았다'고 한다.



* 옵셔널은 원소를 최대 1개 가질 수 있는 **'불변' 컬렉션**이다.
  * `Optional<T>`가 `Collection<T>`를 구현하지는 않았지만, 원칙적으로는 그렇다는 말이ㅏㄷ.



* 보통은 T를 반환해야 하지만 **특정 조건에서는 아무것도 반환하지 않아야 할 때 T 대신 `Optional<T>`를 반환하도록 선언하면 된다.**

  * 그러면 유효한 반환값이 없을 때는 **빈 결과를 반환하는 메서드가 만들어진다.**

  

  * <span style="color:red;">옵셔널을 반환하는 메서드는</span> **예외를 던지는 메서드보다 유연하고 사용하기 쉬우며, null을 반환하는 메서드보다 오류 가능성이 작다.**



<hr>



* 다음의 예시를 보자

  


💎 **컬렉션에서 최댓값을 구한다 (컬렉션이 비었으면 예외를 던진다)**

```java
public static <E extends Comparable<E>> E max(Collection<E> c) {
    if (c.isEmpty()) {
        throw new IllegalArgumentException("빈 컬렉션");
    }
    E result = null;
    for (E e : c){
        if (result == null || e.compareTo(result) > 0){
            result = Objects.requireNonNull(e);
        }
    }
    return result;
}
```

* 이 메서드에 빈 컬렉션을 건네면 IllegalArgumentException을 던진다. 



* 위 코드를 `Optional<E>`를 반환토록 수정하면 아래와 같다.



<hr>



💎 **컬렉션에서 최댓값을 구해 `Optional<E>`로 반환한다.**

```java
public static <E extends Comparable<E>> Optional<E> max(Collection<E> c) {
    if (c.isEmpty()){
       return Optional.empty();
    }
    
    E result = null;
    for (E e : c) {
        if (result == null || e.compareTo(result) > 0) {
            result = Objects.requireNonNull(e);
        }
    }
    return Optional.of(result);
}
```

* 옵셔널을 반환하도록 구현하기는 어렵지 않다.

  * **적절한 정적 팩터리를 사용해 옵셔널을 생성해주기만 하면 된다.**

  

  * 위 코드에서는 두 가지 정적 팩터리를 사용했다.

    * 빈 옵셔널은 **Optional.empty()**로 만들고, 값이 든 옵셔널은 **Optional.of(value)**로 생성했다.

    

  * **null 값도 허용하는 옵셔널**을 만들려면 **Optional.ofNullable(value)**를 사용하면 된다.



* **옵셔널을 반환하는 메서드**에서는 <span style="color:red;">절대 null을 반환하지 말자.</span>

  * 옵셔널을 도입한 취지를 완전히 무시하는 행위다.

  

* 스트림의 종단 연산 중 **상당수가 옵셔널을 반환한다.**
  * 앞의 max 메서드를 아래와 같이 스트림 버전으로 다시 작성한다면 **Stream의 max 연산이 우리에게 필요한 옵셔널을 생성해 줄 것이다.**



<hr>



💎 **컬렉션에서 최댓값을 구해 `Optional<E>`로 반환한다 - 스트림 버전**

```java
public static <E extends Comparable<E>> Optional<E> max(Collection<E> c) {
    return c.stream().max(Comparator.naturalOrder());
}
```

* 그렇다면 **null**을 반환하거나 **예외**를 던지는 대신 <span style="color:red;">옵셔널 반환을 선택해야 하는 기준은 무엇일까?</span>

  * **옵셔널은** <span style="color:red;">검사 예외와 취지가 비슷하다.</span>

  

  * <span style="color:red;">즉</span>, **반환 값이 없을 수도 있음을 API 사용자에게 명확히 알려준다.**

    * <span style="color:red;">비검사 예외를 던지거나 null을 반환한다면</span> **API 사용자가 그 사실을 인지하지 못해 끔찍한 결과로 이어질 수 있다.**

    

    * <span style="color:red;">하지만</span> **검사 예외를 던지면** 클라이언트에서는 **반드시 이에 대처하는 코드를 작성해넣어야 한다.**

    

  * 비슷하게, **메서드가 옵셔널을 반환한다면** 클라이언트는 <span style="color:red;">값을 받지 못했을 때 행동을 선택 해야한다.</span> **그 중 하나는 아래와 같이 기본값을 설정하는 방법이다.**

<hr>



💎 **옵셔널 활용 1 - 기본값을 정해둘 수 있다.**

```java
String lastWordInLexicon = max(words).orElse("단어 없음..");
```

* 또는 <span style="color:red;">상황에 맞는 예외를 던질 수 있다.</span>

  * 아래 코드에서는 **실제 예외가 아니라 예외 팩터리를 건넨 것에 주목** 해야 한다.

  

  * 이렇게 하면 **예외가 실제로 발생하지 않는 한 예외 생성 비용은 들지 않는다.**

<br>



💎 **옵셔널 활용 2 - 원하는 예외를 던질 수 있다.**

```java
Toy myToy = max(toys).orElseThrow(TemperTantrumException::new);
```

* **옵셔널에 항상 값이 채워져 있다고 확신한다면** 아래와 같이 그냥 **곧바로 값을 꺼내 사용하는 선택지도 있다.**



* 다만 잘못 판단한 것이라면 **NoSuchElementException**이 발생 할 것 이다.

<br>



💎 **옵셔널 활용 3 - 항상 값이 채워져 있다고 가정한다.**

```java
Element lastNobleGas = max(Elements.NOBLE_GASES).get();
```



<hr>



##### 🔗 옵셔널 기본값을 설정하는 비용이 아주 커서 부담이 될 때도 있다.

* `Supplier<T>`를 인수로 받는 **orElseGet**을 사용하면, **값이 처음 필요 할 때** `Supplier<T>`를 **사용해 생성하므로 초기 설정 비용을 낮출 수 있다.**
  * (사실 이 메서드는 **compute**로 시작하는 **Map** 메서드들과 밀접하니 **orElseCompute**로 이름 짓는 게 더 나았을지도 모르겠다)



* 더 특별한 쓰임에 대비한 메서드도 준비되어 있다.
  * **filter**, **map**, **flatMap**, **ifPresent**



<hr>



##### 💎 isPresent : 안전 밸브 역할의 메서드

* 옵셔널이 채워져 있으면 **true**를, 비어있으면 **false**를 반환한다.



* 이 메서드는 원하는 모든 작업을 수행할 수 있지만 <span style="color:red">신중히 사용해야 한다.</span>
  * 실제로 **isPresent**를 쓴 코드 중 상당수는 앞서 언급한 메서드들로 대체할 수 있으며, 그렇게 하면 더 짧고 명확하고 용법에 맞는 코드가 된다.



* 다음 코드는 부모 프로세스의 프로세스 ID를 출력하거나, 부모가 없다면 **"N/A"**를 출력하는 코드다. 자바 9에서 소개된 **ProcessHandle** 클래스를 사용했다.

```java
Optional<ProcessHandle> parentProcess = ph.parent();
System.out.println("부모 PID : "  + parentProcess.isPresent() ? String.valueOf(parentProcess.get().pid()) : "N/A"));
```



* 위 코드는 **Optional**의 **map**을 사용하여 다음처럼 다듬을 수 있다.

```java
System.out.println("부모 PID : " + ph.parent().map(h -> String.valueOf(h.pid())).orElse("N/A"));
```

* 스트림을 사용한다면 옵셔널들을 `Stream<Optional<T>>`로 받아서, 그 중 채워진 옵셔널들에서 값을 뽑아 `Stream<T>`에 건네 담아 처리하는 경우가 드물지 않다.

  * 자바 8에서는 다음과 같이 구현할 수 있다.

  

```java
streamOfOptionals
    .filter(Optinal::isPresent)
    .map(Optional::get)
```

* 위 코드는 옵셔널에 값이 있다면 (**Optional::isPresent**) 그 값을 꺼내 (**Optional::get**) 스트림에 매핑한다.



* **자바 9**에서는 **Optional**에 **stream()** 메서드가 추가되었다.

  * 이 메서드는 **Optional**을 **Stream**으로 변환해주는 어댑터다.

  

  * 옵셔널에 값이 있으면 그 값을 원소로 담은 스트림으로, 값이 없다면 빈 스트림으로 변환한다.

  

  * 이를 **Stream**의 **flatMap** 메서드와 조합하면 위의 코드를 다음처럼 명료하게 바꿀 수 있다.

```java
streamOfOptionals.
    flatMap(Optinal::stream)
```



<hr>



##### 💎  반환값으로 옵셔널을 사용한다고 해서 무조건 득이 되는건 아니다.

* **컬렉션, 스트림, 배열, 옵셔널 같은 컨테이너 타입은** <span style="color:red;">옵셔널로 감싸면 안 된다.</span>

  * 빈 `Optional<List<T>>` 를 반환하기보다는 빈 `List<T>`를 반환하는 게 좋다

  

  * 빈 컨테이너를 그대로 반환하면 클라이언트에 **옵셔널 처리 코드를 넣지 않아도 된다.**
    * 참고로 **ProcessHandle.Info** 인터페이스의 **arguments** 메서드는 `Optional<String[]>`을 반환하는데, 이는 <span style="color:red;">예외적인 경우이니 따라하면 안된다.</span>



<br>



##### 💎 그럼 어떤 경우에 메서드 반환 타입을 **T** 대신 `Optinal<T>`로 선언해야 할까?

* <span style="color:red;">기본 규칙은 결과가 없을 수 있으며, 클라이언트가 이 상황을 특별하게 처리해야 한다면</span> `Optional<T>`를 반환한다.

  * 그런데 이렇게 하더라도 `Optional<T>`를 반환하는 데는 <span style="color:red;">대가가 따른다.</span>

  

  * **Optional**도 엄연히 **새로 할당하고 초기화해야 하는 객체이고**, 그 안에서 **값을 꺼내려면 메서드를 호출해야 하니 한 단계를 더 거치는 셈이다.**

  

  * 그래서 <span style="color:red;">성능이 중요한 상황에서는 옵셔널이 맞지 않을 수 있다.</span>

  

* 어떤 메서드가 이 상황에 처하는지 알아내려면 **세심히 측정해보는 수 밖에 없다.**



<hr>



##### 💎 박싱된 기본타입 전용 옵셔널 클래스 

* 박싱된 기본 타입을 담는 옵셔널은 기본 타입 자체보다 무거울 수 밖에 없다.
  * 값을 두 겹이나 감싸기 때문이다.



* 그래서 자바 **API** 설계자는 **int**, **long**, **double** <span style="color:red;">전용 옵셔널 클래스</span>들을 준비해놨다.

  * **OptionalInt**, **OptinalLong**, **OptinalDouble**

    * 이 옵셔널들도 Optional<T>가 제공하는 메서드를 거의 다 제공한다.

    

* **박싱된 기본 타입을 담은 옵셔널**을 <span style="color:red;">반환하는 일은 없도록 해야 한다.</span>

  * <span style="color:red;">단</span>, '**덜 중요한 기본 타입**'용인 **Boolean**, **Byte**, **Character**, **Short**, **Float**은 **예외**일 수 있다.



<hr>



##### 💎 옵셔널을 컬렉션의 키, 값, 원소나 배열의 원소로 사용하는 게 적절한 상황은 거의 없다.

* <span style="color:red;">옵셔널을 맵의 값으로 사용하면 절대 안 된다. </span>대부분 적절치 않기 때문이다.

  * 만약 그리 한다면 맵 안에 키가 없다는 사실을 나타내는 방법이 **두가지가 된다.**

  

  * **하나는 키 자체가 없는 경우이고**, **다른 하나는 키는 있지만 그 키가 속이 빈 옵셔널 인 경우이다.**

  

  * <span style="color:red;">쓸데없이 복잡성만 높여서 혼란과 오류 가능성을 키울 뿐이다.</span>



<hr>



##### 💎 옵셔널을 인스턴스 필드에 저장해두는 게 필요할 때가 있을까?

* 이런 상황 대부분은 필수 필드를 갖는 클래스와, 이를 확장해 선택적 필드를 추가한 하위 클래스를 따로 만들어야 함을 암시하는 '나쁜 냄새다'.



* <span style="color:red;">하지만</span> **가끔은** 적절한 상황도 있다.
  * 예를들어 **인스턴스 필드 중 필수가 아니며** **기본 타입이라 값이 없음을 나타낼 방법이 마땅치 않은 경우** <span style="color:red;">선택적 필드의 게터 메서드들이 옵셔널을 반환하게 해주는 것도 좋은 방법 이다.</span>



<hr>

> 값을 반환하지 못할 가능성이 있고, 호출할 때마다 반환값이 없을 가능성을 염두에 둬야하는 
>
> 메서드라면 옵셔널을 반환해야 할 상황일 수 있다.
>
> 
>
> **하지만 옵셔널 반환에는 성능 저하가 뒤따르니, 성능에 민감한 메서드라면 null을 반환하거나 예외를 던지는 편이 나을 수 있다.**
>
> 
>
> 그리고 옵셔널을 반환값 이외의 용도로 쓰는 경우는 매우 드물다.











```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

