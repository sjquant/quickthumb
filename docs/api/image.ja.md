---
description: quickthumbの画像レイヤーで、ローカル・リモート画像、フィット、配置、マスク、エフェクト、背景除去を使う方法を説明します。
---

# 画像 { #image }

`.image()`は位置を指定した画像を重ねます。ローカルファイル、リモートURL、背景除去、フィット、ブレンド、エフェクトに対応します。

## シグネチャ { #signature }

```python
canvas.image(
    path,
    position,
    width=None,
    height=None,
    fit=None,
    opacity=1.0,
    rotation=0.0,
    align=Align.TOP_LEFT,
    remove_background=False,
    border_radius=0,
    blend_mode=None,
    effects=None,
)
```

## パラメーター { #parameters }

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `path` | `str` | **必須** | ローカルパスかリモートの`http(s)://` URLです。 |
| `position` | `tuple` | **必須** | `(x, y)`位置。整数（ピクセル）か百分率文字列（`"50%"`）です。 |
| `width` | `int \| None` | `None` | 目標幅（ピクセル）。片方の寸法だけなら縦横比を維持します。 |
| `height` | `int \| None` | `None` | 目標高さ（ピクセル）。片方の寸法だけなら縦横比を維持します。 |
| `fit` | `str \| FitMode \| None` | `None` | `width`と`height`の両方を指定したときの合わせ方。[FitMode](enums.md#fitmode)を参照してください。 |
| `opacity` | `float` | `1.0` | `0.0`から`1.0`までの不透明度です。 |
| `rotation` | `float` | `0.0` | 回転角（度）です。 |
| `align` | `str \| Align \| tuple` | `Align.TOP_LEFT` | 画像のどの点を`position`に合わせるか。[Align](enums.md#align)を参照してください。 |
| `remove_background` | `bool` | `False` | AIで背景を除去します。`quickthumb[rembg]`が必要です。 |
| `border_radius` | `int` | `0` | 角の丸み（ピクセル）。0以上の整数です。 |
| `blend_mode` | `str \| BlendMode \| None` | `None` | 合成のブレンドモード。[BlendMode](enums.md#blendmode)を参照してください。 |
| `effects` | `list \| None` | `[]` | `Stroke`、`Shadow`、`Glow`、`Filter`、`Grain`のリストです。 |

## 例 { #examples }

### 基本の重ね合わせ { #basic-overlay }

```python
canvas.image(
    path="portrait.png",
    position=("74%", "54%"),
    width=420,
    height=520,
    fit="cover",
    align=("center", "middle"),
)
```

### エフェクトを付ける { #with-effects }

```python
from quickthumb import Filter, Shadow

canvas.image(
    path="portrait.png",
    position=("74%", "54%"),
    width=420,
    height=520,
    fit="cover",
    align=("center", "middle"),
    border_radius=28,
    effects=[
        Filter(contrast=1.1, saturation=1.05),
        Shadow(offset_x=0, offset_y=12, color="#000000", blur_radius=24),
    ],
)
```

### 背景を除去する { #background-removal }

```python
canvas.image(
    path="portrait.jpg",
    position=("75%", "55%"),
    width=430,
    height=540,
    align=("center", "middle"),
    remove_background=True,
)
```

!!! note
    `remove_background=True`にはPython 3.11以降と`uv pip install "quickthumb[rembg]"`が必要です。初回にONNXモデル（約170 MB）をダウンロードしてキャッシュします。

### リモート画像 { #remote-image }

```python
canvas.image(
    path="https://example.com/avatar.png",
    position=("50%", "50%"),
    width=300,
    height=300,
    align=("center", "middle"),
    border_radius=150,  # circle
)
```

### 縦横比を保つ { #preserve-aspect-ratio }

```python
# Only width: height keeps the image's proportions
canvas.image(path="logo.png", position=(40, 40), width=200)

# Only height: width keeps the image's proportions
canvas.image(path="logo.png", position=(40, 40), height=80)
```

## フィットモード { #fit-modes }

`fit`は`width`と`height`の両方がある場合に適用します。

| 値 | 動作 |
| --- | --- |
| `"cover"` | 枠を埋め、必要ならはみ出す部分を切り取ります。 |
| `"contain"` | 画像全体を枠内に収め、端に余白を残します。 |
| `"fill"` | 縦横比を無視し、枠にぴったり合うように引き伸ばします。 |

## 検証規則 { #validation-rules }

- `path`と`position`は必須です。
- `position`は2要素のタプルです。百分率文字列は`-?N%`形式です。
- `border_radius`は0以上です。
- `opacity`は`0.0`から`1.0`の範囲です。
- 無効な`path`やリモートダウンロードの失敗は、描画時に`RenderingError`になります。
