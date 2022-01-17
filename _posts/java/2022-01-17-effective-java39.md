---
title: 명명 패턴보다 애너테이션을 사용하라 - Effective Java[39]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 명명 패턴의 전통

* **전통적으로** 도구나 프레임워크가 특별히 다뤄야 할 프로그램 요소에는 딱 구분되는 **명명 패턴**을 적용해왔다.

  * ex) 테스트 프레임워크인 Junit은 버전 3까지 테스트 메소드 이름을 test로 시작하게끔 했다.

  

  * 효과적인 방법이지만 <span style="color:red;">단점도 크다.</span>

    * **첫 번째, 오타가 나면 안된다.**

      * ex) 실수로 이름을 tsetSafetyOverride 로 지으면 Junit 3은 이 메소드를 무시하고 지나치기 때문에 개발자는 이 테스트가 (실패하지 않았으니) 통과했다고 오해할 수 있다.

      

    * **두 번째, 올바른 프로그램 요소에서만 사용되리라 보증 할 방법이 없다는 것이다.**

      * ex) 클래스 이름을 TestSafety Mechanisms로 지어 JUnit에 던져줬다고 가정하면, 개발자는 이 클래스에 정의된 테스트 메소드들을 수행해주길 기대하겠지만 JUnit은 클래스 이름에는 관심이 없다.

      

      * 이번에도 JUnit은 경고 메시지조차 출력하지 않지만 개발자가 의도한 테스트는 전혀 수행되지 않는다.

    * **세 번째, 프로그램 요소를 매개변수로 전달할 마땅한 방법이 없다는 것이다.**

      * ex) 특정 예외를 던져야만 성공하는 테스트가 있다고 가정 해보자.

      

      * 기대하는 예외 타입을 테스트에 매개변수로 전달해야 하는 상황이다.

      

      * 예외의 이름을 테스트 메소드 이름에 덧붙이는 방법도 있지만, 보기도 나쁘고 깨지기도 쉽다

      

      * 컴파일러는 메소드 이름에 덧붙인 문자열이 예외를 가리키는지 알 도리가 없다.

      

      * 테스트를 실행하기 전에는 그런 이름의 클래스가 존재하는지 혹은 예외가 맞는지조차 알 수 없다.



<hr>



##### 💎 모든 문제의 해결책 애너테이션 : JUnit 4 부터 전면 도입@@@

* 다음과 같이 직접 제작한 작은 테스트 프레임 워크를 통해 애너테이션에 대해 알아보자.
  * 자동으로 수행되는 간단한 테스트용 애너테이션으로, 예외가 발생하면 해당 테스트를 실패로 처리한다.

<br>



💎 **마커(marker) 애너테이션 타입 선언**

```java
import java.lang.annotation.*;

/**
* 테스트 메소드임을 선언하는 애너테이션이다.
* 매개변수 없는 정적 메소드 전용이다.
*/
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface Test {
    
}
```

* 위 코드에서 **@Test** 애노테이션 타입 선언 자체에도 **두 가지의 다른 애너테이션**이 달려 있다.



* **@Retention**과 **@Target**이다.

  * 이처럼 애너테이션 선언에 다는 애너테이션을 <span style="color:red;">메타애너테이션(meta-annotation)</span>이라 한다.

  

  * **@Retention(RetentionPolicy.RUNTIME)** 메타 애너테이션은 @Test가 <span style="color:red;">런타임에도 유지</span>되어야 한다는 표시다. 만약 이 메타애너테이션을 생략하면 테스트 도구는 @Test를 인식 할 수 없다.

    

  * **@Target(ElementType.METHOD)** 메타애너테이션은  @Test가 반드시 <span style="color:red;">메소드 선언에서만</span> 사용돼야 한다고 알려준다. <span style="color:red;">따라서</span> **클래스 선언, 필드 선언 등 다른 프로그램 요소에는 달 수 없다.**

​	

* 위 코드의 메소드 주석에는 **"매개변수 없는 정적 메소드 전용이다"**라고 쓰여있다.

  * 이 제약을 컴파일러가 강제할 수 있으면 좋겠지만, 그렇게 하려면 적절한 애너테이션 처리기를 직접 구현해야 한다.

  

  * 적절한 애너테이션 처리기 없이 인스턴스 메소드나 매개변수가 있는 메소드에 달면 **컴파일은 잘 되겠지만, 테스트 도구를 실행할 때 문제가 된다.**



<hr>



##### 💎 마커(marker) 애너테이션

