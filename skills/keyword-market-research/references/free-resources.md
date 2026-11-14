# 免费与低成本资源

官方资料核验日：2026-10-09。下表是能力分工，实时权限、额度和可用性以本次读取结果为准。免费网页功能不代表有免费 API；零新增支出也不代表无限请求。

## 发现词与搜索意图

| 渠道 | 能支持什么 | 访问与限制 |
| --- | --- | --- |
| 当前搜索结果、下拉建议、相关问题 | 实际措辞、意图、竞争页面和结果类型 | 用公开页面或当前浏览器；排名受定位、时间和个性化影响。建议词不携带搜索量 |
| Google Trends 网页 | 相对搜索兴趣、季节性、地区和相关查询 | 免费网页；指数标准化为 0–100。低量词可能显示 0，不能据此认定零需求 |
| Google Keyword Planner | 种子扩展、历史搜索量或区间、广告竞争与出价参考 | 使用已有可访问账号；官方要求完成账号设置并输入账单信息。缺权限时换渠道，不为调研自动创建活动或补账单 |
| Bing Webmaster Tools Keyword Research | Bing 侧关键词、趋势及查询扩展 | 免费工具，通常通过账号界面访问；按实际账号检查入口。Bing 搜索口径不能当作 Google 搜索量 |
| Ahrefs Free Keyword Generator | 有限的词建议、工具提供的搜索量与难度 | 免费网页入口；查询限制、地区、验证码与展示数量以界面为准。不能把网页免费理解为付费 API 的免费授权 |

Trends 比较要对齐地区、时段、类别、搜索类型及“主题/搜索词”。不同独立查询的指数各自归一化，不能直接比较两个请求的 100；优先在同一比较请求中读相对关系，跨批比较要解释锚点与局限。上升查询不自动等于可持续商业需求。

Keyword Planner 的广告竞争不是有机 SEO 难度；历史搜索量和预测也不是同一指标。保留查询时间、目标国家、语言、搜索网络、日期范围及界面实际显示的精度。

### 无密钥建议脚本

`scripts/fetch_suggestions.py` 是小样本辅助，不是商业关键词数据库。它使用公开但非正式的 `suggestqueries.google.com/complete/search` 端点；本次核验获得过非空 JSON，但该端点没有本技能可确认的正式服务契约。

- 使用显式 `--query`；多个查询重复该参数，最多十个，重复种子合并。
- 默认英语/美国提示；按任务显式选择。参数不保证查询来自目标国家的真实浏览器定位。
- 每次请求只尝试一次，请求间隔至少一秒。403/429 后剩余种子标为 `skipped`；其他错误保留原因，失败退出码为 1。
- 输出保留各查询来源、时间、状态、原始建议顺序和归并后的词。`empty` 是本次接口没返回建议，不是零需求；`error`/`blocked` 更不是零需求。
- 将输出重定向到系统临时目录，禁止用未核实的量填充报告。

```sh
workdir="$(mktemp -d -t keyword-market-research.XXXXXX)"
python3 scripts/fetch_suggestions.py \
  --query "invoice generator" --query "invoice generator for freelancers" \
  --language en --country us > "$workdir/suggestions.json"
```

## 自有站与正式 API

| 渠道 | 合适用途 | 权限与口径 |
| --- | --- | --- |
| Search Console 网页/官方 API | 已授权站点的查询、页面、国家、设备、曝光、点击、CTR 与平均位置 | 官方 API 免费但有配额；OAuth 和属性访问权必需。不能查询任意竞品或把曝光当成市场总搜索量 |
| Bing Webmaster Tools 网页/可用官方接口 | 自有站 Bing 搜索表现与站长工具 | 使用已授权属性；按当前官方文档检查 API 是否覆盖具体功能。存在 API 不证明 Keyword Research 的每个页面功能都可调用 |
| Google Trends API | 已获批准账号的官方趋势接口 | 官方仍标记 alpha、限获准测试者；未获批准时使用网页，不依赖非官方库模拟正式权限 |
| Google Ads API | 已有开发者令牌、OAuth 和适用访问等级时的关键词能力 | 不是“有 Ads 网页账号就能用”的免配置接口；按当前 API 访问等级核对可调用方法与限制 |

Search Analytics 可能只返回头部行，不保证全量；处理行数限制、分页和隐私省略，保留过滤器及数据状态。授权缺失时说明无法读取，不通过其他站点或插件估算填补自有站实测列。

## 市场证据

- **产品与定价页：** 记录目标客户、任务、价格单位、套餐边界和可核实的差异。竞品多只证明供给存在，不证明你的进入机会。
- **社区与评论：** 按 `agent-reach` 的可用路由读取相关讨论、产品评论或公开问题。优先有具体任务、替代方案、失败原因和真实付费经历的内容；区别求助、赞扬与购买行为。样本选择和平台人群偏差写入限制。
- **广告透明度：** Google Ads Transparency Center 等公开入口适合确认可见广告与素材；广告缺失不证明无人投放，广告存在不披露 ROI。
- **商店与目录：** 可发现分类、评价和替代方案；星级、排名和估算流量不能换算收入。只据实际可见内容作判断。

对未经核实的市场规模先列假设和验证路径。需要完整定位、ICP 或渠道路线图时，转入 `indie-product-gtm`，把本次证据交给它，不在此重复整套 GTM。

## 官方来源

- [Google Trends 数据口径](https://support.google.com/trends/answer/4365533)
- [Google Trends API alpha](https://developers.google.com/search/apis/trends)
- [Keyword Planner 的使用与前置要求](https://support.google.com/google-ads/answer/7337243)
- [Google Ads API 访问等级](https://developers.google.com/google-ads/api/docs/access-levels)
- [Search Console API 概览](https://developers.google.com/webmaster-tools/about)
- [Search Console API 免费与使用限制](https://developers.google.com/webmaster-tools/pricing)
- [Search Analytics query 契约与完整性限制](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- [Search Console API 配额](https://developers.google.com/webmaster-tools/limits)
- [Bing 免费站长工具与 Keyword Research 官方介绍](https://blogs.bing.com/webmaster/2025/6/Start-Using-Bing-Webmaster-Tools-to-Improve-Your-Site-Visibility/)
- [Bing Webmaster Tools](https://www.bing.com/webmasters/)
- [Ahrefs Free Keyword Generator](https://ahrefs.com/keyword-generator)
- [Google Ads Transparency Center](https://adstransparency.google.com/)
