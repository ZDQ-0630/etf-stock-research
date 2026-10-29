# 数据字典与处理逻辑

## 数据文件

- web/data.json、data.js：冻结历史价格、来源清单、参数、历史研究与证据快照。series以代码为键，每行是[ISO日期, 收盘价]。各研究口径按页面声明，不能把价格回报当含分红总回报。
- web/stock-data.json、stock-data.js：7家公司实际经营、独立行情、年度EPS预测、分析情景及缺口说明。JS由JSON生成供静态网页使用。
- web/full-holdings.json：发行商持仓原样识别后的账本，包含股票、现金、衍生品与未知分类。每个基金有独立日期、来源、原始哈希、记录数和缺权重数量。
- web/hub-data.json、hub-data.js：统一入口使用的持仓关联与最新取得行情。complete=true仅指发行商账本记录已取得，不指基金盈利覆盖完整。
- web/forecast-refresh.json：预测供应商取回状态、年度条目和元数据。预测形成时间与取回时间不同。
- web/completion-status.json：实现完成项、受数据阻断项和不可消除限制。
- SHA256.json：离线包文件哈希清单，只检验是否与本次打包文件一致，不证明数据真实、历史点时性或外部时间戳。

## 核心字段

- symbol：证券标识，股票与ETF不共享盈利单位。互换原证券标识保留；underlying_symbol只用于已明确识别的底层公司关联，不作敞口合计。
- quote.price：USD常规收盘快照。quote.date/timestamp保留市场时刻；post_market独立保存，不替换常规收盘。
- retrieved_at：实际取回时间，不是公司公告日、行情日或预测形成日。
- actuals.period：发行商原财年/季度。revenue、operating_income、cfo、capex、fcf在此公司表按十亿美元展示，eps为每股/ADS美元；特殊定义见capex_label、fcf_label和missing。
- operating_margin：小数比例。MSFT部分FCF为CFO减现金PP&E自算，未包含融资租赁全口径；MU为公司净资本开支及调整后FCF，不能无差别比较。
- forecasts.start/end：年度财年代理窗口，部分来自月末而非真实52/53周边界，不是已经精确日历化的季度盈利路径。
- forecasts.eps_mean：供应商年度每股盈利预测；analysts是该条预测人数，不代表总体置信度。asof=null表示形成日未提供，不能写成最新共识。
- forecasts.basis：已知口径说明，未核实项原样保留。至少3家是筛选门槛，不消除选择偏差或会计口径差异。
- scenarios.terminal_eps、terminal_pe：明确标为analysis_assumption的退出盈利和倍数；压力层级没有概率。采用后仍由用户判断经济合理性。
- holdings.records.weight：小数比例，如0.1表示10%；null表示缺失，不能当0。负现金、抵押品和互换比例不能直接当股票NAV覆盖。
- issuer_valuation：发行商披露的PE/forward PE及日期，口径未完全勾稽时不用于倒推整只基金EPS。

## 时间与覆盖

历史实验截止2026-10-26；新行情是2026-10-28常规收盘。QQQM/SOXX/SMH持仓按各自文件2026-10-27日期，DRAM内部日期2026-10-28且当时盘中取回；URL日期和文件内部日期冲突均保留。

完整账本记录数：QQQM 108、SOXX 34、SMH 27、DRAM 25。QQQM一条待收股息权重未知；DRAM是混合账本。记录完整不等于全部股票财务可比或完整ETF盈利可用。

## 计算与边界

ETF绝对情景以独立退出EPS×退出PE为价格锚，再处理显式成本与现金流。倍数分母、期间、价格日和估值日必须一致。旧增长×倍数比接口仅为兼容敏感性。公司经营桥接需要逐年收入、利润率、利息、税、其他项目和股份变化；它不是自动预测。

个股纯价格情景为退出EPS×PE；年化=(退出价格/参考价)^(1/年数)−1；条件最高买价=退出价格/(1+目标年化)^年数。未含费用/税/分红/FX。负EPS不作PE估值。

历史条件分布使用实际历史收盘状态；窗口重叠、事件嵌套及共同市场冲击使观察不独立。3y是3日历年，并非固定756行。未成熟窗口的已观察损失是下界，不能冒充完整分布。

## 缺失值政策

未知保持null或未验证；不以0补齐，不把取回日期充作asOf，不回填后来形成的预测。任何人工修订必须保留原始来源、修订原因、实际修订时间及算法版本。浏览器本地导入和CLI手动更新均不是来源认证。
