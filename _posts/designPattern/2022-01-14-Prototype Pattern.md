---
title: 프로토타입 (Prototype) 패턴
categories:
- DesignPattern
toc: true
toc_sticky: true
toc_label: 목차
---

## 🔗 프로토타입 (Prototype) 패턴이란?

* **프로토타입은** 주로 실제 제품을 만들기에 앞서 **대략적인 샘플 정도의 의미**로 사용되는 단어이다.



* **프로토타입 패턴은** 객체를 생성하는 데 비용(시간과 자원)이 많이 들고,  **비슷한 객체가 이미 있는 경우에 사용되는 생성 패턴 중 하나**이다.



* 프로토타입 패턴은 **Original 객체를 clone() 메소드를 통해 새로운 객체에 복사**하여 필요에 따라 **수정하는 메커니즘을 제공**한다.



* 추상 팩토리 패턴과는 반대로 클라이언트 응용 프로그램 코드 내에서 **객체 창조자(creator)를 서브클래스(subclass)하는 것을 피할 수 있게 해준다.**



##### 💎 프로토타입 패턴 구현시 주의 사항

* 프로토타입 패턴 구현 시 java의 **clone()**을 이용하기 때문에 **생성하고자 하는 객체에 clone에 대한 Override를 요구한다.**
  * 이때 <span style="color:red;">반드시</span> 생성하고자 하는 **객체의 클래스에서 clone()이 정의되어야 한다.**



* 패턴 구현 시 우선 clone() 메소드를 선언하는 **추상 베이스 클래스**를 하나 만든다.
  * 다형적 생성자 기능이 필요한 클래스가 있다면, 그것을 앞서 만든 클래스를 상속받게 한 후 clone() 메소드 내의 코드를 구현한다.



* **얕은 복사 (Shallow Copy)**로 할 지, **깊은 복사(Deep Copy)**로 할 지에 대해서는 <span style="color:red;">선택적</span>으로 행하면 된다.



<hr>



💎 **Cloneable를 상속한 추상 베이스 클래스 - clone 선언 되어 있음**

```java
package CreationalPattern.PrototypePattern;

import java.util.ArrayList;
import java.util.List;

public class Employees implements Cloneable {

    private List<String> empList;

    public Employees() {
        empList = new ArrayList<>();
    }

    public Employees(List<String> empList) {
        this.empList = empList;
    }

    // DB 데이터를 조회하는것이라고 가정해보자.
    public void loadData() {
        empList.add("Pankaj");
        empList.add("Raj");
        empList.add("David");
        empList.add("Lisa");
    }

    public List<String> getEmpList() {
        return empList;
    }

    public void setEmpList(List<String> empList) {
        this.empList = empList;
    }

    @Override
    protected Employees clone() throws CloneNotSupportedException {
        List<String> temp = new ArrayList<>();
        for (String s : this.empList) {
            temp.add(s);
        }
        return new Employees(temp);
    }
}
```

* 위 코드를 보면 **clone() 메소드를 재정의**하기 위해 **Cloneable 인터페이스를 구현**한 것을 확인할 수 있다.
  * 여기서 사용되는 **clone()**은 empList에 대하여 **깊은 복사 (deep copy)**를 실시한다.



<hr>



💎 **clone 실행 main 메소드**

```java
package CreationalPattern.PrototypePattern;

import java.util.List;

public class PrototypePatternTest {
    public static void main(String[] args) throws CloneNotSupportedException {
        
        Employees emps = new Employees();
        emps.loadData();

        Employees cloneNew = (Employees) emps.clone();
        Employees cloneNew1 = (Employees) emps.clone();

        List<String> list = cloneNew.getEmpList();
        list.add("John");
        List<String> list1 = cloneNew1.getEmpList();
        list1.remove("Pankaj");

        //sout
        System.out.println("emps List : " + emps.getEmpList());
        System.out.println("empsNew List : " + list);
        System.out.println("empsNew1 List : " + list1);

    }
}
```

* 실행결과

```java
emps List : [Pankaj, Raj, David, Lisa]
empsNew List : [Pankaj, Raj, David, Lisa, John]
empsNew1 List : [Raj, David, Lisa
```



* **위 코드에서 만약 Employees 클래스가 clone()을 제공하지 않았다면**, loadData를 매번 호출하여 **DB로 부터 데이터를 직접 가져와야 했을 것**이고, 그로 인해 **상당히 큰 비용이 발생**했을 것이다.



* <span style="color:red;">하지만</span> **프로토타입을 사용한다면** 1회의 DB 접근을 통해 가져온 **데이터를 복사**하여 사용한다면 이를 해결할 수 있다. (<span style="color:red;">객체를 복사하는 것이 DB접근보다 훨씬 비용이 적다.</span>)
