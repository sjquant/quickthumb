---
description: quickthumbで作った1080×1080のInstagram速報カードと、実際の描画に使ったスクリプトを紹介します。
---

# Instagramカード { #instagram-card }

![炎の写真に「Wildfires Spread Across 18,000 Acres」と記した正方形の速報カード](../assets/examples/instagram_news_card.png)

写真、赤いラベル、セリフ体の見出し、出典の行を組み合わせた正方形のニュースカードです。

実行するには[uv](https://docs.astral.sh/uv/)をインストールし、リポジトリをクローンしてください。

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/instagram_news_card.py
```

`examples/instagram_news_card.png`を保存します。同名のファイルがあれば上書きします。

## 作り方 { #how-its-built }

- **ラベルは`Background`付きのテキストです。** `Background(color="#CC0000", padding=(11, 22))`が「BREAKING NEWS」の周りに赤い枠を描きます。別の図形を手で調整する必要はなく、文字に合わせて大きくなります。
- **見出しだけ別のフォントを使います。** `font="NotoSerif"`で同梱フォルダーからセリフ体を読み込み、それ以外は既定のRobotoを使います。
- **赤い縦線は幅9pxの長方形です。** 独立した図形なので、2行の見出しに合わせて位置と高さ（176px）を指定します。
- **出典は1枚のテキストレイヤーです。** 2つの`TextPart`で「WORLD NEWS」と日付の色や太さを変えます。
- **位置は主に百分率で指定します。** `("8%", "92%")`のようにするとキャンバスとともに拡大縮小します。赤い縦線だけは、見出しに正確に揃えるためピクセル指定です。

## コード { #code }

```python
--8<-- "examples/instagram_news_card.py"
```
