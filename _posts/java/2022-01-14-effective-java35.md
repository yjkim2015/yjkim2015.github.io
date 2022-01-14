---
title: ordinal 메소드 대신 인스턴스 필드를 사용하라 - Effective Java[35]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 ordinal 메소드의 유혹

* 대부분의 열거 타입 상수는 자연스럽게 하나의 정숫값에 대응된다.

  * **모든 열거 타입은** 해당 상수가 그 열거 타입에서 **몇 번째 위치인지를 반환**하는 **ordinal이라는 메소드를 제공**한다.

  

  * 이런 이유로 **열거 타입 상수와 연결된 정숫값이 필요하면** 다음과 같이 **ordinal 메소드를 이용하고 싶은 <span style="color:red;">유혹</span>에 빠진다.**

  

<hr>



💎 **ordinal을 잘못 사용한 예 - 따라 하지 말 것!**

* 합주단의 종류를 연주자가 1명인 솔로(solo)부터 10명인 디텍트(detect)까지 정의한 열거 타입

```java
public enum Ensemble {
    SOLO, DUET, TRIO, QUARTET, QUINTET,
    SEXTET, SEPTET, OCTET, NONET, DECTET;
    
    public int numberOfMusicians() { return ordinal() + 1; }
}
```

* 동작은 하지만 유지보수하기가 끔찍한 코드다.

  * **상수 선언을 바꾸는 순간** numberOfMusicians가 **오동작하며**, 이미 사용 중인 정수와 값이 같은 상수는 추가할 방법이 없다.
  * ex) 8중주(octet) 상수가 이미 있으니 똑같이 8명이 연주하는 복4중주(double quartet)는 추가할 수 없다.

  

* 값을 중간에 비워둘 수도 없다.

  * ex) 12명이 연주하는 3중 4중주 (triple quartet)를 추가한다고 해보자.

  

  * 그러려면 중간에 11명짜리 상수도 채워야 하는데, 11명으로 구성된 연주를 일컫는 이름이 없다..

    * 11그래서 3중 4중주를 추가하려면 쓰이지 않는 더미(dummy) 상수를 같이 추가해야만 한다.

    

    * 코드가 깔끔하지 못할 뿐 아니라, 쓰이지 않는 값이 많아질수록 실용성이 떨어진다.



<hr>



##### 🔗 해결책은 간단해! 열거 타입 상수에 연결된 값은 ordinal 메소드로 얻지말고, <span style="color:red;">인스턴스 필드에 저장하자.</span>

```java
public enum Ensemble {
    SOLO(1), DUET(2), TRIO(3), QUARTET(4), QUINTET(5),
    SEXTET(6), SEPTET(7), OCTET(8), DOUBLE_QUARTET(8),
    NONET(9), DECTET(10), TRIPLE_QUARTET(12);
    
    private final int numberOfMusicians;
    
    Ensemble(int size) { 
        this.numberOfMusicians = size; 
    }
    public int numberOfMusicians() {
        return numberOfMusicians;
    }
}
```

* **Enum의 API 문서**를 보면 **ordinal**에 대해 이렇게 쓰여있다.



> 대부분의 프로그래머는 이 메소드를 쓸 일이 없다.
>
> 이 메소드는 EnumSet과 EnumMap 같이 열거 타입 기반의 범용 자료구조에 쓸 몪적으로 설계되었다.
>
> 따라서 이런 용도가 아니라면 ordinal 메소드는 절대 사용하지 말자.





```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

