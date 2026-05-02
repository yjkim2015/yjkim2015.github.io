---
title: "프론트엔드 아키텍처 설계 패턴"
categories:
- FRONTEND
toc: true
toc_sticky: true
toc_label: 목차
---

## 도시 계획처럼 생각하기

좋은 도시는 처음부터 잘 설계되어 있습니다. 주거지역, 상업지역, 공원이 분리되어 있고, 도로 체계가 명확합니다. 반면 무계획적으로 성장한 도시는 교통 체증, 슬럼화, 확장 어려움 등의 문제를 겪습니다.

프론트엔드 아키텍처도 마찬가지입니다. 초반 설계가 프로젝트의 미래를 결정합니다.

---

## 1. 컴포넌트 분리 기준

### 아토믹 디자인

```mermaid
graph TD
    ATOMS["원자 (Atoms)
    Button, Input, Label, Icon"]
    MOLECULES["분자 (Molecules)
    SearchBar = Input + Button
    FormField = Label + Input + Error"]
    ORGANISMS["유기체 (Organisms)
    Header = Logo + Nav + SearchBar
    ProductCard = Image + Title + Price + Button"]
    TEMPLATES["템플릿 (Templates)
    PageLayout = Header + Sidebar + Main"]
    PAGES["페이지 (Pages)
    ProductListPage = Template + Data"]

    ATOMS --> MOLECULES
    MOLECULES --> ORGANISMS
    ORGANISMS --> TEMPLATES
    TEMPLATES --> PAGES

    style ATOMS fill:#e74c3c,color:#fff
    style MOLECULES fill:#f39c12,color:#fff
    style ORGANISMS fill:#2ecc71,color:#fff
    style TEMPLATES fill:#3498db,color:#fff
    style PAGES fill:#9b59b6,color:#fff
```

### 컴포넌트 분리 판단 기준

```mermaid
flowchart TD
    A["컴포넌트 분리 고려"] --> B{"재사용 가능한가?"}
    B -->|예| C[분리]
    B -->|아니오| D{"너무 큰가? (150줄+)"}
    D -->|예| E[기능 단위로 분리]
    D -->|아니오| F{"여러 책임을 갖는가?"}
    F -->|예| G[SRP에 따라 분리]
    F -->|아니오| H["현재 크기 유지"]

    style C fill:#2ecc71,color:#fff
    style E fill:#2ecc71,color:#fff
    style G fill:#2ecc71,color:#fff
    style H fill:#3498db,color:#fff
```

---

## 2. 디렉토리 구조

### Feature-Based 구조 (권장)

```
src/
├── components/          # 공통 UI 컴포넌트 (atoms, molecules)
│   ├── ui/
│   │   ├── Button/
│   │   │   ├── Button.tsx
│   │   │   ├── Button.test.tsx
│   │   │   └── index.ts
│   │   ├── Input/
│   │   └── Modal/
│   └── layout/
│       ├── Header/
│       └── Sidebar/
├── features/            # 기능별 모듈
│   ├── auth/
│   │   ├── components/
│   │   │   ├── LoginForm.tsx
│   │   │   └── RegisterForm.tsx
│   │   ├── hooks/
│   │   │   └── useAuth.ts
│   │   ├── api/
│   │   │   └── authApi.ts
│   │   ├── store/
│   │   │   └── authSlice.ts
│   │   └── index.ts     # 공개 API
│   ├── products/
│   └── orders/
├── pages/               # 라우트 컴포넌트
│   ├── HomePage.tsx
│   └── ProductPage.tsx
├── shared/              # 공유 유틸리티
│   ├── api/
│   │   └── httpClient.ts
│   ├── hooks/
│   │   ├── useDebounce.ts
│   │   └── useLocalStorage.ts
│   ├── utils/
│   │   ├── formatDate.ts
│   │   └── validators.ts
│   └── types/
│       └── common.types.ts
├── store/               # 전역 상태
│   └── index.ts
└── App.tsx
```

---

## 3. API Layer 분리

```mermaid
graph TD
    COMPONENT["컴포넌트"] -->|훅 사용| HOOKS["커스텀 훅"]
    HOOKS -->|데이터 요청| REACT_QUERY["React Query / SWR"]
    REACT_QUERY -->|API 호출| API_LAYER["API Layer"]
    API_LAYER -->|HTTP 요청| HTTP_CLIENT["HTTP 클라이언트 (axios/fetch)"]
    HTTP_CLIENT -->|네트워크| SERVER["백엔드 서버"]

    style API_LAYER fill:#3498db,color:#fff
    style HTTP_CLIENT fill:#f39c12,color:#fff
```

