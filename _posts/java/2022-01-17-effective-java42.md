---
title: 익명 클래스보다는 람다를 사용하라 - Effective Java[42]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 익명 클래스

* 예전에는 자바에서 **함수 타입**을 표현할 때 추**상 메소드를 하나만 담은 인터페이스**(드물게는 추상 클래스)를 사용했다.

  * 이런 인터페이스의 인스턴스를 **함수 객체(function object)**라고 하여, 특정 함수나 동작을 나타내는데 썼다.

  

* 1997년 JDK 1.1이 등장하면서 함수 객체를 만드는 주요 수단은 **익명 클래스**가 되었다.



<hr>


##### 💎 익명 클래스의 인스턴스를 함수 객체로 사용 - 낡은 기법이다.

```java
Collections.sort(word, new Comparator<String>() {
   public int compare(String s1, String s2) {
       return Integer.compare(s1.length(), s2.length());
   } 
});
```

* **전략 패턴**처럼, 함수 객체를 사용하는 과거 객체 지향 디자인 패턴에는 익명클래스면 충분했다.



* 위 코드에서 **Comparator 인터페이스**가 **정렬을 담당하는 추상 전략**을 뜻하며, 문자열을 정렬하는 구체적인 전략을 익명 클래스로 구현했다.
  * <span style="color:red;">하지만</span> 익명 클래스 방식은 코드가 너무 길기 떄문에 **자바는 함수형 프로그래밍에 적합하지 않았다.**



<hr>



##### 💎 함수형 인터페이스 

* 자바 8에와서 **추상 메소드 하나짜리 인터페이스**는 특별한 의미를 인정받아 특별한 대우를 받게 되었다.



* **함수형 인터페이스**라 불리는 이 인터페이스들의 인스턴스를 <span style="color:red;">람다식</span>을 사용해 만들 수 있게 된 것이다.



* <span style="color:red;">람다</span>는 함수나 익명 클래스와 개념은 비슷하지만 코드는 훨씬 간결하다.
  * 위 코드의 익명 클래스를 람다식으로 아래와 같이 바꿔보자.

<br>

💎 **람다식을 함수 객체로 사용 - 익명 클래스 대체**

```java
Collections.sort(word, 
                (s1, s2) -> Integer.compare(s1.length(), s2.length()));
```

* 여기서 람다, 매개변수(s1, s2), 반환값의 타입은 각각 (`Comparator<String>`), **String**, **int**지만 코드에서는 언급이 없다.

  * **컴파일러가** 문맥을 살펴 **타입을 추론**해준 것이다.

  

  * **상황에 따라** 컴파일러가 타입을 결정하지 못할 수도 있는데, 그럴 때는 **프로그래머가 직접 명시 해야 한다.**

  

  * **타입을 명시해야 코드가 더 명확할 때만 제외하고는**, <span style="color:red;">람다의 모든 매개변수 타입은 생략하자</span>

    * 컴파일러가 "타입을 알 수 없다"는 오류를 낼 때만 해당 타입을 명시하면 된다.

    

    * 반환값이나 람다식 전체를 형변환해야 할 때도 있겠지만, 아주 드물 것이다.

    

* 람다 자리에 비교자 생성 메소드를 사용하면 이 코드를 더 간결하게 만들 수 있다.

<br>

```java
Collections.sort(word, comparingInt(String::length));
```

<br>

* 더 나아가 자바 8 때 List 인터페이스에 추가된 sort 메소드를 이용하면 더욱 짧아진다.

```java
words.sort(comparingInt(String::length));
```

<br>



> 타입 추론에 관해서 제네릭의 로 타입을 쓰지 말고, 제네릭, 제네릭 메소드를 쓰라고 했다.
>
> 이 내용들은 람다와 함께 쓸 때는 두 배로 중요해진다.
>
> 컴파일러가 타입을 추론하는 데 필요한 타입 정보 대부분을 제네릭에서 얻기 때문이다.
>
> 
>
> 프로그래머가 이 정보를 제공하지 않으면 컴파일러는 람다의 타입을 추론할 수 없게 되어, 결국 프로그래머가 일일이 명시 해야 한다.
>
>
> 
> 좋은 예로, 위 코드에서 인수 words가 매개변수화 타입인 List<String>이 아니라 로타입인 List였다면 컴파일 오류가 났을 것이다.



<hr>



##### 💎 함수 객체의 실용적 사용 : 람다

* 람다를 언어 차원에서 지원하면서 기존에는 적합하지 않았던 곳에서도 함수 객체를 실용적으로 사용할 수 있게 되었다.
  * ex) 열거 타입의 Operation 클래스



💎 **상수별 클래스 몸체와 데이터를 사용한 열거 타입**

```java
public enum Operation {
    PLUS("+") {
        public double apply(double x, double y) { return x + y; }
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
    
    Operation(String symbol) { this.symbol = symbol; }
    
	@Override
    public String toString() {
        return symbol;
    }
    
    public abstract double apply(double x, double y);
}
```

