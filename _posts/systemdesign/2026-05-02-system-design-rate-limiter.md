---
title: "Rate Limiter 설계 — 초당 10만 요청 봇에서 서버를 지키는 법"
categories:
- SYSTEMDESIGN
toc: true
toc_sticky: true
toc_label: 목차
---

2023년, 한 스타트업의 API가 새벽 3시에 다운됐다. 원인은 경쟁사 봇이 초당 5만 건의 요청을 보낸 것이었다. DB 커넥션 풀이 고갈되고 서비스 전체가 멈췄다. Rate Limiter가 있었다면? IP당 초당 100건 제한으로 이 봇의 요청 99.998%가 차단됐을 것이다. **Rate Limiter는 "공정성"의 문제이기 전에 "생존"의 문제다.**

## 왜 Rate Limiter가 필요한가

> **비유**: 놀이공원 인기 어트랙션 앞의 "1회 탑승 후 재줄 서기" 규칙과 같다. 한 사람이 무한 반복 탑승하는 것을 막아 모든 사람이 공정하게 이용한다. 줄을 서지 않고 뒷문으로 수백 번 들어오려는 사람(봇)을 아예 입장 거부시킨다.

Rate Limiter 없으면 어떤 일이 생기는가:

| 상황 | 결과 |
|------|------|
| 악의적 봇: 초당 10만 요청 | 서버 다운 |
| 클라이언트 버그: 무한 루프 API 호출 | DB 커넥션 고갈 |
| 마케팅 이벤트: 트래픽 폭발 | 서비스 전체 느려짐 |
| 스크래퍼: 데이터 무단 수집 | 비용 폭발, 데이터 유출 |

---

## 설계 의사결정 로드맵

### 결정 1: 알고리즘 — 어떤 알고리즘으로 제한할 것인가

**문제**: 잘못 고르면 버스트 트래픽을 막거나, 경계 구간에서 한도의 2배가 통과하거나, 메모리가 폭발한다.

| 후보 | 장점 | 단점 | 선택 이유 |
|------|------|------|-----------|
| Token Bucket | 버스트 허용, 메모리 효율 | 경계 구간 허용량 약간 초과 | API 서버 기본 — 정상 버스트 허용 |
| Sliding Window Log | 가장 정확 | 요청마다 타임스탬프 저장, 메모리 폭발 | 고정밀 금융 규정 준수 한정 |
| Sliding Window Counter | 정확도 + 메모리 균형 | 이전 윈도우 가중 근사치 | **일반 API 기본 선택** |
| Fixed Window Counter | 구현 최단 | 경계에서 2배 허용 버그 | 내부 관리 API 한정 |
| Leaky Bucket | 균일 처리 보장 | 정상 버스트도 차단 | 결제 등 고정 처리율 시스템 |

**우리의 선택: Sliding Window Counter** — 이유: 메모리 O(1), 경계 문제 없음, Redis 2개 키로 구현 가능.

---

### 결정 2: 저장소 — 로컬 메모리 vs Redis

**문제**: 로컬 메모리를 쓰면 서버 3대가 각자 한도를 유지해 실제 허용량이 서버 수만큼 늘어난다.

| 후보 | 장점 | 단점 | 선택 이유 |
|------|------|------|-----------|
| 서버 로컬 메모리 | 지연 0ms, 구현 가장 단순 | 서버 수 × 한도가 실제 한도 | Redis 장애 폴백 용도로만 |
| MySQL/PostgreSQL | 데이터 영속성 | 락 경합으로 수십 ms, 자체가 병목 | Rate Limiter에 부적합 |
| Redis (단일) | 원자적 INCR, 1ms 미만 | 단일 장애점 | 소규모 서비스 |
| **Redis Cluster** | 수평 확장, 고가용성 | 클러스터 관리 복잡도 | **프로덕션 표준** |

**우리의 선택: Redis Cluster** — 이유: INCR 명령 원자성, 초당 100만 ops, TTL 기반 자동 키 만료.

---

### 결정 3: 적용 위치 — API Gateway vs 애플리케이션

**문제**: 위치가 잘못되면 내부 서비스 호출까지 제한하거나, 인프라 전체를 바꿔야 한다.

| 후보 | 장점 | 단점 | 선택 이유 |
|------|------|------|-----------|
| CDN/에지 (Cloudflare) | 서버 도달 전 차단 | 정밀한 사용자별 제한 어려움 | DDoS 1차 방어 |
| API Gateway (Kong/Nginx) | 중앙 집중 관리, 앱 코드 불변 | 게이트웨이 장애가 전체 장애 | **일반 API 표준** |
| 애플리케이션 미들웨어 | 비즈니스 로직 접근 가능 | 서비스마다 별도 구현 | 엔드포인트별 세밀 제어 필요 시 |
| 네트워크 계층 (iptables) | 성능 최고 | IP 기반만 가능, 관리 난이도 높음 | DDoS 필터링 보조 |

**우리의 선택: API Gateway + 애플리케이션 계층 병용** — 이유: Gateway에서 IP 레벨, 앱에서 사용자/엔드포인트 레벨 이중 적용.

### 꼭 API 서버에서 만들어야 하는가? — 계층별 방어 전략

Rate Limiter를 API 코드로 직접 구현하는 것은 **마지막 방어선**이다. 앞단에서 이미 대부분의 악성 트래픽을 걸러낼 수 있고, 그래야 한다. 각 계층이 담당하는 역할이 다르다.

| 계층 | 도구 | 막을 수 있는 것 | 못 막는 것 | 비용 |
|------|------|---------------|-----------|------|
| **1. CDN/DNS** | Cloudflare, AWS Shield | DDoS (L3/L4), 국가 차단, 봇 스코어링 | 로그인한 사용자 구분 불가 | $20~200/월 |
| **2. WAF** | AWS WAF, Cloudflare WAF | SQL Injection, XSS, IP 블랙리스트, 요청 패턴 | 비즈니스 로직 기반 제한 불가 | $5~100/월 |
| **3. API Gateway** | Kong, Nginx, AWS API GW | IP당/API키당 rate limit, 인증 전 차단 | 사용자별 세분화 제한 어려움 | 인프라 포함 |
| **4. 앱 서버** | Redis + Lua, 자체 구현 | 사용자별/엔드포인트별/티어별 세밀한 제한 | 이미 앱까지 도달한 트래픽만 | 개발 비용 |
| **5. DB** | Connection Pool, 쿼리 타임아웃 | slow query 폭주, 커넥션 고갈 | 앞단 트래픽 제어 불가 | 설정만 |

**핵심**: 트래픽이 뒤로 갈수록 처리 비용이 비싸다. CDN에서 1건 차단하는 비용은 거의 0이지만, DB까지 도달한 요청을 차단하면 이미 CPU/메모리/커넥션을 소모한 뒤다.

**실무 추천 조합**:

```
Phase 1 (MAU 1만): Nginx limit_req만으로 충분
Phase 2 (MAU 100만): Cloudflare 무료 + API Gateway rate limit
Phase 3 (MAU 1000만): Cloudflare Pro + AWS WAF + Redis Lua (앱 레벨)
Phase 4 (MAU 1억): Cloudflare Enterprise + 다층 WAF + ML 이상탐지
```

> **면접 포인트**: "Rate Limiter를 어디에 배치하겠습니까?"라는 질문에 "API 서버에서 Redis로"만 답하면 미드 레벨이다. "CDN→WAF→Gateway→App 다층 방어를 구성하고, 각 계층이 담당하는 트래픽 유형이 다르다"고 답해야 시니어다. 앞단에서 90%를 걸러야 뒷단이 살아남는다.

### 차단 기준 설계 + 봇 방어 — 뭘 기준으로, 누구를 막을 것인가

알고리즘보다 **"무엇을 키로 카운팅하고, 누구를 막을 것인가"**가 실무에서 더 중요한 결정이다.

**Rate Limit 키 설계** — 기준을 잘못 잡으면 정상 사용자가 차단되거나 공격자가 우회한다:

| 차단 기준 | 장점 | 단점 | 적합한 상황 |
|-----------|------|------|-----------|
| IP 주소 | 구현 단순, 인증 불필요 | NAT 연좌제, VPN 우회 | DDoS 1차 방어 |
| API 키 | 서비스 단위 제한 | 키 탈취 시 무방비 | B2B API |
| 사용자 ID | 가장 정확 | 비로그인 제한 불가 | 결제, 게시글 작성 |
| 엔드포인트별 | 민감 API만 강하게 | 정책 관리 복잡 | /payment: 5건, /search: 200건 |

실무에서는 **IP → 사용자 → 엔드포인트 → 티어** 복합 키로 계층화한다. IP만 쓰면 회사 전체가 차단되고, 사용자만 쓰면 비로그인 봇이 무방비다.

**봇/스크래퍼 방어** — Rate Limiter의 가장 현실적인 유즈케이스는 경쟁사 봇이 우리 데이터를 긁어가는 것을 막는 것이다. 단순 QPS 제한으로는 해결 안 된다 — 봇은 일반 사용자처럼 행동하기 때문이다.

**봇과 정상 사용자의 차이**:

| 신호 | 정상 사용자 | 초보 봇 | 고급 봇 (Headless Chrome) |
|------|-----------|---------|------------------------|
| 요청 간격 | 불규칙 (3~30초) | 정확히 일정 (1초 간격) | 랜덤 딜레이 삽입 (사람 흉내) |
| User-Agent | Chrome/Safari 정품 | python-requests, curl | 실제 Chrome UA 완벽 복제 |
| 쿠키/JS | 정상 저장, JS 실행 | 쿠키 무시, JS 미실행 | 쿠키 저장, JS 실행 가능 |
| 페이지 패턴 | 홈→목록→상세 자연 흐름 | 상세 페이지만 순차 접근 | 목록→상세 흉내 (패턴 학습) |
| 세션 길이 | 5~30분 | 수시간 연속 무중단 | 세션 분할로 짧게 위장 |
| 마우스/스크롤 | 자연스러운 이동 | 없음 | Puppeteer로 가짜 이벤트 생성 |
| TLS 핑거프린트 | 브라우저 고유 JA3 | 라이브러리 기본 JA3 | 브라우저 JA3 복제 가능 |
| Referer 체인 | 검색→목록→상세 | 없음 (직접 접근) | 가짜 Referer 설정 |

> **현실**: 2024년 이후 봇의 80%는 Headless Chrome + Puppeteer/Playwright 기반이다. 단순 UA 차단이나 간격 분석만으로는 잡을 수 없다. **TLS 핑거프린팅 + 행동 분석 ML의 조합**이 필수다.

**방어 전략 (쉬운 것 → 어려운 것 순서)**:

```
1단계: robots.txt + UA 차단 (구현 5분)
   - robots.txt에 Crawl-delay 설정 (선의의 봇만 준수)
   - 알려진 봇 UA 차단 (python-requests, curl, scrapy)
   - 효과: 가장 쉬움, 초보 봇 즉시 차단

2단계: 허니팟 트랩 (구현 30분, 오탐 0%)
   - CSS display:none 링크를 페이지에 숨김 (사용자 눈에 안 보임)
   - 숨긴 링크를 요청한 IP = 100% 봇 → 즉시 블랙리스트
   - robots.txt Disallow 경로 방문 IP도 봇 확정
   - 효과: 가장 확실, 오탐이 원천적으로 불가능

3단계: 쿠키 기반 검증 (구현 1시간)
   - 첫 요청 시 Set-Cookie로 HMAC 서명된 토큰 발급
   - 이후 요청에 쿠키가 없으면 봇으로 판정
   - 효과: requests/curl 등 쿠키 미지원 봇 차단

4단계: IP Rate Limit + 패턴 분석 (구현 반나절)
   - 동일 IP에서 분당 100+ 상세 페이지 접근 시 차단
   - 상세 페이지 비율 90% 이상이면 봇 의심
   - 효과: IP 로테이션 안 하는 봇 차단

5단계: JS Challenge (Cloudflare 설정)
   - 첫 요청 시 JS 챌린지 페이지 반환
   - 브라우저가 아니면 JS 실행 불가 → 차단
   - Canvas/WebGL 핑거프린트로 디바이스 식별
   - 효과: Headless Chrome 아닌 봇 대부분 차단

6단계: TLS 핑거프린팅 — JA3/JA4 (구현 어려움)
   - TLS 핸드셰이크의 cipher suite 순서가 브라우저마다 고유
   - python-requests, Go http.Client는 브라우저와 JA3 해시가 다름
   - 효과: UA를 위조해도 TLS 레벨에서 탐지

7단계: 행동 분석 — ML 기반 (구현 매우 어려움)
   - 요청 간격 표준편차 (봇은 σ ≈ 0, 사람은 불규칙)
   - Referer 체인 (봇: 상세 직접 접근, 사람: 검색→목록→상세)
   - 마우스/스크롤 이벤트 수집 (프론트에서)
   - 효과: Headless Chrome 봇까지 탐지

8단계: 응답 변조 — Tar Pit (최후의 수단)
   - 봇 판정된 요청에 가짜 데이터 반환 (가격 ±20% 변조)
   - 응답 지연을 점진적으로 늘려 봇 자원 소모
   - 효과: 봇이 차단당한 줄 모르고 오염된 데이터 수집
```

**각 단계 구체적 구현 사례**:

**1단계 — Nginx UA 차단 (nginx.conf)**:
```nginx
# 알려진 봇 UA 차단
if ($http_user_agent ~* "(python-requests|curl|scrapy|wget|Go-http-client)") {
    return 403;
}
```

**2단계 — 허니팟 트랩 (HTML + Spring Boot)**:
```html
<!-- 사용자는 안 보이지만 봇은 크롤링하는 숨겨진 링크 -->
<a href="/trap/hidden-page" style="display:none" aria-hidden="true">secret</a>
```
```java
@RestController
public class HoneypotController {
    private final Set<String> blacklist = ConcurrentHashMap.newKeySet();

    @GetMapping("/trap/**")
    public ResponseEntity<Void> trap(HttpServletRequest req) {
        String ip = req.getRemoteAddr();
        blacklist.add(ip); // 이 링크에 접근한 IP = 100% 봇
        log.warn("BOT DETECTED via honeypot: {}", ip);
        return ResponseEntity.status(403).build();
    }
}
```

**3단계 — 쿠키 기반 검증 (Spring Filter)**:
```java
@Component
public class BotCookieFilter extends OncePerRequestFilter {
    private static final String COOKIE_NAME = "_bv";
    private static final String SECRET = "bot-verify-secret-key";

    @Override
    protected void doFilterInternal(HttpServletRequest req,
            HttpServletResponse res, FilterChain chain) throws Exception {
        Cookie[] cookies = req.getCookies();
        boolean hasValidCookie = false;

        if (cookies != null) {
            for (Cookie c : cookies) {
                if (COOKIE_NAME.equals(c.getName()) && verify(c.getValue())) {
                    hasValidCookie = true;
                    break;
                }
            }
        }

        if (!hasValidCookie) {
            // 첫 방문: HMAC 서명된 쿠키 발급 후 리다이렉트
            String token = System.currentTimeMillis() + ":" +
                hmacSha256(String.valueOf(System.currentTimeMillis()), SECRET);
            res.addCookie(new Cookie(COOKIE_NAME, token));
            res.setStatus(302);
            res.setHeader("Location", req.getRequestURI());
            return; // 쿠키 못 저장하는 봇은 무한 302 루프
        }
        chain.doFilter(req, res);
    }
}
```

**4단계 — IP Rate Limit + 패턴 분석 (Redis)**:
```java
public boolean isPagePatternSuspicious(String sessionId) {
    String key = "page_pattern:" + sessionId;
    Long total = redis.opsForHash().size(key);
    Long detailCount = redis.opsForHash().get(key, "detail");
    if (total > 50 && detailCount / total > 0.9) {
        return true; // 상세 페이지만 90% 이상 접근 = 봇
    }
    return false;
}
```

**5단계 — 허니팟 + JS Challenge 조합 (프론트)**:
```javascript
// 정상 브라우저만 실행하는 검증 스크립트
(function() {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl');
    const fingerprint = gl ? gl.getParameter(gl.RENDERER) : 'none';
    fetch('/api/verify-browser', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            fp: fingerprint,
            screen: window.screen.width + 'x' + window.screen.height,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
        })
    });
})();
// Headless Chrome은 WebGL 렌더러가 "SwiftShader"로 나옴 → 봇 탐지
```

**봇 방어 기법 전체 정리**:

| 기법 | 구현 난이도 | 효과 | 우회 가능성 | 정상 사용자 영향 |
|------|-----------|------|-----------|----------------|
| robots.txt | 매우 쉬움 | 낮음 | 무시하면 끝 | 없음 |
| 쿠키 검증 | 쉬움 | 중간 | 쿠키 저장하면 우회 | 없음 |
| User-Agent 차단 | 쉬움 | 낮음 | UA 위조 가능 | 없음 |
| IP Rate Limit | 쉬움 | 중간 | IP 로테이션 우회 | NAT 연좌제 위험 |
| JS Challenge | 중간 | 높음 | Headless Chrome | CAPTCHA UX 저하 |
| 허니팟 트랩 | 쉬움 | 높음 | CSS 파싱하면 우회 | 없음 (오탐 0%) |
| TLS 핑거프린팅 | 어려움 | 매우 높음 | TLS 라이브러리 교체 | 없음 |
| 행동 분석 (ML) | 매우 어려움 | 매우 높음 | 인간 흉내 봇 | 오탐 가능 |
| 응답 변조 | 중간 | 높음 | 교차 검증 시 발각 | 없음 |

> **실무 추천**: 1~4단계(robots.txt + 쿠키 + UA + IP)만으로 봇의 90%를 막을 수 있다. 5~6단계(허니팟 + TLS)를 추가하면 99%. 7~8단계(ML + 응답 변조)는 가격 비교 사이트, 항공권/호텔 등 스크래핑이 비즈니스 위협인 서비스에서만 필요하다.

**실무 코드 예시 — 행동 기반 봇 탐지**:

```python
def is_suspicious_bot(user_session):
    # 1. 요청 간격이 너무 균일한가 (봇은 정확한 간격)
    intervals = user_session.request_intervals
    if len(intervals) > 10:
        std_dev = statistics.stdev(intervals)
        if std_dev < 0.1:  # 표준편차 100ms 미만 = 기계적
            return True, "uniform_interval"

    # 2. 상세 페이지만 접근하는가 (목록 안 거치고 직접 접근)
    detail_ratio = user_session.detail_page_count / user_session.total_count
    if detail_ratio > 0.9 and user_session.total_count > 50:
        return True, "detail_only_pattern"

    # 3. 세션이 비정상적으로 긴가
    if user_session.duration_minutes > 120 and user_session.total_count > 500:
        return True, "marathon_session"

    return False, None
```

