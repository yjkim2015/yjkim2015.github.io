---
title: 객체지향-객체(Object) Part-2
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



## Step 1 : 다형성과 추상 타입

객체지향이 주는 장점은 구현 변경의 유연함이다.  앞서 객체는 캡슐화를 통해서 객체를 사용하는 다른 코드에 영향을 최소화하면서 객체의 내부 구현을 변경할 수 있는 유연함을 얻을 수 있었다. 

유연함을 얻을 수 있도록 해주는 또 다른  방법은 추상화에 있다.

먼저 추상화를 가능하게 해주는 <span style="color:red;">다형성</span>에 대해 알아보자.

<hr>
**다형성(Polymorphysm)은 한 객체가 여러 가지(poly) 모습(morph)를 갖는다는 것을 뜻한다. 여기서 모습이란 타입을 뜻하는데** 

***즉, 다형성이란 한 객체가 여러 타입을 가질 수 있다는 것을 말한다.***

자바와 같은 정적 타입 언어에서는 <span style="color:red;">타입 상속</span>을 통해서 다형성을 구현한다.

<span style="color:red;">타입 상속</span>은 **인터페이스 상속**과 **구현 상속**으로 구분해 볼 수 있다. 

<br>

**인터페이스 상속은 순전히 타입 정의만을 상속받는것이다.**

자바와 같이 클래스 다중 상속을 지원하지 않는 언어에서는 인터페이스를 이용해서 객체가 다형을 갖게 된다.

<br>


**구현상속은 클래스 상속을 통해서 이루어진다.**

구현상속은 보통 상위 클래스에 정의된 기능을 재사용하기 위한 목적으로 사용된다.



## Step 2 : 추상 타입과 유연함

***추상화는 데이터나 프로세스 등을 의미가 비슷한 개념이나 표현으로 정의하는것이다.***

추상 타입과 실제 구현 클래스는 상속을 통해서 연결한다. 즉, 구현 클래스가 추상 타입을 상속받는 방법으로 둘을 연결하는것이다.



**하위타입[실제구현클래스] 는 상위 타입[추상 타입]에 정의된 기능을 실제로 구현하는데, 이들 클래스들은 실제 구현을 제공한다는 의미에서 **

**'콘크리트 클래스(concrete class)'라고 부른다.**

<hr>

~~why abstraction need?~~ 

~~이쯤 되면 필자가 뭘 좋아하는지 알 것이다.~~

필자는 왜(why)에 집중하며 한두줄 요약을 즐긴다.

<span style="color:red;">그럼 왜 추상화가 필요하냐 ? </span>콘크리트 클래스만 직접 사용해도 되지 않냐? 라고 생각 할 수 있다.



**핵심부터 말하자면 추상화 역시 변경의 유연함을 증가시켜 준다.**

이게 무슨 말이야? 

아래 예시를 보자.

```
public class EatController {
	Logger logger = LoggerFactory.getLogger(getClass());
	String data;
	public void process() {
		Meaterarian meaterarian = new Meaterarian();
		data = meaterarian.eat();
		
		logger.debug("data : " + data)
	}
}
```

EatController에서 process 메소드는 육식주의자 Meaterarian가 식사하는것을 구현했다.



<span style="color:red;">어느 날 새로운 요구 사항이 들어왔다.</span> **육식주의자 뿐만아니라 채식주의자도 구현해달라는것이다.**

이제 어떻게 해야할까? 다음과 같이 조건식을 두어서 할 수 있을 것이다.

```
public class EatLogController {
	Logger logger = LoggerFactory.getLogger(getClass());
 
	private boolean isVegetarian;
	String data;
	public EatController(boolean isVegetarian) {
		this.isVegetarian = isVegetarian;
	}
	
	public void process() {
		if ( isVegetarian ) {
			Vegetarian vegetarian = new Vegetarian();
			data = vegetarian.eat();
		}
		else {
            Meaterarian meaterarian = new Meaterarian();
            data = meaterarian.eat();
		}
		logger.debug("data : " + data);
	}
}
```

**눈치가 빠른 사람이라면 살짝 느낌이 안좋을 것이다**. 

if else 블록의 코드 구성이... 만약 비건에서도 세분화된 세미 베지터리안을 위한 구현을 추가하라면..? 보인다 또 하나의 else 문이 추가 될것이... 

이런 상황들이 유지보수를 어렵게 만드는 것이다.





```
참조 - 개발자가 반드시 정복해야 할 객체지향과 디자인패턴 By 최범균
```

