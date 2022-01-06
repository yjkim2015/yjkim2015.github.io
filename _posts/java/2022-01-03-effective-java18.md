---
title: 상속보다는 컴포지션을 사용하라. - Effective Java[18]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---

상속은 코드를 재사용하는 강력한 수단이지만, 항상 최선은 아니다.

잘못 사용하면 오류를 내기 쉬운 소프트웨어를 만들게 된다.

상위 클래스와 하위 클래스를 모두 같은 프로그래머가 통제하는 패키지 안에서라면 상속도 안전한 방법이다.

<br>

**<span style="color:red">하지만</span> 일반적인 구체 클래스를 패키지 경계를 넘어, 즉 다른 패키지의 구체 클래스를 상속하는 일은 위험하다.**

<hr>

#### 🔗 메소드 호출과 달리 상속은 캡슐화를 깨뜨린다.

* 상위 클래스가 어떻게 구현되느냐에 따라 하위 클래스의 동작에 이상이 생길 수 있다.
* 상위 클래스는 릴리즈마다 내부 구현이 달라질 수 있으며, 그 여파로 코드 한 줄 건드리지 않은 하위 클래스가 오동작 할 수 있다.

<br>



#### 💎 상속의 잘못된 예시

InstrumentedHashSet 클래스는 객체가 처음 생성된 이후 원소가 몇 개 더해졌는지를 확인하기 위해 HashSet을 상속받아 add, addAll 메소드를 재정의 했다.

```java
public class InstrumentedHashSet<E> extends HashSet<E> {
    //추가된 원소의 수
    private int addCount;
    
    public InstrumentedHashSet() {
    }
    
    public InstrumentedHashSet(int initCap, float loadFactor) {
        super(initCap, loadFactor);
    }
    
    @Override
    public boolean add(E e) {
        addCount++;
        return super.add(e);
    }
    
    @Override
    public boolean addAll(Collection<? extends E> c) {
        addCount += c.size();
        return super.addAll(c);
    }
    
    public int getAddCount() {
		return addCount;
    }
}
```

**위 클래스의 addAll 기능은 생각했던 결과 값이 나오지 않는다.**

예를들어 이 클래스 인스턴스에 addAll 메소드로 원소 3개를 더해보자.

getAddCount시 예상 값은 3이지만 6이 나온다.

<span style="color:red;">이유는 아래의 HashSet 클래스에 나와있다.</span>

```java
public class HashSet<E> extends AbstractSet<E> implements Set<E>, Cloneable, java.io.Serializable {
    // ...

    public HashSet(Collection<? extends E> c) {
        map = new HashMap<>(Math.max((int) (c.size() / .75f) + 1, 16));
        addAll(c); // super의 addAll 메서드를 호출한다.
    }

    // ...
}
```

HashSet 클래스는 AbstractSet 클래스를 상속 받고 있다.

```java
public abstract class AbstractSet<E> extends AbstractCollection<E> implements Set<E> {
    /**
     * Sole constructor.  (For invocation by subclass constructors, typically
     * implicit.)
     */
    protected AbstractSet() {
    }
}
```

AbstractSet 클래스는 AbstractCollection 클래스를 상속 받고 있는데,

AbstractCollection에는 addAll 메소드가 정의 되어 있다.

```java
public abstract class AbstractCollection<E> implements Collection<E> {
    // ...

    public boolean addAll(Collection<? extends E> c) {
        boolean modified = false;
        for (E e : c)
            if (add(e))
                modified = true;
        return modified;
    }

    // ...
}
```

InstrumentedHashSet 의 addAll은 addCount에 3을 더한 후 상위 클래스인  HashSet의 addAll을호출한다.

**HashSet의 addAll은 HashSet이 상속하고 있는 상위 클래스의 addAll 메소드이며,**

**각 원소를 add 메서드를 호출해 추가 한다.**

<br>

<span style="color:red;">따라서</span> addCount에 값이 중복해서 더해져, 최종값이 6으로 늘어 난 것이다.

<hr>



#### 💎 해결법은 없는 거야!?

**하위 클래스에서 addAll 메소드를 재정의 하지 않으면 문제를 고칠 수 있다.**

<span style="color:red;">하지만</span> 당장은 제대로 동작할지 모르나, HashSet의 addAll이 add메소드를 이용해 구현했음을 가정한 해법이라는 한계를 가진다.

