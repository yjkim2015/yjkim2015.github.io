---
title: int 상수 대신 열거 타입을 사용하라 - Effective Java[34]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 열거 타입이란

* **열거 타입**은 **일정 개수의 상수 값을 정의**한 다음, **그 외의 값은 허용하지 않는 타입**이다.

  * ex) 사계절, 태양계의 행성, 카드게임의 카드 종류 등

  

* 자바에서 열거 타입을 지원하기 전에는 다음 코드 처럼 **정수 상수를 한 묶음 선언**해서 사용하곤 했다.

<br>



💎 **정수 열거 패턴 - 상당히 취약하다!**

```java
public static final int APPLE_FUJI 			= 0;
public static final int APPLE_PIPPIN 		= 1;
public static final int APPLE_GRANNY_SMITH  = 2;

public static final int ORANGE_NAVEL 		= 0;
public static final int ORAGNE_TEMPLE 		= 1;
public static final int ORANGE_BLOOD 		= 2;
```

* **정수 열거 패턴(int enum pattern)** 기법에는 <span style="color:red;">단점이 많다.</span>

  * 타입 안전을 보장할 방법이 없으며 표현력도 좋지 않다.

  

  * 오렌지를 건네야 할 메소드에 사과를 보내고 동등 연산자(==)로 비교하더라도 컴파일러는 아무런 경고 메시지를 출력하지 않는다.
  * int i = (APPLE_FUJI - ORANGE_TEMPLATE) / APPLE_PIPPIN;

  

* **자바가 정수 열거 패턴을 위한 별도 이름공간(namespace)를 지원하지 않는다.**

  * 때문에 어쩔수 없이 접두어를 써서 이름 충돌을 방지한다.

  

  * ex) 사과용 상수의 이름은 모두 APPLE_로 시작, 오렌지용 상수는 ORANGE_로 시작



* **정수 열거 패턴을 사용한 프로그램은 깨지기 쉽다.**

  * 평범한 상수를 나열한 것 뿐이라 컴파일하면 그 값이 클라이언트 파일에 그대로 새겨진다.

  

  * 따라서 상수의 값이 바뀌면 클라이언트도 반드시 다시 컴파일해야 한다.
    * 다시 컴파일 하지 않은 클라이언트는 실행이 되더라도 엉뚱하게 동작할 것이다.



* **정수 상수는 문자열로 출력하기가 다소 까다롭다.**

  * 그 값을 출력하거나 디버거로 살펴보면 (의미가 아닌) 단지 숫자로만 보여서 썩 도움이 되지 않는다. 

  

  * 같은 정수 열거 그룹에 속한 모든 상수를 한바퀴 순회하는 방법도 마땅치 않다.
    * 심지어 그 안에 상수가 몇 개 인지도 알 수 없다.



* **정수 대신 문자열 상수를 사용하는 변형 패턴도 있지만 더 나쁘다.**
  * 상수의 의미를 출력할 수 있다는 점은 좋지만, 경험이 부족한 프로그래머가 문자열 상수의 이름 대신 문자열 값을 그대로 하드코딩하게 만들기 때문이다.
  * EX) 하드코딩한 문자열에 오타가 있어도 컴파일러는 확인할 길이 없으니 런타임 버그가 생긴다.



<hr>



#### 🔗 열거 패턴 No!! 대안은? 열거 타입 (enum Type) Yes@@



💎 **가장 단순한 열거 타입**

```java
public enum Apple { FUJI, PIPPIN, GRANNY_SMITH }
public enum Orange { NABEL, TEMPLE, BLOOD }
```

<br>



#### 🔗 열거 타입의 장점

* 자바의 **열거 타입은 완전한 형태의 클래스이며** 상수 하나당 자신의 인스턴스를 하나씩 만들어 public static final 필드로 공개한다.



