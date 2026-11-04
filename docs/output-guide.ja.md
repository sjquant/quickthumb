---
description: 出力形式を選び、quickthumbで最初の画像、プレゼンテーション、アニメーションをエクスポートします。
---

# 出力形式を選ぶ { #choose-an-output-format }

同じCanvasやDeckから、画像、プレゼンテーション、アニメーションを作れます。使い道に合わせて形式を選んでください。

| やりたいこと | 形式 | 必要なもの |
| --- | --- | --- |
| 画像を公開する | PNG、JPEG、WebP | 基本パッケージ |
| ブラウザーでプレゼンテーションを共有する | HTML | 基本パッケージ |
| PowerPointやKeynoteでスライドを編集する | [PPTX](reference/export-documents.md#pptx) | `pptx`追加機能 |
| ドキュメントを共有する | PDF | `pdf`追加機能 |
| 短いアニメーションを共有する | GIF | 基本パッケージ |
| 動画を公開する | MP4、WebM、MOV | FFmpeg。MOVには`prores_ks`エンコーダーも必要です。 |
| ベクター画像を使う | SVG、Lottie | SVGは基本パッケージで利用できます。LottieはCanvas専用で、対応する機能が限られます。 |

## 画像をエクスポートする { #export-an-image }

ファイルの拡張子で形式を選びます。この例にはPython 3.11以降と`pip install quickthumb`が必要です。

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720).background(color="#155BD7").text(
    "Make an idea visible.", size=72, color="#FFFFFF", position=(80, 300)
)
result = canvas.export("image.png")
print(result.written_paths)
```

作業ディレクトリの`image.png`を開いてください。再度出力すると上書きします。JPEGには`.jpg`、WebPには`.webp`を使います。Deckを画像形式へ出力すると、番号付きのスライドファイルを保存します。ファイル名は`written_paths`で確認できます。

## スライドやアニメーションを作る { #make-slides-or-animation }

[プレゼンテーションと動画の例](cookbook/decks-and-video.md)には、そのまま実行できる画像、2枚のHTMLプレゼンテーション、GIFの例があります。PowerPointやPDFでは、先に対応する[追加機能](installation.md#optional-extras)をインストールしてください。MP4とWebMには別途FFmpegのインストールが必要です。

エフェクトやアニメーションの再現方法は形式によって異なります。PowerPointやPDFでは画像に置き換える場合があり、HTMLプレゼンテーションはDeckのナレーションを再生しません。実際に使うアプリで結果を確認してください。

対応形式、出力レポート、詳細オプション、代替表現については[エクスポートリファレンス](exports.md)を参照してください。
