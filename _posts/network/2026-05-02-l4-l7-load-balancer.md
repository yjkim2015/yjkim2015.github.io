---
title: "L4 vs L7 로드밸런서 완전 비교 — OSI 계층부터 AWS ALB/NLB까지"
categories:
- NETWORK
toc: true
toc_sticky: true
toc_label: 목차
---

## 실생활 비유: 택배 분류 센터

L4 로드밸런서는 **주소지만 보고 배달하는 단순 택배 분류기**입니다. 편지 봉투에 "서울시 강남구"라고만 쓰여있으면 강남 지점으로 보냅니다. 내용물이 뭔지 모릅니다.

L7 로드밸런서는 **내용물을 열어보는 스마트 분류기**입니다. "이 소포는 냉동식품이니까 냉장 창고로", "이 서류는 법무팀으로"처럼 내용에 따라 지능적으로 분류합니다.

---

## 1. OSI 7계층 복습

```mermaid
graph TD
    L7["7계층: 애플리케이션 HTTP, HTTPS, FTP, SMTP"]
    L6["6계층: 표현 SSL/TLS, 인코딩"]
    L5["5계층: 세션 세션 관리"]
    L4["4계층: 전송 TCP, UDP, 포트"]
    L3["3계층: 네트워크 IP, 라우팅"]
    L2["2계층: 데이터링크 MAC, 이더넷"]
    L1["1계층: 물리 케이블, 광섬유"]

    L7 --> L6 --> L5 --> L4 --> L3 --> L2 --> L1

    style L4 fill:#ff9999
    style L7 fill:#99ccff
```

| 계층 | 이름 | 프로토콜 | 주소 단위 |
|------|------|---------|---------|
| L7 | 애플리케이션 | HTTP, HTTPS, gRPC | URL, 헤더, 쿠키 |
| L4 | 전송 | TCP, UDP | IP:Port |
| L3 | 네트워크 | IP | IP 주소 |

---

## 2. L4 로드밸런서

### 동작 원리

L4 로드밸런서는 **IP 주소와 포트 번호**만 보고 트래픽을 분산합니다. 패킷 내용(HTTP 헤더, URL 경로 등)을 분석하지 않습니다.

```mermaid
graph TD
    Client["클라이언트<br>192.168.1.100:54321"] -->|TCP SYN| L4LB["L4 로드밸런서<br>10.0.0.1:443"]

    L4LB -->|"IP:Port만 확인"| Decision{"분산 결정"}
    Decision --> S1["서버1<br>10.0.1.1:8080"]
    Decision --> S2["서버2<br>10.0.1.2:8080"]
    Decision --> S3["서버3<br>10.0.1.3:8080"]
```

**L4 동작 과정:**
```
1. 클라이언트 → 로드밸런서 TCP SYN
2. 로드밸런서: 목적지 IP:Port 확인 (패킷 열어보지 않음)
3. NAT(Network Address Translation)으로 목적지 IP 변경
4. 선택된 서버로 전달
5. 서버 응답도 로드밸런서를 거쳐 클라이언트로 전달

처리 속도: 마이크로초 단위 (패킷 분석 없음)
```

### L4 로드밸런서 알고리즘

```mermaid
graph TD
    Algo["L4 분산 알고리즘"]
    Algo --> RR["라운드 로빈<br>순서대로 배정"]
    Algo --> Weighted["가중치 라운드 로빈<br>성능 비례 배정"]
    Algo --> LeastConn["최소 연결<br>연결 수 가장 적은 서버"]
    Algo --> IPHash["IP 해시<br>같은 IP → 같은 서버"]
    Algo --> Random["랜덤"]
```

**IP Hash 상세:**
```python
def ip_hash_select(client_ip: str, servers: list) -> str:
    """같은 클라이언트 IP는 항상 같은 서버로"""
    hash_value = sum(int(octet) for octet in client_ip.split('.'))
    server_index = hash_value % len(servers)
    return servers[server_index]

# 192.168.1.100 → (192+168+1+100) % 3 = 461 % 3 = 2 → 서버3
# 192.168.1.101 → (192+168+1+101) % 3 = 462 % 3 = 0 → 서버1
```

