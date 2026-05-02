---
title: "Nginx 완전 가이드 — 설정부터 성능 최적화까지"
categories:
- SERVER
toc: true
toc_sticky: true
toc_label: 목차
---

## 실생활 비유: 호텔 도어맨

Nginx는 호텔 입구의 **만능 도어맨**입니다. 손님(요청)이 오면 어느 객실(서버)로 안내할지 결정하고, VIP 손님은 특별 처리하고, 너무 많은 손님이 몰리면 정중히 대기를 요청합니다. 음식(정적 파일)은 직접 서빙하고, 특별 요리(동적 콘텐츠)는 주방(WAS)에 주문합니다.

---

## 1. Nginx란?

Nginx(엔진엑스)는 2004년 Igor Sysoev가 개발한 **이벤트 기반 비동기 웹 서버**입니다.

### Apache vs Nginx 구조 차이

```mermaid
graph TD
    subgraph Apache - 프로세스/스레드 기반
        A_Req1[요청1] --> A_Thread1[스레드1 대기 포함]
        A_Req2[요청2] --> A_Thread2[스레드2 대기 포함]
        A_Req3[요청3] --> A_Thread3[스레드3 대기 포함]
        A_Req4[요청4] --> A_Thread4[스레드4 대기 포함]
    end

    subgraph Nginx - 이벤트 기반 비동기
        N_Req1[요청1] --> Worker[Worker 프로세스 1개]
        N_Req2[요청2] --> Worker
        N_Req3[요청3] --> Worker
        N_Req4[요청N] --> Worker
        Worker --> EventLoop[이벤트 루프<br/>I/O 완료 시만 처리]
    end
```

| 특성 | Apache | Nginx |
|------|--------|-------|
| 처리 모델 | 프로세스/스레드 per 요청 | 이벤트 기반 비동기 |
| 동시 연결 | 수천 (메모리 한계) | 수만~수십만 |
| 정적 파일 | 보통 | 매우 빠름 |
| 메모리 사용 | 높음 | 낮음 |
| .htaccess | O | X (성능상 제거) |
| 설정 방식 | 분산 (.htaccess) | 중앙 집중 |

---

## 2. Nginx 아키텍처

```mermaid
graph TD
    OS[운영체제 커널] --> Master[마스터 프로세스<br/>설정 읽기, 워커 관리]
    Master --> W1[워커 프로세스 1<br/>CPU 코어 1]
    Master --> W2[워커 프로세스 2<br/>CPU 코어 2]
    Master --> W3[워커 프로세스 3<br/>CPU 코어 3]
    Master --> W4[워커 프로세스 4<br/>CPU 코어 4]
    Master --> Cache[캐시 관리 프로세스]

    W1 --> EventLoop1[이벤트 루프<br/>수천 개 연결 처리]
    W2 --> EventLoop2[이벤트 루프]
```

### 이벤트 기반 처리 원리

```
전통적 블로킹 방식:
요청 → DB 쿼리 시작 → [100ms 대기...] → 결과 → 응답
       (이 동안 스레드가 아무것도 못함)

Nginx 비동기 방식:
요청 → DB 쿼리 시작 → [다른 요청 처리] → DB 완료 이벤트 → 결과 → 응답
       (대기 시간에 다른 작업 처리!)
```

---

## 3. 핵심 설정 구조

```nginx
# /etc/nginx/nginx.conf

# 전역 설정
user nginx;
worker_processes auto;          # CPU 코어 수만큼 자동 설정
worker_rlimit_nofile 65535;     # 워커당 최대 파일 디스크립터
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 4096;    # 워커당 최대 동시 연결 수
    use epoll;                  # Linux 최적 이벤트 방식
    multi_accept on;            # 한 번에 여러 연결 수락
}

http {
    # MIME 타입
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # 로그 포맷
    log_format main '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent"';

    access_log /var/log/nginx/access.log main;

    # 성능 최적화
    sendfile        on;     # OS 커널 수준 파일 전송
    tcp_nopush      on;     # 패킷 최적화
    tcp_nodelay     on;     # 지연 없이 전송
    keepalive_timeout 65;   # Keep-Alive 타임아웃

    # Gzip 압축
    gzip on;
    gzip_comp_level 5;
    gzip_types text/plain text/css application/json application/javascript;

    # 버퍼 설정
    client_body_buffer_size 16k;
    client_max_body_size 10m;   # 업로드 최대 크기

    # 가상 호스트 포함
    include /etc/nginx/conf.d/*.conf;
}
```

