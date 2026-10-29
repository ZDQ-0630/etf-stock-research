# V8核心公式修复与接口

本轮只修改`sites/etf-research/src/v6_calc.js`，新增`v8/core_tests.mjs`及本说明；没有修改`app.js`、V6/V7历史结果或发布网站。Node语法检查和29项核心测试已实际通过。

版本为`absolute-earnings-periods-v8`。所有前瞻数值仍是明确输入的情景，不从代码构造市场事实，也不证明价格便宜、底部存在或预测有效。

## 绝对退出估值：scenarioAbsolute

调用`ResearchMath.scenarioAbsolute(input)`。所需公共字段沿用情景表单：

```javascript
{
  budget, entry, reference, years, fx0, fx1,
  bps, fee, fx_bps, cash_rate, shock,
  dividend, withholding,
  fund_fee,                     // 必须显式提供有限数字，未知不默认0
  fee_mode: 'deduct',            // 或 'embedded'
  valuation_basis: 'ntm',        // 'ttm' / 'ntm' / 'normalized'
  valuation_date: '2026-10-26',
  price_date: '2026-10-26',
  context_mode: 'historical',    // 'current'默认要求同日
  evidence_date: null,           // 缺失表示未验证，不借用价格日期
  base_start: '2026-10-26',
  base_end: '2027-10-26',
  terminal_start: '2029-10-26',
  terminal_end: '2030-10-26',
  base_eps: 5,
  terminal_eps: 8,               // 独立输入，不能由reference反算
  terminal_pe: 20,               // 独立输入
  hurdle: 0.10,
  source_note: '人工输入条件情景，基准与退出均须同基金份额口径'
}
```

基准PE只用于展示：`base_pe = reference / base_eps`。条件毛退出价格为`terminal_eps × terminal_pe`，不再从参考价反算退出倍数。所以只改退出EPS会独立改变退出价和条件买价；只改参考价不会机械改变退出价。它改变基准PE和显示出的相对倍数比例。

`fee_mode='deduct'`时补扣基金费用：`target = gross_target × (1-fund_fee)^years`；`embedded`表示输入退出价格口径已包含基金层面费用，不再重复扣。历史ETF价格不通过这里重复扣费。

返回保留`target/gross_target/maxEntry/fractional/integer/reverse`等执行字段，增加：

- `valuation_model='absolute_terminal_eps_pe'`
- `base_eps/base_pe/terminal_eps/terminal_pe/multiple_ratio_vs_base`
- `base_window/terminal_window/date_alignment`
- `evidence_date/evidence_status`
- `decision_status='not_decision_ready'`

旧相对增长字段`g1/growth/multiple`不参与绝对估值，因此它们缺失或无效不应阻断独立退出EPS/PE计算。

## 日期与证据

- `price_date`、`valuation_date`必须为真实ISO日期，不能缺失。
- `context_mode='current'`要求两日相同；`historical`允许价格日期在估值日前0–7个日历日内，禁止未来价格。冻结研究可直接将估值日选为价格日。
- `evidence_date`为null/缺失/空白时返回`evidence_status='unverified'`；不能把价格截止日、构建日当作盈利预测可得日。
- 显式证据日期必须不晚于估值日；返回`declared_date_not_independently_verified`，没有把用户填写日期冒充独立验证。
- 盈利窗口仍要求一日历年、退出窗口整体平移整数3–20年。NTM从估值日开始；TTM在估值日结束。归一化口径须给足周期/调整说明。

## 相对敏感性兼容

保留`scenarioV6(input)`，另导出同一函数别名`scenarioRelativeV8`。它仍按`reference × (1+g1) × (1+growth)^(years−1) × multiple`计算，但明确返回`valuation_model='relative_sensitivity_compatibility'`与V8版本。

这是显式关联基准PE的相对敏感性，不是独立的退出PE估值。它也执行显式费率、日期/窗口、证据时点和派生有限值检查。

## 经营桥接：operatingBridgeV8

调用格式：

```javascript
{
  R0: 100,
  revenue_growth_path: [0.10, 0.20],
  operating_margin_path: [0.20, 0.25],
  interest_per_share: 2,
  tax_rate: 0.20,
  other_recurring_per_share: 1,
  share_factor_path: [1.10, 1.20]
}
```

`R0`单位为USD/基准日份额；收入增长按年累乘。利息和其他经常项也使用USD/基准日份额，可输入有限标量或同长度逐年数组。`share_factor_path`是累计总股数/基准日总股数的正因子，不是每年股数增长率，避免重复摊薄。

逐年计算：

`收入/基准份额 = R0 × 累计收入增长因子`

`税前利润/基准份额 = 收入 × 经营利润率 − 利息 + 其他税前经常项`

`EPS = [税前利润 − max(税前利润,0)×税率] / 累计股数因子`

亏损时不自动确认税收利益。没有少数股东权益/优先股分配输入，因此明确假设模型利润归属于普通股；输出叫`conditional_common_eps_proxy`，不冒充真实GAAP归母EPS。

`years[]`逐年返回`eps_usd`、收入、经营利润、税前利润、税、股数因子和`pe_valuation_available`。`terminal_eps`保留真实计算值；若最终EPS非正，`valuation_eps=null`、`pe_valuation_available=false`、状态为`unavailable_for_pe_nonpositive_terminal_eps`，不拿0替代亏损。中间年亏损仍保留；若终值年恢复盈利，只允许正终值年进入PE情景。

例如上例首年EPS为16.8/1.1，第二年为25.6/1.2。若收入100、经营利润率−10%、利息2、无其他收益，则EPS为−12，税为0，PE估值不可用。

## 费用、分红、现金与反解

执行接口仍为`executionV6`，另导出别名`executionV8`；它接收已经确定的净退出市场价格，现金引擎本身不再另扣基金费。FX单位始终为每1 USD对应的SGD，余款和分红为USD现金。

分红每持有整周年支付，非整数末期按比例支付；税率为用户情景，分红大于0但税率未知时拒绝税后计算。分红留下USD并按现金假设利率计息，不再投资股票。

碎股最高买价反解仍使用同一份额终值现金流，包含卖出成本及每股净分红累计；零股票时不收不存在的股票交易固定费。资金不足以买入时`maxEntry=null`，不返回负数或假造0。

绝对估值反向门槛增加`reverse.required_terminal_eps`和`required_terminal_pe`；它们分别在另一个退出假设保持不变时反解目标。若现金/分红单独足够，所需非负终值可为0，这只是门槛，并非将公司亏损改成0盈利。

所有返回数值和派生PE/EPS/目标价、份额、现金及压力路径均检查有限性。溢出、下溢导致无意义终值时明确拒绝，不泄漏Infinity/NaN。

## 实际测试

运行`node v8/core_tests.mjs`：29项通过，包括独立EPS反例、参考价不改变退出估值、显式基金费、日期7天边界、未来证据拒绝、非正EPS、PE/EPS溢出、含基金费/分红/税/FX的最高买价回代、退出EPS/PE反解回代、现金币种及周年分红、零股现金利息、经营亏损与税盾、路径长度和摊薄边界。

这些是实现与规格检查，不是市场预期准确性、模型盈利能力或当前入场判断验证。

归一化EPS的年度化基准窗口末日必须等于估值日；用于周期调整的历史期间另在来源说明列明。已追加反例测试。
