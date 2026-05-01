---
title: 추상 클래스보다는 인터페이스를 우선하라 - Effective Java[20]
categories:
- EFFECTIVE_JAVA
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 인터페이스 (interface) , 추상 클래스 (abstract class)

자바가 제공하는 다중 구현 메커니즘은 인터페이스와 추상 클래스, 이렇게 두가지이다. 자바 8부터는 인터페이스도 디폴트 메소드를 제공할 수 있게 되어, 이제는 두 메커니즘 모두 인스턴스 메소드를 구현 형태로 제공할 수 있다.

<hr>



##### 💎 그럼 둘의 차이가 뭐야?

**둘의 가장 큰 차이는** <span style="color:red;">추상 클래스</span>가 정의한 타입을 구현하는 클래스는 **반드시** 추상 클래스의 하위 클래스가 되어야 한다는 점이다.

**자바는 단일 상속만 지원하니**, 추상 클래스 방식은 새로운 타입을 정의하는 데 
**커다란 제약**을 안게 되는 셈이다. 

<span style="color:red;">반면 인터페이스</span>가 선언한 메소드를 모두 정의하고 그 일반 규약을 잘 지킨 클래스라면 다른 어떤 클래스를 상속했든 같은 타입으로 취급 된다.



<hr>



#### 🔗 인터페이스 (interface)의 장점

* **기존 클래스에도 손쉽게 새로운 인터페이스를 구현해 넣을 수 있다.**

  * 인터페이스가 요구하는 메소드를 추가하고, 클래스 선언에 **implements** 구문만 추가하면 끝이다. 자바 플랫폼에서도 Comparable, Iterable, AutoCloseable 인터페이스가 새로 추가됐을 때 표준 라이브러리의 수많은 기존 클래스가 이 인터페이스들을 구현한채 릴리즈 됐다.

* **믹스인(mixin) 정의에 안성맞춤이다.**

  * **믹스인이란 클래스가 구현할 수 있는 타입으로, 믹스인을 구현한 클래스에 원래의 '주된 타입' 외에도 특정 선택적 행위를 제공한다고 선언하는 효과를 준다.**
  * **Comparable**은 자신을 구현한 클래스의 인스턴스들끼리는 순서를 정할 수 있다고 선언하는 믹스인 인터페이스이다.
  * 이처럼 대상 타입의 주된 기능에 선택적 기능을 '**혼합 (mixed in)**' 한다고 해서 믹스인이라 부른다. 
    추상 클래스로는 믹스인을 정의할 수 없다. 이유는 기존 클래스에 덧씌울 수 없기 때문이다.

* **계층구조가 없는 타임 프레임워크를 만들 수 있다.**

  * **타입을 계층적으로 정의하면 수많은 개념을 구조적으로 잘 표현할 수 있지만, 현실에는 계층을 엄격히 구분하기 어려운 개념도 있다.**
    에를 들어 가수 (Singer) 인터페이스와 작곡가(Songwriter) 인터페이스가 있다고 해보자.

    ```java
    public interface Singer {
        AudioClip sing(Song s);
    }
    public interface Songwriter {
        Song compose(int chartPosition);
    }
    ```

    우리 주변엔 작곡도 하는 가수가 제법 있다. 
    이 코드처럼 타입을 인터페이스로 정의하면 가수 클래스가 Singer와 Songwriter 모두를 구현해도 전혀 문제 되지 않는다. 

    <br>

    심지어 Singer와 Songwriter 모두를 확장하고 새로운 메소드까지 
    추가 한 제 3의 인터페이스를 정의 할 수도 있다.

    ```java
    public interface SingerSongwriter extends Singer, SongWriter {
        AudioClip strum();
        void actSensitive();
    }
    ```

    <span style="color:red;">반면에</span> 같은 구조를 클래스로 만들려면 가능한 조합 전부를 각각의 클래스로 정의한 고도비만 계층구조가 만들어 질 것이다.

<hr>



#### 💎 래퍼 클래스 관용구와 함께라면!! 기능 향상! 안전하고 강력한 수단

