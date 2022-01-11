---
title: 타입 안전 이종 컨테이너를 고려하라 - Effective Java[33]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 타입 안전 이종 컨테이너 패턴이란?

* 제네릭은 `Set<E>`, `Map<K,V>` 등의 **컬렉션과** `ThreadLocal<T>`, `AtomicReference<T>` 등의 **단일원소 컨테이너에도** 흔히 쓰인다.



* 이런 모든 쓰임에서 **매개변수화 대는 대상은** (원소가 아닌) **컨테이너 자신**이다.



* 따라서 하나의 컨테이너에서 매개변수화할 수 있는 **타입의 수가 제한된다.**

  * 컨테이너의 일반적인 용도에 맞게 설계된 것이니 문제 될 건 없다.

  

  * ex) **Set**에는 원소의 타입을 뜻하는 단 하나의 타입 매개변수만 있으면 되며, **Map**에는 키와 값의 타입을 뜻하는 2개만 필요한 식이다.



* <span style="color:red;">하지만</span> **더 유연한 수단**이 필요할 때도 종종 있다.

  * ex) 데이터베이스의 행(row)는 임의 개수의 열(column)을 가질 수 있는데, 모두 열을 타입 안전하게 이용할 수 있다면 멋질 것이다.

  

  * <span style="color:red;">해법으로는</span> **컨테이너 대신 키를 매개변수화한 다음, 컨테이너에 값을 넣거나 뺄 때 매개변수화한 키를 함께 제공하면 된다.** 

  

  * 이렇게 하면 **제네릭 타입 시스템이 값의 타입이 키와 같음을 보장**해 줄 것이다.

  

  * **이러한 설계 방식을 <span style="color:red;">타입 안전 이종 컨테이너 패턴</span>이라고 한다.**

    

<hr>



**💎 타입 안전 이종 컨테이너 패턴 **

* 타입별로 즐겨 찾는 인스턴스를 저장하고 검색할 수 있는 **Favorites** 클래스



* 키가 매개변수화 되어있음

```java
public class Favorites {
    public <T> void putFavorite(Class<T> type, T instance);
    public <T> T getFavorite(Class<T> type);
}

public static void main(String[] args) {
    Favorites f = new Favorites();
    
    f.putFavorite(String.class, "Java");
    f.putFavorite(Integer.class, 0xcafebabe);
    f.putFavorite(Class.class, Favorites.class);
    
    String favoriteString = f.getFavorite(String.class);
    int favoriteInteger	= f.getFavorite(Integer.class);
    Class<?> favoriteClass = f.getFavorite(Class.class);
    
    System.out.printf("%s %x %s%n", favoriteString, favoriteInteger, 				favoriteClass.getName());
}
```

* 각 타입의 **Class 객체를 매개변수화 한 키 역할로 사용**하면 되는데, 이 방식이 동작하는 이유는 class의 **클래스가 제네릭이기 때문이다.**

  * **class** 리터럴의 타입은 **Class**가 아닌 `Class<T>`다. 

  

  * ex) **String.class**의 타입은 Class`<String>`이고 **Integer.class**의 타입은 `Class<Integer>` 인 식이다.



* 컴파일타임 타입 정보와 런타임 타입 정보를 알아내기 위해 **메소드들이 주고받는 class 리터럴**을 **<span style="color:red;">타입 토큰(type token)</span>**이라 한다.



* **Favorites** 인스턴스는 타입 안전하다.

  * **String**을 요청했는데 **Integer**를 반환하는 일은 절대 없다.

  

  * 모든 키의 타입이 제각각이라, 일반적인 맵과 달리 여러가지 타입의 원소를 담을 수 있다.

  

  * <span style="color:red;">따라서</span> **Favorites**는 **타입 안전 이종 컨테이너**라 할 만 하다.



<hr>



**💎 타입 안전 이종 컨테이너 패턴 - 구현**

