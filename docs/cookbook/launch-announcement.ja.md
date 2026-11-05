---
description: テーマと自動レイアウトグループを持つJSON仕様から1280×720のリリースカードを描画し、実際の仕様を紹介します。
---

# リリース告知（自動レイアウト） { #launch-announcement-auto-layout }

![「Layouts that build themselves.」の文字と右側の青い円を配置したリリースカード](../assets/examples/launch_announcement.png)

テキストの座標を手で指定しないリリースカードです。見出しの列と機能の行に自動レイアウトを使い、すべての色と文字サイズを`theme`ブロックから読み込みます。文言やブランドを変えても測り直す必要はありません。

実行するには[uv](https://docs.astral.sh/uv/)をインストールし、リポジトリをクローンしてください。

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run --extra svg python examples/launch_announcement.py
```

`examples/launch_announcement.png`を保存し、同名ファイルがあれば上書きします。

きらめきの飾りはSVGファイルなので、`svg`追加機能が必要です。

## 作り方 { #how-its-built }

- **テーマトークン。** 色とサイズを`theme`で一度定義し、`"$theme.colors.blue"`や`"$theme.sizes.title"`として使います。値全体がトークンならJSONの型を維持するため、`"$theme.sizes.title"`は文字列ではなく数値`116`になります。
- **テキストを列グループにします。** リリースラベル、見出し、副題は、`"direction": "column"`、`"gap": 22`の1つの`group`の子です。グループだけを`["7%", "44%"]`に配置し、子には`position`を指定しません。副題が1行増えれば列もそれに合わせて再配置されます。
- **機能は行グループにします。** 「01 GROUPS」から「04 DIAGNOSTICS」は`"direction": "row"`の別のグループです。名前が変わっても間隔を均等に保ちます。
- **飾りも基本図形です。** 円、4本の棒、星は通常の`ellipse`、`rectangle`、`star`です。きらめきは`assets/images/spark.svg`を`Filter(saturation=0, brightness=3)`で白くしています。
- **描画前に検査します。** スクリプトは`canvas.diagnose()`を呼び、指摘事項を表示してから描画します。ターミナルでも`uv run --extra cli quickthumb lint examples/launch_announcement.json`で同じ検査を実行できます。

## 仕様 { #the-spec }

```json
--8<-- "examples/launch_announcement.json"
```

## スクリプト { #the-script }

```python
--8<-- "examples/launch_announcement.py"
```
