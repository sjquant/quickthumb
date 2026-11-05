---
description: quickthumbでGoogle FontsやURLからフォントを読み込み、remove_backgroundで写真の被写体を切り抜きます。
---

# Webフォントと背景除去 { #webfonts-background-removal }

## フォント { #fonts }

テキストレイヤーの`font`にはファミリー名かURLを指定できます。パソコンにないフォントを使う方法は3つあります。

### 名前でGoogle Fontを選ぶ { #a-google-font-by-name }

`font_source="google"`を指定します。初回にファミリーをダウンロードしてキャッシュし、`weight`と`italic`に合うファイルを選びます。

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720).background(color="#0A1730").text(
    content="Hello from Inter",
    font="Inter",
    font_source="google",
    weight=800,
    size=96,
    color="#FFFFFF",
    position=("50%", "50%"),
    align="center",
)
canvas.render("inter.png")
```

Google Fontsのファミリーを名前で選びたいときに使ってください。

### フォントファイルをURLで指定する { #a-font-file-by-url }

`.ttf`、`.otf`、`.woff`、`.woff2`ファイルのURLを渡します。一度ダウンロードしてキャッシュします。

```python
SHOW_FONT_URL = "https://fonts.gstatic.com/s/dmserifdisplay/v17/-nFnOHM81r4j6k0gjAW3mujVU2B2K_c.ttf"

canvas.text(content="Signal to Noise", font=SHOW_FONT_URL, size=50, color="#F5F5F7")
```

URLは特定のファイルを指すため、`weight`、`bold`、`italic`は無視されます。通常と太字を使い分けるなら、たとえば`TextPart`ごとに異なるURLを指定してください。[ポッドキャストの告知](podcast-promo.md)では、この方法で番組名のフォントを読み込みます。

### ローカルのフォントフォルダーを使う { #a-local-font-folder }

`QUICKTHUMB_FONT_DIR`にフォントのフォルダーを指定し、ファミリー名で参照します。`QUICKTHUMB_DEFAULT_FONT`はレイヤーに`font`がないときのフォントを設定します。

```python
import os

os.environ["QUICKTHUMB_FONT_DIR"] = "assets/fonts"
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

canvas.text(content="Hello", font="NotoSerif", weight=700, size=64, color="#FFFFFF")
```

レシピの作例はすべて、リポジトリの`assets/fonts`に同梱されたフォントをこの方法で使います。

## 背景除去 { #background-removal }

画像レイヤーの`remove_background=True`は写真の被写体を切り抜き、残りを取り除きます。

```python
from quickthumb import Canvas, Shadow

canvas = (
    Canvas(1280, 720)
    .background(color="#1C1C1E")
    .image(
        path="portrait.jpg",
        position=(1280, 720),
        width=620,
        height=710,
        fit="cover",
        align=("right", "bottom"),
        remove_background=True,
        effects=[Shadow(offset_x=-12, offset_y=12, color="#00000099", blur_radius=26)],
    )
)
```

`path`には`http(s)` URLも指定できます。

Python 3.11以降が必要な`rembg`追加機能をインストールしてください。

```bash
pip install "quickthumb[rembg]"
```

最初の呼び出しで、分割モデル（約170 MB）をダウンロードしてキャッシュします。

次の点に注意してください。

- **切り抜きが最初です。** 背景除去、サイズ変更、`effects`の順に処理します。そのため`Shadow`は元の長方形ではなく人物の輪郭に沿います。`Filter`は切り抜き後の色を変えますが、切り抜き方には影響しません。
- **人物に適しています。** モデルは主にポートレートで学習しています。背景とはっきり区別できる被写体ほど縁がきれいになります。
- **被写体を端に固定できます。** `position=(1280, 720)`と`align=("right", "bottom")`で、サイズによらず人物を隅に配置できます。[人物中心](youtube-thumbnail.md#talking-head)と[リアクション](youtube-thumbnail.md#reaction)のサムネイルで使っています。
