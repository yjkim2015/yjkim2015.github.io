---
title: 과도한 동기화는 피하라 - Effective Java[79]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗  응답 불가와 안전 실패를 피하려면 동기화 메서드나 동기화 블록 안에서는 제어를 절대로 클라이언트에 양도하면 안 된다.

* 예를 들어 **동기화된 영역 안에서는 재정의할 수 있는 메서드는 호출하면 안 되며**, **클라이언트가 넘겨준 함수 객체를 호출해서도 안 된다.**

  * 동기화된 영역을 포함한 클래스 관점에서는 이런 메서드는 모두 바깥 세상에서 온 외계인이다.

    

  * 그 메서드가 무슨 일을 할지 알지 못하며 통제할 수도 없다는 뜻이다.

  

  * **외계인 메서드(alien method)**가 하는 일에 따라 **동기화된 영역은 예외를 일으키거나, 교착상태에 빠지거나, 데이터를 훼손할 수도 있다.**

  

* **구체적인 예**로 아래의 어떤 집합(Set)을 감싼 래퍼 클래스이고, 이 클래스의 클라이언트는 집합에 원소가 추가되면 알림을 받을 수 있다.

  * 바로 관찰자(Observer) 패턴이다. 


<br>



💎 **잘못된 코드, 동기화 블록 안에서 외계인 메서드를 호출한다.**

```java
public class ObservableSet<E> extends ForwardingSet<E> {
    public ObservableSet(Set<E> set) { super(set); }
    
    private final List<SetObserver<E>> observers = new ArrayList<>();
    
    public void addObserver(SetObserver<E> observer) {
        synchronized(observers) {
			observers.add(observer);
        }
    }
    
    public boolean removeObserver(SetObserver<E> observer) {
        synchronized(observers) {
            return observers.remove(observer);
        }
    }
    
    public void notifyElementAdded(E element) {
        synchronized(observers) {
			for (SetObserver<E> observer : observers) {
                observer.added(this)
            }
        }
    }
    
    @Override
    public boolean add(E element) {
        boolean added = super.add(element);
        if (added) {
            notifyElementAdded(element);
        }
        return added;
    }
    
    @Override
    public booelan addAll(Collection<? extends E> c) {
        boolean result = false;
        for (E element : c) {
            result |= add(element);
        }
        return result;
    }
}
```

* 관찰자들은 **addObserver**와 **removeObserver** 메서드를 호출해 구독을 신청하거나 해지한다.

  * 두 경우 모두 다음 콜백 인터페이스의 인스턴스를 메서드에 건넨다.

  

```java
@FunctionalInterface public interface SetObserver<E> {
    //ObservableSet에 원소가 더해지면 호출한다.
    void added(ObservableSet<E> set, E element);
}
```

* 이 인터페이스는 구조적으로 `BiConsumer<ObserverableSet<E>,E>`와 똑같다.

  * 그럼에도 커스텀 함수형 인터페이스를 정의한 이유는 더 직관적이고 다중콜백을 지원하도록 확장할 수 있어서다.

  

  * 하지만 **BiConsumer**를 그대로 사용했더라도 별 무리는 없었을 것이다.

<hr>



💎**눈으로 보기에 ObservableSet은 잘 동작할 것 같다. 과연?**

```java
public static void main(String[] args) {
    ObservableSet<Integer> set = new ObservableSet<>(new HashSet<>());
    
    set.addObserver(new SetObserver<>() {
       System.out.println(e);
       if (e == 23) {
           s.removeObserver(this);
       }
    });
    
    for (int i = 0 ; i < 100; i++) {
		set.add(i);
    }
}
```

* 위 프로그램은 0부터 23까지 출력한 후 관찰자 자신을 구독해지한 다음 조용히 종료할 것으로 예상된다.

  * 하지만 실제로 실행해보면 이 프로그램은 23까지 출력한 다음 **ConcurrentModificationException**을 던진다.

  

  * 관찰자의 **added** 메서드 호출이 일어난 시점이 **notifyElementAdded**가 관찰자들의 리스트를 순회하는 도중이기 때문이다.

  

  * **added** 메서드는 **ObservableSet**의 **removeObserver** 메서드를 호출하고, 이 메서드는 다시 **observers.remove** 메서드를 호출한다. 

    * <span style="color:red;">여기서 문제가 발생한다.</span>

    

    * 리스트에서 원소를 제거하려 하는데, 마침 지금은 이 리스트를 순회하는 도중이다.

    

    * <span style="color:red;">즉, 허용되지 않은 동작이다.</span>

    

    * **notifyElementAdded** 메서드에서 수행하는 순회는 동기화 블록 안에 있으므로 동시 수정이 일어나지 않도록 보장하지만, 정작 자신이 콜백을 거쳐 되돌아와 수정하는 것까지 막지는 못한다.

    

<hr>



💎 **쓸데 없이 백그라운드 스레드를 사용하는 관찰자**

