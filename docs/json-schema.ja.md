---
description: quickthumb の JSON 仕様形式を解説します。文書構造、公開 JSON Schema、テーマトークン、プラグインレイヤー、各レイヤーとエフェクトを参照できます。
---

# JSON Schema と AI ワークフロー { #json-schema-ai-workflow }

quickthumb のキャンバスは JSON で記述できます。LLM やテンプレートで仕様を生成し、データベースに保存したり、API で送信したり、コンテンツと一緒にバージョン管理したりできます。

最初の仕様を生成・検証・描画する手順は [AI ワークフロー](cookbook/ai-workflow.md)を参照してください。このページでは[レイヤーのフィールド](#layer-schemas)、[エフェクト](#effect-schemas)、[公開スキーマ](#published-schema)を調べられます。`quickthumb` コマンドには `pip install "quickthumb[cli]"` が必要ですが、Python のスキーマヘルパーに CLI extra は不要です。

## シリアライズと復元 { #round-trip-serialization }

正規 JSON は、出力結果レポートとは別に、作成した文書自体を保存します。

```python
from pathlib import Path

from quickthumb import Canvas

# Python → JSON
canvas = Canvas(320, 180).background(color="#102030")
json_str = canvas.to_json()
Path("scene.json").write_text(json_str, encoding="utf-8")

# JSON → Python
restored = Canvas.from_json(Path("scene.json").read_text(encoding="utf-8"))
assert restored.to_json() == json_str
restored.export("from-json.png")
```

!!! note
    `Canvas.from_json()` には **JSON 文字列**を渡します。Python の dict がある場合は、先に `json.dumps(data)` を呼んでください。
    Python 関数は JSON に保存できないため、`.custom(fn)` レイヤーを含むキャンバスはシリアライズできません。

同じ解決済み文書の正規シリアライズ結果は常に同じです。ただし、フォント、画像、メディア、キャッシュにダウンロードしたファイルまでは梱包しません。参照ファイルを保持し、別の環境で描画するときもそのパスにアクセスできるようにしてください。プラグインの JSON に保存されるのは宣言したパラメーターとアセット参照であり、Python コールバックではありません。読み込み時には対応する[明示的なレジストリ](#plugin-layers)を渡します。シーンの JSON が同じでも、フォント、レンダラーのバージョン、プラットフォームが違えば同じピクセルになるとは限りません。

## JSON の構造 { #json-structure }

Canvas の JSON 文書には、4 つの必須トップレベルフィールドと、任意の `theme` ブロックがあります。

```json
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "theme": { ... },
  "layers": [ ... ]
}
```

トップレベルの `"kind"` 判別子は `Canvas.from_json()`、`Deck.from_json()`、CLI のいずれでも必須で、`"canvas"` または `"deck"` を指定します。Canvas 文書は `layers`、Deck 文書は `slides` を持ちます。Deck では共有の既定サイズ、テーマ、遷移も定義できます。各レイヤーオブジェクトにも `"type"` 判別子が必要です。レイヤーは配列順に描画し、最初の項目が最背面になります。レイヤーの識別、配置、整列、モーションには、Python、Canvas JSON のルート、Deck の各スライドで同じ[共通語彙](api/index.md#shared-layer-vocabulary)を使います。Deck 専用の別のレイヤースキーマはありません。

## 公開スキーマ {#published-schema}

`Canvas.from_json()` と同じ Pydantic モデルから、現在の JSON Schema を出力できます。

```bash
quickthumb schema > quickthumb.schema.json
quickthumb schema --output quickthumb.schema.json
quickthumb schema --document --output quickthumb.document-schema.json
```

Python では `canvas_json_schema()` と `document_json_schema()` から同じスキーマを取得できます。このドキュメントでも公開しています。

- <https://quickthumb.solaqua.dev/schema.json>（Canvas）
- <https://quickthumb.solaqua.dev/document-schema.json>（Canvas または Deck）

VS Code で仕様を編集するときに補完と検証を使うには、`.vscode/settings.json` で仕様ファイルを公開スキーマに対応付けます。

```json
{
  "json.schemas": [
    {
      "fileMatch": ["*.thumb.json"],
      "url": "https://quickthumb.solaqua.dev/schema.json"
    }
  ]
}
```

仕様内に `"$schema"` キーを追加するのではなく、このようなファイル対応付けを使ってください。`Canvas.from_json()` は `$schema` を含め、不明なトップレベルフィールドを拒否します。

公開ファイルは `main` ブランチに追従するドキュメントのデプロイごとに再生成します。インストール済みのバージョンに対応するスキーマは `quickthumb schema` で取得してください。

!!! note "スキーマの範囲"
    `quickthumb schema` は、外部ツールや制約付き生成に使う具体的な Canvas 仕様を記述します。Canvas/Deck を統合した判別子付きスキーマには `quickthumb schema --document` を使います。quickthumb が何を読み込めるかの最終的な基準は `Canvas.from_json()` です。

    CLI、`serve`、`Canvas.from_json()`、`Deck.from_json()` は、いずれも対応するトップレベルの `kind` 判別子を必要とします。新しくシリアライズした文書には、Deck のスライドも含め、各文書境界に判別子が入ります。

    Deck が既定の寸法を指定している場合、スライドでは `width` と `height` を省略できます。文書スキーマもこの形式を受け付け、正規 JSON では継承した寸法を各スライドに出力します。遷移オブジェクトには `Deck.from_json()` と同じ、判別子付きの厳密な契約が適用されます。

    `$theme.*` などの記述用の便利な機能は、モデル検証の前に quickthumb が解決します。そのため、quickthumb が読み込める未解決の仕様でも、汎用 JSON Schema バリデーターでは拒否される場合があります。

このコマンドは決定的な JSON だけを出力するため、リポジトリに保存したり、エディターにパイプで渡したり、制約付き生成 API に直接渡したりできます。Canvas スキーマには現在のキャンバスフィールド、組み込みレイヤーの判別子、エフェクト、アニメーション、対応するプラットフォームプリセット、任意のトップレベル `theme` ブロックが含まれます。`--document` スキーマは Deck のルートを追加し、`kind` で両方の文書種別を対応付けます。

## プラグインレイヤー {#plugin-layers}

プラグインは 1 つの明示的な `PluginRegistry` に登録します。登録内容はレイヤー種別とパラメーターを記述します。描画は、別途用意した信頼できる同期 `raster` コールバックが、基準となる RGBA ピクセルとして行います。コールバックはアプリケーションのコードであり、JSON に保存したり JSON からインポートしたりしません。

```python
from quickthumb import Canvas, PluginRegistry, canvas_json_schema

registry = PluginRegistry()
registry.register(
    "brand_badge",
    "1.0",
    params_schema={
        "type": "object",
        "required": ["label"],
        "properties": {"label": {"type": "string"}},
        "additionalProperties": False,
    },
)

canvas = Canvas.from_json(text, registry=registry)
schema = canvas_json_schema(registry=registry)
```

プラグインレイヤーには `type: "plugin"`、`renderer`、`version`、オブジェクト値の `params`、正の整数の `width`/`height` が必要です。`position` は通常のピクセル・パーセント座標を受け付け、`align` と `opacity` はローカルのボックスに適用します。標準の `clip` と `mask` 境界は描画後に適用します。Group は子の配置を制御し、静的なプラグインのピクセルを含むグループ全体をアニメーションできます。文書パーサーと Schema ヘルパーには同じ明示的なレジストリを渡してください。

```python
from PIL import Image

def badge(params, context):
    with Image.new("RGBA", context.size, params["color"]) as image:
        return image.tobytes()

registry.register("badge", "1", raster=badge)
canvas = Canvas(320, 180, registry=registry).plugin(
    "badge", version="1", params={"color": "#42CEB7"},
    position=(20, 30), width=120, height=40,
)
canvas.export("badge.png")
```

`raster` コールバックは params の dict と `context.size` を受け取り、生の RGBA8 バイト列（`width * height * 4`）を返します。外部アセットはレイヤーで `assets={"texture": "assets/texture.png"}` のように宣言し、`context.read_asset("texture")` で読みます。

### 任意のネイティブ SVG { #optional-native-svg }

ベクター出力向けに、SVG 文字列を返す任意の `svg=` コールバックを登録できます。

```python
def badge_svg(params, context):
    width, height = context.size
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<rect width="{width}" height="{height}" fill="{params["color"]}"/></svg>'
    )

registry.register("badge", "1", raster=badge, svg=badge_svg)
```

ネイティブ SVG プラグインに対応しない形式では、自動的に `raster` コールバックによる描画に切り替わります。

### プラグインパラメーターの Schema v1 { #plugin-params-schema-v1 }

`params_schema` は、文書化された `quickthumb plugin-params v1` のサブセットを受け付けます。JSON の型 `object`、`array`、`string`、`number`、`integer`、`boolean`、`null`、および `required`、`properties`、`additionalProperties`、`items`、`const`、`enum`、`oneOf`、`anyOf`、文字列パターンとサイズ制限、数値の最小・最大値に対応します。公開 Schema と実行時の検証を一致させるため、`$ref`、`allOf`、`not` などの未対応キーワードは登録時に拒否します。

プロセス全体の `plugin_registry` も、共通の既定値を使いたいアプリケーション向けに引き続き利用できます。テスト、サービス、ライブラリでは明示的な `PluginRegistry` を使うと、登録を分離し、再現可能にできます。

制約付き生成では、型が決まったフィールドには解決済みの具体値を使ってください。

```text
Use quickthumb.schema.json as the JSON response schema.
Generate one valid quickthumb canvas spec for a 1280x720 YouTube thumbnail.
Return only the JSON object.
Use concrete hex colors and numeric sizes in layer fields.
Use only these layer type discriminators: background, text, image, shape, svg, group, outline.
```

## テーマトークン { #theme-tokens }

トップレベルの `theme` ブロックでブランドのトークンを一度定義し、仕様のどこからでも `$theme.path` で参照できます。

```json
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "theme": {
    "colors": { "primary": "#B8FF00", "ink": "#111111" },
    "sizes": { "title": 96 }
  },
  "layers": [
    { "type": "background", "color": "$theme.colors.ink" },
    { "type": "text", "content": "Hello", "size": "$theme.sizes.title", "color": "$theme.colors.primary" }
  ]
}
```

規則は次のとおりです。

- `theme` ブロックではグループを任意に入れ子にできます。パスは `$theme.colors.primary` のようにドットで指定します。
- 文字列全体が参照なら、元の JSON 型を保ちます。`"size": "$theme.sizes.title"` は数値 `96` になり、トークンにはリストも入れられます。
- スカラートークン（文字列、数値）は、より長い文字列の一部にも埋め込めます。
- テーマ値は他のテーマトークンを参照できます（別名）。循環参照は `ValidationError` になります。
- 未定義のトークン参照は `ValidationError` になります。
- トークンは解析時に解決します。`to_json()` は `theme` ブロックを含めず、解決済みの値を出力します。
- テーマトークンと `$var` テンプレート置換（`quickthumb render --var KEY=VALUE`）は併用できます。`$theme.*` は変数として扱いません。

## レイヤースキーマ {#layer-schemas}

よく使うレイヤーを以下に示します。動画、グラフ、QR コード、カウンター、プラグインのレイヤーも同じ形式です。フィールドは[公開スキーマ](#published-schema)と各 API リファレンスにあります。

### 背景レイヤー { #background-layer }

```json
{
  "type": "background",
  "color": "#0F172A",
  "gradient": null,
  "image": null,
  "opacity": 1.0,
  "blend_mode": null,
  "fit": null,
  "effects": []
}
```

必要なフィールドだけを指定します。それ以外には既定値が使われます。

**グラデーションの種類:**

```json
{
  "type": "background",
  "gradient": {
    "type": "linear",
    "angle": 120,
    "stops": [["#111827", 0.0], ["#11182700", 1.0]]
  }
}
```

```json
{
  "type": "background",
  "gradient": {
    "type": "radial",
    "stops": [["#00000000", 0.0], ["#000000CC", 1.0]],
    "center": [0.5, 0.5]
  }
}
```

**画像の背景:**

```json
{
  "type": "background",
  "image": "https://example.com/photo.jpg",
  "fit": "cover",
  "blend_mode": "multiply",
  "effects": [
    { "type": "filter", "blur": 4, "brightness": 0.75, "contrast": 1.1, "saturation": 0.9 }
  ]
}
```

---

### テキストレイヤー { #text-layer }

```json
{
  "type": "text",
  "content": "Hello World",
  "font_source": "auto",
  "font_variations": {},
  "emoji_style": "monochrome",
  "size": 72,
  "color": "#FFFFFF",
  "position": ["50%", "50%"],
  "align": "center",
  "max_height": null,
  "min_size": 1,
  "balance_lines": false,
  "opacity": 1.0,
  "rotation": 0.0,
  "effects": []
}
```

**`TextPart` リストによるリッチテキスト:**

```json
{
  "type": "text",
  "content": [
    {
      "text": "5 ",
      "color": "#FBBF24",
      "font_source": null,
      "font_variations": null,
      "emoji_style": null,
      "weight": 900,
      "effects": []
    },
    {
      "text": "WARNING SIGNS",
      "color": "#FFFFFF",
      "font_source": "auto",
      "font_variations": {},
      "emoji_style": "monochrome",
      "weight": 900,
      "effects": []
    }
  ],
  "size": 80,
  "position": ["8%", "55%"],
  "align": "left",
  "max_width": "65%",
  "auto_scale": false,
  "rotation": 0.0,
  "opacity": 1.0,
  "effects": [
    { "type": "stroke", "width": 3, "color": "#000000" },
    { "type": "shadow", "offset_x": 4, "offset_y": 4, "color": "#000000", "blur_radius": 8 }
  ]
}
```

**グラデーションで塗る文字:**

```json
{
  "type": "text",
  "content": "GRADIENT",
  "size": 120,
  "fill": {
    "type": "linear",
    "angle": 90,
    "stops": [["#FF6B6B", 0.0], ["#4ECDC4", 1.0]]
  },
  "position": ["50%", "50%"],
  "align": "center",
  "effects": []
}
```

**画像で塗る文字:**

```json
{
  "type": "text",
  "content": "TEXTURE",
  "size": 140,
  "fill": {
    "type": "image",
    "path": "fire_texture.jpg",
    "fit": "cover"
  },
  "position": ["50%", "50%"],
  "align": "center",
  "effects": []
}
```

`fill` の判別子は `"linear"`、`"radial"`、`"image"` で、背景グラデーションと同じタグです。同じ判別子付きオブジェクトで、`TextPart` ごとにも `fill` を設定できます。

**Align の値:** `"center"`、`"left"`、`"right"`、`"top-left"`、`"top-center"`、`"top-right"`、`"bottom-left"`、`"bottom-center"`、`"bottom-right"`

---

### 画像レイヤー { #image-layer }

```json
{
  "type": "image",
  "path": "portrait.png",
  "position": ["74%", "54%"],
  "width": 420,
  "height": 520,
  "fit": "cover",
  "align": "center",
  "opacity": 1.0,
  "rotation": 0.0,
  "remove_background": false,
  "border_radius": 24,
  "blend_mode": "normal",
  "effects": [
    { "type": "filter", "contrast": 1.1, "saturation": 1.05 },
    { "type": "shadow", "offset_x": 0, "offset_y": 12, "color": "#000000", "blur_radius": 24 }
  ]
}
```

---

### 図形レイヤー { #shape-layer }

```json
{
  "type": "shape",
  "shape": "rectangle",
  "position": [48, 48],
  "width": 320,
  "height": 96,
  "color": "#CC0000",
  "border_radius": 14,
  "opacity": 1.0,
  "rotation": 0.0,
  "align": "top-left",
  "effects": [
    { "type": "stroke", "width": 2, "color": "#FFFFFF" }
  ]
}
```

`"shape"` の値: `"rectangle"`、`"ellipse"`、`"pill"`、`"triangle"`、`"star"`、`"polygon"`

**星形と多角形:**

```json
{
  "type": "shape",
  "shape": "star",
  "position": ["80%", "50%"],
  "width": 280,
  "height": 280,
  "color": "#7C5CFF",
  "align": "center",
  "rotation": 12,
  "star_points": 5,
  "inner_radius": 0.45
}
```

```json
{
  "type": "shape",
  "shape": "polygon",
  "position": [600, 60],
  "width": 160,
  "height": 100,
  "color": "#53BF9D",
  "points": [[0.0, 0.25], [0.6, 0.25], [0.6, 0.0], [1.0, 0.5], [0.6, 1.0], [0.6, 0.75], [0.0, 0.75]]
}
```

`"polygon"` には `points` が必須です（他の形では指定できません）。図形のボックス内を `0.0`〜`1.0` に正規化した、3 個以上の頂点を指定します。`star_points`（3 以上）と `inner_radius`（0 より大きく 1 未満）は `"star"` だけに適用します。

---

### SVG レイヤー { #svg-layer }

描画時にラスター化します。`quickthumb[svg]` extra が必要です。[SVG リファレンス](api/svg.md)を参照してください。

```json
{
  "type": "svg",
  "path": "logo.svg",
  "position": ["92%", "10%"],
  "width": 120,
  "align": "center",
  "opacity": 1.0,
  "rotation": 0.0,
  "blend_mode": null,
  "effects": []
}
```

`width`/`height` はラスター寸法を指定します。片方だけなら縦横比を保ちます。SVG レイヤーは画像レイヤーと同じ `effects` を使えます。

---

### グループレイヤー { #group-layer }

自動レイアウトのコンテナーです。子を測定し、行または列に並べるため、子に `position` を指定してはいけません。[Group リファレンス](api/group.md)を参照してください。

```json
{
  "type": "group",
  "direction": "column",
  "gap": 24,
  "padding": 0,
  "position": ["8%", "50%"],
  "align": ["left", "middle"],
  "item_align": "start",
  "children": [
    { "type": "shape", "shape": "pill", "width": 120, "height": 36, "color": "#E94560" },
    { "type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900 },
    { "type": "text", "content": "No coordinates were harmed", "size": 40, "color": "#A2A8D3" }
  ]
}
```

- `direction`: `"column"`（既定）または `"row"`
- `gap`: 子の間隔（ピクセル）。`padding`: 整数、`[vertical, horizontal]`、`[top, right, bottom, left]`
- `item_align`: 交差軸上の配置。`"start"`、`"center"`、`"end"` のいずれか
- `children` の型: `"text"`、`"image"`、`"shape"`、`"svg"`、入れ子の `"group"`

---

### 枠線レイヤー { #outline-layer }

```json
{
  "type": "outline",
  "width": 12,
  "color": "#B8FF00",
  "offset": 0,
  "opacity": 1.0
}
```

---

## エフェクトのスキーマ {#effect-schemas}

エフェクトは各レイヤーの `"effects"` 配列に入れ、`"type"` 判別子を使います。

=== "Stroke"
    ```json
    { "type": "stroke", "width": 4, "color": "#000000" }
    ```

=== "Shadow"
    ```json
    { "type": "shadow", "offset_x": 4, "offset_y": 8, "color": "#000000", "blur_radius": 12 }
    ```

=== "Glow"
    ```json
    { "type": "glow", "color": "#B8FF00", "radius": 16, "opacity": 0.35 }
    ```

=== "Filter"
    ```json
    { "type": "filter", "blur": 4, "brightness": 0.75, "contrast": 1.1, "saturation": 0.9 }
    ```

=== "Background（文字）"
    ```json
    { "type": "background", "color": "#111827CC", "padding": [16, 24], "border_radius": 14, "opacity": 1.0 }
    ```

=== "Grain"
    ```json
    { "type": "grain", "intensity": 0.12, "monochrome": true, "blend_mode": "overlay", "opacity": 1.0 }
    ```

    `blend_mode` の値は `"overlay"`、`"screen"`、`"multiply"`、`"normal"` です。任意の整数 `"seed"` で結果を再現可能にできます。

=== "Duotone"
    ```json
    { "type": "duotone", "shadows": "#0A1730", "highlights": "#7FADFF", "opacity": 1.0 }
    ```

=== "Inner shadow"
    ```json
    { "type": "inner_shadow", "offset_x": 0, "offset_y": 6, "color": "#00000080", "blur_radius": 12, "opacity": 1.0 }
    ```

=== "Backdrop blur"
    ```json
    { "type": "backdrop_blur", "radius": 24, "opacity": 1.0 }
    ```

各レイヤーが使えるエフェクトは、[エフェクトのリファレンス](api/effects.md)にあります。

## 完全な例 { #complete-example }

YouTube 風サムネイルの仕様全体です。

```json
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "layers": [
    {
      "type": "background",
      "image": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3",
      "fit": "cover",
      "effects": [{ "type": "filter", "brightness": 0.6 }]
    },
    {
      "type": "background",
      "color": "#000000",
      "opacity": 0.35
    },
    {
      "type": "shape",
      "shape": "rectangle",
      "position": [52, 52],
      "width": 360,
      "height": 96,
      "color": "#CC0000",
      "border_radius": 14,
      "effects": []
    },
    {
      "type": "text",
      "content": [
        { "text": "AI ", "color": "#B8FF00", "weight": 900, "effects": [] },
        { "text": "THUMBNAILS", "color": "#FFFFFF", "weight": 900, "effects": [] }
      ],
      "size": 108,
      "position": ["8%", "52%"],
      "align": "left",
      "max_width": "58%",
      "rotation": 0.0,
      "opacity": 1.0,
      "effects": [
        { "type": "stroke", "width": 6, "color": "#000000" },
        { "type": "shadow", "offset_x": 4, "offset_y": 4, "color": "#000000", "blur_radius": 8 }
      ]
    },
    {
      "type": "image",
      "path": "portrait.png",
      "position": ["75%", "55%"],
      "width": 430,
      "height": 540,
      "fit": "cover",
      "align": "center",
      "border_radius": 24,
      "effects": [
        { "type": "shadow", "offset_x": 0, "offset_y": 14, "color": "#000000", "blur_radius": 24 }
      ]
    },
    {
      "type": "outline",
      "width": 12,
      "color": "#B8FF00",
      "offset": 0,
      "opacity": 1.0
    }
  ]
}
```

## LLM で仕様を生成する { #generating-specs-with-an-llm }

[AI ワークフロー](cookbook/ai-workflow.md)では、公開スキーマをモデルに渡し、検証エラーや `diagnose()` の検出結果を返して、新しいデザインではなく修正を依頼するまでの手順を説明しています。

## シリアライズ時の注意 { #serialization-notes }

| フィールド | 保存形式 |
| --- | --- |
| `align` | 文字列: `"center"`、`"top-left"` など |
| `blend_mode` | 文字列: `"multiply"`、`"normal"` など |
| `fit` | 文字列: `"cover"`、`"contain"`、`"fill"` |
| `position` | JSON 配列: `[640, 360]` または `["50%", "50%"]` |
| グラデーションの停止点 | `["#color", 0.0]` のペアの JSON 配列 |
| `null` フィールド | 省略したフィールドには `null` または既定値を使います |
| `theme` ブロック | 解析時に解決します。`to_json()` は `theme` ブロックなしで解決済みの値を出力します |