* **열거 타입은** 밖에서 접근할 수 있는 생성자를 제공하지 않으므로 **사실상 final이다.**

  * 따라서 클라이언트가 인스턴스를 직접 생성하거나 확장할 수 없으니 **열거 타입 선언으로 만들어진 인스턴스들은 딱 하나씩만 존재함이 보장된다.**

  

  * **즉, 열거  타입은 인스턴스 통제된다 - 싱글턴**

  

  * 싱글턴은 원소가 하나뿐인 열거 타입이라 할 수 있고, **열거 타입은 싱글턴을 일반화한 형태라고 볼 수 있다.**



* **열거 타입은 컴파일타임 타입 안정성을 제공한다.**

  * 위 코드의 **Apple 타입을 매개변수로 받는 메소드를 선언했다면, 건네받은 참조**는 (null이 아니라면) **Apple의 세 가지 값 중 하나임이 확실하다.**

  

  * **다른 타입의 값을 넘기려 하면 컴파일 오류가 난다.**

  

  * 타입이 다른 열거 타입 변수에 할당하려 하거나 다른 열거 타입의 값끼리 == 연산자로 비교하려는 꼴이기 때문이다.



* **열거 타입에는 각자의 이름공간이 있어서 이름이 같은 상수도 평화롭게 공존한다.**

  * 열거 타입에 새로운 상수를 추가하거나 순서를 바꿔도 다시 컴파일 하지 않아도 된다.

  

  * 공개되는 것이 오직 필드의 이름뿐이라, 정수 열거 패턴과 달리 상수 값이 클라이언트로 컴파일되어 각인되지 않기 때문이다.

  

* **열거 타입의 toString 메소드는 출력하기에 적합한 문자열을 내어준다.**

​	

* 열거 타입에는 **임의의 메소드나 필드를 추가**할 수 있고 **임의의 인터페이스를 구현**하게 할 수도 있다.



<hr>



##### 💎 열거 타입에 메소드나 필드를 추가한다니 ? 어떨 때 필요한 기능이야?

* 각 상수와 연관된 데이터를 해당 상수 자체에 내재시키고 싶다고 가정해보자.
  * ex)  위의 Apple과 Orange를 예로 들어, 과일의 색을 알려주거나 과일 이미지를 반환하는 메소드를 추가하고 싶을 수 있다.



* **열거 타입에는 어떤 메소드도 추가할 수 있다.**
  * 가장 단순하게는 그저 상수모음일 뿐인 열거 타입이지만, (실제로는 클래스이므로) 고차원의 추상 개념 하나를 완벽히 표현해낼 수도 있는 것이지다.



<br>



💎 **데이터와 메소드를 갖는 열거 타입 - 태양계의 여덟 행성**

* 각 행성에는 질량과 반지름이 있고, 이 두 속성을 이용해 표면중력을 계산할 수 있다.



* 따라서 어떤 객체의 질량이 주어지면 그 객체가 행성 표면에 있을 때의 무게도 계산할 수 있다.



* 열거 타입의 모습은 다음과 같다.

```java
public enum Planet {
    MERCURY (3.302e+23, 2.439e6),
    VENUS   (4.869e+24, 6.052e6),
    EARTH   (5.975e+24, 6.378e6),
    MARS    (6.419e+23, 3.393e6),
    JUPITER (1.899e+27, 7.149e7),
    SATURN	(5.685e+26, 6.027e7),
    URANUS	(8.683e+25, 2.556e7),
    NEPTUNE (1.024e+26, 2.477e7);
    
    private final double mass;			 // 질량(단위: 킬로그램)
    private final double radius;		 // 반지름(단위: 미터)
    private final double surfaceGravity; // 표면중력(단위 : m / s^2)
    
    //중력상수(단위: m^3 / kg s^2)
    private static final double G = 6.67300E-11;
    
    //생성자
   	Planet(double mass, double radius) {
        this.mass 		= mass;
        this.radius 	= radius;
        surfaceGravity  = G * mass / (radius * radius);
    }
    
    public double mass()			{ return mass; }
    public double radius() 			{ return radius; }
    public double surfaceGravity()  { return surfaceGravity; }
    
    public double surfaceWeight(double mass) {
        return mass * surfaceGravity;	// F = ma
    }
}
```

