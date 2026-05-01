---
title: "Java/Spring REST API 클라이언트 라이브러리 완전 비교"
categories:
- SPRING
toc: true
toc_sticky: true
toc_label: 목차
---

Java/Spring 생태계에는 HTTP 클라이언트 라이브러리가 매우 다양합니다. RestTemplate, WebClient, RestClient, OpenFeign, Retrofit, Java HttpClient, OkHttp까지 선택지가 많아 어떤 것을 써야 할지 혼란스러울 수 있습니다. 이 글에서는 각 라이브러리의 동작 원리, 장단점, 실무 코드 예제까지 깊이 있게 비교합니다.

---

## RestTemplate

### 동작 원리 — 동기/블로킹

`RestTemplate`은 Spring Framework 3.0에서 도입된 동기(synchronous) HTTP 클라이언트입니다. 호출 스레드가 HTTP 응답이 올 때까지 블로킹됩니다.

```
요청 스레드
    │
    ├── RestTemplate.getForObject() 호출
    │
    ├── [블로킹 대기 — HTTP 응답 수신까지]
    │
    └── 응답 반환 후 다음 로직 실행
```

내부적으로 `ClientHttpRequestFactory`를 통해 실제 HTTP 연결을 생성합니다. 기본 구현은 `SimpleClientHttpRequestFactory`(JDK HttpURLConnection)이며, Apache HttpClient나 OkHttp로 교체 가능합니다.

### 기본 사용법

```java
@Configuration
public class RestTemplateConfig {

    @Bean
    public RestTemplate restTemplate(RestTemplateBuilder builder) {
        return builder
            .connectTimeout(Duration.ofSeconds(5))
            .readTimeout(Duration.ofSeconds(10))
            .build();
    }
}

@Service
public class UserService {
    private final RestTemplate restTemplate;
    private static final String BASE_URL = "https://api.example.com";

    public UserService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    // GET 요청
    public User getUser(Long id) {
        return restTemplate.getForObject(BASE_URL + "/users/{id}", User.class, id);
    }

    // GET 요청 — ResponseEntity로 헤더/상태코드 포함
    public ResponseEntity<User> getUserWithResponse(Long id) {
        return restTemplate.getForEntity(BASE_URL + "/users/{id}", User.class, id);
    }

    // POST 요청
    public User createUser(UserRequest request) {
        return restTemplate.postForObject(BASE_URL + "/users", request, User.class);
    }

    // PUT 요청
    public void updateUser(Long id, UserRequest request) {
        restTemplate.put(BASE_URL + "/users/{id}", request, id);
    }

    // DELETE 요청
    public void deleteUser(Long id) {
        restTemplate.delete(BASE_URL + "/users/{id}", id);
    }

    // exchange — 메서드/헤더/바디 완전 제어
    public List<User> searchUsers(String keyword) {
        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", "Bearer " + getToken());
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<Void> entity = new HttpEntity<>(headers);

        ResponseEntity<List<User>> response = restTemplate.exchange(
            BASE_URL + "/users/search?keyword=" + keyword,
            HttpMethod.GET,
            entity,
            new ParameterizedTypeReference<List<User>>() {} // 제네릭 타입
        );
        return response.getBody();
    }
}
```

### 설정 — 타임아웃, 인터셉터, 에러 핸들러

```java
@Configuration
public class RestTemplateConfig {

    @Bean
    public RestTemplate restTemplate() {
        // Apache HttpClient 기반 — 커넥션 풀 지원
        HttpComponentsClientHttpRequestFactory factory =
            new HttpComponentsClientHttpRequestFactory();

        // 커넥션 풀 설정
        PoolingHttpClientConnectionManager connectionManager =
            new PoolingHttpClientConnectionManager();
        connectionManager.setMaxTotal(200);           // 전체 최대 커넥션
        connectionManager.setDefaultMaxPerRoute(50);   // 호스트당 최대 커넥션

        CloseableHttpClient httpClient = HttpClients.custom()
            .setConnectionManager(connectionManager)
            .setDefaultRequestConfig(RequestConfig.custom()
                .setConnectTimeout(Timeout.ofSeconds(5))    // 연결 타임아웃
                .setResponseTimeout(Timeout.ofSeconds(10))  // 읽기 타임아웃
                .setConnectionRequestTimeout(Timeout.ofSeconds(2)) // 풀에서 커넥션 획득 타임아웃
                .build())
            .build();

        factory.setHttpClient(httpClient);

        RestTemplate restTemplate = new RestTemplate(factory);

        // 인터셉터 추가 — 로깅, 인증 헤더 추가 등
        restTemplate.setInterceptors(List.of(
            new LoggingInterceptor(),
            new AuthInterceptor()
        ));

        // 에러 핸들러 커스터마이즈
        restTemplate.setErrorHandler(new CustomErrorHandler());

        return restTemplate;
    }
}

// 로깅 인터셉터
public class LoggingInterceptor implements ClientHttpRequestInterceptor {
    private static final Logger log = LoggerFactory.getLogger(LoggingInterceptor.class);

    @Override
    public ClientHttpResponse intercept(HttpRequest request, byte[] body,
                                        ClientHttpRequestExecution execution)
            throws IOException {
        log.info("HTTP 요청 — {} {}", request.getMethod(), request.getURI());
        ClientHttpResponse response = execution.execute(request, body);
        log.info("HTTP 응답 — Status: {}", response.getStatusCode());
        return response;
    }
}

// 커스텀 에러 핸들러
public class CustomErrorHandler extends DefaultResponseErrorHandler {
    @Override
    public void handleError(ClientHttpResponse response) throws IOException {
        HttpStatusCode statusCode = response.getStatusCode();
        if (statusCode.is4xxClientError()) {
            throw new ClientException("클라이언트 오류: " + statusCode);
        } else if (statusCode.is5xxServerError()) {
            throw new ServerException("서버 오류: " + statusCode);
        }
        super.handleError(response);
    }
}
```

