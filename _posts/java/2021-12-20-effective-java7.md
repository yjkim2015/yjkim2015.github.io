---
title: 다 쓴 객체 참조를 해제하라
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



자바는 메모리를 자동으로 관리해주는 **가비지 컬렉터**를 지원하는 언어이다.

C,C++ 처럼 메모리를 직접 관리해야하는 언어를 쓰다가 자바를 처음 접하는 순간 신세계를 맛 볼것이다. 다 쓴 객체를 알아서 회수해가니까 말이다.

<hr>

<span style="color:red;">허나</span> 그렇다고 해서 메모리  관리에 더 이상 신경 쓰지 않아도 되는 것은 아니다.

그 이유에 대해서 다음의 스택의 예를 통해 알아보자.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div><div style="line-height:130%">12</div><div style="line-height:130%">13</div><div style="line-height:130%">14</div><div style="line-height:130%">15</div><div style="line-height:130%">16</div><div style="line-height:130%">17</div><div style="line-height:130%">18</div><div style="line-height:130%">19</div><div style="line-height:130%">20</div><div style="line-height:130%">21</div><div style="line-height:130%">22</div><div style="line-height:130%">23</div><div style="line-height:130%">24</div><div style="line-height:130%">25</div><div style="line-height:130%">26</div><div style="line-height:130%">27</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;Stack&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;Objects[]&nbsp;elements;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#0099cc">int</span>&nbsp;size&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#308ce5">0</span>;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">static</span>&nbsp;<span style="color:#ff3399">final</span>&nbsp;<span style="color:#0099cc">int</span>&nbsp;DEFAULT_INITIAL_CAPACITY&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#308ce5">16</span>;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;Stack()&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;elements&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;Object(DEFAULT_INITIAL_CAPACITY);</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">void</span>&nbsp;push(Object&nbsp;e)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ensureCapacity();</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;elements[size<span style="color:#0086b3"></span><span style="color:#ff3399">+</span><span style="color:#0086b3"></span><span style="color:#ff3399">+</span>]&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;e;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;Object&nbsp;pop()&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">if</span>&nbsp;(&nbsp;size&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#308ce5">0</span>&nbsp;)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">throw</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;EmptyStackException();&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;elements[<span style="color:#0086b3"></span><span style="color:#ff3399">-</span><span style="color:#0086b3"></span><span style="color:#ff3399">-</span>size];</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">void</span>&nbsp;ensureCapacity()&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">if</span>&nbsp;(&nbsp;elements.<span style="color:#0099cc">length</span>&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span><span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;size&nbsp;)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;elements&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;Arrays.copyOf(elements,&nbsp;<span style="color:#308ce5">2</span>&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">*</span>&nbsp;size&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">+</span>&nbsp;<span style="color:#308ce5">1</span>);&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

위 코드는 일반적으로 널리 알려진 Stack 클래스이다. 

하지만 위 코드에는 꼭꼭 숨어 있는 <span style="color:red;">'메모리 누수'</span>의 문제가 있다.

**이 스택을 사용하는 프로그램을 오래 실행하다보면 점차 가비지 컬렉션 활동과 메모리 사용량이 늘어나 결국 성능이 저하 될 것이다.** 

<hr>

***그렇다면 도대체 어디에서 메모리 누수가 발생할까?***

위 코드에서는 스택이 커졌다가 줄어들었을 때 스택에서 꺼내진 객체들을 가비지 컬렉터가 회수 하지 않는다.

**그 이유는 스택이 그 객체들의 다 쓴 참조(obsolete reference)를 여전히 가지고 있기 때문이다.**

> 다 쓴 참조(obsolete reference)란 문자 그대로 앞으로 다시 쓰지 않을 참조를 뜻하며,
>
> 위 코드에서는 elements 배열의 '활성 영역' 밖의 참조들이 모두 여기에 해당한다.
>
> 활성 영역은 인덱스가 size보다 작은 원소들로 구성된다.

<hr>

가비지 컬렉션 언어에서는 메모리 누수를 찾기가 아주 까다롭다.

**객체 참조 하나를 살려두면 가비지 컬렉터는 그 객체 뿐만이아니라  객체가 참조하는 모든 객체를 연쇄적으로 회수해가지 못한다.**

그 때문에 단 몇개의 객체가 매우 많은 객체를 회수되지 못하게 할 수 있고 잠재적으로 성능에 악영향을 줄 수 있다.

<hr>

위 코드의 해법은 아래와 같다. 해당 참조를 다 썻을 때 null 처리 (참조 해제) 하면 된다.

