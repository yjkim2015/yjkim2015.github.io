---
title: 직렬화된 인스턴스 대신 직렬화 프록시 사용을 검토하라 - Effective Java[90]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗 직렬화 프록시 패턴을 이용하면 Serialziable 구현의 위험을 크게 줄여줄 수 있다.

* **Serialziable**을 구현하기로 결정한 순간 언어의 정상 메커니즘인 생성자 이외의 방법으로 인스턴스를 생성할 수 있게 된다.

  * 버그와 보안 문제가 일어날 가능성이 커진다는 뜻이다.

  

* <span style="color:red;">하지만</span> 직렬화 프록시 패턴을 이용하면 이 위험을 크게 줄여 줄 수 있다.



<hr>




##### 💎 직렬화 프록시 패턴

* 직렬화 프록시 패턴은 그리 복잡하지 않다.

  * 먼저, **바깥 클래스의 논리적 상태를 정밀하게 표현하는 중첩 클래스를 설계**해 **private static**으로 선언한다.

  

  * **이 중첩 클래스가 바로 바깥 클래스의 직렬화 프록시다.**

  

  * <span style="color:red;">중첩 클래스의 생성자는 단 하나여야 하며, 바깥 클래스를 매개변수로 받아야 한다.</span>

    * **이 생성자는 단순히 인수로 넘어온 인스턴스의 데이터를 복사한다.**

      

    * **일관성 검사나 방어적 복사도 필요 없다.**

    

    * 설계상, 직렬화 프록시의 기본 직렬화 형태는 바깥 클래스의 직렬화 형태로 쓰기에 이상적이다.

    

    * 그리고 바깥 클래스와 직렬화 프록시 모두 **Serialziable**을 구현한다고 선언해야 한다.

<hr>



💎 **Period 클래스용 직렬화 프록시**

* 다음은 아이템 88에서 직렬화한 **Period** 클래스의 직렬화 프록시이다.
  * **Period**는 아주 간단하여 직렬화 프록시도 바깥 클래스와 완전히 같은 필드로 구성되었다.

```java
private static class SerializationProxy implements Serialziable {
    private final Date start;
    private final Date end;
    
    SerializationProxy(Period p) {
        this.start = p.start;
        this.end = p.end;
    }
    
    private static final long serialVersionUID = 234098243823485285L; //아무 값이나 상관없다.  
}
```

* 다음으로 바깥 클래스에 다음의 writeReplace 메서드를 추가한다.
  * 이 메서드는 범용적이니 직렬화 프록시를 사용하는 모든 클래스에 그대로 복사해 쓰면 된다.

```java
// 직렬화 프록시 패턴용 writeReplace 메서드
private Object writeReplace() {
    return new SerializationProxy(this);
}
```

* 이 메서드는 **자바의 직렬화 시스템이 바깥 클래스의 인스턴스 대신 SerializationProxy의 인스턴스를 반환하게 하는 역할을 한다.**
  * 달리 말해, <span style="color:red;">직렬화가 이루어지기 전에 바깥 클래스의 인스턴스를 직렬화 프록시로 변환해준다.</span>



* **writeReplace** 덕분에 직렬화 시스템은 결코 바깥 클래스의 직렬화된 인스턴스를 생성해낼 수 없다.

  * 하지만 공격자는 불변식을 훼손하고자 이런  시도를 해볼 수 있다.

  

  * 다음의 **readObject** 메서드를 바깥 클래스에 추가하면 이 공격을 가볍게 막아낼 수 있다.

```java
// 직렬화 프록시 패턴용 readObject 메서드
private void readObject(ObjectInputStream stream) throws InvalidObjectException {
    throw new InvalidObjectException("프록시가 필요합니다");
}
```

* 마지막으로 바깥 클래스와 논리적으로 동일한 인스턴스를 반환하는 **readResolve** 메서드를 **SerializationProxy** 클래스에 추가한다.
  * **이 메서드는 역직렬화 시에 직렬화 시스템이 직렬화 프록시를 다시 바깥 클래스의 인스턴스로 변환하게 해준다**.



<hr>



💎 **직렬화 프록시 패턴과 readResolve 메소드 사용이 아름다운 이유**

* **readResolve** 메서드는 공개된 API만을 사용해 바깥 크래스의 인스턴스를 생성한다.



