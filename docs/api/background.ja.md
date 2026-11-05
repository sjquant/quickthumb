---
description: quickthumbの背景レイヤーで使う色、グラデーション、画像、不透明度、エフェクト、描画順を説明します。
---

# 背景 { #background }

`.background()`はキャンバス全体を覆う背景レイヤーを追加します。複数回呼ぶと描画順に重なり、最初の背景が一番奥になります。

## シグネチャ { #signature }

```python
canvas.background(
    color=None,
    gradient=None,
    image=None,
    opacity=1.0,
    blend_mode=None,
    fit=None,
    effects=None,
)
```

## パラメーター { #parameters }

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `color` | `str \| tuple \| None` | `None` | 単色の塗り。16進文字列（`"#RRGGBB"`、`"#RRGGBBAA"`）かRGB/RGBAタプルです。 |
| `gradient` | `LinearGradient \| RadialGradient \| None` | `None` | グラデーション。[列挙型とグラデーション](enums.md)を参照してください。 |
| `image` | `str \| None` | `None` | ローカルファイルのパスかリモートURLです。 |
| `opacity` | `float` | `1.0` | `0.0`（透明）から`1.0`（不透明）までのレイヤー不透明度です。 |
| `blend_mode` | `str \| BlendMode \| None` | `None` | 下のレイヤーとの合成方法。[BlendMode](enums.md#blendmode)を参照してください。 |
| `fit` | `str \| FitMode \| None` | `None` | 画像でキャンバスを埋める方法。[FitMode](enums.md#fitmode)を参照してください。 |
| `effects` | `list \| None` | `[]` | 背景エフェクト。`Filter`と`Grain`を受け付けます。 |

## 例 { #examples }

### 単色 { #solid-color }

```python
canvas.background(color="#0F172A")
```

### グラデーションの重ね合わせ { #gradient-overlay }

```python
from quickthumb import LinearGradient

canvas.background(
    gradient=LinearGradient(
        angle=120,
        stops=[("#111827", 0.0), ("#11182700", 1.0)],
    ),
    opacity=0.7,
)
```

### エフェクト付きリモート画像 { #remote-image-with-effects }

```python
from quickthumb import Filter

canvas.background(
    image="https://images.unsplash.com/photo-1516321318423-f06f85e504b3",
    fit="cover",
    blend_mode="multiply",
    effects=[Filter(blur=4, brightness=0.75, contrast=1.1, saturation=0.9)],
)
```

### 暗い色を重ねる { #dark-overlay }

```python
canvas.background(color="#000000", opacity=0.4)
```

## 補足 { #notes }

- 背景レイヤーは常にキャンバス全体を覆います。
- `color`、`gradient`、`image`は単独でも、1枚のレイヤー内で組み合わせても使えます。
- `blend_mode`は、このレイヤーを下のレイヤーへ合成するときに適用します。
- `image`はローカルパスとリモートURLに対応します。
- 利用できるエフェクトは[Filter](effects.md#filter)と[Grain](effects.md#grain)を参照してください。
