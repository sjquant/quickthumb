---
description: レイヤーの描画順、配置と整列、エフェクト、リッチテキスト、自動レイアウト、JSON仕様、検証からquickthumbの基本を学びます。
---

# 基本的な考え方 { #core-concepts }

## キャンバスはレイヤーの集まり { #a-canvas-is-a-list-of-layers }

`Canvas`はサイズと順序付きのレイヤー一覧を持ちます。レイヤーのメソッドは1枚追加してキャンバスを返すので、続けて呼び出せます。

```python
from quickthumb import Canvas

canvas = (
    Canvas(1280, 720)
    .background(color="#0F172A")
    .text(content="Hello", size=64, color="#FFFFFF", align="center")
    .outline(width=8, color="#22D3EE")
)
canvas.render("hello.png")
```

レイヤーは追加した順に描かれます。最初が一番奥、最後が一番手前です。絵を描くときのように、背景から始めて細部を重ねていきます。

## レイヤーの種類 { #layer-types }

| メソッド | 追加するもの | リファレンス |
| --- | --- | --- |
| `.background()` | キャンバス全体の色、グラデーション、画像 | [背景](api/background.md) |
| `.text()` | 通常のテキスト、または書式付きの`TextPart` | [テキスト](api/text.md) |
| `.image()` | 配置した画像。背景除去も可能 | [画像](api/image.md) |
| `.shape()` | 長方形、楕円、カプセル、三角形、星、多角形 | [図形](api/shape.md) |
| `.svg()` | アイコンやロゴなどのSVGファイル。`svg`追加機能が必要 | [SVG](api/svg.md) |
| `.video()` | アニメーション出力用の動画クリップ | [動画](api/video.md) |
| `.chart()`, `.qr_code()` | 棒・折れ線グラフ、QRコード | [データの可視化](api/data-visualizations.md) |
| `.counter()` | ある値から別の値へ数える数字 | [Canvas](api/canvas.md#animated-counters) |
| `.group()` | 子を自動配置する行や列 | [グループ](api/group.md) |
| `.outline()` | キャンバスの縁の枠線 | [枠線](api/outline.md) |
| `.custom(fn)` | Pillow画像へ描く独自の関数 | [Canvas](api/canvas.md) |

## 位置と整列 { #position-and-alignment }

`position`は`(x, y)`の組です。それぞれピクセルかキャンバスに対する百分率で指定でき、混在もできます。

```python
canvas.shape(shape="rectangle", position=(64, 64), width=200, height=80, color="#CC0000")
canvas.text(content="Hello", size=72, color="#FFFFFF", position=("8%", 360))
```

`align`は、レイヤーのどの点を指定位置に合わせるかを決めます。既定は左上です。`align=("center", "middle")`なら中心を合わせます。1280×720のキャンバスで`align=("right", "bottom")`と`position=(1280, 720)`を指定すると、レイヤーのサイズによらず右下に固定できます。

`align`には、同じ意味を持ついくつかの書き方があります。

```python
align=("center", "middle")      # (horizontal, vertical)
align="center"                  # same as ("center", "middle")
align="bottom-right"
align=Align.BOTTOM_RIGHT
```

横方向は`left`、`center`、`right`、縦方向は`top`、`middle`、`bottom`です。テキストに`position`がなく`align`だけがある場合は、キャンバス内の対応する位置に配置します。つまり`align="center"`なら中央です。

## エフェクト { #effects }

エフェクトはレイヤーの描き方を変えます。リストで渡してください。

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

使えるエフェクトはレイヤーの種類によって異なります。

| レイヤー | エフェクト |
| --- | --- |
| 背景 | `Filter`、`Grain` |
| テキスト | `Stroke`、`Shadow`、`Glow`、`Background`（文字の背後の枠） |
| 図形 | `Stroke`、`Shadow`、`Glow`、`InnerShadow`、`BackdropBlur` |
| 画像、SVG、動画 | `Stroke`、`Shadow`、`Glow`、`Filter`、`Grain`、`Duotone`、`InnerShadow`、`BackdropBlur` |

レイヤーが対応していないエフェクトを渡すと`ValidationError`になります。パラメーターは[エフェクトリファレンス](api/effects.md)を参照してください。

## リッチテキスト { #rich-text }

すべて同じ書式なら通常の文字列で十分です。一部の書式を変えるには`TextPart`のリストを渡します。

```python
from quickthumb import TextPart

canvas.text(
    content=[
        TextPart(text="5 ", color="#FBBF24"),
        TextPart(text="WAYS TO WIN", color="#FFFFFF"),
    ],
    size=80,
    weight=900,
    position=("8%", "55%"),
    align=("left", "middle"),
)
```

レイヤーの設定（ここでは`size`と`weight`）は、各パートで指定し直さない限り全体へ適用されます。パートごとに`color`、`size`、`font`、`weight`、`bold`、`italic`、`letter_spacing`、`line_height`、`effects`を上書きできます。

## グラデーション、ブレンド、画像のフィット { #gradients-blend-modes-and-fit }

背景には色や画像に加えて`gradient`も指定できます。

```python
from quickthumb import LinearGradient, RadialGradient

canvas.background(gradient=LinearGradient(angle=135, stops=[("#FF5733", 0.0), ("#3333FF", 1.0)]))
canvas.background(gradient=RadialGradient(center=(0.5, 0.5), stops=[("#FF5733", 0.0), ("#3333FF", 1.0)]))
```

停止点の色にはアルファ（`"#00000080"`）を含められます。これにより、文字の背後にある写真の一部を暗くできます。

背景や画像の`blend_mode`は、下の内容との合成方法を決めます。`normal`、`multiply`、`screen`、`overlay`、`darken`、`lighten`が使えます。

`fit`は画像を枠に収める方法です。`cover`は枠を埋めて余分な部分を切り取り、背景ではこれが既定です。`contain`は画像全体を枠内に収め、`fill`は引き伸ばします。

## 自動レイアウト { #auto-layout }

手で座標を指定したテキストは、文言が長くなるとレイアウトが崩れがちです。`group`は子のサイズを測り、行や列に並べます。グループを一度配置すれば、子の位置は自動で決まります。

```python
canvas.group(
    children=[
        {"type": "shape", "shape": "pill", "width": 120, "height": 36, "color": "#E94560"},
        {"type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900},
        {"type": "text", "content": "Longer copy pushes the rest down", "size": 40, "color": "#A2A8D3"},
    ],
    direction="column",
    gap=24,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

子には`position`を指定しません。グループを入れ子にもできます。[グループ](api/group.md)を参照してください。

## JSON仕様 { #json-specs }

ここまでの内容はPythonだけでなくJSONでも書け、キャンバスと相互に変換できます。

```python
spec = canvas.to_json()
same_canvas = Canvas.from_json(spec)
```

例外は`.custom(fn)`です。Python関数はJSONに保存できません。

JSONの`theme`ブロックで色やサイズを一度定義し、`$theme.<path>`で参照することもできます。

```json
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "theme": { "colors": { "primary": "#B8FF00" }, "sizes": { "title": 96 } },
  "layers": [
    { "type": "text", "content": "Hello", "size": "$theme.sizes.title", "color": "$theme.colors.primary" }
  ]
}
```

[JSON SchemaとAIワークフロー](json-schema.md)を参照してください。

## パスのモーション { #path-motion }

`Canvas.path()`はSVGパスデータ、グラデーションを含む塗り、破線に対応します。固定された`width`/`height`のビューポートがローカルの描画を切り取り、回転や拡大縮小中も正規化された`anchor`の基準となります。

```python
from quickthumb import AnimationSpec, Canvas, KeyframeSpec, ScaleTrack, TimingSpec