### 왜 Deprecated 방향인가?

Spring 공식 문서는 Spring Framework 6.1부터 `RestTemplate`을 유지보수 모드로 전환하고 `RestClient` 또는 `WebClient` 사용을 권장합니다.

- **블로킹 I/O**: 스레드당 하나의 요청만 처리 — 동시 요청이 많으면 스레드 수가 늘어 메모리/컨텍스트 스위칭 비용 증가
- **레거시 API 설계**: `exchange()`, `getForObject()` 등 메서드명이 직관적이지 않음
- **Fluent API 부재**: 요청 구성이 장황함
- **WebFlux와의 부조화**: 리액티브 스택과 함께 사용하기 어려움

---

## WebClient (Spring WebFlux)

### 비동기/논블로킹 동작 원리

`WebClient`는 Spring WebFlux에서 제공하는 논블로킹(non-blocking) HTTP 클라이언트입니다. 요청 스레드가 응답을 기다리지 않고 다른 작업을 계속 처리합니다.

```
요청 스레드
    │
    ├── WebClient.get().retrieve() 호출 → 즉시 반환 (Mono/Flux)
    │
    ├── [스레드는 다른 작업 처리 중]
    │
    └── 응답 도착 시 콜백/리액티브 파이프라인 실행
```

### Reactor Netty 기반

WebClient는 기본적으로 **Reactor Netty**를 사용합니다. Netty의 이벤트 루프 기반으로 적은 수의 스레드로 수천 개의 동시 연결을 처리합니다.

```
Reactor Netty 이벤트 루프 (CPU 코어 수 * 2개 스레드)
  ├── EventLoop-1 → 커넥션 100개 처리
  ├── EventLoop-2 → 커넥션 100개 처리
  └── EventLoop-N → 커넥션 100개 처리

vs RestTemplate (Servlet 스레드 모델)
  ├── Thread-1 → 커넥션 1개 (블로킹)
  ├── Thread-2 → 커넥션 1개 (블로킹)
  └── Thread-N → 커넥션 1개 (블로킹)
```

### Mono/Flux 사용법

```java
@Configuration
public class WebClientConfig {

    @Bean
    public WebClient webClient() {
        // 커넥션 풀 및 타임아웃 설정
        HttpClient httpClient = HttpClient.create()
            .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 5000)
            .responseTimeout(Duration.ofSeconds(10))
            .doOnConnected(conn ->
                conn.addHandlerLast(new ReadTimeoutHandler(10))
                    .addHandlerLast(new WriteTimeoutHandler(5)));

        return WebClient.builder()
            .baseUrl("https://api.example.com")
            .clientConnector(new ReactorClientHttpConnector(httpClient))
            .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .defaultHeader(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
            .codecs(configurer ->
                configurer.defaultCodecs().maxInMemorySize(2 * 1024 * 1024)) // 2MB
            .filter(ExchangeFilterFunctions.basicAuthentication("user", "pass"))
            .filter(logRequest())
            .build();
    }

    private ExchangeFilterFunction logRequest() {
        return ExchangeFilterFunction.ofRequestProcessor(clientRequest -> {
            log.info("WebClient 요청 — {} {}", clientRequest.method(), clientRequest.url());
            return Mono.just(clientRequest);
        });
    }
}

@Service
public class UserWebClientService {
    private final WebClient webClient;

    // GET — Mono (단일 객체)
    public Mono<User> getUser(Long id) {
        return webClient.get()
            .uri("/users/{id}", id)
            .retrieve()
            .onStatus(HttpStatusCode::is4xxClientError,
                response -> Mono.error(new ClientException("클라이언트 오류")))
            .onStatus(HttpStatusCode::is5xxServerError,
                response -> Mono.error(new ServerException("서버 오류")))
            .bodyToMono(User.class);
    }

    // GET — Flux (스트리밍 목록)
    public Flux<User> getAllUsers() {
        return webClient.get()
            .uri("/users")
            .retrieve()
            .bodyToFlux(User.class);
    }

    // POST — 요청 바디 포함
    public Mono<User> createUser(UserRequest request) {
        return webClient.post()
            .uri("/users")
            .bodyValue(request)
            .retrieve()
            .bodyToMono(User.class);
    }

    // 헤더 포함 요청
    public Mono<ResponseEntity<User>> getUserWithHeaders(Long id, String token) {
        return webClient.get()
            .uri("/users/{id}", id)
            .header("Authorization", "Bearer " + token)
            .retrieve()
            .toEntity(User.class);
    }

    // 복잡한 에러 처리 — ResponseSpec 활용
    public Mono<User> getUserSafe(Long id) {
        return webClient.get()
            .uri("/users/{id}", id)
            .retrieve()
            .bodyToMono(User.class)
            .timeout(Duration.ofSeconds(3))           // 개별 요청 타임아웃
            .retry(2)                                  // 실패 시 2회 재시도
            .onErrorReturn(TimeoutException.class, User.defaultUser()) // 타임아웃 시 기본값
            .onErrorResume(WebClientResponseException.NotFound.class,
                e -> Mono.empty());                    // 404 시 empty
    }

    // 병렬 요청 — Mono.zip
    public Mono<UserProfile> getUserProfile(Long userId) {
        Mono<User> userMono = getUser(userId);
        Mono<List<Order>> ordersMono = getOrders(userId).collectList();
        Mono<Address> addressMono = getAddress(userId);

        return Mono.zip(userMono, ordersMono, addressMono)
            .map(tuple -> UserProfile.of(tuple.getT1(), tuple.getT2(), tuple.getT3()));
    }
}
```

