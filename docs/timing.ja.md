---
description: quickthumbのアニメーション時間、スライド切り替え、音声、再生を制御します。
---

# アニメーションのタイミング { #animation-timing }

アニメーションやスライドの長さは秒で指定します。無音ループにはGIF、音付きの動きには動画、対話的なプレゼンテーションにはHTMLを選んでください。

## シーンを動かして静止させる { #animate-and-hold-a-scene }

この例は図形を1秒かけてフェードインし、最後の画像を2秒維持します。作業ディレクトリへ`timed.gif`を保存し、同名ファイルがあれば上書きします。

```python
from quickthumb import AnimationSpec, Canvas, GifOptions

canvas = Canvas(320, 180).background(color="#102030").shape(
    "rectangle", (80, 40), 160, 100, "#42CEB7",
    animation=AnimationSpec.fade(duration=1),
)
canvas.export("timed.gif", animation=GifOptions(hold=2))
```

MP4、WebM、MOVでは`VideoOptions(hold=2)`を使います。動画出力にはFFmpegが必要です。`GifOptions`と`VideoOptions`は`fps`も受け付け、既定値はそれぞれ20と30です。GIFに音声はありません。準備は[出力形式](output-guide.md)を参照してください。

## スライドの長さと切り替え { #slide-duration-and-transitions }

Deckは各スライドのモーションと入場トランジションを再生した後、静止した状態を`hold`秒（既定は3秒）維持します。2枚目以降は別のトランジションを選ばない限り0.5秒のクロスフェードです。`Cut()`なら即座に切り替わります。

Deck動画の`slide(duration=...)`は、入場トランジションとアニメーションを含むスライド全体の時間枠を設定します。長さを明示しない場合はナレーションが時間枠を決められます。映像のアニメーションがより長ければ最後まで再生し、ナレーションは予定された枠に合わせて切り取りまたはパディングします。GIFはスライドのナレーションと`slide(duration=...)`を無視します。

トランジションの`advance_after`は通常の保持時間を置き換えます。ただしアニメーション、動画のナレーション、明示した長さが終わるまではスライドを維持します。正確な境界規則は[タイミングリファレンス](reference/timing-details.md#slide-duration-and-transitions)を参照してください。

## 音声、字幕、動きを抑える設定 { #audio-captions-and-reduced-motion }

MP4、WebM、MOVには、対応するクリップ音声、スライドのナレーション、サウンドトラックを含められます。GIFは無音です。動画クリップの字幕は配置されたクリップを基準に時刻を指定し、対応する動画フレームへ焼き込みます。

`ExportPolicy(reduced_motion=True)`では、作成したレイヤーモーションとトランジションを抑えますが、保持時間、ナレーション、字幕のタイミングは維持します。Deckの既定のクロスフェードは残ることがあります。HTMLは対話的なクリックキューを維持しますが、Deckナレーションは再生せず、動画レイヤーは静止フレームになります。出力先のアプリで確認してください。

## 時間方向の露光 { #temporal-exposure }

GIF、動画、画像シーケンスにモーションブラーを加えるには、対応する出力オプションへ`MotionBlur`を渡します。

```python
from quickthumb import MotionBlur, VideoOptions

canvas.export(
    "exposure.mp4",
    animation=VideoOptions(fps=30, motion_blur=MotionBlur(samples=8, shutter_angle=180)),
)
```

モーションブラーは出力時の設定で、HTMLやPowerPointでは再現しません。`MotionBlur`は2–64サンプルと、0度より大きく360度以下のシャッター角を受け付けます。タイミング、対応範囲、出力レポートは[モーションブラーの詳細](reference/timing-details.md#temporal-exposure)を参照してください。

### 対応範囲とレポート { #support-and-receipts }

出力後の`result.capability_report`で適用されたモーションブラーを、`result.timing_metrics`で実際にエンコードされた再生を確認できます。[対応表](reference/timing-details.md#support-and-receipts)も参照してください。

## 時間の基準を選ぶ { #choose-the-clock }

`sample()`は作成したタイムラインを観察します。GIFや動画では形式の性質により、長さやフレーム数が少し異なる場合があります。HTMLは固定長の動画ではなく対話的です。正確なフレーム時刻や出力指標が必要なら[サンプリングとタイミング](reference/timing-details.md#choose-the-clock)を参照してください。

## 再生を確認する { #verify-playback }

共有先のアプリでファイルを再生し、スライド切り替え、字幕、音、最後の保持区間を確認します。正確なタイミングは`result.timing_metrics`で調べてください。[タイミングリファレンス](reference/timing-details.md#verify-playback)ではプロジェクトの再生テストも説明しています。
