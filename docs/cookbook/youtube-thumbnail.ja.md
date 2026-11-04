---
description: quickthumbで作った1280×720のYouTubeサムネイル5種類と、それぞれの描画に使ったスクリプトを紹介します。
---

# YouTubeサムネイル { #youtube-thumbnails }

1280×720のレイアウトを5種類紹介します。各画像は直下のスクリプトで描画したもので、リポジトリの`examples/`にあります。

[uv](https://docs.astral.sh/uv/)をインストールしてリポジトリをクローンし、ルートから実行してください。スクリプトは`assets/`から素材を読み込み、`examples/`へPNGを保存します。同名ファイルは上書きします。

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/youtube_thumbnail_01.py
```

## ビフォー・アフターのカード { #before-after }

![「Better thumbnails. Faster.」の文字と、傾いたビフォー・アフターのカード2枚を並べたサムネイル](../assets/examples/youtube_thumbnail_01.png)

写真の背景に左側の見出し、右側の傾いたカード2枚を重ね、どんな変化が得られるかを具体的に見せます。

- 横方向の`LinearGradient`をほぼ黒から透明へ変化させます。左側は文字を読める暗さを保ち、右側には写真を見せます。
- 3行の見出しは1枚の`.text()`レイヤーです。各`TextPart`でサイズと色を変えています。
- カードは`Stroke`付きの回転した`rectangle`です。手前のカードには`Shadow`も付けます。文字もカードと同じ`rotation`にします。

??? example "examples/youtube_thumbnail_01.py"

    ```python
    --8<-- "examples/youtube_thumbnail_01.py"
    ```

## 大きく問いかける { #burnout }

![彩度を落とした写真に「Are you burning out?」と大きく書いたサムネイル](../assets/examples/youtube_thumbnail_02.png)

色をほとんど取り除いた写真に、問いかけを1つ大きく載せます。

- `Filter(saturation=0.32)`で写真の色を抑え、オレンジのアクセントだけを強く残します。
- 見出しの各行を独立したテキストレイヤーとしてピクセルで配置し、行間を正確に調整します。
- 文言の上の細い線は、`#FFFFFF33`（不透明度20%の白）の高さ1pxの長方形です。

??? example "examples/youtube_thumbnail_02.py"

    ```python
    --8<-- "examples/youtube_thumbnail_02.py"
    ```

## 人物を主役にする { #talking-head }

![青いパネル上の切り抜いた人物と「AI tools. What actually works.」の文字を配置したサムネイル](../assets/examples/youtube_talking_head.png)

左に見出し、右に話し手を配置します。

- URLから人物写真を取得し、`remove_background=True`で切り抜きます。`rembg`追加機能（Python 3.11以降）とネットワーク接続が必要です。`uv run --extra rembg python examples/youtube_talking_head.py`で実行します。
- `position=(1280, 720)`と`align=("right", "bottom")`で、サイズによらず人物を右下に固定します。
- `max_width="55%"`で人物にかかる前に見出しを折り返します。

??? example "examples/youtube_talking_head.py"

    ```python
    --8<-- "examples/youtube_talking_head.py"
    ```

## リアクション { #reaction }

![驚いた人物の切り抜きと「Viral, 12.4M views」を配置したサムネイル](../assets/examples/youtube_reaction.png)

大きな言葉、大きな数字、反応を見せる顔で構成します。

- 人物の背後を中心にした`RadialGradient`で淡い赤い光を加え、その上の`LinearGradient`で文字側を暗く保ちます。
- 一番奥の`#1`は、不透明度13%、470pxのテキストレイヤーです。
- 人物には`remove_background=True`（`rembg`追加機能が必要）と`Filter(saturation=0.08)`を使い、ほぼ白黒にします。

??? example "examples/youtube_reaction.py"

    ```python
    --8<-- "examples/youtube_reaction.py"
    ```

## チュートリアル { #tutorial }

![短いコードを表示する青いパネルと「Master Python.」の文字を配置したサムネイル](../assets/examples/youtube_tutorial_explainer.png)

写真を使わず、見出し、青いパネル、数行の「コード」で構成します。

- パネルのコードは1枚のテキストレイヤーです。各`TextPart`で色と太さを変えるだけで、構文ハイライトのように見せられます。
- 色はモジュールの定数（`BLUE`、`WHITE`、`GRAY`）なので、3行を変えるだけで配色を変更できます。

??? example "examples/youtube_tutorial_explainer.py"

    ```python
    --8<-- "examples/youtube_tutorial_explainer.py"
    ```
