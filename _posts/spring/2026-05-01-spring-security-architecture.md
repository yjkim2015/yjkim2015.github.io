---
title: "Spring Security 아키텍처"
categories:
- SPRING
toc: true
toc_sticky: true
toc_label: 목차
---

JWT 토큰이 없는 요청이 `/api/admin`에 들어왔는데 그냥 통과됐다. 필터 순서가 잘못됐거나 필터 자체가 누락된 것이다. Spring Security 아키텍처를 모르면 어디서 막혀야 하는지조차 알 수 없다.

> **비유로 먼저 이해하기**: Spring Security는 공항 보안검색대와 같다. 탑승구(Controller)에 도달하려면 발권 확인(인증 필터), 수하물 검사(권한 필터), 위험물 탐지(CSRF 필터) 등 여러 단계를 순서대로 통과해야 한다. 한 단계라도 실패하면 그 자리에서 차단된다.

---

## 1. SecurityFilterChain 구조

Spring Security는 **Servlet Filter 체인**으로 구현된다. `DelegatingFilterProxy`가 Servlet 컨테이너와 Spring Security를 연결한다.

<div class="mermaid">
graph TD
    A[HTTP 요청] --> B[Servlet Container]
    B --> C["DelegatingFilterProxy<br>Servlet Filter, Spring Bean이 아닌 척 동작"]
    C -->|"Spring ApplicationContext에서<br>FilterChainProxy Bean을 찾아 위임"| D["FilterChainProxy<br>Spring Bean, SecurityFilterChain 목록 관리"]
    D -->|"요청 URL에 맞는 SecurityFilterChain 선택"| E["SecurityFilterChain (보안 필터 목록)<br>1. DisableEncodeUrlFilter<br>2. WebAsyncManagerIntegrationFilter<br>3. SecurityContextHolderFilter<br>4. HeaderWriterFilter<br>5. CorsFilter<br>6. CsrfFilter<br>7. LogoutFilter<br>8. UsernamePasswordAuthenticationFilter<br>9. DefaultLoginPageGeneratingFilter<br>10. BasicAuthenticationFilter<br>11. RequestCacheAwareFilter<br>12. SecurityContextHolderAwareRequestFilter<br>13. AnonymousAuthenticationFilter<br>14. SessionManagementFilter<br>15. ExceptionTranslationFilter<br>16. AuthorizationFilter"]
    E --> F[DispatcherServlet]
    F --> G[Controller]
</div>

