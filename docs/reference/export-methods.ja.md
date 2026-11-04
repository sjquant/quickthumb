---
description: quickthumb の出力メソッドと結果レポートのリファレンスです。
---

# 出力メソッドと結果レポート { #export-methods-and-receipts }

[出力リファレンス](../exports.md) · [出力形式を選ぶ](../output-guide.md)

## 推奨する出力 API { #recommended-output-api }

`export()` で Canvas や Deck を保存すると、`ExportResult` が返ります。`written_paths`、機能・代替表現の診断、ピクセル・時間のメタデータ、アセット、観測した描画環境を含みます。形式は拡張子で選びます。MP4、WebM、MOV、GIF はアニメーションタイムラインを再生し、Deck の動画ではスライドごとのナレーションもミックスします。

```python
from quickthumb import VideoOptions

result = deck.export("slides.mp4", animation=VideoOptions(hold=2, render_quality="high"))
print(result.written_paths, result.fallback_diagnostics)
deck.export("slides.html")  # interactive slideshow with click-triggered motion
canvas.export("card.webp", quality=85)  # JPEG/WebP compression quality
```

| 目的 | 使用する API |
| --- | --- |
| 機能ポリシーを適用してファイルを書き、結果レポートを取得 | `export(path, ...)` |
| デバッグ用のボックスを描く、または低レベルのファイルレンダラーを使う | `render(path, ...)` |
| バイト列またはメモリ上の文書を取得 | `to_mp4()`、`to_gif()`、`to_html()` など |
| ナレーション付き Deck を出力 | `export(path, animation=VideoOptions(hold=3))` / `to_mp4(hold=3)` |
| 無音のアニメーションフレームとマニフェストを保存 | `export_image_sequence(directory, options=...)` |
| 対応範囲を限定した Canvas 専用 Lottie ベクターを保存 | `canvas.export("scene.lot", animation=LottieOptions(fps=30, hold=3))`。[Lottie ベクター](export-lottie.md#lottie-vectors)を参照 |

アニメーションのバイト列メソッドとオプションはすべて、最終状態の保持秒数に `hold` を使います。`render_quality="standard"` または `"high"` はアニメーション合成を制御し、`export()`/`render()` の `quality` は圧縮品質です。JPEG は整数 1〜95、WebP は 1〜100 を受け付けます。高度な spawn による並列描画が必要でなければ `workers=1` のまま使ってください。任意の[時間方向の露光](../timing.md#temporal-exposure)で Canvas 出力にモーションブラーを付けられます。`export()` と `render()` はともに、書き込み前に `unsupported_motion="error"` などのファイル機能ポリシーを適用します。`export()` はさらに結果レポートを返します。バイト列メソッドは出力先ごとの設定を提供しますが、共通のファイル結果レポートはありません。Deck のラスター出力は番号付きファイルなので、返された `written_paths` を使ってください。画像シーケンスは新しいディレクトリを出力先とするため、別の API です。

## 形式とオプションの選択 { #format-and-option-selection }

Canvas と Deck の選択規則は同じですが、`.lot` だけは Canvas 専用で、Deck は Lottie 出力を拒否します。

| 入力 | 結果 |
| --- | --- |
| 拡張子だけで `format` なし | 拡張子から形式を選びます。`.jpg`/`.jpeg` は `output_format="jpeg"`、`.htm`/`.html` は `"html"` と報告します。 |
| `format="PNG"`、`"JPEG"`、`"WEBP"`（大文字・小文字を区別しない） | ラスター拡張子、不明な拡張子、拡張子なしの名前に対しラスターエンコードを選びます。ファイル名は指定どおりで、形式に合わせて変更しません。 |
| 文書・アニメーションの拡張子にラスターの `format` | SVG、PDF、HTML、PPTX、動画、`.lot` の名前に画像バイトを書かず、拒否します。 |
| `quality` | JPEG は整数 1〜95、WebP は整数 1〜100。他の対象では拒否します。 |
| `animation` | GIF は `GifOptions`、MP4/WebM/MOV は `VideoOptions`、Canvas の `.lot` は `LottieOptions`。その他の静的・文書形式では拒否します。 |

形式選択、圧縮品質、アニメーションのオプション分類の競合は、アセットの読み込みやファイル書き込み前に拒否します。コーデック固有の制限は出力準備時に検証します。その後に描画・エンコードが失敗する場合はあります。通常のファイル出力は、複数ファイルを一括更新するアトミックなトランザクションではありません。Canvas や番号付き Deck の名前を推測せず、`written_paths` を確認してください。Deck を単一の SVG にはできないため、Canvas の各スライドを個別に出力します。新しいディレクトリとエンコードオプションの別契約は、[画像シーケンス](export-frames.md#image-sequences)を参照してください。

## 文書レイヤーの振り分け { #document-layer-routing }

Canvas/Deck の HTML/PPTX と Canvas の SVG/PDF 出力は、実際に実行したレイヤーの経路を、`feature="layer_representation"` として `result.capability_report` に報告します。ネイティブ HTML/CSS、SVG/PDF の基本要素、編集可能な PowerPoint オブジェクト、元の埋め込み SVG は `support="native"` です。出力した PNG 断片は `support="fallback"` と `fallback="rasterize"` になります。PPTX の編集可能な前景と固定 glow 画像の混合は `support="partial"` と `fallback="rasterize"` です。前景を編集した後にエフェクトを更新するには再出力してください。これは表現方式の観測であり、ピクセルの忠実度測定ではありません。

`result.fallback_diagnostics` は、対象の検査用 `layer_id` と理由を示します。保持したグループには子孫の ID を `layer_ids` に含めます。背景に依存する共有の前方合成には単独の `layer_id` がなく、関係する全ソースを `layer_ids` に列挙します。これらは合成したピクセルで見た目が決まるため、まとめて報告します。フラット化した自動レイアウトの子も、元の検査 ID を保持します。空のラスター断片と空の文字は、要素も表現の観測結果も作りません。

実行経路の `native_attempt=True` は、ネイティブ内容の出力、またはラスター代替になったネイティブ候補の実行・検証を含みます。実際に採用した表現は `support` と `fallback` で確認します。`False` はネイティブ生成・検証の前にラスターキャプチャを選んだという意味です。機能照会だけの診断では不明（`None`）のままの場合があります。親子シーンは SVG/PDF/PPTX では静的な合成を報告し、HTML では焼き込み済みアフィン CSS モーションを持つ PNG ソースも報告できます。既存のモーション機能診断とは別です。SVG/PDF の観測は作成時の静的出力を示します。PDF テキストは対応する場合にフォントを埋め込みますが、文字整形、グリフの収録範囲、埋め込み制約によって、理由付きのラスター断片を選ぶ場合があります。

Deck の実行観測には、ゼロ始まりの `slide_index` も付きます。レイヤー ID は `deck.inspect().slides[index]` と同じくスライド内で有効なので、スライド間で重複する ID は両フィールドで区別してください。Canvas の観測では `slide_index` を省略します。Deck HTML の対話型キュー、遷移、ノートは残ります。この表現記録によって、クリック式のスライドショーが固定時間の再生に変わることはありません。

たとえば `ExportPolicy(unsupported_motion="error")` は、静的なマスク付き図形を拒否しません。HTML のこの経路は PNG 断片でマスクを保ち、その判断を報告します。レイヤー選択ポリシーは追加しません。実行経路レポートの対象は Canvas SVG/PDF と Canvas/Deck HTML/PPTX で、Deck PDF はまだ収集しません。忠実度の指標は文書全体を記述し、個々の代替レイヤーには割り当てません。HTML の出力先を開く前に全スライドを描画するため、後続スライドの未対応機能や strict モーションの拒否でも既存ファイルを保持します。

PPTX の経路は実際の OOXML 表現です。ネイティブのテキストボックスやオートシェイプは編集可能なオブジェクトとして残り、PNG 断片はラスター内容と配置を保持しますが、文字・ベクター単位の編集性を失います。ラスター化の理由にはマスク、背景合成、画像・放射状の文字塗り、未対応のフォントの意味付けなどがあります。Canvas ではスライド番号を省略し、Deck では識別します。PPTX ファイル出力は出力先を開く前にプレゼンテーション全体を構築するため、後続ソースの描画失敗でも既存ファイルを保持します。

この構造的な観測は、特定の PowerPoint/Keynote ビューアーでのピクセル一致、フォントの利用可否、アニメーション時間、透明度を保証しません。PPTX 忠実度ポリシーや自動アプリケーションレンダラーはありません。PPTX の寸法はソース 1 ピクセルを 9,525 EMU（1 インチ 96 ピクセル）、つまり PDF の 0.75 ポイントとして扱います。後で PDF 経由のビューアー比較をする場合、PDF 出力の 1 ピクセル＝1 ポイントを仮定せず、実際のページ寸法から倍率を求めてください。

## 出力呼び出しの移行 { #migrating-output-calls }

- `Deck.to_mp4()` は Canvas やファイル出力と同じくアニメーションを再生します。旧 `to_animated_mp4()` と `to_narrated_mp4()` を `to_mp4()` に置き換えてください。
- `render_mp4()` と `render_narrated_mp4()` は `export("deck.mp4")` に置き換えます。別の静止スライド用エンコーダーは削除され、別名はありません。静止シーンを保つには静的 Canvas と `Cut()` を使いますが、既存のアニメーション Deck を凍結したり、同じエンコード結果を保証したりはしません。
- `export_png_sequence()` は `export_image_sequence()` に置き換わりました。公開のオプション・マニフェスト・結果モデルは `ImageSequence*` となり、旧別名はありません。
- アニメーション Deck の `slide_duration=` とナレーションの `default_duration=` は `hold=` に置き換えます。アニメーションの `quality=` は `render_quality=` にします。保存済みの GifOptions、VideoOptions、ImageSequenceOptions JSON も対象です。別名はありません。

## 出力の仕組み { #how-export-works }

SVG、PDF、PPTX は対応するレイヤーを**ネイティブ**に保ち、ネイティブ表現がない部分に基準 PNG 断片を使います。位置、折り返し、整列の計算はラスターレンダラーと共通です。HTML も同じネイティブ・ラスター併用方式です。[HTML](export-documents.md#html)を参照してください。

一方 [Lottie](export-lottie.md#lottie-vectors) は、範囲を限定したネイティブベクターだけを受け付け、未対応の内容は書き込み前に拒否します。PNG フレームには置き換えません。

| レイヤー | SVG | PPTX | PDF |
| --- | --- | --- | --- |
| 背景色・グラデーション | ネイティブ `rect` と gradient 定義 | ネイティブ図形の塗り（線形はネイティブ、放射状は埋め込み） | ネイティブの塗り。不透明グラデーションはネイティブ、半透明は埋め込み |
| 枠線 | ネイティブ `rect` の線 | ネイティブの枠付き矩形 | ネイティブ矩形の線 |
| 図形（すべての基本形） | 回転・stroke/shadow/glow を含むネイティブ要素 | ネイティブのオートシェイプ。多角形はフリーフォーム | 回転を含むネイティブパス。エフェクト付きは埋め込み |
| テキスト（単純・リッチ） | 折り返し、字間、グラデーション、エフェクトを含む、行・run ごとのネイティブ `<text>` | run ごとに装飾した編集可能なテキストボックス | フォントを埋め込め、複雑な整形が不要なら選択可能なネイティブ文字。未対応フォント、グラデーション・画像塗り、ぼかしはピクセルとして埋め込み |
| グループ（自動レイアウト） | レイアウト位置に子をネイティブ出力 | 同左 | 同左 |
| 画像・画像で塗った文字 | PNG 断片の埋め込み | 画像の埋め込み | 画像の埋め込み |
| SVG レイヤー | ベクターの data URL として埋め込み。エフェクト付きはラスター | 画像の埋め込み | 画像の埋め込み |
| ブレンドモード・custom レイヤー | 最後の blend/custom レイヤー以下を 1 枚の PNG に統合 | 同左 | 同左 |

## Deck（複数の画像とスライド） { #decks-multiple-images-and-slides }

`Deck` は Canvas の順序付きリストです。各スライドは完全な `Canvas` で、単独の場合と同じように描画します。全メソッドは [Deck API リファレンス](../api/deck.md)を参照してください。

Deck のサイズを一度指定すれば、各スライドは引数なしの `Canvas()` でそれを継承できます。

```python
from quickthumb import AudioTrack, Canvas, Deck, VideoOptions

deck = (
    Deck(1280, 720)   # default slide size; Deck.from_aspect_ratio("16:9", 1280) also works
    .slide(Canvas().background(color="#101820").text(content="Cover", size=96, color="#FFFFFF"))
    .slide(Canvas().background(color="#1A1A2E").text(content="Body", size=64, color="#FFFFFF"))
)
# pre-built canvases work too: Deck(slides=[cover, body])

deck.render("deck.pdf")     # one multi-page PDF (a page per slide)
deck.render("deck.pptx")    # one multi-slide PPTX (a slide per slide)
deck.render("deck.gif")     # one animation playing transitions between slides
deck.export("deck.mp4")     # animated slides with per-slide narration
deck.render(
    "deck.mp4",
    animation=VideoOptions(soundtrack=AudioTrack(path="music.mp3", loop=True)),
)  # animated + mixed audio
deck.render("animated.mp4", animation=VideoOptions(fps=20))  # animated, silent
deck.render("slides.png")   # numbered sequence: slides_01.png, slides_02.png, …

pdf_bytes = deck.to_pdf()
pptx_bytes = deck.to_pptx()
gif_bytes = deck.to_gif()
webm_bytes = deck.to_webm()
mp4_bytes = deck.to_mp4()   # timeline with per-slide narration
```

`render()` は拡張子で処理を選びます。`.pdf` と `.pptx` は 1 つの文書、`.gif`、`.mp4`、`.webm`、`.mov` はアニメーションになります。ラスター形式には複数ページのネイティブコンテナーがないため、ゼロ埋め番号付きでスライドごとにファイルを保存し、パスを返します。

スライドの寸法は異なっても構いません。`deck.diagnose()` は各スライドの[診断](../diagnostics.md)を `slide_index` 付きでまとめ、寸法が違えば `mixed-slide-size` 警告を追加します。PDF は各ページをそのスライドの寸法にしますが、PPTX のプレゼンテーションサイズは最初のスライドで決まるため、それより大きいスライドは PowerPoint で切り取られます。`.pptx` ではサイズを揃えてください。Deck は `deck.to_json()` / `Deck.from_json(...)` で JSON 保存・復元でき、Canvas ごとのシリアライズを再利用します。

## CLI { #cli }

CLI も出力拡張子で形式を選びます。

```bash
quickthumb render spec.json -o card.svg
quickthumb render spec.json -o card.pptx
quickthumb render spec.json -o card.pdf

# Live HTML slides; open /?presenter for the presenter dashboard
quickthumb serve slides.py
```