**봇으로 판정된 경우 대응**:

| 대응 | 장점 | 단점 |
|------|------|------|
| 즉시 차단 (403) | 확실한 방어 | 오탐 시 정상 사용자 이탈 |
| 속도 제한 (Throttle) | 부분 허용, 오탐 피해 적음 | 봇이 느려도 계속 긁어감 |
| **허니팟 데이터 반환** | 봇이 가짜 데이터 수집 | 구현 복잡 |
| CAPTCHA 챌린지 | 정상 사용자 통과 가능 | UX 저하, 봇도 CAPTCHA 풀기 서비스 이용 |
| **점진적 지연 (Tar Pit)** | 봇의 자원을 소모시킴 | 우리 서버 커넥션도 점유 |

> **핵심**: 단순 QPS 제한은 봇 방어의 10%밖에 안 된다. 봇은 속도를 낮춰서 제한을 우회하기 때문이다. **행동 패턴 분석**이 핵심이며, "요청 간격의 균일성 + 페이지 접근 패턴 + JS 실행 여부"를 조합해야 정상 사용자를 해치지 않으면서 봇을 막을 수 있다.

---

### 결정 4: 초과 응답 — 429 즉시 거부 vs 큐잉

**문제**: 즉시 거부하면 클라이언트가 재시도 폭풍을 일으키고, 무조건 큐잉하면 메모리가 무한 증가한다.

| 후보 | 장점 | 단점 | 선택 이유 |
|------|------|------|-----------|
| 429 즉시 거부 | 서버 자원 보호, 클라이언트 즉시 인지 | 재시도 폭풍 유발 가능 | **표준 — Retry-After 헤더 필수 병행** |
| 큐잉 (지연 처리) | 요청 손실 없음 | 큐 메모리 폭발, 지연 예측 불가 | 비동기 처리 가능한 배치 API 한정 |
| 점진적 스로틀링 | 부드러운 UX | 구현 복잡, 경계 계산 어려움 | 스트리밍 API 특수 상황 |

**우리의 선택: 429 즉시 거부 + Retry-After 헤더** — 이유: 표준 HTTP 스펙, 클라이언트가 올바른 재시도 타이밍을 알 수 있어 재시도 폭풍 방지.

---

## 왜 Token Bucket인가? — 알고리즘 선택의 트레이드오프

Rate Limiter 알고리즘은 5가지가 있다. 어떤 것을 선택하느냐는 "버스트 트래픽을 허용할 것인가"와 "메모리를 얼마나 쓸 것인가"의 트레이드오프다.

API 서비스의 현실적인 사용 패턴을 보면, 사용자는 대부분 평소에는 조용하다가 특정 순간에 몰아서 요청한다. 예를 들어 모바일 앱이 켜지는 순간 10개의 API를 동시에 호출한다. 이 "정상적 버스트"를 막으면 UX가 나빠진다. 반대로 초당 1만 건을 꾸준히 보내는 봇은 막아야 한다.

- **토큰 버킷**: 정상적 버스트 허용, 꾸준한 과부하 차단 → **대부분의 API에 적합**
- **누출 버킷**: 버스트도 차단, 균일한 처리율 보장 → 결제처럼 처리 속도가 고정된 시스템
- **슬라이딩 윈도우**: 경계 문제 없는 정확한 제한 → 금융 규정 준수처럼 정확도가 최우선

> 핵심: 실무에서는 토큰 버킷(또는 슬라이딩 윈도우 카운터)을 기본으로 선택한다. 누출 버킷은 버스트를 원천 차단해야 하는 특수한 상황에만 쓴다.

---

## Rate Limiting 알고리즘 5가지

### 알고리즘 1: 토큰 버킷 (Token Bucket)

> **비유**: 물통에 일정 속도로 토큰(동전)이 채워진다. 요청마다 토큰 1개를 꺼낸다. 토큰이 없으면 요청 거부. 오래 기다리면 토큰이 쌓여 순간 폭발적 요청도 처리할 수 있다.

```mermaid
graph LR
    Refill["매초 2개 토큰 보충"] --> Bucket["버킷"]
    Request["요청 도착"] --> Check{"토큰 있나?"}
    Check -->|"Yes: 1개 소비"| Allow["허용"]
    Check -->|"No: 0개"| Deny["429 Too Many Reque"]
    Bucket --> Check
```

```python
class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity      # 최대 토큰 수
        self.refill_rate = refill_rate  # 초당 보충 토큰 수
        self.tokens = capacity
        self.last_refill = time.time()

    def allow_request(self) -> bool:
        self._refill()
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

    def _refill(self):
        elapsed = time.time() - self.last_refill
        # 경과 시간에 비례해 토큰 보충 (최대 용량 초과 불가)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = time.time()
```

**특징**: 순간 버스트(burst) 허용 — 버킷이 꽉 찬 상태면 한 번에 많은 요청 처리 가능. 메모리 효율적.

### 알고리즘 2: 누출 버킷 (Leaky Bucket)

> **비유**: 밑에 구멍 뚫린 양동이. 물을 아무리 빨리 부어도 일정 속도로만 흘러나온다. 균일한 처리 속도가 보장된다.

요청이 큐에 들어가고, 일정 속도로 꺼내 처리한다. 큐가 가득 차면 새 요청을 버린다. 서버에 균일한 부하를 보장할 때 유용하다.

### 알고리즘 3: 고정 윈도우 카운터 (Fixed Window Counter)

1분 단위로 카운터를 초기화하고, 그 안에서 N회 제한한다. 구현이 가장 단순하지만 **경계 문제**가 있다:

```
00:59 → 100건 (허용, 새 윈도우 직전)
01:00 → 100건 (허용, 새 윈도우 시작)
→ 2초 사이에 200건이 처리됨!
```

### 알고리즘 4: 슬라이딩 윈도우 로그 (Sliding Window Log)

각 요청의 타임스탬프를 저장해두고, 현재 시각 기준 "최근 1분" 윈도우를 정확하게 계산한다. 경계 문제 없지만 요청마다 타임스탬프를 저장하므로 **메모리 사용량이 요청 수에 비례**한다.

### 알고리즘 5: 슬라이딩 윈도우 카운터 (Sliding Window Counter) — 추천

고정 윈도우 카운터의 경계 문제를 해결하면서 메모리도 효율적이다. **실무에서 가장 널리 쓰이는 방식.**

```mermaid
sequenceDiagram
    participant C as 현재 시각 01:15
    participant P as 이전 윈도우 (00:00~01:00)
    participant N as 현재 윈도우 (01:00~02:00)
    Note over C,N: 현재 시각이 현재 윈도우의 25% 경과
    Note over P: 이전 윈도우: 50건
    Note over N: 현재 윈도우: 30건
    Note over C: 추정치 = 50 × (1-0.25) + 30 = 67.5건
    Note over C: 한도 100건이면 → 허용
```

```python
class SlidingWindowCounter:
    def allow_request(self, user_id: str, redis) -> bool:
        now = time.time()
        current_window = int(now / self.window) * self.window
        prev_window = current_window - self.window
        # 현재 윈도우에서 경과한 비율 (0.0 ~ 1.0)
        elapsed_ratio = (now - current_window) / self.window

        prev_count = int(redis.get(f"counter:{user_id}:{prev_window}") or 0)
        curr_count = int(redis.get(f"counter:{user_id}:{current_window}") or 0)

        # 이전 윈도우의 "남은 비율"만큼 가중치 적용
        estimated = prev_count * (1 - elapsed_ratio) + curr_count

        if estimated >= self.limit:
            return False

        redis.incr(f"counter:{user_id}:{current_window}")
        return True
```

---

## 알고리즘 비교

| 알고리즘 | 메모리 | 정확도 | 버스트 허용 | 복잡도 |
|---------|--------|--------|------------|--------|
| 토큰 버킷 | 낮음 | 중간 | O | 낮음 |
| 누출 버킷 | 낮음 | 높음 | X | 낮음 |
| 고정 윈도우 | 낮음 | **낮음** (경계 문제) | X | 매우 낮음 |
| 슬라이딩 로그 | **높음** | 높음 | X | 중간 |
| **슬라이딩 카운터** | **낮음** | **높음** | X | 중간 |

---

## 왜 Redis인가? — 로컬 카운터로는 안 되는 이유

가장 단순한 구현은 각 서버가 메모리에 카운터를 유지하는 것이다. 왜 이게 안 되는가?

| 방식 | 구현 난이도 | 정확도 | 서버 장애 시 | 서버 증설 시 |
|------|-----------|--------|------------|------------|
| 서버 로컬 메모리 | 매우 쉬움 | **낮음** (서버마다 별개) | 카운터 초기화 | 한도가 서버 수에 비례해 늘어남 |
| MySQL/PostgreSQL | 중간 | 높음 | 데이터 유지 | **병목** (락 경합, 수십ms) |
| **Redis** | 중간 | **높음** | TTL로 자동 복구 | 클러스터로 수평 확장 |

로컬 메모리의 핵심 문제: 서버 3대가 각자 "분당 100건" 한도를 유지하면 실제 한도는 300건이 된다. 로드밸런서가 요청을 고르게 분산한다는 보장도 없으므로 실제 허용량은 100~300건 사이 어딘가가 된다.

MySQL을 카운터 저장소로 쓰면 안 되는 이유: Rate Limiter는 **모든 API 요청마다** 카운터를 읽고 증가시킨다. QPS 10,000이면 MySQL에 초당 20,000 쿼리(읽기 + 쓰기)가 발생한다. 카운터 행에 락 경합이 발생해 Rate Limiter 자체가 병목이 된다. Redis는 단일 스레드 이벤트 루프로 락 없이 초당 100만 ops를 처리한다.

> 핵심: Redis는 "빠른 원자적 카운터"가 필요한 정확히 이 상황을 위해 설계됐다. INCR 명령 하나가 읽기+증가를 원자적으로 처리한다.

---

## 분산 환경에서의 문제 — 서버가 여러 대면 카운터가 분산된다

서버가 3대이고 각 서버가 독립적으로 카운터를 유지하면?

서버 1에 60건, 서버 2에 60건이 가면 각각은 한도(100건) 이하라 통과시키지만 실제로는 120건이다. **해결: 중앙화된 Redis**로 카운터를 공유한다.

```mermaid
graph LR
    S1["서버 1~N"] --> R["Redis"] --> C["통합 카운터"]
```

**Lua 스크립트로 원자적 처리** (GET → 비교 → INCR 사이에 끼어들기 없음):

```lua
local key   = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local current = redis.call('GET', key)
if current and tonumber(current) >= limit then
    return 0  -- 거부
end

local count = redis.call('INCR', key)
if count == 1 then
    redis.call('EXPIRE', key, window)
end
return 1  -- 허용
```

만약 Lua 없이 GET → 비교 → INCR을 따로 하면? 두 서버가 동시에 GET → 둘 다 99건 → 둘 다 INCR → 실제 101건인데 모두 허용된다.

---

## Rate Limiter 아키텍처 — 미들웨어로 구현

```mermaid
graph LR
    Client["클라이언트"] --> MW["Rate Limiter 미들웨어"]
    MW --> Redis["Redis 클러스터"]
    MW -->|"허용"| API["API 서버"]
    MW -->|"거부"| Resp["429 Too Many Reque"]
```

429 응답 헤더에 제한 정보를 담아야 클라이언트가 올바르게 재시도할 수 있다:

```
X-RateLimit-Limit: 100       → 한도
X-RateLimit-Remaining: 45    → 남은 횟수
X-RateLimit-Reset: 1704067260 → 윈도우 리셋 시각
Retry-After: 60              → 재시도 가능까지 대기 초
```

이 헤더가 없으면? 클라이언트가 즉시 재시도를 반복해서 오히려 더 많은 429를 만든다.

---

## 계층별 Rate Limiting

단일 계층만으로는 모든 상황을 막을 수 없다:

```mermaid
graph LR
    Req["요청"] --> L1["L1: IP 레벨"]
    L1 --> L2["L2: API 키 레벨"]
    L2 --> L3["L3: 엔드포인트별"]
    L3 --> L4["L4: 사용자 티어"]
    L4 --> API["API 서버"]
```

```python
RATE_LIMIT_TIERS = {
    'free':       {'per_day': 1_000,    'per_minute': 20,     'burst': 50},
    'pro':        {'per_day': 100_000,  'per_minute': 500,    'burst': 1_000},
    'enterprise': {'per_day': 10_000_000, 'per_minute': 10_000, 'burst': 50_000},
}

# 엔드포인트별 추가 제한 (티어 제한과 AND 조건)
ENDPOINT_LIMITS = {
    '/api/auth/login':    (5, 60),     # 분당 5번 — 브루트포스 방지
    '/api/auth/register': (3, 3600),   # 시간당 3번
    '/api/send-sms':      (10, 3600),  # SMS는 비싸므로 엄격하게
}
```

---


## 극한 시나리오

### 시나리오 1: 봇넷 DDoS — 초당 10만 요청이 몰리면

단일 IP Rate Limiter만 있는 상태에서 1만 개 IP 봇넷이 각각 초당 10건씩 공격한다. 총 초당 10만 QPS. IP당 제한은 통과한다.

```
무너지는 순서:
T+0초:   10만 QPS 유입. API 서버 CPU 급등.
T+3초:   DB 커넥션 풀 고갈. 응답 지연 시작.
T+8초:   메모리 부족으로 GC 폭발. P99 응답 10초+
T+15초:  Health check 실패 → 로드밸런서가 서버 제외
T+20초:  남은 서버에 부하 집중 → 연쇄 다운

다층 방어로 막는 방법:
1. CDN(Cloudflare): IP 평판 기반으로 알려진 봇 IP 차단 (도달 전에 차단)
2. ASN 레벨 제한: 동일 클라우드(AWS AS16509) 대역에서 비정상 패턴 감지 시 해당 대역 스로틀
3. 행동 분석: 요청 간격이 정확히 100ms로 일정 → 봇 판별 → CAPTCHA 요구
4. API 게이트웨이: 초당 5만 QPS 이상은 물리적으로 드롭
```

### 시나리오 2: Redis 클러스터 장애 — Rate Limiter 저장소가 죽으면

초당 5만 QPS 서비스에서 Redis 클러스터 장애. Rate Limiter가 카운터를 읽을 수 없다.

```
선택지 3가지와 트레이드오프:

옵션 A: 전부 허용 (Fail Open)
  - 서비스는 살아있음
  - 봇 공격 무방비 상태. 5만 QPS가 전부 DB로 직행
  - DB 커넥션 고갈 → 서비스 다운. Rate Limiter 장애가 전체 장애로 전파

옵션 B: 전부 거부 (Fail Closed)
  - 봇 차단 유지
  - 정상 사용자도 전부 429 오류. 서비스 중단과 동일
  - 금융·보안 API에만 적합

옵션 C: 로컬 카운터 폴백 (권장)
  - 각 서버가 독립적으로 로컬 카운터 유지
  - 정확도 감소 (서버 10대면 실제 한도가 10배)를 일시적으로 수용
  - Redis 복구 후 즉시 중앙 카운터로 복귀
  - 대부분의 일반 API에 적합

구현: Redis 연결 실패 시 자동으로 로컬 카운터 클래스로 전환하는 Circuit Breaker 패턴
```

### 시나리오 3 (기존): 봇넷 다층 방어

```mermaid
graph LR
    DDoS["봇넷"] --> CF["Cloudflare"]
    CF --> WAF["AWS WAF"]
    WAF --> LB["로드밸런서"]
    LB --> AppRL["애플리케이션"]
    AppRL --> API["API 서버"]
```

**자동 IP 차단:**

```python
class AdaptiveRateLimiter:
    def check(self, ip: str) -> str:
        if self.redis.sismember("banned_ips", ip):
            return "BANNED"  # 영구 차단 목록

        minute_count = self._get_count(ip, 60)

        if minute_count > 500:   # 분당 500건 초과
            self.redis.setex(f"temp_ban:{ip}", 3600, 1)  # 1시간 임시 차단
            self._alert_security_team(ip)
            return "BLOCKED"

        if minute_count > 100:   # 분당 100건 초과
            return "CHALLENGE"   # CAPTCHA 요구

        return "ALLOW"
```

---

## 극악의 봇 시나리오 — 현실에서 실제로 일어나는 공격

위의 8단계 방어를 다 갖춰도 뚫리는 공격들이 있습니다. 2024년 이후 봇 시장은 **산업화**되었고, 공격 도구가 SaaS로 판매됩니다.

### 시나리오 A: 레지덴셜 프록시 — IP 차단이 무력화되는 순간

**상황**: 공격자가 Bright Data, Oxylabs 같은 레지덴셜 프록시 서비스를 이용합니다. 전 세계 일반 가정의 공유기 IP(수백만 개)를 경유해 요청을 보냅니다. 각 IP는 진짜 가정용이라 IP 평판 DB에도 "정상"으로 등록되어 있습니다.

**왜 기존 방어가 안 되는가:**
- IP Rate Limit: 각 IP에서 요청 1~2건만 보내므로 한도 이하
- IP 평판 DB (Cloudflare): 가정용 IP라 "clean" 판정
- ASN 차단: 일반 ISP(KT, SKT, LG U+)를 차단할 수 없음
- TLS 핑거프린팅: 진짜 브라우저를 경유하므로 JA3 정상

**방어 전략:**

| 기법 | 원리 | 효과 |
|------|------|------|
| **디바이스 핑거프린팅** | Canvas/WebGL/AudioContext 해시 조합으로 기기 식별 — 같은 기기가 IP를 바꿔도 동일 핑거프린트 | 높음 |
| **행동 시퀀스 분석** | 정상 사용자: 홈→목록→상세→장바구니 흐름. 봇: 상세 페이지만 직접 접근 | 높음 |
| **마우스 엔트로피** | 프론트에서 마우스 궤적을 수집, Shannon 엔트로피 계산. 봇은 직선/없음, 사람은 곡선 | 중간 |
| **요청 간 세션 일관성** | 같은 세션에서 IP가 5분마다 바뀌면 프록시 의심 | 중간 |

```java
// 디바이스 핑거프린트 기반 Rate Limiting
public boolean checkDeviceFingerprint(String fingerprint, String ip) {
    // 동일 핑거프린트가 다른 IP로 분당 10회 이상 → 프록시 사용 확정
    String key = "fp_ips:" + fingerprint;
    redis.sadd(key, ip);
    redis.expire(key, 300); // 5분 윈도우
    long distinctIps = redis.scard(key);

    if (distinctIps > 10) {
        redis.sadd("banned_fingerprints", fingerprint);
        return false; // 차단
    }
    return true;
}
```

