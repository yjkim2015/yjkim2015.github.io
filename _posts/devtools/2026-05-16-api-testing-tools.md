---
title: "API 테스트 도구 완벽 가이드 — Postman, Insomnia, curl, httpie"
categories: DEVTOOLS
tags: [Postman, Insomnia, curl, httpie, API테스트, HTTPClient]
toc: true
toc_sticky: true
toc_label: 목차
date: 2026-05-16
---

API 테스트 도구는 백엔드 개발의 청진기다. Postman으로 GUI 기반 탐색, curl/httpie로 CLI 자동화, IntelliJ HTTP Client로 코드 옆에서 바로 검증까지 — 5가지 도구의 심화 사용법과 CI/CD 파이프라인 연동, 인증 처리, 계약 테스트까지 한 번에 정리한다.

---

## 왜 API 테스트 도구가 필요한가

백엔드 개발에서 API는 모든 시스템의 접점이다. 프론트엔드, 모바일 앱, 외부 파트너 시스템 모두 API를 통해 데이터를 주고받는다. 이 접점이 제대로 동작하는지 검증하지 않으면, 장애는 배포 후에야 발견된다.

> **비유:** API 테스트 도구는 의사의 청진기다. 환자(서버)에게 "숨을 크게 쉬어보세요"(요청을 보내고) 하고, 심장 소리(응답 코드, 바디, 헤더)를 듣는 것이다. 청진기 없이 "아마 건강하겠지"라고 넘기면, 수술실(프로덕션)에서 문제가 터진다.

API 테스트 도구가 필요한 구체적인 이유는 다음과 같다.

**개발 중 즉시 검증:** 컨트롤러를 작성한 직후, 프론트엔드가 완성되기 전에 API 동작을 확인해야 한다. 브라우저 개발자 도구만으로는 POST/PUT/DELETE 요청을 보내기 번거롭다.

**재현 가능한 테스트:** "아까는 됐는데 지금은 안 된다"는 상황에서, 동일한 요청을 정확히 재현할 수 있어야 한다. 테스트 도구는 요청을 저장하고 반복 실행할 수 있다.

**팀 협업:** QA 엔지니어, 프론트엔드 개발자, 외부 파트너에게 "이 API는 이렇게 호출하면 된다"를 도구의 Collection이나 .http 파일로 공유할 수 있다.

**자동화:** 수동 테스트는 규모가 커지면 한계가 있다. CI/CD 파이프라인에서 배포마다 자동으로 API를 검증해야 한다.

```mermaid
graph LR
    DEV["개발자 작성"] --> TOOL["API 테스트 도구"]
    TOOL --> MANUAL["수동 검증"]
    TOOL --> AUTO["자동화 테스트"]
    AUTO --> CICD["CI/CD 파이프라인"]
    CICD --> DEPLOY["안전한 배포"]
```

---

## 5대 도구 비교표

API 테스트 도구는 크게 GUI 기반과 CLI 기반으로 나뉜다. 각 도구는 사용 목적과 환경에 따라 장단점이 명확하다.

| 항목 | Postman | Insomnia | curl | httpie | IntelliJ HTTP Client |
|------|---------|----------|------|--------|---------------------|
| **타입** | GUI | GUI | CLI | CLI | IDE 내장 |
| **가격** | 무료 + 유료 플랜 | 무료(오픈소스 코어) | 무료 | 무료 | IntelliJ 라이선스 포함 |
| **학습 곡선** | 낮음 | 낮음 | 높음 | 중간 | 중간 |
| **자동화** | Newman CLI | CLI 제한적 | 네이티브 | 네이티브 | Gradle/Maven 연동 |
| **팀 협업** | Cloud 동기화 | Git Sync | 스크립트 공유 | 스크립트 공유 | .http 파일 Git 공유 |
| **환경 변수** | Environment | Environment | 셸 변수 | 셸 변수 | http-client.env.json |
| **스크립팅** | JavaScript | JavaScript/Plugin | 셸 스크립트 | 셸 스크립트 | JavaScript |
| **CI/CD 통합** | Newman | 제한적 | 네이티브 | 네이티브 | Gradle task |
| **오프라인** | 가능 | 가능 | 가능 | 가능 | 가능 |
| **플러그인** | 풍부 | 보통 | 없음 | 플러그인 지원 | IDE 플러그인 |

> **비유:** Postman은 풀옵션 SUV다. 편하고 기능이 많지만 무겁다. curl은 수동 변속 스포츠카다. 불편하지만 가장 빠르고 어디든 간다. httpie는 자동 변속 스포츠카다. curl의 파워에 편의성을 더했다. IntelliJ HTTP Client는 차고에 내장된 정비 리프트다. 코드 바로 옆에서 테스트한다.

---

## Postman 심화

Postman은 가장 널리 쓰이는 API 테스트 도구다. 단순히 요청을 보내는 것을 넘어, Collection, Environment, Pre/Post Script, Newman을 활용하면 엔터프라이즈 수준의 API 테스트 체계를 구축할 수 있다.

### Collection 구조 설계

Collection은 관련 API 요청을 폴더로 그룹화한 것이다. 단순히 요청을 모아두는 것이 아니라, 실행 순서와 데이터 흐름을 설계하는 단위다.

> **비유:** Collection은 요리 레시피북이다. "한식" 폴더 안에 "밥 짓기", "국 끓이기", "반찬 만들기"가 순서대로 들어 있다. 레시피북을 처음부터 끝까지 따라하면(Collection Runner), 한 상 차림이 완성된다.

실무에서 Collection 구조를 설계할 때는 다음 원칙을 따른다.

**도메인별 분리:** `/users`, `/orders`, `/products` 등 도메인별로 최상위 폴더를 나눈다. 마이크로서비스 아키텍처라면 서비스별로 Collection 자체를 분리한다.

**CRUD 순서 배치:** 각 도메인 폴더 안에서 Create -> Read -> Update -> Delete 순서로 요청을 배치한다. Collection Runner로 순차 실행하면 데이터 생성부터 삭제까지 전체 라이프사이클을 테스트할 수 있다.

