---
title: "프론트엔드 아키텍처"
categories: FRONTEND
tags: [프론트엔드 아키텍처, 컴포넌트 설계, 상태관리, 테스트, 코드스플리팅, 성능최적화]
toc: true
toc_sticky: true
toc_label: 목차
---

## 비유로 시작하기

도시 설계를 생각해보세요. 주거/상업/공업 구역이 명확히 나뉘고, 도로(인터페이스)로 연결됩니다. 상업 구역이 변경되어도 주거 구역은 영향받지 않습니다. 각 건물은 독립적으로 지어지고 수리됩니다.

프론트엔드 아키텍처도 마찬가지입니다. **컴포넌트, 상태, API 통신, 비즈니스 로직을 명확히 분리**하면 유지보수 가능하고 테스트 가능한 코드가 됩니다.

---

## 컴포넌트 설계 원칙

### Atomic Design

<div class="mermaid">
graph LR
    ATOM[Atoms<br/>Button, Input, Icon] -->
    MOL[Molecules<br/>SearchBar, FormField] -->
    ORG[Organisms<br/>Header, ProductList] -->
    TEMP[Templates<br/>ProductPageLayout] -->
    PAGE[Pages<br/>ProductDetailPage]
</div>

```
src/
├── components/
│   ├── atoms/
│   │   ├── Button/
│   │   │   ├── Button.tsx
│   │   │   ├── Button.stories.tsx  (Storybook)
│   │   │   └── Button.test.tsx
│   │   ├── Input/
│   │   └── Badge/
│   ├── molecules/
│   │   ├── SearchBar/
│   │   └── FormField/
│   ├── organisms/
│   │   ├── Header/
│   │   ├── ProductCard/
│   │   └── OrderForm/
│   └── templates/
│       └── MainLayout/
├── pages/ (or app/)
├── hooks/          (Custom Hooks)
├── services/       (API 레이어)
├── store/          (상태 관리)
├── types/          (TypeScript 타입)
└── utils/          (순수 유틸 함수)
```

### 컨테이너-프레젠테이션 패턴

```tsx
// Presentational Component: UI만 담당, 순수함
function ProductCardView({
    name,
    price,
    imageUrl,
    onAddToCart,
    isLoading
}: ProductCardViewProps) {
    return (
        <div className="product-card">
            <img src={imageUrl} alt={name} />
            <h3>{name}</h3>
            <p>₩{price.toLocaleString()}</p>
            <button onClick={onAddToCart} disabled={isLoading}>
                {isLoading ? '처리 중...' : '장바구니 담기'}
            </button>
        </div>
    );
}

// Container Component: 데이터와 로직 담당
function ProductCard({ productId }: { productId: string }) {
    const { data: product } = useProduct(productId);
    const { mutate: addToCart, isLoading } = useAddToCart();

    return (
        <ProductCardView
            name={product.name}
            price={product.price}
            imageUrl={product.imageUrl}
            onAddToCart={() => addToCart(productId)}
            isLoading={isLoading}
        />
    );
}
```

---

## API 레이어 분리

컴포넌트에서 직접 `fetch`를 호출하면 안 됩니다. API 레이어로 분리합니다.

```typescript
// services/api/client.ts (기본 설정)
import axios from 'axios';

const apiClient = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL,
    timeout: 10000,
    headers: { 'Content-Type': 'application/json' }
});

// 요청 인터셉터: 토큰 자동 추가
apiClient.interceptors.request.use((config) => {
    const token = tokenStorage.get();
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});

// 응답 인터셉터: 에러 처리
apiClient.interceptors.response.use(
    response => response,
    async (error) => {
        if (error.response?.status === 401) {
            await refreshToken();
            return apiClient(error.config);  // 재시도
        }
        return Promise.reject(error);
    }
);

export default apiClient;

// services/api/product.ts (도메인별 API)
import apiClient from './client';
import type { Product, ProductListParams } from '@/types/product';

export const productApi = {
    getList: (params: ProductListParams) =>
        apiClient.get<Product[]>('/products', { params }).then(r => r.data),

    getById: (id: string) =>
        apiClient.get<Product>(`/products/${id}`).then(r => r.data),

    create: (data: CreateProductDto) =>
        apiClient.post<Product>('/products', data).then(r => r.data),

    update: (id: string, data: UpdateProductDto) =>
        apiClient.put<Product>(`/products/${id}`, data).then(r => r.data),
};

// hooks/useProduct.ts (React Query와 결합)
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productApi } from '@/services/api/product';

export function useProductList(params: ProductListParams) {
    return useQuery({
        queryKey: ['products', params],
        queryFn: () => productApi.getList(params),
        staleTime: 5 * 60 * 1000,
    });
}

export function useProduct(id: string) {
    return useQuery({
        queryKey: ['product', id],
        queryFn: () => productApi.getById(id),
        enabled: !!id,
    });
}

export function useCreateProduct() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: productApi.create,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['products'] }),
    });
}
```