* 타입을 추상 클래스로 정해두면 그타입에 기능을 추가하는 방법은 상속뿐이다.

* 상속해서 만든 클래스는 래퍼 클래스보다 활용도가 떨어지고 깨지기는 더 쉽다.



<hr>



#### 💎 나는야 이름하여 디폴트(default) 메소드

자바 8부터 인터페이스는 디폴트 메소드를 갖게 되었다. 

디폴트 메소드는 body, 즉 구현을 가진 메소드라고 보면 된다.

**인터페이스의 메소드 중 구현 방법이 명백한 것이 있다면,** 그 구현을 디폴트 메소드로 제공해 프로그래머들의 일감을 덜어줄 수 있다.

디폴트 메소드를 제공할 때는 앞에서 배운 <span style="color:red;">@implSpec</span> 자바 독 태그를 붙여 상속하려는 사람을 위한 설명을 문서화 해야한다.

<hr>



##### 💎 디폴트 메소드의 제약

* 많은 인터페이스가 eqauls와 hashCode와 같은 Object의 메소드를 정의하고 있지만, 이들은 디폴트 메소드로 제공해서는 안 된다.
* 인터페이스는 인스턴스 필드를 가질 수 없고 public이 아닌 정적 멤버도 가질 수 없다.(단, private 정적 메소드는 예외)
* 직접 만들지 않은 인터페이에는 디폴트 메소드를 추가할 수 없다.



<hr>



#### 🔗 인터페이스와 추상 클래스의 장점을 모두 취하는 방법이 있다고?

인터페이스와 추상 골격 구현(skeletal implementation) 클래스를 함께 제공하는  방법이다.

* **인터페이스로는 타입을 정의하고**, 필요하면 디폴트 메소드 몇 개도 함께 제공한다.
* **골격 구현 클래스는 나머지 메소드들까지 구현한다.**
* 이렇게하면 단순히 골격 구현을 확장하는 것만으로 이 인터페이스를 구현하는 데 필요한 일이 대부분 완료된다.
* 이를 <span style="color:red;">템플릿 메소드 패턴</span>이라 부른다.

* 관례상 인터페이스 이름이 ***Interface***라면 그 골격 구현 클래스의 이름은 ***AbstractInterface***로 짓는다. 
  좋은 예로, 컬렉션 프레임워크의 AbstractCollection, AbstractSet, AbstractList, AbstractMap 각각이 바로 핵심 컬렉션 인터페이스의 골격 구현이다.

* 제대로 설계 했다면 골격 구현은 (**독립된 추상 클래스든 디폴트 메소드로 이루어진 인터페이스든**) 그 인퍼테이스로 나름의 구현을 만들려는 프로그래머의 일을 상당히 덜어준다.



<hr>

예시를 보자.

**💎 골격 구현을 사용해 완성한 구체 클래스**

```java
static List<Integer> intArrayAsList(int[] a) {
    Objects.requireNonNull(a);
    
   	//다이아몬드 연산자를 이렇게 사용하는 건 자바 9부터 가능하다.
    //더 낮은 버전을 사용한다면 <Integer>로 수정하자.
    return new AbstractList<>() {
		@Override
        public Integer get(int i) {
            return a[i]; //오토박싱
        }
        
        @Override
        public Integer set(int i, Integer val) {
            int oldVal = a[i];
            a[i] = val;
            return oldVal;
        }
        
        @Override
        public int size() {
            return a.length;
        }
    };
}
```

- **골격 구현 클래스는 추상 클래스처럼 구현을 도와주는 동시에**, 추상 클래스로 타입을 정의할 때 따라오는 심각한 제약에서는 자유롭다.
- 골격 구현을 확장하는 것으로 인터페이스 구현이 거의 끝나지만, 반드시 이렇게 해야하는 것은 아니다.
- 구조상 골격 구현을 확장하지 못한다면 인터페이스를 직접 구현해야 한다. 그래도 여전히 디폴트 메서드의 이점을 누릴 수 있다.
- 골격 구현 클래스를 우회적으로 이용할 수도 있다.
  - 인터페이스를 구현한 클래스에서 해당 골격 구현을 확장한 private 내부 클래스를 정의하고, 각 메서드 호출을 내부 클래스의 인스턴스에 전달하면 된다.
  - 래퍼 클래스와 비슷한 이 방식을 **시뮬레이트한 다중 상속(simulated multiple inheritance)**이라 하며, 다중 상속의 많은 장점을 제공하면서 단점은 피하게 해준다.

