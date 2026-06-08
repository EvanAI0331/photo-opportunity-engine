# Location-Time-Subject 摄影机会引擎 MVP

## 本质

云端世界模型第一版不是通用世界模型，而是摄影相关世界状态预测系统。

它只回答一个问题：

某个地点、某个时间、某个题材，是否值得拍，是否值得提醒用户。

## 最小架构

```text
数据源层
  -> 时空标准化层
  -> 摄影特征层
  -> 机会评分模型
  -> Agent 决策层
  -> 手表/手机提醒
```

## 1. 数据源层

### 天气数据

字段：

- 云量
- 云层高度
- 能见度
- 湿度
- 降雨概率
- 风速
- 雾
- 空气质量

用途：

- 日出
- 日落
- 雾景
- 云海
- 火烧云

### 天文数据

字段：

- 日出日落
- 金色时刻
- 蓝调时刻
- 月升月落
- 月相
- 银河位置
- 太阳/月亮方位角

用途：

- 风光
- 星空
- 月亮
- 逆光拍摄窗口

### 地理数据

字段：

- 海岸线
- 山峰
- 湖泊
- 河流
- 城市建筑
- 桥梁
- 观景点
- 海拔
- 朝向
- 遮挡物

用途：

- 判断机位
- 判断视线方向
- 判断前景和主体关系

### 摄影知识数据

字段：

- 热门机位
- 历史照片
- 最佳拍摄季节
- 推荐焦段
- 题材类型

用途：

- 让 Agent 知道一个地点通常拍什么

## 2. 时空标准化层

所有上游数据统一到同一时空查询对象：

```json
{
  "location": {
    "lat": -33.8568,
    "lng": 151.2153
  },
  "time": "2026-06-08T17:12:00+10:00",
  "radius_m": 3000
}
```

核心约束：

- 同一地点
- 同一时间窗口
- 同一半径范围
- 聚合所有可用信息

## 3. 摄影特征层

原始数据必须先转换成摄影语言，再交给评分模型或 Agent。

示例：

```json
{
  "golden_hour": true,
  "sun_azimuth": 287,
  "cloud_cover": 62,
  "high_cloud": 38,
  "visibility_km": 18,
  "fog_probability": 0.12,
  "moon_phase": 0.78,
  "milky_way_visible": false,
  "water_reflection_score": 0.71,
  "landmark_visibility_score": 0.84
}
```

要求：

- LLM 不直接阅读天气 JSON 做核心判断。
- 特征层必须输出可解释摄影因子。
- 缺失字段必须显式标记，不能静默补假数据。

## 4. 机会评分模型

第一版使用规则 + 轻量模型，不上复杂深度学习。

日落评分示例：

```text
sunset_score =
  golden_hour_weight
+ cloud_structure_score
+ visibility_score
+ foreground_score
+ direction_match_score
- rain_penalty
- haze_penalty
```

输出示例：

```json
{
  "opportunity_type": "sunset_landscape",
  "score": 0.86,
  "window": "17:21-17:42",
  "direction": "west-northwest",
  "reason": "high cloud + clear horizon + strong side light"
}
```

要求：

- 输出分数。
- 输出窗口。
- 输出方向。
- 输出主要证据。
- 输出扣分项。
- 不足以判断时返回 blocked 或 insufficient_data，不能伪成功。

## 5. Agent 决策层

Agent 不算天气、不算天文、不算地理基础指标。

Agent 基于工具结果和评分模型决策：

- 是否提醒用户
- 提醒什么
- 提前多久提醒
- 是否值得用户移动
- 推荐哪个机位
- 用什么镜头
- 拍什么主题

示例输出：

```text
18 分钟后海港大桥西北方向可能出现强日落云色。
建议移动到 Mrs Macquarie's Chair，使用 70-200mm 压缩歌剧院与桥。
```

## 推荐技术栈

后端：

- Python
- FastAPI
- PostgreSQL + PostGIS
- Redis
- Celery 或 Temporal

数据库：

- PostGIS：地点、机位、地理对象
- TimescaleDB：天气、天文、历史评分
- Vector DB：摄影作品、机位描述、用户风格记忆

Agent 层：

- LLM + tool calling
- spec 驱动
- skill 驱动
- workflow 调度

## 当前 Harness 接入

已加入轻量 Harness 和持久化 Loop：

- `app/orchestrator.py`
- `app/opportunity_loop.py`
- `app/memory_store.py`
- `docs/harness-loop.md`

当前 loop 可完成数据采集、特征计算、机会评分、Agent 输入包生成、运行记录持久化和反馈记录持久化。

当前尚未接入真实 LLM Agent runtime 和 notification provider，因此不能声明已完成 Agent 最终判断或真实推送。

## MVP 交付边界

第一版只需要做到：

- 知道哪里
- 知道什么时候
- 知道拍什么
- 判断值不值得拍
- 判断值不值得提醒

暂不做：

- 通用世界模拟
- 全自动深度学习训练
- 百科式地点问答
- 无证据的推荐文案生成
- 无 spec 编译器支撑的伪 agent

## 待接入的系统能力

本项目已接入桌面 SpecX 编译器，入口见：

- `specx/contracts/photo_opportunity_agent.contract.json`
- `scripts/specx_compile.sh`
- `specx/README.md`

在实现 Agent 前，仍必须确认运行时具备：

- spec 生成器
- spec 编译器
- agent role spec 产物
- agent execution spec 产物
- agent output spec 产物
- skill 注册和调用机制
- tool calling 运行时
- 执行记录持久化

如果这些能力不存在，先接入系统，不手写伪造已编译 spec。
