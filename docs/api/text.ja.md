---
description: quickthumbのテキストレイヤーで、部分書式、フォント、整列、折り返し、輪郭線、影、サイズを指定します。
---

# テキスト { #text }

`.text()`はテキストレイヤーを追加します。内容には通常の文字列か、区間ごとに書式を指定する`TextPart`のリストを使えます。

## シグネチャ { #signature }

```python
canvas.text(
    content,
    font=None,
    font_source="auto",
    font_variations=None,
    emoji_style="monochrome",
    size=None,
    color=None,
    fill=None,
    position=None,
    align=None,
    bold=False,
    italic=False,
    weight=None,
    max_width=None,
    max_height=None,
    min_size=1,
    balance_lines=False,
    effects=None,
    line_height=None,
    letter_spacing=None,
    auto_scale=False,
    rotation=0.0,
    opacity=1.0,
)
```

## パラメーター { #parameters }

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `content` | `str \| list[TextPart]` | **必須** | 通常の文字列か、リッチテキスト用の`TextPart`リストです。 |
| `font` | `str \| None` | `None` | ファミリー名、ローカルパス、リモートのWebフォントURLです。 |
| `font_source` | `"auto" \| "system" \| "google"` | `"auto"` | 検索元。`"google"`は指定したGoogle Fontを読み込み、キャッシュします。 |
| `font_variations` | `dict[str, float] \| None` | `None` | `{"wght": 650}`などOpenTypeの可変軸の値です。 |
| `emoji_style` | `"monochrome" \| "color"` | `"monochrome"` | 絵文字の表示方式です。 |
| `size` | `int \| None` | `None` | 文字サイズ（ピクセル）。正の整数です。 |
| `color` | `str \| None` | `None` | 既定の文字色。16進文字列（`"#RRGGBB"`、`"#RRGGBBAA"`）です。 |
| `fill` | `LinearGradient \| RadialGradient \| TextFillImage \| None` | `None` | グリフのグラデーション・画像による塗り。指定時は`color`より見た目で優先されます。[グラデーションと画像の塗り](#gradient-and-image-fills)を参照してください。 |
| `position` | `tuple \| None` | `None` | `(x, y)`位置。整数（ピクセル）か百分率文字列（`"50%"`）です。 |
| `align` | `str \| Align \| tuple \| None` | `None` | テキストブロックの整列。[Alignの値](#align-values)を参照してください。 |
| `bold` | `bool` | `False` | 太字の指定。`weight`とは同時に使えません。 |
| `italic` | `bool` | `False` | 斜体の指定です。 |
| `weight` | `int \| str \| None` | `None` | CSS方式の太さ（`700`、`900`、`"bold"`など）。`bold`とは同時に使えません。 |
| `max_width` | `int \| str \| None` | `None` | 折り返す幅。ピクセルか百分率文字列（`"60%"`など）です。 |
| `max_height` | `int \| str \| None` | `None` | ブロックの最大高さ。ピクセルか百分率文字列です。 |
| `min_size` | `int` | `1` | 自動縮小時に許容する最小文字サイズです。 |
| `balance_lines` | `bool` | `False` | `max_width`がある場合に行の長さを均等にします。 |
| `effects` | `list \| None` | `[]` | `Stroke`、`Shadow`、`Glow`、`Background`のリストです。 |
| `line_height` | `float \| None` | `None` | 行の高さの倍率。正の実数です。 |
| `letter_spacing` | `int \| None` | `None` | 横方向の字間調整（ピクセル）です。 |
| `auto_scale` | `bool` | `False` | `max_width`や`max_height`に収まるまで文字を縮小します。 |
| `rotation` | `float` | `0.0` | 回転角（度）です。 |
| `opacity` | `float` | `1.0` | `0.0`から`1.0`までの不透明度です。 |

## Alignの値 {#align-values}

`align`には次の形式を使えます。

```python
align="center"              # shorthand
align="top-left"            # compound string
align=("left", "middle")    # (horizontal, vertical) tuple
align=Align.BOTTOM_RIGHT    # enum
```

| 文字列 | 列挙型 | 位置 |
| --- | --- | --- |
| `"center"` | `Align.CENTER` | 縦横とも中央 |
| `"left"` | `Align.LEFT` | 左揃え、縦は中央 |
| `"right"` | `Align.RIGHT` | 右揃え、縦は中央 |
| `"top-left"` | `Align.TOP_LEFT` | 左上 |
| `"top-center"` | `Align.TOP_CENTER` | 上辺の中央 |
| `"top-right"` | `Align.TOP_RIGHT` | 右上 |
| `"bottom-left"` | `Align.BOTTOM_LEFT` | 左下 |
| `"bottom-center"` | `Align.BOTTOM_CENTER` | 下辺の中央 |
| `"bottom-right"` | `Align.BOTTOM_RIGHT` | 右下 |

タプルの横方向は`left`、`center`、`right`、縦方向は`top`、`middle`、`bottom`です。

## 例 { #examples }

### 通常のテキスト { #plain-text }

```python
canvas.text(
    content="Hello World",
    size=64,
    color="#FFFFFF",
    align="center",
)
```

### `TextPart`で書式を分ける { #rich-text-with-textpart }

```python
from quickthumb import Stroke, TextPart

canvas.text(
    content=[
        TextPart(text="5 ", color="#FBBF24", weight=900),
        TextPart(text="WARNING SIGNS", color="#FFFFFF", weight=900),
    ],
    size=72,
    position=("8%", "55%"),
    align=("left", "middle"),
)
```

### エフェクトを加える { #with-effects }

```python
from quickthumb import Background, Glow, Shadow, Stroke

canvas.text(
    content="BREAKING",
    size=96,
    color="#FFFFFF",
    position=("8%", "50%"),
    align=("left", "middle"),
    weight=900,
    max_width="65%",
    effects=[
        Stroke(width=4, color="#000000"),
        Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=8),
        Glow(color="#B8FF00", radius=16, opacity=0.25),
        Background(color="#111827CC", padding=(16, 24), border_radius=14),
    ],
)
```

### 枠に収まるよう縮小する { #auto-scale-to-fit }

```python
canvas.text(
    content="This is a very long title that should fit",
    size=80,
    color="#FFFFFF",
    max_width="70%",
    auto_scale=True,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

### Webフォントを使う { #using-a-webfont }

```python
canvas.text(
    content="Custom Font",
    font="https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiA.woff2",
    size=72,
    color="#FFFFFF",
    align="center",
)
```

!!! note "WebフォントのURL"
    `font`がURLなら特定のファイルを指すため、`bold`、`italic`、`weight`は無視します。スタイルごとに別のURLを使うか、ファミリー名と`font_source="google"`を指定して`weight`と`italic`でファイルを選んでください。

### グラデーションと画像の塗り {#gradient-and-image-fills}

単色の代わりにグラデーションや画像で文字を塗ります。`fill`へ`LinearGradient`、`RadialGradient`、`TextFillImage`を渡します。

```python
from quickthumb import Canvas, LinearGradient, RadialGradient, TextFillImage, TextPart

# Linear gradient headline
canvas.text(
    content="GRADIENT",
    size=120,
    fill=LinearGradient(angle=90, stops=[("#FF6B6B", 0.0), ("#4ECDC4", 1.0)]),
    position=("50%", "50%"),
    align="center",
)

# Image-filled text
canvas.text(
    content="TEXTURE",
    size=140,
    fill=TextFillImage(path="fire_texture.jpg", fit="cover"),
    position=("50%", "50%"),
    align="center",
)

# Per-segment fills using TextPart
canvas.text(
    content=[
        TextPart(
            text="HOT ",
            fill=LinearGradient(angle=45, stops=[("#FF4500", 0.0), ("#FFD700", 1.0)]),
            weight=900,
        ),
        TextPart(
            text="COLD",
            fill=LinearGradient(angle=45, stops=[("#00BFFF", 0.0), ("#8A2BE2", 1.0)]),
            weight=900,
        ),
    ],
    size=110,
    position=("50%", "50%"),
    align="center",
)
```

`TextPart`の`fill`は、その区間だけレイヤーの`fill`を上書きします。`fill`と`color`は独立しており、`fill`を指定すると見た目では優先されます。画像の塗りのオプションは[TextFillImage](enums.md#textfillimage)を参照してください。

## TextPart { #textpart }

`TextPart`はテキストレイヤー内の区間ごとに書式を設定します。

```python
from quickthumb import Stroke, TextPart

TextPart(
    text="HOT",
    color="#FF3B30",
    fill=None,
    size=56,
    font="Impact",
    font_source=None,
    font_variations=None,
    emoji_style=None,
    weight=900,
    italic=False,
    line_height=None,
    letter_spacing=0,
    effects=[Stroke(width=3, color="#000000")],
)
```

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `text` | `str` | **必須** | 区間の文字列。空にはできません。 |
| `color` | `str \| None` | `None` | この区間の16進色を上書きします。 |
| `fill` | `LinearGradient \| RadialGradient \| TextFillImage \| None` | `None` | この区間のグラデーション・画像の塗り。その区間だけレイヤーの`fill`を上書きします。 |
| `size` | `int \| None` | `None` | この区間の文字サイズです。 |
| `font` | `str \| None` | `None` | この区間のフォントです。 |
| `font_source` | `"auto" \| "system" \| "google" \| None` | `None` | `None`ならレイヤーを継承し、明示値なら上書きします。 |
| `font_variations` | `dict[str, float] \| None` | `None` | `None`なら継承し、`{}`なら継承した可変軸を明示的に消します。 |
| `emoji_style` | `"monochrome" \| "color" \| None` | `None` | `None`なら継承し、`"monochrome"`なら明示的に上書きします。 |
| `bold` | `bool \| None` | `None` | 太字の上書き。`weight`とは同時に使えません。 |
| `italic` | `bool \| None` | `None` | 斜体の上書きです。 |
| `weight` | `int \| str \| None` | `None` | 太さの上書き。`bold`とは同時に使えません。 |
| `line_height` | `float \| None` | `None` | 行の高さの倍率です。 |
| `letter_spacing` | `int \| None` | `None` | 字間の上書きです。 |
| `effects` | `list[TextEffect]` | `[]` | 区間専用の`Stroke`、`Shadow`、`Glow`、`Background`です。 |

## テキストのアニメーション { #text-animations }

`RangeSelector`で単語単位や文字単位に動かせます。

```python
from quickthumb import AnimationSpec, Canvas, KeyframeSpec, PositionTrack, RangeSelector, TimingSpec

canvas = Canvas(800, 400).text(
    "Words appear one by one",
    size=48,
    color="#FFFFFF",
    position=(50, 150),
    animation=AnimationSpec.timeline(
        PositionTrack(keyframes=[
            KeyframeSpec(time=0, value=(0, 20)),
            KeyframeSpec(time=0.4, value=(0, 0)),
        ]),
        selector=RangeSelector(
            target="words",  # "words", "lines", or "characters"
            offset=[KeyframeSpec(time=0, value=-100), KeyframeSpec(time=2, value=100)],
        ),
        timing=TimingSpec(duration=2),
    ),
)
```

選択の形、タイミング、色の変化は[テキスト範囲の選択](video.md#text-range-selectors)を参照してください。

## 検証規則 { #validation-rules }

- `content`は必須で、空のリストにはできません。
- `TextPart.text`は空文字列にできません。
- `TextLayer`と`TextPart`で`weight`と`bold=True`は同時に使えません。
- `auto_scale=True`には`max_width`か`max_height`が必要です。
- `max_width`は正の整数か`"60%"`のような正の百分率文字列です。
- `position`の百分率文字列は`-?N%`形式です。負の百分率も有効です。
- `fill`と`color`は独立し、両方あれば`fill`が見た目で優先されます。
- `TextFillImage.path`はローカルパスとリモートURLに対応します。ローカルファイルがなければ描画時に`FileNotFoundError`になります。
