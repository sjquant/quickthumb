---
description: canvas.diagnose() でレイアウトや読みやすさを検査し、quickthumb CLI で仕様の検査、描画、監視、比較、プレビューを行います。
---

# 診断と CLI { #diagnostics-cli }

quickthumb はファイルを出力せずに、レイアウトや読みやすさに関するよくある問題を検査できます。Python では `canvas.diagnose()`、ターミナルでは `quickthumb lint` を使います。

Python から検査する場合は、次の例から始めてください。JSON ファイルには [CLI をインストールして `quickthumb lint` を実行](#quickthumb-lint)します。出力に必要な依存関係は [`quickthumb doctor`](#quickthumb-doctor)、ファイルへの出力は [`quickthumb render`](#quickthumb-render) を使ってください。詳しい検出ルールとその他の CLI コマンドを以下に説明します。

## `canvas.diagnose()` { #canvasdiagnose }

`DiagnosticReport` を返します。その `findings` リストには `Diagnostic` が入ります。リストが空なら、検査対象の問題は見つからなかったという意味です。見た目の品質を保証したり、あらゆる問題を検出したりするものではないため、描画結果も確認してください。

```python
from quickthumb import Canvas

with open("spec.json", encoding="utf-8") as f:
    canvas = Canvas.from_json(f.read())

for finding in canvas.diagnose().findings:
    print(finding.severity, finding.code, finding.message)
```

各 `Diagnostic` は、人が読める安定したフィールドと、自動処理向けの任意の構造化フィールドを持ちます。

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `code` | `str` | `"off-canvas"`、`"tiny-text"`、`"text-overflow"`、`"text-clipped"`、`"missing-glyph"`、`"low-contrast"`、`"layer-overlap"`、`"layer-hidden"`、`"edge-crowding"`、`"near-alignment"`、`"caption-safe-area"`、`"caption-timing"`、`"caption-overlap"`、`"caption-reading-time"`、`"clip-stretch"`、`"motion-path-unused-handle"` のいずれか |
| `severity` | `str` | `"warning"` または `"error"` |
| `layer_index` | `int` | 問題のあるレイヤーの `canvas.layers` 内のインデックス |
| `message` | `str` | 測定値を含む、人が読める説明 |
| `layer_id` | `str \| None` | 測定対象の安定したレイヤー ID。例: `"layer:3"`、グループ内の子なら `"layer:3:0"` |
| `layer_name` | `str \| None` | レイヤーモデルに名前がある場合はその名前 |
| `bbox` | `dict \| None` | キャンバス座標で測定した境界ボックス。`x`、`y`、`width`、`height` を含みます |
| `related_layers` | `list[str]` | 検出結果に関係するレイヤー ID |
| `measured` | `dict` | コントラスト比、フォントサイズ、キャンバス寸法など、ルール固有の生の測定値 |
| `suggestion` | `str \| None` | ルールが提示できる場合の修正案 |

### 検査する項目 { #what-gets-checked }

| コード | 検出条件 |
| --- | --- |
| `off-canvas` | レイヤーの境界ボックスが一部または全部、キャンバスの外にあります |
| `motion-path-unused-handle` | 最初の位置キーフレームの入力ハンドル、または最後の出力ハンドルに隣接する区間がありません |
| `tiny-text` | 文字の大きさがキャンバスの高さの 2.5% 未満で、サムネイルでは読めない可能性があります |
| `text-overflow` | 単語がレイヤーの `max_width` より長く、折り返せません |
| `text-clipped` | 折り返した文字がキャンバスまたは指定したテキストボックスをはみ出します |
| `missing-glyph` | 選択したフォントで、1 文字以上が欠落グリフの代替記号として描画されます |
| `low-contrast` | 文字色と、その下に合成したレイヤーのコントラスト比が 2.0 未満です |
| `layer-overlap` | 表示中の 2 つのレイヤーが大きく重なり、互いを隠しています |
| `layer-hidden` | 表示中のレイヤーが、後から描く不透明なレイヤーに完全に隠れています |
| `edge-crowding` | 表示中のレイヤーがキャンバスの安全余白や配信先のオーバーレイに近すぎます |
| `near-alignment` | 関連する回転していないレイヤーの x/y の開始位置が 3 ピクセル以内でずれています |
| `caption-safe-area` | 動画字幕がキャンバスの安全余白内に入っています |
| `caption-timing` | 動画字幕の終了時刻がクリップの終了後にあるため、最後まで表示されません |
| `caption-overlap` | 2 つの動画字幕が同じ時間帯と描画背景を共有しています |
| `caption-reading-time` | 表示が 0.8 秒未満、または毎秒 20 表示桁を超え、読む時間が不足しています。日本語や韓国語などの全角文字は 1 文字を 2 桁、接合子や結合文字は 0 桁と数えます。字幕がクリップより長い場合は、実際に見える区間だけで測定します |
| `clip-stretch` | クリップが元の速度の 0.5 倍未満、または 2 倍を超える速度で再生されます。通常はシーンに合わせた引き伸ばしですが、意図的なスローモーションやタイムラプスも同じように報告されます |

!!! tip "LLM と使う場合"
    新しいデザインを依頼するのではなく、検出結果を具体的な修正指示としてモデルに返してください。[AI ワークフロー](cookbook/ai-workflow.md)を参照してください。

近接整列の検査では、描画後のレイヤー位置を比較し、意図しない 1〜3 ピクセルのずれを見つけます。

!!! note "コントラストと整列の検査"
    - **コントラスト検査**では、テキストレイヤーに付けた `Background` のピル形背景も含め、その下に合成した背景をサンプリングします。
    - **近接整列**では、ほぼ揃っているレイヤー（3px 以内）を報告するため、座標を推測せずに揃えられます。

## `quickthumb` CLI { #the-quickthumb-cli }

CLI には `cli` extra が必要です。

```bash
pip install "quickthumb[cli]"
```

### `quickthumb inspect` { #quickthumb-inspect }

Canvas または Deck の JSON 仕様を、出力ファイルを作らずに検査します。

```bash
quickthumb inspect spec.json
quickthumb inspect deck.json --format json
quickthumb inspect deck.json --target video --fps 24 --max-samples 100
quickthumb inspect spec.json --reduced-motion --var title="Hello"
```

テキスト出力には、順序付きのページ・レイヤー境界、レイヤーごとのモーション時間とイベント数、機能対応と代替表現の行、観測したアセット、レイアウト診断が含まれます。`--format json` は Python の [`inspect_document()` の結果エンベロープ](api/inspection.md)とまったく同じ形式で、`version` と文書の `kind` も出力します。両方の文書種別でページ順と共通フィールドが同じなので、スクリプト側で入力種別を推測する必要はありません。

`--target` は機能の分類（`raster`、`html`、`pptx`、`video`）を選びます。省略すると 4 種類すべてを報告します。`--fps` と `--max-samples` は、画像フレームの生成ではなく、上限付きのモーションプロパティ観測を制御します。`--reduced-motion` はアクセシビリティ用の静的表示ポリシーを検査します。`--var KEY=VALUE` は他の仕様コマンドと同じ規則です。

検査時に、測定のためのフォント・アセット解決やメディアのデコードが行われることがあります。観測したアセット状態を報告しますが、別途プリフェッチや準備状態の確認は行いません。モーション検査の時間はエンコード済み動画の長さではありません。基準となるフレームや再生タイミングには Python の `sample()` タイムラインを使ってください。

検出結果は参考情報なので、警告があっても検査自体が成功すれば終了コードは `0` です。入力・検証・アセット欠落のエラーは `1`、描画・出力カテゴリのエラー（空の Deck のモーション検査を含む）は `2` です。JSON 出力では、これらのエラーに既存の `{"errors": [...]}` 構造化エンベロープを使います。診断結果を合否判定に使うには `lint --fail-on`、環境の準備確認には `doctor` を使ってください。`--fps abc` などの引数解析エラーは、従来どおり Typer 標準のテキストを標準エラーに出し、`2` で終了します。JSON エラーエンベロープは引数解析後に適用されます。

### `quickthumb lint` {#quickthumb-lint}

JSON 仕様に対し、`diagnose()` と同じ検査を行います。

```bash
quickthumb lint spec.json
quickthumb lint spec.json --format json
quickthumb diagnose spec.json --format json
```

```text
[warning] layer 3: tiny-text: text size 14px is below 18px (2.5% of canvas height) ...
[warning] layer 4: low-contrast: text contrast ratio 1.47 against the layers below it ...
```

`--format json` では、機械で処理できるペイロードを出力します。

```json
{
  "summary": {
    "diagnostic_count": 1,
    "error_count": 0,
    "warning_count": 1
  },
  "diagnostics": [
    {
      "code": "tiny-text",
      "severity": "warning",
      "layer_index": 3,
      "message": "text size 14px is below 18px ...",
      "layer_id": "layer:3",
      "bbox": {"x": 80, "y": 64, "width": 120, "height": 17},
      "related_layers": ["layer:3"],
      "measured": {"font_size": 14, "threshold": 18.0},
      "suggestion": "increase text size to at least 18px"
    }
  ]
}
```

`lint` は CI で判定に使える終了コードを返します。

| 終了コード | 意味 |
| --- | --- |
| `0` | 問題なし |
| `1` | 無効な仕様（不正な JSON、検証エラー、アセット欠落、無効なオプション） |
| `2` | 描画失敗 |
| `3` | 検出結果あり |

`diagnose` は `lint` の別名です。どちらも次の自動処理オプションを受け付けます。

```bash
quickthumb lint spec.json --fail-on error
quickthumb lint spec.json --ignore edge-crowding --ignore missing-glyph
```

`--fail-on warning`（既定）は、無視されずに残った検出結果が 1 件でもあれば `3` で終了します。`--fail-on error` は警告を許容し、エラーでのみ失敗します。`--fail-on never` は結果を表示した後、常に `0` で終了します。`--ignore` は一致する診断コードを出力と終了コードの判定の両方から除きます。`--format json` で無効な仕様を処理した場合は、トレースバックではなく[構造化エラー詳細](errors.md)の `errors` リストを出力します。

JSON 入力には、トップレベルの `kind` 判別子（`canvas` または `deck`）が必要です。Deck の検出結果には `slide_index` が加わり、元のレイヤー ID、境界ボックス、測定値、関連レイヤー、修正案も保持されます。

### `quickthumb diff` { #quickthumb-diff }

見た目の変更を採用する前に、描画した画像を基準画像と比較します。

```bash
quickthumb diff golden.png output.png
quickthumb diff golden.png output.png --format json --output diff.png
```

平均知覚ハッシュとピクセル単位の指標を組み合わせて比較します。既定ではチャンネルごとの差が 2 以下なら無視しますが、その許容値を超えるピクセルが 1 つでもあると比較に失敗します。知覚ハッシュの類似度の既定しきい値は `0.95` です。使用するレンダラーに合わせて調整できます。

```bash
quickthumb diff golden.png output.png \
  --threshold 0.98 \
  --pixel-tolerance 1 \
  --max-diff-ratio 0.005
```

CI やエージェントのパイプラインには `--format json` を使います。`--max-diff-ratio` では差を許容するピクセルの割合を指定でき、`--output` では目視確認用のピクセル差分画像を書き出せます。終了コードは次のとおりです。

| 終了コード | 意味 |
| --- | --- |
| `0` | 設定した許容範囲で画像が一致 |
| `1` | 画像が不一致、入力が無効、または出力を書き込めない |

同じ比較を Python のアサーションでも使えます。

```python
from quickthumb import assert_image_similar

assert_image_similar(
    "golden.png",
    "output.png",
    threshold=0.95,
)
```

このアサーションは `ImageDiff` を返します。詳しく報告したい場合は、画像寸法、差のあるピクセル数、正規化した平均誤差、知覚ハッシュ、類似度の指標を利用できます。

### `quickthumb render` {#quickthumb-render}

JSON 仕様を画像ファイルに描画します。

```bash
quickthumb render spec.json -o thumbnail.png
quickthumb render spec.json -o thumbnail.webp --format WEBP --quality 90
quickthumb render spec.json -o debug.png --debug
```

| オプション | 説明 |
| --- | --- |
| `-o, --output` | 出力ファイルのパス（既定: `output.png`） |
| `--format` | `PNG`、`JPEG`、`WEBP` |
| `--quality` | 圧縮品質。JPEG は 1〜95、WebP は 1〜100 です。描画品質を制御するものではありません |
| `--debug` | 公開レイヤー ID の境界ボックスをラスター出力に重ねます |
| `--var KEY=VALUE` | 仕様内の `$KEY` プレースホルダーを置換します（複数回指定可） |
| `--error-format` | `text`（既定）または `json`。[構造化エラー](errors.md)を参照してください |

無効な仕様、アセット欠落、無効なオプションでは `1`、未対応の出力形式などの出力失敗では `2` で終了します。

### `quickthumb watch` { #quickthumb-watch }

ファイルの変更ごとに仕様を再描画します。手作業でレイアウトを調整するときに便利です。

```bash
quickthumb watch spec.json -o preview.png
```

`watch` は `--error-format` を除き `render` と同じオプションを受け付けます。失敗時はテキストを表示し、監視を続けます。

### `quickthumb doctor` {#quickthumb-doctor}

出力前に、パッケージ、ツール、ソースに必要な要件、出力先の権限を検査します。

```bash
quickthumb doctor pdf -o out/thumbnail.pdf
quickthumb doctor mp4 --spec spec.json --format json
```

ワークフローは `png`、`jpeg`、`webp`、`gif`、`svg`、`html`、`pdf`、`pptx`、`mp4`、`webm`、`mov` のいずれかです。`--spec` を指定すると、その仕様のプラグインレンダラー、フォント、SVG・動画レイヤー、背景除去、リモートアセットの要件も調べます。`-o` は出力先に書き込めるかを確認しますが、何も作成しません。

結果はそれぞれ `ok`、`warning`（フォント欠落や利用できないアセットキャッシュなど、任意機能の制限）、`error`（`quickthumb[pdf]` extra や ffmpeg の欠落、未登録プラグイン、書き込めない出力先など、必須要件の失敗）です。すべての警告とエラーに `fix`/`remedy` が付きます。プラグインは CLI プロセスのレジストリで検査します。ここにはインポート時に登録されたプラグインしかないため、コードで登録するプラグインを使う仕様では未登録と報告されます。必須検査に失敗しなければ終了コードは `0`、それ以外は `1` です。

成功しても、出力や忠実度が保証されたわけではありません。パッケージが見つかってもネイティブ Cairo をロードできるとは限らず、FFmpeg が見つかっても必要なエンコーダーがそのビルドに含まれるとは限りません。`doctor` は描画や出力比較を行いません。実際に目的の出力を実行し、結果レポートとファイルを確認してください。見た目の比較が重要なら、明示的な忠実度ポリシーや `quickthumb diff` を使います。

### `quickthumb serve` { #quickthumb-serve }

自動再読み込みに対応したローカル HTML スライドショーサーバーを起動します。ソース引数がなければ `slides.py`、`slides.json`、`slides.html`、`slides.htm` の順で探します。

```bash
quickthumb serve
quickthumb serve examples/investor_deck.py
quickthumb serve deck.json --port 4040 --no-open
```

Python ソースでは、モジュールのトップレベルに `deck`、`slides`、`canvas` のいずれかの名前で 1 つの `Deck` または `Canvas` を定義してください。JSON ソースには `kind: "canvas"` または `kind: "deck"` が必要です。Canvas 文書は `layers`、Deck 文書はトップレベルの `slides` リストを持ちます。`--host` と `--port` で待ち受け先を変更し、`--no-open` で最初のブラウザー起動を抑止できます。JSON テンプレートの置換には `--var KEY=VALUE` を繰り返し指定します。

聴衆向けの画面は `/` です。発表者モードは `?presenter` クエリで選びます。

```text
http://localhost:3030/?presenter
```

発表者モードはプレビューと同じライトテーマです。左側に現在のスライドとノート、右側に次のスライドと一時停止・再開・リセットできるタイマー、その下に移動操作があります。スライドのプレビューは元の縦横比を保ちます。移動位置とスライドごとのアニメーション進行は、同じサーバーから開いた聴衆タブに配信され、再読み込み後も復元されます。聴衆側だけでの移動はそのタブ内に留まります。Python では `.slide(canvas, notes="...")`、JSON ではスライドの `notes` 文字列でノートを追加します。

### タイムラインスクラバー { #timeline-scrubber }

Python や JSON の文書を作成しながら、ラスターのタイムラインを開けます。

```bash
quickthumb serve examples/timeline_preview.py --timeline
quickthumb serve deck.json --timeline --no-open
```

通常の `serve` セッションでも `http://localhost:3030/timeline` から利用できます。既定の画面は引き続き HTML プレゼンテーションで、スライド移動、クリックで始まるアニメーション、同期した発表者操作が使えます。Presentation と Inspect motion は、スライド選択とサムネイル移動を共有します。Presentation ではスライドを元の縦横比で中央に表示し、Inspect motion では下にフレームを探せるパネルを開きます。Presenter は同期した発表者画面、Present は HTML スライドの全画面表示です。HTML 出力が静的または近似になる場合はモーションの注記で説明します。これらはローカルでの制作ツールで、出力する HTML には追加されません。単独の HTML にはサンプリング元の文書がないため、タイムラインには元の Python または JSON を使ってください。

検査画面は出力レンダラーのフレームを表示します。再生、オーディオ、編集機能はありません。ここでのシーク位置は発表者・聴衆の同期とは独立しています。

- 時間スライダーをドラッグするか、秒数を入力するか、スライド・遷移・モーションの境界をクリックします
- **Proxy** は出力の最長辺を 640 ピクセルに制限します（1080×1920 は 360×640）。再利用できるレイヤー画像を用意し、小さいサーフェス上で通常のモーションを合成します。後続のサイズが異なるスライドも同じ出力矩形に収めます
- **Full** は最初のスライドの元の寸法を使います。`Canvas.sample(time=...)` / `Deck.sample(time=...)` と同じ標準品質の基準タイムラインサンプラーです
- ソースを保存すると再読み込みします。選択した解像度と時刻を URL フラグメントに保ち、新しいタイムラインが短ければ時刻を範囲内に収めます
- ブラウザーからのフレーム要求は同時に 1 つだけ実行します。素早くシークすると、待機中の要求は最新の選択に置き換わります。要求したフレームの準備ができるまでは、表示中のラベルは前のフレームを示します。編集によるエラーは表示され、次の保存後に復旧します

タイムラインスクラバーは、出力タイミングに対応する瞬間的なフレームプレビューを描画します。

- **Proxy モード**: 縮小フレーム（最大 640px）を描画し、滑らかに素早くシークします。
- **Full モード**: 標準の出力品質に一致するフル解像度で描画します。
- タイムライン操作中は音声を再生しません。

!!! tip "ローカルでの安全性"
    `quickthumb serve` は手元のコンピューターでローカルの Python・JSON ファイルを実行します。信頼できない内容をプレビューするときは、既定のループバックアドレス（`127.0.0.1`）を使ってください。

### 変数の置換 { #variable-substitution }

JSON を扱うコマンドでは、`--var` により解析前に `$KEY`（または `${KEY}`）プレースホルダーを埋められます。

```bash
quickthumb render template.json -o ep42.png \
  --var TITLE="EPISODE 42" \
  --var ACCENT="#B8FF00"
```

未解決のプレースホルダーがあると終了コードは `1` です。`$theme.*` 参照は変数ではなく、仕様内の[テーマブロック](json-schema.md#theme-tokens)で解決します。
