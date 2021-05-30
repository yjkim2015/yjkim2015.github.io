---

title: SpringBoot - 회원 관리 예제
categories:
- Spring Boot
toc: true
toc_sticky: true
toc_label: 목차
---



이번엔 가벼운 회원 관리 프로그램을 만들어 볼 것이다.

DB는 사용하지 않을것이기에 전역변수를 활용한다.

순서는 아래와 같이 진행된다.

## Step 1:  비즈니스 요구사항 정리

데이터 : 회원 ID, 이름

기능 : 회원등록, 조회

가상의 시나리오

## Step 2:  회원 도메인과 레포지토리 만들기

아래와 같이 도메인과 레포지토리를 생성한다.

**회원 ID, 이름을 가진 Member Domain**

![image-20210530230747276](../../assets/images/2021-05-30-springboot-회원 관리 예제/image-20210530230747276.png)



**레포지토리 인터페이스와 구현체**

![image-20210530230758975](../../assets/images/2021-05-30-springboot-회원 관리 예제/image-20210530230758975.png)



![image-20210530230811983](../../assets/images/2021-05-30-springboot-회원 관리 예제/image-20210530230811983.png)





```
김영한님의 스프링 입문 - 코드로 배우는 스프링부트, 웹 MVC, DB접근 기술 강의 참조
```