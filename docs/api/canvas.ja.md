---
description: quickthumbのCanvasの作成、縦横比、レイヤー構成、レンダリング、JSON読み込み、画像出力を説明します。
---

# Canvas { #canvas }

`Canvas`は寸法と順序付きレイヤー一覧を持つ最上位オブジェクトです。作成用フィールドは、Deckスライドや正規JSONにも共通する[レイヤー用語](index.md#shared-layer-vocabulary)に従います。

## 作成 { #creation }

### `Canvas(width=None, height=None)` { #canvaswidthnone-heightnone }

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720)
```

| パラメーター | 型 | 説明 |
| --- | --- | --- |
| `width` | `int \| None` | 幅（ピクセル）。正の整数です。 |
| `height` | `int \| None` | 高さ（ピクセル）。正の整数です。 |

幅と高さは両方指定するか、両方省きます。サイズ**なし**の`Canvas()`は*未設定サイズ*の状態です。レイヤーは追加できますが、直接サイズを与えるか、サイズ付きの[`Deck`](deck.md)へ追加して既定サイズを継承するまでは、描画、診断、シリアライズができません。`canvas.has_size`で区別できます。

### `Canvas.from_aspect_ratio(ratio, base_width)` { #canvasfrom_aspect_ratioratio-base_width }

縦横比の文字列と基準幅から作ります。高さは自動計算します。

```python
wide     = Canvas.from_aspect_ratio("16:9", base_width=1280)   # 1280×720
square   = Canvas.from_aspect_ratio("1:1",  base_width=1080)   # 1080×1080
vertical = Canvas.from_aspect_ratio("9:16", base_width=1080)   # 1080×1920
```

| パラメーター | 型 | 説明 |
| --- | --- | --- |
| `ratio` | `str` | `"16:9"`など`"W:H"`形式の縦横比です。 |
| `base_width` | `int` | 幅（ピクセル）です。 |

## レイヤービルダー { #layer-builders }

すべてのビルダーはキャンバスを変更して`self`を返すため、メソッドを連続して呼べます。

| メソッド | 説明 |
| --- | --- |
| `.background(...)` | キャンバス全体の背景を追加 |
| `.text(...)` | テキストを追加 |
| `.image(...)` | 重ねる画像を追加 |
| `.shape(...)` | 図形を追加 |
| `.path(...)` | 塗りや線のある[パス](path.md)を描画 |
| `.svg(...)` | 描画時にラスタライズするSVGを追加 |
| `.video(...)` | 動く構成へ[動画クリップ](video.md)を追加 |
| `.counter(...)` | [動く数字](#animated-counters)を追加 |
| `.group(...)` | 子を自動配置するグループを追加 |
| `.outline(...)` | キャンバスの枠線を追加 |
| `.chart(...)` | 型付き仕様から決定的な棒・折れ線グラフを追加 |
| `.qr_code(...)` | 正方形のQRコードを追加 |
| `.custom(fn)` | Pillowのコールバックレイヤーを追加 |

全パラメーターは[データの可視化](data-visualizations.md)や各レイヤーのページを参照してください。

### 数字のアニメーション {#animated-counters}

`.counter(from_, to, duration, ...)`で数字をテキストレイヤーとして動かせます。`position`、`size`、`color`など通常の文字オプションを渡します。

```python
from quickthumb import Canvas

canvas = Canvas(320, 180).background(color="#102030").counter(
    0, 100, 2, suffix="%", size=64, color="#FFFFFF", position=(40, 50)
)
canvas.render("counter.gif")
```

`delay`、`decimals`、`minimum_integer_digits`、`prefix`、`suffix`、`grouping`で時間と表示形式を制御します。`style`は`"plain"`、`"odometer"`、`"flip"`、`easing`は`"linear"`、`"ease_in"`、`"ease_out"`、`"ease_in_out"`です。静止出力は最終値を表示します。

## `.diagnose()` { #diagnose }

ファイルを保存せず、配置や読みやすさを検査します。`Diagnostic`を格納する`findings`付きの`DiagnosticReport`を返し、問題がなければリストは空です。

```python
for finding in canvas.diagnose().findings:
    print(finding.severity, finding.code, finding.message)
