---
title: Spring boot Security - Authentication Manager
categories:
- Spring Boot Security
toc: true
toc_sticky: true
toc_label: 목차

---

## Authentication Manger

* AuthenticationProvider 목록 중에서 인증 처리 요건에 맞는 AuthenticationProvider를 찾아 인증처리를 위임한다.

* 부모 ProviderManger를 설정하여 AuthenticationProvider를 계속 탐색 할 수 있다.

  

![image-20210606221055297](../../assets/images/2021-06-06-AuthenticationManager/image-20210606221055297.png)



```
스프링 시큐리티 - Spring boot 기반으로 개발하는 Spring Security 강의 중
```