```java
public class Favorites {
    private Map<Class<?>, Object> favorites = new HashMap<>();
    
    public <T> void putFavorites(Class<T> type, T instance) {
        favorites.put(Objects.requireNonNull(type), instance);
    }
    
    public <T> T getFavorite(Class<T> type) {
        return type.cast(favorites.get(type));
    }
}
```

* **Facvorties**가 사용하는 **private** 맵 변수인 **favorites**의 타입은 `Map<Class<?>, Object>` 이다.



* **비한정적 와일드카드 타입**이라 이 맵 안에 아무것도 넣을 수 없다고 생각할 수 있지만, <span style="color:red;">사실은 그 반대다.</span>

  * **와일드카드 타입이 중첩(nested)**되었다는 점을 깨달아야 한다.

  

  * **이는 모든 키가 서로 다른 매개변수화 타입일 수 있다는 뜻이다.** 

    * ex) `Class<String>`, `Class<Integer>`

    

  * **다양한 타입을 지원하는 힘이 여기서 나온다.**

    

* **favorites** 맵의 값 타입은 단순히 **Object**이다.

  * **모든 값이 키로 명시한 타입임을 보증하지 않는다.**

  

  * 사실 자바의 타입 시스템에서는 이 관계를 명시할 방법이 없다.
    * <span style="color:red;">하지만</span>, 우리는 이 관계가 성립함을 알고 있고, 즐겨찾기를 검색할 때 그 이점을 누리게 된다.



* **putFavorite** 구현은 아주 쉽다.

  * 주어진 **Class** 객체와 즐겨찾기 인스턴스를 **favorites**에 추가해 관계를 지으면 끝이다.

  

  * 키와 값 사이의 **'타입 링크(type linkage)' 정보는 버려진다.**

  

  * <span style="color:red;">즉</span>, **그 값이 그 키 타입의 인스턴스라는 정보가 사라진다.**

  

  * <span style="color:red;">하지만</span>, **getFavorite** 메소드에서 이 관계를 되살릴 수 있으니 상관없다.



* **getFavorite** 코드는 **putFavorite** 보다 중요하다.

  * 먼저 주어진 **Class** 객체에 해당하는 값을 **favorites** 맵에서 꺼낸다.

  

  * 이 객체가 바로 반환해야 할 객체가 맞지만, <span style="color:red;">잘못된 컴파일타임 타입</span>을 가지고 있다.

  

  * 이 객체의 **타입은** **(favorites 맵의 값 타입인) Object**이나, 이를 **T**로 바꿔 **반환**해야 한다.

  

  * <span style="color:red;">따라서</span> **getFavorite** 구현은 **Class**의 **cast** 메소드를 사용해 이 객체 참조를 **Class** 객체가 가리키는 타입으로 <span style="color:red;">동적 형변환</span>한다.



* cast 메소드는 단지 인수를 그대로 반환한다. **그런데 왜 굳이 사용하는 것일까?**
  * 그 이유는 **cast 메소드의 시그니처가 Class 클래스가 제네릭이라는 이점을 완벽히 활용**하기 때문이다.
  * 다음 코드에서 보든 **cast의 반환 타입**은 **Class 객체의 타입 매개변수와 <span style="color:red;">같다.</span>**

```java
public class Class<T> {
	T cast(Object obj);
}
```

* 이것이 정확히 getFavorite 메소드에 필요한 기능으로, **T로 비검사 형변환하는 손실 없이도 Favorites를 <span style="color:red;">타입 안전하게 만드는 비결</span>이다.**



<hr>



**🔗 Favorites 클래스에서 알아두어야 할 제약 첫 번째@@**

