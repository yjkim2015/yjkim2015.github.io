---
title: 플라이웨이트 (Flyweight) 패턴
categories:
- DesignPattern
toc: true
toc_sticky: true
toc_label: 목차
---

## 🔗 플라이웨이트 (flyweight) 패턴이란?

* **플라이웨이트 패턴은** 어떤 클래스의 **인스턴스 한 개만 가지고 여러 개의 "가상 인스턴스"를 제공하고 싶을 때 사용하는 패턴이다**.

  * <span style="color:red;">즉, 인스턴스를 가능한 대로 공유</span>시켜 쓸데없이 new 연산자를 통한 메모리 낭비를 줄이는 방식이다.

  

  *  **많은 수의 객체를 생성해야 할 때 사용하는 패턴**으로 <span style="color:red;">공유(Sharing)</span>을 통하여 **대량의 객체들을 효과적으로 지원하는 방법**이다



* 주로 **생성 된 객체 수를 줄이고 메모리 사용 공간을 줄이며** <span style="color:red;">성능을 향상시키는 데 사용</span>되며, 이러한 유형의 디자인 패턴은 오브젝트 패턴을 감소시켜 어플리케이션에 필요한 오브젝트 구조를 향상시킨다.



<hr>



##### 💎 플라이웨이트 패턴이 적합한 경우

* 어플리케이션에 의해 생성되는 객체의 수가 많아야 한다.



* 생성된 객체가 오래도록 메모리에 상주하며 사용되는 횟수가 많다.



* **객체의 특성**을 **내적 속성**과 **외적 속성**으로 나눴을 때, **객체의 외적 특성이 클라이언트 프로그램으로부터 정의**되어야 한다.

  

<hr>



##### 💎 내적 속성? 외적 속성?

* 객체의 **내적 속성은 객체를 유니크하게 하는 것**이고, **외적 속성은 클라이언트의 코드로부터 설정**되어 다른 동작을 수행하도록 사용되는 특성이다.



<hr>



💎 **플라이웨이트 패턴 활용 예**

* **자바의 모든 래퍼 클래스의 valueOf 메서드**

  * 그래서 래퍼 클래스를 생성해야 할 때 **new 키워드**를 통해 인스턴스를 매번 생성하기보다는 **valueOf()** 메서드를 통해 생성하는 것이 더 효율적이다.

  

* **Java의 String Pool**

  * 자바에서는 **String Poo**l을 별도로 두어 같은 문자열에 대해 다시 사용될 때에 새로운 메모리를 할당하는 것이 아니라 **String Pool**에 있는지 검사해서 있으면 가져오고 없으면 새로 메모리를 할당하여 **String Pool**에 등록한 후에 사용하고 있다.



<hr>



💎 **Shape.java**

* 도형을 그리는 draw 메소드를 갖고 있는 인터페이스

```java
package StructurePattern.FlyweightPattern;

import java.awt.*;

public interface Shape {
    public void draw(Graphics g, int x, int y, int width, int height, Color color);
}
```



<hr>



💎 **Line.java**

* Shape 인터페이스를 구현하는 선을 그리는 클래스



* 인스턴스화 할 때 시간이 많이 걸린다는 것을 조금 더 과장해서 보여주기 위해 Thread.sleep 코드를 넣었다.

```java
package StructurePattern.FlyweightPattern;

import java.awt.*;

public class Line implements Shape {

    public Line() {
        System.out.println("Creating Line Object");

        try {
            Thread.sleep(2000);
        }catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    @Override
    public void draw(Graphics line, int x1, int y1, int x2, int y2, Color color) {
        line.setColor(color);
        line.drawLine(x1, y1, x2, y2);
    }
}
```



<hr>



💎 **Oval.java**

* Shape 인터페이스를 구현하여 원형을 그리는 클래스



* 인스턴스화 할 때 시간이 많이 걸린다는 것을 조금 더 과장해서 보여주기 위해 Thread.sleep 코드를 넣었다.

```java
package StructurePattern.FlyweightPattern;

import java.awt.*;

public class Oval implements Shape {

    private boolean fill;

    public Oval(boolean f) {
        this.fill = f;
        System.out.println("Creating Oval obejct with fill = " + f);

        try {
            Thread.sleep(2000);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    @Override
    public void draw(Graphics circle, int x, int y, int width, int height, Color color) {
        circle.setColor(color);
        circle.drawOval(x, y, width, height);

        if (fill) {
            circle.fillOval(x, y, width, height);
        }
    }
}
```





<hr>



💎 **ShapeFactory.java**

* **Map**으로 **객체들을 관리**하여 팩토리 안에 정의 해둔 **Map에 객체가 있다면 별도의 인스턴스 생성 없이 그대로 Map에서 리턴** 하고 **만약 없다면 새로 인스턴스를 생성**하여 맵에 저장(put) 한 후에 그 객체를 리턴한다.