* 다음과 같이 **아무 매개변수 없이** 단순히 **대상에 마킹(marking)**하는 애너테이션을 **마커 애너테이션**이라 칭한다.
  * 이 애너테이션을 사용하면 프로그래머가 Test 이름에 오타를 내거나 메소드 선언 외의 프로그램 요소에 달면 컴파일 오류를 내준다.

<br>



💎 **마커 애너테이션을 사용한 프로그램 예**

```java
public class Sample {
    @Test public static void m1() { } //성공해야 한다.
    public static void m2() {}
    @Test public static void m3() { // 실패 해야 한다.
        throw new RuntimeException("실패");
    }
    public static void m4() {}
    @Test public void m5() {} // 잘못 사용한 예 : 정적 메소드가 아니다.
    @Test public static void m7() {
        throw new RuntimeException("실패");
    }
    public static void m8() { }
}
```

* Sample 클래스에는 정적 메소드가 7개고, 그중 4개에 **@Test**를 달았다.

  * m3와 m7 메소드는 예외를 던지고 m1과 m5는 그렇지 않다.

  

  * 그리고 m5는 인스턴스 메소드이므로 @Test를 잘못 사용한 경우이다.



* **@Test** 애노테이션이 **Sample** 클래스의 의미에 직접적인 영향을 주지는 않는다.

  * 그저 이 애노테이션에 관심있는 프로그램에게 추가 정보를 제공할 뿐이다.

  

  * 대상 코드의 의미는 그대로 둔 채 **그 애너테이션에 관심 있는 도구**에서 **특별한 처리를 할 기회를 준다.**

  

  * 다음의 **RunTests**가 **바로 그런 도구의 예**이다.



<hr>



💎 **마커 애너테이션을 처리하는 프로그램**

```java
import java.lang.reflect.*;

public class Runtests {
    public static void main(String[] args) throws Exception {
        int test = 0;
        int passed = 0;
        Class<T> testClass = Class.forName(agrs[0]);
        
        for (Method m : testClass.getDeclaredMethods()) {
            if (m.isAnnotationPresent(Test.class)) {
                tests++;
                try {
                    m.invoke(null);
                    passed++;
                }
                catch (InvocationTargetException wrappedExc) {
                    Throwable exc = wrappedExc.getCause();
                    System.out.println(m + " 실패 : " + exc);
                }
                catch (Exception exc) {
                    System.out.println("잘못 사용한 @Test : " + m);
                }
            }
        }
        
    }
}
```

* 이 테스트 러너는 명령줄로부터 완전 정규화된 클래스 이름을 받아, 그 클래스에서 **@Test** 애노테이션이 달린 메소드를 차례로 호출한다.

  * **isAnnotationPresent**가 실행할 메소드를 찾아주는 메소드다.

  

  * 테스트 메소드가 예외를 던지면 리플렉션 메커니즘이 **InvocationTargetException**으로 감싸서 다시 던진다.

  

  *  그래서 이 프로그램은 **InvocationTargetException**을 잡아 원래 예외에 담긴 실패 정보를 추출해**(getCause)**를 출력한다.



* **InvocationTargetException** <span style="color:red;">외의 예외</span>가 발생한다면 **@Test 애노테이션을 잘못 사용했다는 뜻이다.**
  * 아마도 인스턴스 메소드, 매개변수가 있는 메소드, 호출 할 수 없는 메소드 등에 애너테이션을 달았을 것으로 추정된다.



<hr>



💎**매개변수 하나를 받는 애너테이션 타입**



* 특정 예외를 던져야만 성공하는 테스트를 지원해보자. 아래와 같이 새로운 애너테이션 타입이 필요하다.

```java
import java.lang.annotation.*;

/**
* 명시한 예외를 던져야만 성공하는 테스트 메소드용 애너테이션
*/
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface ExceptionTest {
    Class<? extends Throwable> value();
}
```

* 이 애노테이션의 매개변수 타입은 **Class<? extends Throwable>**이다.

  * 여기서 와일드카드 타입은 많은 의미를 담고 있다.

  

  * **"Throwable을 확장한 클래스의 Class 객체"**라는 뜻이며, <span style="color:red;">따라서 모든 예외 타입을 다 수용한다.</span>

  

  * 이는 한정적 타입 토큰의 또 하나의 활용 사례이다.

<br>



💎 **매개변수 하나짜리 애너테이션을 사용한 프로그램**

