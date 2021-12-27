---
title: clone 재정의는 주의해서 진행해라
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---

<code>**Cloneable**</code>은 복제해도 되는 클래스임을 명시하는 용도의 믹스인 인터페이스(mixin interface)지만,

아쉽게도 의도한 목적을 제대로 이루지 못했다.

가장 큰 문제는 <code>clone</code> 메소드가 선언된 곳이 Cloneable이 아닌 <code>Object</code>이고, 그마저도 <code>protected</code> 접근자로 되있다는 것이다.

그래서 <code>Cloneable</code>을 구현하는 것만으로는 외부 객체에서 clone 메소드를 호출할 수 없다.



<span style="color:red">하지만</span> 이를 포함한 여러 문제점에도 불구하고 Cloneable방식은 널리 쓰이고 있어서 잘 알아 두는 것이 좋다.

<hr>

#### 🔗 도대체 무슨 일을 하는데 널리 쓰인다는거야?

자 충격적인걸 보자. 

![image-20211227214539238](../../assets/images/2021-12-27-effective-java13/image-20211227214539238.png)

**<code>Cloneable</code> 인터페이스는 메서드 하나 조차 가지고 있지 않다.** 

<span style="color:red;">하지만</span> 이 인터페이스는 놀랍게도 <code>Object</code>의 <code>protected</code> 메소드인 <code>clone</code>의 동작 방식을 결정한다.

<code>**Cloneable**</code>을 구현한 클래스의 인스턴스에서 <code>clone</code>을 호출하면 그 객체의 필드들을 하나하나 복사한 객체를 반환하며, 그렇지 않은 클래스의 인스턴스에서 호출하면 <code>CloneNotSupportedException</code>을 던진다.

<br>

**이는 인터페이스를 상당히 이례적으로 사용한 예이니 따라하지는 말자.**

인터페이스를 구현한다는 것은 일반적으로 해당 클래스가 그 인터페이스에서 정의한 기능을 제공한다고 선언하는 행위이다. <span style="color:red;">그런데</span> <code>Cloneable</code>의 경우에는 **상위 클래스**에 정의된 <code>protected</code> 메소드의 동작 방식을 변경한 것이다.

<hr>
##### 💎실무에서 <code>Cloneable</code>을 구현한 클래스는 <code>clone</code> 메소드를 <code>public</code>으로 제공하며, 사용자는 당연히 복제가 제대로 이뤄지리라 기대한다.

이 기대를 만족시키려면 그 클래스와 모든 상위클래스는 복잡하고, 강제할 수 없고, 허술하게 기술된 프로토콜을 지켜야만 하는데, **그 결과로 깨지기 쉽고, 위험하고, 모순적인 메커니즘이 탄생한다**.

**생성자를 호출하지 않고도 객체를 생성할 수 있게 되는 것이다.**

clone 메소드의 일반 규약은 다음과 같이 허술하다.

<hr>

> 이 객체의 복사본을 생성해 반환한다. '복사'의 정확한 뜻은 그 객체를 구현한 클래스에 따라 다를 수 있다. 일반적인 의도는 다음과 같다. 어떤 객체 x에 대해 다음 식은 참이다.
>
> x.clone() != x
>
> 또한 다음 식도 참이다.
>
> x.clone().getClass() == x.getClass()
>
> 하지만 이상의 요구를 반드시 만족해야 하는 것은 아니다.
>
> 한편 다음 식도 일반적으로는 참이지만, 역시 필수는 아니다.
>
> x.clone().equals(x)
>
> 관례상, 이 메소드가 반환하는 객체는 super.clone을 호출해 얻어야 한다. 이 클래스와 Object를 제외한 모든 상위 클래스가 이 관례를 따른다면 다음 식은 참이다.
>
> x.clone().getClass() == x.getClass()
>
> 관례상, 반환된 객체와 원본 객체는 독립적이어야 한다. 이를 만족하려면 super.clone으로 얻은 객체의 필드 중 하나 이상을 반환 전에 수정해야 할 수도 있다.