---

## 4. 서버 블록 (Virtual Host)

```nginx
# /etc/nginx/conf.d/example.com.conf

server {
    listen 80;
    listen [::]:80;
    server_name example.com www.example.com;

    # HTTP → HTTPS 리다이렉트
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name example.com www.example.com;

    # SSL 인증서
    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # SSL 보안 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS (HTTP Strict Transport Security)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;

    root /var/www/example.com;
    index index.html index.php;

    # 로그
    access_log /var/log/nginx/example.com.access.log main;
    error_log  /var/log/nginx/example.com.error.log warn;
}
```

---

## 5. Location 블록 심층 분석

```nginx
server {
    # Location 우선순위 (높은 순)
    # 1. = (완전 일치) - 가장 높은 우선순위
    location = /favicon.ico {
        log_not_found off;
        access_log off;
    }

    # 2. ^~ (접두사 일치, 정규식보다 우선)
    location ^~ /images/ {
        root /var/www/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # 3. ~ (정규식, 대소문자 구분)
    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }

    # 4. ~* (정규식, 대소문자 무시)
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff2)$ {
        expires 1y;
        add_header Cache-Control "public";
        access_log off;
    }

    # 5. / (기본 - 가장 낮은 우선순위)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**`try_files` 동작:**
```
try_files $uri $uri/ /index.html;

1. $uri: 파일로 존재하면 반환 (예: /about.html)
2. $uri/: 디렉토리로 존재하면 index 파일 반환
3. /index.html: 위 둘 다 없으면 SPA fallback
```

---

## 6. Reverse Proxy 설정

```mermaid
graph LR
    Client[클라이언트] --> Nginx[Nginx<br/>:80/443]
    Nginx --> NodeApp[Node.js 앱<br/>:3000]
    Nginx --> JavaApp[Spring Boot<br/>:8080]
    Nginx --> PythonApp[FastAPI<br/>:8000]
```

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    # 프록시 기본 설정
    proxy_http_version 1.1;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # WebSocket 지원
    proxy_set_header Upgrade    $http_upgrade;
    proxy_set_header Connection "upgrade";

    # 타임아웃 설정
    proxy_connect_timeout 10s;
    proxy_send_timeout    60s;
    proxy_read_timeout    60s;

    # 버퍼 설정
    proxy_buffering on;
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;

    location / {
        proxy_pass http://127.0.0.1:8080;
    }

    location /api/v2/ {
        proxy_pass http://127.0.0.1:9090;
    }
}
```

---

## 7. 로드밸런싱 설정

```nginx
http {
    # Upstream 그룹 정의
    upstream backend {
        # 기본: 라운드 로빈
        server 10.0.1.1:8080 weight=3;  # 가중치 3
        server 10.0.1.2:8080 weight=2;  # 가중치 2
        server 10.0.1.3:8080 weight=1 backup;  # 장애 시만 사용

        # 서버 상태 설정
        server 10.0.1.4:8080 max_fails=3 fail_timeout=30s;

        # 최소 연결 방식
        # least_conn;

        # IP 해시 방식 (스티키 세션)
        # ip_hash;

        # Keep-Alive 연결 재사용
        keepalive 32;
    }

    upstream api_v2 {
        least_conn;  # 최소 연결 방식
        server 10.0.2.1:9090;
        server 10.0.2.2:9090;
    }

    server {
        location / {
            proxy_pass http://backend;
        }

        location /api/v2/ {
            proxy_pass http://api_v2;
        }
    }
}
```

---

## 8. 캐싱 설정

```nginx
http {
    # 캐시 저장 경로 설정
    proxy_cache_path /var/cache/nginx
        levels=1:2
        keys_zone=my_cache:10m    # 캐시 키 저장 공간 10MB
        max_size=10g              # 최대 캐시 크기 10GB
        inactive=60m              # 60분 미사용 시 제거
        use_temp_path=off;

    server {
        location / {
            proxy_pass http://backend;

            # 캐시 활성화
            proxy_cache my_cache;
            proxy_cache_key "$scheme$request_method$host$request_uri";

            # 캐시 유효 시간 (응답 코드별)
            proxy_cache_valid 200 1h;   # 200 응답: 1시간
            proxy_cache_valid 404 1m;   # 404: 1분

            # 백엔드 오류 시 캐시 사용
            proxy_cache_use_stale error timeout updating http_500 http_502 http_503;

            # 캐시 재갱신 중 이전 캐시 사용
            proxy_cache_background_update on;
            proxy_cache_lock on;

            # 캐시 상태 헤더 추가
            add_header X-Cache-Status $upstream_cache_status;
        }

        # 정적 파일 캐싱
        location ~* \.(css|js|png|jpg|gif|ico|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            add_header Vary "Accept-Encoding";

            # Gzip 사전 압축 파일 사용
            gzip_static on;
        }
    }
}
```

