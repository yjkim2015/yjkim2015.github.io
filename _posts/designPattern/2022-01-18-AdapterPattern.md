---
title: 어댑터 (Adapter) 패턴
categories:
- DesignPattern
toc: true
toc_sticky: true
toc_label: 목차
---

## 🔗 어탭터 (Adapter) 패턴이란?



* **어탭터 패턴**은 이름대로 어댑터 처럼 사용되는 패턴이다.

  * ex) 220V를 사용하는 한국에서 쓰던 기기들을, 어댑터를 사용하면 110V를 쓰는곳에 가서도 그대로 쓸 수 있다.

  

  * 호환성이 없는 인터페이스 때문에 **함께 동작할 수 없는 클래스들이 함께 작동하도록 해주는 패턴**이다.



* <span style="color:red;">즉</span>, **클래스의 인터페이스를 <span style="color:red;">사용자가 기대하는 인터페이스 형태로 변환</span>시키는 패턴이다.**



<hr>



##### 💎  어댑터 패턴 장점

* 관계가 없는 인터페이스 간 같이 사용 가능



* 프로그램 검사 용이



* 클래스 재활용성 증가



<hr>

💎 **Volt 클래스 - volt의 값을 갖고 있음** 

```java
package StructurePattern.AdapterPattern;

public class Volt {
    private int volts;

    public Volt(int volts) {
        this.volts = volts;
    }

    public int getVolts() {
        return volts;
    }

    public void setVolts(int volts) {
        this.volts = volts;
    }
}
```



💎 **Socket 클래스 -  120볼트를 값으로 갖는 볼트 객체를 생성하는 클래스**

```java
package StructurePattern.AdapterPattern;

public class Socket {

    public Volt getVolt() {
        return new Volt(120);
    }
}
```



💎 **120볼트뿐만 아니라 3볼트와 12볼트로 추가로 생성하는 어댑터 인터페이스** 

```java
package StructurePattern.AdapterPattern;

public interface SocketAdapter {
    public Volt get120Volt();

    public Volt get12Volt();

    public Volt get3Volt();
}
```



<hr>



##### 💎 어댑터 패턴 구현 방법

* **Class Adapter - 자바의 상속(Inheritance)를 이용한 방법**

```java
package StructurePattern.AdapterPattern;

//ClassAdapter 자바의 상속을 이용한 방법
//어댑터 패턴은 클래스의 인터페이스를 사용자가 기대하는 인터페이스 형태로 변환시키는 패턴입니다.
public class SocketClassAdapterImpl extends Socket implements SocketAdapter {

    @Override
    public Volt get120Volt() {
        return getVolt();
    }

    @Override
    public Volt get12Volt() {
        Volt v = getVolt();
        return convertVolt(v,10);
    }

    @Override
    public Volt get3Volt() {
        Volt v = getVolt();
        return convertVolt(v,40);
    }

    private Volt convertVolt(Volt v, int i) {
        return new Volt(v.getVolts()/i);
    }
}
```



* **Object Adapter - 자바의 합성(Composite)을 이용한 방법**

```java
package StructurePattern.AdapterPattern;

//Object Adapter 방식
//어댑터 패턴은 클래스의 인터페이스를 사용자가 기대하는 인터페이스 형태로 변환시키는 패턴입니다.
public class SocketObjectAdapterImpl implements SocketAdapter {

    private Socket socket = new Socket();

    @Override
    public Volt get120Volt() {
        return socket.getVolt();
    }

    @Override
    public Volt get12Volt() {
        Volt v = socket.getVolt();
        return convertVolt(v,10);
    }

    @Override
    public Volt get3Volt() {
        Volt v = socket.getVolt();
        return convertVolt(v,40);
    }

    private Volt convertVolt(Volt v, int i) {
        return new Volt(v.getVolts()/i);
    }
}
```



<hr>



💎 **어댑터 테스트 코드**

```java
package StructurePattern.AdapterPattern;

//어댑터 패턴은 클래스의 인터페이스를 사용자가 기대하는 인터페이스 형태로 변환시키는 패턴입니다.
public class AdapterPatternTest {
    public static void main(String[] args) {
        testClassAdapter();
        testObjectAdapter();
    }

    private static void testObjectAdapter() {
        SocketAdapter socketAdapter = new SocketObjectAdapterImpl();
        Volt v3 = getVolt(socketAdapter, 3);
        Volt v12 = getVolt(socketAdapter, 12);
        Volt v120 = getVolt(socketAdapter, 120);

        System.out.println("v3 volts using Object Adapter = " + v3.getVolts());
        System.out.println("v12 volts using Object Adapter = " + v12.getVolts());
        System.out.println("v120 volts using Object Adapter = " + v120.getVolts());

    }


    private static void testClassAdapter() {
        SocketAdapter socketAdapter = new SocketClassAdapterImpl();
        Volt v3 = getVolt(socketAdapter, 3);
        Volt v12 = getVolt(socketAdapter, 12);
        Volt v120 = getVolt(socketAdapter, 120);

        System.out.println("v3 volts using Class Adapter = " + v3.getVolts());
        System.out.println("v12 volts using Class Adapter = " + v12.getVolts());
        System.out.println("v120 volts using Class Adapter = " + v120.getVolts());
    }

    private static Volt getVolt(SocketAdapter socketAdapter, int i) {
        switch (i) {
            case 3: return socketAdapter.get3Volt();
            case 12: return socketAdapter.get12Volt();
            case 120: return socketAdapter.get120Volt();
            default: return socketAdapter.get120Volt();
        }
    }
}
```