```java
public class Sample2 {
    @ExceptionTest(ArithmeticException.class)
    public static void m1() { //성공해야 한다.
        int i = 0;
        i = i / i;
    }
    
    @ExceptionTest(ArithmeticException.class)
    public static void m2() {	//실패해야 한다. (다른 예외 발생)
        int[] a = new int[0];
        int i = a[1];
    }
    
    @ExceptionTest(ArithmeticException.class)
    public static void m3() { } // 실패해야 한다. (예외가 발생하지 않음)
}
```

* 이제 이 애노테이션을 다룰 수 있도록 다음과 같이 테스트 도구를 수정한다.

<br>



```java
if (m.isAnnotationPresent(ExceptionTest.class)) {
	tests++;
    try {
        m.invoke(null);
        System.out.println("테스트 %s 실패 : 예외를 던지지 않음%n", m);
    }
    catch (InvocationTargetException wrappedEx) {
        Throwable exc = wrappedEx.getCause();
        Class<? extends Throwable> excType = m.getAnnotation(ExceptionTest.class).values();
        if (excType.isInstance(exc)) {
            passed++;
        }
        else {
            System.out.printf("테스트 %s 실패 : 기대한 예외 %s, 발생한 예외 %s%n", m, excType.getName(), exc);
        }
    }
    catch (Exception exc){
        System.out.println("잘못 사용한 @ExceptionTest: " + m);
    }
}
```

* **@Test** 애노테이션용 코드와 비슷해보이지만, <span style="color:red;">한 가지 차이</span>가 있다.

  * 이 코드는 <span style="color:red;">애너테이션 매개변수의 값을 추출</span>하여 **테스트 메소드가 올바른 예외를 던지는지 확인**하는 데 사용한다.

  

  * 형변환 코드가 없으니 **ClassCastException** 걱정은 없다.

  

  * 따라서 테스트 프로그램이 문제없이 컴파일되면 애너테이션 매개변수가 가리키는 예외가 올바른 타입이라는 뜻이다.

  

  * <span style="color:red;">단</span>, 해당 예외의 클래스 파일이 컴파일타임에는 존재했으나 런타임에는 존재하지 않을 수는 있다.
    * 이런 경우라면 테스트 러너가 **TypeNotPresentException**을 던질 것이다.



<hr>



💎 **배열 매개변수를 받는 애너테이션 타입**

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface ExceptionTest {
	Class<? extends Throwable>[] value();
}
```

* **배열 매개변수를 받는 애너테이션용 문법은 아주 유연하다.**



* 단일 원소 배열에 최적화했지만, 앞서의 **@ExceptionTest들도 모두 수정 없이 수용**한다.
  * 원소가 여럿인 배열을 지정할 때는 다음과 같이 원소들을 **중괄호로 감싸고 쉼표로 구분**해주기만 하면 된다.

<br>



💎 **배열 매개변수를 받는 애노테이션을 사용하는 코드**

```java
@ExceptionTest({IndexOutOfBoundsException.class, NullPointerException.class})
public static void doubleBad() { // 성공해야 한다.
    List<String> list = new ArrayList<>();
    
    list.addAll(5,null);
}
```

* 다음은 이 새로운 @ExceptionTest를 지원하도록 테스트 러너를 수정한 모습이다.



<br>

```java
if (m.isAnnotationPresent(ExceptionTest.class)) {
    tests++;
    try {
        m.invoke(null);
        System.out.printf("테스트 %s 실패 : 예외를 던지지 않음%n",m);
    }
    catch (Throwable wrappedExc) {
        Throwable exc = wrappedExc.getCause();
        int oldPassed = passed;
        Class<? extends Throwable>[] excTypes = 
            m.getAnnotation(ExceptionTest.class).values();
        
        for (Class<? extends Throwable> excType : excTypes) {
            if (excType.isInstance(exc)) {
                passed++;
                break;
            }
        }
        if (passed == oldPassed) {
			System.out.printf("테스트 %s 실패 : %s %n", m, exc);
        }
    }
}
```

* **자바 8에서는 여러 개의 값을 받는 애노테이션을 다른 방식으로 만들 수 있다.**

  * 배열 매개변수를 사용하는 대신 애노테이션에 **@Repeatable** 메타애너테이션을 다는 방식이다.

  

  * **@Repeatable**을 단 애너테이션은 하나의 프로그램 요소에 여러 번 달 수 있다.

  

* <span style="color:red;">단, 주의 할 점이 있다.</span>

  * 첫 번째, **@Repeatable**을 단 애너테이션을 반환하는 **'컨테이너 애너테이션'을 하나 더 정의**하고, **@Repeatable**에 이 컨테이너 애너테이션의 class 객체를 매개변수로 전달해야 한다.

  

  * 두 번째, **컨테이너 애너테이션은** 내부 애너테이션 타입의 배열을 반환하는 **value 메소드를 정의**해야 한다.

  

  * 컨테이너 애너테이션 타입에는 적절한 **보존 정책(@Retention)**과 **적용 대상(@Target)**을 <span style="color:red;">명시</span>해야 한다.
    * 그렇지 않으면 컴파일되지 않을 것이다.



<hr>



💎 **반복 가능한 애너테이션 타입**

```java
// 반복 가능한 애너테이션
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
@Reapeatable(ExceptionTestContainer.class)
public @interface ExceptionTest {
    Class<? extends Throwable> values();
}

