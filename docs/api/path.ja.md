---
description: ローカルviewBox、グラデーション、破線、パスアニメーションを使って、塗りや線のあるSVGパスを描きます。
---

# パス { #path }

`Canvas.path()`は、標準SVGパスデータ（`d`）から塗りや線のあるベクターパスを描きます。外部SVGファイルや追加の依存関係は不要です。

```python
from quickthumb import Canvas

canvas = Canvas(160, 120).path(
    "M 0 0 H 100 V 100 H 0 Z M 25 25 H 75 V 75 H 25 Z",
    position=(20, 10),
    width=120,
    height=100,
    view_box=(0, 0, 100, 100),
    color="#42CEB7",
)
canvas.export("path.png")
```

## パラメーター { #parameters }

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `d` | `str` | **必須** | SVGパス命令（`M`、`L`、`H`、`V`、`C`、`S`、`Q`、`T`、`A`、`Z`）です。 |
| `position` | `tuple` | **必須** | ピクセルか百分率文字列（`"50%"`）による`(x, y)`位置です。 |
| `width` | `int` | **必須** | 枠の幅（ピクセル）です。 |
| `height` | `int` | **必須** | 枠の高さ（ピクセル）です。 |
| `view_box` | `tuple \| None` | `None` | ローカル座標の範囲`(x, y, width, height)`。既定は`(0, 0, width, height)`です。 |
| `color` | `str \| None` | `"#000000"` | 単色の塗り。線だけなら`None`にします。 |
| `fill` | `LinearGradient \| RadialGradient \| None` | `None` | グラデーションの塗り。指定時は`color`を置き換えます。 |
| `stroke` | `str \| None` | `None` | 線の色（16進文字列）です。 |
| `stroke_width` | `int \| float` | `1` | ローカル単位での線の太さです。 |
| `line_cap` | `str` | `"butt"` | 端の形。`"butt"`、`"round"`、`"square"`です。 |
| `line_join` | `str` | `"miter"` | 角のつなぎ方。`"miter"`、`"bevel"`、`"round"`です。 |
| `miter_limit` | `float` | `4` | ベベルに切り替えるまでの最大マイター比率です。 |
| `dash_array` | `tuple \| None` | `None` | 破線の長さの組`(dash, gap, ...)`です。 |
| `dash_offset` | `float` | `0` | 破線パターンの開始位相です。 |
| `rotation` | `float` | `0.0` | 回転角（度）です。 |
| `opacity` | `float` | `1.0` | `0.0`から`1.0`の不透明度です。 |
| `anchor` | `tuple` | `(0.5, 0.5)` | 回転と拡大縮小の正規化された中心です。 |
| `animation` | `AnimationSpec \| None` | `None` | 移動、トリム、破線位相、モーフィングのタイムラインです。 |

## 例 { #examples }

### 破線で曲線を描く { #stroked-curves-with-dashed-outline }

```python
canvas.path(
    "M10 50 C30 0 70 100 90 50",
    position=(20, 10),
    width=120,
    height=100,
    color=None,
    stroke="#42CEB7",
    stroke_width=6,
    line_cap="round",
    view_box=(0, 0, 100, 100),
    dash_array=(12, 6),
    dash_offset=3,
)
```

### 穴のあるグラデーション { #gradient-fill-with-cutouts }

パスは**偶奇規則**で塗ります。内側の輪郭が重なる部分は、自然に切り抜きや穴になります。

```python
from quickthumb import LinearGradient

canvas.path(
    "M10 10 H90 V90 H10 Z M30 30 H70 V70 H30 Z",
    position=(20, 10),
    width=120,
    height=100,
    color=None,
    fill=LinearGradient(angle=45, stops=[("#42CEB7", 0), ("#315D8E", 1)]),
    view_box=(0, 0, 100, 100),
)
```

## パスのアニメーション { #path-animations }

### 破線の位相を動かす { #animated-dash-phase-marching-ants }

`DashOffsetTrack`を動かすと、破線が進む効果を作れます。

```python
from quickthumb import AnimationSpec, DashOffsetTrack, KeyframeSpec, TimingSpec

phase_animation = AnimationSpec.timeline(
    DashOffsetTrack(keyframes=[
        KeyframeSpec(time=0, value=0),
        KeyframeSpec(time=1, value=20),
    ]),
    timing=TimingSpec(duration=1),
    easing="linear",
)

canvas.path(
    "M0 10 H100",
    position=(10, 10),
    width=200,
    height=20,
    color=None,
    stroke="#42CEB7",
    dash_array=(6, 4),
    animation=phase_animation,
)
```

### 線を徐々に描く { #stroke-trim-self-drawing-line }

`TrimEndTrack`で線や輪郭を始点から終点へ徐々に描けます。

```python
from quickthumb import AnimationSpec, KeyframeSpec, TimingSpec, TrimEndTrack

draw_outline = AnimationSpec.timeline(
    TrimEndTrack(keyframes=[
        KeyframeSpec(time=0, value=0.0),
        KeyframeSpec(time=1.5, value=1.0),
    ]),
    timing=TimingSpec(duration=1.5),
    easing="ease_in_out",
)

canvas.path(
    "M0 20 Q50 -10 100 20",
    position=(20, 20),
    width=200,
    height=60,
    view_box=(0, -10, 100, 30),
    color=None,
    stroke="#42CEB7",
    stroke_width=4,
    animation=draw_outline,
)
```

- `TrimStartTrack`と`TrimEndTrack`は、全パス長に対する正規化された端点（`0.0`–`1.0`）です。
- `TrimOffsetTrack`は、トリムされた区間をパスに沿って移動します。

### パスのモーフィング { #path-morphing }

`PathMorphTrack`で、あるベクター図形から別の図形へ滑らかに変形できます。

```python
from quickthumb import AnimationSpec, KeyframeSpec, PathMorphTrack, TimingSpec

morph = AnimationSpec.timeline(
    PathMorphTrack(keyframes=[
        KeyframeSpec(time=0, value="M10 10 H50 V50 H10 Z"),
        KeyframeSpec(time=1, value="M20 20 H60 V60 H20 Z"),
    ]),
    timing=TimingSpec(duration=1),
    easing="ease_in_out",
)

canvas.path(
    "M10 10 H50 V50 H10 Z",
    position=(10, 10),
    width=100,
    height=100,
    color="#42CEB7",
    animation=morph,
)
```

各キーには、退化していない輪郭が1–16個必要です。輪郭の数、順序、開閉、巻き方向、入れ子構造を一致させてください。変形の途中も含め、輪郭同士が交差したり接触したりしてはいけません。互換性のないキーは`path_morph_topology`になります。途中の図形が無効なら、位相を変更して続けず描画中に失敗します。

複雑な輪郭では、輪郭あたり256個の細分化頂点、4096個の対応点、100万回の辺の組み合わせ検査という制限を超える場合があります。再サンプリングでは頂点をローカルSVG単位の¼以内に保つ必要があり、拡大すると近似が見えることがあります。準備で拒否されたらパスを単純化してください。

## 出力対応 { #export-support }

- **ラスター・動画（PNG、GIF、MP4、WebM）**：パス、破線、トリム、モーフィングを描画します。
- **Lottie**：対応する[パスモーフィング](../reference/export-lottie.md#lottie-path-morph)をベクターで出力します。
- **HTML**：対応する開いたパスをネイティブSVGとCSSの線アニメーションで表現します。モーフィングは作成時の静止画です。
- **PDF・PPTX**：対応するパスはベクターで、モーフィングは作成時の静止画として出力します。
