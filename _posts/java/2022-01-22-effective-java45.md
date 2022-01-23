---
title: 스트림은 주의해서 사용하라 - Effective Java[45]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 스트림 API가 제공하는 추상 개념의 핵심 두가지

* **첫 번째**, <span style="color:red;">스트림(Stream)</span>은 데이터 원소의 유한 혹은 무한 시퀀스(sequence)를 뜻한다.



* **두 번째**, <span style="color:red;">스트림 파이프라인(stream pipeline)</span>은 이 원소들로 수행하는 연산 단계를 표현하는 개념이다.

  * 스트림의 원소들은 어디로부터든 올 수 있다.

  

  * ex) 컬렉션, 배열, 파일 정규표현식 패턴 매처, 난수 생성기, 혹은 다른 스트림

  

  * 스트림 안의 데이터 원소들은 객체 참조나 기본 타입 값이다.

  

  * 기본 타입 값으로는 int, long, double 세가지를 지원한다.





<hr>


💎 **스트림 파이프라인의 시작과 끝**

* **스트림 파이프라인은** **소스 스트림에서 시작**해 **종단 연산으로 끝**나며, 그 사이에 하나 이상의 **중간 연산**이 있을 수 있다.



* 각 **중간 연산**은 **스트림을** 어떠한 방식으로 **변환한다**.

  * ex) 각 원소에 함수를 적용하거나 특정 조건을 만족 못하는 원소를 걸러낼 수 있다.

  

* **중간 연산**들은 모두 한 스트림을 다른 스트림으로 변환하는데, **변환된 스트림의 원소 타입은 변환 전 스트림의 원소 타입과 같을 수도 있고 다를 수도 있다.**



* **종단 연산**은 마지막 중간 연산이 내놓은 **스트림에 최후의 연산을 가한다.**
  * 원소를 정렬해 컬렉션에 담거나, 특정 원소 하나를 선택하거나 모든 원소를 출력하는 식이다.



<hr>



💎 **스트림 파이프라인은 지연 평가된다 **

* **평가는 종단 연산이 호출될 때 이뤄지며**, 종단 연산에 쓰이지 않는 데이터 원소는 계산이 쓰이지 않는다.

  * 이러한 지연 평가가 무한 스트림을 다룰 수 있게 해주는 열쇠다.

  

* 종단 연산이 없는 스트림 파이프라인은 아무 일도 하지 않는 no-op와 같으니, <span style="color:red;">종단 연산을 빼먹는 일이 절대 없도록 하자.</span>



<hr>



##### 💎 플루언트 API : 스트림 API

* 스트림 API는 **메서드 연쇄를 지원**하는 <span style="color:red;">플루언트 API(fluent API)다.</span>

  * 즉, 파이프라인 하나를 구성하는 **모든 호출을 연결**하여 **단 하나의 표현식으로 완성**할 수 있다.

  

  * **파이프라인 여러 개를 연결**해 표현식 하나로 만들 수도 있다.



<hr>



💎 **순차적 수행 : 스트림 파이프라인**

* 기본적으로 스트림 파이프라인은 **순차적으로 수행**된다.
  * **파이프라인을** <span style="color:red;">병렬로 실행하려면</span> 파이프라인을 구성하는 스트림 중 하나에서 **parallel 메서드를 호출**해주기만 하면 되나, 효과를 볼 수 있는 상황은 많지 않다.



<hr>



💎 **다재다능?  : 스트림 API**

* 스트림 API는 다재다능하여 사실상 어떠한 계산이라도 해낼 수 있다.

  * 하지만 할 수 있다는 뜻이지, 해야 한다는 뜻은 아니다.

  

* 스트림을 제대로 사용하면 프로그램이 깔끔해지지만, 잘못 사용하면 읽기 어렵고 유지보수도 힘들어 진다.

  

* 스트림을 언제 써야하는지를 규정하는 확고부동한 규칙은 없지만, **참고할 만한 노하우는 있다.**

  * 아래에서 확인하자



<br>



💎 **사전 하나를 훑어 원소 수가 많은 아나그램 그룹들을 출력한다.**

* 아나그램이란 철자를 구성하는 알파벳이 같고 순서만 다른 단어

