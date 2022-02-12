---
title: 전통적인 for 문보다는 for-each 문을 사용하라 - Effective Java[58]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗  while 문 보다는 낫지만 가장 좋은 방법이이 아닌 관용구들


* 다음은 전통적인 for문으로 컬렉션을 순회하는 코드다.

<br>



💎 **컬렉션 순회하기 - 더 나은 방법이 있다.**

```java
for (Iterator<Element> i = c.iterator(); i.hasNext();) {
    Element e = i.next();
    ... // e로 무언가를 한다.
}
```

*  다음은 전통적인 for문으로 배열을 순회하는 코드이다.

<br>



💎 **배열 순회하기 - 더 나은 방법이 있다.**

```java
for (int i = 0; i < a.length; i++) {
    ... // a[i]로 무언가를 한다.
}
```

* 반복자와 인덱스 변수는 모두 코드를 지저분하게 할 뿐 **우리가 진짜 필요한 건 원소들 뿐이다.**

  * 더군다나 이처럼 쓰이는 **요소 종류가 늘어나면 오류가 생길 가능성이 높아진다.**

  

  * 1회 반복에서 반복자는 세 번 등장하며, 인덱스는 네 번이나 등장하여 **변수를 잘못 사용할 틈새가 넓어진다.**

  

  * 혹시라도 잘못된 변수를 사용했을 때 **컴파일러가 잡아주리라는 보장도 없다.**

  

  * 마지막으로 **컬렉션이나 배열이냐에 따라 코드 형태가 상당히 달라지므로 주의**해야 한다.



<hr>



##### 💎 이상의 문제는 for-each 문을 사용하면 모두 해결된다.

* 참고로 **for-each** 문의 정식 이름은 '**향상된 for 문(enhanced for statement)**'이다.



* **반복자와 인덱스 변수를 사용하지 않으니** <span style="color:red;">코드가 깔끔해지고 오류가 날 일도 없다.</span>
  * 하나의 관용구로 컬렉션과 배열을 모두 처리할 수 있어서 어떤 컨테이너를 다루는지는 신경 쓰지 않아도 된다.

<br>



💎 **컬렉션과 배열을 순회하는 올바른 관용구**

```java
for (Element e : elements) {
    ... // e로 무언가를 한다.
}
```

* 반복 대상이 컬렉션이든 배열이든, **for-each** 문을 사용해도 속도는 그대로다.
  * **for-each** 문이 만들어내는 코드는 사람이 손으로 최적화한것과 사실상 같기 때문이다.



* **컬렉션을 중첩해 순회해야 한다면** <span style="color:red;">for-each 문의 이점이 더욱 커진다.</span>
  * 다음 코드는 반복문을 중첩할 때 **흔히 저주르는 실수가 담겨있다.**



```java
enum Suit { CLUB, DIAMOND, HEART, SPADE }
enum RANK { AEC, DEUCE, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT,
          NINE, TEN, JACK, QUEEN, KING }
...
   
static Collection<Suit> = Arrays.asList(Suit.values());
static Collection<Rank> = Arrays.asList(Rank.values());

List<Card> deck = new ArrayList<>();
for (Iterator<Suit> i = suits.iterator(); i.hasNext(); ) {
    for (Iterator<Rank> j = ranks.iterator(); j.hasNext();) {
        deck.add(new Card(i.next(), j.next()));
    }
}
```

* 위 코드의 문제는 바깥 컬렉션(**suits**)의 반복자에서 **next** 메서드가 너무 많이 불린다는 것이다.

  * 마지막 줄의 i.next()를 보면 '숫자(Suit) 하나당' 한번 씩만 불려야 하는데, 안쪽 반복문에서 호출되는 바람에 '카드(Rank) 하나당' 한 번씩 불리고 있다.

  

  * 그래서 숫자가 바닥나면 반복문에서 **NoSuchElementException**을 던진다.



