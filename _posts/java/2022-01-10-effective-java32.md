---
title: 제네릭과 가변인수를 함께 쓸 때는 신중하라 - Effective Java[32]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 가변인수(varargs) 메소드와 제네릭은 베프가 될 수 없어!!

* **가변인수(varargs)** 메소드와 **제네릭**은 자바 5 때 함께 추가되었으니 **서로 잘 어우러지리라 기대하겠지만, <span style="color:red;">슬프게도 그렇지 않다.</span>**



* **가변인수는** 메소드에 넘기는 인수의 개수를 클라이언트가 조절할 수 있게 해주는데, 구현 방식에 <span style="color:red;">허점</span>이 있다.

  * 가변인수 메소드를 호출하면 가변인수를 담기 위한 **배열**이 자동으로 하나 만들어진다.

  

  * 그런데 내부로 감춰야 했을 이 배열을 <span style="color:red;">클라이언트에게 노출하는 문제</span>가 생겼다.

  

  * <span style="color:red;">그 결과</span> varargs 매개변수에 제네릭이나 매개변수화 타입이 포함되면 **알기 어려운 컴파일 경고가 발생한다.**



* **실체화 불가 타입**은 런타임에는 컴파일타임보다 타입 관련 정보를 **적게** 담고 있다.

  * **거의 모든 제네릭과 매개변수화 타입은 실체화되지 않는다.**

  

  * 메소드를 선언할 때 실체화 불가 타입으로 **varargs** 매개변수를 선언하면 <span style="color:red;">컴파일러가 경고</span>를 보낸다.

  

  * 가변 인수 메소드를 호출할 때도 **varargs** 매개변수가 실체화 불가 타입으로 추론되면, 그 호출에 대해서도 다음과 같이 경고를 낸다.

```
warning: [unchecked] Possible heap pollution from
	parameterized vararg type List<String>
```



* ***매개변수화 타입의 변수가***  **타입이 다른 객체를 참조하면 <span style="color:red;">힙 오염</span>이 발생한다**.
  * 이렇게 다른 타입 객체를 참조하는 상황에서는 컴파일러가 자동 생성한 형변환이 실패할 수 있으니, **제네릭 타입 시스템이 약속한 타입 안정성의 근간이 흔들려버린다.**



<hr>



**💎 제네릭과 varargs를 혼용하면 타입 안정성이 깨진다.**

```java
static void dangerous(List<String>... stringLists) {
    List<Integer> intList = List.of(42);
    Object[] objects = stringLists;
    objects[0] = intList;	// 힙 오염 발생
    String s = stringLists[0].get(0); //ClassCastException
}
```

* 이 메소드에서는 형변환하는 곳이 보이지 않는데도 인수를 건네 호출하면 **ClassCastException**을 던진다.

  * 매개변수로 받은 타입은 **String**이고, **Object** 배열에 옮겨 담았지만, **Object** 배열의 첫번째 인덱스를 **Integer List** 값으로 할당하는 순간 **객체의 원본이 오염된다**.

  

  * 마지막 줄에 컴파일러가 생성한(보이지 않는) 형변환이 숨어 있기 때문이다.



* 이처럼 타입 안정성이 깨지니 **제네릭 varargs 배열 매개변수에 값을 저장하는 것은 <span style="color:red;">안전하지 않다.</span>**



<hr>



##### 💎 제네릭 배열을 직접 생성하는건 안되면서 제네릭 varargs 매개변수를 받는 메소드 선언은 왜 돼?

* 제네릭이나 매개변수화 타입의 **varargs** 매개변수를 받는 메소드가 **실무에서 매우 유용하기 때문이다.**

  * 그래서 언어 설계자는 이 모순을 수용하기로 했다.

  

* 사실 자바 라이브러리도 이런 메소드를 여럿 제공한다.

  * ex) `Arrays.asList(T... a)`, `Collections.addAll(Collection<? super T> c`, `T... elements)`, `EnumSet.of(E first, E... rest)`

  

  * 다행인점은 이들은 **타입안전하다**.



<hr>



#### 🔗 @SafeVarargs 두둥 등장!!

* 자바 7 이전에는 제네릭 가변인수 메소드의 작성자가 호출자 쪽에서 발생하는 경고에 대해서 해줄 수 있는 일이 없었다.



* 사용자는 이 경고들을 그냥 두거나 호출하는 곳마다 **@SuppressWarnings("unchecked")** 애너테이션을 달아 경고를 숨겨야 했다.
  * **지루한 작업이고, 가독성을 떨어뜨리고, 때로는 진짜 문제를 알려주는 경고마저 숨기는 안좋은 결과로  이어졌다.**



* 자바 7 부터는 **@SafeVarargs** 어노테이션이 추가되어 **제네릭 가변인수 메소드 작성자가 클라이언트 측에서 발생하는 경고를 숨길 수 있게 되었다.**