* **직렬화는 생성자를 이용하지 않고도 인스턴스를 생성하는 기능을 제공하는데**, <span style="color:red;">이 패턴은 직렬화의 이런 언어도단적 특성을 상당 부분 제거한다.</span>

  * 즉, 일반 인스턴스를 만들 때와 똑같은 생성자, 정적 팩터리, 혹은 다른 메서드를 사용해 역직렬화된 인스턴스를 생성하는 것이다.

  

  * **따라서 역직렬화된 인스턴스가 해당 클래스의 불변식을 만족하는지 검사할 또 다른 수단을 강고하지 않아도 된다.**

  

  * 그 클래스의 정적 팩터리나 생성자가 불변식을 확인해주고 인스턴스 메서드들이 불변식을 잘 지켜준다면, 따로 더 해줘야 할 일이 없는 것이다.



* 앞서의 **Period.SerializationProxy**용 **readResolve** 메서드는 아래와 같이 생겼다.

```java
// Period.SerializationProxy용 readResolve 메서드
private Object readResolve() {
    return new Period(start, end); //public 생성자를 사용한다.
}
```



<hr>



💎 **방어적 복사처럼, 직렬화 프록시 패턴은 가짜 바이트 스트림 공격과 내부 필드 탈취 공격을 프록시 수준에서 차단해준다.**

* 직렬화 프록시는 Period의 필드를 final로 선언해도 되므로 Period 클래스를 진정한 불변으로 만들 수 도 있다.



* 어떤 필드가 기만적인 직렬화 공격의 목표가 될지 고민하지 않아도 되며, 역직렬화 때 유효성 검사를 수행하지 않아도 된다.



<hr>



💎  **직렬화 프록시 패턴이 readObject에서의 방어적 복사보다 강력한 경우가 하나 더 있다.**

* 직렬화 프록시 패턴은 역직렬화한 인스턴스와 원래의 직렬화된 인스턴스의 클래스가 **달라도 정상 작동한다.**



* **EnumSet**의 사례를 보자.

  * 이 클래스는 **public** 생성자 없이 정적 팩토리들만 제공한다.

  

  * 클라이언트 입장에서는 이 팩터리들이 **EnumSet** 인스턴스를 반환하는 걸로 보이지만, 현재의 **OpenJDK**를 보면 열거 타입의 크기에 따라 두 하위 클래스 중 하나의 인스턴스를 반환한다.

    * 열거 타입의 원소가 64개 이하면 **RegularEnumSet**

    

    * 그보다 크면 **JumboEnumSet**

    

  * 원소 64개짜리 열거 타입을 가진 **EnumSet**을 직렬화한 다음 원소 5개를 추가하고 역직렬화하면 어떤 일이 벌어질지 알아보자.

    * 처음 직렬화 된것은 **RegularEnumSet** 인스턴스다.

    

    * 하지만 역직렬화는 **JumboEnumSet** 인스턴스로 하면 좋을 것이다.

    

    * 그리고 **EnumSet**은 직렬화 프록시 패턴을 사용해서 실제로도 이렇게 동작한다.



<hr>



💎 **실제 EnumSet의 직렬화 프록시**

```java
private static class SerializationProxy <E extends Enum<E>> implements Serializable {
    // 이 EnumSet의 원소 타입
    private final Class<E> elementType;
    
    // 이 EnumSet 안의 원소들
    private final Enum<?>[] elements;
    
    SerializationProxy(EnumSet<E> set) {
        EnumSet<E> result = EnumSet.noneOf(elementType);
        for (Enum<?> e : elements) {
            result.add((E)e);
        }
        return result;
    }
    
    private static final long serialVersionUID = 362491234563181265L;
}
```



<hr>



##### 💎 직렬화 프록시 패턴의 한계 

* **첫 번째**, 클라이언트가 멋대로 확장할 수 있는 클래스에는 적용할 수 없다.



* **두 번째**, 객체 그래프에 순환이 있는 클래스에도 적용할 수 없다.

  * 이런 객체의 메서드를 직렬화 프록시의 **readResolve** 안에서 호출하려 하면 **ClassCastException**이 발생할 것이다.

  

  * 직렬화 프록시만 가졌을 뿐 실제 객체는 아직 만들어진 것이 아니기 때문이다.



* **세 번째**, 직렬화 프록시 패턴이 주는 강력함과 안전성에도 대가는 따른다.
  * **Period** 예를 실행해보니 방어적 복사 때보다 14%가 느렸다.



<hr>



> 제3자가 확장할 수 없는 클래스라면 가능한 한 직렬화 프록시 패턴을 사용하자.
>
> 
>
> 이 패턴이 아마도 중요한 불변식을 안정적으로 직렬화해주는 가장 쉬운 방법일 것이다.






```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

