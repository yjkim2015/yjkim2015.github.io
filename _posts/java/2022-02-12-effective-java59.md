---
title: 라이브러리를 익히고 사용하라 - Effective Java[59]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗  표준 라이브러리를 사용하면 그 코드를 작성한 전문가의 지식과 앞서 사용한 다른 프로그래머들의 경험을 활용할 수 있다.


* 무작위 정수 하나를 생성한다고 가정해보자.


  * 값의 범위는 0부터 명시한 수 사이다.

  


  * 흔히 마주치는 문제로, 많은 프로그래머가 다음과 같은 짤막한 메서드를 만들곤 한다.



<br>

💎 **흔하지만 문제가 심각한 코드!**

```java
static Random rnd = new Random();

static int random(int n) {
    return Math.abs(rnd.nextInt()) % 3;
}
```

* 위 코드는 **세 가지의 문제를 내포하고 있다.**

  * **첫 번째**, n이 그리 크지 않은 2의 제곱은 2의 제곱수라면 얼마 지나지 않아 같은 수열이 반복된다.

  

  * **두 번째**, n이 2의 제곱수가 아니라면 몇몇 숫자가 평균적으로 더 자주 반환된다.

    * n값이 크면 이 현상은 더 두드러진다.

    

    * 다음의 예시 코드를 보자.

    * ```java
      public static void main(String[] args) {
          int n = 2 * (Integer.MAX_VALUE / 3);
          int low = 0;
          for (int i = 0; i < 1000000; i++) {
              if (random(n) < n/2) {
                  low++;
              }
          }
         	System.out.println(low);
      }
      ```

     

    * **random** 메서드가 이상적으로 동작한다면 약 50만 개가 출력되어야 하지만, 실제로 돌려보면 666,666에 가까운 값을 얻는다.

      

    * 무작위로 생성된 수 중에서 2/3 가량이 중간값보다 낮은 쪽으로 쏠린 것이다.

    

  * **세 번째**, 지정한 범위 '바깥'의 수가 종종 튀어나올 수 있다.

    * rnd.nextInt()가 반환한 값을 Math.abs를 이용해 음수가 아닌 정수로 매핑하기 때문이다.

    

    * nextInt()가 Integer.MIN_VALUE를 반환하면 Math.abs도 Integer.MIN_VALUE를 반환하고, 나머지 연산자(%)는 음수를 반환해버린다.



<br>



##### 💎 해결책은 이미 만들어져있다!

* 다행히 위에서 언급한 문제에 대한 해결책은 이미 만들어져 있다.

  * **Random.nextInt(int)이다.**

  

* 알고리즘에 능통한 개발자가 설계와 구현과 검증에 시간을 들여 개발했고, 이분야의 여러 전문가가 잘 동작함을 검증해줬다.

  * 또한 이 라이브러리가 릴리스된 후 20여 넌 가까이 수백만의 개발자가 열심히 사용했지만 버그가 보고된 적이 없다.



* 표준 라이브러리를 사용하면 그 코드를 작성한 전문가의 지식과 앞서 사용한 다른 프로그래머들의 경험을 활용 할 수 있다.



<hr>



##### 💎 자바 7부터는 ThreadLocalRandom으로 대체하면 대부분 잘 작동한다.

* **Random**보다 더 고품질의 무작위 수를 생성할 뿐 아니라 속도도 더 빠르다.



* <span style="color:red;">한편</span>, 포크-조인 풀이나 병렬 스트림에서는 **SpittableRandom**을 사용하라.



<hr>

##### 🔗 표준 라이브러리를 쓰는 또 다른 이점들

* **두 번째**, 핵심적인 일과 크게 관련 없는 문제를 해결하느라 시간을 허비하지 않아도 된다는 것이다.
  * 프로그래머들  하부 공사를 하기보다는 애플리케이션 기능 개발에 집중하고 싶어 한다.



* **세 번째**, 따로 노력하지 않아도 성능이 지속해서 개선된다는 점이다.

  * 사용자가 많고, 업계 표준 벤치마크를 사용해 성능을 확인하기 때문에 표준 라이브러리 제작자들은 더 나은 방법을 꾸준히 모색할 수 밖에 없다.

  

  * 자바 플랫폼 라이브러리의 많은 부분이 수 년에 걸쳐 지속해서 다시 작성되며, 떄론 성능이 극적으로 개선되기도 한다.