```

コードは`off-canvas`、`tiny-text`、`text-overflow`、`text-clipped`、`missing-glyph`、`low-contrast`、`layer-overlap`、`layer-hidden`、`edge-crowding`です。詳細と同等のCLIコマンド`quickthumb lint`（または`quickthumb diagnose`）は[診断とCLI](../diagnostics.md)を参照してください。

## `.prefetch_assets()`（任意） { #prefetch_assets-optional }

必ず呼ぶ必要はありません。`render()`と`export()`はリモート画像、SVG、文字の塗り、フォントを自分でダウンロードし、`export()`は`asset_manifest`も返します。長い出力の前に通信失敗や期限切れキャッシュを確認したい場合、または後のオフライン描画用にキャッシュを用意する場合だけ使ってください。描画せずマニフェストを返します。

```python
manifest = canvas.prefetch_assets().asset_manifest
if any(entry.status == "stale" for entry in manifest):
    ...  # decide whether to proceed with cached bytes
```

状態、`QUICKTHUMB_ASSET_MAX_AGE`、オフラインモードは[リモートアセットとキャッシュ](../reference/export-assets.md#remote-assets-and-caching)を参照してください。

## 出力メソッド { #export-methods }

### `.export(path, policy=None, *, format=None, quality=None, animation=None)` { #exportpath-policynone-formatnone-qualitynone-animationnone }

`render()`と同様に保存し、保存した1ファイルの`written_paths`を持つ`ExportResult`を返します。パスは文字列か`pathlib.Path`です。`format`、`quality`、`animation`、`policy`は`render()`と同じ意味です。

```python
result = canvas.export("card.png")
print(result.written_paths)
```

結果のフィールド、機能ポリシーの事前検査、`export()`と以下のメソッドとの関係は[推奨出力API](../reference/export-methods.md#recommended-output-api)を参照してください。

### `.render(path, format=None, quality=None, debug=False, animation=None, policy=None)` { #renderpath-formatnone-qualitynone-debugfalse-animationnone-policynone }

描画結果をファイルへ保存します。拡張子で形式を選び、`.svg`、`.pptx`、`.pdf`はベクター・文書、`.gif`、`.mp4`、`.webm`、`.mov`はレイヤーの`animation`を再生するアニメーションになります。[エクスポート](../exports.md)を参照してください。

Canvasの`.lot`は[Lottieベクター](../reference/export-lottie.md#lottie-vectors)に記載した限定範囲のネイティブベクターを保存します。fpsと最後の保持は`LottieOptions`で指定します。未対応の内容はPNGへ置き換えず、書き込み前に拒否します。

```python
from quickthumb import GifOptions, VideoOptions

canvas.render("output.png")
canvas.render("output.jpg", format="JPEG", quality=85)
canvas.render("output.webp", format="WEBP", quality=90)
canvas.render("debug.png", debug=True)  # raster output with public layer-id bboxes
canvas.render("output.svg")
canvas.render("output.pptx")  # requires quickthumb[pptx]
canvas.render("output.pdf")   # requires quickthumb[pdf]
canvas.render("output.gif")   # animated; .mp4/.webm/.mov require the ffmpeg binary
canvas.render(
    "preview.gif",
    animation=GifOptions(fps=8, max_size=(540, 960), colors=128),
)
canvas.render("preview.mp4", animation=VideoOptions(fps=30))
```

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `path` | `str` | — | 出力パスです。 |
| `format` | `str \| None` | `None` | 大文字小文字を区別しない`"PNG"`、`"JPEG"`、`"WEBP"`の再指定です。文書・アニメーション拡張子では拒否します。 |
| `quality` | `int \| None` | `None` | 圧縮品質。JPEGは1–95、WebPは1–100で、それ以外は拒否します。 |
| `debug` | `bool` | `False` | 視覚確認用に公開レイヤーIDの境界をラスター出力へ描きます。 |
| `animation` | `GifOptions \| VideoOptions \| LottieOptions \| None` | `None` | GIFは`GifOptions`、MP4/WebM/MOVは`VideoOptions`、`.lot`は`LottieOptions`です。 |
| `policy` | `ExportPolicy \| None` | `None` | 動画・HTML・PPTXの`reduced_motion`などのポリシーです。`render()`と`export()`は書き込み前に`unsupported_motion`を適用します。`export()`は明示的に要求した[静的SVG検証](../reference/export-validation.md#optional-static-svg-fidelity-report)も報告します。 |

!!! warning
    `format="PNG"`に`quality`を渡すと`RenderingError`になります。文書・アニメーション（`.svg`、`.pptx`、`.pdf`、`.html`、`.gif`、`.mp4`、`.webm`、`.mov`、`.lot`）に`debug=True`を渡しても`RenderingError`になります。

`GifOptions`、`VideoOptions`、`LottieOptions`は`quickthumb`から取得できます。`GifOptions`は`fps`、`hold`、`matte`、`loop`、`max_size=(width, height)`、`colors`を、`VideoOptions`は`fps`、`hold`、`matte`、`soundtrack=AudioTrack(...)`、`loop_audio`を受け付けます。

`VideoOptions(transparent=True)`はVP9 WebMとProRes 4444 MOVのアルファを維持します。厳密なブール型で既定は`False`です。他の出力はすべて拒否します。両方の`hold`は厳密な有限の非負数（既定3秒）で、既定値なら保存時に省略します。描画には`workers`（厳密な整数1–8、既定1）と`render_quality="standard"`または`"high"`を指定できます。spawnや対応入力は[並列描画](../reference/export-frames.md#parallel-animated-rendering)を参照してください。MP4/WebM/MOVはGIFのサイズ・パレット制御を拒否します。

### `.to_svg(embed_fonts=False)` { #to_svgembed_fontsfalse }

SVG文書の文字列を返します。`embed_fonts=True`で使用したフォントを`@font-face`のデータURLとして埋め込みます。

```python
svg = canvas.to_svg(embed_fonts=True)
```

### `.to_pptx()` { #to_pptx }

編集可能なテキストボックスとオートシェイプを持つ1枚のPowerPointをバイト列で返します。`pptx`追加機能が必要です。

```python
with open("deck.pptx", "wb") as f:
    f.write(canvas.to_pptx())