```typescript
// shared/api/httpClient.ts
import axios from 'axios';

const httpClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 10000
});

// 요청 인터셉터
httpClient.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 응답 인터셉터
httpClient.interceptors.response.use(
  response => response.data,
  async error => {
    if (error.response?.status === 401) {
      await refreshToken();
      return httpClient.request(error.config); // 재시도
    }
    return Promise.reject(error);
  }
);

export default httpClient;

// features/products/api/productsApi.ts
import httpClient from '@/shared/api/httpClient';
import type { Product, CreateProductDto } from '../types';

export const productsApi = {
  getAll: (params?: { category?: string; page?: number }) =>
    httpClient.get<Product[]>('/products', { params }),

  getById: (id: string) =>
    httpClient.get<Product>(`/products/${id}`),

  create: (dto: CreateProductDto) =>
    httpClient.post<Product>('/products', dto),

  update: (id: string, dto: Partial<CreateProductDto>) =>
    httpClient.patch<Product>(`/products/${id}`, dto),

  delete: (id: string) =>
    httpClient.delete(`/products/${id}`)
};

// features/products/hooks/useProducts.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productsApi } from '../api/productsApi';

export function useProducts(params?: { category?: string }) {
  return useQuery({
    queryKey: ['products', params],
    queryFn: () => productsApi.getAll(params)
  });
}

export function useCreateProduct() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: productsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    }
  });
}
```

---

## 4. 상태 설계 패턴

```mermaid
graph TD
    STATE["상태 분류"] --> LOCAL["로컬 상태<br/>(컴포넌트 내부)"]
    STATE --> SHARED["공유 상태<br/>(여러 컴포넌트)"]
    STATE --> SERVER["서버 상태<br/>(API 데이터)"]
    STATE --> URL["URL 상태<br/>(라우터 파라미터)"]

    LOCAL --> USESTATE["useState, useReducer"]
    SHARED --> CONTEXT["Context / Zustand"]
    SERVER --> RQ["React Query / SWR"]
    URL --> ROUTER["React Router / Next.js Router"]

    style LOCAL fill:#2ecc71,color:#fff
    style SERVER fill:#e74c3c,color:#fff
```

---

## 5. 에러 처리 전략

```jsx
// ErrorBoundary 컴포넌트
class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // 에러 리포팅 서비스에 전송
    Sentry.captureException(error, { extra: errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <ErrorFallback
          error={this.state.error}
          onReset={() => this.setState({ hasError: false })}
        />
      );
    }
    return this.props.children;
  }
}

// 중첩 ErrorBoundary로 세밀한 에러 처리
function App() {
  return (
    <ErrorBoundary fallback={<GlobalError />}>
      <Layout>
        <ErrorBoundary fallback={<SidebarError />}>
          <Sidebar />
        </ErrorBoundary>
        <ErrorBoundary fallback={<ContentError />}>
          <MainContent />
        </ErrorBoundary>
      </Layout>
    </ErrorBoundary>
  );
}
```

---

## 6. 모노레포 구조

```mermaid
graph TD
    subgraph "모노레포 구조"
        ROOT["root/"]
        ROOT --> APPS["apps/"]
        ROOT --> PACKAGES["packages/"]
        ROOT --> TOOLS["tools/"]

        APPS --> WEB["apps/web (Next.js)"]
        APPS --> MOBILE["apps/mobile (React Native)"]
        APPS --> ADMIN["apps/admin (React)"]

        PACKAGES --> UI["packages/ui (공통 컴포넌트)"]
        PACKAGES --> TYPES["packages/types (공통 타입)"]
        PACKAGES --> UTILS["packages/utils (유틸리티)"]
        PACKAGES --> CONFIG["packages/config (ESLint, TS 설정)"]
    end

    style UI fill:#3498db,color:#fff
    style TYPES fill:#2ecc71,color:#fff
```

```json
// package.json (루트)
{
  "name": "my-monorepo",
  "private": true,
  "workspaces": ["apps/*", "packages/*"],
  "scripts": {
    "build": "turbo run build",
    "dev": "turbo run dev",
    "test": "turbo run test",
    "lint": "turbo run lint"
  },
  "devDependencies": {
    "turbo": "latest",
    "typescript": "^5.0.0"
  }
}

// packages/ui/package.json
{
  "name": "@myapp/ui",
  "exports": {
    ".": "./src/index.ts"
  },
  "dependencies": {
    "react": "^18.0.0"
  }
}

// apps/web에서 사용
// import { Button, Input } from '@myapp/ui';
```

---

## 7. 마이크로 프론트엔드

```mermaid
graph TD
    SHELL["Shell App (앱 컨테이너)"]
    SHELL --> AUTH["Auth MFE<br/>(팀 A)"]
    SHELL --> PRODUCTS["Products MFE<br/>(팀 B)"]
    SHELL --> CART["Cart MFE<br/>(팀 C)"]
    SHELL --> CHECKOUT["Checkout MFE<br/>(팀 D)"]

    AUTH -.->|독립 배포| AUTH
    PRODUCTS -.->|독립 배포| PRODUCTS
    CART -.->|독립 배포| CART

    style SHELL fill:#e74c3c,color:#fff
    style AUTH fill:#3498db,color:#fff
    style PRODUCTS fill:#2ecc71,color:#fff
    style CART fill:#f39c12,color:#fff
```

