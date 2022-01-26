---
title: 프록시 (Proxy) 패턴
categories:
- DesignPattern
toc: true
toc_sticky: true
toc_label: 목차
---

## 🔗 프록시 (Proxy) 패턴이란?

* **프록시 패턴은 구조 패턴 중 하나로**, 어떤 **다른 객체로 접근하는 것을 통제**하기 위해서 **그 객체의 대리자**나 **자리표시자의 역할을 하는 객체를 제공**하는 패턴이다.

  

* <span style="color:red">즉</span>, **실제 기능을 수행하는 객체(Real Object)** <span style="color:red;">대신 가상의 객체(Proxy Object)를 사용</span>해 **로직의 흐름을 제어**하는 디자인 패턴이다.

  * 프록시 패턴을 사용하는 경우는 어**떤 클래스의 객체 생성이 오래 걸릴 때** 그 일을 분업을 하여 **proxy 클래스에서 처리 할 수 있는 부분은 처리를 하고** <span style="color:red;">proxy 클래스에서 처리할 수 없는 작업에 대해서만 실제 클래스의 객체를 생성하고 위임</span>하는 방식을 취한다.



* **Spring Framework**의 <span style="color:red;">AOP</span>도 **프록시 기반의 구현체**이다.

  

<hr>



##### 💎 프록시 패턴 특징

* 원래 하려던 기능을 수행하며 **그 외의 부가적입 작업(로깅, 인증, 네트워크 통신 등)을 수행** 할 수 있다.



* **비용이 많이드는 연산**(DB 쿼리, 대용량 텍스트 파일 등)을 **실제로 필요한 시점에 수행**할 수 있다.



* **실제 객체의 리소스가 무거운 경우**, 프록시 객체에서 간단한 처리를 하거나 기본 객체를 캐싱 처리함으로써 부하를 줄일 수있다.



* **실제 객체에 대한 수정 없이** 클라이언트에서의 사용과 **기본 객체 사이에 일련의 로직을 프록시 객체를 통해 넣을 수 있다.**



* **프록시는** 기본 객체와 요청 사이에 있기 때문에 **일종의 방패(보안)의 역할**도 한다.



* **사용자 입장에서는 프록시 객체나 실제 객체나 사용법이 유사**하므로 구조나 코드 구현이 간단하다.



<hr>



💎 **CommandExecutor.java **

* 프록시 패턴에 사용될 인터페이스

```java
package StructurePattern.ProxyPattern;

/*
프록시 패턴은 어떤 객체에 대하여 접근할 때에 Wrapper Class를 두어 접근에 대한 통제(Control access)를 위해 사용합니다.
 */
public interface CommandExecutor {

    public void runCommand(String cmd) throws Exception;

}
```



<br>

💎 **CommandExecutorImpl.java**

* 프록시 패턴에 사용될 인터페이스를 확장한 클래스

```java
package StructurePattern.ProxyPattern;

public class CommandExecutorImpl implements CommandExecutor {
    @Override
    public void runCommand(String cmd) throws Exception {
        Runtime.getRuntime().exec(cmd);
        System.out.println("'" + cmd + "' command executed.");
    }
}
```

<br>



💎 **CommandExecutorProxy.java**

* 실제 수행할 객체를 제어할 프록시 클래스

```java
package StructurePattern.ProxyPattern;

public class CommandExecutorProxy implements CommandExecutor {

    private boolean isAdmin;
    private CommandExecutor commandExecutor;

    public CommandExecutorProxy(String user, String pwd) {
        if ( "really".equals(user) && "holly".equals(pwd) ) {
            isAdmin = true;
        }
        commandExecutor = new CommandExecutorImpl();

    }

    @Override
    public void runCommand(String cmd) throws Exception {
        if ( isAdmin ) {
            commandExecutor.runCommand(cmd);
        }
        else {
            if ( cmd.trim().startsWith("rm") ) {
                throw new Exception("rm command is not allowd for non-admin users.");
            }
            else {
                commandExecutor.runCommand(cmd);
            }
        }
    }
}
```

* 위 프록시 클래스에서의 **runCommand** 메서드는 **Admin** [관리자] 이냐 아니냐에 따라 **실행 명령을 제한[제어]** 한다.

  

💎 **실행 테스트**

```java
package StructurePattern.ProxyPattern;

public class ProxyPatternTest {

    public static void main(String[] args) {

        CommandExecutor executor = new CommandExecutorProxy("really", "wrong_pwd");
        try {
            executor.runCommand("ls -ltr");
            executor.runCommand("rm -rf abc.pdf");
        } catch (Exception ex) {
            System.out.println("Exception Message :: " + ex.getMessage());
        }
    }
}
```

* 위 코드의 첫 번째 **Command**인 ls -ltr은 정상적으로 수행되지만, 두 번째 Command는 관리자 권한이 없어서 프**록시 클래스가 접근을 제어** 한다.
