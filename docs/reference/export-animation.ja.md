---
description: quickthumb の GIF、動画、ナレーション出力のリファレンスです。
---

# GIF・動画・ナレーション { #gif-video-and-narration }

[出力リファレンス](../exports.md) · [出力形式を選ぶ](../output-guide.md)

## アニメーション GIF と動画 { #animated-gif-video }

基準サンプリングとエンコードするフレーム数の違い、スライド・ナレーションの時間軸、字幕、対話型 HTML の動作は、[アニメーションのタイミング](../timing.md)を参照してください。

アニメーション出力は PNG と同じピクセル処理経路でサンプリングし、レイヤーの `animation` と Deck のスライド `transition` を実際のラスターフレームとして描画します。Canvas と Deck の GIF/MP4/WebM/MOV は、オプションを省略したファイル出力でもこのアニメーションタイムラインを再生します。

```python
from quickthumb import AudioTrack, Canvas, Deck, Fade, GifOptions, VideoOptions
from quickthumb.transitions import Push

canvas = Canvas(1280, 720).background(color="#101820").text(
    content="Hello", position=("50%", "50%"), size=96, color="#FFFFFF",
    animation=Fade(duration=0.6),
)
canvas.render("hello.gif")                     # defaults: 20 fps, 3s hold
canvas.render(
    "preview.gif",
    animation=GifOptions(fps=8, max_size=(540, 960), colors=128),
)
mp4 = canvas.to_mp4(fps=30, hold=2.0)          # tunable variants return bytes

other = Canvas(1280, 720).background(color="#204060")
deck = Deck(1280, 720).slide(canvas).slide(other, transition=Push(direction="left"))
gif = deck.to_gif(fps=20, hold=3.0, loop=0)
webm = deck.to_webm(fps=30, hold=3.0)
```

各エフェクトは `duration`、`delay`、`trigger` に加え、2 つの時間制御を受け付けます。

- `easing` は共通のイージング名（`"linear"`、`"ease"`、`"ease_out_cubic"`、`"ease_out_back"` など）から表示の変化曲線を選びます。従来のエフェクトは既定で `"ease"`、正規プリセットは easing/feel を解決し、それ以外では `"linear"` を使います。経過時間を示すバーには、進捗を正しく表す `"linear"` が必要です。HTML では名前付きイージングと独自の cubic-bezier タイミング関数を CSS に渡します。名前付きの多項式曲線には既存の CSS cubic-bezier 近似を使うため、曲線は似ていても、中間のピクセル状態が基準サンプリングと完全に一致するとは限りません。
- `start` は直前の処理につなげる代わりに、スライド内の絶対時刻を指定します。絶対時刻を指定したエフェクトは、周囲の相対エフェクトをつなぐカーソルを動かさないため、両方を混在できます。

```python
from quickthumb import Wipe

canvas.shape(
    shape="rectangle", position=(0, 700), width=1280, height=6, color="#E8A552",
    animation=Wipe(direction="right", duration=6.0, easing="linear"),
)
canvas.shape(
    shape="rectangle", position=(80, 180), width=180, height=14, color="#E8A552",
    animation=Wipe(direction="right", duration=2.4, start=0.9, easing="linear"),
)
```

正規の `AnimationSpec` に `stagger` を指定すると、対象ごとに時間をずらして動かします。行の対象はレイヤーの完成した描画から切り出すため、描画時のレイアウトを保ち、自分の順番まで画面外で待ちます。

```python
from quickthumb import AnimationSpec

canvas.text(
    content="가로로 한 번.\n세로로 한 번.\n미리보기로 또 한 번.",
    position=(80, 150), size=38, color="#F2EFE9", line_height=1.5,
    animation=AnimationSpec.rise(
        from_="bottom", distance=26, duration=0.45, stagger=0.32, target="lines"
    ),
)
```

接するほど行間が狭い行は描画結果から分離できず、単語・文字単位の対象にも分離可能な帯がありません。これらはレイヤー全体の移動に切り替わります。