**의존성 체이닝:** POST /users 응답에서 userId를 추출하여 GET /users/{% raw %}{{userId}}{% endraw %}에 사용하는 식으로, 앞선 요청의 응답을 뒤 요청의 입력으로 연결한다.

```json
{
  "collection": {
    "info": { "name": "User Service API" },
    "item": [
      {
        "name": "Users",
        "item": [
          { "name": "Create User",   "request": { "method": "POST",   "url": "{% raw %}{{baseUrl}}{% endraw %}/users" }},
          { "name": "Get User",      "request": { "method": "GET",    "url": "{% raw %}{{baseUrl}}{% endraw %}/users/{% raw %}{{userId}}{% endraw %}" }},
          { "name": "Update User",   "request": { "method": "PUT",    "url": "{% raw %}{{baseUrl}}{% endraw %}/users/{% raw %}{{userId}}{% endraw %}" }},
          { "name": "Delete User",   "request": { "method": "DELETE", "url": "{% raw %}{{baseUrl}}{% endraw %}/users/{% raw %}{{userId}}{% endraw %}" }}
        ]
      }
    ]
  }
}
```

### Environment와 변수 시스템

Postman의 변수 시스템은 5단계 스코프를 가진다. 좁은 범위가 넓은 범위를 오버라이드한다.

1. **Local (Data):** Collection Runner에서 CSV/JSON으로 주입하는 일회성 데이터
2. **Environment:** dev, staging, prod 등 환경별 설정 (baseUrl, apiKey 등)
3. **Collection:** 해당 Collection 안에서만 유효한 변수
4. **Global:** 모든 Collection에서 공유하는 변수
5. **Built-in:** {% raw %}`{{$randomInt}}`{% endraw %}, {% raw %}`{{$timestamp}}`{% endraw %} 등 Postman 내장 동적 변수

```mermaid
graph LR
    LOCAL["Local 변수"] --> ENV["Environment"]
    ENV --> COLL["Collection 변수"]
    COLL --> GLOBAL["Global 변수"]
    GLOBAL --> BUILT["Built-in 변수"]
```

실무에서 가장 중요한 것은 Environment 분리다. 같은 Collection을 dev/staging/prod 환경에서 실행할 때, Environment만 전환하면 된다.

```json
{
  "id": "env-dev",
  "name": "Development",
  "values": [
    { "key": "baseUrl",  "value": "http://localhost:8080/api" },
    { "key": "apiKey",   "value": "dev-key-xxx" },
    { "key": "timeout",  "value": "30000" }
  ]
}
```

**주의사항:** prod 환경의 API Key나 시크릿을 Postman Cloud에 동기화하면 안 된다. Environment에서 "Current Value"는 로컬에만 저장되고 "Initial Value"는 클라우드에 동기화된다. 시크릿은 반드시 Current Value에만 입력한다.

### Pre-request Script와 Test Script

Pre-request Script는 요청 전에 실행되는 JavaScript 코드다. 동적 데이터 생성, 인증 토큰 갱신, 타임스탬프 계산 등에 사용한다.

Test Script(Post-response Script)는 응답을 받은 후 실행되는 코드다. 상태 코드 검증, 응답 바디 파싱, 변수 저장 등에 사용한다.

> **비유:** Pre-request Script는 식당 예약 전에 전화로 "오늘 특별 메뉴 있나요?"를 확인하는 것이다. Test Script는 음식이 나온 뒤 "주문한 것과 같은가? 온도는 적당한가? 양은 충분한가?"를 체크하는 것이다.

**Pre-request Script 예시 — 동적 토큰 갱신:**

{% raw %}
```javascript
// 토큰 만료 확인 후 자동 갱신
const tokenExpiry = pm.environment.get("tokenExpiry");
const now = Date.now();

if (!tokenExpiry || now > parseInt(tokenExpiry)) {
    pm.sendRequest({
        url: pm.environment.get("baseUrl") + "/auth/token",
        method: "POST",
        header: { "Content-Type": "application/json" },
        body: {
            mode: "raw",
            raw: JSON.stringify({
                clientId: pm.environment.get("clientId"),
                clientSecret: pm.environment.get("clientSecret")
            })
        }
    }, function (err, res) {
        const body = res.json();
        pm.environment.set("accessToken", body.accessToken);
        // 만료 5분 전에 갱신하도록 설정
        pm.environment.set("tokenExpiry", now + (body.expiresIn * 1000) - 300000);
    });
}
```
{% endraw %}

**Test Script 예시 — 응답 검증 + 변수 체이닝:**

{% raw %}
```javascript
// 상태 코드 검증
pm.test("Status code is 201", function () {
    pm.response.to.have.status(201);
});

// 응답 시간 검증 (SLA: 500ms 이내)
pm.test("Response time < 500ms", function () {
    pm.expect(pm.response.responseTime).to.be.below(500);
});

// 응답 바디 구조 검증
pm.test("Response has required fields", function () {
    const body = pm.response.json();
    pm.expect(body).to.have.property("id");
    pm.expect(body).to.have.property("email");
    pm.expect(body.email).to.be.a("string");
});

// 다음 요청에서 사용할 변수 저장
const userId = pm.response.json().id;
pm.environment.set("userId", userId);
```
{% endraw %}

### Newman — CI/CD 연동의 핵심

Newman은 Postman Collection을 CLI에서 실행하는 도구다. GUI 없이 터미널이나 CI/CD 파이프라인에서 Postman 테스트를 자동화한다.

```bash
# 기본 실행
newman run collection.json -e environment.json

# HTML 리포트 생성
newman run collection.json \
  -e environment.json \
  -r htmlextra \
  --reporter-htmlextra-export ./reports/api-test.html

# 반복 실행 + 데이터 주입
newman run collection.json \
  -e environment.json \
  -d testdata.csv \
  -n 100 \
  --delay-request 100

# 특정 폴더만 실행
newman run collection.json \
  -e environment.json \
  --folder "Users"
```

**Newman의 주요 옵션:**

| 옵션 | 설명 | 예시 |
|------|------|------|
| `-e` | Environment 파일 | `-e dev.json` |
| `-d` | 데이터 파일 (CSV/JSON) | `-d users.csv` |
| `-n` | 반복 횟수 | `-n 50` |
| `--delay-request` | 요청 간 딜레이(ms) | `--delay-request 200` |
| `--timeout-request` | 요청 타임아웃(ms) | `--timeout-request 5000` |
| `-r` | 리포터 | `-r cli,htmlextra,junit` |
| `--bail` | 첫 실패 시 중단 | `--bail` |