<hr>

#### 💎 골격 구현의 작성법

1. **인터페이스를 잘 살펴 다른 메소드들의 구현에 사용되는 기반 메소드들을 선정한다.** 
   이 기반 메소드들은 골격 구현에서는 추상 메소드가 될 것이다.
2.  **기반 메소드들을 사용해 직접 구현할 수 있는 메소드를 모두 디폴트 메소드로 제공한다.**
   <span style="color:red;">단, equals와 hashCode 와 같은 Object의 메소드는 디폴트 메소드로 제공하면 안된다.</span>

<br>

만약 인터페이스의 메소드 모두가 **기반 메소드와 디폴트 메소드**가 된다면 골격 구현 클래스를 별도로 만들 이유는 없다.

기반 메소드나 디폴트 메소드로 만들지 못한 메소드가 남아 있다면, 
이 인터페이스를 구현하는 골격 구현 클래스를 하나 만들어 남은 메소드들을 작성해 넣는다.

골격 구현 클래스에는 필요하면 public이 아닌 필드와 메소드를 추가해도 된다.



<hr>

예시를 보자.

##### 💎 골격 구현 클래스 - Map.Entry 인터페이스

```java
public abstract class AbstractMapEntry<K, V> implements Map.Entry<K, V> {

    // 변경 가능한 엔트리는 이 메서드를 반드시 재정의해야 한다.
    @Override
    public V setValue(V value) {
        throw new UnsupportedOperationException();
    }

    // Map.Entry.equals의 일반 규약을 구현한다.
    @Override
    public boolean equals(Object obj) {
        if (obj == this) {
            return true;
        }
        if (!(obj instanceof Map.Entry)) {
            return false;
        }
        Map.Entry<?, ?> e = (Map.Entry) obj;
        return Objects.equals(e.getKey(), getKey()) && Objects.equals(e.getValue(), getValue());
    }

    // Map.Entry.hashCode의 일반 규약을 구현한다.
    @Override
    public int hashCode() {
        return Objects.hashCode(getKey()) ^ Objects.hashCode(getValue());
    }

    @Override
    public String toString() {
        return getKey() + "=" + getValue();
    }
}
```

**getKey**, **getValue**는 확실히 기반 메소드이며, 선택적으로 **setValue**도 포함할 수 있다.

이 인터페이스는 **equals**와 **hashCode**의 동작 방식도 정의해놨다.

<span style="color:red;">Object 메소드들은 디폴트 메소드로 제공해서는 안 되므로</span>, 해당 메소드들은 모두 골격 구현 클래스에 구현한다. **toString**도 기반 메소드를 사용해 구현해놨다.

<hr>



> Map.Entry 인터페이스나 그 하위 인터페이스로는 이 골격 구현을 제공할 수 없다. 디폴트 메소드는 equals, hashCode, toString 같은 Object 메소드를 재정의 할 수 없기 때문이다.



<hr>



***💎골격 구현은 반드시 그 동작 방식을 잘 정리해 문서로 남겨야한다.***



<hr>



**💎 단순 구현(simple implementation)?**

**단순 구현**은 골격 구현의 작은 변종으로, **AbstractMap.SimpleEntry**가 좋은 예다. **단순 구현도 골격 구현과 같이 상속을 위해 인터페이스를 구현한 것이지만**, 
<span style="color:red;">추상클래스가 아니란 점</span>이 다르다.

쉽게 말해 동작하는 가장 단순한 구현이다. 이러한 단순 구현은 그대로 써도 되고 필요에 맞게 확장해도 된다.