---

## 9. Rate Limiting (속도 제한)

```nginx
http {
    # 요청 속도 제한 Zone 정의
    # rate=10r/s: 초당 10요청
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=3r/m;

    # 연결 수 제한 Zone
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

    server {
        location /api/ {
            # 버스트 20개 허용, nodelay로 즉시 처리
            limit_req zone=api_limit burst=20 nodelay;
            limit_req_status 429;

            proxy_pass http://backend;
        }

        location /auth/login {
            # 분당 3회만 허용 (브루트포스 방지)
            limit_req zone=login_limit burst=5;
            limit_req_status 429;

            proxy_pass http://backend;
        }

        # IP당 최대 10개 동시 연결
        location / {
            limit_conn conn_limit 10;
            proxy_pass http://backend;
        }
    }
}
```

---

## 10. 보안 설정

```nginx
server {
    # 버전 정보 숨기기
    server_tokens off;

    # 보안 헤더
    add_header X-Frame-Options           "SAMEORIGIN" always;
    add_header X-Content-Type-Options    "nosniff" always;
    add_header X-XSS-Protection          "1; mode=block" always;
    add_header Referrer-Policy           "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy   "default-src 'self'; script-src 'self' 'unsafe-inline'" always;
    add_header Permissions-Policy        "camera=(), microphone=(), geolocation=()" always;

    # 악성 요청 차단
    if ($request_method !~ ^(GET|HEAD|POST|PUT|DELETE|PATCH)$) {
        return 405;
    }

    # 특정 User-Agent 차단 (봇/스캐너)
    if ($http_user_agent ~* (sqlmap|nikto|nmap|masscan)) {
        return 403;
    }

    # 숨겨진 파일 접근 차단
    location ~ /\. {
        deny all;
        return 404;
    }

    # 백업 파일 차단
    location ~* \.(bak|config|sql|fla|psd|ini|log|sh|inc|swp|dist)$ {
        deny all;
        return 404;
    }
}
```

---

## 11. 성능 최적화 튜닝

```nginx
# /etc/nginx/nginx.conf 성능 최적화 완전판

worker_processes auto;
worker_cpu_affinity auto;          # CPU 코어 자동 바인딩
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
    accept_mutex off;              # 성능 향상 (Linux 3.9+)
}

http {
    # 파일 전송 최적화
    sendfile           on;
    sendfile_max_chunk 1m;
    tcp_nopush         on;
    tcp_nodelay        on;

    # Keep-Alive 최적화
    keepalive_timeout     65;
    keepalive_requests    10000;   # Keep-Alive당 최대 요청 수

    # 해시 테이블 최적화
    server_names_hash_bucket_size 64;
    types_hash_max_size           2048;

    # 오픈 파일 캐시
    open_file_cache          max=65535 inactive=20s;
    open_file_cache_valid    30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors   on;

    # Gzip 최적화
    gzip                on;
    gzip_vary           on;
    gzip_proxied        any;
    gzip_comp_level     6;        # 1(빠름/낮은압축) ~ 9(느림/높은압축)
    gzip_min_length     1024;    # 1KB 미만은 압축 안함
    gzip_buffers        16 8k;
    gzip_http_version   1.1;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml
        application/rss+xml
        image/svg+xml;

    # 클라이언트 버퍼
    client_body_buffer_size     128k;
    client_max_body_size        100m;
    client_header_buffer_size   1k;
    large_client_header_buffers 4 8k;

    # 타임아웃
    client_body_timeout   12s;
    client_header_timeout 12s;
    send_timeout          10s;
}
```

---

## 12. 모니터링: stub_status

```nginx
server {
    listen 127.0.0.1:8080;  # 내부에서만 접근

    location /nginx_status {
        stub_status on;
        allow 127.0.0.1;
        deny all;
    }
}
```

