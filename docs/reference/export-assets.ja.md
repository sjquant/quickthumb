---
description: quickthumb の基準サンプル、アセット、描画の再現性のリファレンスです。
---

# サンプル・アセット・再現性 { #samples-assets-and-reproducibility }

[出力リファレンス](../exports.md) · [出力形式を選ぶ](../output-guide.md)

## 基準サンプル { #canonical-samples }

`sample()` は、出力と比較するためのレンダラーに依存しない基準を、JSON に保存できる `FrameSequence` として返します。Canvas と Deck は同じ契約を使い、Canvas の観測結果は、その Canvas だけを含む 1 枚の Deck と同じになります。

```python
still = canvas.sample()                         # settled frame(s), as PNG/PDF/PPTX draw them
timed = deck.sample(fps=10)                     # uniform grid over the whole animated timeline
probe = deck.sample([0.0, 1.25, 4.0], hold=2.0) # explicit instants, ascending
```

- **フレーム。** 各 `CanonicalFrame` は `width * height` ピクセルを、生の 8 ビット RGBA（左上から行優先、sRGB、ストレートアルファ）の base64 として `data` に保持し、そのバイト列の `sha256` も持ちます。`index` はシーケンス内の位置、`slide` は表示するページです。ダイジェストや寸法がデータと一致しないフレームは、読み込み時に拒否します。
- **静止画キャプチャ**（`capture="still"`）は、スライド順でページごとに 1 フレームを、そのページ固有の寸法と透明度を保って取得します。`time` は `None`、`duration` は `0`、`timeline` は空です。
- **タイムラインキャプチャ**（`capture="timeline"`）は、アニメーション WebM/MP4 が再生するタイムラインを観測します。遷移、Morph、レイヤーアニメーション、ナレーションに基づくスライド時間、明示的な時間のないページの最終状態の保持 `hold` 秒（既定 3）を含みます。フレームは秒単位の `time` の昇順で、最初のスライドの寸法に揃え、不透明な `matte`（既定は黒）に合成します。matte は `#RRGGBB` で報告します。Deck の GIF は現在、明示的な時間とナレーションによる時間を無視するため、これらがない Deck だけがこのタイムラインと一致します。
- **サンプリング。** `fps=N`（最大 120）は `duration` より前の各 `k / N` の瞬間を観測します。明示時刻は昇順が必要で、`duration` 以降の時刻は最終状態を表示します。1 回で観測できるのは最大 100,000 時点です。それより大きい明示リストや fps グリッドは、描画前に `ValidationError` で拒否します。このグリッドは観測の予定であり、出力側のフレーム予定ではありません。各出力処理は区間ごとに独自のフレームグリッドでサンプリングし、1 フレーム未満のスライドを 1 フレームまで延ばします。
- **時間。** `duration` は正確なタイムラインの長さで、`fps` や要求した時刻には依存しません。各 `TimelineSegment` は、スライドの絶対時刻 `start`、`transition_end`、`animation_end`、`end` をナノ秒に丸めて示します。表示区間は `[start, end)` なので、境界の瞬間は次に入るスライドに属します。
- **メモリ。** 異なるフレームの生 RGBA が 768 MiB を超えるキャプチャは `ValidationError` になります。静止画キャプチャの全ページ、またはタイムラインの 1 フレームだけですでに超える場合は、描画前に拒否します。時点数や `fps` を減らす、`hold` を短くする、文書を小さくするなどで調整してください。
- **環境。** `sample()` と `export()` は quickthumb、Pillow、FreeType のバージョン、テキストレイアウトエンジン（`basic` または `raqm`）、利用可能な RAQM/HarfBuzz/FriBidi のバージョン、動画レイヤーがある文書の FFmpeg バージョンを報告します。動作する FFmpeg なしに動画をサンプリングすると、描画前に `RenderingError` になります。`environment.fonts` はその処理で実際に選択したフォントフェイスのバイトを示し、アセットマニフェストは作成時の参照を別に記録します。

## 描画の再現性 { #render-reproducibility }

フォントファミリー名と `QUICKTHUMB_DEFAULT_FONT` はマシンのフォント検索パスに依存します。移植可能な識別子と考えず、実際に選択されたフェイスを確認してください。

```python
capture = canvas.sample()
for font in capture.environment.fonts:
    print(font.source, font.sha256, font.variations)
```