---

## 상태 관리 전략

상태를 종류에 따라 올바른 곳에 저장합니다.

<div class="mermaid">
graph TD
    STATE[상태 종류]
    STATE --> SERVER[서버 상태<br/>API 데이터<br/>React Query / SWR]
    STATE --> LOCAL[로컬 UI 상태<br/>모달 열기, 입력값<br/>useState]
    STATE --> GLOBAL[전역 클라이언트 상태<br/>유저 세션, 장바구니<br/>Zustand / Redux]
    STATE --> URL[URL 상태<br/>필터, 페이지, 검색어<br/>Next.js searchParams]
</div>

```typescript
// URL 상태 활용 (필터/검색)
// /products?category=electronics&sort=price&page=2

// app/products/page.tsx
export default function ProductsPage({
    searchParams
}: {
    searchParams: { category?: string; sort?: string; page?: string }
}) {
    const params = {
        category: searchParams.category || 'all',
        sort: searchParams.sort || 'latest',
        page: Number(searchParams.page) || 1,
    };

    return <ProductList params={params} />;
}

// 필터 변경 → URL 변경 → 페이지 재렌더링 → 뒤로가기 지원
'use client'
function CategoryFilter({ currentCategory }) {
    const router = useRouter();
    const searchParams = useSearchParams();

    const handleChange = (category: string) => {
        const params = new URLSearchParams(searchParams);
        params.set('category', category);
        params.delete('page');  // 카테고리 변경 시 페이지 리셋
        router.push(`?${params.toString()}`);
    };
    // ...
}
```

---

## 테스트 전략

### 테스트 피라미드

```
          /\
         /E2E\           (소수: Cypress, Playwright)
        /------\
       /통합테스트\        (중간: Testing Library)
      /----------\
     /  단위테스트  \     (다수: Jest, Vitest)
    /--------------\
```

### 단위 테스트 (Jest + Testing Library)

```tsx
// components/Button/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from './Button';

describe('Button', () => {
    it('렌더링된다', () => {
        render(<Button>Click me</Button>);
        expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
    });

    it('클릭 시 onClick이 호출된다', async () => {
        const handleClick = jest.fn();
        render(<Button onClick={handleClick}>Click</Button>);

        await userEvent.click(screen.getByRole('button'));
        expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('disabled 시 클릭이 동작하지 않는다', async () => {
        const handleClick = jest.fn();
        render(<Button onClick={handleClick} disabled>Click</Button>);

        await userEvent.click(screen.getByRole('button'));
        expect(handleClick).not.toHaveBeenCalled();
    });

    it('loading 상태를 표시한다', () => {
        render(<Button loading>Submit</Button>);
        expect(screen.getByRole('button')).toBeDisabled();
        expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });
});
```

### 통합 테스트 (MSW로 API 모킹)

```tsx
// __tests__/ProductDetail.test.tsx
import { setupServer } from 'msw/node';
import { rest } from 'msw';
import { render, screen, waitFor } from '@testing-library/react';
import { ProductDetail } from '@/components/organisms/ProductDetail';

const server = setupServer(
    rest.get('/api/products/:id', (req, res, ctx) => {
        return res(ctx.json({
            id: '1',
            name: '테스트 상품',
            price: 10000,
            stock: 5,
        }));
    })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('상품 정보를 표시한다', async () => {
    render(<ProductDetail productId="1" />);

    expect(screen.getByRole('progressbar')).toBeInTheDocument();

    await waitFor(() => {
        expect(screen.getByText('테스트 상품')).toBeInTheDocument();
        expect(screen.getByText('₩10,000')).toBeInTheDocument();
    });
});

test('재고 없을 때 버튼이 비활성화된다', async () => {
    server.use(
        rest.get('/api/products/:id', (req, res, ctx) =>
            res(ctx.json({ id: '1', name: '테스트', price: 100, stock: 0 }))
        )
    );

    render(<ProductDetail productId="1" />);
    await waitFor(() => {
        expect(screen.getByRole('button', { name: /장바구니/ })).toBeDisabled();
    });
});
```