### 동기 모드로도 사용 가능 (.block())

WebFlux를 사용하지 않는 환경(Spring MVC)에서도 WebClient를 동기적으로 사용할 수 있습니다.

```java
// .block()으로 동기 변환 — Mono → 값
User user = webClient.get()
    .uri("/users/{id}", 1L)
    .retrieve()
    .bodyToMono(User.class)
    .block(Duration.ofSeconds(5)); // 최대 5초 대기

// .collectList().block()으로 Flux → List 변환
List<User> users = webClient.get()
    .uri("/users")
    .retrieve()
    .bodyToFlux(User.class)
    .collectList()
    .block();
```

**주의:** 리액티브 파이프라인 내에서 `.block()` 호출은 데드락을 유발할 수 있습니다. Spring MVC 컨트롤러(서블릿 스레드)에서만 사용하세요.

---

## RestClient (Spring 6.1+)

### 새로운 동기 HTTP 클라이언트

`RestClient`는 Spring Framework 6.1(Spring Boot 3.2)에서 도입된 **새로운 동기 HTTP 클라이언트**입니다. RestTemplate을 대체하며, WebClient의 Fluent API를 동기 방식으로 제공합니다.

**RestTemplate의 후계자:** RestTemplate과 동일하게 동기/블로킹으로 동작하지만, API 설계가 훨씬 직관적입니다.

### Fluent API 사용법

```java
@Configuration
public class RestClientConfig {

    @Bean
    public RestClient restClient() {
        return RestClient.builder()
            .baseUrl("https://api.example.com")
            .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .defaultStatusHandler(HttpStatusCode::is4xxClientError,
                (req, res) -> {
                    throw new ClientException("4xx 오류: " + res.getStatusCode());
                })
            .defaultStatusHandler(HttpStatusCode::is5xxServerError,
                (req, res) -> {
                    throw new ServerException("5xx 오류: " + res.getStatusCode());
                })
            .requestInterceptor((req, body, execution) -> {
                req.getHeaders().add("X-Request-Id", UUID.randomUUID().toString());
                return execution.execute(req, body);
            })
            .build();
    }
}

@Service
public class UserRestClientService {
    private final RestClient restClient;

    // GET — 단일 객체
    public User getUser(Long id) {
        return restClient.get()
            .uri("/users/{id}", id)
            .retrieve()
            .body(User.class);
    }

    // GET — 제네릭 타입 (List, Map 등)
    public List<User> getAllUsers() {
        return restClient.get()
            .uri("/users")
            .retrieve()
            .body(new ParameterizedTypeReference<List<User>>() {});
    }

    // GET — ResponseEntity (헤더, 상태코드 포함)
    public ResponseEntity<User> getUserWithMeta(Long id) {
        return restClient.get()
            .uri("/users/{id}", id)
            .retrieve()
            .toEntity(User.class);
    }

    // POST — 요청 바디
    public User createUser(UserRequest request) {
        return restClient.post()
            .uri("/users")
            .body(request)
            .retrieve()
            .body(User.class);
    }

    // PUT — 업데이트
    public User updateUser(Long id, UserRequest request) {
        return restClient.put()
            .uri("/users/{id}", id)
            .body(request)
            .retrieve()
            .body(User.class);
    }

    // DELETE — 상태코드 확인
    public void deleteUser(Long id) {
        restClient.delete()
            .uri("/users/{id}", id)
            .retrieve()
            .toBodilessEntity(); // 바디 없는 응답
    }

    // 쿼리 파라미터 빌더 활용
    public List<User> searchUsers(String name, int page, int size) {
        return restClient.get()
            .uri(uriBuilder -> uriBuilder
                .path("/users/search")
                .queryParam("name", name)
                .queryParam("page", page)
                .queryParam("size", size)
                .build())
            .retrieve()
            .body(new ParameterizedTypeReference<List<User>>() {});
    }

    // 커스텀 에러 처리 — 요청별
    public Optional<User> findUser(Long id) {
        try {
            User user = restClient.get()
                .uri("/users/{id}", id)
                .retrieve()
                .onStatus(HttpStatusCode::is4xxClientError,
                    (req, res) -> {}) // 4xx 무시
                .body(User.class);
            return Optional.ofNullable(user);
        } catch (Exception e) {
            return Optional.empty();
        }
    }
}
```

