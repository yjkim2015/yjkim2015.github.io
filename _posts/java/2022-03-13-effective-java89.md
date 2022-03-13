---
title: 인스턴스 수를 통제해야 한다면 readResolve보다는 열거 타입을 사용하라 - Effective Java[89]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗 아이템 3에서 싱글턴 패턴을 설명하며 다음 예를 보여주었다.

* 이 클래스는 바깥에서 생성자를 호출하지 못하게 막는 방식으로 인스턴스가 오직 하나만 만들어짐을 보장했다.

```java
public class Elvis {
    public static final Elvis INSTANCE = new Elvis();
    private Elvis() { ... }
    
    public void leaveTheBuilding() { ... }
}
```

* 위 클래스는 선언에 **implements Serializable**을 추가하는 순간 더 이상 싱글턴이 아니게 된다.

  * 기본 직렬화를 쓰지 않더라도, 그리고 명시적인 **readObject**를 제공하더라도 소용없다.

  

  * 어떤 **readObject**를 사용하든 이 클래스가 초기화될 때 만들어진 인스턴스와는 별개인 인스턴스를 반환하게 된다.



<hr>



##### 💎 readResolve 기능을 이용하면 readObject가 만들어낸 인스턴스를 다른 것으로 대체할 수 있다.

* 역직렬화 후 새로 생성된 객체를 인수로 이 메서드가 호출되고, 이 메서드가 반환한 객체 참조가 새로 생성된 객체를 대신해 반환한다.
  * **대부분의 경우 이때 새로 생성된 객체의 참조는 유지하지 않으므로 바로 가비지 컬렉션 대상이 된다.**



* 위의 **Elvis** 클래스가 **Serializable**을 구현한다면 다음의 **readResolve** 메서드를 추가해 **싱글턴이라는 속성을 유지할 수 있다.**

<br>

```java
// 인스턴스 통제를 위한 readResolve - 개선의 여지가 있다!
private Object readReolve() {
    // 진짜 Elvis를 반환하고, 가짜 Elvis는 가비지 컬렉터에 맡긴다.
    return INSTANCE;
}
```

* 위 메서드는 **역직렬화한 객체는 무시하고 클래스 초기화 때 만들어진 Elvis 인스턴스를 반환한다.**

  * 따라서 **Elvis** 인스턴스의 직렬화 형태는 아무런 실 데이터를 가질 이유가 없으니 모든 인스턴스 필드를 **transient**로 선언해야 한다.

  

  * 사실, **readResolve를 인스턴스 통제 목적으로 사용한다면** <span style="color:red;">객체 참조 타입 인스턴스 필드는 모두 transient로 선언해야 한다.</span>
    * 그렇지 않으면 이전 챕터에서 본 MutablePeriod 공격과 비슷한 방식으로 readResolve 메서드가 수행되기 전에 역직렬화된 객체의 참조를 공격할 여지가 남는다.



<hr>



##### 💎 싱글턴이 transient가 아닌 참조 필드를 가지고 있다면 그 필드의 내용은 readResolve 메서드가 실행되기 전에 역직렬화 된다.

* 그렇다면 잘 조작된 스트림을 써서 해당 참조 필드의 내용이 역직렬화되는 시점에 그 역직렬화된 인스턴스의 참조를 훔쳐올 수 있다.



* 더 자세히 알아보자.

  * 먼저, **readResolve 메서드와 인스턴스 필드 하나를 포함한 '도둑(stealer)' 클래스를 작성한다.**

  

  * 이 인스턴스 필드는 **도둑이 '숨길' 직렬화된 싱글턴을 참조하는 역할을 한다.**

  

  * 직렬화된 스트림에서 싱글턴의 비휘발성 필드를 이 도둑의 인스턴스로 교체한다.

  

  * 이제 싱글턴은 도둑을 참조하고 도둑은 싱글턴을 참조하는 순환고리가 만들어졌다.



* 싱글턴이 도둑을 포함하므로 싱글턴이 역직렬화될 때 도둑의 **readResolve** 메서드가 먼저 호출된다.
  * 그 결과, 도둑의 **readResolve** 메서드가 수행될  때 도둑의 인스턴스 필드에는 역직렬화 도중인 (그리고 **readResolve**가 수행되기 전인) 싱글턴의 참조가 담겨 있게 된다.



* 도둑의 **readResolve** 메서드는 이 인스턴스 필드가 참조한 값을 정적 필드로 복사하여 **readResolve**가 끝난 후에도 참조할 수 있도록 한다.

  * 그런 다음 이 메서드는 도둑이 숨긴 **transient**가 아닌 필드의 원래 타입에 맞는 값을 반환한다.

  

  * 이 과정을 생략하면 직렬화 시스템이 도둑의 참조를 이 필드에 저장하려 할 때 **VM**이 **ClassCastException**을 던진다.

<br>



💎 **잘못된 싱글턴 - transient가 아닌 참조 필드를 가지고 있다!**

```java
public class Elvis implements Serializable {
    public static final Elvis INSTANCE = new Elvis();
    private Elvis() { }
    
    private String[] favoriteSongs = {
        "Hound Dog", "Heartbreak Hotel"
    };
    
    private Object readResolve() {
        return INSTANCE;
    }
}
```

<br>

💎 **도둑 클래스**

```java
public class ElvisStealer implements Serializable {
    static Elvis impersonator;
    private Elvis payload;
    
    private Object readResolve() {
        // resolve되기 전의 Elvis 인스턴스의 참조를 저장한다.
        impersonator = payload;
        
        //facvoriteSongs 필드에 맞는 타입의 객체를 반환한다.
        return new String[] { "A Fool Such as  I"};
    }
   	private static final long serialVersionUID = 0;
}
```

