# Investigation Blueprint: Profitability Diagnostics

## 1. Actual Problem

Apex Global's revenue has grown for 18 months, but profit margins are shrinking. That is dangerous because revenue growth can hide broken unit economics. If the company keeps scaling the same behavior, it may spend more money acquiring orders, discount more heavily to maintain growth, and subsidize operational costs that each new sale makes worse.

The business risk is not simply "lower margin." The real risk is that leadership may reward growth channels, product categories, customer segments, or discount strategies that are destroying value under the surface.

## 2. Metrics That Matter Beyond Revenue

Revenue alone answers, "How much did customers buy?" It does not answer whether the company should want more of those purchases.

The core metrics for this diagnosis are:

| Metric | Why it matters |
|---|---|
| Gross revenue | Shows headline sales volume before discounts and costs. |
| Discount amount and discount percent | Reveals whether growth is being bought through margin-eroding incentives. |
| Net revenue | Shows revenue after discounts, which is closer to the cash actually retained from sales. |
| COGS | Separates sales growth from product-level profitability. |
| Gross margin percent | Shows whether product pricing covers product cost. |
| Shipping fee deficit | Shows whether Apex is subsidizing fulfillment in specific regions or order types. |
| Return rate | Identifies categories where sales reverse into refunds, handling costs, and markdown losses. |
| Return handling and support costs | Captures operational drag that does not appear in gross margin. |
| Net operating profit | The central outcome: profit after product, fulfillment, support, and marketing costs. |
| Net margin percent | Allows comparison across segments, products, channels, and periods. |
| CAC vs LTV | Shows whether marketing channels produce customers whose profit exceeds acquisition cost. |
| Repeat purchase rate | Distinguishes healthy growth from one-time subsidized acquisition. |

## 3. Ranked Hypotheses

### 1. High discounts are cannibalizing profit

Aggressive discounts are the most likely first leak because they can raise order volume and revenue while reducing or eliminating contribution margin. The danger is especially high if discounts above 20 percent are concentrated in low-margin products or price-sensitive customer segments.

**Expected signal:** High-discount orders show strong revenue volume but materially lower gross margin and net margin.

### 2. Paid Social acquisition cost exceeds customer value

Marketing may be optimizing for revenue, new customers, or order count instead of profitable customer relationships. If Paid Social customers have high CAC and low repeat purchase behavior, revenue growth can become cash burn.

**Expected signal:** Paid Social has higher CAC, lower LTV, weaker repeat purchase rate, and lower first-order profit than Email, Referral, or Organic.

### 3. Remote-region logistics subsidies wipe out order margin

Free or undercharged shipping can quietly destroy profit when carrier costs vary by region and weight. This leak is operationally plausible because customers see a simple shipping fee, while Apex absorbs the true cost variance.

**Expected signal:** Remote regions show higher actual shipping cost, larger shipping fee deficits, and lower net margin even when gross margin looks healthy.

### 4. Apparel and electronics returns create hidden losses

High-return categories can look attractive on gross sales but underperform after refunds, return handling, restocking, markdowns, and support load. This is especially likely in apparel subcategories with sizing issues and electronics with expectation mismatch.

**Expected signal:** High-return subcategories show lower realized net revenue, higher fulfillment cost per item, and weaker net operating profit.

### 5. Wholesale or Corporate customers may be over-discounted

Large customers can create the appearance of healthy revenue concentration, but negotiated discounts and fulfillment complexity may reduce margin. This is less likely than broad discount leakage but should be checked because segment-level decisions are operationally actionable.

**Expected signal:** A segment contributes high revenue share but below-average net margin after discounts and fulfillment costs.

### 6. Product mix has shifted toward lower-margin categories

Revenue can rise while margins fall if the company is selling more low-margin products. This may be a secondary effect of discounts, marketing campaigns, or seasonal demand.

**Expected signal:** Category revenue mix shifts over time toward lower gross margin or higher return-rate products.

### 7. Support costs are concentrated in specific order types

Support load may be a smaller leak, but it can identify avoidable complexity in late deliveries, returns, damaged items, or confusing promotions.

**Expected signal:** Orders with support tickets have lower net operating profit, especially when combined with returns or shipping delays.

## 4. Investigation Sequence

### Step 1: Confirm the headline pattern

Start with monthly revenue, gross margin percent, and net margin percent over the 18-month period. This verifies that the project's central business problem exists in the generated data.

