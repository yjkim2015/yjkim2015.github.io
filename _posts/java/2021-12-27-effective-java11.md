---
title: equals를 재정의하려거든 hashCode도 재정의하라. - Effective Java[11]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---

#### 🔗 <code>equals</code>를 재정의한 클래스 모두에서 <code>hashCode</code>로 재정의해야 한다.

그렇지않으면 <code>hashCode</code> 일반 규약을 어기게 되어 해당 클래스의 인스턴스를 <code>HashMap</code>이나 <code>HashSet</code> 같은 컬렉션의 원소로 사용할 때 문제를 일으킬 것이다.

<hr>

다음은 Object 명세에서 발췌한 규약이다.

> * equals 비교에 사용되는 정보가 변경되지 않았다면, 애플리케이션이 실행되는 동안 그 객체의 hashCode 메소드는 몇 번을 호출해도 일관되게 항상 같은 값을 반환해야 한다.
>
>   단, 애플리케이션을 다시 실행한다면 이 값이 달라져도 상관없다.
>
> * equals(Object)가 두 객체를 같다고 판단했다면, 두 객체의 hashCode는 똑같은 값을 반환해야 한다.
>
> * equals(Object)가 두 객체를 다르다고 판단했더라도, 두 객체의 hashCode가 서로 다른 값을 반환할 필요는 없다. 단, 다른 객체에 대해서는 다른 값을 반환해야 해시테이블의 성능이 좋아진다.

<hr>

위 규약에서 <code>hashCode</code> 재정의를 잘못했을 때 크게 문제가 되는 조항은 두 번째이다.

**즉, 논리적으로 같은 객체는 같은 해시코드를 반환해야 한다**.

우리는 앞선 블로깅에서 <code>equals</code>는 물리적으로 다른 두 객체를 논리적으로 같다고 할 수 있다는것을 보았다.

**<span style="color:red;">하지만</span> Object의 기본 hashCode 메소드는 이 둘이 전혀 다르다고 판단하여, 규약과 달리 서로 다른값을 반환한다.**

<hr>

아래의 예시를 보자. [**hashCode 재정의가 안되었다고 가정**]

```
Map<PhoneNumber, String> phoneMap = new HashMap<>();
phoneMap.put(new PhoneNumber(707,867,5309), "제니");
System.out.println(phoneMap.get(new PhoneNumber(707,867,5309)).equals("제니"));
```

위 코드에서 phoneMap.get(new PhoneNumber(707,867,5309))의 결과 값이 "제니"가 나와야 할 것 처럼 보이나, 실제로는 null을 반환한다.

여기에는 2개의 PhoneNumber 인스턴스가 사용이 되었는데, 하나는 HashMap에 "제니"를 넣을 때 사용됐고, 또 하나는 이를 꺼내려할 때 사용되었다.

<hr>
**PhoneNumber 클래스는 hashCode를 재정의 하지 않았기 때문에 논리적 동치인 두 객체가 서로 다른 해시 코드를 반환하여 두 번째 규약을 지키지 못한다.** 

그 결과로 get 메서드는 엉뚱한 해시 버킷에 가서 객체를 찾으려 한 것이다. 

만약 두 인스턴스가 같은 버킷에 담겨있더라도 <code>get</code> 메서드는 여전히 <code>null</code>을 반환하는데, 그 이유는 <code>hashMap</code>은 해시코드가 다른 엔트리끼리는 동치성 비교를 시도조차 하지 않도록 설계되어 있기 때문이다.

<hr>

#### 🔗 최악의 해시 코드 구현?

아래의 코드는 최악의 코드라 불리는 절대 사용해서는 안되는 해시코드 구현법이다.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%">@Override</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">int</span>&nbsp;hashCode()&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;<span style="color:#308ce5">42</span>;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

이 코드는 동치인 모든 객체에게 똑같은 해시코드를 반환하니 적법하다. 하지만 모든 객체에게 똑같은 값만 내어주므로 모든 객체가 해시 테이블의 버킷 하나에 담겨 마치 연결리스트처럼 동작한다.

그 결과 평균 수행시간이 O(1)인 해시테이블이 O(n)으로 느려져서, 객체가 많아지면 도저히 쓸 수 없게 된다.

<hr>

#### 🔗 올바른 해시 코드 메소드 작성법은 어떻게?

다음은 좋은 hashCode를 작성하는 간단한 요령이다.

1. **int 변수 <code>result</code>를 선언한 후 값을 c로 초기화한다.**
   *  이때 c는 해당 객체의 첫번째 핵심 필드를 **2.1**방식으로 계산한 해시코드이다

2. **해당 객체의 나머지 핵심 필드인 <code>f</code> 각각에 대해 다음 작업을 수행한다.**
   1. 해당 필드의 해시 코드 <code>c</code>를 계산한다.
      * 기본 타입 필드라면, <code>Type.hashCode(f)</code>를 수행한다. 여기서 Type은 해당 기본 타입의 박싱 크래스이다.
      * 참조 타입 필드면서 이 클래스의 <code>equals</code> 메서드가 이 필드의 <code>equals</code>를 재귀적으로 호출해 비교한다면, 이 필드의 <code>hashCode</code>를 재귀적으로 호출한다. 
      * 필드가 배열이라면, 핵심 원소 각각을 별도 필드처럼 다룬다. 
        모든 원소가 핵심 원소라면 <code>Arrays.hashCode</code>를 사용한다.
   2.  단계 2.1에서 계산한 해시코드 c로 <code>result</code>를 갱신한다.
      * <code>result</code> = 31 * <code>result</code> + c;