### SecurityFilterChain 설정

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            // CSRF 설정
            .csrf(csrf -> csrf.disable())  // REST API는 보통 비활성화

            // 세션 설정
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))  // JWT 사용 시

            // 인가 규칙
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/public/**").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .requestMatchers(HttpMethod.GET, "/api/orders").hasAnyRole("USER", "ADMIN")
                .anyRequest().authenticated()
            )

            // JWT 필터 추가
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    // 여러 SecurityFilterChain 설정 가능 (URL 패턴별로)
    @Bean
    @Order(1)
    public SecurityFilterChain apiFilterChain(HttpSecurity http) throws Exception {
        http
            .securityMatcher("/api/**")  // /api/** 에만 적용
            .authorizeHttpRequests(auth -> auth.anyRequest().authenticated())
            .httpBasic(Customizer.withDefaults());
        return http.build();
    }

    @Bean
    @Order(2)
    public SecurityFilterChain webFilterChain(HttpSecurity http) throws Exception {
        http
            .securityMatcher("/**")     // 나머지에 적용
            .authorizeHttpRequests(auth -> auth.anyRequest().permitAll());
        return http.build();
    }
}
```

---

## 2. 인증(Authentication) vs 인가(Authorization)

| 구분 | Authentication (인증) | Authorization (인가) |
|------|----------------------|---------------------|
| 질문 | "당신이 누구인가?" | "당신이 이것을 할 수 있는가?" |
| 처리 시점 | 먼저 | 인증 후 |
| 실패 시 | 401 Unauthorized | 403 Forbidden |
| 담당 컴포넌트 | AuthenticationManager | AuthorizationManager |
| Spring Security | UsernamePasswordAuthenticationFilter 등 | AuthorizationFilter |

---

## 3. 주요 필터 상세 동작

### UsernamePasswordAuthenticationFilter

폼 로그인 처리. `POST /login` 요청을 가로챈다.

<div class="mermaid">
sequenceDiagram
    participant C as 클라이언트
    participant F as UsernamePasswordAuthenticationFilter
    participant AM as AuthenticationManager
    participant AP as DaoAuthenticationProvider
    participant UDS as UserDetailsService
    participant SC as SecurityContextHolder
    participant SH as AuthenticationSuccessHandler

    C->>F: POST /login (username, password)
    F->>F: 1. UsernamePasswordAuthenticationToken 생성 (미인증)
    F->>AM: 2. authenticate()
    AM->>AP: 적절한 AuthenticationProvider 탐색
    AP->>UDS: 3. loadUserByUsername(username)
    UDS-->>AP: UserDetails 반환
    AP->>AP: 4. 비밀번호 검증 (PasswordEncoder)
    AP-->>AM: 5. 인증 성공 → 완전한 Authentication 객체 반환
    AM-->>F: Authentication 반환
    F->>SC: 6. SecurityContext에 Authentication 저장
    F->>SH: 7. 성공 응답 (리다이렉트 or JSON)
    SH-->>C: 응답
</div>

```java
// 커스텀 설정
@Bean
public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    http.formLogin(form -> form
        .loginPage("/login")                    // 커스텀 로그인 페이지
        .loginProcessingUrl("/login")           // 로그인 처리 URL (POST)
        .defaultSuccessUrl("/dashboard")        // 성공 시 이동
        .failureUrl("/login?error=true")        // 실패 시 이동
        .usernameParameter("email")             // 파라미터 이름 변경
        .passwordParameter("passwd")
        .successHandler(customSuccessHandler)   // 커스텀 핸들러
        .failureHandler(customFailureHandler)
    );
    return http.build();
}
```

### BasicAuthenticationFilter

HTTP Basic 인증 처리. `Authorization: Basic base64(username:password)` 헤더.

```java
http.httpBasic(basic -> basic
    .realmName("My API")
    .authenticationEntryPoint(customEntryPoint)
);
```

### AnonymousAuthenticationFilter

인증되지 않은 요청에 익명 Authentication을 생성해 SecurityContext에 저장한다.

```java
// 필터 체인 끝까지 인증이 안 되면 이 필터가 익명 Authentication 생성
// SecurityContext에 항상 Authentication이 있음을 보장
Authentication anonymous = new AnonymousAuthenticationToken(
    "anonymousUser",
    "anonymousUser",
    List.of(new SimpleGrantedAuthority("ROLE_ANONYMOUS"))
);
```

### ExceptionTranslationFilter

보안 예외를 HTTP 응답으로 변환한다.

<div class="mermaid">
graph TD
    A[AuthorizationFilter에서 예외 발생] --> B[ExceptionTranslationFilter]
    B --> C{예외 종류}
    C -->|AccessDeniedException 인가 실패| D{사용자 유형}
    D -->|익명 사용자| E["AuthenticationEntryPoint (401)"]
    D -->|인증된 사용자| F["AccessDeniedHandler (403)"]
    C -->|AuthenticationException 인증 실패| G["AuthenticationEntryPoint<br>LoginUrlAuthenticationEntryPoint: 로그인 페이지 리다이렉트<br>HttpStatusEntryPoint: 401 반환 REST API<br>BearerTokenAuthenticationEntryPoint: WWW-Authenticate 헤더"]
</div>

---

## 4. AuthenticationManager와 AuthenticationProvider

### 구조

<div class="mermaid">
graph TD
    AM[AuthenticationManager] -->|구현체| PM[ProviderManager]
    PM -->|등록된 AuthenticationProvider 순회| AP1["DaoAuthenticationProvider<br>(username/password)"]
    PM --> AP2["JwtAuthenticationProvider<br>(JWT 커스텀)"]
    PM --> AP3["OAuth2LoginAuthenticationProvider<br>(OAuth2)"]
    PM --> AP4[RememberMeAuthenticationProvider]
    PM --> AP5[AnonymousAuthenticationProvider]
</div>

```java
// DaoAuthenticationProvider 동작
public class DaoAuthenticationProvider extends AbstractUserDetailsAuthenticationProvider {

    protected UserDetails retrieveUser(String username, UsernamePasswordAuthenticationToken auth) {
        // UserDetailsService에서 사용자 조회
        UserDetails user = userDetailsService.loadUserByUsername(username);
        if (user == null) throw new UsernameNotFoundException(username);
        return user;
    }

    protected void additionalAuthenticationChecks(UserDetails userDetails,
                                                   UsernamePasswordAuthenticationToken auth) {
        // 비밀번호 검증
        if (!passwordEncoder.matches(
            auth.getCredentials().toString(),
            userDetails.getPassword())) {
            throw new BadCredentialsException("비밀번호 불일치");
        }
    }
}
```

### ProviderManager 위임 구조

```java
// 부모 ProviderManager로 위임 가능 (계층 구조)
@Bean
public AuthenticationManager authenticationManager() {
    DaoAuthenticationProvider provider = new DaoAuthenticationProvider();
    provider.setUserDetailsService(userDetailsService);
    provider.setPasswordEncoder(passwordEncoder());

    return new ProviderManager(List.of(provider));
}
```

---

## 5. UserDetailsService

```java
public interface UserDetailsService {
    UserDetails loadUserByUsername(String username) throws UsernameNotFoundException;
}

public interface UserDetails extends Serializable {
    Collection<? extends GrantedAuthority> getAuthorities(); // 권한 목록
    String getPassword();
    String getUsername();
    boolean isAccountNonExpired();
    boolean isAccountNonLocked();
    boolean isCredentialsNonExpired();
    boolean isEnabled();
}
```

### 구현 예제

```java
@Service
public class CustomUserDetailsService implements UserDetailsService {

    @Autowired
    private UserRepository userRepository;

    @Override
    public UserDetails loadUserByUsername(String username)
            throws UsernameNotFoundException {
        User user = userRepository.findByEmail(username)
                .orElseThrow(() -> new UsernameNotFoundException("사용자 없음: " + username));

        return org.springframework.security.core.userdetails.User.builder()
                .username(user.getEmail())
                .password(user.getPassword())  // 이미 BCrypt 인코딩된 비밀번호
                .roles(user.getRole().name())  // ROLE_ 접두사 자동 추가
                .accountExpired(!user.isActive())
                .accountLocked(user.isLocked())
                .build();
    }
}
```

### 커스텀 UserDetails

```java
// 추가 정보를 담은 커스텀 UserDetails
public class CustomUserDetails implements UserDetails {
    private final User user;  // 도메인 User 객체

    public CustomUserDetails(User user) {
        this.user = user;
    }

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return user.getRoles().stream()
                .map(role -> new SimpleGrantedAuthority("ROLE_" + role.name()))
                .collect(Collectors.toList());
    }

    @Override
    public String getPassword() { return user.getPassword(); }

    @Override
    public String getUsername() { return user.getEmail(); }

    // 도메인 객체 접근
    public Long getId() { return user.getId(); }
    public String getName() { return user.getName(); }

    // ... isAccountNonExpired, isEnabled 등
}
```

---

## 6. SecurityContext와 ThreadLocal

### SecurityContextHolder

<div class="mermaid">
graph TD
    SCH["SecurityContextHolder<br>기본 전략: ThreadLocalSecurityContextHolderStrategy"] --> SC["SecurityContext<br>ThreadLocal로 Thread마다 독립"]
    SC --> AUTH[Authentication]
    AUTH --> P["Principal<br>UserDetails 또는 사용자 식별자"]
    AUTH --> CR["Credentials<br>비밀번호, 인증 후 보통 null로 초기화"]
    AUTH --> AU["Authorities<br>권한 목록"]
    AUTH --> IA["isAuthenticated<br>인증 여부"]
</div>

```java
// SecurityContext에서 현재 사용자 꺼내기
Authentication auth = SecurityContextHolder.getContext().getAuthentication();
String username = auth.getName();
Collection<? extends GrantedAuthority> authorities = auth.getAuthorities();

// UserDetails 캐스팅
UserDetails userDetails = (UserDetails) auth.getPrincipal();

// 커스텀 UserDetails 캐스팅
CustomUserDetails customUser = (CustomUserDetails) auth.getPrincipal();
Long userId = customUser.getId();

// Spring MVC에서 자동 주입
@GetMapping("/mypage")
public String myPage(@AuthenticationPrincipal CustomUserDetails user) {
    Long userId = user.getId();
    return "mypage";
}
```

### ThreadLocal 기반 동작

<div class="mermaid">
graph TD
    subgraph "요청 1 - Thread-1"
        A1[FilterChainProxy] -->|SecurityContext 생성| B1[ThreadLocal 저장]
        B1 --> C1["Controller → SecurityContextHolder.getContext()<br>→ Thread-1의 SecurityContext"]
    end
    subgraph "요청 2 - Thread-2"
        A2[FilterChainProxy] -->|SecurityContext 생성| B2[ThreadLocal 저장]
        B2 --> C2["Controller → SecurityContextHolder.getContext()<br>→ Thread-2의 SecurityContext"]
    end
    C1 --- NOTE["각 Thread가 독립적인 SecurityContext를 가짐 → Thread 안전"]
    C2 --- NOTE
</div>

**주의**: 비동기 처리 시 SecurityContext가 전파되지 않을 수 있다.

```java
// @Async 메서드에서 SecurityContext 전파
@Configuration
@EnableAsync
public class AsyncConfig implements AsyncConfigurer {
    @Override
    public Executor getAsyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.initialize();
        // SecurityContext를 자식 Thread에 전파
        return new DelegatingSecurityContextAsyncTaskExecutor(executor);
    }
}
```

### SecurityContextHolderStrategy 변경

```java
// 비동기/반응형 환경에서 전략 변경
// ThreadLocal 대신 InheritableThreadLocal 사용
SecurityContextHolder.setStrategyName(
    SecurityContextHolder.MODE_INHERITABLETHREADLOCAL
);
```

---

## 7. CSRF 동작 원리

CSRF(Cross-Site Request Forgery): 인증된 사용자의 브라우저를 이용해 악의적 요청을 보내는 공격.

```
[CSRF 공격 시나리오]
1. 사용자가 bank.com에 로그인 (세션 쿠키 발급)
2. 악의적 사이트(evil.com) 방문
3. evil.com의 자동 폼 제출:
   POST bank.com/transfer (amount=10000, to=hacker)
   → 브라우저가 자동으로 bank.com 세션 쿠키 포함
4. bank.com은 유효한 세션으로 인식 → 이체 실행!
```

### Spring Security CSRF 방어

<div class="mermaid">
sequenceDiagram
    participant C as 클라이언트 (브라우저)
    participant CF as CsrfFilter
    participant S as 서버

    C->>CF: GET /form-page
    CF->>CF: CsrfToken 생성 (랜덤 값)<br>세션 또는 쿠키에 저장
    CF-->>C: 폼 응답 (hidden input _csrf=토큰값 포함)

    C->>CF: POST /submit (데이터 + _csrf=토큰값)
    CF->>CF: 요청의 _csrf 값과 서버 저장값 비교
    alt 불일치
        CF-->>C: 403 Forbidden
    else 일치
        CF->>S: 다음 필터로 전달
        S-->>C: 정상 응답
    end
</div>

```java
// Thymeleaf: 자동으로 CSRF 토큰 포함
<form th:action="@{/submit}" method="post">
    <!-- Thymeleaf가 자동으로 hidden input 추가 -->
</form>

// JavaScript (Axios 등): 헤더로 전송
axios.defaults.headers.common['X-CSRF-TOKEN'] = document.querySelector('meta[name="_csrf"]').content;
```

### REST API에서 CSRF 비활성화

```java
http.csrf(csrf -> csrf.disable());
// JWT + Stateless 세션 사용 시 CSRF 불필요
// 쿠키 기반 세션이 없으면 CSRF 공격 불가
```

---

## 8. CORS 동작 원리

CORS(Cross-Origin Resource Sharing): 브라우저의 동일 출처 정책(SOP)을 제어하는 메커니즘.

```
[SOP 위반 예시]
프론트엔드: http://localhost:3000
백엔드 API: http://localhost:8080

브라우저: "출처가 다르다! 요청 차단!"
```

### Preflight 요청

브라우저가 실제 요청 전에 OPTIONS 메서드로 서버에 허용 여부를 물어본다.

```
OPTIONS /api/orders
Origin: http://localhost:3000
Access-Control-Request-Method: POST
Access-Control-Request-Headers: Content-Type, Authorization
    |
    v
[서버 응답]
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 3600  ← 이 시간 동안 Preflight 캐시
    |
    v
[실제 요청 전송]
POST /api/orders
```

### Spring Security CORS 설정

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.cors(cors -> cors.configurationSource(corsConfigurationSource()));
        // ...
        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration config = new CorsConfiguration();

        config.setAllowedOrigins(List.of(
            "http://localhost:3000",
            "https://myapp.com"
        ));
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"));
        config.setAllowedHeaders(List.of("*"));
        config.setAllowCredentials(true);  // 쿠키/인증 헤더 허용
        config.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", config);
        return source;
    }
}
```

```java
// 컨트롤러 레벨 CORS
@RestController
@CrossOrigin(origins = "http://localhost:3000")
public class OrderController { ... }

// 메서드 레벨
@CrossOrigin(origins = "*", maxAge = 3600)
@GetMapping("/public/orders")
public List<Order> publicOrders() { ... }
```

---

## 9. JWT 인증 구현 예제

JWT는 세션 없이 상태를 토큰에 담는 방식이다.

```java
// JWT 인증 필터
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @Autowired
    private UserDetailsService userDetailsService;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                     HttpServletResponse response,
                                     FilterChain filterChain)
            throws ServletException, IOException {

        // 1. 헤더에서 토큰 추출
        String token = resolveToken(request);

        // 2. 토큰 유효성 검증
        if (token != null && jwtTokenProvider.validateToken(token)) {
            // 3. 토큰에서 사용자 정보 추출
            String username = jwtTokenProvider.getUsername(token);

            // 4. UserDetails 로드
            UserDetails userDetails = userDetailsService.loadUserByUsername(username);

            // 5. Authentication 객체 생성
            UsernamePasswordAuthenticationToken auth =
                new UsernamePasswordAuthenticationToken(
                    userDetails,
                    null,
                    userDetails.getAuthorities()
                );
            auth.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));

            // 6. SecurityContext에 저장
            SecurityContextHolder.getContext().setAuthentication(auth);
        }

        filterChain.doFilter(request, response);
    }

    private String resolveToken(HttpServletRequest request) {
        String bearer = request.getHeader("Authorization");
        if (StringUtils.hasText(bearer) && bearer.startsWith("Bearer ")) {
            return bearer.substring(7);
        }
        return null;
    }
}
```

---

## 정리

| 구성요소 | 역할 |
|---------|------|
| DelegatingFilterProxy | Servlet Container ↔ Spring 연결 |
| FilterChainProxy | SecurityFilterChain 목록 관리 |
| SecurityFilterChain | 보안 필터 체인 |
| UsernamePasswordAuthenticationFilter | 폼 로그인 처리 |
| AuthenticationManager (ProviderManager) | 인증 위임 |
| AuthenticationProvider | 실제 인증 처리 |
| UserDetailsService | 사용자 정보 로드 |
| SecurityContextHolder | ThreadLocal로 Authentication 저장 |
| ExceptionTranslationFilter | 보안 예외 → HTTP 응답 변환 |
| AuthorizationFilter | 인가 처리 |
| CSRF | 동일 출처 위조 방어 (세션 기반에서 필요) |
| CORS | 교차 출처 요청 허용 정책 |