Newman을 GitHub Actions에서 실행하는 워크플로우는 다음과 같다.

```yaml
name: API Test
on:
  push:
    branches: [main]

jobs:
  api-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Newman
        run: npm install -g newman newman-reporter-htmlextra

      - name: Run API Tests
        run: |
          newman run ./postman/collection.json \
            -e ./postman/env-staging.json \
            -r cli,junit,htmlextra \
            --reporter-junit-export results.xml \
            --reporter-htmlextra-export report.html

      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: api-test-report
          path: report.html
```

---

## Insomnia — 경량 오픈소스 대안

Insomnia는 Kong이 개발한 오픈소스 API 테스트 도구다. Postman 대비 가볍고, Git 기반 동기화를 지원하며, GraphQL과 gRPC 테스트에 특히 강점을 가진다.

> **비유:** Postman이 대형 마트라면, Insomnia는 동네 전문 식료품점이다. 품목 수는 적지만, 필요한 것은 다 있고, 동선이 짧아서 빠르게 장을 볼 수 있다.

### Insomnia의 핵심 특징

**Git Sync:** Insomnia의 데이터는 Git 저장소에 직접 동기화된다. Postman Cloud 계정이 필요 없고, 기존 Git 워크플로우(브랜치, PR, 리뷰)를 그대로 활용할 수 있다. API 스펙 변경을 코드 리뷰와 동일한 프로세스로 관리할 수 있다는 것이 핵심이다.

**경량 UI:** Electron 기반이지만 Postman 대비 메모리 사용량이 적다. 요청 편집기, 응답 뷰어, 환경 관리 등 핵심 기능에 집중한 미니멀한 인터페이스다.

**플러그인 시스템:** 커뮤니티 플러그인으로 기능을 확장할 수 있다. 커스텀 인증, 코드 생성, 테마 등을 추가할 수 있다.

**Design 탭:** OpenAPI(Swagger) 스펙을 직접 편집하고, 스펙에서 바로 요청을 생성할 수 있다. API-first 개발 방식에 적합하다.

```yaml
# Insomnia에서 export된 YAML 형식
_type: export
__export_format: 4
resources:
  - _type: request
    name: Create User
    method: POST
    url: "{% raw %}{{ _.baseUrl }}{% endraw %}/users"
    body:
      mimeType: application/json
      text: |
        {
          "name": "{% raw %}{{ _.userName }}{% endraw %}",
          "email": "{% raw %}{{ _.userEmail }}{% endraw %}"
        }
    headers:
      - name: Authorization
        value: "Bearer {% raw %}{{ _.token }}{% endraw %}"
```

### Insomnia vs Postman 선택 기준

**Insomnia를 선택해야 할 때:**
- Git 기반 협업이 조직 표준인 경우
- GraphQL/gRPC API를 주로 테스트하는 경우
- Postman Cloud 의존성을 피하고 싶은 경우
- 가벼운 도구를 선호하는 경우

**Postman을 선택해야 할 때:**
- 대규모 팀에서 Collection 공유가 필요한 경우
- Newman 기반 CI/CD 파이프라인이 이미 구축된 경우
- Mock Server, Monitor 등 고급 기능이 필요한 경우
- 비개발자(QA, PM)도 함께 사용하는 경우

---

## curl 고급 사용법

curl은 가장 오래되고 가장 보편적인 HTTP 클라이언트다. 모든 리눅스/맥 시스템에 기본 설치되어 있고, 스크립트 자동화에 가장 적합하다. 하지만 옵션이 방대하여 고급 사용법을 모르면 활용도가 제한된다.

> **비유:** curl은 스위스 군용 칼이다. 수십 가지 도구가 접혀 있지만, 칼날과 가위만 쓰는 사람이 대부분이다. 드라이버, 톱, 병따개(고급 옵션)를 알면 활용 범위가 폭발적으로 넓어진다.

### 기본 요청

```bash
# GET 요청
curl https://api.example.com/users

# POST JSON 요청
curl -X POST https://api.example.com/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Kim", "email": "kim@example.com"}'

# PUT 요청
curl -X PUT https://api.example.com/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Kim Updated"}'

# DELETE 요청
curl -X DELETE https://api.example.com/users/1

# PATCH 요청
curl -X PATCH https://api.example.com/users/1 \
  -H "Content-Type: application/json" \
  -d '{"email": "new@example.com"}'
```

### 응답 분석 옵션

```bash
# 응답 헤더 포함 출력
curl -i https://api.example.com/users

# 응답 헤더만 출력
curl -I https://api.example.com/users

# 상세 디버그 정보 (요청/응답 헤더 모두)
curl -v https://api.example.com/users

# 응답 시간 측정
curl -o /dev/null -s -w "\
  DNS Lookup:  %{time_namelookup}s\n\
  TCP Connect: %{time_connect}s\n\
  TLS Setup:   %{time_appconnect}s\n\
  First Byte:  %{time_starttransfer}s\n\
  Total:       %{time_total}s\n\
  Status:      %{http_code}\n\
  Size:        %{size_download} bytes\n" \
  https://api.example.com/users

# JSON 응답 포맷팅 (jq 연동)
curl -s https://api.example.com/users | jq '.'

# 특정 필드 추출
curl -s https://api.example.com/users | jq '.[0].name'
```

### 인증 처리

```bash
# Basic Auth
curl -u username:password https://api.example.com/protected

# Bearer Token
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9..." \
  https://api.example.com/protected

# API Key (헤더)
curl -H "X-API-Key: your-api-key" \
  https://api.example.com/data

# API Key (쿼리 파라미터)
curl "https://api.example.com/data?api_key=your-api-key"

# OAuth2 토큰 발급 후 사용
TOKEN=$(curl -s -X POST https://auth.example.com/oauth/token \
  -d "grant_type=client_credentials" \
  -d "client_id=xxx" \
  -d "client_secret=yyy" | jq -r '.access_token')

curl -H "Authorization: Bearer $TOKEN" \
  https://api.example.com/resource
```