* 열거 타입 상수 각각을 특정 데이터와 연결지으려면 생성자에서 데이터를 받아 인스턴스 필드에 저장하면 된다.



* **열거 타입은** 근본적으로 **불변**이라 **<span style="color:red;">모든 필드는 final이어야 한다.</span>**



* 필드를 public으로 선언해도 되지만, **private으로 두고 별도의 public 접근자 메소드를 두는게 낫다.**



<hr>



💎 **Planet 열거 타입의 실제 사용**  

* 어떤 객체의 지구에서의 무게를 입력받아 여덟 행성에서의 무게를 출력하는 일

```java
public class WeightTable {
    public static void main(String[] args) {
        double earthWeight = Double.parseDouble(args[0]);
        double mass = earthWeight / Planet.EARTH.surfaceGravity();
        for (Planet p : Planet.values()) {
            System.out.printf("%s에서의 무게는 %f이다.%n", p, p.surfaceWeight(mass));
        }
    }
}
```

* 열거 타입은 자신 안에 **정의된 상수들의 값을 배열에 담아 반환하는 정적 메소드인 values를 제공한다.**

  * 값들은 **선언된 순서로 저장**된다.

  

  * 각 열거 타입 값의 **toString** 메소드는 **상수 이름을 문자열로 반환**하므로 println과 printf로 출력하기에 안성맞춤이다.



<hr>



##### 💎 열거 타입에서 상수를 하나 제거하면 어떻게 될까?

* 제거한 상수를 참조하지 않는 클라이언트에는 아무 영향이 없다.



* **제거된 상수를 참조하는 클라이언트는** 프로그램을 **다시 컴파일하면** 제거된 상수를 참조하는 줄에서 디버깅에 유용한 메시지를 담은 **<span style="color:red;">컴파일 오류가 발생</span>** 할 것이다.

  * 클라이언트를 **다시 컴파일 하지 않으면 <span style="color:red;">런타임에</span>**, 역시 같은 줄에서 유용한 예외가 발생할 것이다.

  

  * 정수 열거 패턴에서는 기대할 수 없는 가장 바람직한 대응이라고 볼 수 있다.





<hr>



💎 **열거 타입을 선언한 클래스 혹은 그 패키지에서만 유용한 기능은 private이나 package-private 메소드로 구현한다**

* 이렇게 구현된 열거 타입 상수는 자신을 선언한 클래스 혹은 패키지에서만 사용할 수 있는 기능을 담게 된다.



* 일반 클래스와 마찬가지로, 그 기능을 클라이언트에 노출해야 할 합당한 이유가 없다면 private으로, 혹은 (필요하다면) package-private으로 선언하라



<hr>



💎 **널리 쓰이는 열거 타입은 톱레벨 클래스로 만들고, 특정 톱레벨 클래스에서만 쓰인다면 해당 클래스의 멤버 클래스로 만든다.**

* 예를들어 소수 자릿수의 **반올림 모드**를 뜻하는 **열거 타입**인 **java.math.RoundingMode**는 **BigDecimal**이 사용한다.



* <span style="color:red;">그런데</span> **반올림 모드는 BigDecimal과 관련 없는 영역에서도 유용한 개념**이라 자바 라이브러리 설계자는 **RoundingMode를 톱레벨로 올렸다.**
  * 이 개념을 많은 곳에서 사용하여 다양한 API가 더 일관된 모습을 갖출 수 있도록 장려한 것이다



<hr>



💎 **Planet 예에서 보여주는 특성은 뭔가 아쉬워! 상수가 더 다양한 기능을 제공해줬으면 좋겠는데!!!@@**



* 위 코드 Planet에서 상수들은 서로 다른 데이터와 연결되는 데 그쳤지만, 한 걸음 더 나아가 상수마다 동작이 달라져야 하는 상황도 있을 것이다.ㄷ



* 실제 연산까지 열거 타입 상수가 직접 수행했으면 한다고 해보자.

