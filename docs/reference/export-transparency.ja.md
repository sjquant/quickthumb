---
description: quickthumbの透過動画出力と、コーデック・アルファ対応の制限を説明します。
---

# 透過動画 { #transparent-video }

[エクスポートリファレンス](../exports.md) · [出力形式を選ぶ](../output-guide.md)

## 透過WebM { #transparent-webm }

VP9 WebMは`VideoOptions(transparent=True)`か、`Canvas.to_webm()`、`Deck.to_webm()`のキーワード専用`transparent=True`でアルファを維持できます。既定の`False`では、従来の不透明出力のマットと設定を維持します。レイヤーやモーションではなく出力オプションなので、Canvas/Deck JSONや`inspect_motion()`には含めません。`VideoOptions.model_validate_json()`とモデルのJSONスキーマは厳密なブール型として公開します。`validate_export()`は引き続き文書モーションを説明し、`render()`は未対応形式の透明オプションを拒否します。

```python
canvas.render("overlay.webm", animation=VideoOptions(transparent=True))
deck.render("overlay.webm", animation=VideoOptions(transparent=True, render_quality="high", workers=2))
webm_bytes = canvas.to_webm(transparent=True)
options = VideoOptions.model_validate_json('{"transparent": true, "fps": 24}')
```

省くのは出力のマットだけです。作成した背景は残り、空の部分やサイズ混在スライドの余白は透明です。0番スライドの切り替えは透明から始めます。フェードとマスクの切り替えは乗算済みの色を補間し、覆う・拡大縮小するスライドはsource-overアルファで合成します。キー付きMorphはサイズの違うスライドを最初の出力空間へ正規化し、位置、寸法、半透明ピクセルを補間します。親や字幕を伴うMorphの代替制限は従来通りです。

両方の合成品質、spawnワーカー、音楽、Deckナレーションが透過WebMで使えます。エンコーダーはアルファ平面を守るため無損失VP9符号化でRGBAをVP9の`yuva420p`へ送ります。RGBAからYUVへの変換で、デコード後のアルファが8ビットの1段階変わる場合があります。RGBは4:2:0色差サブサンプリングなので、元の色ピクセルは無損失ではありません。不透明WebMよりファイルが大きくなる場合があります。制限されたフレームバッチとアトミックな保存先置き換えは維持します。透過切り替えには正確な乗算済み合成用の一時浮動小数点平面を使い、メモリは寸法とワーカー数に応じて増えます。MP4、GIF、文書・ラスターは保存前にこのオプションを拒否します。PNGアニメーションシーケンスには別の[`export_image_sequence()` API](export-frames.md#image-sequences)を使います。

VP9 WebMのアルファに対応した再生・編集アプリを使ってください。FFmpegで実際のアルファ平面を見るには、入力の**前に**libvpxデコーダーを指定します。

```bash
ffmpeg -c:v libvpx-vp9 -i overlay.webm -frames:v 1 -pix_fmt rgba frame.png
```

標準のVP9デコーダーは色だけを報告・デコードする場合があり、`alpha_mode`だけでは透明度が維持された証拠になりません。回帰テストはlibvpxでRGBAをデコードし、透明・半透明・不透明のピクセルを比較します。半透明パネルと透明な周囲を持つ例は`examples/transparent_lower_third.py`を参照してください。

## ProRes 4444 MOV { #prores-4444-mov }

CanvasとDeckは、FFmpegの`prores_ks`で固定のProRes 4444プロファイルの`.mov`へ出力できます。Deck切り替えとナレーションを含むアニメーションを常に再生します。`transparent`はWebMと同じ厳密なブール型で既定は`False`です。通常はマットへ合成し、有効にするとそのマットだけを省きます。背景、余白、切り替え、品質、ワーカーは上の透過WebMと同じです。

```python
canvas.render("overlay.mov", animation=VideoOptions(transparent=True, fps=24))
deck.export("overlay.mov", animation=VideoOptions(transparent=True, render_quality="high", workers=2))
mov_bytes = canvas.to_mov(hold=2.0, transparent=True)
mov_bytes = deck.to_mov(hold=2.0, transparent=True, soundtrack="music.wav")
```

奇数幅・高さでも切り取らず、正確なCanvas寸法を維持します。透過出力は4:4:4色差と16ビットアルファ符号化（`yuva444p10le`）を使い、Final Cut Pro、DaVinci Resolve、Adobe Premiereなどの専門編集ツール向けの標準的なアルファ再現性を提供します。

音楽、スライド別ナレーション、動画内の音声は、MP4と同じ予定・ループ・パディング・切り取りでAACにします。音声入力がないCanvas MOVは映像だけです。Deck MOVはナレーションがない場合も、従来の処理の無音AACトラックを維持します。固定のコーデック・プロファイル・音声形式を選び直すAPIはありません。ProResはWebM/MP4より大幅に大きい場合があり、対応する再生・編集アプリが必要です。符号化区間のサイズは制限され、全符号化と多重化が成功してから保存先を置き換えます。`prores_ks`がなければ描画エラーになり、既存の出力は保護します。アルファはプロファイル情報だけでなく、ピクセルをデコードして確認してください。

```bash
ffmpeg -i overlay.mov -frames:v 1 -pix_fmt rgba frame.png
```

`examples/transparent_lower_third.py`はWebMとProRes MOVの両方を作ります。
