---
name: git-sync-preserve
description: 同步本地 main 与 origin/main、合并分叉历史，或在同步时保留暂存、未暂存和未跟踪工作。
---

# 无损同步 main

最后更新：2026-11-14

目标：用 **merge** 让两端已存在的提交都成为同步结果的祖先，保留所有未提交工作的内容和暂存意图。
备份分支只保护提交，**不保护工作区或索引**。文件差异消失不一定丢失：它可能已被上游包含。

## 适用门：先满足宿主与项目规则

先读适用的全局及项目 `AGENTS.md`；本技能不覆盖其中的任务分支、rebase、提交确认、PR 和推送约束。普通开发任务按这些规则执行，不因调用本技能获得在 main 上修改或发布的豁免。

下文第 1–6 节只用于明确授权的 main 历史保全同步，且项目规则允许在目标 main 上 merge。若规则要求每任务新分支、推前 rebase 或 PR 合并，不进入下文的 live merge／直接推送流程；可先只读诊断，保留原工作，再按上位规则处理。需要改写已有提交的 rebase 不具备本技能的祖先保全保证，不称作此 merge 流程已通过。保护脏工作时仍可复用 [快照与隔离预演](references/dirty-work.md)。

## 授权与自动化

- 用户已授权同步时，完成诊断并简报后，沿可证明安全的路径自动执行；已授权推送才推送。
- 用户说“先等我确认方案”等明确暂停时，止于诊断与方案；确认前不建备份分支、不 stash、不合并、不推送。
- 只在目标仓库／远端／分支／工作归属不明、真实冲突、安全检查或验证失败、越过授权边界、远端持续竞态时询问。
- 通过适用门的历史保全流程使用 merge；上位规则要求的 rebase 走上位流程。禁止 `reset --hard`、`push --force`、自动 ours/theirs、为了备份临时提交未提交内容；`force-with-lease` 不属于普通同步，只有上位规则及用户明确授权均允许时才另行处理。
- 不自动提交或推送原有未提交内容；不删备份、不 pop/drop 任何 stash、不修改其他工作树。

## 1. 定位与能力门

发现实际路径与配置；下面的名称只是已核实目标为 `origin/main` 时的例子，不把当前机器的目录写成假设。

```sh
pwd
git rev-parse --show-toplevel --git-common-dir
git branch --show-current
git --no-optional-locks status --porcelain=v2 --branch -z
git worktree list --porcelain
git remote -v
git config --get-all remote.origin.fetch
git config --get-all remote.origin.pushurl
```

- 核实 fetch 与 push 的实际地址、分支上游、仓库本地规则、未结束的 merge/rebase/cherry-pick 等操作。
- 仅在已通过适用门的目标 main 检出操作；main 在另一工作树、当前为无关脏分支、detached HEAD 或目标不明确时，报告位置并询问，不代替用户搬动它。
- 检查子模块／嵌套仓库、稀疏检出、索引特殊标志、LFS／自定义过滤器、合并驱动及 hooks。无法可靠保存、重放或验证其语义时停止，明确不支持之处，不宣称已有完整快照。
- 有编辑器、构建器或其他写入者时，先协调暂停写入；无法保证静止就不清理工作区。不可只靠两次 status 相同推断无人写入。
- 诊断输出可能含凭据或秘密：报告脱敏地址、OID 和必要路径，不回显文件秘密。

完成条件：确定唯一目标与授权范围，当前状态可处理，写入者已协调。

## 2. Fetch 后只读诊断

先核对 refspec；fetch 只更新目标远端跟踪引用，不改本地 main，不 prune 备份。失败即停，不能用旧的 origin/main 冒充最新。

```sh
git -c fetch.pruneTags=false fetch --no-tags --no-prune origin refs/heads/main:refs/remotes/origin/main
git rev-parse refs/heads/main refs/remotes/origin/main
git rev-list --left-right --count refs/heads/main...refs/remotes/origin/main
git log --left-right --graph --oneline refs/heads/main...refs/remotes/origin/main
git diff --stat refs/heads/main refs/remotes/origin/main
git diff --name-status
git diff --cached --name-status
git ls-files --others --exclude-standard -z
git stash list --format='%H %gs'
```

记录 `L`＝本地 main OID、`R`＝本次 fetch 的 origin/main OID，列出双方独有提交；若无共同祖先，停止，不自动允许无关历史。
同时记录暂存／未暂存／未跟踪路径、已有 stash 的固定 OID、其他工作树和忽略文件碰撞风险。
先向用户简报：领先／落后数、独有提交、脏工作范围、备份与验证方案、是否会创建 merge commit、是否包含推送。
有明确“等确认”要求就在此结束；否则已授权的安全路径继续，不为常规步骤反复确认。

完成条件：诊断基于成功 fetch，方案覆盖全部本地工作，暂停要求已满足。

## 3. 检查点先于修改

在仓库外建立私有任务目录：优先可用的 `/tmp/opencode/`，否则用环境提供的临时目录；使用随机唯一子目录和仅本人可读写权限。
进入任务时记录原工作环境的 umask。私有权限仅用于备份目录和证据文件；若使用 `umask 077`，只在备份操作的子 shell 内设置。预演 clone／checkout、live merge 和恢复沿用原 umask，不把备份权限策略传播到工作区；核验实际文件权限（含读写位），不能只看 Git mode。出现非预期权限变化即停，先查清来源。
在执行前记录绝对位置与留存期限；临时目录可能被系统清理，不能称作永久备份。需要跨清理周期时先约定持久位置。
保存诊断、原始 OID、stash 清单、计划和验证证据，秘密不进入仓库或对外日志。