<br>



💎 **값에 따라 분기하는 열거 타입 - 이대로 만족하는가?**

```java
public enum Operation {
    PLUS, MINUS, TIMES, DIVIDE;
    
    // 상수가 뜻하는 연산을 수행한다.
    public double apply(double x, double y) {
        switch(this) {
            case PLUS: return x + y;
            case MINUS: return x - y;
            case TIMES: return x * y;
            case DIVIDE: return x / y;
        }
        throw new AssertionError("알 수 없는 연산: " + this);
    }
}
```

* **위 코드는 동작은 하지만 깨지기 쉬운 코드이다.**

  * 새로운 상수를 추가하면 해당 case 문도 추가해야 한다.

  

  * 혹시라도 깜빡한다면, 컴파일은 되지만 새로 추가한 연산을 수행하려 할 때 "알 수 없는 연산" 이라는 런타임 오류를 내며 프로그림이 종료된다.





* **다행히 열거 타입은 상수별로 다르게 동작하는 코드를 구현하는 더 나은 수단을 제공한다.**

  * 열거 타입에 **apply라는 추상 메소드를 선언**하고 **각 상수별 클래스 몸체**, <span style="color:red;">즉 각 상수에서 자신에 맞게 재정의하는 방법이다.</span>

  

  * **이를 <span style="color:red;">상수별 메소드 구현</span>이라 한다.**



<hr>


##### 💎 상수별 메소드 구현을 활용한 열거 타입

```java
public enum Operation {
    PLUS  {public double apply(double x, double y) {return x + y ;}},
    MINUS {public double apply(double x, double y) {return x - y ;}},
    TIMES {public double apply(double x, double y) {return x * y ;}},
    DIVIDE{public double apply(double x, double y) {return x / y ;}};
    
    public abstract double apply(double x, double y);
}
```

* apply 메소드가 상수 선언 바로 옆에 붙어있으니 새로운 상수를 추가 할 때 apply도 재정의해야 한다는 사실을 깜빡하기는 어려울 것이다.



* 상수별 메소드 구현을 다음과 같이 **상수별 데이터와 결합** 할 수도 있다.



<br>

##### 💎 상수별 클래스 몸체(class body)와 데이터를 사용한 열거 타입

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

* 다음은 이 toString이 계산식 출력을 얼마나 편하게 해주는지를 보여준다.

<br>



💎 **Operation Enum 클래스 사용 예시**

```java
public static void main(String[] args) {
    double x = Double.parseDouble(args[0]);
    double y = Double.parseDouble(args[1]);
    for (Operation op : Operation.values()) {
        System.out.printf("%f %s %f = %f%n", x, op, y, op.apply(x, y));
    }
}
```

* **열거 타입**에는 상수 이름을 입력받아 그 이름에 해당하는 상수를 반환해주는 **valueOf(String) 메소드가 자동 생성된다.**



* <span style="color:red;">한편</span>, **열거 타입의** **toString 메소드를 재정의**하려거든, toString이 **반환하는 문자열을 해당 열거 타입 상수로 반환해주는 fromString 메소드도 함께 제공**하는 걸 고려해보자.

<br>



##### 💎 열거 타입용 fromString 메소드 구현하기

```java
private static final Map<String, Opeation> stringToEnum = 
    	Stream.of(values()).collect(
			toMap(Object::toString, e -> e));

// 지정한 문자열에 해당하는 Operation을 (존재한다면) 반환한다.
public static Optional<Operation> fromString(String symbol) {
    return Optional.ofNullable(stringToEnum.get(symbol));
}
```

* Operation 상수가 stringToEnum 맵에 추가되는 시점은 **열거 타입 상수 생성 후 정적 필드가 초기화될 때다.**



