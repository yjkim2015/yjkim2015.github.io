---
title: "JPA 핵심 개념"
categories:
- SPRING
toc: true
toc_sticky: true
toc_label: 목차
---

Spring Boot로 애플리케이션을 만들다 보면 SQL 한 줄 짜지 않았는데 쿼리가 수십 번 나가거나, 분명히 값을 바꿨는데 DB에 반영이 안 되는 경험을 하게 된다. 이런 문제의 뿌리는 대부분 JPA 내부 동작을 모르는 데 있다.

## Step 1: JPA란? ORM이란?

### ORM (Object-Relational Mapping)

> 비유: 번역가와 같다. 개발자가 자바 객체 언어로 말하면 ORM이 데이터베이스가 이해하는 SQL로 통역해준다.

객체지향 언어에서 사용하는 **객체(Object)**와 관계형 데이터베이스의 **테이블(Relation)** 사이의 불일치를 자동으로 해결해주는 기술이다.

개발자가 SQL을 직접 작성하는 대신, 객체를 조작하면 ORM 프레임워크가 적절한 SQL을 자동으로 생성하고 실행한다.

**객체와 테이블의 패러다임 불일치 문제**

```
[객체 세계]                    [관계형 DB 세계]
- 상속                         - 슈퍼타입/서브타입
- 연관관계 (참조)               - 외래키 (JOIN)
- 그래프 탐색                   - SQL JOIN으로만 탐색
- 동일성 (==)                   - 기본키로 구분
```

### JPA (Java Persistence API)

JPA는 자바 진영의 **ORM 기술 표준 명세(Specification)**이다. 즉, JPA 자체는 인터페이스의 모음이며 실제 구현체가 별도로 존재한다.

```java
// JPA는 인터페이스다
public interface EntityManager {
    public void persist(Object entity);
    public <T> T find(Class<T> entityClass, Object primaryKey);
    public <T> T merge(T entity);
    public void remove(Object entity);
    // ...
}
```

### JPA vs Hibernate vs Spring Data JPA

이 세 가지를 혼동하는 경우가 많다. 관계를 명확히 정리하면 아래와 같다.

<div class="mermaid">
graph TD
    SDJ["Spring Data JPA<br/>(JpaRepository, 쿼리 메서드 자동 생성)"]
    JPA["JPA<br/>(Java Persistence API - 표준 명세)"]
    HIB["Hibernate"]
    ECL["EclipseLink"]
    OJP["OpenJPA"]
    JDBC["JDBC (데이터베이스 드라이버)"]
    DB["Database (MySQL, Oracle ...)"]

    SDJ --> JPA
    JPA --> HIB
    JPA --> ECL
    JPA --> OJP
    HIB --> JDBC
    ECL --> JDBC
    OJP --> JDBC
    JDBC --> DB
</div>

- **JPA**: 표준 인터페이스. `javax.persistence` 패키지. 어떻게 동작해야 하는지 규약을 정의한다.
- **Hibernate**: JPA의 가장 대표적인 구현체. 실제로 SQL을 생성하고 실행하는 라이브러리다.
- **Spring Data JPA**: Hibernate 위에서 더 편리하게 JPA를 사용할 수 있도록 추상화한 스프링 모듈. `JpaRepository` 인터페이스를 상속하면 기본 CRUD, 페이징, 정렬이 자동으로 제공된다.

```java
// Spring Data JPA 사용 예시
public interface MemberRepository extends JpaRepository<Member, Long> {
    // 메서드 이름만으로 쿼리 자동 생성
    List<Member> findByUsername(String username);
    List<Member> findByAgeGreaterThan(int age);
}
```

실무에서 대부분은 Spring Data JPA를 사용하지만, 내부적으로는 Hibernate가 동작하고 있다. 따라서 **Hibernate(JPA)의 동작 원리를 이해하지 못하면 실무에서 예상치 못한 버그를 만나게 된다.**

---

## Step 2: 영속성 컨텍스트 (Persistence Context) 동작 원리

