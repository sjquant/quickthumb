---
description: ベクターロゴのアニメーション、描き進む輪郭線、再利用できるイントロを作ります。
---

<a id="lottie-vectors"></a>

# Lottieアニメーション { #lottie-animations }

[エクスポートリファレンス](../exports.md) · [出力形式を選ぶ](../output-guide.md)

形が変わるロゴ、描き進む輪郭線、タイトルと動くバッジのイントロを作れます。
Canvasを`.lot`に出力し、Lottieプレーヤーでベクターとして再生します。
動画のフレーム画像や閲覧側のフォントファイルを配布する必要はありません。

## 形が変わるロゴを作る { #create-a-shape-changing-logo }

```python
from quickthumb import (
    AnimationSpec,
    Canvas,
    KeyframeSpec,
    LottieOptions,
    PathMorphTrack,
    TimingSpec,
)

square = "M20 20 H80 V80 H20 Z"
diamond = "M50 10 L90 50 L50 90 L10 50 Z"
morph = AnimationSpec.timeline(
    PathMorphTrack(keyframes=[
        KeyframeSpec(time=0, value=square),
        KeyframeSpec(time=1, value=diamond),
    ]),
    timing=TimingSpec(duration=1),
    easing="ease_in_out",
)
Canvas(120, 120).path(
    square, (10, 10), 100, 100, "#159A8C",
    view_box=(0, 0, 100, 100), animation=morph,
).export("logo.lot", animation=LottieOptions(fps=24, hold=0.5))
```

正方形からひし形へ1秒で変わり、0.5秒停止します。2つのパス、色、サイズ、easingを変えて使ってください。

<a id="playback-verification"></a>

## Webで再生する { #play-it-on-the-web }

Webプロジェクトに`lottie-web@5.13.0`をインストールし、
`<div id="logo" style="width:120px;height:120px"></div>`などのコンテナーを用意します。
公開アセットに`logo.lot`を配置して再生します：

```javascript
import lottie from "lottie-web";

lottie.loadAnimation({
  container: document.getElementById("logo"),
  renderer: "svg",
  loop: true,
  autoplay: true,
  path: "/logo.lot",
});
```

塗り・線・レイヤーの不透明度を正しく組み合わせるには`renderer: "svg"`を使います。
lottie-web 5.12.2/5.13.0のCanvasには不透明度の結合不具合があります。
公開前にサイトやアプリの対象プレーヤーで確認してください。基準バージョンと再実行方法は
[開発者向け検証](export-validation.md#lottie-reference-player)を参照してください。

## 完成したイントロを再利用する { #reuse-a-complete-intro }

リポジトリのルートから実行すると、輪郭化したタイトル、描いた後に円へ変わるロゴ、
回転するバッジを含む2秒のイントロを作れます：

```bash
pip install 'quickthumb[lottie]'
python -m examples.lottie_intro /tmp/intro.lot
```

最後に0.5秒停止します。[イントロ例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_intro.py)の
タイトル、色、パス、回転を変更して再利用してください。閲覧側のフォントは不要です。

## アートワークと時間を選ぶ { #choose-artwork-and-timing }

単色背景・図形、塗り・線・穴のあるSVG Pathに、位置・スケール・回転・不透明度のトラックを組み合わせます。
[静的図形](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_static.py)、
[曲線Path](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_paths.py)、
[動く図形](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_motion.py)から始められます。

`LottieOptions(fps=24, hold=0.5)`は24 fpsで動きをサンプリングし、最後に0.5秒停止します。
既定は30 fps、最大120です。高くすると動きが細かくなり、ファイルも大きくなります。
各ポーズは次のサンプルまで維持されます。出力結果でフレーム数と長さを確認できます。

## Lottieパスモーフィング { #lottie-path-morph }

`PathMorphTrack`に塗り、線、不透明度、変換、トリムを組み合わせられます。
曲線には[ロゴモーフィング例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_morph.py)を応用してください。

全パスの輪郭数と開閉状態をそろえます。`view_box`には曲線・制御点・線の余白を取り、
線付きパスは均一に拡縮します。形状や作業量のエラーが出たら、案内に従ってview boxを
広げる、パスを単純にする、fpsを下げるなど調整してください。[Pathモーフィング](../api/path.md#path-morphing)も参照できます。

## Lottieの線トリム { #lottie-stroke-trim }

`TrimEndTrack`で輪郭を描き進めます。上のロゴ例に続けて実行します：

```python
from quickthumb import TrimEndTrack

outline = AnimationSpec.timeline(
    TrimEndTrack(keyframes=[
        KeyframeSpec(time=0, value=0),
        KeyframeSpec(time=1, value=1),
    ]),
    timing=TimingSpec(duration=1),
    easing="ease_in_out",
)
Canvas(120, 120).path(
    square, (10, 10), 100, 100, None,
    view_box=(0, 0, 100, 100), stroke="#159A8C", stroke_width=3,
    animation=outline,
).export("outline.lot", animation=LottieOptions(fps=24, hold=0.5))
```

見える区間を動かすには`TrimStartTrack`と`TrimOffsetTrack`を使います。静的な
`trim_start`、`trim_end`、`trim_offset`も使えます。0から1はモーフィング中も輪郭順の
全パス長を示し、オフセットは両方向へ循環します。0→1は全体を描き、同じ端点や1→0は
線を隠します。塗りは完全なままです。単色実線を使い、切った端は`line_cap`で選びます。
短すぎる区間で精度エラーが出たら区間を広げてください。[トリム例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_trim.py)も参照できます。

## 図形をまとめて動かす { #move-shapes-together }

ShapeをNullへ`parent`で結ぶと、図形をまとめて回転・移動できます。
[親子関係の例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_parenting.py)から始めてください。
子の描画順と不透明度は独立しています。全体をフェードするには各子の不透明度を動かします。
百分率位置はCanvas基準です。親のない動く図形の作成ポーズはCanvas内に置きます。
親付き図形は外から入れられます。親子関係はShapeとNullで使えます。

## Lottieの文字アウトライン { #lottie-outlined-text }

`quickthumb[lottie]`で、静的な1行の印刷可能ASCIIタイトルを輪郭化できます。閲覧側に
フォントは不要です。変更するときは元のタイトルを編集して再出力します。
[文字例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_text.py)のようにローカルの
アウトラインフォント、不透明な文字色、複数文字では0以外の`letter_spacing`を使います。
半透明にはレイヤーの`opacity`を使い、タイトルは回転・親子関係なしで配置します。
動く文字や多言語の文字には[動画出力](../output-guide.md)を選んでください。

## 出力前に互換性を確認する { #check-compatibility-before-exporting }

既存のデザインには先に`canvas.validate_export("lottie")`を実行します。グラデーション、
画像、エフェクト、文字アニメーションなど変更が必要なレイヤーとフィールドを報告します。
出力時にもサンプル形状と精度を書き込み前に確認するため、拒否時は既存ファイルを保護します。

ベクターLottieには上の作例の図形とトラックを使います。画像やエフェクトも保つ場合は
[動画出力](../output-guide.md)を選んでください。Lottie出力は黙って画像に置き換えません。

静止版には正の`hold`と`ExportPolicy(reduced_motion=True)`を使います。
最終ポーズではなく作成時のアートワークを出力します。
