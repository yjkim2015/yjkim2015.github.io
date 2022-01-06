---
title: try-finally보다는 try-with-resources를 사용하라 - Effective Java[9]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



자바 라이브러리에는close 메소드를 호출해 직접 닫아줘야 하는 자원이 많다.

그런데 자원 닫기는 클라이언트가 놓치기 쉬워서 예측할 수 없는 성능 문제로 이어지기도 한다.

**이런 자원 중 상당수가 안전망으로 앞에서 배운 finalizer를 활용하고는 있지만 한 치 앞을 예상 할 수 없는 녀석이라 믿음이 가지 않는다.**



전통적으로 제대로 닫힘을 보장하는 수단으로 try-finally가 쓰였다.

아래의 예제를 보자.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div><div style="line-height:130%">6</div><div style="line-height:130%">7</div><div style="line-height:130%">8</div><div style="line-height:130%">9</div><div style="line-height:130%">10</div><div style="line-height:130%">11</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">static</span>&nbsp;<span style="color:#0099cc">String</span>&nbsp;firstLineOfFile(<span style="color:#0099cc">String</span>&nbsp;path)&nbsp;<span style="color:#ff3399">throws</span>&nbsp;IOException&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;BufferedReader&nbsp;br&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;BufferedReader(<span style="color:#ff3399">new</span>&nbsp;FileReader(path));</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">try</span>&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;br.readLine();</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">finally</span>&nbsp;{</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;br.close();</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

책에서는 위 코드에 대해서 미묘한 결점으로 오류가 발생할 시에 예외에 대한 로그처리가 문제시 된다고 언급을 하고 또한 여러개의 자원을 사용하였을때의 지저분하다고 표현을 한다.

***하지만, 솔직히 내가 봤을땐 catch 문을 넣어서 예외 처리를 하면 되지 않을까 싶다.***

***물론 여러개의 자원을 사용하더라도 catch clouse를 추가해주면 되기때문에 그렇게 막.. 지저분하진 않아보인다.*** 



**그런 문제보단 위 코드의 문제는 BufferedReader의 자원을 사용 후 닫아 줘야한다는 점이다.**

**이 때문에 try-finally보다는 try-with-resources를 권장하는 이유이다.**

<hr>


#### try-finally보다는 try-with-resources를 사용하라

**이 구조를 사용하려면 해당 자원이 AutoCloseable 인터페이스를 구현해야한다.**

단순히 void를 반환하는 close 메소드 하나만 정의한 인터페이스이긴 한데 , 이미 수많은 자바 라이브러리에서 이 AutoCloseable 인터페이스를 구현하거나 확장해뒀다.

아래의 예제를 보자.

<div class="colorscripter-code" style="color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important; position:relative !important;overflow:auto"><table class="colorscripter-code-table" style="margin:0;padding:0;border:none;background-color:#fafafa;border-radius:4px;" cellspacing="0" cellpadding="0"><tr><td style="padding:6px;border-right:2px solid #e5e5e5"><div style="margin:0;padding:0;word-break:normal;text-align:right;color:#666;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="line-height:130%">1</div><div style="line-height:130%">2</div><div style="line-height:130%">3</div><div style="line-height:130%">4</div><div style="line-height:130%">5</div></div></td><td style="padding:6px 0;text-align:left"><div style="margin:0;padding:0;color:#010101;font-family:Consolas, 'Liberation Mono', Menlo, Courier, monospace !important;line-height:130%"><div style="padding:0 6px; white-space:pre; line-height:130%"><span style="color:#ff3399">static</span>&nbsp;<span style="color:#0099cc">String</span>&nbsp;firstLineOfFile(<span style="color:#0099cc">String</span>&nbsp;path)&nbsp;<span style="color:#ff3399">throws</span>&nbsp;IOException&nbsp;{</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">try</span>&nbsp;(BufferedReader&nbsp;br&nbsp;<span style="color:#0086b3"></span><span style="color:#ff3399">=</span>&nbsp;<span style="color:#ff3399">new</span>&nbsp;BufferedReader(<span style="color:#ff3399">new</span>&nbsp;FileReader(path))){</div><div style="padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#ff3399">return</span>&nbsp;br.readLine();</div><div style="background-color:#f0f0f0; padding:0 6px; white-space:pre; line-height:130%">&nbsp;&nbsp;&nbsp;&nbsp;}</div><div style="padding:0 6px; white-space:pre; line-height:130%">}</div></div><div style="text-align:right;margin-top:-13px;margin-right:5px;font-size:9px;font-style:italic"><a href="http://colorscripter.com/info#e" target="_blank" style="color:#e5e5e5text-decoration:none">Colored by Color Scripter</a></div></td><td style="vertical-align:bottom;padding:0 2px 4px 0"><a href="http://colorscripter.com/info#e" target="_blank" style="text-decoration:none;color:white"><span style="font-size:9px;word-break:normal;background-color:#e5e5e5;color:white;border-radius:10px;padding:1px">cs</span></a></td></tr></table></div>

앞선 코드를 변형했다. 어떠한가? 가독성도 좋다, 또한 close를 일일이 안해줘도 되기 때문에 너도 행복 나도 행복 

위아더 해피하다. 또한 보통의 try-finally에서처럼 try-with-resources에서도 catch 절을 사용 할 수 있다.

catch 절 덕분에 예외 처리를 더 손쉽게 할 수 있다.



> 정리하자면 꼭 회수해야 하는 자원을 다룰 때는 try-finally 말고, try-with-resources를 사용하자.
>
> 예외는 없다. 코드는 더 짧고 분명해지고, 만들어지는 예외 정보도 훨씬 유용하다. try-finally로 작성하면 실용적이지 못한 만큼 코드가 지저분해지는 경우라도, try-with-resources로는 정확하고 쉽게 자원을 회수할 수 있다.




```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

