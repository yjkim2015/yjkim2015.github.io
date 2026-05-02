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

> **비유**: AI는 뛰어난 신입 개발자와 같다. 빠르게 코드를 작성하지만 맥락을 모르면 엉뚱한 방향으로 간다. 시니어 개발자(하네스 엔지니어)가 명확한 지시, 제약, 검증 체계를 갖춰줄 때 비로소 제 실력을 발휘한다. 신입에게 "알아서 해봐"라고 하면 안 된다.

---

## AI-Driven Development란

AI-Driven Development(ADD)는 AI 도구를 개발 워크플로우의 중심에 배치하고, 개발자가 **방향·검증·아키텍처 결정**에 집중하는 개발 방식이다.

| 구분 | 전통 개발 | AI-Driven 개발 |
|------|-----------|----------------|
| 코드 작성 | 개발자 직접 작성 | AI 생성, 개발자 검토 |
| 반복 작업 | 개발자가 직접 처리 | AI 자동화 |
| 디버깅 | 로그/디버거 기반 | AI와 대화식 해결 |
| 테스트 작성 | 수동 작성 | AI 초안 생성 후 검토 |
| 개발자 역할 | 구현자 | 설계자 + 검증자 |

### 핵심 원칙

1. **의도를 명확히 표현**: 모호한 지시는 나쁜 결과를 낳는다
2. **작은 단위로 반복**: 큰 작업을 쪼개어 각 단계를 검증한다
3. **AI 출력을 맹신하지 않는다**: 반드시 검토하고 테스트한다
4. **컨텍스트를 관리한다**: 관련 파일, 규칙, 제약을 명시적으로 제공한다

---

## AI 개발 워크플로우

<div class="mermaid">
graph TD
    A["1️⃣ 요구사항 분석 (개발자)"] --> B["2️⃣ 컨텍스트 준비\n관련 파일, 규칙, 제약 명시"]
    B --> C["3️⃣ AI에게 작업 지시 (프롬프트)"]
    C --> D["4️⃣ AI 출력 검토 (개발자)"]
    D --> E["5️⃣ 테스트/검증 실행"]
    E -->|"수정 필요"| B
    E -->|"완료"| F["완료"]
</div>

### AI가 잘하는 것 vs 못하는 것

**AI가 잘하는 것**
- 보일러플레이트 코드 생성
- 단순 CRUD 구현
- 리팩토링 (변수명 변경, 메서드 추출)
- 테스트 케이스 생성
- 문서 작성, 주석 추가
- 정규식, SQL 쿼리 작성

**AI가 잘 못하는 것**
- 복잡한 비즈니스 로직 설계
- 성능 병목 원인 분석 (컨텍스트 부족 시)
- 장기적 아키텍처 결정
- 다중 시스템 연동 설계
- 도메인 특화 지식이 필요한 구현

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
- 기존 UserRepository: findByEmail(String email) 있음

[작업]
이메일/비밀번호 기반 로그인 API를 구현해주세요.

[제약]
- POST /api/auth/login 엔드포인트
- 성공 시 AccessToken(15분) + RefreshToken(7일) 반환
- 실패 시 적절한 HTTP 상태코드와 에러 메시지 반환
- 비밀번호는 BCrypt로 검증
- 생성자 주입 사용

[출력 형식]
1. LoginRequest DTO
2. LoginResponse DTO
3. AuthService 로그인 메서드
4. AuthController 엔드포인트
5. 단위 테스트
```

### 프롬프트 패턴

**Chain-of-Thought**: 단계별 분석을 유도해 정확도를 높인다.
```
다음 문제를 단계별로 분석해줘:
1. 현재 코드의 문제점 파악
2. 해결 방법 제시
3. 구현 코드 작성
4. 테스트 방법 설명
```

**Few-Shot**: 기대하는 패턴을 예시로 보여준다.
```java
// 예시 패턴으로 작성해줘:
public Result<User> findById(Long id) {
    return userRepository.findById(id)
        .map(Result::success)
        .orElse(Result.failure("사용자를 찾을 수 없습니다"));
}
// 위 패턴으로 OrderService.findByOrderNumber() 작성해줘
```

**반복 정제**: 한 번에 완성하려 하지 말고 단계적으로 개선한다.
```
1차: "UserService.registerUser() 메서드 작성해줘"
2차: "이메일 중복 검사 추가하고, 예외를 커스텀 예외로 바꿔줘"
3차: "이메일 형식 검증과 비밀번호 정책 검증 추가해줘"
4차: "단위 테스트 작성해줘. 성공/실패/예외 케이스 포함"
```

---

## 하네스 엔지니어링

하네스 엔지니어링이란 **AI가 올바르게 동작하도록 환경, 제약, 가이드를 설계하는 기술**이다. 자동차의 와이어 하네스가 전기 신호를 올바른 곳으로 인도하듯, AI의 출력을 원하는 방향으로 유도한다.

<div class="mermaid">
graph TD
    subgraph "하네스 엔지니어링 레이어"
        CLAUDEMD["CLAUDE.md\n프로젝트 규칙/제약 정의"]
        MCP["MCP 서버\n외부 도구 연동"]
        HOOKS["Hooks\n자동화 검증 파이프라인"]
        PROMPT["프롬프트 패턴\n일관된 출력 유도"]
    end
    CLAUDEMD --> AI["AI 에이전트"]
    MCP --> AI
    HOOKS --> AI
    PROMPT --> AI
    AI --> OUTPUT["일관되고 안전한 출력"]
</div>

### CLAUDE.md — 프로젝트 전역 AI 지시서

Claude Code에서 프로젝트 루트에 위치하는 설정 파일이다. AI가 작업을 시작할 때 자동으로 읽어 컨텍스트로 활용한다.

```markdown
# 프로젝트: MyShop Backend

