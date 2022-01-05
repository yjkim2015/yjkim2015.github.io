---
title: 비검사 경고를 제거하라
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 비검사 경고

**비검사 경고란 warning : [unchecked]를 말하며, casting 할 때 검사를 하지 않았다고 뜨는 경고이다.**



제네릭을 사용하기 시작하면 수많은 컴파일러 경고를 보게 될 것이다.

**비검사 형변환 경고, 비검사 메소드 호출 경고, 비검사 매개변수화 가변인수 타입 경고, 비검사 변환 경고 등이다.**



대부분의 비검사 경고는 쉽게 제거 할 수 있다.

<br>

**💎잘못된 코드 - warning [unchecked] unchecked conversion** 

```java
Set<Lark> exaltation = new HashSet();
```

* 위 코드 작성시 컴파일러는 무엇이 잘못됐는지 설명해 줄 것이다.



* 타입 매개변수를 명시하지 않고, 자바 7부터 지원하는 다이아몬드 연산자만으로도 해결 할 수 있다.
  * 컴파일러가 올바른 실제 타입 매개변수 (이 경우는 Lark)를 추론해준다.



<hr>



#### 💎 가능 하다면 모든 비검사 경고를 제거하라@@

* **모든 비검사 경고를 제거한다면 그 코드는 타입 안정성이 보장된다.**



* **런타임에 ClassCastException이 발생할 일이 없다.**



<hr>



##### 💎 경고를 제거할 수는 없지만 타입 안전하다고 확신할 수 있다면 @SuppressWarnings("unchecked") 애너테이션을 달아 경고를 숨기자.

* <span style="color:red;">단</span>, 타입 안전함을 검증하지 않은 채 **경고를 숨기면** 스스로에게 잘못된 보안 인식을 심어주는 꼴이다.
  * 그 코드는 경고 없이 컴파일되겠지만, 런타임에는 여전히 **ClassCastException**을 던질 수 있다.



* 안전하다고 검증된 비검사 경고를 **(숨기지 않고) 그대로 두면**, 진짜 문제를 알리는 새로운 경고가 나와도 눈치채지 못할 수 있다.
  * 제거하지 않은 수많은 거짓 경고 속에 새로운 경고가 파묻힐것이기 때문이다.



<hr>



##### 💎@SuppressWarnings 애너테이션은 항상 가능한 한 좁은 범위에 적용하자.

* @SuppressWarnings 애너테이션은 개별 지역변수 선언부터 클래스 전체까지 어떤 선언에도 달 수 있다.



* **<span style="color:red;">보통은</span> 변수 선언, 아주 짦은 메소드, 혹은 생성자가 될 것이다.**



* 자칫 심각한 경고를 놓칠 수 있으니 **<span style="color:red;">절대로</span> 클래스 전체에 적용해서는 안 된다.**



* 한 줄이 넘는 메소드나 생성자에 달린 @SuppressWarnings 애너테이션을 발견하면 지역변수 선언 쪽으로 옮기자. 다소 수고를 해야 할 수도 있지만, 그만한 값어치가 있을 것이다.

<br>



**💎 ArrayList에서 가져온 toArray 메소드 - warning : [unchecked] unchecked cast**

```java
public <T> T[] toArray(T[] a) {
	if (a.length < size) {
        return (T[]) Arrays.copyOf(elements, size, a.getClass());
    }
    System.arraycopy(elements, 0, a, 0, size);
    if (a.length > size) {
        a[size] = null;
    }
    return a;
}
```

* 위 코드를 컴파일하면 **warning : [unchecked] unchecked cast** 경고가 발생한다.



* 애너테이션은 선언에만 달 수 있기 때문에 return 문에는 **@SuppressWarnings**를 다는게 불가능하다.

  * 메소드 전체에 달고 싶겠지만, 범위가 필요 이상으로 넓어지니 자제하자.

  

  * **그 대신 반환값을 담을 지역변수를 하나 선언하고 그 변수에 애너테이션을 달아주자.**



<br>

**💎지역변수를 추가해 @SuppressWarnings의 범위를 좁힌다.**

```java
public <T> T[] toArray(T[] a) {
	if (a.length < size) {
        // 생성한 배열과 매개변수로 받은 배열의 타입이 모두 T[]로 같으므로
		// 올바른 형변환이다.
        @SuppressWarnings("unchecked") T[] result = 
            (T[]) Arrays.copyOf(elements, size, a.getClass());
        return result;
    }
    System.arraycopy(elements, 0, a, 0, size);
    if (a.length > size) {
        a[size] = null;
    }
    return a;
}
```

* **SuppressWarnings("unchecked") 애너테이션을 사용할 때면 그 경고를 무시해도 안전한 이유를 항상 주석으로 남겨야 한다.**



* 다른 사람이 그 코드를 이해하는데 도움이 되며, 더 중요하게는 다른 사람이 그 코드를 잘못 수정하여 타입 안정성을 잃는 상황을 줄여준다.



<hr>



> 비검사 경고는 중요하니 무시하지 말자.
>
> 모든 비검사 경고는 런타임에 ClassCastException을 일으킬 수 있는 잠재적 가능성을 뜻하니
>
> 최선을 다해 제거하라.
>
> 경고를 없앨 방법을 찾지 못하겠다면, 그 코드가 타입 안전함을 증명하고 가능한 한 범위를 좁혀
>
> @SuppressWarnings("unchecked") 애너테이션으로 경고를 숨겨라.
>
> 그런 다음 경고를 숨기기로 한 근거를 주석으로 남겨라.



```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