### RestTemplate과 RestClient API 비교

```java
// RestTemplate — 장황한 API
ResponseEntity<List<User>> response = restTemplate.exchange(
    "/users",
    HttpMethod.GET,
    new HttpEntity<>(headers),
    new ParameterizedTypeReference<List<User>>() {}
);
List<User> users = response.getBody();

// RestClient — 간결한 Fluent API
List<User> users = restClient.get()
    .uri("/users")
    .headers(h -> h.addAll(headers))
    .retrieve()
    .body(new ParameterizedTypeReference<List<User>>() {});
```

### RestTemplate → RestClient 마이그레이션

```java
// RestClient는 기존 RestTemplate 인프라 재사용 가능
@Bean
public RestClient restClientFromRestTemplate(RestTemplate restTemplate) {
    return RestClient.create(restTemplate); // RestTemplate 설정(인터셉터, 커넥션 풀 등) 재사용
}
```

---

## OpenFeign (Spring Cloud)

### 선언적 HTTP 클라이언트

OpenFeign은 인터페이스 선언만으로 HTTP 클라이언트를 구현하는 **선언적(Declarative) HTTP 클라이언트**입니다. 실제 HTTP 호출 코드를 직접 작성하지 않습니다.

```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-openfeign</artifactId>
</dependency>
```

```java
// 메인 클래스에 활성화
@SpringBootApplication
@EnableFeignClients
public class Application { ... }
```

### 인터페이스 기반 (@FeignClient)

```java
// Feign 클라이언트 인터페이스 선언
@FeignClient(
    name = "user-service",
    url = "${services.user-service.url}",
    fallback = UserServiceFallback.class,          // Circuit Breaker fallback
    configuration = FeignClientConfig.class         // 커스텀 설정
)
public interface UserServiceClient {

    @GetMapping("/users/{id}")
    User getUser(@PathVariable Long id);

    @GetMapping("/users")
    List<User> getAllUsers(
        @RequestParam String name,
        @RequestParam int page,
        @RequestParam int size
    );

    @PostMapping("/users")
    User createUser(@RequestBody UserRequest request);

    @PutMapping("/users/{id}")
    User updateUser(@PathVariable Long id, @RequestBody UserRequest request);

    @DeleteMapping("/users/{id}")
    void deleteUser(@PathVariable Long id);

    // 헤더 전달
    @GetMapping("/users/me")
    User getCurrentUser(@RequestHeader("Authorization") String token);
}

// 서비스에서 일반 빈처럼 사용
@Service
public class OrderService {
    private final UserServiceClient userServiceClient;

    public Order createOrder(Long userId, OrderRequest request) {
        User user = userServiceClient.getUser(userId); // HTTP 호출 자동 처리
        // ...
    }
}
```

### Feign 설정 커스터마이즈

```java
@Configuration
public class FeignClientConfig {

    // 타임아웃 설정
    @Bean
    public Request.Options options() {
        return new Request.Options(
            5, TimeUnit.SECONDS,   // connectTimeout
            10, TimeUnit.SECONDS,  // readTimeout
            true                   // followRedirects
        );
    }

    // 재시도 설정
    @Bean
    public Retryer retryer() {
        return new Retryer.Default(
            100,   // 초기 대기 ms
            1000,  // 최대 대기 ms
            3      // 최대 시도 횟수
        );
    }

    // 로깅 수준
    @Bean
    public Logger.Level feignLoggerLevel() {
        return Logger.Level.FULL; // NONE, BASIC, HEADERS, FULL
    }

    // 인터셉터 — 모든 요청에 Authorization 헤더 추가
    @Bean
    public RequestInterceptor requestInterceptor() {
        return requestTemplate -> {
            String token = SecurityContextHolder.getContext()
                .getAuthentication().getCredentials().toString();
            requestTemplate.header("Authorization", "Bearer " + token);
        };
    }

    // 에러 디코더
    @Bean
    public ErrorDecoder errorDecoder() {
        return (methodKey, response) -> {
            if (response.status() == 404) {
                return new NotFoundException("리소스를 찾을 수 없습니다.");
            }
            if (response.status() >= 500) {
                return new ServiceException("서비스 오류: " + response.status());
            }
            return new Default().decode(methodKey, response);
        };
    }
}
```

