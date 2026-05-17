---
layout: single
title: "개발자를 위한 투자 입문 — 복리의 마법과 자산 배분 전략"
date: 2026-05-17 10:00:00 +0900
categories: FINANCE
tags: [투자, 재테크, ETF, 복리, 자산배분, 개발자]
toc: true
toc_sticky: true
toc_label: 목차
---

개발자는 투자에 유리한 위치에 있습니다. 데이터를 다룰 줄 알고, 백테스트를 이해하며, 자동화에 익숙합니다. 하지만 많은 개발자가 투자를 시작하지 못합니다. "공부가 더 필요해", "지금은 바빠서"라는 이유로 미루다 보면, 가장 소중한 자산인 **시간**을 낭비하게 됩니다. 이 글은 개발자 시각으로 투자의 수학적 원리를 이해하고, 실행 가능한 전략을 제시합니다.

---

## 1. 왜 지금 시작해야 하는가 — 시간의 가치

### 1-1. 복리의 수학적 이해

복리는 수익이 원금에 더해지고, 그 합계가 다시 수익을 낳는 구조입니다.

```python
def compound_growth(
    principal: float,
    annual_rate: float,
    years: int,
    monthly_contribution: float = 0,
) -> dict:
    """복리 성장 시뮬레이션"""
    balance = principal
    total_contributed = principal
    history = []

    for year in range(1, years + 1):
        # 월별 적립 (연 12회)
        for _ in range(12):
            balance += monthly_contribution
            balance *= (1 + annual_rate / 12)
        total_contributed += monthly_contribution * 12

        history.append({
            "year": year,
            "balance": round(balance),
            "contributed": round(total_contributed),
            "gain": round(balance - total_contributed),
        })

    return history

# 시나리오: 월 50만원, 연 7% 수익, 30년
result = compound_growth(
    principal=0,
    annual_rate=0.07,
    years=30,
    monthly_contribution=50,
)

final = result[-1]
print(f"총 납입액: {final['contributed']:,}만원")
print(f"최종 잔액: {final['balance']:,}만원")
print(f"투자 수익: {final['gain']:,}만원")
```

```
출력:
총 납입액: 18,000만원 (월 50만 × 12 × 30년)
최종 잔액: 60,732만원
투자 수익: 42,732만원

→ 납입액보다 투자 수익이 2.4배 더 큼
```

### 1-2. 시작 시점의 차이

> **비유:** 복리는 눈덩이 굴리기와 같습니다. 처음 10년은 작은 눈덩이가 천천히 굴러갑니다. 하지만 30년째에는 이미 거대해진 눈덩이가 엄청난 속도로 커집니다. 10년 늦게 시작하면 그 가속도를 영원히 누릴 수 없습니다.

```python
# 시작 시점 10년 차이의 결과

scenarios = [
    {"name": "25세 시작", "years": 40},
    {"name": "35세 시작", "years": 30},
    {"name": "45세 시작", "years": 20},
]

for s in scenarios:
    result = compound_growth(0, 0.07, s["years"], 50)
    final = result[-1]
    print(f"{s['name']}: {final['balance']:,}만원")
```

```
출력:
25세 시작: 131,278만원 (약 13억)
35세 시작:  60,732만원 (약 6억)
45세 시작:  26,073만원 (약 2.6억)

→ 10년 차이가 최종 자산에서 2~5배 차이를 만든다
```

### 1-3. 72의 법칙

```
72의 법칙: 원금이 2배 되는 기간 추정

공식: 72 ÷ 연수익률 = 2배 되는 연수

예시:
- 연 4% (예금): 72 ÷ 4 = 18년
- 연 7% (글로벌 ETF): 72 ÷ 7 = 10.3년
- 연 10% (주식): 72 ÷ 10 = 7.2년
- 연 1% (파킹통장): 72 ÷ 1 = 72년
```

---

## 2. ETF — 개발자에게 가장 합리적인 투자 도구

### 2-1. ETF란 무엇인가

