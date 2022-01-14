---
title: ordinal 인덱싱 대신 EnumMap을 사용하라 - Effective Java[37]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



#### 🔗 ordinal 인덱싱

* 이따금 배열이나 리스트에서 원소를 꺼낼 때 다음과 같이 **ordinal** 메소드로 인덱스를 얻는 코드가 있다.

<br>



💎 **식물을 간단히 나타낸 클래스**

```java
class Plant {
    enum LifeCycle { ANNUAL, PERENNIAL, BIENNIAL }
    
    final String name;
    final LifeCycle lifeCycle;
    
    Plant(String name, LifeCycle lifeCycle) {
        this.name = name;
        this.lifeCycle = lifeCycle;
    }
    
    @Override
    public String toString() {
        return name;
    }
}
```



* 이제 정원에 심은 식물들을 배열 하나로 관리하고, 이들을 생애주기(한해살이, 여러해살이, 두해살이) 별로 묶어보자.

  * 생애주기별로 총 3개의 집합을 만들고 정원을 한 바퀴 돌며 각 식물을 해당 집합에 넣는다.

  

  * 이때 어떤 프로그래머는 집합들을 배열 하나에 넣고 생애주기의 **ordinal** 값을 그 배열의 인덱스로 사용하려 할 것이다.

  

<hr>



##### 💎 ordinal()을 배열 인덱스로 사용 - 따라하지 말 것

```java
Set <Plant>[] plantsByLifeCycle =
    (Set<Plant>[]) new Set[Plant.LifeCycle.values().length];
for ( int i = 0; i < plantsByLifeCycle.length; i++ ) {
    plantsByLifeCycle[i] = new HashSet<>();
}

for ( Plant p : garden ) {
	plantsByLifeCycle[p.lifeCycle.ordinal()].add(p);
}

for ( int i = 0; i < plantsByLifeCycle.length; i++ ) {
    System.out.printf("%s: %s%n", Plant.LifeCycle.values()[i], plantsByLifeCycle[i]);
}
```

* 동작은 하지만 문제가 한가득이다.
  * **배열은 제네릭과 호환되지 않으니** 비검사 형변환을 수행해야 하고 **깔끔히 컴파일되지 않을 것이다.**



* **배열은 각 인덱스의 의미를 모르니** 출력 결과에 직접 레이블을 달아야 한다.



* <span style="color:red;">가장 심각한 문제는</span> 정확한 **정숫값을 사용한다는 것을 직접 보증**해야 한다는 점이다.

  * **정수는 열거 타입과 달리 타입 안전하지 않기 때문이다**.

  

  * 잘못된 값을 사용하면 잘못된 동작을 묵묵히 수행하거나 (운이 좋다면) **ArrayIndexOutOfBoundsException**을 던질 것이다.





<hr>



#### 🔗 해결사 등장@@ EnumMap의 등장 

* 위 코드에서  배열은 실질적으로 **열거 타입 상수를 값으로 매핑**하는 일을 한다.

  * 그러니 Map을 사용할 수 있을 것이다.

  

* **열거 타입을 키로 사용**하도록 설계한 아**주 빠른 Map 구현체**가 존재하는데 바로 <span style="color:red;">EnumMap이 그 주인공이다.</span>

<br>



💎 **EnumMap을 사용해 데이터와 열거 타입을 매핑한다.**

```java
Map<Plant.LifeCycle, Set<Plant>> plantsByLifeCycle = 
    new EnumMap<>(Plant.LifeCycle.class);

for (Plant.LifeCycle lc : Plant.LifeCycle.values()) {
    plantsByLifeCycle.put(lc, new HashSet<>());
}

for (Plant p : garden) {
    plantsByLifeCycle.get(p.lifeCycle.ordinal()).add(p);
}
System.out.println(plantsByLifeCycle);
```

* 더 짧고 명료하고 안전하고 성능도 원래 버전과 비등하다.



* **안전하지 않은 형변환은 쓰지 않고**, 맵의 키인 열거 타입이 그 자체로 출력용 문자열을 제공하니 **출력 결과에 직접 레이블을 달 일도 없다.**



* **배열 인덱스를 계산하는 과정에서 오류가 날 가능성도 원천봉쇄된다.**