> 비유: 회사의 임시 보고서 수신함 같다. 결재 요청이 오면 바로 본사(DB)로 보내는 게 아니라 일단 수신함에 모아두었다가 한꺼번에 처리한다.

영속성 컨텍스트는 **"엔티티를 영구 저장하는 환경"**이다. JPA를 이해하는 데 있어 가장 핵심적인 개념이다.

EntityManager는 영속성 컨텍스트에 접근하는 창구 역할을 하며, 내부적으로 영속성 컨텍스트를 관리한다.

<div class="mermaid">
graph LR
    APP["Application<br/>em.persist(member)"]
    subgraph EM["EntityManager"]
        PC["영속성 컨텍스트<br/>─────────────<br/>[1차 캐시]<br/>[쓰기지연 SQL]"]
    end
    DB["Database"]

    APP --> EM
    PC -->|flush| DB
</div>

### 2-1. 1차 캐시

영속성 컨텍스트 내부에는 **1차 캐시**라는 Map이 존재한다. 키는 `@Id`로 매핑한 식별자, 값은 엔티티 인스턴스이다.

```java
// 1차 캐시에 저장
Member member = new Member();
member.setId(1L);
member.setUsername("kim");
em.persist(member); // 1차 캐시에 저장됨. DB에는 아직 저장 안됨.

// 1차 캐시에서 조회 (DB 쿼리 없음)
Member findMember1 = em.find(Member.class, 1L); // SELECT 쿼리 없음
System.out.println(findMember1.getUsername()); // kim

// 1차 캐시에 없는 경우 DB 조회 후 1차 캐시에 저장
Member findMember2 = em.find(Member.class, 2L); // SELECT 쿼리 실행
```

**SQL 로그 확인**

```sql
-- em.find(Member.class, 1L) : 1차 캐시 HIT -> 쿼리 없음
-- em.find(Member.class, 2L) : 1차 캐시 MISS -> DB 조회
Hibernate:
    select
        member0_.id as id1_0_0_,
        member0_.username as username2_0_0_
    from
        Member member0_
    where
        member0_.id=?
```

1차 캐시는 **트랜잭션 단위로 존재**하기 때문에 트랜잭션이 종료되면 사라진다. 애플리케이션 전체에서 공유하는 2차 캐시와는 다르다.

### 2-2. 동일성 (Identity) 보장

동일한 트랜잭션 내에서 같은 식별자로 조회한 엔티티는 항상 **동일한 인스턴스**를 반환한다.

```java
Member a = em.find(Member.class, 1L);
Member b = em.find(Member.class, 1L);

System.out.println(a == b); // true (같은 인스턴스)
```

이는 마치 자바 컬렉션에서 같은 객체를 두 번 꺼내도 동일한 참조를 갖는 것과 같다. JPA가 1차 캐시를 통해 **반복 가능한 읽기(Repeatable Read)** 수준의 트랜잭션 격리를 애플리케이션 레벨에서 제공하는 것이다.

### 2-3. 쓰기 지연 (Transactional Write-Behind)

`em.persist()`를 호출할 때마다 즉시 SQL을 날리지 않는다. 내부적으로 **쓰기 지연 SQL 저장소**에 SQL을 모아두었다가 트랜잭션 커밋 시점에 한꺼번에 DB로 전송한다.

```java
EntityTransaction tx = em.getTransaction();
tx.begin();

em.persist(memberA);
// INSERT INTO Member ... -> 쓰기 지연 SQL 저장소에 보관
em.persist(memberB);
// INSERT INTO Member ... -> 쓰기 지연 SQL 저장소에 보관

// 여기까지 DB에 INSERT 쿼리 안 날아감

tx.commit();
// flush() 호출 -> 쓰기 지연 SQL 저장소의 쿼리가 DB로 전송
// 이후 실제 DB 트랜잭션 커밋
```

**쓰기 지연 SQL 저장소 동작 흐름**

