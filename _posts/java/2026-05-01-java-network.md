---
title: "Java 네트워크 프로그래밍"
categories:
- JAVA
toc: true
toc_sticky: true
toc_label: 목차
---

Java는 소켓부터 HTTP 클라이언트까지 풍부한 네트워크 API를 제공합니다. TCP/UDP 저수준 통신부터 NIO 기반 고성능 서버까지 전체를 상세히 정리합니다.

> **비유:** Java 네트워크 프로그래밍은 우체국 시스템과 같습니다. `Socket`은 두 사람 사이에 놓인 전화선이고, `ServerSocket`은 교환원이 앉아있는 교환대입니다. TCP는 등기우편(배달 확인, 순서 보장)이고, UDP는 엽서(빠르지만 분실 가능)입니다. NIO Selector는 한 명의 교환원이 수백 개의 전화선을 동시에 감시하며 벨이 울리는 회선만 연결해주는 현대식 자동 교환기입니다.

---

## 1. 네트워크 기본 개념

### 1.1 TCP/IP 계층 구조

Java 네트워크 API는 계층 구조에 따라 역할이 나뉩니다. 응용 계층의 `HttpClient`는 HTTP 프로토콜을 추상화하고, 전송 계층의 `Socket`은 TCP/UDP를 직접 다루며, 인터넷 계층의 `InetAddress`는 IP 주소와 DNS를 처리합니다.

```mermaid
graph TD
    A["4. 응용 계층"] --> A1["HTTP, FTP, SMTP, DNS"]
    A --> A2["java.net.http.HttpClient"]
    B["3. 전송 계층"] --> B1["TCP (신뢰성) / UDP (속도)"]
    B --> B2["Socket, ServerSocket (TCP)"]
    B --> B3["DatagramSocket (UDP)"]
    C["2. 인터넷 계층"] --> C1["IP (패킷 라우팅)"]
    C --> C2["InetAddress"]
    D["1. 네트워크 계층"] --> D1["Ethernet, Wi-Fi (OS 처리)"]
    A --> B
    B --> C
    C --> D
```

### 1.2 소켓(Socket)이란?

> **비유:** 소켓은 전화기의 수화기입니다. IP 주소가 전화번호(어느 건물인지)이고, 포트 번호가 내선번호(건물 안 어느 부서인지)입니다. 전화를 걸려면 상대방의 전화번호(IP)와 내선(포트)을 모두 알아야 하고, 양쪽에 수화기(소켓)가 있어야 통화가 가능합니다.

소켓은 네트워크 통신의 끝점(Endpoint)입니다. IP 주소 + 포트 번호로 식별됩니다.

```mermaid
sequenceDiagram
    participant C as 클라이언트(192.168.1.10:54321)
    participant S as ServerSocket(192.168.1.1:8080)
    participant CS as Socket(클라이언트 전용)
    C->>S: TCP 연결 요청 (SYN)
    S->>C: SYN-ACK
    C->>S: ACK (3-way handshake 완료)
    S->>CS: accept() → 새 Socket 생성
    C-->>CS: 데이터 송수신
```

### 1.3 TCP vs UDP

> **비유:** TCP는 택배 서비스입니다. 보내기 전 수취인 확인(3-way handshake), 배송 추적(순서 보장), 분실 시 재발송(재전송)을 해줍니다. UDP는 전단지 살포입니다. 주소지 근처에 뿌리되 누가 받았는지, 순서대로 읽었는지 확인하지 않습니다. 대신 엄청나게 빠르고 한 번에 많은 사람에게 전달(멀티캐스트)할 수 있습니다.

| 항목 | TCP | UDP |
|------|-----|-----|
| 연결 | 연결 지향 (3-way handshake) | 비연결 |
| 신뢰성 | 보장 (재전송, 순서 보장) | 보장 안 함 |
| 속도 | 상대적으로 느림 | 빠름 |
| 용도 | HTTP, FTP, 채팅 | 동영상 스트리밍, DNS, 게임 |
| Java 클래스 | Socket, ServerSocket | DatagramSocket |

---

## 2. InetAddress — IP 주소 다루기

```java
import java.net.*;

// IP 주소 조회
InetAddress local = InetAddress.getLocalHost();
System.out.println("호스트명: " + local.getHostName());
System.out.println("IP 주소: " + local.getHostAddress());

// 도메인 → IP 변환 (DNS 조회)
InetAddress google = InetAddress.getByName("www.google.com");
System.out.println("Google IP: " + google.getHostAddress());

// 여러 IP 주소 (라운드 로빈 DNS)
InetAddress[] addresses = InetAddress.getAllByName("www.google.com");
for (InetAddress addr : addresses) {
    System.out.println(addr.getHostAddress());
}

// IP → 도메인 역조회
InetAddress byIp = InetAddress.getByName("8.8.8.8");
System.out.println("역조회: " + byIp.getHostName());

// 연결 가능 여부 확인
boolean reachable = google.isReachable(3000);  // 3초 타임아웃
System.out.println("연결 가능: " + reachable);

// 주소 타입 확인
System.out.println("루프백: " + local.isLoopbackAddress());
System.out.println("멀티캐스트: " + google.isMulticastAddress());

// IPv4 vs IPv6
InetAddress v4 = InetAddress.getByName("192.168.1.1");
InetAddress v6 = InetAddress.getByName("::1");
System.out.println("IPv4: " + (v4 instanceof Inet4Address));
System.out.println("IPv6: " + (v6 instanceof Inet6Address));
```

