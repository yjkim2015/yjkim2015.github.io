---
title: "AI-Driven Development와 하네스 엔지니어링"
categories: AI
tags: [AI, ClaudeCode, Cursor, MCP, CLAUDE.md, PromptEngineering, TDD]
toc: true
toc_sticky: true
toc_label: 목차
date: 2026-05-01
---

AI가 코드를 생성하는 시대가 되면서 개발자의 역할이 바뀌고 있다. AI를 단순히 사용하는 것을 넘어, AI가 올바르게 작동하도록 환경과 제약을 설계하는 **하네스 엔지니어링(Harness Engineering)**이 새로운 핵심 역량으로 부상했다.

---

## AI-Driven Development란

AI-Driven Development(ADD)는 AI 도구를 개발 워크플로우의 중심에 배치하고, 개발자가 **방향·검증·아키텍처 결정**에 집중하는 개발 방식이다.

### 전통 개발 vs AI-Driven 개발

| 구분 | 전통 개발 | AI-Driven 개발 |
|------|-----------|----------------|
| 코드 작성 | 개발자 직접 작성 | AI 생성, 개발자 검토 |
| 반복 작업 | 개발자가 직접 처리 | AI 자동화 |
| 디버깅 | 로그/디버거 기반 | AI와 대화식 해결 |
| 문서화 | 별도 작성 | AI 자동 생성 |
| 테스트 작성 | 수동 | AI 초안 생성 후 검토 |
| 개발자 역할 | 구현자 | 설계자 + 검증자 |

### AI-Driven 개발의 핵심 원칙

1. **의도를 명확히 표현**: 모호한 지시는 나쁜 결과를 낳는다
2. **작은 단위로 반복**: 큰 작업을 쪼개어 각 단계를 검증한다
3. **AI 출력을 맹신하지 않는다**: 반드시 검토하고 테스트한다
4. **컨텍스트를 관리한다**: 관련 파일, 규칙, 제약을 명시적으로 제공한다

---

## AI 개발 워크플로우

### 기본 루프

```
1. 요구사항 분석 (개발자)
   ↓
2. 컨텍스트 준비 (관련 파일, 규칙 명시)
   ↓
3. AI에게 작업 지시 (프롬프트)
   ↓
4. AI 출력 검토 (개발자)
   ↓
5. 테스트/검증
   ↓
6. 피드백 및 수정 반복
```

### 작업 분류별 AI 활용

**AI가 잘 하는 것**
- 보일러플레이트 코드 생성
- 단순 CRUD 구현
- 리팩토링 (변수명 변경, 메서드 추출)
- 테스트 케이스 생성
- 문서 작성, 주석 추가
- 정규식, SQL 쿼리 작성
- 특정 라이브러리 사용법 검색

**AI가 잘 못하는 것**
- 복잡한 비즈니스 로직 설계
- 성능 병목 원인 분석 (컨텍스트가 부족할 때)
- 장기적 아키텍처 결정
- 도메인 특화 지식이 필요한 구현
- 다중 시스템 연동 설계

### 실전 워크플로우 예시

```
[새 기능 개발]

1. 아키텍처 결정 (개발자)
   "UserService에 소셜 로그인 기능 추가, OAuth2 사용"

2. 컨텍스트 제공
   - 기존 UserService 코드 첨부
   - SecurityConfig 첨부
   - 사용 중인 라이브러리 명시

3. 단계별 AI 지시
   Step 1: "OAuth2UserService 인터페이스 구현체 작성"
   Step 2: "UserPrincipal 클래스 작성"
   Step 3: "SecurityConfig OAuth2 설정 추가"
   Step 4: "각 클래스에 대한 단위 테스트 작성"

4. 각 단계마다 코드 검토 + 테스트 실행
```

---

## 프롬프트 엔지니어링

### 좋은 프롬프트의 구조

```
[역할] + [컨텍스트] + [작업] + [제약] + [출력 형식]
```

**나쁜 프롬프트**
```
로그인 기능 만들어줘
```

**좋은 프롬프트**
```
당신은 시니어 Java/Spring Boot 개발자입니다.

[컨텍스트]
- Spring Boot 3.2, Spring Security 6
- JWT 기반 인증 사용 중
- 기존 UserRepository: findByEmail(String email) 메서드 있음

[작업]
이메일/비밀번호 기반 로그인 API를 구현해주세요.

[제약]
- POST /api/auth/login 엔드포인트
- 성공 시 AccessToken(15분) + RefreshToken(7일) 반환
- 실패 시 적절한 HTTP 상태코드와 에러 메시지 반환
- 비밀번호는 BCrypt로 검증
- 생성자 주입 사용
- @Transactional 적절히 사용

[출력 형식]
1. LoginRequest DTO
2. LoginResponse DTO
3. AuthService 로그인 메서드
4. AuthController 엔드포인트
5. 단위 테스트
```