<div class="mermaid">
graph TD
    PA["em.persist(memberA)"]
    PA1["1차 캐시에 memberA 저장"]
    PA2["쓰기지연 SQL 저장소: [INSERT memberA]"]
    PB["em.persist(memberB)"]
    PB1["1차 캐시에 memberB 저장"]
    PB2["쓰기지연 SQL 저장소: [INSERT memberA, INSERT memberB]"]
    TC["tx.commit()"]
    FL["flush() 실행"]
    DB1["INSERT memberA → DB"]
    DB2["INSERT memberB → DB"]
    CM["DB 트랜잭션 커밋"]

    PA --> PA1
    PA --> PA2
    PB --> PB1
    PB --> PB2
    PA2 --> PB
    TC --> FL
    FL --> DB1
    FL --> DB2
    DB1 --> CM
    DB2 --> CM
</div>

Hibernate의 `hibernate.jdbc.batch_size` 설정을 통해 여러 SQL을 배치로 한꺼번에 전송해 성능을 최적화할 수 있다.

```yaml
# application.yml
spring:
  jpa:
    properties:
      hibernate:
        jdbc:
          batch_size: 50
```

### 2-4. 변경 감지 (Dirty Checking) — 스냅샷 비교 메커니즘

JPA에서 엔티티를 수정할 때 `em.update()` 같은 메서드는 존재하지 않는다. 엔티티 필드 값을 변경하기만 하면 트랜잭션 커밋 시점에 자동으로 UPDATE SQL이 실행된다.

```java
// 영속 엔티티 조회
Member member = em.find(Member.class, 1L);

// 필드 값 변경
member.setUsername("newName");
member.setAge(30);

// em.update(member) 같은 코드 불필요! 자동으로 UPDATE 실행됨
tx.commit();
```

**스냅샷 비교 메커니즘**

<div class="mermaid">
graph TD
    FIND["em.find() 시점"]
    SAVE1["1차 캐시에 엔티티 저장"]
    SAVE2["최초 상태를 스냅샷으로 저장"]
    SET["member.setUsername('newName')<br/>member.setAge(30)"]
    CMP["엔티티 vs 스냅샷 비교<br/>→ 변경 감지!"]
    FL["flush() 시점"]
    GEN["UPDATE SQL 생성"]
    REG["쓰기 지연 SQL 저장소에 등록"]
    SEND["DB로 전송"]

    FIND --> SAVE1
    FIND --> SAVE2
    SAVE1 --> SET
    SAVE2 --> SET
    SET --> FL
    FL --> CMP
    CMP --> GEN
    GEN --> REG
    REG --> SEND
</div>

**생성되는 SQL 로그**

```sql
Hibernate:
    update
        Member
    set
        age=?,
        username=?
    where
        id=?
```

Hibernate 기본 설정에서는 변경된 필드만이 아니라 **모든 필드를 UPDATE**한다. `@DynamicUpdate`를 사용하면 변경된 필드만 UPDATE할 수 있다.

```java
@Entity
@DynamicUpdate // 변경된 필드만 UPDATE
public class Member {
    // ...
}
```

### 2-5. 지연 로딩 (Lazy Loading) 프록시 동작 원리

연관된 엔티티를 즉시 로딩하지 않고, 실제로 접근하는 시점에 쿼리를 실행하는 방식이다.

```java
@Entity
public class Member {
    @Id @GeneratedValue
    private Long id;
    private String username;

    @ManyToOne(fetch = FetchType.LAZY) // 지연 로딩 설정
    @JoinColumn(name = "team_id")
    private Team team;
}
```

```java
Member member = em.find(Member.class, 1L);
// SELECT * FROM Member WHERE id=1 (Team 조회 안함)

Team team = member.getTeam();
// team은 아직 프록시 객체 (실제 Team이 아님)
// DB 쿼리 실행 안됨

String teamName = team.getName();
// 이 시점에 Team SELECT 쿼리 실행!
// SELECT * FROM Team WHERE id=?
```

**프록시 동작 원리**

