---
description: 間隔、余白、子の整列、入れ子に対応するquickthumbのグループレイヤーで、行や列の自動レイアウトを作ります。
---

# グループ（自動レイアウト） { #group-auto-layout }

`.group()`は子のサイズを測って行や列に並べるコンテナーです。子を一つずつ手で配置する必要はありません。子の本来のサイズから位置を計算し直すので、見出しが長くなったりバッジが増えたりしても同じ仕様を使えます。LLMが生成するレイアウトにも適しています。

## シグネチャ { #signature }

```python
canvas.group(
    children,
    direction="column",
    gap=0,
    padding=0,
    position=None,
    align=None,
    item_align="start",
)
```

## パラメーター { #parameters }

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `children` | `list` | **必須** | 並べる順の子レイヤー。dictか、`text`、`image`、`shape`、`svg`、`chart`、`qr_code`、入れ子の`group`のモデルです。 |
| `direction` | `str` | `"column"` | 主軸。`"column"`は上から下、`"row"`は左から右です。 |
| `gap` | `int` | `0` | 主軸に沿った子の間隔（ピクセル）。0以上です。 |
| `padding` | `int \| tuple` | `0` | 内側の余白。整数1つ、`(vertical, horizontal)`、`(top, right, bottom, left)`です。 |
| `position` | `tuple \| None` | `None` | グループの枠の基準位置。ピクセルか百分率文字列です。 |
| `align` | `str \| Align \| tuple \| None` | `None` | 画像レイヤーと同様、枠のどの点を`position`に合わせるかを決めます。[Align](enums.md#align)を参照してください。 |
| `item_align` | `str` | `"start"` | 子の交差軸方向の配置。`"start"`、`"center"`、`"end"`です。 |

!!! warning "子に`position`を指定しないでください"
    位置はグループが決めます。子が`position`を指定すると`ValidationError`になります。子の`align`も無視されるので、グループの`item_align`を使ってください。

## 例 { #examples }

### 見出しを縦に並べる { #stacked-headline-block }

```python
canvas = Canvas(1280, 720).background(color="#16213E").group(
    children=[
        {"type": "shape", "shape": "pill", "width": 120, "height": 36, "color": "#E94560"},
        {"type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900},
        {"type": "text", "content": "No coordinates were harmed", "size": 40, "color": "#A2A8D3"},
    ],
    direction="column",
    gap=24,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

### バッジを横に並べる { #horizontal-badge-row }

```python
def chip(label):
    return {
        "type": "text",
        "content": label,
        "size": 24,
        "color": "#22D3EE",
        "weight": 700,
        "effects": [
            {"type": "background", "color": "#1D2547", "padding": [8, 14], "border_radius": 18},
        ],
    }

canvas.group(
    children=[chip("GROUPS"), chip("TOKENS"), chip("LINT")],
    direction="row",
    gap=14,
    position=("50%", "88%"),
    align=("center", "middle"),
)
```

### グループを入れ子にする { #nested-groups }

列の中に行を置いたり、その逆の構成にしたりできます。

```python
canvas.group(
    children=[
        {"type": "text", "content": "RELEASE 0.5", "size": 96, "color": "#FFFFFF", "weight": 900},
        {
            "type": "group",
            "direction": "row",
            "gap": 14,
            "children": [chip("GROUPS"), chip("TOKENS"), chip("LINT")],
        },
    ],
    direction="column",
    gap=28,
    position=("7%", "50%"),
    align=("left", "middle"),
)
```

### 交差軸方向の整列 { #cross-axis-alignment }

```python
canvas.group(
    children=[
        {"type": "text", "content": "CENTERED", "size": 80, "color": "#FFFFFF", "weight": 900},
        {"type": "text", "content": "Both children share a center line", "size": 36, "color": "#A2A8D3"},
    ],
    direction="column",
    gap=18,
    item_align="center",            # cross-axis: center each child horizontally
    position=("50%", "50%"),
    align=("center", "middle"),
)
```

## サイズの決まり方 { #how-sizing-works }

1. 各子の本来のサイズ（文字の境界、画像の寸法、図形の`width`/`height`）を測ります。
2. 主軸に沿って`gap`の間隔を空けながら順に配置します。
3. すべての子を囲む範囲に`padding`を足し、グループの枠にします。
4. 枠全体の`align`で指定した点を`position`へ合わせます。

## JSON形式 { #json-form }

グループもほかのレイヤーと同じようにシリアライズします。完全なスキーマは[JSON Schema](../json-schema.md#group-layer)を参照してください。

```json
{
  "type": "group",
  "direction": "column",
  "gap": 24,
  "position": ["8%", "50%"],
  "align": ["left", "middle"],
  "item_align": "start",
  "children": [
    { "type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900 }
  ]
}
```

## 検証規則 { #validation-rules }

- `children`は空でないリストが必要です。
- 子に`position`は指定できません。グループが位置を決めます。
- 有効な子の種類は`text`、`image`、`shape`、`svg`、`group`です。
- `gap`と`padding`は0以上です。余白のタプルは2要素か4要素です。
