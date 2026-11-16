# 计划文件格式

`move.py` 只吃一个 JSON。写错会明确报错，不会猜。

## 最小计划

```json
{
  "repo": "/abs/path/to/repo",
  "moves": [
    {"from": "scripts/tidy.py", "to": "tools/tidy.py"}
  ],
  "verify": "npm run test"
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `repo` | 是 | 仓库根目录绝对路径。必须含 `.git`。 |
| `moves` | 是 | 至少一条。`from`/`to` 都是仓库相对路径，用 `/` 分隔。 |
| `verify` | 否 | 在 `repo` 里跑的 shell 命令。为空或省略则跳过验证。 |

## 路径规则（会拒绝的）

- 绝对路径、含 `..` 的路径 → 必须留在仓库内。
- `from` 不存在、`to` 已存在。
- 两个搬移的 `to` 相同。
- **扩展名变了**（`a.ts` → `a.js`）。改引用时无法区分「移动」和「改名」，容易把引用改坏。要改名就单独一次 `git mv`，引用手工改。

## 一次搬一组，不是一次搬一个

搬一个目录下的多个文件，写多条 `moves` 即可，`rewrite` 会把它们一次性处理完，不会互相打架：

```json
{"repo": "/p", "moves": [
  {"from": "src/a/x.ts", "to": "src/lib/x.ts"},
  {"from": "src/a/y.ts", "to": "src/lib/y.ts"}
]}
```

前提：搬移本身不能互相依赖（不能一条的 `to` 是另一条的 `from`）。

## verify 怎么写

写项目自己验收用的那条命令，别自创：

| 项目类型 | 写法 |
|---|---|
| Node | `npm run test` 或 `npm run build` |
| Python | `pytest -q` 或 `python -m compileall -q <dir>` |
| Rust | `cargo check` |
| Go | `go build ./...` |
| Astro | `npm run build`（构建会报所有断掉的 import） |
| 纯文档/数据 | 省略 `verify` |

## 退出码

| 码 | 含义 | 该怎么办 |
|---|---|---|
| 0 | 成功 | 验收步骤 |
| 2 | 计划被拒 | 按打印的原因改计划 |
| 3 | 工作区脏 | 先提交或 stash，别用 `--allow-dirty` |
| 4 | verify 失败 | 按打印的命令回滚，查漏改的引用形态 |

## 回滚

`move.py` 用 `git mv` 搬文件、用普通写入改引用，所以整体回滚是一条命令：

```bash
git -C <repo> restore --staged --worktree . && git -C <repo> clean -fd
```

已经 commit 过的话：`git -C <repo> reset --hard <搬移前的提交>`。

## 空跑

不加 `--apply` 就是空跑：打印每条将要改的引用（文件、原文、改成什么、出现几次），一个字节都不写。**计划给用户看之前先空跑一遍**，用真实数字填「引用要改的文件数」那一列。