* **@SafeVarargs 어노테이션은 메소드 작성자가 그 메소드가 <span style="color:red;">타입 안전함을 보장</span>하는 장치다.**

  * 컴파일러는 이 약속을 믿고 그 메소드가 안전하지 않을 수 있다는 경고를 더 이상 하지 않는다.

  

  * **메소드가 안전한게 확실하지 않다면** <span style="color:red;">절대</span> @SafeVarargs 애노테이션을 달아서는 안 된다.



<hr>



##### 💎  메소드가 안전한지는 어떻게 확신해?

* 가변인수 메소드를 호출할 때 **varargs** 매개변수를 담는 **제네릭 배열이 만들어진다는 사실**을 기억하자.

  * **메소드가 이 배열에 아무것도 저장하지 않**고(그 매개변수들을 덮어쓰지 않고), 
    **그 배열의 참조가 밖으로 노출되지 않는다면**(신뢰할 수 없는 코드가 배열에 접근할 수 없다면) <span style="color:red;">타입 안전하다.</span>

  

  * <span style="color:red;">즉,</span> 이 **varargs** 매개변수 배열이 호출자로부터 그 메소드로 **순수하게 인수들을 전달하는 일만 한다면**(varargs의 목적대로만 쓰인다면) <span style="color:red;">그 메소드는 안전하다.</span>

  

  * 이때, **varargs** 매개변수 **배열에 아무것도 저장하지 않고도 타입 안정성을 깰 수 있으니** 주의해야 한다.

<br>



**💎 자신의 제네릭 매개변수 배열의 참조를 노출한다. - 안전하지 않다.**

```java
static <T> T[] toArray(T... args) {
	return args;
}
```

* 이 메소드가 반환하는 **배열의 타입**은 이 메소드에 인수를 넘기는 **컴파일 타입에 결정**되는데, 그 시점에는 컴파일러에게 **충분한 정보가 주어지지 않아** **<span style="color:red;">타입을 잘못 판단</span>**할 수 있다.



* <span style="color:red;">따라서</span> 자신의 varargs 매개변수 **배열을 그대로 반환하면** 힙 오염을 **이 메소드를 호출한 쪽의 콜스택으로까지 전이하는 결과**를 낳을 수 있다.

<br>



**💎 T 타입 인수 3개를 받아 그중 2개를 무작위로 골라 담은 배열을 반환**

```java
static <T> T[] pickTwo(T a, T b, T c) {
    switch(ThreadcLocalRandom.current().nextInt(3)) {
        case 0: return toArray(a, b);
        case 1: return toArray(a, c);
        case 2: return toArray(b, c);
    }
    throw new AssertionError(); //도달할 수 없다.
}
```

* 이 메소드는 제네릭 가변인수를 받는 **toArray** 메소드를 호출한다는 점만 빼면 위험하지 않고 경고도 내지 않을 것이다.



* **toArray**가 반환하는 **배열의 타입은 Object[]**이다.
  **pickTwo**에 어떤 타입의 객체를 넘기더라도 담을 수 있는 **가장 구체적인 타입**이기 때문이다.
  <span style="color:red;">즉,</span> pickTwo 메소드는 **항상 Object[] 타입 배열을 반환**한다는 것이다.

<br>



**💎 pickTwo 메소드를 사용하는 main 메소드**

```java
public static void main(String[] args) {
    String[] attributes = pickTwo("좋은", "빠른", "저렴한");
}
```

* 위 코드는 컴파일시 별다른 경고는 발생하지 않지만, 실행하면 **ClassCastException**이 발생한다.



* 위에서 말했듯 pickTwo 메소드가 반환하는 타입은 항상 **Object[]** 배열이다.  

  * **Object[]**는 **String[]**의 **하위 타입이 아니므로 이 형변환은 실패**한다.

  

* 힙 오염을 발생시킨 진짜 원인인 toArray로 부터 두 단계나 떨어져 있고, varargs 매개변수 배열은 실제 매개변수가 저장된 후 변경된 적도 없다.



* 위 예는 **제네릭 varargs 매개변수 배열**에 **다른 메소드가 접근하도록 허용하면 <span style="color:red;">안전하지 않다는 점</span>**을 다시 한번 상기 시킨다.

  

<hr>



**💎 제네릭 varargs 매개변수 배열**에 **다른 메소드가 접근하도록 허용하면 <span style="color:red;">안전한 예외</span>**



* **@SafeVarargs로 제대로 애노테이트된** 또 다른 varargs 메소드에 넘기는 것은 **안전하다.**



* 그저 이 배열 내용의 일부 함수를 호출만 하는 (varargs를 받지 않는) 일반 메소드에 넘기는 것도 안전하다.

<br>