```java
public class Anagrams {
    public static void main(String[] args) throws IOException {
        File dictionary = new File(args[0]);
        int minGroupSize = Integer.parseInt(args[1]);
        
        Map<String, Set<String>> groups = new HashMap<>();
        try (Scanner s = new Scanner(dictionary)) {
            while(s.hasNext()){
				String word = s.next();
                groups.computeIfAbsent(alphabetize(word),
                                       (unused) -> new TreeSet<>()).add(word);
            }
        }
        
        for (Set<String> group : groups.values()){
            if (group.size() >= minGroupSize) {
                System.out.println(group.size() + ": " + group);
            }
        }
    }
    
    private static String alphabetize(String s) {
        char[] a = s.toCharArray();
        Arrays.sort(a);
        return new String(a);
    }
}
```

* 위 프로그램에서 각 단어를 삽입 할 때 자바 8에서 추가된 **computeIfAbsent** 메서드를 사용했다.

  * 이 메서드는 **맵 안에 키가 있는지 찾은 다음**, 있으면 단순히 **그 키에 매핑된 값을 반환**한다.

  

  * **키가 없으면 건네진 함수 객체를 키에 적용**하여 값을 계산해낸 다음 **그 키와 값을 매핑해놓고, 계산된 값을 반환**한다.

  

  * 이처럼 **computeIfAbsent**를 사용하면 각 **키에 다수의 값을 매핑하는 맵을 쉽게 구현**할 수 있다.

  

<hr>



💎 **스트림을 과하게 사용했다 - 따라하지 말 것!**

```java
public class Anagrams {
    public static void main(String[] args) throws IOException {
        Path dictionary = Paths.get(args[0]);
        int minGroupSize = Integer.parseInt(args[1]);
        
        try (Stream<String> words = Files.lines(dictionary)) {
            words.collect(
            	groupingBy(word -> word.chars().sorted()
                          .collect(StringBuilder::new,
                                  (sb, c) -> sb.append((char) c),
                                  StringBuilder::append).toString()))
                .values().stream()
                .stream(group -> group.size() >= minGroupSize)
        }
    }
}
```

* **모든 사람이 이해하기 어려운 코드**

  * 이처럼 스트림을 과용하면 프로그램이 읽거나 유지보수하기 어려워진다.

  

* 다음 처럼 절충하여 적당히 사용하자.

<br>



💎 **스트림을 적절히 활용하면 깔끔하고 명료해진다.**

```java
public class Anagrams {
    public static void main(String[] args) throws IOException {
        Path dictionary = Paths.get(args[0]);
        int minGroupSize = Integer.parseInt(args[1]);
        
        try (Stream<String> word = Files.lines(dictionary)) {
            words.collect(groupingBy(word -> alphabetize(word)))
                .values().stream()
                .filter(group -> group.size() >= minGroupSize)
                .forEach(g -> System.out.println(g.size() + " : "+ g));
        }
    }
   ...
}
```

* 위 코드에는 **try-with-resources** 블록에서 사전 파일을 열고, 파일의 모든 라인으로 구성된 스트림을 얻는다.

  * 스트림 변수의 이름을 **words**로 지어 스트림 안의 각 원소가 단어임을 명확히 했다.

  

  * 이 스트림의 파이프라인에는 중간 연산은 없으며, 종단 연산에서는 모든 단어를 수집해 맵으로 모은다.

    

* 그다음으로 이 맵의 **values()**가 반환한 값으로부터 새로운 `Stream<List<String>>` 스트림을 연다.

  * 이 스트림의 원소는 물론 아나그램 리스트이다.

  

  * 그 리스트들 중 원소가 **minGroupSize**보다 적은 것은 필터링돼 무시된다.

  

* 마지막으로 종단 연산인 **forEach**는 살아남은 리스트를 출력한다.

<br>



> 람다 매개변수의 이름은 주의해서 정해야 한다. ex) 위 코드의 매개변수 g -> group
>
> **람다에서는 타입 이름을 자주 생략하므로 매개변수 이름을 잘 지어야 스트림 파이프라인의 가독성이 유지된다.**
>
> 한편, 단어의 철자를 알파벳순으로 정렬하는 일은 별도 메서드인 alphabetize에서 수정했다.
>
> 연산에 적절한 이름을 지어주고 세부 구현을 주 프로그램 로직 밖으로 빼내 전체적인 가독성을 높인 것이다.
>
> **도우미 메서드를 적절히 활용하는 일의 중요성은 일반 반복코드에서보다는 스트림 파이프라인에서 훨씬 크다.**
>
> 파이프라인에서는 타입 정보가 명시되지 않거나 임시 변수를 자주 사용하기 떄문이다.