各フェイスには、解決したファイルパス（または `pillow:default`）、SHA-256、適用した可変座標（フォントの軸名がキー）があります。ハッシュはフォントのバイトを識別します。Pillow 内蔵のフェイスは、バイトを取得できなければハッシュを報告しません。パスは診断用です。マシン間ではハッシュと座標を比較してください。報告するのは現在の処理でロードしたフェイスだけで、未使用の名前付きフォントや過去の処理のフェイスは含みません。

リモートフォントと Google Fonts は、解決したバイトの内容アドレス付きコピーからロードします。そのため、別の文書が元の URL を更新しても、プリフェッチ済みのフェイスは変わりません。コピーはアセットキャッシュに置かれ、呼び出し側が管理する削除ライフサイクルに従います。処理中はローカルの入力ファイルを変更しないでください。

基準ラスター出力を再現するには、文書データ、入力アセットのバイト、選択したフォントと可変座標、描画オプション、環境を揃え、対応する手続き型エフェクトには seed を指定します。フォント、文字整形、ラスター化のバージョンが違うと、レイアウトや輪郭ピクセルが変わる場合があります。このレポートは入力を説明するもので、プラットフォームやネイティブ出力ビューアーをまたぐ完全一致を約束しません。そのような出力の比較には形式別の忠実度許容値を使ってください。

## リモートアセットとキャッシュ { #remote-assets-and-caching }

`render()` と `export()` は、リモートの画像、SVG、文字の塗りつぶし、フォントを共有キャッシュにダウンロードします。`export()` は使用したすべてのアセットを示す `asset_manifest` を返します。任意の `prefetch_assets()` は同じダウンロードを事前に行い、描画せずにマニフェストを返します。長い出力の前に通信失敗や古いエントリーを検出したり、オフライン描画用にキャッシュを準備したりできます。各 `AssetManifestEntry` は、記述した `source`、意味上の `asset_type`、`status`、取得できた識別情報を持ちます。識別情報には `source_key`（正規 URL）、`cache_key`、`cache_path`、`content_hash`（実際に使ったバイトの SHA-256）、`fetched_at`（UTC のダウンロード時刻）があります。

| `status` | 意味 |
| --- | --- |
| `local` | 存在するローカルファイルです。 |
| `missing` | 存在しないローカルパスです。 |
| `network` | 今回ダウンロードし、キャッシュに保存しました。 |
| `fresh` | `max_age` 以内のキャッシュから読みました。`max_age` 未指定なら常にこの状態です。 |
| `stale` | 更新できなかったため期限切れのキャッシュを使ったか、オフラインで読みました。理由は `stale_reason` にあります。 |
| `unresolved` | まだ解決していないリモート参照です。 |

キャッシュは環境変数で制御します。

- `QUICKTHUMB_ASSET_CACHE_DIR`: キャッシュディレクトリ。既定はシステムの一時ディレクトリです。
- `QUICKTHUMB_ASSET_MAX_AGE`: キャッシュをネットワークから更新するまでの秒数。更新失敗時は古いバイトを使い、`stale` と報告します。未設定なら期限切れになりません。
- `QUICKTHUMB_ASSET_OFFLINE=1`: ネットワーク要求を行いません。キャッシュを使い、期限切れなら `stale` と報告します。

## 所有と再利用 { #ownership-and-reuse }

`prefetch_assets()`、`sample()`、出力の間で解決結果を再利用するには、同じ `Canvas` または `Deck` を保持してください。各 Canvas は最初のリモート解決結果と状態を保持し、Deck はスライドの結果を使います。リモートの画像、文字の塗りつぶし、SVG は、この保持したバイトから描画します。Google Fonts を含むリモートフォントは、解決したバイトの内容アドレス付きコピーからロードするため、別の文書による URL 更新でプリフェッチ済みフェイスは変わりません。サンプリングから出力までキャッシュファイルを利用可能にしてください。現在のキャッシュポリシーで同じ参照を再解決するには、新しい文書を作ります。

`PrefetchResult` と `asset_manifest` は JSON に安全に保存できるレポートであり、リソースハンドルではありません。JSON の保存・読み込みでバイトが移動したり、別の文書に事前ロードされたりはしません。新しい文書も永続化したキャッシュを再利用でき、使えるエントリーなら `fresh` と報告します。ローカルの画像、フォント、動画、音声のパスは呼び出し側が所有するファイルです。サンプリングや出力が終わるまで、利用可能なまま変更しないでください。プリフェッチはこれらを固定・コピーしません。動画と音声はプリフェッチでダウンロードしません。リモート動画は必要時に FFmpeg が読み、このキャッシュ契約の対象外です。ファイル・URL 参照のない生成コンテンツには外部アセットのエントリーはありません。