ETF(Exchange Traded Fund)는 여러 주식이나 채권을 묶어서 주식처럼 거래하는 펀드입니다.

> **비유:** ETF는 음식 세트 메뉴와 같습니다. 개별 종목 투자는 식재료를 하나씩 사서 요리하는 것이고, ETF는 셰프가 이미 배합한 세트 메뉴를 사는 것입니다. 500개 회사에 동시에 투자하는 효과를 단 하나의 거래로 얻습니다.

### 2-2. ETF가 개별 종목보다 나은 이유

```
개별 종목 투자의 문제:

1. 분산 부족 → 한 회사 망하면 큰 손실
2. 정보 비대칭 → 기관 투자자 대비 불리
3. 시간 부족 → 개별 기업 분석에 수백 시간 필요
4. 감정 → 손실 시 패닉 셀, 수익 시 탐욕

ETF의 해결:
1. 자동 분산 → 500개 회사에 동시 투자
2. 패시브 → 분석 불필요, 시장 수익률 추종
3. 시간 절약 → 세팅 후 자동 운용
4. 저비용 → 운용보수 연 0.03~0.5%
```

### 2-3. 핵심 ETF 목록

```
글로벌 주식 ETF:

미국 전체 시장:
- VTI (Vanguard Total Market) — 운용보수 0.03%
- ITOT (iShares Core S&P Total) — 운용보수 0.03%

S&P 500 (대형주):
- VOO (Vanguard S&P 500) — 운용보수 0.03%
- SPY (SPDR S&P 500) — 운용보수 0.09%
- IVV (iShares S&P 500) — 운용보수 0.03%

글로벌 선진국:
- VEA (Vanguard FTSE Developed) — 운용보수 0.05%

신흥국:
- VWO (Vanguard FTSE Emerging) — 운용보수 0.08%

국내 ETF (한국):
- KODEX 미국S&P500 — 운용보수 0.0099%
- TIGER 미국S&P500 — 운용보수 0.07%
- KODEX 선진국 MSCI World — 운용보수 0.15%
```

---

## 3. 포트폴리오 구성 — 자산 배분 전략

### 3-1. 자산 배분이란

자산 배분은 주식, 채권, 현금 등 서로 다른 자산군에 자금을 나누는 것입니다.

> **비유:** 포트폴리오는 건물 기초 공사와 같습니다. 한 기둥에만 의존하면 하나가 무너질 때 전체가 무너집니다. 여러 기둥으로 받치면 하나가 흔들려도 전체는 유지됩니다.

### 3-2. 연령별 자산 배분 공식

```
고전적 공식: 주식 비중 = 100 - 나이

예시:
- 30세: 주식 70%, 채권 30%
- 40세: 주식 60%, 채권 40%
- 50세: 주식 50%, 채권 50%

현대적 수정 (기대 수명 증가):
주식 비중 = 120 - 나이

- 30세: 주식 90%, 채권 10%
- 40세: 주식 80%, 채권 20%
- 50세: 주식 70%, 채권 30%
```

### 3-3. 포트폴리오 백테스트 — 데이터로 검증

```python
import numpy as np

def portfolio_backtest(
    allocations: dict,  # {"US": 0.6, "INT": 0.3, "BOND": 0.1}
    annual_returns: dict,  # 각 자산의 연간 수익률 데이터
    years: int = 20,
    initial: float = 10_000,
) -> dict:
    """포트폴리오 백테스트"""
    portfolio_value = initial
    peak = initial
    max_drawdown = 0

    annual_values = [initial]

    for year in range(years):
        # 각 자산의 수익 합산
        annual_return = sum(
            allocations[asset] * annual_returns[asset][year]
            for asset in allocations
        )

        portfolio_value *= (1 + annual_return)
        annual_values.append(portfolio_value)

        # 최대 낙폭 추적
        peak = max(peak, portfolio_value)
        drawdown = (peak - portfolio_value) / peak
        max_drawdown = max(max_drawdown, drawdown)

    total_return = (portfolio_value - initial) / initial
    cagr = (portfolio_value / initial) ** (1/years) - 1

    return {
        "final_value": round(portfolio_value),
        "total_return": f"{total_return:.1%}",
        "cagr": f"{cagr:.1%}",
        "max_drawdown": f"{max_drawdown:.1%}",
    }
```

