---
description: Canvasをまとめ、複数ページのPDF、PPTX、HTMLスライドショー、動画、番号付き画像へ出力するquickthumbのDeckを説明します。
---

# Deck { #deck }

`Deck`は順序付きの`Canvas`スライドの集まりです。各スライドは単独とまったく同じように描画し、同じパイプラインで複数形式への出力を追加します。Canvasの[レイヤー用語とシーン内ID](index.md#shared-layer-vocabulary)も維持します。

## 作成 { #creation }

### `Deck(width=None, height=None, slides=None, theme=None)` { #deckwidthnone-heightnone-slidesnone-themenone }

```python
from quickthumb import Canvas, Deck

deck = Deck()                          # empty, no default size
deck = Deck(1280, 720)                 # default slide size for unsized slides
deck = Deck(slides=[cover, body])      # from pre-built canvases
```

| パラメーター | 型 | 説明 |
| --- | --- | --- |
| `width` | `int \| None` | スライドの既定幅。`height`と一緒に指定するか、両方省きます。 |
| `height` | `int \| None` | スライドの既定高さです。 |
| `slides` | `list[Canvas] \| None` | 順序付きの初期スライド。各要素は`Canvas`です。 |
| `theme` | `dict \| None` | 全スライドの`$theme.*`参照で共有するトークングループです。スライド側のテーマが優先されます。`to_json()`/`from_json()`で維持します。 |

### `Deck.from_aspect_ratio(ratio, base_width)` { #deckfrom_aspect_ratioratio-base_width }

`Canvas.from_aspect_ratio`と同様に、縦横比から既定のスライドサイズを決めます。

```python
deck = Deck.from_aspect_ratio("16:9", 1280)   # default 1280×720
```

## スライドを追加する { #adding-slides }

コンストラクターの`Deck(slides=[...])`へ初期スライドを渡すか、`.slide(canvas, transition=None, *, audio=None, duration=None, notes=None)`で1枚ずつ追加します。両方も使えます。Deckを変更して`self`を返すので連続呼び出しが可能です。Deckに既定サイズがあれば、**サイズ未設定**の`Canvas()`はそれを継承します。明示サイズのCanvasは元の寸法を保ち、異なる場合は`mixed-slide-size`警告になります。

| メソッド | 説明 |
| --- | --- |
| `.slide(canvas, transition=None, *, audio=None, duration=None, notes=None)` | `Canvas`を1枚追加します。音声と長さは任意のナレーション設定、ノートはHTML発表者モードだけに表示します。 |

```python
deck = (
    Deck(1280, 720)
    .slide(
        Canvas().background(color="#101820").text(content="Cover", size=96, color="#FFFFFF"),
        audio="voice.wav",
        duration=2.5,
        notes="Introduce the central thesis.",
    )
    .slide(Canvas().background(color="#1A1A2E").text(content="Body", size=64, color="#FFFFFF"))
)
```

既定サイズのないDeckへサイズ未設定Canvasを追加すると`ValidationError`になります。DeckかCanvasにサイズを与えてください。

Deckはシーケンスでもあり、`len(deck)`、`deck[i]`、スライドの反復が使えます。`deck.slides`と`deck.notes`は対応するスライド・ノート一覧のコピーを返し、返されたリストを変えてもDeckは変わりません。

## 出力メソッド { #export-methods }

### `.export(path, policy=None, *, format=None, quality=None, animation=None)` { #exportpath-policynone-formatnone-qualitynone-animationnone }

`render()`のように保存し、`ExportResult`を返します。`written_paths`には、ラスターなら番号付きスライドファイル、ほかはPDF、PPTX、HTML、アニメーションの1ファイルを格納します。パスは文字列か`pathlib.Path`です。`format`、`quality`、`animation`、`policy`は`render()`と同じです。

```python
result = deck.export("slides.png")
print(result.written_paths)
```

結果、機能の事前検査、`export()`と以下のメソッドとの関係は[推奨出力API](../reference/export-methods.md#recommended-output-api)を参照してください。

### `.render(path, format=None, quality=None, animation=None, policy=None)` { #renderpath-formatnone-qualitynone-animationnone-policynone }

拡張子に応じて描画し、保存したパスのリストを返します。

```python
from quickthumb import GifOptions, VideoOptions

deck.render("deck.pdf")      # one multi-page PDF (a page per slide)
deck.render("deck.pptx")     # one multi-slide PPTX (a slide per slide)
deck.render("deck.gif")      # one animation playing transitions between slides
deck.render(
    "preview.gif",
    animation=GifOptions(fps=8, max_size=(540, 960), colors=128),
)
deck.render("deck.html")     # one self-contained HTML slideshow
deck.render("slides.png")    # slides_01.png, slides_02.png, …
deck.render("slides.jpg", quality=85)
```

| 拡張子 | 動作 |
| --- | --- |
| `.pdf` | 複数ページのPDF1つ。`pdf`追加機能が必要です。 |
| `.pptx` | 複数スライドのPPTX1つ。`pptx`追加機能が必要です。 |
| `.gif` / `.webm` / `.mov` | 既定設定でレイヤーと切り替えを再生するアニメーション1つ。WebM/MOVには`ffmpeg`が必要で、MOVは`prores_ks`を使います。 |
| `.mp4` | 任意のスライド別ナレーションを持つアニメーション。H.264/yuv420p映像とAAC音声です。`ffmpeg`と、ナレーションには`ffprobe`が必要です。静止スライドには静的Canvasと`Cut()`を使います。 |
| `.html` / `.htm` | 自己完結した動くHTMLスライドショー1つです。 |
| `.png` / `.jpg` / `.jpeg` / `.webp` | 0埋め番号付きでスライドごとに保存します。 |

| パラメーター | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `path` | `str` | — | 保存先。ラスターは`<stem>_NN<ext>`になります。 |
| `format` | `str \| None` | `None` | 大文字小文字を区別しない`"PNG"`、`"JPEG"`、`"WEBP"`の再指定。文書・アニメーション拡張子では拒否します。 |
| `quality` | `int \| None` | `None` | JPEGは1–95、WebPは1–100の圧縮品質。それ以外は拒否します。 |
| `animation` | `GifOptions \| VideoOptions \| None` | `None` | GIFは`GifOptions`、MP4/WebM/MOVは`VideoOptions`です。 |
| `policy` | `ExportPolicy \| None` | `None` | 動画・HTML・PPTXの`reduced_motion`などのポリシーです。`render()`と`export()`は書き込み前に`unsupported_motion`を適用します。 |

!!! warning
    `.pdf`、`.pptx`、アニメーションに`quality`を指定すると`RenderingError`になります。空のDeckの描画も同じです。

`GifOptions`と`VideoOptions`は`quickthumb`から取得できます。`GifOptions`はGIFのfps、`hold`、ループ回数、マット、比率を保つ`max_size`、パレット`colors`を、`VideoOptions`はMP4/WebM/MOVのfps、`hold`、マット、サウンドトラック、音声ループを制御します。音楽は`AudioTrack(path="music.mp3", loop=True)`として渡します。

`VideoOptions(transparent=True)`はVP9 WebMとProRes 4444 MOVでアルファを保ちます。厳密なブール型で既定は`False`です。他の出力はすべて拒否します。両方の`hold`は厳密な有限の非負数（既定3秒）で、既定値なら保存時に省略します。`workers`は厳密な整数1–8（既定1）、`render_quality="standard"`または`"high"`を指定できます。spawnと対応入力は[並列描画](../reference/export-frames.md#parallel-animated-rendering)を参照してください。別のアニメーション形式の専用オプションは拒否します。

### `.to_html()` { #to_html }

自己完結したスライドショー文書を返します。通常の観客画面はクリック、Space、矢印キーで操作できます。`quickthumb serve`で`?presenter`を付けて開くと、現在・次のスライド、発表者ノート、一時停止・再開・リセットのタイマー、同期した観客操作が加わります。

```python
html = deck.to_html()
deck.render("slides.html")
```

開発中は`quickthumb serve slides.py`を使えます。Pythonソースはモジュール変数`deck`、`slides`、`canvas`でDeckを公開します。

### `.to_pdf()` / `.to_pptx()` { #to_pdf-to_pptx }

Canvasごとに1ページ・1スライドの文書バイト列を返します。

```python
with open("deck.pdf", "wb") as f:
    f.write(deck.to_pdf())   # requires quickthumb[pdf]
pptx_bytes = deck.to_pptx()  # requires quickthumb[pptx]
```

### `.to_gif(...)` / `.to_webm(...)` / `.to_mov(...)` { #to_gif-to_webm-to_mov }

各スライドのレイヤーを動かし、最後の状態を保持するアニメーションを返します。トランジションはそのスライドへ入る変化です。時間の仕組みは[GIFと動画](../reference/export-animation.md#animated-gif-video)を参照してください。`.to_webm()`と`.to_mov()`には`PATH`上か`QUICKTHUMB_FFMPEG`で指定した`ffmpeg`が必要です。

```python
gif_bytes = deck.to_gif(fps=20, hold=3.0, loop=0, matte="#000000")
webm_bytes = deck.to_webm(fps=30, hold=3.0)
overlay_bytes = deck.to_webm(fps=30, hold=3.0, transparent=True)
```

全アニメーションバイトメソッドはキーワード専用の`workers=1`と`render_quality="standard"`を受け付けます。`"high"`はスーパーサンプリングです。`.to_gif()`は比率を保つ`max_size=None`、パレットの`colors=None`（指定時2–256）も受け付けます。既存の位置引数は変わりません。

これらは`.to_mp4()`でも使えます。静止ナレーションには静的Canvasと`Cut()`を使います。ファイルオプションとバイトメソッドはどちらも`hold`を使います。ナレーションも明示的な長さもないスライドがある場合、動画には正の既定保持時間が必要です。Deck GIFと無音の画像シーケンスでは0も有効です。Deck GIFはスライドごとのナレーションと明示長を無視します。

`.to_webm()`と`.to_mov()`のキーワード専用`transparent`は出力マットだけを省き、作成した背景は残ります。コーデック、アルファのデコード、切り替えは[透過WebM](../reference/export-transparency.md#transparent-webm)を参照してください。

`.to_mov()`は`.to_webm()`と同じパラメーターと時間で、ProRes 4444映像とAAC音声に固定されます。奇数や1ピクセルの寸法も保ちます。RGBAソースは8ビットです。16ビットのアルファ符号化はデコード後の8ビット値に1段階の差を生むことがあり、色は損失のある4:4:4 YUVです。変換の限界と要件は[ProRes MOV](../reference/export-transparency.md#prores-4444-mov)を参照してください。`render()`と`export()`は不透明・透明の両方で`VideoOptions`と`.mov`を受け付けます。

### `.export_image_sequence(output_directory, *, format="png", quality=None, matte=None, lossless=None, options=None, policy=None)` { #export_image_sequenceoutput_directory-formatpng-qualitynone-mattenone-losslessnone-optionsnone-policynone }

既存の親の下の新しいディレクトリへ、アニメーションを独立したPNG（既定）、JPEG、WebPと`manifest.json`で保存します。`ImageSequenceOptions(fps=30, hold=3, workers=1, render_quality="standard")`で時間と合成を、メソッドのキーワードで画像符号化を選びます。JPEGは不透明マット（既定白）のRGBで`quality=1..95`です。WebPはアルファと`lossless=True`をサポートし、損失WebPでは品質を指定できます。PNGと無損失WebPはレンダラーのRGBA8を正確に保ちます。不透明WebPがRGBで開かれる場合もあり、マニフェストのモードは論理的なRGBAデコードを表します。実際のフレーム数、時間、符号化、保存先を報告します。検証、形式別情報、上書きしないアトミックな公開は[画像シーケンス](../reference/export-frames.md#image-sequences)を参照してください。

### `.to_mp4(...)` { #to_mp4 }

`.to_webm()`と同じアニメーションをH.264 MP4で返します。予定されたスライド別ナレーションと任意のミックス音楽を含みます。MP4/WebM/MOVはDeckあたりナレーション付きスライド最大64枚です。無音スライドはこのFFmpeg入力数の運用制限に含めません。

ファイル出力には`deck.export("deck.mp4", animation=VideoOptions(soundtrack=AudioTrack(path="music.mp3", loop=True)))`を使います。各スライドの`audio`ナレーションと音楽を描画中にミックスします。オプションなしの`deck.export("deck.mp4")`も、既定の`VideoOptions()`で同じタイムラインを使います。

## `.diagnose()` { #diagnose }

各スライドの[`Canvas.diagnose()`](canvas.md#diagnose)をまとめ、Deck全体の検査を加えます。`findings`に`DeckDiagnostic`を格納する`DiagnosticReport`を返します。

```python
for finding in deck.diagnose().findings:
    print(finding.slide_index, finding.code, finding.message)
```

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `code` | `str` | スライドのコード（`off-canvas`、`tiny-text`など）か`mixed-slide-size`です。 |
| `severity` | `str` | `"warning"`か`"error"`です。 |
| `message` | `str` | 人が読む説明です。 |
| `slide_index` | `int \| None` | 該当スライド。Deck全体なら`None`です。 |
| `layer_index` | `int \| None` | 該当する場合のスライド内レイヤーです。 |
| `layer_id` | `str \| None` | グループの子を含む、発生元レイヤーの安定したIDです。 |
| `layer_name` | `str \| None` | 存在する場合の発生元レイヤー名です。 |
| `bbox` | `dict \| None` | キャンバス座標で測定した境界です。 |
| `related_layers` | `list[str]` | 指摘に関係するレイヤーIDです。 |
| `measured` | `dict` | 規則ごとの測定値です。 |
| `suggestion` | `str \| None` | 利用できる場合の修正ヒントです。 |

サイズが揃っていないと`mixed-slide-size`警告になります。PDFはページごとのサイズですが、PPTXは最初のスライドのサイズを全体へ使うため、後ろの大きなスライドがPowerPointで切れます。`.pptx`ではサイズを揃えてください。

## `.prefetch_assets()`（任意） { #prefetch_assets-optional }

[`Canvas.prefetch_assets()`](canvas.md#prefetch_assets-optional)と同様、全スライドのリモートアセットを事前取得し、Deck全体の`asset_manifest`を返します。描画と出力自体が取得するので、長い処理の前に通信失敗や期限切れを確認したい場合だけ呼んでください。

## JSON { #json }

### `.to_json()` / `Deck.from_json(json_str)` { #to_json-deckfrom_jsonjson_str }

各Canvasのシリアライズを再利用し、正規JSONを往復します。形式は`{"kind": "deck", "width": ..., "height": ..., "theme": {...}, "slides": [<canvas spec>, ...]}`で、各スライドも`"kind": "canvas"`を持ちます。既定サイズの`width`/`height`と`theme`は設定時だけ出力します。Deckに既定サイズがあればJSONのスライドは寸法を省略でき、正規保存では継承した値を具体化します。スライド別の`transition`、`audio`、`duration`、`notes`もCanvasのフィールドとともに維持します。最上位の`theme`は全スライドで共有し、`Canvas.from_json`と同じように`$theme.*`を参照できます。

```python
spec = deck.to_json()
restored = Deck.from_json(spec)
```

!!! note
    `Canvas.to_json()`と同様、`.custom(fn)`を含むスライドはコールバックを登録しなければ保存できません。`from_json()`はdictではなく**JSON文字列**を受け付けます。
