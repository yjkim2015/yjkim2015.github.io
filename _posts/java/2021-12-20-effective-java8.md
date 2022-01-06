---
title: finalizer와 cleaner 사용을 피하라 - Effective Java[8]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---

자바는 아래와 같이 두 가지 객체 소멸자를 제공한다.

* **finalizer**
  * 예측 할 수 없고, 상황에 따라 위험할 수 있어 일반적으로 불필요하다.
  * 나름의 쓰임새가 몇 가지 있긴 하지만 기본적으로 쓰지말아야 하며, 자바 9에서는 deprecated 로 지정 되었다. (but 여전히 사용하고 있긴함)

* **cleaner**
  * finalizer보다는 덜 위험하지만, 여전히 예측할 수 없고, 느리고, 일반적으로 불필요하다

<hr>

자바의 finalizer와 cleaner는 C++의 파괴자(destructor) 와는 다른 개념이다.

C++에서의 파괴자는 특정 객체와 관련된 자원을 회수하는 보편적인 방법이다.

***자바에서는 접근할 수 없게 된 객체를 회수하는 역할을 가비지 컬렉터가  담당하고 비메모리 자원을 회수할 때는 try-with-resources와 try-finally를 사용해 해결한다.***

<hr>

#### finalizer와 cleaner는 즉시 수행된다는 보장이 없다.

객체에 접근 할 수 없게 된 후 finalizer나 cleaner가 실행되기까지 얼마나 걸릴지 알 수 없다.

**즉, finalizer와 cleaner로는 제때 실행되어야 하는 작업은 절대 할 수 없다는 말이다.**



> 예를 들어 파일 닫기를 finalizer나 cleaner에게 맡기면 중대한 오류가 발생할 수 있다. 
>
> 시스템이 동시에 열 수 있는 파일 개수에 한계가 있기 때문이다.
>
> finalizer나 cleaner를 얼마나 신속하게 실행될지는 전적으로 가비지 컬렉터 알고리즘에 달렸으며 가비지 컬렉터 구현 마다 천차만별이다

<hr>

자바 언어 명세는 finalizer나 clenear의 수행 시점 뿐 아니라 수행 여부조차 보장 하지 않는다.

***따라서 프로그램 생애주기와 상관없는, 상태를 영구적으로 수정하는 작업에서는 절대!!! finalizer나 cleaner에 의존하면 안된다.***

> 예를들어 데이터 베이스 같은 공유 자원의 영구 락(lock) 해제를 finalizer나 cleaner에 맡겨 놓으면 분산 시스템 전체가 서서히 멈출 것이다.



<hr>

#### System.gc나 System.runFinalization 메소드에 현혹되지 말자.

finalizer와 cleaner가 실행될 가능성을 높여줄 수는 있으나, 보장해주진 않는다. 

사실 이를 보장해주겠다는 메서드가 2개 있었으니, 바로 System.runFinalizersOnExit와 그 쌍둥이인 Runtime.runFinalizersOnExit다.  하지만 이 두 메소드는 심각한 결함 때문에 수십년간 지탄받아 왔다.

<hr>

#### finalizer 동작 중 발생한 예외는 무시되며, 처리할 작업이 남았더라도 그 순간 종료된다.

잡지 못한 예외 때문에 해당 객체는 자칫 마무리가 된 상태로 남을 수 있다. 그리고 다른 스레드가 이처럼 훼손된 객체를 사용하려 한다면 어떻게 동작할지 예측할 수 없다. 경고조차 출력하지 않기 때문이다.

그나마 cleaner를 사용하는 라이브러리는 자신의 스레드를 통제하기 때문에 이러한 문제가 발생하진 않는다.



**이쯤 되면 끝났지 싶나? ㅎㅎ 생각보다 그들은 대단한 Ten Birds이다.**

**아직 더 많은 문제가 남아있다. 살펴보자**

<hr>

#### finalizer와 cleaner는 심각한 성능 문제도 동반한다.

finalizer의 성능을 비교하기 위해  (try-with-resources 방식으로) 간단한 AutoCloseable 객체를 생성하고 가비지 컬렉터가 수거하기 까지 약 12ns가 걸린 반면 finalizer를 사용하면 550ns가 걸렸다.

다시 말하면 finalizer를 사용한 객체를 생성하고 파괴하니 50배가 느렸다. finalizer가 가비지 컬렉터의 효율을 떨어뜨리기 때문이다. cleaner도 클래스의 모든 인스턴스를 수거하는 형태로 사용하면 성능은 finalizer와 비슷하게 암울하다.

<hr>

