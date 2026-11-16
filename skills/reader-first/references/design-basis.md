# 设计依据与适用边界

以下资料支持本技能的取舍原则；技能正文是面向对话与产品内容的独立整理，没有照搬网站自身的格式规定。

| 来源 | 采用的判断 | 适用边界 |
|---|---|---|
| [GOV.UK：满足用户需求](https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/writing-guidelines/meet-user-needs/) | 需求决定应当发布哪些内容 | 政务服务偏向完成事务；对话中的理解、讨论和情感支持也可以是正当需求 |
| [Google Technical Writing：Audience](https://developers.google.com/tech-writing/one/audience) | 补齐完成任务所需知识与已有知识的差值 | 角色只是近似；要结合领域熟悉度和上下文，不把所有读者当新手 |
| [GOV.UK：清晰结构](https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/writing-guidelines/clear-structure/) | 重要信息前置，标题帮助定位 | 不把网页扫读研究换算成通用字数或句数配额 |
| [NN/g：Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/) | 分开主要任务与进阶需求，并让入口及其用途可见 | 原文针对交互界面；不能把费用、限制、失败恢复藏成次要内容 |
| [GOV.UK：有效链接](https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/writing-guidelines/add-links/) | 链接具体目标，在需要处出现，文字说明用途 | 标题不含链接等属于 GOV.UK 站内规则；不要求所有场景照搬 |
| [W3C：WCAG 2.4.4 链接用途](https://www.w3.org/WAI/WCAG21/Understanding/link-purpose-in-context.html) | 链接用途可由文字及其上下文判断 | 不要求每个锚文本都独立解释一切，不以加长标签代替有效上下文 |

正文中把信息安排到按钮、错误提示、报告和对话的规则，是对上述原则的应用设计，不是这些来源逐条证明的实验结论。

## 与邻近技能配合

- `humanizer` / `humanizer-zh`：已有内容的语气与表达需要润色时使用。Reader First 先解决该写什么、写在哪里，润色不能代替信息取舍。
- `writing-for-agents`：最终读者是 agent，尤其在创建技能和修改 agent 约定时，由它负责触发、指令结构与执行可靠性。
- 领域技能：事实调查、工程实现、产品定位等仍由对应技能负责。Reader First 只组织表达，不扩大行动授权。

## 验证原则

本目录的 `test-prompts.json` 保存合成场景及可观察检查项，`trigger-tests.json` 保存触发边界。它们用于维护，写作时无需读取。执行者只拿任务和技能正文；评审者拿任务、匿名产出和检查项。对照实验衡量任务完成与阅读负担，不把字数越少当作越好。

这些测试能发现漏项和明显的结构问题，不能证明所有读者、语言或模型上都有效。实测结论应在交付时按实际样本、模型和评审结果报告。

核对日期：2026-11-17
