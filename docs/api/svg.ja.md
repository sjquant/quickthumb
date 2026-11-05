---
description: quickthumbのSVGレイヤーでアイコンやロゴを描画時にラスタライズし、サイズ、整列、ブレンド、エフェクトを指定します。
---

# SVG { #svg }

`.svg()`はSVGを重ねるレイヤーを追加し、描画時にラスタライズします。どの出力サイズでも鮮明にしたいアイコン、ロゴ、ベクター装飾に使ってください。

!!! note "追加の依存関係"
    SVGレイヤーには`svg`追加機能（[cairosvg](https://cairosvg.org/)）が必要です。

    ```bash
    pip install "quickthumb[svg]"
    ```

    未インストールのまま`svg`レイヤーを含むキャンバスを描画すると、`RenderingError`になります。

## シグネチャ { #signature }

```python
canvas.svg(
    path,
    position,
    width=None,
    height=None,
    opacity=1.0,
    rotation=0.0,
    align=Align.TOP_LEFT,
    effects=None,
    blend_mode=None,
)
```

## パラメーター { #parameters }

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `path` | `str` | **必須** | SVG文書のローカルパスかURLです。 |
| `position` | `tuple` | **必須** | `(x, y)`位置。整数（ピクセル）か百分率文字列（`"50%"`）です。 |
| `width` | `int \| None` | `None` | ラスター出力の幅（ピクセル）。`height`を省くと縦横比を維持します。 |
| `height` | `int \| None` | `None` | ラスター出力の高さ（ピクセル）。`width`を省くと縦横比を維持します。 |
| `opacity` | `float` | `1.0` | `0.0`から`1.0`までの不透明度です。 |
| `rotation` | `float` | `0.0` | 回転角（度）です。 |
| `align` | `str \| Align \| tuple` | `Align.TOP_LEFT` | レイヤーのどの点を`position`に合わせるか。[Align](enums.md#align)を参照してください。 |
| `effects` | `list \| None` | `[]` | 画像と同じ`Stroke`、`Shadow`、`Glow`、`Filter`です。 |
| `blend_mode` | `str \| BlendMode \| None` | `None` | 下のレイヤーと合成するブレンドモードです。 |

固定サイズのビットマップを拡大するのではなく、指定サイズでSVGをラスタライズするため、大きく描いてもロゴの鮮明さを保てます。

## 例 { #examples }

### 隅にロゴを置く { #logo-in-a-corner }

```python
canvas.svg(
    path="logo.svg",
    position=("95%", "6%"),
    width=120,
    align=("right", "top"),
)
```

### 回転と不透明度を指定した装飾 { #decorative-element-with-rotation-and-opacity }

```python
canvas.svg(
    path="assets/images/spark.svg",
    position=("70%", "20%"),
    width=44,
    align=("center", "middle"),
    rotation=20,
    opacity=0.8,
)
```

### 影付きのリモートSVG { #remote-svg-with-a-shadow }

```python
from quickthumb import Shadow

canvas.svg(
    path="https://example.com/badge.svg",
    position=("50%", "85%"),
    width=200,
    align=("center", "middle"),
    effects=[Shadow(offset_x=0, offset_y=8, color="#000000", blur_radius=16)],
)
```

## 検証規則 { #validation-rules }

- `path`と`position`は必須です。
- `position`は2要素のタプルです。百分率文字列は`-?N%`形式です。
- `opacity`は`0.0`から`1.0`の範囲です。
- `quickthumb[svg]`がない状態で描画すると`RenderingError`になります。