<div class="mermaid">
sequenceDiagram
    participant App as Application
    participant EM as EntityManager
    participant Proxy as TeamProxy
    participant DB as Database

    App->>EM: em.find(Member.class, 1L)
    EM-->>App: Member 반환 (team 필드 = TeamProxy)
    Note over Proxy: target: null<br/>id: 2L (FK만 알고 있음)
    App->>Proxy: team.getName() 호출
    Proxy->>DB: SELECT * FROM Team WHERE id=2
    DB-->>Proxy: Team 데이터
    Note over Proxy: target에 실제 Team 설정
    Proxy-->>App: "개발팀" 반환
</div>

**주의사항**: 영속성 컨텍스트가 종료된 후(준영속 상태)에 지연 로딩을 시도하면 `LazyInitializationException`이 발생한다.

```java
// 트랜잭션 종료 후
Member member = memberRepository.findById(1L).get();
// 여기서 트랜잭션이 끝나면...

member.getTeam().getName(); // LazyInitializationException 발생!
```

---

## Step 3: 엔티티 생명주기

> 비유: 사람의 고용 상태와 같다. 입사 지원서만 낸 상태(비영속), 재직 중(영속), 퇴직(준영속), 말소(삭제)로 나뉜다.

<div class="mermaid">
stateDiagram-v2
    [*] --> 비영속 : new
    비영속 --> 영속 : persist()
    영속 --> 준영속 : detach() / close() / clear()
    준영속 --> 영속 : merge()
    영속 --> 삭제 : remove()
    삭제 --> [*]
</div>

### 비영속 (new / transient)
영속성 컨텍스트와 전혀 관계 없는 상태. 단순히 객체를 생성만 한 상태이다.

```java
Member member = new Member();
member.setId(1L);
member.setUsername("kim");
// 영속성 컨텍스트와 무관한 순수 자바 객체
```

### 영속 (managed)
영속성 컨텍스트에 의해 관리되는 상태. 1차 캐시에 저장되며, 변경 감지, 쓰기 지연 등의 이점을 모두 누릴 수 있다.

```java
em.persist(member); // 영속 상태로 전환
// 또는
Member findMember = em.find(Member.class, 1L); // 조회한 엔티티는 영속 상태
```

### 준영속 (detached)
영속성 컨텍스트에서 분리된 상태. 이전에 영속 상태였지만 더 이상 관리되지 않는다. 변경 감지가 동작하지 않는다.

```java
em.detach(member); // 특정 엔티티만 준영속으로 전환
em.clear();        // 영속성 컨텍스트 전체 초기화
em.close();        // 영속성 컨텍스트 종료
```

### 삭제 (removed)
삭제가 예약된 상태. 트랜잭션 커밋 시 실제 DELETE SQL이 실행된다.

```java
em.remove(member); // 삭제 상태로 전환
tx.commit();       // DELETE FROM Member WHERE id=?
```

---

## Step 4: flush vs commit

> 비유: flush는 초안 문서를 상대방에게 보내는 것이고, commit은 최종 서명까지 완료하는 것이다. 초안을 보낸 후에도 서명 전이면 회수(롤백)할 수 있다.

두 개념을 혼동하는 경우가 많다. 명확히 구분해야 한다.

| 구분 | flush | commit |
|------|-------|--------|
| 역할 | 영속성 컨텍스트의 변경내용을 DB에 동기화 | DB 트랜잭션을 최종 확정 |
| 1차 캐시 | 유지됨 | 종료됨 (트랜잭션 범위에 따라) |
| 발생 시점 | commit 직전, JPQL 실행 전, 직접 호출 | 명시적 tx.commit() 호출 |
| 롤백 가능 여부 | flush 후에도 롤백 가능 | 커밋 후 롤백 불가 |

```java
tx.begin();

em.persist(memberA);
em.flush(); // SQL이 DB로 전송되지만 아직 트랜잭션 커밋 안됨
            // -> 다른 트랜잭션에서는 memberA가 보이지 않음
            // -> 이 트랜잭션에서는 롤백으로 취소 가능

tx.commit(); // 이제 DB에 영구 반영
```

**flush 발생 시점 3가지**