#### finalizer를 사용한 클래스는 finalizer 공격에 노출되어 심각한 보안 문제를 일으킬 수 있다.

**생성자나 직렬화 과정에서 예외가 발생하면, 이 생성 되다 만 객체에서 악의적인 하위 클래스의 finalizer가 수행 될 수 있게하는게 finalizer의 공격 원리이다.**

이 finalizer는 정적 필드에 자신의 참조를 할당하여 가비지 컬렉터가 수집하지 못하게 막을 수 있다.

이렇게 일그러진 객체가 만들어지고 나면, 이 객체의 메서드를 호출해 애초에는 허용되지 않았을 작업을 수행하는건 일도 아니다.



**final 클래스들은 그 누구도 하위 클래스를 만들 수 없으니 이 공격에서 안전하지만, final이 아닌 클래스를 finalizer 공격으로부터 방어하려면 아무 일도 하지 않는 finalize 메소드를 만들고 final로 선언해야한다.**

<hr>

#### finalizer와 cleaner 도대체 왜 만든거야? 어디 쓰이는 거야?

이쯤이면 이 ~~절망적인~~ 수준의 물건들이 어디서 쓰이는지 궁금해진다.

적절한 쓰임새가 (아마도) 아래와 같이 두 가지가 있다고 한다.ㅋㅋㅋㅋ

* **자원의 소유자가 close 메소드를 호출하지 않는 것에 안전망 역할이다.**
  * finalizer와 cleaner가 즉시 호출되리라는 보장은 없지만, 클라이언트가 하지 않은 자원 회수를 늦게라도 해주는것이 안하는 것보다는 낫다는 이론이다. [글쎄... 그럴만한 값어치가 있을까..?]
  * 안정망 역할의 finalizer를 제공하는 자바 라이브러리 중 일부 클래스 [FileInputStream, FileOutputStream, ThreadPoolExecutor]

* **네이티브 피어(native peer)와 연결된 객체에서이다.**
  * 네이티브 피어란 일반 자바 객체가 네이티브 메서드를 통해 기능을 위임한 네이티브 객체를 말한다.
  * 네이티브 피어는 자바 객체가 아니니 가비지 컬렉터는 그존재를 모른다. 때문에, 자바 피어를 회수 할 때 네이티브 객체까지 회수하지 못한다. cleaner나 finalizer가 나서서 처리하기에 적당한 작업이다.
  * 단, 성능 저하를 감당할 수 있고 네이티브 피어가 심각한 자원을 가지고 있지 않을 때에만 해당된다.
  * 즉시 회수를 위해서는 close 메소드를 실행하라.



<hr>

#### 아니 이정도면 대안이 있겠지? 그럼 대안이 뭐야?

***대안은 의외로 간단하다. 그저 AutoCloseable을 구현해주고 , 클라이언트에서 인스턴스를 다 쓰고나면 close 메소드를 호출하면 된다.  (일반적으로는 예외가 발생해도 제대로 종료 되도록 try-with-resources를 사용해야 한다.)***

알아둬야 할 팁은 close 메소드에서 이 객체는 더 이상 유효하지 않음을 필드에 기록하고, 다른 메서드는 이 필드를 검사해서 객체가 닫힌  후에 불렸다면 IllegalStateException을 던지는 것이다.