---

## 3. L7 로드밸런서

### 동작 원리

L7 로드밸런서는 **HTTP 헤더, URL 경로, 쿠키, 메서드** 등 애플리케이션 계층 정보를 분석하여 라우팅합니다.

```mermaid
graph TD
    Client["클라이언트"] --> L7LB["L7 로드밸런서<br>HTTP 완전 해석"]

    subgraph "HTTP 분석"
        URL["URL 경로 분석"]
        Header["헤더 분석"]
        Cookie["쿠키 분석"]
        Body["요청 본문 일부"]
    end

    L7LB --> URL
    L7LB --> Header
    L7LB --> Cookie

    URL -->|"/api/*"| APIServer["API 서버 그룹"]
    URL -->|"/images/*"| StaticServer["정적 파일 서버"]
    URL -->|"/video/*"| VideoServer["동영상 서버"]
    Header -->|"X-Version: v2"| NewServer["신버전 서버"]
    Cookie -->|session=ABC| SameServer["기존 연결 서버"]
```

**L7 라우팅 규칙 예시 (Nginx):**
```nginx
http {
    upstream api_servers {
        server api1.example.com:8080 weight=3;
        server api2.example.com:8080 weight=2;
        server api3.example.com:8080 weight=1;
    }

    upstream static_servers {
        server static1.example.com:80;
        server static2.example.com:80;
    }

    upstream video_servers {
        server video1.example.com:8080;
        server video2.example.com:8080;
    }

    server {
        listen 443 ssl;

        # URL 경로 기반 라우팅
        location /api/ {
            proxy_pass http://api_servers;
        }

        location ~* \.(jpg|jpeg|png|gif|css|js)$ {
            proxy_pass http://static_servers;
            proxy_cache_valid 200 1d;
        }

        location /video/ {
            proxy_pass http://video_servers;
            proxy_read_timeout 300s;
        }

        # 헤더 기반 라우팅 (카나리 배포)
        location /api/ {
            if ($http_x_canary = "true") {
                proxy_pass http://canary_servers;
                break;
            }
            proxy_pass http://api_servers;
        }
    }
}
```

---

## 4. L4 vs L7 상세 비교

```mermaid
graph LR
    subgraph L4
        L4F["처리 계층: TCP/UDP"]
        L4S["분산 기준: IP + Port"]
        L4P["처리 속도: 극빠름"]
        L4SSL["SSL: 미처리"]
        L4C["내용 확인: 불가"]
    end

    subgraph L7
        L7F["처리 계층: HTTP/HTTPS"]
        L7S["분산 기준: URL, 헤더, 쿠키"]
        L7P["처리 속도: 빠름"]
        L7SSL["SSL: 처리 가능"]
        L7C["내용 확인: 가능"]
    end
```

| 특성 | L4 (NLB) | L7 (ALB) |
|------|---------|---------|
| 동작 계층 | Transport (TCP/UDP) | Application (HTTP) |
| 분산 기준 | IP, Port | URL, Header, Cookie, Method |
| 처리 속도 | 극히 빠름 (μs) | 빠름 (ms) |
| SSL 종료 | 불가 (Pass-through) | 가능 |
| 스티키 세션 | IP Hash 기반 | 쿠키 기반 (정확) |
| WebSocket | O | O |
| gRPC | O | O (ALB는 gRPC 지원) |
| 헬스체크 | TCP 연결 | HTTP 응답 코드 |
| DDoS 방어 | 제한적 | WAF 연동 가능 |
| 비용 | 낮음 | 높음 |
| 용도 | 게임, 금융, IoT | 웹 앱, REST API, MSA |

---

