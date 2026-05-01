---
title: equals는 일반 규약을 지켜 재정의하라 - Effective Java[10]
categories:
- EFFECTIVE_JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

**<code>equals</code> 메소드는 기본적으로 최상위 객체인 <code>Object</code>에서 제공하는 메소드로서 재정의를 염두에 두고 설계된 것이다. 때문에 재정의 시 지켜야 하는 일반 규약이 명확이 정의가 되어있다.**

이러한 규약을 지키지 않고 재정의를 했다간 끔찍한 결과를 초래할 수 있다.



**<span style="color:red;">그렇다면 먼저 <code>equals</code> 재정의 규약을 살펴보기 전에 어느 상황에서는 재정의 하면 안되는지 부터 알아보자.</span>**

<hr>

### 🔗 각 인스턴스가 본질적으로 고유하다.

값을 표현하는게 아니라 동작하는 개체를 표현하는 클래스가 여기 해당한다. <code>Thread</code>가 좋은 예로, Object의 equals 메서드는 이러한 클래스에 딱 맞게 구현되었다.

<hr>

### 🔗 인스턴스의 '논리적 동치성(logical equality)'를 검사할 일이 없다.

- 논리적 동치: 두 명제 p, q에 대해 쌍방 조건이 항진 명제인 경우, 즉 p<=>q
- 항진 명제: 논리식 혹은 합성명제에 있어 각 명제의 참·거짓의 모든 조합에 대하여 항상 참인 것
- **즉, 쉽게 말하면 인스턴스들 끼리 equals() 메서드를 사용해서, 논리적으로 같은지 검사할 필요가 없는 경우에는 <code>Object</code>의 기본 <code>equals</code> 로만으로도 해결한다.**

<hr>

### 🔗 상위 클래스에서 재정의한 equals가 하위 클래스에도 딱 들어맞는다.

- HashSet, TreeSet, EnumSet 등 대부분의 Set 구현체 - <code>AbstractSet</code> 에서 정의된 equals 사용
- ArrayList, Vector 등 대부분의 List 구현체 - <code>AbstractList</code> 에서 정의된 equals 사용
- HashMap, TreeMap, EnumMap 등 대부분의 Map 구현체 - <code>AbstractMap</code> 에서 정의된 equals 사용

<hr>

### 🔗 클래스가 private이거나 package-private이고 equals 메소드를 호출할 일이 없다.

이 경우에는 equals가 실수로라도 호출되는 걸 막고 싶다면 아래와 같이  하는것이 좋다고 한다.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%">@Override</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">boolean</span>&nbsp;<span style="color:#0099cc">equals</span>(Object&nbsp;o)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">throw</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;AssertionError();</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>



**여기까지 <code>equals</code>를 재정의하면 안되는 상황들에 대해 알아보았다.**

<hr>

**<span style="color:red;">그렇다면 이제 도대체 언제 <code>equals</code>를 정의해야하는지에 대해 알아보자.</span>**




> ##### equals를 재정의해야 할 때는
>
> ##### 객체 식별성(object identity : 두 객체가 물리적으로 같은가)이 아니라 
>
> ##### 논리적 동치성을 확인해야하는데, 
>
> ##### 상위 클래스의 equals가 논리적 동치성을 비교하도록 재정의 되지 않았을 때이다.

<br>

**주로 값 클래스들이 해당한다 [값 클래스란 <code>Integer</code>와 <code>String</code>처럼 값을 표현하는 클래스]**

두 값 객체를 equals로 비교하는 프로그래머는 객체가 같은지가 아닌 값이 같은지를 알고 싶어 할 것이다.

**<code>equals</code>가 논리적 동치성을 비교하도록 재정의 해두면, 그 인스턴스는 값을 비교하길 원하는 프로그래머의 기대에 부응함은 물론 Map의 키와 Set의 원소로 사용할 수 있게 된다.**

<hr>
<span style="color:red;">하지만</span>, 값 클래스라 해도, <code>싱글턴 클래스[인스턴스 통제 클래스]</code> 처럼 같은 인스턴스가 둘 이상 만들어지지 않음을 보장하는 녀석에게는 <code>equals</code>를 재정의 할 이유가 없다.
<br>