// 컨테이너 애너테이션
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface ExceptionTestContainer {
    ExceptionTest[] value();
}
```

* 배열 방식 대신 반복 가능 애너테이션을 아래와 같이 적용해보자.

<br>



💎 **반복 가능 애너테이션을 두 번 단 코드**

```java
@ExceptionTest(IndexOutOfBoundsException.class)
@ExceptionTest(NullPointerException.class)
public static void doublyBad() { ... }
```

* 반복 가능 애너테이션은 처리할 때도 <span style="color:red;">주의를 요한다.</span>



* **반복 가능 애너테이션**을 여러 개 달면 하나만 달았을 때와 구분하기 위해 해당 **'컨테이너' 애너테이션 타입이 적용된다.**

  * **getAnnotationsByType** 메소든느 이 둘을 구분하지 않아서 반복 가능 애너테이션과 그 컨테이너 애너테이션을 모두 가져오지만, **isAnnotationPresent** 메소드는 둘을 명확히 구분한다.

  

  * 따라서 반복 가능한 애너테이션을 여러 번 단 다음 **isAnnotationPresent**로 반복 가능 애너테이션이 달렸는지 검사한다면 "그렇지 않다"라고 알려준다<span style="color:red;">(컨테이너가 달렸기 때문이다).</span>

    * 그 결과 애너테이션을 여러 번 단 메소드들을 모두 무시하고 지나친다.

    

    * 같은 이유로, **isAnnotationPresent**로 컨테이너 애너테이션이 달렸는지 검사한다면 반복 가능 애너테이션을 한 번만 단 메소드를 무시하고 지나친다.

    

    * 그래서 달려 있는 수와 상관없이 모두 검사하려면 아래와 같이 둘을 따로따로 확인해야 한다.



<hr>



💎 **반복 가능 애너테이션 다루기**

```java
if (m.isAnnotationPresent(ExceptionTest.class)
   	|| m.isAnnotationPresent(ExceptionTestContainer.class)) {
    tests++;
    try {
        m.invoke(null);
        System.out.printf("테스트 %s 실패 : 예외를 던지지 않음%n", m);
    }
    catch (Throwsable wrappedExc) {
        Throwable exc = wrappedExc.getCause();
        int oldPassed = passed;
        ExceptionTest[] excTests = 
            	m.getAnnotationsByType(ExceptionTest.class);
        for(ExceptionTest excTest : excTests) {
            if (excTest.value().isInstance(exc)) {
                passed++;
                break;
            }
        }
        if (passwd = oldPassed) {
			System.out.printf("테스트 %s 실패 : %s %n", m, exc);
        }
    }
}
```

* 이 방식으로 코드의 가독성을 개선할 수 있다면 이 방식을 사용하도록 하자.



* <span style="color:red;">하지만</span> 애너테이션을 선언하고 이를 처리하는 부분에서는 코드 양이 늘어나며, 특히 처리 코드가 복잡해져 오류가 날 가능성이 커짐을 명심하자.



<hr>



> 다른 프로그래머가 소스코드에 추가 정보를 제공할 수 있는 도구를 만드는 일을 한다면 적당한 애너테이션 타입도 함께 정의해 제공하자.
>
> **애너테이션으로 할 수 있는 일을 명명 패턴으로 처리할 이유는 없다.**
>
> 
>
> 도구 제작자를 제외하고는, 일반 프로그래머가 애너타이션 타입을 직접 정의할 일은 거의 없다.
>
> **하지만 자바 프로그래머라면 예외 없이 자바가 제공하는 애너테이션 타입들은 사용해야 한다.**
>
> IDE나 정적 분석 도구가 제공하는 애너테이션을 사용하면 해당 도구가 제공하는 진단 정보의 품질을 높여줄 것이다.





```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