---

## 3. Socket / ServerSocket — TCP 통신

> **비유:** `ServerSocket`은 식당의 안내 데스크입니다. 손님(클라이언트)이 오면 `accept()`로 맞이하고, 전담 웨이터(새 Socket)를 배정합니다. 안내 직원은 계속 입구를 지키고, 실제 서빙은 웨이터가 담당합니다. 웨이터가 한 명(단일 스레드)이면 손님이 줄을 서야 하고, 여러 명(스레드풀)이면 동시에 여러 테이블을 서빙할 수 있습니다.

### 동작 원리

`ServerSocket`은 특정 포트에서 연결을 기다립니다. `accept()`는 클라이언트가 연결할 때까지 현재 스레드를 블로킹합니다. 연결이 들어오면 클라이언트 전용 `Socket`을 반환합니다. 이 구조에서 단일 스레드 서버는 한 번에 한 클라이언트만 처리할 수 있으므로 실무에서는 반드시 스레드풀과 함께 사용합니다.

### 3.1 기본 TCP 에코 서버

```java
// 서버
public class EchoServer {
    public static void main(String[] args) throws IOException {
        // 포트 8080에서 대기, backlog=50 (연결 대기 큐 크기)
        try (ServerSocket serverSocket = new ServerSocket(8080, 50)) {
            System.out.println("서버 시작: " + serverSocket.getLocalSocketAddress());

            while (true) {
                Socket clientSocket = serverSocket.accept();  // 블로킹: 클라이언트 대기
                System.out.println("클라이언트 연결: " + clientSocket.getRemoteSocketAddress());

                // 단일 스레드: 한 번에 하나만 처리 (실무에서는 멀티스레드 사용)
                handleClient(clientSocket);
            }
        }
    }

    private static void handleClient(Socket socket) throws IOException {
        try (socket;
             BufferedReader in = new BufferedReader(
                     new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));
             PrintWriter out = new PrintWriter(
                     new BufferedWriter(
                             new OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8)),
                     true)) {  // autoFlush=true

            String line;
            while ((line = in.readLine()) != null) {
                System.out.println("수신: " + line);
                out.println("ECHO: " + line);  // 에코
            }
        }
    }
}
```

### 3.2 기본 TCP 클라이언트

```java
public class EchoClient {
    public static void main(String[] args) throws IOException {
        try (Socket socket = new Socket("localhost", 8080);
             BufferedReader in = new BufferedReader(
                     new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));
             PrintWriter out = new PrintWriter(
                     new BufferedWriter(
                             new OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8)),
                     true);
             Scanner scanner = new Scanner(System.in)) {

            System.out.println("서버에 연결됨: " + socket.getRemoteSocketAddress());

            while (scanner.hasNextLine()) {
                String input = scanner.nextLine();
                if ("quit".equalsIgnoreCase(input)) break;

                out.println(input);           // 서버로 전송
                String response = in.readLine(); // 서버 응답 수신
                System.out.println("서버 응답: " + response);
            }
        }
    }
}
```

### 3.3 소켓 옵션 설정

```java
Socket socket = new Socket();

// 연결 타임아웃 설정 (connect 전에 설정)
socket.connect(new InetSocketAddress("example.com", 80), 5000);  // 5초

// 읽기 타임아웃 (SocketTimeoutException 발생)
socket.setSoTimeout(10000);  // 10초

// TCP_NODELAY: 작은 패킷 즉시 전송 (Nagle 알고리즘 비활성화)
socket.setTcpNoDelay(true);

// SO_KEEPALIVE: 연결 유지 확인 패킷 전송
socket.setKeepAlive(true);

// SO_LINGER: close() 시 데이터 전송 보장 대기
socket.setSoLinger(true, 5);  // 최대 5초 대기

// 수신/송신 버퍼 크기
socket.setReceiveBufferSize(65536);  // 64KB
socket.setSendBufferSize(65536);

// SO_REUSEADDR: 이미 사용 중인 포트 재사용 (서버 재시작 시 유용)
ServerSocket serverSocket = new ServerSocket();
serverSocket.setReuseAddress(true);
serverSocket.bind(new InetSocketAddress(8080));
```

### 3.4 멀티스레드 TCP 서버

```java
public class MultiThreadServer {
    private final ExecutorService threadPool = Executors.newFixedThreadPool(100);

    public void start(int port) throws IOException {
        try (ServerSocket serverSocket = new ServerSocket(port)) {
            System.out.println("멀티스레드 서버 시작: " + port);

            while (!Thread.currentThread().isInterrupted()) {
                Socket clientSocket = serverSocket.accept();
                // 각 클라이언트를 별도 스레드에서 처리
                threadPool.submit(() -> handleClient(clientSocket));
            }
        } finally {
            threadPool.shutdown();
        }
    }

    private void handleClient(Socket socket) {
        try (socket;
             var in = new BufferedReader(new InputStreamReader(
                     socket.getInputStream(), StandardCharsets.UTF_8));
             var out = new PrintWriter(socket.getOutputStream(), true)) {

            String line;
            while ((line = in.readLine()) != null) {
                out.println(processRequest(line));
            }
        } catch (IOException e) {
            System.err.println("클라이언트 처리 오류: " + e.getMessage());
        }
    }

    private String processRequest(String request) {
        return "처리결과: " + request.toUpperCase();
    }

    public static void main(String[] args) throws IOException {
        new MultiThreadServer().start(8080);
    }
}
```