## 5. SSL/TLS 종료 (Termination)

```mermaid
sequenceDiagram
    participant C as 클라이언트
    participant LB as L7 로드밸런서
    participant S as 백엔드 서버

    Note over C,LB: HTTPS (암호화)
    C->>LB: HTTPS 요청 (암호화됨)
    LB->>LB: SSL 복호화 (인증서 보유)
    Note over LB,S: HTTP (평문, 내부망)
    LB->>S: HTTP 요청 (평문으로 전달)
    S-->>LB: HTTP 응답
    LB->>LB: SSL 암호화
    LB-->>C: HTTPS 응답
```

**SSL 종료의 장점:**
- 백엔드 서버가 SSL 처리 부담 없음
- 인증서를 로드밸런서 한 곳에서만 관리
- 백엔드 서버들 간 암호화 필요 없음 (내부망 신뢰)

**SSL Passthrough (L4):**
```
클라이언트 → L4 LB → 서버
                ↑
        IP:Port만 보고 전달
        SSL 내용 모름, 백엔드가 직접 복호화
```

---

## 6. 헬스체크 (Health Check)

```mermaid
graph TD
    LB["로드밸런서"] -->|"매 5초 체크"| S1["서버1: 정상 ✅"]
    LB -->|"매 5초 체크"| S2["서버2: 정상 ✅"]
    LB -->|"매 5초 체크"| S3["서버3: 장애 ❌"]

    S3 -->|"3회 연속 실패"| Remove["트래픽 제거"]
    S3 -->|"복구 후 2회 성공"| Restore["트래픽 복원"]
```

**L4 헬스체크:**
```
TCP Connect 방식:
로드밸런서가 서버 IP:Port에 TCP 연결 시도
연결 성공 → 정상
연결 실패 / 타임아웃 → 비정상
```

**L7 헬스체크 (더 정확):**
```
HTTP GET /health HTTP/1.1
Host: server1.internal

응답 200 OK → 정상
응답 500, 503, 타임아웃 → 비정상
```

```nginx
# Nginx upstream 헬스체크
upstream backend {
    server 10.0.1.1:8080;
    server 10.0.1.2:8080;
    server 10.0.1.3:8080;

    # Nginx Plus 기능
    health_check interval=5s fails=3 passes=2 uri=/health;
}
```

---

## 7. 스티키 세션 (Sticky Session)

> 로그인 상태 등 세션 정보가 특정 서버에 저장된 경우, 같은 사용자는 같은 서버로 연결되어야 합니다.

```mermaid
graph TD
    User["사용자 - 로그인 상태"]

    User -->|"첫 요청"| LB["L7 로드밸런서"]
    LB --> S1["서버1: 세션 데이터"]
    S1 -->|"쿠키: SERVERID=S1"| User

    User -->|"두 번째 요청 + 쿠키"| LB
    LB -->|"쿠키 확인 → 서버1로!"| S1
```

**쿠키 기반 스티키 세션 (Nginx):**
```nginx
upstream backend {
    sticky cookie srv_id expires=1h domain=.example.com path=/;
    server backend1.example.com;
    server backend2.example.com;
    server backend3.example.com;
}
```

> **권장 사항**: 스티키 세션보다 **외부 세션 저장소(Redis)**를 사용하는 것이 확장성에 유리합니다.

---

## 8. HAProxy 설정 예시

HAProxy는 고성능 L4/L7 로드밸런서입니다.