이처럼 자신의 다른 부분을 사용하는 <span style="color:red;">'자기 사용'</span> 여부는 해당 클래스의 내부 구현 방식에 해당하며, 자바 플랫폼 전반적인 정책인지, 그래서 다음 릴리즈에서도 유지될 지는 알 수 없다. 이런 가정에 기댄 클래스는 깨지기 쉽다.

<br>

**addAll 메소드를 다른 식으로 재정의 할 수도 있다.** 주어진 컬렉션을 순회하며 원소 하나당 add 메소드를 한 번만 호출 하는 것이다.

<span style="color:red">하지만</span> 상위 클래스의 메소드 동작을 다시 구현하는 이 방식은 어렵고, 시간도 더 들고, 자칫 오류를 내거나 성능을 떨어뜨릴 수도 있다. 또한 하위 클래스에서는 접근할 수 없는 private 필드를 써야 하는 상황이라면 이 방식으로는 구현 자체가 불가능하다.

<hr>



#### 💎 아직 남았다. 하위 클래스가 깨지기 쉬운 이유

**다음 릴리즈에서 상위 클래스에 새로운 메소드를 추가한다면 어떨까?**

* **새로운 메소드를 사용해 <span style="color:red;">'허용되지 않은' </span>원소를 추가할 수 있게 된다.**
  * 보안 때문에 컬렉션에 추가된 모든 원소가 특정 조건을 만족해야만 하는 프로그램을 생각해보자. 그 컬렉션을 상속하여 원소를 추가하는 모든 메소드를 재정의해 필요한 조건을 먼저 검사하게끔 하면 될 것 같다.
  * **하지만 이 방식이 통하는 것은 상위 클래스에 또 다른 원소 추가 메소드가 만들어 지기 전 까지이다.**

<br>

**그럼 재정의 안하고 메소드 새로 만들면 괜찮지 않아?**

이 방식이 훨씬 안전한 것은 맞지만, 위험이 전혀 없는 것은 아니다.

* **다음 릴리즈에서 상위 클래스에 새 메소드가 추가됐는데, 만약 하위 클래스에 추가한 메소드와 시그니처가 같고 반환 타입은 다르다면 클래스는 컴파일 조차 되지 않는다.**



<hr>



#### 🔗  모든 것을 해결할 묘안 Composition!!

* **기존 클래스를 확장하는 대신, 새로운 클래스를 만들고 private 필드로 기존 클래스의 인스턴스를 참조하게 하자.**
  * 기존 클래스가 새로운 클래스의 구성요소로 쓰인다는 뜻에서 이러한 설계를 <span style="color:red;">Composition(구성) 컴포지션</span> 이라 한다.

* **새 클래스의 인스턴스 메소드들은 (private 필드를 참조하는) 기존 클래스의 대응하는 메소드를 호출해 그 결과를 반환한다.**
  * 이 방식을 전달(forwarding)이라 하며, 새 클래스의 메소드들을 전달 메소드(forwarding method)라 부른다.
  * 그 결과 새로운 클래스는 기존 클래스의 내부 구현 방식의 영향에서 벗어나며, 심지어 기존 클래스에 새로운 메소드가 추가되더라도 전혀 영향 받지 않는다.

<hr>

구체적인 예시를 보자.

**💎 래퍼클래스 [집합 클래스 자신]**

```java
public class InstrumentedSet<E> extends ForwardingSet<E> {
	private int addCount = 0;
    
    public InstrumentedSet(Set<E> s) {
		super(s);
    }
    
    @Override
    public boolean add(E e) {
        addCount++;
        return super.add(e);
    }
    
    @Override
    public boolean addAll(Collection<? extends E> c) {
        addCount += c.size();
        return super.addAll(c);
    }
    
    
}
```



**💎전달 메소드만으로 이루어진 재사용 가능한 전달 클래스**