### 파일 업로드/다운로드

```bash
# 파일 업로드 (multipart/form-data)
curl -X POST https://api.example.com/upload \
  -F "file=@/path/to/document.pdf" \
  -F "description=Invoice 2026"

# 여러 파일 동시 업로드
curl -X POST https://api.example.com/upload \
  -F "files[]=@file1.jpg" \
  -F "files[]=@file2.jpg"

# 파일 다운로드
curl -O https://api.example.com/files/report.pdf

# 파일 다운로드 + 이름 지정
curl -o my_report.pdf https://api.example.com/files/report.pdf

# 대용량 파일 이어받기
curl -C - -O https://api.example.com/files/large.zip
```

### 고급 스크립팅 패턴

```bash
#!/bin/bash
# API 헬스체크 스크립트

ENDPOINTS=(
  "https://api.example.com/health"
  "https://auth.example.com/health"
  "https://payment.example.com/health"
)

for endpoint in "${ENDPOINTS[@]}"; do
  status=$(curl -s -o /dev/null -w "%{http_code}" "$endpoint")
  latency=$(curl -s -o /dev/null -w "%{time_total}" "$endpoint")

  if [ "$status" -eq 200 ]; then
    echo "[OK]   $endpoint (${latency}s)"
  else
    echo "[FAIL] $endpoint (HTTP $status, ${latency}s)"
    # 슬랙 알림 전송
    curl -s -X POST "$SLACK_WEBHOOK" \
      -H "Content-Type: application/json" \
      -d "{\"text\": \"API Down: $endpoint (HTTP $status)\"}"
  fi
done
```

---

## httpie — 사람 친화적 CLI

httpie는 "CLI를 위한 Postman"이라 불린다. curl과 동일한 기능을 제공하지만, 문법이 직관적이고 출력이 컬러풀하다. JSON을 기본 지원하며, 사람이 읽기 쉬운 형식으로 요청과 응답을 보여준다.

> **비유:** curl이 어셈블리어라면, httpie는 Python이다. 같은 일을 하지만, httpie는 사람이 읽을 때 편하도록 설계되었다. curl의 `-X POST -H "Content-Type: application/json" -d '{"key":"value"}'`가 httpie에서는 `http POST url key=value`로 줄어든다.

### 설치

```bash
# macOS
brew install httpie

# Ubuntu/Debian
sudo apt install httpie

# pip
pip install httpie

# Windows
winget install httpie
```

### 기본 문법

httpie의 핵심 철학은 "자주 쓰는 것은 짧게"다. method, URL, 데이터를 직관적으로 나열한다.

```bash
# GET (기본 method)
http https://api.example.com/users

# POST JSON (= 으로 문자열, := 으로 숫자/불린/JSON)
http POST https://api.example.com/users \
  name="Kim" \
  age:=30 \
  active:=true \
  tags:='["dev", "backend"]'

# PUT
http PUT https://api.example.com/users/1 name="Updated"

# DELETE
http DELETE https://api.example.com/users/1

# 헤더 추가 (: 구분)
http https://api.example.com/users \
  Authorization:"Bearer token123" \
  Accept:application/json

# 쿼리 파라미터 (== 구분)
http https://api.example.com/users \
  page==2 \
  size==20 \
  sort==name
```

### curl과 httpie 비교

같은 요청을 curl과 httpie로 비교하면 문법 차이가 명확하다.

**curl:**
```bash
curl -X POST https://api.example.com/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer token123" \
  -d '{"name": "Kim", "age": 30, "roles": ["admin"]}'
```

**httpie:**
```bash
http POST https://api.example.com/users \
  Authorization:"Bearer token123" \
  name="Kim" \
  age:=30 \
  roles:='["admin"]'
```

httpie는 Content-Type을 자동으로 `application/json`으로 설정한다. JSON 데이터도 따옴표 이스케이핑 없이 key=value 형식으로 입력한다.

### 세션 관리

httpie는 세션을 파일로 저장하여 인증 정보를 유지할 수 있다.

```bash
# 세션 생성 (로그인)
http --session=dev POST https://api.example.com/auth/login \
  email="admin@example.com" \
  password="secret"

# 같은 세션으로 후속 요청 (쿠키/헤더 자동 포함)
http --session=dev https://api.example.com/users

# 읽기 전용 세션 (세션 파일을 수정하지 않음)
http --session-read-only=dev https://api.example.com/users
```

### 다운로드와 스트리밍

```bash
# 파일 다운로드
http --download https://api.example.com/files/report.pdf

# SSE(Server-Sent Events) 스트리밍
http --stream https://api.example.com/events

# 요청 바디를 파일에서 읽기
http POST https://api.example.com/users < user.json

# 출력을 파일로 저장
http https://api.example.com/users > users.json
```

---

## IntelliJ HTTP Client — IDE 내장 테스트

IntelliJ HTTP Client는 `.http` 또는 `.rest` 확장자 파일에 HTTP 요청을 작성하면 IDE 안에서 바로 실행할 수 있는 도구다. 코드를 작성하면서 바로 옆에서 API를 테스트할 수 있다는 것이 가장 큰 장점이다.

> **비유:** IntelliJ HTTP Client는 주방에 설치된 시식 코너다. 요리(코드)를 만들면서 바로 옆에서 맛(API 응답)을 볼 수 있다. Postman은 별도의 시식 매장이라 이동이 필요하고, curl은 직접 그릇에 담아 먹어봐야 한다.

### .http 파일 문법

```http
### 사용자 생성
POST http://localhost:8080/api/users
Content-Type: application/json

{
  "name": "Kim",
  "email": "kim@example.com",
  "age": 30
}

### 사용자 조회
GET http://localhost:8080/api/users/{{userId}}
Authorization: Bearer {{authToken}}

### 사용자 수정
PUT http://localhost:8080/api/users/{{userId}}
Content-Type: application/json
Authorization: Bearer {{authToken}}

{
  "name": "Kim Updated"
}

### 사용자 삭제
DELETE http://localhost:8080/api/users/{{userId}}
Authorization: Bearer {{authToken}}
```

