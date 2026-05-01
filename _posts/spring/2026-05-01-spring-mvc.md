---
title: "Spring MVC 동작 원리"
categories:
- SPRING
toc: true
toc_sticky: true
toc_label: 목차
---

## 1. DispatcherServlet 구조

Spring MVC의 핵심은 **DispatcherServlet**이다. 모든 HTTP 요청을 받아 적절한 핸들러에 위임하는 **Front Controller** 패턴을 구현한다.

<div class="mermaid">
graph TD
    Client[클라이언트] -->|HTTP 요청| DS["DispatcherServlet<br>모든 요청의 단일 진입점"]
    DS -->|위임| OC[OrderController]
    DS -->|위임| UC[UserController]
    DS -->|위임| PC[ProductController]
</div>

### DispatcherServlet 초기화

<div class="mermaid">
graph TD
    A([Spring Boot 시작]) --> B[ServletWebServerApplicationContext 생성]
    B --> C[DispatcherServlet 등록 자동]
    C --> D[DispatcherServlet.init()]
    D --> E[WebApplicationContext 연결]
    E --> F["전략 컴포넌트 초기화<br>HandlerMapping 목록<br>HandlerAdapter 목록<br>ViewResolver 목록<br>HandlerExceptionResolver 목록"]
</div>

---

## 2. 요청 처리 흐름

<div class="mermaid">
sequenceDiagram
    participant C as 클라이언트
    participant DS as DispatcherServlet
    participant HM as HandlerMapping
    participant HA as HandlerAdapter
    participant IC as Interceptor Chain
    participant CM as Controller Method
    participant VR as ViewResolver
    participant V as View

    C->>DS: HTTP 요청 GET /orders/1
    DS->>HM: 1. getHandler()
    HM-->>DS: HandlerExecutionChain 반환 (Handler + Interceptor 목록)
    DS->>HA: 2. getHandlerAdapter()
    DS->>IC: 3. Interceptor.preHandle()
    DS->>CM: 4. handle() - 실제 컨트롤러 실행
    Note over CM: ArgumentResolver로 파라미터 바인딩<br>비즈니스 로직 실행<br>ReturnValueHandler로 반환값 처리
    CM-->>DS: ModelAndView 반환
    DS->>IC: 5. Interceptor.postHandle()
    DS->>VR: 6. processDispatchResult()
    Note over VR: 뷰 이름 → View 객체 변환<br>@ResponseBody면 MessageConverter 사용
    VR->>V: 7. View.render()
    Note over V: 템플릿 렌더링 (Thymeleaf, JSP 등)
    DS->>IC: 8. Interceptor.afterCompletion()
    DS-->>C: HTTP 응답
</div>

### HandlerMapping

요청 URL을 어떤 핸들러(컨트롤러 메서드)가 처리할지 결정한다.

```java
// RequestMappingHandlerMapping이 처리하는 매핑
@RestController
@RequestMapping("/orders")
public class OrderController {

    @GetMapping("/{id}")         // GET /orders/{id}
    @PostMapping                 // POST /orders
    @PutMapping("/{id}")         // PUT /orders/{id}
    @DeleteMapping("/{id}")      // DELETE /orders/{id}
    @PatchMapping("/{id}")       // PATCH /orders/{id}

    // 조건부 매핑
    @GetMapping(value = "/search",
                params = "type=recent",        // 쿼리 파라미터 조건
                headers = "X-API-Version=2",   // 헤더 조건
                consumes = "application/json", // Content-Type 조건
                produces = "application/json") // Accept 조건
    public List<Order> searchOrders() { ... }
}
```

### HandlerAdapter

다양한 형태의 핸들러(컨트롤러)를 일관된 방식으로 실행할 수 있도록 어댑터 패턴을 적용한다.

```java
// RequestMappingHandlerAdapter가 처리하는 흐름
public class RequestMappingHandlerAdapter {

    public ModelAndView handle(HttpServletRequest request,
                               HttpServletResponse response,
                               Object handler) {
        HandlerMethod handlerMethod = (HandlerMethod) handler;

        // 1. ArgumentResolver로 파라미터 준비
        Object[] args = resolveArguments(handlerMethod, request);

        // 2. 메서드 실행
        Object returnValue = handlerMethod.invoke(args);

        // 3. ReturnValueHandler로 반환값 처리
        handleReturnValue(returnValue, handlerMethod, response);
    }
}
```

