---
title: 확장할 수 있는 열거 타입이 필요하면 인터페이스를 사용하라 - Effective Java[38]
categories:
- EFFECTIVE_JAVA
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 열거 타입은 모든 상황에서 타입 안전 열거 패턴보다 우수하지만 단 하나의 예외가 있다.

* **타입 안전 열거 패턴은 확장**할 수 있으나 <span style="color:red;">열거 타입은 그럴 수 없다는 것이다.</span>



* 달리 말하면, 타입 안전 열거 패턴은 열거한 값들을 그대로 가져온 다음 값을 더 추가하여 다른 목적으로 쓸 수 있는 반면,  열거 타입은 그렇게 할 수 없다는 뜻이다.



<br>



💎 **대부분의 상황에서 <span style="color:red;">열거 타입을 확장하는건 좋지 않은 생각이야!</span>**

* 확장한 타입의 원소는 기반 타입의 원소로 취급하지만 그 반대는 성립하지 않는다면 이상하다!



* 기반 타입과 확장된 타입들의 원소 모두를 순회할 방법도 마땅치 않다.



* 확장성을 높이려면 고려할 요소가 늘어나 설계와 구현이 더 복잡해진다.



<hr>



💎 **그래도 확장할 수 있는 열거 타입이  쓰이는 한 구석은 있지~  <span style="color:red;">연산 코드 (operation code)</span>**

* 연산 코드의 각 원소는 특정기계가 수행하는 연산을 뜻한다.
  * 이따금 API가 제공하는 기본 연산 외에 사용자 확장 연산을 추가할 수 있도록 열어줘야 할 때가 있다.



* 아래와 같이 **열거 타입**으로 이 효과를 내는 멋진 방법이 있다.

  * 열거 타입이 **임의의 인터페이스를 구현할 수 있다는 사실을 이용**하는 것이다.

  

  * **연산 코드용 인터페이스를 정의**하고 **<span style="color:red;">열거 타입이 이 인터페이스를 구현</span>**하게 하면 된다.

  

  * 이때 <span style="color:red;">열거 타입이 그 인터페이스의 표준 구현체 역할</span>을 한다.



<hr>



💎 **인터페이스를 이용해 확장 가능 열거 타입을 흉내 냈다.**

```java
public interface Operation {
    double apply(double x, double y);
}

public enum BasicOperation implements Operation {
    PLUS("+") {
        public double apply(doulbe x, double y) { return x + y; }
    },
    MINUS("-") {
        public double apply(double x, double y) { return x - y; }
    },
    TIMES("*") {
        public double apply(double x, double y) { return x * y; }
    },
    DIVIDE("/") {
        public double apply(double x, double y) { return x / y; }
    };
    
    private final String symbol;
    
    BasicOperation(String symbol) {
		this.symbol = symbol;
    }

    @Override
    public String toString() {
        return symbol;
    }
}
```

* **열거 타입인 BasicOperation은 확장할 수 없지만** <span style="color:red;">인터페이스인 Operation은 확장할 수 있고</span>, 이 인터페이스를 연산의 타입으로 사용하면 된다.

  

* 이렇게 하면 **Operation**을 구현한 **또 다른 열거 타입을 정의**해 **기본 타입인 BasicOperation을 대체** 할 수 있다.

  * ex) 아래와 같이 앞의 연산 타입을 확장해 지수 연산(EXP)과 나머지 연산(REMAINDER)를 추가해보자.



<hr>



💎 **확장 가능 열거 타입**

```java
public enum ExtendedOperation implements Operation {
    EXP("^") {
        pulbic double apply(double x, double y) {
            return Math.pow(x, y);
        }
    },
    REMAINDER("%") {
        public double apply(double x, double y) {
            return x % y;
        }
    };
	
    private final String symbol;
    
    ExtendedOperation(String symbol) {
        this.symbol = symbol;
    }
    
    @Override
    public String toString() {
        return symbol;
    }
}
```

* 새로 작성한 연산은 기존 연산을 쓰던 곳이면 **어디든 쓸 수 있다.**

  * (BasicOperation이 아닌) Operation 인터페이스를 사용하도록 작성되어 있기만 하면 된다.

  

* **apply**가 인터페이스(Operation)에 선언되어 있으니 열거 타입에 따로 추상 메소드로 선언하지 않아도 된다.



* 개별 인스턴스 수준에서뿐 아니라 **타입 수준에서도**, 기본 열거 타입 대신 **확장된 열거 타입을 넘겨 확장된 열거 타입의 원소 모두를 사용**하게 할 수도 있다.



<br>

```java
public static void main(String[] args) {
    double x = Double.parseDouble(args[0]);
    double y = Double.parseDouble(args[1]);
    test(ExtendedOperation.class, x, y);
}

private static <T extends Enum<T> & Operation> void test (
		Class<T> opEnumType, double x, double y) {
    for (Operation op : opEnumType.getEnumConstants()) {
        System.out.printf("%f %s %f = %f%n", x, op, y, op.apply(x, y));
    }
}
```

* **main** 메소드는 test 메소드에 **ExtendedOperation**의 <span style="color:red;">class 리터럴을 넘겨</span> 확장된 연산들이 무엇인지 알려준다.

  * **여기서 class 리터럴은 한정적 타입 토큰 역할을 한다.**

  

  * **opEnumType** 매개변수의 선언 (`<T extends Enum<T> & Operation> Class<T>`) 은 **Class 객체가 열거 타입인 동시에 Operation의 하위 타입**이어야 한다는 뜻이다.

  

  * 열거 타입이어야 원소를 순회할 수 있고, Opeartion이어야 원소를 뜻하는 연산을 수행할 수 있기 때문이다.

  

* 두 번째 대안은 **Class 객체 대신** <span style="color:red;">한정적 와일드카드 타입인</span> **Collection<? extends Operation>**을 넘기는 방법이다.

```java
public static void main(String[] args) {
    double x = Double.parseDouble(args[0]);
    double y = Double.parseDouble(args[1]);
    test(Arrays.asList(ExtendedOperation.values()), x, y);
}

private static void test(Collection<? extends Operation> opSet,
       		double x, double y) {
    for (Operation op : opSet) {
        System.out.printf("%f %s %f = %f%n", x, op, y, op.apply(x,y));
    }
}
```

* 여러 구현 타입의 연산을 조합해 호출할 수 있게 되었다.



* 반면, 특정 연산에서는 EnumSet과 EnumMap을 사용하지 못한다.





<hr>



##### 🔗 인터페이스를 확장한 열거 타입 흉내 방식도 사소한 문제가 있어!



* <span style="color:red;">열거 타입끼리 구현을 상속할 수 없다는 점이다.</span>



* 아무 상태에도 의존하지 않는 경우에는 **디폴트 구현**을 이용해 **인터페이스에 추가하는 방법**이 있다.





<hr>



> 열거 타입 자체는 확장할 수 없지만, 
>
> **인터페이스와 그 인터페이스를 구현하는 기본 열거 타입을 함께 사용해 같은 효과를 낼 수 있다.**
>
> 이렇게 하면 클라이언트는 이 인터페이스를 구현해 자신만의 열거 타입(혹은 다른 타입)을 만들 수 있다.
>
> 
>
> 그리고 API가(기본 열거 타입을 직접 명시하지 않고) 인터페이스 기반으로 작성되었다면 
>
> 기본 열거 타입의 인스턴스가 쓰이는 모든곳을 새로 확장한 열거 타입의 인스턴스로 대체해 사용할 수 있다.







```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

