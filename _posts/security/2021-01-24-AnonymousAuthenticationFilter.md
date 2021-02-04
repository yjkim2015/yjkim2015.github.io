---
title: Spring boot Security - AnonymousAuthenticationFilter
categories:
- SECURITY
toc: true
toc_sticky: true
toc_label: 목차
---

##### AnonymousAuthenticationFilter

* 익명사용자 인증 처리 필터
* 익명사용자와 인증 사용자를 구분해서 처리하기 위한 용도로 사용
* 화면에서 인증 여부를 구혈할 때 isAnonymous()와 isAuthenticated()로 구분해서 사용
* 인증객체를 세션에 저장하지 않는다.

처리과정은 아래의 그림과 같다.



![image-20210124205926415](../../assets/images/2021-01-24-spring-boot-security-2/image-20210124205926415.png)