---

## 3. @Controller vs @RestController

```java
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Documented
@Controller
@ResponseBody  // 이것이 유일한 차이
public @interface RestController { }
```

`@RestController = @Controller + @ResponseBody`

### @Controller (View 반환)

```java
@Controller
public class PageController {

    @GetMapping("/orders")
    public String orders(Model model) {
        model.addAttribute("orders", orderService.findAll());
        return "orders/list";  // ViewResolver → templates/orders/list.html
    }

    @GetMapping("/orders/{id}")
    public String orderDetail(@PathVariable Long id, Model model) {
        model.addAttribute("order", orderService.findById(id));
        return "orders/detail";
    }
}
```

### @RestController (데이터 반환)

```java
@RestController
@RequestMapping("/api/orders")
public class OrderApiController {

    @GetMapping("/{id}")
    public OrderResponse getOrder(@PathVariable Long id) {
        return orderService.findById(id);  // JSON으로 직렬화
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public OrderResponse createOrder(@RequestBody @Valid OrderRequest request) {
        return orderService.create(request);
    }
}
```

### @ResponseBody 동작

<div class="mermaid">
graph TD
    A["컨트롤러 반환값 (OrderResponse 객체)"] --> B["HttpMessageConverter<br>MappingJackson2HttpMessageConverter: Java 객체 → JSON<br>StringHttpMessageConverter: String → text/plain<br>ByteArrayHttpMessageConverter: byte[] → application/octet-stream"]
    B --> C["HTTP Response Body (JSON 문자열)"]
</div>

Accept 헤더와 Content-Type을 보고 적절한 MessageConverter를 선택한다.

---

## 4. ArgumentResolver와 ReturnValueHandler

### ArgumentResolver (HandlerMethodArgumentResolver)

컨트롤러 메서드의 파라미터를 어떻게 만들지 결정한다.

```java
// Spring이 기본 제공하는 ArgumentResolver가 처리하는 파라미터들
@GetMapping("/orders")
public String getOrders(
    @PathVariable Long id,             // PathVariableMethodArgumentResolver
    @RequestParam String status,       // RequestParamMethodArgumentResolver
    @RequestBody OrderRequest request, // RequestResponseBodyMethodProcessor
    @ModelAttribute OrderSearch search,// ModelAttributeMethodProcessor
    HttpServletRequest request,        // ServletRequestMethodArgumentResolver
    @RequestHeader String auth,        // RequestHeaderMethodArgumentResolver
    @CookieValue String token,         // ServletCookieValueMethodArgumentResolver
    @SessionAttribute User user,       // SessionAttributeMethodArgumentResolver
    Principal principal,               // PrincipalMethodArgumentResolver
    Locale locale,                     // LocaleContextMethodArgumentResolver
    @AuthenticationPrincipal UserDetails userDetails  // Spring Security
) { ... }
```

### 커스텀 ArgumentResolver

```java
// 커스텀 어노테이션
@Target(ElementType.PARAMETER)
@Retention(RetentionPolicy.RUNTIME)
public @interface LoginUser { }

// 커스텀 ArgumentResolver 구현
@Component
public class LoginUserArgumentResolver implements HandlerMethodArgumentResolver {

    @Override
    public boolean supportsParameter(MethodParameter parameter) {
        // @LoginUser 어노테이션이 붙은 파라미터 처리
        return parameter.hasParameterAnnotation(LoginUser.class)
            && parameter.getParameterType().equals(User.class);
    }

    @Override
    public Object resolveArgument(MethodParameter parameter,
                                  ModelAndViewContainer mavContainer,
                                  NativeWebRequest webRequest,
                                  WebDataBinderFactory binderFactory) {
        HttpSession session = ((HttpServletRequest) webRequest.getNativeRequest()).getSession();
        return session.getAttribute("loginUser");
    }
}

// 등록
@Configuration
public class WebConfig implements WebMvcConfigurer {
    @Autowired
    private LoginUserArgumentResolver loginUserArgumentResolver;

    @Override
    public void addArgumentResolvers(List<HandlerMethodArgumentResolver> resolvers) {
        resolvers.add(loginUserArgumentResolver);
    }
}

// 사용
@GetMapping("/mypage")
public String myPage(@LoginUser User loginUser, Model model) {
    model.addAttribute("user", loginUser);
    return "mypage";
}
```

