---
title: 박싱된 기본 타입보다는 기본 타입을 사용하라 - Effective Java[61]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗  자바의 데이터 타입은 크게 두 가지로 나눌 수 있다.


* **int**, **double**, **boolean** 같은 <span style="color:red;">기본 타입</span>과 **String**, **List** 같은 <span style="color:red;">참조 타입</span>이다.




* 그리고 **각각의 기본 타입에는 대응하는 참조 타입**이 하나씩 있으며, 이를 <span style="color:red;">박싱된 기본 타입</span>이라고 한다.

  * ex) **int**, **double**, **boolean**에 대응하는 <span style="color:red;">박싱된 기본 타입</span>은 **Integer**, **Double**, **Boolean**이다.




* **오토박싱**과 **오토언박싱** 덕분에 크게 구분하지 않고 사용할 수는 있지만, 그렇다고 차이가 사라지는 것은 아니다.

  * 둘 사이에는 분명한 차이가 있으니 **어떤 타입을 사용하는지는 상당히 중요하다.**

  

  * <span style="color:red;">주의해서 선택해야 한다.</span>



<hr>



##### 💎 기본 타입과 박싱된 기본 타입의 주된 차이는 크게 세 가지다.

* **첫 번째**, 기본 타입은 값만 가지고 있으나, <span style="color:red;">박싱된 기본 타입은 값에 더해 식별성(identity)이란 속성을 갖는다.</span>
  * 박싱된 기본 타입의 **두 인스턴스는 값이 같아도 서로 다르다고 식별될 수 있다.**



* **두 번째**, 기본 타입의 값은 언제나 유효하나, **박싱된 기본 타입은 유효하지 않은 값, 즉 null을 가질 수 있다.**



* **세 번째**, <span style="color:red;">기본 타입</span>이 박싱된 기본 타입보다 <span style="color:red;">시간과 메모리 사용면에서 더 효율적이다.</span>



* 이상의 세 가지 차이 때문에 주의하지 않고 사용하면 진짜로 문제가 발생할 수 있다.



<hr>



💎 **잘못 구현된 비교자 - 문제를 찾아보라!**

* 다음은 **Integer** 값을 오름차순으로 정렬하는 비교자다
  * 비교자의 **compare** 메서드는 첫 번째 원소가 두 번째 원소보다 작으면 음수, 같으면 0, 크면 양수를 반환한다. (사실 **Integer**는 그 자체로 순서가 있다.)

```java
Comparator<Integer> naturalOrder = 
    (i, j) -> (i < j) ? -1 : ( i == j ? 0 : 1 );
```

<br>

* 위 코드를 테스트 해봐도 잘 동작하지만, 실제로는 <span style="color:red;">심각한 결함이 숨어 있다.</span>

  * **naturalOrder.compare(new Integer(42), new Integer(42))**의 값을 출력해보면 **예상 결과값은 0이지만, 실제로는 1을 출력한다.**

  

  * <span style="color:red;">즉</span>, 첫번째 **Integer**가 두 번째보다 크다고 주장한다.



* **naturalOrder**의 첫 번째 검사 (i < j)는 잘 작동한다.

  * 여기서 i와 j가 참조하는 오토박싱된 **Integer** 인스턴스는 기본 타입 값으로 변환된다.

  

  * 그런 다음 첫 번째 정숫값이 두 번째 값보다 작은지를 평가한다.

  

  * 만약 작지 않다면 두 번째 검사 **(i == j)**이 이뤄진다.

  

  * <span style="color:red;">그런데</span> 두 번째 검사에서는 **두 '객체 참조'의 식별성을 검사하게 된다.**

  

  * i와 j가 서로 다른 **Integer** 인스턴스라면 (비록 값은 같더라도) 이 비교의 결과는 false가 되고, 비교자는 1을 반환한다.

  

  * <span style="color:red;">즉</span>, 첫 번째 **Integer** 값이 두 번째보다 크다는 것이다.



* **박싱된 기본 타입에 == 연산자를 사용하면 오류가 일어난다.**



<hr>



💎  **기본 타입을 다루는 비교자가 필요하다면 Comparator.naturalOrder()를 사용하자.**

* 비교자를 직접 만들면 비교자 생성 메서드나 기본 타입을 받는 정적 **compare** 메서드를 사용해야 한다.