`###`은 요청 구분자다. 각 요청 옆에 실행 버튼이 나타나며, 클릭 한 번으로 실행할 수 있다. `{% raw %}{{변수명}}{% endraw %}`으로 환경 변수를 참조한다.

### 환경 변수 설정

프로젝트 루트에 `http-client.env.json`과 `http-client.private.env.json` 두 파일로 환경을 관리한다.

**http-client.env.json** (Git에 커밋):
```json
{
  "dev": {
    "baseUrl": "http://localhost:8080/api",
    "userId": "1"
  },
  "staging": {
    "baseUrl": "https://staging.example.com/api",
    "userId": "100"
  },
  "prod": {
    "baseUrl": "https://api.example.com",
    "userId": "1000"
  }
}
```

**http-client.private.env.json** (Git 무시 — .gitignore에 추가):
```json
{
  "dev": {
    "authToken": "dev-jwt-token-xxx",
    "apiKey": "dev-api-key-xxx"
  },
  "staging": {
    "authToken": "staging-jwt-token-xxx"
  }
}
```

### Response Handler Script

IntelliJ HTTP Client는 JavaScript 기반 응답 검증 스크립트를 지원한다. Postman의 Test Script와 유사한 역할이다.

```http
### 사용자 생성 + 응답 검증
POST http://localhost:8080/api/users
Content-Type: application/json

{
  "name": "Test User",
  "email": "test@example.com"
}

> {%
  // 상태 코드 검증
  client.test("Status is 201", function() {
    client.assert(response.status === 201, "Expected 201, got " + response.status);
  });

  // 응답 바디 검증
  client.test("Has user id", function() {
    client.assert(response.body.id !== undefined, "Missing id field");
  });

  // 응답 시간 검증
  client.test("Response time < 1s", function() {
    client.assert(response.headers.valueOf("X-Response-Time") < 1000);
  });

  // 변수 저장 (다음 요청에서 사용)
  client.global.set("userId", response.body.id);
%}

### 방금 생성한 사용자 조회
GET http://localhost:8080/api/users/{{userId}}
Authorization: Bearer {{authToken}}

> {%
  client.test("User name matches", function() {
    client.assert(response.body.name === "Test User");
  });
%}
```

### CLI 실행 (CI/CD 연동)

IntelliJ HTTP Client는 Gradle/Maven 플러그인으로 CI/CD에서도 실행할 수 있다.

```kotlin
// build.gradle.kts
plugins {
    id("org.jetbrains.kotlinx.http-client") version "2024.1"
}

tasks.register<RunHttpClientTask>("apiTest") {
    httpFiles.from("src/test/http")
    environment.set("staging")
}
```

```bash
# Gradle로 실행
./gradlew apiTest

# 특정 .http 파일만 실행
./gradlew apiTest --http-file=users.http
```

---

## 자동화 테스트 파이프라인

수동 API 테스트는 반복 가능하지 않다. 배포할 때마다 모든 API를 수동으로 확인하는 것은 불가능하다. 자동화 테스트 파이프라인을 구축해야 API 품질을 지속적으로 보장할 수 있다.

```mermaid
graph LR
    PR["PR 생성"] --> UNIT["단위 테스트"]
    UNIT --> BUILD["빌드+배포"]
    BUILD --> API["API 자동 테스트"]
    API --> GATE["품질 게이트"]
    GATE --> MERGE["머지 승인"]
```

> **비유:** 자동화 테스트 파이프라인은 공장의 품질 검사 라인이다. 모든 제품(배포)이 라인을 지나면서 치수 검사(상태 코드), 무게 검사(응답 시간), 외관 검사(응답 바디)를 자동으로 통과해야 한다. 검사를 통과하지 못하면 출하(머지)되지 않는다.

### 테스트 레벨별 도구 선택

API 테스트는 목적에 따라 여러 레벨로 나뉘며, 각 레벨에 적합한 도구가 다르다.

**Smoke Test (연기 테스트):** 배포 직후 핵심 API가 살아있는지 확인한다. curl이나 httpie로 간단한 헬스체크 스크립트를 작성한다. 실행 시간 30초 이내가 목표다.

```bash
#!/bin/bash
# smoke-test.sh
BASE_URL="${1:-http://localhost:8080}"
FAILED=0

check() {
  local name=$1 url=$2 expected=$3
  status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
  if [ "$status" -eq "$expected" ]; then
    echo "[PASS] $name"
  else
    echo "[FAIL] $name (expected $expected, got $status)"
    FAILED=$((FAILED + 1))
  fi
}

check "Health"     "$BASE_URL/actuator/health" 200
check "Users API"  "$BASE_URL/api/users"       200
check "Auth API"   "$BASE_URL/api/auth/status"  200

exit $FAILED
```

**Functional Test (기능 테스트):** 각 API의 정상/비정상 케이스를 검증한다. Postman Collection + Newman이 적합하다. CRUD 전체 플로우, 에러 케이스, 엣지 케이스를 포함한다.

**Contract Test (계약 테스트):** 마이크로서비스 간 API 스펙이 호환되는지 검증한다. 소비자가 기대하는 응답 구조와 실제 제공자의 응답 구조가 일치하는지 확인한다. Pact 프레임워크가 대표적이다.

**Performance Test (성능 테스트):** API의 응답 시간, 처리량, 동시 접속자 수를 측정한다. k6, Apache JMeter, Gatling 등을 사용한다.

### 극한 시나리오: CI/CD 자동 API 테스트

실무에서는 단순한 테스트 실행을 넘어, 다음과 같은 극한 시나리오를 대비해야 한다.

**시나리오 1 — 배포 중 API 테스트 타이밍:**
Blue-Green 배포에서 Green 인스턴스가 올라온 직후 API 테스트를 실행한다. 이때 애플리케이션이 완전히 기동되지 않아 헬스체크가 실패할 수 있다. 해결책은 **Readiness Probe 대기 + 재시도 로직**이다.

```bash
# 서버 기동 대기 후 테스트 실행
MAX_RETRIES=30
RETRY_INTERVAL=2

for i in $(seq 1 $MAX_RETRIES); do
  status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/actuator/health")
  if [ "$status" -eq 200 ]; then
    echo "Server ready after $((i * RETRY_INTERVAL))s"
    break
  fi
  sleep $RETRY_INTERVAL
done

newman run collection.json -e env.json --bail
```

