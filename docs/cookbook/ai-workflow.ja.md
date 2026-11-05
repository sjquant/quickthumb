---
description: LLMでquickthumbのJSON仕様を作り、検証と診断の結果を返しながら修正してレンダリングします。
---

# AIワークフロー { #ai-workflow }

LLMはレイアウトをJSONで書けますが、フィールド名を推測させると間違えることがあります。quickthumbには公開JSON Schemaがあり、無効な仕様には問題のフィールドを示すエラーを返します。有効な仕様でも、描画前にレイアウトの問題を検査できます。

次の流れで繰り返します。

1. モデルにスキーマを渡し、欲しい画像を説明します。
2. 応答を`Canvas.from_json()`で読み込みます。失敗したらエラーをモデルへ返します。
3. `diagnose()`を実行し、指摘があればそれも返します。
4. レンダリングします。

## 1. モデルにスキーマを渡す { #1-give-the-model-the-schema }

スキーマを一度出力します。

```bash
python -m pip install "quickthumb[cli]"
quickthumb schema --output quickthumb.schema.json
```

Pythonの`canvas_json_schema()`でも取得できます。約100 KBと大きいため、プロバイダーが対応していれば、構造化出力やツール呼び出しの応答スキーマとして使うのが適しています。制約の適用範囲はプロバイダー次第です。返された仕様を検証し、描画結果も確認してください。プロンプトへ直接入れる場合は、`layers`と`effects`の定義が重要です。

たとえば次のように指示できます。

```text
Write a quickthumb canvas spec as JSON, following the attached schema.

Canvas: 1280×720 YouTube thumbnail.
- Dark navy background (#0F172A).
- Left-aligned two-line headline: "AI-GENERATED" in cyan (#22D3EE),
  "THUMBNAILS" in white, 96px, weight 900.
- Cyan outline around the canvas, 12px.

Use percentage strings like "8%" for positions. Return only the JSON.
```

## 2. 読み込んでエラーを返す { #2-load-it-and-send-back-errors }

```python
import json
from quickthumb import Canvas, ValidationError

spec = """
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "layers": [
    {"type": "background", "color": "#0F172A"},
    {
      "type": "text",
      "id": "headline",
      "content": [
        {"text": "AI-GENERATED\\n", "color": "#22D3EE"},
        {"text": "THUMBNAILS", "color": "#FFFFFF"}
      ],
      "font": "Inter",
      "font_source": "google",
      "size": 96,
      "weight": 900,
      "position": ["8%", "50%"],
      "align": ["left", "middle"]
    },
    {"type": "outline", "width": 12, "color": "#22D3EE"}
  ]
}
"""

try:
    canvas = Canvas.from_json(spec)
except ValidationError as error:
    feedback = [
        f"{detail.path}: {detail.message}" + (f" ({detail.suggestion})" if detail.suggestion else "")
        for detail in error.details
    ]
    # Send `feedback` back to the model and ask for a corrected spec.
    raise
```

`error.details`の各項目にはフィールドのJSON Pointer（`path`）、存在する場合はレイヤーの`id`、安定した`code`、場合によっては`suggestion`が含まれます。各レイヤーに`id`を付けると、モデルが指摘箇所を修正しやすくなります。

```text
/layers/1/size (layer 'headline'): Input should be greater than 0
```

コードの一覧は[構造化エラー](../errors.md)を参照してください。

## 3. レイアウトを検査する { #3-check-the-layout }

仕様として有効でも、小さすぎる文字、枠からはみ出す単語、明るい写真上の白文字など、見た目の問題は起こりえます。`diagnose()`でこうした問題を検出できます。

```python
findings = canvas.diagnose().findings
for finding in findings:
    print(finding.severity, finding.code, finding.message)
```

```text
warning low-contrast text worst-tile contrast ratio 1.04 against the layers below it is under 2.0; the text may be hard to read
```

検証エラーと同様に、診断結果もモデルへ返してください。検査項目は[診断とCLI](../diagnostics.md)にあります。

## 4. レンダリングする { #4-render }

```python
canvas.render("thumbnail.png")
```

## 変更を依頼する { #asking-for-changes }

気に入った仕様ができたら、新しいデザインではなく部分的な修正を頼みます。現在の仕様と具体的な変更を1つ渡してください。

```text
Here is the current spec:

<spec>

Change the outline color to #B8FF00 and the headline size to 104.
Keep everything else the same. Return only the JSON.
```

小さな修正なら、ほかのレイアウトを安定させたまま調整できます。2つのJSONファイルの差分を取れば、モデルが変えた箇所も正確に確認できます。

## PythonではなくJSONを使う理由 { #why-json-rather-than-python }

モデルはquickthumbのPythonコードも書けますが、その場合は生成されたコードを実行する必要があります。JSON仕様はデータなので、モデルが書いたコードを実行せずに検証、保存、差分比較、レンダリングができます。