* 열거 타입 상수는 **생성자에서 자신의 인스턴스를 맵에 추가할 수 없다.**

  * 이렇게 하려면 컴파일 오류가 나는데, 만약 이 방식이 허용되었다면 런타임에 **NullPointerException**이 발생했을 것이다.

  

  * **열거 타입의 정적 필드 중 열거 타입의 생성자에서 접근할 수 있는 것은 상수 변수뿐이다.**

  

  * 열거 타입 생성자가 실행되는 시점에는 정적 필드들이 아직 초기화되기 전이라, **자기 자신을 추가하지 못하게 하는 제약이 <span style="color:red;">꼭 필요하다.</span>**



* **fromString**이 `Optional<Operation>`을 **반환하는 점도 주의**하자.
  * 이는 주어진 문자열이 가리키는 연산이 존재하지 않을 수 있음을 클라이언트에 알리고, 그 상황을 클라이언트에서 대처하도록 한 것이다.



<hr>



##### 💎 상수별 메소드 구현의 단점

* 상수별 메소드 구현에는 **열거 타입 상수끼리 코드를 공유하기 어렵다**

  * ex) 급여명세서에서 쓸 요일을 표현하는 열거 타입

  

  * 이 열거 타입은 직원의 (시간당) 기본 임금과 그날 일한 시간(분 단위)이 주어지면 일당은 계산해주는 메소드를 갖고 있다.

  

  * 주중에 오버타임이 발생하면 잔업수당이 주어지고, 주말에는 무조건 잔업수당이 주어진다.



<hr>



💎 **값에 따라 분기하여 <span style="color:red;">코드를 공유</span>하는 열거 타입** - 좋은 방법인가?

```java
enum PayrollDay {
    MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY,
    SATURDAY, SUNDAY;
    
    private static final int MINS_PER_SHIFT = 8 * 60;
    
    int pay(int minutesWorked, int payRate) {
        int basePay = minutesWorked * payRate;
        
        int overtimePay;
        switch(this) {
            case SATURDAY: // 주말
            case SUNDAY:   // 주말
                overtimePay = basePay / 2;
                break;
            default: // 주중
                overtimePay = minutesWorked <= MINS_PER_SHIFT ?
                    0 : (minutesWorked - MINS_PER_SHIFT) * payRate / 2;
        }
        return basePay + overtimePay;
    }
}
```

* 분명 간결하지만, 관리 관점에서는 위험한 코드다.
  * 휴가와 같은 새로운 값을 열거 타입에 추가하려면 그 값을 처리하는 case 문을 잊지 말고 쌍으로 넣어줘야 하는 것이다. ( 깜빡하면 어떻게 될 지 상상해보라 ㅎㅎ )



* 상수별 메소드 구현으로 급여를 정확히 계산하는 방법은 두 가지다.

  * 잔업 수당을 계산하는 코드를 모든 상수에 중복해서 넣으면 된다.

  

  * 계산 코드를 평일용과 주말용으로 나눠 각각을 도우미 메소드로 작성한 다음 각 상수가 자신에게 필요한 메소드를 적절히 호출하면 된다.

  

* 두 방식 모두 코드가 장황해져 **가독성이 크게 떨어지고 오류 발생 가능성이 높아진다.**



* **가장 깔끔한 방법은** 새로운 상수를 추가할 때 잔업수당 '**<span style="color:red;">전략</span>**'을 선택하도록 하는 것이다.

  * 잔업수당 계산을 **private 중첩 열거 타입**(다음 코드의 PayType)으로 옮기고 **PayrollDay 열거 타입의 생성자에서 이 중 적당한 것을 선택**한다.

  

  * 그러면 PayrollDay 열거 타입은 **잔업수당 계산을 그 <span style="color:red;">전략 열거 타입</span>에 위임**하여, switch 문이나 상수별 메소드 구현이 필요 없게 된다.

    

<hr>



##### 💎 두둥 등장@@ 전략 열거 타입 패턴

