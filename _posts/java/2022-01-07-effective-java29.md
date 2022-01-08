---
title: 이왕이면 제네릭 타입으로 만들라 - Effective Java[29]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 제네릭 관련 용어

| 한글용어                 | 영문용어                | 예                                 |
| ------------------------ | ----------------------- | ---------------------------------- |
| 매개변수화 타입          | parameterized type      | `List<String>`                     |
| 실제 타입 매개변수       | actual type parameter   | String                             |
| 제네릭 타입              | generic type            | `List<E>`                          |
| 정규 타입 매개변수       | formal type parameter   | E                                  |
| 비한정적 와일드카드 타입 | unbounded wildcard type | `List<?>`                          |
| 로 타입                  | raw type                | List                               |
| 한정적 타입 매개변수     | bounded type parameter  | `<E extends Nubmer>`               |
| 재귀적 타입 한정         | recursive type bound    | `<T extends Comparable<T>>`        |
| 한정적 와일드카드 타입   | bounded wildcard type   | `List<? extends Number>`           |
| 제네릭 메소드            | generic method          | `static <E> List<E> asList(E[] a)` |
| 타입 토큰                | type token              | String.class                       |



<hr>



#### 🔗 제네릭 타입을 새로 만드는건 조금 더 어려워!



**💎 그렇지만 배워두면 그만한 값어치는 하지 ㅋㅋ**



**💎Object 기반 스택 - 제네릭이 절실한 강력 후보**

```java
public class Stack {
    private Object[] elements;
    private int size = 0;
    private static final int DEFAULT_INITIAL_CAPACITY = 16;
    
    public Stack() {
        elements = new Object[DEFAULT_INITIAL_CAPACITY];
    }
    
    public void push(Object e) {
        ensureCapacity();
        elements[size++] = e;
    }
    
    public Object pop() {
        if (size == 0) {
            throw new EmptyStackException();
        }
        Object result = elements[--size];
        elements[size] = null;
        return result;
    }
    
    public boolean isEmpty() {
        return size == 0;
    }
    
    private void ensureCapcity() {
        if ( elements.length == size ) {
            elements = Arrays.copyOf(elements, 2 * size + 1);
        }
    }
}
```

* 위 클래스를 제네릭 타입으로 만들어보자.



* 일반 클래스를 제네릭 클래스로 만드는 **첫 단계는 클래스 선언에 타입 매개 변수를 추가하는 일이다.**



* 이때 타입 이름으로는 보통 E를 사용한다.



<hr>



##### 💎 제네릭 스택으로 가는 첫 단계 - 컴파일 되지 않는다.

```java
private class Stack<E> {
    private E[] elements;
    private int size = 0;
    private static final int DEFAULT_INITIAL_CAPACITY = 16;
    
    public Stack() {
        elements = new E[DEFAULT_INITIAL_CAPACITY];
    }
    
    public void push(E e) {
        ensureCapacity();
        elements[size++] = e;
    }
    
    public E pop() {
        if (size == 0) {
            throw new EmptyStackException();
        }
        E result = elements[--size];
        elements[size] = null;
        return result;
    }
    ...
}
```

* 이 단계에서는 다음과 같은 오류가 하나 발생한다. - **generic array creation**



* **elements = new <span style="color:red">E</span>[DEFAULT_INITIAL_CAPAACITY];** 

  * <span style="color:red;">E</span>와 같은 **실체화 불가 타입으로는 배열을 만들 수 없다.**

  

  * 배열을 사용하는 코드를 제네릭으로 만들려 할 때는 이 문제가 항상 발목을 잡을 것이다.

  

  * 적절한 해결책은 **두 가지다.**



<hr>




##### 💎 첫번째 : 제네릭 배열 생성을 금지하는 제약을 대놓고 우회하기



* **Object 배열을 생성한 다음 제네릭 배열로 형변환** 해보자.

  

* 이제 컴파일러는 오류 대신 아래와 같이 경고를 내보낼 것이다.

```
Stack.java:8: warning: [unchecked] unchecked cast
found: Object[], required: E[]
		elements = (E[]) new Object[DEFAULT_INITIAL_CAPCITY];
```

* 컴파일러는 이 프로그램이 타입 안전한지 증명할 방법이 없지만 개발자는 알 수 있다.



* **따라서 이 비검사 형변환이 프로그램이 타입 안정성을 해치지 않음을 <span style="color:red;">스스로 확인해야 한다.</span>**
  
  * 문제의 배열 elements는 private 필드에 저장되고, 클라이언트로 반환되거나 다른 메소드에 전달되는 일이 전혀 없다.
  
  
  
  * push 메소드를 통해 배열에 저장되는 **원소의 타입은 항상 E다.**
  
  
  
  * 따라서 이 비검사 형변환은 **안전하다**.