지금까지 <code>equals</code>를 언제 재정의하는지도 알아보았다. 

<span style="color:red;">중요한게 남아있다. <code>equals</code> 메소드를 재정의할 때는 따라야하는 규약이 있다고 한다.</span>

아래에서 살펴보자.



### 🔗 equals 메소드를 재정의 할 때 따라야하는 일반 규약

다음은 Object 명세에 적힌 규약이다.



> equals 메소드는 동치관계(equivalence relation)을 구현하며, 다음을 만족한다.
>
> * **반사성(reflexivity)** : null이 아닌 모든 참조 값 x에 대해, x.equals(x)는 true이다.
> * **대칭성(symmetry)** : null이 아닌 모든 참조 값 x,y에 대해, x.equals(y)가 true이면 y.equals(x)도 true이다.
> * **추이성(transitivity)** : null이 아닌 모든 참조 값 x,y,z에 대해, x.equals(y)가 true이고 y.equals(z)도 true이면 x.equals(z)도 true이다.
> * **일관성(consistency)**: null이 아닌 모든 참조 값 x,y에 대해, x.equals(y)를 반복해서 호출하면 항상 true를 반환하거나 항상 false를 반환한다.
> * **null-아님** : null이 아닌 모든 참조 값 x에 대해, x.equals(null)은 false이다.



<hr>

하나하나씩 자세히 살펴보도록 하자.



### 💎 반사성

**단순히 말하면 객체는 자기 자신과 같아야 한다는 말**이라는데 ? 뭔 당연한 소릴 하는걸까? 라고 생각할 것 같다.

이 요건은 일부러 여기는 경우가 아니라면 만족시키지 못하기가 더 어렵다고 한다.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div><div style="line-height:130%">12</div><div style="line-height:130%">13</div><div style="line-height:130%">14</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;Car&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">static</span>&nbsp;<span style="color:#ff3399">void</span>&nbsp;main(<span style="color:#0099cc">String</span>[]&nbsp;args)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Set<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span>Car<span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>&nbsp;carSet&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;Set<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span><span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>();</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Car&nbsp;car&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;Car();</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;carSet.<span style="color:#0099cc">add</span>(car);</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#999999">//반사성을&nbsp;어기면&nbsp;해당&nbsp;값이&nbsp;false가&nbsp;나온다고&nbsp;한다.</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#0099cc">System</span>.<span style="color:#0099cc">out</span>.<span style="color:#0099cc">println</span>(carSet.contains(car));</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>



<hr>

### 💎 대칭성

두 객체는 서로에 대한 동치 여부에 똑같이 답해야 한다.

다음의 예시를 보자.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div><div style="line-height:130%">12</div><div style="line-height:130%">13</div><div style="line-height:130%">14</div><div style="line-height:130%">15</div><div style="line-height:130%">16</div><div style="line-height:130%">17</div><div style="line-height:130%">18</div><div style="line-height:130%">19</div><div style="line-height:130%">20</div><div style="line-height:130%">21</div><div style="line-height:130%">22</div><div style="line-height:130%">23</div><div style="line-height:130%">24</div><div style="line-height:130%">25</div><div style="line-height:130%">26</div><div style="line-height:130%">27</div><div style="line-height:130%">28</div><div style="line-height:130%">29</div><div style="line-height:130%">30</div><div style="line-height:130%">31</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">package</span>&nbsp;Item10;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">import</span>&nbsp;java.util.Objects;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;CaseInsensitiveString&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">final</span>&nbsp;<span style="color:#0099cc">String</span>&nbsp;s;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;CaseInsensitiveString(<span style="color:#0099cc">String</span>&nbsp;s)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">this</span>.s&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;Objects.requireNonNull(s);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">static</span>&nbsp;<span style="color:#ff3399">void</span>&nbsp;main(<span style="color:#0099cc">String</span>[]&nbsp;args)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;CaseInsensitiveString&nbsp;cis&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;CaseInsensitiveString(<span style="color:#993333">"Polish"</span>);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#0099cc">String</span>&nbsp;s&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#993333">"polish"</span>;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#0099cc">System</span>.<span style="color:#0099cc">out</span>.<span style="color:#0099cc">println</span>(cis.<span style="color:#0099cc">equals</span>(s));</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;@Override</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">boolean</span>&nbsp;<span style="color:#0099cc">equals</span>(Object&nbsp;o)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">if</span>&nbsp;(&nbsp;o&nbsp;<span style="color:#ff3399">instanceof</span>&nbsp;CaseInsensitiveString)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;s.<span style="color:#0099cc">equalsIgnoreCase</span>(((CaseInsensitiveString)&nbsp;o).s);</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">if</span>&nbsp;(&nbsp;o&nbsp;<span style="color:#ff3399">instanceof</span>&nbsp;<span style="color:#0099cc">String</span>)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;s.<span style="color:#0099cc">equalsIgnoreCase</span>((<span style="color:#0099cc">String</span>)&nbsp;o);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;<span style="color:#308ce5">false</span>;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

