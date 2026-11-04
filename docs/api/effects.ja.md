---
description: quickthumbの輪郭線、影、グロー、フィルター、テキスト背景、粒子、デュオトーン、内側の影、背景ぼかしと、対応するレイヤーを説明します。
---

# エフェクト { #effects }

エフェクトは1枚のレイヤーの描き方を変えます。使えるものはレイヤーの種類で決まり、対応しないものを渡すと`ValidationError`になります。

| エフェクト | テキスト | 画像、SVG、動画 | 図形 | 背景 |
| --- | :---: | :---: | :---: | :---: |
| `Stroke` | ✓ | ✓ | ✓ | — |
| `Shadow` | ✓ | ✓ | ✓ | — |
| `Glow` | ✓ | ✓ | ✓ | — |
| `Filter` | — | ✓ | — | ✓ |
| `Background` | ✓ | — | — | — |
| `Grain` | — | ✓ | — | ✓ |
| `Duotone` | — | ✓ | — | — |
| `InnerShadow` | — | ✓ | ✓ | — |
| `BackdropBlur` | — | ✓ | ✓ | — |

レイヤーの`effects`にリストで渡してください。

```python
from quickthumb import Shadow, Stroke

canvas.text(
    content="CLICK NOW",
    size=96,
    color="#FFFFFF",
    effects=[
        Stroke(width=4, color="#000000"),
        Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=8),
    ],
)
```

---

## Stroke { #stroke }

文字のグリフ、画像の縁、図形の縁に輪郭線を描きます。

```python
from quickthumb import Stroke

Stroke(width=4, color="#000000")
```

| パラメーター | 型 | 説明 |
| --- | --- | --- |
| `width` | `int` | 線の太さ（ピクセル）。正の整数です。 |
| `color` | `str` | 線の色。16進文字列（`"#RRGGBB"`、`"#RRGGBBAA"`）です。 |

### 例 { #example }

```python
from quickthumb import Stroke, TextPart

canvas.text(
    content=[
        TextPart(text="BIG TEXT", color="#FFFFFF", effects=[Stroke(width=6, color="#000000")]),
    ],
    size=108,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

---

## Shadow { #shadow }

レイヤーからずらした位置に影を付けます。

```python
from quickthumb import Shadow

Shadow(offset_x=4, offset_y=8, color="#000000", blur_radius=12)
```

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `offset_x` | `int` | **必須** | 横方向のずれ（ピクセル）。負の値も使えます。 |
| `offset_y` | `int` | **必須** | 縦方向のずれ（ピクセル）。負の値も使えます。 |
| `color` | `str` | **必須** | 影の色。16進文字列です。 |
| `blur_radius` | `int` | `0` | ぼかしの広がり（ピクセル）。0以上の整数です。 |

### 例 { #example_1 }

```python
from quickthumb import Shadow

canvas.image(
    path="portrait.png",
    position=("74%", "54%"),
    width=420,
    height=520,
    effects=[Shadow(offset_x=0, offset_y=14, color="#000000", blur_radius=24)],
)
```

---

## Glow { #glow }

レイヤーの周囲に柔らかな色の光を付けます。

```python
from quickthumb import Glow

Glow(color="#B8FF00", radius=16, opacity=0.35)
```

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `color` | `str` | **必須** | 光の色。16進文字列です。 |
| `radius` | `int` | **必須** | 光の広がり（ピクセル）。正の整数です。 |
| `opacity` | `float` | `1.0` | `0.0`–`1.0`の光の強さです。 |

### 例 { #example_2 }

```python
from quickthumb import Glow

canvas.text(
    content="ELECTRIC",
    size=96,
    color="#FFFFFF",
    effects=[Glow(color="#22d3ee", radius=24, opacity=0.5)],
)
```

---

## Filter { #filter }

画像処理による調整です。背景と画像レイヤーに使います。

```python
from quickthumb import Filter

Filter(blur=4, brightness=0.75, contrast=1.1, saturation=0.9)
```

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `blur` | `int` | `0` | ガウスぼかしの半径。0以上の整数です。 |
| `brightness` | `float` | `1.0` | 明るさの倍率。正の実数です。`1.0`は変更なし、`0.5`は半分です。 |
| `contrast` | `float` | `1.0` | コントラストの倍率。正の実数です。`1.0`は変更なしです。 |
| `saturation` | `float` | `1.0` | 彩度の倍率。0以上の実数です。`0.0`はグレースケール、`1.0`は変更なしです。 |

すべての既定値は中立なので、変えたい項目だけ指定します。

### 例 { #example_3 }

```python
from quickthumb import Filter

canvas.background(
    image="hero.jpg",
    fit="cover",
    effects=[Filter(blur=6, brightness=0.6, saturation=0.8)],
)
```

---

## Background（テキストの背景） { #background-text-fill }

テキストブロックの背後に、塗りのある角丸長方形を描きます。テキストレイヤー専用です。

```python
from quickthumb import Background