* 이번에는 이상한 것을 시도해보자.
  * 구독해지를 하는 관찰자를 작성하는데, **removeObserver**를 **직접 호출하지 않고** 실행자 서비스(**ExecutorService**)를 사용해 **다른 스레드에게 부탁한다.**

```java
set.addObserver(new SetObserver<>() {
    public void  added(ObservableSet<Integer> s, Integer e) {
        System.out.println(e);
        if (e == 23) {
            ExecutorService exec = Executors.newSingleThreadExecutor();
            try {
                exec.submit(() -> s.removeObserver(this)).get();
            } catch (ExecutionException | InterruptedException ex) {
                throw new AssertionError(ex);
            } finally {
                exec.shutdown();
            }
        }
    }
});
```

* **위 프로그램을 실행하면** 예외는 나지 않지만 **교착상태에 빠진다.**

  * 백그라운드 쓰레드가 **s.removeObserver**를 호출하면 관찰자를 잠그려 시도하지만 **락을 얻을 수 없다.**

  

  * **메인 스레드가 이미 락을 쥐고 있기 때문이다.**

  

  * 그와 동시에 메인스레드는 백그라운드 쓰레드가 관찰자를 제거하기만을 기다리는 중이다.

  

  * <span style="color:red;">바로 교착 상태다!</span>



* 사실 관찰자가 자신을 구독해지하는 데 굳이 백그라운드 스레드를 이용할 이유가 없으니 좀 억지스러운 예지만, 여기서 보인 문제 자체는 진짜다. 실제 시스템에서도 동기화된 영역 안에서 외계인 메서드를 호출하여 교착상태에 빠지는 사례는 자주 있다.



* 앞서의 예외와 교착상태에서는 운이 좋았다.

  * 동기화 영역이 보호하는 자원(**관찰자**)는 외계인 메서드(**added**)가 호출될 때 일관된 상태였으니 말이다.

  

<hr>



💎 **똑같은 상황이지만 불변식이 임시로 깨진 경우라면 어떻게 될까?**

* **자바 언어의 락은 재진입(reentrant)를 허용**하므로 **교착상태에 빠지지는 않는다.**

  * **예외를 발생시킨 첫 번째 예에서라면** 외계인 메서드를 호출하는 스레드는 이미 락을 쥐고 있으므로 다음번 락 획득도 성공한다.

  

  * 그 락이 보호하는 데이터에 대해 개념적으로 관련이 없는 다른 작업이 진행 중인데도 말이다.

  

  * 이것 때문에 실로 참혹한 결과가 빚어질 수도 있다.

  

  * 문제의 주 원인은 락이 제 구실을 하지 못했기 때문이다.
    * 재진입 가능 락은 객체 지향 멀티스레드 프로그램을 쉽게 구현할 수 있도록 해주지만, 응답 불가(교착상태)가 될 상황을 안전 실패(데이터 훼손)로 변모시킬 수도 있다.



* 다행히 이런 문제는 아래와 같이 **대부분 어렵지 않게 해결할 수 있다.**

  * <span style="color:red;">외계인 메서드 호출을 동기화 블록 바깥으로 옮기면 된다.</span>

  

  * **notifyElementAdded** 메서드에서라면 **관찰자 리스트를 복사해 쓰면** 락 없이도 안전하게 순회할 수 있다.

  

  * **이 방식을 적용하면** 앞서의 <span style="color:red;">예외 발생과 교착상태 증상이 사라진다.</span>



<hr>


💎 **외계인 메서드를 동기화 블록 바깥으로 옮겼다.**

```java
private void notifyElementAdded(E element) {
    List<SetObserver<E>> snapshot = null;
    synchronized(observers) {
        shapshot = new ArrayList<>(observers);
    }
    for (SetObserver<E> observer : snapshot) {
        observer.added(this, element);
    }
}
```

* 사실 외계인 메서드 호출을 동기화 블록 바깥으로 옮기는 더 나은 방법이 있다.

  * **자바의 동시성 컬렉션 라이브러리의 CopyOnWriteArrayList**가 정확히 이 목적으로 특별히 설계된 것이다.

  

  * 이름이 말해주듯 **ArrayList**를 구현한 클래스로, 내부를 변경하는 작업은 항상 깨끗한 복사본을 만들어 수행해주도록 구현했다.

    * **내부의 배열은 절대 수정되지 않으니 순회할 때 락이 필요 없어 매우 빠르다.**

    

    * 다른 용도로 쓰인다면 **CopyOnWriteArrayList**는 끔찍이 느리겠지만, 수정할 일은 드물고 순회만 빈번히 일어나는 관찰자 리스트 용도로는 최적이다.



* 위 처럼 동기화 영역 바깥에서 호출되는 **메서드를 열린 호출(open call)**이라 한다.

  * 외계인 메서드는 얼마나 오래 실행될지 알 수 없는데, **동기화 영역 안에서 호출된다면 그동안 다른 스레드는 보호된 자원을 사용하지 못하고 대기해야만 한다.**

  

  * <span style="color:red;">따라서 열린 호출은 실패 방지 효과외에도 동시성 효율을 크게 개선해준다.</span>

