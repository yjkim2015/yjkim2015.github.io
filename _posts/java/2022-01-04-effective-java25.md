---
title: 톱 레벨 클래스는 한 파일에 하나만 담으라 - Effective Java[25]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 소스 파일 하나에 톱 레벨 클래스 여러 개 두기

**톱 레벨 클래스란** 중첩 클래스가 아닌 클래스이다.

소스 파일 하나에 톱 레벨 클래스를 여러 개 선언하더라도 자바 컴파일러는 불평하지 않는다.

<span style="color:red;">하지만</span> 아무런 득이 없을 뿐더러 **심각한 위험을 감수해야 하는 행위다**.

**그 중 어느 것을 사용할지는 <span style="color:red;">어느 소스 파일을 먼저 컴파일 하느냐에 따라 달라지기 때문이다.</span>**



<br>


##### 💎 두 클래스가 한 파일(Utensil.java)에 정의 됨 

```java
public class Main {
    public static void main(String[] args) {
        System.out.println(Utensil.NAME + Dessert.NAME);
    }
}

class Utensil {
    static final String NAME = "pan";
}

class Dessert {
    static final String NAME = "cake";
}
```

집기(Utensil)와 디저트(Dessert) 클래스는 Utensil.java라는 한 파일에 정의 되어있다.
Main의 실행 결과 값은 pancake로서 지금까지는 문제가 없다.

<br>

다시 똑같은 두 클래스를 담은 Dessert.java라는 파일을 만들어보자.

##### 💎 두 클래스가 한 파일(Dessert.java)에 정의 됨 

```java
class Utensil {
    static final String NAME = "pan";
}

class Dessert {
    static final String NAME = "cake";
}
```

- 운 좋게 **javac Main.java Dessert.java** 명령으로 컴파일한다면 컴파일 오류가 나고 Utensil과 Dessert 클래스를 중복 정의했다고 알려줄 것이다.
  - **컴파일러는 가장 먼저 Main.java를 컴파일하고, 그 안에서 (Dessert 참조보다 먼저 나오는) Utensil 참조를 만나면 Utensil.java 파일을 살펴 Utensil과 Dessert를 모두 찾아낸다.**
  - 다음으로 컴파일러가 두 번째 명령줄 인수로 넘어온 **Dessert.java**를 처리하려 할 때 같은 클래스의 정의가 이미 있음을 알게 된다.
- <span style="color:red;">한편</span>, **javac Main.java나 javac Main.java Utensil.java 명령으로 컴파일하면 Dessert.java 파일을 작성하기 전처럼 pancake를 출력한다.**
- <span style="color:red;">그러나</span>, javac Dessert.java Main.java 명령으로 컴파일하면 potpie를 출력한다.
- **즉, 컴파일러에 어느 소스 파일을 먼저 건네느냐에 따라 동작이 달라지는 문제가 발생한다.**



<hr>



#### 🔗 해결책 : 톱 레벨 클래스들을 서로 다른 소스 파일로 분리

**해결책으로는 톱레벨 클래스들(Utensil과 Dessert)을 서로 다른 소스 파일로 분리하면 된다.**

- 굳이 여러 톱레벨 클래스를 한 파일에 담고 싶다면 **정적 멤버 클래스**를 사용하는 방법을 고려해볼 수 있다.
  - 다른 클래스에 딸린 부차적인 클래스라면 정적 멤버 클래스로 만드는 쪽이 일반적으로 더 나을 것이다.
  - 읽기 좋고, private로 선언하면 접근 범위도 최소로 관리할 수 있기 때문이다.

<br>



**💎 톱 레벨 클래스들을 정적 멤버 클래스로 바꿔본 모습**

```java
public class Test {
    public static void main(String[] args) {
        System.out.println(Utensil.NAME + Dessert.NAME);
    }

    private static class Utensil {
        static final String NAME = "pan";
    }

    private static class Dessert {
        static final String NAME = "cake";
    }
}
```

<br>



> 교훈은 명확하다. 
>
> **소스 파일 하나에는 반드시 톱레벨 클래스(혹은 톱레벨 인터페이스)를 하나만 담자.**
>
> 이 규칙만 따른다면 컴파일러가 한 클래스에 대한 정의를 여러 개 만들어 내는 일은 사라진다. 
>
> 소스 파일을 어떤 순서로 컴파일하든 바이너리 파일이나 프로그램의 동작이 달라지는 일은 결코 일어나지 않을 것이다.



```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