<hr>

위 설명을 자세히보면 관례라는 말이 많이 나온다. 그 말 그대로 강제성이 없다는 것이다.

<span style="color:red;">만약</span>, <code>clone</code> 메소드가 <code>super.clone</code>이 아닌, 생성자를 호출해 얻은 인스턴스를 반환하더라도 컴파일시에 문제가 되지않지만 해당 클래스의 하위 클래스에서 <code>super.clone</code>을 호출한다면 하위 클래스 타입 객체를 반환하지 않고 상위 클래스 타입 객체를 반환하여 문제가 생길 수 있다.

<br>

<code>clone</code>을 재정의한 클래스가 <code>final</code>이라면 걱정해야 할 하위 클래스가 없으니 <span style="color:red;">이 관례는 무시</span>해도 된다. 하지만 <code>final</code> 클래스의 <code>clone</code>메소드가 <code>super.clone</code>을 호출하지 않는다면 <code>Cloneable</code>을 구현할 이유도 없다. <code>Object</code>의 <code>clone</code>구현의 동작 방식에 기댈 필요가 없기 때문이다.

<hr>

#### 🔗 가변 객체를 참조하지 않는 클래스의 clone

제대로 동작하는 <code>clone</code> 메소드를 가진 상위 클래스를 상속해 <code>Cloneable</code>을 구현한 코드를보자.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%">@Override</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;PhoneNumber&nbsp;<span style="color:#0099cc">clone</span>()&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">try</span>&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;(PhoneNumber)&nbsp;<span style="color:#ff3399">super</span>.<span style="color:#0099cc">clone</span>();</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">catch</span>(CloneNotSupportedException&nbsp;e)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">throw</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;AssertionError();&nbsp;<span style="color:#999999">//일어날&nbsp;수&nbsp;없는&nbsp;일</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

**위 코드는 모든 필드가 기본 타입이거나 불변 객체를 참조하는 코드이다**

💎**즉 ,가변 상태를 참조하지 않는 <code>clone</code> 코드란 얘기이다.**

위 메소드가 동작하게하려면 PhoneNumber의 클래스 선언에 <code>Cloneable</code>을 구현해야한다.

<code>Object</code>의 <code>clone</code> 메소드는 <code>Object</code>를 반환하지만 PhoneNumber의 <code>clone</code>메소드는 PhoneNumber를 반환하게 했다.

**자바가 공변 반환 타이핑을 지원하니 이렇게 하는것이 가능하고 권장하는 방식이기도 한다.**

<br>

<code>super.clone</code> 호출을 <code>try-catch</code> 블록으로 감싼 이유는 <code>Object</code>의 <code>clone</code> 메소드가 <span style="color:red;">검사 예외</span>인 <code>CloneNotSupportedException</code>을 던지도록 선언되었기 때문이다.  사실 알고보면 <span style="color:red;">비검사 예외</span>였지만 말이다. 그것은 나중에 알아보자.

<hr>

**💎가변 객체를 참조하는 클래스의 clone에 대해 살펴보자.**