### E2E 테스트 (Playwright)

```typescript
// e2e/checkout.spec.ts
import { test, expect } from '@playwright/test';

test('상품 구매 플로우', async ({ page }) => {
    // 로그인
    await page.goto('/login');
    await page.fill('[name=email]', 'test@example.com');
    await page.fill('[name=password]', 'password123');
    await page.click('button[type=submit]');

    // 상품 페이지 이동
    await page.goto('/products/1');
    await expect(page.locator('h1')).toBeVisible();

    // 장바구니 담기
    await page.click('text=장바구니 담기');
    await expect(page.locator('.cart-count')).toContainText('1');

    // 결제
    await page.goto('/cart');
    await page.click('text=결제하기');
    await page.fill('[name=card-number]', '4111111111111111');
    await page.click('text=결제 완료');

    await expect(page).toHaveURL('/orders/success');
    await expect(page.locator('.order-id')).toBeVisible();
});
```

---

## 코드 스플리팅 (Code Splitting)

초기 번들 크기를 줄여 로딩 시간을 개선합니다.

```tsx
import dynamic from 'next/dynamic';
import { Suspense, lazy } from 'react';

// Next.js dynamic import
const HeavyChart = dynamic(() => import('@/components/HeavyChart'), {
    loading: () => <ChartSkeleton />,
    ssr: false  // 서버사이드 렌더링 비활성화 (브라우저 API 필요한 경우)
});

// React lazy (App Router 외)
const AdminPanel = lazy(() => import('./AdminPanel'));

function Dashboard({ isAdmin }) {
    return (
        <div>
            <HeavyChart data={data} />  {/* 별도 청크로 분리, 지연 로딩 */}
            {isAdmin && (
                <Suspense fallback={<div>로딩 중...</div>}>
                    <AdminPanel />
                </Suspense>
            )}
        </div>
    );
}
```

### 번들 분석

```bash
# Next.js 번들 분석
npm install @next/bundle-analyzer

# next.config.js
const withBundleAnalyzer = require('@next/bundle-analyzer')({
    enabled: process.env.ANALYZE === 'true',
});
module.exports = withBundleAnalyzer({});

# 분석 실행
ANALYZE=true npm run build
```

---

## 성능 최적화 체크리스트

### Core Web Vitals 목표

| 지표 | 의미 | 목표 |
|------|------|------|
| LCP (Largest Contentful Paint) | 가장 큰 콘텐츠 로드 시간 | < 2.5초 |
| FID (First Input Delay) | 첫 입력 반응 시간 | < 100ms |
| CLS (Cumulative Layout Shift) | 레이아웃 이동 누적 | < 0.1 |
| INP (Interaction to Next Paint) | 상호작용 응답 시간 | < 200ms |

```tsx
// LCP 개선: Hero 이미지 priority 설정
<Image src="/hero.jpg" priority alt="히어로" width={1200} height={600} />

// CLS 개선: 이미지에 명시적 크기 지정
// width, height 속성 없으면 이미지 로드 후 레이아웃 이동 발생

// CLS 개선: 동적 콘텐츠 영역 높이 예약
.card-skeleton { min-height: 200px; }

// FID/INP 개선: 무거운 연산은 Web Worker로 오프로드
const worker = new Worker('/workers/calculation.js');
worker.postMessage({ data: largeData });
worker.onmessage = (e) => setResult(e.data);
```

---

## 극한 시나리오

### 시나리오: 컴포넌트 의존성 순환 (Circular Dependency)

```
ProductCard → useCart → CartContext → ProductCard (순환!)

해결:
1. 의존성 방향을 단방향으로 정리
2. 공통 타입/인터페이스를 별도 파일로 분리
3. 이벤트 기반으로 리팩토링

ProductCard → (이벤트 발행) → CartEventBus → CartContext (단방향)
```

### 시나리오: 전역 상태 과부하

```typescript
// 나쁜 예: 모든 것을 전역 상태에
const globalStore = {
    user: {...},
    theme: 'dark',
    products: [...],       // 서버 상태를 전역 상태에
    cart: [...],
    modalOpen: false,      // UI 로컬 상태를 전역 상태에
    searchQuery: '',       // URL 상태를 전역 상태에
};

// 좋은 예: 상태 종류에 맞는 관리
// 서버 상태 → React Query
// UI 로컬 상태 → useState
// URL 상태 → searchParams/router
// 전역 클라이언트 상태 → Zustand (cart, user)
```