```java
// 1. 직접 호출
em.flush();

// 2. 트랜잭션 커밋 시 자동 호출
tx.commit();

// 3. JPQL 쿼리 실행 전 자동 호출
em.persist(memberA);
em.persist(memberB);
// 아직 DB에 없는 상태

List<Member> members = em.createQuery("select m from Member m", Member.class)
        .getResultList();
// JPQL 실행 전에 flush 자동 호출 -> memberA, memberB가 결과에 포함됨
```

---

## Step 5: 연관관계 매핑

> 비유: 직원(Member)이 팀(Team)을 참조하는 것은 명함에 부서명을 적는 것과 같다. DB에서는 직원 테이블의 team_id(외래키)가 그 역할을 한다.

### 기본 어노테이션

**@ManyToOne (가장 많이 사용)**

```java
@Entity
public class Member {
    @Id @GeneratedValue
    private Long id;
    private String username;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "team_id") // FK 컬럼명
    private Team team;
}
```

**@OneToMany**

```java
@Entity
public class Team {
    @Id @GeneratedValue
    private Long id;
    private String name;

    @OneToMany(mappedBy = "team") // Member.team 필드를 따라감
    private List<Member> members = new ArrayList<>();
}
```

**@OneToOne**

```java
@Entity
public class Member {
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "locker_id")
    private Locker locker;
}

@Entity
public class Locker {
    @OneToOne(mappedBy = "locker")
    private Member member;
}
```

**@ManyToMany** (실무에서는 사용 지양)

```java
// 실무에서는 중간 테이블에 추가 컬럼이 필요한 경우가 많아
// @ManyToMany 대신 중간 엔티티를 만들어 @ManyToOne, @OneToMany로 풀어내는 것이 권장된다.
@Entity
public class MemberProduct { // 중간 엔티티
    @Id @GeneratedValue
    private Long id;

    @ManyToOne
    @JoinColumn(name = "member_id")
    private Member member;

    @ManyToOne
    @JoinColumn(name = "product_id")
    private Product product;

    private int orderAmount; // 추가 컬럼
    private LocalDateTime orderDate;
}
```

### 단방향 vs 양방향

<div class="mermaid">
graph LR
    subgraph 단방향
        M1[Member] -->|team 참조| T1[Team]
    end
    subgraph 양방향
        M2[Member] -->|team 참조| T2[Team]
        T2 -->|members 참조| M2
    end
</div>

```java
// 단방향: Member -> Team
@Entity
public class Member {
    @ManyToOne
    @JoinColumn(name = "team_id")
    private Team team;
}

// 양방향 추가: Team -> Member
@Entity
public class Team {
    @OneToMany(mappedBy = "team") // mappedBy 필수!
    private List<Member> members = new ArrayList<>();
}
```

### 연관관계 주인 (Owner)

양방향 매핑에서 실제로 FK를 관리하는 쪽이 **연관관계의 주인**이다.

- **주인**: `mappedBy` 속성 없음. FK를 직접 관리. DB에 실제로 반영됨.
- **반대쪽**: `mappedBy` 속성 있음. 읽기 전용. DB에 반영 안됨.

<div class="mermaid">
graph LR
    subgraph MEMBER["MEMBER 테이블"]
        mid[id]
        mname[name]
        tid[team_id ← FK]
    end
    subgraph TEAM["TEAM 테이블"]
        tmid[id]
        tmname[name]
    end
    tid -->|FK| tmid
</div>

따라서 FK가 있는 Member.team이 연관관계의 주인이 된다.

```java
Team team = new Team();
team.setName("개발팀");
em.persist(team);

Member member = new Member();
member.setUsername("kim");
member.setTeam(team); // 주인 쪽에 설정 -> DB에 반영됨
em.persist(member);

// 편의 메서드: 양쪽 모두 설정하는 것이 안전
public void changeTeam(Team team) {
    this.team = team;
    team.getMembers().add(this); // 반대쪽도 동기화
}
```

**흔한 실수**: 주인이 아닌 쪽에만 설정하면 DB에 반영되지 않는다.

```java
team.getMembers().add(member); // 주인이 아닌 쪽만 설정 -> DB 반영 안됨!
// member.setTeam(team) 이 없으면 team_id = null로 저장됨
```

---

## Step 6: 상속 매핑 전략