### 프롬프트 패턴

**Chain-of-Thought (CoT)**
```
다음 문제를 단계별로 분석해줘:
1. 현재 코드의 문제점 파악
2. 해결 방법 제시
3. 구현 코드 작성
4. 테스트 방법 설명
```

**Few-Shot (예시 제공)**
```
다음 패턴으로 코드를 작성해줘:

// 예시 1
public Result<User> findById(Long id) {
    return userRepository.findById(id)
        .map(Result::success)
        .orElse(Result.failure("사용자를 찾을 수 없습니다"));
}

// 위 패턴을 따라 OrderService.findByOrderNumber() 메서드 작성해줘
```

**Role Prompting**
```
당신은 코드 리뷰어입니다. 아래 코드에서 다음 관점에서 문제를 찾아주세요:
- 잠재적 NullPointerException
- 트랜잭션 경계 문제
- N+1 쿼리
- 스레드 안전성
```

### 반복 정제 패턴

```
1차: 초안 생성
"UserService.registerUser() 메서드 작성해줘"

2차: 개선 요청
"이메일 중복 검사 추가하고, 예외를 커스텀 예외로 바꿔줘"

3차: 엣지 케이스
"이메일 형식 검증과 비밀번호 정책 검증 추가해줘"

4차: 테스트
"위 메서드에 대한 단위 테스트 작성해줘. 성공/실패/예외 케이스 포함"
```

---

## 하네스 엔지니어링

하네스 엔지니어링이란 **AI가 올바르게 동작하도록 환경, 제약, 가이드를 설계하는 기술**이다. 자동차의 와이어 하네스가 전기 신호를 올바른 곳으로 인도하듯, AI의 출력을 원하는 방향으로 유도한다.

### CLAUDE.md

Claude Code에서 프로젝트 루트에 위치하는 설정 파일이다. AI가 작업을 시작할 때 자동으로 읽어 컨텍스트로 활용한다.

```markdown
# 프로젝트: MyShop Backend

## 기술 스택
- Java 21, Spring Boot 3.2
- MySQL 8.0, Redis 7
- Maven 빌드

## 코딩 규칙
- 생성자 주입 강제 (필드 주입 금지)
- 모든 공개 메서드에 Javadoc 필수
- 커스텀 예외는 BaseException 상속
- 로깅: SLF4J 사용, log.info/warn/error만 사용

## 작업 규칙
- 코드 변경 전 반드시 기존 코드 파악
- 변경 후 lsp_diagnostics 실행
- 테스트 없이 커밋 금지
- 커밋 메시지: [타입] 제목 형식

## 금지 사항
- System.out.println 사용 금지
- @Autowired 필드 주입 금지
- 하드코딩된 설정값 금지 (application.yml 사용)

## 테스트
- 단위 테스트: JUnit 5 + Mockito
- 통합 테스트: @SpringBootTest
- 테스트 DB: H2 in-memory

## 디렉토리 구조
src/main/java/com/myshop/
├── domain/          # 도메인 모델
├── application/     # 유스케이스
├── infrastructure/  # 외부 연동
└── presentation/    # API 레이어
```

### .cursorrules

Cursor IDE에서 사용하는 프로젝트별 AI 규칙 파일이다.

```
# MyShop Backend Rules

You are a senior Java/Spring developer working on an e-commerce backend.

## Architecture
Follow hexagonal architecture:
- domain: pure business logic, no framework dependencies
- application: use cases, orchestrates domain objects
- infrastructure: Spring, JPA, external APIs
- presentation: REST controllers

## Coding Standards
- Use constructor injection only
- All services must be stateless
- Use Optional properly (never call get() without isPresent())
- Prefer composition over inheritance
- Name variables in English, comments in Korean

## Error Handling
- Use custom exceptions extending BaseException
- Always include error code in exceptions
- HTTP status codes:
  - 400: validation errors
  - 401: authentication required
  - 403: authorization failed
  - 404: resource not found
  - 409: conflict (duplicate, etc.)
  - 500: unexpected errors

## Testing
- Mock external dependencies
- Test method names: should_[expected]_when_[condition]
- Arrange-Act-Assert pattern
```

### MCP (Model Context Protocol)

Anthropic이 설계한 표준 프로토콜로, AI 에이전트가 외부 도구·데이터소스와 통신하는 방식을 정의한다.

