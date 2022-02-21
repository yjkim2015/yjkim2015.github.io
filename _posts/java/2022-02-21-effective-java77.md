---
title: 예외를 무시하지 말라 - Effective Java[77]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗  API 설계자가 메서드 선언에 예외를 명시하는 까닭은, 그 메서드를 사용할 때 적절한 조치를 취해달라는 것이다.

* 안타깝게도 예외를 무시하기란 아주 쉽다.



* 아래 코드 처럼 해당 메서드 호출을 try 문으로 감싼 후 catch 블록에서 아무 일도 하지 않으면 끝이다.

```java
// catch 블록을 비워두면 예외가 무시된다. 아주 의심스러운 코드다!
try {
    ...
} catch (SomeException e) {
}
```




<hr>


##### 💎  예외는 문제 상황에 잘 대처하기 위해 존재하는데 catch 블록을 비워두면 예외가 존재할 이유가 없어진다.

* 비유하자면 화재경보를 무시하는 수준을 넘어 아예 꺼버려, 다른 누구도 화재가 발생했음을 알지 못하게 하는 것과 같다. 
  * 운이 좋아 별 탈이 없으면 다행이지만 끔찍한 참사로 이어질 수도 있으니, 빈 **catch** 블록을 목격한다면 반드시 머릿속에 사이렌을 울려야 한다.




<hr>



##### 💎  예외를 무시해야 할 때도 있다구!

* 예를들어 **FileInputStream**을 닫을 때가 그렇다.

  * (입력 전용 스트림이므로) 파일의 상태를 변경하지 않았으니 복구할 것이 없으며, (스트림을 닫는다는 건) 필요한 정보는 이미 다 읽었다는 뜻이니 남은 작업을 중단할 이유도 없다.

  

  * 혹시나 같은 예외가 자주 발생한다면 조사해보는 것이 좋을테니 파일을 닫지 못했다는 사실을 로그로 남기는것도 좋은 생각이다.



* **예외를 무시하기로 했다면** 아래와 같이 <span style="color:red;">catch 블록 안에 그렇게 결정한 이유를 주석으로 남기고 예외 변수의 이름도 ignored로 바꿔놓도록 하라.</span>

```java
Future<Integer> f = exec.submit(planarMap::chromaticNumber);

int numColors = 4; //기본 값. 어떤 지도라도 이 값이면 충분하다.
try {
    numColors = f.get(1L, TimeUnit.SECONDS);
} catch (TimeoutException | ExecutionException ignored) {
    //기본 값을 사용한다(색상 수를 최소화하면 좋지만, 필수는 아니다)
}
```






```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

