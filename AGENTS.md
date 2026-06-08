# AGENTS.md

## Core Engineering Baseline

机制必须是 agent/LLM + 脚本共同执行：agent 依靠 skill 和 spec 执行，脚本只负责取数、标准化、特征计算、校验、持久化、工具执行等可验证工作。

严禁把 agent 当傀儡，用硬编码关键词脚本承担核心决策。严禁硬编码写死、降级兜底、伪成功态、伪完成态。没有 LLM 支撑的模块，严禁称为 agent。

Agent 核心逻辑必须是 LLM 驱动，并通过 workflow 调用 tools/scripts/skills。约束类内容写入对应 agent spec；方式、技巧、策略、能力类内容写入对应 skill。

必须为 agent 建立专用的角色 spec、执行 spec 和输出 spec 文件。spec 文件必须通过系统内置专业 spec 生成和编译器生成；如果项目缺少 spec 生成器或编译器，必须先提示用户接入系统，不能手写伪造已编译 spec。

## Product Boundary

本项目不是百科式世界模型，也不是通用真实世界模拟器。

目标是构建摄影相关世界状态预测系统：

- 某个地点
- 某个时间
- 某个题材
- 是否值得拍
- 是否值得提醒用户

第一版核心形态是 Location-Time-Subject 摄影机会引擎。

## Architecture Principle

数据、规则和模型负责形成可解释摄影机会；Agent 负责基于机会、用户偏好、移动成本和提醒策略做决策。

LLM 不直接阅读原始天气 JSON 进行拍摄判断。原始数据必须先经过时空标准化和摄影特征转换。

推荐分层：

1. 数据源层
2. 时空标准化层
3. 摄影特征层
4. 机会评分模型
5. Agent 决策层
6. 手表/手机提醒

## Agent Boundary

Agent 不负责计算天气、天文、地理基础指标。

Agent 负责：

- 是否提醒用户
- 提醒什么内容
- 提前多久提醒
- 是否值得用户移动
- 推荐哪个机位
- 推荐镜头和焦段
- 推荐拍摄主题
- 解释机会原因

Agent 可调用工具：

- `weather_tool`
- `astronomy_tool`
- `geo_visibility_tool`
- `photo_spot_tool`
- `user_style_tool`
- `notification_tool`

## Implementation Guardrails

- 不允许用关键词路由替代 agent 决策。
- 不允许把失败包装成成功。
- 不允许在缺数据时静默降级成虚假结论。
- 评分规则可以是脚本或轻量模型，但必须输出可解释中间结果。
- Agent 输入应为摄影因子、机会评分、候选机位、用户偏好和工具证据。
- Agent 输出必须可校验，并按输出 spec 持久化。

## Communication

确保言简意赅，少用 token。
