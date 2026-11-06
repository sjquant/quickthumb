---
description: 浏览可直接运行的 quickthumb 示例，涵盖 YouTube 缩略图、Instagram 卡片、播客宣传图、Shorts 封面及 AI 工作流。
---

# 示例集 { #cookbook }

选择你想制作的图像、演示文稿或视频。每个预览均由对应的示例脚本直接生成；你可以修改其中的文案、图片和配色，快速应用到自己的工作中。

## 演示文稿与视频 { #presentations-and-video }

<div class="qt-gallery" markdown>
<figure markdown="span">
[![Orbit Atlas 演示文稿封面](../assets/home/orbit-slide-1.webp)](decks-and-video.md#orbit-atlas)
<figcaption>演示文稿与幻灯片</figcaption>
</figure>
<figure markdown="span">
[![Orbit Atlas 视频预览](../assets/home/orbit-film-poster.webp)](decks-and-video.md#orbit-atlas)
<figcaption>动画视频</figcaption>
</figure>
</div>

[探索演示文稿与视频示例 →](decks-and-video.md)

## 图像与图形 { #images-and-graphics }

<div class="qt-gallery qt-gallery--cookbook" markdown>
<figure markdown="span">
[![YouTube 缩略图](../assets/examples/youtube_thumbnail_01.png)](youtube-thumbnail.md#before-after)
<figcaption>YouTube 缩略图</figcaption>
</figure>
<figure markdown="span">
[![职业倦怠主题](../assets/examples/youtube_thumbnail_02.png)](youtube-thumbnail.md#burnout)
<figcaption>职业倦怠主题</figcaption>
</figure>
<figure markdown="span">
[![Instagram 新闻卡片](../assets/examples/instagram_news_card.png)](instagram-card.md)
<figcaption>Instagram 新闻卡片</figcaption>
</figure>
<figure markdown="span">
[![出镜人像](../assets/examples/youtube_talking_head.png)](youtube-thumbnail.md#talking-head)
<figcaption>出镜人像</figcaption>
</figure>
<figure markdown="span">
[![反应 / 解说](../assets/examples/youtube_reaction.png)](youtube-thumbnail.md#reaction)
<figcaption>反应 / 解说</figcaption>
</figure>
<figure markdown="span">
[![教程 / 解说](../assets/examples/youtube_tutorial_explainer.png)](youtube-thumbnail.md#tutorial)
<figcaption>教程 / 解说</figcaption>
</figure>
<figure markdown="span">
[![播客宣传图](../assets/examples/podcast_interview_promo.png)](podcast-promo.md)
<figcaption>播客宣传图</figcaption>
</figure>
<figure markdown="span">
[![Shorts / 竖版封面](../assets/examples/shorts_cover_agent.png)](shorts-cover.md)
<figcaption>Shorts / 竖版封面</figcaption>
</figure>
<figure markdown="span">
[![发布公告](../assets/examples/launch_announcement.png)](launch-announcement.md)
<figcaption>发布公告</figcaption>
</figure>
</div>

## 更多创作方式 { #more-ways-to-create }

- [渲染第一组卡片](../getting-started.md)：无需克隆代码仓库，直接复用一套版式。
- [AI 工作流](ai-workflow.md)：生成、校验并渲染 JSON 规范版式。
- [网络字体与背景移除](webfonts-rembg.md)：引入自定义字体或对人像进行抠图。

## 运行示例代码 { #running-the-recipes }

大部分示例均直接使用代码仓库内自带的字体和图片。
安装 [uv](https://docs.astral.sh/uv/) 后，克隆代码仓库并在本地运行：

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/instagram_news_card.py
```

其中有两个 YouTube 版式使用 `remove_background=True` 移除了人像背景。
它们需要安装 `rembg` 额外依赖（支持 Python 3.11 或更高版本）：

```bash
uv run --extra rembg python examples/youtube_reaction.py
```
