---
title: 상속을 고려해 설계하고 문서화하라. 그러지 않았다면 상속을 금지하라
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---




#### 🔗 상속을 고려한 설계와 문서화가 정확히 무슨 말이야?

* 메소드를 재정의하면 어떤 일이 일어나는지를 정확히 정리하여 문서로 남겨야 한다. 
  **즉, 상속용 클래스는 재정의 할 수 있는 메소드들을 내부적으로 어떻게 이용하는지(자기사용) 문서로 남겨야 한다.**
* 클래스의 API로 공개된 메소드에서 클래스 자신의 또 다른 메소드를 호출할 수도 있다. 그런데 호출되는 메소드가 재정의 가능 메소드라면 그 사실을 호출하는 메소드의 API설명에 적시해야 한다.



<hr>



##### 💎 Implementation Requirements? 

**API** 문서의 메소드 설명 끝에서 종종 위 문구로 시작하는 절을 볼 수 있는데, 그 메소드의 내부 동작 방식을 설명하는 곳이다.

이 절은 메소드 주석에 <span style="color:red;">@implSpec</span> 태그를 붙여주면 자바독 도구가 생성해준다.

<hr>

다음은 **java.util.AbstractCollection**에서 발췌한 예이다.



> public boolean remove(Object o)
>
> 주어진 원소가 이 컬렉션 안에 있다면 그 인스턴스 하나 제거한다(선택적 동작)
> 더 정확하게 말하면, 이 컬렉션 안에 'Object.equals(o, e) 가 참인 원소' e가 
> 하나 이상 있다면 그 중 하나를 제거한다. 주어진 원소가 컬렉션 안에 있었다면(즉, 호출 결과 이 컬렉션이 변경됐다면) true를 반환한다.
>
> Implementation Requirements : 이 메소드는 컬렉션을 순회하며 주어진 원소를 찾도록 구현되었다. 주어진 원소를 찾으면 반복자의 remove 메소드를 사용해 컬렉션에서 제거한다. 이 컬렉션이 주어진 객체를 갖고 있으나, 이 컬렉션의 iterator 메소드가 반환한 반복자가 remove 메소드를 구현하지 않았다면 UnsupportedOperationException을 던지니 주의하자.

<br>

**위 설명에 따르면 iterator 메소드를 재정의하면 remove 메소드의 동작에 영향을 줌을 알 수 있다. iterator 메소드로 얻은 반복자의 동작이 remove 메소드의 동작에 주는 영향도 정확히 설명 했다.**



**<span style="color:red;">클래스를 안전하게 상속할 수 있도록 하려면 내부 구현 방식을 설명해야만 한다.</span>**



> @impleSpec 태그는 자바 8에서 처음 도입되어 자바 9부터 본격적으로 사용되기 시작했다.

<hr>

#### 💎 훅 (Hook)?

효율적인 하위 클래스를 큰 어려움 없이 만들 수 있게 하려면 클래스의 내부 동작 과정 중간에 끼어들 수 있는 **훅(hook)**을 잘 선별하여 **protected** **메소드 형태로 공개해야 할 수도 있다.**

드물게는 protected 필드로 공개해야 할수도 있다.

<hr>

java.util.AbstractList의 removeRange 메소드를 예로 살펴보자.

> proctected void removeRange(int fromIndex, int toIndex)
>
> fromIndex(포함) 부터 toIndex(미포함)까지의 모든 원소를 이 리스트에서 제거한다.
>
> toIndex 이후의 원소들은 앞으로 (index만큼씩) 당겨진다. 이 호출로 리스트는 'toIndex - fromIndex' 만큼 짧아진다. (toIndex == fromIndex라면 아무 효과가 없다.)
>
> 이 리스트 혹은 이 리스트의 부분리스트에 정의된 clear 연산이 이 메소드를 호출한다. 리스트 구현의 내부 구조를 활용하도록 이 메소드를 재정의하면 이 리스트와 부분리스트의 clear 연산 성능을 크게 개선할 수 있다.
>
> Implementation Requirements : 이 메소드는 fromIndex에서 시작하는 리스트 반복자를 얻어 모든 원소를 제거할 때 까지 ListIterator.next와 ListIterator.remove를 반복 호출하도록 구현되었다. 
>
> 주의 : ListIterator.remove가 선형 시간이 걸리면 이 구현의 성능은 제곱이 비례한다.
>
> Parameters:
> 	fromIndex	제거할 첫 원소의 인덱스
> 	toIndex		 제거할 마지막 원소의 다음 인덱스

List 구현체의 최종 사용자는 removeRnage 메소드에 관심이 없다.

**그럼에도 불구하고 이 메소드를 제공하는 이유는 단지 하위 클래스에서 부분리스트의 <span style="color:red;">clear 메소드를 고성능으로 만들기 쉽게 하기 위해서이다.</span>**

removeRange 메소드가 없다면 하위 클래스에서 clear 메소드를 호출하면 제곱에 비례해 성능이 느려지거나 부분리스트의 메커니즘을 밑바닥 부터 새로 구현해야 했을 것이다.

<br>

**그렇다면 상속용 클래스를 설계 할 때 어떤 메소드를 protected로 노출해야 할지는 어떻게 결정 할까?**

특별한 방법은 없고 소위 말하는 <span style="color:red;">'노가다'</span>가 필요하다.

심사숙고해서 잘 예측해본 다음, 실제 하위 클래스를 만들어 시험해보는것이 최선이다.