Background(color="#111827CC", padding=(16, 24), border_radius=14, opacity=1.0)
```

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `color` | `str` | **必須** | 塗りの色。16進文字列（`"#RRGGBB"`、`"#RRGGBBAA"`）です。 |
| `padding` | `int \| tuple` | `0` | 内側の余白。均一な`int`、`(vertical, horizontal)`、`(top, right, bottom, left)`です。 |
| `border_radius` | `int` | `0` | 角の丸み（ピクセル）。0以上の整数です。 |
| `opacity` | `float` | `1.0` | `0.0`–`1.0`の塗りの不透明度です。 |

### 例 { #example_4 }

```python
from quickthumb import Background

canvas.text(
    content="BREAKING NEWS",
    size=72,
    color="#FFFFFF",
    position=("8%", "50%"),
    align=("left", "middle"),
    effects=[
        Background(color="#CC0000", padding=(12, 20), border_radius=8),
    ],
)
```

!!! note
    エフェクトの`Background`とレイヤービルダーの`.background()`は別です。エフェクトはテキストの背後に適用し、レイヤーはキャンバス全体を覆います。

---

## Grain { #grain }

背景や画像にフィルム粒子のノイズを加えます。

```python
from quickthumb import Grain

Grain(intensity=0.12, monochrome=True, blend_mode="overlay", opacity=1.0)
```

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `intensity` | `float` | **必須** | ノイズの振幅。`0.0`（なし）から`1.0`（最大）です。 |
| `monochrome` | `bool` | `True` | `True`は輝度ノイズ（灰色の粒子）、`False`はチャンネルごとに独立した色ノイズです。 |
| `blend_mode` | `str` | `"overlay"` | ノイズの合成方法。`"overlay"`、`"screen"`、`"multiply"`、`"normal"`です。 |
| `opacity` | `float` | `1.0` | 全体の強さ。`0.0`（見えない）から`1.0`（完全）です。 |
| `seed` | `int \| None` | `None` | 再現可能な出力の乱数シード。`None`なら描画ごとにランダムです。 |

`intensity=0.0`ならノイズを加えません。

### 例 { #example_5 }

```python
from quickthumb import Canvas, Grain

canvas = (
    Canvas(1280, 720)
    .background(
        color="#1A1A2E",
        effects=[Grain(intensity=0.12, monochrome=True)],
    )
    .image(
        path="portrait.png",
        position=("70%", "50%"),
        width=400,
        height=500,
        align=("center", "middle"),
        effects=[Grain(intensity=0.08, monochrome=False, blend_mode="overlay", opacity=0.6)],
    )
)
```

!!! note
    `Grain`は背景、画像、SVG、動画に使えます。テキストと図形には使えません。

---

## Duotone { #duotone }

明るさに応じて2色へ変換します。暗部は`shadows`、明部は`highlights`となり、その間を滑らかに混ぜます。写真をブランドカラーに揃えるときに便利です。

```python
from quickthumb import Duotone

Duotone(shadows="#0A1730", highlights="#7FADFF", opacity=1.0)
```

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `shadows` | `str` | **必須** | 最も暗い部分の色です。 |
| `highlights` | `str` | **必須** | 最も明るい部分の色です。 |
| `opacity` | `float` | `1.0` | 元の色を置き換える強さ。`0.0`–`1.0`です。 |

---

## InnerShadow { #innershadow }

レイヤーの縁の内側に影を描き、へこんだように見せます。

```python
from quickthumb import InnerShadow

InnerShadow(offset_x=0, offset_y=6, color="#00000080", blur_radius=12)
```

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `color` | `str` | **必須** | 影の色。色に含まれるアルファを反映します。 |
| `offset_x` | `int` | `0` | 横方向のずれ（ピクセル）です。 |
| `offset_y` | `int` | `0` | 縦方向のずれ（ピクセル）です。 |
| `blur_radius` | `int` | `0` | ぼかしの半径（ピクセル）です。 |
| `opacity` | `float` | `1.0` | 全体の強さ。`0.0`–`1.0`です。 |

---

## BackdropBlur { #backdropblur }

すりガラスのように、レイヤーの形の内側で、すでに背後に描かれた内容をぼかします。半透明の塗りを組み合わせると、パネルの形も見せられます。

```python
from quickthumb import BackdropBlur, Canvas

canvas = (
    Canvas(1280, 720)
    .background(image="photo.jpg", fit="cover")
    .shape(
        shape="rectangle",
        position=(80, 440),
        width=640,
        height=200,
        color="#FFFFFF33",
        border_radius=24,
        effects=[BackdropBlur(radius=24)],
    )
)
```

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `radius` | `int` | **必須** | ぼかしの半径（ピクセル）です。 |
| `opacity` | `float` | `1.0` | ぼかした背景を表示する強さ。`0.0`–`1.0`です。 |