### ReturnValueHandler

컨트롤러의 반환값을 어떻게 처리할지 결정한다.

```java
// 반환 타입별 처리
@GetMapping("/")
public String viewName() { ... }         // ViewNameMethodReturnValueHandler

@GetMapping("/")
public ModelAndView mav() { ... }        // ModelAndViewMethodReturnValueHandler

@GetMapping("/")
@ResponseBody
public OrderDto json() { ... }           // RequestResponseBodyMethodProcessor

@GetMapping("/")
public ResponseEntity<OrderDto> re() { ... }  // HttpEntityMethodProcessor

@GetMapping("/")
public CompletableFuture<OrderDto> async() { ... }  // AsyncTaskMethodReturnValueHandler
```

---

## 5. 인터셉터 vs 필터

### 필터 (Filter)

Servlet 스펙의 구성요소. **Spring 컨텍스트 외부**에서 동작.

<div class="mermaid">
graph TD
    A[HTTP 요청] --> B
    subgraph "Servlet 컨테이너 레벨"
        B["Filter Chain<br>CharacterEncodingFilter<br>CorsFilter<br>SecurityFilterChain"]
    end
    B --> C[DispatcherServlet]
    subgraph "Spring MVC 레벨"
        C --> D[Interceptor Chain]
        D --> E[Controller]
    end
</div>

```java
@Component
public class LoggingFilter implements Filter {

    @Override
    public void doFilter(ServletRequest request,
                         ServletResponse response,
                         FilterChain chain) throws IOException, ServletException {
        HttpServletRequest httpRequest = (HttpServletRequest) request;
        log.info("Filter: {} {}", httpRequest.getMethod(), httpRequest.getRequestURI());

        chain.doFilter(request, response);  // 다음 필터 또는 서블릿으로

        log.info("Filter: 응답 완료");
    }
}
```

### 인터셉터 (HandlerInterceptor)

Spring MVC 구성요소. **Spring 컨텍스트 내부**에서 동작. Spring Bean 주입 가능.

```java
@Component
public class AuthInterceptor implements HandlerInterceptor {

    @Autowired
    private JwtTokenProvider jwtTokenProvider;  // Spring Bean 주입 가능

    // 컨트롤러 실행 전
    @Override
    public boolean preHandle(HttpServletRequest request,
                              HttpServletResponse response,
                              Object handler) throws Exception {
        String token = request.getHeader("Authorization");
        if (!jwtTokenProvider.validate(token)) {
            response.sendError(HttpServletResponse.SC_UNAUTHORIZED);
            return false;  // false 반환 시 컨트롤러 실행 중단
        }
        return true;
    }

    // 컨트롤러 실행 후, View 렌더링 전
    @Override
    public void postHandle(HttpServletRequest request,
                           HttpServletResponse response,
                           Object handler,
                           ModelAndView modelAndView) {
        // ModelAndView 수정 가능
    }

    // View 렌더링 후 (예외 발생 시에도 실행)
    @Override
    public void afterCompletion(HttpServletRequest request,
                                HttpServletResponse response,
                                Object handler,
                                Exception ex) {
        // 리소스 정리
    }
}

// 등록
@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(authInterceptor)
                .addPathPatterns("/api/**")       // 적용할 URL 패턴
                .excludePathPatterns("/api/login", "/api/signup")  // 제외할 패턴
                .order(1);                        // 순서
    }
}
```

### 필터 vs 인터셉터 비교

| 구분 | Filter | Interceptor |
|------|--------|-------------|
| 레벨 | Servlet 컨테이너 | Spring MVC |
| Spring Bean 주입 | 불가 (DelegatingFilterProxy 사용 시 가능) | 가능 |
| 적용 범위 | 모든 요청 (정적 리소스 포함) | DispatcherServlet 이후 |
| 예외 처리 | `@ExceptionHandler` 불가 | `@ExceptionHandler` 가능 |
| 용도 | 인코딩, CORS, Security, 로깅 | 인증/인가, 로깅, API 버전 |

---

## 6. 예외 처리

### @ExceptionHandler

특정 컨트롤러에서 발생한 예외를 처리한다.

