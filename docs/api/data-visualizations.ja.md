---
description: 同じ入力から同じ結果を得られる、棒グラフ、折れ線グラフ、QRコードのレイヤーを説明します。
---

# データの可視化 { #data-visualizations }

quickthumbには、ダッシュボード、カード、SNS画像に使う小さなグラフとQRコードのレイヤーがあります。同じ入力からは常に同じ結果が得られます。棒グラフと折れ線グラフは`ChartData`を共有し、それぞれの種類に必要なスタイルモデルを持ちます。汎用の作図システムではありません。

```python
from quickthumb import (
    BarChartSpec,
    BarChartStyle,
    Canvas,
    LineChartSpec,
    LineChartStyle,
)

canvas = (
    Canvas(800, 400)
    .chart(
        spec=BarChartSpec(
            data=[-4, 8, 12, 6],
            style=BarChartStyle(color="#2563EB", negative_color="#DC2626"),
        ),
        position=(40, 40),
        width=220,
        height=120,
    )
    .chart(
        spec=LineChartSpec(
            data=[2, 5, 3, 7],
            style=LineChartStyle(color="#7C3AED", fill="#DDD6FE"),
        ),
        position=(40, 200),
        width=440,
        height=120,
    )
    .qr_code("https://example.com", position=(620, 40), size=140)
)
```

## 共通のデータとスタイル { #shared-chart-data-and-style }

`ChartData(values=[...])`は、生成する仕様で名前付きのデータオブジェクトが欲しいときに便利です。ビルダーとJSONは普通の数値リストも受け付けます。空、一定、負の値の系列も有効です。値は有限の数でなければならず、`NaN`、無限大、数値以外は`ValidationError`になります。

`BarChartStyle`は`color`、`padding`、`opacity`、`negative_color`、`bar_gap`を受け付けます。`LineChartStyle`は`color`、`padding`、`opacity`、`fill`、`fill_opacity`、`stroke_width`、`point_radius`、`show_points`を受け付けます。選んだグラフで意味のないオプションは、黙って無視せず`ValidationError`にします。どちらの仕様も同じ`.chart()`へ渡します。

折れ線の値は描画枠に合わせて拡大縮小します。一定の系列は縦方向の中央に配置します。棒グラフは値域に必ず0を含むため、正と負の値は基準線の反対側に描かれます。空の系列は何も描きません。

## レイヤービルダー { #layer-builders }

| ビルダー | JSONの種類 | 用途 |
| --- | --- | --- |
| `.chart(spec, position, width, height)` | `chart` / `bar` | `BarChartSpec`で、0を反映した基準線から縦棒を描きます。 |
| `.chart(spec, position, width, height)` | `chart` / `line` | `LineChartSpec`で、既定では点マーカー付きの折れ線を描きます。 |
| `.qr_code(data, position, size)` | `qr_code` | 誤り訂正と余白を指定する正方形のQRコードです。 |

JSONでは`"spec"`内に識別子付きのグラフ仕様を保存します。例：`{ "type": "bar", "data": [1, -2] }`。

グラフはピクセルまたは百分率の位置、`align`、`opacity`、既存の`clip`と`mask`を受け付けます。グループの子にもでき、その場合は位置をグループが自動設定します。QRコードは`foreground`、`background`、`error_correction`（`L`、`M`、`Q`、`H`）、`quiet_zone`を受け付けます。指定した正方形がQRのモジュール行列を維持できないほど小さければ`RenderingError`になります。グラフとQRコードには、PPTXやGIF・動画向けの既存のレイヤー`animation`も指定できます。省略時は静止画となり、同じ入力なら同じ結果を再現できます。

`Canvas.to_json()`で保存し、`Canvas.from_json()`で検証でき、`quickthumb schema`にも含まれます。SVG、HTML、PDF、PPTXでは標準のピクセル単位で一致するラスター代替として維持します。
