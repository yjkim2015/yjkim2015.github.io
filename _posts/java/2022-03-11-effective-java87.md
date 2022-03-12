---
title: 커스텀 직렬화 형태를 고려해보라 - Effective Java[87]
categories:
- Java
toc: true
toc_sticky: true
toc_label: 목차
---



##### 🔗 개발 일정에 쫓기는 상황에서는 API 설계에 노력을 집중하는 편이 나을 것이다.

* 이 말은 종종 다음 릴리스에서 제대로 다시 구현하기로 하고, 이번 릴리스에서는 그냥 동작만 하도록 만들어 놓으라는 뜻이다.



* 보통은 크게 문제되지 않는 전략이다.



* 하지만 클래스가 **Serializable**을 구현하고 기본 직렬화 형태를 사용한다면 다음 릴리스 때 버리려 한 현재의 구현에 영원히 발이 묶이게 된다.

  * 기본 직렬화 형태를 버릴 수 없게 되는 것이다.

  

  * 실제로도 **BigInteger** 같은 일부 자바 클래스가 이 문제에 시달리고 있다.



##### 💎 먼저 고민해보고 괜찮다고 판단될 때만 기본 직렬화 형태를 사용하라.

* 기본 직렬화 형태는 유연성, 성능, 정확성 측면에서 신중히 고민한 후 합당할 때만 사용해야 한다.
  * 일반적으로 직접 설계하더라도 기본 직렬화 형태와 거의 같은 결과가 나올 경우에만 기본 형태를 써야 한다.



<hr>



##### 💎 객체의 물리적 표현과 논리적 내용이 같다면 기본 직렬화 형태라도 무방하다.

* 예컨대 사람의 성명을 간략히 표현한 다음 예는 기본 직렬화 형태를 써도 괜찮을 것이다.



💎 **기본 직렬화 형태에 적합한 후보**

```java
public class Name implements Serialziable {
    /**
    * 성. null이 아니어야 함.
    * @serial
    */
    private final String lastName;
    
    /**
    * 이름. null이 아니어야 함.
	* @serial
    */
    private final String firstName;
    
    /**
    * 중간이름, 중간이름이 없다면 null
	* @serial
	*/
    private final String middleName;
    
    ... // 나머지 코드는 생략
}
```

* 성명은 논리적으로 이름, 성, 중간이름이라는 3개의 문자열로 구성되며, 앞 코드의 인스턴스 필들들은 이 논리적 구성요소를 정확히 반영했다.



<hr>



##### 💎 기본 직렬화 형태가 적합하다고 결정했더라도 불변식 보장과 보안을 위해 readObject 메서드를 제공해야 할 때가 많다.

* 위의 **Name** 클래스의 경우에는 **readObject** 메서드가 **lastName**과 **firstName** 필드가 **null**이 아님을 보장해야 한다.



```
Name의 세 필드 모두 private임에도 문서화 주석이 달려있다.

이 필드들은 결국 클래스의 직렬화 형태에 포함되는 공개 API에 속하며 공개 API는 모두 문서화해야 하기 때문이다.

private 필드의 설명을 API 문서에 포함하라고 자바독에 알려주는 역할은 @serial 태그가 한다.

@serial 태그로 기술한 내용은 API 문서에서 직렬화 형태를 설명하는 특별한 페이지에 기록된다.
```



<hr>



💎 **기본 직렬화 형태에 적합하지 않은 클래스**

```java
public final class StringList implements Serializable {
    private int size = 0;
    private Entry head = null;
    
    private static class Entry implements Serializable {
        String data;
        Entry next;
        Entry previous;
    }
    
    ... // 나머지 코드는 생략
}
```

* **논리적으로 이 클래스는 일련의 문자열을 표현한다.**

  * **물리적으로는 문자열들을 이중 연결 리스트로 연결했다.**

  

  * 이 클래스에 기본 직렬화 형태를 사용하면 각 노드의 양방향 연결 정보를 포함해 모든 엔트리(Entry)를 철두철미하게 기록한다.



<hr>