> 비유: '상품'이라는 대분류 아래 '음반'과 '영화'가 있을 때, DB에 표현하는 방법은 세 가지다. 공통 테이블 하나에 다 넣거나, 분리하거나, 각자 독립 테이블로 만들거나.

객체는 상속이 있지만 DB에는 상속이 없다. JPA는 이를 3가지 전략으로 해결한다.

```java
@Entity
@Inheritance(strategy = InheritanceType.JOINED) // 전략 선택
@DiscriminatorColumn(name = "DTYPE") // 구분 컬럼
public abstract class Item {
    @Id @GeneratedValue
    private Long id;
    private String name;
    private int price;
}

@Entity
@DiscriminatorValue("A")
public class Album extends Item {
    private String artist;
}

@Entity
@DiscriminatorValue("M")
public class Movie extends Item {
    private String director;
    private String actor;
}
```

### 전략 비교

**1. JOINED (조인 전략)**

<div class="mermaid">
graph TD
    ITEM["ITEM 테이블<br/>──────────<br/>id<br/>name<br/>price<br/>DTYPE"]
    ALBUM["ALBUM 테이블<br/>──────────<br/>item_id (FK)<br/>artist"]
    MOVIE["MOVIE 테이블<br/>──────────<br/>item_id (FK)<br/>director<br/>actor"]
    ITEM --> ALBUM
    ITEM --> MOVIE
</div>

- 장점: 정규화됨, 외래키 무결성 제약 가능, 저장 공간 효율적
- 단점: 조회 시 JOIN 필요, 쿼리 복잡

**2. SINGLE_TABLE (단일 테이블 전략)**

<div class="mermaid">
graph TD
    ITEM["ITEM 테이블 (단일)<br/>────────────────────────────────<br/>id │ name │ price │ DTYPE │ artist │ director<br/>────────────────────────────────<br/>1 │ 음반 │ 10000 │ A │ BTS │ null<br/>2 │ 영화 │ 20000 │ M │ null │ 봉준호"]
</div>

- 장점: JOIN 없어 조회 성능 빠름, 쿼리 단순
- 단점: null 허용 컬럼 多, 테이블 비대해질 수 있음

**3. TABLE_PER_CLASS (구현 클래스마다 테이블)**

<div class="mermaid">
graph LR
    ALBUM["ALBUM 테이블<br/>──────────────────<br/>id │ name │ price │ artist"]
    MOVIE["MOVIE 테이블<br/>─────────────────────────<br/>id │ name │ price │ director"]
</div>

- 장점: 서브타입 명확히 구분, not null 제약 가능
- 단점: 여러 테이블 함께 조회 시 UNION 사용, 성능 나쁨
- 실무에서 거의 사용 안 함

| 전략 | 조회 성능 | 정규화 | NULL 허용 | 추천 여부 |
|------|-----------|--------|-----------|-----------|
| JOINED | 보통 (JOIN) | O | X | 기본 추천 |
| SINGLE_TABLE | 빠름 | X | O (서브타입 컬럼) | 단순 구조 시 |
| TABLE_PER_CLASS | 나쁨 (UNION) | - | X | 미추천 |

---

## Step 7: JPQL vs Criteria API vs QueryDSL

> 비유: JPQL은 손으로 쓴 SQL 메모, Criteria API는 복잡한 양식지, QueryDSL은 자동완성이 되는 워드프로세서다. 실무에서는 자동완성이 되는 QueryDSL을 가장 많이 쓴다.

### JPQL (Java Persistence Query Language)

SQL과 유사하지만 **테이블이 아닌 엔티티 객체를 대상**으로 쿼리한다.

```java
// JPQL: 엔티티 이름(Member)과 필드명(username) 기준으로 작성
String jpql = "select m from Member m where m.username = :username";
List<Member> result = em.createQuery(jpql, Member.class)
        .setParameter("username", "kim")
        .getResultList();

// 실행되는 SQL
// SELECT m.id, m.username, m.team_id FROM Member m WHERE m.username = ?
```

**JPQL 주요 기능**