```java
public static class SimpleEntry<K, V> implements Entry<K, V>, java.io.Serializable {
    private static final long serialVersionUID = -8499721149061103585L;

    private final K key;
    private V value;

    /**
     * Creates an entry representing a mapping from the specified
     * key to the specified value.
     *
     * @param key the key represented by this entry
     * @param value the value represented by this entry
     */
    public SimpleEntry(K key, V value) {
        this.key = key;
        this.value = value;
    }

    /**
     * Creates an entry representing the same mapping as the
     * specified entry.
     *
     * @param entry the entry to copy
     */
    public SimpleEntry(Entry<? extends K, ? extends V> entry) {
        this.key = entry.getKey();
        this.value = entry.getValue();
    }

    /**
     * Returns the key corresponding to this entry.
     *
     * @return the key corresponding to this entry
     */
    public K getKey() {
        return key;
    }

    /**
     * Returns the value corresponding to this entry.
     *
     * @return the value corresponding to this entry
     */
    public V getValue() {
        return value;
    }

    /**
     * Replaces the value corresponding to this entry with the specified
     * value.
     *
     * @param value new value to be stored in this entry
     * @return the old value corresponding to the entry
     */
    public V setValue(V value) {
        V oldValue = this.value;
        this.value = value;
        return oldValue;
    }

    /**
     * Compares the specified object with this entry for equality.
     * Returns {@code true} if the given object is also a map entry and
     * the two entries represent the same mapping.  More formally, two
     * entries {@code e1} and {@code e2} represent the same mapping
     * if<pre>
     *   (e1.getKey()==null ?
     *    e2.getKey()==null :
     *    e1.getKey().equals(e2.getKey()))
     *   &amp;&amp;
     *   (e1.getValue()==null ?
     *    e2.getValue()==null :
     *    e1.getValue().equals(e2.getValue()))</pre>
     * This ensures that the {@code equals} method works properly across
     * different implementations of the {@code Map.Entry} interface.
     *
     * @param o object to be compared for equality with this map entry
     * @return {@code true} if the specified object is equal to this map
     *         entry
     * @see    #hashCode
     */
    public boolean equals(Object o) {
        if (!(o instanceof Map.Entry))
            return false;
        Map.Entry<?, ?> e = (Map.Entry<?, ?>) o;
        return eq(key, e.getKey()) && eq(value, e.getValue());
    }

    /**
     * Returns the hash code value for this map entry.  The hash code
     * of a map entry {@code e} is defined to be: <pre>
     *   (e.getKey()==null   ? 0 : e.getKey().hashCode()) ^
     *   (e.getValue()==null ? 0 : e.getValue().hashCode())</pre>
     * This ensures that {@code e1.equals(e2)} implies that
     * {@code e1.hashCode()==e2.hashCode()} for any two Entries
     * {@code e1} and {@code e2}, as required by the general
     * contract of {@link Object#hashCode}.
     *
     * @return the hash code value for this map entry
     * @see    #equals
     */
    public int hashCode() {
        return (key == null ? 0 : key.hashCode()) ^
                (value == null ? 0 : value.hashCode());
    }

    /**
     * Returns a String representation of this map entry.  This
     * implementation returns the string representation of this
     * entry's key followed by the equals character ("{@code =}")
     * followed by the string representation of this entry's value.
     *
     * @return a String representation of this map entry
     */
    public String toString() {
        return key + "=" + value;
    }

}
```



<hr>





> 일반적으로 다중 구현용 타입으로는 인터페이스가 가장 적합하다.
> 복잡한 인터페이스라면 구현하는 수고를 덜어주는 골격 구현을 함께 제공하는 방법을 꼭 고려해보자.
>
> 골격 구현은 '가능한 한' 인터페이스의 디폴트 메소드로 제공하여 그 인터페이스를 구현한 곳에서 활용하도록 하는것이 좋다. 
>
> '가능한 한'이라고 한 이유는 인터페이스에 걸려 있는 구현상의 제약 때문에 골격 구현을 추상 클래스로 제공하는 경우가 더 흔하기 때문이다.



```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

