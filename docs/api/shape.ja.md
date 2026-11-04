---
description: quickthumbの長方形、楕円、カプセル、三角形、星、多角形のレイヤーと、線、影、配置を説明します。
---

# 図形 { #shape }

`.shape()`は位置を指定して、長方形、楕円、カプセル、三角形、星、多角形を追加します。

## シグネチャ { #signature }

```python
canvas.shape(
    shape,
    position,
    width,
    height,
    color,
    fill=None,
    border_radius=0,
    opacity=1.0,
    rotation=0.0,
    align=None,
    points=None,
    star_points=5,
    inner_radius=0.5,
    effects=None,
)
```

## パラメーター { #parameters }

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `shape` | `str` | **必須** | `"rectangle"`、`"ellipse"`、`"pill"`、`"triangle"`、`"star"`、`"polygon"`です。 |
| `position` | `tuple` | **必須** | `(x, y)`位置。整数（ピクセル）か百分率文字列（`"50%"`）です。 |
| `width` | `int` | **必須** | 図形の幅（ピクセル）。正の整数です。 |
| `height` | `int` | **必須** | 図形の高さ（ピクセル）。正の整数です。 |
| `color` | `str` | **必須** | 塗りの色。16進文字列（`"#RRGGBB"`、`"#RRGGBBAA"`）です。 |
| `fill` | `LinearGradient \| RadialGradient \| None` | `None` | 図形内を塗り、図形とともに回転するグラデーションです。グラデーションを描けない対象（PPTX、PDF、SVG、HTML）では`color`が単色の代替になります。 |
| `border_radius` | `int` | `0` | 角の丸み（ピクセル）。`"rectangle"`専用の0以上の整数です。 |
| `opacity` | `float` | `1.0` | `0.0`から`1.0`までの不透明度です。 |
| `rotation` | `float` | `0.0` | 回転角（度）です。 |
| `align` | `str \| Align \| tuple \| None` | `None` | 図形のどの点を`position`に合わせるか。[Align](enums.md#align)を参照してください。 |
| `points` | `list[tuple[float, float]] \| None` | `None` | `"polygon"`の頂点。図形の枠内で`0.0`–`1.0`に正規化し、3点以上が必要です。 |
| `star_points` | `int` | `5` | `"star"`の突起数。最小3です。 |
| `inner_radius` | `float` | `0.5` | `"star"`の外半径に対する内半径の比率。`0.0`より大きく`1.0`より小さい値です。 |
| `effects` | `list \| None` | `[]` | `Stroke`、`Shadow`、`Glow`のリストです。 |

## 例 { #examples }

### ラベル用の長方形 { #label-rectangle }

```python
from quickthumb import Shadow, Stroke

canvas.shape(
    shape="rectangle",
    position=(64, 64),
    width=320,
    height=96,
    color="#CC0000",
    border_radius=14,
    effects=[
        Stroke(width=3, color="#FFFFFF"),
        Shadow(offset_x=0, offset_y=10, color="#000000", blur_radius=18),
    ],
)
```

### 回転したバッジ { #rotated-badge }

```python
canvas.shape(
    shape="rectangle",
    position=(64, 64),
    width=360,
    height=120,
    color="#CC0000",
    border_radius=16,
    opacity=0.95,
    rotation=-4,
    align=("left", "top"),
)
```

### 楕円・円 { #ellipse-circle }

```python
# Circle: set width == height
canvas.shape(
    shape="ellipse",
    position=("50%", "50%"),
    width=200,
    height=200,
    color="#22d3ee",
    align=("center", "middle"),
)
```

### カプセル { #pill }

両端が完全に丸い長方形です。`border_radius`は不要です。

```python
canvas.shape(
    shape="pill",
    position=(64, 60),
    width=220,
    height=56,
    color="#B8FF00",
)
```

### 三角形 { #triangle }

`width` × `height`の枠に内接する上向きの二等辺三角形です。向きを変えるには`rotation`を使います。

```python
canvas.shape(
    shape="triangle",
    position=("50%", "20%"),
    width=140,
    height=120,
    color="#F59E0B",
    align=("center", "middle"),
    rotation=180,   # point down
)
```

### 星 { #star }

`star_points`が突起数、`inner_radius`が鋭さを決めます。値が小さいほど尖ります。

```python
from quickthumb import Glow

canvas.shape(
    shape="star",
    position=("80%", "50%"),
    width=280,
    height=280,
    color="#7C5CFF",
    align=("center", "middle"),
    rotation=12,
    star_points=5,
    inner_radius=0.45,
    effects=[Glow(color="#7C5CFF", radius=40, opacity=0.5)],
)
```

### 多角形 { #polygon }

頂点を図形の枠に対して正規化します。`(0.0, 0.0)`が左上、`(1.0, 1.0)`が右下です。

```python
# A right-pointing arrow
canvas.shape(
    shape="polygon",
    position=(600, 60),
    width=160,
    height=100,
    color="#53BF9D",
    points=[
        (0.0, 0.25), (0.6, 0.25), (0.6, 0.0),
        (1.0, 0.5),
        (0.6, 1.0), (0.6, 0.75), (0.0, 0.75),
    ],
)
```

### 中央の図形にグローを付ける { #centered-shape-with-glow }

```python
from quickthumb import Glow

canvas.shape(
    shape="rectangle",
    position=("50%", "80%"),
    width=480,
    height=72,
    color="#111827",
    border_radius=36,
    align=("center", "middle"),
    effects=[Glow(color="#22d3ee", radius=24, opacity=0.4)],
)
```

## 検証規則 { #validation-rules }

- `shape`、`position`、`width`、`height`、`color`は必須です。
- `position`は2要素のタプルです。百分率文字列は`-?N%`形式です。
- `border_radius`は0以上です。
- `opacity`は`0.0`から`1.0`の範囲です。
- `points`は`"polygon"`で必須で、ほかの図形では拒否されます。各値を`0.0`–`1.0`に正規化した3点以上が必要です。
- `star_points`は3以上、`inner_radius`は`0.0`より大きく`1.0`より小さい値です。