---

## 4. DatagramSocket — UDP 통신

> **비유:** UDP는 편지를 우체통에 넣는 것입니다. 상대방이 받았는지 확인하지 않고(`receive()` 전까지 모름), 편지 여러 통을 보내면 도착 순서가 뒤바뀔 수 있습니다. 대신 봉투(DatagramPacket) 하나에 주소와 내용을 담아 던지면 끝이라 절차가 단순하고 빠릅니다.

UDP는 연결 설정 없이 데이터그램 패킷을 독립적으로 전송합니다. 각 패킷은 독립적으로 라우팅되며 순서가 바뀌거나 유실될 수 있습니다. 그 대신 연결 수립 오버헤드가 없어 레이턴시가 낮습니다.

```mermaid
graph LR
    A["UDP 클라이언트"] -->|"DatagramPacket 전송"| B["UDP 서버 (9090)"]
    B -->|"응답 패킷"| A
    Note1["패킷 유실 가능 (비신뢰성)"]
    Note2["순서 보장 없음"]
    Note3["연결 설정 없음 (빠름)"]
```

```java
// UDP 서버
public class UdpServer {
    public static void main(String[] args) throws IOException {
        try (DatagramSocket socket = new DatagramSocket(9090)) {
            System.out.println("UDP 서버 시작: 9090");
            byte[] buffer = new byte[1024];

            while (true) {
                DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
                socket.receive(packet);  // 블로킹: 패킷 수신 대기

                String received = new String(packet.getData(), 0,
                        packet.getLength(), StandardCharsets.UTF_8);
                System.out.println("수신(" + packet.getAddress() + "): " + received);

                // 응답 전송
                String response = "UDP ECHO: " + received;
                byte[] responseBytes = response.getBytes(StandardCharsets.UTF_8);
                DatagramPacket responsePacket = new DatagramPacket(
                        responseBytes, responseBytes.length,
                        packet.getAddress(), packet.getPort());
                socket.send(responsePacket);
            }
        }
    }
}

// UDP 클라이언트
public class UdpClient {
    public static void main(String[] args) throws IOException {
        try (DatagramSocket socket = new DatagramSocket()) {
            socket.setSoTimeout(5000);  // 5초 타임아웃

            InetAddress serverAddress = InetAddress.getByName("localhost");
            byte[] data = "Hello UDP".getBytes(StandardCharsets.UTF_8);

            // 전송
            DatagramPacket sendPacket = new DatagramPacket(
                    data, data.length, serverAddress, 9090);
            socket.send(sendPacket);

            // 수신
            byte[] buffer = new byte[1024];
            DatagramPacket receivePacket = new DatagramPacket(buffer, buffer.length);
            socket.receive(receivePacket);

            String response = new String(receivePacket.getData(), 0,
                    receivePacket.getLength(), StandardCharsets.UTF_8);
            System.out.println("응답: " + response);
        }
    }
}
```

### 4.1 멀티캐스트 (UDP)

```java
// 멀티캐스트 그룹 주소: 224.0.0.0 ~ 239.255.255.255
InetAddress group = InetAddress.getByName("224.0.0.1");

// 멀티캐스트 수신자 (그룹 참여)
try (MulticastSocket ms = new MulticastSocket(5000)) {
    ms.joinGroup(group);
    byte[] buffer = new byte[1024];
    DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
    ms.receive(packet);
    System.out.println("멀티캐스트 수신: " +
            new String(packet.getData(), 0, packet.getLength()));
    ms.leaveGroup(group);
}

// 멀티캐스트 송신자
try (DatagramSocket ds = new DatagramSocket()) {
    String msg = "멀티캐스트 메시지";
    byte[] data = msg.getBytes(StandardCharsets.UTF_8);
    DatagramPacket packet = new DatagramPacket(data, data.length, group, 5000);
    ds.send(packet);
}
```

---

## 5. URL과 URLConnection

```java
// URL 파싱
URL url = new URL("https://api.example.com:8443/v1/users?page=1&size=10#section");
System.out.println("프로토콜: " + url.getProtocol());  // https
System.out.println("호스트:   " + url.getHost());      // api.example.com
System.out.println("포트:     " + url.getPort());      // 8443
System.out.println("경로:     " + url.getPath());      // /v1/users
System.out.println("쿼리:     " + url.getQuery());     // page=1&size=10
System.out.println("앵커:     " + url.getRef());       // section

// URLConnection으로 HTTP 요청
URL apiUrl = new URL("https://httpbin.org/get");
HttpURLConnection conn = (HttpURLConnection) apiUrl.openConnection();

conn.setRequestMethod("GET");
conn.setRequestProperty("Accept", "application/json");
conn.setConnectTimeout(5000);
conn.setReadTimeout(10000);

int responseCode = conn.getResponseCode();
System.out.println("응답 코드: " + responseCode);

try (BufferedReader reader = new BufferedReader(
        new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {
    String line;
    StringBuilder response = new StringBuilder();
    while ((line = reader.readLine()) != null) {
        response.append(line);
    }
    System.out.println("응답: " + response);
}
conn.disconnect();
```