---

**1단계: 분석 — 왜 뚫리는가**

IP Rate Limit은 "IP 주소 = 사람"이라는 가정 위에 서 있습니다. 레지덴셜 프록시는 이 가정을 정면으로 깨뜨립니다. Bright Data 기준 전 세계 7,200만 개의 실제 가정용 IP를 보유하고 있으며, 요청마다 자동으로 IP를 교체합니다. 각 IP는 진짜 KT·SKT·LG U+ 가입자 공유기에서 나오기 때문에 ISP ASN도 정상입니다. 공격자가 악용하는 취약점은 두 가지입니다.

첫째, IP 기반 Rate Limit은 "동일 사람이 여러 IP를 쓰는 경우"를 식별하지 못합니다. 둘째, IP 평판 DB(Cloudflare Threat Score, MaxMind 등)는 과거 기록 기반이라 "지금 이 순간 프록시로 쓰이고 있는 가정용 IP"를 실시간으로 알 수 없습니다.

**2단계: 탐지 — 어떻게 발견하는가**

핵심 지표는 "동일 디바이스 핑거프린트가 짧은 시간 안에 여러 AS번호(ASN)에서 출현하는가"입니다. 실제 사용자가 셀룰러(SKT AS9644)에서 WiFi(KT AS4766)로 전환하는 경우도 있지만, 5분 안에 3개 이상의 서로 다른 ASN에서 같은 핑거프린트가 나타나는 것은 불가능합니다.

```python
# Prometheus 기반 모니터링 쿼리
# 5분 윈도우 안에 동일 핑거프린트에서 3개 이상 ASN 변경이 감지된 수
rate(fingerprint_asn_distinct_count{count>="3"}[5m]) > 0

# 알람 조건
# 1분간 레지덴셜 프록시 의심 핑거프린트 수가 100개를 초과하면 PagerDuty 알람
sum(fingerprint_proxy_suspect_total) > 100
```

Redis에서 실시간으로 수집하는 방법:

```python
import redis
import requests

def track_fingerprint_asn(redis_client, fingerprint, ip):
    """IP의 ASN을 조회해 핑거프린트별로 누적"""
    # ipinfo.io API로 ASN 조회 (캐시 필수)
    asn_key = f"asn_cache:{ip}"
    asn = redis_client.get(asn_key)
    if not asn:
        resp = requests.get(f"https://ipinfo.io/{ip}/org", timeout=1)
        asn = resp.text.strip()  # 예: "AS4766 Korea Telecom"
        redis_client.setex(asn_key, 86400, asn)  # 24시간 캐시

    # 핑거프린트별 ASN Set에 추가
    fp_asn_key = f"fp_asn:{fingerprint}"
    redis_client.sadd(fp_asn_key, asn)
    redis_client.expire(fp_asn_key, 300)  # 5분 윈도우
    return redis_client.scard(fp_asn_key)  # 고유 ASN 수 반환
```

**3단계: 검증 — 정말 봇인가 확인**

오탐의 주요 원인은 "모바일 로밍 사용자"와 "VPN 사용자"입니다. 이를 구분하기 위해 "의심" 단계와 "확정" 단계를 분리합니다.

| 조건 | 판정 | 근거 |
|------|------|------|
| 5분 내 ASN 2개 이하 변경 | 정상 | 셀룰러↔WiFi 전환 가능 |
| 5분 내 ASN 3~4개 변경 | **의심** — 추가 검증 요청 | 해외 로밍 중일 수 있음 |
| 5분 내 ASN 5개 이상 변경 | **확정 봇** — 즉시 차단 | 물리적으로 불가능한 이동 속도 |
| IP 위치 간 직선 거리 > 1,000km / 5분 | **확정 봇** | 광속 이동 불가 |

```python
from geopy.distance import geodesic

def is_impossible_travel(redis_client, fingerprint, current_lat, current_lon):
    """연속된 두 위치 간 이동이 물리적으로 불가능한지 확인"""
    prev_key = f"fp_location:{fingerprint}"
    prev_location = redis_client.get(prev_key)

    if prev_location:
        prev_lat, prev_lon, prev_ts = prev_location.decode().split(",")
        elapsed_minutes = (time.time() - float(prev_ts)) / 60
        distance_km = geodesic(
            (float(prev_lat), float(prev_lon)),
            (current_lat, current_lon)
        ).km

        # 비행기 최고속도 1,000km/h = 16.7km/분
        # 이를 초과하면 물리적으로 불가능
        if elapsed_minutes > 0 and distance_km / elapsed_minutes > 16.7:
            return True  # 불가능한 이동 = 봇 확정

    redis_client.setex(
        prev_key, 300,
        f"{current_lat},{current_lon},{time.time()}"
    )
    return False
```

**4단계: 차단 — 어떻게 막는가**

점진적 대응으로 오탐 피해를 최소화합니다.

```java
public RateLimitDecision enforceByFingerprint(
        String fingerprint, String ip, HttpServletRequest req) {

    long asnCount = trackFingerprintAsn(fingerprint, ip);

    // 1단계: ASN 3개 이상 — 조용한 속도 제한 (사용자는 모름)
    if (asnCount >= 3 && asnCount < 5) {
        String throttleKey = "fp_throttle:" + fingerprint;
        long count = redis.incr(throttleKey);
        redis.expire(throttleKey, 60);
        if (count > 10) { // 1분에 10건으로 제한
            return RateLimitDecision.THROTTLE; // 429 + Retry-After: 6
        }
    }

    // 2단계: ASN 5개 이상 — CAPTCHA 도전
    if (asnCount >= 5 && asnCount < 8) {
        return RateLimitDecision.CAPTCHA_REQUIRED;
    }

    // 3단계: ASN 8개 이상 — 핑거프린트 차단 + 가짜 데이터 반환
    if (asnCount >= 8) {
        redis.sadd("banned_fingerprints", fingerprint);
        redis.expire("banned_fingerprints", 86400); // 24시간 차단

        // Tar Pit: 차단 사실을 숨기고 가짜 데이터 반환
        return RateLimitDecision.SERVE_FAKE_DATA;
    }

    return RateLimitDecision.ALLOW;
}
```

Redis로 핑거프린트별 IP 변경 추적과 AS번호 분산도를 계산하는 전체 흐름:

```python
def get_proxy_score(redis_client, fingerprint, ip) -> float:
    """0.0(정상) ~ 1.0(확정 프록시) 점수 반환"""
    # 고유 IP 수 (5분 윈도우)
    ip_key = f"fp_ips:{fingerprint}"
    redis_client.sadd(ip_key, ip)
    redis_client.expire(ip_key, 300)
    unique_ips = redis_client.scard(ip_key)

    # 고유 ASN 수 (5분 윈도우)
    asn = get_asn(ip)  # 캐시된 ASN 조회
    asn_key = f"fp_asn:{fingerprint}"
    redis_client.sadd(asn_key, asn)
    redis_client.expire(asn_key, 300)
    unique_asns = redis_client.scard(asn_key)

    # 점수 계산: ASN 분산도가 핵심 지표
    # 정상 사용자: unique_asns=1~2, unique_ips=1~3
    # 프록시 봇: unique_asns=10~50, unique_ips=50~500
    score = min(1.0, (unique_asns - 1) / 10.0)
    return score
```

**5단계: 사후 분석 — 재발 방지**

공격 종료 후 수행할 분석:

```python
def post_attack_analysis(redis_client, attack_window_start, attack_window_end):
    """공격 후 패턴 분석 및 방어 강화"""

    # 1. 공격에 사용된 ASN 분포 추출
    # 특정 ISP(예: AS7922 Comcast)가 다수 등장하면 해당 ISP 가중치 상향
    attack_asns = get_attack_asns(attack_window_start, attack_window_end)
    for asn, count in attack_asns.most_common(20):
        print(f"ASN {asn}: {count}건 — 임계값 강화 검토")

    # 2. 오탐 계정 식별 (차단됐지만 실제 사용자였던 경우)
    false_positives = identify_false_positives(attack_window_start, attack_window_end)
    print(f"오탐률: {len(false_positives) / total_blocked:.2%}")

    # 3. 방어 임계값 자동 조정
    # 오탐률 > 5%이면 ASN 임계값을 5 → 7로 완화
    if len(false_positives) / total_blocked > 0.05:
        update_config("fp_asn_threshold", current_threshold + 2)
        alert("ASN 임계값 완화: 오탐률 초과")
```

---

### 시나리오 B: CAPTCHA 풀이 서비스 — JS Challenge도 돈으로 뚫린다

**상황**: Cloudflare JS Challenge나 reCAPTCHA를 설정했는데도 봇이 통과합니다. 공격자가 2Captcha, Anti-Captcha 같은 서비스를 이용해 실제 사람이 CAPTCHA를 풀어줍니다. 건당 $0.001~$0.003, 초당 수천 건 처리 가능.

**왜 기존 방어가 안 되는가:**
- JS Challenge: 실제 브라우저가 실행하므로 통과
- reCAPTCHA v2: 사람이 직접 풀어서 통과
- hCaptcha: 동일하게 사람이 풀기

**방어 전략:**

| 기법 | 원리 | 효과 |
|------|------|------|
| **reCAPTCHA v3 (점수 기반)** | 사용자 인터랙션 없이 행동 점수(0~1) 산출, 0.3 이하면 봇 | 높음 — 풀이 서비스가 우회 불가 |
| **Proof of Work** | 클라이언트에게 해시 계산 과제 부여 (100ms 소요). 봇은 대량 요청 시 CPU 비용 폭발 | 매우 높음 |
| **경제성 파괴** | CAPTCHA 난이도를 의심 점수에 비례하여 동적 조절. 고점수 봇은 건당 30초짜리 CAPTCHA → 풀이 비용 100배 증가 | 높음 |
| **CAPTCHA 응답 시간 분석** | 사람: 3~15초, 풀이 서비스: 20~60초 (큐 대기). 응답 시간이 일정하면 서비스 이용 의심 | 중간 |

```python
# Proof of Work — 클라이언트가 해시 퍼즐을 풀어야 API 접근 가능
import hashlib, secrets

def generate_challenge():
    """서버: 난이도 4 (앞 4비트가 0인 해시를 찾아라)"""
    nonce = secrets.token_hex(16)
    return {"nonce": nonce, "difficulty": 4}

def verify_solution(nonce, solution, difficulty):
    """서버: 클라이언트가 제출한 답 검증"""
    hash_result = hashlib.sha256(f"{nonce}{solution}".encode()).hexdigest()
    return hash_result[:difficulty] == "0" * difficulty
    # 난이도 4 → 클라이언트가 평균 65,536번 해시 계산 필요 (~100ms)
    # 정상 사용자: 100ms 대기 (체감 안 됨)
    # 봇 초당 1만 건: 1만 × 100ms = CPU 1,000초 필요 (불가능)
```

---

**1단계: 분석 — 왜 뚫리는가**

CAPTCHA는 "사람만 풀 수 있다"는 가정에 기반합니다. 2Captcha·Anti-Captcha 같은 풀이 서비스는 이 가정을 완전히 무너뜨립니다. 구조는 단순합니다. 봇이 CAPTCHA 이미지를 API로 전송하면, 제3세계 국가의 인간 작업자가 실제로 풀고 결과를 돌려줍니다. 건당 $0.001~$0.003으로, 10만 건 풀이에 $100~$300입니다.

공격자가 악용하는 취약점은 CAPTCHA 시스템이 "풀이 행위자가 누구인가"를 검증하지 않는다는 점입니다. reCAPTCHA v2가 반환하는 토큰은 "이 CAPTCHA가 풀렸다"는 증명이지, "이 요청을 보낸 브라우저가 직접 풀었다"는 증명이 아닙니다. 봇은 토큰만 훔쳐서 자기 요청에 붙이면 됩니다.

**2단계: 탐지 — 어떻게 발견하는가**

핵심 지표는 **CAPTCHA 응답 시간 분포**입니다. 사람이 직접 푸는 경우: 3~10초(집중 상태) 또는 10~20초(산만한 상태). 풀이 서비스를 경유하는 경우: 20~60초(큐 대기 + 전송 왕복). 이 분포는 서비스마다 다르지만 일반적으로 20초 이상이면 풀이 서비스 의심입니다.

```python
import redis
import numpy as np
from collections import Counter

def analyze_captcha_timing(redis_client, window_minutes=60):
    """최근 N분간 CAPTCHA 응답 시간 분포를 분석"""
    timings_raw = redis_client.lrange("captcha_solve_times", 0, -1)
    timings = [float(t) for t in timings_raw]

    if len(timings) < 30:
        return  # 데이터 부족

    # 히스토그램 구간: 0-3초, 3-10초, 10-20초, 20-60초, 60초+
    buckets = [0, 3, 10, 20, 60, float('inf')]
    labels = ["<3s(의심)", "3-10s(정상)", "10-20s(느림)", "20-60s(풀이서비스의심)", ">60s(이상)"]
    counts, _ = np.histogram(timings, bins=buckets)

    for label, count in zip(labels, counts):
        pct = count / len(timings) * 100
        print(f"{label}: {count}건 ({pct:.1f}%)")

    # 알람 조건: 20초 이상 응답이 전체의 30% 초과
    slow_ratio = sum(1 for t in timings if t >= 20) / len(timings)
    if slow_ratio > 0.30:
        trigger_alert(f"CAPTCHA 풀이 서비스 의심: 20초+ 응답 {slow_ratio:.1%}")

def record_captcha_solve_time(redis_client, session_id, solve_seconds):
    """CAPTCHA 응답 시간 기록"""
    redis_client.lpush("captcha_solve_times", solve_seconds)
    redis_client.ltrim("captcha_solve_times", 0, 9999)  # 최근 1만 건만 유지
    redis_client.expire("captcha_solve_times", 3600)

    # 세션별 기록 (검증 단계에서 사용)
    redis_client.setex(f"captcha_time:{session_id}", 300, solve_seconds)
```

모니터링 대시보드 쿼리:

```
# Prometheus: CAPTCHA 응답 시간 P50/P95/P99
histogram_quantile(0.95, rate(captcha_solve_duration_seconds_bucket[5m]))

# 알람: P50이 15초 초과 (풀이 서비스가 다수이면 중앙값이 올라감)
histogram_quantile(0.50, rate(captcha_solve_duration_seconds_bucket[10m])) > 15
```

**3단계: 검증 — 정말 봇인가 확인**

응답 시간 하나만으로 차단하면 네트워크 지연이 심한 정상 사용자를 오탐할 수 있습니다. 두 가지 조건을 동시에 만족해야 "확정"으로 분류합니다.

| 조건 | 의심 | 확정 |
|------|------|------|
| CAPTCHA 응답 시간 | 20초 이상 | 20초 이상 **AND** 성공률 100% |
| 성공률 | — | 5회 연속 1회 시도 성공 |
| 세션 내 CAPTCHA 패턴 | 1회만 풀고 다수 요청 | 풀이 간격이 일정(큐 대기 패턴) |
| IP 다양성 | — | 동일 응답 시간 분포를 가진 IP가 다수 |

```python
def is_captcha_farm(redis_client, session_id, solve_time_seconds) -> bool:
    """CAPTCHA 풀이 서비스인지 판정"""
    # 조건 1: 응답 시간 20초 이상
    if solve_time_seconds < 20:
        return False

    # 조건 2: 이 세션의 CAPTCHA 성공 횟수와 시도 횟수 비교
    success_count = int(redis_client.get(f"captcha_success:{session_id}") or 0)
    attempt_count = int(redis_client.get(f"captcha_attempt:{session_id}") or 1)

    # 5번 모두 1번 시도에 성공 → 사람이 아니라 전문 풀이 서비스
    if attempt_count >= 5 and success_count / attempt_count >= 0.99:
        return True

    return False
```

**4단계: 차단 — 어떻게 막는가**

의심 단계부터 풀이 비용을 점진적으로 올려서 경제성을 파괴합니다.

```python
import hashlib, secrets, time

# 동적 PoW 난이도 조절
DIFFICULTY_TABLE = {
    "normal":   4,   # 평균 100ms, 65,536회 해시
    "suspect":  6,   # 평균 1.6초, 16,777,216회 해시 — 풀이 비용 16배
    "likely":   8,   # 평균 25초, 4억 회 해시 — 풀이 비용 250배
    "confirmed": 10, # 평균 6.5분 — 경제적으로 불가능
}

def get_pow_difficulty(redis_client, session_id, ip) -> int:
    """세션 위험도에 따라 PoW 난이도 반환"""
    solve_time = float(redis_client.get(f"captcha_time:{session_id}") or 0)
    is_farm = is_captcha_farm(redis_client, session_id, solve_time)

    if is_farm:
        # 확정: 난이도 10 (건당 6.5분 → 분당 요청 불가)
        redis_client.setex(f"pow_difficulty:{session_id}", 3600, 10)
        return DIFFICULTY_TABLE["confirmed"]

    if solve_time >= 20:
        # 의심: 난이도 6 (건당 1.6초 → 초당 요청 불가)
        return DIFFICULTY_TABLE["suspect"]

    return DIFFICULTY_TABLE["normal"]

def generate_challenge(redis_client, session_id, ip):
    nonce = secrets.token_hex(16)
    difficulty = get_pow_difficulty(redis_client, session_id, ip)
    redis_client.setex(f"pow_nonce:{session_id}", 300, nonce)
    return {"nonce": nonce, "difficulty": difficulty}

def verify_pow(redis_client, session_id, nonce, solution):
    stored_nonce = redis_client.get(f"pow_nonce:{session_id}")
    if not stored_nonce or stored_nonce.decode() != nonce:
        return False
    difficulty = int(redis_client.get(f"pow_difficulty:{session_id}") or 4)
    hash_val = hashlib.sha256(f"{nonce}{solution}".encode()).hexdigest()
    return hash_val[:difficulty] == "0" * difficulty
```

비용 계산 정리:

| 난이도 | 평균 해시 횟수 | 클라이언트 시간 | 풀이 서비스 비용(초당 1만 건 기준) |
|--------|-------------|--------------|----------------------------------|
| 4 (정상) | 65,536 | ~100ms | 초당 $10 |
| 6 (의심) | 16,777,216 | ~1.6초 | 초당 $160 |
| 8 (likely) | 4,294,967,296 | ~25초 | 초당 $2,500 — 비경제적 |