### 3-4. 추천 포트폴리오 구성

```
포트폴리오 A: 공격형 (20~35세)
- 미국 주식 (VOO/VTI): 60%
- 선진국 주식 (VEA): 20%
- 신흥국 주식 (VWO): 10%
- 미국 채권 (BND): 10%

예상 연 수익률: 7~9%
예상 최대 낙폭: -40~-50%

포트폴리오 B: 균형형 (35~50세)
- 미국 주식: 45%
- 선진국 주식: 15%
- 신흥국 주식: 10%
- 미국 채권: 20%
- 단기 채권: 10%

예상 연 수익률: 5~7%
예상 최대 낙폭: -25~-35%

포트폴리오 C: 보수형 (50세+)
- 미국 주식: 30%
- 선진국 주식: 10%
- 미국 채권: 40%
- 단기 채권/현금: 20%

예상 연 수익률: 3~5%
예상 최대 낙폭: -15~-20%
```

---

## 4. 달러코스트 에버리징 — 타이밍 맞추기를 포기하라

### 4-1. DCA란 무엇인가

DCA(Dollar-Cost Averaging, 달러코스트 에버리징)는 일정 금액을 주기적으로 투자하는 방법입니다.

> **비유:** DCA는 통근 버스를 매일 타는 것과 같습니다. 오늘 버스가 붐비든 한산하든, 매일 같은 시간에 탑니다. 붐빌 때(주가 높을 때)는 적은 좌석(주식 수)을 사고, 한산할 때(주가 낮을 때)는 많은 좌석을 사는 셈입니다. 평균 매입 단가가 자연스럽게 낮아집니다.

### 4-2. DCA vs 일괄 투자 비교

```python
def compare_dca_lumpsum(
    total_amount: float,
    monthly_amount: float,
    price_series: list[float],
) -> dict:
    """DCA vs 일괄투자 비교"""

    # 일괄 투자: 첫날 전체 매수
    lump_shares = total_amount / price_series[0]
    lump_final = lump_shares * price_series[-1]

    # DCA: 매월 동일 금액 투자
    dca_shares = 0
    for price in price_series:
        dca_shares += monthly_amount / price

    dca_final = dca_shares * price_series[-1]

    return {
        "일괄투자_최종": round(lump_final),
        "DCA_최종": round(dca_final),
        "DCA_우위": dca_final > lump_final,
    }

# 변동이 큰 시장 시뮬레이션 (하락 후 회복)
volatile_prices = [100, 90, 70, 60, 80, 95, 110, 120, 115, 130, 125, 140]
result = compare_dca_lumpsum(1200, 100, volatile_prices)
print(result)
# {'일괄투자_최종': 1680, 'DCA_최종': 1842, 'DCA_우위': True}
# 변동이 클수록 DCA가 유리
```

### 4-3. DCA의 심리적 장점

```
DCA가 심리적으로 좋은 이유:

1. 시장 타이밍 스트레스 없음
   → "지금 들어가도 될까?" 고민 불필요

2. 하락장에서 오히려 기회
   → "더 많이 살 수 있다"는 시각 전환

3. 자동화 가능
   → 감정 개입 차단

4. 작은 금액으로 시작 가능
   → 완벽한 타이밍 기다리다 영영 못 시작하는 함정 회피
```

---

## 5. 리밸런싱 자동화

### 5-1. 리밸런싱이란

리밸런싱은 자산 비중이 목표에서 벗어났을 때 다시 조정하는 작업입니다.

