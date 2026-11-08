<p align="center">
  <img src="docs/assets/brand/quickthumb-icon-192.png" alt="quickthumb" width="88" />
</p>

<h1 align="center">quickthumb</h1>

<p align="center">
  <a href="README.md">English</a> · <a href="README.ko.md">한국어</a> · <a href="README.ja.md">日本語</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <strong>次のサムネイルも、同じレイアウトで。</strong>
</p>

quickthumbは、**サムネイルやSNS用画像を継続的に作る開発者向けのPythonライブラリ**です。
レイアウトをコードにしておき、見出し、エピソード番号、色を変えて次の画像を作れます。
Python関数やJSON仕様をコンテンツ制作のパイプラインに組み込めます。

<p align="center">
  <a href="https://quickthumb.solaqua.dev/ja/getting-started/">はじめる</a> · <a href="https://quickthumb.solaqua.dev/ja/cookbook/">作例を見る</a> · <a href="https://quickthumb.solaqua.dev/ja/api/">APIリファレンス</a>
</p>

## 最初のエピソードカードを3枚作る

この例では、1つのレイアウトから**1280 × 720のエピソードカードを3枚**作ります。
基本パッケージと内蔵フォントのみを使うため、インストール後に素材をダウンロードする必要はありません。

| 12 | 13 | 14 |
| --- | --- | --- |
| ![エピソード 12](docs/assets/home/episode-12.png) | ![エピソード 13](docs/assets/home/episode-13.png) | ![エピソード 14](docs/assets/home/episode-14.png) |

**Python 3.11以降**が必要です。quickthumbのチェックアウト先とは別の作業フォルダーで実行してください。
仮想環境が必要な場合は、[インストール手順](https://quickthumb.solaqua.dev/ja/installation/)のBash/Zsh・Windows向けの
説明を参照してから、次のコマンドでインストールします。

```bash
python -m pip install quickthumb
```

以下のコード全体を`episode_cards.py`として保存し、次のコマンドで実行してください。

```bash
python episode_cards.py
```

同じフォルダーに作成される`episode-12.png`、`episode-13.png`、`episode-14.png`を開いてください。
**実行するたびにこの3つのファイルを上書きします。**

内蔵フォントですぐに試せるよう、サンプルのタイトルは英語のままにしています。

```python
from quickthumb import Canvas, Stroke

INK = "#111111"
WHITE = "#FFFFFF"


def episode_card(episode, title, accent):
    return (
        Canvas(1280, 720)
        .background(color=INK)
        .shape("rectangle", position=(0, 0), width=1280, height=360, color=accent)
        # 数字を帯に重ね、上端で見切れるようにします。
        .text(
            str(episode),
            size=540,
            color=INK,
            # 文字と同じ色の縁取りで、内蔵フォントを太く見せます。
            effects=[Stroke(width=8, color=INK)],
            position=(1240, 360),
            align=("right", "bottom"),
            letter_spacing=-10,
        )
        .text(
            "THE BUILDER'S\nNOTEBOOK",
            size=26,
            color=INK,
            effects=[Stroke(width=1, color=INK)],
            position=(48, 44),
            letter_spacing=1,
        )
        .text(
            "EPISODE",
            size=26,
            color=INK,
            effects=[Stroke(width=1, color=INK)],
            position=(48, 330),
            align=("left", "bottom"),
            letter_spacing=1,
        )
        .text(
            title,
            size=136,
            color=WHITE,
            effects=[Stroke(width=2, color=WHITE)],
            position=(48, 688),
            align=("left", "bottom"),
            max_width=1184,
            max_height=290,
            auto_scale=True,
            balance_lines=True,
            line_height=1.04,
        )
    )


episodes = [
    (12, "Ship your first release", "#FF4B1F"),
    (13, "Make room for better work", "#FFD400"),
    (14, "Build less. Finish more.", "#4D8DFF"),
]

for episode, title, accent in episodes:
    episode_card(episode, title, accent).render(f"episode-{episode}.png")
```

`episodes`のタイトルやアクセントカラーを
変えて再実行すると、同じレイアウトで内容を差し替えたカードができます。
まとめて生成する前に、一番長いタイトルでも表示を確認してください。

日本語などを使う場合は、必要な文字を含むローカルフォントを指定してください。
設定方法は[テキスト](https://quickthumb.solaqua.dev/ja/api/text/)、レイアウトの変更方法は
[最初のカードを作る](https://quickthumb.solaqua.dev/ja/getting-started/)で説明しています。

## レイアウトを残して、中身を変える

- **内容とレイアウトを分ける。** Python関数を再利用するか、パイプラインから
  [JSON仕様](https://quickthumb.solaqua.dev/ja/json-schema/)を読み込めます。
- **タイトルの長さに備える。** 折り返しや文字サイズの調整範囲を指定するか、
  [自動レイアウトグループ](https://quickthumb.solaqua.dev/ja/api/group/)で行や列に並べられます。
- **出力前に確認する。** `diagnose()`はキャンバス外のレイヤー、小さすぎる文字、
  コントラスト不足などを検出します。デザインの良し悪しを判断するものではありません。
  [診断の範囲と限界](https://quickthumb.solaqua.dev/ja/diagnostics/)を確認してください。

同じレンダリング結果を再現するには、素材、フォント、レンダリング環境を保持する必要があります。
実行時やマシンが変わっても同じピクセルを得たい場合は、
[再現性の条件](https://quickthumb.solaqua.dev/ja/reference/export-assets/#render-reproducibility)を確認してください。

## 作例から始める

![quickthumbで作成したリリース告知画像](examples/launch_announcement.png)

| YouTubeサムネイル | 解説動画のサムネイル | ポッドキャストのエピソード |
| --- | --- | --- |
| [![YouTubeサムネイル](examples/youtube_thumbnail_01.png)](https://quickthumb.solaqua.dev/ja/cookbook/youtube-thumbnail/) | [![解説動画のサムネイル](examples/youtube_reaction.png)](https://quickthumb.solaqua.dev/ja/cookbook/youtube-thumbnail/#reaction) | [![ポッドキャストのエピソード](examples/podcast_interview_promo.png)](https://quickthumb.solaqua.dev/ja/cookbook/podcast-promo/) |

[レイアウトとソースコードを見る →](https://quickthumb.solaqua.dev/ja/cookbook/)

## ほかの形式で出力するには

基本パッケージでPNG、JPEG、WebP、SVG、HTML、GIFを出力できます。PDFとPPTXには
追加パッケージ、MP4とWebMにはFFmpegが必要です。対応範囲や見た目は形式によって異なります。
[インストール](https://quickthumb.solaqua.dev/ja/installation/)と[エクスポート](https://quickthumb.solaqua.dev/ja/exports/)を参照してください。

複数スライドのプレゼンテーションやナレーション付き動画は
[Deckガイド](https://quickthumb.solaqua.dev/ja/api/deck/)、生成したJSON仕様の利用は
[JSONとAIワークフロー](https://quickthumb.solaqua.dev/ja/json-schema/)を参照してください。

## ライセンス

[MIT](LICENSE)
