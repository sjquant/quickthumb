---
description: quickthumbの動画レイヤーで、トリミング、フィット、速度、字幕、色調整、マスク、アニメーションを使います。
---

# 動画 { #video }

`.video()`はキャンバスへ動画クリップを加えます。ほかの視覚レイヤーと同様、切り取り、拡大縮小、ループ、位置変更、角丸、色調整、マスク、タイムライン上のアニメーションを適用できます。

動画レイヤーはアニメーション出力（GIF、MP4、WebM、MOV）と`render_frame(...)`でネイティブに描画します。静的ドキュメント（PPTX、PDF、SVG、HTML）では静止フレームです。

## シグネチャ { #signature }

```python
canvas.video(
    source,
    position,
    width,
    height,
    fit="contain",
    trim_start=0.0,
    trim_end=None,
    start=0.0,
    duration=None,
    speed=1.0,
    volume=1.0,
    captions=None,
    border_radius=0,
    opacity=1.0,
    rotation=0.0,
    align=None,
    blend_mode=None,
    effects=None,
    clip=None,
    mask=None,
    animation=None,
)
```

## パラメーター { #parameters }

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `source` | `str` | **必須** | 動画ファイルのパスです。 |
| `position` | `tuple` | **必須** | ピクセルか百分率文字列（`"50%"`）の`(x, y)`位置です。 |
| `width` | `int` | **必須** | レイヤーの幅（ピクセル）です。 |
| `height` | `int` | **必須** | レイヤーの高さ（ピクセル）です。 |
| `fit` | `str \| FitMode` | `"contain"` | 枠への合わせ方。`"contain"`、`"cover"`、`"fill"`です。[FitMode](enums.md#fitmode)を参照してください。 |
| `trim_start` | `float` | `0.0` | ソース内の再生開始時刻（秒）です。 |
| `trim_end` | `float \| None` | `None` | ソース内の再生終了時刻。既定はクリップ末尾です。 |
| `start` | `float` | `0.0` | タイムライン上で再生を始める時刻（秒）です。 |
| `duration` | `float \| None` | `None` | シーン内に表示する長さです。 |
| `speed` | `float` | `1.0` | 速度倍率。`0.5`は半速、`2.0`は倍速です。 |
| `volume` | `float` | `1.0` | MP4/WebM/MOVのクリップ音量。GIFは常に無音です。 |
| `captions` | `list \| None` | `[]` | フレームへ焼き込む時刻付き字幕です。 |
| `border_radius` | `int` | `0` | 角丸の半径（ピクセル）です。 |
| `opacity` | `float` | `1.0` | `0.0`から`1.0`までの不透明度です。 |
| `rotation` | `float` | `0.0` | 回転角（度）です。 |
| `align` | `str \| Align \| tuple \| None` | `None` | `position`の基準点。[Align](enums.md#align)を参照してください。 |
| `blend_mode` | `str \| BlendMode \| None` | `None` | 合成のブレンドモードです。 |
| `effects` | `list \| None` | `[]` | `Filter`、`Duotone`、`Grain`、`Glow`、`Shadow`、`Stroke`、`InnerShadow`です。 |
| `clip` | `LayerClip \| None` | `None` | 幾何的な境界で切り取ります。 |
| `mask` | `LayerMask \| None` | `None` | 図形かパスでマスクします。 |
| `animation` | `Animation \| AnimationSpec \| list \| None` | `None` | 入場・退場プリセットか独自のキーフレームモーションです。 |

## 例 { #examples }

### トリミングと色調整 { #trimming-and-color-grading }

6秒の範囲を切り取り、白黒にして角を丸めます。

```python
from quickthumb import Canvas
from quickthumb.models import Filter

canvas = Canvas(1280, 720).video(
    "clip.mp4",
    position=(64, 64),
    width=1152,
    height=592,
    fit="cover",
    trim_start=1.0,
    trim_end=7.0,
    duration=6.0,
    border_radius=16,
    effects=[Filter(saturation=0.0, contrast=1.15)],
)
```

### 位置を動かす { #animating-position }

再生しながらシーンを横切るように移動します。

```python
from quickthumb import AnimationSpec, Canvas, KeyframeSpec, PositionTrack, TimingSpec

canvas = Canvas(1280, 720).video(
    "clip.mp4",
    position=(0, 200),
    width=480,
    height=270,
    fit="cover",
    duration=4.0,
    animation=AnimationSpec.timeline(
        PositionTrack(
            keyframes=[
                KeyframeSpec(time=0.0, value=(0, 0)),
                KeyframeSpec(time=4.0, value=(800, 0)),
            ]
        ),
        timing=TimingSpec(start=0.0, duration=4.0),
        easing="ease_in_out",
    ),
)
```

### スプリングイージング { #spring-easing }

`SpringEasing`で物理的な跳ね返りを加えます。

```python
from quickthumb import AnimationSpec, KeyframeSpec, PositionTrack, SpringEasing

motion = AnimationSpec.timeline(
    PositionTrack(keyframes=[
        KeyframeSpec(time=0, value=(0, 0)),
        KeyframeSpec(time=1, value=(180, 0)),
    ]),
    easing=SpringEasing(stiffness=100, damping=10, mass=1),
)
```

### Wiggleトラック修飾子 { #wiggle-track-modifiers }

任意のトラックへ`Wiggle(frequency=2, amplitude=12, seed=42)`を付けると、自然で再現可能な揺れを作れます。

```python
from quickthumb import AnimationSpec, KeyframeSpec, PositionTrack, TimingSpec, Wiggle

motion = AnimationSpec.timeline(
    PositionTrack(
        keyframes=[KeyframeSpec(time=0, value=(0, 0))],
        wiggle=Wiggle(frequency=2, amplitude=12, seed=42),
    ),
    timing=TimingSpec(duration=2),
)
```

## 透過動画を重ねる { #transparent-video-overlays }

背景が透明な動画を出力できます。ローワーサード、動くステッカー、ゲームのオーバーレイに適しています。

- **WebM（アルファ付きVP9）**：`VideoOptions(transparent=True)`
- **ProRes 4444 MOV**：`canvas.export("overlay.mov", animation=VideoOptions(transparent=True))`

```python
from quickthumb import Canvas, VideoOptions

canvas = Canvas(1280, 720).shape("pill", (100, 600), 400, 80, "#42CEB7")
canvas.export("lower_third.webm", animation=VideoOptions(transparent=True))
```

詳細は[透過動画](../reference/export-transparency.md)を参照してください。

## 補足 { #notes }

- **ソースの長さ**：シーンが元クリップより長い場合は、`speed`を`1.0`未満にすると滑らかに再生を引き伸ばせます。
- **字幕**：読みやすさのため、構成内の全レイヤーより上に描きます。
- **診断**：`canvas.diagnose()`で字幕の位置、余白、読む速さを自動検査します。

---

# 高度なモーションと合成 { #advanced-motion-compositing }

以下はテキスト、図形、画像、パス、動画など、視覚レイヤーで共通する高度な機能です。

## 曲線のモーションパス { #curved-motion-paths }

接線ハンドル付きの`PositionKeyframeSpec`で、直線の代わりに滑らかなBézier曲線を使えます。

```python
from quickthumb import AnimationSpec, Canvas, PositionKeyframeSpec, PositionTrack, TimingSpec

canvas = Canvas(640, 360).shape(
    "pill", (60, 230), 48, 24, "#42CEB7",
    animation=AnimationSpec.timeline(
        PositionTrack(
            keyframes=[
                PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=(120, -200)),
                PositionKeyframeSpec(time=4, value=(480, 0), in_tangent=(-120, -200)),
            ],
            auto_orient=True,  # Rotate layer to follow the path tangent
        ),
        timing=TimingSpec(start=0, duration=4),
        easing="linear",
    ),
)
```

### ハンドルと速度 { #handles-and-speed }

- `out_tangent=(dx, dy)`はキーから出る曲線の形を決めます。
- `in_tangent=(dx, dy)`はキーへ入る曲線の形を決めます。
- `easing="linear"`なら、曲線に沿って一定速度で移動します。

### 接線に向きを合わせる { #following-the-tangent }

`auto_orient=True`で、進む方向に合わせて自動回転します。右向きが`0°`、時計回りが正です。

### 出力対応 { #export-support }

曲線モーションはラスターアニメーション（GIF、MP4、WebM）とHTMLに対応します。PPTX、PDFは最初のフレームを表示します。

## 変換の基準点と軸別スケール { #transform-anchors-and-independent-scale }

既定ではレイヤーの中心（`anchor=(0.5, 0.5)`）で拡大縮小・回転します。`anchor=(x, y)`で変更できます。

- `(0, 0)`：左上
- `(0.5, 0.5)`：中央（既定）
- `(1, 1)`：右下

```python
from quickthumb import (
    AnimationSpec, Canvas, KeyframeSpec, RotationTrack, ScaleXTrack, ScaleYTrack, TimingSpec,
)

canvas = Canvas(320, 240).shape(
    "rectangle", (100, 100), 80, 40, "#42CEB7",
    anchor=(0, 1),  # Pivot around bottom-left corner
    animation=AnimationSpec.timeline(
        ScaleXTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=2, value=1.5)]),
        ScaleYTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=2, value=0.6)]),
        RotationTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=2, value=30)]),
        timing=TimingSpec(duration=2),
    ),
)
```

### 出力対応 { #export-support_1 }

独自の基準点と軸別スケール（`ScaleXTrack`、`ScaleYTrack`）は、ラスターフレーム、GIF、MP4、WebM、モダンなHTMLプレゼンテーションで動作します。

## テキストと図形の色を動かす { #animated-text-and-shape-colors }

`ColorTrack`で塗りや文字色を時間とともに変えます。

```python
from quickthumb import AnimationSpec, Canvas, ColorTrack, KeyframeSpec, TimingSpec

canvas = Canvas(640, 360).text(
    "Color in motion", position=(40, 40), size=48, color="#FF0000",
    animation=AnimationSpec.timeline(
        ColorTrack(keyframes=[
            KeyframeSpec(time=0, value="#FF0000"),
            KeyframeSpec(time=2, value="#0055FF"),
        ]),
        timing=TimingSpec(start=0, duration=2),
    ),
)
```

知覚的に均一なOklab色空間で滑らかに補間し、途中の色が濁るのを避けます。

## タイムラインのライブプレビュー { #live-timeline-preview }

動画をエンコードせずに、ブラウザーでアニメーションを対話的に探れます。

```bash
quickthumb serve scene.py --timeline
```

`http://localhost:3030/timeline`で、フレーム移動と保存時の即時再読み込みに対応するスクラバーが開きます。

## 親子関係とNullコントローラー { #parent-links-and-null-controllers }

`parent="parent-layer-id"`でレイヤーを階層化します。親の移動、回転、拡大縮小に子が追従します。

```python
from quickthumb import Canvas

scene = (
    Canvas(320, 240)
    .null(position=(100, 50), id="controller")  # Invisible point controller
    .shape("rectangle", (10, 20), 40, 20, "#42CEB7", parent="controller")
)
```

### 幾何の規則 { #geometry-contract }

- 子の位置は親の座標空間を基準にします。
- 親のモーション変換（位置、回転、スケール）を継承します。
- 親のスタイル（不透明度、エフェクト、マスク）は**継承せず**、子のスタイルは独立しています。

### 現在の対応と制限 { #current-adapters-and-boundaries }

親子関係はラスター、GIF、MP4、WebMで完全に対応します。PPTX、PDF、SVGでは、親を持つグループを静止した描画断片として出力します。

## テキスト範囲の選択 { #text-range-selectors }

`RangeSelector`で単語、行、文字ごとに動かせます。

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

### 文字ごとの扱い { #character-ownership }

`target="characters"`ではグリフごとに独立したアニメーション段階を持ちます。空白や句読点も正確なフォント測定値で維持します。

## トラックマット { #track-mattes }

`mask=TrackMatte(layer="source-id")`で別のレイヤーをアルファ・輝度マスクにします。

```python
from quickthumb import Canvas, TrackMatte

canvas = (
    Canvas(640, 360)
    .shape("ellipse", (120, 80), 200, 200, color="#FFFFFF", id="hole")
    .image("photo.jpg", position=(0, 0), width=640, height=360, mask=TrackMatte(layer="hole"))
)
```

- `mode="alpha"`：ソースの透明度でマスクします。
- `mode="luma"`：ソースの明るさでマスクします。
- `invert=True`：切り抜く領域を反転します。

### 図形マスクを動かす { #animated-shape-mask-geometry }

`MaskPositionTrack`、`MaskSizeTrack`、`MaskFeatherTrack`で位置、サイズ、フェザーを動的に変えられます。

### HTMLのネイティブ図形マスク { #native-html-shape-masks }

長方形、カプセル、楕円のマスクはHTMLスライドショーでCSSクリッピングになります。

### 所有レイヤーに付けるパスマスク { #owner-attached-path-masks }

`LayerMask(shape="path", d="M0 0 H40 V40 H0 Z")`で、任意のレイヤーへ独自のSVGパスマスクを直接付けられます。

### パスの形をしたマット { #path-shaped-mattes }

`Canvas.path()`レイヤーを動的なトラックマットとして参照し、独自の動く切り抜きを作れます。
