---
description: 再利用できるPythonのレイアウトからエピソードカードを3枚作り、内容を変えて自分のカードに仕上げます。
---

# 最初のカードを作る { #render-your-first-cards }

エピソードカードのレイアウトを1つ作り、3種類の内容でレンダリングします。その後、タイトルを変えて自分用のカードを作ってみましょう。

<div class="qt-gallery" markdown>
![オレンジ色の帯に大きな12と「Ship your first release」を配置したエピソード12のカード](assets/home/episode-12.png)

![黄色い帯に大きな13と「Make room for better work」を配置したエピソード13のカード](assets/home/episode-13.png)

![青い帯に大きな14と「Build less. Finish more.」を配置したエピソード14のカード](assets/home/episode-14.png)
</div>

## 1. quickthumbをインストールする { #1-install-quickthumb }

**Python 3.11以降**が必要です。Python環境で次を実行します。

```bash
python -m pip install quickthumb
```

環境の準備から始める場合は、[インストール](installation.md#isolated-environment)の手順を終えてから戻ってください。この例で使うのは基本パッケージと内蔵フォントだけです。インストール後にフォントや写真をダウンロードしたり、追加のレンダラーを用意したりする必要はありません。

## 2. レイアウトを保存して実行する { #2-save-and-run-the-layout }

quickthumbのチェックアウトとは別の作業ディレクトリに、次のコードを`episode_cards.py`として保存します。

```python
--8<-- "examples/episode_cards.py"
```

そのディレクトリで実行します。

```bash
python episode_cards.py
```

同じディレクトリにある`episode-12.png`、`episode-13.png`、`episode-14.png`を開いてください。いずれも1280 × 720の画像です。スクリプトは毎回同じファイル名で保存するため、同名のファイルがあれば上書きします。

## 3. 次のカードを作る { #3-make-the-next-card }

関数はそのままにして、`episodes`へ1行追加します。

```python
(15, "Your next big idea", "#FF4B1F"),
```

再び実行し、`episode-15.png`を開きます。同じレイアウトを使い、エピソード番号、タイトル、色だけを変更できました。

タイトルは`max_width`の範囲内で折り返します。`auto_scale=True`を指定すると、設定した幅と高さに収まるまで文字が小さくなります。まとめてカードを作る前に、実際に使う最も長いタイトルで確認してください。

## デザインを調整する { #adapt-the-design }

`episode_card()`内の色、数字やタイトルのサイズ、位置を一度変更すると、すべてのカードに反映されます。レイヤーは追加した順に描画されます。好みの書体を使うには、各`.text()`に`font="/path/to/your-font.ttf"`のようなローカルフォントのパスを追加します。フォント自体が十分に太ければ`Stroke`エフェクトを外してください。

レイアウトを拡張するときは、`canvas.diagnose()`でキャンバスからはみ出したレイヤーや低いコントラストなどを確認します。この例では数字を意図的に切り取っているため、`off-canvas`が1件報告されます。検査項目と制限は[診断](diagnostics.md)を参照してください。指摘がなくても、見た目のよいデザインであることを保証するものではありません。

## 次のステップを選ぶ { #choose-your-next-step }

- [レシピ集](cookbook/index.md)：サムネイル、ソーシャルカード、ポッドキャストのレイアウトを応用します。
- [基本的な考え方](concepts.md)：レイヤー、エフェクト、配置を理解します。
- [自動レイアウト](api/group.md)：内容が変わる要素を行や列に並べます。
- [JSONとAIワークフロー](json-schema.md)：JSONのレイアウトを読み込み、検証します。
- [出力形式を選ぶ](output-guide.md)：画像、プレゼンテーション、アニメーションを作ります。
- [APIリファレンス](api/index.md)：クラスやパラメーターを調べます。
