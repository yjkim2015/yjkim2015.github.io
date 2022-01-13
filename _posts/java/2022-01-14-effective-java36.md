---
title: 비트 필드 대신 EnumSet을 사용하라 - Effective Java[36]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 구닥다리 기법 feat 비트 필드 열거 상수

* 열거한 값들이 주로 (단독이 아닌) 집합으로 사용될 경우, 예전에는 각 상수에 서로 다른 2의 거듭제곱 값을 할당한 **정수 열거 패턴**을 사용해왔다.



<br>


💎 **비트 필드 열거 상수**

```java
public class Text {
    public static final int STYLE_BOLD			= 1 << 0; //1
    public static final int STYLE_ITALIC		= 1 << 1; //2
    public static final int STYLE_UNDERLINE 	= 1 << 2; //4
    public static final int STYLE_STRIKETHROUGH = 1 << 3; //8
    
    // 매개변수 styles는 0개 이상의 STYLE_ 상수를 비트별 OR한 값이다.
    public void applyStyles(int styles) { ... }
}
```

<br>



아래와 같은 식으로 **비트별 OR**을 사용해 여러 상수를 하나의 집합으로 모을 수 있으며, 이렇게 만들어진 집합을 **비트 필드(bit field)**라고 한다.

```java
text.applyStyles(STYLE_BOLD | STYLE_ITALIC);
```

* 비트 필드를 사용하면 비트별 연산을 사용해 합집합과 교집합 같은 집합 연산을 효율적으로 수행할 수 있다.



* <span style="color:red;">하지만</span> **비트 필드는 정수 열거 상수의 단점을 그대로 지니며**, 추가로 다음과 같은 문제까지 안고 있다.

  * 비트 필드 값이 그대로 출력되면 단순한 정수 열거 상수를 출력할 때보다 **해석하기가 훨씬 어렵다.**

  

  * 비트 필드 하나에 녹아 있는 모든 원소를 순회하기도 까다롭다.

  

  * **최대 몇 비트가 필요한지를 API 작성 시 미리 예측하여 적절한 타입(보통은 int나 long)을 선택해야 한다.**
    * API를 수정하지 않고는 비트 수(32비트 or 64비트)를 더 늘릴 수 없기 때문이다.



<hr>





#### 🔗 더 나은 대안 EnumSet@@

* 정수 상수보다 열거 타입을 선호하는 프로그래머 중에도 상수 집합을 주고 받아야 할 때는 여전히 비트 필드를 사용하기도 한다.



* <span style="color:red;">하지만</span> 이제 더 나은 **대안**이 있다. **java.util 패키지의 EnumSet 클래스는 열거 타입 상수의 값으로 구성된 집합을 <span style="color:red;">효과적으로 표현해준다.</span>**



* **Set 인터페이스를 완벽히 구현**하며, **타입 안전**하고, **다른 어떤 Set 구현체와도 함께 사용**할 수 있다.



* <span style="color:red;">하지만</span> **EnumSet**의 내부는 비트 벡터로 구현되었다.

  * 원소가 총 64개 이하라면, <span style="color:red;">즉</span> 대부분의 경우에 **EnumSet** 전체를 **long 변수 하나로 표현**하여 **비트 필드에 비견되는 성능**을 보여준다.

  

  * **removeAll**과 **retainAll** 같은 대량 작업은 (비트 필드를 사용할 때 쓰는 것과 같은) **비트를 효율적으로 처리할 수 있는 산술 연산을 써서 구현**했다.

  

  * 그러면서도 비트를 직접 다룰 때 흔히 겪는 오류들에서 해방된다.
    * 난해한 작업을 EnumSet이 다 처리해주기 때문이다.



<hr>



💎 **EnumSet - 비트 필드를 대체하는 현대적 기법**

```java
public class Text {
    public enum Style { BOLD, ITALIC, UNDERLINE, STRIKERTHROUGH }
    
    // 어떤 Set을 넘겨도 되나, EnumSet이 가장 좋다.
    public void applyStyles(Set<Style> styles) { ... }

    public static void main(String[] args) {
        Text text = new Text();
        text.applyStyles(EnumSet.of(Style.BOLD, Style.ITALIC));
    }
}
```

* 위 코드에서 **applyStyles** 메소드에 **EnumSet**을 파라미터로 넘기는데 **EnumSet**은 집합 생성 등 **다양한 기능의 정적 팩토리를 제공**하며, 그 중 **of 메소드를 사용**했다.



* applyStyles 메소드가 `EnumSet<Style>`이 아닌 `Set<Style>`을 받도록 선언되있는 이유는 뭘까?

  * **모든 클라이언트가 EnumSet을 건네리라 짐작되는 상황**이라도 **이왕이면 인터페이스로 받는게** <span style="color:red;">일반적으로 좋은 습관이다.</span>

  

  * 이렇게 하면 좀 특이한 클라이언트가 다른 **Set 구현체를** 넘기더라도 처리할 수 있어서 그렇다.



<hr>



> **열거할 수 있는 타입을 한데 모아 집합 형태로 사용한다고 해도 비트 필드를 사용할 이유는 없다.**
>
> EnumSet 클래스가 비트 필드 수준의 명료함과 성능을 제공하고 열거 타입의 장점까지 선사하기 떄문이다.
>
> EnumSet의 유일한 단점이라면 (자바 9까지는 아직) 불변 EnumSet을 만들 수 없다는 것이다.
>
> 향후 릴리즈에서 수정되기 전까진 (명확성과 성능이 조금 희생되지만) Collections.unmodifiableSet으로 EnumSet을 감싸 사용할 수 있다.







```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

