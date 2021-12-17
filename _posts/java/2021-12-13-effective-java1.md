---
title: 생성자 대신 정적 팩토리 메소드를 고려하라
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



클래스는 클라이언트에 public 생성자 대신 (혹은 생성자와 함께)  그 클래스의 인스턴스를 반환하는 단순한 **정적 팩토리 메서드**를 제공할 수 있다. 

다음 코드는 boolean 기본 타입의 박싱 클래스(boxed class)인 Boolean에서 발췌한 간단한 예이다.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">static</span>&nbsp;Boolean&nbsp;<span style="color:#0099cc">valueOf</span>(<span style="color:#0099cc">boolean</span>&nbsp;b)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;b&nbsp;?&nbsp;Boolean.TRUE&nbsp;:&nbsp;Boolean.FALSE;</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

위 메서드는 기본 타입인 boolean 값을 받아 Boolean 객체 참조로 변환해 준다.



여기서의 정적 팩토리 메서드란 디자인 패턴에서의 팩토리 메소드와는 다르다.

이 방식에는 <span style="color:red;">장점과 단점</span>이 모두 존재하는데 **먼저 장점에 대해 알아보자.**

## Step 1 : 이름을 가질 수 있다.

생성자에 넘기는 매개변수와 생성자 자체만으로는 반환될 객체의 특성을 제대로 설명하지 못한다.

반면 정적 팩토리는 이름만 잘 지으면 반환될 객체의 특성을 쉽게 묘사할 수 있다.

**예를들어 생성자인 BigInteger(int, int, Random)과 정적 팩토리 메서드인 BigInteger.probablePrime 중 어느 쪽이 '값이 소수인 BigInteger를 반환한다.' 는 의미인지 생각하보자.**

**아마 모든사람들이 후자라고 생각할 것이다.**



한 클래스에 <span style="color:red;">시그니처(메소드명, 파라미터 수, 파라미터 타입의 순서) </span>가 같은 생성자가 여러개 필요할 것 같으면, 생성자를 정적 팩토리 메소드로 바꾸고 각각의 차이를 잘 드러내는 이름을 지어주는게 좋다.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div><div style="line-height:130%">12</div><div style="line-height:130%">13</div><div style="line-height:130%">14</div><div style="line-height:130%">15</div><div style="line-height:130%">16</div><div style="line-height:130%">17</div><div style="line-height:130%">18</div><div style="line-height:130%">19</div><div style="line-height:130%">20</div><div style="line-height:130%">21</div><div style="line-height:130%">22</div><div style="line-height:130%">23</div><div style="line-height:130%">24</div><div style="line-height:130%">25</div><div style="line-height:130%">26</div><div style="line-height:130%">27</div><div style="line-height:130%">28</div><div style="line-height:130%">29</div><div style="line-height:130%">30</div><div style="line-height:130%">31</div><div style="line-height:130%">32</div><div style="line-height:130%">33</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">package</span>&nbsp;Item01;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;Car&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#0099cc">String</span>&nbsp;name;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#0099cc">String</span>&nbsp;engine;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;Car()&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#999999">//오류</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#999999">//하나의&nbsp;시그니처로는&nbsp;&nbsp;생성자를&nbsp;하나만&nbsp;만들&nbsp;수&nbsp;있다.</span></div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;Car(<span style="color:#0099cc">String</span>&nbsp;name)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">this</span>.name&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;name;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;Car(<span style="color:#0099cc">String</span>&nbsp;engine)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">this</span>.engine&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;engine;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#999999">//아래의&nbsp;정적&nbsp;팩토리&nbsp;메소드들은&nbsp;오류가&nbsp;없이&nbsp;가능하다.</span></div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;Car&nbsp;getCar(<span style="color:#0099cc">String</span>&nbsp;name)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Car&nbsp;car&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;Car();</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;car.name&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;name;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;car;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;Car&nbsp;getEngine(<span style="color:#0099cc">String</span>&nbsp;engine)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Car&nbsp;car&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;Car();</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;car.engine&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;engine;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;car;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>



## Step 2 : 호출될 때마다 인스턴스를 생성하지는 않아도 된다.

위에서 언급한 Boolean.valueOf(boolean) 메서드가 대표적인 예로서 객체를 아예 생성하지 않는다.