```

### `.to_pdf()` { #to_pdf }

1ページのPDFをバイト列で返します。背景と図形はネイティブベクターです。安全に埋め込めるフォントで複雑なシェーピングが不要なら、選択可能な文字も使います。未対応の文字はピクセル単位で一致する画像断片にします。`pdf`追加機能が必要です。

```python
with open("card.pdf", "wb") as f:
    f.write(canvas.to_pdf())
```

### `.to_gif(...)` / `.to_mp4(...)` / `.to_webm(...)` / `.to_mov(...)` { #to_gif-to_mp4-to_webm-to_mov }

レイヤーの`animation`を順に再生し、最後の静止状態を`hold`秒保つアニメーションを返します。[GIFと動画](../reference/export-animation.md#animated-gif-video)を参照してください。アニメーションがなければ1フレームのGIFです。`.to_mp4()`、`.to_webm()`、`.to_mov()`には`PATH`上か`QUICKTHUMB_FFMPEG`で指定した`ffmpeg`が必要です。

```python
gif_bytes = canvas.to_gif(fps=20, hold=3.0, loop=0, matte="#000000")
mp4_bytes = canvas.to_mp4(fps=30, hold=2.0, soundtrack="music.mp3")
webm_bytes = canvas.to_webm(fps=30, hold=2.0)
overlay_bytes = canvas.to_webm(fps=30, hold=2.0, transparent=True)
```

`.to_mp4()`/`.to_webm()`/`.to_mov()`は、動画の長さに切って多重化する音声ファイル`soundtrack`と、明示的な再指定`loop_audio`も受け付けます。`AudioTrack(..., loop=True)`は短いトラックを繰り返します。従来の文字列パスは以前のループ既定値を維持します。GIFに音声は含められません。全パラメーターは[Deck API](deck.md)を参照してください。

全アニメーションバイトメソッドはキーワード専用の`workers=1`、`render_quality="standard"`を受け付けます。`"high"`はスーパーサンプリングを有効にします。`.to_gif()`は比率を保つ`max_size=None`と、パレットの`colors=None`（指定時2–256）も受け付けます。既存の位置引数は変わりません。

`.to_webm()`と`.to_mov()`のキーワード専用`transparent`は出力マットだけを省き、作成した背景は残ります。コーデック、アルファのデコード、切り替えは[透過WebM](../reference/export-transparency.md#transparent-webm)を参照してください。

`.to_mov()`は`.to_webm()`と同じパラメーターと時間で、ProRes 4444映像とAAC音声に固定されます。奇数や1ピクセルの寸法も保ちます。RGBAソースは8ビットです。16ビットのアルファ符号化はデコード後の8ビット値に1段階の差を生むことがあり、色は損失のある4:4:4 YUVです。測定した変換の限界とエンコーダー要件は[ProRes MOV](../reference/export-transparency.md#prores-4444-mov)を参照してください。`render()`と`export()`は不透明・透明の両方で`VideoOptions`と`.mov`を受け付けます。

### `.export_image_sequence(output_directory, *, format="png", quality=None, matte=None, lossless=None, options=None, policy=None)` { #export_image_sequenceoutput_directory-formatpng-qualitynone-mattenone-losslessnone-optionsnone-policynone }

既存の親の下に新しいディレクトリを作り、アニメーションを独立したPNG（既定）、JPEG、WebPと`manifest.json`で保存します。`ImageSequenceOptions(fps=30, hold=3, workers=1, render_quality="standard")`が時間と合成を、メソッドのキーワードが画像符号化を選びます。JPEGは不透明マット（既定白）のRGBで、`quality=1..95`です。WebPはアルファを保ち`lossless=True`に対応し、損失WebPは品質指定に対応します。PNGと無損失WebPはレンダラーのRGBA8を正確に保ちます。不透明なWebPがRGBで開かれる場合もあり、マニフェストのモードは論理的なRGBAデコードを説明します。結果には実際のフレーム数、時間、符号化、保存先を報告します。検証、形式別メタデータ、上書きしないアトミックな公開は[画像シーケンス](../reference/export-frames.md#image-sequences)を参照してください。

### `.to_base64(format="PNG", quality=None)` { #to_base64formatpng-qualitynone }

描画画像をbase64文字列で返します。

```python
b64 = canvas.to_base64(format="PNG")
b64 = canvas.to_base64(format="WEBP", quality=90)
```

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `format` | `str` | `"PNG"` | `"PNG"`、`"JPEG"`、`"WEBP"`です。 |
| `quality` | `int \| None` | `None` | JPEGは1–95、WebPは1–100の圧縮品質です。 |

### `.to_data_url(format="PNG", quality=None)` { #to_data_urlformatpng-qualitynone }

描画画像をデータURL（`data:<mime>;base64,...`）で返します。

```python
url = canvas.to_data_url(format="JPEG", quality=90)
# → "data:image/jpeg;base64,..."
```

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `format` | `str` | `"PNG"` | `"PNG"`、`"JPEG"`、`"WEBP"`です。 |
| `quality` | `int \| None` | `None` | JPEGは1–95、WebPは1–100の圧縮品質です。 |

### `.inspect()` { #inspect }

レイヤーID、順序、可視性、境界、作成時の文字配置情報を持つ決定的な`CanvasInspection`を返します。ファイルは出力しません。寸法のために既存のフォントや画像を読む場合がありますが、親レイヤーの描画は呼び出しません。

```python
report = canvas.inspect()
for layer in report.layers:
    print(layer.id, layer.bbox)
