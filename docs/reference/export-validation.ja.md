---
description: quickthumb の形式別の忠実度と検証のリファレンスです。
---

# 形式別の忠実度と検証 { #format-fidelity-and-validation }

[出力リファレンス](../exports.md) · [出力形式を選ぶ](../output-guide.md)

## 任意の静的 SVG 忠実度レポート { #optional-static-svg-fidelity-report }

作業ごとに明示的な合格基準がある場合、`ExportPolicy` から CairoSVG 比較を要求できます。3 つの限界値すべてが必須で、形式ごとの組み込み許容値はありません。次の例は、輪郭やフォントの差を用途別に許容するのではなく、可視 RGBA の完全一致を求めます。

```python
from quickthumb import Canvas, ExportPolicy

policy = ExportPolicy(fidelity={"svg": {
    "pixel_tolerance": 0,
    "max_different_pixel_ratio": 0,
    "min_hash_similarity": 1,
}})
canvas = Canvas(160, 90).background(color="#123456")
result = canvas.export("checked.svg", policy=policy)
comparison = result.pixel_metrics.fidelity
print(comparison.verdict, comparison.pixel_diff_ratio, comparison.hash_similarity)
```

任意の `quickthumb[svg]` extra とシステムの Cairo が必要なのは、選んだ SVG 出力でこの検査を要求したときだけです。レポートには CairoSVG/Cairo のバージョン、基準描画環境、適用した限界値、実際にラスター化した寸法を記録します。作成時の静的な `sample()` の静止画と、リサイズせずに比較します。`exact` は可視 RGBA の全チャンネルが一致、`tolerated` は指定したピクセル割合と平均ハッシュの限界を満たし、`out_of_policy` は限界または寸法が不一致という意味です。平均絶対誤差は 4 チャンネルに対して正規化し、最大チャンネル差も報告します。完全透明なピクセルの隠れた RGB は無視するため、この exact の定義は基準の生ピクセル SHA-256 の一致とは異なります。8×8 平均ハッシュは白に合成しますが、RGBA 測定は独立してアルファ欠落を検出するため、ハッシュが同じでも検出できます。

これは報告専用です。判定が `out_of_policy` でも元の SVG を書き込みます。忠実度の診断は観測結果を示すだけで、新たなラスター代替には切り替えません。参照描画が利用できないか失敗した場合は、出力先を開く前に例外となり、既存ファイルを保持します。既定の出力と SVG 以外ではこの比較を行いません。

