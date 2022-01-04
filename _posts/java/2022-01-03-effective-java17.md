---
title: 변경 가능성을 최소화하라
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



<span style="color:red;">불변클래스</span>란 간단히 말해 그 인스턴스의 내부 값을 수정할 수 없는 클래스다.

**불변 인스턴스에 저장된 정보는 고정되어 객체가 파괴되는 순간 까지 절대 달라지지 않는다.**

불변 클래스는 가변 클래스보다 설계하고 구현하고 사용하기 쉬우며, 오류가 생기기도 적고 훨씬 안전하다.

<hr>




#### 🔗 클래스를 불변으로 만드는 규칙

* **객체의 상태를 변경하는 메소드(변경자)를 제공하지 않는다.**
* **클래스를 확장할 수 없도록한다.**
  * 하위 클래스에서 부주의하게 혹은 나쁜 의도로 객체의 상태를 변하게 만드는 사태를 막아준다. 
  * 상속을 막는 대표적인 방법은 클래스를 final로 선언하는 것이다.

* **모든 필드를 final로 선언한다.**

  * 시스템이 강제하는 수단을 이용해 설계자의 의도를 명확히 드러내는 방법이다.

    새로 생성된 인스턴스를 동기화 없이 다른 스레드로 건네도 문제없이 동작하게끔 보장하는 데도 필요하다.

* **모든 필드를 private으로 선언한다.**

  * 필드가 참조하는 가변 객체를 클라이언트에서 직접 접근해 수정하는 일을 막아준다.

    기술적으로는 기본 타입 필드나 불변 객체를 참조하는 필드를 public final로만 선언해도 불변 객체가 되지만, 이렇게 하면 다음 릴리스에서 내부 표현을 바꾸지 못하므로 권하지는 않는다.

* **자신 외에는 내부의 가변 컴포넌트에 접근할 수 없도록 한다.**
  * 클래스에 가변객체를 참조하는 필드가 하나라도 있다면 클라이언트에서 그 객체의 참조를 얻을 수 없도록 해야 한다. 
  * 이런 필드는 절대 클라이언트가 제공한 객체 참조를 가리키게 해서는 안 되며, 접근자 메소드가 그 필드를 그대로 반환해서도 안 된다. <span style="color:red;">생성자 , 접근자, readObject 메소드 모두에서 방어적 복사를 수행해야한다.</span>

<hr>



#### 🔗 함수형 프로그래밍

아래의 불변 복소수 클래스 예시를 보며 함수형 프로그래밍에 대해 알아보자.

이 클래스는 복소수(실수부와 허수부로 구성된 수)를 표현하며 생성자와 사칙연산 메소드들을 정의했다.

```java
public final class Complex {
	private final double re;
    private final double im;
    
    public Complex(double re, double im) {
        this.re = re;
        this.im = im;
    }
    
    public double realPart() { return re; }
    public double imaginaryPart() { return im; }
    
    public Complex plus(Complex c) {
        return new Complex(re + c.re, im + c.im);
    }
    public Complex minus(Complex c) {
        return new Complex(re - c.re, im - c.im);
    }
   	
    //...
    
    @Override
    public boolean equals(Object o) {
        if ( o == this ) {
            return true;
        }
        if ( !(o instanceof Complex) ) {
            return false;
        }
        Complex c = (Complex) o;
        
        //== 대신 compare를 사용하는 이유는 double,float엔 부동소수점 있기 때문
        return Double.compare(c.re, re) == 0 && Double.compare(c.im, im) == 0;
    }
   
    @Override
    public int hashCode() {
        return 31 * Double.hashCode(re) + Double.hashCode(im);
    }
    
    @Override
    public String toString() {
        return "(" + re + " + " + im + "i)";
    }
}
```

**보다가 재미있는 점을 발견했을 것이다.** 

**사칙 연산 메소드들은 인터턴스 자신은 수정하지 않고 새로운 Complex 인스턴스를 만들어 반환한다는 점이다.**

이처럼 피연산자에 함수를 적용해 그 결과를 반환하지만, 피연산자 자체는 그대로인 프로그래밍 패턴을 <span style="color:red;">함수형 프로그래밍</span>이라 한다.

<br>

또한 메소드 이름으로 (add) 같은 동사 대신 (plus) 같은 전치사를 사용한 점에도 주목해야 한다.

**이는 해당 메소드가 객체의 값을 변경하지 않는다는 사실을 강조하려는 의도이다.**

<br>

***<span style="color:red;">함수형 프로그래밍 방식은 코드에서 불변이 되는 영역의 비율이 높아지는 장점을 누릴 수 있다.</span>***



<hr>



#### 🔗 불변 객체의 장점

* **불변 객체는 단순하다.**
  * 불변 객체는 생성된 시점의 상태를 파괴될 때까지 그대로 간직한다.
* **불변 객체는 근본적으로 스레드 안전하여 따로 동기화할 필요가 없다.**
  * 불변 객체에 대해서는 그 어떤 스레드도 다른 스레드에 영향을 줄 수 없으니 
    안심하고 공유할 수 있다.
  * 따라서 불변 클래스라면 한번 만든 인스턴스를 최대한 재활용하길 권한다. [정적 팩토리]
  * 방어적 복사도 필요없다. 그렇기 때문에 불변 클래스는 clone 메소드나 복사 생성자를 제공하지 않는게 좋다. String 클래스의 복사 생성자는 이 사실을 잘 이해하지 못한 자바 초창기 때 만들어진 것으로, 되도록이면 사용하지 말아야 한다.
