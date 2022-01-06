---
title: 인스턴스화를 막으려거든 private 생성자를 사용하라. - Effective Java[4]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



객체 지향적으로 사고하지 않는 이들이 종종 남용하는 경우가 있지만, 정적 메서드와 정적필드만을 담은 클래스는 나름의 쓰임새가 있다. 아래의 예시를 보자

* java.lang.Math, java.util.Arrays처럼 기본 타입 값이나 배열 관련 메소드들의 모아놓을 수 있다.

* java.util.Collections처럼 특정 이너페이스를 구현하는 객체를 생성해주는 정적 메소드를 모아놓을 수 있다.
* final 클래스와 관련한 메서드들을 모아놓을 수 있다.

<hr>

***이러한 정적 멤버만 담은 유틸리티 클래스는 인스턴스로 만들어 쓰려고 설계한 게아니다.***

하지만 생성자를 명시하지 않으면 컴파일러가 자동으로 기본 생성자를 만들어준다.

**즉, 매개변수를 받지 않는 public 생성자가 만들어지며, 사용자는 이 생성자가 자동 생성된 것인지 구분할 수 없다.**



<hr>

**추상 클래스로 만드는 것으로는 인스턴스화를 막을 수 없다.** 

하위 클래스로 만들어 인스턴스화하면 그만이다라는 말이다. 

이를 본 사용자는 상속해서 사용하라는 뜻으로 오해 할 여지도 있기에 큰 문제이다.

다행히도 인스턴스화를 막는 방법은 아주 간단하며, 아래와 같다.



## Step 1 : private 생성자를 추가하면 클래스의 인스턴스화를 막을 수 있다.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;UtilityClass&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#999999">//기본&nbsp;생성자가&nbsp;만들어지는&nbsp;것을&nbsp;막는다&nbsp;(인스턴스화&nbsp;방지용);</span></div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;UtilityClass()&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">throw</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;AssertionError();</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

컴파일러가 기본 생성자를 만드느 경우는 오직 명시된 생성자가 없을 경우 뿐이니 위처럼 private 생성자를 추가하면 클래스의 인스턴스화를 막을 수 있다.



**명시적 생성자가 private이니 클래스 바깥에서는 접근할 수 없다.**

**하지만 생성자가 분명 존재하는데 호출할 수는 없어서, 그다지 직관적이지 않다. **

**그러기 때문에 위의 코드처럼 적절한 주석을 달아주도록 하자.**

<hr>

***<span style="color:red;">이 방식은 상속을 불가능하게 하는 효과도 있다.</span> 모든 생성자는 명시적이든 묵시적이든 상위 클래스의 생성자를 호출하게 되는데, 이를 private으로 선언했으니 하위 클래스가 상위 클래스의 생성자에 접근할 길이 막혀버린다.***






```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

