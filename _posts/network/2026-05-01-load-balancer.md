---
title: "L4/L7 로드밸런서"
categories: NETWORK
tags: [Load Balancer, L4, L7, Nginx, HAProxy, 헬스체크, 세션]
toc: true
toc_sticky: true
toc_label: 목차
---

## 비유로 시작하기

은행 창구를 생각해보세요. 고객이 몰려오면 안내 직원이 "3번 창구 가세요", "5번 창구 가세요" 하고 안내합니다. 어느 창구가 바쁜지, 어느 창구가 비었는지를 파악해서 최대한 균등하게 배분합니다. 특정 업무(대출)는 특정 창구(전문 창구)로 안내합니다.

로드밸런서(Load Balancer)는 이 안내 직원입니다. 들어오는 네트워크 트래픽을 여러 서버에 분산시켜 **가용성과 성능을 높이는 장치**입니다.

---

## OSI 7계층과 로드밸런서

<div class="mermaid">
graph TD
    L7[L7 Application Layer<br/>HTTP, HTTPS, WebSocket]
    L4[L4 Transport Layer<br/>TCP, UDP]
    L3[L3 Network Layer<br/>IP]
    L2[L2 Data Link Layer<br/>MAC]

    LB_L7[L7 로드밸런서<br/>Nginx, AWS ALB, HAProxy]
    LB_L4[L4 로드밸런서<br/>AWS NLB, HAProxy, LVS]

    L7 --> LB_L7
    L4 --> LB_L4

    style LB_L7 fill:#A9DFBF
    style LB_L4 fill:#AED6F1
</div>

---

## L4 로드밸런서

**TCP/UDP 계층**에서 동작합니다. 패킷의 IP 주소와 포트만 보고 라우팅하며, 패킷 내용(HTTP 헤더, URL)은 보지 않습니다.

### 특징

| 항목 | 내용 |
|------|------|
| 동작 계층 | Transport Layer (L4) |
| 라우팅 기준 | IP + Port |
| 패킷 내용 확인 | 불가 |
| SSL 종료 | 불가 (Pass-through) |
| 처리 속도 | 매우 빠름 |
| 사용 예 | 게임 서버, 실시간 스트리밍, DB 클러스터 |

### 동작 방식

```
클라이언트 → L4 LB (IP: 10.0.0.1, Port: 443)
              ↓ NAT (IP 변환)
         서버 1 (IP: 192.168.1.10, Port: 443)
         서버 2 (IP: 192.168.1.11, Port: 443)
```

패킷의 목적지 IP/포트를 서버 IP/포트로 변환(NAT)하여 전달합니다.

---

## L7 로드밸런서

**Application 계층**에서 동작합니다. HTTP 헤더, URL 경로, 쿠키, 요청 본문까지 분석하여 라우팅합니다.

### 특징

| 항목 | 내용 |
|------|------|
| 동작 계층 | Application Layer (L7) |
| 라우팅 기준 | URL, Host, Header, Cookie |
| 콘텐츠 기반 라우팅 | 가능 |
| SSL 종료 | 가능 (TLS Termination) |
| 처리 속도 | L4보다 느림 |
| 사용 예 | 웹 서비스, 마이크로서비스, API Gateway |

### 콘텐츠 기반 라우팅 예시

```nginx
# Nginx L7 라우팅 예시
upstream order-service {
    server order1:8080;
    server order2:8080;
}

upstream product-service {
    server product1:8080;
    server product2:8080;
}

server {
    listen 80;
    server_name api.example.com;

    # URL 경로 기반 라우팅
    location /api/orders {
        proxy_pass http://order-service;
    }

    location /api/products {
        proxy_pass http://product-service;
    }

    # 헤더 기반 라우팅 (A/B 테스트)
    location /api/experiment {
        if ($http_x_user_segment = "beta") {
            proxy_pass http://beta-service;
        }
        proxy_pass http://stable-service;
    }

    # Host 기반 라우팅
    server_name admin.example.com;
    location / {
        proxy_pass http://admin-service;
    }
}
```

---

## L4 vs L7 비교

<div class="mermaid">
graph LR
    subgraph L4
        C1[클라이언트] -->|TCP:443| L4LB[L4 LB]
        L4LB -->|TCP:443| S1A[서버 1]
        L4LB -->|TCP:443| S1B[서버 2]
        L4LB -->|패킷 내용 모름| NOTE1[IP+Port만 본다]
    end

    subgraph L7
        C2[클라이언트] -->|HTTP GET /api/orders| L7LB[L7 LB]
        L7LB -->|URL 분석| S2A[Order 서버]
        L7LB -->|URL 분석| S2B[Product 서버]
        L7LB -->|헤더/쿠키/URL 분석| NOTE2[콘텐츠 기반 라우팅]
    end
</div>

| 항목 | L4 | L7 |
|------|----|----|
| 속도 | 빠름 | 상대적으로 느림 |
| 유연성 | 낮음 | 높음 |
| SSL 종료 | 서버에서 처리 | LB에서 처리 가능 |
| 로깅 | IP/포트 수준 | HTTP 상세 로깅 |
| 비용 | 낮음 | 높음 |
| 마이크로서비스 | 부적합 | 적합 |

---

## 로드밸런싱 알고리즘

### Round Robin

요청을 순서대로 각 서버에 배분합니다.

```
요청 1 → 서버 A
요청 2 → 서버 B
요청 3 → 서버 C
요청 4 → 서버 A (다시 시작)
```

```nginx
upstream backend {
    server server1:8080;
    server server2:8080;
    server server3:8080;
}
```

적합: 모든 서버 성능이 동일하고 요청 처리 시간이 비슷할 때.

