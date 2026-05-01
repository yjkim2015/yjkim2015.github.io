---
title: "Tomcat vs Netty"
categories: SERVER
tags: [Tomcat, Netty, NIO, 스레드모델, VirtualThread, WebFlux]
toc: true
toc_sticky: true
toc_label: 목차
date: 2026-05-01
---

Tomcat과 Netty는 Java 생태계에서 가장 널리 사용되는 두 서버 엔진이다. 둘 다 네트워크 I/O를 처리하지만 설계 철학과 스레드 모델이 근본적으로 다르다. Spring MVC와 Spring WebFlux의 기반이 되는 두 엔진을 이해하면 성능 문제를 더 잘 진단하고 올바른 기술을 선택할 수 있다.

---

## Tomcat 아키텍처

### 개요

Apache Tomcat은 Java Servlet 명세를 구현한 서블릿 컨테이너이자 웹 서버다. Spring MVC의 기본 내장 서버이며, Thread-Per-Request 모델을 따른다.

### 내부 컴포넌트

```
[Client Request]
      ↓
[Connector] ← HTTP/1.1 또는 HTTP/2 처리
      ↓
[ProtocolHandler] ← NIO 기반 소켓 처리
      ↓
[Executor (Thread Pool)] ← 작업 스레드 할당
      ↓
[Engine → Host → Context → Wrapper]
      ↓
[Servlet / Filter Chain]
      ↓
[DispatcherServlet] (Spring MVC)
```

- **Connector**: 클라이언트 연결을 받아들이는 입구. HTTP/1.1, HTTP/2, AJP 등 프로토콜 지원
- **ProtocolHandler**: 실제 소켓 I/O를 처리. NIO, NIO2, APR 방식 선택 가능
- **Executor**: 요청을 처리하는 스레드 풀

### NIO 스레드 모델

Tomcat 8.5부터 NIO가 기본값이다.

```
[Acceptor Thread (1~2개)]
  → 새 연결을 수락하고 Poller에 등록

[Poller Thread (1~2개)]
  → java.nio.channels.Selector로 I/O 이벤트 감시
  → I/O 준비된 소켓을 Worker Pool로 전달

[Worker Thread Pool (기본 200개)]
  → 실제 HTTP 요청 처리
  → 요청 처리 완료까지 스레드 점유
```

```yaml
# Spring Boot application.yml
server:
  tomcat:
    threads:
      max: 200          # 최대 워커 스레드 수
      min-spare: 10     # 최소 유지 스레드 수
    max-connections: 8192
    accept-count: 100
    connection-timeout: 20s
```

### Thread-Per-Request의 한계

```
[문제 시나리오]
maxThreads=200, 외부 API 응답 지연 3초 발생 시:

t=0: 200개 요청 도착 → 200개 스레드 모두 외부 API 대기 중
t=1: 201번째 요청 → accept-count 대기 큐 진입
t=2: 큐도 가득 참 → 503 Service Unavailable

결과: 200개 스레드 전부 BLOCKED, CPU는 놀고 있음 → 리소스 낭비
```

---

## Netty 아키텍처

### 개요

Netty는 비동기 이벤트 기반 네트워크 I/O 프레임워크다. Spring WebFlux의 기본 서버이며, Reactor 패턴을 기반으로 한다.

### 핵심 컴포넌트

```
[NioEventLoopGroup (Boss, 1~2개 스레드)]
  → 새 TCP 연결 수락 전담

[NioEventLoopGroup (Worker, CPU코어 × 2개 스레드)]
  → Channel I/O 처리 전담

[Channel]
  → 각 연결을 표현하는 객체
  → 하나의 EventLoop에 고정 바인딩

[ChannelPipeline]
  → [Handler 1] → [Handler 2] → ... → [Handler N]
```

### EventLoop

하나의 스레드가 하나의 EventLoop를 담당하고, 하나의 EventLoop는 여러 Channel을 처리한다.

```
EventLoop Thread 1 (무한 루프)
  ├── select()             ← I/O 이벤트 대기 (논블로킹)
  ├── processSelectedKeys() ← 준비된 채널 처리
  └── runAllTasks()        ← 큐에 쌓인 작업 실행

EventLoop Thread 1이 담당하는 Channel들:
  ├── Channel A (연결 1)
  ├── Channel B (연결 2)
  └── Channel C (연결 3)
```