<br>



💎 **CopyOnWriteArrayList를 사용해 구현한 스레드 안전하고 관찰 가능한 집합**

```java
private final List<SetObserver<E>> observers = new CopyOnWriteArrayList<>();

public void addObserver(SetObserver<E> observer) {
	observers.add(observer);
}

public boolean removeObserver(SetObserver<E> observer) {
    return observers.remove(observer);
}

private void notifyElementAdded(E element) {
    for (SetObserver<E> observer : observers) {
        observers.added(this, element);
    }
}
```



<hr>



##### 💎 동시성 효율 향상의 기본 규칙은 동기화 영역에서는 가능한 한 일을 적게 하는 것이다.

* 락을 얻고, 공유 데이터를 검사하고, 필요하면 수정하고, 락을 놓는다.



* 오래 걸리는 작업이라면 동기화 영역 바깥으로 옮기는 방법을 찾아보자.	

<hr>



##### 💎  자바의 동기화 비용은 빠르게 낮아져 왔지만, 과도한 동기화를 피하는 일은 과거 어느 때보다 중요하다.

* 멀티코어가 일반화된 오늘날, 과도한 동기화가 초래하는 **진짜 비용은 락을 얻는 데 드는 CPU 시간이 아니다.**

  * **바로 경쟁하느라 낭비하는 시간, 즉 병렬로 실행할 기회를 잃고, 모든 코어가 메모리를 일관되게 보기 위한 지연시간이 진짜 비용이다.**

  

  * **가상머신의 코드 최적화를 제한한다는 점도 과도한 동기화의 또 다른 숨은 비용이다**.



<hr>



##### 💎 가변 클래스를 작성하려거든 다음 두 선택지 중 하나를 따르자.

* **첫 번째**, 동기화를 전혀 하지 말고, 그 클래스를 동시에 사용해야 하는 클래스가 외부에서 알아서 동기화하게 하자.



* **두 번째**, 동기화를 내부에서 수행해 스레드 안전한 클래스로 만들자.
  * 단, 클라이언트가 외부에서 객체 전체에 락을 거는 것보다 동시성을 월등히 개선할 수 있을 때만 두 번째 방법을 선택해야 한다.



* **java.util**은 (이제 구식이 된 **Vector**와 **Hashtable**을 제외하고) 첫 번째 방식을 취했고, **java.util.concurrent**는 두 번째 방식을 취했다.



* 자바도 초창기에는 이 지침을 따르지 않은 클래스가 많았다.

  * ex) **StringBuffer** 인스턴스는 거의 항상 단일 스레드에서 쓰였음에도 내부적으로 동기화를 수행했다.

    * 뒤늦게 **StringBuilder**가 등장한 이유이기도 하다(**StringBuilder**는 그저 동기화하지 않은 **StringBuffer**이다)

    

  * 비슷한 이유로, 스레드 안전한 의사 난수 발생기인 **java.util.Random**은 동기화하지 않은 버전인 **java.util.concurrent.ThreadLocalRandom**으로 대체되었다.

  

  * 선택하기 어렵다면 동기화하지 말고, 대신 문서에 **"스레드 안전하지 않다"**고 명시하자.



* 클래스를 내부에서 동기화하기로 했다면, 락 분할, 락 스트라이핑, 비차단 동시성 제어 등 다양한 기법을 동원해 동시서을 높여줄 수 있다.



<hr>



##### 💎 여러 스레드가 호출할 가능성이 있는 메서드가 정적 필드를 수정한다면 그 필드를 사용하기 전에 반드시 동기화해야 한다.(비결정적 행동도 용인하는 클래스라면 상관없다)

* 그런데 클라이언트가 여러 스레드로 복제돼 구동되는 상황이라면 다른 클라이언트에서 이 메서드를 호출하는 걸 막을 수 없으니 외부에서 동기화할 방법이 없다.

  * 결과적으로, 이 정적 필드가 심지어 **private**라도 서로 관련 없는 스레드들이 동시에 읽고 수정할 수 있게 된다.

  

  * 사실상 전역 변수와 같아진다는 뜻이다.





<hr>



> **교착상태와 데이터 훼손을 피하려면 동기화 영역 안에서 외계인 메서드를 절대 호출하지 말자.**
>
> **일반화해 이야기하면, 동기화 영역 안에서의 작업은 최소한으로 줄이자.**
>
> 
>
> 가변 클래스를 설계할 때는 스스로 동기화해야 할지 고민하자.
>
> 
>
> 멀티코어 세상인 지금은 **과도한 동기화를 피하는 게 과거 어느 때보다 중요하다.**
>
> **합당한 이유가 있을 때만 내부에서 동기화하고, 동기화했는지 여부를 문서에 명확히 밝히자.**










```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

