---
title: "Kubernetes"
categories: CLOUD
tags: [Kubernetes, K8s, Pod, Deployment, Service, HPA, Helm]
toc: true
toc_sticky: true
toc_label: 목차
---

## 비유로 시작하기

대형 물류 센터를 생각해보세요. 수백 명의 작업자(컨테이너)가 있고, 관리자(Kubernetes)가 일을 배분합니다. 작업자가 쓰러지면 다른 작업자가 즉시 대체합니다. 주문량이 많아지면 인력을 더 투입하고, 줄어들면 퇴근시킵니다. 각 작업자에게 맞는 구역(노드)을 배치합니다.

Kubernetes(K8s)는 **컨테이너 오케스트레이션 플랫폼**입니다. 수백 개의 컨테이너를 자동으로 배포, 스케일링, 복구하는 시스템입니다.

---

## 아키텍처

<div class="mermaid">
graph TD
    subgraph Control Plane Master
        API[API Server]
        ETCD[(etcd)]
        SCHED[Scheduler]
        CM[Controller Manager]
        API --> ETCD
        API --> SCHED
        API --> CM
    end

    subgraph Worker Node 1
        KL1[kubelet]
        KP1[kube-proxy]
        C1[Pod: app-1]
        C2[Pod: app-2]
        KL1 --> C1
        KL1 --> C2
    end

    subgraph Worker Node 2
        KL2[kubelet]
        KP2[kube-proxy]
        C3[Pod: app-3]
        KL2 --> C3
    end

    API -->|명령| KL1
    API -->|명령| KL2
</div>

### Control Plane (Master Node)

| 컴포넌트 | 역할 |
|---------|------|
| API Server | 모든 요청의 진입점. kubectl 명령을 받아 처리 |
| etcd | 클러스터 상태를 저장하는 분산 Key-Value DB |
| Scheduler | 새로운 Pod를 어느 Node에 배치할지 결정 |
| Controller Manager | 실제 상태가 원하는 상태와 일치하도록 지속 감시 |

### Worker Node

| 컴포넌트 | 역할 |
|---------|------|
| kubelet | API Server와 통신하며 Pod를 실행/관리 |
| kube-proxy | 네트워크 라우팅 규칙 관리 |
| Container Runtime | containerd, CRI-O (컨테이너 실행) |

---

## 핵심 리소스

### Pod

**가장 작은 배포 단위**. 하나 이상의 컨테이너가 같은 네트워크/스토리지를 공유합니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp-pod
  labels:
    app: myapp
spec:
  containers:
  - name: myapp
    image: myapp:1.0
    ports:
    - containerPort: 8080
    resources:
      requests:
        memory: "256Mi"
        cpu: "250m"
      limits:
        memory: "512Mi"
        cpu: "500m"
    livenessProbe:
      httpGet:
        path: /actuator/health/liveness
        port: 8080
      initialDelaySeconds: 30
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /actuator/health/readiness
        port: 8080
      initialDelaySeconds: 10
      periodSeconds: 5
    env:
    - name: SPRING_PROFILES_ACTIVE
      value: "prod"
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: password
```

Pod는 직접 배포하지 않습니다. Deployment가 Pod를 관리합니다.

### Deployment

**Pod의 선언적 관리**. 원하는 상태(replicas, image 등)를 선언하면 Controller Manager가 맞춰줍니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-deployment
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # 배포 중 최대 추가 Pod 수
      maxUnavailable: 0  # 배포 중 최소 가용 Pod 수 (0 = 무중단)
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:1.1  # 버전 업데이트
        # ... (Pod spec과 동일)
```

```bash
# 배포
kubectl apply -f deployment.yaml

# 배포 상태 확인
kubectl rollout status deployment/myapp-deployment

# 롤백
kubectl rollout undo deployment/myapp-deployment

# 특정 버전으로 롤백
kubectl rollout undo deployment/myapp-deployment --to-revision=2
```

### Service

**Pod에 접근하는 안정적인 엔드포인트**. Pod IP는 재시작마다 변하기 때문에 Service가 필요합니다.

```yaml
# ClusterIP: 클러스터 내부 통신
apiVersion: v1
kind: Service
metadata:
  name: myapp-service
spec:
  type: ClusterIP
  selector:
    app: myapp          # 이 라벨의 Pod들로 트래픽 분산
  ports:
  - port: 80
    targetPort: 8080
---
# NodePort: 외부에서 노드 IP:포트로 접근
apiVersion: v1
kind: Service
metadata:
  name: myapp-nodeport
spec:
  type: NodePort
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8080
    nodePort: 30080   # 30000-32767 범위
---
# LoadBalancer: 클라우드 LB 연동
apiVersion: v1
kind: Service
metadata:
  name: myapp-lb
spec:
  type: LoadBalancer
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8080
```