**Decision value:** Establishes the executive narrative: growth is real, but profitability is weakening.

### Step 2: Decompose margin from revenue to net profit

Break gross revenue into discounts, net revenue, COGS, fulfillment costs, support costs, marketing allocation, and net operating profit.

**Decision value:** Shows which cost layer is expanding faster than revenue.

### Step 3: Test discount cannibalization

Group orders by discount band, customer segment, category, and month. Compare order count, net revenue, gross margin percent, and net margin percent.

**Decision value:** Identifies where discount caps or promo redesigns can improve margin without stopping all growth.

### Step 4: Test logistics subsidization

Compare shipping fee charged against actual shipping cost by region, carrier, order weight proxy, and customer segment.

**Decision value:** Identifies where shipping minimums, thresholds, or surcharges may be needed.

### Step 5: Test return-rate economics

Analyze return rates, return handling cost, fulfillment cost per item, and net margin by category and subcategory.

**Decision value:** Distinguishes high-revenue categories from actually profitable categories.

### Step 6: Test marketing efficiency

Compare CAC, first-order margin, customer LTV, and repeat purchase rate by acquisition channel and cohort month.

**Decision value:** Identifies where budget should be reallocated without increasing total marketing spend.

### Step 7: Model drivers of profit

Use regression and tree-based feature importance to estimate which variables most strongly explain order-level net operating profit.

**Decision value:** Validates whether the suspected leaks remain important after controlling for overlapping factors.

### Step 8: Simulate recommendations

Estimate the business impact of discount caps, marketing reallocation, and shipping policy changes.

**Decision value:** Converts findings into quantified executive recommendations.

## 5. Required Data Tables

| Table | Purpose |
|---|---|
| customers | Customer segment, acquisition channel, region, signup date, satisfaction score, and CAC context. |
| products | Product category, subcategory, unit cost, retail price, and built-in return risk. |
| orders | Order date, customer, discount behavior, promo code, channel, and shipping fee charged. |
| order_items | Product-level quantities, sold prices, and return flags. |
| fulfillment | Actual shipping cost, carrier, delivery days, return handling cost, and support tickets. |
| marketing_spend | Monthly spend, channel, and new customers acquired for CAC analysis. |

## 6. Analytical Approaches

| Approach | What it reveals |
|---|---|
| KPI views in SQL | Creates a consistent profit calculation used across the whole project. |
| Monthly trend analysis | Confirms whether margin erosion worsens over time while revenue grows. |
| Grouped diagnostics | Shows margin differences by discount band, region, category, segment, and channel. |
| Cohort analysis | Tests whether newer customers are less profitable or less likely to return. |
| CAC vs LTV analysis | Determines whether customer acquisition is creating or destroying value. |
| Regression | Estimates directional effects, such as how discount percent relates to profit. |
| Random forest feature importance | Finds nonlinear drivers and interaction-heavy patterns. |
| Scenario simulation | Quantifies likely impact of operational recommendations. |

## Initial Recommendation Targets

The final recommendations should be specific enough to act on within one quarter. Candidate recommendation forms include:

- Cap discounts above a defined threshold for segments or categories where net margin turns negative.
- Raise free-shipping thresholds or add region-specific shipping rules for high-deficit regions.
- Reduce promotional investment in high-return subcategories unless price, sizing, or quality issues are addressed.
- Reallocate a defined percent of marketing spend from Paid Social to channels with stronger LTV-to-CAC ratios.
- Prioritize customer segments with positive LTV, repeat purchase behavior, and manageable fulfillment costs.

## Refinement Decisions

The project will use the following design choices:

| Question | Decision | Implication |
|---|---|---|
| Should one leak dominate, or should two leaks compete for first place? | Two leaks should compete for first place. | The dataset should make discount cannibalization and marketing CAC/LTV imbalance both plausible primary causes, so the analysis has to separate visible revenue growth from true profitability. |
| Should recommendations preserve revenue growth or prioritize margin recovery? | Prioritize short-term margin recovery. | Recommendations should focus on actions Apex can implement within one quarter, even if they modestly reduce low-quality revenue. |
| Who is the dashboard for? | Cross-functional view for Finance, Marketing, and Operations. | The dashboard should include CFO-level profit KPIs, Marketing channel efficiency, and Operations fulfillment/returns diagnostics in one shared interface. |