**5단계: 사후 분석 — 재발 방지**

```python
def post_captcha_attack_analysis(redis_client, db):
    """CAPTCHA 풀이 서비스 공격 후 분석"""

    # 1. 풀이 서비스를 이용한 세션이 실제로 어떤 행동을 했는가
    # → 스크래핑인지, 계정 탈취 시도인지, 스팸 게시인지 파악
    farm_sessions = db.query("""
        SELECT session_id, action_type, count(*) as cnt
        FROM request_logs
        WHERE session_id IN (
            SELECT session_id FROM captcha_events
            WHERE solve_time >= 20 AND solve_success_rate >= 0.99
            AND created_at >= NOW() - INTERVAL '24 hours'
        )
        GROUP BY session_id, action_type
        ORDER BY cnt DESC
    """)

    # 2. 공격자가 얻어간 데이터 범위 파악
    for session in farm_sessions:
        print(f"세션 {session.session_id}: {session.action_type} {session.cnt}건")

    # 3. 방어 강화 조치
    # 공격 목적이 스크래핑이면 → Tar Pit(가짜 데이터) 활성화
    # 공격 목적이 계정 탈취면 → 해당 이메일 대상 MFA 강제
    # 공격 목적이 스팸이면 → 콘텐츠 필터 강화

    # 4. PoW 기본 난이도 재검토
    # 풀이 서비스 탐지 비율이 1% 초과이면 기본 난이도를 4→5로 상향
    farm_ratio = get_captcha_farm_ratio(redis_client)
    if farm_ratio > 0.01:
        update_config("pow_base_difficulty", 5)
        print(f"PoW 기본 난이도 상향: 탐지 비율 {farm_ratio:.2%}")
```

### 시나리오 B-2: AI CAPTCHA 솔버 — GPT-4V가 CAPTCHA를 99% 풀어버린다

2024년 이후 CAPTCHA 풀이 시장이 근본적으로 바뀌었습니다. 사람이 아니라 **AI가 풀어줍니다.**

**현재 AI CAPTCHA 솔버 현황:**

| CAPTCHA 유형 | AI 풀이 성공률 | 풀이 시간 | 비용 (건당) |
|-------------|:---:|:---:|:---:|
| 이미지 텍스트 (왜곡 문자) | **99.8%** | 0.5초 | $0.0001 |
| reCAPTCHA v2 (이미지 선택) | **96%** | 2초 | $0.001 |
| reCAPTCHA v3 (점수 기반) | **우회 가능** | — | Playwright 행동 조작으로 0.7+ 점수 |
| hCaptcha | **94%** | 3초 | $0.002 |
| Cloudflare Turnstile | **90%+** | 5초 | $0.003 |
| Proof of Work (해시 퍼즐) | **뚫을 수 없음** | 컴퓨팅 비용 비례 | CPU 시간 × 난이도 |

> **핵심**: 이미지/텍스트 기반 CAPTCHA는 **AI에게 이미 졌습니다.** GPT-4V, Claude Vision이 왜곡된 텍스트를 사람보다 더 잘 읽습니다. reCAPTCHA v3의 "행동 점수"도 Playwright + 가짜 마우스로 0.7 이상을 만들 수 있습니다.

**왜 기존 CAPTCHA 방어가 다 뚫리는가:**

```python
# 공격자의 AI CAPTCHA 솔버 — reCAPTCHA v2 이미지 선택
import anthropic, base64

client = anthropic.Anthropic()

def solve_recaptcha_image(image_bytes, instruction):
    """예: '버스가 있는 이미지를 모두 선택하세요'"""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64",
                    "media_type": "image/png",
                    "data": base64.b64encode(image_bytes).decode()}},
                {"type": "text", "text": f"이 3x3 그리드에서 {instruction} "
                    "해당하는 셀 번호를 쉼표로 반환해. 숫자만."}
            ]
        }]
    )
    return [int(x.strip()) for x in response.content[0].text.split(",")]
    # 성공률 96%, 풀이 시간 2초, 비용 $0.001/건
```

**AI 시대의 CAPTCHA 대안 — CAPTCHA를 버리고 다른 것으로 가야 합니다:**

| 대안 | 원리 | AI 우회 가능성 | 구현 난이도 |
|------|------|:---:|:---:|
| **Proof of Work (PoW)** | 클라이언트 CPU에게 해시 계산 강제 — AI 여부와 무관하게 **컴퓨팅 비용** 부과 | ❌ 불가 — 수학적 보장 | 중간 |
| **행동 생체 인증** | 타이핑 리듬, 터치 압력, 자이로스코프 데이터 | 매우 어려움 — 하드웨어 센서 필요 | 높음 |
| **지연 기반 PoW** | 의심 점수에 비례해 응답 지연 (0.1초~30초) | ❌ 불가 — 시간을 사야 함 | 낮음 |
| **경제적 마찰** | SMS 인증, 신용카드 등록, 보증금 | 대량 확보 비용 높음 | 낮음 |
| **인비저블 챌린지** | 브라우저 API 호출 패턴 (Web Audio, WebGL, Battery API 등 50+ 신호) | 어려움 — 모든 API를 완벽 시뮬레이션 불가 | 높음 |

**Proof of Work가 AI 시대의 답인 이유:**

CAPTCHA는 "사람인지 봇인지"를 구분하려 합니다. 하지만 AI가 사람을 흉내 낼 수 있으므로 이 구분은 더 이상 유효하지 않습니다. PoW는 질문을 바꿉니다: **"사람인지 봇인지"가 아니라 "이 요청에 컴퓨팅 비용을 지불했는가?"**

```java
// 적응형 Proof of Work — 의심 점수에 따라 난이도 동적 조절
public class AdaptiveProofOfWork {

    // 의심 점수 0~100에 따라 PoW 난이도 결정
    public int getDifficulty(double threatScore) {
        if (threatScore < 20) return 0;   // 정상 — PoW 없음
        if (threatScore < 50) return 4;   // 경미 의심 — 100ms (사용자 체감 없음)
        if (threatScore < 70) return 6;   // 중간 의심 — 1.6초
        if (threatScore < 90) return 8;   // 높은 의심 — 25초 (봇 비경제적)
        return 10;                         // 확정 봇 — 6분+ (사실상 차단)
    }

    // 비용 계산:
    // 정상 사용자: 난이도 0 = 0ms 추가 지연
    // 봇 초당 1,000건 × 난이도 8 = 초당 25,000초 CPU 필요 = GPU 25대 필요
    // → 봇 운영 비용이 데이터 가치를 초과하는 시점에서 공격 포기
}
```

**핵심 통찰**: CAPTCHA 군비 경쟁에서 방어측이 이길 수 없습니다. AI 솔버는 점점 좋아지고 저렴해집니다. **PoW는 물리 법칙(연산에는 시간이 걸린다)에 의존**하므로 AI로 우회할 수 없습니다. 의심 점수가 높을수록 PoW 난이도를 올려 공격 비용을 지수적으로 증가시키는 것이 AI 시대의 봇 방어 핵심입니다.

---

### 시나리오 C: 계정 탈취 후 합법 토큰 악용

**상황**: 크리덴셜 스터핑으로 탈취한 수만 개의 실제 계정으로 로그인합니다. 각 계정의 합법적인 JWT 토큰으로 API를 호출합니다. 사용자 ID 기반 Rate Limiting도 각 계정당 한도 이하입니다.

**왜 기존 방어가 안 되는가:**
- IP Rate Limit: 레지덴셜 프록시와 결합하면 무력
- 사용자 ID Rate Limit: 계정당 요청 수가 정상 범위
- 인증: 탈취된 실제 JWT 토큰이라 유효

**방어 전략:**

| 기법 | 원리 | 효과 |
|------|------|------|
| **로그인 이상 탐지** | 평소 한국에서 접속하던 계정이 갑자기 러시아 IP로 → MFA 강제 | 높음 |
| **계정 행동 클러스터링** | 수만 개 계정이 동일 시간대에 동일 API를 호출 → 비정상 집단 행동 탐지 | 매우 높음 |
| **API 호출 패턴 프로파일링** | 각 사용자의 평소 API 호출 빈도/패턴을 학습, 3σ 이상 벗어나면 차단 | 높음 |
| **동시 세션 제한** | 계정당 활성 세션 3개로 제한, 초과 시 가장 오래된 세션 강제 만료 | 중간 |

```java
// 집단 행동 탐지 — 같은 시간에 같은 API를 호출하는 계정 클러스터 식별
@Scheduled(fixedRate = 60_000) // 1분마다
public void detectCoordinatedAbuse() {
    // 최근 1분간 /api/products 호출한 사용자 목록
    Set<String> recentUsers = redis.smembers("api_users:products:last_1m");

    if (recentUsers.size() > 1000) { // 평소 대비 10배 이상
        // 이 사용자들의 IP 분포, 요청 간격 분포 분석
        double intervalStdDev = calculateIntervalStdDev(recentUsers);

        if (intervalStdDev < 0.5) { // 요청 간격이 너무 균일 → 봇 집단
            recentUsers.forEach(userId ->
                redis.setex("suspicious:" + userId, 3600, "coordinated_abuse"));
            alertSecurityTeam("Coordinated abuse detected: " + recentUsers.size() + " accounts");
        }
    }
}
```

---

**1단계: 분석 — 왜 뚫리는가**

사용자 ID 기반 Rate Limit은 "계정 = 사람 1명"이라는 가정에 의존합니다. 크리덴셜 스터핑으로 탈취한 계정 1만 개는 이 가정을 1만 배로 희석시킵니다. 각 계정이 분당 5건씩만 호출해도 전체 시스템에는 분당 5만 건이 들어옵니다. 탈취된 JWT 토큰은 서명이 유효하기 때문에 인증 레이어도 통과합니다.

공격자가 악용하는 취약점은 개별 계정 관점에서는 모든 수치가 정상이라는 점입니다. 이상은 오직 **집단 행동 패턴**에서만 드러납니다. 수만 개의 계정이 동일한 시간대에 동일한 API를 동일한 간격으로 호출하는 패턴은 자연 발생적으로는 불가능합니다.

**2단계: 탐지 — 어떻게 발견하는가**

두 가지 신호를 동시에 모니터링합니다.

첫째, 글로벌 로그인 실패율 급증과 동시에 다수 계정에서 비정상 API 호출이 발생합니다. 둘째, 정상 상태에서 특정 API의 호출 계정 수 분포는 멱함수(소수 헤비 유저 + 다수 라이트 유저)를 따르는데, 공격 중에는 수천 개의 계정이 동시에 동일 API를 호출하는 이상 분포가 됩니다.

```python
import redis
from collections import Counter
import statistics

def detect_coordinated_abuse(redis_client, api_endpoint, window_minutes=1):
    """집단 행동 탐지 — 동일 시간대 동일 API 호출 계정 클러스터 식별"""

    key = f"api_users:{api_endpoint}:last_{window_minutes}m"
    recent_users = redis_client.smembers(key)
    user_count = len(recent_users)

    # 기준선(baseline) 대비 10배 초과 시 의심
    baseline_key = f"api_users_baseline:{api_endpoint}"
    baseline = float(redis_client.get(baseline_key) or user_count)

    surge_ratio = user_count / max(baseline, 1)

    # 요청 간격 표준편차 계산 (낮을수록 봇)
    interval_key = f"api_intervals:{api_endpoint}:last_{window_minutes}m"
    intervals = [float(x) for x in redis_client.lrange(interval_key, 0, 999)]
    interval_stddev = statistics.stdev(intervals) if len(intervals) > 10 else 999

    print(f"[{api_endpoint}] 계정 수: {user_count} (기준선 대비 {surge_ratio:.1f}x), "
          f"간격 표준편차: {interval_stddev:.3f}s")

    # 알람 조건: 기준선 10배 초과 AND 간격 표준편차 0.5 미만
    if surge_ratio >= 10 and interval_stddev < 0.5:
        trigger_alert(
            f"집단 행동 공격 감지: {api_endpoint} — "
            f"{user_count}개 계정, 간격편차={interval_stddev:.3f}s"
        )
        return True
    return False
```

Prometheus 모니터링 쿼리:

```
# 계정당 API 호출 수 분포가 비정상적으로 균일해지는지 감지
# 정상: 소수 헤비 유저가 대부분의 요청을 차지
# 공격: 수천 계정이 동일한 소량 요청 (균일 분포)
stddev(rate(api_calls_per_user_total[1m])) / avg(rate(api_calls_per_user_total[1m])) < 0.2

# 동시에 로그인 실패율 급증 감지
rate(login_failure_total[1m]) > rate(login_failure_total[1m] offset 1h) * 5
```

**3단계: 검증 — 정말 봇인가 확인**

정상 사용자 중에도 마케팅 이벤트나 앱 업데이트 배포 시 일시적으로 동시 접속이 급증할 수 있습니다. 이와 구분하기 위해 계정별 "평소 행동 프로파일"과의 유사도를 비교합니다.

```python
import numpy as np

def compute_behavior_similarity(user_id, current_window_hours=1):
    """사용자의 현재 행동과 평소 프로파일의 코사인 유사도 계산"""

    # 평소 프로파일: 지난 30일 시간대별 API 호출 분포 (24차원 벡터)
    profile_key = f"user_profile:{user_id}:hourly"
    profile = np.array([float(x) for x in redis.lrange(profile_key, 0, 23)])

    # 현재 행동: 지난 1시간의 API 호출 패턴
    current_key = f"user_current:{user_id}:api_pattern"
    current = np.array([float(x) for x in redis.lrange(current_key, 0, 23)])

    if profile.sum() == 0 or current.sum() == 0:
        return 1.0  # 데이터 없으면 정상으로 간주

    # 코사인 유사도 (1.0 = 완전 일치, 0.0 = 완전 다름)
    similarity = np.dot(profile, current) / (
        np.linalg.norm(profile) * np.linalg.norm(current) + 1e-9
    )
    return float(similarity)

def classify_account_status(user_id) -> str:
    similarity = compute_behavior_similarity(user_id)

    if similarity >= 0.7:
        return "NORMAL"          # 평소와 70% 이상 유사
    elif similarity >= 0.4:
        return "SUSPICIOUS"      # 추가 검증 필요
    else:
        return "LIKELY_COMPROMISED"  # 평소와 완전히 다른 행동
```

| 코사인 유사도 | 판정 | 조치 |
|-------------|------|------|
| 0.7 이상 | 정상 | 허용 |
| 0.4~0.7 | 의심 | MFA 재인증 요청 |
| 0.4 미만 | 탈취 의심 확정 | 세션 강제 만료 + 이메일 알림 |

**4단계: 차단 — 어떻게 막는가**

```java
@Service
public class CompromisedAccountDefense {

    // 이상 행동 감지 시 세션 강제 만료 + MFA 강제
    public void handleSuspiciousActivity(String userId, String reason) {
        double similarity = computeBehaviorSimilarity(userId);

        if (similarity < 0.4) {
            // 1단계: 모든 활성 세션 즉시 만료
            invalidateAllSessions(userId);

            // 2단계: 새 로그인 시 MFA 강제 (24시간)
            redis.setex("force_mfa:" + userId, 86400, reason);

            // 3단계: 계정 소유자에게 알림
            sendSecurityAlert(userId,
                "비정상적인 접근이 감지되어 세션이 종료되었습니다. " +
                "본인이 아니면 비밀번호를 즉시 변경하세요.");

            // 4단계: 보안팀 에스컬레이션 로그
            securityLog.warn("Account likely compromised: userId={}, " +
                "behaviorSimilarity={}, reason={}", userId, similarity, reason);

        } else if (similarity < 0.7) {
            // 의심 단계: 조용히 추가 인증 요청 (사용자 경험 최소 침해)
            redis.setex("soft_mfa:" + userId, 3600, "suspicious_behavior");
        }
    }

    // 집단 행동 감지 시 일괄 대응
    public void handleCoordinatedAbuse(Set<String> suspiciousUserIds) {
        // 집단으로 의심되는 계정들의 Rate Limit을 일시적으로 강화
        suspiciousUserIds.forEach(userId -> {
            String key = "emergency_rate_limit:" + userId;
            redis.setex(key, 3600, "10");  // 1시간 동안 분당 10건으로 제한
        });

        // 1,000개 이상이면 글로벌 비상 모드
        if (suspiciousUserIds.size() > 1000) {
            redis.setex("global_emergency_mode", 3600, "coordinated_attack");
            enableEmergencyRateLimit();  // 모든 사용자 Rate Limit 50% 강화
        }
    }
}
```

**5단계: 사후 분석 — 재발 방지**

```python
def post_account_takeover_analysis(db, redis_client, attack_start, attack_end):
    """계정 탈취 공격 후 분석"""

    # 1. 탈취된 계정 수와 피해 범위 파악
    compromised_accounts = db.query("""
        SELECT COUNT(DISTINCT user_id) as count,
               SUM(CASE WHEN action='data_access' THEN 1 ELSE 0 END) as data_exposures,
               SUM(CASE WHEN action='purchase' THEN amount ELSE 0 END) as financial_damage
        FROM security_events
        WHERE event_type='compromised_session'
        AND created_at BETWEEN %s AND %s
    """, (attack_start, attack_end))

    print(f"탈취 계정: {compromised_accounts.count}개")
    print(f"데이터 노출: {compromised_accounts.data_exposures}건")
    print(f"금전 피해: {compromised_accounts.financial_damage:,}원")

    # 2. 탈취된 계정들의 공통점 분석
    # → 특정 기간에 가입한 계정인가? 특정 이메일 도메인인가?
    # → 패스워드 강도가 낮은 계정인가?
    common_patterns = analyze_compromised_account_patterns(compromised_accounts)

    # 3. 방어 강화 조치
    # 탈취 계정 비율이 높았던 이메일 도메인에 MFA 강제
    for domain in common_patterns.high_risk_domains:
        force_mfa_for_domain(domain)

    # 4. 행동 프로파일 베이스라인 재계산
    # 공격 기간의 데이터를 제외하고 재학습
    rebuild_behavior_profiles(exclude_window=(attack_start, attack_end))

    # 5. 동시 세션 제한 임계값 검토
    # 공격 중 계정당 최대 동시 세션이 몇 개였는가
    max_concurrent = get_max_concurrent_sessions_during_attack(attack_start, attack_end)
    print(f"공격 중 계정당 최대 동시 세션: {max_concurrent}")
    if max_concurrent > 3:
        update_config("max_concurrent_sessions", 2)  # 더 엄격하게 조정
```

---

### 시나리오 D: Slowloris / Low-and-slow — 탐지 안 되는 느린 공격