```javascript
// Module Federation (Webpack 5)
// apps/shell/webpack.config.js
module.exports = {
  plugins: [
    new ModuleFederationPlugin({
      name: 'shell',
      remotes: {
        products: 'products@http://localhost:3001/remoteEntry.js',
        cart: 'cart@http://localhost:3002/remoteEntry.js'
      }
    })
  ]
};

// apps/products/webpack.config.js
module.exports = {
  plugins: [
    new ModuleFederationPlugin({
      name: 'products',
      filename: 'remoteEntry.js',
      exposes: {
        './ProductList': './src/ProductList',
        './ProductDetail': './src/ProductDetail'
      }
    })
  ]
};

// shell에서 사용
const ProductList = lazy(() => import('products/ProductList'));
```

---

## 8. 성능 아키텍처

```mermaid
flowchart LR
    USER["사용자"] --> CDN["CDN<br/>(정적 파일)"]
    USER --> LB["로드 밸런서"]
    LB --> EDGE["Edge Runtime<br/>(미들웨어)"]
    EDGE --> SSR["SSR 서버"]
    SSR --> CACHE["Redis 캐시"]
    SSR --> API["API 서버"]
    API --> DB["데이터베이스"]

    CDN -->|캐시 히트| USER
    CACHE -->|캐시 히트| SSR

    style CDN fill:#2ecc71,color:#fff
    style CACHE fill:#f39c12,color:#fff
```

---

## 9. 타입 안전성

```typescript
// 공통 타입 정의
// packages/types/src/api.types.ts

export type ApiResponse<T> = {
  data: T;
  meta: {
    page: number;
    total: number;
  };
};

export type ApiError = {
  code: string;
  message: string;
  details?: Record<string, string[]>;
};

// 타입 가드
export function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    'message' in error
  );
}

// Zod로 런타임 타입 검증
import { z } from 'zod';

const ProductSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(100),
  price: z.number().positive(),
  category: z.enum(['electronics', 'clothing', 'food']),
  createdAt: z.string().datetime()
});

type Product = z.infer<typeof ProductSchema>;

async function fetchProduct(id: string): Promise<Product> {
  const data = await httpClient.get(`/products/${id}`);
  return ProductSchema.parse(data); // 런타임 검증
}
```

---

## 10. 테스트 아키텍처

```mermaid
graph TD
    subgraph "테스트 피라미드"
        E2E["E2E 테스트 (소수)<br/>Playwright, Cypress"]
        INT["통합 테스트 (중간)<br/>React Testing Library"]
        UNIT["단위 테스트 (다수)<br/>Jest, Vitest"]
    end

    UNIT --> INT
    INT --> E2E

    style E2E fill:#e74c3c,color:#fff
    style INT fill:#f39c12,color:#fff
    style UNIT fill:#2ecc71,color:#fff
```

---

## 11. 극한 시나리오 - 레거시 마이그레이션

```mermaid
flowchart LR
    A["레거시 앱<br/>(jQuery, 스파게티 코드)"]
    B["점진적 마이그레이션"]
    C["현대적 앱<br/>(React, TypeScript)"]

    A -->|"Strangler Fig 패턴"| B
    B --> C

    subgraph "단계별 전환"
        STEP1["1. 공통 UI 컴포넌트 React화"]
        STEP2["2. 새 기능은 React로"]
        STEP3["3. 기존 페이지 점진적 교체"]
        STEP4["4. 레거시 제거"]
    end

    B --> STEP1 --> STEP2 --> STEP3 --> STEP4
```

```javascript
// 레거시 jQuery와 React 공존
// iframe 또는 Custom Element로 격리

// React를 Custom Element로 래핑
class ReactWidget extends HTMLElement {
  connectedCallback() {
    const mountPoint = document.createElement('div');
    this.attachShadow({ mode: 'open' }).appendChild(mountPoint);

    ReactDOM.createRoot(mountPoint).render(
      <React.StrictMode>
        <ReactComponent props={this.dataset} />
      </React.StrictMode>
    );
  }
}

customElements.define('react-widget', ReactWidget);

// 레거시 HTML에서 사용
// <react-widget data-user-id="123"></react-widget>
```

---

## 12. 정리 - 좋은 아키텍처의 원칙

```mermaid
mindmap
  root((좋은 아키텍처))
    관심사 분리
      UI vs 비즈니스 로직
      기능별 모듈화
      API 레이어 분리
    단방향 의존성
      상위 → 하위
      순환 참조 금지
    테스트 용이성
      컴포넌트 순수성
      의존성 주입
    확장 가능성
      Feature Flag
      플러그인 구조
    타입 안전성
      TypeScript
      런타임 검증
```

좋은 프론트엔드 아키텍처의 핵심은 **"변경이 쉬운 구조"**입니다. 비즈니스 요구사항은 항상 바뀌므로, 변경의 영향이 최소화되는 경계를 잘 설정하는 것이 가장 중요합니다.