```
# /etc/haproxy/haproxy.cfg

global
    maxconn 50000
    log /dev/log local0
    stats socket /run/haproxy/admin.sock mode 660

defaults
    mode http
    timeout connect 5s
    timeout client  30s
    timeout server  30s
    option httplog
    option dontlognull

# L7 프론트엔드 (HTTP)
frontend http_front
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/cert.pem  # SSL 종료
    redirect scheme https if !{ ssl_fc }

    # URL 기반 라우팅
    acl is_api path_beg /api/
    acl is_static path_end .jpg .png .css .js
    acl is_admin path_beg /admin/

    use_backend api_backend if is_api
    use_backend static_backend if is_static
    use_backend admin_backend if is_admin
    default_backend web_backend

# 백엔드 그룹들
backend api_backend
    balance roundrobin
    option httpchk GET /health
    server api1 10.0.1.1:8080 check weight 3
    server api2 10.0.1.2:8080 check weight 3
    server api3 10.0.1.3:8080 check weight 2

backend static_backend
    balance leastconn
    server static1 10.0.2.1:80 check
    server static2 10.0.2.2:80 check

backend web_backend
    balance roundrobin
    cookie SERVERID insert indirect nocache
    server web1 10.0.3.1:8080 check cookie web1
    server web2 10.0.3.2:8080 check cookie web2

# L4 프론트엔드 (TCP - 데이터베이스)
frontend mysql_front
    bind *:3306
    mode tcp
    default_backend mysql_backend

backend mysql_backend
    mode tcp
    balance leastconn
    option mysql-check user haproxy
    server db1 10.0.4.1:3306 check
    server db2 10.0.4.2:3306 check backup  # 장애 시만 사용
```

---

## 9. AWS ALB vs NLB

```mermaid
graph TD
    AWS["AWS 로드밸런서"]
    AWS --> ALB["ALB<br>Application Load Balancer<br>L7"]
    AWS --> NLB["NLB<br>Network Load Balancer<br>L4"]
    AWS --> CLB["CLB<br>Classic Load Balancer<br>Legacy"]

    ALB --> A1["HTTP/HTTPS/gRPC"]
    ALB --> A2["URL/헤더 기반 라우팅"]
    ALB --> A3["WAF 연동"]
    ALB --> A4["Lambda 타겟 지원"]
    ALB --> A5["사용자 인증 Cognito"]

    NLB --> N1["TCP/UDP/TLS"]
    NLB --> N2["초고성능 초당 수백만 요청"]
    NLB --> N3["고정 IP 지원"]
    NLB --> N4["게임, 금융, IoT"]
    NLB --> N5["최저 지연시간"]
```

**ALB 라우팅 규칙 (Terraform):**
```hcl
resource "aws_alb_listener_rule" "api_rule" {
  listener_arn = aws_alb_listener.https.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_alb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }
}

resource "aws_alb_listener_rule" "canary_rule" {
  listener_arn = aws_alb_listener.https.arn
  priority     = 50  # 높은 우선순위

  action {
    type = "forward"
    forward {
      target_group {
        arn    = aws_alb_target_group.production.arn
        weight = 90  # 90% 트래픽
      }
      target_group {
        arn    = aws_alb_target_group.canary.arn
        weight = 10  # 10% 카나리
      }
    }
  }

  condition {
    path_pattern {
      values = ["/api/v2/*"]
    }
  }
}
```

**NLB 설정 (고정 IP):**
```hcl
resource "aws_lb" "nlb" {
  name               = "game-nlb"
  internal           = false
  load_balancer_type = "network"

  subnet_mapping {
    subnet_id     = aws_subnet.public_a.id
    allocation_id = aws_eip.nlb_a.id  # 고정 IP
  }

  subnet_mapping {
    subnet_id     = aws_subnet.public_b.id
    allocation_id = aws_eip.nlb_b.id
  }
}

resource "aws_lb_target_group" "game_udp" {
  name     = "game-udp"
  port     = 7777
  protocol = "UDP"  # UDP 게임 서버
  vpc_id   = aws_vpc.main.id

  health_check {
    protocol = "TCP"
    port     = 7777
  }
}
```

---

## 10. 글로벌 로드밸런싱 (GSLB)