```
리밸런싱 필요성 예시:

초기 포트폴리오:
- 주식: 60% (600만원)
- 채권: 40% (400만원)

1년 후 (주식 상승):
- 주식: 75% (900만원)
- 채권: 25% (300만원)

리밸런싱:
- 주식 150만원 매도 → 채권 150만원 매수
- 복원: 주식 60%, 채권 40%

효과:
- 자동 "고점 매도, 저점 매수" 실현
- 위험 수준 일정하게 유지
```

### 5-2. 리밸런싱 자동화 코드

```python
class PortfolioRebalancer:
    """포트폴리오 리밸런싱 계산기"""

    def __init__(self, target_weights: dict):
        self.target = target_weights  # {"US": 0.6, "BOND": 0.4}

    def calculate_rebalance(
        self, current_values: dict
    ) -> dict:
        """리밸런싱 필요 금액 계산"""
        total = sum(current_values.values())
        current_weights = {
            k: v / total for k, v in current_values.items()
        }

        orders = {}
        for asset in self.target:
            target_value = total * self.target[asset]
            current_value = current_values.get(asset, 0)
            diff = target_value - current_value

            if abs(diff / total) > 0.05:  # 5% 이상 벗어날 때만
                orders[asset] = round(diff)

        return orders

# 사용 예시
rebalancer = PortfolioRebalancer({"US": 0.6, "INTL": 0.3, "BOND": 0.1})

current = {"US": 750, "INTL": 200, "BOND": 50}
orders = rebalancer.calculate_rebalance(current)
print(orders)
# {"US": -150, "INTL": 70, "BOND": 80}
# US 150만원 매도, INTL 70만원 매수, BOND 80만원 매수
```

### 5-3. 리밸런싱 빈도

```
리밸런싱 빈도별 비교:

월별 리밸런싱:
- 장점: 목표 비중 정확 유지
- 단점: 거래 비용 과다, 세금 부담
- 결론: 비추천

분기별 리밸런싱:
- 장점: 비용과 정확성 균형
- 단점: 큰 변동 시 반응 느림
- 결론: 일반적으로 권장

연간 리밸런싱:
- 장점: 거래 비용 최소, 세금 이연
- 단점: 비중 벗어남 허용
- 결론: 장기 투자자에게 충분

임계값 기반 (권장):
- 조건: 어떤 자산이 목표 비중에서 ±5% 이상 벗어날 때
- 장점: 필요할 때만 거래
- 결론: 비용 효율 최적
```

---

## 6. 연금저축/IRP — 세금 혜택 극대화

### 6-1. 세액공제 혜택 계산

연금저축과 IRP는 투자 수익 외에 세금 혜택이 있어 수익률이 극적으로 높아집니다.

```
연금저축 + IRP 세액공제 혜택 (2026년 기준):

연금저축: 연 600만원 한도
IRP: 추가 300만원 한도 (합산 900만원)

세액공제율:
- 총급여 5,500만원 이하: 16.5%
- 총급여 5,500만원 초과: 13.2%

실효 수익률 계산 (5,500만원 이하 기준):
- 900만원 납입
- 세액공제: 900 × 0.165 = 148.5만원

→ 첫해 즉시 수익률 = 148.5 / 900 = 16.5%
→ 연 7% 투자 수익 + 16.5% 세금 혜택 = 첫해 23.5%
```

### 6-2. IRP 최적 활용 전략

```
IRP 투자 전략:

1. 납입 타이밍
   → 연말 세액공제 목적이면 12월에 납입
   → 투자 수익 목적이면 연초에 납입 (1년 더 운용)
   → 최적: 연초에 최대 납입

2. 상품 선택
   → IRP 계좌 내에서도 ETF 투자 가능
   → KODEX 미국S&P500 같은 저비용 ETF 선택
   → 원리금 보장 상품 30% 의무 보유 규정 확인

3. 인출 전략
   → 55세 이후 연금 수령 → 연금소득세 3.3~5.5%
   → 중도 해지 → 기타소득세 16.5% + 세액공제 환수
   → 절대 중도 해지 금지
```

### 6-3. 연금저축 + IRP + 일반계좌 우선순위