---

## 6. HttpURLConnection — HTTP 통신

```java
public class HttpUtils {

    // GET 요청
    public static String get(String urlStr) throws IOException {
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");
        conn.setRequestProperty("User-Agent", "JavaApp/1.0");
        conn.setConnectTimeout(5000);
        conn.setReadTimeout(15000);

        try {
            int code = conn.getResponseCode();
            InputStream is = (code >= 400) ? conn.getErrorStream() : conn.getInputStream();

            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(is, StandardCharsets.UTF_8))) {
                return reader.lines().collect(Collectors.joining("\n"));
            }
        } finally {
            conn.disconnect();
        }
    }

    // POST 요청 (JSON body)
    public static String post(String urlStr, String jsonBody) throws IOException {
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
        conn.setRequestProperty("Accept", "application/json");
        conn.setDoOutput(true);  // 요청 body 사용
        conn.setConnectTimeout(5000);
        conn.setReadTimeout(15000);

        // 요청 body 전송
        try (OutputStream os = conn.getOutputStream()) {
            os.write(jsonBody.getBytes(StandardCharsets.UTF_8));
        }

        int code = conn.getResponseCode();
        InputStream is = (code >= 400) ? conn.getErrorStream() : conn.getInputStream();

        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(is, StandardCharsets.UTF_8))) {
            return reader.lines().collect(Collectors.joining("\n"));
        } finally {
            conn.disconnect();
        }
    }
}
```

---

## 7. HttpClient (Java 11+) — 현대적 HTTP 클라이언트

> **비유:** `HttpClient`는 비서입니다. `HttpURLConnection`이 직접 전화를 걸고 끊고 메모하는 것(저수준)이라면, `HttpClient`는 비서에게 "이 URL로 GET 요청 보내줘"라고 지시하면 비서가 연결·요청·응답·정리를 모두 처리합니다. 비동기(`sendAsync`) 모드에서는 비서가 여러 전화를 동시에 걸고 결과만 보고합니다.

Java 11에서 도입된 `java.net.http.HttpClient`는 HTTP/2, WebSocket, 비동기 처리를 지원합니다. `HttpURLConnection`과 달리 불변 빌더 패턴으로 설정하고, `CompletableFuture` 기반의 비동기 API를 제공합니다.

```java
import java.net.http.*;
import java.net.http.HttpResponse.*;

// HttpClient 생성 (재사용 권장 — 내부적으로 커넥션 풀 관리)
HttpClient client = HttpClient.newBuilder()
        .version(HttpClient.Version.HTTP_2)   // HTTP/2 우선
        .followRedirects(HttpClient.Redirect.NORMAL)
        .connectTimeout(Duration.ofSeconds(5))
        .executor(Executors.newFixedThreadPool(10))
        .build();

// 동기 GET 요청
HttpRequest getRequest = HttpRequest.newBuilder()
        .uri(URI.create("https://httpbin.org/get"))
        .header("Accept", "application/json")
        .timeout(Duration.ofSeconds(10))
        .GET()
        .build();

HttpResponse<String> response = client.send(getRequest, BodyHandlers.ofString());
System.out.println("상태 코드: " + response.statusCode());
System.out.println("응답 본문: " + response.body());
System.out.println("응답 헤더: " + response.headers().map());

// 비동기 요청 (CompletableFuture)
CompletableFuture<HttpResponse<String>> futureResponse =
        client.sendAsync(getRequest, BodyHandlers.ofString());

futureResponse
        .thenApply(HttpResponse::body)
        .thenAccept(body -> System.out.println("비동기 응답: " + body))
        .exceptionally(e -> {
            System.err.println("오류: " + e.getMessage());
            return null;
        });

// 여러 요청 병렬 처리
List<URI> uris = List.of(
        URI.create("https://httpbin.org/get"),
        URI.create("https://httpbin.org/ip"),
        URI.create("https://httpbin.org/user-agent")
);

List<CompletableFuture<String>> futures = uris.stream()
        .map(uri -> HttpRequest.newBuilder(uri).build())
        .map(req -> client.sendAsync(req, BodyHandlers.ofString())
                         .thenApply(HttpResponse::body))
        .toList();

CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
        .thenRun(() -> futures.forEach(f ->
                System.out.println(f.join().substring(0, 100))))
        .join();
```

---

## 8. 블로킹 vs 논블로킹 I/O

### 동작 원리 비교

블로킹 I/O는 스레드가 데이터를 기다리는 동안 아무 일도 하지 못합니다. 클라이언트 10,000개를 동시에 처리하려면 10,000개의 스레드가 필요하고(C10K 문제), 스레드 메모리와 컨텍스트 스위칭 비용이 폭발적으로 증가합니다.