3.  **<code>result</code>를 반환한다.**

<br>

단계 2.2 의 곱셈 31 * result는 필드를 곱하는 순서에 따라 result 값이 크게 달라지게 한다.

***그 결과로 클래스에 비슷한 필드가 여러 개 일때 해시 효과를 크게 높여준다.***

곱할 숫자를 31로 정한 이유는 31이 홀수이면서 소수이기 때문이다. 만약 이 숫자가 짝수이고 

오버플로가 발생한다면 정보를 잃게 된다.

2를 곱하는 것은 시프트 연산과 같은 결과를 내기 때문이다.



<hr>

#### 💎전형적인 HashCode 메소드

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%">@Override</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">int</span>&nbsp;hashCode()&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#0099cc">int</span>&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;Short.hashCode(areaCode);</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#308ce5">31</span>&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">*</span>&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">+</span>&nbsp;Short.hashCode(prefix);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#308ce5">31</span>&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">*</span>&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">+</span>&nbsp;Short.hashCode(lineNum);</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;result;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

이 메서드는 PhoneNumber 인스턴스의 핵심 필드 3개만을 사용해 간단한 계산만 수행하는데 그 과정에 비결정적 요소는 전혀 없으므로 동치인 PhoneNumber 인스턴스들은 같은 해시코드를 가질 것이 확실하다.

<hr>

#### 💎Objects 클래스의 hashCode 메소드

**Objects 클래스는 아래와 같이 임의의 개수만큼 객체를 받아 해시코드를 계산해주는 정적 메소드인 hash를 제공한다.**

<span style="color:red;">하지만 아쉽게도 속도가 느리다</span>

[입력 인수를 담기 위한 배열이 만들어지고, 입력 중 기본 타입이 있다면 박싱과 언박싱도 거쳐야 하기 때문]

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%">@Override</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">int</span>&nbsp;hashCode()&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;Objects.hash(lineNum,&nbsp;prefix,&nbsp;areaCode);</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

그러니까 위 hash 메소드는 성능에 민감하지 않은 상황에서만 사용하자.



<hr>

#### 💎해시코드를 지연 초기화하는 hashCode 메소드

**클래스가 불변이고 해시코드를 계산하는 비용이 크다면, 매번 새로 계산하기 보다는 캐싱한는 방식을 고려해야 한다. 이 타입의 객체가 주로 해시의 키로 사용될 것 같다면 인스턴스가 만들어질 때 해시코드를 계산해둬야 한다.** 

해시의 키로 사용되지 않는 경우라면 hashCode가 처음 불릴 때 계산하는 **<span style="color:red;">지연 초기화 전략</span>**에 대해 고려해보자.

필드를 지연 초기화하려면 그 클래스를 스레드 세이프 하게 만들도록 신경 써야한다.

아래의 예시를 보자. 

**유념해야 할 것은 hashCode 필드의 초깃값은 흔히 생성되는 객체의 해시코드와는 달라야 한다는 것이다.**

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div><div style="line-height:130%">12</div><div style="line-height:130%">13</div><div style="line-height:130%">14</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">private</span>&nbsp;<span style="color:#0099cc">int</span>&nbsp;hashCode;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">@Override</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">int</span>&nbsp;hashCode()&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#0099cc">int</span>&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;hashCode;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">if</span>&nbsp;(result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span><span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#308ce5">0</span>)&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;Short.hashCode(areaCode);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#308ce5">31</span>&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">*</span>&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">+</span>&nbsp;Short.hashCode(prefix);</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#308ce5">31</span>&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">*</span>&nbsp;result&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">+</span>&nbsp;Short.hashCode(lineNum);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;hashCode&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;result;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;result;</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

<hr>

#### 💎HashCode 작성 시 주의 할 점

* 파생 필드[다른 필드로부터 계산해 낼 수 있는 필드]는 해시코드 계산에서 제외해도 된다.
* equals 비교에 사용되지 않는 필드는 '반드시'제외해야 한다.
* 성능을 높인답시고 해시코드를 계산할 때 핵심필드를 생략해서는 안 된다.
* hashCode가 반환하는 값의 생성 규칙을 API 사용자에게 자세히 공표하지 말 것
  그래야 클라이언트가 이 값에 의지하지 않게 되고, 추후에 계산 방식을 바꿀 수 있다.
* 해시 충돌이 더욱 적은 방법을 꼭 써야 한다면 Guava[com.google.common.hash.Hashing] 을 참조하자.

<hr>

> equals를 재정의할 때는 hashCode도 반드시 재정의해야 한다. 그렇지 않으면 프로그램이 제대로 동작하지 않을 것이다. 재정의한 hashCode는 Object의 API문서에 기술된 일반 규약을 따라야 하며, 서로 다른 인스턴스라면 되도록 해시코드도 서로 다르게 구현해야 한다. 




```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