キャッシュディレクトリと削除は呼び出し側が管理します。Quickthumb はリモートのキャッシュファイルとメタデータをアトミックに書きますが、自動削除はしません。文書や出力ワーカーがそのキャッシュを使わなくなってから、不要なエントリーを削除してください。既存のマニフェストは観測記録であり、`cache_path` のファイルが今も存在する保証ではありません。メモリ上のリモート解決結果には明示的な文書 close は不要で、文書とともに解放されます。

使えるキャッシュもネットワーク応答もないと、ソース、原因、検索したキャッシュディレクトリを示す `RenderingError` になります。古い入力を拒否したい場合は、描画前にマニフェストを確認してください。

```python
prefetched = canvas.prefetch_assets()
stale = [entry for entry in prefetched.asset_manifest if entry.status == "stale"]
if stale:
    raise SystemExit(f"stale assets: {[(e.source, e.stale_reason) for e in stale]}")
```

## アセットとプラグインのライフサイクル検証 { #asset-and-plugin-lifecycle-fixtures }

`tests/test_asset_cache.py` の共有フォント・テクスチャのシナリオは、非公開のプラグインレジストリ、リポジトリ内の TTF、一時 localhost HTTP サーバーが配信する生成画像バイトを使います。公開 Canvas/Deck API とキャッシュ環境変数を検証します。制御した標準時計で、待機やキャッシュファイル・メタデータの編集なしに期限を進めます。外部ネットワークやプラットフォーム固有のピクセルスナップショットは不要です。

| シナリオ | 観測する証拠 | 回帰検査 |
| --- | --- | --- |
| ネットワーク → 新しい文書で fresh → 期限切れ更新 | 解決状態、取得時刻、変化した内容ハッシュ、実際のフォント識別、デコードした PNG ピクセル。元の文書は解決済みバイトを保持します | `test_combined_resources_refresh_only_for_new_expired_documents`（`canvas`、`deck`） |
| オフラインで期限切れキャッシュ | プラグイン実行や出力前に、両リソースがソース、ハッシュ、取得時刻、offline/max-age の理由付きで `stale` を報告します。続行すると、要求なしで元の RGBA・フォントを使います | `test_combined_offline_stale_evidence_precedes_optional_rendering`（`canvas`、`deck`） |
| キャッシュなしのオフラインフォント・プラグインテクスチャ | 公開 prefetch が後続スライド、ソース URL、キャッシュディレクトリを特定します。テクスチャエラーはレイヤー・アセットのパスも示します。コールバックも書き込みもありません | `test_combined_cold_offline_failure_identifies_later_slide_resource`（`font`、`texture`） |
| プリフェッチ済みリソースのラスター・ネイティブ文書出力 | Canvas/Deck のラスター一致、実際のフォント SHA、アセットマニフェスト、ネイティブ SVG テキスト、完全一致のプラグイン PNG 代替 | `test_prefetched_font_and_private_plugin_keep_shared_export_evidence` |
| プラグインに宣言した依存アセットの欠落 | エスケープした JSON Pointer、レイヤー識別、書き込み前の失敗 | `test_plugin_declared_missing_assets_fail_before_output_or_callback` |
| プラグインのネイティブ一致、許容差、不一致、未対応の出力先 | 実際のローカル SVG 比較と採用したネイティブ・PNG 表現、理由付きの代替と strict での拒否 | `tests/test_plugin_svg.py`、`tests/test_plugin_runtime.py` の `test_plugin_document_fallback_reports_and_preserves_output` |
| 既定・ファミリー・ファイル・可変フォント | sample/export 環境で実際に選んだフェイスのハッシュと座標 | `tests/test_canonical_sampling.py` のフォント識別ケース |

古いアセットを拒否するかは、前述の返されたマニフェストを使って呼び出し側が決めます。自動的な refuse-stale 出力フラグはありません。オフラインの検証では、プラグインコールバックや出力先の変更前に判断材料が得られることを確認し、その古いバイトで描画するという選択を別に検証します。キャッシュなしでは失敗し、別のフォントや空のテクスチャには置き換えません。

`uv run --locked pytest tests/test_asset_cache.py tests/test_plugin_runtime.py
tests/test_plugin_svg.py tests/test_canonical_sampling.py --no-cov -q` を実行してください。既存の自動品質ジョブ `pytest tests/` に含まれています。シナリオ名とパラメーター ID が問題のリソース・文書を特定します。期待ハッシュは管理したソースのバイトから計算し、描画サンプルは同じ記録済みフォント・描画環境で比較します。マシンやネイティブビューアー間で同じフォントピクセルになることは保証しません。