## 기술 스택
- Java 21, Spring Boot 3.2
- MySQL 8.0, Redis 7

## 코딩 규칙
- 생성자 주입 강제 (@Autowired 필드 주입 금지)
- 모든 공개 메서드에 Javadoc 필수
- 커스텀 예외는 BaseException 상속
- 로깅: SLF4J 사용, System.out.println 금지

## 작업 규칙
- 코드 변경 전 반드시 기존 코드 파악 (Read 먼저)
- 변경 후 lsp_diagnostics 실행 → 오류 0개 확인
- 테스트 없이 커밋 금지

## 금지 사항
- 하드코딩된 설정값 금지 (application.yml 사용)
- git push 실행 금지 (사람이 검토 후 실행)
- 프로덕션 DB 직접 접근 금지
```

### MCP (Model Context Protocol)

Anthropic이 설계한 표준 프로토콜로, AI 에이전트가 외부 도구·데이터소스와 통신하는 방식을 정의한다.

```
Claude Code (MCP Client)
    ↕ MCP Protocol (JSON-RPC)
MCP Server
    ↕
외부 시스템 (DB, API, 파일시스템, IDE)
```

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
      "env": { "DATABASE_URL": "postgresql://localhost/mydb" }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "ghp_..." }
    }
  }
}
```

### Hooks — 실행 흐름 자동화

Claude Code의 Hooks는 AI 에이전트의 실행 흐름에 개입하는 자동화 메커니즘이다.

| Hook | 트리거 시점 |
|------|-----------|
| PreToolUse | 도구 실행 전 |
| PostToolUse | 도구 실행 후 |
| Stop | 에이전트 종료 시 |

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

파일 수정 후 자동으로 포맷팅이 적용되므로 코드 스타일 불일치가 방지된다.

---

## AI + TDD

AI와 TDD를 결합하면 코드 품질을 높이면서 생산성도 유지할 수 있다. 테스트를 먼저 정의하면 AI의 출력 방향이 명확해진다.

```
1. 요구사항 → 테스트 케이스 설계 (개발자)
2. AI에게 테스트 코드 작성 요청
3. 테스트 검토 및 수정 (개발자)
4. AI에게 테스트를 통과하는 구현 코드 작성 요청
5. 테스트 실행으로 검증
6. 리팩토링 (AI 도움 활용)
```

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

**2단계: AI가 생성한 테스트 → 검토 후**
**3단계: 구현 코드 요청**
```
위 테스트를 모두 통과하는 UserService.withdraw() 메서드를 구현해줘.
Account 도메인 객체에 withdraw() 메서드를 만들고 도메인 로직은 도메인 객체 안에 위치시켜줘.
```

---

## AI Slop 방지

**AI Slop**이란 AI가 생성했지만 불필요하게 장황하고 진부하며 실제로 유용하지 않은 코드를 말한다.

```java
// AI Slop: 자명한 주석, 불필요한 null 체크, 과도한 로깅
public Optional<User> findUserById(Long userId) {
    if (userId == null) {           // 불필요한 null 체크
        logger.warn("userId가 null입니다");  // 자명한 로그
        return Optional.empty();
    }
    if (userId <= 0) {              // 불필요한 음수 체크
        logger.warn("유효하지 않은 userId: {}", userId);
        return Optional.empty();
    }
    try {
        Optional<User> userOptional = userRepository.findById(userId);
        if (userOptional.isPresent()) {
            logger.debug("사용자 조회 성공: {}", userId);  // 자명한 로그
            return userOptional;
        }
        return Optional.empty();
    } catch (Exception e) {
        logger.error("오류 발생", e);
        return Optional.empty();    // 예외를 삼켜버림
    }
}

// 올바른 코드: 단 1줄
public Optional<User> findUserById(Long userId) {
    return userRepository.findById(userId);
}
```

**AI Slop 방지 프롬프트**
```
다음 규칙을 지켜서 코드를 작성해줘:
- 불필요한 null 체크 금지 (Non-null이 보장되는 곳)
- 자명한 주석 금지 ("// 사용자 조회" 같은 주석)
- 코드 줄 수를 최소화
- 방어적 프로그래밍이 필요한 곳만 예외처리
```

---

## 하네스 엔지니어링 성숙도 모델

<div class="mermaid">
graph TD
    L1["Level 1: 단순 사용\nAI 출력 그대로 붙여넣기\n→ AI Slop 누적"]
    L2["Level 2: 프롬프트 개선\n컨텍스트 제공, 제약 명시\n→ 더 나은 코드, 일관성 없음"]
    L3["Level 3: 환경 설정\nCLAUDE.md / .cursorrules 작성\nMCP 도구 연동\n→ 일관된 코드 스타일"]
    L4["Level 4: 자동화 파이프라인\nHooks로 사후 검증 자동화\nAI + CI/CD 통합\n→ 품질 게이트 자동 적용"]
    L5["Level 5: 에이전트 오케스트레이션\n멀티 에이전트 병렬 실행\n전문화된 에이전트 역할 분리\n→ 대규모 자율 개발"]
    L1 --> L2 --> L3 --> L4 --> L5
</div>

---

## AI 생성 코드 검증 체크리스트

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
□ 보안 취약점이 없는가? (SQL Injection, XSS 등)
```
