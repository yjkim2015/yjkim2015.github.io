---
title: Spring boot Security - 2
categories:
- SECURITY
toc: true
toc_sticky: true
toc_label: 목차
---

##### 사용자 정의 보완 기능 구현



지난 블로깅에서 Security 의존성만 추가해 간단한 보안 시스템을 만들었다면

이번 블로깅에서는 추가적으로 보안 기능을 설정 할 것이다.



**WebSecurityConfigurerAdapter**는 스프링 시큐리티의 웹 보안 기능 초기화 및 설정하는 클래스이다.

이 클래스를 상속받아 추가적으로 설정한다.

![image-20210111212616335](../../assets/images/2021-01-11-spring-boot-security/image-20210111212616335.png)



아래와 같이 SecurityConfig.java를 생성한다. 

![image-20210111222814699](../../assets/images/2021-01-11-spring-boot-security/image-20210111222814699.png)

계정과 암호를 별도로 설정한다. application.properties

![image-20210111214120378](../../assets/images/2021-01-11-spring-boot-security/image-20210111214120378.png)

위와 같이 설정 후 어플리케이션을 실행한다.

![image-20210111222910375](../../assets/images/2021-01-11-spring-boot-security/image-20210111222910375.png)

![image-20210111222939502](../../assets/images/2021-01-11-spring-boot-security/image-20210111222939502.png)