##### 💎객체의 물리적 표현과 논리적 표현의 차이가 클 때 기본 직렬화 형태를 사용하면 크게 네 가지 면에서 문제가 생긴다.

* **공개 API가 현재의 내부 표현 방식에 영구히 묶인다.**

  * 위의 예에서 **private** 클래스인 **StringList.Entry**가 공개 **API**가 되어 버린다.

  

  * 다음 릴리즈에서 내부 표현 방식을 바꾸더라도 **StringList** 클래스는 여전히 연결 리스트로 표현된 입력도 처리할 수 있어야 한다.

  

  * **즉, 연결 리스트를 더는 사용하지 않더라도 관련 코드를 절대 제거 할 수 없다.**



* **너무 많은 공간을 차지할 수 있다.**

  * 앞 예의 직렬화 형태는 연결 리스트의 모든 엔트리와 연결 정보까지 기록했지만, 엔트리와 연결 정보는 내부 구현에 해당하니 직렬화 형태에 포함할 가치가 없다.

  

  * 이처럼 직렬화 형태가 너무 커져서 디스크에 저장하거나 네트워크로 전송하는 속도가 느려진다.



* **시간이 너무 많이 걸릴 수 있다.**
  * 직렬화 로직은 객체 그래프의 위상에 관한 정보가 없으니 그래프를 직접 순회해볼 수밖에 없다.
  * 위의 예에서는 간단히 다음 참조를 따라 가보는 정도로 충분하다.



* **스택 오버플로를 일으킬 수 있다.**
  * 기본 직렬화 과정은 객체 그래프를 재귀 순회하는데, 이 작업은 중간 정도 크기의 객체 그래프에서도 자칫 스택 오버플로를 일으킬 수 있다.



<hr>



##### 💎 StringList를 위한 합리적인 직렬화 형태

* 단순히 리스트가 포함한 문자열의 개수를 적은 다음, 그 뒤로 문자열들을 나열하는 수준이면 될 것이다.

  * **StringList**의 <span style="color:red;">물리적인 상세 표현은 배제한 채 논리적인 구성만 담는 것이다.</span>

  

  * 아래는 **StringList**를 이 방식으로 구현한 모습이다

  

  * **wrtieObject**와 **readObject**가 직렬화 형태를 처리한다.

  

  * **한 가지, 일시적이란 뜻의 transient 한정자는 해당 인스턴스 필드가 기본 직렬화 형태에 포함되지 않는다는 표시다.**

<br>



💎 **합리적인 커스텀 직렬화 형태를 갖춘 StringList**

```java
public final class StringList implements Serializable {
    private transient int size = 0;
    private transient Entry head = null;
    
    //이제는 직렬화되지 않는다.
    private static class Entry {
		String data;
        Entry next;
        Entry previous;
    }
    
    //지정한 문자열을 이 리스트에 추가한다.
    public final void add(String s) { ... }
    
    /**
    *
    * 이 {@code StringList} 인스턴스를 직렬화한다.
    * 
    * @serialData 이 리스트의 크기(포함된 문자열의 개수)를 기록한 후
    * ({@code int}), 이어서 모든 원소를(각각은 {@code String})
	* 순서대로 기록한다.
    */
    
    private void writeObject(ObjectOutputStream s) throws IOException {
        s.defaultWriteObject();
        s.writeInt(size);
        
        //모든 원소를 올바른 순서로 기록한다.
        for (Entry e = head; e != null; e = e.next) 
            s.writeObject(e.data);
        }
    }

	private void readObject(ObjectInputStream s) throws IOException, ClassNotFoundException {
        s.defaultReadObject();
        int numElements = s.readInt();
        
        //모든 원소를 읽어 이 리스트에 삽입한다.
        for (int i = 0; i < numElements; i++) {
            add((String) s.readObject());
        }
    }
    ... // 나머지 코드는 생략
}
```

* **StringList**의 필드 모두가 **transient**더라도 **writeObject**와 **readObject**는 각각 가장 먼저 **defaultWriteObject**와 **defaultReadObject**를 호출한다.



