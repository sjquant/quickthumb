---
description: そのまま実行できるquickthumbのYouTubeサムネイル、Instagramカード、ポッドキャスト告知、Shortsカバー、AIワークフローのレシピを探します。
---

# レシピ集 { #cookbook }

作りたい画像、プレゼンテーション、動画を選んでください。プレビューはそれぞれリンク先の例から生成したものです。文字、画像、色を変えて自分の制作に応用できます。

## プレゼンテーションと動画 { #presentations-and-video }

<div class="qt-gallery" markdown>
<figure markdown="span">
[![Orbit Atlasプレゼンテーションの表紙](../assets/home/orbit-slide-1.webp)](decks-and-video.md#orbit-atlas)
<figcaption>プレゼンテーションとスライド</figcaption>
</figure>
<figure markdown="span">
[![Orbit Atlas動画のプレビュー](../assets/home/orbit-film-poster.webp)](decks-and-video.md#orbit-atlas)
<figcaption>アニメーション動画</figcaption>
</figure>
</div>

[プレゼンテーションと動画の例を見る →](decks-and-video.md)

## 画像とグラフィック { #images-and-graphics }

<div class="qt-gallery qt-gallery--cookbook" markdown>
<figure markdown="span">
[![YouTubeサムネイル](../assets/examples/youtube_thumbnail_01.png)](youtube-thumbnail.md#before-after)
<figcaption>YouTubeサムネイル</figcaption>
</figure>
<figure markdown="span">
[![燃え尽き症候群をテーマにした画像](../assets/examples/youtube_thumbnail_02.png)](youtube-thumbnail.md#burnout)
<figcaption>燃え尽き症候群</figcaption>
</figure>
<figure markdown="span">
[![Instagramニュースカード](../assets/examples/instagram_news_card.png)](instagram-card.md)
<figcaption>Instagramニュースカード</figcaption>
</figure>
<figure markdown="span">
[![人物を主役にした画像](../assets/examples/youtube_talking_head.png)](youtube-thumbnail.md#talking-head)
<figcaption>人物を主役にする</figcaption>
</figure>
<figure markdown="span">
[![リアクション・解説用の画像](../assets/examples/youtube_reaction.png)](youtube-thumbnail.md#reaction)
<figcaption>リアクション・解説</figcaption>
</figure>
<figure markdown="span">
[![チュートリアル・説明用の画像](../assets/examples/youtube_tutorial_explainer.png)](youtube-thumbnail.md#tutorial)
<figcaption>チュートリアル・説明</figcaption>
</figure>
<figure markdown="span">
[![ポッドキャストの告知](../assets/examples/podcast_interview_promo.png)](podcast-promo.md)
<figcaption>ポッドキャストの告知</figcaption>
</figure>
<figure markdown="span">
[![Shorts・縦長カバー](../assets/examples/shorts_cover_agent.png)](shorts-cover.md)
<figcaption>Shorts・縦長カバー</figcaption>
</figure>
<figure markdown="span">
[![リリース告知](../assets/examples/launch_announcement.png)](launch-announcement.md)
<figcaption>リリース告知</figcaption>
</figure>
</div>

## 制作の幅を広げる { #more-ways-to-create }

- [最初のカードを作る](../getting-started.md)：リポジトリをクローンせずにレイアウトを再利用します。
- [AIワークフロー](ai-workflow.md)：JSONレイアウトを生成、検証、レンダリングします。
- [Webフォントと背景除去](webfonts-rembg.md)：書体を加えたり、人物を切り抜いたりします。

## レシピを実行する { #running-the-recipes }

多くのレシピはリポジトリに同梱されたフォントと写真を使います。[uv](https://docs.astral.sh/uv/)をインストールし、クローンしたリポジトリで実行してください。

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/instagram_news_card.py
```

YouTubeレイアウトのうち2つは`remove_background=True`で人物を切り抜きます。Python 3.11以降が必要な`rembg`追加機能をインストールしてください。

```bash
uv run --extra rembg python examples/youtube_reaction.py
```
