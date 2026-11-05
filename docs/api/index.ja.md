---
description: Canvas、レイヤー、背景、テキスト、画像、図形、枠線、エフェクト、列挙型、グラデーションのquickthumb APIを調べます。
---

# APIリファレンス { #api-reference }

`Canvas`でシーンを作り、`Deck`で順番に並べます。どちらも同じ文書操作を実装します。各レイヤーに指定できるフィールドは、個別のページで説明しています。

## サポートする公開インターフェース { #supported-public-surface }

文書化された作成用の型と結果モデルは`quickthumb`から、音声解析は`quickthumb.audio`からインポートしてください。別のモジュールから名前をインポートできても、サポートする入口とは限りません。

| インターフェース | サポートする使い方 |
| --- | --- |
| 作成 | `Canvas`、`Deck`、文書化されたレイヤー・エフェクトモデル、モーショントラック、トランジション、オプションモデル |
| 文書操作 | 両方の`validate()`、`inspect()`、`diagnose()`、`prefetch_assets()`、`sample()`、`export()`。汎用処理には`inspect_document()` |
| 結果 | 型付きレポート、`ExportResult`、`CanonicalFrame` / `FrameSequence`、`ImageSequence*`の結果。`model_dump_json()`で保存します。 |
| JSON | `to_json()`、`Canvas.from_json()`、`Deck.from_json()`、`canvas_json_schema()`、`document_json_schema()` |
| 音声に基づく作成 | [`quickthumb.audio.analyze_audio()`と`AudioAnalysis`](audio.md)。ソース時刻のオンセットやRMSに応じたスケールを数値モーションへ記録します。 |
| 用途別の出力 | 戻り値や制御が目的に合う場合に使う、文書化された`render()`、`render_frame()`、`to_*()`、`export_image_sequence()` |