```java
// 페이징
List<Member> result = em.createQuery("select m from Member m", Member.class)
        .setFirstResult(10)  // 시작 위치
        .setMaxResults(20)   // 최대 개수
        .getResultList();

// 조인
String jpql = "select m from Member m join m.team t where t.name = :teamName";

// 집계
String jpql = "select count(m), avg(m.age) from Member m";
```

**단점**: 문자열이라 컴파일 시점에 오류를 잡을 수 없다.

### Criteria API

JPQL을 자바 코드로 빌더 패턴으로 작성하는 방식. 컴파일 시점 오류 감지 가능.

```java
CriteriaBuilder cb = em.getCriteriaBuilder();
CriteriaQuery<Member> query = cb.createQuery(Member.class);
Root<Member> m = query.from(Member.class);

query.select(m)
     .where(cb.equal(m.get("username"), "kim"));

List<Member> result = em.createQuery(query).getResultList();
```

**단점**: 코드가 너무 복잡하고 직관적이지 않아 실무에서 거의 사용하지 않는다.

### QueryDSL

JPQL을 타입 안전하게 작성할 수 있는 라이브러리. **실무에서 가장 많이 사용**한다.

```java
// build.gradle 의존성 추가 필요
// implementation 'com.querydsl:querydsl-jpa'

JPAQueryFactory queryFactory = new JPAQueryFactory(em);
QMember m = QMember.member;

List<Member> result = queryFactory
        .selectFrom(m)
        .where(m.username.eq("kim")
                .and(m.age.gt(20)))
        .orderBy(m.username.asc())
        .offset(0)
        .limit(10)
        .fetch();
```

**장점**: 타입 안전, 코드 자동완성, 동적 쿼리 작성 용이, JPQL과 1:1 매핑.

---

## Step 8: 벌크 연산 주의사항

> 비유: 영속성 컨텍스트(1차 캐시)는 직원의 개인 메모장이다. 벌크 연산은 본사(DB)에 직접 공문을 보내는 것이라, 메모장을 거치지 않는다. 이후 메모장을 비워야(clear) 최신 공문 내용을 다시 받아볼 수 있다.

벌크 연산은 여러 행을 한 번의 쿼리로 수정/삭제하는 연산이다.

```java
// 나이가 20 이상인 모든 회원의 나이를 1 증가
int resultCount = em.createQuery(
        "update Member m set m.age = m.age + 1 where m.age >= 20")
        .executeUpdate();

// 또는 Spring Data JPA에서
@Modifying
@Query("update Member m set m.age = m.age + 1 where m.age >= :age")
int bulkAgePlus(@Param("age") int age);
```

**핵심 주의사항: 벌크 연산은 영속성 컨텍스트를 무시하고 DB에 직접 쿼리한다.**

```java
Member member = em.find(Member.class, 1L); // age = 20, 영속성 컨텍스트에 로드됨

// 벌크 연산 실행
em.createQuery("update Member m set m.age = m.age + 1 where m.age >= 20")
  .executeUpdate();
// DB: age = 21
// 영속성 컨텍스트: age = 20 (여전히 이전 값!)

Member findMember = em.find(Member.class, 1L);
System.out.println(findMember.getAge()); // 20 (DB와 불일치 발생!)
```

**해결책**: 벌크 연산 후 반드시 영속성 컨텍스트를 초기화한다.

```java
// 방법 1: em.clear()로 영속성 컨텍스트 초기화
em.createQuery("update Member m set m.age = m.age + 1 where m.age >= 20")
  .executeUpdate();
em.clear(); // 영속성 컨텍스트 초기화
Member findMember = em.find(Member.class, 1L); // DB에서 새로 조회 (age = 21)

// 방법 2: Spring Data JPA에서 @Modifying(clearAutomatically = true)
@Modifying(clearAutomatically = true) // 실행 후 자동으로 em.clear() 호출
@Query("update Member m set m.age = m.age + 1 where m.age >= :age")
int bulkAgePlus(@Param("age") int age);
```

---

```
참조 - 자바 ORM 표준 JPA 프로그래밍 By 김영한
```
