---
title: 가변 인수는 신중히 사용하라 - Effective Java[53]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗  가변 인수는 인수 개수가 정해지지 않았을 때 아주 유용하다.

* 가변인수(**varargs**) 메서드는 명시한 타입의 인수를 0개 이상 받을 수 있다.

  * 가변인수 메서드를 호출하면, 가장 먼저 인수의 개수와 길이가 같은 배열을 만들고 인수들을 이 배열에 저장하여 가변인수 메서드에 건네준다.

  

  * 다음은 입력받은 **int** 인수들의 합을 계산해주는 가변인수 메서드다.

* <br>




💎 **간단한 가변인수 활용 예**

```java
static int sum(int... args) {
    int sum = 0;
    for (int arg : args) {
        sum += args;
    }
    return sum;
}
```

* 인수 1개이상 이어야 할 때도 있다.
  * ex) 최솟값을 찾는 메서드인데 아래와 같이 인수 0개만 받을 수도 있도록 설계하는 건 좋지 않다.



💎 **인수가 1개 이상이어야 하는 가변인수 메서드 - 잘못 구현한 예!**

```java
static int min(int... args) {
    if (args.length == 0) {
        throw new IllegalArgumentException("인수가 1개 이상 필요합니다");
    }
    
    int min = args[0];
    for (int i = 1; i < args.length; i++) {
        min = args[i];
    }
    
    return min;
}
```

* 위 방식의 가장 큰 문제는 인수를 0개만 넣어 호출하면 런타임에 실패한다는 점이다.
  * 코드도 지저분하다



* 위 문제는 아래와 같이 매개변수를 2개 받도록 하여 해결하는 방법이 있다.



💎 **해결책 - 인수가 1개 이상이어야 할 때 가변인수를 제대로 사용하는 방법**

```java
static int min(int firstArgs, int ... remainingArgs) {
    int min = firstArg;
    for (int arg : remainArgs) {
        if (arg < min) {
            min = arg;
        }
    }
    return min;
}
```

* 이상의 예에서 보듯, 가변인수는 인수 개수가 정해지지 않았을 때 아주 유용하다

  * **printf**는 가변인수와 한 묶음으로 자바에 도입되었고, 이때 핵심 **리플렉션** 기능도 재정비되었다.

  

  * **printf**와 **리플렉션** 모두 가변인수 덕을 톡톡히 보고 있다.



<hr>



##### 🔗 성능에 민감한 상황이라면 가변인수가 걸림돌이 될 수가 있어..

* 가변인수 메서드는 호출될 때마다 배열을 새로 하나 할당하고 초기화 한다.

  * 다행히 이 비용을 감당 할 수 있는 없지만 가변인수의 유연성이 필요할 때 선택할 수 있는 <span style="color:red">멋진 패턴이 있다.</span>

    * ex)  해당 메서드 호출의 95%가 인수를 3개 이하로 사용 한다고 가정하고 다음과 같이 인수가 0개 인 것처럼 4개인 것 까지, 총 5개를 다중정의하자.

    

    * 마지막 다중정의 메서드가 인수 4개 이상인 5%의 호출을 담당하는 것이다.

```java
public void foo() {}
public void foo(int a1) {}
public void foo(int a1, int a2) {}
public void foo(int a1, int a2, int a3) {}
public void foo(int a1, int a2, int a3, int... rest) {}
```

* 따라서 메서드 호출 중 단 5%만이 배열을 생성한다. 대다수의 성능 최적화와 마찬가지로 이 기법도 보통 때는 별 이득이 없지만, 꼭 필요한 특수 상황에서는 사막의 오아시스가 되어줄 것이다.



* **EnumSet**의 정적 팩토리도 이 기법을 사용해 **열거 타입 집합 생성 비용을 최소화한다.**
  * **EnumSet**은 비트 필드를 대체하면서 성능까지 유지해야 하므로 **아주 적절하게 활용한 예라 할 수 있다.**



<hr>

> 인수 개수가 일정하지 않은 메서드를 정의해야 한다면 가변인수가 반드시 필요하다.
>
> 메서드를 정의할 때 필수 매개변수는 가변인수 앞에 두고, 가변인수를 사용할 때는 성능 문제까지 고려하자.









```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

