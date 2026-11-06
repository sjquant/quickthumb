---
title: quickthumb · Pythonでつくる、繰り返し使えるデザイン
description: 画像、プレゼンテーション、動画をPythonで作成。レイアウトをコードに残し、写真やタイトルを差し替えて次の制作にも活用できます。
template: home.html
hide:
  - navigation
  - toc
---

<section class="qt-hero" aria-labelledby="qt-heading" markdown>
<div class="qt-container qt-hero-layout" markdown>
<div class="qt-hero-copy" markdown>

<p class="qt-eyebrow">画像・スライド・動画をPythonで</p>

<h1 id="qt-heading">一度つくったデザインを、<br>次の制作にも。</h1>

<p class="qt-hero-description">画像、プレゼンテーション、動画をPythonで作成。レイアウトをコードとして残せるため、写真やタイトルを差し替えて繰り返し活用できます。</p>

<div class="qt-actions" markdown>
[作例を見る <span aria-hidden="true">→</span>](cookbook/index.md){ .qt-button .qt-button-white }
[インストールする](installation.md){ .qt-button .qt-button-outline }
</div>

<ul class="qt-traits">
<li><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19.14 7.5A2.86 2.86 0 0 1 22 10.36v3.78A2.86 2.86 0 0 1 19.14 17H12c0 .39.32.96.71.96H17v1.68a2.86 2.86 0 0 1-2.86 2.86H9.86A2.86 2.86 0 0 1 7 19.64v-3.75a2.85 2.85 0 0 1 2.86-2.85h5.25a2.85 2.85 0 0 0 2.85-2.86V7.5zm-4.28 11.79c-.4 0-.72.3-.72.89s.32.71.72.71a.71.71 0 0 0 .71-.71c0-.59-.32-.89-.71-.89m-10-1.79A2.86 2.86 0 0 1 2 14.64v-3.78A2.86 2.86 0 0 1 4.86 8H12c0-.39-.32-.96-.71-.96H7V5.36A2.86 2.86 0 0 1 9.86 2.5h4.28A2.86 2.86 0 0 1 17 5.36v3.75a2.85 2.85 0 0 1-2.86 2.85H8.89a2.85 2.85 0 0 0-2.85 2.86v2.68zM9.14 5.71c.4 0 .72-.3.72-.89s-.32-.71-.72-.71c-.39 0-.71.12-.71.71s.32.89.71.89"/></svg>Python 3.11+</li>
<li><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15.41 22h-.19a.46.46 0 0 1-.26-.27l-2.22-5.8c-.09-.24.03-.51.26-.61.71-.26 1.28-.82 1.58-1.49.64-1.43 0-3.1-1.43-3.74s-3.1 0-3.74 1.41c-.3.71-.32 1.5-.05 2.19.3.74.89 1.31 1.64 1.59.24.09.37.36.28.61L9 21.69c-.04.12-.13.22-.25.27-.12.04-.25.04-.36 0C3.24 19.97.67 14.18 2.66 9.03s7.78-7.72 12.93-5.73c2.47.96 4.46 2.85 5.54 5.27a9.9 9.9 0 0 1 .2 7.65c-1.01 2.66-3.1 4.78-5.75 5.78zM12 3.59c-4.97-.13-9.1 3.8-9.23 8.77a9.01 9.01 0 0 0 5.55 8.54l1.89-4.9c-1.83-1-2.52-3.28-1.53-5.11a3.784 3.784 0 0 1 5.11-1.53 3.775 3.775 0 0 1 0 6.64l1.89 4.93a9.11 9.11 0 0 0 4.76-5c1.84-4.62-.4-9.85-5.02-11.7A9.1 9.1 0 0 0 12 3.59"/></svg>オープンソース</li>
<li><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 3h2v2H5v5a2 2 0 0 1-2 2 2 2 0 0 1 2 2v5h2v2H5c-1.07-.27-2-.9-2-2v-4a2 2 0 0 0-2-2H0v-2h1a2 2 0 0 0 2-2V5a2 2 0 0 1 2-2m14 0a2 2 0 0 1 2 2v4a2 2 0 0 0 2 2h1v2h-1a2 2 0 0 0-2 2v4a2 2 0 0 1-2 2h-2v-2h2v-5a2 2 0 0 1 2-2 2 2 0 0 1-2-2V5h-2V3zm-7 12a1 1 0 0 1 1 1 1 1 0 0 1-1 1 1 1 0 0 1-1-1 1 1 0 0 1 1-1m-4 0a1 1 0 0 1 1 1 1 1 0 0 1-1 1 1 1 0 0 1-1-1 1 1 0 0 1 1-1m8 0a1 1 0 0 1 1 1 1 1 0 0 1-1 1 1 1 0 0 1-1-1 1 1 0 0 1 1-1"/></svg>コードまたはJSON</li>
</ul>