* **EnumMap**의 성능이 **ordinal**을 쓴 배열에 **비견되는 이유**는 **<span style="color:red;">그 내부에서 배열을 사용하기 때문</span>**이다.

  * 내부 구현 방식을 안으로 숨겨서 **Map의 타입 안정성과 배열의 성능을 모두 얻어낸 것**이다.

  

  * 여기서 **EnumMap**의 생성자가 받는 **키 타입의 Class 객체는** **<span style="color:red;">한정적 타입 토큰</span>**으로, **런타임 제네릭 타입 정보를 제공한다.**



<hr>



##### 🔗 **스트림을 사용해 맵을 관리하면 코드를 더 줄일 수 있다.**



💎 **스트림을 사용한 코드 1 - EnumMap을 사용하지 않는다.**

```java
System.out.println(Arrays.stream(garden)
        .collect(groupingBy(p -> p.lifeCycle)));
```

* 이 코드는 **EnumMap이 아닌 고유한 맵 구현체를 사용**했기 떄문에 **<span style="color:red;">EnumMap을 써서 얻은 공간과 성능 이점이 사라진다는 문제</span>**가 있다.



* 이 문제를 좀 더 구체적으로 살펴보자.
  * 매개변수 3개짜리 **Collectors.groupingBy** 메소드는 **mapFactory** 매개변수에 원하는 맵 구현체를 명시해 호출할 수 있다.

<br>



💎 **스트림을 사용한 코드 - EnumMap을 이용해 데이터와 열거 타입을 매핑했다.**

```java
System.out.println(Arrays.stream(garden)
        .collect(groupingBy(p -> p.lifeCycle,
           () -> new EnumMap<>(LifeCycle.class), toSet())));
```

* 스트림을 사용하면 **EnumMap**만 사용했을 때와는 살짝 다르게 동작한다.

  * **EnumMap** 버전은 언제나 식물의 생애주기당 하나씩의 중첩 맵을 만들지만, 스트림 버전에서는 해당 생애주기에 속하는 식물이 있을 때만 만든다.

  

  * ex) 정원에 한해살이와 여러해살이 식물만 살고 두해살이는 없다면, **EnumMap** 버전에서는 맵을 3개 만들고 스트림 버전에서는 2개만 만든다.



* **두 열거 타입 값들을 매핑**하느라 **ordinal**을 (두 번이나) 쓴 배열들의 배열을 본 적이 있을 것이다.

  * 다음은 이 방식을 적용해 **두 가지 상태(Phase)를 전이(Transition)와 매핑**하도록 구현한 프로그램이다.

  

  * ex) 액체(LIQUID)에서 고체(SOLID)로의 전이는 응고(FREEZE)가 되고, 액체에서 기체(GAS)로의 전이는 기화(BOIL)가 된다.



<hr>



💎 **배열들의 배열의 인덱스에 ordinal()을 사용 - 따라 하지 말 것!**

```java
public enum Phase {
    SOLID, LIQUID, GAS;
    
    public enum Transition {
        MELT, FREEZE, BOIL, CONDENSE, SUBLIME, DEPOSIT;
        
        //행은 from의 ordinal을, 열은 to의 orinal을 인덱스로 쓴다.
        private static final Transition[][] TRANSITIONS = {
            { null, MELT, SUBLIME },
            { FREEZE, null, BOIL },
            { DEPOSIT, CONDENSE, null }
        };
        
        // 한 상태에서 다른 상태로의 전이를 반환한다.
        public static Transition from(Phase from, Phase to) {
            return TRANSITIONS[from.ordinal()][to.ordinal()];
        }
    }
}
```

* 앞서 보여준 간단한 정원 예제와 마찬가지로 컴파일러는 ordinal과 배열 인덱스의 관계를 알 도리가 없다.

  * 즉, Phase나 Phase.Transition 열거 타입을 수정하면서 표 TRANSITIONS를 함께 수정하지 않거나 실수로 잘못 수정하면 런타임 오류가 날 것이다.

  

  * ArrayIndexOutOfBoundsException이나 NullPointerException을 던질 수도 있고, 예외도 던지지 않고 이상하게 동작 할 수도 있다.



<hr>



##### 🔗 EnumMap이 짱이야

* 전이(Transition) 하나를 얻으려면 이전 상태(from)와 이후 상태(to)가 필요하니, 맵 2개를 중첩하면 쉽게 할 수 있다.

  * **안쪽 맵은 이전 상태와 전이를 연결**하고 **바깥 맵은 이후 상태와 안쪽 맵을 연결**한다.

  

* 전이 전후의 두 상태를 전이 열거 타입 Transition의 입력으로 받아, 이 Transition 상수들로 중첩된 EnumMap을 초기화 하면 된다.

<br>



