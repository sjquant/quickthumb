---
description: quickthumbのSVG、HTML、PowerPoint、PDF出力を説明します。
---

# SVG、HTML、PowerPoint、PDF { #svg-html-powerpoint-and-pdf }

[エクスポートリファレンス](../exports.md) · [出力形式を選ぶ](../output-guide.md)

## SVG { #svg }

```python
svg = canvas.to_svg()
svg = canvas.to_svg(embed_fonts=True)
```

既定では`font-family="Roboto"`のようにファミリー名でフォントを参照します。ファイルを小さくできますが、閲覧するパソコンにもそのフォントが必要です。`embed_fonts=True`は使用したファイルを`@font-face`のデータURLとして埋め込み、どこでも同じ文字を描画できるようにします。

!!! note "ビューアーの対応"
    影とグローはSVGフィルター（`feGaussianBlur`）です。ブラウザーは忠実に描画しますが、簡易なSVGラスタライザーは一部のフィルターしか適用しない場合があります。

## HTML { #html }

```python
html = canvas.to_html()
canvas.render("card.html")
```

自己完結したHTMLファイル1つになります。背景、図形、枠線、文字はHTML/CSSになり、画像やCSSで表せない内容はPNG断片として埋め込みます。SVG、PDF、PPTXとは異なり、レイヤーの`animation`を再生し、クリックで進めます。

デザインは再配置しない固定サイズのステージです。既定の`responsive=True`ではステージ全体をブラウザーの窓に合わせます。正確なピクセルサイズには`responsive=False`を指定してください。フォントは既定で埋め込む（`embed_fonts=True`）ため、別のパソコンでも同じ見た目になります。

Deckも同様に、発表者画面付きHTMLスライドショーへ出力します。[Deck](../api/deck.md)を参照してください。

## PPTX { #pptx }

編集可能な文字と対応する図形で、PowerPointやKeynoteで仕上げられるスライドを作ります。`pptx`追加機能をインストールしてください。

```bash
pip install "quickthumb[pptx]"
```

```python
from quickthumb import Canvas

canvas = Canvas(640, 360).background(color="#101826").text(
    "Ready to share", font="Arial", size=36, color="#FFFFFF", position=(60, 120)
)
canvas.export("promo.pptx")
```

スライド編集アプリで`promo.pptx`を開きます。Canvasは1枚のスライドです。複数枚には`deck.export("promo.pptx")`を使います。

!!! note "装飾した内容の編集"
    グローは固定画像で、輪郭線は別のオブジェクトになる場合があります。装飾した文字や図形を変更した後は、光や枠を揃えるためPythonから再出力してください。一部の組み合わせは画像になり、個別の文字や図形としては編集できません。[PPTX互換性](export-validation.md#pptx-compatibility)を参照してください。

!!! note "フォントと配置"
    フォントは埋め込みません。quickthumbとスライド編集アプリの両方で利用できるフォントを選んでください。代替フォント、サイズが混在する文字、回転は間隔や配置を変える場合があります。実際のアプリで確認してください。

## PDF { #pdf }

`pdf`追加機能が必要です。

```bash
pip install "quickthumb[pdf]"
```

Canvasのピクセル寸法に合わせた1ページのPDFになります（1ピクセルあたり1ポイント）。背景、枠線、図形、対応する文字を、ラスターと同じ配置計算でネイティブPDFベクターとして描きます。安全に埋め込めて複雑なシェーピングが不要なフォントはサブセットを含めます。未対応の文字は、見た目を保つためピクセル単位で一致するPNG断片になります。

```python
canvas.render("promo.pdf")
# or
with open("promo.pdf", "wb") as f:
    f.write(canvas.to_pdf())
```

!!! note "再現性"
    PDFシェーディングは透明度を表せないため、半透明のグラデーションや停止点を含むものは画像になります。ぼかし（影、グロー）、図形の線、文字のグラデーション・画像塗りにも忠実なPDFベクター表現がなく、同様にピクセル単位で一致するPNG断片を使います。