인스턴스를 미리 만들어 놓거나 새로 생성한 인스턴스를 캐싱하여 재활용하는 식으로 불필요한 객체 생성을 피할 수 있다. 

반복되는 요청에 같은 객체를 반환하는 식으로 정적 팩토리 방식의 클래스는 언제 어느 인스턴스를 살아 있게 할지를 철저히 통제 할 수 있는데, 이러한 클래스를 **인스턴스 통제(instance-controlled) 클래스**라 한다.

<hr>

***그렇다면 왜 인스턴스를 통제할까?***  사실 아래의 내용은 4줄이지만 한줄의 의미와 같다고 본다..

* 싱글톤 클래스로 만들 수 있다.



* 인스턴스화 불가로 만들 수 있다.



* 불변 값 클래스에서 동치인 인스턴스가 하나임을 보장 할 수 있다.



* 인스턴스 통제는 플라이웨이트 패턴의 근간이 되며, 열거 타입은 인스턴스가 하나만 만들어 짐을 보장한다.





## Step 3 : 반환 타입의 하위 타입 객체를 반환 할 수 있는 능력이 있다.

**정적 팩토리 메소드는 반환할 객체의 클래스를 자유롭게 선택할 수 있게 하는 '엄청난 유연성'을 선물한다.**

<span style="color:red;">(리턴 타입의 상속을 받은 모든 클래스 가능) 즉, 인터페이스로부터 정적 팩토리 메서드를 구현하여 다형성을 가진 객체를 제공해 줄 수 있다.</span>

<hr>

API를 만들 때 이 유연성을 응용하면 구현 클래스를 공개하지 않고도 그 객체를 반환 할 수 있어 API를 작게 유지할 수 있다.  이는 인터페이스를 정적 팩토리 메서드의 반환 타입으로 사용하는 인터페이스 기반 프레임워크(컬렉션) 을 만드는 핵심 기술이기도 하다.



컬렉션 프레임워크는 핵심 인터페이스들의 핵심 인터페이스에 수정 불가나 동기화 등의 기능을 덧붙인 유틸리티를 제공하는데, 이 구현체 대부분을 단 하나의 인스턴스화 불가 클래스인 java.util.Collections에서 정적 팩토리 메서드를 통해 얻도록 했다.



## Step 4: 입력 매개변수에 따라 매번 다른 클래스의 객체를 반환 할 수 있다. 

step1에서  우리는 시그니처에 따라 내용이 다른 인스턴스를 제공 할 수 있다는 것을 확인했다.

<span style="color:red;">하지만 시그니처에 따라 다른 클래스(하위클래스)의 인스턴스도 제공 할 수 있다.</span>

반환 타입의 하위 타입이기만 하면 어떤 클래스의 객체를 반환하든 상관없다.

클라이언트는 정적 팩토리 메소드가 건네주는 객체가 어느 클래스의 인스턴스인지 알 수도 없고 알 필요도 없다.

<hr>

아래의 예제에서 RentCar와 NormarCar는 모두 Car의 하위 타입이다.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div><div style="line-height:130%">12</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;Car&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">static</span>&nbsp;Car&nbsp;getCarByType(<span style="color:#0099cc">String</span>&nbsp;type)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">if</span>&nbsp;(&nbsp;type.<span style="color:#0099cc">equals</span>(<span style="color:#993333">"Rent"</span>)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;RentCar();</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">else</span>&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;NormalCar();</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>



## Step 5: 정적 팩토리 메소드를 작성하는 시점에는 반환 할 객체의 클래스가 존재하지 않아도 된다.

<span style="color:red;">인터페이스나 클래스가 만들어지는 시점에 하위 타입의 클래스가 존재하지 않아도 나중에 만들 클래스가 기존의 인터페이스나 클래스를 상속 받으면 언제든지 의존성을 주입받아서 사용이 가능하다. </span>

**반환 값이 인터페이스가 되며 정적 팩토리 메서드의 변경 없이 구현체를 바꿔 끼울 수 있다.**

<hr>

아래의 예제에서 Owner는 인터페이스이지만 구현체는 존재하지 않음에도 불구하고, 

반환 값에 인터페이스인 ArrayList인 바꿀 수 있다.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;Car&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">static</span>&nbsp;List<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span>Owner<span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>&nbsp;getOwners()&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;ArrayList<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span><span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>();</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>



이런 유연함은 **서비스 제공자 프레임워크 (service provider framework)**를 만드는 근간이 되는데, 