```
public Object pop() {
	if ( size == 0 ) {
		throw new EmptyStackException();		
	}
	Object result = elements[--size];
	elements[size] = null;
	return result;
}
```

이렇게 다 쓴 참조를 null 처리 하면 다른 이점도 따라온다. 만약 null 처리한 참조를 실수로 사용하려 하면 프로그램은 즉시 NullPointerException을 던지며 종료한다.

<span style="color:red;">하지만, 객체 참조를 null 처리하는 일은 예외적인 경우여야 한다.</span> 다 쓴 참조를 해재하는 가장 좋은 방법은 그 참조를 담은 변수를 유효범위(scope) 밖으로 밀어내는 것이다.

<hr>

#### *그럼 null 처리는 도대체 언제해?*

일반적으로 stack 과 같이 자기 메모리를 직접 관리하는 클래스라면 원소를 다 사용한 즉시 그 원소가 참조한 객체들을 null 처리를 해줘야 해~



## 메모리 누수를 일으키는 주범

* **자기 메모리를 직접 관리하는 클래스**
* **캐시**
  * 객체 참조를 Map과 같은 캐시에 넣고 나서, 객체를 다 쓴 뒤로도 까먹고 한참을 놔두는 경우가 비일비재 하다.  캐시 외부에서 키(key)를 참조하는 동안만 엔트리가 살아 있는 캐시가 필요한 상황이라면 WeakHashMap을 사용해 캐시를 만들자. 다 쓴 엔트리는 그 즉시 자동으로 제거 될 것이다.
* **Listener(리스너) 혹은 Callback(콜백)**
  * 클라이언트가 콜백을 등록만 하고 명확히 조치해주지 않는 한 콜백은 계속 쌓여갈 것이다. 이럴떄 콜백을 약한 참조(week reference)키로 저장하면 카비지 컬렉터가 즉시 수거해간다.



## Java Reference

* **Strong Reference**

  일반적으로 new를 통해서 객체를 생성하게 되면 생기게 되는 참조.

  강한 참조를 통해 참조되고 있는 객체는 가비지 컬렉션의 대상에서 제외된다.

  ```
  SampleObject obj = new SampleObject();
  ```

  위 코드에서 obj 변수가 SampleObject 객체의 참조를 가지고 있는 동안에는 해당 객체는 GC의 대상이 되지 않는다.



* **Soft Reference**

​		강한 참조와는 다르게 GC에 의해 수거될 수도 있고, 수거되지 않을 수도 있다. 메모리에 충분한 여		유가 있다면 GC가 수행되고 있다 하더라도 수거되지 않는다. 하지만 out of memory의 시점에 		가깝다면 수거될 확률이 높다.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div><div style="line-height:130%">12</div><div style="line-height:130%">13</div><div style="line-height:130%">14</div><div style="line-height:130%">15</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">void</span>&nbsp;softReferenceTest()&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;SampleObject&nbsp;obj&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;SampleObject();</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;SoftReference<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span>SampleObject<span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>&nbsp;ref&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;SoftReference<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span><span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>(obj);</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;obj&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#0099cc">null</span>;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#0099cc">System</span>.gc();&nbsp;<span style="color:#999999">//테스트를&nbsp;위해서&nbsp;강제&nbsp;호출</span></div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#999999">//메모리가&nbsp;충분한&nbsp;경우&nbsp;GC의&nbsp;실행&nbsp;대상이&nbsp;되지&nbsp;않음</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#999999">//null&nbsp;이&nbsp;아닌&nbsp;기존의&nbsp;객체가&nbsp;반환</span></div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;obj&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;ref.get();</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#999999">//실행&nbsp;결과는&nbsp;not&nbsp;null이다.</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#0099cc">System</span>.<span style="color:#0099cc">out</span>.<span style="color:#0099cc">println</span>(obj&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span><span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#0099cc">null</span>&nbsp;?&nbsp;<span style="color:#993333">"null"</span>&nbsp;:&nbsp;<span style="color:#993333">"not&nbsp;null"</span>);&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

