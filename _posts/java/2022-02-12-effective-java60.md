---
title: 정확한 답이 필요하다면 float와 double은 피하라 - Effective Java[60]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗  float와 double 타입은 특히 금융 관련 계산과는 맞지 않는다.


* **float**와 **double** 타입은 과학과 공학 계산용으로 설계되었다.


  * 이진 부동소수점 연산에 쓰이며, 넓은 범위의 수를 빠르게 정밀한 '**근사치**'로 계산하도록 세심하게 설계되었다.

  


  * <span style="color:red;">따라서</span> **정확한 결과가 필요할 때는 사용하면 안 된다.**


    * ex) 주머니에 1.03 달러가 있었는데 그중 42센트를 썼다고 가정해보자. 남은 돈은 얼마인가? 다음은 이 문제의 답을 구하기 위해 '어설프게' 작성해본 코드다.

    ```java
    System.out.println(1.03 - 0.42);
    ```

    * 안타깝게도 이 코드는 0.6100000000000001을 출력한다. 이는 특수한 사례도 아니다.



* 결괏값을 출력하기 전에 반올림하면 해결되리라 생각할지 모르지만, 반올림을 해도 틀린 답이 나올 수 있다.

  * ex) 주머니에는 1달러가 있고, 선반에 10센트, 20센트, 30센트, ... 1달러짜리의 맛있는 사탕이 놓여 있다고 해보자.

  

  * 10센트짜리부터 하나씩, 살 수 있을 때까지 사보자.

    * 사탕을 몇 개나 살 수 있고, 잔돈을 얼마가 남을까?

    

    * 다음은 이 문제의 답을 구하는 '어설픈' 코드다.

<br>



💎 **오류 발생! 금융 계산에 부동소수 타입을 사용했다**

```java
public static void main(String[] args) {
    double funds = 1.00;
    int itemBought = 0;
    for (double price = 0.10; funds >= price; price += 0.10) {
        funds -= price;
        itemBought++;
    }
    System.out.println(itemsBought + "개 구입");
    System.out.println("잔돈(달러): " + funds);
}
```

* 프로그램을 실행해보면 사탕 3개를 구입한 후 잔돈은 0.399~~~9달러가 남았음을 알게 된다.

  * 물론 잘못된 결과다

  

  * 이 문제를 올바로 해결하려면 금융 계산에는 **BigDecimal**, **int** 혹은 **long**을 사용해야 한다.



* 다음은 앞서의 코드에서 **double** 타입을 **BigDecimal**로 교체만 한 코드이다.
  * **BigDecimal**의 생성자 중 문자열을 받는 생성자를 사용한 이유는 계산 시 부정확한 값이 사용되는 걸 막기 위해 필요한 조치다.



<br>

💎 **BigDeicmal을 사용한 해법, 속도가 느리고 쓰기 불편하다.**

```java
public static void main(String[] args) {
    final BigDecimal TEN_CENTS = new BigDecimal(".10");
    
    int itemsBought = 0;
    BigDecimal funds = new BigDecimal("1.00");
    for (BigDecimal price = TEN_CENTS; funds.compareTo(price) >=0;
        price = price.add(TEN_CENTS)) {
        funds = funds.subtract(price);
        itemsBought++;
    }
    System.out.println(itemsBought + "개 구입");
    System.out.println("잔돈(달러): " + funds);
}
```

* 위 프로그램은 정상적으로 동작하지만, **BigDecimal**에는 단점이 두 가지가 있다.

  * <span style="color:red;">기본 타입보다 쓰기가 훨씬 불편하고, 훨씬 느리다.</span>

  

  * 단발성 계산이라면 느리다는 문제를 무시할 수 있지만, 쓰기 불편하다는 점은 못내 아쉬울 것이다.



* **BigDiemcal의 대안**으로 **int** 혹은 **long** 타입을 쓸 수도 있다.
  * 그럴 경우 <span style="color:red;">다룰 수 있는 값의 크기가 제한되고, 소수점을 직접 관리해야 한다.</span>



💎 **정수 타입을 사용한 해법**

```java
public static void main(String[] args) {
    int itemsBought = 0;
    int funds = 100;
    for (int price = 10; funds >= price; price+= 10) {
        funds -= price;
        itemsBought++;
    }
    System.out.println(itemsBought + "개 구입");
    System.out.println("잔돈(센트): " +funds);
}
```



<hr>



> **정확한 답이 필요한 계산에는 float나 double을 피하라**. 소수점 추적은 시스템에 맡기고, 코딩 시의 불편함이나 성능 저하를 신경 쓰지 않겠다면 BigDecimal을 사용하라.



> BigDecimal이 제공하는 여덟 가지 반올림 모드를 이용하여 반올림을 완벽히 제어할 수 있다.
>
> 법으로 정해진 반올림을 수행해야 하는 비즈니스 계산에서 아주 편리한 기능이다.
>
> **반면, 성능이 중요하고 소수점을 직접 추적할 수 있고 숫자가 너무 크지 않다면 int나 long을 사용하라.**



> <span style="color:red;">숫자를 아홉자리 십진수로 표현할 수 있다면</span> **int**를 사용하고, <span style="color:red;">열여덟 자리 십진수로 표현할 수 있다면</span> **long**을 사용하라.
>
> <span style="color:red;">열여덟 자리를 넘어가면</span> **BigDecimal**을 사용해야 한다.







```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