### Circuit Breaker 연동 (Resilience4j)

```yaml
# application.yml
spring:
  cloud:
    openfeign:
      circuitbreaker:
        enabled: true

resilience4j:
  circuitbreaker:
    instances:
      user-service:
        registerHealthIndicator: true
        slidingWindowSize: 10
        minimumNumberOfCalls: 5
        permittedNumberOfCallsInHalfOpenState: 3
        failureRateThreshold: 50
        waitDurationInOpenState: 30s
```

```java
// Fallback 구현
@Component
public class UserServiceFallback implements UserServiceClient {

    @Override
    public User getUser(Long id) {
        return User.defaultUser(id); // 기본값 반환
    }

    @Override
    public List<User> getAllUsers(String name, int page, int size) {
        return Collections.emptyList(); // 빈 목록 반환
    }

    @Override
    public User createUser(UserRequest request) {
        throw new ServiceUnavailableException("사용자 서비스 일시 중단");
    }

    // ...
}
```

### 장단점

| 항목 | 내용 |
|------|------|
| 장점 | 선언적 코드, 보일러플레이트 최소화, Spring Cloud 통합 용이 |
| 장점 | Circuit Breaker, 로드밸런싱(Ribbon/LoadBalancer) 연동 |
| 단점 | 동기/블로킹 (WebFlux와 부조화) |
| 단점 | Spring Cloud 의존성 필요 |
| 단점 | 복잡한 요청 구성 시 한계 (인터페이스 제약) |

---

## Retrofit

### Square 라이브러리

Retrofit은 Square가 개발한 인터페이스 기반 HTTP 클라이언트입니다. Android와 서버 양쪽에서 모두 사용 가능하며, OkHttp를 기반으로 합니다.

```xml
<dependency>
    <groupId>com.squareup.retrofit2</groupId>
    <artifactId>retrofit</artifactId>
    <version>2.11.0</version>
</dependency>
<dependency>
    <groupId>com.squareup.retrofit2</groupId>
    <artifactId>converter-jackson</artifactId>
    <version>2.11.0</version>
</dependency>
```

### 인터페이스 기반 선언

```java
// API 인터페이스 정의
public interface UserApi {

    @GET("users/{id}")
    Call<User> getUser(@Path("id") Long id);

    @GET("users")
    Call<List<User>> getUsers(
        @Query("name") String name,
        @Query("page") int page
    );

    @POST("users")
    Call<User> createUser(@Body UserRequest request);

    @PUT("users/{id}")
    Call<User> updateUser(@Path("id") Long id, @Body UserRequest request);

    @DELETE("users/{id}")
    Call<Void> deleteUser(@Path("id") Long id);

    @Headers("Accept: application/json")
    @GET("users/profile")
    Call<User> getProfile(@Header("Authorization") String token);

    // 비동기 지원 (RxJava)
    @GET("users/{id}")
    Observable<User> getUserReactive(@Path("id") Long id);

    // Kotlin Coroutines 지원
    // @GET("users/{id}")
    // suspend fun getUserSuspend(@Path("id") Long id): User
}

// Retrofit 인스턴스 생성
@Configuration
public class RetrofitConfig {

    @Bean
    public UserApi userApi() {
        OkHttpClient okHttpClient = new OkHttpClient.Builder()
            .connectTimeout(5, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.SECONDS)
            .addInterceptor(new HttpLoggingInterceptor()
                .setLevel(HttpLoggingInterceptor.Level.BODY))
            .addInterceptor(chain -> {
                Request request = chain.request().newBuilder()
                    .addHeader("X-API-Key", "api-key-value")
                    .build();
                return chain.proceed(request);
            })
            .build();

        Retrofit retrofit = new Retrofit.Builder()
            .baseUrl("https://api.example.com/")
            .client(okHttpClient)
            .addConverterFactory(JacksonConverterFactory.create())
            .build();

        return retrofit.create(UserApi.class);
    }
}

// 사용 — 동기
@Service
public class UserRetrofitService {
    private final UserApi userApi;

    // 동기 호출
    public User getUser(Long id) throws IOException {
        Response<User> response = userApi.getUser(id).execute();
        if (response.isSuccessful()) {
            return response.body();
        }
        throw new ApiException("API 오류: " + response.code());
    }

    // 비동기 호출 (Callback)
    public void getUserAsync(Long id, Consumer<User> onSuccess, Consumer<Throwable> onError) {
        userApi.getUser(id).enqueue(new Callback<User>() {
            @Override
            public void onResponse(Call<User> call, Response<User> response) {
                if (response.isSuccessful()) {
                    onSuccess.accept(response.body());
                } else {
                    onError.accept(new ApiException("오류: " + response.code()));
                }
            }

            @Override
            public void onFailure(Call<User> call, Throwable t) {
                onError.accept(t);
            }
        });
    }
}
```

