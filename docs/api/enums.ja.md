---
description: 整列、画像のフィット、図形、フィルター、色の変化に使うquickthumbの列挙型とグラデーションモデルを説明します。
---

# 列挙型とグラデーション { #enums-gradients }

## Align { #align }

レイヤーのどの点を`position`へ合わせるかと、テキストの横方向の整列を決めます。

```python
from quickthumb import Align
```

### 値 { #values }

| 列挙型 | 文字列の別名 | 横 | 縦 |
| --- | --- | --- | --- |
| `Align.CENTER` | `"center"` | 中央 | 中央 |
| `Align.LEFT` | `"left"` | 左 | 中央 |
| `Align.RIGHT` | `"right"` | 右 | 中央 |
| `Align.TOP_LEFT` | `"top-left"` | 左 | 上 |
| `Align.TOP_CENTER` | `"top-center"` | 中央 | 上 |
| `Align.TOP_RIGHT` | `"top-right"` | 右 | 上 |
| `Align.BOTTOM_LEFT` | `"bottom-left"` | 左 | 下 |
| `Align.BOTTOM_CENTER` | `"bottom-center"` | 中央 | 下 |
| `Align.BOTTOM_RIGHT` | `"bottom-right"` | 右 | 下 |

### 使い方 { #usage }

```python
# Enum value
canvas.image(..., align=Align.TOP_LEFT)

# String alias
canvas.image(..., align="center")

# (horizontal, vertical) tuple
canvas.image(..., align=("center", "middle"))
```

タプルの横方向は`"left"`、`"center"`、`"right"`、縦方向は`"top"`、`"middle"`、`"bottom"`です。

---

## BlendMode { #blendmode }

先に描かれたレイヤーとの合成方法を決めます。

```python
from quickthumb import BlendMode
```

### 値 { #values_1 }

| 列挙型 | 文字列の別名 | 効果 |
| --- | --- | --- |
| `BlendMode.NORMAL` | `"normal"` | 特別なブレンドをせず上に描きます。 |
| `BlendMode.MULTIPLY` | `"multiply"` | 色を乗算して暗くします。 |
| `BlendMode.OVERLAY` | `"overlay"` | 乗算とスクリーンを組み合わせます。 |
| `BlendMode.SCREEN` | `"screen"` | 反転、乗算、再反転で明るくします。 |
| `BlendMode.DARKEN` | `"darken"` | ピクセルごとに暗い方を選びます。 |
| `BlendMode.LIGHTEN` | `"lighten"` | ピクセルごとに明るい方を選びます。 |

### 使い方 { #usage_1 }

```python
# Enum value
canvas.background(image="texture.jpg", blend_mode=BlendMode.MULTIPLY)

# String alias
canvas.background(image="texture.jpg", blend_mode="multiply")
```

`.background()`と`.image()`で使えます。

---

## FitMode { #fitmode }

目標の枠が指定されているときに、画像をどう拡大縮小するかを決めます。

```python
from quickthumb import FitMode
```

### 値 { #values_2 }

| 列挙型 | 文字列の別名 | 動作 |
| --- | --- | --- |
| `FitMode.COVER` | `"cover"` | 枠を埋め、はみ出しを切り取ります。 |
| `FitMode.CONTAIN` | `"contain"` | 全体を枠内に収め、残りに余白を付けます。 |
| `FitMode.FILL` | `"fill"` | 縦横比を無視し、枠いっぱいに引き伸ばします。 |

### 使い方 { #usage_2 }

```python
# Enum value
canvas.image(path="portrait.png", position=("75%", "55%"), width=420, height=520, fit=FitMode.COVER)

# String alias
canvas.image(path="portrait.png", position=("75%", "55%"), width=420, height=520, fit="cover")
```

`.background(image=...)`と`.image()`で使えます。`width`と`height`の両方で目標の枠が定まる場合にだけ適用します。背景レイヤーではキャンバス全体がその枠です。

