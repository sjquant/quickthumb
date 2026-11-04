---
description: quickthumbのインストール、テキスト、フォント、画像、出力形式、JSON仕様、エラーについて、よくある質問に答えます。
---

# よくある質問 { #faq }

## インストール { #installation }

### 対応するPythonのバージョンは？ { #which-python-versions-are-supported }

Python 3.11以降です。パッケージの分類は3.11と3.12で、CIは3.11で実行します。背景除去の`rembg`追加機能も同じです。

### `quickthumb`コマンドが見つかりません { #the-quickthumb-command-isnt-found }

コマンドラインツールは追加機能です。`pip install "quickthumb[cli]"`でインストールしてください。利用できる追加機能は[インストール](installation.md)にまとめています。

### SVGレイヤーで`RenderingError`が出るのはなぜですか？ { #why-does-my-svg-layer-raise-renderingerror }

SVGファイルの描画には`svg`追加機能が必要です。`pip install "quickthumb[svg]"`でインストールします。キャンバスをSVGへ*出力する*場合は不要です。

## キャンバスとレイヤー { #canvas-and-layers }

### レイヤーのないキャンバスをレンダリングするとどうなりますか？ { #what-happens-if-i-render-a-canvas-with-no-layers }

キャンバスと同じサイズの、完全に透明な画像になります。エラーではありません。

### グループの子で「group children must not set position」が出るのはなぜですか？ { #why-does-a-group-child-raise-group-children-must-not-set-position }

グループ自身が子の位置を決めるためです。子の`position`を外し、代わりにグループを配置してください。

```python
canvas.group(
    children=[{"type": "text", "content": "TITLE", "size": 96, "color": "#FFFFFF"}],
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

子の`align`も無視されます。グループの交差軸方向に子を揃えるには、グループの`item_align`を使います。

### レンダリング前にデザインの問題を確認できますか？ { #how-do-i-check-a-design-for-problems-before-rendering }

`canvas.diagnose()`を呼ぶか、JSON仕様に`quickthumb lint spec.json`を実行してください。小さすぎる文字、キャンバスからのはみ出し、低いコントラスト、隠れたレイヤーなどを報告します。[診断とCLI](diagnostics.md)を参照してください。

## テキストとフォント { #text-and-fonts }

### テキストがキャンバスからはみ出します { #my-text-runs-off-the-canvas }

`max_width`を設定すると折り返せます。

```python
canvas.text(content="A longer title that needs two lines", size=72, color="#FFFFFF", max_width="60%")
```

文字を小さくして収める場合は、`max_width`、`max_height`、または両方とともに`auto_scale=True`を追加します。

### `bold=True`と`weight=900`を設定したらエラーになりました { #i-set-boldtrue-and-weight900-and-got-an-error }

同じ属性を指定するため、どちらか一方を使います。`weight`ならより細かく指定できます。例：`TextPart(text="STRONG", weight=900)`。

### Google Fontを使うには？ { #how-do-i-use-a-google-font }

フォント名と`font_source="google"`を指定します。一度ダウンロードしてキャッシュし、`weight`に合うファイルを選びます。

```python
canvas.text(content="Hello", font="Inter", font_source="google", weight=800, size=72, color="#FFFFFF")
```

フォントファイルのURLを渡したり、`QUICKTHUMB_FONT_DIR`にフォントのフォルダーを指定したりする方法もあります。[Webフォントと背景除去](cookbook/webfonts-rembg.md)を参照してください。

## 画像 { #images }

### URLの画像は使えますか？ { #can-i-use-images-from-a-url }

はい。`background(image=...)`と`image(path=...)`は`http(s)` URLを受け付け、レンダリング中にダウンロードしてキャッシュします。設定は[リモートアセットとキャッシュ](reference/export-assets.md#remote-assets-and-caching)を参照してください。

### 人物の背景を除去するには？ { #how-do-i-remove-the-background-behind-a-person }

画像レイヤーに`remove_background=True`を設定します。`rembg`追加機能が必要です。

```python
canvas.image(path="portrait.jpg", position=("75%", "55%"), width=420, height=520, remove_background=True)
```

### `cover`、`contain`、`fill`はどう違いますか？ { #whats-the-difference-between-cover-contain-and-fill }

`cover`は枠を埋め、収まらない部分を切り取ります。`contain`は画像全体を枠内に収め、余白を残します。`fill`は縦横比を無視し、枠いっぱいに引き伸ばします。

## 出力 { #output }

### どの形式に出力できますか？ { #which-formats-can-i-export }

`render()`へ渡すファイルの拡張子で決まります。

| 種類 | 形式 | 必要なもの |
| --- | --- | --- |
| 画像 | PNG、JPEG、WebP | |
| ベクター・ドキュメント | SVG、PDF、PPTX | PDFとPPTXにはそれぞれ`pdf`、`pptx`追加機能 |
| Web | HTML | |
| アニメーション | GIF、MP4、WebM | MP4とWebMには`ffmpeg` |

最初の出力は[出力形式を選ぶ](output-guide.md)から始めてください。各形式で維持されるものと失われるものは[エクスポートリファレンス](exports.md)で説明しています。

### PNGに`quality`は指定できますか？ { #can-i-set-quality-for-a-png }

いいえ。`quality`はJPEGとWebP専用です。PNGに渡すと`RenderingError`になります。

### ファイルに書かずに画像を受け取るには？ { #how-do-i-get-the-image-without-writing-a-file }

```python
png_base64 = canvas.to_base64(format="PNG")
jpeg_data_url = canvas.to_data_url(format="JPEG", quality=90)
```

## JSON { #json }

### `Canvas.from_json()`にdictを渡せますか？ { #can-i-pass-a-dict-to-canvasfrom_json }

いいえ。JSON文字列を受け付けます。先に`json.dumps(data)`で変換してください。

### `to_json()`で`ValidationError`が出るのはなぜですか？ { #why-does-to_json-raise-validationerror }

キャンバスに`.custom(fn)`レイヤーがあるためです。Python関数はJSONに保存できないので、先にそのレイヤーを取り除いてください。

### `to_json()`の後に`theme`ブロックがなくなりました { #my-theme-block-disappeared-after-to_json }

仕様を読み込むときにテーマトークンを実際の値へ置き換えるため、`to_json()`は値だけを書き、`theme`ブロックは残しません。トークンを編集し続けたい場合は、元の仕様ファイルを保管してください。

## エラー { #errors }

### エラーの種類は何を意味しますか？ { #what-do-the-different-errors-mean }

- `ValidationError`：引数や仕様のフィールドが無効です。レイヤーの追加時、または仕様の読み込み時に発生します。
- `RenderingError`：ダウンロードなど、描画中の処理に失敗しました。
- `MissingAssetError`：仕様が参照するローカルファイルが存在しません。

どのエラーも`details`に安定したコード、該当フィールドのJSON Pointer、レイヤーIDを持ちます。[構造化エラー](errors.md)を参照してください。