**핵심 원칙**: EventLoop 스레드를 절대 블로킹하면 안 된다. 블로킹 작업은 별도 스레드 풀(`Schedulers.boundedElastic()`)로 오프로드해야 한다.

### ChannelPipeline

```
소켓 → [인바운드 방향 →]
        [ByteToMessage Decoder  ]
        [HTTP 객체 Decoder      ]
        [Business Logic Handler ]
        [HTTP 객체 Encoder      ]
        [MessageToByte Encoder  ]
       [← 아웃바운드 방향] → 소켓
```

### 기본 Netty 서버 코드

```java
public class SimpleNettyServer {

    public void start(int port) throws InterruptedException {
        NioEventLoopGroup bossGroup = new NioEventLoopGroup(1);
        NioEventLoopGroup workerGroup = new NioEventLoopGroup(); // 기본: CPU × 2

        try {
            ServerBootstrap bootstrap = new ServerBootstrap()
                .group(bossGroup, workerGroup)
                .channel(NioServerSocketChannel.class)
                .option(ChannelOption.SO_BACKLOG, 128)
                .childOption(ChannelOption.SO_KEEPALIVE, true)
                .childHandler(new ChannelInitializer<SocketChannel>() {
                    @Override
                    protected void initChannel(SocketChannel ch) {
                        ch.pipeline()
                            .addLast(new HttpServerCodec())
                            .addLast(new HttpObjectAggregator(65536))
                            .addLast(new SimpleServerHandler());
                    }
                });

            ChannelFuture future = bootstrap.bind(port).sync();
            future.channel().closeFuture().sync();
        } finally {
            bossGroup.shutdownGracefully();
            workerGroup.shutdownGracefully();
        }
    }
}

@ChannelHandler.Sharable
class SimpleServerHandler extends SimpleChannelInboundHandler<FullHttpRequest> {

    @Override
    protected void channelRead0(ChannelHandlerContext ctx, FullHttpRequest request) {
        // EventLoop 스레드에서 실행 — 블로킹 금지!
        ByteBuf content = Unpooled.copiedBuffer("Hello, Netty!", CharsetUtil.UTF_8);
        FullHttpResponse response = new DefaultFullHttpResponse(
            HttpVersion.HTTP_1_1, HttpResponseStatus.OK, content
        );
        response.headers()
            .set(HttpHeaderNames.CONTENT_TYPE, "text/plain")
            .set(HttpHeaderNames.CONTENT_LENGTH, content.readableBytes());
        ctx.writeAndFlush(response);
    }
}
```

### Spring WebFlux + Netty

```java
@RestController
public class ReactiveController {

    private final WebClient webClient = WebClient.create("https://api.example.com");

    @GetMapping("/users/{id}")
    public Mono<UserDto> getUser(@PathVariable Long id) {
        return webClient.get()
            .uri("/users/{id}", id)
            .retrieve()
            .bodyToMono(UserDto.class)
            .map(user -> new UserDto(user.id(), user.name().toUpperCase()))
            .timeout(Duration.ofSeconds(3))
            .onErrorReturn(new UserDto(-1L, "Unknown"));
    }

    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<String> stream() {
        return Flux.interval(Duration.ofSeconds(1))
            .map(i -> "Event: " + i)
            .take(10);
    }
}
```

---

## 스레드 모델 비교

### 동시 연결 처리

**Tomcat (Thread-Per-Request)**
```
1,000 동시 요청 (각 100ms I/O 대기)
├── 스레드 최대 200개 → 나머지 800개는 대기
├── 200개 스레드 모두 BLOCKED 상태
└── 메모리: 200 × 1MB(스택) ≈ 200MB
```

**Netty (Event Loop)**
```
1,000 동시 연결 (각 100ms I/O 대기)
├── EventLoop 스레드 8개 (CPU 4코어 × 2)
├── I/O 대기 중 다른 채널 처리 → 8개로 1,000개 처리 가능
└── 메모리: 8 × 1MB(스택) ≈ 8MB
```

### I/O 바운드 vs CPU 바운드