💎 **중첩 enumMap으로 데이터와 열거 타입 쌍을 연결했다.**

```java
public enum Phase {
    SOLID, LIQUID, GAS;
    
    public enum Transition {
        MELT(SOLID, LIQUID), FREEZE(LIQUID, SOLID),
        BOIL(LIQUID, GAS), CONDENSE(GAS, LIQUID),
        SUBLIME(SOLID, GAS), DEPOSIT(GAS, SOLID);
        
        private final Phase from;
        private final Phase to;
        
        Transition(Phase from, Phase to) {
            this.from = from;
            this.to = to;
        }
        
        // 상전이 맵을 초기화한다.
        private static final Map<Phase, Map<Phase, Transition>> m = 
            	Stream.of(values()).collect(groupingBy(t -> t.from,
                      	() -> new EnumMap<>(Phase.class),
                        toMap(t -> t.to, t -> t,
                        (x, y) -> y, () -> new EnumMap<>(Phase.class))));
        
        public static Transition from(Phase from, Phase to) {
            return m.get(from).get(to);
        }
    }
}
```

* 위 코드에서 상전(Transition)이 맵을 초기화하는 코드는 제법 복잡하다.



* 이 맵의 타입인 `Map<Phase, Map<Phase,Transition>>`은 **"이전 상태에서 '이후 상태에서 전이로의 맵'에 대응 시키는 맵"이라는 뜻**이다.

  * 이러한 맵의 맵을 초기화하기 위해 수집기**(java.util.stream.Collector)** 2개를 차례로 사용했다.

  

  * **첫 번째 수집기**인 **groupingBy**에서는 **전이를 이전 상태를 기준으로 묶고**, **두 번째 수집기**인 **toMap**에서는 **이후 상태를 전이에 대응**시키는 **EnumMap**을 생성한다.

  

  * **두 번째 수집기의 병합 함수인 (x, y) -> y는 선언만 하고 실제로는 쓰이지 않는데**, 이는 단지 **EnumMap**을 얻으려면 **맵 팩토리**가 필요하고 **수집기들은 점층적 팩토리를 제공**하기 때문이다.



* 이제 여기에 새로운 상태인 플라스마(PLASMA)를 추가해보자.

  * 이 상태와 연결된 전이는 2개다.

  

  * 첫 번째는 기체에서 플라스마로 변하는 이온화(IONIZE)이고, 둘째는 플라스마에서 기체로 변하는 탈이온화(DEIONIZE)다.

  

  * 배열로 만든 코드 에서는 해당 내용을 수정하려면 새로운 상수를 Phase에 1개, Phase.Transition에 2개를 추가하고, 원소 9개짜리인 배열들의 배열을 원소 16개짜리로 교체해야 한다.

    * 원소 수를 너무 적거나 많이 기입하거나, 잘못된 순서로 나열하면 런타임에 문제를 일으킬 것이다.

    

  * <span style="color:red;">반면</span>, **EnumMap** 버전에서는 상태 목록에 PLASMA를 추가하고, 전이 목록에 IONIZE(GAS, PLASMA)와 DEIONIZE(PLASMA, GAS)만 추가하면 끝이다.



<hr>



💎 **EnumMap 버전에 새로운 상태 추가하기**

```java
public enum Phase {
    SOLID, LIQUID, GAS, PLASMA;
    
    public enum Transition {
        MELT(SOLID, LIQUID), FREEZE(LIQUID, SOLID),
        BOIL(LIQUID, GAS), CONDENSE(GAS, LIQUID),
        SUBLIME(SOLID, GAS), DEPOSIT(GAS, SOLID),
        IONIZE(GAS, PLASMA), DEIONIZE(PLASMA, GAS);
        
        .. //나머지 코드는 그대로다.
    }
}
```

*  실제 내부에서는 맵들의 맵이 배열들의 배열로 구현되니 낭비되는 공간과 시간도 거의 없이 명확하고 안전하고 유지보수하기 좋다.



<hr>



> 배열의 인덱스를 얻기 위해 ordinal을 쓰는 것은 일반적으로 좋지 않으니, 대신 EnumMap을 사용하라.
>
> 다차원 관계는 EnumMap<..., EnumMap<...>>으로 표현하라.
>
> "애플리케이션 프로그래머는 Enum.ordinal을 (웬만해서는) 사용하지 말아야 한다"는 
>
> 일반 원칙의 특수한 사례다.







```
참조 - 이펙티브 자바 3/E - 조슈아 블로크
```