**출력 예시:**
```
Active connections: 291
server accepts handled requests
 16630948 16630948 31070465
Reading: 6 Writing: 179 Waiting: 106
```

| 항목 | 설명 |
|------|------|
| Active connections | 현재 활성 연결 수 |
| accepts | 수락된 총 연결 수 |
| handled | 처리된 총 연결 수 |
| requests | 처리된 총 요청 수 |
| Reading | 헤더 읽는 중인 연결 |
| Writing | 응답 쓰는 중인 연결 |
| Waiting | Keep-Alive 대기 중 |

---

## 13. HTTP/2 및 gRPC 설정

```nginx
server {
    listen 443 ssl http2;

    # gRPC 백엔드
    location /grpc.service/ {
        grpc_pass grpc://127.0.0.1:50051;

        # gRPC 설정
        grpc_set_header Host            $host;
        grpc_set_header X-Real-IP       $remote_addr;

        # gRPC 타임아웃
        grpc_read_timeout  300s;
        grpc_send_timeout  300s;
    }

    # gRPC-Web (브라우저 지원)
    location /grpc-web/ {
        grpc_pass grpcs://127.0.0.1:50051;
    }
}
```

---

## 14. 극한 시나리오: C10K 문제 해결

**C10K 문제**: 동시에 10,000개 연결을 처리할 수 있는가?

```
Apache (프로세스 기반):
- 연결 1개당 메모리 2MB
- 10,000 연결 = 20GB RAM 필요
- 불가능!

Nginx (이벤트 기반):
- Worker 1개가 10,000 연결 처리
- Worker 4개 = 40,000 동시 연결
- RAM 사용: 10MB 정도
- 가능!
```

**Nginx 최대 성능 설정:**
```nginx
worker_processes 8;           # 8코어 서버
worker_connections 65535;     # 워커당 최대 연결

# 이론적 최대: 8 × 65535 = 524,280 동시 연결
# 실제: OS 파일 디스크립터 한계, 메모리에 따라 제한
```

**OS 튜닝 (sysctl.conf):**
```bash
# 파일 디스크립터 한계 증가
fs.file-max = 2097152

# TCP 연결 설정
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 10
net.ipv4.tcp_keepalive_time = 300
net.ipv4.ip_local_port_range = 1024 65535

# TIME_WAIT 소켓 재사용
net.ipv4.tcp_tw_reuse = 1
```

---

## 완성된 Nginx 설정 (프로덕션 예시)

```nginx
# 전체 아키텍처
# 클라이언트 → Nginx (리버스 프록시) → Spring Boot 앱들

upstream spring_backend {
    least_conn;
    server 10.0.1.1:8080 max_fails=3 fail_timeout=30s;
    server 10.0.1.2:8080 max_fails=3 fail_timeout=30s;
    server 10.0.1.3:8080 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g;
limit_req_zone $binary_remote_addr zone=api_rate:10m rate=100r/s;

server {
    listen 443 ssl http2;
    server_name api.myapp.com;

    ssl_certificate /etc/letsencrypt/live/api.myapp.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.myapp.com/privkey.pem;

    # 보안 헤더
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;

    # API 엔드포인트
    location /api/ {
        limit_req zone=api_rate burst=200 nodelay;

        proxy_pass http://spring_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # GET 요청 캐싱
        proxy_cache api_cache;
        proxy_cache_methods GET;
        proxy_cache_valid 200 5m;
        proxy_cache_bypass $http_authorization;  # 인증 요청은 캐시 안함
        add_header X-Cache-Status $upstream_cache_status;
    }

    # 정적 파일
    location /static/ {
        root /var/www;
        expires 1y;
        add_header Cache-Control "public, immutable";
        gzip_static on;
    }

    # 헬스체크
    location /health {
        return 200 "OK";
        access_log off;
    }
}
```

---

## 핵심 설계 결정 요약

| 설정 | 권장값 | 이유 |
|------|--------|------|
| worker_processes | auto | CPU 코어 수 자동 |
| worker_connections | 4096 | 코어당 적정 연결 수 |
| keepalive_timeout | 65s | 연결 재사용 최대화 |
| gzip_comp_level | 5-6 | 압축률/CPU 균형 |
| proxy_cache | on | 반복 요청 처리 속도 향상 |
| ssl_session_cache | 10m | SSL 핸드셰이크 재사용 |
| open_file_cache | max=65535 | 파일 시스템 I/O 감소 |