NIO Selector는 하나의 스레드가 여러 채널을 감시하다가 이벤트가 발생한 채널만 처리합니다. 비유하자면 블로킹은 "손님마다 직원 한 명이 전담"이고, NIO는 "안내 직원 한 명이 전화벨 울리는 테이블만 달려가는" 구조입니다.

```mermaid
graph TD
    subgraph "블로킹 I/O"
    A["스레드1"] --> A1["read() 대기..."]
    B["스레드2"] --> B1["read() 대기..."]
    C["스레드3"] --> C1["read() 대기..."]
    end
    subgraph "NIO Selector"
    D["스레드1(단일)"] --> E["Selector.select()"]
    E --> F["채널A 처리"]
    E --> G["채널B 처리"]
    E --> H["채널C 처리"]
    end
```

### 8.1 Selector 기반 논블로킹 서버

```java
public class NioServer {
    private final Selector selector;
    private final ServerSocketChannel serverChannel;
    private final Map<SocketChannel, Queue<ByteBuffer>> pendingWrites = new HashMap<>();

    public NioServer(int port) throws IOException {
        selector = Selector.open();

        serverChannel = ServerSocketChannel.open();
        serverChannel.bind(new InetSocketAddress(port));
        serverChannel.configureBlocking(false);
        serverChannel.register(selector, SelectionKey.OP_ACCEPT);

        System.out.println("NIO 서버 시작: " + port);
    }

    public void run() throws IOException {
        while (true) {
            selector.select();  // 이벤트 발생까지 블로킹

            Iterator<SelectionKey> keys = selector.selectedKeys().iterator();
            while (keys.hasNext()) {
                SelectionKey key = keys.next();
                keys.remove();

                if (!key.isValid()) continue;

                if (key.isAcceptable())      handleAccept(key);
                else if (key.isReadable())   handleRead(key);
                else if (key.isWritable())   handleWrite(key);
            }
        }
    }

    private void handleAccept(SelectionKey key) throws IOException {
        ServerSocketChannel server = (ServerSocketChannel) key.channel();
        SocketChannel client = server.accept();
        client.configureBlocking(false);
        client.register(selector, SelectionKey.OP_READ);
        System.out.println("연결 수락: " + client.getRemoteAddress());
    }

    private void handleRead(SelectionKey key) throws IOException {
        SocketChannel client = (SocketChannel) key.channel();
        ByteBuffer buffer = ByteBuffer.allocate(1024);

        int bytesRead = client.read(buffer);
        if (bytesRead == -1) {
            client.close();
            return;
        }

        buffer.flip();
        String received = StandardCharsets.UTF_8.decode(buffer).toString().trim();
        System.out.println("수신: " + received);

        // 쓰기 예약
        ByteBuffer response = StandardCharsets.UTF_8.encode("ECHO: " + received + "\n");
        pendingWrites.computeIfAbsent(client, k -> new LinkedList<>()).add(response);
        key.interestOps(SelectionKey.OP_READ | SelectionKey.OP_WRITE);
    }

    private void handleWrite(SelectionKey key) throws IOException {
        SocketChannel client = (SocketChannel) key.channel();
        Queue<ByteBuffer> queue = pendingWrites.get(client);

        while (queue != null && !queue.isEmpty()) {
            ByteBuffer buf = queue.peek();
            client.write(buf);
            if (buf.hasRemaining()) break;  // 소켓 버퍼 가득 참
            queue.poll();
        }

        if (queue == null || queue.isEmpty()) {
            pendingWrites.remove(client);
            key.interestOps(SelectionKey.OP_READ);  // 쓰기 감시 해제
        }
    }

    public static void main(String[] args) throws IOException {
        new NioServer(8080).run();
    }
}
```

---

## 9. 채팅 서버 예제

### 9.1 멀티스레드 채팅 서버

```java
public class ChatServer {
    private final Set<PrintWriter> clients = ConcurrentHashMap.newKeySet();
    private final ExecutorService pool = Executors.newCachedThreadPool();

    public void start(int port) throws IOException {
        try (ServerSocket server = new ServerSocket(port)) {
            System.out.println("채팅 서버 시작: " + port);
            while (true) {
                Socket socket = server.accept();
                pool.submit(() -> handleClient(socket));
            }
        }
    }

    private void handleClient(Socket socket) {
        PrintWriter out = null;
        try (socket;
             var in = new BufferedReader(new InputStreamReader(
                     socket.getInputStream(), StandardCharsets.UTF_8))) {
            out = new PrintWriter(new BufferedWriter(new OutputStreamWriter(
                    socket.getOutputStream(), StandardCharsets.UTF_8)), true);

            // 닉네임 수신
            out.println("닉네임을 입력하세요:");
            String nickname = in.readLine();
            clients.add(out);
            broadcast("[시스템] " + nickname + "님이 입장했습니다.", null);

            String message;
            while ((message = in.readLine()) != null) {
                broadcast("[" + nickname + "] " + message, null);
            }

            broadcast("[시스템] " + nickname + "님이 퇴장했습니다.", null);
        } catch (IOException e) {
            System.err.println("클라이언트 오류: " + e.getMessage());
        } finally {
            if (out != null) clients.remove(out);
        }
    }

    private void broadcast(String message, PrintWriter exclude) {
        System.out.println(message);
        for (PrintWriter client : clients) {
            if (client != exclude) {
                client.println(message);
            }
        }
    }

    public static void main(String[] args) throws IOException {
        new ChatServer().start(8080);
    }
}
```