### Retrofit vs OpenFeign

| 항목 | Retrofit | OpenFeign |
|------|----------|-----------|
| 주요 환경 | Android + 서버 | Spring Cloud 서버 |
| Spring 통합 | 직접 구성 필요 | @EnableFeignClients로 통합 |
| 비동기 | RxJava/Coroutines | 기본 동기 |
| Circuit Breaker | 직접 연동 필요 | Spring Cloud 통합 용이 |
| 어노테이션 | Retrofit 어노테이션 | Spring MVC 어노테이션 |

---

## HttpClient (Java 11+)

### JDK 내장 — 외부 의존성 없음

Java 11에서 도입된 `java.net.http.HttpClient`는 JDK 내장 HTTP 클라이언트입니다. 외부 라이브러리 없이 HTTP/1.1, HTTP/2, WebSocket을 지원합니다.

```java
// HttpClient 인스턴스 생성
HttpClient client = HttpClient.newBuilder()
    .version(HttpClient.Version.HTTP_2)         // HTTP/2 우선
    .connectTimeout(Duration.ofSeconds(5))
    .followRedirects(HttpClient.Redirect.NORMAL)
    .executor(Executors.newFixedThreadPool(10)) // 비동기 실행 스레드 풀
    .build();

@Service
public class UserHttpClientService {
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private static final String BASE_URL = "https://api.example.com";

    // 동기 GET
    public User getUser(Long id) throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
            .GET()
            .uri(URI.create(BASE_URL + "/users/" + id))
            .header("Accept", "application/json")
            .timeout(Duration.ofSeconds(10))
            .build();

        HttpResponse<String> response = httpClient.send(
            request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() == 200) {
            return objectMapper.readValue(response.body(), User.class);
        }
        throw new ApiException("오류: " + response.statusCode());
    }

    // 비동기 GET — CompletableFuture
    public CompletableFuture<User> getUserAsync(Long id) {
        HttpRequest request = HttpRequest.newBuilder()
            .GET()
            .uri(URI.create(BASE_URL + "/users/" + id))
            .build();

        return httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofString())
            .thenApply(response -> {
                if (response.statusCode() != 200) {
                    throw new RuntimeException("오류: " + response.statusCode());
                }
                try {
                    return objectMapper.readValue(response.body(), User.class);
                } catch (JsonProcessingException e) {
                    throw new RuntimeException("JSON 파싱 오류", e);
                }
            });
    }

    // POST — JSON 바디
    public User createUser(UserRequest request) throws Exception {
        String requestBody = objectMapper.writeValueAsString(request);

        HttpRequest httpRequest = HttpRequest.newBuilder()
            .POST(HttpRequest.BodyPublishers.ofString(requestBody))
            .uri(URI.create(BASE_URL + "/users"))
            .header("Content-Type", "application/json")
            .header("Accept", "application/json")
            .build();

        HttpResponse<String> response = httpClient.send(
            httpRequest, HttpResponse.BodyHandlers.ofString());

        return objectMapper.readValue(response.body(), User.class);
    }

    // 병렬 요청
    public List<User> getUsersParallel(List<Long> userIds) {
        List<CompletableFuture<User>> futures = userIds.stream()
            .map(this::getUserAsync)
            .toList();

        return futures.stream()
            .map(CompletableFuture::join)
            .toList();
    }
}
```

### HTTP/2 지원

```java
// HTTP/2 서버 푸시 지원
HttpClient.newBuilder()
    .version(HttpClient.Version.HTTP_2) // HTTP/2 우선, 불가 시 HTTP/1.1로 폴백
    .build();

// 응답 헤더에서 HTTP 버전 확인
HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
System.out.println(response.version()); // HTTP_2 또는 HTTP_1_1
```

---

## OkHttp

### 커넥션 풀, 인터셉터, 캐시

OkHttp는 Square가 개발한 효율적인 HTTP 클라이언트입니다. Retrofit의 기반이기도 하며, 자체적으로 사용해도 강력합니다.

```xml
<dependency>
    <groupId>com.squareup.okhttp3</groupId>
    <artifactId>okhttp</artifactId>
    <version>4.12.0</version>
</dependency>
```