```mermaid
graph TD
    User["전세계 사용자"]
    User --> DNS["DNS 서버<br>지리 기반 응답"]

    DNS -->|"한국 사용자"| Seoul["서울 리전<br>ap-northeast-2"]
    DNS -->|"미국 사용자"| Virginia["버지니아 리전<br>us-east-1"]
    DNS -->|"유럽 사용자"| Frankfurt["프랑크푸르트 리전<br>eu-central-1"]

    Seoul --> ALB_Seoul["ALB 서울"]
    Virginia --> ALB_VA["ALB 버지니아"]
    Frankfurt --> ALB_FRA["ALB 프랑크푸르트"]

    subgraph "리전 장애 시"
        Failover["Route53 Health Check<br>→ 자동 다른 리전으로"]
    end
```

---

## 11. 로드밸런서 고가용성

```mermaid
graph TD
    VIP["Virtual IP: 10.0.0.1"]
    VIP --> Active["Active LB<br>실제 처리"]
    Active -.-->|Heartbeat| Standby["Standby LB<br>대기"]

    Active -->|"장애!"| Failover["VRRP/Keepalived<br>VIP 이전"]
    Failover --> Standby
    Standby -->|"새 Active"| Continue["서비스 계속"]
```

**Keepalived 설정 (L4 HA):**
```bash
# /etc/keepalived/keepalived.conf
# Active 노드
vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100        # Active가 더 높은 우선순위
    advert_int 1

    authentication {
        auth_type PASS
        auth_pass secretpassword
    }

    virtual_ipaddress {
        10.0.0.1/24    # 가상 IP (VIP)
    }
}

# Standby 노드
vrrp_instance VI_1 {
    state BACKUP
    interface eth0
    virtual_router_id 51
    priority 90         # 낮은 우선순위
    advert_int 1
    # ... 나머지 동일
}
```

---

## 12. 극한 시나리오: 초당 100만 요청 처리

```mermaid
graph TD
    Traffic["초당 100만 요청"] --> DNS_LB["DNS 라운드로빈<br>여러 LB IP 반환"]

    DNS_LB --> LB1["L7 ALB 1<br>초당 25만"]
    DNS_LB --> LB2["L7 ALB 2<br>초당 25만"]
    DNS_LB --> LB3["L7 ALB 3<br>초당 25만"]
    DNS_LB --> LB4["L7 ALB 4<br>초당 25만"]

    LB1 --> S1_Group["서버 그룹 1<br>10대"]
    LB2 --> S2_Group["서버 그룹 2<br>10대"]
    LB3 --> S3_Group["서버 그룹 3<br>10대"]
    LB4 --> S4_Group["서버 그룹 4<br>10대"]

    subgraph "성능 계산"
        P1["ALB 한 대: ~100만 RPS 한계"]
        P2["NLB 한 대: ~수백만 RPS"]
        P3["여러 ALB: 수평 확장"]
    end
```

---

## 핵심 정리

```mermaid
graph TD
    Q{"어떤 로드밸런서?"}

    Q -->|"초고성능 TCP/UDP<br>게임/금융/IoT"| NLB["NLB L4<br>AWS Network LB<br>HAProxy TCP"]

    Q -->|"HTTP/HTTPS<br>URL 기반 라우팅<br>MSA API 게이트웨이"| ALB["ALB L7<br>AWS Application LB<br>Nginx / HAProxy HTTP"]

    Q -->|"SSL 종료 필요"| ALB
    Q -->|"고정 IP 필요"| NLB
    Q -->|"카나리 배포"| ALB
    Q -->|"WebSocket 대용량"| NLB
```

| 상황 | 추천 |
|------|------|
| 웹 애플리케이션 | L7 (Nginx, ALB) |
| MSA API 라우팅 | L7 (ALB, Traefik) |
| 게임 서버 | L4 (NLB) |
| 데이터베이스 앞단 | L4 (HAProxy TCP) |
| 금융 거래 | L4 (초저지연) |
| 카나리 배포 | L7 (가중치 라우팅) |
| 글로벌 서비스 | DNS GSLB + L7 |