```

親子関係のあるシーンの境界は、アニメーションフレームではなく作成時の静的レイアウトです。描画ピクセルより広い保守的な境界になる場合があります。`canvas.render("debug.png", debug=True)`で表示できます。クリップ、マスク、カウンター、親変換は[複雑なレイアウトの検査](../reference/inspection-details.md)を参照してください。

### `.to_json()` { #to_json }

キャンバスをJSON文字列にします。

```python
json_str = canvas.to_json()
```

`.custom(fn)`があれば、コールバックを保存できないため`ValidationError`になります。

### `Canvas.from_json(json_str)` { #canvasfrom_jsonjson_str }

JSON文字列からキャンバスを復元します。

```python
canvas = Canvas.from_json(json_str)
```

!!! note
    `from_json()`はdictではなく**JSON文字列**を受け付けます。dictなら先に`json.dumps(data)`を使ってください。

## `.custom(fn)` { #customfn }

Pillowの`Image`を受け取り返すコールバックを追加します。

```python
from PIL import ImageDraw
from quickthumb import Canvas

def draw_badge(image):
    d = ImageDraw.Draw(image)
    d.polygon([(70, 70), (240, 70), (155, 180)], fill="#FF3B30")
    return image

canvas = Canvas(512, 512).custom(draw_badge)
```

| 規則 | 詳細 |
| --- | --- |
| `fn`は呼び出し可能 | `PIL.Image.Image`を受け取ります。 |
| 戻り値 | 変更した同じ画像、同じサイズの新しい画像、`None`を返せます。 |
| エラー | コールバックの例外は`RenderingError`で包みます。 |
| 保存 | カスタムレイヤーはJSONに保存**できません**。 |
