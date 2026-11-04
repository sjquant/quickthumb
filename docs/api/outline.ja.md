---
description: 幅、色、不透明度、角の丸みを指定してキャンバスの枠線を描く、quickthumbの枠線レイヤーを説明します。
---

# 枠線 { #outline }

`.outline()`はキャンバス全体の縁に枠線を描きます。すべての内容の上に表示するため、通常は最後のレイヤーとして追加します。

## シグネチャ { #signature }

```python
canvas.outline(
    width,
    color,
    offset=0,
    opacity=1.0,
)
```

## パラメーター { #parameters }

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `width` | `int` | **必須** | 枠線の太さ（ピクセル）。正の整数です。 |
| `color` | `str` | **必須** | 枠線の色。16進文字列（`"#RRGGBB"`、`"#RRGGBBAA"`）です。 |
| `offset` | `int` | `0` | キャンバスの縁から内側への距離（ピクセル）。0以上の整数です。 |
| `opacity` | `float` | `1.0` | `0.0`から`1.0`までのレイヤー不透明度です。 |

## 例 { #examples }

### 基本の枠線 { #basic-outline }

```python
canvas.outline(width=12, color="#B8FF00")
```

### 内側に寄せた枠線 { #inset-outline }

```python
# Drawn 8px inside the canvas edge
canvas.outline(width=4, color="#FFFFFF", offset=8)
```

### 半透明の枠線 { #semi-transparent-outline }

```python
canvas.outline(width=8, color="#FFFFFF", opacity=0.5)
```

### 全体の構成で使う例 { #typical-usage-in-a-full-composition }

```python
canvas = (
    Canvas(1280, 720)
    .background(color="#0F172A")
    .text(content="TITLE", size=96, color="#FFFFFF", align="center")
    .outline(width=12, color="#22d3ee")  # always last
)
```

## 補足 { #notes }

- 既定の`offset=0`では、キャンバスの縁から内側へ描きます。
- 大きな`offset`と細い`width`で、浮いて見える額縁のような効果を作れます。
- `opacity`は`0.0`から`1.0`の範囲です。