ファイル出力には`export()`を推奨します。機能ポリシーを事前検査し、保存先と診断を返します。用途別メソッドは独自の戻り値を持ち、すべてが同じポリシーを適用するわけではありません。[出力API](../reference/export-methods.md#recommended-output-api)を参照してください。内部の出力処理を直接呼ばず、このAPIで形式ごとのオプションを指定します。

`_`で始まるモジュール、レンダラーやコンテキスト、タイムラインのコンパイルヘルパーは実装詳細です。サポートするライフサイクルなしに変わったり削除されたりします。コンパイラーとレンダラーを自分で調整せず、`sample()`でフレームを取得してください。リファレンスと生成スキーマはインストールした版の対応フィールドを説明します。公開APIでも、バージョン間で固定される意味ではありません。

### 共通の文書ワークフロー { #one-document-workflow }

Python、正規JSON、Deckで同じレイヤーデータを使います。レンダラーオブジェクトや追加の依存関係は不要です。

```python
from quickthumb import Canvas, Deck, Document, ExportResult

canvas = Canvas(320, 180).background(color="#102030").shape(
    "rectangle", position=(24, 24), width=80, height=40, color="#42CEB7",
    id="badge", motion_key="brand", anchor=(0, 0),
)
restored = Canvas.from_json(canvas.to_json())
document: Document = Deck(slides=[restored])
result: ExportResult = document.export("slides.png")
print(result.written_paths)  # Numbered paths are reported by the result.
print(document.sample().frames[0].sha256)
```

## 共通のレイヤー用語 { #shared-layer-vocabulary }

CanvasのレイヤーはDeckスライドや正規JSONでも同じフィールドを使います。Deckが加えるのは順番、切り替え、ナレーション、ノートであり、レイヤーフィールドの名前は変えません。PythonタプルはJSON配列、列挙値は文字列になり、各レイヤーには`type`識別子があります。

| フィールド・概念 | 意味 |
| --- | --- |
| `id` | グループの子孫を含むCanvasシーン内で一意な任意の識別子です。Deckの各スライドは独立した範囲を持ちます。 |
| `motion_key` | Morphでシーン間を対応付ける任意のキーです。シーン内の`id`とは別です。 |
| `position`, `width`, `height` | 作成時の配置とサイズ。対応するレイヤーではピクセルか百分率文字列を使います。百分率はキャンバス基準です。必須フィールドや寸法規則は各レイヤーを参照してください。 |
| `align` | `position`へ合わせるレイアウト枠の点。テキストの整列も決めます。[Align](enums.md#align)を参照してください。 |
| `rotation`, `anchor` | 回転は度です。`anchor=(x, y)`は基準モーション用の0–1の正規化ピボットで、レイアウトの整列とは異なります。静的回転には独自の枠規則があります。[変換の基準点](video.md#transform-anchors-and-independent-scale)を参照してください。 |
| `opacity` | 対応するレイヤーで0から1までの不透明度です。 |
| `animation` | プリセットか、型付きトラックと時間を持つ`AnimationSpec`です。位置トラックは作成位置からの差分です。スケールは外側の物体を変換し、`ImageZoomTrack`は枠内の画像内容を変えます。 |
| グループ | 自動レイアウトが子を配置します。各子の座標を指定せず、行や列には`.group()`を使います。 |
| `parent` / null | 最上位の動かせるレイヤーのための、シーン内の高度な変換階層です。子の位置は親基準ですが、百分率はキャンバス基準のままです。グループレイアウトとは別です。[親変換](video.md#parent-links-and-null-controllers)を参照してください。 |

すべてのレイヤーがすべてのフィールドを受け付けるわけではありません。背景、枠線、null、描画レイヤーは役割が異なります。各ページと[JSONスキーマ](../json-schema.md#published-schema)がフィールドの契約です。[プラグイン登録](../json-schema.md#plugin-layers)ではパラメーターを宣言し、明示的な`PluginRegistry`で描画コールバックを渡せます。JSONを読むだけでコールバックを同梱・インストールするわけではありません。

## ページ一覧 { #pages }

| ページ | 内容 |
| --- | --- |
| [Canvas](canvas.md) | キャンバスの作成、全レイヤーメソッド、検査、出力メソッド |
| [Deck](deck.md) | 複数のキャンバスを1つのPDF、PPTX、HTML、動画、画像シーケンスにする |
| [ドキュメントの検査](inspection.md) | `inspect_document()`とCanvas/Deck共通のサンプリング |
| [背景](background.md) | `.background()`の色、グラデーション、画像 |
| [テキスト](text.md) | `.text()`と`TextPart`、通常・リッチテキスト |
| [画像](image.md) | `.image()`の配置と切り抜き |
| [図形](shape.md) | `.shape()`の長方形、楕円、カプセル、三角形、星、多角形 |
| [パス](path.md) | `.path()`の塗り・線と対応範囲内のモーション |
| [SVG](svg.md) | `.svg()`でSVGのアイコンやロゴを使う |
| [動画](video.md) | `.video()`のクリップ、字幕、音声 |
| [グループ](group.md) | `.group()`の行・列の自動配置 |
| [枠線](outline.md) | `.outline()`のキャンバス枠線 |
| [データの可視化](data-visualizations.md) | `.chart()`と`.qr_code()` |
| [エフェクト](effects.md) | `Stroke`、`Shadow`、`Glow`、`Filter`、`Background`、`Grain`、`Duotone`、`InnerShadow`、`BackdropBlur` |
| [列挙型とグラデーション](enums.md) | `Align`、`BlendMode`、`FitMode`、`LinearGradient`、`RadialGradient`、`TextFillImage` |

## エラーの種類 { #error-types }

| 例外 | 発生する場面 |
| --- | --- |
| `ValidationError` | レイヤービルダーへ無効な引数を渡したとき。即座に発生します。 |
| `RenderingError` | `.render()`、`.to_base64()`、`.to_data_url()`の処理中に失敗したとき |