### Weighted Round Robin

서버 성능에 비례하여 더 많은 요청을 배분합니다.

```nginx
upstream backend {
    server server1:8080 weight=5;  # 5/8 트래픽
    server server2:8080 weight=2;  # 2/8 트래픽
    server server3:8080 weight=1;  # 1/8 트래픽
}
```

적합: 서버 스펙이 다를 때 (고성능 서버에 더 많이).

### Least Connections

현재 연결 수가 가장 적은 서버로 보냅니다.

```nginx
upstream backend {
    least_conn;
    server server1:8080;
    server server2:8080;
    server server3:8080;
}
```

적합: 요청 처리 시간이 들쑥날쑥할 때 (파일 업로드, API 응답시간 다양).

### IP Hash

클라이언트 IP를 해시하여 항상 같은 서버로 보냅니다.

```nginx
upstream backend {
    ip_hash;
    server server1:8080;
    server server2:8080;
    server server3:8080;
}
```

적합: 세션 상태가 서버 메모리에 저장될 때 (세션 지속성).

### Least Response Time (HAProxy)

응답 시간이 가장 짧은 서버로 보냅니다.

```haproxy
backend myapp
    balance leastconn
    option httpchk GET /health
    server server1 192.168.1.10:8080 check
    server server2 192.168.1.11:8080 check
```

---

## Nginx 실무 설정

```nginx
# /etc/nginx/nginx.conf
worker_processes auto;  # CPU 코어 수만큼 자동 설정

events {
    worker_connections 65535;  # 워커당 최대 연결 수
    use epoll;                 # Linux epoll 사용 (효율적)
    multi_accept on;
}

http {
    # 업스트림 서버 그룹
    upstream api-servers {
        least_conn;
        keepalive 32;  # 업스트림과 keepalive 연결 유지

        server app1:8080 weight=1 max_fails=3 fail_timeout=30s;
        server app2:8080 weight=1 max_fails=3 fail_timeout=30s;
        server app3:8080 weight=1 max_fails=3 fail_timeout=30s;
        # fail_timeout 동안 max_fails 실패 시 임시 제외
    }

    server {
        listen 80;
        listen 443 ssl http2;
        server_name api.example.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

        # 요청 타임아웃
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # 버퍼 설정
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;

        location / {
            proxy_pass http://api-servers;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 헬스체크 엔드포인트는 로깅 제외
        location /health {
            proxy_pass http://api-servers;
            access_log off;
        }
    }
}
```

---

## 헬스체크 (Health Check)

장애 서버를 자동으로 감지하고 트래픽에서 제외합니다.

### Passive 헬스체크

실제 트래픽 응답으로 판단합니다 (Nginx 기본).

```nginx
upstream backend {
    server server1:8080 max_fails=3 fail_timeout=30s;
    # 30초 안에 3번 실패 → 30초 동안 제외
}
```

### Active 헬스체크 (Nginx Plus / HAProxy)

주기적으로 직접 헬스체크 요청을 보냅니다.

```haproxy
# HAProxy
backend myapp
    option httpchk GET /actuator/health
    http-check expect status 200
    default-server inter 10s rise 2 fall 3
    # 10초마다 체크, 2번 성공 시 복구, 3번 실패 시 제외

    server app1 192.168.1.10:8080 check
    server app2 192.168.1.11:8080 check
```

---

## 세션 지속성 (Session Persistence)

사용자가 같은 서버에 계속 연결되도록 보장합니다.

### 방법 1: IP Hash (Nginx)

같은 IP → 같은 서버. NAT 뒤에 있으면 비효율적입니다.

### 방법 2: 쿠키 기반 (HAProxy)

```haproxy
backend myapp
    cookie SERVER_ID insert indirect nocache
    server app1 192.168.1.10:8080 cookie app1
    server app2 192.168.1.11:8080 cookie app2
    # LB가 쿠키를 심어 다음 요청도 같은 서버로 라우팅
```

### 방법 3: 세션 외부화 (권장)

```
Stateless 서버 + Redis 세션 저장

클라이언트 → 어떤 서버든 OK
서버 → Redis에서 세션 조회

장점: 서버 추가/제거 자유, 서버 장애 시 세션 유지
```

```java
// Spring Session + Redis
@Configuration
@EnableRedisHttpSession(maxInactiveIntervalInSeconds = 1800)
public class SessionConfig {
    // 자동으로 모든 세션을 Redis에 저장
}
```

---

## 극한 시나리오

### 시나리오: 서버 1대 장애 시 503 응답 급증

**원인**: 헬스체크 감지 전에 이미 다수의 요청이 장애 서버로 라우팅

```nginx
# 빠른 장애 감지 설정
upstream backend {
    server app1:8080 max_fails=1 fail_timeout=10s;
    # 1번만 실패해도 10초 제외 (더 공격적)
}

# 재시도 설정 (멱등한 GET 요청에만)
proxy_next_upstream error timeout http_500 http_502 http_503;
proxy_next_upstream_tries 2;  # 최대 2개 서버 시도
proxy_next_upstream_timeout 5s;
```

### 시나리오: 로드밸런서 자체가 SPOF

```
해결: LB도 이중화 (Active-Passive 또는 Active-Active)

Active-Passive:
  LB-1 (Active) ← VIP (가상 IP)
  LB-2 (Standby) → LB-1 장애 시 VIP 인계 (VRRP/Keepalived)

Active-Active:
  DNS Round Robin으로 두 LB에 분산
  → 더 높은 처리량
```

```bash
# Keepalived VRRP 설정 (Active LB)
vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    virtual_ipaddress {
        10.0.0.100/24  # 가상 IP
    }
}
```
