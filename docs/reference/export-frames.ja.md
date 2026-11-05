---
description: quickthumb の画像シーケンスと描画品質のリファレンスです。
---

# 画像シーケンスと描画品質 { #image-sequences-and-render-quality }

[出力リファレンス](../exports.md) · [出力形式を選ぶ](../output-guide.md)

## 画像シーケンス { #image-sequences }

`Canvas.export_image_sequence()` と Deck の同名メソッドは、実際のアニメーションタイムラインを個別の PNG、JPEG、WebP ファイルと 1 つのマニフェストに保存します。出力先はまだ存在しない新しいパスとし、親ディレクトリは事前に用意してください。既定の形式は PNG です。

```python
from quickthumb import ImageSequenceOptions

options = ImageSequenceOptions(fps=24, hold=2, render_quality="high", workers=2)
result = canvas.export_image_sequence("overlay_frames", options=options)
canvas.export_image_sequence("review_frames", format="jpeg", quality=85, matte="white", options=options)
canvas.export_image_sequence("web_frames", format="webp", lossless=True, options=options)
print(result.frame_count, result.duration, result.manifest_path)
```

エンコード設定はメソッドのキーワード引数です。時間と合成を制御する `ImageSequenceOptions(fps=30, hold=3, workers=1, render_quality="standard")` とは別に指定します。

| 設定 | PNG | JPEG | WebP |
| --- | --- | --- | --- |
| `format`（大文字・小文字を区別しない） | `"png"`（既定） | `"jpeg"` | `"webp"` |
| `quality` | 指定不可 | 整数 1〜95、既定 90 | 非可逆出力の整数 1〜95、既定 80 |
| `matte` | 指定不可 | 不透明な色の文字列、既定は白 | 指定不可 |
| `lossless` | 指定不可 | 指定不可 | 真偽値、既定 `False` |

`lossless=True` と `quality` は併用できません。quality は非可逆圧縮の品質であり、可逆 WebP エンコーダーの処理量ではありません。型が無効、または設定の組み合わせが不適切な場合は、出力やステージングを作る前に失敗します。オプションモデルにあるのは `fps`（有限、0 より大きく 120 以下）、`hold`（有限の非負の秒数）、`workers`（厳密な整数 1〜8）、`render_quality`（`"standard"` または `"high"`）だけです。

PNG は隠れた RGB も含め、レンダラーの **8 ビットのストレートアルファ RGBA バイト列**をそのまま保持します。可逆 WebP も同じピクセルを隠れた RGB ごと保持します。JPEG は解決したマットにアルファを合成して RGB にエンコードします。JPEG と非可逆 WebP では色が変わることがあり、基準ピクセルとの完全一致は保証しません。WebP はアルファを保持しますが、完全に不透明なファイルでは冗長なアルファ面を省略し、画像読み込み時に RGB になる場合があります。マニフェストの論理的な `mode: "RGBA"` として扱うときは、RGBA に変換してください。作成した背景はどの形式でも残ります。奇数や 1 ピクセルの寸法でも、すべての行と列を保持します。サイズが違うスライドは最初の Canvas の全寸法に収め、エンコード前に透明な余白（JPEG ではマット色）を付けます。入力画像を ICC 正規化することはありません。出力では継承したプロファイルやメタデータを除去し、sRGB やカラープロファイルへの適合を表明しません。

ディレクトリには `000000.png`、`.jpg`、`.webp` から続くファイルと、コンパクトな `manifest.json` を 1 つ保存します。そこには `version: "1"`、`format: "image_sequence"`、文書の `kind`、`encoding: "png"|"jpeg"|"webp"`、相対的な `filename_pattern`（`%06d.png`、`%06d.jpg`、`%06d.webp`）、`start_index: 0` が記録されます。実際の `frame_count`、`fps`、`duration`、`width`、`height` は保存したファイルを表します。ピクセルフィールドは論理的なデコード形式です。PNG/WebP は `mode: "RGBA"` と `alpha: "straight"`、JPEG は `"RGB"` と `"none"`、`bit_depth` は 8 です。`lossless` は選んだエンコードを示し、解決済みの `quality` と `matte` は該当する場合に記録し、それ以外は `null` です。

`ImageSequenceResult` は `ImageSequenceManifest` に、絶対パスの `output_directory`、`manifest_path`、`capability_report` の診断を加えます。両モデルと `ImageSequenceOptions` は JSON の保存・復元と `model_json_schema()` に対応します。Canvas/Deck の文書フィールドやラスター形式の列挙値は増えません。フレームパスや時刻の増え続けるリストもありません。同一フレームは基準となるショットごとに一度エンコードし、ハードリンクではなく個別に編集できるファイルとして保存します。フレーム用メモリには上限がありますが、既存のシーン準備やワーカーのバッファーもメモリを使います。

時間の扱いはアニメーション出力と同じで、明示的なスライド時間、`advance_after`、ナレーションから求めた表示時間、遷移、Morph を含みます。累積的なフレーム割り当てにより、小数の保持時間が続いてもずれを防ぎます。短い静止スライドや hold がゼロのスライドにも最低 1 フレームを割り当てます。報告する時間は、実際に保存したファイルから求めた `frame_count / fps` に厳密に等しく、独立したタイムラインサンプラーの長さやサンプル数とは異なる場合があります。`validate_export("image_sequence")` と `inspect_motion(target="image_sequence")` は動画のモーション機能を使います。既存の strict/reduced-motion ポリシーと、親、Morph、字幕、ワーカーの制限が適用されます。