**시나리오 2 — 부하 테스트 연계:**
기능 테스트를 통과한 후, 같은 API 시나리오로 부하 테스트를 실행한다. Postman Collection을 k6 스크립트로 변환하면 동일한 시나리오를 재사용할 수 있다.

```javascript
// k6 부하 테스트 스크립트
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },   // 1분간 50 VU로 증가
    { duration: '3m', target: 50 },   // 3분간 50 VU 유지
    { duration: '1m', target: 200 },  // 1분간 200 VU로 증가 (스파이크)
    { duration: '2m', target: 200 },  // 2분간 200 VU 유지
    { duration: '1m', target: 0 },    // 1분간 0으로 감소
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% 요청이 500ms 이내
    http_req_failed: ['rate<0.01'],    // 실패율 1% 미만
  },
};

export default function () {
  const res = http.get('https://api.example.com/users');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'body has users': (r) => r.json().length > 0,
  });
  sleep(1);
}
```

**시나리오 3 — 마이크로서비스 간 계약 테스트:**
서비스 A가 서비스 B의 API를 호출할 때, B의 응답 구조가 변경되면 A가 깨진다. 계약 테스트는 이 문제를 **배포 전에** 감지한다.

```mermaid
graph LR
    CONS["Consumer 서비스"]
    PROV["Provider 서비스"]
    BROKER["Pact Broker"]
    CONS -->|"계약 생성"| BROKER
    BROKER -->|"계약 검증"| PROV
    PROV -->|"검증 결과"| BROKER
```

Consumer(호출하는 쪽)가 "나는 이런 형태의 응답을 기대한다"를 Pact 파일로 정의하고, Provider(제공하는 쪽)가 자신의 API가 이 기대를 충족하는지 검증한다. 두 팀이 독립적으로 배포하되, 호환성은 자동으로 보장된다.

---

## 인증 처리 — OAuth2, JWT, API Key

API 테스트에서 인증 처리는 가장 자주 마주하는 문제다. 테스트 환경마다 인증 방식이 다르고, 토큰 만료, 리프레시 토큰 갱신 등 복잡한 흐름을 도구에서 자동화해야 한다.

### OAuth2 플로우

OAuth2는 가장 복잡한 인증 방식이다. Client Credentials, Authorization Code, PKCE 등 여러 Grant Type이 있으며, 테스트 환경에서는 주로 Client Credentials를 사용한다.

> **비유:** OAuth2는 호텔 카드키 시스템이다. 프론트 데스크(Authorization Server)에서 신분증(Client Credentials)을 보여주면 카드키(Access Token)를 받는다. 카드키로 객실(API)에 들어간다. 카드키는 만료 시간이 있어서, 시간이 지나면 프론트 데스크에서 다시 발급받아야 한다.

**Postman에서 OAuth2 자동화:**

Postman은 Collection 레벨에서 OAuth2 인증을 설정할 수 있다. Authorization 탭에서 OAuth 2.0을 선택하고, Token URL, Client ID, Client Secret을 입력하면 토큰 발급과 갱신을 자동으로 처리한다.

하지만 CI/CD(Newman)에서는 GUI가 없으므로 Pre-request Script로 처리해야 한다. 위에서 소개한 Pre-request Script 예시가 바로 이 패턴이다.

**curl에서 OAuth2:**

```bash
#!/bin/bash
# oauth2-curl.sh — 토큰 캐싱 + 자동 갱신

TOKEN_FILE="/tmp/api_token.json"

get_token() {
  curl -s -X POST https://auth.example.com/oauth/token \
    -d "grant_type=client_credentials" \
    -d "client_id=$CLIENT_ID" \
    -d "client_secret=$CLIENT_SECRET" \
    -d "scope=read write" > "$TOKEN_FILE"
}

get_access_token() {
  # 토큰 파일이 없거나 만료되었으면 갱신
  if [ ! -f "$TOKEN_FILE" ]; then
    get_token
  fi

  local expires_at=$(jq -r '.expires_at // 0' "$TOKEN_FILE")
  local now=$(date +%s)

  if [ "$now" -ge "$expires_at" ]; then
    get_token
    # 만료 시간 저장 (현재 시간 + expires_in - 5분 버퍼)
    local expires_in=$(jq -r '.expires_in' "$TOKEN_FILE")
    jq --arg ea "$((now + expires_in - 300))" '. + {expires_at: $ea}' \
      "$TOKEN_FILE" > "${TOKEN_FILE}.tmp" && mv "${TOKEN_FILE}.tmp" "$TOKEN_FILE"
  fi

  jq -r '.access_token' "$TOKEN_FILE"
}

# 사용
TOKEN=$(get_access_token)
curl -H "Authorization: Bearer $TOKEN" https://api.example.com/resource
```

### JWT 토큰 디버깅

JWT 토큰 문제를 디버깅할 때는 토큰을 디코딩하여 payload를 확인해야 한다.

```bash
# JWT 토큰 디코딩 (jq 사용)
echo "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.xxx" \
  | cut -d. -f2 \
  | base64 -d 2>/dev/null \
  | jq '.'

# 만료 시간 확인
echo "$TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null \
  | jq '.exp | todate'
```

### API Key 관리 best practice

API Key는 가장 단순한 인증 방식이지만, 관리가 허술하면 보안 사고로 이어진다.

**절대 하면 안 되는 것:**
- API Key를 Postman Collection에 하드코딩하여 Git에 커밋
- curl 명령어의 API Key를 셸 히스토리에 남기기
- 팀 전체가 같은 API Key를 공유

**안전한 관리 방법:**
- Postman: Environment의 Current Value에만 저장 (Initial Value 비움)
- curl: 환경 변수 또는 `.env` 파일에서 읽기
- IntelliJ: `http-client.private.env.json`에 저장 (.gitignore 추가)
- CI/CD: GitHub Secrets, Vault 등 시크릿 관리 도구 사용

```bash
# 환경 변수에서 API Key 읽기 (히스토리에 남지 않음)
export API_KEY=$(cat ~/.secrets/api_key)
curl -H "X-API-Key: $API_KEY" https://api.example.com/data

# .netrc 파일 활용 (Basic Auth)
# ~/.netrc 파일:
# machine api.example.com
# login username
# password secretpassword
curl --netrc https://api.example.com/data
```

