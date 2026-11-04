---
description: 安定したコードと JSON Pointer の位置情報を持つ共通の構造化エラーで、検証、アセット欠落、出力、CLI の失敗に対処します。
---

# 構造化エラー { #structured-errors }

quickthumb のすべての失敗（無効なフィールド、アセット欠落、出力先で実現できない機能、不正なコマンドラインオプション）は、共通の機械可読な詳細情報を持ちます。エージェントは説明文を解析せずに問題の入力を特定して対処でき、人には明確な 1 行のメッセージを表示できます。

## エラー詳細のフィールド { #error-detail-fields }

| フィールド | 型 | 意味 |
| --- | --- | --- |
| `code` | string | 失敗の種類を示す安定した識別子（[コード一覧](#error-codes)を参照） |
| `category` | string | `validation`、`asset`、`export`、`input` |
| `message` | string | 人が読める失敗の説明 |
| `path` | string または `null` | 文書内に位置がある場合、その入力位置を指す [RFC 6901 JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901) |
| `layer_id` | string または `null` | 判明している場合、`path` を含む最も内側のレイヤー ID |
| `suggestion` | string または `null` | 提示できる場合、具体的な修正案 |

`path` は解析・検証している文書を基準にします。`Canvas.from_json`、`Deck.from_json`、`validate()`、CLI では文書のルートが基準なので、Deck のエラーは `/slides/<index>` から始まります。`TextLayer(...)` のように Python で直接作ったモデルでは、そのモデルからの相対位置です。

## Python API { #python-api }

quickthumb の例外はすべて `QuickthumbError` を継承し、同じ詳細情報を公開します。

```python
from quickthumb import Canvas, QuickthumbError

try:
    Canvas.from_json(spec).render("out.png")
except QuickthumbError as error:
    for detail in error.details:
        print(detail.code, detail.path, detail.layer_id, detail.suggestion)
    print(error)  # "/layers/1/max_width (layer 'title'): max_width must be positive"
```

| 例外 | カテゴリ | 発生する状況 |
| --- | --- | --- |
| `ValidationError` | `validation` | 不正な JSON、不明・不足のフィールド、無効な値 |
| `MissingAssetError` | `asset` | ローカルの画像、SVG、動画、文字の塗りつぶし、音声のファイルが存在しない場合。`FileNotFoundError` でもあります |
| `RenderingError` | `export` | 未対応の出力形式、出力先が実現できない機能、レンダラーの失敗 |
| `InputError` | `input` | 無効なコマンドラインオプション、読み取れない仕様ファイル |

`Canvas.validate()` と `Deck.validate()` も `ValidationReport.errors` に同じ `ErrorDetail` レコードを返します。事前検査でも描画失敗でも、問題を同じ形式で扱えます。

## CLI { #cli }

`quickthumb render` は `--error-format json`、`quickthumb lint` と `quickthumb diagnose` は `--format json` を使います。失敗時は、すべての詳細フィールドを含む 1 つのエンベロープを標準出力に書き出します。

```bash
quickthumb render spec.json -o out.png --error-format json
```

```json
{
  "errors": [
    {
      "code": "asset_missing",
      "category": "asset",
      "message": "Asset not found: 'hero.png'",
      "path": "/slides/1/layers/0/path",
      "layer_id": "hero",
      "suggestion": "check the path relative to the working directory or use an http(s) URL"
    }
  ]
}
```

テキストモードでは、詳細 1 件につき 1 行を標準エラーに表示し、先頭にコードを付けます。

```text
error[asset_missing] /slides/1/layers/0/path (layer 'hero'): Asset not found: 'hero.png'. Suggestion: check the path relative to the working directory or use an http(s) URL.
```

終了コードはカテゴリに従います。`export` の失敗は `2`、`validation`、`asset`、`input` の失敗は `1` です。

## エラーコード { #error-codes }

| コード | カテゴリ | 意味 |
| --- | --- | --- |
| `invalid_json` | `validation` | 文書が有効な JSON ではありません |
| `invalid_document` | `validation` | 空の Deck など、文書構造が利用できません |
| `invalid_field` | `validation` | フィールドの型が違うか、値が範囲外です |
| `missing_field` | `validation` | 必須フィールドがありません |
| `unknown_field` | `validation` | スキーマにないフィールドです |
| `unknown_plugin` | `validation` | プラグインレイヤーが未登録のレンダラーを指定しています |
| `asset_missing` | `asset` | 参照先のローカルファイルがありません |
| `unsupported_format` | `export` | 拡張子が出力形式に対応していません |
| `unsupported_capability` | `export` | 文書が要求する機能を出力先で実現できません。プラグインレイヤーの描画（quickthumb はプラグインレイヤーを検証できますが、まだ描画できません）や、必要な代替表現を出力ポリシーで禁止した場合（例: `ExportPolicy(unsupported_motion="error")`）などです |
| `missing_dependency` | `export` | FFmpeg などの外部ツールが利用できません |
| `export_failed` | `export` | 書き込めない出力先など、その他の出力・描画失敗です |
| `invalid_option` | `input` | コマンドラインオプションの値が無効です |
| `input_unreadable` | `input` | 仕様ファイルを読めません |
| `unresolved_variable` | `input` | `$KEY` プレースホルダーに対応する `--var` がありません |

コードは安定していますが、メッセージの表現は変わることがあります。自動処理では `message` ではなく `code` と `path` で分岐してください。
