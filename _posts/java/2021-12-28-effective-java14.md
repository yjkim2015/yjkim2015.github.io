---
title: Comparable을 구현할지 고려하라.
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---




#### 🔗 Comparable 인터페이스의 유일무이한 메서드 compareTo

**compareTo는 두가지 성격만 빼면 Object의 equals와 같다.**

**첫번째 다른점**은 <code>compareTo</code>는 단순 동치성 비교에 더해 순서까지 비교할 수 있으며, 제네릭하다는 것이다. 그러기 때문에 **Comparable**을 구현했다는 것은 그 클래스의 인스턴스들에는 자연적인 순서가 있음을 뜻한다. 

그래서 <code>Comparable</code>을 구현한 객체들의 배열은 다음처럼 손쉽게 정렬할 수 있다.

```
Arrays.sort(a);
```

<br>

검색, 극단값 계산, 자동 정렬되는 컬렉션 관리도 역시 쉽게 할 수 있다.

예컨대 다음 프로그램은 명령줄 인수들을 중복은 제거하고 알파벳 순으로 출력한다.

<code>String</code>이 <code>Comparable</code>을 구현한 덕분이다.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">class</span>&nbsp;WordList&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#ff3399">static</span>&nbsp;<span style="color:#ff3399">void</span>&nbsp;main(<span style="color:#0099cc">String</span>[]&nbsp;args)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Set<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span><span style="color:#0099cc">String</span><span style="color:#ff3399">&gt;</span>&nbsp;strSet&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;TreeSet<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span><span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>();</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Collections.addAll(s,&nbsp;args);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#0099cc">System</span>.<span style="color:#0099cc">out</span>.<span style="color:#0099cc">println</span>(s);</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>



<hr> 

💎**compareTo 메서드의 일반 규약은 다음과 같다.** 



> 이 객체와 주어진 객체의 순서를 비교한다. 이 객체가 주어진 객체보다 작으면 음의 정수를,
>
> 같으면 0을, 크면 양의 정수를 반환한다. 이 객체와 비교할 수 없는 타입의 개체가 주어지면 ClassCastException을 던진다.
>
> 다음 설명에서 sgn(표현식) 표기는 수학에서 말하는 부호 함수(signum function)을 뜻하며, 표현식의 값이 음수, 0 , 양수일 때 -1,0,1을 반환하도록 정의했다.
>
> 
>
> * Comparable을 구현한 클래스는 모든 x,y에 대해 sgn(x.compareTo(y)) == -sgn(y.compareTo(x)) 여야 한다(따라서 x.compareTo(y)는 y.compareTo(x)가 예외를 던질 떄에 한해 예외를 던져야 한다.)
> * Comparable을 구현한 클래스는 추이성을 보장해야 한다. 즉, (x.compareTo(y) > 0 && y.compareTo(z) > 0) 이면 x.compareTo(z) < 0 이다.
> * Comparable을 구현한 클래스는 모든 z에 대해 x.compareTo(y) == 0이면 sgn(x.compareTo(z)) == sgn(x.compareTo(z)) == sgn(y.compareTo(z))이다.
> * 이번 권고가 필수는 아니지만 꼭 지키는 게 좋다. (x.compareTo(y) == 0) == (x.equals(y))여야 한다. Comparable을 구현하고 이 권고를 지키지 않는 모든 클래스는 그 사실을 명시해야 한다. 다음과 같이 명시하면 적당할 것이다.
>   "주의 : 이 클래스의 순서는 equals 메소드와 일관되지 않다."



<hr>



**💎뭔가 어디서 본 것 같다. 그렇다 앞에서 본 eqauls규약과 비슷하다.**



**천천히 첫 번째 규약부터 살펴보자.**

<span style="color:red;">첫 번째 규약</span>은 두 객체 참조의 순서를 바꿔 비교해도 예상한 결과가 나와야 한다는 얘기이다. [대칭성]

* ~~내이름은 이효리 거꾸로해도 이효리? 이런 느낌인건가~~

<span style="color:red;">두 번째 규약</span>은 첫 번째가 두 번째보다 크면, 두 번째가 세 번째보다 크면, 첫 번째는 세 번째보다 커야한다는 것이다 [추이성]

<span style="color:red;">세 번째 규약</span>은 크기가 같은 객체들끼리는 어떤 객체와 비교하더라도 항상 같아야 한다는 뜻이다. [반사성]

<span style="color:red;">네 번째 규약</span>은 필수는 아니지만 꼭 지키길 권한다. 간단히 말하면 <code>compareTo</code> 메소드로 수행한 동치성 테스트의 결과가 <code>eqauls</code>와 같아야 한다는 것이다. 이를 잘 지키면 <code>compareTo</code>로 줄지은 순서와 <code>equals</code>의 결과가 일관되게 된다.

