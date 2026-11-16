# Agent Skills

我在日常工作中实际使用的 Agent 技能库。本仓库是**自建技能的唯一源**：`skills/` 下的目录是真实文件，本机 `~/.dsh/skills` 与 `~/.cc-switch/skills` 通过软链接指向这里，改仓库即改本地生效内容。

导入的第三方技能不转载正文，只在 [CATALOG.md](CATALOG.md) 登记名称、来源与许可证，避免版权问题。

## 结构

```text
agent-skills/
├── skills/           # 自建技能，每个目录含 SKILL.md
├── scripts/          # 链接与校验脚本
├── CATALOG.md        # 全部技能索引（含第三方来源与许可证）
└── README.md
```

## 自建技能

| 技能 | 用途 |
|---|---|
| `umi-ocr` | 用本机 Umi-OCR 精确识别图片文字，逐行给置信度和坐标 |
| `add-entry-to-p3l-me` | 给 p3l.me 添加公开目录条目 |
| `git-sync-preserve` | 无损同步 main 与 origin/main，保留未提交工作 |
| `godot-scene-quality` | 审查改进 Godot 3D 场景画面与声音 |
| `grilling` | 用 design tree 逐轮追问，压测计划或想法 |
| `indie-product-gtm` | 把产品想法收成定位、ICP、渠道与 GTM 路线 |
| `keyword-market-research` | 调研 SEO 关键词与市场机会 |
| `repo-layout` | 按项目已有约定整理目录，盘点漂移、安全搬移并验证引用 |

## 安装到新机器

```sh
git clone git@github.com:p33333333333333l/agent-skills.git
cd agent-skills
./scripts/link-skills.sh          # 建立软链接
./scripts/link-skills.sh --check  # 校验链接与 SKILL.md 完整性
```

`link-skills.sh` 会为 `skills/` 下每个技能在 `~/.dsh/skills` 和 `~/.cc-switch/skills` 建立软链接。已存在的真实目录不会被覆盖，脚本会提示先自行处理。`--check` 除了逐个校验链接，还会反向扫一遍两个目标目录，把指向已不存在技能的 `STALE` 链接报出来并以非零退出。两个目标目录可用 `DSH_SKILLS_DIR`、`CC_SKILLS_DIR` 覆盖（想先试跑就指到临时目录）。

`specialist-team` 已迁移为 DSH 插件，由插件注入任务分流、专家职责与选模规则。请通过 DSH 的插件机制安装和启用；本仓库的技能链接脚本不安装该插件。

## 新增技能

1. 在 `skills/<name>/` 下写 `SKILL.md`，frontmatter 至少含 `name` 和 `description`。
2. `description` 决定何时自动触发，写清触发场景和不该用的场景。
3. 跑 `./scripts/link-skills.sh` 建立链接，重启 agent 后生效。
4. 在 [CATALOG.md](CATALOG.md) 登记。

## 许可证

自建技能为 Apache License 2.0，见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。第三方技能版权归各自作者，本仓库不转载其内容。