* **불변 객체는 자유롭게 공유할 수 있음은 물론, 불변 객체끼리는 내부 데이터를 공유할 수 있다.**
  * BigInteger 클래스는 내부에서 값의 부호와 크기를 따로 표현한다. 부호에는 int 변수를, 크기에는 int 배열을 사용하는 것이다. 한편 negate 메소드는 크기가 같고 부호만 반대인 새로운 BIgInteger를 생성하는데, 이때 배열은 비록 가변이지만 복사하지않고 원본 인스턴스와 공유해도 된다. 그 결과 새로 만든 BigInteger 인스턴스도 원본 인스턴스가 가리키는 내부 배열을 그대로 가리킨다.

* **객체를 만들 때 다른 불변 객체들을 구성요소로 사용하면 이점이 많다.**
  * 값이 바뀌지 않는 구성요소들로 이루어진 객체라면 그 구조가 아무리 복잡하더라도 불변식을 유지하기 훨씬 수월하기 때문이다.
* **불변 객체는 그 자체로 실패 원자성을 제공한다.**
  * 실패 원자성이란 메소드에서 예외가 발생한 후에도 그 객체는 여전히 (메소드 호출 전과 똑같은) 유효한 상태여야 한다는 성질이다.
  * 상태가 절대 변하지 않으니 잠깐이라도 불일치 상태에 빠질 가능성이 없다.



<hr>



#### 🔗 불변 객체의 단점

* **값이 다르면 반드시 독립된 객체로 만들어야 한다.**

  * **값의 가짓수가 많다면 이들을 모두 만드는데 큰 비용을 치러야한다.**
    예를들어 백만비트 짜리 BigInteger에서 비트 하나를 바꿔야 한다고 가정해보자.

    ```java
    BigInteger moby = ...;
    moby = moby.flipBit(0);
    ```

    flipBit 메소드는 새로운 BigInteger 인스턴스를 생성한다. 원본과 단지 한 비트만 다른 백만 비트짜리 인스턴스를 말이다. 이 연산은 BigInteger의 크기에 비례해 시간과 공간을 잡아먹는다.

    BitSet도 BigInteger처럼 임의 길이의 비트 순열을 표현하지만, BigInteger와는 달리 '가변'이다. 즉, BItSet 클래스는 원하는 비트 하나만 상수 시간 안에 바꿔주는 메소드를 제공한다.

    <br>

    **<span style="color:red;">이를 대처하는 방법 중 하나는 흔히 쓰일 다단계 연산들을 예측하여 기본기능으로 제공하는 방법이다.</span>**

    <br>

    이러한 다단계 연산을 기본으로 제공한다면 더 이상 각 단계마다 객체를 생성하지 않아도 된다. 불변 객체는 내부적으로 아주 영리한 방식으로 구현할 수 있기 때문이다.

    <br>

    클라이언트가 원하는 복잡한 연산들을 정확히 예측할 수 있다면 이러한 다단계 연산속도를 높여주는 package-private인 가변 동반 클래스만으로 충분하다.

    <br>

    예측이 불가능 하다면 가변 동반 클래스를 public으로 제공하는게 최선이다.

    대표적인 예로 StringBuilder, StringBuffer가 있다.

    

<hr>



**💎 불변 객체를 만드는 또다른 설계 방법**

앞서 클래스가 불변임을 보장하려면 자신을 상속하지 못하게 해야한다고 했다.

가장 쉬운 방법은 final클래스로 선언하는 것이지만, <span style="color:red;">더 유연한 방법이 있다.</span>



***모든 생성자를 private 혹은 package-private으로 만들고 public 정적 팩토리를 제공하는 방법이다.***

다음의 예시를보자

```java
public class Complex {
    private final double re;
    private final double im;
    
    private Complex(double re, double im) {
        this.re = re;
        this.im = im;
    }
    
    public static Complex valueOf(double re, double im) {
        return new Complex(re, im);
    }
}
```

* 이 방식은 바깥에서 볼 수 없는 package-private 구현 클래스를 원하는 만큼 만들어 활용할 수 있으니 훨씬 유용하다.

* 패키지 바깥의 클라이언트에서 바라본 이 불변 객체는 사실상 final이다. 
  public이나 protected 생성자가 없으니 다른 패키지에서는 이 클래스를 확장하는게 불가능하기 때문이다.
* 정적 팩토리 방식은 다수의 구현 클래스를 활용한 유연성을 제공하고, 이에 더해 다음 릴리즈에서 객체 캐싱 기능을 추가해 성능을 끌어 올릴 수 있다.
* 어떤 불변 클래스는 계산 비용이 큰 값을 나중에 (처음 쓰일 때) 계산하여 final이 아닌 필드에 캐싱하여 사용함으로써 계산 비용을 절감한다. 객체가 불변이기 떄문에 가능한 방법이다.



<hr>



> * 클래스는 꼭 필요한 경우가 아니라면 불변이어야 한다.
> * 단순한 값 객체는 불변으로 만들자.
> * 불변으로 만들 수 없는 클래스라도 변경할 수 있는 부분을 최소한으로 줄이자.
> * 특별한 이유가 없다면 모든 필드는 private final이어야 한다.
> * 생성자는 불변식 설정이 모두 완료된, 초기화가 완벽히 끝난 상태의 개체를 생성해야 한다.
>   * 확실한 이유가 없다면 생성자와 정적 팩토리 외에는 그 어떤 초기화 메소드도 public 으로 제공해서는 안된다.
>   * 객체를 재활용할 목적으로 상태를 다시 초기화하는 메소드도 안 된다.







```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```