シーケンスは無音です。音声のエンコード、mux、音楽、音声サイドカーは作りません。ナレーションは従来のファイル検証と時間推定を使いますが、エンコーダーの音声入力 64 個の制限は受けません。画像だけのシーンに FFmpeg は不要です。ナレーションの長さを推定する場合は引き続き ffprobe、動画レイヤーには通常のプローブ・デコード要件が必要です。

すべてのフレームと `manifest.json` は、公開前にアトミックなステージングディレクトリへ描画します。出力先ディレクトリは存在してはいけません。すでに存在する場合は安全に失敗し、誤った上書きを防ぎます。

`examples/image_sequence_overlay.py` では、FFmpeg なしで PNG、白マットの JPEG、可逆 WebP のローワーサードシーケンスを作れます。実行するたび、3 つの出力ディレクトリすべてに新しいパスが必要です。

## 高品質なアニメーション合成 { #high-quality-animated-compositing }

`GifOptions(render_quality="high")` と `VideoOptions(render_quality="high")` は、2 倍のレイヤー合成サーフェスを使い、最後に一度 LANCZOS で縮小します。既定の `render_quality="standard"` は従来の出力を保ちます。この専用オプションは、JPEG/WebP の `render(..., quality=...)` とは別です。アニメーションのバイト列メソッドでも、キーワード専用引数 `render_quality="high"` を使えます。

```python
canvas.render("smooth.mp4", animation=VideoOptions(fps=30, render_quality="high"))
deck.render("smooth.gif", animation=GifOptions(fps=12, colors=64, render_quality="high"))
```

high モードは、元画像すべての拡大コピーを保持せず、準備済みレイヤーと時間差を付けた対象を大きなサーフェスへ直接フィルタリングします。回転・縮小した輪郭のなじみを改善しますが、寸法、時間、音声、GIF のパレット・サイズ設定、`workers` の意味は変わりません。フレームとキャッシュした背景プレートは 4 倍のピクセルを持つため、描画時間とメモリ消費が増えます。ワーカーごとに独自のバッファーもあるので、`workers` とともに全体のメモリが増える場合があります。

これは**レイヤー合成**のスーパーサンプリングであり、ソースのレイアウトを高解像度にするものではありません。フォント・アセットや背景依存のソースサーフェスは元のサイズで準備します。作成時の静的な回転もソースに焼き込まれています。字幕は縮小後に元の解像度で描画し、スライド遷移とキー付き Morph も従来の元解像度の経路を使います。high モードは準備済みソースにない細部を復元できず、ごく小さい文字が柔らかくなる場合があります。同条件のコスト測定と文字の比較は[ベンチマークガイド](https://github.com/sjquant/quickthumb/tree/main/benchmarks)を参照してください。

## アニメーションの並列描画 { #parallel-animated-rendering }

`GifOptions(workers=2)` と `VideoOptions(workers=2)` は、別プロセスによるフレーム描画を有効にします。アニメーションのバイト列メソッドにも、同じキーワード専用の `workers` 引数があります。値は厳密な整数 1〜8 で、既定は引き続き 1、CPU 数に応じた自動調整はありません。小さい出力や静的な出力では、プロセス起動、スライド準備、フレームコピーの負荷により、1 ワーカーの方が速い場合があります。エンコードと音声ミックスは引き続き親の出力処理で行います。

インポート可能なスクリプトと Python の main ガードを使ってください。Linux でも必ず `spawn` を使い、アプリケーション全体の開始方式は変更しません。メインモジュールをインポートできない対話環境では `workers=1` を使います。

```python
from quickthumb import Canvas, Fade, VideoOptions

def main():
    canvas = Canvas(640, 360).background(color="#123456")
    canvas.shape("rectangle", (40, 40), 200, 160, "#FF3355",
                 animation=Fade(duration=2))
    canvas.render("parallel.mp4", animation=VideoOptions(fps=30, workers=2))

if __name__ == "__main__":
    main()
```

ワーカーは独立したフォントと動画デコーダーを使い、組み込み Canvas を再構築します。処理待ちには上限付きの順序付きフレームジョブだけを置くため、既存のショット時間、まとめた静止区間、字幕境界、遷移順を保ちます。ローカルの動画レイヤー、字幕、seed 付き grain、組み込みモーションは並列で動きます。custom/plugin レイヤー、Canvas のサブクラス、リモート動画、seed がなく強度がゼロでない grain には `workers=1` が必要です。スライド準備で解決したリモート画像・フォントはワーカー用に固定します。出力中はローカルアセットとフォントキャッシュを変更しないでください。ソースまたはワーカーが失敗すると出力も失敗し、既存の出力先は保持します。

ワーカーを増やすとメモリも増えます。処理中の RGB フレームに加え、各ワーカーに Python ランタイム、フォント、準備したスライド画像、デコーダーキャッシュがあるためです。正常終了時もエラー時も、実行中のジョブの終了を待ってデコーダーを閉じます。失敗時には待機中のジョブを取り消し、異常終了したワーカーは描画エラーとして報告します。OS による強制終了では通常の後処理を実行できません。