* 정말 운이 나빠서 바깥 컬렉션의 크기가 안쪽 컬렉션 크기의 배수라면 이 반복문은 예외를 던지지 않고 종료한다.

  * 물론 우리가 원하는 일을 수행하지 않은 채 말이다.

  

  * ex) 다음의 주사위를 두 번 굴렸을 때 나올 수 있는 모든 경우의 수를 출력하는 코드를 살펴보자.

<br>



💎 **같은 버그, 다른 증상!**

```java
enum Face { ONE, TWO, THREE, FOUR, FIVE, SIX }
...
Collection<Face> faces = EnumSet.allOf(Face.class);

for (Iterator<Face> i = faces.iterator(); i.hasNext();) {
    for (Iterator<Face> j = faces.iterator(); j.hasNext();) {
        System.out.println(i.next() + " " + j.next(););
    }
}
```

* 위 프로그램은 예외를 던지진 않지만, 가능한 조합을 단 여섯 쌍만 출력하고 끝나버린다. 

  * 36개 조합이 나와야 한다.

  

  * 이 문제를 해결하려면 아래와 같이 바깥 반복문에서 바깥 원소를 저장하는 변수를 하나 추가해야 한다.

<br>



💎 **문제는 고쳤지만 보기 좋진 않다. 더 나은 방법이 있다!**

```java
for (Iterator<Suit> i = suits.iterator(); i.hasNext();) {
    Suit suit = i.next();
    for (Iterator<Rank> j = ranks.iterator(); j.hasNext();) {
        deck.add(new Card(suit, j.next());
    }
}
```

* 위 코드의 문제점은 아래와 같이 for-each 문을 중첩하는 것으로 간단히 해결된다.
  * 코드도 간결해진다.

<br>



💎 **컬렉션이나 배열의 중첩 반복을 위한 권장 관용구**

```java
for (Suit suit : suits) {
    for (Rank rank : ranks) {
        deck.add(new Card(suit, rank));
    }
}
```



<hr>



##### 💎 for-each 문을 <span style="color:red;">사용할 수 없는 상황 세 가지</span>

* **파괴적인 필터링(destructive filtering)** 

  * **컬렉션을 순회하면서 선택된 원소를 제거해야 한다면** 반복자의 **remove** 메서드를 호출해야 한다.

  

  * 자바 8부터는 **Collection**의 **removeIf** 메서드를 사용해 컬렉션을 명시적으로 순회하는 일을 피할 수 있다.



* **변형(transforming)**
  * **리스트나 배열을 순회하면서 그 원소의 값 일부 혹은 전체를 교체해야 한다면** <span style="color:red;">리스트의 반복자나 배열의 인덱스를 사용해야 한다.</span>



* **병렬 반복(parallel iteration)** 
  * **여러 컬렉션을 병렬로 순회해야 한다면** <span style="color:red;">각각의 반복자와 인덱스 변수를 사용해 엄격하고 명시적으로 제어해야 한다</span>



<hr>



💎 **for-each 문은 컬렉션과 배열은 물론 Iterable 인터페이스를 구현한 객체라면 무엇이든 순회 가능**

* **Iterable** 인터페이스는 다음과 같이 메서드가 단 하나 뿐이다.

```java
public interface Iterable<E> {
    // 이 객체의 원소들을 순회하는 반복자를 반환한다.
    Iterator<E> iterator();
}
```

* **Iterable**을 처음부터 직접 구현하기는 까다롭지만, 원소들의 묶음을 표현하는 타입을 작성해야 한다면 **Iterable**을 구현하는 쪽으로 고민해봐야 한다.
  * 해당 타입에서 **Collection** 인터페이스는 구현하지 않기로 했더라도 말이다.



* **Iterable**을 구현해두면 그 타입을 사용하는 프로그래머가 **for-each** 문을 사용 할 때마다 편리할 것이다.



<hr>


> 전통적인 for 문과 비교했을 때 for-each 문은 명료하고, 유연하고, 버그를 예방해준다.
>
> 성능 저하도 없다.
>
> 가능한 모든 곳에서 for 문이 아닌 for-each문을 사용하되 위의 3가지 상황에서는 피하자.







```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