* **Weak Reference**

  약한 참조는 GC가 발생하면 무조건 수거된다. WeakReference가 사라지는 시점이 GC의 실행 주기와 일치하며 이를 이용하여 짧은 주기에 자주 사용되는 객체를 캐시할 때 유용하다.

  >  (실제로 톰캣 컨테이너의 `ConcurrentCache class`에서 `WeakHashMap`을 사용한다고 한다)

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div><div style="line-height:130%">12</div><div style="line-height:130%">13</div><div style="line-height:130%">14</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">void</span>&nbsp;weakReferenceTest()&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;SampleObject&nbsp;obj&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;SampleObject();</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;WeakReference<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span>SampleObject<span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>&nbsp;ref&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;WeakReference<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span><span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>(obj);</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;obj&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#0099cc">null</span>;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#0099cc">System</span>.gc();&nbsp;<span style="color:#999999">//테스트를&nbsp;위해서&nbsp;강제&nbsp;호출</span></div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#999999">//Weak&nbsp;Reference는&nbsp;GC&nbsp;대상이므로&nbsp;null을&nbsp;반환한다.</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;obj&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;ref.get();</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#999999">//실행&nbsp;결과는&nbsp;null이다.</span></div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#0099cc">System</span>.<span style="color:#0099cc">out</span>.<span style="color:#0099cc">println</span>(obj&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span><span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#0099cc">null</span>&nbsp;?&nbsp;<span style="color:#993333">"null"</span>&nbsp;:&nbsp;<span style="color:#993333">"not&nbsp;null"</span>);&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

* **Phantomly Reference (팬텀 참조) **- 매우 어려움 추후 여러 공부 후에 다시 봐야 할 듯

**Reference Queue**

팬텀 참조를 이해하기 위해서는 `Reference Queue` (설명의 편의를 위해 `RQ`라고 하겠다)에 대해서 이해할 필요가 있다. **SoftReference / WeakReference 객체가 참조하는 객체가 GC 대상이 되면 참조는 `null`이 되고 SoftReference / WeakReference 객체는 `RQ`에 `enqueue` 된다**. `RQ` 에 `enqueue` 하는 작업은 GC에 의해 자동으로 수행된다. `RQ` 에 SoftReference / WeakReference 객체가 `enqueue` 되었다는 것을 확인하면 참조하던 객체가 GC되었는지 확인할 수 있고, 이에 따라 관련된 리소스나 객체에 대한 후처리 작업을 할 수 있다.

<hr>

**SoftReference와 WeakReference는 `RQ` 를 사용할 수도 있고 사용하지 않을 수도 있다.** 이는 생성자 중에서 `RQ`를 인자로 받는 생성자를 사용하느냐 아니냐로 결정한다. <span style="color:red;">그러나 PhantomReference의 생성자는 단 하나이므로 반드시 `RQ`를 사용해야만 한다.</span>

```
SampleObject object = new SampleObject(); 
ReferenceQueue rq = new ReferenceQueue<>(); PhantomReference pr = new PhantomReference<>(object, rq);
```

위에서 언급했듯이 SoftReference, WeakReference는 내부의 참조가 `null`이 된 이후에 `RQ`에 `enqueue` 된다. **하지만 PhantomReference는 <span style="color:red;">내부의 참조를 `null` 로 설정하지 않고</span> 참조된 객체를 phantomly reachable 객체로 만든 뒤에 `RQ`에 `enqueue` 된다.**



<hr>

GC 대상 객체를 처리하는 작업과 할당된 메모리를 회수하는 작업은 연속된 작업이 아니다. 

GC 대상 객체를 처리하는 작업(객체의 `finalize()` 작업)이 이루어진 후에 GC 알고리즘에 따라 할당된 메모리를 회수한다.

<hr>

GC 대상 여부를 결정하는 부분에 관여하는 softly reachable, weakly reachable과는 달리, 

phantomly reachable은 `finalize()`와 메모리 회수 사이에 관여한다. 

PhantomReference로 참조되는 객체는 `finalize()` 된 후에 phantomly reachable로 간주된다. 

즉, 객체에 대한 참조가 PhantomReference만 남게되면 해당 객체는 바로 `finalize()` 된다.

<hr>

GC가 객체를 처리하는 순서는 다음과 같다.

1. soft references
2. weak references
3. 파이널라이즈
4. phantom references
5. 메모리 회수

<hr>

PhantomReference의 `get()` 메서드는 SoftReference, WeakReference와 달리 항상 `null`을 반환한다. 따라서 한 번 phantomly reachable로 판명된 객체는 더 이상 사용될 수 없게 된다. 

그리고 phantomly reachable로 판명된 객체에 대한 참조를 GC가 자동으로 `null`로 설정하지 않으므로, 후처리 작업 후에 사용자 코드에서 명시적으로 `clear()`를 실행하여 `null`로 설정해야 메모리 회수가 진행된다.



> 참조 자료 https://dev-mb.tistory.com/266





> 메모리 누수는 겉으로 잘 드러나지 않아 시스템에 수년간 잠복하는 사례도 있다.
>
> 이런 누수는 철저한 리뷰나 힙 프로파일러 같은 디버깅 도구를 동원해야만 발견되기도 한다. 
>
> 그래서 이런 종류의 문제는 예방법을 익혀두는 것이 중요하다.




```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