### ConfigMap & Secret

```yaml
# ConfigMap: 일반 설정
apiVersion: v1
kind: ConfigMap
metadata:
  name: myapp-config
data:
  application.properties: |
    server.port=8080
    spring.datasource.url=jdbc:mysql://mysql-service:3306/mydb
  LOG_LEVEL: "INFO"
---
# Secret: 민감 정보 (base64 인코딩)
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  password: bXlwYXNzd29yZA==  # base64("mypassword")
stringData:
  api-key: "my-api-key-plain"  # stringData는 자동 인코딩
```

---

## 스케줄링

Scheduler가 Pod를 어느 Node에 배치할지 결정하는 과정:

1. **Filtering**: 요구사항을 충족하지 못하는 Node 제거 (CPU/메모리 부족, 테인트 등)
2. **Scoring**: 남은 Node에 점수 부여 (리소스 활용률, 어피니티 등)
3. **Binding**: 가장 높은 점수의 Node에 배치

### Node Affinity

```yaml
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: node-type
            operator: In
            values: ["high-memory"]
```

### Pod Anti-Affinity (고가용성)

```yaml
spec:
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: myapp
        topologyKey: kubernetes.io/hostname
        # 같은 노드에 같은 앱 Pod 2개 배치 금지
```

### Taint & Toleration

```bash
# GPU 노드에 taint 설정 (GPU 작업만 배치)
kubectl taint nodes gpu-node1 gpu=true:NoSchedule
```

```yaml
# GPU 작업 Pod에 toleration 설정
spec:
  tolerations:
  - key: "gpu"
    operator: "Equal"
    value: "true"
    effect: "NoSchedule"
```

---

## HPA (Horizontal Pod Autoscaler)

부하에 따라 **Pod 수를 자동으로 조절**합니다.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp-deployment
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70   # CPU 70% 초과 시 스케일 아웃
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30   # 30초 안정화 후 스케일 아웃
    scaleDown:
      stabilizationWindowSeconds: 300  # 5분 안정화 후 스케일 인
```

---

## Ingress

**클러스터 외부에서 내부 Service로 라우팅**하는 규칙입니다. L7 로드밸런서 역할입니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.example.com
    secretName: api-tls-secret
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /api/orders
        pathType: Prefix
        backend:
          service:
            name: order-service
            port:
              number: 80
      - path: /api/products
        pathType: Prefix
        backend:
          service:
            name: product-service
            port:
              number: 80
```

---

## Helm

Kubernetes 리소스를 **패키지(Chart)로 관리**하는 패키지 매니저입니다.

```bash
# Chart 생성
helm create myapp-chart

# 구조
myapp-chart/
├── Chart.yaml          # 차트 메타데이터
├── values.yaml         # 기본 값
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── hpa.yaml
└── charts/             # 의존 차트
```

```yaml
# values.yaml
replicaCount: 3
image:
  repository: myregistry/myapp
  tag: "1.0.0"
  pullPolicy: IfNotPresent
service:
  type: ClusterIP
  port: 80
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

```bash
# 배포
helm install myapp ./myapp-chart -f values-prod.yaml

# 업그레이드
helm upgrade myapp ./myapp-chart --set image.tag=1.1.0

# 롤백
helm rollback myapp 1

# 릴리즈 목록
helm list -A
```

---

## 실무 운영 명령어

```bash
# 전체 리소스 확인
kubectl get all -n production

# Pod 상태 상세 확인
kubectl describe pod myapp-xxx -n production

# 로그 확인
kubectl logs myapp-xxx -n production -f --previous

# Pod 내부 접속
kubectl exec -it myapp-xxx -n production -- /bin/sh

# 포트 포워딩 (로컬 디버깅)
kubectl port-forward pod/myapp-xxx 8080:8080 -n production

# 리소스 사용량
kubectl top pods -n production
kubectl top nodes

# 강제 재시작
kubectl rollout restart deployment/myapp-deployment -n production
```

---

## 극한 시나리오

### 시나리오: 배포 중 전체 서비스 다운

**원인**: `maxUnavailable: 1`, `minReplicas: 1`인 상태에서 배포 시 잠깐 Pod 0개 상태

**해결**:
```yaml
strategy:
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0  # 배포 중 절대 Pod 수 줄이지 않음
```

### 시나리오: Node 장애 시 Pod 재배치 지연

기본적으로 Node 장애 감지 후 Pod 재배치까지 5분 대기합니다.

```yaml
# 빠른 재배치를 위한 tolerations 튜닝
spec:
  tolerations:
  - key: "node.kubernetes.io/unreachable"
    effect: "NoExecute"
    tolerationSeconds: 30  # 기본 300초 → 30초로 단축
  - key: "node.kubernetes.io/not-ready"
    effect: "NoExecute"
    tolerationSeconds: 30
```