* 그렇더라도 이문제를 고치려면 아래와 같이 **지역변수 2개를 두어** 각각 박싱된 **Integer** 매개변수의 값을 **기본 타입 정수로 저장한 다음**, 모든 비교를 이 기본 타입 변수로 수행해야 한다.
  * 이렇게 하면 오류의 원인인 식별성 검사가 이뤄지지 않는다.



💎 **문제를 수정한 비교자**

```java
Comparator<Integer> naturalOrder = (iBoxed, jBoxed) -> {
    int i = iBoxed, j = jBoxed; // 오토박싱
    return i < j ? -1 : ( i == j ? 0 : 1);
};
```



<hr>



##### 💎 기본 타입과 박싱된 기본 타입을 혼용한 연산에서는 <span style="color:red;">박싱된 기본 타입의 박싱이 자동으로 풀린다.</span>

```java
public class Unbelievable {
    static Integer i;
    
    public static void main(String[] args) {
        if (i == 42) {
            System.out.println("믿을 수 없군!");
        }
    }
}
```

* 위 프로그램의 결과는 **NullPointerException**을 던지는 것이다.

  * 원인은 **i**가 **int**가 아닌 **Integer**이며, 다른 참조 타입 필드와 마찬가지로 **i**의 초깃값도 **null**이라는 데 있다.

  

  * 즉, **i == 42**는 **Integer**와 **int**를 비교하는 것이다.

  

  * <span style="color:red;">거의 예외 없이</span> 기본 타입과 박싱된 기본 타입을 혼용한 연산에서는 박싱된 기본 타입의 박싱이 자동으로 풀린다.

    * 그리고 **null 참조를 언박싱하면** **NullPointerException**이 발생한다.

    

  * 다행히 해법은 i를  int로 선언해주면 끝이다.

<hr>



💎 **끔직이 느린 예시**

```java
public static void main(String[] args) {
    Long sum = 0L;
    for (long i = 0; i <= Integer.MAX_VALUE; i++) {
        sum += i;
    }
    System.out.println(sum);
}
```

* 위 코드는 실수로 지역변수 sum을 박싱된 기본 타입으로 선언하여 느려졌다.

  

* 오류나 경고 없이 컴파일되지만, 박싱과 언박싱이 반복해서 일어나 체감될 정도로 성능이 느려진다.



<hr>



##### 💎 그렇다면 박싱된 기본 타입은 언제 써야 하는가?

* **첫 번째**, <span style="color:red;">컬렉션의 원소, 키, 값으로 쓴다.</span>

  * **컬렉션은** 기본 타입을 담을 수 없으므로 **어쩔 수 없이 박싱된 기본 타입을 써야만 한다.**

  

  * 더 일반화해 말하면, <span style="color:red;">매개변수화 타입이나 매개변수화 메서드의 타입 매개변수</span>로는 **박싱된 기본 타입을 써야 한다.**
    * ex) 변수를 `ThreadLocal<int>` 타입으로 선언하는 건 불가능하며, 대신 `ThreadLocal<Integer>`를 써야한다.

  

* <span style="color:red;">마지막으로</span>, **리플렉션**을 통해 **메서드를 호출**할 때도 **박싱된 기본 타입을 사용해야 한다.**



<hr>



> 기본 타입과 박싱된 기본 타입 중 하나를 선택해야 한다면 가능하면 기본 타입을 사용하라.
>
> 기본 타입은 간단하고 빠르다. 박싱된 기본 타입을 써야 한다면 주의를 기울이자. 
>
> 
>
> 오토박싱이 박싱된 기본 타입을 사용할 때의 번거로움을 줄여주지만, 그 위험까지 없애주지는 않는다.
>
> 두 박싱된 기본 타입을 == 연산자로 비교한다면 식별성 비교가 이뤄지는데, 이는 원한게 아닐 가능성이 크다.
>
> 
>
> **같은 연산에서 기본 타입과 박싱된 기본 타입을 혼용하면 언박싱이 이뤄지며, 언박싱 과정에서 NullPointerException을 던질 수 있다.**
>
> 
>
> 마지막으로, 기본 타입을 박싱하는 작업은 필요 없는 객체를 생성하는 부작용을 나을 수 있다.











```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