この観測が対象とするのは、記録した環境での静的 Cairo 描画です。Cairo はインストール済みフォントを使い、埋め込み CSS `@font-face` を反映しないため、同じフォント環境を別途用意してください。[CairoSVG ドキュメント](https://cairosvg.org/documentation/)を参照してください。ブラウザー、HTML、アニメーションの忠実度を保証するものではありません。SVG のモーションは引き続き作成時の静的な状態です。

## 任意の静的 PDF 忠実度レポート { #optional-static-pdf-fidelity-report }

Canvas の PDF 出力は、`"pdf"` キーに同じ 3 つの明示的な限界値を指定できます。

```python
policy = ExportPolicy(fidelity={"pdf": {
    "pixel_tolerance": 0,
    "max_different_pixel_ratio": 0,
    "min_hash_similarity": 1,
}})
result = Canvas(160, 90).background(color="#123456").export("checked.pdf", policy=policy)
print(result.pixel_metrics.fidelity.verdict)
```

ReportLab と任意の PDFium 観測機能には `quickthumb[pdf]` をインストールします。通常の PDF 出力は PDFium をインポートしません。比較を要求すると、実際の PDF バイトを倍率 1 の透明 RGBA に描画します。この出力では、基準 1 ピクセルを PDF の 1 ポイントとし、96 DPI の印刷寸法変換は行いません。レポートには PDFium とバインディングのバージョン、実際のページ寸法（ポイント）、ページ数、描画寸法、基準環境を記録します。ネイティブ PDFium の文書・描画・後処理の呼び出しはスレッド間で直列化しますが、基準描画とピクセル比較はそのロックの外で行います。期待するポイント寸法の 1 ページだけが必要で、ピクセルの許容値が緩くてもページ・寸法が違えばポリシー外です。リサイズや白背景への合成で、アルファや形状の欠落を隠すことはありません。

前述と同じ可視 RGBA・ハッシュの基準と、報告専用の動作が適用されます。Canvas が予期せず複数ページになった場合、指標は最初のページを観測し、報告ページ数によってポリシー外となります。PDF 生成と要求した比較は出力先を開く前に終わるため、観測機能が欠けるか失敗しても既存ファイルを保持します。忠実度判定にかかわらず、ネイティブの文字・ベクターと、理由を示したラスター断片は残ります。ネイティブ PDF テキストは検索できるベクターですが、PowerPoint のような編集性を約束するものではありません。Deck PDF の比較は明示的に拒否します。Canvas の各スライドを個別に出力してください。この観測から PPTX やアニメーションの忠実度を判断することはできません。

## PPTX の互換性 { #pptx-compatibility }

PPTX は対応する文字と図形を編集可能なまま保存します。Glow は固定画像として編集可能な内容に添えられます。編集後に glow を更新するには再出力してください。縁取り付きの内容も、複数のオブジェクトを一緒に編集するか、再出力が必要な場合があります。

次のエフェクトの組み合わせでは、対象レイヤーを画像として出力します。

- stroke/glow を付けた半透明の文字、図形、枠線。
- stroke/glow を付けたグラデーション塗りの図形。
- glow 付きリッチテキスト、または glow と shadow の組み合わせ。
- 元の図形がスライド外にはみ出す shape glow。

不透明な線形グラデーションの文字では、編集可能な塗りと縁取りを保てます。半透明かどうかは各テキスト部分で実際に使う塗りだけで判断するため、未使用・上書き済みの色で編集性が失われることはありません。

出力前に `canvas.validate_export("pptx")`、出力後に結果の `capability_report` を確認すると、互換性の判断がわかります。編集可能な前景と固定エフェクトの混合は `support="partial"`、レイヤー全体の画像は `support="fallback"` です。結果レポートのフィールドは[文書レイヤーの振り分け](export-methods.md#document-layer-routing)を参照してください。

`ExportPolicy(pptx={"title": "native"})` は、ID が `title` のレイヤーでこれらのエフェクト画像や混合表現を拒否します。`ExportPolicy(unsupported_motion="error")` も同じエフェクト代替を拒否します。Canvas と Deck の `to_pptx(policy=...)` も、ファイル出力と同じポリシー検査を行います。既定では、理由を示した代替を許可します。

## HTML ブラウザー検証ハーネス { #html-browser-validation-harness }

開発者向けのハーネスは、明示的に選んだ Chrome と Node 組み込みの WebSocket を使い、実際に出力した Canvas と 2 枚の Deck のステージを撮影します。ブラウザーをインストールしたり、`ExportPolicy` を変更したりしません。

```bash
PYTHONPATH=. python scripts/check_html_fidelity.py \
  --chrome "/path/to/chrome" --output /tmp/quickthumb-html-observations
```

出力ディレクトリは新しいものが必要です。Chrome は一時プロファイルとループバック CDP でヘッドレス実行し、既存のブラウザーセッションには接続しません。フォント、画像、スライド遷移を待ち、元寸法のステージだけを DPR 1 で撮影して、クリック開始の実際の CSS フェードを 0、5、10 秒へシークします。レポートにはブラウザー・Node のバージョン、基準環境、入力アセットのハッシュ、実行した経路の診断、寸法、シーク位置、検証データの明示的な限界値、ピクセル・ハッシュ指標、判定を記録します。基準とブラウザーの PNG も隣に残ります。

文字・図形・画像・マスクを組み合わせた検証データでは、チャンネル差 16、異なるピクセル最大 8%、平均ハッシュ類似度 0.94 以上を許容します。各構成要素にも記録した領域基準を適用します。文字は差のあるピクセル 20% まででハッシュ類似度 0.95 以上、ネイティブ楕円は 2% までで 0.98 以上です。埋め込み画像は完全一致、マスク断片はチャンネル値 1 段階の丸めだけを許します。文字と楕円のチャンネル許容差は 16 です。この局所基準により、小さい要素の欠落がステージ全体の平均に埋もれるのを防ぎます。負の対照では、横長 Canvas と縦長 Deck の両方から文字・画像・マスク・楕円をそれぞれ取り除き、他の指標だけでなく該当領域で失敗することを求めます。許容値はこの検証データ専用で、一般の文書の基準ではありません。単純なフェードはチャンネル値 1 段階の丸めだけを許し、意図的に誤った文書は比較に失敗する必要があります。想定外の判定ではコマンドが失敗し、レポートは保持します。自動のラスター代替や、ブラウザー・CI のインストールは行いません。

観測するのは 1 つの Chrome・フォント・プラットフォーム環境と、範囲を限定した 1 つの CSS アニメーションです。すべてのブラウザー、アニメーション、キュー、Deck 遷移を保証するものではありません。CairoSVG ではこのブラウザー観測を代用できません。既存の Node ランタイムテストは、ブラウザーのピクセルとは別に、スケジュールと状態の動作を検査します。

## 静的な出力形式間の検査 { #static-cross-export-checks }

`tests/test_static_export_matrix.py` は、同じ作成内容を公開 Canvas/Deck ファイル出力 API に渡します。最初の 160×120 スライドは、リポジトリのフォントを使う文字、ネイティブ矩形、生成画像、楕円マスクを組み合わせます。Deck の 2 枚目は透明キャンバス上の半透明矩形です。見た目の測定と構造上の証拠を区別します。

| 形式 | Canvas | Deck | 機能・代替表現の証拠 |
| --- | --- | --- | --- |
| PNG | デコードした RGBA が基準サンプルと一致 | 番号付きの各スライドが基準サンプルと一致 | ラスター出力のみ。ネイティブオブジェクトや文書ビューアーの保証はありません |
| SVG | 実際の CairoSVG 観測と、ネイティブ文字・ベクター・PNG の検査 | 単一ファイルの Deck SVG は拒否し、各 Canvas を別に測定 | 実行したソース ID、ネイティブ経路、理由付きの画像・マスク PNG 経路 |
| HTML | ステージのマークアップ、ネイティブ文字・CSS、完全一致のマスク PNG | ステージ数とスライド内の経路 | 構造のみ。この検査でブラウザーピクセルは測定しません |
| PDF | 実際の PDFium 観測、検索可能な文字、ベクターパス、画像オブジェクト | ページ数・寸法、ネイティブオブジェクト、描画した要素の領域 | Canvas 経路を報告。Deck の実行経路と結果レポートの忠実度はまだ収集しません |
| PPTX | 編集可能な OOXML 文字・図形、正確な位置のマスク PNG | スライド数とスライドごとのネイティブ・ラスター要素 | 実行経路を報告。PowerPoint/Keynote での見た目は未測定です |

混合 SVG/PDF の検証データには、画像全体でチャンネル許容差ゼロ、異なるピクセル最大 8%、ハッシュ類似度 0.94 以上という明示的な限界を使います。これは検証データ固有のフォント・輪郭の許容値で、出力の既定値ではありません。ネイティブ文字は文字として存在する必要があり、小さい矩形、画像、マスク内部も完全一致が必要です。要素の欠落が画像全体の許容範囲に隠れることはできません。文字領域はハッシュ類似度 0.95 以上で、フォント輪郭のラスター化用にチャンネル差 16 を認めた後、異なるピクセルを最大 30% まで許します。白地に白文字を含む実際の Deck PDF は、文字オブジェクトや他の領域が正常でも、この領域検査に失敗する必要があります。透明矩形に限ってはアルファの完全一致を求め、レンダラーの乗算済みアルファ変換・逆変換の丸めにより、可視 RGB はチャンネルごとに最大 2 段階の差を許します。完全に隠れた RGB には既存の可視 RGBA 比較規則を使いますが、PNG は生 RGBA を完全に保持します。リサイズや、架空のマットへの合成は行いません。

`uv run --locked pytest tests/test_static_export_matrix.py --no-cov -q` を実行してください。既存の品質ワークフローは、SVG/PDF/PPTX extra とネイティブ Cairo を用意して `pytest tests/` からこのファイルを実行しています。任意の観測機能がないローカル環境では、依存関係の理由を示して該当ケースをスキップします。Pytest のケース ID は形式と文書種別を示します。各ケースの一時ディレクトリには、ソース JSON、基準 PNG、実際の出力、JSON 結果レポートを保持します。測定したレポートには、レンダラーのバージョン、基準環境、限界値、指標が入ります。失敗はプラットフォーム固有のスクリーンショットではなく、共通の検証データと名前付き形式検査から再現できます。

これは範囲を限定した静的な検査です。ブラウザー実行、PPTX ビューアーのピクセル・フォント・時間の保証、Deck PDF の忠実度ポリシーの追加は行いません。別の HTML ブラウザーハーネスやネイティブのプレゼンテーションビューアー観測には、それぞれの実行と環境の証拠が必要です。構造上の成功を、描画ピクセルの忠実度の判定として報告してはいけません。

## Lottie 基準プレイヤー { #lottie-reference-player }

検証範囲と既知の差異は[再生の検証](export-lottie.md#playback-verification)を参照してください。

```bash
uv sync --locked --extra lottie --dev
npm ci --prefix tests/fixtures/lottie/player --ignore-scripts --no-audit --no-fund
PYTHONPATH=. uv run --locked python scripts/check_lottie_fidelity.py \
  --chrome /path/to/chrome \
  --player tests/fixtures/lottie/player/node_modules/lottie-web/build/player/lottie.min.js \
  --output /tmp/quickthumb-lottie-observations
```

### Android native graphics の再実行

Web 検査の manifest と既存の JDK 21、Maven 3.9+ を使用します。Maven はテスト専用依存を取得します。

```bash
PYTHONPATH=. uv run --locked python scripts/check_lottie_android.py \
  --maven /path/to/mvn --java-home /path/to/jdk-21 \
  --cases /tmp/quickthumb-lottie-observations/cases.json \
  --output /tmp/quickthumb-android-observations
```
