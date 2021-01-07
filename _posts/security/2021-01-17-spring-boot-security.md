---
title: Spring boot Security - 1
categories:
-SECURITY
toc: true
toc_sticky: true
toc_label: 목차
---

##### 프로젝트 생성

![image-20210107220113406](../../assets/images/2021-01-17 Spring boot Security/image-20210107220113406.png)

![image-20210107220141727](../../assets/images/2021-01-17 Spring boot Security/image-20210107220141727.png)



##### Controller 생성 

![image-20210107232539351](../../assets/images/2021-01-17 spring boot security/image-20210107232539351.png)

##### 실행 (Security 적용 전)

![image-20210107232633723](../../assets/images/2021-01-17 spring boot security/image-20210107232633723.png)

##### POM.XML 설정 (Security dependency 추가)

![image-20210107232009891](../../assets/images/2021-01-17 spring boot security/image-20210107232009891.png)

##### 실행 (Security 적용 후)

![image-20210107232901989](../../assets/images/2021-01-17 spring boot security/image-20210107232901989.png)



단지 POM.XML에 Security dependecy를 추가 한 후 실행 했을때의 화면이다.

기본적으로 제공되는 id는 user이며 pw는 실행 했을때 아래와 같이 나온다.

![image-20210107233230201](../../assets/images/2021-01-17 spring boot security/image-20210107233230201.png)