<hr>



##### 💎 char 값들을 처리할 때는 스트림을 삼가는 편이 낫다.

* 위 alphabetize 메소드도 스트림을 사용해 다르게 구현할 수 있다.



* 하지만 그렇게하면 **명확성이 떨어지고 잘못 구현할 가능성이 커진다.**

  * 심지어 느려질 수도 있다.

  

* 자바가 기본 타입인 char용 스트림을 지원하지 않기 때문이다.

<br>

```java
"Hello world!".chars().forEach(System.out::print);
```

* 위 코드의 결과 값은 Hello world가 아닌 7210~ 블라블라 의 int형이다.

  * "Hello world".chars()가 반환하는 스트림의 원소는 char가 아닌 int 값이기 때문이다.

  

  * 때문에 정상적인 값을 원한다면 아래와 같이 형변환을 명시적으로 해줘야 한다.

<br>

```java
"Hello world!".chars().forEach(x -> System.out.print(char) x);
```



<hr>



💎 **기존 코드는 스트림을 사용하도록 리팩터링하되, 새 코드가 더 나아 보일때만 반영하자**

* 스트림을 처음 쓰기 시작하면 모든 반복문을 스트림으로 바꾸고 싶은 유혹이 일겠지만, 서두르지 않는 게 좋다.



* 스트림으로 바꾸는 게 가능할지라도 코드 가독성과 유지보수 측면에서는 손해를 볼 수 있기 때문이다.



* 중간 정도 복잡한 작업에도 **스트림과 반복문을 적절히 조합**하는게 **최선이다**.



<hr>



💎 **함수 객체로는 할 수 없지만 코드 블록으로는 할 수 있는 일**

* 위 코드에서는 스트림 파이프라인은 **되풀이되는 계산**을 **함수 객체(주로 람다나 메서드 참조)로 표현한다.**



* <span style="color:red;">반면</span> **반복 코드**에서는 **코드 블록을 사용해 표현**한다.



* 그런데 **함수 객체로는 할 수 없지만** <span style="color:red;">코드 블록으로는 할 수 있는 일</span>들이 있으니, 다음이 그 예다.

  * **코드 블록**에서는 일정 범위 안의 지역변수를 읽고 수정할 수 있다. 
    <span style="color:red;">하지만</span> **람다에서는** **final**이거나 사실상 **final**인 변수만 읽을 수 있고, **지역변수를 수정하는 건 불가능하다.**

  

  * **코드 블록**에서는 **return** 문을 사용해 메서드에서 빠져나가거나,
    **break**나 **continue** 문으로 블록 바깥의 반복문을 종료하거나 반복을 한 번 건너뛸 수 있다. 
    또한 **메서드 선언에 명시된 검사 예외**를 던질 수 있다. 
    <span style="color:red;">하지만</span> 람다로는 이 중 어떤 것도 할 수 없다.



<hr>



💎 **농심 안성맞춤 :: 스트림을 적용하기 좋은 후보**

* 원소들의 **시퀀스를 일관되게 변환**한다.



* 원소들의 **시퀀스를 필터링**한다.



* 원소들의 **시퀀스를 하나의 연산을 사용해 결합**한다(더하기, 연결하기, 최솟값 구하기 등)



* 원소들의 **시퀀스를 컬렉션에 모은다**(아마도 공통된 속성을 기준으로 묶어가며)



* 원소들의 **시퀀스에서 특정 조건을 만족하는 원소를 찾는다.**



<hr>



💎 **스트림으로 처리하기 어려운 일**

* 한 데이터가 파이프라인의 여러 단계를 통과할 때 이 **데이터의 각 단계에서의 값들에 동시에 접근**하기는 <span style="color:red;">어려운 경우다.</span>

  * 스트림 파이프라인은 **일단 한 값을 다른 값에 매핑하고 나면** **원래의 값은 잃는 구조**이기 때문이다.

  

  * 원래 값과 새로운 값의 쌍을 저장하는 객체를 사용해 매핑하는 우회 방법도 있지만, 그리 만족 스러운 해법은 아닐 것이다.

  

  * 매핑 객체가 필요한 단계가 여러 곳이라면 특히 그렇다.

  

  * 이런 방식은 코드 양도 많고 지저분하여 스트림을 쓰는 주목적에서 온전히 전혀 벗어난다.

  

  * **가능한 경우라면**, 앞 단계의 값이 필요할 때 <span style="color:red;">매핑을 거꾸로 수행하는 방법</span>이 나을 것이다.