| 작업 유형 | Tomcat | Netty |
|-----------|--------|-------|
| I/O 바운드 (외부 API, DB) | 스레드 블로킹 → 낭비 | EventLoop가 다른 채널 처리 → 효율적 |
| CPU 바운드 (복잡한 계산) | 자연스러움 | EventLoop 점유 시 다른 채널 지연 → 별도 풀 필요 |

### 처리량 비교 (이론적)

| 시나리오 | Tomcat (200스레드) | Netty (8 EventLoop) |
|----------|-------------------|---------------------|
| 빠른 응답 (<1ms) | 높음 | 더 높음 |
| I/O 대기 (100ms) | ~200 req/s | 수천 req/s |
| CPU 집약 (50ms) | ~4,000 req/s | 비슷 (별도 풀 필요) |
| 대용량 연결 유지 | 스레드 고갈 가능 | 수만 연결 가능 |

---

## Virtual Thread와의 비교 (Java 21+)

### Virtual Thread란

Java 21에서 정식 출시된 경량 스레드다. JVM이 OS 스레드 위에 수백만 개의 가상 스레드를 실행할 수 있다.

```java
// 블로킹 코드를 그대로 작성해도 OS 스레드는 해제됨
Thread.ofVirtual().start(() -> {
    String result = blockingHttpCall(); // 블로킹 발생 시 OS 스레드 언마운트
    process(result);                    // 응답 도착 시 다시 마운트
});
```

**Spring Boot + Virtual Thread 활성화**
```yaml
spring:
  threads:
    virtual:
      enabled: true  # Spring Boot 3.2+
```

### 3가지 모델 비교

| 항목 | Tomcat (플랫폼 스레드) | Netty (리액티브) | Tomcat + Virtual Thread |
|------|----------------------|-----------------|------------------------|
| 프로그래밍 모델 | 동기/블로킹 | 비동기/비블로킹 | 동기/블로킹 |
| 코드 복잡도 | 낮음 | 높음 | 낮음 |
| I/O 바운드 성능 | 낮음 | 매우 높음 | 높음 |
| CPU 바운드 성능 | 보통 | 보통 | 보통 |
| 스택 트레이스 가독성 | 명확 | 복잡(리액티브 체인) | 명확 |
| 메모리 (1만 연결) | ~10GB | ~수십MB | ~수백MB |
| JPA/JDBC 사용 | 자연스러움 | 불가(블로킹) | 자연스러움 |
| 학습 곡선 | 낮음 | 높음 | 낮음 |

### WebFlux에서 블로킹 코드 처리

```java
@Service
public class UserService {

    // JPA(블로킹)를 WebFlux 환경에서 사용할 때
    public Mono<User> findById(Long id) {
        return Mono.fromCallable(() -> userRepository.findById(id).orElseThrow())
            .subscribeOn(Schedulers.boundedElastic()); // 블로킹 작업용 스레드 풀
    }

    // R2DBC(리액티브 DB 드라이버) 사용 시
    public Mono<User> findByIdReactive(Long id) {
        return r2dbcUserRepository.findById(id); // 논블로킹
    }
}
```

---

## 선택 기준

```
Tomcat (플랫폼 스레드)
  → 레거시 코드베이스, JPA 사용, 팀 경험 부족, 단순 CRUD 서비스

Netty (WebFlux)
  → 대용량 실시간 스트리밍, SSE, WebSocket, 극한 성능 필요
  → 팀이 리액티브 프로그래밍에 익숙한 경우

Tomcat + Virtual Thread
  → 신규 프로젝트, I/O 바운드 위주, 비동기 복잡도 없이 성능 개선 원할 때
  → Java 21+, Spring Boot 3.2+ 환경
```

---

## 마치며

Tomcat과 Netty는 각각 다른 문제를 해결하기 위해 설계됐다. Tomcat은 단순함과 안정성을, Netty는 극한의 처리량과 확장성을 추구한다. Java 21의 Virtual Thread 도입으로 Tomcat도 I/O 바운드 시나리오에서 경쟁력을 갖게 됐다. 새 프로젝트라면 Virtual Thread + Tomcat 조합이 학습 비용 대비 성능을 얻기 쉬운 선택이다.