---

## 실무 실수 TOP 5

실무에서 API 테스트 도구를 사용하면서 가장 흔히 저지르는 실수 5가지와 해결책을 정리한다.

### 실수 1: 환경 변수 분리 미흡

dev 환경의 baseUrl을 하드코딩해두고, staging 테스트할 때 일일이 URL을 수정하는 패턴이다. 수정을 깜빡하면 dev 서버에 staging 데이터가 들어가거나, prod 서버에 테스트 데이터가 생성된다.

**해결책:** 모든 URL, 인증 정보, 타임아웃 값을 Environment 변수로 추출한다. 하드코딩된 값이 하나도 없어야 한다.

### 실수 2: 테스트 데이터 정리 미흡

POST로 생성한 테스트 데이터를 삭제하지 않아서, 테스트를 반복 실행하면 "이미 존재하는 이메일" 에러가 발생한다.

**해결책:** Collection의 마지막에 Cleanup 폴더를 두고, 생성한 데이터를 모두 삭제하는 요청을 배치한다. 또는 Pre-request Script에서 랜덤 데이터를 생성한다.

{% raw %}
```javascript
// Pre-request Script — 고유 테스트 데이터 생성
const uniqueId = Date.now();
pm.environment.set("testEmail", `test_${uniqueId}@example.com`);
pm.environment.set("testName", `User_${uniqueId}`);
```
{% endraw %}

### 실수 3: 응답 시간 미검증

상태 코드 200만 확인하고 응답 시간을 검증하지 않는다. API가 10초 걸려도 테스트는 통과한다. 프로덕션에서 사용자가 체감하는 느린 응답은 테스트에서 잡지 못한다.

**해결책:** 모든 API 테스트에 응답 시간 임계값(SLA)을 설정한다.

{% raw %}
```javascript
// Postman Test Script
pm.test("Response time within SLA", function () {
    // 일반 API: 500ms, 검색 API: 1000ms, 리포트 API: 3000ms
    const sla = pm.request.url.toString().includes("/search") ? 1000 : 500;
    pm.expect(pm.response.responseTime).to.be.below(sla);
});
```
{% endraw %}

### 실수 4: 에러 케이스 미테스트

정상 케이스(Happy Path)만 테스트하고, 비정상 케이스(에러 응답)를 테스트하지 않는다. 잘못된 입력, 권한 부족, 존재하지 않는 리소스 등에 대한 API 응답이 올바른지 검증해야 한다.

**테스트해야 할 에러 케이스 목록:**
- 400 Bad Request: 필수 필드 누락, 잘못된 형식
- 401 Unauthorized: 인증 토큰 없음, 만료된 토큰
- 403 Forbidden: 권한 부족
- 404 Not Found: 존재하지 않는 리소스
- 409 Conflict: 중복 생성
- 422 Unprocessable Entity: 비즈니스 규칙 위반
- 429 Too Many Requests: Rate Limit 초과
- 500 Internal Server Error: 서버 내부 오류

### 실수 5: 시크릿 유출

Postman Collection을 Git에 커밋할 때 API Key나 토큰이 포함되어 있다. 한 번 Git 히스토리에 들어간 시크릿은 force push로 지워도 이미 clone한 사람의 로컬에 남아있다.

**해결책:**
- `.gitignore`에 `http-client.private.env.json`, `*.postman_environment.json` 추가
- Git pre-commit hook으로 시크릿 패턴 탐지 (gitleaks, trufflehog)
- CI/CD에서는 환경 변수나 Vault에서 시크릿을 주입

---

## 도구 선택 의사결정 트리

어떤 도구를 선택할지 상황별로 정리한다.

```mermaid
graph LR
    Q1["GUI 필요?"]
    Q1 -->|"예"| Q2["팀 규모?"]
    Q1 -->|"아니오"| Q3["자동화 목적?"]
    Q2 -->|"대규모"| PM["Postman"]
    Q2 -->|"소규모"| INS["Insomnia"]
    Q3 -->|"스크립트"| CURL["curl"]
    Q3 -->|"대화형"| HTTP["httpie"]
```

**정리:**
- 혼자 또는 소규모 팀, GUI 선호 -> **Insomnia**
- 대규모 팀, 엔터프라이즈 기능 필요 -> **Postman**
- CI/CD 스크립트, 서버 자동화 -> **curl**
- CLI 선호하지만 가독성 중시 -> **httpie**
- Java/Kotlin 프로젝트, IDE 안에서 테스트 -> **IntelliJ HTTP Client**
- 여러 도구 병행: Postman(탐색) + curl/Newman(자동화) + IntelliJ(개발 중 검증)

---

## 면접 포인트 5개

<details>
<summary><strong>Q1. Postman Collection Runner와 Newman의 차이를 설명하고, CI/CD에서 Newman을 사용하는 이유를 말해주세요.</strong></summary>

Collection Runner는 Postman GUI 안에서 Collection을 순차/반복 실행하는 기능이다. 수동 테스트와 디버깅에 적합하다. Newman은 Postman Collection을 CLI에서 실행하는 Node.js 패키지로, GUI 없이 터미널이나 CI/CD 파이프라인에서 동작한다.

CI/CD에서 Newman을 사용하는 이유는 세 가지다. 첫째, **헤드리스 실행**이 가능하여 서버 환경(GUI 없음)에서 동작한다. 둘째, **종료 코드**를 반환하므로 테스트 실패 시 파이프라인을 중단할 수 있다. 셋째, **리포터 플러그인**(JUnit XML, HTML)으로 CI 도구(Jenkins, GitHub Actions)와 통합할 수 있다.

핵심은 "같은 Collection으로 수동 테스트(GUI)와 자동 테스트(CLI)를 모두 수행할 수 있다"는 점이다.
</details>

<details>
<summary><strong>Q2. curl과 httpie의 근본적인 설계 철학 차이는 무엇인가요?</strong></summary>