위 코드의 문제점을 무엇일까?

<code>CaseInsensitiveString</code>의 <code>equals</code>는 일반 문자열과 비교를 시도하며 결과는 <code>true</code>를 반환한다.

문제는 <code>CaseInsensitiveString</code> 의 재정의된 <code>equals</code>는 일반 <code>String</code> 을 알고 있지만 <code>String</code>의 <code>equals</code>는 재정의 되있지 않기 때문에 <code>CaseInsensitiveString</code>의 존재를 모른다. 



**따라서 역으로 s.equals(cis)는 false를 반환하여, 대칭성을 명백히 위반한다.**

<hr>

이 문제를 해결하려면 <code>CaseInsensitiveString</code>의 <code>equals</code>를 <code>String</code>과도 연동한다는 허황된 꿈을 버려야 하며 아래와 같이 해결해야 한다. 

**결론 - 같은 놈 끼리만 비교해라;;**

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%">@Override</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">boolean</span>&nbsp;<span style="color:#0099cc">equals</span>(Object&nbsp;o)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;o&nbsp;<span style="color:#ff3399">instanceof</span>&nbsp;CaseInsensitiveString&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">&amp;</span><span style="color:#0086b3"></span><span style="color:#ff3399">&amp;</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;((CaseInsensitiveString)&nbsp;o).s.<span style="color:#0099cc">equalsIgnoreCase</span>(s);</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

<hr>

### 💎 추이성

***추이성은 첫번째 객체와 두 번째 객체가 같고, 두 번째 객체와 세 번째 객체가 같다면, 첫 번째 객체와 세 번째 객체도 같아야 한다는 뜻이다. 겉보기에는 이 요건도 간단해보이지만 자칫하면 어기기 쉽다.***

상위 클래스에는 없는 새로운 필드를 하위클래스에 추가하는 상황을 생각해보자.

equals 비교에 영향을 주는 정보를 추가하는 것이다.

아래 예시를 통해 자세히 살펴보자.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div><div style="line-height:130%">12</div><div style="line-height:130%">13</div><div style="line-height:130%">14</div><div style="line-height:130%">15</div><div style="line-height:130%">16</div><div style="line-height:130%">17</div><div style="line-height:130%">18</div><div style="line-height:130%">19</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;Point&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">final</span>&nbsp;<span style="color:#0099cc">int</span>&nbsp;x;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">final</span>&nbsp;<span style="color:#0099cc">int</span>&nbsp;y;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;Point(<span style="color:#0099cc">int</span>&nbsp;x,&nbsp;<span style="color:#0099cc">int</span>&nbsp;y)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">this</span>.x&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;x;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">this</span>.y&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;y;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;@Override</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">boolean</span>&nbsp;<span style="color:#0099cc">equals</span>(Object&nbsp;o)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">if</span>&nbsp;(&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">!</span>(o&nbsp;<span style="color:#ff3399">instanceof</span>&nbsp;Point)&nbsp;)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;<span style="color:#308ce5">false</span>;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Point&nbsp;p&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;(Point)o;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;p.x&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span><span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;x&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">&amp;</span><span style="color:#0086b3"></span><span style="color:#ff3399">&amp;</span>&nbsp;p.y&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span><span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;y;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