**상황**: 봇이 HTTP 연결을 열고 헤더를 극도로 느리게 보냅니다 (10초마다 1바이트). 서버는 연결이 완료되길 기다리며 스레드/커넥션을 점유합니다. 초당 요청 수는 0건이라 Rate Limiter에 안 걸립니다.

**왜 기존 방어가 안 되는가:**
- QPS Rate Limit: 완성된 요청이 0건이므로 카운터에 안 잡힘
- IP Rate Limit: 연결만 열고 있을 뿐 요청을 완성하지 않음
- WAF: 정상적인 HTTP 헤더를 보내고 있어 패턴 매칭 불가

**방어 전략:**

| 기법 | 설정 | 효과 |
|------|------|------|
| **연결 타임아웃 단축** | Nginx `client_header_timeout 10s` | 10초 내 헤더 미완성 시 강제 종료 |
| **동시 연결 수 제한** | Nginx `limit_conn_zone` IP당 최대 50개 | 연결 독점 방지 |
| **최소 전송률** | Apache `RequestReadTimeout header=20-40,MinRate=500` | 초당 500바이트 미만이면 끊기 |
| **리버스 프록시 버퍼링** | Nginx가 요청을 완전히 수신한 후 백엔드로 전달 | 백엔드 서버 보호 |

```nginx
# Nginx Slowloris 방어 설정
http {
    # IP당 동시 연결 50개로 제한
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;
    limit_conn conn_limit 50;

    # 헤더 수신 타임아웃 10초, 바디 수신 타임아웃 30초
    client_header_timeout 10s;
    client_body_timeout 30s;

    # Keep-alive 연결 최대 100개, 타임아웃 30초
    keepalive_timeout 30s;
    keepalive_requests 100;
}
```

---

**1단계: 분석 — 왜 뚫리는가**

Slowloris가 통하는 이유는 HTTP/1.1 서버가 설계상 "헤더 수신 완료"를 기다리기 때문입니다. 스레드 기반 서버(Apache prefork, Tomcat BIO)는 연결마다 스레드를 할당하고, 헤더가 완성될 때까지 그 스레드를 점유합니다. 공격자는 10바이트짜리 헤더를 10초에 1바이트씩 보냅니다. 요청은 영원히 "진행 중"이고, 스레드는 영원히 "대기 중"입니다.

QPS Rate Limit이 무력화되는 이유는 정확합니다. 완성된 요청이 0건이기 때문입니다. 방화벽과 WAF도 정상적인 HTTP 헤더 구문(`GET /index.html HTTP/1.1\r\nHost: target.com\r\n`)을 보내고 있어 패턴 매칭이 불가능합니다. 공격자는 연결만 열면 되고, 요청을 완성할 필요가 없습니다.

**2단계: 탐지 — 어떻게 발견하는가**

핵심 지표는 **불완전 연결 수(incomplete connections)**와 **연결 대비 완료 요청 비율**입니다.

```bash
# netstat으로 ESTABLISHED 연결 중 오래된 연결 탐지
# SYN_RECV 상태가 급증하면 SYN Flood, ESTABLISHED가 급증하면 Slowloris
watch -n 1 'netstat -ant | awk "{print \$6}" | sort | uniq -c | sort -rn'

# IP별 연결 수 상위 목록 (특정 IP가 50+ 연결 유지 중이면 의심)
netstat -ant | grep ESTABLISHED | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head -20

# ss 명령으로 더 상세한 연결 상태 확인
ss -s  # 전체 요약
ss -ant state established | wc -l  # 현재 ESTABLISHED 연결 수
```

Prometheus + Nginx 연동 모니터링:

```python
import subprocess
import re
from prometheus_client import Gauge

# 메트릭 정의
incomplete_connections = Gauge('nginx_incomplete_connections',
                                'Number of connections without completed request')
connection_completion_ratio = Gauge('nginx_connection_completion_ratio',
                                    'Ratio of completed requests to active connections')

def collect_slowloris_metrics():
    """Nginx 상태 페이지 + netstat으로 Slowloris 징후 수집"""

    # Nginx stub_status 파싱
    # nginx.conf에 location /nginx_status { stub_status; } 설정 필요
    import requests
    status = requests.get("http://localhost/nginx_status", timeout=2).text
    # 예시 출력:
    # Active connections: 847
    # server accepts handled requests: 12345 12345 54321
    # Reading: 823 Writing: 15 Waiting: 9

    reading = int(re.search(r'Reading: (\d+)', status).group(1))
    writing = int(re.search(r'Writing: (\d+)', status).group(1))
    active = int(re.search(r'Active connections: (\d+)', status).group(1))

    # Reading이 높고 Writing이 낮으면 → 헤더 수신 중인 연결이 많음 = Slowloris 징후
    incomplete_connections.set(reading)
    if active > 0:
        connection_completion_ratio.set(writing / active)

    # 알람 조건: Reading/Active 비율이 80% 초과
    if active > 100 and reading / active > 0.8:
        trigger_alert(
            f"Slowloris 의심: Active={active}, Reading={reading} "
            f"({reading/active:.1%}) — 헤더 미완성 연결 급증"
        )
```

Prometheus 알람 규칙:

```yaml
# alerting_rules.yml
groups:
  - name: slowloris
    rules:
      - alert: SlowlorisAttackSuspected
        # Reading 연결이 전체의 70% 초과이고 100개 이상
        expr: nginx_reading_connections > 100 AND
              nginx_reading_connections / nginx_active_connections > 0.7
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Slowloris 공격 의심 — 즉시 확인 필요"
```

**3단계: 검증 — 정말 봇인가 확인**

정상적인 느린 연결과 Slowloris를 구분하는 기준은 **Content-Length 헤더**와 **전송 속도**입니다.

| 조건 | 정상 느린 연결 | Slowloris |
|------|-------------|-----------|
| Content-Length 헤더 | 존재 (대용량 업로드) | 없거나 헤더 자체가 미완성 |
| 전송 속도 | 느리지만 일정 (수십 KB/s) | 극도로 느림 (수 바이트/초) |
| 헤더 완성 여부 | 헤더는 빠르게 완성 | 헤더가 수십 초째 미완성 |
| User-Agent | 정상 브라우저 | 없거나 의심스러운 값 |
| 같은 IP 연결 수 | 1~3개 | 수십~수백 개 |

```bash
# tcpdump로 의심 IP의 패킷 간격 분석
# 정상: 패킷이 꾸준히 옴, Slowloris: 매우 드문드문 옴
tcpdump -i eth0 -n host 1.2.3.4 -A 2>/dev/null | \
    awk '/^[0-9]/{print $1}' | \
    awk 'NR>1{printf "%.6f\n", $1-prev} {prev=$1}' | \
    sort -n | tail -5
# 패킷 간격이 수 초 이상이면 Slowloris 확정

# Nginx 로그에서 헤더 수신 시간이 긴 요청 필터링
# log_format에 $request_time 포함 필요
awk '$NF > 30' /var/log/nginx/access.log | \
    awk '{print $1}' | sort | uniq -c | sort -rn | head -10
```

**4단계: 차단 — 어떻게 막는가**

Nginx 설정 강화와 커널 레벨 방어를 결합합니다.

```nginx
# /etc/nginx/nginx.conf — Slowloris 완전 방어 설정
http {
    # 연결 추적용 공유 메모리 존
    limit_conn_zone $binary_remote_addr zone=conn_limit_per_ip:10m;
    limit_conn_zone $server_name        zone=conn_limit_per_server:10m;

    server {
        # IP당 동시 연결 20개로 제한 (기존 50개에서 강화)
        limit_conn conn_limit_per_ip     20;
        # 서버 전체 최대 동시 연결 1000개
        limit_conn conn_limit_per_server 1000;

        # 헤더 수신 타임아웃: 5초 (기존 10초에서 강화)
        client_header_timeout 5s;
        # 바디 수신 타임아웃: 10초
        client_body_timeout   10s;
        # 응답 전송 타임아웃: 10초
        send_timeout          10s;

        # Keep-alive 연결 타임아웃 단축
        keepalive_timeout     15s;
        keepalive_requests    50;

        # 최소 전송 속도: 초당 100바이트 미만이면 연결 끊기
        # (대용량 업로드와 구분: Content-Length 있으면 예외)
        client_body_min_rate 100;
    }
}
```

커널 레벨 SYN Cookie 활성화 (SYN Flood 병행 방어):

```bash
# /etc/sysctl.conf에 추가
# SYN Cookie: SYN Flood 방어 (SYN 큐 가득 차면 자동 활성화)
net.ipv4.tcp_syncookies = 1

# TIME_WAIT 소켓 재사용 허용 (연결 고갈 방지)
net.ipv4.tcp_tw_reuse = 1

# FIN_WAIT2 타임아웃 단축
net.ipv4.tcp_fin_timeout = 15

# TCP keep-alive 설정 (유령 연결 탐지)
net.ipv4.tcp_keepalive_time = 60
net.ipv4.tcp_keepalive_intvl = 10
net.ipv4.tcp_keepalive_probes = 3

# 설정 즉시 적용
sysctl -p
```

공격 진행 중 실시간 IP 차단 스크립트:

```bash
#!/bin/bash
# slowloris_blocker.sh — 50개 이상 연결 유지 IP 자동 차단

THRESHOLD=50
WHITELIST=("10.0.0.0/8" "172.16.0.0/12")  # 내부 IP 제외

netstat -ant | grep ESTABLISHED | \
    awk '{print $5}' | cut -d: -f1 | \
    sort | uniq -c | sort -rn | \
    while read count ip; do
        if [ "$count" -gt "$THRESHOLD" ]; then
            # 화이트리스트 확인
            is_whitelisted=false
            for cidr in "${WHITELIST[@]}"; do
                if ipcalc -n "$ip" "$cidr" 2>/dev/null | grep -q "NETWORK"; then
                    is_whitelisted=true
                fi
            done

            if [ "$is_whitelisted" = false ]; then
                echo "차단: $ip ($count 연결)"
                iptables -I INPUT -s "$ip" -j DROP
                # 1시간 후 자동 해제
                (sleep 3600 && iptables -D INPUT -s "$ip" -j DROP) &
            fi
        fi
    done
```

**5단계: 사후 분석 — 재발 방지**

```python
def post_slowloris_analysis(log_file, attack_start, attack_end):
    """Slowloris 공격 후 분석 및 타임아웃 설정 최적화"""

    # 1. 공격 피해 규모: 정상 사용자 요청 중 타임아웃 발생 건수
    timeout_requests = parse_nginx_log_timeouts(log_file, attack_start, attack_end)
    print(f"공격 중 타임아웃 요청: {len(timeout_requests)}건")

    # 2. 공격 IP 분포 분석
    attack_ips = get_attack_ips(log_file, attack_start, attack_end)
    print(f"공격 IP 수: {len(attack_ips)}개")
    print(f"상위 10개 IP: {attack_ips.most_common(10)}")

    # 3. 타임아웃 설정 최적화
    # 정상 요청의 P99 헤더 수신 시간을 기준으로 타임아웃 설정
    normal_header_times = get_normal_header_times(log_file)
    p99_time = sorted(normal_header_times)[int(len(normal_header_times) * 0.99)]
    optimal_timeout = max(3, p99_time * 1.5)  # P99의 1.5배, 최소 3초

    print(f"정상 요청 P99 헤더 수신 시간: {p99_time:.2f}초")
    print(f"권장 client_header_timeout: {optimal_timeout:.0f}초")

    # 4. 연결 수 임계값 재설정
    # 공격 중 공격 IP당 평균 연결 수의 50%를 새 임계값으로
    avg_attack_connections = sum(attack_ips.values()) / len(attack_ips)
    new_conn_limit = max(10, int(avg_attack_connections * 0.5))
    print(f"권장 limit_conn: {new_conn_limit}")

    # 5. iptables 블랙리스트에 공격 IP 영구 등록
    for ip, count in attack_ips.most_common(100):
        add_to_permanent_blacklist(ip, reason="slowloris_attack")
```

---

### 시나리오 E: GraphQL 쿼리 폭탄 — 단일 요청으로 서버를 죽인다

**상황**: GraphQL API가 있으면 공격자가 깊이 중첩된 쿼리 하나로 서버를 다운시킬 수 있습니다. 요청 1건이라 Rate Limiter에 안 걸리지만, 서버에서 수백만 행을 조인합니다.

```graphql
# 한 번의 요청으로 DB를 죽이는 쿼리
query {
  users(first: 1000) {
    orders(first: 100) {
      items(first: 50) {
        product {
          reviews(first: 100) {
            author { orders { items { product { name } } } }
          }
        }
      }
    }
  }
}
# 1000 × 100 × 50 × 100 = 5억 행 조회 시도
```

**방어 전략:**

| 기법 | 원리 | 구현 |
|------|------|------|
| **쿼리 깊이 제한** | depth > 5 거부 | `graphql-depth-limit` 라이브러리 |
| **쿼리 복잡도 점수** | 각 필드에 가중치, 합산 > 1000 거부 | 커스텀 validation rule |
| **쿼리 비용 기반 Rate Limit** | 요청 1건이 아니라 "비용"으로 카운팅 | Redis에 비용 합산 저장 |
| **타임아웃** | 쿼리 실행 5초 초과 시 강제 취소 | `DataFetcherTimeout` 설정 |
| **Persisted Queries** | 사전 등록된 쿼리만 허용, 임의 쿼리 거부 | Apollo Server `persistedQueries` |

```java
// 쿼리 복잡도 기반 Rate Limiting
public class QueryCostAnalyzer {
    public int calculateCost(GraphQLQuery query) {
        int cost = 0;
        for (Field field : query.getFields()) {
            int multiplier = field.getArgument("first", 1); // pagination 크기
            cost += multiplier * (1 + calculateCost(field.getSubFields()));
        }
        return cost;
    }
}

// Rate Limiter에서 요청 수가 아니라 "비용"으로 제한
public boolean allowRequest(String userId, int queryCost) {
    String key = "graphql_cost:" + userId;
    long totalCost = redis.incrBy(key, queryCost);
    redis.expire(key, 60); // 분당 윈도우
    return totalCost <= 10_000; // 분당 비용 한도
}
```

---

**1단계: 분석 — 왜 뚫리는가**

GraphQL의 근본적인 취약점은 "요청 1건 = 작업 1개"라는 REST의 가정이 성립하지 않는다는 점입니다. REST에서 `/products/1`은 DB 쿼리 1개이지만, GraphQL에서 `users(first:1000) { orders(first:100) { items(first:50) } }`는 1,000 × 100 × 50 = 5,000만 번의 DB 조회를 유발할 수 있습니다.

QPS Rate Limit이 무력화되는 이유는 명확합니다. 공격자는 단 1건의 요청만 보냅니다. Rate Limit 카운터는 1 증가하고, 서버는 수억 행을 조인하다가 다운됩니다. 공격자가 악용하는 취약점은 GraphQL 스키마가 공개(introspection)되어 있어 어떤 중첩이 가능한지 쉽게 파악할 수 있다는 점과, 기본 설정에서 깊이·복잡도 제한이 없다는 점입니다.

**2단계: 탐지 — 어떻게 발견하는가**

핵심 지표는 **쿼리 실행 시간 P99 급증**과 **DB CPU 급등**의 동시 발생입니다. 일반적인 트래픽 증가와 다르게, GraphQL 폭탄은 요청 수가 적음에도 불구하고 DB 부하가 폭발적으로 증가합니다.

```python
import time
import redis
from functools import wraps

def monitor_graphql_execution(redis_client):
    """GraphQL 쿼리 실행 시간 모니터링 데코레이터"""
    def decorator(resolve_fn):
        @wraps(resolve_fn)
        def wrapper(*args, **kwargs):
            start = time.monotonic()
            result = resolve_fn(*args, **kwargs)
            elapsed_ms = (time.monotonic() - start) * 1000

            # 실행 시간 히스토그램 기록
            redis_client.lpush("graphql_exec_times", elapsed_ms)
            redis_client.ltrim("graphql_exec_times", 0, 9999)
            redis_client.expire("graphql_exec_times", 300)

            # 단일 쿼리가 1초 초과 시 즉시 알람
            if elapsed_ms > 1000:
                query_info = args[1].field_name if len(args) > 1 else "unknown"
                trigger_alert(
                    f"GraphQL 폭탄 의심: {query_info} 실행 {elapsed_ms:.0f}ms"
                )
            return result
        return wrapper
    return decorator
```

Prometheus 모니터링 쿼리:

```
# GraphQL 쿼리 실행 시간 P99가 2초 초과
histogram_quantile(0.99, rate(graphql_execution_duration_seconds_bucket[1m])) > 2

# 동시에 DB CPU 사용률 80% 초과
rate(db_cpu_usage_percent[1m]) > 80

# 요청 수는 평소와 비슷한데 DB 부하만 폭증 (GraphQL 폭탄 특징)
# 요청 수 증가율 < 1.5x, DB CPU 증가율 > 5x
rate(http_requests_total[5m]) / rate(http_requests_total[5m] offset 5m) < 1.5
AND
rate(db_cpu_percent[5m]) / rate(db_cpu_percent[5m] offset 5m) > 5
```

쿼리 복잡도 실시간 로깅:

```java
// GraphQL 실행 전 복잡도 계산 및 로깅
public class ComplexityLoggingInstrumentation extends SimpleInstrumentation {
    @Override
    public InstrumentationContext<ExecutionResult> beginExecution(
            InstrumentationExecutionParameters params) {

        int complexity = calculateComplexity(params.getDocument());
        String query = params.getQuery().substring(0, Math.min(200, params.getQuery().length()));

        log.info("GraphQL query complexity={} userId={} query={}",
            complexity,
            params.getContext().getUserId(),
            query);

        // 복잡도 상위 1% 쿼리 별도 추적
        if (complexity > 5000) {
            log.warn("HIGH_COMPLEXITY_QUERY complexity={} userId={} fullQuery={}",
                complexity, params.getContext().getUserId(), params.getQuery());
            metrics.increment("graphql.high_complexity_queries");
        }

        return super.beginExecution(params);
    }
}
```

**3단계: 검증 — 정말 봇인가 확인**

단순히 복잡한 쿼리를 작성한 개발자와 의도적 공격을 구분합니다.

| 조건 | 실수/개발자 | 의도적 공격 |
|------|-----------|-----------|
| 복잡도 점수 | 1,000~5,000 | 10,000 이상 |
| 동일 쿼리 반복 | 없음 (1~2회) | 수십~수백 회 반복 |
| 요청 간격 | 불규칙 | 자동화된 일정 간격 |
| 쿼리 구조 | 실제 UI 기능에 필요한 수준 | 의도적으로 최대 중첩 |
| 발신 환경 | 브라우저/앱 | curl, python-requests |

