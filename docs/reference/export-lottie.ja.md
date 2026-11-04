---
description: 形が変わるロゴ、自動で描かれる輪郭線、動く図形をLottieベクターアニメーションとして作ります。
---

<a id="lottie-vectors"></a>

# Lottieアニメーション { #lottie-animations }

[エクスポートリファレンス](../exports.md) · [出力形式を選ぶ](../output-guide.md)

形が変わるロゴ、描き進む輪郭線、動く図形を、Lottieプレーヤー向けベクターアニメーションへ出力します。`.lot`は標準Lottie JSONで、フレーム画像や音声を埋め込みません。

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

正方形からひし形へ1秒で変わり、その後0.5秒停止します。公開前に対象プレーヤーで確認してください。曲線、塗り、線を使う例は[ロゴモーフィング](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_morph.py)を実行してください。

## アートワークと時間を選ぶ { #choose-artwork-and-timing }

1つのCanvasに単色背景・図形、SVG Path、位置・スケール・回転・不透明度のアニメーション、線トリム、対応する静的文字を含められます。図形は長方形、角丸長方形、楕円、カプセル、三角形、星、多角形です。パスは`M/L/H/V/C/S/Q/T/A/Z`、単色の塗り・線、偶奇規則の穴に対応します。

`LottieOptions.fps`は既定30、最大120です。大きくすると動きが細かくなり、ファイルも大きくなります。この間隔と作成したキー・イベントの境界でサンプリングし、各ポーズを次のサンプルまで維持します。プレーヤーはその間を滑らかには補間しません。静止画像もベクターのままです。

`hold`は最後の停止を秒で追加し、0以上が必要です。最後のアニメーション終了と保持時間を足し、フレーム単位で切り上げた長さになります。保持0の静的Canvasでも1フレームを使います。出力結果にフレーム数と長さを報告します。

作例：[静的図形](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_static.py)、[曲線Path](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_paths.py)、[動く図形](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_motion.py)。

## Lottieパスモーフィング { #lottie-path-morph }

`PathMorphTrack`は作成時のview boxを維持しながら形を変えます。塗り、単色線、不透明度、変換、線トリムを組み合わせられます。[Pathの制限](../api/path.md#path-morphing)内で、開いた輪郭、閉じた輪郭、入れ子の穴に対応します。

元のPathと全キーで輪郭数と開閉状態を一致させます。サンプルした曲線、制御点、線の余白がすべてview box内に収まる必要があります。見た目で収まっても境界を超える曲線があるので、形を拡縮・再配置してください。線付きPathはview boxの均一な拡縮が必要で、退化した線の輪郭は拒否します。

大きく複雑な動きは、Canvas全体のポーズ・輪郭頂点の観察100,000回を超える場合があります。報告されたらfpsを下げるかパスを単純化してください。途中のモーフィングはQuickthumbのフレームと同じ近似輪郭を使い、正確な作成端点では曲線を保ちます。

## Lottieの線トリム { #lottie-stroke-trim }

`TrimEndTrack`で線を徐々に描き、`TrimStartTrack`と`TrimOffsetTrack`で見える区間を動かせます。静的な`trim_start`、`trim_end`、`trim_offset`も使えます。[線トリムの例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_trim.py)を参照してください。

位置は輪郭順に、全パス長の0から1です。オフセットは循環し、負や1超も可能です。0→1はオフセットに関係なく線全体を保ち、同じ端点や1→0は線を隠します。下の塗りは全体のままです。閉じた継ぎ目はjoin、切った端は選んだcapを使います。破線と破線位相のアニメーションは未対応です。プレーヤーの丸めで消えたり端点が大きく動いたりするほど短いトリム区間は拒否される場合があります。

## 図形をまとめて動かす { #move-shapes-together }

[親子関係の例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_parenting.py)のように、対応するShapeとNullを`parent`で結びます。子は親の変換に従い、描画順と不透明度は独立します。親の不透明度で子はフェードしません。子を含む百分率の位置もCanvas基準です。Pathの親子関係は未対応です。

独立した動く図形は、開始前にCanvas内へ収まる必要があります。親付きなら、親変換で表示領域に入る場合に外から開始できます。Shape/Nullの0以下の均一スケールは未対応です。軸別スケールは反転や潰れを含む通常の動作を保ちます。

## Lottieの文字アウトライン { #lottie-outlined-text }

静的な1行の印刷可能ASCII文字には`quickthumb[lottie]`をインストールします。文字はベクターの輪郭になり、閲覧側にフォントは不要ですが文字として編集できません。Shape/Pathだけならこの追加依存は不要です。[文字アウトラインの例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_text.py)を参照してください。

必要なグリフがすべて入ったローカルの非可変・非カラーフォントと、不透明な文字色を使います。未対応グリフはエラーです。文字のアニメーション、親子関係、回転、折り返し・フィット、リッチテキスト、カウンター、エフェクト、マスク、グラデーション、リモートフォント、複雑な文字のシェーピングは未対応です。RAQMで複数文字を使う場合は0以外の`letter_spacing`を明示します。字間なしBASICでは文字送り幅の加算性が必要です。レイヤーごとに最大1024文字、65,536輪郭頂点、64 MiBのフォントを許容します。

## 出力前に互換性を確認する { #check-compatibility-before-exporting }

`canvas.validate_export("lottie")`で未対応のレイヤーやフィールドを確認できます。出力は保存先を開く前に拒否し、既存ファイルを保護します。途中のモーフィング、精度、リソース上限の一部は、出力のコンパイル時だけ見つかります。

グラデーション、エフェクト・プリセット、stagger、マスク、ビューポートクリップ、色・破線トラック、モーションパス、画像、プラグイン、Deckは未対応です。ポリシーで要求しても静止・ラスターに置き換えることはできません。Lottieの読み込み、ZIP化、既存ファイルの編集は提供しません。

`ExportPolicy(reduced_motion=True)`は作成時の静的な絵を`hold`秒出力します。アニメーションの最終ポーズを選ぶわけではありません。他の未対応機能は取り除く必要があります。
