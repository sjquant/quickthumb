---
description: quickthumbをインストールし、SVG、PDF、PPTX、動画、背景除去、CLIに必要な追加機能と実行環境を準備します。
---

# インストール { #installation }

quickthumbにはPython 3.11以降が必要です。

## 独立した仮想環境 { #isolated-environment }

quickthumbのチェックアウトとは別の場所に仮想環境を作り、quickthumb 0.8.0をインストールします。

```bash
mkdir -p quickthumb-first-export
cd quickthumb-first-export
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "quickthumb==0.8.0"
```

Windowsでは、代わりに`.venv\Scripts\activate`で有効にします。上のシェルコマンドはBash/Zsh向けです。依存パッケージのインストールには、パッケージインデックスへの接続か、必要なファイルが入ったローカルキャッシュが必要です。チェックアウトの外で実行することで、Pythonがソースディレクトリではなくインストール済みwheelを読み込みます。

### 既存のuvプロジェクト { #existing-uv-project }

```bash
uv add "quickthumb[cli]>=0.8.0"
```

基本パッケージだけでPNG、JPEG、WebP、GIF、SVG出力、HTMLを利用できます。追加のレンダラーを入れる前に、[最初のエピソードカード](getting-started.md)を作ってみてください。この例では、インストール後にフォントや画像をダウンロードする必要はありません。

## 追加機能 { #optional-extras }

一部の機能には追加パッケージが必要です。`pip install "quickthumb[svg,pdf]"`のように名前を指定してインストールします。

| 追加機能 | 用途 |
| --- | --- |
| `svg` | SVGファイルをレイヤーとして描画します。SVGへの*出力*には不要です。 |
| `pdf` | PDF出力と、任意で行うPDFの再現性検証に使います。 |
| `pptx` | PowerPointへ出力します。 |
| `lottie` | CanvasのLottie出力で、対応するテキストをアウトライン化します。図形だけのLottieには不要です。 |
| `rembg` | 画像の背景を除去します。初回に約170 MBのモデルをダウンロードします。 |
| `cli` | `render`、`lint`、`watch`、`doctor`などの`quickthumb`コマンドを使えます。 |

MP4、WebM、MOVの出力には[ffmpeg](https://ffmpeg.org/)も必要です。Pythonパッケージではなく、システムにインストールするプログラムです。

```bash
brew install ffmpeg      # macOS
sudo apt install ffmpeg  # Debian / Ubuntu
```

MOVには`prores_ks`エンコーダーを含むFFmpegビルドが必要です。

SVGレイヤーにはネイティブのCairoライブラリも必要です。Pythonの追加機能ではシステムライブラリをインストールしません。[CairoSVGのインストール案内](https://cairosvg.org/documentation/)で各プラットフォームの要件を確認してください。

## 実行環境を確認する { #check-your-environment }

`cli`追加機能の`quickthumb doctor`で、エクスポートに必要な環境を確認できます。

```bash
quickthumb doctor            # PNG, the default
quickthumb doctor mp4        # discover ffmpeg/ffprobe
quickthumb doctor pdf --spec card.json -o out/card.pdf
```

必須の検査に失敗すると終了コード1を返すため、CIにも組み込めます。ただし、テストファイルをレンダリングしたり、ネイティブライブラリ、コーデック対応、見た目の再現性を保証したりはしません。実際に使うエクスポートも実行してください。詳細は[診断とCLI](diagnostics.md#quickthumb-doctor)を参照してください。

## 開発中のチェックアウトを使う { #development-checkout }

未リリースの変更を試すには、リポジトリで`uv build`を実行し、生成されたwheelの絶対パスを指定して独立した環境へインストールします。例：`python -m pip install "/path/to/dist/quickthumb-0.8.0-py3-none-any.whl[cli]"`。公開済みリリースではなく、チェックアウトしたコードがインストールされます。0.7.0から更新する場合は[0.8.0の移行ガイド](releases/0.8.0.md#migration-from-v070)も確認してください。

## 環境変数 { #environment-variables }

すべて任意です。

| 変数 | 役割 |
| --- | --- |
| `QUICKTHUMB_FONT_DIR` | `font`がファミリー名の場合にフォントファイルを探すフォルダー |
| `QUICKTHUMB_DEFAULT_FONT` | テキストレイヤーに`font`がない場合のフォント |
| `QUICKTHUMB_FONT_CACHE_DIR` | ダウンロードしたフォントの保存先。既定はシステムの一時フォルダーです。 |
| `QUICKTHUMB_ASSET_CACHE_DIR` | ダウンロードした画像の保存先。既定はシステムの一時フォルダーです。 |
| `QUICKTHUMB_ASSET_MAX_AGE` | キャッシュをネットワークから更新するまでの秒数。未設定なら更新しません。 |
| `QUICKTHUMB_ASSET_OFFLINE` | `1`ならダウンロードせず、キャッシュされたファイルだけを使います。 |
| `QUICKTHUMB_FFMPEG`, `QUICKTHUMB_FFPROBE` | `PATH`にない場合の`ffmpeg`と`ffprobe`のパス |

キャッシュの詳細は[リモートアセットとキャッシュ](reference/export-assets.md#remote-assets-and-caching)を参照してください。
