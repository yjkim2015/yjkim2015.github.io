---
title: 로(raw) 타입은 사용하지 말라
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 제네릭 타입 (generic Type)

* 클래스와 인터페이스 선언에 타입 매개변수가 쓰이면, 이를 **제네릭 클래스** 혹은 **제네릭 인터페이스**라 한다.

  ```java
  ex) List<E>
  ```

  **제네릭 클래스**와 **제네릭 인터페이스**를 통틀어 <span style="color:red">제네릭 타입</span>이라 한다.

  

* 각각의 제네릭 타입은 일련의 **매개변수화 타입**을 정의한다.

  * 먼저 클래스(혹은 인터페이스) 이름이 나오고, 이어서 꺾쇠괄호 안에 실제 타입 매개변수들을 나열한다.

    ```java
    ex) List<String>
    ```

    여기서 **String**이 정규 타입 매개변수 **E**에 해당하는 **실제 타입**이다.

    

* 제네릭 타입을 하나 정의하면 그에 딸린 **<span style="color:red;">로 타입 (raw type)</span>**도 함께 정의된다. 

  * **<span style="color:red;">로 타입(raw type)</span>** 이란 제네릭 타입에서 타입 매개변수를 전혀 사용하지 않을 때를 말한다.

    ```java
    ex) List  <- raw Type
    ```

    

  * **로 타입**은 타입 선언에서 제네릭 타입 정보가 전부 지워진 것처럼 동작하는데, 제네릭이 도래하기 전 코드와 호환되도록 하기 위한 궁여지책이라 할 수 있다.



<hr>



##### 💎 컬렉션의 로 타입 (raw Type) - 따라 하지 말 것@

```java
//Stamp 인스턴스만 취급한다.
private final Collections stamps = ...;
```



이 코드를 사용하면 실수로 **도장(Stamp)대신 동전(Coin)**을 넣어도 <span style="color:red;">아무 오류 없이 컴파일 되고 실행된다</span>(컴파일러가 경고 메시지를 보여주긴 할 것이다).

```java
//실수로 동전을 넣는다.
stamps.add(new Coin(...)); //"unchecked call" 경고를 내뱉는다
```



컬렉션에서 이 동전을 다시 꺼내기 전에는 오류를 알아 채지 못한다.



##### 💎 반복자의 로 타입 - 따라 하지 말 것

```java
for (Iterator i = stamps.iterator(); i.hasNext(); ) {
	Stamp stamp = (Stamp) i.next(); //ClassCastException 발생
	stamp.cancel();
}
```



**오류는 가능한 발생 즉시, 이상적으로는 컴파일 할 때 발견하는 것이 좋다.**

위 예에서는 오류가 발생하고 한참 뒤인 런타임에야 알아챌 수 있는데, 

<span style="color:red;">이렇게 되면</span> 런타임에 문제를 겪는 코드와 원인을 제공한 코드가 물리적으로 상당히 떨어져 있을 가능성이 커진다.



<hr>



**💎 매개변수화된 컬렉션 타입 - 타입안정성 확보**

```java
private final Collection<Stamp> stamps = ...;
```

* 위처럼 제네릭 타입을 명시해주면 stamps에는 **Stamp의 인스턴스만 넣어야 함을 컴파일러가 인지**하게 된다.
  
* 아무런 경고 없이 컴파일된다면 의도대로 동작할 것임을 보장한다.



**💎 매개변수화된 컬렉션 타입 - 엉뚱한 타입 넣어보기!**

```java
stamps.add(new Coin());
```

* Stamp 타입으로 명시된 stamps에 coin을 넣으려 하면 아래와 같은 컴파일 오류가 발생한다.



```
error: incompatible types: Coin cannot be converted to Stamp
```

* 위 같은 상황은 현업에서도 종종 일어나는 일이다.



* 예를들어 BigDecimal용 컬렉션에 BigInteger를 넣는 상황이다.



<hr>



#### 🔗 로 타입(타입 매개변수가 없는 제네릭 타입)은 절대로 써서는 안돼!!

* 로 타입을 쓰면 제네릭이 안겨주는 안정성과 표현력을 모두 잃게 된다.



<br>

##### 💎 아니 그럼 만들지를 말지 왜 쓰지말래 ?

* 호 . 환.  성 때문이다



* 자바가 제네릭을 받아들기까지 **거의 10년이 걸린 탓에 제네릭 없이 짠 코드가 대부분이다.**



* **기존 코드를 모두 수용**하면서 제네릭을 사용하는 **새로운 코드**와도 맞물려 돌아가게 해야만 했기 때문이다.



* 로 타입을 사용하는 메소드에 **매개변수화 타입의 인스턴스**를 넘겨도 (반대도) 동작해야만 했다.



<hr>



#### **💎 임의 객체를 허용하는 매개변수화 타입은 괜찮아!!**

* List 같은 로 타입은 사용해서는 안 되나, `List<Object>`처럼 **임의 객체를 허용하는 매개변수화 타입**은 괜찮다.

  * List는 **제네릭 타입에서 완전히 발을 뺀 것**이다.
  * `List<Object>`는 **<span style="color:red;">모든 타입을 허용</span>한다는 의사를 컴파일러에 명확히 전달** 한 것이다.

  

* 매개변수로 **List**를 받는 **메소드에 `List<String>`**을 넘길 수 있지만, **`List<Object>`**를 받는 메소드에는 넘길 수 없다. <span style="color:red;">이는 제네릭의 하위 타입 규칙 때문이다.</span>
  * `List<String>`은 로 타입인 List의 하위 타입이다.
    
  * `List<Object>`는 List의 하위 타입이 아니다.
    
  * `List<Object>`같은 매개변수화 타입을 사용할 때와 달리 List 같은 로 타입을 사용하면 타입 안정성을 잃게 된다.

