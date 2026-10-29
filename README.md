# ETF + Stock Research / ETF与个股研究

Source-backed research prototype. A scenario calculator and evidence notebook; no calibrated market-bottom signal and no trading automation.

中文入口：同一网站研究QQQM、SMH、SOXX、DRAM及7家核心公司。ETF持仓关联到个股，个股反查基金；历史风险与条件估值分开显示。

网站：https://etf-research-notebook-zdq.zhaodingqi0630.chatgpt.site/

## 如何使用

1. 在仓库下载 `etf-stock-research.zip`，解压进入 `etf-stock-research` 文件夹。源码和网页均在包内，无需市场数据账号。
2. 安装 Python 3.10 或以上，在该文件夹运行：

```sh
python -m http.server 8000 --directory web
```

3. 浏览器打开 http://localhost:8000/ 。结束使用时按 Ctrl+C 停止服务。不要把服务直接暴露公网。也可使用任何静态网站托管服务部署web目录。
4. 先读 `docs/USER_GUIDE.zh-CN.md`，再选标的。先核对来源与日期，再填写你明确采用的盈利和估值假设。最高买价是目标回报的条件反解，不是买入建议。

## 数据是什么时候的

- 历史实验冻结至2026-10-26；不是实时行情，未把新快照混入旧回测。
- 新行情为2026-10-28常规收盘，2026-10-29取回；盘后独立保留，不视为成交报价。
- 持仓按发行商各自文件日期。DRAM为混合互换/抵押品/直接持仓账本，不能把记录权重全部当股票NAV。
- 年度EPS是供应商预测；形成日期asOf缺失仍为null。MSFT/GOOGL预测取回早于10月28日财报窗口。
- 没有完整可比的ETF三年盈利。部分公司、财年和口径覆盖不等于基金预测。
- 定时监测已经暂停；下载程序也不会自动联网或交易。

## 复现与更新

纯Python图表与回撤状态复现：

```sh
python tools/reproduce.py --input web/data.json --symbol QQQM --horizon 3y
```

它生成本地HTML图和分布统计，仅复现价格口径的图表/分桶/窗口统计。不是原研究全部宏观策略、原始下载或投资有效性的独立复现。

验证并同步你编辑的公开快照（先复制原文件备份）：

```sh
python tools/sync_snapshot.py --kind stock --input web/stock-data.json
python tools/sync_snapshot.py --kind stock --input web/stock-data.json --write
python tools/sync_snapshot.py --kind history --input web/data.json --write
python tools/verify_package.py
```

不加--write只校验。更新须自己取得合法使用的数据并核对来源、币种、期间、EPS口径和实际时间。工具不会补造缺失数，不验证来源真伪。stock更新同时同步统一入口的个股快照；history更新使动态图重新计算，但不重跑静态历史研究表、策略测试或旧证据台账。修改后的哈希校验失败是预期，需自行记录变更并重新生成清单；不要把新参数回填成旧时点预测。

原始供应商数据与下载器不包含在此包。离线包包含网站已经展示的处理后研究快照和原始来源目录/哈希。没有付费点时预测数据库；不声称可以重建真实历史共识。

核心算法在 `web/v6_calc.js`（兼容文件名，内部算法为V8）、`web/model.js`、`web/stocks.js`。Node.js 18+可运行 `node tools/core_check.mjs` 检查核心公式反解。该检查仅验证实现自洽，不验证投资收益。

## 结构与模型逻辑

发行商持仓/公司财报/供应商预测 → 保留各自日期、单位与口径 → ETF/个股关联目录 → 历史风险与独立情景计算 → 输出所需盈利、条件买价、来源和未验证项。

ETF绝对情景：退出价格=独立的退出EPS×退出PE；再处理基金费、现金分红、预扣税、交易摩擦、换汇及余款。个股页面目前为USD价格毛回报，不含分红、税费与FX，不能直接与ETF的SGD净回报比较。没有统一的“最优标的”排名。

见 `docs/DATA_DICTIONARY.md`、`docs/LIMITATIONS.md`、`DATA_NOTICE.md`。没有任何软件测试能证明未来底部或收益。公开页面不含浏览器localStorage里的个人情景；导出个人情景前请自行检查，勿提交账户资料或API密钥。

## 问题反馈与协作

提交Issue请附页面/算法版本、数据日期、可公开的最小输入、预期结果和实际结果。不要上传持仓账户、私人资金计划、凭据或日志中的密钥。代码可阅读和本地研究，授权边界见NOTICE；第三方数据不自动获得再分发或商用许可。
