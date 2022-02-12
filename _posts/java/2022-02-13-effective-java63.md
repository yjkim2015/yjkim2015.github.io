---
title: 문자열 연결은 느리니 주의하라 - Effective Java[63]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗  문자열 연결 연산자로 문자열 n개를 잇는 시간은 n^2에 비례한다.

* 문자열 연결 **연산자(+)**는 여러 문자열을 하나로 합쳐주는 편리한 수단이다.

  * <span style="color:red;">그런데</span> 한 줄짜리 출력값 혹은 작고 크기가 고정된 객체의 문자열 표현을 만들때라면 괜찮지만, **본격적으로 사용하기 시작하면 성능 저하를 감내하기 어렵다.**

  

  * <span style="color:red;">문자열은 불변</span>이라서 **두 문자열을 연결할 경우 양쪽의 내용을 모두 복사해야 하므로 성능 저하는 피할 수 없는 결과다.**
    * ex) 다음의 메서드는 청구서의 품목(item)을 전부 하나의 문자열로 연결해준다.

<br>

💎 **문자열 연결을 잘못 사용한 예 - 느리다!**

```java
public String statement() {
    String result = "";
    for (int i = 0; i < numItems(); i++) {
        result += lineForItem(i); // 문자열 연결
    }
    return result;
}
```

* 품목이 많을 경우 메서드는 심각하게 느려질 수 있다.



<hr>



##### 💎 성능을 포기하고 싶지 않다면 String 대신 StringBuilder를 사용하자.

* **StringBuilder**를 사용하면 문자열 연결 성능이 크게 개선된다.

```java
public String statement2() {
    StringBuilder b = new StringBuilder(numItems() * LINE_WIDTH);
    for (int i = 0; i < numItems(); i++) {
        b.append(lineForItem(i));
    }
    return b.toString();
}
```

* **StringBuilder**를 전체 결과를 담기에 충분한 크기로 초기화 한점을 기억하라.



<hr>



>원칙은 간단하다. 
>
>**성능에 신경 써야 한다면 많은 문자열을 연결할 때는 문자열 연결 연산자(+)를 피하자.**
>
>대신 StringBuilder의 append 메서드를 사용하라.
>
>문자 배열을 사용하거나, 문자열을 (연결하지 않고) 하나씩 처리하는 방법도 있다.






```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

