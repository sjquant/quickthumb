---
description: 画面いっぱいのポートレートとURLから読み込むWebフォントを使い、quickthumbで1280×720のポッドキャスト告知を作ります。
---

# ポッドキャストの告知 { #podcast-promo }

![右側にゲストの写真を配置した「Signal to Noise」エピソード06の告知カード](../assets/examples/podcast_interview_promo.png)

番組名、エピソード名、ゲストを載せ、右側をゲストの写真で埋めたカードです。

実行するには[uv](https://docs.astral.sh/uv/)をインストールし、リポジトリをクローンしてください。

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/podcast_interview_promo.py
```

`examples/podcast_interview_promo.png`を保存し、同名ファイルがあれば上書きします。

初回は番組名のWebフォントをダウンロードするためネットワーク接続が必要です。以降はキャッシュを使います。

## 作り方 { #how-its-built }

- **ポートレートを背景にします。** `.background(image=..., fit=FitMode.COVER)`でキャンバス全体を写真で埋めます。人物を切り抜かないため、切り抜いた縁を調整する必要もありません。
- **グラデーションで文字の場所を確保します。** 4つの停止点を持つ`LinearGradient`で、文字の背後を黒、顔の上を完全な透明にします。中間の停止点を動かすと、色が消える位置を調整できます。
- **番組名はWebフォントです。** `font=SHOW_FONT_URL`はGoogle Fontsの`.ttf`ファイルを指します。URLは特定のスタイルのファイルなので、`weight`、`bold`、`italic`は適用されません。
- **アクセントカラーは1色です。** 番組名の下の短い赤線だけに色を使い、ほかは白とグレーに揃えます。

## コード { #code }

```python
--8<-- "examples/podcast_interview_promo.py"
```

同じレイアウトで全面写真の代わりに人物を切り抜く場合は、[Webフォントと背景除去](webfonts-rembg.md)を参照してください。