```java
@RestController
public class OrderController {

    @GetMapping("/{id}")
    public OrderResponse getOrder(@PathVariable Long id) {
        return orderService.findById(id); // OrderNotFoundException 발생 가능
    }

    // 이 컨트롤러에서 발생한 OrderNotFoundException만 처리
    @ExceptionHandler(OrderNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ErrorResponse handleOrderNotFound(OrderNotFoundException e) {
        return new ErrorResponse("ORDER_NOT_FOUND", e.getMessage());
    }
}
```

### @ControllerAdvice / @RestControllerAdvice

전역 예외 처리. 모든 컨트롤러에서 발생한 예외를 처리한다.

```java
@RestControllerAdvice  // @ControllerAdvice + @ResponseBody
public class GlobalExceptionHandler {

    // 유효성 검증 실패
    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ErrorResponse handleValidation(MethodArgumentNotValidException e) {
        List<String> errors = e.getBindingResult()
                               .getFieldErrors()
                               .stream()
                               .map(fe -> fe.getField() + ": " + fe.getDefaultMessage())
                               .collect(Collectors.toList());
        return new ErrorResponse("VALIDATION_FAILED", errors.toString());
    }

    // 비즈니스 예외
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ErrorResponse> handleBusiness(BusinessException e) {
        return ResponseEntity
                .status(e.getHttpStatus())
                .body(new ErrorResponse(e.getCode(), e.getMessage()));
    }

    // 그 외 모든 예외
    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public ErrorResponse handleException(Exception e) {
        log.error("예상치 못한 예외", e);
        return new ErrorResponse("INTERNAL_SERVER_ERROR", "서버 오류가 발생했습니다.");
    }
}
```

### HandlerExceptionResolver 처리 순서

<div class="mermaid">
graph TD
    A[예외 발생] --> B["ExceptionHandlerExceptionResolver<br>@ExceptionHandler 탐색<br>컨트롤러 → @ControllerAdvice 순"]
    B -->|처리 성공| Z[종료]
    B -->|처리 못한 경우| C["ResponseStatusExceptionResolver<br>@ResponseStatus 어노테이션 탐색<br>ResponseStatusException 처리"]
    C -->|처리 성공| Z
    C -->|처리 못한 경우| D["DefaultHandlerExceptionResolver<br>Spring MVC 표준 예외 처리<br>TypeMismatchException → 400<br>NoSuchRequestHandlingMethodException → 404<br>HttpRequestMethodNotSupportedException → 405"]
    D -->|처리 성공| Z
    D -->|처리 못한 경우| E[Servlet Container로 예외 전달]
</div>

---

## 7. 데이터 바인딩과 유효성 검증

```java
@PostMapping("/orders")
public ResponseEntity<OrderResponse> createOrder(
    @RequestBody @Valid OrderRequest request,  // @Valid: Bean Validation 실행
    BindingResult bindingResult               // 검증 결과 (optional)
) {
    if (bindingResult.hasErrors()) {
        // 직접 처리
    }
    return ResponseEntity.ok(orderService.create(request));
}

// DTO 유효성 규칙
public class OrderRequest {
    @NotNull(message = "상품 ID는 필수입니다")
    private Long productId;

    @Min(value = 1, message = "수량은 1 이상이어야 합니다")
    @Max(value = 100, message = "수량은 100 이하여야 합니다")
    private int quantity;

    @NotBlank(message = "배송 주소는 필수입니다")
    @Size(max = 200, message = "주소는 200자 이하여야 합니다")
    private String address;

    @Email(message = "이메일 형식이 올바르지 않습니다")
    private String email;
}
```

---

## 정리

| 구성요소 | 역할 |
|---------|------|
| DispatcherServlet | Front Controller, 모든 요청의 진입점 |
| HandlerMapping | URL → Handler 매핑 결정 |
| HandlerAdapter | Handler를 일관된 방식으로 실행 |
| ArgumentResolver | 컨트롤러 파라미터 바인딩 |
| ReturnValueHandler | 컨트롤러 반환값 처리 |
| MessageConverter | Java 객체 ↔ JSON/XML 변환 |
| ViewResolver | 뷰 이름 → View 객체 변환 |
| Filter | Servlet 레벨. 모든 요청에 적용 |
| Interceptor | Spring MVC 레벨. Bean 주입 가능 |
| @ExceptionHandler | 컨트롤러 단위 예외 처리 |
| @ControllerAdvice | 전역 예외 처리 |