---

## 10. 네트워크 프로그래밍 주의사항

### 10.1 타임아웃 반드시 설정

타임아웃을 설정하지 않으면 네트워크가 끊겼을 때 스레드가 영원히 블로킹됩니다. 스레드풀의 모든 스레드가 블로킹되면 서비스 전체가 멈추는 **스레드 고갈(Thread Starvation)** 이 발생합니다.

```java
// 연결 타임아웃 + 읽기 타임아웃 항상 설정
Socket socket = new Socket();
socket.connect(new InetSocketAddress("remote-server.com", 8080), 5_000);  // 연결: 5초
socket.setSoTimeout(30_000);  // 읽기: 30초

// HttpClient
HttpClient client = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(5))
        .build();

HttpRequest request = HttpRequest.newBuilder()
        .uri(URI.create("https://api.example.com"))
        .timeout(Duration.ofSeconds(30))  // 요청 전체 타임아웃
        .build();
```

### 10.2 리소스 반드시 해제

```java
// try-with-resources 항상 사용
try (ServerSocket server = new ServerSocket(8080);
     Socket client = server.accept();
     BufferedReader in = new BufferedReader(
             new InputStreamReader(client.getInputStream()))) {
    // 처리
}  // 자동으로 모두 close()
```

### 10.3 버퍼 관리

```java
// NIO 버퍼 읽기 - 루프로 완전 수신 보장
private String readFully(SocketChannel channel, int expectedLength) throws IOException {
    ByteBuffer buffer = ByteBuffer.allocate(expectedLength);

    while (buffer.hasRemaining()) {
        int read = channel.read(buffer);
        if (read == -1) throw new EOFException("연결이 끊어졌습니다");
    }

    buffer.flip();
    return StandardCharsets.UTF_8.decode(buffer).toString();
}

// 메시지 경계 처리: 길이-값(Length-Value) 프로토콜
private void sendMessage(SocketChannel channel, String message) throws IOException {
    byte[] data = message.getBytes(StandardCharsets.UTF_8);
    ByteBuffer buffer = ByteBuffer.allocate(4 + data.length);
    buffer.putInt(data.length);  // 먼저 길이 전송
    buffer.put(data);
    buffer.flip();

    while (buffer.hasRemaining()) {
        channel.write(buffer);
    }
}
```

**극한 시나리오:** TCP는 스트림 프로토콜이라 "메시지 경계"가 없습니다. 1000바이트 데이터를 한 번에 보내도 수신 측에서는 500+500, 300+700, 1000 등 임의로 나눠 받을 수 있습니다. 길이-값 프로토콜 없이 `readLine()`에만 의존하면 대용량 데이터나 지연이 있는 네트워크에서 데이터가 잘려 읽히는 버그가 발생합니다.

**실무 실수:** `HttpURLConnection`을 사용할 때 `conn.disconnect()`를 `finally`에서 호출하지 않으면 커넥션이 풀에 반환되지 않아 연결 고갈(connection exhaustion)이 발생합니다.

---

<details class="extreme-scenario-details" ontoggle="if(this.open){var ad=this.querySelector('.extreme-scenario-ad');if(ad&&!ad.dataset.loaded){ad.dataset.loaded='1';(adsbygoogle=window.adsbygoogle||[]).push({});}}">
<summary class="extreme-scenario-summary">
<span class="extreme-scenario-icon">🔥</span>
<span class="extreme-scenario-label">극한 시나리오 — 클릭하여 펼치기</span>
<span class="extreme-scenario-toggle"></span>
</summary>
<div class="extreme-scenario-body">
<div class="extreme-scenario-ad" style="text-align:center; margin-bottom:1.5em;">
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="ca-pub-7225106491387870"
     data-ad-slot="0000000000"
     data-ad-format="auto"
     data-full-width-responsive="true"></ins>
</div>
<div class="extreme-scenario-content" markdown="1">

### 시나리오 1: 채팅 서버 (100 TPS, 동시 접속 1,000명)

> **비유:** 100명이 동시에 대화하는 단체 카톡방입니다. 한 명이 메시지를 보내면 나머지 99명에게 전달해야 하는데, 전달이 느리면 대화가 밀리고 빠르면 자연스럽습니다.

- **문제:** 스레드-per-클라이언트 모델에서 동시 접속 1,000명이면 1,000개의 스레드가 필요합니다. 각 스레드가 1MB 스택을 차지하면 1GB의 메모리가 스레드만으로 소진됩니다. 브로드캐스트 시 한 클라이언트의 `write()`가 블로킹되면 나머지 클라이언트에게 메시지 전달이 지연됩니다.
- **해결:** NIO Selector 기반으로 전환하여 스레드 1~2개로 1,000개 연결을 다중화합니다. 쓰기 큐를 채널별로 분리하고, `OP_WRITE` 이벤트가 발생했을 때만 쓰기를 수행합니다.
- **근거:** NIO Selector는 `epoll`/`kqueue` 커널 메커니즘을 활용하므로 이벤트 기반으로 동작하며, 유휴 연결이 리소스를 소비하지 않습니다.