```java
public QueryClassification classifyQuery(String userId, GraphQLQuery query, int complexity) {
    // 조건 1: 복잡도 임계값
    if (complexity < 1000) return QueryClassification.NORMAL;

    // 조건 2: 동일 사용자가 동일 구조의 고복잡도 쿼리를 반복하는가
    String queryHash = hashQueryStructure(query); // 변수값 제외, 구조만 해시
    String repeatKey = "query_repeat:" + userId + ":" + queryHash;
    long repeatCount = redis.incr(repeatKey);
    redis.expire(repeatKey, 60); // 1분 윈도우

    if (complexity > 5000 && repeatCount > 3) {
        // 고복잡도 쿼리를 1분에 3회 이상 반복 = 의도적 공격
        return QueryClassification.ATTACK;
    }

    if (complexity > 1000 && repeatCount > 10) {
        // 중간 복잡도 쿼리를 1분에 10회 이상 반복 = 의심
        return QueryClassification.SUSPICIOUS;
    }

    // 복잡도는 높지만 반복이 없으면 = 실수한 개발자
    return QueryClassification.COMPLEX_BUT_LEGITIMATE;
}
```

**4단계: 차단 — 어떻게 막는가**

쿼리 비용 한도 초과 시 즉시 거부와 Persisted Queries를 결합합니다.

```java
// GraphQL Validation Rule — 복잡도 초과 쿼리 즉시 거부
public class MaxComplexityRule implements ValidationRule {
    private static final int MAX_COMPLEXITY = 1000;

    @Override
    public List<ValidationError> validate(ValidationContext context) {
        int complexity = new ComplexityCalculator().calculate(context.getDocument());

        if (complexity > MAX_COMPLEXITY) {
            return List.of(ValidationError.newValidationError()
                .message(String.format(
                    "쿼리 복잡도 %d가 한도 %d를 초과합니다. 쿼리를 분할하세요.",
                    complexity, MAX_COMPLEXITY))
                .build());
        }
        return List.of();
    }
}

// 쿼리 화이트리스트 — Persisted Queries 구현
@Service
public class PersistedQueryService {

    // 사전 등록된 쿼리만 허용 (프로덕션 모드)
    public boolean isAllowedQuery(String queryHash) {
        // Redis Set에 허용된 쿼리 해시 저장
        return redis.sismember("allowed_query_hashes", queryHash);
    }

    // 새 쿼리 등록 (개발팀만 가능 — CI/CD 파이프라인에서 자동 등록)
    public void registerQuery(String query) {
        String hash = sha256(query);
        redis.sadd("allowed_query_hashes", hash);
        log.info("쿼리 등록: hash={} query={}", hash, query.substring(0, 100));
    }

    // 요청 처리
    public ExecutionResult executeQuery(String queryHash, String rawQuery,
                                         Map<String, Object> variables) {
        boolean isProd = isProdEnvironment();

        if (isProd && !isAllowedQuery(queryHash)) {
            // 프로덕션: 미등록 쿼리 거부
            throw new QueryNotAllowedException(
                "임의 쿼리는 허용되지 않습니다. 등록된 쿼리 해시를 사용하세요.");
        }

        // 등록된 쿼리 또는 개발 환경: 복잡도 검증 후 실행
        return graphQL.execute(rawQuery, variables);
    }
}
```

점진적 대응 체계:

```java
public GraphQLResponse handleRequest(String userId, GraphQLQuery query) {
    int complexity = calculateComplexity(query);
    QueryClassification classification = classifyQuery(userId, query, complexity);

    switch (classification) {
        case NORMAL:
            return execute(query);

        case COMPLEX_BUT_LEGITIMATE:
            // 실수한 개발자: 실행하되 경고 메시지 포함
            GraphQLResponse result = execute(query);
            result.addExtension("warning",
                "쿼리 복잡도가 높습니다. 페이지네이션을 줄이는 것을 권장합니다.");
            return result;

        case SUSPICIOUS:
            // 의심: 실행하되 Rate Limit 강화 + 느린 응답
            Thread.sleep(500); // 0.5초 인위적 지연
            return execute(query);

        case ATTACK:
            // 확정: 즉시 거부 + 사용자 차단
            redis.setex("graphql_banned:" + userId, 3600, "complexity_attack");
            throw new RateLimitException("쿼리 복잡도 한도를 반복 초과하여 1시간 차단되었습니다.");

        default:
            return execute(query);
    }
}
```

**5단계: 사후 분석 — 재발 방지**

```python
def post_graphql_bomb_analysis(db, redis_client, attack_time):
    """GraphQL 폭탄 공격 후 분석 및 스키마 강화"""

    # 1. 어떤 쿼리 구조가 사용되었는가
    high_complexity_queries = db.query("""
        SELECT query_hash, query_structure, complexity_score,
               COUNT(*) as execution_count, AVG(execution_time_ms) as avg_time
        FROM graphql_query_logs
        WHERE complexity_score > 5000
        AND created_at >= %s - INTERVAL '1 hour'
        AND created_at <= %s + INTERVAL '1 hour'
        GROUP BY query_hash, query_structure, complexity_score
        ORDER BY complexity_score DESC
        LIMIT 20
    """, (attack_time, attack_time))

    for q in high_complexity_queries:
        print(f"복잡도 {q.complexity_score}: {q.execution_count}회, "
              f"평균 {q.avg_time:.0f}ms — {q.query_structure[:100]}")

    # 2. 공격에 사용된 필드 조합 분석
    # → 특정 타입의 중첩(예: User→Orders→Items→Product→Reviews)이 반복되면
    #   해당 경로에 깊이 제한 추가
    dangerous_paths = extract_dangerous_field_paths(high_complexity_queries)
    for path in dangerous_paths:
        print(f"위험 경로 감지: {path} — 깊이 제한 추가 권장")
        add_field_level_depth_limit(path, max_depth=2)

    # 3. 복잡도 임계값 재보정
    # 정상 쿼리의 P99 복잡도를 기준으로 임계값 설정
    normal_complexities = db.query("""
        SELECT PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY complexity_score)
        FROM graphql_query_logs
        WHERE created_at >= NOW() - INTERVAL '7 days'
        AND execution_time_ms < 100  -- 빠른 쿼리만 = 정상 쿼리
    """)
    p99_complexity = normal_complexities[0][0]
    recommended_limit = int(p99_complexity * 2)  # P99의 2배를 새 한도로

    print(f"정상 쿼리 P99 복잡도: {p99_complexity:.0f}")
    print(f"권장 MAX_COMPLEXITY: {recommended_limit}")

    # 4. Introspection 비활성화 검토
    # 공격자가 스키마를 정찰했는지 확인
    introspection_requests = db.query("""
        SELECT COUNT(*) FROM graphql_query_logs
        WHERE query_structure LIKE '%__schema%'
        AND created_at BETWEEN %s - INTERVAL '24 hours' AND %s
    """, (attack_time, attack_time))

    if introspection_requests[0][0] > 10:
        print("경고: 공격 전 Introspection 정찰 감지 — 프로덕션 Introspection 비활성화 권장")
        # GraphQL 설정에서 introspection=False (프로덕션 환경)
```

---

### 시나리오 F: 크리덴셜 스터핑 — 분당 10만 로그인 시도

**상황**: 다크웹에서 유출된 이메일/비밀번호 조합 1억 건을 로그인 API에 쏟아붓습니다. 봇넷 1만 대에서 분산 실행하므로 IP당 요청 수는 분당 10건.

**왜 위험한가:**
- 성공률 0.1%만 돼도 10만 계정 탈취
- 탈취된 계정으로 포인트 도용, 개인정보 유출
- 로그인 API가 병목 → 정상 사용자도 로그인 불가

**방어 전략:**

| 계층 | 기법 | 효과 |
|------|------|------|
| **1차: 속도** | 로그인 실패 5회 후 30초 딜레이 (IP 무관, 계정 기준) | 봇 속도 100배 감소 |
| **2차: 인증** | 실패 10회 후 CAPTCHA 강제 | 자동화 차단 |
| **3차: 차단** | 실패 30회 후 계정 잠금 + 이메일 알림 | 완전 차단 |
| **4차: 탐지** | 로그인 시도 IP의 지리적 분포 분석 — 전 세계에서 동시 시도면 스터핑 확정 | 사전 차단 |
| **5차: 예방** | Have I Been Pwned API로 유출 비밀번호 사전 차단 | 근본 해결 |

```java
// 크리덴셜 스터핑 다층 방어
public LoginResult login(String email, String password, String ip) {
    String accountKey = "login_fail:" + email;
    String ipKey = "login_fail_ip:" + ip;

    int accountFails = redis.incr(accountKey);
    redis.expire(accountKey, 1800); // 30분 윈도우

    // 계층 1: 속도 제한
    if (accountFails > 5) {
        Thread.sleep(Math.min(accountFails * 1000, 30_000)); // 최대 30초 딜레이
    }

    // 계층 2: CAPTCHA
    if (accountFails > 10) {
        if (!captchaVerified) return LoginResult.CAPTCHA_REQUIRED;
    }

    // 계층 3: 계정 잠금
    if (accountFails > 30) {
        lockAccount(email);
        sendLockNotification(email);
        return LoginResult.ACCOUNT_LOCKED;
    }

    // 계층 4: 글로벌 스터핑 탐지
    int globalFailRate = redis.incr("global_login_fail");
    if (globalFailRate > 10_000) { // 분당 1만 실패 → 스터핑 공격 중
        enableEmergencyCaptchaForAll();
        alertSecurityTeam("Credential stuffing detected: " + globalFailRate + " fails/min");
    }

    // 실제 인증 로직
    return authenticate(email, password);
}
```

---

**1단계: 분석 — 왜 뚫리는가**

크리덴셜 스터핑이 강력한 이유는 공격 도구가 아니라 **데이터**에 있습니다. 다크웹에서 이메일/비밀번호 조합 1억 건을 $50에 구매할 수 있습니다. 사람들이 여러 사이트에서 동일한 비밀번호를 재사용하기 때문에, 다른 사이트에서 유출된 비밀번호가 우리 서비스에서도 통합니다. 성공률은 서비스마다 다르지만 평균 0.1~2%입니다.

IP 기반 Rate Limit이 무력화되는 이유는 봇넷 1만 대를 활용하면 IP당 하루 10건의 요청만으로 전체 1억 건을 며칠 만에 시도할 수 있기 때문입니다. 계정 기반 Rate Limit은 각 계정에 대해 1~2번만 시도하는 방식으로 우회합니다. 공격자는 성공률을 최대화하는 것보다 차단을 피하는 것을 우선합니다.

**2단계: 탐지 — 어떻게 발견하는가**

글로벌 로그인 실패율이 baseline 대비 10배 급증하는 것이 1차 신호입니다. 더 결정적인 신호는 **실패한 이메일의 존재 여부**입니다.

```python
import redis
from collections import Counter

def detect_credential_stuffing(redis_client, db, window_minutes=5):
    """크리덴셜 스터핑 탐지"""

    # 1. 글로벌 실패율 확인
    fail_key = f"login_fail_global:{get_current_minute()}"
    current_fails = int(redis_client.get(fail_key) or 0)

    # 기준선(baseline): 평소 분당 로그인 실패 수
    baseline = float(redis_client.get("login_fail_baseline") or 50)
    surge_ratio = current_fails / max(baseline, 1)

    print(f"현재 실패율: {current_fails}/분 (기준선 대비 {surge_ratio:.1f}x)")

    # 2. 실패한 이메일이 우리 DB에 존재하는지 확인
    # 크리덴셜 스터핑은 외부 유출 DB 기반이므로 존재하지 않는 이메일도 다수 포함
    recent_failed_emails = get_recent_failed_emails(redis_client, window_minutes)
    total_attempts = len(recent_failed_emails)

    if total_attempts == 0:
        return False

    # DB에 존재하지 않는 이메일 비율 계산
    nonexistent_count = sum(
        1 for email in recent_failed_emails
        if not db.user_exists(email)
    )
    nonexistent_ratio = nonexistent_count / total_attempts

    print(f"존재하지 않는 이메일 비율: {nonexistent_ratio:.1%} "
          f"({nonexistent_count}/{total_attempts})")

    # 판정 기준:
    # - 실패율 10배 이상 AND 존재하지 않는 이메일 30% 이상 → 크리덴셜 스터핑 확정
    # - 실패율 10배 이상만 → 브루트포스 (특정 계정 대상)
    if surge_ratio >= 10 and nonexistent_ratio >= 0.30:
        trigger_alert(
            f"크리덴셜 스터핑 공격 확정: 실패율 {surge_ratio:.0f}x 급증, "
            f"미존재 이메일 {nonexistent_ratio:.0%} — 즉시 비상 모드 활성화"
        )
        return True

    if surge_ratio >= 10:
        trigger_alert(
            f"로그인 공격 의심 (브루트포스): 실패율 {surge_ratio:.0f}x 급증"
        )

    return False
```

Prometheus 모니터링 쿼리:

```
# 분당 로그인 실패 수가 기준선 대비 10배 초과
rate(login_failure_total[1m]) > 10 * rate(login_failure_total[1m] offset 1d)

# IP별 로그인 실패 지리적 분포 엔트로피 (높을수록 분산 공격)
# 정상: 엔트로피 낮음 (특정 국가 집중), 스터핑: 엔트로피 높음 (전 세계 분산)
login_failure_geo_entropy > 3.5

# 알람: 위 두 조건 동시 만족
(rate(login_failure_total[1m]) > 10 * rate(login_failure_total[1m] offset 1d))
AND (login_failure_geo_entropy > 3.5)
```

**3단계: 검증 — 정말 봇인가 확인**

존재하지 않는 이메일 비율이 핵심 구분 기준입니다.

| 공격 유형 | 실패율 | 미존재 이메일 비율 | 판정 |
|---------|--------|----------------|------|
| 정상 사용자 오타 | 기준선 이하 | 5~10% | 정상 |
| 특정 계정 브루트포스 | 10배 이상 | 5% 미만 | 브루트포스 |
| **크리덴셜 스터핑** | **10배 이상** | **30~80%** | **확정** |
| 내부 계정 열거 | 보통 | 50~90% | 계정 열거 |

```python
def verify_stuffing_attack(redis_client, db):
    """공격 유형 정밀 분류"""

    recent_fails = get_recent_login_failures(redis_client, minutes=10)

    # 실패 이메일 분석
    emails = [f['email'] for f in recent_fails]
    email_counts = Counter(emails)

    # 동일 이메일이 반복 시도되는 비율 (브루트포스 특징)
    repeated_emails = sum(1 for e, c in email_counts.items() if c > 3)
    repeat_ratio = repeated_emails / max(len(email_counts), 1)

    # DB 미존재 이메일 비율 (스터핑 특징)
    nonexistent = sum(1 for e in email_counts if not db.user_exists(e))
    nonexistent_ratio = nonexistent / max(len(email_counts), 1)

    if nonexistent_ratio > 0.5 and repeat_ratio < 0.1:
        return "CREDENTIAL_STUFFING"   # 다양한 미존재 이메일 + 반복 없음
    elif repeat_ratio > 0.5:
        return "BRUTE_FORCE"           # 동일 계정 반복 시도
    elif nonexistent_ratio > 0.7:
        return "ACCOUNT_ENUMERATION"   # 계정 존재 여부 확인 목적
    else:
        return "UNKNOWN_ATTACK"
```

**4단계: 차단 — 어떻게 막는가**

크리덴셜 스터핑 확정 시 글로벌 비상 모드를 즉시 활성화합니다.

```java
@Service
public class CredentialStuffingDefense {

    // 글로벌 비상 모드 활성화
    public void activateEmergencyMode(String reason) {
        // 1. 모든 로그인에 CAPTCHA 강제 (기존: 실패 10회 이후)
        redis.setex("global_captcha_required", 3600, reason);

        // 2. 로그인 처리 속도 제한 (전체 시스템)
        redis.setex("global_login_throttle", 3600, "300"); // 분당 300건으로 제한

        // 3. 실시간 모니터링 강화
        redis.setex("enhanced_monitoring", 3600, "true");

        log.warn("크리덴셜 스터핑 비상 모드 활성화: {}", reason);
        alertSecurityTeam("EMERGENCY: Credential stuffing — " + reason);
    }

    public LoginResult login(String email, String password,
                              String ip, String captchaToken) {
        // 비상 모드 확인
        boolean emergencyMode = redis.exists("global_captcha_required");

        if (emergencyMode) {
            // 비상 모드: CAPTCHA 무조건 검증
            if (!verifyCaptcha(captchaToken)) {
                return LoginResult.CAPTCHA_REQUIRED;
            }
        }

        // Have I Been Pwned API 연동 — 유출 비밀번호 사전 차단
        if (isPasswordPwned(password)) {
            // 차단하지 않고 경고 후 비밀번호 변경 강제
            // (차단 시 공격자가 어떤 비밀번호가 유효한지 알 수 있음)
            flagAccountForPasswordReset(email);
            return LoginResult.PASSWORD_CHANGE_REQUIRED;
        }

        // 계정별 실패 횟수 확인 (기존 로직)
        String failKey = "login_fail:" + email;
        int fails = Integer.parseInt(redis.get(failKey) != null
            ? redis.get(failKey) : "0");

        if (fails > 5) {
            long delay = Math.min(fails * 1000L, 30_000L);
            Thread.sleep(delay);
        }
        if (fails > 10 && !emergencyMode) {
            if (!verifyCaptcha(captchaToken)) return LoginResult.CAPTCHA_REQUIRED;
        }
        if (fails > 30) {
            lockAccount(email);
            return LoginResult.ACCOUNT_LOCKED;
        }

        return authenticate(email, password);
    }

    // Have I Been Pwned k-Anonymity API 연동
    // 비밀번호 평문을 전송하지 않고 SHA1 해시의 앞 5자리만 전송
    private boolean isPasswordPwned(String password) {
        try {
            String sha1 = sha1Hex(password).toUpperCase();
            String prefix = sha1.substring(0, 5);
            String suffix = sha1.substring(5);

            // HIBP API: 앞 5자리로 조회, 나머지는 로컬에서 매칭
            String response = httpClient.get(
                "https://api.pwnedpasswords.com/range/" + prefix);

            return Arrays.stream(response.split("\n"))
                .anyMatch(line -> line.startsWith(suffix));
        } catch (Exception e) {
            log.warn("HIBP API 조회 실패, 차단 없이 진행: {}", e.getMessage());
            return false; // API 장애 시 로그인 막지 않음
        }
    }
}
```