```java
// OkHttpClient 설정
OkHttpClient client = new OkHttpClient.Builder()
    // 타임아웃
    .connectTimeout(5, TimeUnit.SECONDS)
    .readTimeout(10, TimeUnit.SECONDS)
    .writeTimeout(10, TimeUnit.SECONDS)

    // 커넥션 풀 (기본: 5개, 5분 유지)
    .connectionPool(new ConnectionPool(20, 5, TimeUnit.MINUTES))

    // 캐시 설정
    .cache(new Cache(new File("cache"), 10 * 1024 * 1024)) // 10MB 캐시

    // 애플리케이션 인터셉터 (재시도 포함, 캐시 전)
    .addInterceptor(new HttpLoggingInterceptor()
        .setLevel(HttpLoggingInterceptor.Level.BODY))
    .addInterceptor(chain -> {
        // 인증 헤더 자동 추가
        Request original = chain.request();
        Request request = original.newBuilder()
            .header("Authorization", "Bearer " + getToken())
            .build();
        return chain.proceed(request);
    })

    // 네트워크 인터셉터 (리다이렉트 후, 캐시 후)
    .addNetworkInterceptor(chain -> {
        Response response = chain.proceed(chain.request());
        // 캐시 제어 헤더 수정
        return response.newBuilder()
            .header("Cache-Control", "max-age=60")
            .build();
    })

    // 재시도 설정
    .retryOnConnectionFailure(true)
    .build();

@Service
public class UserOkHttpService {
    private final OkHttpClient client;
    private final ObjectMapper objectMapper;
    private static final MediaType JSON = MediaType.get("application/json");

    // 동기 GET
    public User getUser(Long id) throws IOException {
        Request request = new Request.Builder()
            .url("https://api.example.com/users/" + id)
            .get()
            .build();

        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new ApiException("오류: " + response.code());
            }
            return objectMapper.readValue(response.body().string(), User.class);
        }
    }

    // 비동기 POST
    public void createUserAsync(UserRequest userRequest, Consumer<User> onSuccess,
                                Consumer<IOException> onError) throws JsonProcessingException {
        String json = objectMapper.writeValueAsString(userRequest);
        RequestBody body = RequestBody.create(json, JSON);

        Request request = new Request.Builder()
            .url("https://api.example.com/users")
            .post(body)
            .build();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onResponse(Call call, Response response) throws IOException {
                if (response.isSuccessful()) {
                    User user = objectMapper.readValue(response.body().string(), User.class);
                    onSuccess.accept(user);
                }
            }

            @Override
            public void onFailure(Call call, IOException e) {
                onError.accept(e);
            }
        });
    }
}
```

### Retrofit의 기반으로서의 OkHttp

```java
// Retrofit이 OkHttp를 내부적으로 사용
OkHttpClient okHttpClient = new OkHttpClient.Builder()
    .addInterceptor(loggingInterceptor)
    .connectionPool(new ConnectionPool(10, 5, TimeUnit.MINUTES))
    .build();

Retrofit retrofit = new Retrofit.Builder()
    .baseUrl("https://api.example.com/")
    .client(okHttpClient) // OkHttp 공유
    .addConverterFactory(JacksonConverterFactory.create())
    .build();
```

---

## 종합 비교 표

### 기본 특성 비교

| 라이브러리 | 동기/비동기 | Spring 통합 | 외부 의존성 | 선언적 API | HTTP/2 |
|-----------|------------|------------|------------|-----------|--------|
| RestTemplate | 동기 | Spring MVC 내장 | 없음 | X | △ |
| WebClient | 비동기 (동기 가능) | Spring WebFlux 내장 | Reactor Netty | X | O |
| RestClient | 동기 | Spring 6.1+ 내장 | 없음 | X | △ |
| OpenFeign | 동기 | Spring Cloud | Spring Cloud | O | X |
| Retrofit | 동기/비동기 | 수동 설정 | OkHttp | O | O |
| Java HttpClient | 동기/비동기 | 없음 | 없음 (JDK) | X | O |
| OkHttp | 동기/비동기 | 없음 | 없음 | X | O |

### 성능 및 편의성 비교

| 라이브러리 | 처리량 | 메모리 효율 | 코드 양 | 학습 곡선 | 테스트 용이성 |
|-----------|--------|------------|---------|----------|-------------|
| RestTemplate | 보통 | 보통 | 많음 | 낮음 | 보통 |
| WebClient | 높음 | 높음 | 중간 | 높음 | 보통 |
| RestClient | 보통 | 보통 | 적음 | 낮음 | 높음 |
| OpenFeign | 보통 | 보통 | 매우 적음 | 낮음 | 높음 |
| Retrofit | 보통~높음 | 보통 | 매우 적음 | 낮음 | 높음 |
| Java HttpClient | 보통~높음 | 높음 | 많음 | 중간 | 낮음 |
| OkHttp | 높음 | 높음 | 중간 | 중간 | 중간 |

### Spring 생태계 통합도

| 라이브러리 | Spring Boot AutoConfig | Spring Security 연동 | Actuator 통합 | Spring Cloud |
|-----------|----------------------|---------------------|--------------|-------------|
| RestTemplate | O (RestTemplateBuilder) | O | 제한적 | O |
| WebClient | O | O | O (Metrics) | O |
| RestClient | O | O | O | O |
| OpenFeign | O | O | O | O (핵심) |
| Retrofit | X (수동) | 수동 | X | X |
| Java HttpClient | X (수동) | 수동 | X | X |
| OkHttp | X (수동) | 수동 | X | X |