### 시나리오 2: API 게이트웨이 (10K TPS)

> **비유:** 공항 출입국 심사대입니다. 심사관(스레드)이 한 명의 여권을 검사하는 동안(블로킹 I/O) 뒤에 줄 선 수천 명이 기다립니다. 자동 심사대(비동기 HttpClient)를 도입하면 여권 스캔 후 결과를 기다리는 동안 다음 사람의 여권을 받을 수 있습니다.

- **문제:** `HttpURLConnection`으로 외부 API를 호출하는 게이트웨이에서 초당 10,000건 요청이 들어옵니다. 외부 API 응답이 500ms로 느려지면 스레드풀(200개)이 모두 블로킹되어 2초 만에 전체 서비스가 멈춥니다.
- **해결:** `HttpClient.sendAsync()` + `CompletableFuture`로 비동기 전환합니다. 외부 응답을 기다리는 동안 스레드가 다른 요청을 처리할 수 있어 200개 스레드로 10K TPS를 감당합니다. 타임아웃은 요청 레벨(`HttpRequest.timeout`)과 연결 레벨(`connectTimeout`) 모두 설정합니다.
- **근거:** 비동기 모델에서는 스레드가 I/O 대기에 묶이지 않으므로 처리량이 스레드 수가 아닌 CPU 능력에 비례합니다.

### 시나리오 3: 실시간 게임 서버 (100K 동시 연결)

> **비유:** 10만 명이 동시에 참여하는 온라인 게임입니다. 플레이어마다 전담 직원을 두면(스레드-per-연결) 직원 월급(메모리)만으로 파산합니다. 대신 안내 방송 시스템(NIO Selector)으로 움직임이 있는 플레이어만 처리합니다.

- **문제:** 100K 동시 연결에서 스레드-per-연결은 100GB 메모리(스레드당 1MB)가 필요하여 물리적으로 불가능합니다. 게임 패킷은 작지만(수십 바이트) 빈도가 높아(초당 30~60회) TCP Nagle 알고리즘이 작은 패킷을 묶어 지연을 유발합니다.
- **해결:** NIO Selector + `setTcpNoDelay(true)`(Nagle 비활성화) 조합을 사용합니다. 또는 Netty 프레임워크로 이벤트 루프 기반 서버를 구축합니다. UDP를 위치 동기화에 사용하고, TCP는 채팅/거래 등 신뢰성이 필요한 통신에만 사용합니다.
- **근거:** Netty의 EventLoop는 NIO Selector를 추상화하여 연결당 메모리 오버헤드를 수 KB로 줄이며, 100K 연결을 4~8개 스레드로 처리합니다.

---
</div>
</div>
</details>

## 12. 실무에서 자주 하는 실수

### 실수 1: 타임아웃 미설정

```java
// 위험: 타임아웃 없이 연결 → 상대 서버 장애 시 스레드가 영원히 블로킹
Socket socket = new Socket("remote-server.com", 8080);  // 무한 대기 가능!

// 해결: 연결 타임아웃 + 읽기 타임아웃 항상 설정
Socket socket = new Socket();
socket.connect(new InetSocketAddress("remote-server.com", 8080), 5_000);  // 5초
socket.setSoTimeout(30_000);  // 읽기 30초
```

### 실수 2: HttpURLConnection 미해제

```java
// 위험: disconnect() 누락 → 커넥션 풀 고갈
HttpURLConnection conn = (HttpURLConnection) url.openConnection();
String body = readBody(conn.getInputStream());
// conn.disconnect() 호출 안 함 → 커넥션이 풀에 반환되지 않음

// 해결: finally에서 반드시 disconnect()
HttpURLConnection conn = null;
try {
    conn = (HttpURLConnection) url.openConnection();
    return readBody(conn.getInputStream());
} finally {
    if (conn != null) conn.disconnect();
}
```

### 실수 3: TCP 메시지 경계 무시

```java
// 위험: TCP는 스트림이므로 한 번의 write가 한 번의 read에 대응하지 않음
out.write("Hello".getBytes());
out.write("World".getBytes());
// 수신 측에서 "HelloWorld"로 한 번에 읽히거나, "Hel" + "loWorld"로 나뉠 수 있음

// 해결: 길이-값(Length-Value) 프로토콜 사용
ByteBuffer buf = ByteBuffer.allocate(4 + data.length);
buf.putInt(data.length);  // 먼저 길이 전송
buf.put(data);            // 이후 데이터 전송
```

### 실수 4: HttpClient를 매 요청마다 생성

```java
// 위험: 매 요청마다 HttpClient 생성 → 커넥션 풀 재사용 불가, 성능 저하
for (String url : urls) {
    HttpClient client = HttpClient.newHttpClient();  // 매번 새로 생성!
    client.send(request, BodyHandlers.ofString());
}

// 해결: HttpClient 하나를 재사용 (내부적으로 커넥션 풀 관리)
HttpClient client = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(5))
        .build();
for (String url : urls) {
    client.send(buildRequest(url), BodyHandlers.ofString());  // 재사용
}
```

### 실수 5: NIO 버퍼의 flip() 누락

