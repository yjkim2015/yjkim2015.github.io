---
layout: post
title:  "SpringBoot & JPA & Thymeleaf CRUD 게시판 - 1"
date:   2020-06-30 13:19:00
categories: SpringBoot JPA Thymeleaf CRUD 게시판
---
SpringBoot & JPA & Thymeleaf CRUD 게시판 만들기



프로젝트 구조이다. 여기서  restController는 쓰지 않으니 만들 필요가 없다.

![image-20200630132227255]("https://yjkim2015.github.io/assets/image-20200630132227255.png")



필자는 데이터베이스는 mysql을 사용했다. 

pom.xml에 관련된 설정을 추가해주자. (jpa, thymeleaf, mysql)

![image-20200630132442423]("https://yjkim2015.github.io/assets/image-20200630132442423.png")

그 다음으로 게시판을 만들기 위해 필요한 객체와 데이터베이스 테이블을 생성 후 환경설정한다. 

```javascript
JPA는 ORM(Object Relational Mapping)

객체와 관계형 데이터베이스의 데이터를 자동으로 매핑(연결)해주는 것을 말한다.
객체 지향 프로그래밍은 클래스를 사용하고, 관계형 데이터베이스는 테이블을 사용한다.
객체 모델과 관계형 모델 간에 불일치가 존재한다.
ORM을 통해 객체 간의 관계를 바탕으로 SQL을 자동으로 생성하여 불일치를 해결한다.
데이터베이스 데이터 <—매핑—> Object 필드
객체를 통해 간접적으로 데이터베이스 데이터를 다룬다.
Persistant API라고도 할 수 있다.
Ex) JPA, Hibernate 등
즉, 객체 관계 매핑이므로 데이터베이스의 테이블과 적용하고자 하는 객체의 매핑이 맞아야한다.
```



먼저 게시판을 만들기 위한 객체의 내용은  다음과 같다. 

![image-20200630133051642]("https://yjkim2015.github.io/assets/image-20200630133051642.png")



데이터베이스의 테이블 내용은 다음과 같다.

![image-20200630133149976]("https://yjkim2015.github.io/assets/image-20200630133149976.png")



데이터베이스와의 접속을 위한 환경설정을 한다.

application.properties 파일을 각자의 환경에 맞게 끔 변경한다.

![image-20200630133334643]("https://yjkim2015.github.io/assets/image-20200630133334643.png")

여기까지 되었다면 본격적으로 간단한 CRUD 게시판을 만들어보자.

#### 1. INSERT

먼저 게시글을 등록을 해보자.

HttpMethod에는 GET,POST등 여러 메소드가 있지만, 이렇게 어떤 페이지를 조회할 때는 GET방식을 사용한다.

각 메소드 별 차이는 추후에 블로깅 하겠다.

그렇다면  웹에서 게시글을 등록하려면 게시글을 작성하는 페이지가 있어야한다.

게시글을 작성하는 페이지로 들어가려면 HttpMethod중 GET을 통해 해당 페이지를 보여줘야한다.



필자는 간단히 게시글을 등록하는 페이지에 /insertBoard 라는 주소를 부여했다.

/insertBoard 주소에 맞는 컨트롤러를 작성해보자.

다음과 같이 추가한다.

![image-20200630134129091]("https://yjkim2015.github.io/assets/image-20200630134129091.png")

위에 /insertBoard를 보면 return  "insertBoard"로 되있는데 이 의미는 insertBoard.html을 보여주겠다는 의미이다. 



그럼 이제 insertBoard.html을 만들어보자 

src/main/resources 아래에 templates아래에 insertBoard.html을 생성하고

다음과 같이 게시글 입력 폼을 만들어 준다.

![image-20200630134438848]("https://yjkim2015.github.io/assets/image-20200630134438848.png")

이제 프로젝트를 실행 후 브라우저를 열어 주소창에 localhost:8080/insertBoard를 입력하면

![image-20200630134556977]("https://yjkim2015.github.io/assets/image-20200630134556977.png")



정말 볼품없는 폼이 나올것이다.... (하지만 이 글은 정말 기초적인 단계이므로 UserInterface에는 신경 쓰지말자..)



우리는 글을 등록하기 위한 페이지를 만들었다. 

이제 이 페이지에서 내용을 넣어서 데이터베이스에 넣으면 등록기능이 완성이 된다.

자 이제 데이터를 입력해서 컨트롤러로 넘겨서 디비에 넣어보자!!



위에 insert.html을 자세히 보면 form태그에 action ="/insertBoard" method="post"가 써있을 것이다. 이 말은 내가 작성한 데이터를 insertBoard라는 주소로 post 방식으로 데이터를 전송할거야!! 라는 뜻이다. 

그렇다면 그 전송된 데이터를 받을 컨트롤러를 생성해보자.



다시 MainController 안에 다음과 같이 작성한다.

![image-20200630135151478]("https://yjkim2015.github.io/assets/image-20200630135151478.png")

이렇게 작성하면 insert.html에서 작성한 데이터를 전송 시 컨트롤러에서 데이터를 받을 것이다.



이제 남은건 데이터베이스에 넣어 주기 위한 로직을 추가 해야한다.

여기서부터가 jpa의 시작이다. 사실 위의 기술한 내용들은 스프링을 공부해본 사람이라면 모르는 사람이 없을 것이다.



다음과 같이 jpa를 통한 디비 작업을 위해 BoardRepository를 생성한다.

![image-20200630135559106]("https://yjkim2015.github.io/assets/image-20200630135559106.png")



JpaRepository를 상속받는다.

여기서 살펴보면 JpaRepository는 또 내부에 CrudRepository를 상속받는다. 

이 CrudRepository는 내부적으로 save, find 등등의 기능이있다.

우리는 데이터를 넣기위해 별도의 로직을 만들지 않고 jpa에서 제공하는 save기능을 사용할 것이다.

![image-20200630135848886]("https://yjkim2015.github.io/assets/image-20200630135848886.png")

boardRepo를 생성했다면 이제 서비스 로직을 위한 BoardService을 생성한다.

다음과 같이 작성한다.

![image-20200630140148539]("https://yjkim2015.github.io/assets/image-20200630140148539.png")



boardRepository를 주입받고 insertBoard 메소드 내에서 repo내의 save를 호출한다.



이제 컨트롤러에서 BoardService를 주입하고 사용하기만하면 끝이다!

다시 컨트롤러로 돌아가 다음과 같이 수정한다.

![image-20200630140308292]("https://yjkim2015.github.io/assets/image-20200630140308292.png")





![image-20200630140346344]("https://yjkim2015.github.io/assets/image-20200630140346344.png")

모든 작성이 끝났다면 다시 웹 어플리케이션을 실행 한 후 글을 작성하여 등록을 해보자.



등록 버튼을 누른 후 실제 데이터가 저장되었는지 디비를 열어 확인해보자!!

![image-20200630140433127]("https://yjkim2015.github.io/assets/image-20200630140433127.png")



![image-20200630140500804]("https://yjkim2015.github.io/assets/image-20200630140500804.png")

데이터가 잘들어갔다. 이렇게 jpa의 save 기능을 사용해보았다.

다음 글에서 게시판의 나머지 기능들을 포스팅하겠다.
