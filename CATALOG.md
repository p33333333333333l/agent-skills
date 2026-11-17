# 技能索引

本机在用技能的全量清单。**只有「自建」技能的正文收录在本仓库**；导入技能仅登记来源与许可证，正文不入库，避免转载版权内容。

- 自建：8 个，正文在 `skills/`
- 导入：23 个，正文在 `~/.cc-switch/skills/`（本机），来源见下表
- 合计：31 个

数字口径：本索引登记的技能数；自建以 `skills/` 下 8 个真实目录为准，导入以 `~/.cc-switch/skills/` 下 23 个真实目录为准。软链接可能尚未全部安装，实际入口状态用 `scripts/link-skills.sh --check` 核对。`specialist-team` 已迁移为 DSH 插件，不计入技能清单。

## 自建技能（正文已收录）

| 技能 | 用途 | 文件数 |
|---|---|---|
| [`umi-ocr`](skills/umi-ocr/SKILL.md) | 用本机 Umi-OCR 精确识别图片文字，逐行给置信度与坐标 | 2 |
| [`add-entry-to-p3l-me`](skills/add-entry-to-p3l-me/SKILL.md) | 给 p3l.me 添加公开目录条目，含分类、双语文案、DR 与截图证据 | 2 |
| [`git-sync-preserve`](skills/git-sync-preserve/SKILL.md) | 无损同步 main 与 origin/main，保留暂存、未暂存和未跟踪工作 | 3 |
| [`godot-scene-quality`](skills/godot-scene-quality/SKILL.md) | 审查并改进 Godot 3D 场景的画面与声音 | 3 |
| [`grilling`](skills/grilling/SKILL.md) | 用 design tree 逐轮追问，压测计划、decision 或想法 | 2 |
| [`indie-product-gtm`](skills/indie-product-gtm/SKILL.md) | 把产品想法收成定位、主 ICP、渠道优先级与 GTM 路线 | 2 |
| [`keyword-market-research`](skills/keyword-market-research/SKILL.md) | 调研 SEO 关键词、验证搜索需求、分析竞品流量 | 6 |
| [`reader-first`](skills/reader-first/SKILL.md) | 按读者意图取舍信息、安排重点与链接，减少阅读和沟通负担 | 4 |

## 导入技能（仅索引，正文不入库）

「许可证」列取自技能内的 `license` 字段或 `LICENSE` 文件；标「未声明」的是技能包本身没有许可证声明，版权归原作者，使用前请自行核实。

| 技能 | 来源 | 许可证 | 说明 |
|---|---|---|---|
| `cloudflare` | Cloudflare 官方技能包 | 未声明 | 云产品选型与架构 |
| `cf-cli` | Cloudflare 官方技能包 | 未声明 | cf CLI 命令检索与执行 |
| `wrangler` | Cloudflare 官方技能包 | 未声明 | Wrangler 项目开发与部署 |
| `workers-best-practices` | Cloudflare 官方技能包 | 未声明 | Workers 生产实践 |
| `workers-profiling` | Cloudflare 官方技能包 | 未声明 | Workers CPU/内存分析 |
| `durable-objects` | Cloudflare 官方技能包 | 未声明 | Durable Objects 状态与协调 |
| `turnstile-spin` | Cloudflare 官方技能包 | 未声明 | Turnstile 人机验证接入 |
| `nextjs-on-cloudflare` | Cloudflare 官方技能包 | 未声明 | Next.js 部署到 Workers |
| `cloudflare-email-service` | Cloudflare 官方技能包 | 未声明 | Email Sending/Routing |
| `web-perf` | 未查明 | 未声明 | Core Web Vitals 与性能优化 |
| `agent-reach` | github.com/Panniantong/Agent-Reach | 未声明 | 只读抓取各平台内容 |
| `darwin-skill` | alchaincyf（花叔） | MIT | 技能自优化，含 9 维评分 |
| `humanizer` | Siqi Chen，v4.0.0 | MIT | 英文去 AI 味改写 |
| `humanizer-zh` | 基于 blader/humanizer v3.0.0 与 Humanizer-zh PR 39 | MIT | 中文去 AI 味改写 |
| `ponytail` | 未查明 | MIT | 最小改动的懒资深开发模式 |
| `ponytail-audit` | 未查明 | 未声明 | 全仓质量审计，一次性出报告，不改代码 |
| `ponytail-review` | 未查明 | 未声明 | 审查一次改动：逻辑、安全、负载、测试、性能、冗余 |
| `design-taste-frontend` | tasteskill 2.5.1 | 未声明 | 前端设计与反模板化检查 |
| `high-end-visual-design` | Classic style skill 包 | 未声明 | 高端视觉风格（按名调用） |
| `minimalist-ui` | Classic style skill 包 | 未声明 | 极简编辑风 UI（按名调用） |
| `redesign-existing-projects` | Classic style skill 包 | 未声明 | 已退役，并入 design-taste-frontend |
| `obsidian-markdown` | 未查明 | 未声明 | Obsidian 风格 Markdown |
| `writing-for-agents` | 未查明 | 未声明 | 写给 agent 读的文档 |

> 标注「未查明」的 6 项（`web-perf`、`ponytail`、`ponytail-audit`、`ponytail-review`、`obsidian-markdown`、`writing-for-agents`）：本机无来源记录，且当前网络检索不可用，未做核实。请勿据此判断归属。

## 本机路径映射

| 路径 | 内容 |
|---|---|
| `~/.dsh/skills/<name>` | DSH 读取的技能入口 |
| `~/.cc-switch/skills/<name>` | 技能实际存放位置（导入技能） |
| `~/workspaces/agent-skills/skills/<name>` | 自建技能实际存放位置（本仓库） |

自建技能的真实目录在本仓库，另两处为指向本仓库的软链接；导入技能的真实目录在 `~/.cc-switch/skills/`，`~/.dsh/skills/` 为指向它的软链接。