```java
enum PayrollDay {
    MONDAY(WEEKDAY), TUESDAY(WEEKDAY), WEDNESDAY(WEEKDAY),
    THURSDAY(WEEKDAY), FRIDAY(WEEKDAY),
    SATURDAY(WEEKDAY), SUNDAY(WEEKEND);
    
    private final PayType payType;
    
    PayrollDay(PayType payType) { this.payType = payType; }
    
    int pay(int minutesWorked, int payRate) {
        return payType.pay(minutesWorked, payRate);
    }
    
   // 전략 열거 타입
   enum PayType {
       WEEKDAY {
           int overtimePay(int minsWorked, int payRate) {
               return minsWorked <= MINS_PER_SHIFT ? 0 :
               		(minsWorked - MINS_PER_SHIFT) * payRate / 2;
           }
       },
       WEEKEND {
           int overtimePay(int minWorked, int payRate) {
               return minsWorked * payRate / 2;
           }
       };
       
       abstract int overtimePay(int mins, int payRate);
       
       private static final int MINS_PER_SHIFT = 8 * 60;
       
       int pay(int minsWorked, int payRate) {
           int basePay = minsWorked * payRate;
           return basePay + overtimePay(minsWorked, payRate);
       }
   }
}
```

* 이 패턴은 switch 문보다 복잡하지만 **더 안전하고 유연하다.**



* 보다시피 switch 문은 열거 타입의 상수별 동작을 구현하는 데 적합 하지 않다.

  * <span style="color:red;">하지만</span> 기존 열거 타입에 **상수별 동작을 혼합해 넣을 때는 switch 문이 좋은 선택**이 될 수 있다.

  

  * ex)  서드파티에서 가져온 **Operation 열거 타입**이 있는데, 각 연산의 반대 연산을 반환하는 메소드가 필요하다고 해보자. 다음은 이러한 효과를 내주는 정적 메소드다.

<br>



💎 **switch 문을 이용해 원래 열거 타입에 없는 기능을 수행한다.**

```java
public static Operation inverse(Operation op) {
    switch(op) {
        case PLUS  : return Operation.MINUS;
        case MINUS : return Operation.PLUS;
        case TIMES : return Operation.DIVIDE;
        case DIVIDE: return Operation.TIMES;
            
        default: throw new AssertionError("알 수 없는 연산: " + op);
    }
}
```

* **추가하려는 메소드가 의미상 열거 타입에 속하지 않는다면** 직접 만든 열거 타입이라도 **이 방식을 적용하는게 좋다.**
  * 종종 쓰이지만 열거 타입 안에 포함할만큼 유용하지 않은 경우도 마찬가지다.



<hr>



##### 🔗 열거 타입은 언제 써야해?

* 대부분의 경우 열거 타입의 성능은 정수 상수와 별반 다르지 않다.

  * 열거 타입을 메모리에 올리는 공간과 초기화하는 시간이 들긴 하지만 체감될 정도는 아니다.

  

* 필요한 원소를 **컴파일타임에 다 알 수 있는 상수 집합**이라면 **<span style="color:red;">항상 열거 타입을 사용하자.</span>**

  * ex) 태양계 행성, 한 주의 요일, 체스 말
  * ex) 메뉴 아이템, 연산 코드, 명령줄 플래그 등 **허용하는 값 모두를 컴파일타임에 이미 알고 있을 때**



* **열거 타입에 정의된 상수 개수가 <span style="color:red;">영원히 고정 불변일 필요는 없다.</span>**
  * 열거 타입은 나중에 상수가 추가돼도 바이너리 수준에서 호환되도록 설계되었다.



<hr>



> 열거 타입은 확실히 정수 상수보다 뛰어나다.
>
> 더 읽기 쉽고 안전하고 강력하다.
>
> 대다수 열거 타입이 명시적 생성자나 메소드 없이 쓰이지만,
>
> 각 상수를 특정 데이터와 연결짓거나 상수마다 다르게 동작하게 할 떄는 필요하다.
>
> 드물게는 하나의 메소드가 상수별로 다르게 동작해야 할 때도 있다.
>
> 이런 열거 타입에서는 switch문 대신 상수별 메소드 구현을 사용하자.
>
> 열거 타입 상수 일부가 같은 동작을 공유한다면 전략 열거 타입 패턴을 사용하자.











```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