* <code>compareTo</code>의 순서와 <code>equals</code>의 결과가 일관되지 않은 클래스도 여전히 동작은 한다. 단, 이 클래스의 객체를 정렬된 컬렉션에 넣으면 해당 컬렉션이 구현한 인터페이스(<code>Collection</code>, <code>Set</code>, 혹은 <code>Map</code>)에 정의된 동작과 엇박자를 낼 것이다. 이 인터페이스들은 <code>eqauls</code> 메서드의 규약을 따르고 있지만, 재미있게도 정렬된 컬렉션들은 동치성을 비교할 때 <code>equals</code> 대신 <code>compareTo</code>를 사용하기 때문이다. 큰 문제는 아니지만 주의해야 한다.



<hr>

**💎 궁금해 compareTo와 equals가 일관되지 않는 예가 있어?**

<code>BigDecimal</code>  클래스를 예로 생각해보자. 빈 <code>HashSet</code> 인스턴스를 생성한 다음 <code>new BigDecimal("1.0")</code>과 <code>new BigDecimal("1.00")</code>를 차례로 추가한다. 이 두 <code>BigDecimal("1.0")</code>은 <code>equals</code> 메소드로 비교하면 서로 다르기 때문에 <code>HashSet</code>은 원소를 2개 갖게 된다.

<span style="color:red;">하지만</span> <code>HashSet</code> 대신 <code>TreeSet</code>을 사용하면 원소를 하나만 갖게 된다. <code>compareTo</code> 메소드로 비교하면 두 <code>BigDecimal</code> 인스턴스가 똑같기 때문이다.



<hr>



#### 🔗 compareTo 메소드 작성 주의 사항

* <code>Comparable</code>은 타입을 인수로 받는 제네릭 인터페이스이므로 <code>compareTo</code> 메서드의 인수타입은 컴파일 타입에 정해진다.
  * 입력 인수의 타입을 확인하거나 형변환 할 필요가 없다는 뜻이다. 

* <code>compareTo</code> 메소드는 각 필드가 동치인지를 비교하는게 아니라 그 순서를 비교한다.
  * 객체 참조 필드를 비교하려면 <code>compareTo</code> 메소드를 재귀적으로 호출한다.
    Comparable을 구현하지 않은 필드나 표준이 아닌 순서로 비교해야 한다면 비교자(Comparator)를 대신 사용한다. 비교자는 직접 만들거나 자바가 제공하는 것을 골라 쓰면 된다.

* 클래스에 핵심 필드가 여러 개라면 어느 것을 먼저 비교하느냐가 중요해진다.
  * 가장 핵심적인 필드부터 비교해나가자. 비교 결과가 0이 아니라면, 즉 순서가 결정되면 거기서 끝이다. 가장 핵심이 되는 필드가 똑같다면, 똑같지 않은 필드를 찾을 때까지 그 다음으로 중요한 필드를 비교해 나간다.  아래의 예시를 보자.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">int</span>&nbsp;compareTo(PhoneNumber&nbsp;pn)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#0099cc">int</span>&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;Short.compare(areaCode,&nbsp;pn.areaCode);&nbsp;<span style="color:#999999">//가장&nbsp;중요한&nbsp;필드</span></div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">if</span>&nbsp;(result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span><span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#308ce5">0</span>)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;Short.compare(prefix,&nbsp;pn.prefix);&nbsp;<span style="color:#999999">//&nbsp;두&nbsp;번째로&nbsp;중요한&nbsp;필드&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">if</span>&nbsp;(result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span><span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#308ce5">0</span>)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;Short.compare(lineNum,&nbsp;pn.lineNum);&nbsp;<span style="color:#999999">//&nbsp;세&nbsp;번째로&nbsp;중요한&nbsp;</span></div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>



**💎  Comparator 인터페이스가 메서드 연쇄 방식으로 비교자를 생성할 수 있게 됬대!! **

자바 8부터는 <code>Comparator</code> 인터페이스가 일련의 비교자 생성 메서드와 팀을 꾸려 메서드 연쇄 방식으로 비교자를 생성할 수 있게 되었다. 그리고 이 비교자들을 <code>Comparable</code> 인터페이스가 원하는 <code>compareTo</code> 메소드를 구현하는데 활용 될 수 있다. 

이 방식은 간결하다. <span style="color:red;">하지만</span> 약간의 성능 저하가 뒤따른다.

<br>

다음은 비교자 생성 메소드를 활용한 비교자 예시이다.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">private</span>&nbsp;<span style="color:#ff3399">static</span>&nbsp;<span style="color:#ff3399">final</span>&nbsp;Comparator<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span>PhoneNumber<span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>&nbsp;COMPARATOR&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;comparingInt((PhoneNumber&nbsp;pn)&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">-</span><span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>&nbsp;pn.areaCode)</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;.thenComparingInt(pn&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">-</span><span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>&nbsp;pn.prefix)</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;.thenComparingInt(pn&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">-</span><span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>&nbsp;pn.lineNum);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">int</span>&nbsp;compareTo(PhoneNumber&nbsp;pn)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;COMPARATOR.compare(<span style="color:#ff3399">this</span>,&nbsp;pn);</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