**5단계: 사후 분석 — 재발 방지**

```python
def post_stuffing_analysis(db, redis_client, attack_start, attack_end):
    """크리덴셜 스터핑 공격 후 분석"""

    # 1. 탈취 성공 계정 수 파악
    # 공격 중 로그인 성공한 계정 중 이후 비정상 행동이 있는 것
    compromised = db.query("""
        SELECT COUNT(DISTINCT l.user_id) as count
        FROM login_logs l
        JOIN user_activity a ON l.user_id = a.user_id
        WHERE l.created_at BETWEEN %s AND %s
        AND l.success = true
        AND l.ip IN (
            -- 공격 IP 목록: 공격 기간 중 다수 실패를 기록한 IP
            SELECT ip FROM login_logs
            WHERE created_at BETWEEN %s AND %s
            AND success = false
            GROUP BY ip HAVING COUNT(*) > 20
        )
    """, (attack_start, attack_end, attack_start, attack_end))

    print(f"탈취 의심 계정: {compromised.count}개")

    # 2. 탈취 성공 계정 일괄 처리
    # 비밀번호 변경 강제 + 세션 만료 + 이메일 알림
    force_password_reset_batch(compromised.user_ids)

    # 3. 공격에 사용된 이메일/비밀번호 패턴 분석
    # 어떤 유출 DB 기반인지 파악 (Have I Been Pwned에서 확인)
    attack_emails_sample = get_attack_email_sample(attack_start, attack_end, limit=1000)
    breach_sources = identify_breach_sources(attack_emails_sample)
    print(f"유출 출처 추정: {breach_sources}")

    # 4. 글로벌 비상 모드 해제 조건 확인
    # 실패율이 기준선의 2배 이하로 30분 이상 유지되면 해제
    current_fail_rate = get_current_fail_rate(redis_client)
    baseline = float(redis_client.get("login_fail_baseline") or 50)
    if current_fail_rate < baseline * 2:
        redis_client.delete("global_captcha_required")
        redis_client.delete("global_login_throttle")
        print("글로벌 비상 모드 해제")

    # 5. 방어 강화 조치
    # 공격에 사용된 IP 대역 블랙리스트에 추가
    attack_ip_ranges = extract_attack_ip_ranges(attack_start, attack_end)
    for cidr in attack_ip_ranges:
        add_to_ip_blacklist(cidr, duration_days=30)

    # 6. 취약 계정(약한 비밀번호) 사전 강제 변경 캠페인
    # 유출 DB에 포함된 이메일 주소로 비밀번호 변경 권고 발송
    vulnerable_users = find_users_with_pwned_passwords(db, batch_size=10000)
    send_password_change_campaign(vulnerable_users)
    print(f"비밀번호 변경 권고 발송: {len(vulnerable_users)}명")
```

---

### 봇 방어 최종 정리 — 비용 vs 효과 매트릭스

| 공격 유형 | 난이도 | 방어 비용 | 핵심 방어 기법 |
|----------|--------|----------|--------------|
| 초보 스크래퍼 (requests/curl) | ⭐ | 무료 | UA 차단 + 쿠키 검증 |
| Headless Chrome 봇 | ⭐⭐ | 무료~$20/월 | JS Challenge + TLS 핑거프린팅 |
| 레지덴셜 프록시 봇 | ⭐⭐⭐ | $100/월 | 디바이스 핑거프린팅 + 행동 분석 |
| CAPTCHA 풀이 서비스 | ⭐⭐⭐ | $50/월 | Proof of Work + reCAPTCHA v3 |
| 계정 탈취 + API 악용 | ⭐⭐⭐⭐ | $500/월 | 집단 행동 탐지 + 이상 세션 감지 |
| Slowloris | ⭐⭐ | 무료 | Nginx 타임아웃 + 연결 수 제한 |
| GraphQL 폭탄 | ⭐⭐ | 무료 | 깊이 제한 + 비용 기반 Rate Limit |
| 대규모 크리덴셜 스터핑 | ⭐⭐⭐⭐ | $200/월 | 다층 로그인 방어 + HIBP |
| 국가급 DDoS (L3/L4) | ⭐⭐⭐⭐⭐ | $3,000+/월 | Cloudflare Enterprise + Anycast |

> **현실**: 봇 방어는 **군비 경쟁**입니다. 100% 차단은 불가능하고, 공격 비용을 수익보다 높게 만드는 것이 목표입니다. 스크래핑 1건당 $0.001의 비용이 들게 만들면, 100만 건 수집에 $1,000이 필요합니다. 우리 데이터의 가치가 $1,000 미만이면 공격자가 포기합니다.

---

## 공격자 관점 — 내가 봇 개발자라면 이렇게 뚫는다

방어를 설계하려면 공격자의 사고방식을 알아야 합니다. 위에서 설명한 모든 방어를 갖춘 서비스를 공격한다고 가정하겠습니다.

### 공격 1단계: 정찰 — 방어 체계 파악

방어를 뚫기 전에 **뭐가 걸려있는지** 먼저 파악합니다.

```python
# 공격자의 정찰 스크립트
import requests, time

target = "https://target.com/api/products"

# 1. Rate Limit 헤더 확인 — 한도와 리셋 시간 노출
r = requests.get(target)
print(r.headers.get('X-RateLimit-Limit'))      # "100" → 분당 100건
print(r.headers.get('X-RateLimit-Remaining'))   # "99"
print(r.headers.get('Retry-After'))             # 429일 때 대기 시간

# 2. 차단 기준 파악 — IP인지 쿠키인지 세션인지
# 쿠키 없이 요청 → 302 리다이렉트? → 쿠키 검증 있음
# 100건 보내고 429 → IP 기반 제한
# VPN 바꿔서 다시 100건 → 통과 → IP 기반 확정

# 3. JS Challenge 유무 — curl로 접근
r = requests.get(target, headers={"User-Agent": "Mozilla/5.0..."})
if "challenge" in r.text or r.status_code == 403:
    print("JS Challenge 감지")

# 4. TLS 핑거프린팅 유무 — python-requests vs Chrome 비교
# 같은 IP에서 requests로 차단, Chrome으로 통과 → JA3 체크 있음
```

> **방어측 교훈**: `X-RateLimit-Limit` 헤더가 한도를 정확히 노출합니다. 공격자는 이 값을 읽고 "분당 99건까지 안전"이라고 판단합니다. **헤더에 정확한 한도를 노출하지 않는 것도 전략**입니다 — `Remaining`만 반환하고 `Limit`는 숨기는 서비스도 있습니다.

**🛡️ 방어자의 답 — 정찰 자체를 무력화하기:**

```java
// 1. Rate Limit 헤더에서 정확한 한도를 숨긴다
// ❌ X-RateLimit-Limit: 100  → 공격자에게 한도 노출
// ✅ X-RateLimit-Remaining: 45 만 반환 (한도는 비공개)
response.setHeader("X-RateLimit-Remaining",
    String.valueOf(remaining));
// Limit 헤더 의도적 생략

// 2. 봇 탐지 시 429가 아니라 200 + 가짜 데이터를 반환
// 공격자가 "차단당했다"는 사실 자체를 모르게 한다
if (threatScore > 80) {
    return ResponseEntity.ok(fakeProductData()); // 가격 ±20% 변조
}

// 3. 허니팟 엔드포인트로 정찰 도구를 역탐지
// /api/v2/internal-products (실제로 없는 API)를 robots.txt에 넣지 않고 방치
// 이 경로를 호출하는 IP = 100% API 스캔 중인 봇
@GetMapping("/api/v2/internal-products")
public ResponseEntity<Void> honeypotApi(HttpServletRequest req) {
    banIp(req.getRemoteAddr(), Duration.ofHours(24));
    return ResponseEntity.ok().build(); // 200을 주되 IP는 차단
}
```

### 공격 2단계: Rate Limit 우회 — 한도 이하로 늦추기

가장 단순한 우회: **그냥 느리게 보냅니다.** 분당 100건 한도면 분당 95건씩 보냅니다. 하루에 136,800건.

```python
# 공격자의 "착한 봇" — Rate Limit 한도 이하로 동작
import time, random

for product_id in range(1, 1_000_000):
    response = session.get(f"https://target.com/api/products/{product_id}")
    # 분당 95건 = 0.63초 간격 + 랜덤 지터
    time.sleep(0.63 + random.uniform(0, 0.3))
```

**왜 이게 문제인가**: Rate Limiter가 "분당 100건 이하 = 정상"으로 판단합니다. IP 1개로 하루 13만 건을 가져갈 수 있습니다.

> **방어측 대응**:
> - **일일 누적 한도** 추가 — 분당 100건이어도 일일 5,000건 초과 시 차단
> - **세션 총 요청 수** 추적 — 한 세션에서 1,000페이지 이상 조회 시 봇 의심
> - **데이터 접근 패턴 분석** — 상품 ID 1부터 순차 접근은 100% 봇

**🛡️ 방어자의 답 — 느린 봇을 잡는 다층 누적 한도:**

```java
// 분당 + 시간당 + 일일 + 주간 4단계 누적 Rate Limit
public class MultiWindowRateLimiter {

    private static final Map<String, int[]> WINDOWS = Map.of(
        "min",   new int[]{60,     100},     // 분당 100
        "hour",  new int[]{3600,   2000},    // 시간당 2,000
        "day",   new int[]{86400,  5000},    // 일일 5,000
        "week",  new int[]{604800, 20000}    // 주간 20,000
    );

    public RateLimitResult check(String userId) {
        for (var entry : WINDOWS.entrySet()) {
            String key = "rl:" + entry.getKey() + ":" + userId;
            int window = entry.getValue()[0];
            int limit = entry.getValue()[1];

            long count = redis.incr(key);
            if (count == 1) redis.expire(key, window);

            if (count > limit) {
                return RateLimitResult.blocked(entry.getKey(), count, limit);
            }
        }
        return RateLimitResult.allowed();
    }
}
// 분당 95건으로 느리게 보내도 → 일일 5,000건에서 걸림
// 일일 4,900건으로 더 느리게 보내도 → 주간 20,000건에서 걸림
```

```java
// 순차 접근 탐지 — 상품 ID가 1,2,3,4... 순서대로 올라가면 봇 확정
public boolean isSequentialAccess(String sessionId) {
    List<Long> recentIds = redis.lrange("access:" + sessionId, 0, 49)
        .stream().map(Long::parseLong).toList();

    if (recentIds.size() < 20) return false;

    // 연속 증가하는 ID 비율 계산
    int sequential = 0;
    for (int i = 1; i < recentIds.size(); i++) {
        if (recentIds.get(i) - recentIds.get(i-1) <= 5) sequential++;
    }
    double ratio = (double) sequential / recentIds.size();
    return ratio > 0.7; // 70% 이상 순차적이면 봇
}
```

### 공격 3단계: 핑거프린트 우회 — 사람처럼 보이기

```python
# 공격자의 Playwright 봇 — 진짜 Chrome을 띄워서 모든 브라우저 체크 통과
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,  # headless=True면 WebGL이 SwiftShader → 탐지됨
        args=[
            '--disable-blink-features=AutomationControlled',  # navigator.webdriver 숨김
            '--window-size=1920,1080',
        ]
    )
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        locale='ko-KR',
        timezone_id='Asia/Seoul',
        geolocation={'latitude': 37.5665, 'longitude': 126.9780},
    )
    page = context.new_page()

    # JS Challenge 통과 — 진짜 Chrome이니까
    page.goto("https://target.com")
    time.sleep(3)  # Cloudflare 체크 대기

    # 사람처럼 마우스 움직이기 — 엔트로피 체크 우회
    page.mouse.move(100, 200)
    page.mouse.move(300, 400, steps=20)  # 20단계로 곡선 이동
    page.mouse.wheel(0, 500)  # 스크롤

    # 쿠키, 세션, 모든 JS 실행 → 방어 체계에 "정상 사용자"로 인식
    data = page.content()
```

**왜 이게 문제인가**: 진짜 Chrome이 실행되므로 JS Challenge, Canvas 핑거프린트, WebGL, TLS(JA3) 전부 정상입니다. `navigator.webdriver`도 패치하면 Selenium 탐지도 안 됩니다.

> **방어측 대응**:
> - **행동 시퀀스 ML** — 마우스 궤적의 베지어 곡선 패턴, 스크롤 가속도, 클릭 위치 분포를 학습. Playwright 가짜 마우스는 직선적이거나 완벽한 곡선이라 사람과 다릅니다.
> - **세션 내 인터랙션 깊이** — 사람은 검색→필터→정렬→상세→뒤로가기→다른 상세. 봇은 상세 페이지만 순차 방문.
> - **시간대 패턴** — 새벽 3시에 8시간 연속 요청하는 "사람"은 없습니다. 사람의 활동 시간대 분포를 프로파일링합니다.

**🛡️ 방어자의 답 — Headless Chrome을 정밀 탐지하는 3중 검증:**

```javascript
// 프론트엔드에서 수집하는 50+ 브라우저 신호
const signals = {
    // 1. Headless 탐지 — navigator 속성
    webdriver: navigator.webdriver,                    // true면 확정 봇
    languages: navigator.languages.length,             // 0이면 봇 (사람은 1+)
    plugins: navigator.plugins.length,                 // Headless는 0개

    // 2. WebGL 렌더러 — SwiftShader면 Headless Chrome
    renderer: (() => {
        const gl = document.createElement('canvas').getContext('webgl');
        const ext = gl?.getExtension('WEBGL_debug_renderer_info');
        return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : 'none';
    })(),
    // 정상: "ANGLE (NVIDIA GeForce RTX 3060...)"
    // Headless: "Google SwiftShader" 또는 "Mesa OffScreen"

    // 3. 마우스 궤적 엔트로피 — 자연스러움 측정
    mouseEntropy: (() => {
        const movements = [];
        document.addEventListener('mousemove', e => {
            movements.push({x: e.clientX, y: e.clientY, t: Date.now()});
        });
        // 5초 후 분석
        setTimeout(() => {
            if (movements.length < 5) return 0; // 마우스 움직임 없음 = 봇
            // 각도 변화의 표준편차 계산
            const angles = [];
            for (let i = 2; i < movements.length; i++) {
                const dx1 = movements[i-1].x - movements[i-2].x;
                const dy1 = movements[i-1].y - movements[i-2].y;
                const dx2 = movements[i].x - movements[i-1].x;
                const dy2 = movements[i].y - movements[i-1].y;
                angles.push(Math.atan2(dy2, dx2) - Math.atan2(dy1, dx1));
            }
            const std = standardDeviation(angles);
            // 사람: std > 0.5 (불규칙 곡선)
            // Playwright fake mouse: std < 0.1 (완벽한 직선/곡선)
            return std;
        }, 5000);
    })(),

    // 4. 타이밍 공격 — Date.now()와 performance.now() 정밀도 차이
    // Headless Chrome은 시간 해상도가 다를 수 있음
    timingPrecision: performance.now() % 1 !== 0,
};

// 서버로 전송 → 봇 점수 계산
fetch('/api/browser-verify', {
    method: 'POST',
    body: JSON.stringify(signals),
});
```

```java
// 서버: 브라우저 신호 종합 판정
public BotVerdict analyzeBrowserSignals(BrowserSignals s) {
    double score = 0;

    if (s.webdriver) score += 100;                          // 확정 봇
    if ("Google SwiftShader".equals(s.renderer)) score += 80; // Headless 강한 징후
    if (s.plugins == 0) score += 30;
    if (s.languages == 0) score += 30;
    if (s.mouseEntropy < 0.1) score += 40;                  // 기계적 마우스
    if (s.mouseEntropy == 0) score += 60;                   // 마우스 없음

    if (score >= 100) return BotVerdict.CONFIRMED;
    if (score >= 50) return BotVerdict.SUSPICIOUS;
    return BotVerdict.HUMAN;
}
```

```java
// 세션 네비게이션 깊이 분석 — 봇은 상세 페이지만 간다
public double getNavigationDepthScore(String sessionId) {
    Map<String, Long> pageCounts = redis.hgetAll("nav:" + sessionId)
        .entrySet().stream()
        .collect(Collectors.toMap(Map.Entry::getKey, e -> Long.parseLong(e.getValue())));

    long total = pageCounts.values().stream().mapToLong(Long::longValue).sum();
    long search = pageCounts.getOrDefault("search", 0L);
    long list = pageCounts.getOrDefault("list", 0L);
    long detail = pageCounts.getOrDefault("detail", 0L);

    if (total < 10) return 0; // 데이터 부족

    // 정상 사용자: search 20% + list 30% + detail 40% + 기타 10%
    // 봇: detail 90%+
    double detailRatio = (double) detail / total;
    double searchRatio = (double) search / total;

    if (detailRatio > 0.85 && searchRatio < 0.05) return 90; // 거의 확정 봇
    if (detailRatio > 0.7) return 50; // 의심
    return 0;
}
```

### 공격 4단계: 스케일 아웃 — 프록시 + 계정 팜

단일 봇의 한계를 넘으려면 **병렬화**합니다.

```python
# 공격자의 병렬 스크래핑 인프라
from concurrent.futures import ThreadPoolExecutor

# Bright Data 레지덴셜 프록시 — 월 $500으로 수백만 IP 사용
proxies = [
    "http://user:pass@brd.superproxy.io:22225",  # 자동 IP 로테이션
]

# 다크웹에서 구매한 계정 1만 개 — 계정당 한도 별도 적용
accounts = load_accounts("stolen_accounts.csv")

def scrape_worker(product_id, account, proxy):
    session = create_session(proxy, account)
    session.cookies.update(account.cookies)
    # 각 계정 + 각 IP로 분당 5건씩만 → Rate Limit 안 걸림
    # 계정 1만 × 분당 5건 = 분당 50,000건
    return session.get(f"https://target.com/api/products/{product_id}")

with ThreadPoolExecutor(max_workers=100) as executor:
    for i, pid in enumerate(product_ids):
        account = accounts[i % len(accounts)]
        executor.submit(scrape_worker, pid, account, proxies[0])
```

**왜 이게 문제인가**: 계정 1만 개 × IP 수백만 개 조합이면 모든 Rate Limit 계층을 통과합니다. 각 계정/IP가 한도 이하니까요.

**🛡️ 방어자의 답 — 계정 팜 + 프록시 조합을 무력화하는 복합 탐지:**

