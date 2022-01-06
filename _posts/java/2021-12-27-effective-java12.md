---
title: toString을 항상 재정의하라 - Effective Java[12]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---

#### 🔗 모든 하위 클래스에서 toString 메소드를 항상 재정의하라.

Object의 기본 toString 메소드는 우리가 작성한 클래스에 적합한 문자열을 반환하는 경우는 거의 없다.

이 메소드는 단순히 **클래스_이름@16진수로_표시한_해시코드**를 반환할 뿐이다.

**toString의 일반 규약에 따르면 '간결하면서 사람이 읽기 쉬운 형태의 유익한 정보'를 반환해야 한다.**

**또한 toString의 규약은 "모든 하위 클래스에서 이 메소드를 재정의하라"고 한다.**



***toString을 잘 구현한 클래스는 사용하기에 훨씬 즐겁고, 그 클래스를 사용한 시스템은 디버깅하기 쉽다.***

<hr>

#### 💎toString 작성 시 주의 할 점

* **toString은 그 객체가 가진 주요 정보 모두를 반환하는게 좋다.**
  * 하지만 객체가 거대하거나 객체의 상태가 문자열로 표현하기에 적합하지 않다면 무리가 있다.
    **이런 상황이라면 "맨해튼 거주자 전화번호부 (총 1487536개)"나 Thread[main,5,main]"과 같은 요약 정보를 담아야 한다.**
    **이상적으로는 스스로를 완벽히 설명하는 문자열이어야한다.**
* **반환 값의 포맷을 문서화할지 정해야 한다.** 전화번호나 행렬 같은 값 클래스라면 문서화하기를 권한다. 포맷을 명시하면 그 객체는 표준적이고, 명확하고, 사람이 읽을 수 있게 된다.
  따라서 그 값 그대로 입출력에 사용하거나 CSV 파일처럼 사람이 읽을 수 있는 데이터 객체로 저장할 수 도 있다.

* **포맷을 명시하든 아니든 개발자의 의도는 명확히 밝혀야 한다.**

  포맷을 명시하려면 아주 정확하게 해야한다. 다음의 toString 메소드를 보자.

  <div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div><div style="line-height:130%">12</div><div style="line-height:130%">13</div><div style="line-height:130%">14</div><div style="line-height:130%">15</div><div style="line-height:130%">16</div><div style="line-height:130%">17</div><div style="line-height:130%">18</div><div style="line-height:130%">19</div><div style="line-height:130%">20</div><div style="line-height:130%">21</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;<span style="color:#999999">//&nbsp;포맷을&nbsp;명시하기로&nbsp;한&nbsp;경우</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;<span style="color:#999999">/**</span></div><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#999999">&nbsp;&nbsp;&nbsp;*&nbsp;이&nbsp;전화번호의&nbsp;문자열&nbsp;표현을&nbsp;반환한다.</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%"><span style="color:#999999">&nbsp;&nbsp;&nbsp;*&nbsp;이&nbsp;문자열은&nbsp;"XXX-YYY-ZZZZ"&nbsp;형태의&nbsp;12글자로&nbsp;구성된다.</span></div><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#999999">&nbsp;&nbsp;&nbsp;*&nbsp;XXX는&nbsp;지역&nbsp;코드,&nbsp;YYY는&nbsp;프리픽스,&nbsp;ZZZZ는&nbsp;가입자&nbsp;번호다.</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%"><span style="color:#999999">&nbsp;&nbsp;&nbsp;*&nbsp;각각의&nbsp;대문자는&nbsp;10진수&nbsp;숫자&nbsp;하나를&nbsp;나타낸다.</span></div><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#999999">&nbsp;&nbsp;&nbsp;*</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%"><span style="color:#999999">&nbsp;&nbsp;&nbsp;*&nbsp;전화번호의&nbsp;각&nbsp;부분의&nbsp;값이&nbsp;너무&nbsp;작아서&nbsp;자릿수를&nbsp;채울&nbsp;수&nbsp;없다면,</span></div><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#999999">&nbsp;&nbsp;&nbsp;*&nbsp;앞에서부터&nbsp;0으로&nbsp;채워나간다.&nbsp;예컨대&nbsp;가입자&nbsp;번호가&nbsp;123이라면</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%"><span style="color:#999999">&nbsp;&nbsp;&nbsp;*&nbsp;전화번호의&nbsp;마지막&nbsp;네&nbsp;문자는&nbsp;"0123"이&nbsp;된다.</span></div><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#999999">&nbsp;&nbsp;&nbsp;*/</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;@Override&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">String</span>&nbsp;<span style="color:#0099cc">toString</span>()&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;<span style="color:#0099cc">String</span>.<span style="color:#0099cc">format</span>(<span style="color:#993333">"%03d-%03d-%04d"</span>,</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;areaCode,&nbsp;prefix,&nbsp;lineNum);</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;<span style="color:#999999">//&nbsp;포맷을&nbsp;명시하지&nbsp;않기로&nbsp;한&nbsp;경우</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;<span style="color:#999999">/**</span></div><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#999999">&nbsp;&nbsp;&nbsp;*&nbsp;상세형식은&nbsp;정해지지&nbsp;않았으며&nbsp;향후&nbsp;변경될&nbsp;수&nbsp;있다.&nbsp;</span></div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%"><span style="color:#999999">&nbsp;&nbsp;&nbsp;*/</span></div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;@Override&nbsp;<span style="color:#ff3399">public</span>&nbsp;<span style="color:#0099cc">String</span>&nbsp;<span style="color:#0099cc">toString</span>()&nbsp;{...}</div></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

​		만약 이러한 설명을 읽고도 이 포맷에 맞춰 코딩하거나 특정 값을 빼내어 영구 저장한 프로그래머		는 나중에 포맷이 바뀌어 피해를 입어도 자기 자신을 탓할 수 밖에 없을 것이다.



* **toString이 반환한 값에 포함된 정보를 얻어올 수 있는 API를 제공하자.**

  * 예를들어 PhoneNumber 클래스는 areaCode, prefix, lineNum 접근자를 제공해야 한다.

    그렇지 않으면 이 정보가 필요한 프로그래머는 toString의 반환 값을 파싱할 수 밖에 없다.

    성능이나빠지고, 필요하지도 않은 작업이다.





> 모든 구체 클래스에서 Object의 toString을 재정의하자. 상위 클래스에서 이미 알맞게 재정의한 경우는 예외다. toString을 재정의한 클래스는 사용하기도 즐겁고 그 클래스를 사용한 시스템을 디버깅하기 쉽게 해준다. toString은 해당 객체에 관한 명확하고 유용한 정보를 읽기 좋은 형태로 반환해야한다.




```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