</div>
<div class="qt-artwork" role="group" aria-label="quickthumbで作った作例" markdown>

[![クリエイター向けPythonのサムネイル](assets/home/python-for-creators.png)](cookbook/decks-and-video.md#cleaner-future){ .qt-art .qt-art-front }
[![ポッドキャストのゲスト告知](assets/examples/podcast_interview_promo.png)](cookbook/podcast-promo.md){ .qt-art .qt-art-back }
[![Orbit Atlasプレゼンテーションの表紙](assets/home/orbit-slide-1.webp)](cookbook/decks-and-video.md#orbit-atlas){ .qt-art .qt-art-bottom }

</div>
</div>
</section>

<section class="qt-story" aria-labelledby="images-heading" markdown>
<div class="qt-container qt-story-grid" markdown>
<div class="qt-story-copy" markdown>

<p class="qt-kicker">画像・グラフィック</p>

## 次のサムネイルは、<br>写真とタイトルを<br>差し替えて。 { #images-heading }

文字や写真、図形の配置をコードに残せます。写真やタイトルを差し替えて、同じレイアウトのサムネイルやSNS画像を続けて作れます。

[サムネイルの作例を見る <span aria-hidden="true">→</span>](cookbook/decks-and-video.md#orbit-atlas){ .qt-button .qt-button-blue }

</div>
<div class="qt-visual qt-image-pair" markdown>

![Pythonで地球を地図にしたというタイトルのクリエイター用サムネイル](assets/home/orbit-thumbnail-planet.webp)

```python
# Simplified from examples/orbit_atlas.py
canvas = Canvas(WIDTH, HEIGHT).image(
    CREATOR, (0, 0), WIDTH, HEIGHT, fit="cover"
)
canvas.text(
    "I MAPPED\nTHE PLANET", position=(716, 58),
    font=HEAVY, size=86, color=WHITE,
)
canvas.shape("rectangle", (722, 252), 486, 104,
             YELLOW, rotation=-3)
canvas.text(
    "WITH PYTHON", position=(756, 270),
    font=HEAVY, size=62, color="#111923",
    rotation=-3,
)
```

</div>
</div>
</section>

<section class="qt-story qt-story-tinted" aria-labelledby="slides-heading" markdown>
<div class="qt-container qt-story-grid" markdown>
<div class="qt-story-copy" markdown>

<p class="qt-kicker">プレゼンテーション</p>

## スライドづくりも、<br>Pythonで。 { #slides-heading }

表紙から各スライドまでコードで組み立て、ひとつのプレゼンテーションにまとめられます。ブラウザーで表示できるほか、PowerPointファイルとしても出力できます。

[スライドの作例を見る <span aria-hidden="true">→</span>](cookbook/decks-and-video.md#orbit-atlas){ .qt-button .qt-button-blue }

</div>
<div class="qt-visual qt-deck-preview" markdown>

![山と湖を配置したOrbit Atlasプレゼンテーションの表紙](assets/home/orbit-slide-1.webp)

<div class="qt-slide-strip" markdown>

<img src="/assets/home/orbit-slide-1.webp" alt="">

![Orbit Atlasのカバレッジグラフ](assets/home/orbit-slide-2.webp)

![Orbit Atlasの指標スライド](assets/home/orbit-slide-3.webp)

![Orbit Atlasの締めくくりのスライド](assets/home/orbit-slide-4.webp)

</div>

</div>
</div>
</section>

<section class="qt-story" aria-labelledby="motion-heading" markdown>
<div class="qt-container qt-story-grid" markdown>
<div class="qt-story-copy" markdown>

<p class="qt-kicker">動画・アニメーション</p>

## 文字が現れ、<br>写真が動く。 { #motion-heading }

文字や写真に動きをつけ、シーンの長さを指定して動画やGIFを作成できます。音楽を加えた仕上がりは、下のOrbit Atlasの動画で確認できます。

[動画の作例を見る <span aria-hidden="true">→</span>](cookbook/decks-and-video.md#orbit-atlas){ .qt-button .qt-button-blue }

</div>
<div class="qt-visual qt-video-preview">
<div class="qt-video-player">
<video controls playsinline preload="none" poster="/assets/home/orbit-film-poster.webp" aria-label="quickthumbで生成したOrbit Atlasアニメーション">
<source src="/assets/home/orbit-film.mp4" type="video/mp4">
このブラウザーは動画に対応していません。 <a href="/assets/home/orbit-film.mp4">動画をダウンロード</a>。
</video>
<button class="qt-play" type="button" data-qt-play aria-label="Orbit Atlasの動画を再生"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.14v14l11-7z"/></svg></button>
</div>
<div class="qt-video-frames">
<img src="/assets/home/orbit-film-frame-1.webp" width="480" height="270" alt="動画の一場面：近くから見た地球" loading="lazy">
<img src="/assets/home/orbit-film-frame-2.webp" width="480" height="270" alt="動画の一場面：山を登るルートを示した「Every trail」" loading="lazy">
<img src="/assets/home/orbit-film-frame-3.webp" width="480" height="270" alt="動画の一場面：上昇する棒グラフを示した「Every number」" loading="lazy">
</div>
</div>
</div>
</section>

<section class="qt-story qt-story-tinted" aria-labelledby="reuse-heading" markdown>
<div class="qt-container qt-story-grid" markdown>
<div class="qt-story-copy" markdown>

<p class="qt-kicker">レイアウトをコードに残す</p>

## 次の制作は、<br>手元のコードから。 { #reuse-heading }

PythonやJSONで残したレイアウトは、次の制作に合わせて書き換えて再利用できます。下の作例では、ひとつのスクリプトからサムネイル、プレゼンテーション、動画をそれぞれ出力しています。

</div>
<div class="qt-visual qt-reuse" markdown>

```python
# Simplified from examples/orbit_atlas.py
planet_thumbnail().render(
    str(out / "orbit-thumbnail-planet.webp"),
    quality=88,
)

slides = deck()
slides.render(str(out / "orbit-deck.html"))
if args.pptx:
    slides.render(str(out / "orbit-deck.pptx"))

if not args.stills:
    render_film(out)  # orbit-film.mp4
```

<ul class="qt-outputs">
<li><img src="/assets/home/orbit-thumbnail-planet.webp" width="1280" height="720" alt="" loading="lazy"><span><strong>サムネイル</strong>WebP</span></li>
<li><img src="/assets/home/orbit-slide-1.webp" width="1280" height="720" alt="" loading="lazy"><span><strong>プレゼンテーション</strong>HTML, PPTX</span></li>
<li><img src="/assets/home/orbit-film-poster.webp" width="1280" height="720" alt="" loading="lazy"><span><strong>動画</strong>MP4</span></li>
</ul>

</div>
</div>
</section>

<section class="qt-story" id="install" aria-labelledby="install-heading" markdown>
<div class="qt-container qt-story-grid" markdown>
<div class="qt-story-copy" markdown>

<p class="qt-kicker">はじめる</p>

## 作例を、<br>自分好みにアレンジ。 { #install-heading }

Python 3.11以降が必要です。インストール後は、作例のタイトルや色を変えて最初の一枚を出力してみてください。

インストール手順は[インストールガイド](installation.md)をご覧ください。

[最初のカードをつくる <span aria-hidden="true">→</span>](getting-started.md){ .qt-button .qt-button-dark }

</div>
<div class="qt-visual" markdown>

```bash
python -m pip install quickthumb
```

</div>
</div>
</section>