이 단계에서는 단일 기법으로 막을 수 없습니다. **복합 시그널 스코어링**이 필요합니다:

```java
// 복합 위협 스코어 — 단일 지표로 안 걸려도 점수 합산으로 차단
public double calculateThreatScore(RequestContext ctx) {
    double score = 0.0;

    // 1. 세션 내 상세 페이지 비율 (정상: 30~50%, 봇: 90%+)
    double detailRatio = ctx.getDetailPageRatio();
    if (detailRatio > 0.8) score += 30;
    else if (detailRatio > 0.6) score += 15;

    // 2. 요청 간격 엔트로피 (정상: 높음, 봇: 낮음)
    double intervalEntropy = ctx.getRequestIntervalEntropy();
    if (intervalEntropy < 1.0) score += 25;  // 매우 균일
    else if (intervalEntropy < 2.0) score += 10;

    // 3. 세션 지속 시간 (정상: 5~30분, 봇: 수시간)
    if (ctx.getSessionMinutes() > 120) score += 20;

    // 4. 일일 누적 페이지뷰 (정상: 50~200, 봇: 1000+)
    if (ctx.getDailyPageViews() > 1000) score += 25;
    else if (ctx.getDailyPageViews() > 500) score += 10;

    // 5. 동일 디바이스 핑거프린트의 IP 변경 횟수
    if (ctx.getDistinctIpsForFingerprint() > 5) score += 20;

    // 6. 접근 시간대 (새벽 2~6시 연속 활동)
    if (ctx.isNighttimeActivity()) score += 15;

    // 7. Referer 체인 깊이 (정상: 2~4단계, 봇: 0 직접 접근)
    if (ctx.getAvgRefererDepth() < 1) score += 15;

    return score;
    // 50점 이상: CAPTCHA 요구
    // 70점 이상: 속도 제한 (응답 5초 지연)
    // 90점 이상: 차단 + 가짜 데이터 반환
}
```

### 공격 5단계: 최종 병기 — 사람을 고용한다

모든 자동화 탐지를 뚫는 궁극의 방법: **실제 사람이 스크래핑합니다.**

Amazon Mechanical Turk, 크라우드소싱 플랫폼에서 사람을 고용해 수동으로 데이터를 복사하게 합니다. 또는 CAPTCHA 풀이 서비스 + 사람 클릭 서비스를 조합합니다.

**왜 이게 문제인가**: 진짜 사람이므로 행동 분석, 마우스 패턴, 세션 패턴이 모두 "정상"입니다.

**🛡️ 방어자의 최종 답 — 기술 + 법률 + 경제학의 삼각방어:**

기술적 방어만으로는 한계가 있습니다. **공격 비용을 수익보다 높게 만드는 것**이 목표입니다.
>
> | 전략 | 원리 |
> |------|------|
> | **워터마킹** | API 응답에 사용자별 고유 워터마크를 삽입. 유출된 데이터에서 누가 가져갔는지 역추적 |
> | **법적 대응** | Terms of Service에 스크래핑 금지 명시, CFAA(컴퓨터 사기 및 남용법) 기반 소송 — LinkedIn vs hiQ Labs 판례 |
> | **데이터 가치 분산** | 핵심 데이터(가격, 재고)를 이미지로 렌더링하여 OCR 비용 강제 부여 |
> | **허니팟 데이터** | 가짜 상품을 섞어놓고, 해당 데이터가 경쟁사 사이트에 나타나면 스크래핑 증거로 활용 |
> | **접근 비용 부과** | 로그인 + 유료 플랜에서만 상세 데이터 제공. 무료 사용자에겐 제한된 정보만 |

```java
// 워터마킹 — API 응답에 사용자별 고유 마커를 삽입
// 유출된 데이터에서 누가 가져갔는지 역추적
@Component
public class ResponseWatermarkFilter implements Filter {

    @Override
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain)
            throws IOException, ServletException {

        String userId = getCurrentUserId(req);
        ContentCachingResponseWrapper wrapper =
            new ContentCachingResponseWrapper((HttpServletResponse) res);

        chain.doFilter(req, wrapper);

        String body = new String(wrapper.getContentAsByteArray());
        String contentType = wrapper.getContentType();

        if (contentType != null && contentType.contains("json")) {
            // JSON 응답의 숫자 필드에 미세한 변조를 삽입
            // 가격 29,900원 → 29,901원 (사용자마다 다른 끝자리)
            // 이 패턴이 경쟁사 사이트에 나타나면 유출 경로 특정
            String watermarked = injectWatermark(body, userId);
            wrapper.resetBuffer();
            wrapper.getWriter().write(watermarked);
        }
        wrapper.copyBodyToResponse();
    }

    private String injectWatermark(String json, String userId) {
        // 사용자 ID의 해시값 하위 2비트를 가격 끝자리에 반영
        int mark = Math.abs(userId.hashCode()) % 4; // 0~3
        // {"price": 29900} → {"price": 29900 + mark}
        return json.replaceAll(
            "\"price\":\\s*(\\d+)",
            "\"price\": " + "$1".replaceFirst(".$", String.valueOf(mark))
        );
    }
}
```

```python
# 허니팟 상품 — 실제로 존재하지 않는 가짜 상품을 카탈로그에 삽입
# 이 상품이 경쟁사 사이트에 등장하면 스크래핑 증거로 법적 대응 가능
HONEYPOT_PRODUCTS = {
    "product_id": "HP-2024-TRAP-001",
    "name": "프리미엄 블루투스 이어폰 XR-7700",  # 실존하지 않는 상품
    "price": 89900,
    "description": "독점 한정 상품",  # 검색엔진에서 이 문구를 모니터링
}

# 매주 Google Alerts로 허니팟 상품명/설명을 검색
# 다른 사이트에 나타나면 → 스크래핑 증거 확보 → 법적 대응 개시

# 데이터 가치 분산 — 핵심 데이터를 이미지로 렌더링
# 가격, 재고 수량을 텍스트가 아닌 서버 렌더링 이미지로 제공
# OCR 비용: 건당 $0.01 → 100만 상품 = $10,000
# 스크래핑 경제성을 파괴
```

### 공격자 관점 방어 체크리스트

방어 설계 후 이 질문에 "예"라고 답할 수 있어야 합니다:

| # | 질문 | "아니오"면 뚫린다 |
|---|------|-----------------|
| 1 | Rate Limit 한도를 헤더로 정확히 노출하고 있지 않은가? | 공격자가 한도 직전까지 최적화 |
| 2 | 분당 한도뿐 아니라 **일일/주간 누적 한도**가 있는가? | 느린 봇이 하루 13만 건 수집 |
| 3 | IP뿐 아니라 **디바이스 핑거프린트** 기반 추적이 있는가? | 레지덴셜 프록시 우회 |
| 4 | 순차적 ID 접근(1,2,3,4...)을 탐지하는가? | 전수 스크래핑 |
| 5 | 상세 페이지만 접근하는 패턴을 탐지하는가? | 목록 안 거치는 봇 |
| 6 | 새벽 시간대 장시간 연속 활동을 탐지하는가? | 24시간 봇 |
| 7 | 요청 간격의 **엔트로피**(불규칙성)를 측정하는가? | 봇의 균일 간격 |
| 8 | 동일 핑거프린트가 **IP를 자주 바꾸는 것**을 탐지하는가? | 프록시 로테이션 |
| 9 | **복합 스코어**(단일 지표가 아닌 가중 합산)로 판정하는가? | 각 지표를 개별 우회 |
| 10 | 차단 시 **가짜 데이터를 반환**하는 옵션이 있는가? | 봇이 차단 사실을 모르게 |

---

## 보안 고려사항

> **비유**: 놀이공원 회전문은 한 명씩만 통과시킨다. 그런데 100명이 다른 회전문으로 동시에 들어오면? 분산 봇넷은 정확히 이 방식으로 Rate Limiter를 우회한다.

**IP 로테이션 / 분산 봇넷 우회 방어**

단순 IP 기반 Rate Limiting은 봇넷에 무력하다. 1만 개 IP에서 각 IP당 1건씩 보내면 IP 레벨 제한을 피하면서 총 1만 QPS를 발생시킨다. 대응 전략:
- **User-Agent 핑거프린팅**: 헤더 조합이 자동화 도구 패턴과 일치하면 CAPTCHA 요구
- **행동 분석**: 요청 간격이 비정상적으로 일정하면(봇은 정확한 간격) 의심 IP로 분류
- **ASN(자율 시스템) 레벨 제한**: 동일 ISP·클라우드 대역에서 비정상 패턴 감지 시 해당 ASN 전체 스로틀링

**API 키 남용 감지**

API 키가 유출되면 공격자가 무제한 호출할 수 있다. 키별로 일/시간/분 단위 사용량을 모니터링하고, 평소 패턴 대비 3배 이상 급증 시 자동 알림과 일시 정지를 적용한다.

**Redis 장애 시 폴백 전략**

Rate Limiter의 카운터 저장소(Redis)가 죽으면 세 가지 선택지가 있다:
- **전부 허용**: 서비스는 유지되지만 봇 공격에 무방비 — 비공개 API에 적합
- **전부 거부**: 안전하지만 정상 사용자도 차단 — 금융·보안 엔드포인트에 적합
- **로컬 카운터**: 각 서버가 독립적으로 카운터를 유지 (분산 정확도 감소 수용) — 일반적 추천

---

### 꼭 직접 만들어야 하는가? — Build vs Buy

| 선택지 | 장점 | 단점 | 적합한 시점 |
|--------|------|------|-----------|
| Cloudflare Rate Limiting | 설정만으로 적용, L7 레벨, DDoS 방어 연계 | 사용자 티어별 차등 제한 불가, 엔드포인트별 세밀한 정책 어려움 | Phase 1~2 |
| AWS WAF Rate-based Rules | IP당 5분 윈도우, AWS 생태계 통합 | 윈도우 고정, 사용자 식별 기반 제한 불가 | Phase 1~2 |
| Kong/API Gateway 플러그인 | 코드 없이 설정으로 적용, 다양한 알고리즘 지원 | 플러그인 커스텀 한계, 분산 환경 정확도 이슈 | Phase 2~3 |
| 직접 구축 (Redis Lua) | 사용자별/티어별 세밀한 제어, 임의 윈도우·알고리즘 | 구현·운영 부담, Redis 장애 시 대응 로직 필요 | Phase 3~4 |

**실무 판단 기준**: 사용자 티어별 차등 제한, 엔드포인트별 세밀한 정책이 필요할 때 직접 구축으로 전환한다.

> 핵심: Phase 1에서 직접 구축하면 오버 엔지니어링이고, Phase 3에서 SaaS에 의존하면 비용 폭발이다. 현재 MAU에 맞는 선택을 하고, 병목이 실제로 발생할 때 전환한다.

---
## Day 1 → Scale 진화

### Phase 1: MAU 1만 — Nginx rate_limit 모듈 (월 비용 약 $50)

단일 서버에 Nginx `limit_req_zone` 으로 IP당 분당 100건 제한. Redis 없음. 서버 재시작 시 카운터 초기화. 서버 1대라 분산 문제 없음.

```
구성: Nginx 1대, 앱 서버 1대
한계: 서버 추가 즉시 카운터 분산 문제 발생
```

### Phase 2: MAU 10만 — Redis 단일 인스턴스 ($150/월)

앱 서버가 2대 이상이 되는 시점에 Redis를 중앙 카운터 저장소로 도입. Sliding Window Counter + Lua 스크립트로 원자성 보장. Retry-After 헤더 추가.

```
구성: 앱 서버 3대 + Redis 단일 (r6g.large, 16GB)
한계: Redis 단일 장애점, AZ 장애 시 전체 Rate Limiter 다운
```

### Phase 3: MAU 500만 — Redis Cluster + 다층 제한 ($800/월)

Redis Cluster 3샤드 × 복제 계수 2. IP/사용자/엔드포인트 3계층 제한. Circuit Breaker로 Redis 장애 시 로컬 카운터 폴백. CDN에서 알려진 봇 IP 1차 차단.

```
구성: Redis Cluster 6노드 + Cloudflare WAF + Kong API Gateway
추가: 계층별 제한 (IP→API키→사용자→엔드포인트), 자동 IP 차단
```

### Phase 4: MAU 1억 이상 — ML 이상 탐지 + 엣지 분산 ($5,000+/월)

행동 패턴 기반 ML 모델로 봇 탐지. 요청 간격 분포, User-Agent 패턴, 요청 순서를 실시간 분석. 엣지(Cloudflare Workers)에서 국가/ASN 레벨 제한 처리. 중앙 Redis 도달 전 90% 차단.

```
구성: Cloudflare Workers (엣지) + Redis Cluster (코어) + Flink 실시간 이상탐지
추가: ML 스코어 기반 동적 한도 조정, 정상 사용자 자동 화이트리스트
```

---

## 핵심 운영 메트릭 5개

| 메트릭 | 정상 | 경고 | 장애 | 의미 |
|--------|------|------|------|------|
| 차단율 (blocked_ratio) | < 1% | 1~5% | > 5% | 봇 공격 또는 설정 오류 — 정상 트래픽 차단 가능성 |
| 429 응답수/분 | 기준선 ±20% | 3배 급증 | 10배 급증 | 공격 탐지 지표 — 갑작스러운 급증은 봇넷 신호 |
| Redis P99 응답시간 | < 2ms | 2~10ms | > 10ms | Redis 지연 = Rate Limiter 전체 지연으로 직결 |
| 오탐율 (false_positive_rate) | < 0.1% | 0.1~0.5% | > 0.5% | 정상 사용자 차단 비율 — 높으면 매출 직결 피해 |
| 로컬 카운터 폴백 비율 | 0% | > 0% 감지 즉시 | — | Redis 장애 신호 — 분산 정확도 저하 시작 |

---

## 실제 장애 사례

### 사례 1: Cloudflare 전역 장애 (2022년 6월)

**상황**: Cloudflare가 네트워크 설정 오류로 19개 주요 데이터센터를 동시에 내렸다. Cloudflare의 Rate Limiting 서비스에 의존하던 수천 개 서비스에서 트래픽이 원본 서버로 직접 쏟아졌다. 동시에 Cloudflare DDoS 방어가 사라지며 봇 트래픽도 함께 원본 서버로 유입됐다.

**원인**: 네트워크 접두사 광고(BGP) 오설정으로 Cloudflare 내부 라우팅이 블랙홀에 빠졌다. Rate Limiting은 Cloudflare 엣지에서 처리했으므로 엣지가 죽자 제한 자체가 무력화됐다.

**해결**: 설정 롤백으로 34분 만에 복구. 그러나 이 34분 동안 Cloudflare에 완전 의존한 서비스들은 DB 커넥션 고갈 → 서비스 다운 연쇄 발생.

**교훈**: 엣지 Rate Limiting은 1차 방어로만 활용하고, 애플리케이션 계층에 Redis 기반 2차 Rate Limiting을 반드시 병행해야 한다. CDN 장애 시 원본 서버가 직접 감당할 수 있는 최대 QPS 이상의 트래픽이 쏟아질 수 있으므로 Circuit Breaker와 로드쉐딩(load shedding)을 함께 설계해야 한다.

---

### 사례 2: GitHub API Rate Limit 우회 사고 (2021년)

**상황**: GitHub은 인증된 요청에 시간당 5,000건, 비인증 요청에 시간당 60건 제한을 적용한다. 2021년 특정 오픈소스 도구가 GitHub Actions 환경에서 수천 개의 병렬 워크플로를 실행하며 공유 IP(GitHub Actions runner 풀)의 비인증 한도 60건을 순식간에 소진했다. 이후 같은 IP를 쓰는 **다른 사용자들**도 429를 받았다.

**원인**: 여러 사용자가 같은 NAT IP를 공유하는 환경에서 IP 기반 Rate Limiting은 결백한 사용자까지 연좌제로 차단한다. 특히 클라우드 함수(AWS Lambda, GitHub Actions)는 수천 개의 인스턴스가 소수의 NAT IP를 공유한다.

**해결**: 해당 도구가 GitHub Token을 명시적으로 주입하도록 수정. 인증 요청으로 전환해 사용자별 별도 한도 적용. GitHub도 이후 GitHub Actions IP 범위에 대한 한도 정책을 조정했다.

**교훈**: IP 기반 Rate Limiting 단독으로는 클라우드/NAT 환경에서 공정성이 깨진다. 사용자 ID > API 키 > IP 순서의 우선순위로 식별자를 선택해야 한다. IP는 최후 수단이며, "이 IP의 모든 사용자"를 차단하는 부작용을 항상 인식하고 설계해야 한다.

---

## 핵심 설계 결정 요약

| 결정 | 선택 | 이유 |
|------|------|------|
| 알고리즘 | 슬라이딩 윈도우 카운터 | 정확도 + 메모리 효율 균형 |
| 저장소 | Redis Cluster | 분산 환경 원자적 카운터 |
| 원자성 | Lua 스크립트 | GET→비교→INCR 사이 Race Condition 방지 |
| 식별자 | API키 > 사용자ID > IP | 정밀도 높은 쪽 우선 |
| 응답 헤더 | X-RateLimit-* 표준 | 클라이언트가 재시도 타이밍 알 수 있게 |
| DDoS | 다층 방어 (CDN → WAF → 앱) | 단일 계층 우회 방지 |

---

## 실무에서 자주 하는 실수

1. **분산 환경에서 로컬 카운터 사용** — 각 서버가 자체 메모리에 카운터를 유지하면 서버 3대 기준 실제 한도의 3배 요청이 허용된다. Redis Cluster 기반 중앙 카운터가 필수다.

2. **사용자 식별 기준 미정의** — API 키, 사용자 ID, IP 중 어떤 기준으로 제한할지 모호하게 설계하면 우회가 쉬워진다. 인증된 요청은 API 키, 비인증은 IP 기준으로 다층 적용해야 한다.

3. **Rate Limit 응답 헤더 누락** — 클라이언트가 자신의 남은 쿼터를 모르면 무작정 재시도해 상황을 악화시킨다. `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After` 헤더를 표준으로 반환해야 한다.

4. **알고리즘 선택 없이 단순 카운터만 적용** — Fixed Window는 경계 시점에 2배 버스트가 허용된다. 슬라이딩 윈도우나 토큰 버킷을 서비스 특성에 맞게 선택해야 한다.

5. **Rate Limiter 자체 장애 시 처리 미정의** — Redis가 다운되면 모든 요청을 차단할지 허용할지 결정하지 않으면 서비스 중단이 발생한다. Fail-open(허용)이 일반적이지만 보안 민감 API는 Fail-closed(차단)가 맞다.
