---
title: 배열보다는 리스트를 사용하라 - Effective Java[28]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 배열과 제네릭 타입의 차이



##### 💎 배열은 공변, 제네릭은 불공변

* **배열은 공변(covariant)이다.** 

  * ex) Sub가 Super의 하위 타입이라면 Sub[]는 배열 Super[]의 하위 타입이 된다. 

  

  * **즉, 함께 변한다는 뜻** [자기 자신과 자식 객체로 타입 변환을 허용해주는 것]

  

* **제네릭은 불공변(invariant)이다**

  * 서로 다른 타입 Type1, Type2가 있을 때, `List<Type1>`은 `List<Type2>`의 하위 타입도 아니고 상위 타입도 아니다.

    

  * **불공변은 자기와 타입이 같은 것만 같다고 인식하는 것이 특징이다.**

  

  * **즉, 두 개의 타입은 전혀 관련이 없다는 뜻이다.**



<br>



**💎배열 예제 - 런타임 시점에 실패한다.**

```java
Object[] objectArray = new Long[1];
objectArray[0] = "타입이 달라 넣을 수 없다."; //ArrayStoreException 발생
```





**💎제네릭 예제 - 컴파일 시점에 실패한다.**

```java
List<Object> ol = new ArrayList<Long>(); // 호환되지 않는 타입이다.
ol.add("타입이 달라 넣을 수 없다.")
```



* 어느 쪽이든 Long용 저장소에 String을 넣을 수는 없다.



* 배열에서는 그 실수를 런타임에야 알게 되지만, **제네릭 리스트에서는 컴파일 할 때 바로 알 수 있다.**



<hr>



##### 💎 배열은 실체화, 제네릭은 타입정보 런타임 시 소거

* **배열은 런타임에도 자신이 담기로 한 원소의 타입을 인지하고 확인한다.**
  * 위 코드에서 보듯 **Long** 배열에 **String**을 넣으려 하면 **ArrayStoreException**이 발생한다.



* **제네릭은 타입 정보가 런타임에는 소거 된다.**

  * 원소 타입을 컴파일타임에만 검사하며 런타임에는 알 수조차 없다는 뜻이다.

    

  * 소거는 제네릭이 지원되기 전의 레거시 코드와 제네릭 타입을 함께 사용할 수 있게 해주는 메커니즘이다.



<hr>



##### 💎 제네릭 배열은 왜 못만들게 했을까?

* **타입 안전하지 않기 때문이다.**



* <span style="color:red;">제네릭 배열을 허용한다면</span> 컴파일러가 자동 생성한 형변환 코드에서 런타임에 **ClassCastException**이 발생한다.



* 런타임에 **ClassCastException**이 발생하는 일을 막아주겠다는 **제네릭 타입 시스템의 취지**에 <span style="color:red;">어긋나는것이다.</span>

<br>



**💎 제네릭 배열 생성을 허용하지 않는 이유 - 컴파일 되지 않는다.**

```java
List<String>[] stringLists = new List<String>[1]; // (1)
List<Integer> intList = List.of(42); // (2)
Object[] objects = stringLists; // (3)
objects[0] = intList; // (4)
String s = stringLists[0].get(0); // (5)
```

* 제네릭 배열을 생성하는 (1)이 허용된다고 상상해보자.



* (2)는 원소가 하나 뿐인 `List<Integer>`를 생성한다.



* (3)은 (1)에서 생성한 `List<String>`의 배열을 **Object** 배열에 할당한다.



* (4)는 (2)에서 생성한 `List<Integer>`의 인스턴스를 **Object** 배열의 첫 원소로 저장한다.



* `List<String>` 인스턴스만 담겠다고 선언한 **stringLists** 배열에는 `List<Integer>` 인스턴스가 저장돼 있다.

  * (5)는 이 배열의 처음 리스트에서 첫 원소를 꺼내려한다.

  

  * 컴파일러는 꺼낸 원소를 자동으로 **String**으로 형변환하는데, 이 원소는 **Integer** 이므로 런타임에 **ClassCastExcetpion**이 발생한다.

  

* **이런 일을 방지하려면 <span style="color:red;">(제네릭 배열이 생성되지 않도록)</span> (1)에서 컴파일 오류를 내야 한다.**



<hr>



#### 🔗 실체화 불가 타입

* **E**, `List<E>`, `List<String>` 같은 타입을 **실체화 불가 타입**이라 한다.



* <span style="color:red;">즉,</span> 실체화되지 않아서 런타임에는 컴파일타임보다 타입 정보를 적게 가지는 타입이다.