이제 이 클래스를 확장해서 상위 클래스에는 없는 Color 필드를 하위 클래스에 집어넣어보자.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div><div style="line-height:130%">12</div><div style="line-height:130%">13</div><div style="line-height:130%">14</div><div style="line-height:130%">15</div><div style="line-height:130%">16</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;ColorPoint&nbsp;<span style="color:#ff3399">extends</span>&nbsp;Point&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">final</span>&nbsp;Color&nbsp;color;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;ColorPoint(<span style="color:#0099cc">int</span>&nbsp;x,&nbsp;<span style="color:#0099cc">int</span>&nbsp;y,&nbsp;Color&nbsp;color)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">super</span>(x,y);</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">this</span>.color&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;color;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;@Override</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">boolean</span>&nbsp;<span style="color:#0099cc">equals</span>(Object&nbsp;o)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">if</span>&nbsp;(&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">!</span>(o&nbsp;<span style="color:#ff3399">instanceof</span>&nbsp;ColorPoint)&nbsp;)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;<span style="color:#308ce5">false</span>;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;<span style="color:#ff3399">super</span>.<span style="color:#0099cc">equals</span>(o)&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">&amp;</span><span style="color:#0086b3"></span><span style="color:#ff3399">&amp;</span>&nbsp;((ColorPoint)o).color&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span><span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;color;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

이제 위 클래스의 인스턴스를 하나씩 만들어 실제로 동작하는 모습을 확인해보자.

```
Point p = new Point(1,2);
ColorPoint cp = new ColorPoint(1,2, Color.BLUE);
Systen.out.println(p.equals(cp));  //true
System.out.println(cp.equals(p));  //false
```

위 코드를 보면 일반 Point를 ColorPoint에 비교한 결과와 그 둘을 바꿔 비교한 결과는 다르다. <span style="color:red;">[대칭성 위배]</span>

Point의 equals는 색상을 무시하고, ColorPoint의 equals는 입력 매개변수의 클래스 종류가 다르다며 매번 false만 반환 할 것이다. <span style="color:red;">(ColorPoint는 Point이지만, Point는 ColorPoint가 아니기 때문)</span>



<hr>

그렇다면 ColorPoint.equals가 Point와 비교할 때는 색상을 무시하도록 하면 해결될까?

다음의 <span style="color:red;">추이성을 위배</span>하는 예시를 보자.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div><div style="line-height:130%">12</div><div style="line-height:130%">13</div><div style="line-height:130%">14</div><div style="line-height:130%">15</div><div style="line-height:130%">16</div><div style="line-height:130%">17</div><div style="line-height:130%">18</div><div style="line-height:130%">19</div><div style="line-height:130%">20</div><div style="line-height:130%">21</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;ColorPoint&nbsp;<span style="color:#ff3399">extends</span>&nbsp;Point&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">final</span>&nbsp;Color&nbsp;color;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;ColorPoint(<span style="color:#0099cc">int</span>&nbsp;x,&nbsp;<span style="color:#0099cc">int</span>&nbsp;y,&nbsp;Color&nbsp;color)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">super</span>(x,y);</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">this</span>.color&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;color;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;@Override</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">boolean</span>&nbsp;<span style="color:#0099cc">equals</span>(Object&nbsp;o)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">if</span>&nbsp;(&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">!</span>(o&nbsp;<span style="color:#ff3399">instanceof</span>&nbsp;Point)&nbsp;)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;<span style="color:#308ce5">false</span>;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">if</span>&nbsp;(&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">!</span>(o&nbsp;<span style="color:#ff3399">instanceof</span>&nbsp;ColorPoint)&nbsp;)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;o.<span style="color:#0099cc">equals</span>(<span style="color:#ff3399">this</span>);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;<span style="color:#ff3399">super</span>.<span style="color:#0099cc">equals</span>(o)&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">&amp;</span><span style="color:#0086b3"></span><span style="color:#ff3399">&amp;</span>&nbsp;((ColorPoint)o).color&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span><span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;color;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

위 코드가 실제 동작하는 모습을 살펴보자

