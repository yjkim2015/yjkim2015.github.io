---
title: null이 아닌, 빈 컬렉션이나 배열을 반환하라 - Effective Java[54]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗  null 반환은 나빠!

* 다음은 주변에서 흔히 볼 수 있는 메서드이다.

<br>

💎 **컬렉션이 비었으면 null을 반환한다. - 따라 하지 말 것 ! **

```java
private final List<Cheese> cheeseInStock = ...;
/**
*	@return 매장 안의 모든 치즈 목록을 반환한다.
*	단, 재고가 하나도 없다면 null을 반환한다.
*/
public List<Cheese> getCheeses() {
    return cheesesInStock.isEmpty() ? null : new ArrayList<>(cheeseInStock);
}
```

* 재고가 없다고 해서 특별히 null을 반환 해야 한다면 클라이언트는 아래와 같이 null을 처리하는 코드를 추가로 작성해야 한다.

<br>

```java
List<Cheese> cheeses = shop.getCheeses();
if (cheeses != null && cheeses.contains(Cheese.STILTON)) {
    System.out.println("좋았어, 바로 그거야.");
}
```

* **컬렉션이나 배열 같은 컨테이너(container)가 비었을 때 null을 반환하는 메서드를 사용할 때면** 항시 이와 같은 **방어 코드를 넣어줘야 한다.**

  * 클라이언트에서 <span style="color:red;">방어 코드를 빼먹으면 오류가 발생할 수 있다.</span>

  

  * 실제로 객체가 0개일 가능성이 거의 없는 상황에서는 수년 뒤에야 오류가 발생하기도 한다.

  

* <span style="color:red;">한편</span>, **null을 반환하려면** 반환하는 쪽에서도 **이 상황을 특별히 취급해줘야 해서 코드가 더 복잡해진다.**



* 때로는 빈 컨테이너를 할당하는 데도 비용이 드니 null을 반환하는 쪽이 낫다는 주장도 있다.

  * <span style="color:red;">하지만</span>, 이는 아래와 같이 **두가지 면에서 틀린 주장이다.**

  

  * <span style="color:red;">첫 번째</span>, 성능 분석 저하의 주범이라고 확인되지 않는 한, **이 정도의 성능 차이는 신경 쓸 수준이 못 된다.**

  

  * <span style="color:red;">두 번째</span>, 빈 컬렉션과 배열은 **굳이 새로 할당하지 않고도 반환 할 수 있다.**
    * 다음은 빈 컬렉션을 반환하는 전형적인 코드로, **대부분의 상황에서는 이렇게 하면 된다.**



<hr>



💎 **빈 컬렉션을 반환 하는 올바른 예**

```java
public List<Cheese> getCheeses() {
    return new ArrayList<>(cheesesInStock);
}
```

* 가능성은 작지만, **사용 패턴에 따라 빈 컬렉션 할당이 성능을 눈에 띄게 떨어 뜨릴 수도 있다.**

  * 다행히 **해법은** 간단하다.

  

  * **매번 똑같은 빈 '불변' 컬렉션을 반환**하는 것이다.

  

  * 불변 객체는 자유롭게 공유해도 안전하다.



* 다음 코드에서 사용하는 **Collections.emptyList** 메서드가 그러한 예이다.

  * 집합이 필요하면 **Collections.emptySet**

  

  * 맵이 필요하면 **Colletions.emptyMap**

  

  * <span style="color:red;">단, 이 역시 최적화에 해당하니 꼭 필요할 때만 사용하자.</span>
    * 최적화가 필요하다고 판단되면 수정 전과 후의 성능을 측정하여 실제로 성능이 개선되는지 꼭 확인하자.



<hr>



💎 **최적화 - 빈 컬렉션을 매번 새로 할당하지 않도록 했다.**

```java
public List<Cheese> getCheeses() {
	return cheesesInStock.isEmpty() ? Collections.emptyList()
        : new ArrayList<>(cheesesInStock);
}
```

* 배열을 쓸 때도 마찬가지다.

  * <span style="color:red;">절대 null을 반환하지 말고</span> **길이가 0인 배열을 반환하라.**

  

  * 보통은 단순히 정확한 길이의 배열을 반환하기만 하면 된다.

    * 그 길이가 0일 수도 있을 뿐이다.

    

* 다음 코드에서 **toArray** 메서드에 건넨 **길이 0짜리 배열은** 우리가 **원하는 반환 타입을 알려주는 역할을 한다.**

<hr>


💎 **길이가 0일 수도 있는 배열을 반환하는 올바른 방법**

```java
public Cheese[] getCheeses() {
    return cheesesInStock.toArray(new Cheese[0]);
}
```

* <span style="color:red;">이 방식이 성능을 떨어뜨릴 것 같다면</span> 아래와 같이**길이 0짜리 배열을 미리 선언해두고 매번 그 배열을 반환**하면 된다.
  * **길이 0인 배열은 모두 불변이기 때문이다.**



<br>



💎 최적화 - 빈 배열을 매번 새로 할당하지 않도록 했다.

```java
private static final Cheese[] EMPTY_CHEESE_ARRAY = new Cheese[0];

public Cheese[] getCheeses() {
    return cheesesInStock.toArray(EMPTY_CHEESE_ARRAY);
}
```

* 위 코드의 **getCheeses**는 항상 **EMPTY_CHEESE_ARRAY**를 인수로 넘겨 **toArray**를 호출한다.



* <span style="color:red;">따라서</span> **cheeseInStock**이 비었을 때면 언제나 **EMPTY_CHEESE_ARRAY**를 반환하게 된다.



* <span style="color:red;">단순히 성능을 개선할 목적이라면</span> **toArray에 넘기는 배열을 미리 할당하는 건 추천하지 않는다.**
  * 오히려 성능이 떨어진다는 연구 결과도 있다.



<hr>

💎 **나쁜 예 - 배열을 미리 할당하면 성능이 나빠진다.**

```java
return cheesesInStock.toArray(new Cheese[cheesesInStock.size()]);
```






<hr>

> **null이 아닌, 빈 배열이나 컬렉션을 반환하라.**
>
> null을 반환하는 API는 사용하기 어렵고 오류 처리 코드도 늘어난다.
>
> 그렇다고 성능이 좋은 것도 아니다.









```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

