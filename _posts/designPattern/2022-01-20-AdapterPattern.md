---
title: 합성 (Composite) 패턴
categories:
- DesignPattern
toc: true
toc_sticky: true
toc_label: 목차
---

## 🔗 합성 (Composite) 패턴이란?

* **객체들의 관계를 트리 구조로 구성**하여 <span style="color:red;">전체-부분 계층을 표현하는 패턴</span>으로 여러 개의 객체들로 구성된 **복합 객체와 단일 객체**를 클라이언트에서 구별 없이 다루게 한다.



* 즉, <span style="color:red;">전체-부분의 관계</span>를 갖는 **객체들 사이의 관계를 정의**할 때 유용하다.
  * **클라이언트는** <span style="color:red;">전체와 부분을 구분하지 않고</span> **동일한 인터페이스를 사용**할 수 있다.




<hr>


##### 💎 합성 패턴의 구성 요소

* **Base Component**

  * **베이스 컴퍼넌트**는 클라이언트가 <span style="color:red;">composition내의 오브젝트들을 다루기 위해 제공되는 인터페이스를 말한다.</span>

  

  * 베이스 컴포넌트는 **인터페이스 또는 추상 클래스로 정의**되며 모든 오브젝트들에게 <span style="color:red;">공통되는 메서드를 정의</span>해야 한다.

* **Leaf**

  * composition 내 오브젝트들의 행동을 정의한다.

  

  * **구체적인 부분 클래스**로 <span style="color:red">단일 객체</span>**[Base Component]를 구현**한다.

  

  * Leaf는 다른 컴포넌트에 대해 참조를 가지면 안된다.

    

* **Composite**

  * **복합 객체 그룹을 표현**할 클래스로 <span style="color:red;">전체 클래스이다.</span>
    * 역시 **단일 객체[Base Component]를 구현**한다.

  

  * Leaf 객체들로 이루어져 있으며 베이스 컴퍼넌트 내 명령들을 구현한다.



<hr>



💎 **BaseComponent - Leaf와 Composite의 공통되는 메소드들을 정의**



* **Shape.java - 도형을 그리는 draw 메소드 정의**

```java
package StructurePattern.CompositPattern;

/**
 * Base Component - 베이스 컴포넌트는 클라이언트가 composition 내의 오브젝트들을 다루기 위해 제공되는 인터페이스를 말합니다.
 * 베이스 컴포넌트는 인터페이스 또는 추상 클래스로 정의되며 모든 오브젝트들에게 공통되는 메소드를 정의해야 합니다.
 */
public interface Shape {
    public void draw(String fillColor);
}

```



<hr>



💎 **Leaf Objects - Leaf 객체들은 복합체에 포함되는 요소로, Base Component를 구현해야 한다.**



* **Traingle.java**

```java
package StructurePattern.CompositPattern;

/*
Leaf 객체들은 복합체에 포함되는 요소로, Base Component를 구현해야 합니다.
 */
public class Triangle implements Shape {

    @Override
    public void draw(String fillColor) {
        System.out.println("Drawing Triangle with color : " + fillColor);
    }
}
```



* **Circle.java**

```java
package StructurePattern.CompositPattern;

/*
Leaf 객체들은 복합체에 포함되는 요소로, Base Component를 구현해야 합니다.
 */
public class Circle implements Shape {

    @Override
    public void draw(String fillColor) {
        System.out.println("Drawing Circle with color : " + fillColor);
    }
}
```



<hr>



💎 **Composite Objects - Composite 객체는 Leaf 객체를 포함하며, Base Component를 구현**

* **Drawing.java**

```java
package StructurePattern.CompositPattern;

import java.util.ArrayList;
import java.util.List;

/*
Composite 객체는 Leaf 객체들을 포함하고 있으며,
Base Component를 구현할 뿐만 아니라 Leaf 그룹에 대해 add와 remove를 할 수 있는 메소드들을 클라이언트에게 제공합니다.
 */
public class Drawing implements Shape {
    private List<Shape> shapeList = new ArrayList<>();

    @Override
    public void draw(String fillColor) {
        for ( Shape oneShape : shapeList ) {
            oneShape.draw(fillColor);
        }
    }

    public void add(Shape s) {
        shapeList.add(s);
    }

    public void remove(Shape s) {
        shapeList.remove(s);
    }

    public void clear() {
        System.out.println("Clearing all the shapes form drawing");
        this.shapeList.clear();
    }
}
```



<hr>



💎 **Test 코드**

* **TestCompositePattern.java**

```java
package StructurePattern.CompositPattern;

import java.util.ArrayList;
import java.util.List;

/*
구조 패턴이란 작은 클래스들을 상속과 합성을 이용하여 더 큰 클래스를 생성하는 방법을 제공하는 패턴입니다.

이 패턴을 사용하면 서로 독립적으로 개발한 클래스 라이브러리를 마치 하나인 양 사용할 수 있습니다.
또, 여러 인터페이스를 합성(Composite)하여 서로 다른 인터페이스들의 통일된 추상을 제공합니다.

구조 패턴의 중요한 포인트는 인터페이스나 구현을 복합하는 것이 아니라 객체를 합성하는 방법을 제공한다는 것입니다.
이는 컴파일 단계에서가 아닌 런타임 단계에서 복합 방법이나 대상을 변경할 수 있다는 점에서 유연성을 갖습니다.
 */
public class TestCompositePattern {
    public static void main(String[] args) {
        Triangle triangle = new Triangle();
        Triangle triangle1 = new Triangle();
        Circle circle = new Circle();

        Drawing drawing = new Drawing();
        drawing.add(triangle);
        drawing.add(triangle1);
        drawing.add(circle);

        drawing.draw("Red");

        System.out.println("==========================================");
        List<Shape> shapes = new ArrayList<>();
        shapes.add(drawing);
        shapes.add(new Triangle());
        shapes.add(new Circle());

        for (Shape shape : shapes) {
            shape.draw("Green");
        }
    }
}
```

* **drawing - Composite[전체] 객체를 통해 Triangle, Circle 등의 Leaf[부분] 객체들을 그룹으로 묶어서 한번에 동작을 수행할 수 있다.**



* 또한 **drawing 객체 또한** 다른 도형들과 마찬가지로 **Shape 인터페이스를 구현**하고 있기 떄문에 drawing이 **다른 도형들과 함께 취급** 될 수있다.



* <span style="color:red;">즉</span>, 클라이언트 입장에선 <span style="color:red;">전체[Composite]와 부분[Leaf] 의 구별 없이 사용</span>할 수 있다.



💎 **실행 결과**

```java
Drawing Triangle with color : Red
Drawing Triangle with color : Red
Drawing Circle with color : Red
==========================================
Drawing Triangle with color : Green
Drawing Triangle with color : Green
Drawing Circle with color : Green
Drawing Triangle with color : Green
Drawing Circle with color : Green
```