* **네 번째**, 기능이 점점 많아진다는 것이다.
  * 라이브러리에 부족한 부분이 있다면 개발자 커뮤니티에서 이야기가 나오고 논의된 후 다음 릴리스에 해당 기능이 추가되곤 한다.



* **마지막**, 직접 작성한 코드가 많은 사람에게 낯익은 코드가 된다는 것이다.
  * 자연스럽게 다른 개발자들이 더 읽기 좋고, 유지보수하기 좋고, 재활용하기 쉬운 코드가 된다.



<hr>



##### 🔗 표준라이브러리 사용의 장점이 많은데 왜  많은 프로그래머들은 직접 구현하는거야?

* <span style="color:red;">아마도 라이브러리에 그런 기능이 있는지 모르기 때문일 것이다.</span>



* 메이저 릴리스마다 주목할 만한 수많은 기능이 라이브러리에 추가된다.

  * 자바는 메이저 릴리스마다 새로운 기능을 설명하는 웹페이지를 공시하는데, 한 번쯤 읽어볼 만하다.

  

  * ex) 지정한 URL의 내용을 가져오는 명령줄 애플리케이션을 작성해보자.
    * 예전에는 작성하기가 까다로운 기능이었지만, 자바 9에서 **InputStream**에 추가된 **transferTo** 메서드를 사용하면 쉽게 구현할 수 있다.

<br>



💎 **transferTo 메서드를 이용해 URL의 내용 가져오기 - 자바 9부터 가능하다.**

```java
public static void main(String[] args) throw IOException {
    try (InputStream in = new URL(args[0]).openStream()) {
        in.transferTo(System.out);
    }
}
```



<hr>



##### 🔗 라이브러리가 너무 방대한데 모든 API를 다 살펴봐야해?

* <span style="color:red;">자바 프로그래머라면 적어도</span> **java.lang, java.util, java.io**와 **그 하위 패키지들에는 익숙해져야 한다.**

  * 다른 라이브러리들은 필요할 때마다 익히기 바란다.

  

  * 라이브러리는 매년 아주 빠르게 성장하고 있으니 **모든 기능을 요약하는 건 무리다.**



* <span style="color:red;">하지만 언급해둘 만한 라이브러리는 몇 개 있다.</span>

  * **컬렉션 프레임워크**와 **스트림 라이브러리**다.

  

  * **java.util.concurrent**의 동시성 기능도 마찬가지로 알아두면 큰 도움이 된다.
    * 이 패키지는 멀티스레드 프로그래밍 작업을 단순화해주는 고수준의 편의 기능은 물론, 능숙한 개발자가 자신만의 고수준 개념을 직접 구현할 수 있도록 도와주는 저수준 요소들을 제공한다.



<hr>



##### 🔗 근데 내가 필요한 기능을 라이브러리가 충분히 제공하지 못하면 어떻게 해?

* <span style="color:red;">때때로</span> 라이브러리가 **우리에게 필요한 기능을 충분히 제공하지 못할 수 있다.**

  * 더 전문적인 기능을 요구할수록 이런 일이 더 자주 생길 것이다.

  

  * 우선은 라이브러리를 사용하려 시도해보자.



* 어떤 영역의 기능을 제공하는지 살펴보고, <span style="color:red;">원하는 기능이 아니라 판단되면 대안을 사용하자.</span>

  * **어떤 라이브러리든** 제공하는 기능은 유한하므로 **항상 빈 구멍이 있기 마련이다.**

  

  * 자바 표준 라이브러리에서 원하는 기능을 찾지 못하면, **그다음 선택지는 고품질의 서드파티 라이브러리가 될 것이다.**

  

  * 구글의 멋진 구아바 라이브러리가 대표적이다.
    * 적합한 서드파티 라이브러리도 찾지 못했다면, 다른 선택이 없으니 직접 구현하자.



<hr>

> **바퀴를 다시 발명하지 말자.**
>
> 아주 특별한 나만의 기능이 아니라면 누군가 이미 라이브러리 형태로 구현해놓았을 가능성이 크다. 그런 라이브러리가 있다면, 쓰면 된다.
> 있는지 잘 모르겠다면 찾아보라.
>
> 일반적으로 라이브러리의 코드는 여러분이 직접 작성한 것보다 품질이 좋고, 점차 개선될 가능성이 크다.
>
> **코드 품질에도 규모의 경제가 적용된다.**
>
> **즉, 라이브러리 코드는 개발자 각자가 작성하는 것보다 주목을 훨씬 많이 받으므로 코드 품질도 그만큼 높아진다.**









```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```