**MCP 구조**
```
Claude Code (MCP Client)
    ↕ MCP Protocol (JSON-RPC over stdio/SSE)
MCP Server
    ↕
외부 시스템 (DB, API, 파일시스템, IDE)
```

**MCP 서버 종류**

| 서버 | 기능 |
|------|------|
| filesystem | 파일 읽기/쓰기/탐색 |
| github | PR, Issue, 코드 검색 |
| postgres | DB 쿼리 실행 |
| puppeteer | 브라우저 자동화 |
| slack | 메시지 전송/조회 |
| notion | 페이지 읽기/쓰기 |
| lsp | IDE의 Language Server 연동 |

**settings.json 설정 예시**
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/project"]
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "postgresql://localhost/mydb"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_..."
      }
    }
  }
}
```

### Hooks

Claude Code의 Hooks는 AI 에이전트의 실행 흐름에 개입하는 자동화 메커니즘이다.

**Hook 종류**

| Hook | 트리거 시점 |
|------|-----------|
| PreToolUse | 도구 실행 전 |
| PostToolUse | 도구 실행 후 |
| PreCompact | 컨텍스트 압축 전 |
| Notification | 알림 발생 시 |
| Stop | 에이전트 종료 시 |

**settings.json Hook 설정**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "echo '위험한 명령어 실행 전 확인' >&2"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /scripts/verify_edit.py"
          }
        ]
      }
    ]
  }
}
```

**실전 Hook 예시: 파일 수정 후 자동 포맷**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "cd $PROJECT_ROOT && ./gradlew spotlessApply -q 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
```

### 에이전트 제어 전략

**권한 범위 제한**
```markdown
# CLAUDE.md - 작업 범위

## 허용된 작업
- src/ 디렉토리 내 파일 수정
- 테스트 실행 (./gradlew test)
- Git 상태 확인 (git status, git diff)

## 금지된 작업
- git push 실행 금지 (항상 사람이 검토 후 실행)
- 프로덕션 DB 직접 접근 금지
- .env 파일 수정 금지
- 의존성 추가 시 반드시 사람 승인 후 진행
```

**작업 체크리스트 강제**
```markdown
## 코드 변경 체크리스트
코드를 변경할 때마다 다음을 순서대로 실행:
1. 변경할 파일을 먼저 Read로 읽기
2. lsp_diagnostics로 현재 오류 파악
3. 변경 실행
4. lsp_diagnostics 재실행 - 오류 0개 확인
5. 관련 테스트 실행
```

---

## AI + TDD

AI와 TDD를 결합하면 코드 품질을 높이면서 생산성도 유지할 수 있다.

### AI-TDD 워크플로우

```
1. 요구사항 → 테스트 케이스 설계 (개발자)
2. AI에게 테스트 코드 작성 요청
3. 테스트 검토 및 수정 (개발자)
4. AI에게 테스트를 통과하는 구현 코드 작성 요청
5. 테스트 실행 검증
6. 리팩토링 (AI 도움 활용)
```

### 실전 예시

**1단계: 테스트 케이스 설계 지시**
```
UserService.withdraw() 메서드에 대한 TDD를 진행한다.
다음 케이스에 대한 단위 테스트를 먼저 작성해줘:
- 정상 출금
- 잔액 부족
- 출금 한도 초과
- 계좌가 잠긴 경우
- 금액이 0 이하인 경우
```

**2단계: AI가 생성한 테스트**
```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock UserRepository userRepository;
    @Mock AccountRepository accountRepository;
    @InjectMocks UserService userService;

    @Test
    @DisplayName("정상 출금 성공")
    void should_withdraw_success_when_balance_sufficient() {
        // Arrange
        Account account = Account.builder()
            .balance(100_000L)
            .status(AccountStatus.ACTIVE)
            .dailyLimit(500_000L)
            .build();
        given(accountRepository.findById(1L)).willReturn(Optional.of(account));

        // Act
        WithdrawResult result = userService.withdraw(1L, 50_000L);

        // Assert
        assertThat(result.isSuccess()).isTrue();
        assertThat(account.getBalance()).isEqualTo(50_000L);
    }

    @Test
    @DisplayName("잔액 부족 시 InsufficientBalanceException 발생")
    void should_throw_exception_when_balance_insufficient() {
        Account account = Account.builder()
            .balance(10_000L)
            .status(AccountStatus.ACTIVE)
            .build();
        given(accountRepository.findById(1L)).willReturn(Optional.of(account));

        assertThatThrownBy(() -> userService.withdraw(1L, 50_000L))
            .isInstanceOf(InsufficientBalanceException.class)
            .hasMessageContaining("잔액이 부족합니다");
    }

    // ... 추가 케이스
}
```

**3단계: 구현 코드 요청**
```
위 테스트를 모두 통과하는 UserService.withdraw() 메서드를 구현해줘.
Account 도메인 객체에 withdraw() 메서드를 만들고, 도메인 로직은 도메인 객체 안에 위치시켜줘.
```

---

## AI Slop 방지

**AI Slop**이란 AI가 생성했지만 불필요하게 장황하고, 진부하며, 실제로 유용하지 않은 코드나 텍스트를 말한다.

### AI Slop의 특징

```java
// AI Slop 예시 - 불필요하게 복잡한 "방어적" 코드
public Optional<User> findUserById(Long userId) {
    // null 체크 (ID가 null일 수 있으므로)
    if (userId == null) {
        logger.warn("userId가 null입니다");
        return Optional.empty();
    }

    // ID 유효성 검사 (음수 ID는 유효하지 않음)
    if (userId <= 0) {
        logger.warn("유효하지 않은 userId: {}", userId);
        return Optional.empty();
    }

    try {
        // 데이터베이스에서 사용자 조회
        Optional<User> userOptional = userRepository.findById(userId);

        // 사용자가 존재하는 경우
        if (userOptional.isPresent()) {
            logger.debug("사용자 조회 성공: {}", userId);
            return userOptional;
        } else {
            // 사용자가 존재하지 않는 경우
            logger.debug("사용자를 찾을 수 없음: {}", userId);
            return Optional.empty();
        }
    } catch (Exception e) {
        logger.error("사용자 조회 중 오류 발생", e);
        return Optional.empty();
    }
}