**대표적인 서비스 제공자 프레임워크로는 JDBC (Java Database Connectivity)가 있다.**



***서비스 제공자 프레임워크란***

> *다양한 서비스 제공자들이 하나의 서비스를 구성하는 시스템으로 클라이언트가 실제 구현된 서비스를 이용할 수 있도록 하는데, 클라이언트는 세부적인 구현은 몰라도 서비스를 이용할 수 있다. JDBC의 경우 mysql, oracle등의 서비스 제공자들이 JDBC라는 하나의 서비스를 구성한다.*



서비스 제공자 프레임워크 구성

* <span style="color:red;">서비스 인터페이스</span>: 구현체의 동작을 정의
* <span style="color:red;">제공자 등록 API</span> : 제공자가 구현체를 등록할 때 사용
* <span style="color:red;">서비스 접근 API</span> : **클라이언트가 서비스의 인스턴스를 얻을 때 사용**. 클라이언트는 원하는 구현체의 조건을 명시할 수 있다. 이 서비스 접근 API가 서비스 제공자 프레임 워크의 근간이라고 한 **'유연한 정적 팩토리'**의 실체이다.
* <span style="color:red;">서비스 제공자 인터페이스</span>: 서비스 인터페이스의 인스턴스를 생성하는 팩토리 객체를 말한다.



**이제 단점에 대해 알아보자.**

## Step 6 : 상속을 하려면 public이나 protected 생성자가 필요하니 정적 팩토리 메소드만 제공하면 하위 클래스를 만들 수 없다.

상속을 하기 위해서는 생성자가 필요없더라도 필수적으로 필요하다.

정적 팩토리 메소드만 제공하게 되면 상속보다는 컴포지션(합성) 사용을 유도 할 수 있고 불변 클래스로 만들기 위해 해당 제약을 지켜야한다는 점에서는 장점으로 받아들일 수 있다.



## Step 7 : 정적 팩토리 메서드는 프로그래머가 찾기 힘들다.

생성자처럼 API 설명에 명확히 드러나지 않으니 사용자는 정적 팩토리 메서드 방식 클래스를 인스턴스화 할 방법을 알아내야 한다.



<hr>

**다음은 정적 팩토리 메서드에 흔히 사용되는 명명 방식들이다.**

* **from : 매개 변수를 하나 받아서 해당 타입의 인스턴스를 반환하는 형변환 메서드**

  ```
  예) Date d = Date.from(instant);
  ```

* **of : 여러 매개변수를 받아 적합한 타입의 인스턴스를 반환하는 집계 메서드**

  ```
  예) Set<Rank> faceCards = EnumSet.of(JACK, QUEEN, KING);
  ```

* **valueOf : from과 of의 더 자세한 버전**

  ```
  예) BigInteger prime = BigInteger.valueOf(Integer.MAX_VALUE);
  ```

* **instance || getInstance : 매개변수로 명시한 인스턴스를 반환하지만, 같은 인스턴스임을 보장하지는 않는다.**

  ```
  예) StackWalker luke = StackWalker.getInstance(options);
  ```

* **create 혹은 newInstance : instance 혹은 getInstance와 같지만, 매번 새로운 인스턴스를 생성해 반환함을 보장한다.**

  ```
  예) Object newArray = Array.newInstance(classObject, arrayLen);
  ```

  **getType : getInstance와 같으나, 생성할 클래스가 아닌 다른 클래스에 팩토리 메소드를 정의할 때 사용한다.**

* ```
  예) FileStore fs = Files.getFileStore(path);
  ```

* **newType : newInstance와 같으나, 생성할 클래스가 아닌 다른 클래스에 팩토리 메소드를 정의할 때 사용한다.** 

  ```
  예) BufferedReader br = Files.newBufferedReader(path);
  ```

  **type : getType과 newType의 간결한 버전**

* ```
  예) List<Complaint> litany = Collections.list(legacyLitany);
  ```

<hr>

> 정리하자면, 정적 팩토리 메소드와 public 생성자는 각자의 쓰임새가 있으니 상대적인 장단점을 이해하고 사용하는 것이 좋다. 그렇다고 하더라도 정적 팩토리 메소드를 사용하는게 유리한 경우가 더 많으므로 무작정 public 생성자를 제공하던 습관이 있다면 고쳐야한다.




```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

