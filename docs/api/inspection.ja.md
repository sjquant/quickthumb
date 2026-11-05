---
description: CanvasとDeckをJSON対応の共通形式で検査し、文書の種類で分岐せずに基準サンプルとページのレイアウトを対応付けます。
---

# ドキュメントの検査とサンプリング { #document-inspection-and-sampling }

CanvasとDeckの両方を扱うツールやエージェントでは`inspect_document()`を使ってください。既存のレイアウト、モーション、診断レポートと観察したアセット情報を、`DocumentInspection`にまとめます。

```python
from quickthumb import Canvas, Deck, inspect_document

document = Deck(slides=[Canvas(320, 180).background(color="#FFFFFF")])
report = inspect_document(document, target="video", fps=24, max_samples=100)
print(report.model_dump_json(indent=2))

for page_index, page in enumerate(report.pages):
    print(page_index, page.width, page.height, len(page.layers))
```

## 共通フィールド { #common-fields }

| フィールド | 両方の文書での意味 |
| --- | --- |
| `version` | 結果スキーマのバージョン。現在は`"1"`です。 |
| `kind` | ソースの識別子。`"canvas"`か`"deck"`です。 |
| `width`, `height` | アニメーションの出力ステージと同じ、最初のページのピクセル寸法です。 |
| `pages` | Canvasでは`CanvasInspection`1件、Deckでは文書順の全スライドです。 |
| `motion` | 既存の`MotionInspection`。タイミング、サンプルしたプロパティ状態、スライド別の詳細、機能の行、出力診断を含みます。 |
| `diagnostics` | 既存の`DiagnosticReport`。Deckの指摘は`slide_index`を維持し、文書全体の指摘では`null`です。 |
| `asset_manifest` | 観察したアセット参照、解決状態、利用できる識別情報・ハッシュ・キャッシュ情報です。 |

各ページはレイヤーID、順序、入れ子の子、バウンディングボックス、文字の測定値を維持します。サイズが混在するDeckでも各ページの寸法を保ちます。外側の寸法は作成時のDeck既定値と違っても最初のページのものです。従来の`deck.inspect()`は、引き続き作成時の既定値を報告します。

`target`には出力系統を1つ（`raster`、`html`、`pptx`、`video`）、系統のイテラブル、または全4系統を表す`None`を指定します。`policy`、`fps`、`max_samples`はそのまま`inspect_motion()`へ渡します。モーション観察は`max_samples`で制限され、ラスターフレームではなくプロパティの状態です。空のDeckや無効なオプションには、既存の構造化Quickthumbエラーを返します。

ファイルは出力しません。ただし個別の検査・診断と同様、測定のためにフォントの読み込み、アセットの解決、メディアのデコードを行う場合があります。マニフェストは処理後の状態を表し、別の事前取得を始めたり未解決リソースが利用可能だと保証したりはしません。明示的な解決には`prefetch_assets()`、環境の準備確認には`doctor`を使ってください。

`canvas.inspect()`と`deck.inspect()`の結果型やJSONフィールドは変わりません。レイアウトだけが必要なら、これらの限定されたメソッドを使ってください。

`DocumentInspection.model_json_schema()`はこの結果の構造を説明します。文書作成用のスキーマは引き続き入力仕様を表し、この結果とは異なります。`DiagnosticReport`と同様、診断の指摘は通常のJSONオブジェクトとして復元されます。JSONを往復した後はPythonの診断クラスに依存せず、`code`、`severity`、`message`、位置のフィールドを読んでください。

## 基準サンプルとレイアウトを対応付ける { #join-canonical-samples-to-layout }

両方の文書の`sample()`は、同じ`FrameSequence`を返します。均等なサンプル格子は観察の時刻であり、エンコードされたフレームのインデックスではありません。GIF・動画の量子化とナレーションの差は[アニメーションのタイミング](../timing.md)を参照してください。ページ番号は0始まりで、`frames[].slide`と`timeline[].slide`に一致します。

```python
from quickthumb import DocumentInspection, FrameSequence

layout = DocumentInspection.model_validate_json(report.model_dump_json())
samples = FrameSequence.model_validate_json(document.sample().model_dump_json())
for frame in samples.frames:
    page = layout.pages[frame.slide]
    print(frame.index, frame.time, frame.width, frame.height, len(page.layers))
```

このループには文書の種類による分岐が不要です。`kind`はソースを識別し、ページ別・フレーム別の情報もそのまま使えます。

- `sample()`は作成時の静的なRGBAを各ページ1フレーム取得し、そのページの寸法と透明度を維持します。`time`は`None`、`duration`は0、`timeline`は空です。
- `sample(time=[0, 0.5])`や`sample(fps=24)`はアニメーションのタイムラインを取得します。フレームは時刻順で、最初のページの寸法と不透明なマットを使います。
- `frames[].index`は観察順、`frames[].slide`は表示中のページを表します。タイムライン区間がページの時間と切り替えを説明します。
- `environment`はレンダラーのバージョンを記録します。各フレームはその環境で決定的に比較できるよう、RGBAの生データとSHA-256ダイジェストを持ちます。

時間の意味は別々です。`report.motion.duration`は従来の作成済みモーション検査の意味を維持します。`samples.duration`は`hold`引数と解決されたナレーション時間を含む基準キャプチャの長さです。たとえば静的Canvasのモーション長は0ですが、`hold=2`で時間指定したサンプルは2秒です。再生比較にはサンプルの`duration`、`fps`、`timeline`、フレームの`time`を使い、レイアウトレポートやプロパティサンプルから推測しないでください。