// 적절한 코드
public Optional<User> findUserById(Long userId) {
    return userRepository.findById(userId);
}
```

### AI Slop 방지 전략

**1. 프롬프트에 명시적 제약 추가**
```
다음 규칙을 지켜서 코드를 작성해줘:
- 불필요한 null 체크 금지 (Non-null이 보장되는 곳)
- 과도한 로깅 금지
- 코드 줄 수를 최소화
- 자명한 주석 금지 ("// 사용자 조회" 같은 주석)
- 방어적 프로그래밍이 필요한 곳만 예외처리
```

**2. 코드 리뷰 프롬프트 활용**
```
아래 코드에서 AI Slop을 제거해줘:
- 자명한 주석 제거
- 불필요한 null 체크 제거
- 과도하게 방어적인 로직 단순화
- 중복 코드 통합
핵심 비즈니스 로직과 정상적인 예외처리는 유지해줘.
```

**3. oh-my-claudecode ai-slop-cleaner 활용**
```bash
# Claude Code 내에서
/oh-my-claudecode:ai-slop-cleaner
```

### 검증 체크리스트

```
AI 생성 코드 검토 시 확인 사항:
□ 실제로 동작하는가? (테스트 실행)
□ 기존 코드 패턴과 일치하는가?
□ 불필요한 추상화가 없는가?
□ 자명한 주석이 없는가?
□ 과도한 예외처리가 없는가?
□ 사용되지 않는 import가 없는가?
□ 하드코딩된 값이 없는가?
□ 기존에 있는 유틸리티를 재발명하지 않았는가?
```

---

## 하네스 엔지니어링 성숙도 모델

```
Level 1: 단순 사용
  - AI에게 코드 작성 요청, 그대로 붙여넣기
  - 결과: AI Slop 누적, 품질 저하

Level 2: 프롬프트 개선
  - 컨텍스트 제공, 제약 명시
  - 결과: 더 나은 코드, 하지만 일관성 없음

Level 3: 환경 설정
  - CLAUDE.md / .cursorrules 작성
  - MCP 도구 연동
  - 결과: 일관된 코드 스타일

Level 4: 자동화 파이프라인
  - Hooks로 사후 검증 자동화
  - AI + CI/CD 통합
  - 결과: 품질 게이트 자동 적용

Level 5: 에이전트 오케스트레이션
  - 멀티 에이전트 병렬 실행
  - 전문화된 에이전트 역할 분리
  - 결과: 대규모 자율 개발
```

---

## 마치며

AI-Driven Development는 도구를 잘 쓰는 것에서 끝나지 않는다. AI가 올바른 방향으로 작업하도록 환경을 설계하고(하네스 엔지니어링), AI 출력을 검증하는 체계를 갖추는 것이 핵심이다. 결국 AI를 잘 활용하는 개발자는 더 빠르게, 더 일관된 품질로 소프트웨어를 만들 수 있다.