* 앞서 상수별 클래스 몸체를 구현하는 방식보다는 **열거 타입에 인스턴스 필드를 두는 편이 낫다**고 했다.

  * 람다를 이용하면 후자의 방식, **즉 열거 타입의 인스턴스 필드를 이용하는 방식**으로 **상수별로 다르게 동작하는 코드를 쉽게 구현**할 수 있다.

    

  * 단순히 **각 열거 타입 상수의 동작을 람다로 구현해 생성자에 넘기고, 생성자는 이 람다를 인스턴스 필드로 저장해둔다**. 그런 다음 **apply** 메소드에서 필드에 저장된 람다를 호출하기만 하면 된다.

<br>



💎 **함수 객체(람다)를 인스턴스 필드에 저장해 상수별 동작을 구현한 열거 타입**

```java
public enum Operation {
    PLUS  ("+", (x, y) -> x + y),
    MINUS ("-", (x, y) -> x - y),
    TIMES ("*", (x, y) -> x * y),
    DIVIDE("/", (x, y) -> x / y);
    
    private final String symbol;
    private final DoubleBinaryOperator op;
    
    Operation(String symbol, DoubleBinaryOperator op) {
        this.symbol = symbol;
        this.op = op;
    }
    
    @Override
    public String toString() {
        return symbol;
    }
		
    public double apply(double x, double y){
        return op.applyAsDouble(x, y);
    }
}
```



* 이 코드에서 열거 타입 상수의 동작을 표현한 람다를 **DoubleBinaryOperator** 인터페이스 변수에 할당했다.



* **DoubleBinaryOperator**는 java.util.function 패키지가 제공하는 다양한 함수 인터페이스 중 하나로, double 타입 인수 2개를 받아 double 타입 결과를 돌려준다.



<hr>



##### 💎 람다가 항상 좋진 않아!

* 람다 기반 Operation 열거 타입을 보면 상수별 클래스 몸체는 더 이상 사용할 이유가 없다고 느낄지 모르지만, <span style="color:red;">꼭 그렇지는 않다.</span>



* 메소드나 클래스와 달리, <span style="color:red;">람다는 이름이 없고 문서화도 못한다.</span>



* <span style="color:red;">따라서</span> 코드 자체로 **동작이 명확히 설명되지 않거나 코드 줄 수가 많아지면** <span style="color:red">람다를 쓰지 말아야 한다.</span>



* 람다는 **한 줄 일 때 가장 좋고 길거야 세 줄 안에** 끝내는 게 좋다.
  * 람다가 길거나 읽기 어렵다면 더 간단히 줄여보거나 람다를 쓰지 않는 쪽으로 리팩토링해라



* **열거 타입 생성자에 넘겨지는 인수들의 타입도 컴파일타임에 추론된다.**

  * <span style="color:red;">따라서</span> 열거 타입 생성자 안의 람다는 열거 타입의 인스턴스 멤버에 접근할 수 없다.

  

  * **인스턴스는 런타임에 만들어지기 때문이다**.

  

  * <span style="color:red;">따라서</span> 상수별 동작을 단 몇 줄로 구현하기 어렵거나, 인스턴스 필드나 메소드를 사용해야만 하는 상황이라면 상수별 클래스 몸체를 사용해야 한다.



<hr>



##### 💎 람다로 대체할 수 없는 곳

* **람다는 함수형 인터페이스에서만 쓰인다.**



* **추상 클래스의 인스턴스를 만들 때** 람다를 쓸 수 없으니, **익명 클래스를 써야 한다.**



* 비슷하게 추상 메소드가 여러 개인 인터페이스의 인스턴스를 만들 때도 익명 클래스를 쓸 수 있다.



* **람다는 자신을 참조 할 수 없다**.

  * 람다에서의 **this** 키워드는 바깥 인스턴스를 가리킨다.

  

  * <span style="color:red;">반면</span>, 익명 클래스에서의 **this**는 익명 클래스의 **인스턴스 자신**을 가리킨다.

  

  * **그래서 함수 객체가 자신을 참조해야 한다면** <span style="color:red;">반드시 익명 클래스를 써야 한다.</span>



<hr>



##### 💎 람다를 직렬화하는 일은 극히 삼가야 한다

* **람다도 익명 클래스처럼 직렬화 형태가 구현별로 다를 수 있다.**



* 따라서 람다를 직렬화 하는 일은 극히 삼가야 한다.



* 직렬화해야만 하는 함수 객체가 있다면(가령 Comparator처럼) **private 정적 중첩 클래스의 인스턴스를 사용하자.**



<hr>



> 자바가 8로 판올림되면서 작은 함수 객체를 구현하는 데 적합한 람다가 도입되었다.
>
> 
>
> **익명 클래스는 (함수형 인터페이스가 아닌) 타입의 인스턴스를 만들 때만 사용하라.**
>
>
> 람다는 작은 함수 객체를 아주 쉽게 표현할 수 있어 함수형 프로그래밍의 지평을 열었다.





```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