<hr>

 아래의 예제를 통해 cleaner의 안전망으로서의 쓰임과 예측할 수 없는 상황을 살펴보자.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div><div style="line-height:130%">12</div><div style="line-height:130%">13</div><div style="line-height:130%">14</div><div style="line-height:130%">15</div><div style="line-height:130%">16</div><div style="line-height:130%">17</div><div style="line-height:130%">18</div><div style="line-height:130%">19</div><div style="line-height:130%">20</div><div style="line-height:130%">21</div><div style="line-height:130%">22</div><div style="line-height:130%">23</div><div style="line-height:130%">24</div><div style="line-height:130%">25</div><div style="line-height:130%">26</div><div style="line-height:130%">27</div><div style="line-height:130%">28</div><div style="line-height:130%">29</div><div style="line-height:130%">30</div><div style="line-height:130%">31</div><div style="line-height:130%">32</div><div style="line-height:130%">33</div><div style="line-height:130%">34</div><div style="line-height:130%">35</div><div style="line-height:130%">36</div><div style="line-height:130%">37</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;Room&nbsp;<span style="color:#ff3399">implements</span>&nbsp;AutoCloseable&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">static</span>&nbsp;<span style="color:#ff3399">final</span>&nbsp;Cleaner&nbsp;cleaner&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;Cleaner.create();</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#999999">//청소한&nbsp;필요한&nbsp;자원.&nbsp;절대&nbsp;Room을&nbsp;참조해서는&nbsp;안된다.</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">static</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;State&nbsp;<span style="color:#ff3399">implements</span>&nbsp;Runnable&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#0099cc">int</span>&nbsp;numJunkPiles;&nbsp;<span style="color:#999999">//방(Room)&nbsp;안의&nbsp;쓰레기&nbsp;수</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;State(<span style="color:#0099cc">int</span>&nbsp;numJunkPiles)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">this</span>.numJunkPiles&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;numJunkPiles;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#999999">//close&nbsp;메소드나&nbsp;cleaner가&nbsp;호출한다.&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;@Override</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">void</span>&nbsp;run()&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#0099cc">System</span>.<span style="color:#0099cc">out</span>.<span style="color:#0099cc">println</span>(<span style="color:#993333">"room&nbsp;clear"</span>);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;numJunkPiles&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#308ce5">0</span>;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#999999">//방의&nbsp;상태</span></div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">final</span>&nbsp;State&nbsp;state;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#999999">//cleanable&nbsp;객체.&nbsp;수거대상이&nbsp;되면&nbsp;방을&nbsp;</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">final</span>&nbsp;Cleaner.Cleanable&nbsp;cleanable;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;Room(<span style="color:#0099cc">int</span>&nbsp;numJunkPiles)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">this</span>.state&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;State(numJunkPiles);</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cleanable&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;cleaner.register(<span style="color:#ff3399">this</span>,state);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;@Override</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">void</span>&nbsp;close()&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;cleanable.clean();</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

위 코드에서 State는 Runnable을 구현하고, 그 안의 run 메소드는 cleanable에 의해 딱 한 번만 호출될 것이다.

run 메소드가 호출 되는 상황은 둘 중 하나인데, 보통은 Room의 close메소드를 호출할 때이다.

close 메소드에서 Cleanable 의 clean 을 호출하면 이 메서드 안에서 run을 호출한다. 혹은 가비지 컬렉터가 Room을 회수 할 때까지 클라이언트가 close를 호출하지 않는다면, cleaner가 state의 run 메소드를 호출해 줄것이다(언젠가).

<hr>

여기서 중요한 점은 State가 정적 중첩클래스 인 이유가 여기에 있는데, 정적이 아닌 중첩 클래스는 자동으로 바깥 객체의 참조를 갖게 되고, 바깥 Room 인스턴스를 참조 할 경우 순환 참조가 생겨 가비지 컬렉터가 Room 인스턴스를 회수 해갈 기회가 오지 않는다.



자 이제 안전망으로 쓰이는 방법에 대해 살펴볼 것이다.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;Adult&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">static</span>&nbsp;<span style="color:#ff3399">void</span>&nbsp;main(<span style="color:#0099cc">String</span>[]&nbsp;args)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">try</span>&nbsp;(&nbsp;Room&nbsp;room&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;Room(<span style="color:#308ce5">7</span>))&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#0099cc">System</span>.<span style="color:#0099cc">out</span>.<span style="color:#0099cc">println</span>(<span style="color:#993333">"청소가즈아"</span>);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

클라이언트가 모든 Room 생성으로 try-with-resource 블록으로 감쌌기 때문에 자동 닫힘 AutoCloseable의 close가 호출되어서, 청소가즈아 출력 후 , 방 청소가 출력된다.



다음으로는 예측할 수 없는 상황을 보자.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;Teenager&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">static</span>&nbsp;<span style="color:#ff3399">void</span>&nbsp;main(<span style="color:#0099cc">String</span>[]&nbsp;args)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">new</span>&nbsp;Room(<span style="color:#308ce5">9</span>);</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#0099cc">System</span>.<span style="color:#0099cc">out</span>.<span style="color:#0099cc">println</span>(<span style="color:#993333">"청소가즈아아"</span>);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

위 코드가 바로 Cleaner에 언제 닫히지? 예측 할 수 없는 상황이다. 청소 가즈아아 다음에 방 청소가 출력이 언제 될지는 아무도 모른다.



> cleaner의 명세에는 이렇게 작성되있다.  System.exit를 호출할 때의 cleaner 동작은 구현하기 나름이다. 청소가 이뤄질지는 보장하지 않는다.
>
> cleaner(자바 8까지는 finalizer)는 안전망 역할이나 중요하지 않은 네이티브 자원회수용으로만 사용하다.
>
> 물론 이런 경우라도 불확실성과 성능하에 주의해야한다.




```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