```java
package StructurePattern.FlyweightPattern;

import java.util.HashMap;

/*
디자인 패턴의 교과서인 GoF에서는 플라이웨이트 패턴에 대해 다음과 같이 정의하고 있습니다.

'공유(Sharing)'를 통하여 대량의 객체들을 효과적으로 지원하는 방법

이처럼 플라이웨이트 패턴은 많은 수의 객체를 생성해야 할 때 주로 쓰입니다.

쉽게 말하면 캐시된 데이터 사용하는거 같은데?
 */


/*
플라이웨이트 패턴은 어디에서 쓰이고 있을까요?

자바의 모든 래퍼 클래스의 valueOf() 메소드가 바로 이 플라이웨이트 패턴을 사용하고 있습니다.
그래서 래퍼 클래스를 생성해야 할 때 new 키워드를 통해 인스턴스를 매번 생성하기보다는 valueOf() 메소드를 통해 생성하는 것이 더 효율적입니다.


또, 대표적으로 사용되는 것이 바로 Java의 String Pool 입니다.
Java에서는 String Pool을 별도로 두어 같은 문자열에 대해 다시 사용될 때에 새로운 메모리를 할당하는 것이 아니라
tring Pool에 있는지 검사해서 있으면 가져오고 없으면 새로 메모리를 할당하여 String Pool에 등록한 후에 사용하도록 하고 있습니다.
 */
public class ShapeFactory {
    private static final HashMap<ShapeType, Shape> shapes = new HashMap<ShapeType, Shape>();
    public static Shape getShape(ShapeType type) {
        Shape shapeImpl = shapes.get(type);
        if ( shapeImpl == null ) {
            if ( type.equals(ShapeType.OVAL_FILL) ) {
                shapeImpl = new Oval(true);
            }
            else if ( type.equals(ShapeType.OVAL_NOFILL) ) {
                shapeImpl = new Oval(false);
            }
            else if ( type.equals(ShapeType.LINE) ) {
                shapeImpl = new Line();
            }
            shapes.put(type, shapeImpl);
        }
        return shapeImpl;
    }


    public static enum ShapeType {
        OVAL_FILL, OVAL_NOFILL, LINE;
    }
}
```



<hr>



💎 **DrawingClient.java**

* 테스트 코드



* 반복문 내에서 20번 **ShapeFactory** 클래스의 **getShape**를 호출한다.



* Line 객체와 Oval 객체가 최초에 생성 될 때에만 생성자에서 설정해두었던 Sleep(2000)이 실행되고 이후에는 별도의 딜레이 없이 빠르게 생성되는 것을 확인할 수 있다.

```java
package StructurePattern.FlyweightPattern;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

public class DrawingClient extends JFrame {

    private final int WIDTH;
    private final int HEIGHT;

    private static final ShapeFactory.ShapeType shapes[] = {ShapeFactory.ShapeType.LINE, ShapeFactory.ShapeType.OVAL_FILL, ShapeFactory.ShapeType.OVAL_NOFILL};
    private static final Color colors[] = {Color.RED, Color.green, Color.yellow};

    public DrawingClient(int width, int height) {
        this.WIDTH = width;
        this.HEIGHT = height;
        Container contentPane = getContentPane();

        JButton startButton = new JButton("Draw");
        final JPanel panel = new JPanel();

        contentPane.add(panel, BorderLayout.CENTER);
        contentPane.add(startButton, BorderLayout.SOUTH);
        setSize(WIDTH, HEIGHT);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setVisible(true);

        startButton.addActionListener(new ActionListener() {
            public void actionPerformed(ActionEvent event) {
                Graphics g = panel.getGraphics();
                for (int i = 0; i < 20; ++i) {
                    Shape shape = ShapeFactory.getShape(getRandomShape());
                    shape.draw(g, getRandomX(), getRandomY(), getRandomWidth(),
                            getRandomHeight(), getRandomColor());
                }
            }
        });
    }

    private ShapeFactory.ShapeType getRandomShape() {
        return shapes[(int) (Math.random() * shapes.length)];
    }

    private int getRandomX() {
        return (int) (Math.random() * WIDTH);
    }

    private int getRandomY() {
        return (int) (Math.random() * HEIGHT);
    }

    private int getRandomWidth() {
        return (int) (Math.random() * (WIDTH / 10));
    }

    private int getRandomHeight() {
        return (int) (Math.random() * (HEIGHT / 10));
    }

    private Color getRandomColor() {
        return colors[(int) (Math.random() * colors.length)];
    }

    public static void main(String[] args) {
        DrawingClient drawing = new DrawingClient(500,600);
    }

}
```