```java
// 위험: write 모드에서 바로 read하면 데이터가 없음
ByteBuffer buffer = ByteBuffer.allocate(1024);
channel.read(buffer);     // 데이터를 buffer에 씀 (position이 앞으로 이동)
// buffer.flip() 빠뜨림!
String data = StandardCharsets.UTF_8.decode(buffer).toString();  // 빈 문자열!

// 해결: 쓰기→읽기 전환 시 반드시 flip()
channel.read(buffer);
buffer.flip();  // position=0, limit=이전 position으로 전환
String data = StandardCharsets.UTF_8.decode(buffer).toString();  // 정상 데이터
```

---

## 13. 면접 포인트

### Q1: TCP와 UDP의 차이점은?

**A:** TCP는 연결 지향 프로토콜로, 3-way handshake로 연결을 수립하고 데이터의 순서 보장과 재전송을 통한 신뢰성을 제공합니다. UDP는 비연결 프로토콜로, 연결 수립 없이 패킷을 독립적으로 전송하므로 순서와 도착을 보장하지 않지만 오버헤드가 적어 빠릅니다. HTTP, 파일 전송 등 신뢰성이 중요한 경우 TCP를, 실시간 스트리밍이나 DNS 조회처럼 속도가 중요한 경우 UDP를 사용합니다.

### Q2: 블로킹 I/O와 NIO의 차이점은?

**A:** 블로킹 I/O는 `read()`/`accept()` 호출 시 데이터가 올 때까지 스레드가 대기합니다. 10,000 연결이면 10,000 스레드가 필요하여 메모리와 컨텍스트 스위칭 비용이 폭발합니다. NIO는 `Selector`가 여러 채널을 감시하다가 이벤트(읽기/쓰기/연결)가 발생한 채널만 처리합니다. 하나의 스레드로 수만 개의 연결을 다중화할 수 있어 C10K 문제를 해결합니다. 단, NIO는 코드 복잡도가 높아 실무에서는 Netty 같은 프레임워크를 주로 사용합니다.

### Q3: HttpURLConnection과 HttpClient의 차이점은?

**A:** `HttpURLConnection`은 Java 1.1부터 존재하는 레거시 API로, 동기 전용이며 커넥션 풀 관리가 수동적입니다. `HttpClient`(Java 11+)는 HTTP/2를 지원하고, 불변 빌더 패턴으로 설정하며, `sendAsync()`를 통한 `CompletableFuture` 기반 비동기 처리를 제공합니다. 또한 내부적으로 커넥션 풀을 자동 관리하므로 인스턴스를 재사용하는 것이 권장됩니다.

### Q4: 네트워크 프로그래밍에서 타임아웃을 설정해야 하는 이유는?

**A:** 타임아웃이 없으면 상대 서버 장애, 네트워크 단절, 방화벽 차단 등의 상황에서 스레드가 무한히 블로킹됩니다. 스레드풀의 모든 스레드가 블로킹되면 새 요청을 받을 수 없는 스레드 고갈(Thread Starvation)이 발생하여 서비스 전체가 멈춥니다. 반드시 연결 타임아웃(connect timeout)과 읽기 타임아웃(read/socket timeout)을 분리하여 설정해야 하며, 비즈니스 요구사항에 맞는 적정값(보통 연결 3~5초, 읽기 10~30초)을 사용합니다.

### Q5: TCP에서 메시지 경계 문제란 무엇이고, 어떻게 해결하나요?

**A:** TCP는 바이트 스트림 프로토콜이므로 "메시지" 단위를 인식하지 않습니다. 1000바이트를 한 번에 `write()`해도 수신 측에서 500+500, 300+700 등 임의로 나뉘어 `read()`될 수 있습니다. 해결 방법은 세 가지입니다. 첫째, 길이-값(Length-Value) 프로토콜로 먼저 데이터 길이(4바이트)를 보내고 이어서 데이터를 보냅니다. 둘째, 구분자 기반(\n 등)으로 `readLine()`을 사용합니다. 셋째, 고정 길이 메시지를 사용합니다. 실무에서는 길이-값 방식이 가장 범용적입니다.

---

## 14. 전체 구조 요약

```mermaid
graph TD
    A["Java 네트워크 API"] --> B["저수준 java.net"]
    A --> C["고성능 java.nio"]
    A --> D["현대적 java.net.http (Java 11+)"]
    B --> B1["InetAddress: IP/DNS"]
    B --> B2["Socket: TCP 클라이언트"]
    B --> B3["ServerSocket: TCP 서버"]
    B --> B4["DatagramSocket: UDP"]
    B --> B5["HttpURLConnection: HTTP (레거시)"]
    C --> C1["SocketChannel: TCP 논블로킹"]
    C --> C2["ServerSocketChannel: TCP 서버 논블로킹"]
    C --> C3["Selector: 멀티플렉싱 이벤트 루프"]
    D --> D1["HttpClient: HTTP/1.1, HTTP/2"]
    D --> D2["비동기 CompletableFuture 지원"]
    E["상황별 권장"] --> E1["간단한 HTTP → HttpClient (Java 11+)"]
    E --> E2["TCP 서버 소규모 → ServerSocket + 스레드풀"]
    E --> E3["TCP 서버 대규모 → NIO Selector 또는 Netty"]
    E --> E4["UDP 통신 → DatagramSocket"]
```