* 클래스의 인스턴스 필드 모두가 **transient**면 **defaultWriteObject**와 **defaultReadObject**를 호출하지 않아도 된다고 들었을지 모르지만, **직렬화 명세는 이 작업을 무조건 하라고 요구한다.**

  * **이렇게 해야 향후 릴리즈에서 transient가 아닌 인스턴스 필드가 추가되더라도 상호(상위와 하위 모두) 호환되기 때문이다.**

  

  * **신버전 인스턴스를 직렬화한 후 구버전으로 역직렬화하면 새로 추가된 필드들은 무시될 것이다.**

  

  * 구버전 **readObject** 메서드에서 **defaultReadObject**를 호출하지 않는다면 역직렬화할 때 **StreamCorruptedException**이 발생할 것이다.

<br>

```
writeObject는 private 메서드임에도 문서화 주석이 달려 있다.
앞서 Name 클래스의 private 필드에 문서화 주석을 단 이유의 연장선이다.

이 private 메서드는 직렬화 형태에 포함되는 공개 API에 속하며, 공개 API는 모두 문서화해야 한다.

필드용의 @serial 태그처럼 메서드에 달린 @serialData 태그는 자바독 유틸리티에게 이 내용을 직렬화 형태 페이지에 추가하도록 요청하는 역할을 한다.
```



<hr>



💎 **개선 버전 StringList의 성능**

* 개선 버전의 **StringList**의 직렬화 형태는 원래 버전의 절반 정도의 공간을 차지한다.



* 또한 스택 오버플로가 전혀 발생하지 않아 실질적으로 직렬화 할 수 있는 크기 제한이 없어졌다.



<hr>



💎  **StringList에서도 기본 직렬화 형태는 적합하지 않았지만 상태가 훨씬 심한 클래스들도 있다.**

* **StringList**의 기본 직렬화 형태는 비록 유연성과 성능이 떨어졌더라도, 객체를 직렬화한 후 역직렬화하면 원래 객체를 그 불변식까지 포함해 제대로 복원해낸다는 점에서 정확하다고 할 수 있다.

  

* <span style="color:red;">하지만 그 불변식이 세부 구현에 따라 달라지는 객체에서는 이 정확성마저 깨질 수 있다.</span>

  * ex) 해시 테이블은 물리적으로 키-값 엔트리들을 담은 해시 버킷을 차례로 나열한 형태다.

  

  * 어떤 엔트리를 어떤 버킷에 담을지는 키에서 구한 해시코드가 결정하는데, 그 계산 방식은 구현에 따라 달라질 수 있다.

  

  * 사실 계산할 때마다 달라지기도 한다.

  

  * **따라서 해시테이블에 기본 직렬화를 사용하면 불변식이 심각하게 훼손된 객체들이 생겨날 수 있는 것이다.**



<hr>



##### 💎 기본 직렬화를 수용하든 하지 않든 defaultWriteObject 메서드를 호출하면 transient로 선언하지 않은 모든 인스턴스 필드가 직렬화된다.

* > 따라서 transient로 선언해도 되는 인스턴스 필드에는 모두 transient 한정자를 붙여야 한다.



* 캐시된 해시 값처럼 다른 필드에서 유도되는 필드도 여기 해당한다.

  * **JVM**을 실행할 때마다 값이 달라지는 필드도 마찬가지인데, 네이티브 자료구조를 가리키는 long 필드가 여기 속한다.

  

  * **해당 객체의 논리적 상태와 무관한 필드라고 확신할 때만 transient 한정자를 생략해야 한다.**
    * 그래서 커스텀 직렬화 형태를 사용한다면, 앞서의 **StringList** 예에서처럼 대부분의 인스턴스 필드를 **transient**로 선언해야 한다.



<hr>



##### 💎 기본 직렬화를 사용한다면 transient 필드들은 역직렬화될 때 기본값으로 초기화됨을 잊지 말자.

* 객체 참조 필드는 **null**로, 숫자 기본 타입 필드는 0으로, **boolean** 필드는 **false**로 초기화된다.



* **기본값을 그대로 사용해서는 안 된다면** <span style="color:red;">readObject 메서드에서 defaultReadObject를 호출한 다음, 해당 필드를 원하는 값으로 복원하자.</span>
  * 혹은 그 값을 처음 사용할 때 초기화하는 방법도 있다.