```
ColorPoint p1 = new ColorPoint(1, 2, Color.RED);
Point p2 = new Point(1,2);
ColorPoint p3 = new ColorPoint(1, 2, Color.BLUE);
```

***p1.equals(p2)와 p2.equals(p3)는 true를 반환하는데, p1.equals(p3)는 false을 반환한다. 추이성에 명백히 위배된다.***

<hr>

그럼 도대체 어떻게 해야 추이성을 위배하지 않고 위 문제를 해결 할 수 있을까?

***사실 위 현상은 모든 객체 지향 언어의 동치관계에서 나타나는 근본적인 문제로서, 구체 클래스를 확장해 새로운 값을 추가하면서 equals 규약을 만족시킬 방법은 존재하지 않는다.***

<hr>

<span style="color:red;">하지만, 구체 클래스의 하위 클래스에서 값을 추가할 방법은 없지만 괜찮은 우회 방법이 하나 있다.</span>

**그것은 바로 상속 대신 컴포지션을 사용하는 방법이다**.

Point를 상속하는 대신 Point를 ColorPoint의 private 필드로 두고, ColorPoint와 같은 위치의 일반 Point를 반환하는 view 메소드를 public으로 추가하는 식이다. 

아래의 예제를 보자.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div><div style="line-height:130%">12</div><div style="line-height:130%">13</div><div style="line-height:130%">14</div><div style="line-height:130%">15</div><div style="line-height:130%">16</div><div style="line-height:130%">17</div><div style="line-height:130%">18</div><div style="line-height:130%">19</div><div style="line-height:130%">20</div><div style="line-height:130%">21</div><div style="line-height:130%">22</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;ColorPoint&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">final</span>&nbsp;Point&nbsp;point;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">final</span>&nbsp;Color&nbsp;color;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;ColorPoint(Point&nbsp;point,&nbsp;Color&nbsp;color)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">this</span>.point&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;point;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">this</span>.color&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;color;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;Point&nbsp;getPoint()&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;<span style="color:#ff3399">this</span>.point;&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;@Override</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">boolean</span>&nbsp;<span style="color:#0099cc">equals</span>(Object&nbsp;o)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">if</span>&nbsp;(<span style="color:#0086b3"></span><span style="color:#ff3399">!</span>(o&nbsp;<span style="color:#ff3399">instanceof</span>&nbsp;ColorPoint))&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;<span style="color:#308ce5">false</span>;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ColorPoint&nbsp;cp&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;(ColorPoint)&nbsp;o;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;cp.point.<span style="color:#0099cc">equals</span>(point)&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">&amp;</span><span style="color:#0086b3"></span><span style="color:#ff3399">&amp;</span>&nbsp;cp.color.<span style="color:#0099cc">equals</span>(color);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>



> 추상 클래스의 하위 클래스에서라면 equals 규약을 지키면서도 값을 추가할 수 있다.
>
> "태그 달린 클래스보다는 클래스 계층구조를 활용하라"는 조언을 따르는 클래스 계층구조에서는 아주 중요한 사실이다. 예를들어 값을 갖지않는 추상클래스인 Shape를 위에 두고, 이를 확장하여 radius를 필드를 추가한 Circle 클래스와, length와 width 필드를 추가한 Rectangle 클래스를 만들 수 있다. 상위 클래스를 직접 인스턴스로 만드는게 불가능하다면 지금까지 이야기한 문제는 일어나지 않는다.

<hr>

### 💎 일관성

**일관성은 두 객체가 같다면 (어느 하나 두 객체 모두가 수정 되지 않는 한) 앞으로도 영원히 같아야 한다는 뜻이다.**

클래스가 불변이든 가변이든 equals의 판단에 신뢰할 수 없는 자원이 끼어들게 해서는 안 된다.

이 제약을 어기면 일관성 조건을 만족시키기가 매우 어렵다.

<br>

예컨대 java.net.URL의 equals는 주어진 URL과 매핑된 호스트의 IP주소를 이용해 비교한다. 

그런데 호스트 이름을 IP 주소로 바꾸려면 네트워크를 통해야 하는데, 그 결과가 항상 보장 할 수 없다. 