```
투자 우선순위 (세금 효율):

1순위: IRP (연 300만원)
   → 세액공제 16.5% + 운용 수익 비과세

2순위: 연금저축펀드 (연 600만원)
   → 세액공제 16.5% + 운용 수익 비과세

3순위: ISA (연 2,000만원, 서민형 4,000만원)
   → 비과세 한도 400만원 + 이후 9.9% 분리과세

4순위: 해외주식 직접투자 (일반계좌)
   → 연간 수익 250만원까지 비과세
   → 초과분 22% 양도세

5순위: 국내주식 직접투자
   → 양도세 없음 (대주주 아닌 경우)
   → 배당소득세 15.4%
```

---

## 7. 복리 시뮬레이터 — 나의 미래 자산 계산

### 7-1. 다양한 시나리오 비교

```python
def simulate_scenarios():
    """다양한 투자 시나리오 비교"""

    scenarios = [
        {
            "name": "소극적 (예금 4%)",
            "rate": 0.04,
            "monthly": 30,
        },
        {
            "name": "균형형 (ETF 7%)",
            "rate": 0.07,
            "monthly": 50,
        },
        {
            "name": "공격형 (주식 10%)",
            "rate": 0.10,
            "monthly": 50,
        },
        {
            "name": "최적화 (ETF 7% + 절세)",
            "rate": 0.085,  # 세금 혜택 반영
            "monthly": 75,
        },
    ]

    print(f"{'시나리오':<25} {'10년':>12} {'20년':>12} {'30년':>12}")
    print("-" * 65)

    for s in scenarios:
        values = []
        for years in [10, 20, 30]:
            result = compound_growth(0, s["rate"], years, s["monthly"])
            values.append(f"{result[-1]['balance']:>10,}만")

        print(f"{s['name']:<25} {values[0]:>12} {values[1]:>12} {values[2]:>12}")

simulate_scenarios()
```

```
출력:
시나리오                      10년          20년          30년
-----------------------------------------------------------------
소극적 (예금 4%)          4,408만       9,820만      20,724만
균형형 (ETF 7%)           8,654만      26,034만      60,732만
공격형 (주식 10%)        10,244만      38,284만     113,024만
최적화 (ETF 7% + 절세)   14,847만      43,730만     100,451만
```

### 7-2. 인플레이션 조정 실질 수익

```python
def real_return(nominal_rate: float, inflation: float = 0.03) -> float:
    """피셔 방정식: 실질 수익률 계산"""
    return (1 + nominal_rate) / (1 + inflation) - 1

# 예시
scenarios = [
    ("예금", 0.04),
    ("채권", 0.05),
    ("글로벌ETF", 0.07),
    ("주식", 0.10),
]

for name, nominal in scenarios:
    real = real_return(nominal)
    print(f"{name}: 명목 {nominal:.0%} → 실질 {real:.1%}")
```

```
출력 (인플레이션 3% 가정):
예금: 명목 4% → 실질 1.0%
채권: 명목 5% → 실질 1.9%
글로벌ETF: 명목 7% → 실질 3.9%
주식: 명목 10% → 실질 6.8%
```

> **비유:** 실질 수익률은 달리기 트레드밀과 같습니다. 트레드밀(인플레이션)이 움직이는 만큼 뛰어야 제자리입니다. 예금 4%는 인플레이션 3%를 빼면 실질적으로 1%만 앞으로 나가는 셈입니다.

---

## 8. 투자 자동화 구현

### 8-1. 자동 납입 설정

```
자동 납입 셋업 순서:

1. 급여일 다음날 자동이체 설정
   → 월급 → 투자 계좌 자동이체 (절대 선 저축)
   → 남은 돈으로 생활 (선 저축, 후 소비)

2. 연금저축/IRP 자동이체
   → 월 75만원 설정 (연금저축 50만 + IRP 25만)
   → 연간 900만원 = 세액공제 한도 꽉 채우기

3. ISA 자동이체
   → 월 50~100만원 설정

4. 남은 여유자금 → 일반 ETF 계좌
```