**protected 메소드 하나하나가 내부 구현에 해당하므로 그 수는 가능한 한 적어야 한다. 한편으로는 너무 적게 노출해서 상속으로 얻는 이점마저 없애지 않도록 주의해야 한다.**

<hr>



#### 💎 상속 용 클래스를 시험하는 방법?

이또한 노가다다.. **즉,  상속용 클래스를 시험하는 방법은 직접 하위 클래스를 만들어 보는 것이 <span style="color:red">유일</span>하다**.

<br>

꼭 필요한 protected 멤버를 놓쳤다면 하위 클래스를 작성할 때 그 빈자리가 확연히 드러난다. 
거꾸로 하위 클래스를 여러 개 만들 때까지 전혀 쓰이지 않는 protected 멤버는
사실 private이었어야 할 가능성이 크다.

<br>

**널리 쓰일 클래스를 상속용으로 설계한다면 문서화한 내부 사용 패턴과, protected 메소드와 필드를 구현하면서 선택한 결정에 영원히 책임져야 함을 잘 인식해야 한다.**

이 결정들이 그 클래스의 성능과 기능에 영원한 족쇄가 될 수 있다.

**<span style="color:red">그러니</span> 상속용으로 설계한 클래스는 배포 전에 반드시 하위 클래스를 만들어 검증해야한다.**



<hr>

#### 🔗 상속을 허용하는 클래스가 지켜야 할 제약

**상속용 클래스의 생성자는 직접적으로든 간접적으로든 재정의 가능 메소드를 호출해서는 안된다.**

<br>

상위 클래스의 생성자가 하위 클래스의 생성자보다 먼저 실행되므로 하위 클래스에서 재정의한 메소드가 하위 클래스의 생성자보다 먼저 호출된다.

이때 그 재정의한 메소드가 <span style="color:red">하위 클래스의 생성자에서 초기화하는 값에 의존한다면 </span>의도대로 동작 하지 않을것이다.

<hr>

예시를 보자.

```java
public class Super {
    //잘못된 예 - 생성자가 재정의 가능 메소드를 호출한다.
    public Super() {
        overrideMe();
    }
    
    public void overrideMe() {
    }
}
```



```java
public final class Sub extends Super {
    //초기화 되지 않은 final 필드, 생성자에서 초기화 한다.
    private final Instant instant;
    
    Sub() {
        instant = Instant.now();
    }
    
    //재정의 가능 메소드, 상위 클래스의 생성자가 호출한다.
    @Override
    public void overrideMe() {
        System.out.println(instant);
    }
    
    public static void main(String[] args) {
        Sub sub = new Sub();
        sub.overrideMe();
    }
}
```

위 프로그램이 instant를 두 번 출력하리라 기대했겠지만, 첫 번째는 null을 출력한다. 상위 클래스의 생성자는 하위 클래스의 생성자가 인스턴스 필드를 초기화 하기도 전에 overrideMe를 호출하기 때문이다.

<hr>

> private, final, static 메소드는 재정의가 불가능하니 생성자에서 안심하고 호출해도 된다.

<hr>



#### 💎 상속의 설계를 더 어렵게 ! Cloneable, Serializable

Cloneable과 Serializable 인터페이스 둘 중 하나라도 구현한 클래스를 상속할 수 있게 설계하는 것은 일반적으로 좋지 않은 생각이다. 

그 클래스를 확장하려는 프로그래머에게 엄청난 부담을 지우기 때문이다.

<br>



clone과 readObject 메소드는 생성자와 비슷한 효과를 낸다(새로운 객체를 만든다). 

**즉, clone과 readObject 모두 직접적으로든 간접적으로든 재정의 가능 메소드를 호출해서는 안 된다.**

<br>

**readObject**의 경우 하위 클래스의 상태가 미처 다 역직렬화 되기 전에 재정의한 메소드부터 호출하게 된다.

**clone**의 경우 하위 클래스의 clone 메소드가 복제본의 상태를 (올바른 상태로) 수정하기 전에 재정의한 메소드를 호출한다.

<span style="color:red;">어느 쪽이든 프로그램 오작동으로 이어질 것이다.</span>

<br>

**마지막으로**, Serializable을 구현한 상속용 클래스가 **readResolve나 writeReplace** 메소드를 갖는다면 이 메소드들은 **private이 아닌 protected로 선언해야 한다.**

private으로 선언한다면 하위 클래스에서 상속을 허용하기 위해 내부 구현을 클래스 API로 공개하는 예 중 하나이다.



<hr>



> 상속용 클래스를 설계하기란 결코 만만치 않다. 
> 클래스 내부에서 스스로를 어떻게 사용하는지(자기사용 패턴) 모두 문서로 남겨야 하며, 일단 문서화한 것은 그 클래스가 쓰이는 한 반드시 지켜야 한다. 
> 그렇지 않으면 그 내부 구현 방식을 믿고 활용하던 하위 클래스를 오동작하게 만들 수 있다. 
>
> 다른 이가 효율 좋은 하위 클래스를 만들 수 있도록 일부 메소드를 protected로 제공해야 할 수도 있다.
>
> **그러니 클래스를 확장해야 할 명확한 이유가 떠오르지 않으면 상속을 금지하는 편이 나을 것이다.**
>
> **상속을 금지하려면 클래스를 final로 선언하거나 생성자 모두를 외부에서 접근할 수 없도록 만들면 된다.**





```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