* 악의적인 클라이언트가 **Class 객체를 <span style="color:red;">(제네릭이 아닌) 로 타입으로 넘기면</span>** **Favorites** 인스턴스의 **안정성이 쉽게 깨진다**.

  * 하지만 이렇게 짜여진 클라이언트 코드에서는 **컴파일할 때 비검사 경고가 뜰 것이다.**

  * **HashSet**과 **HashMap** 등의 일반 컬렉션 구현체에도 **똑같은 문제가 있다.**

    * ex) **HashSet**의 로 타입을 사용하면 `HashSet<Integer>`에 **String**을 넣는 건 아주 쉬운 일이다.

    

  * 그렇기는 하지만, 이 정도의 문제를 감수하겠다면 런타임 타입 안정성을 얻을 수  있다.

  

  * **Favorites**가 타입 불변식을 어기는 일이 없도록 보장하려면 **putFavorite 메소드에서 인수로 주어진 instance의 타입이 type으로 명시한 타입과 <span style="color:red;">같은지 확인</span>**하면 된다.
    * 아래와 같이 **동적 형변환**을 쓰면 된다.

<br>

**💎 동적 형변환으로 런타임 안정성 확보**

```java
public <T> void putFavorite(Class<T> type, T instance) {
    favorites.put(Objects.requireNonNUll(type), type.cast(instance));
}
```

* **java.util.Collections**에는 **checkedSet**, **checkedList**, **checkedMap** 같은 메소드가 있는데, 바로 이 방식을 적용한 컬렉션 래퍼들이다.

  * 이 정적 팩토리 메소드들은 컬렉션(혹은 맵) 과 함께 1개(혹은 2개)의 Class 객체를 받는다.

  

  * 이 메소드들은 모두 제네릭이라 Class 객체와 컬렉션의 컴파일타임 타입이 같음을 보장한다.

  

  * 이 래퍼들은 내부 컬렉션들을 실체화한다.

    * ex) 런타임에 **Coin**을 `Collection<Stamp>`에 넣으려 하면 **ClassCastException**을 던진다.

    

    * 이 래퍼들은 제네릭과 로 타입을 섞어 사용하는 애플리케이션에서 클라이언트 코드가 컬렉션에 잘못된 타입의 원소를 넣지 못하게 추적하는 데 도움을 준다.



<hr>



**🔗 Favorites 클래스에서 알아두어야 할 제약 두 번째@@**

* **실체화 불가 타입에는 사용할 수 없다는 것이다.**

  * <span style="color:red;">즉</span>, 즐겨 찾는 **String**이나 **String[]**은 저장할 수 있어도 즐겨 찾는 `List<String>`은 저장할 수 없다는 말이다.

    * `List<String>`을 저장하려는 코드는 컴파일되지 않을 것이다.

    

    * `List<String>`용 **Class** 객체를 얻을 수 없기 때문이다.

      

    * `List<String>.class`라고 쓰면 <span style="color:red;">문법 오류</span>가 난다.

    

    * `List<String>`과 `List<Integer>`는 **List.class**라는 **같은 Class를 공유**하므로, 만약 둘 다 똑같은 객체 참조를 반환한다면 아수라장이 된다.

    

    * 두 번째 제약에 대한 완벽히 만족스러운 우회로는 없다.

<br>



> 이 두번째 제약을 슈퍼 타입 토큰(super type token)으로 해결하려는 시도도 있다.
>
> 
>
> 슈퍼 타입 토큰은 자바 업계의 거장인 닐 개프터가 고안한 방식으로,
>
> 실제로 아주 유용하여 스프링 프레임워크에서는 아예 **ParameterizedTypeReference**라는 클래스로 미리 구현해놓았다.
>
> 
>
> 위 Favorites에 슈퍼 타입 토큰을 적용하면 다음 코드처럼 제네릭 타입도 문제없이 저장할 수 있다.
>
> Favorites f = new Favorites();
>
> `List<String>` pets = Arrays.asList("개", "고양이", "앵무");
>
> f.putFavorite(**new TypeRef<`List<String>`>(){},** pets);
>
> `List<String>` listofStrings = f.getFavorite(**new TypeRef<`List<String>`>(){}**);
>
> 
>
> **하지만 이 방식도 완벽하진 않으니 주의해서 사용해야 한다.**



<hr>



##### 💎 한정적 타입토큰이란?