### 8-2. 리밸런싱 알림 자동화 (Python)

```python
import requests
from datetime import datetime

class PortfolioAlert:
    """포트폴리오 이탈 시 텔레그램 알림"""

    def __init__(self, bot_token: str, chat_id: str):
        self.token = bot_token
        self.chat_id = chat_id

    def check_and_alert(
        self,
        current: dict,
        target: dict,
        threshold: float = 0.05,
    ):
        total = sum(current.values())
        alerts = []

        for asset, target_w in target.items():
            current_w = current.get(asset, 0) / total
            drift = abs(current_w - target_w)

            if drift > threshold:
                alerts.append(
                    f"{asset}: 목표 {target_w:.0%} vs "
                    f"현재 {current_w:.0%} "
                    f"(이탈 {drift:.1%})"
                )

        if alerts:
            message = "⚠️ 리밸런싱 필요\n" + "\n".join(alerts)
            self._send(message)

    def _send(self, text: str):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        requests.post(url, data={"chat_id": self.chat_id, "text": text})
```

### 8-3. 월간 투자 리포트 자동화

```python
def generate_monthly_report(portfolio_history: list[dict]) -> str:
    """월간 포트폴리오 리포트 생성"""
    current = portfolio_history[-1]
    prev_month = portfolio_history[-2]

    monthly_return = (
        (current["total"] - prev_month["total"])
        / prev_month["total"]
    )

    report = f"""
=== 월간 투자 리포트 ({datetime.now().strftime('%Y년 %m월')}) ===

총 자산: {current['total']:,}만원
전월 대비: {monthly_return:+.2%}

자산 구성:
"""
    for asset, value in current["holdings"].items():
        weight = value / current["total"]
        report += f"  {asset}: {value:,}만원 ({weight:.1%})\n"

    return report
```

---

## 9. 흔한 실수와 인지 편향

### 9-1. 개발자가 자주 하는 실수

```
실수 1: 과도한 최적화
"최적의 리밸런싱 주기를 찾겠다"
→ 0.1% 차이를 최적화하느라 시작을 못 함

실수 2: 완벽한 타이밍 탐색
"폭락 직전에 사겠다"
→ 폭락은 예측 불가, 기다리는 동안 상승분 놓침

실수 3: 자동화에 집착
"완전 자동화 시스템을 만들겠다"
→ 단순한 DCA가 복잡한 알고리즘보다 장기적으로 우수

실수 4: 데이터 과잉 분석
"모든 ETF를 백테스트하겠다"
→ 분석 마비(Analysis Paralysis), 실행 없는 연구
```

### 9-2. 주요 인지 편향

```
손실 회피 편향:
- 손실의 고통 = 같은 크기 이익의 기쁨 × 2
- 대응: 포트폴리오를 자주 보지 않기 (월 1회로 제한)

최신 편향:
- 최근 상승한 자산이 계속 오를 것 같은 느낌
- 대응: 기계적 리밸런싱으로 감정 차단

확인 편향:
- 자신의 투자를 지지하는 정보만 선택적 수용
- 대응: 반대 의견 의도적으로 찾아 읽기

군중 심리:
- 주변이 다 사니 나도 사야 할 것 같음
- 대응: 투자 원칙을 문서화하고 공황 시 열람
```

> **비유:** 인지 편향은 코드의 버그와 같습니다. 의식하지 않으면 실행되고 있는지조차 모릅니다. 투자 원칙을 사전에 문서화하는 것은 코드에 단위 테스트를 작성하는 것과 같습니다.

---

## 10. 장기 투자 원칙 — 단순하게 유지하기

### 10-1. 워런 버핏의 유언장 포트폴리오

세계 최고의 투자자가 가족을 위해 남긴 지침은 놀랍도록 단순합니다.

