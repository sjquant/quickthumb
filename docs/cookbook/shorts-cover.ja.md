---
description: quickthumbでJSON仕様から作った1080×1920のShortsカバーと、生成に使った仕様を紹介します。
---

# Shorts・縦長カバー { #shorts-vertical-cover }

![切り取った写真を表示する傾いたスマートフォンと「Turn long videos into Shorts」の文字を配置した縦長カバー](../assets/examples/shorts_cover_agent.png)

デザイン全体をJSONファイルで記述した1080×1920のカバーです。Python側では読み込んでレンダリングするだけなので、LLMやテンプレートシステムでレイアウトを作る場合にも使える構成です。

実行するには[uv](https://docs.astral.sh/uv/)をインストールし、リポジトリをクローンしてください。

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/shorts_cover_agent.py
```

`examples/shorts_cover_agent.png`を保存し、同名ファイルがあれば上書きします。

## 作り方 { #how-its-built }

- **同じ写真を2回使います。** 横長の16:9の切り取りと、スマートフォン内の画面に使います。`"fit": "cover"`が各枠の形に合わせて切り取ります。
- **スマートフォンは2枚のレイヤーです。** 暗い角丸長方形が本体、その上の写真が画面です。両方と画面上の3つのラベルに`"rotation": 3`を指定して、一緒に傾けます。
- **パスはリポジトリのルート基準です。** 例：`assets/images/denise-jans-WIRvXd1PYlg-unsplash.jpg`。スクリプトは描画前にルートへ移動するため、どのディレクトリからでも実行できます。
- **背景に少し粒子を加えます。** 固定の`seed`を持つ`grain`で、毎回同じ質感を再現します。

## 仕様 { #the-spec }

```json
--8<-- "examples/shorts_cover_agent.json"
```

## スクリプト { #the-script }

```python
--8<-- "examples/shorts_cover_agent.py"
```

`Canvas.from_json()`は描画前に仕様を検証します。不正な仕様では、問題のフィールドを示す`ValidationError`になります。利用できるフィールドは[JSON SchemaとAIワークフロー](../json-schema.md)を参照してください。
