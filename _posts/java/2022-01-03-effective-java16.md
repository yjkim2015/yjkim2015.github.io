---
title: public 클래스에서는 public 필드가 아닌 접근자 메서드를 사용하라 - Effective Java[16]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---




#### 🔗 public 클래스에서의 public 필드를 통한 데이터 접근의 단점

* API를 수정하지 않고는 내부 표현을 바꿀 수 없다.
* 불변식 보장 불가
* 외부에서 필드에 접근할 때 부수 작업 수행 불가

예시)

```java
class Point {
	public double x;
    public double y;
}
```



<hr>



#### 🔗 그럼 어떻게 해야돼?

앞 블로그에서도 봤지만, 우리는 객체지향 프로그래밍에서 접근권한을 최소화 하면서 얻는 캡슐화의 이점을 살펴봤다.

**위 필드들을 모두 private으로 바꾸고 public 접근자 (getter)를 추가한다.**

예시)

```java
class Point {
	private double x;
	private double y;
    
    public Point(double x, double y) {
        this.x = x;
        this.y = y;
    }
	
    public double getX() { return x; }
    public double getY() { return y; }

    public void setX(double x) { this.x = x; }
    public void setY(double y) { this.y = y; }
}
```



<hr>


#### 🔗 public 데이터 필드를 노출해도 문제가 되지 않는 클래스가 있다며?

**package-private[default] 클래스 혹은 private 중첩 클래스라면 데이터 필드를 public으로 노출한다해도 문제가 되지 않는다.** 그 클래스가 표현하려는 추상 개념만 올바르게 표현해주면 된다.

* **pacakage-private[default]** 클래스인 경우 패키지 내부에서 사용하는 코드이다. 
  (즉, 패키지 바깥 코드는 전혀 손대지 않고도 데이터 표현 방식 변경 가능)

* **private** 중첩 클래스인 경우 수정범위가 더 좁아져서 이 클래스를 포함하는 외부 클래스까지로 제한된다.



<hr>



#### 🔗 public 데이터 필드가 불변인건 어때?

public 클래스의 필드가 불변이라면 직접 노출할 떄의 단점이 조금은 줄어들지만, 여전히 결코 좋은 생각은 아니다.

**API를 변경하지 않고는 표현방식을 바꿀 수 없고, 필드를 읽을 때 부수 작업을 수행할 수 없다는 단점은 여전하다.**



<span style="color:red;">단, 불변식은 보장할 수 있게 된다. </span>

예시를 보자. 다음 클래스는 각 인스턴스가 유효한 시간을 표현함을 보장한다.

```java
public final class Time {
	private static final int HOURS_PER_DAY    = 24;
    private static final int MINUTES_PER_HOUR = 60;
	
    public final int hour;
    public final int minute;
    
    public Time(int hour, int minute) {
        if (hour < 0 || hour >= HOURS_PER_DAY) {
            throw new IllegalArgumentException("시간 : " + hour);
        }
        if (minute < 0 || minute >= MINUTES_PER_HOUR) {
            throw new IllegalArgumentException("분 : " + minute);
        }
        this.hour = hour;
        this.minute = minute;
    }
}
```





<hr>



> public 클래스는 절대 가변 필드를 직접 노출해서는 안 된다. 불변 필드라면 노출해도 덜 위험하지만 완전히 안심할 수는 없다. 하지만 package-private 클래스나 private 중첩 클래스에서는 종종 (불변이든 가변이든) 필드를 노출하는 편이 나을 때도 있다.







```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