curl은 **프로토콜 범용 전송 도구**로 설계되었다. HTTP뿐 아니라 FTP, SMTP, LDAP 등 수십 가지 프로토콜을 지원하며, 모든 옵션을 명시적으로 지정해야 한다. "아무것도 가정하지 않는다"가 원칙이다. 그래서 Content-Type, method, 데이터 형식을 모두 수동으로 지정해야 한다.

httpie는 **HTTP 전용 CLI 클라이언트**로 설계되었다. "사람이 읽기 쉽고, 자주 쓰는 것은 짧게"가 원칙이다. JSON을 기본 Content-Type으로 가정하고, 데이터 타입을 자동 추론하며(`=`은 문자열, `:=`은 숫자/불린), 응답을 컬러 하이라이팅한다.

선택 기준은 용도다. 셸 스크립트 자동화, 서버 환경(httpie 미설치) -> curl. 개발자가 대화형으로 API 탐색 -> httpie.
</details>

<details>
<summary><strong>Q3. 마이크로서비스 아키텍처에서 API 계약 테스트(Contract Test)가 왜 필요한가요?</strong></summary>

마이크로서비스 환경에서 각 서비스는 독립적으로 배포된다. 서비스 B가 API 응답에 필드 하나를 제거하면, 서비스 A가 해당 필드에 의존하고 있을 때 A가 깨진다. 이 문제는 **통합 테스트에서만** 발견되는데, 통합 테스트는 모든 서비스를 동시에 띄워야 하므로 비용이 크고 느리다.

계약 테스트(Contract Test)는 이 문제를 **배포 전에, 각 서비스의 빌드 단계에서** 감지한다. Consumer가 "나는 이 필드를 기대한다"를 Pact 파일로 선언하고, Provider가 자신의 빌드에서 이 기대를 충족하는지 검증한다. 두 서비스가 물리적으로 연결되지 않아도, 계약 호환성은 보장된다.

핵심 가치는 "독립 배포 가능성을 유지하면서 호환성을 자동 검증한다"는 것이다. 서비스 수가 늘어날수록 계약 테스트의 가치는 기하급수적으로 증가한다.
</details>

<details>
<summary><strong>Q4. API 테스트에서 멱등성(Idempotency)을 어떻게 검증하나요?</strong></summary>

멱등성은 "같은 요청을 여러 번 보내도 결과가 동일하다"는 성질이다. GET, PUT, DELETE는 멱등해야 하고, POST는 일반적으로 멱등하지 않다.

검증 방법은 다음과 같다. 첫째, **같은 PUT 요청을 2회 전송**하고, 두 번째 응답이 첫 번째와 동일한지(200 OK, 같은 바디) 확인한다. 데이터베이스에 중복 레코드가 생기지 않았는지도 검증한다.

둘째, **같은 DELETE 요청을 2회 전송**하고, 첫 번째는 200/204, 두 번째는 404가 반환되는지 확인한다. 또는 두 번째도 204를 반환하는 설계라면 그에 맞게 검증한다.

셋째, **Idempotency Key가 있는 POST**의 경우, 같은 Key로 2회 전송하면 두 번째 요청은 첫 번째와 동일한 응답을 반환하고 리소스가 하나만 생성되었는지 확인한다. 결제 API에서 특히 중요하다.

Postman에서는 Collection Runner의 반복 실행(`-n 3`)으로 멱등성을 자동 검증할 수 있다.
</details>

<details>
<summary><strong>Q5. API 부하 테스트에서 Ramp-up, Soak, Spike 테스트의 차이를 설명해주세요.</strong></summary>

세 가지 테스트는 서로 다른 유형의 성능 문제를 발견한다.

**Ramp-up (점진 증가) 테스트:** 동시 사용자를 0에서 목표치까지 서서히 증가시킨다. 시스템이 감당할 수 있는 최대 동시 사용자 수(breaking point)를 찾는다. "우리 시스템은 동시 500명까지 p95 < 500ms를 유지한다"를 확인한다.

**Soak (장시간 지속) 테스트:** 일정한 부하를 4~24시간 동안 유지한다. 메모리 누수, 커넥션 풀 고갈, 로그 파일 디스크 가득 참 등 **시간이 지나야 드러나는 문제**를 발견한다. 1시간 테스트에서는 괜찮지만 8시간 후 OOM이 터지는 케이스를 잡는다.

**Spike (급증) 테스트:** 정상 부하에서 갑자기 10배로 급증시킨 뒤 정상으로 복귀한다. 타임세일, 이벤트 오픈 등 **급격한 트래픽 변동**에 시스템이 어떻게 반응하는지 확인한다. 오토스케일링이 제때 작동하는지, 급증 후 정상 상태로 복귀하는지가 핵심이다.

k6 기준으로 세 가지를 stages 옵션으로 구분한다. Ramp-up은 `target`을 점진 증가, Soak은 동일 `target`을 긴 `duration`으로 유지, Spike는 짧은 시간에 높은 `target`으로 급증시킨다.
</details>

---

## 정리

| 상황 | 추천 도구 | 이유 |
|------|-----------|------|
| 처음 API 탐색 | Postman | GUI로 직관적, 학습 곡선 낮음 |
| 팀 공유 + 자동화 | Postman + Newman | Collection 공유 + CI/CD 연동 |
| 경량 + Git 중심 | Insomnia | 오픈소스, Git Sync 기본 |
| 셸 스크립트 | curl | 어디든 설치됨, 범용 |
| 대화형 CLI | httpie | 가독성, JSON 기본 지원 |
| IDE 내 테스트 | IntelliJ HTTP Client | 코드 옆에서 바로 검증, Git 공유 |
| 부하 테스트 | k6 + curl 시나리오 | 기능 테스트 재사용 |
| 계약 테스트 | Pact + CI/CD | 마이크로서비스 호환성 보장 |

API 테스트 도구는 하나만 쓰는 것이 아니라, 목적에 따라 조합하여 사용한다. Postman으로 탐색하고, .http 파일로 팀과 공유하며, Newman/curl로 CI/CD에서 자동화하고, k6로 성능을 검증하는 것이 현실적인 조합이다. 도구보다 중요한 것은 **테스트를 자동화하고, 배포 파이프라인에 통합하여, 수동 확인 없이도 API 품질을 보장하는 체계**를 구축하는 것이다.