canvas = Canvas(320, 240).path(
    "M2 20C2 2 38 2 38 20C38 38 2 38 2 20Z", (100, 80), 40, 40,
    "#38B6A080", anchor=(0.5, 0.5),
    animation=AnimationSpec.timeline(
        ScaleTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=4)]),
        timing=TimingSpec(duration=1), easing="linear",
    ),
)
frame = canvas.render_frame(0.75)
```

パスのアニメーションにはトラックタイムラインを使います。対応範囲は出力形式によって異なります。パスではプリセット、stagger、Groupの子、変換の親子関係をサポートしていません。詳細は[Path API](api/path.md)を参照してください。

## エラーと検査 { #errors-and-checks }

描画前のレイヤー追加時に引数を検証します。

```python
from quickthumb import ValidationError

try:
    canvas.text(content="Hello", size=64, color="#FFF")
except ValidationError as error:
    print(error)  # /color: invalid hex color: #FFF
```

ダウンロードの失敗など、描画中に分かる問題は`RenderingError`、存在しないローカルファイルは`MissingAssetError`になります。どのエラーも構造化された`details`を持ちます。[構造化エラー](errors.md)を参照してください。

有効なキャンバスでも見た目に問題がある場合はあります。`canvas.diagnose()`はファイルを出力せず、小さすぎる文字、はみ出し、低いコントラスト、他のレイヤーに隠れたレイヤーなどを調べます。[診断とCLI](diagnostics.md)を参照してください。
