# 判读：哪些是真问题

`inventory.py` 只测量，不下结论。这一页是下结论的部分。

## 一、什么算「乱」

只有一条标准：**项目自己说过的话，和仓库里的实际样子不一致**。项目没说话的地方，不由你替它定规矩。

项目会通过这几类文件说话：`AGENTS.md`、`CLAUDE.md`、`SCHEMA.md`、`ARCHITECTURE.md`、`CONTRIBUTING.md`、`README.md`、`docs/` 下的结构说明、`package.json` 的 `workspaces`/`exports`、`pyproject.toml` 的 `packages`。

脚本用两条规则从这些文件里取区名，其余一律不当声明：

- 目录树行：`|-- src/`、`├── src/`、`+-- src/`
- 反引号或加粗包裹、且以斜杠结尾：`` `src/` ``、`**src/**`

散文里出现的「和 `notes/` 类似」「origin/main」「src/pages/index.astro」不算。表格分隔线 `|---|---|` 也不算。这是刻意的：宁可漏一个声明，也不要凭空造一个。

## 二、五类问题的处理

### ABSENT（声明了但不存在）

两种可能，必须问：

- 文档过期 → 改文档，删掉那一行。
- 目录被误删/还没建 → 建目录，或从历史里恢复。

不要沉默地建一个空目录了事。空目录进不了 git，等于没做。

### 未命名区（存在但没声明）

被跟踪文件 ≥2 个的顶层目录，文档里没提。判断顺序：

1. 这个区是不是一次迁移的残留（README 里提到「正在迁到 xxx」）？→ 补文档说明它是旧的，或搬空它。
2. 是不是纯产物区（`releases/`、`dist/`）？→ 进 `.gitignore`，不是搬。
3. 都不是 → 它是项目的真实一部分，补进文档的结构段。

**补文档通常比搬文件更对。** 一个能跑的项目，目录已经形成了事实约定；搬动的收益往往小于破坏引用的风险。

### 根目录散落

根目录该有的只有：

- 构建/工具配置：`package.json`、`tsconfig.json`、`astro.config.mjs`、`Makefile`、`pyproject.toml`、`Cargo.toml`、`.gitignore`、`.env.example`
- 入口文档：`README.md`、`AGENTS.md`、`CLAUDE.md`、`LICENSE`、`SCHEMA.md`

其余都该有归属。判断该去哪：看项目已有的区哪个语义最近，不要新建一个区来装一个文件。

一个文件如果哪个区都不合适，它可能就该留在根目录——入口文档就是这样（`APP_FLOW.md`、`PRODUCT.md`、`DESIGN_SYSTEM.md` 在 p3l.me 就合理地留在根）。

### 被跟踪的产物

`tracked but generated` 段里的。处理：`git rm --cached` + 补 `.gitignore`。不要搬进别的目录——搬了还是产物。

常见的漏网：`.pyc`（提交在 `__pycache__` 里）、`.dll`/`.exe`（提交在 `releases/` 里）、`Player.log`、`.DS_Store`。

### 无引用源文件

只报不搬。脚本的判定是「这个文件名在全部语料里只出现一次」。误报来源：

- `.astro` / `.vue` / `.svelte` 里的 import（脚本只读扩展名白名单内的文本）
- 框架按位置加载：`content.config.ts`、`middleware.ts`、`robots.txt.ts`、`+page.svelte`、`app/layout.tsx`
- 动态 import、`require()` 拼出来的路径
- 配置里按字符串引用的路径（`vite.config.ts` 的 `input`、`tsconfig.json` 的 `paths`）

确认一个孤儿真的没用了，再交给用户决定删不删——**本技能不删文件**。

## 三、各语言的引用写法

`move.py` 不解析语法，它把路径当文本匹配。这样跨语言都能用，代价是每种写法都得覆盖到：

| 语言 | 写法 | 处理 |
|---|---|---|
| JS/TS | `'./nav'`、`'../data/nav'`、`'../data/nav.ts'`、`'src/data/nav'` | 全改 |
| Python | `from nav import`（同目录裸名）、`from src.data.nav import`（点号包名） | 裸名改；点号包名**不改**，需人工确认 |
| 文档 | `` `src/data/nav.ts` ``、`./src/data/nav` | 改（路径形状才改，裸名不改） |
| 配置 | `"main": "host/patch-doc.js"`、`tsconfig.paths` | 改（repo 相对路径） |

裸包名（`from 'nav'`、`import requests`）**永远不改**。它指的是包，不是文件。脚本靠「有没有目录部分或扩展名」区分。

点号包名是已知缺口：`from host.patch_doc import x` 在 `host/patch-doc.js` 搬走后不会自动改。搬 Python 包内文件时，在计划里额外列出要手工改的点号引用，或在 `verify` 里用 `pytest` 兜住。

## 四、什么时候该停

- 用户说的「乱」和你测出来的「乱」不是一回事 → 先对齐再动手。
- 搬一个文件要改 20 个引用 → 收益/风险比很差，提出来让用户决定，通常答案是别搬。
- 项目没有测试也没有 typecheck → 只能验证引用改写，不能验证行为。在汇报里写明这一点。
- 目标结构需要「新建 5 个目录」才成立 → 你在套模板，不是在整理这个项目。停下。