---

## 실무 선택 가이드 (상황별 추천)

### 의사결정 트리

```
Spring Boot 3.x 프로젝트인가?
├── Yes
│   ├── 비동기/리액티브 필요한가?
│   │   ├── Yes → WebClient (Reactor 기반)
│   │   └── No
│   │       ├── MSA/서비스 간 호출이 많은가?
│   │       │   ├── Yes, Spring Cloud 사용 중 → OpenFeign
│   │       │   └── No → RestClient (Spring 6.1+)
│   └── (RestTemplate은 신규 개발 지양)
│
└── No (레거시 Spring MVC)
    ├── 비동기 필요 → WebClient (.block() 허용)
    ├── MSA → OpenFeign
    └── 기존 RestTemplate 유지 (레거시 유지보수)

Android/멀티플랫폼?
└── Retrofit + OkHttp

Spring 외부 Java 프로젝트?
├── 의존성 최소화 → Java HttpClient (JDK 11+)
└── 고성능 필요 → OkHttp
```

### 시나리오별 추천

**시나리오 1: Spring Boot 3.x MVC, 단순 외부 API 호출**

```java
// 추천: RestClient
// 이유: Spring 내장, 간결한 Fluent API, 동기 방식으로 충분
@Bean
public RestClient restClient() {
    return RestClient.builder()
        .baseUrl("https://external-api.com")
        .build();
}
```

**시나리오 2: MSA 환경, 서비스 간 동기 호출**

```java
// 추천: OpenFeign
// 이유: 선언적 API, Circuit Breaker 통합, 로드밸런싱 용이
@FeignClient(name = "inventory-service", fallback = InventoryFallback.class)
public interface InventoryClient {
    @GetMapping("/inventory/{productId}")
    Inventory checkInventory(@PathVariable Long productId);
}
```

**시나리오 3: 고트래픽 비동기 처리, WebFlux 스택**

```java
// 추천: WebClient
// 이유: 논블로킹 I/O, Reactor 파이프라인 통합, 높은 동시성
webClient.get()
    .uri("/products")
    .retrieve()
    .bodyToFlux(Product.class)
    .flatMap(product -> processAsync(product))
    .subscribe();
```

**시나리오 4: 외부 라이브러리 최소화, JDK만 사용**

```java
// 추천: Java HttpClient (JDK 11+)
// 이유: 의존성 없음, HTTP/2 지원
HttpClient.newBuilder()
    .version(HttpClient.Version.HTTP_2)
    .build();
```

**시나리오 5: Android + 서버 공유 코드, 멀티플랫폼**

```java
// 추천: Retrofit + OkHttp
// 이유: Android 표준, 선언적 API, Kotlin Coroutines 지원
```

**시나리오 6: 레거시 Spring 5.x 유지보수**

```java
// 추천: RestTemplate 유지 (마이그레이션 비용 vs 이점 검토)
// 신규 기능은 RestClient/WebClient 도입 검토
```

### 라이브러리별 의존성 요약

```xml
<!-- RestTemplate, RestClient, WebClient — Spring Boot에 포함 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>

<!-- WebClient — WebFlux 의존성 추가 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webflux</artifactId>
</dependency>

<!-- OpenFeign -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-openfeign</artifactId>
</dependency>

<!-- Retrofit -->
<dependency>
    <groupId>com.squareup.retrofit2</groupId>
    <artifactId>retrofit</artifactId>
    <version>2.11.0</version>
</dependency>

<!-- OkHttp (단독 사용) -->
<dependency>
    <groupId>com.squareup.okhttp3</groupId>
    <artifactId>okhttp</artifactId>
    <version>4.12.0</version>
</dependency>
```

---

## 정리

| 라이브러리 | 추천 상황 | 비추천 상황 |
|-----------|----------|-----------|
| **RestClient** | Spring Boot 3.x 신규, 동기 API 호출 | 비동기, Spring 6.1 미만 |
| **WebClient** | 비동기/리액티브, 고동시성 | 단순 동기 호출 (.block() 남용) |
| **OpenFeign** | MSA 서비스 간 호출, Spring Cloud | 단독 사용, 비동기 필요 |
| **RestTemplate** | 레거시 유지보수 | 신규 개발 |
| **Retrofit** | Android/멀티플랫폼, Kotlin Coroutines | Spring 전용 서버 |
| **Java HttpClient** | 의존성 최소화, HTTP/2 | 복잡한 요청 구성 |
| **OkHttp** | Retrofit 하위, 커스텀 인터셉터/캐시 | Spring 통합이 필요한 경우 |

Spring Boot 3.x 신규 프로젝트라면 **동기는 RestClient, 비동기는 WebClient, MSA는 OpenFeign** 조합이 가장 자연스럽습니다. 레거시 코드의 RestTemplate은 섣불리 마이그레이션하기보다 RestClient로의 점진적 전환을 권장합니다.