* 비검사 형변환이 안전함을 직접 증명했다면 범위를 최소로 좁혀 아래와 같이 **@SuppressWarnings** 애너테이션으로 해당 경고를 숨긴다.

```java
// 배열 elements는 push(E)로 넘어온 e 인스턴스만 넘긴다.
// 따라서 타입 안정성을 보장하지만,
// 이 배열의 런타임 타입은 E[]가 아닌 Objects[]이다.

@SuppressWarnings("unchecked")
public Statck() {
    elements = ([E]) new Object[DEFAULT_INITIAL_CAPACITY];
}
```

* 위 방법은 가독성이 좋으며, 두 번째 방식에 비해 코드도 더 짧다.



* 배열의 타입을 E[]로 선언하여 오직 E 타입 인스턴스만 받음을 확실히 어필한다.



* 형변환을 배열 생성 시 단 한번만 해주면 된다.



* 현업에서 선호하는 방식이다.



* <span style="color:red;">하지만</span> (E가 Object가 아닌 한) 배열의 런타임 타입이 컴파일타임 타입과 달라 힙 오염을 일으킨다.



<hr>


##### 💎 두번째 : elements 필드의 타입을 E[]에서 Object[]로 바꾸는 것!

* 이렇게하면 다음과 같은 오류가 발생한다.

```java
Stack.java:19: incompatible types
found: Object, required: E
        E result = elements[--size];
```



* 배열이 반환한 원소를 e로 형변환 하면 오류 대신 다음과 같은 경고가 발생한다.

```java
Stack.java:19: warning: [unchecked] unchecked cast
found: Object, required: E
      	E result = (E) elements[--size];
```



* **E는 실체화 불가 타입**으므로 컴파일러는 런타임에 이뤄지는 형변환이 안전한지 증명할 방법이 없다.



* 마찬가지로 개발자가 직접 증명하고 경고를 숨길 수 있다.



* pop 전체 메소드 전체에서 경고를 숨기지 말고, **아래처럼 비검사 형변환을 수행하는 할당문만 숨길 수 있다.**

```java
//비검사 경고를 적절히 숨긴다
public E pop() {
    if (size == 0) {
        throw new EmptyStackException();
    }
    
    //push에서 E 타입만 허용하므로 이 형변환은 안전하다.
    @SuppressWarnings("unchecked") E result = (E) elements[--size];
    
    elements = null;
    return result;
}
```

* 위 방식은 배열에서 원소를 읽을 때 마다 형변환을 한다.



* 이 방식은 힙 오염이 맘에 걸리는 프로그래머가 첫 번째 방식보다 사용하는 방식이다.







<hr>


**💎 제네릭 타입 안에서 리스트를 사용하는게 항상 가능하지도, 꼭 좋지도 않다.**

* 자바가 리스트를 기본 타입으로 제공하지 않으므로 ArrayList 같은 제네릭 타입도 결국은 기본 타입인 배열을 사용해 구현해야 한다.



* HashMap같은 제네릭 타입은 성능을 높일 목적으로 배열을 사용하기도 한다.



<hr>



**💎 제네릭 타입 매개변수에 기본 타입은 사용 할 수 없다.**

* `Stack<int>`나 `Stack<double>`을 만들려고 하면 컴파일 오류가 난다.



* 자바 제네릭 타입 시스템의 근본적인 문제이나, 박싱된 기본 타입을 사용해 우회할 수 있다.





<hr>



**💎 타입 매개변수에 제약을 두는 제네릭 타입도 있어!**

* java.util.concurrent.DelayQueue는 다음처럼 선언되어 있다.

  

  * class DelayQueue`<E extends Delayed>` implements BlockingQueue`<E>`

  

  * 타입 매개변수 목록인 `<E extends Delayed>`는 java.util.concurrent.Delayed의 하위 타입만 받는다는 뜻이다.

  

  * 이렇게 하여 DelayQueue 자신과 DelayQueue를 사용하는 클라이언트는 DelayQueue의 원소에서 (형변환 없이) 곧바로 Delayed 클래스의 메소드를 호출 할 수 있다.

    * ClassCastException 걱정은 할 필요가 없다.

    

    * 이러한 타입 매개변수 E를 한정적 타입 매개변수라 한다.





<hr>



> 클라이언트에서 직접 형변환해야 하는 타입보다 제네릭 타입이 더 안전하고 쓰기 편하다.
>
> 그러니 새로운 타입을 설계할 때는 형변환 없이도 사용할 수 있도록 하라.
>
> 그렇게 하려면 제네릭 타입으로 만들어야 할 경우가 많다.
>
> 기존 타입 중 제네릭이었어야 하는게 있다면 제네릭 타입으로 변경하자.
>
> 기존 클라이언트에는 아무 영향을 주지 않으면서, 새로운 사용자를 훨씬 편하게 해주는 길이다.






```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