다음은 Stack 클래스의 코드이다.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div><div style="line-height:130%">12</div><div style="line-height:130%">13</div><div style="line-height:130%">14</div><div style="line-height:130%">15</div><div style="line-height:130%">16</div><div style="line-height:130%">17</div><div style="line-height:130%">18</div><div style="line-height:130%">19</div><div style="line-height:130%">20</div><div style="line-height:130%">21</div><div style="line-height:130%">22</div><div style="line-height:130%">23</div><div style="line-height:130%">24</div><div style="line-height:130%">25</div><div style="line-height:130%">26</div><div style="line-height:130%">27</div><div style="line-height:130%">28</div><div style="line-height:130%">29</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;Stack&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;Object[]&nbsp;elements;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#0099cc">int</span>&nbsp;size&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#308ce5">0</span>;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">static</span>&nbsp;<span style="color:#ff3399">final</span>&nbsp;<span style="color:#0099cc">int</span>&nbsp;DEFAULT_INITIAL_CAPACITY&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#308ce5">16</span>;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;Stack()&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">this</span>.elemens&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;Object[DEFAULT_INITIAL_CAPACITY];</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">void</span>&nbsp;push(Object&nbsp;e)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ensureCapacity();</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;elements[size<span style="color:#0086b3"></span><span style="color:#ff3399">+</span><span style="color:#0086b3"></span><span style="color:#ff3399">+</span>]&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;e;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;Object&nbsp;pop()&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">if</span>&nbsp;(&nbsp;size&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span><span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#308ce5">0</span>&nbsp;)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">throw</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;EmptyStackException();&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Object&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;elements[<span style="color:#0086b3"></span><span style="color:#ff3399">-</span><span style="color:#0086b3"></span><span style="color:#ff3399">-</span>size];</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;elements[size]&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#0099cc">null</span>;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;result;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">void</span>&nbsp;ensureCapacity()&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">if</span>&nbsp;(&nbsp;elements.<span style="color:#0099cc">length</span>&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span><span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;size&nbsp;)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;elements&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;Arrays.copyOf(elements,&nbsp;<span style="color:#308ce5">2</span>&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">*</span>&nbsp;size&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">+</span>&nbsp;<span style="color:#308ce5">1</span>);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

간단했던 앞서의 <code>clone</code> 메소드를 이용하여 단순히 <code>super.clone</code>의 결과를 그대로 반환한다면 어떻게 될까?

**반환된 <code>Stack</code> 인스턴스의 <code>size</code> 필드는 올바른 값을 갖겠지만, <code>elements</code> 필드는 원본 <code>Stack></code> 인스턴스와 똑같은 배열을 참조할 것이다.**



<hr>

#### 🔗 이렇게 가변 객체를 참조하는 클래스의 clone은 어떻게 해야해?

**<code>Stack</code> 클래스의 하나뿐인 생성자를 호출한다면 이러한 상황은 절대 일어나지 않는다.** 

<code>clone</code> 메소드는 사실상 생성자와 같은 효과를 낸다. 즉, <code>clone</code>은 원본 객체에 아무런 해를 끼치지 않는 동시에 복제된 객체의 불변식을 보장해야한다.

다음의 예를 통해 가변 객체를 참조하는 클래스의 <code>clone</code> 방법 중 가장 쉬운 방법을 살펴보자.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%">@Override</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;Stack&nbsp;Clone()&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">try</span>&nbsp;&nbsp;&nbsp;&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Stack&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;(Stack)&nbsp;<span style="color:#ff3399">super</span>.<span style="color:#0099cc">clone</span>();</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;result.elements&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;elements.<span style="color:#0099cc">clone</span>();</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;result;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">catch</span>&nbsp;(CloneNotSupportedException&nbsp;e)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">throw</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;AssertionError();</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

방법은 바로 elements 배열의 clone을 **재귀적으로 호출**해 주는것이다.

배열의 clone은 런타임 타입과 컴파일 타임 타입 모두가 원본 배열과 똑같은 배열을 반환한다.

따라서 배열을 복제할 떄는 배열의 clone 메소드를 사용하라고 권장한다.

***사실, 배열은 clone 기능을 제대로 사용하는 유일한 예라고 한다.***

<br>

**💎<span style="color:red;">final</span> 필드는 clone이 안된다고?**

<code>final</code> 필드에는 새로운 값을 할당 할 수 없기 때문이다. 이는 근본적인 문제로, 직렬화와 마찬가지로 <code>Cloneable</code> 아키텍처는 **'가변객체를 참조하는 필드는 <code>final</code>로 선언하라'**는 일반 용법과 충돌한다.



💎 **clone을 재귀적으로 호출하는 것만으로는 충분하지 않을 때도 있다고?**

이번에는 해시테이블용 clone 메소드를 생각해보자. 해시테이블 내부는 버킷들의 배열이고, 각 버킷은 키-값 쌍을 담는 연결 리스트의 첫 번째 엔트리를 참조한다.





<hr>






```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

