---

title: Spring Project 시작하기
categories:
- Spring Legacy
toc: true
toc_sticky: true
toc_label: 목차


---

## Step 1:  프로젝트 생성

![image-20200810112447612](../../assets/images/2020-08-10-spring_project_1/image-20200810112447612.png)



File -> New -> Other -> Spring Legacy Projcet 



![image-20200810112531225](../../assets/images/2020-08-10-spring_project_1/image-20200810112531225.png)



Spring MVC Project 선택 -> Project Name 작성 후 Next 클릭



![image-20200810112646079](../../assets/images/2020-08-10-spring_project_1/image-20200810112646079.png)



패키지 명 작성 [패키지명은 xxx.xxx.xxx 처럼 3구간으로 나누어야한다.]

![image-20200810132837992](../../assets/images/2020-08-10-spring_project_1/image-20200810132837992.png)



패키지 생성 후 pom.xml에서 자바 버전과 스프링버전을 변경해준다. [필자는 자바 1.8에 스프링 4버전대를 사용]

완료 후 메이븐 업데이트



![image-20200810132914434](../../assets/images/2020-08-10-spring_project_1/image-20200810132914434.png)

톰캣의 환경설정에서 생성한 프로젝트를 등록하고 Path를 /로 설정한다.



![image-20200810133027201](../../assets/images/2020-08-10-spring_project_1/image-20200810133027201.png)

톰캣 시작 후 웹 접속



![image-20200810133204735](../../assets/images/2020-08-10-spring_project_1/image-20200810133204735.png)

**프로젝트 디렉터리 구조**

1) src/main/java 

 자바코드 (Controller, Service, Dao) 가 들어가며 기능별로 패키징을 묶는다. 

2) src/main/resource 

자바 코드에서 사용할 리소스 (log4j2.xml, mapper.xml, *.properties 등) 

3) src/test/test 

 테스트 코드가 들어간다. (필자는 보통 테스트 코드에서 junit을 통해 디비 접속 테스트를 하지만..  TDD(테스트 주도 개발) 에서는 기능 단위로 테스트를 만든다.)

4)  src/test/resources 

테스트 코드에서 사용할 리소스

5)  src/main/webapp/resources

js,css,image등 파일 관리

6) src/main/webapp/class

컴파일된 클래스들을 관리

7) src/main/webapp/WEB-INF/views

html,jsp등 페이지를 관리

5) servlet-context.xml  

웹과 관련된 설정 파일

6) root-context.xml 

디비 관련 설정 파일

7) web.xml 

 웹프로젝트 환경설정 파일