* 마지막으로 다음의 괴이한 프로그램은 수작업으로 만든 스트림을 이용해 2개의 싱글턴 인스턴스를 만들어낸다.
  * deserialize 메서드는 생략했다.

<br>

💎 **직렬화의 허점을 이용해 싱글턴 객체를 2개 생성한다.**

```java
public class ElvisImpersonator {
    //진짜 Elvis 인스턴스로는 만들어질 수 없는 바이트 스트림!
    private static final byte[] serializedForm = {
        (byte)0xac, (byte)0xed, 0x00, 0x05, 0x73, 0x72, 0x00, 0x05,
        0x45, 0x6c, 0x76, 0x69, 0x73, (byte)0x84, (byte)0xe6,
        (byte)0x93, 0x33, (byte)0xc3, (byte)0xf4, (byte)0x8b,
        0x32, 0x02, 0x00, 0x01, 0x4c, 0x00, 0x0d, 0x66, 0x61, 0x76,
        0x6f, 0x72, 0x69, 0x74, 0x65, 0x53, 0x6f, 0x6e, 0x67, 0x73,
        0x74, 0x00, 0x12, 0x4c, 0x6a, 0x61, 0x76, 0x61, 0x2f, 0x6c,
        0x61, 0x6e, 0x70, 0x73, 0x72, 0x00, 0x0c, 0x45, 0x6c, 0x76,
        0x69, 0x73, 0x53, 0x74, 0x65, 0x61, 0x6c, 0x65, 0x72, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x01,
        0x4c, 0x00, 0x07, 0x70, 0x61, 0x79, 0x6c, 0x6f, 0x61, 0x64,
        0x74, 0x00, 0x07, 0x4c, 0x45, 0x6c, 0x76, 0x69, 0x73, 0x3b,
        0x78, 0x70, 0x71, 0x00, 0x7e, 0x00, 0x02
    };

	public static void main(String[] args) {
        // ElvisStealer.impersonator를 초기화한 다음,
        // 진짜 Elvis(즉, Elvis.INSTANCE)를 반환한다.
        Elvis elvis = (Elvis) deserialize(serializedForm);
        Elvis impersonator = ElvisStealer.impersonator;
        
        elvis.printFavorites();
        impersonator.printFavorites();
    }
}
```

* 위 프로그램을 실행하면 다음 결과를 출력한다.
  * 이것으로 서로 다른 2개의 Elvis 인스턴스를 생성할 수 있음을 증명했다.

```
[Hound Dog, Heartbreak Hotel]
[A Fool Such as I]
```

* **favoriteSong** 필드를 **transient**로 선언하여 이 문제를 고칠 수 있지만 **Elvis**를 원소 하나짜리 열거 타입으로 바꾸는 편이 더 나은 선택이다.
  * **ElvisStealer** 공격으로 보여줬듯이 **readResolve** 메서드를 사용해 '순간적으로' 만들어진 역직렬화된 인스턴스에 접근하지 못하게 하는 방법은 **깨지기 쉽고 신경을 많이 써야 하는 작업이다.**



<hr>



##### 💎 직렬화 가능한 인스턴스 통제 클래스를 열거 타입을 이용해 구현하면 선언한 상수 외의 다른 객체는 존재하지 않음을 자바가 보장해준다.

* 물론 공격자가 **AccessibleObject.setAccessible** 같은 특권 메서드를 악용한다면 이야기가 달라진다.

  * 임의의 네이티브 코드를 수행할 수 있는 특권을 가로챈 공격자에게는 모든 방어가 무력화된다.

  

  * 다음은 **Elvis** 예를 열거 타입으로 구현한 모습이다.

<br>

💎 **열거 타입 싱글턴 - 전통적인 싱글턴보다 우수하다.**

```java
public enum Elvis {
    INSTNACE;
    private String[] favoriteSong = {
        "Hound Dog", "Heartbreak Hotel"
    };
    
    public void printFavorites() {
        System.out.println(Arrays.toString(favoriteSongs));
    }
}
```

* **인스턴스 통제를 위해 readResolve를 사용하는 방식이 완전히 쓸모없는 것은 아니다.**
  * 직렬화 가능 인스턴스 통제 클래스를 작성해야 하는데, <span style="color:red;">컴파일타임에는 어떤 인스턴스들이 있는지 알 수 없는 상황이라면 열거타입으로 표현하는 것이 불가능하기 때문이다.</span>



<hr>



##### 💎 readResolve 메서드의 접근성은 매우 중요하다.

* **final** 클래스에서라면 **readResolve** 메서드는 **private**이어야 한다.



* **final**이 아닌 클래스에서는 다음의 몇 가지를 주의해서 고려해야 한다.

  * **private**으로 선언하면 하위 클래스에서 사용할 수 없다.

  

  * **package-private**으로 선언하면 같은 패키지에 속한 하위 클래스에서만 사용할 수 있다.

  

  * **protected**나 **public**으로 선언하면 이를 재정의하지 않은 모든 하위 클래스에서 사용할 수 있다.

  

  * **protected**나 **public**이면서 하위 클래스에서 재정의하지 않았다면, 하위 클래스의 인스턴스를 역직렬화하면 상위 클래스의 인스턴스를 생성하여 **ClassCastException**을 일으킬 수 있다.



<hr>



> 불변식을 지키기 위해 인스턴스를 통제해야 한다면 가능한 한 열거 타입을 사용하자.
>
> 
>
> 여의치 않은 상황에서 직렬화와 인스턴스 통제가 모두 필요하다면 readResolve 메서드를 작성해 넣어야 하고, 그 클래스에서 모든 참조 타입 인스턴스 필드를 transient로 선언해야 한다.






```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