* **소거 메커니즘** 때문에 **매개변수화 타입** 가운데 실체화될 수 있는 타입은 
  `List<?`>와 `Map<?,?>` 같은 **비한정적 와일드 카드** 뿐이다.



* 배열을 비한정적 와일드카드 타입으로 만들 수는 있지만, 유용하게 쓰일 일은 거의 없다.





<hr>



##### 💎 배열을 제네릭으로 만들 수 없어 귀찮은 상황도 있어 T_T

* 제네릭 컬렉션에서는 자신의 원소 타입을 담은 배열을 반환하는게 보통은 불가능하다.



* 제네릭 타입과 가변인수 메소드**(varargs method)**를 함께 쓰면 해석하기 어려운 경고 메시지를 받게 된다.

  * 가변인수 메소드를 호출할 때마다 가변인수 매개변수를 담을 배열이 하나 만들어지는데, 이때 그 배열의 원소가 실체화 불가 타입이라면 경고가 발생하는 것이다.

  

  * **@SafeVarargs** 애너테이션으로 대처할 수 있다.



<hr>



##### 💎 배열로 형변환 할 때 제네릭 배열 생성 오류나 비검사 형변환 경고가 뜨는 경우

* 대부분은 배열인 `E[]` 대신 컬렉션인 `List<E>`를 사용하면 해결된다.



* 코드가 조금 복잡해지고 성능이 살짝 나빠질 수도 있지만, **타입 안정성과 상호 운용성은 좋아진다.**



<br>

**💎생성자에서 컬렉션을 받는 클래스 - 제네릭을 시급히 적용해야한다.**

```java
public class Chooser {
    private final Object[] choiceArray;
    
    public Chooser(Collection choices) {
        choiceArray = choices.toArray();
    }
    
    public Object choose() {
        Random rnd = ThreadLocalRandom.current();
        return choiceArray[rnd.nextInt(choiceArray.length)];
    }
}
```

* 이 클래스를 사용하려면 choose 메소드를 호출할 때마다 반환된 Object를 원하는 타입으로 형변환 해야한다.
  * 만약 다른 타입의 원소가 들어 있었따면 런타임에 형변환 오류가 날 것이다.

<br>

**💎 Chooser를 제네릭으로 만들기 위한 첫 시도 - 컴파일 되지 않는다.**

```java
public class Chooser {
    private final T[] choiceArray;
    
    public Chooser(Collection<T> choices) {
        choiceArray = choices.toArray();
    }

    public Object choose() {
        Random rnd = ThreadLocalRandom.current();
        return choiceArray[rnd.nextInt(choiceArray.length)];
    }
}
```
* 이 클래스를 컴파일하면 다음과 같은 오류가 출력된다.



* error : incompatible types: Object[] cannot be converted to T[]

<br>

**💎해결책 인 줄 알았지!!? Object 배열을 T배열로 형변환 - 경고**

```java
public class Chooser {
    private final T[] choiceArray;
    
    public Chooser(Collection<T> choices) {
        choiceArray = (T[]) choices.toArray();
    }
	...
}
```
* warning : [unchecked] unchecked cast choiceArray = (T[]) choices.toArray();



* **T가 무슨 타입인지 알 수 없으니 컴파일러는 이 형변환이 런타임에도 안전한지 보장할 수 없다는 메시지이다.**



* 제네릭에서는 원소의 타입 정보가 소거되어 런타임에는 무슨 타입인지 알 수 없다고 했다.
  * ex) `List<String>` 컴파일 시점 -> List 런타임 시점



<hr>



##### 💎 비검사 형변환 경고를 제거하려면 배열 대신 리스트를 쓰자!



```java
public class Chooser {
    private final List<T> choiceList;
    
    public Chooser(Collection<T> choices) {
        choiceList = new ArrayList<>(choices);
    }

    public Object choose() {
        Random rnd = ThreadLocalRandom.current();
        return choiceList.get(rnd.nextInt(choiceList.size()));
    }
}
```
* 코드 양이 조금 늘었고 성능상 조금 더 느릴테지만, 런타임에 ClassCastException을 만날 일이 없으니 그만한 가치가 있다.



<hr>



> 배열과 제네릭에는 매우 다른 타입 규칙이 적용된다.
>
> **배열은 공변이고 실체화되는 반면, 제네릭은 불공변이고 타입 정보가 소거된다.**
>
> 그 결과 배열은 런타임에는 타입 안전하지만 컴파일타임에는 그렇지 않다.
>
> 제네릭은 반대다.
>
> 그래서 둘을 섞어 쓰기란 쉽지 않다.
>
> 둘을 섞어 쓰다가 컴파일 오류나 경고를 만나면, 
>
> 가장 먼저 배열을 리스트로 대체하는 방법을 적용해보자.





```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

