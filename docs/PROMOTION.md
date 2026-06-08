# Promotion Kit

## One-Liner

Photo Opportunity Engine is an open-source Location-Time-Subject engine that predicts when a place is worth photographing.

## Short Description

Photo Opportunity Engine combines weather, sun/moon geometry, OpenStreetMap geography, curated photo spots, and LLM Agent decisions to answer one practical question: should a photographer go shoot this location now?

It ships with a FastAPI backend, a static dashboard, SpecX-governed Agent contracts, a persistent opportunity loop, and a spot-photo factor research database built from open photo sources such as Wikimedia Commons and iNaturalist.

## GitHub About

Description:

```text
Open-source Location-Time-Subject photography opportunity engine with weather, astronomy, geo evidence, factor research, and LLM Agent decisions.
```

Website:

```text
https://github.com/EvanAI0331/photo-opportunity-engine
```

Topics:

```text
photography, ai-agent, fastapi, open-meteo, openstreetmap, wikimedia-commons, inaturalist, astronomy, suncalc, factor-research
```

## Launch Post

```text
I open-sourced Photo Opportunity Engine.

It is not a generic world model. It is a practical Location-Time-Subject engine for photography:

Given a place, a time, and a subject, should you shoot or skip?

The MVP connects:
- Open-Meteo weather
- Sun/moon geometry via SunCalc
- OpenStreetMap geography
- curated photo spots
- Wikimedia Commons / iNaturalist photo evidence
- SpecX-governed LLM Agent decisions

It turns raw weather and geo data into photography features like golden hour, high cloud, visibility, water reflection, direction match, and spot-subject match.

Repo:
https://github.com/EvanAI0331/photo-opportunity-engine
```

## Short Social Post

```text
Open-sourced a photography opportunity engine.

Location + Time + Subject -> worth shooting?

Weather, sun/moon geometry, OSM, curated spots, open photo evidence, factor research, and an LLM Agent decision layer.

https://github.com/EvanAI0331/photo-opportunity-engine
```

## Chinese Launch Copy

```text
我开源了一个摄影机会引擎 Photo Opportunity Engine。

它不是通用世界模型，而是一个很具体的 Location-Time-Subject 摄影机会系统：

某个地点、某个时间、某个题材，到底值不值得拍？

当前 MVP 已接入：
- Open-Meteo 天气
- SunCalc 太阳/月亮几何
- OpenStreetMap 地理信息
- 人工机位库
- Wikimedia Commons / iNaturalist 开放照片证据
- SpecX 约束的 LLM Agent 决策层

它会把天气和地理数据转成摄影因子，比如金色时刻、高云、能见度、水面反射、方向匹配、机位题材匹配，然后再做机会评分和 Agent 决策。

GitHub:
https://github.com/EvanAI0331/photo-opportunity-engine
```

## Distribution Checklist

- GitHub repository is public.
- README explains the product, quick start, screens, API, and factor research.
- Runtime secrets and SQLite databases are excluded.
- Clean zip package is generated at `dist/photo-opportunity-engine-clean.zip`.
- GitHub topics should be added from the About panel or with `gh repo edit --add-topic`.

## Suggested Channels

- GitHub social post
- X / Twitter
- LinkedIn
- Hacker News `Show HN`
- Reddit: r/photography, r/opensource, r/selfhosted, r/Python
- Product Hunt after a hosted demo exists

## Next Public Demo Milestone

Before wider launch beyond GitHub, add:

- hosted read-only demo
- example Sydney run output
- screenshots exported as PNG
- a small sample SQLite seed database with non-sensitive open data
- a 60-second demo video