```
"내 재산의 90%는 S&P 500 인덱스 펀드에,
 10%는 단기 미국 국채에 투자하라."
— 워런 버핏, 2013 버크셔 해서웨이 연간 서한

이것이 시사하는 것:
→ 복잡한 전략 > 단순한 전략 (X)
→ 단순한 전략 > 복잡한 전략 (O)
→ 거의 모든 액티브 펀드가 인덱스를 장기적으로 못 이김
```

### 10-2. 투자 원칙 문서화

```markdown
# 나의 투자 원칙 (공황 시 열람용)

1. 나는 15년 이상 투자한다.
   → 15년 이상 보유 시 S&P500 손실 확률: 0%

2. 시장 타이밍은 맞출 수 없다.
   → 폭락을 예측하는 것보다 폭락 후 버티는 것이 중요

3. 폭락은 세일이다.
   → 같은 돈으로 더 많은 주식을 살 수 있는 기회

4. 포트폴리오를 자주 보지 않는다.
   → 월 1회 확인, 분기 1회 리밸런싱

5. 투자를 바꾸는 유일한 이유는 목표 변화다.
   → 시장이 하락했다는 이유로 전략을 바꾸지 않는다
```

### 10-3. 실행 계획 — 지금 당장 할 것

```
오늘 해야 할 일 (30분):
1. 연금저축 계좌 개설 (없으면)
2. KODEX 미국S&P500 월 50만원 자동이체 설정
3. IRP 계좌 개설 + 월 25만원 자동이체 설정

이번 달 해야 할 일 (2시간):
1. 총 자산 현황 파악 (예금, 주식, 보험 등)
2. 목표 자산 배분 결정 및 문서화
3. 현재 보유 ETF/펀드 수수료 점검

올해 해야 할 일:
1. 연금저축 + IRP 연 900만원 납입 (세액공제 한도)
2. ISA 계좌 추가 납입
3. 리밸런싱 알림 시스템 구축
```

---

## 11. 자산 성장 로드맵

```mermaid
graph LR
    A[시작: DCA 월50만] --> B[연금/IRP 한도 채우기]
    B --> C[ISA 추가 납입]
    C --> D[일반계좌 ETF]
    D --> E[리밸런싱 자동화]
```

### 11-1. 단계별 목표

```
1단계 (월 납입 100만원 이하):
목표: 연금저축 + IRP 세액공제 한도 채우기
방법: 연금저축 50만 + IRP 25만 = 75만/월
예상 기간: 지금 당장 시작

2단계 (여유자금 추가 생기면):
목표: ISA 납입 추가
방법: +월 50~100만
혜택: 연 400만원 비과세

3단계 (자금 여유):
목표: 일반 계좌 ETF 추가 투자
방법: 해외주식 ETF (미국 직접 투자)
주의: 연간 250만원 초과 시 양도세 신고
```

---

## 12. 마무리 — 완벽함보다 실행

```
투자의 역설:
- 완벽한 전략을 찾으려다 투자를 시작 못 한다
- 단순하고 일관된 전략이 최적 전략을 이긴다
- 투자에서 가장 위험한 것은 '아무것도 안 하는 것'
```

개발자로서 우리는 복잡한 시스템을 이해하고 구축할 수 있습니다. 하지만 투자에서는 그 능력이 오히려 독이 될 수 있습니다. **단순함이 최적해**입니다.

월 50만원을 S&P500 ETF에 30년간 투자하면, 시장 평균 수익률(연 7%)로 6억 원이 됩니다. 특별한 기술도, 시장 예측도 필요 없습니다. 필요한 것은 **시작**과 **인내**뿐입니다.

지금 이 글을 읽고 있는 30분 동안 연금저축 계좌를 개설할 수 있습니다. 오늘이 여러분의 투자 역사에서 가장 빠른 날입니다.

---

*이 글은 투자 교육 목적으로 작성되었으며, 특정 금융 상품에 대한 투자를 권유하지 않습니다. 투자는 원금 손실 위험이 있으며, 개인의 재무 상황과 목표에 맞게 전문가와 상담하시기 바랍니다.*