* Favorites가 사용하는 타입 토큰은 비한정적이다.
  * 즉, getFavorite과 putFavorite은 어떤 Class 객체든 받아들인다.
  * 때로는 이 메소드들이 **허용하는 타입을 제한**하고 싶을 수 있는데, **한정적 토큰을 활용하면 가능하다.**



* **한정적 타입 토큰이란** 단순히 한정적 타입 매개변수나 한정적 와일드카드를 사용하여 **표현가능한 타입을 제한하는 타입 토큰**이다.



* **애노테이션 API는 한정적 타입 토큰을 적극적으로 사용한다.**

  * ex) 다음은 **AnnotatedElement** 인터페이스에 선언된 메소드로, **대상 요소에 달려 있는 애노테이션을 런타임에 읽어 오는 기능을 한다.**

  

  * 이 메소드는 리플렉션의 대상이 되는 타입들, 즉 클래스 (`java.lang.Class<T>`), 메소드(`java.lang.reflect.Method`), 필드(`java.lang.reflect.Field`) 같이 프로그램 요소를 표현하는 타입들에서 구현한다.

<br>

```java
public <T extends Annotation>
	T getAnnotation(Class<T> annotationType);
```

* 여기서 **annotationType 인수는** 애노테이션 타입을 뜻하는 **한정적 타입 토큰이다.**

  * 이 메소드는 토큰으로 명시한 타입의 애노테이션이 대상 요소에 달려 있다면 그 애노테이션을 반환하고, 없다면 null을 반환한다.

  

  * <span style="color:red;">즉</span>, **애노테이션된 요소는** 그 키가 애노테이션 타입인, **타입 안전 이종 컨테이너인 것이다.**



<hr>



**💎 Class<?> 타입의 객체가 있고, 이를 (getAnnotation처럼) 한정적 타입 토큰을 받는 메소드에 넘기려면 어떻게 해야 할까**

* 객체를 `Class<? extends Annotation>`으로 형변환할 수도 있지만, **이 형변환은 비검사이므로 컴파일하면 경고가 뜰 것이다.**



* **Class 클래스가** 이런 형변환을 안전하게 (그리고 동적으로) 수행해주는 **인스턴스 메소드를 제공한다.**

  * ex) **asSubclass** 메소드로 ,  호출된 인스턴스 자신의 **Class** 객체를 **인수로 명시한 클래스로 형변환**한다
    (형변환된다는 것은 이 클래스가 인수로 명시한 클래스의 하위 클래스라는 뜻이다).

  

  * 형변환에 성공하면 인수로 받은 클래스 객체를 반환하고, 실패하면 ClassCastException을 던진다.



<hr>



**💎 asSubclass를 사용해 한정적 타입 토큰을 안전하게 형변환한다.**

```java
static Annotation getAnnotation(AnnotatedElement element, String annotationTypeName) {
    Class<?> annotationType = null; //비한정적 타입 토큰
    try {
        annotationType = Class.forName(annotationTypeName);
    } catch (Exception ex) {
        throw new IllegalArgumentException(ex);
    }
    return element.getAnnotation(annotationType.asSubclass(Annotation.class));
}
```



<hr>



> 컬렉션 API로 대표되는 일반적인 형태에서는 한 컨테이너가 다룰 수 있는 타입 매개변수의 수가 고정되어 있다.
>
> <span style="color:red;">하지만</span> 컨테이너 자체가 아닌 **<span style="color:red;">키를 타입 매개변수</span>로 바꾸면 이런 제약이 없는 타입 안전 이종 컨테이너를 만들 수 있다.**
>
> **타입 안전 이종 컨테이너는 Class를 키로 쓰며, 이런식으로 쓰이는 Class 객체를 타입 토큰이라 한다.**
>
> 
>
> 또한, 직접 구현한 키 타입도 쓸 수 있다. 
>
> 예컨대 데이터베이스의 행(컨테이너)를 표현한 DatabaseRow 타입에는 제네릭 타입인 Column<T>를 키로 사용할 수 있다.





​	



```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