위 코드는 클래스를 초기화 할 때 다음과 같은 **비교자 생성 메소드**를 2개를 이용해 비교자를 생성한다.

* **comparingInt**
  * 객체 참조를 int 타입 키에 매핑하는 키 추출함수를 인수로 받아, 그 키를 기준으로 순서를 정하는 비교자를 반환하는 정적 메소드이다.
  * 위의 예에서는 람다를 인수로 받으며, 이 람다는 PhoneNumber에서 추출한 areaCode를 기준으로 전화번호의 순서를 정하는 Comparator<PhoneNumber>를 반환한다.
    이 람다에서 입력 인수의 타입을 명시한 점에 주목해야 한다. 자바의 타입 추론 능력이 강력하지 않기때문에 프로그램이 컴파일되도록 개발자가 도운 것이다.

* **thenComparingInt**
  * Comparator의 인스턴스 메소드로, int 키 추출자 함수를 입력 받아 다시 비교자를 반환한다.
  * 이 비교자는 첫 번째 비교자를 적용한 다음 새로 추출한 키로 추가 비교를 수행한다.
  * 원하는 만큼 연달아 호출 할 수 있다.

<hr>

**💎 자바 8부터는 compareTo 메소드에서 관계 연산자 < 와 > 를 추천하지 않는대!!**

자바 7이전에는 <code>compareTo</code> 메소드에서 정수 기본 타입 필드를 비교할때는 관계 연산자인 <와 >를 , 실수 기본 타입 필드를 비교할 때는 정적 메소드인 <code>Double.compare</code>와 <code>Float.compare</code>를 사용하라고 권했다. 

<br>

<span style="color:red;">하지만</span> **자바 7부터는 박싱된 기본 타입 클래스들에 새로 추가된 정적 메소드인 <code>compare</code>를 사용하도록 권장한다.** 이전 방식은 거추장스럽고 오류를 유발하니, 이제는 추천하지 않는다는 것이다.



<hr>



**💎 값의 차를 기준으로 compareTo를 구현하면 안돼!!**

간혹가다가 '값의 차'를 기준으로 첫 번째 값이 두 번째 값보다 작으면 음수를, 두 값이 같으면 0을, 첫 번째 값이 크면 양수를 반환하는 <code>compareTo</code>나 <code>compare</code> 메소드와 마주할 것이다.

솔직히 나도 이 책을 보기전엔 예전에 그런 적 있다...

다음의 예를 보자.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">static</span>&nbsp;Comparator<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span>Object<span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>&nbsp;hashCodeOrder&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;Comparator<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span><span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>()&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">int</span>&nbsp;compare(Object&nbsp;o1,&nbsp;Object&nbsp;o2)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;o1.hashCode()&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">-</span>&nbsp;o2.hashCode();</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

이 방식은 정수 오버플로를 일으키거나 IEEE 754 부동 소수점 계산ㄴ방식에 따른 오류를 낼 수 있으므로 사용하면 안된다. 또한 속도가 빠른것도 아니다.

대신에 다음의 두 방식 중 한가지를 사용하자.



* 정적 compare 메소드를 활용한 비교자

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">static</span>&nbsp;Comparator<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span>Object<span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>&nbsp;hashCodeOrder&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;Comparator<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span><span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>()&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">int</span>&nbsp;compare(Object&nbsp;o1,&nbsp;Object&nbsp;o2)&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;Integer.compare(o1.hashCode(),&nbsp;o2.hashCode());</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

* 비교자 생성 메소드를 활용한 비교자

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">static</span>&nbsp;Comparator<span style="color:#0086b3"></span><span style="color:#ff3399">&lt;</span>Object<span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>&nbsp;hashCodeOrder&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;Comparator.comparingInt(o&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">-</span><span style="color:#0086b3"></span><span style="color:#ff3399">&gt;</span>&nbsp;o.hashCode());</div></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>



> 순서를 고려해야 하는 값 클래스를 작성한다면 꼭 Comparable 인터페이스를 구현하여, 그 인스턴스들을 쉽게 정렬하고, 검색하고, 비교 기능을 제공하는 컬렉션과 어우러지도록 해야 한다.
> compareTo 메소드에서 필드의 값을 비교할 때 < 와 > 연산자는 쓰지 말아야 한다.
> 그 대신 박싱된 기본 타입 클래스가 제공하는 정적 compare 메소드나 Comparator 인터페이스가 제공하는 비교자 생성 메소드를 사용하자.



```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