<hr>



##### 💎 기본 직렬화 사용 여부와 상관없이 객체의 전체 상태를 읽는 메서드에 적용해야 하는 동기화 메커니즘을 직렬화에도 적용해야 한다.

* 따라서 에컨대 모든 메서드를 **synchronized**로 선언하여 스레드 안전하게 만든 객체에서 기본 직렬화를 사용하려면 **writeObject**도 다음 코드처럼 **synchronized**로 선언해야 한다.

<br>

💎 **기본 직렬화를 사용하는 동기화된 클래스를 위한 writeObject 메서드**

```java
private synchronized void writeObject(ObjectOutputStream s) throws IOException {
    s.defaultWriteObject();
}
```

* **writeObject** 메서드 안에서 동기화하고 싶다면 클래스의 다른 부분에서 사용하는 락 순서를 똑같이 따라야 한다.
  * 그렇지 않으면 **자원 순서 교착상태(resource-ordering deadlock)**에 빠질 수 있다.



<hr>



##### 💎 어떤 직렬화 형태를 택하든 직렬화 가능 클래스 모두에 직렬 버전 UID를 명시적으로 부여하자.

* 이렇게 하면 직렬 버전 **UID**가 일으키는 잠재적인 호환성 문제가 사라진다.

  * 성능도 조금 빨라지는데, 직렬 버전 **UID**를 명시하지 않으면 이 값을 생성하느라 복잡한 연산을 수행하기 때문이다.

  

  * 직렬 버전 **UID** 선언은 각 클래스에 아래 같은 한 줄만 추가해주면 끝이다.

```java
private static final long serialVersionUID = <무작위로 고른 long 값>;
```



* 새로 작성하는 클래스에서는 어떤 **long** 값을 선택하든 상관없다.
  * 클래스 일련번호를 생성해주는 **serialver** 유틸리티를 사용해도 되며, 그냥 생각나는 아무 값이나 선택해도 된다.
    * 직렬 버전 **UID**가 꼭 고유할 필요는 없다.



* 한편 직렬 버전 **UID**가 없는 기존 클래스를 구버전으로 직렬화된 인스턴스와 호환성을 유지한 채 수정하고 싶다면, 구버전에서 사용한 자동 생성된 값을 그대로 사용해야 한다.
  * 이 값은 직렬화된 인스턴스가 존재하는 구버전 클래스를 **serialver** 유틸리티에 입력으로 주어 실행하면 얻을 수 있다.



<hr>



💎 **기본 버전 클래스와의 호환성을 끊고 싶다면 단수히 직렬 버전 UID의 값을 바꿔주면 된다.**

* 이렇게 하면 기존 버전의 직렬화된 인스턴스를 역직렬화할 때 **InvalidClassException**이 던져질 것이다.



* 구버전으로 직렬화된 인스턴스들과의 호환성을 끊으려는 경우를 제외하고는 직렬 버전 **UID**를 절대 수정하지 말자.



<hr>



> 클래스를 직렬화하기로 했다면 어떤 직렬화 형태를 사용할지 심사숙고하기 바란다.
>
> 
>
> 자바의 기본 직렬화 형태는 객체를 직렬화한 결과가 해당 객체의 논리적 표현에 부합할 때만 사용하고,
>
> 그렇지 않으면 객체를 적절히 설명하는 커스텀 직렬화 형태를 고안하라
>
> 
>
> 직렬화 형태도 공개 메서드를 설계할 때에 준하는 시간을 들여 설계해야 한다.
>
> 한번 공개된 메서드는 향후 릴리즈에서 제거할 수 없듯이, 직렬화 형태에 포함된 필드도 마음대로 제거할 수 없다
>
> 
>
> 직렬화 호환성을 유지하기 위해 영원히 지원해야 하는 것이다.
>
> 잘못된 직렬화 형태를 선택하면 해당 클래스의 복잡성과 성능에 영구히 부정적인 영향을 남긴다.












```
참조 - 이펙티브 자바 3/E - 조슈아 블로크때
```