**💎 제네릭 varargs 매개변수를 안전하게 사용하는 메소드**

```java
@SafeVarargs
static <T> List<T> flatten(List<? extends T>... lists) {
    List<T> result = new ArrayList<>();
    for ( List<? extends T> list : lists ) {
        result.addAll(list);
    }
    return result;
}
```

* 위 메소드는 임의 개수의 리스트를 인수로 받아, 받은 순서대로 그 안의 모든 원소를 하나의 리스트로 옮겨 담아 반환한다.



* **@SafeVarargs** 애노테이션이 달려 있으니 선언하는 쪽과 사용하는 쪽 모두에서 경고를 내지 않는다.

<hr>



#### 🔗 @SafeVarargs 애노테이션을 사용해야 할 때를 정하는 규칙

* @SafeVarargs 애노테이션을 사용해야 할 떄를 정하는 규칙은 간단하다.

  

* **제네릭이나 매개변수화 타입의 varargs 매개변수를 받는 모든 메소드에 @SafeVarargs를 달아라.**

  * 그래야 사용자를 헷갈리게 하는 컴파일러 경고를 없앨 수 있다.

    

  * 안전하지 않은 varargs 메소드는 절대 작성해서는 안 된다는 뜻이기도 하다.



* 정리 하자면 다음 두 조건을 모두 만족하는 제네릭 varargs 메소드는 안전하다. **둘 중 하나라도 어겼다면 수정하라.**

  * varargs 매개변수 배열에 아무것도 저장하지 않는다.

  

  * 그 배열(혹은 복제본)을 신뢰할 수 없는 코드에 노출하지 않는다.



<br>

> **@SafeVarargs 애노테이션은 재정의할 수 없는 메소드에만 달아야 한다.**
>
> 재정의한 메소드도 안전할지는 보장할 수 없기 때문이다.
>
> 자바 8에서 이 애노테이션은 오직 정적 메소드와 final 인스턴스 메소드에만 붙일 수 있고
>
> 자바 9부터는 private 인스턴스 메소드에도 허용된다.



<hr>



#### 🔗 @SafeVarargs 애노테이션이 유일한 정답은 아니라고?



* **(실체는 배열인) varargs 매개변수를 <span style="color:red;">List 매개변수로 바꿀 수도 있다.</span>**

<br>



**💎 제네릭 varargs 매개변수를 List로 대체한 예 - 타입 안전하다.**

```java
static <T> List<T> flatten(List<List? extends T>> lists) {
    List<T> result = new ArrayList<>();
    for ( List<? extends T> list : lists ) {
        result.addAll(list);
    }
    return result;
}
```

* 정적 팩토리 메소드인 **List.of**를 활용하면 다음 코드와 같이 이 메소드에 임의개수의 인수를 넘길 수 있다.

<br>

```java
audience = flatten(List.of(friends, romans, countrymen));
```

* 이렇게 사용하는게 가능한 이유는 **List.of**에도 **@SafeVarargs** 애노테이션이 달려 있기 때문이다.



* **이 방식의 장점은 컴파일러가 이 메소드의 타입 안정성을 검증할 수 있다는데 있다.**
  * **@SafeVarargs** 애노테이션을 우리가 직접 달지 않아도 되며, 실수로 안전하다고 판단할 걱정도 없다.
  * 단점이라면 클라이언트 코드가 살짝 지저분해지고 속도가 조금 느려질 수 있다는 정도다



* **또한 이 방식은 위 toArray 메소드 처럼 varargs 메소드를 안전하게 작성하는게 불가능한 상황에서도 쓸 수 있다.**
  * 이 toArray의 List 버전이 바로 List.of 버전이다.

<br>



**💎 List.of를 적용한 pickTwo, main 메소드** - 타입 안전하다

```java
statifc <T> List<T> pickTwo(T a, T b, T c) {
    switch(ThreadLocalRandom.current().nextInt(3)) {
        case 0: return List.of(a, b);
        case 1: return List.of(a, c);
        case 2: return List.of(b, c);
    }
    throw new AssertionError();
}

public static void main(String[] args) {
    List<String> attributes = pickTwo("좋은", "빠른", "저렴한")
}
```



<hr>



> 가변인수와 제네릭은 궁합이 좋지 않다.
>
> 가변인수 기능은 배열을 노출하여 추상화가 완벽하지 못하고, 
>
> **배열과 제네릭의 타입 규칙이 서로 다르기 때문이다.**
>
> **제네릭 varargs 매개변수는 타입 안전하지는 않지만, 허용된다.**
>
> 메소드에 제네릭 (혹은 매개변수화된) varargs 매개변수를 사용하고자 한다면,
>
> 먼저 그 메소드가 타입 안전한지 확인한 다음 @SafeVarargs 애노테이션을 달아 사용하는 데
>
> 불편함이 없게끔 하자.







```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