```sh
# 先生成并检查本次唯一 ID；分支名已存在就换 ID，不能覆盖。
git branch "backup/main-before-sync-$id" "$L"
git branch "backup/origin-main-before-sync-$id" "$R"
```

逐条读回分支 tip，必须分别等于 L、R。之后每次再次合并远端，都为当时的两端另建检查点，保留原检查点。
有任意暂存／未暂存／未跟踪内容，**先完整读取并执行 [脏工作与冲突分支](references/dirty-work.md)**；它负责快照、预演、短暂清理和恢复。
干净路径也要检查 ignored 文件是否会被写入或覆盖；不能保护就停。所有 live merge 使用 `--no-overwrite-ignore`，关闭自动 stash。

完成条件：提交检查点读回成功；脏内容已核验快照并预演，或确认原本干净；没有未保护的覆盖风险。

## 4. 合并固定的 R

先复核 HEAD、main、索引和工作区仍等于预期。只有清理后的目标检出可执行以下命令；不用隐式 pull。

| 祖先关系 | 操作 |
| --- | --- |
| L = R，或 R 是 L 的祖先 | main 不变；如有推送授权，进入验证 |
| L 是 R 的祖先 | `git -c merge.autoStash=false merge --ff-only --no-overwrite-ignore "$R"` |
| 两端各有独有提交 | 先在独立临时检出／支持的内存 merge 中预演，再 `git -c merge.autoStash=false merge --no-edit --no-overwrite-ignore "$R"` |

预演不用 live 工作区，也不在其他人的工作树执行；临时检出避免共享索引、用户缓存和自动运行未知 hooks。
预演有冲突就提供安全候选与冲突路径，等待人工决定，不先把标记写进编辑器正在看的文件。
意外 live 冲突：停止后续修改与推送，保留检查点和现场，报告当前操作；不擅自 abort、恢复旧文件或替人选边。
合并完成后立即按脏分支恢复工作，缩短清空窗口；不要把原工作长期留在 stash 等待网络或测试。

完成条件：无未合并索引项／待完成操作；所有未提交工作已恢复并通过语义核对。

## 5. 验证与普通推送

对本次及历次同步检查点逐一执行，任一失败均停止：

```sh
git merge-base --is-ancestor "$L" refs/heads/main
git merge-base --is-ancestor "$R" refs/heads/main
git ls-files --unmerged
```

还要核对备份分支 tip 未变、原 stash OID 全部仍在、工作区／索引语义清单通过；不能只比脏文件数量。
从项目本地文档选择受影响的检查。冲突涉及着色器／界面时，需要相关编译／解析和画面核验，不能仅凭 Git 无冲突认定可用。
复用与当前候选仍有效的通过证据；失败就停。缓存／配额故障可用新的任务专用可丢弃缓存重跑受影响部分，不删别人的任务或任何备份。
记录通过验证的 main 固定 OID `V`；确认它没有收进原有未提交内容。

**仅在适用门允许直接同步 main 且已授权推送时**，推送前再 fetch 并比较远端 OID；要求 rebase／PR 的宿主不执行本节直接推送：

- 仍为 R：确认远端 tip 是 V 的祖先、本地 main 仍为 V，再按已核实的项目发布规则显式普通推送；本技能不授权绕过任务分支或 PR。
- 远端已变：展示新增独有提交；保存新的两端检查点，重新走能力、脏工作预演、merge 和受影响验证，不复用过时快照覆盖新工作。
- 最多进行 **2 次额外同步尝试**；再次变化或安全检查失败就停，请用户协调写入时段。push 期间仍可能竞态：非快进拒绝也按此预算处理。
- 分支保护、权限或服务端校验拒绝是阻塞；报告原因，不强推、不绕过保护，也不擅自改成其他发布流程。

普通 push 成功后再次 fetch，验证 V 为最新远端 tip 的祖先；只有 tip 相等才称两端一致。
若已被他人继续推进，报告“V 已被远端包含，但两端又有差异”，按剩余重试预算处理；预算耗尽则停止。
未授权 push 时只交付本地结果和待推送 OID，不把同步授权扩成发布授权。

完成条件：祖先、未提交内容、项目验证均通过；远端结果有实测证据，或明确未推送／阻塞。

## 6. 交付与携带

简报两端前后 OID、独有提交的去向、merge commit、未提交工作的分类变化、检查结果、备份分支／目录／stash OID、未完成项。
保留全部备份和既有 stash；任何后续清理单独授权。不要把同步成功说成部署成功。

使用：把**整个 `git-sync-preserve/` 文件夹**复制到目标智能体支持的技能目录，按宿主机制发现／调用 `git-sync-preserve`；也可明确要求读取本入口。
仅存放在文档仓库不会自动安装或改变宿主发现规则；本技能不修改全局配置，不依赖特定产品工具或新建代理。
修改本技能时执行 [维护检查与沙箱场景](references/maintenance.md)，运行产物留在任务临时目录。