<br>

💎 **처음 20개의 메르센 소수를 출력하는 프로그램**

* **메르센 수**는 2^p -1 형태의 수다. 여기서 **p가 소수이면** 해당 메르센 수도 소수일 수 있는데 이때의 수를 메르센 소수라 한다.



* 이 파이프라인의 첫 스트림으로는 모든 소수를 사용할 것이다.



* 다음 코드는 (무한) 스트림을 반환하는 메서드다. **BigInteger**의 정적 멤버들은 정적임포트하여 사용한다고 가정한다.

```java
static Stream<BigInteger> primes() {
    return Stream.iterate(TWO, BigInteger::nextProbablePrime);
}

public static void main(String[] args) {
    primes().map(p -> TWO.pow(p.intValueExact()).subtract(ONE))
        .filter(mersenne -> mersenne.isProbablePrime(50))
        .limit(20)
        .forEach(System.out::println);
}
```

* 메서드 이름 primes는 스트림의 원소가 소수임을 말해준다.

  * 스트림을 반환하는 메서드 이름은 이처럼 원소의 정체를 알려주는 복수 명사로 쓰기를 강력히 추천한다.

  

  * 스트림 파이프라인의 가독성이 크게 좋아질 것이다.

  

* 이 메서드가 사용하는 **Stream.iterate**라는 정적 팩터리 메서드는 매개변수를 2개 받는다.

  * 첫 번째 매개변수는 스트림의 첫 번째 원소이고, 두 번째 매개변수는 스트림에서 다음 원소를 생성해주는 함수다.



* 각 메르센 소수의 앞에 지수(p)를 출력하길 원할 때, 이 값은 초기 스트림에만 나타나므로 결과를 출력하는 조단 연산에서는 접근 할 수 없다.

  * <span style="color:red;">하지만</span> 다행히 첫 번째 중간 연산에서 수행한 매핑을 거꾸로 수행해 메르센 수의 지수를 쉽게 계산해 낼 수 있다.

  

  * 지수는 단순히 숫자를 이진수로 표현한 다음 몇 비트인지를 세면 나오므로, 종단 연산을 다음처럼 작성하면 원하는 결과를 얻을 수 있다.

```java
.forEach(mp -> System.out.println(mp.bitLength() + ": " + mp));
```



<hr>



💎 **스트림과 반복 중 어느 쪽을 써야할지 바로 알기 어려운 경우도 많아!**

* ex) 카드 덱을 초기화 하는 작업

  * 카드는 숫자(rank)와 무늬(suit)를 묶은 **불변 값 클래스**이고, 숫자와 무늬는 모두 **열거 타입**이라 하자.

  

  * 이 작업은 두 집합의 원소들로 만들 수 있는 **가능한 모든 조합을 계산하는 문제다.**

  

  * 수학자들은 이를 두 집합의 **데카르트 곱**이라고 부른다.

<br>



💎 **데카르트 곱 계산을 반복 방식으로 구현 : for-each 반복문**

```java
private static List<Card> newDeck() {
    List<Card> result = new ArrayList<>();
    for (Suit suit : Suit.values()) {
        result.add(new Card(suit, rank));
    }
    return result;
}
```



💎 **스트림으로 구현**

* 중간 연산으로 사용한 flatMap은 스트림의 원소 각각을 하나의 스트림으로 매핑한 다음 그 스트림들을 다시 하나의 스트림으로 합친다.
  * 이를 평탄화라고 한다.

```java
private static List<Card> newDeck() {
    return Stream.of(Suit.values())
        .flatMap(suit -> Stream.of(Rank.values())
                .map(rank -> new Card(suit, rank)))
        .collect(toList());
}
```





<hr>



> 스트림을 사용해야 멋지게 처리할 수 있는 일이 있고, 반복 방식이 더 알맞은 일도 있다.
>
> 그리고 수많은 작업이 이 둘을 조합했을 때 가장 멋지게 해결된다.
>
> 어느 쪽을 선택하는 확고부동한 규칙은 없지만 참고할 만한 지침 정도는 있다.
>
> 어느 쪽이 나은지가 확연히 드러나는 경우가 많겠지만, 아니더라도 방법은 있다.
>
> **스트림과 반복 중 어느 쪽이 나은지 확신하기 어렵다면 둘 다 해보고 더 나은 쪽을 택하라.**







```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```