静的なテキストやトップレベルのグループも、明示的な親チェーンの末端として時間差を付けられます。分離した帯は祖先のアフィン変換全体を継承し、独自のアンカーと外観トラックを保ちます。前述と同じ部分的な帯アダプターと全体への代替処理を使います。時間差を付けたレイヤー自体を別レイヤーの親にはできません。カウンターと stagger の併用、および動的ソースには引き続き制限があります。[親変換の対応範囲](../api/video.md#current-adapters-and-boundaries)と、実行例 `examples/parent_stagger.py` を参照してください。

`Canvas.render()` と `Deck.render()` は、アニメーションファイル向けに形式別のオプションを受け付けます。GIF には `GifOptions`（`fps`、`hold`、`matte`、`loop`、`max_size=(width, height)`、`colors`）、MP4/WebM/MOV には `VideoOptions`（`fps`、`hold`、`matte`、`soundtrack=AudioTrack(...)`、`loop_audio`、WebM/MOV の `transparent=True`）を使います。両方とも `workers=1` と `render_quality="standard"` を受け付けます。動画に GIF のサイズ・パレット設定を指定したり、GIF に動画オプションを指定したりすると拒否されます。汎用の `render(..., quality=...)` は引き続き JPEG/WebP のラスター出力専用です。

両モデルの既定値は静止状態を保つ `hold=3.0` で、Canvas と Deck のバイト列メソッドの `hold` と同じです。有限の非負の数値が必要で、真偽値と文字列は拒否します。既定の hold はオプションのシリアライズ時に省略し、読み込み時に復元しますが、明示したゼロは残します。動画の進行時間は引き続きナレーションと Deck の明示的なスライド時間から決まり、Deck の GIF はこれらのスライド時間を無視します。Deck のアニメーション動画には従来の制限があります。ナレーションも明示的な正の時間もないスライドがあると、音声スケジュールに正の長さの無音区間が必要なため、`hold=0` は失敗します。その場合は正の hold を使ってください。Canvas、Deck の GIF、無音の画像シーケンスでは引き続きゼロを指定できます。

バイト列メソッドも、キーワード専用のスカラー引数として同じ描画制御を受け付けます。Canvas の GIF/MP4/WebM/MOV、Deck の GIF とアニメーション MP4/WebM/MOV に `workers=1` と `render_quality="standard"`、GIF にはさらに `max_size=None` と `colors=None` があります。これらのメソッドは `hold` を使い、オプションオブジェクトは受け付けません。ナレーションも他の動画出力と同じ Deck MP4 タイムラインを使います。

ファイル出力では、まず形式を確定してから出力ポリシーを検査します。Canvas と Deck の MP4 は常にアニメーションタイムラインを再生し、オプションがなければ `VideoOptions()` を使います。静的ファイルや reduced-motion で使わない Morph 遷移は、代替表現のエラーや結果レポートの診断を発生させません。アニメーションを抑えた場合も、エンコーダーの保持時間とスライド間の既定の遷移は残ります。サンプリングレート、エンコードする映像のフレーム数・長さは[アニメーションのタイミング](../timing.md)を参照してください。

`ExportResult.pixel_metrics.width` と `height` は、引き続き最初の Canvas の基準ラスター寸法です。GIF のリサイズや MP4/WebM のクロップ寸法ではありません。画像シーケンスは、フルサイズの出力寸法を別に報告します。

`validate_export(target)` は宣言されたモーション機能を問い合わせるもので、ファイル出力のオプションとは独立しています。たとえば reduced-motion ポリシーでも `validate_export("mp4")` はアニメーション動画を照会します。具体的な `svg` と `pdf` の照会は、既存の `raster` 分類名で静的文書の代替表現を示します。対象名は大文字・小文字を区別せず、`jpg`、`jpeg`、`webp`、`png`、`gif`、`mp4`、`webm`、`mov`、`htm`、`image_sequence` を対応する分類の別名として受け付けます。GIF の照会は `raster` を使いますが、互換性のため GIF の `ExportResult.target` は引き続き `video` です。

## ナレーション付き Deck 動画 { #narrated-deck-video }

スライドごとに音声を付けて、Deck を動画にできます。

- `Deck.slide()` に `audio=` を渡します。`duration=` を省略すると `ffprobe` でナレーションの長さを測定します。`duration=` を明示すると音声を切り詰めるか、無音で延長します。音声のないスライドは `hold`（3 秒）の間、無音で表示します。
- `deck.export("deck.mp4")` と `deck.render("deck.mp4")` は、既定でレイヤーアニメーションと遷移をナレーションとともに再生します。`deck.to_mp4()`、`deck.to_webm()`、`deck.to_mov()` はアニメーション動画のバイト列を返します。
- 静止スライドにナレーションを付けるには、静的な Canvas を作り、遷移に明示的な `Cut()` を指定します。出力は H.264/yuv420p で、音声がある場合は AAC です。遷移の省略はカットではなく既定のフェードになります。`reduced_motion=True` も既定の遷移を選ぶため、静止スライド出力モードではありません。通常の MP4 経路では既存のアニメーションレイヤーも再生されます。
- 背景音楽は `deck.export()` または `deck.render()` に `animation=VideoOptions(soundtrack=AudioTrack(path="music.mp3", volume=0.16, loop=True))` を指定します。Quickthumb がスライドのナレーションとミックスするため、事前に自分で混ぜる必要はありません。

```python
from quickthumb import Canvas, Deck, VideoOptions
from quickthumb.transitions import Cut

deck = Deck(640, 360).transition(Cut())
deck.slide(Canvas(640, 360).background(color="#123456"),
           audio="voice.wav", duration=2.5)
deck.slide(Canvas(640, 360).background(color="#456789"), duration=1.0)
result = deck.export("narrated.mp4", animation=VideoOptions(fps=30))
mp4_bytes = deck.to_mp4(fps=30)
```

## タイミング { #timing }

動画と GIF は HTML スライドショーと同じタイミングで動きますが、クリックできないため、`on_click` は `after_previous` のように順番に自動再生します（PowerPoint の動画出力も同じです）。各スライドは前のスライドの最後のフレームに重ねて遷移し、HTML と同様に遷移とともにアニメーションを開始します。その後、遷移の `advance_after` があればその時間、なければ `hold` の間、最終状態を保ちます。ナレーション付き MP4/WebM/MOV では、推定・明示したナレーションの長さ（または無音スライドの既定値）が `advance_after` より長ければ、画面も延長します。遷移未指定のスライドは 0.5 秒でクロスフェードします（未指定のスライド 0 は即座に始まります）。スライド 0 に遷移を指定するとマットから登場し、ループ GIF のつなぎ目も滑らかになります。

GIF は Pillow がフレームごとの時間を使ってエンコードするため、追加の依存関係は不要です。MP4（H.264）、WebM（VP9）、MOV（ProRes 4444）には、`PATH` 上の `ffmpeg` バイナリー、または環境変数 `QUICKTHUMB_FFMPEG` で指定したバイナリーが必要です。

Canvas の MP4、WebM、MOV には音楽を付けられます。ffmpeg がデコードできる音声ファイル（MP3、WAV、AAC、OGG など）を使え、MP4/MOV では AAC、WebM では Opus にエンコードします。

```python
mp4 = canvas.to_mp4(soundtrack="music.mp3")                    # loops to fill the video
mp4 = canvas.to_mp4(soundtrack="jingle.wav", loop_audio=False) # plays once, then silence
```

音声は必ず動画の長さに切り詰めます。`AudioTrack` の `loop=True` は短い音声を繰り返し、`loop=False` は一度再生してから無音にします。`loop_audio` で明示的に上書きできます。従来の文字列パスは以前と同じループの既定動作を保ちます。GIF には音声を付けられません。

!!! tip "形式選びのヒント"
    - **背景**: フレームは不透明なマット（既定は黒）に合成します。アルファ付きの重ね合わせには WebM または MOV の `transparent=True` を使います。
    - **解像度**: H.264/VP9 の 4:2:0 エンコードには、1280×720 など偶数ピクセルの寸法が必要です。
    - **GIF の最適化**: `GifOptions` の `max_size=(w, h)` と `colors=128`（または 64）でファイルを小さくできます。
    - **ナレーション付き Deck**: 1 回の Deck 動画出力は、ナレーション付きスライドを最大 64 枚まで扱えます。それより長いプレゼンテーションは複数の動画に分けてください。