```java
public class ForwardingSet<E> implements Set<E> {
    private final Set<E> s;

    public ForwardingSet(Set<E> s) {
        this.s = s;
    }

    public int size() {
        return 0;
    }

    public boolean isEmpty() {
        return s.isEmpty();
    }

    public boolean contains(Object o) {
        return s.contains(o);
    }

    public Iterator<E> iterator() {
        return s.iterator();
    }

    public Object[] toArray() {
        return s.toArray();
    }

    public <T> T[] toArray(T[] a) {
        return s.toArray(a);
    }

    public boolean add(E e) {
        return s.add(e);
    }

    public boolean remove(Object o) {
        return s.remove(o);
    }

    public boolean containsAll(Collection<?> c) {
        return s.containsAll(c);
    }

    public boolean addAll(Collection<? extends E> c) {
        return s.addAll(c);
    }

    public boolean retainAll(Collection<?> c) {
        return s.retainAll(c);
    }

    public boolean removeAll(Collection<?> c) {
        return s.removeAll(c);
    }

    public void clear() {
        s.clear();
    }

    @Override
    public boolean equals(Object o) {
        return s.equals(o);
    }

    @Override
    public int hashCode() {
        return s.hashCode();
    }

    @Override
    public String toString() {
        return s.toString();
    }
}
```

- InstrumentedSet은 HashSet의 모든 기능을 정의한 Set 인터페이스를 활용해 설계되어 견고하고 아주 유연하다.
  - 구체적으로는 Set 인터페이스를 구현했고, Set의 인스턴스를 인수로 받는 생성자를 하나 제공한다.
- 임의의 Set에 계측 기능을 덧씌워 새로운 Set으로 만드는 것이 이 클래스의 핵심이다.

<hr>

상속 방식은 구체 클래스를 각각 따로 확장해야 하며, 지원하고 싶은 상위 클래스의 생성자 각각에 대응하는 생성자를 별도로 정의해줘야 한다.
**<span style="color:red">반면</span>, 컴포지션 방식은 한 번만 구현해두면 어떠한 Set 구현체라도 계측할 수 있으며, 기존 생성들과도 함께 사용 할 수 있다.**



<br>

* 다른 Set 인스턴스를 감싸고(Wrap) 있다는 뜻에서 InstrumentedSet 같은 클래스를 **래퍼 클래스라** 한다.
* 다른 Set에 계층 기능을 덧씌운다는 뜻에서 데코레이터 패턴이라 한다.
* **래퍼 클래스**는 단점이 거의 없다. 
  * 한 가지, 래퍼 클래스가 콜백 프레임워크와는 어울리지 않는다는 점만 주의하면 된다.
  * 콜백 프레임 워크에서는 자기 자신의 참조를 다른 객체에 넘겨서 다음 호출(콜백) 때 사용하도록 한다.
  * 내부 객체는 자신을 감싸고 있는 래퍼 클래스의 존재를 모르니 대신 자신(this)의 참조를 넘기고, 콜백 때는 래퍼가 아닌 내부 객체를 호출하게 된다.
    이를 SELF 문제라고 한다.

<hr>



#### 🔗  그럼 상속은 언제 써~ ?

* **상속은 반드시 하위 클래스가 상위 클래스의 '진짜' 하위 타입인 상황에서만 쓰여야 한다.**
* **즉, 클래스 B가 클래스 A와 is-a [B는 A다] 관계일 때만 A를 상속해야 한다.**
* **만약 is-a 관계가 아니면 A는 B의 필수 구성요소가 아니라 구현하는 방법 중 하나 일뿐이다.**

<hr>



#### 💎 상속을 사용 하기로 결정 했다면 주의 해야 할 점

* 컴포지션 대신 상속을 사용하기로 결정하기 전에 마지막으로 자문해야할 질문이 있다. **확장하려는 클래스의 API에 아무런 결함이 없는가? 결함이 있다면, 이 결함이 구현하고자 하는 클래스의 API까지 전파돼도 괜찮은가?**
* **컴포지션으로는 이런 결함을 숨기는 API를 설계할 수 있지만, 상속은 상위 클래스의 API를 '그 결함까지도' 그대로 승계한다.**



<hr>



> 상속은 강력하지만 캡슐화를 해친다는 문제가 있다. 상속은 상위 클래스와 하위 클래스가 순수한 is-a 관계일 때만 써야 한다. 
>
> is-a 관계일 때도 안심할 수 만은 없는게, 하위 클래스의 패키지가 상위 클래스와 다르고, 상위 클래스가 확장을 고려해 설계되지 않았다면 여전히 문제가 될 수 있다.
>
> 상속의 취약점을 피하려면 상속 대신 컴포지션과 전달을 사용하자.
>
> 특히 래퍼 클래스로 구현할 적당한 인터페이스가 있다면 더욱 그렇다.
>
> 래퍼 클래스는 하위 클래스보다 견고하고 강력하다.





```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