이는 URL의 equals가 일반 규약을 어기게 하고, 실무에서도 종종 문제를 일으킨다.

이런 문제를 피하려면 equals는 항시 메모리에 존재하는 객체만을 사용한 결정적 계산만 수행해야 한다.

<hr>

### 💎 NULL-아님

ㅋㅋ 이름이 좀 별거 없어보이는데, 공식이름이 없어서 임의로 설정 한 것이라고 한다. ~~그냥 not null이라 하지..~~

**null-아님은 이름처럼 모든 객체가 null과 같지 않아야 한다는 것이다.**

의도하지 않았음에도 o.equals(null)이 true를 반환하는 상황은 상상하기 힘들지만, 실수로 NullPointerException을 던지는 코드는 흔할 것이다.

<br>

수 많은 클래스가 입력이 null인지를 확인해 자신을 보호하는데, equals 메소드에서는 그러한 검사는 필요없다.

동치성을 검사하기 위해서는 건네받은 객체를 적절히 형변환한 후 피루수 필드들의 값을 알아내야하는데, 이때 instanceof 연산자로 입력 매개변수가 올바른지 판단하기 때문이다.

<hr>

지금까지의 내용을 종합해서 양질의 equals 메소드 구현방법을 단계별로 아래와 같이 정리해본다.

1. **== 연산자를 사용해 입력이 자기 자신의 참조인지 확인한다.**



2. **instanceof 연산자로 입력이 올바른 타입인지 확인한다.**



3. **입력을 올바른 타입으로 형변환한다.**



4. **입력 객체와 자기 자신의 대응되는 핵심 필드들이 모두 일치하는지 하나씩 검사한다.**

<hr>

### 🔗 equals의 성능을 잡아라!!



**어떤 필드를 먼저 비교하느냐가 equals의 성능을 좌우하기도 한다.** 



**<span style="color:red;">최상의 성능을 바란다면 다를 가능성이 더 크거나 비교하는 비용이 싼 필드를 먼저 비교하자.</span>**

동기화용 락(lock)필드 같이 객체의 논리적 상태와 관련 없는 필드는 비교하면 안된다.

<hr>

### 🔗 equals 재정의 시 마지막 주의 사항

* **equals를 재정의할 땐 hashCode도 반드시 재정의하자.**

* **너무 복잡하게 해결하려 들지말자.**

  * 필드들의 동치성만 검사해도 equals 규약을 어렵지 않게 지킬 수 있다. 오히려 너무 공격적으로 파고들다가 문제를 일으키기도 한다. 일반적으로 별칭(alias)은 비교하지 않는게 좋다. 예컨대 File 클래스라면, 심볼릭 링크를 비교해 같은 파일을 가리키는지를 확인하려 들면 안된다.

* **Object 외의 타입을 매개변수로 받는 equals 메소드는 선언하지말자. 많은 프로그래머가 다음과 같이 equals를 작성해놓고 문제의 원인을 찾아 해맨다.**

  * ```
    public boolean equals(Myclass o) {
    	...
    }
    ```

​			이 메서드는 Object.equals를 재정의[오버라이딩]이 아니라, 오버로딩한 것이다. 이러한 실수는 			@Override 어노테이션을 사용하면 예방 할 수 있다.

<hr>

### 🔗 equals 작성과 테스트를 알아서 해준다고!? 누가!?

equals를 작성하고 테스트하는 일은 지루하고 이를 테스트하는 코드는 항상 뻔하다. 다행히 이 작업을 대신해줄 오픈소스가 있으니, **구글이 만든 AutoValue 프레임워크이다** 

이 프레임워크는 클래스에 애너테이션 하나만 추가하면 알아서 메서드들을 작성해준다.

<hr>

> 꼭 필요한 경우가 아니면 equals를 재정의하지 말자. 많은 경우에 Object의 equals가 우리가 원하는 비교를 정확히 수행해준다. 재정의해야 할 때는 그 클래스의 핵심 필드 모두를 빠짐없이, 다섯 가지 규약을 확실히 지켜가며 비교해야한다.




```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