---

## LinearGradient { #lineargradient }

角度と色の停止点で定義する線形グラデーションです。

```python
from quickthumb import LinearGradient

LinearGradient(
    angle=135,
    stops=[("#FF5733", 0.0), ("#3333FF", 1.0)],
)
```

| パラメーター | 型 | 説明 |
| --- | --- | --- |
| `angle` | `float` | 方向（度）。`0`は上から下、`90`は左から右です。 |
| `stops` | `list[tuple[str, float]]` | `(color, position)`のリスト。位置は`0.0`–`1.0`の実数です。 |

### 例 { #examples }

```python
# Top-to-bottom dark fade
LinearGradient(angle=0, stops=[("#000000", 0.0), ("#00000000", 1.0)])

# Diagonal blue-to-purple
LinearGradient(angle=135, stops=[("#3B82F6", 0.0), ("#8B5CF6", 1.0)])

# Three-stop gradient
LinearGradient(
    angle=90,
    stops=[("#FF0000", 0.0), ("#00FF00", 0.5), ("#0000FF", 1.0)],
)
```

`.background(gradient=...)`へ渡します。

```python
canvas.background(
    gradient=LinearGradient(angle=120, stops=[("#0F172A", 0.0), ("#0F172A00", 1.0)]),
    opacity=0.8,
)
```

---

## RadialGradient { #radialgradient }

中心点から広がる放射状のグラデーションです。

```python
from quickthumb import RadialGradient

RadialGradient(
    stops=[("#FF5733", 0.0), ("#3333FF", 1.0)],
    center=(0.5, 0.5),
)
```

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `stops` | `list[tuple[str, float]]` | **必須** | `(color, position)`のリスト。位置は`0.0`–`1.0`の実数です。 |
| `center` | `tuple[float, float]` | `(0.5, 0.5)` | キャンバスの寸法に対する比率`(x, y)`で指定する中心です。 |

### 例 { #examples_1 }

```python
# Vignette (dark edges, bright center)
RadialGradient(
    stops=[("#00000000", 0.0), ("#000000CC", 1.0)],
    center=(0.5, 0.5),
)

# Off-center spotlight
RadialGradient(
    stops=[("#FFFFFF33", 0.0), ("#FFFFFF00", 1.0)],
    center=(0.25, 0.3),
)
```

`.background(gradient=...)`へ渡します。

```python
canvas.background(
    gradient=RadialGradient(
        stops=[("#22d3ee33", 0.0), ("#22d3ee00", 1.0)],
        center=(0.5, 0.5),
    ),
)
```

---

## TextFillImage { #textfillimage }

文字のグリフを画像で塗ります。テキストのバウンディングボックスに合わせて画像を拡大縮小し、文字の形にマスクします。

```python
from quickthumb import TextFillImage

TextFillImage(
    path="fire_texture.jpg",
    fit="cover",
)
```

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `path` | `str` | **必須** | 塗りに使う画像のローカルパスかリモートURLです。 |
| `fit` | `str \| FitMode` | `"cover"` | テキストの枠への合わせ方。`"cover"`、`"contain"`、`"fill"`です。 |

### 例 { #examples_2 }

```python
from quickthumb import Canvas, TextFillImage

# Local file
canvas.text(
    content="FIRE",
    size=140,
    fill=TextFillImage(path="assets/fire_texture.jpg", fit="cover"),
    position=("50%", "50%"),
    align="center",
)

# Remote URL
canvas.text(
    content="MARBLE",
    size=140,
    fill=TextFillImage(
        path="https://example.com/textures/marble.jpg",
        fit="cover",
    ),
    position=("50%", "50%"),
    align="center",
)
```

`.text()`か`TextPart`の`fill`へ`TextFillImage`を渡します。実際の使い方は[グラデーションと画像の塗り](text.md#gradient-and-image-fills)を参照してください。