<br>



**💎 unsafeAdd 메소드가 로 타입(List)를 사용 - 런타임에 실패한다.**

```java
public static void main(String[] args) {
	List<String> strings = new ArrayList<>();
	unsafeAdd(strings, Integer.valueOf(42));
	String s = strings.get(0); // 컴파일러가 자동으로 형변환 코드를 넣어준다.
}

public static void unsafeAdd(List list, Object o) {
	list.add(o);
} 
```

위 코드는 컴파일은 되지만 로 타입인 List를 사용하여 다음과 같은 경고가 발생한다.

```
warning: [unchecked] unchecked call to add(E) as a member of the raw type List
```

* 위 프로그램 실행 시 strings.get(0)의 결과를 형변환하려 할 때 ClassCastException을 던진다.
  Integer를 String으로 변환하려 시도한 것이다.



* 이 형변환은 컴파일러가 자동으로 만들어준 것이라 보통은 실패하지 않지만, 위 경우엔 경고를 무시하여 그 대가를 치른 것이다.



* 로 타입인 List를 매개변수화 타입인 `List<Object>`로 바꾼 다음 다시 컴파일하면, 아래와 같은 오류를 출력하며 컴파일 조차 되지 않는다.

  ```
  error : incompatible types: List<String> cannot be converted to List<Object>
  ```



<hr>



#### **🔗 비한정적 와일드카드 타입을 사용해! **



이쯤되면 원소의 타입을 몰라도 되는 로 타입을 쓰고 싶어질 수 있다.

다음의 예를 보자.

**💎로 타입의 잘못된 예**

```java
static int numElementsInCommon(Set s1, Set s2) {
    int result = 0;
    for (Object o1 : s1) {
        if (s2.contains(o1)) {
            result++;
        }
        return result;
    }
}
```

* 위 메소드는 동작은 하지만 로 타입을 사용해 안전하지 않다.



* 따라서 **비한정적 와일드카드(unbounded wildcard type)**을 사용하는게 좋다.



* 제네릭 타입을 쓰고 싶지만 실제 타입 매개변수가 무엇인지 신경쓰고 싶지 않다면 **<span style="color:red;">물음표(?)</span>**를 사용하자.

  * ex) `Set<E>` -> `Set<?>`

  

  * 이것은 어떤 타입이라도 담을 수 있는 가장 범용적인 매개변수화 타입이다.



<br>

**💎비한정적 와일드카드 타입 사용 예**

```java
static int numElementsInCommon(Set<?> s1, Set<?> s2) {...}
```

* **비한정적 와일드카드 타입인 `Set<?>`와 로 타입의 Set의 차이는 안전하냐 안전하지 않냐의 차이다.**



* 로 타입 컬렉션에는 아무 원소나 넣을 수 있으니 **타입 불변식을 훼손하기 쉽다.**



* **비한정적 와일드 카드를 사용한 `Collection<?>`에는 <span style="color:red;">null외에 어떤 원소도 넣을 수 없다.</span>**

  * Object class에서 제공하는 메소드일 때 사용

  

  * 매개변수 타입에 의존하지 않는 제네릭 클래스의 메소드를 사용할 때 사용





<hr>



#### 🔗 예외는 항상 있는법 이럴 땐 써도 돼 로타입!!



* **class 리터럴에는 로 타입을 써야 한다.**
  * 자바 명세는 class 리터럴에 매개변수화 타입을 사용하지 못하게 했다. (배열과 기본 타입허용)
  * ex) List.class, String[].class, int.class 허용  `List<String>.class`, `List<?>.class` 비허용



* **instanceof 연산자 사용 할 때**

  * 런타임에는 제네릭 타입 정보가 지워지므로 **instanceof 연산자는 비한정적 와일드카드 타입** 
    **이외의 매개변수화 타입에는 적용할 수 없다.**

  

  * 로 타입이든 비한정적 와일드카드 타입이든 instanceof는 완전히 똑같이 동작한다.

  

  * 비한정적 와일드카드 타입의 꺾쇠괄호와 물음표는 아무런 역할 없이 코드만 지저분하게 하니, 차라리 로 타입을 쓰는 편이 깔끔하다.

<br>



**💎 로 타입을 써도 좋은 예 - instanceof 연산자**

```java
if (o instanceof Set) { // 로 타입
	Set<?> s = (Set<?>)o; // 와일드카드 타입
	..
}
```

* o의 타입이 Set임을 확인한 다음 와일드 카드 타입인 `Set<?>`로 형변환해야 한다.  (로 타입인 Set이 아니다)



* 이는 검사 형변환(checked cast)이므로 컴파일러 경고가 뜨지 않는다.



<hr>



> **로 타입을 사용하면 런타임에 예외가 일어날 수 있으니 사용하면 안 된다.**
>
> 로 타입은 제네릭이 도입되기 이전 코드와의 호환성을 위해 제공될 뿐이다.
>
> 빠르게 훑어보자면, `Set<Object>`는 어떤 타입의 객체도 저장할  수 있는 **매개변수화 타입**이고,
>
> `Set<?>`는 모종의 타입 객체만 저장할 수 있는 **와일드카드 타입**이다.
>
> **그리고 이들의 로 타입인 Set은 제네릭 타입 시스템에 속하지 않는다.**
>
> **`Set<Object>`와 `Set<?>`는 안전하지만, 로 타입인 Set은 안전하지 않다.**









```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

