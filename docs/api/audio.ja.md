---
description: quickthumbで音の立ち上がりとRMS音量を解析し、タイミングの基準点やスケールトラックを再利用できるアニメーションJSONに記録します。
---

# 音に反応するアニメーション { #audio-reactive-authoring }

`quickthumb.audio.analyze_audio(path, cache_dir=None)`は、制作前にローカル音声を解析します。FFmpegが必要です。急激な音の立ち上がり時刻と、ソースに対するRMS振幅を持つ検証済み`AudioAnalysis`を返します。オンセットは音量が急増する点であり、音楽の**ビートの格子やテンポの推定ではありません**。

オンセットを通常の数値の`TimingSpec.start`として使います。これにより、サンプリング、JSONの復元、ワーカー描画時にサウンドトラックオプションへ依存しません。

```python
from quickthumb import AnimationSpec, ColorTrack, KeyframeSpec, TimingSpec
from quickthumb.audio import analyze_audio

analysis = analyze_audio("music.wav")
if analysis.onsets:
    motion = AnimationSpec.timeline(
        ColorTrack(keyframes=[
            KeyframeSpec(time=0, value="#102030"),
            KeyframeSpec(time=0.2, value="#42CEB7"),
        ]),
        timing=TimingSpec(start=analysis.onsets[0], duration=0.2),
        easing="linear",
    )
```

`motion`をレイヤーの`animation=`へ設定します。実行できる[`examples/audio_onsets.py`](https://github.com/sjquant/quickthumb/blob/main/examples/audio_onsets.py)は、シーン、解析のサイドカーファイル、正規JSON、同じ音源をサウンドトラックにしたMP4を作ります。数値として記録したモーションは`inspect_motion()`でも検査でき、各対象の既存の色トラック対応か明示された代替を使います。HTMLはサウンドトラックを再生せず、GIFも無音です。事前に記録したタイミングは、これらの形式でリアルタイムの音声同期を保証するものではありません。

## ソース時刻とRMS { #source-clock-and-rms }

時刻は、最初にデコードした音声ストリームの先頭からの秒数です。値はソースの振幅を表します。無音ならRMSは0でオンセットはありません。オンセットのない音源もあるため、添字で読む前に`onsets`を確認してください。

??? info "解析の解像度とオンセット検出"
    8 kHzへ再サンプリングしたモノラル音声を、連続した160サンプル（20 ms）の窓で解析します。`rms[i]`は`i * 0.02`に始まる窓の線形RMS振幅です。最後の窓は短い場合があります。値は音源ごとに正規化したものではなくソースの振幅です。無音ならRMSは0でオンセットもありません。

    バージョン付きの検出器は、RMSが0.01を超え、直前の窓と直前10窓の平均の両方の2倍を超えるアタックを要求します。基準点の間隔は100 ms以上です。基準の過渡音は20 msの1窓以内でテストしています。緩やかな立ち上がりや音楽の裏拍では基準点が生成されないことがあります。添字でアクセスする前に`onsets`を確認してください。

出力ゲイン、音楽のループ・フェードアウト、ナレーション、ほかのミックス音声はソース解析を変えません。Deckの時刻はスライド内のものなので、サウンドトラックのオンセットを対象スライドの時刻へ変換する必要があります。出力オプションを変えても、基準点を自動で繰り返したり移したりはしません。

## 音量でスケールを変える { #loudness-driven-scale }

`AudioAnalysis.scale_track(min_scale=1.0, max_scale=1.15)`は通常の`ScaleTrack`を返します。`AnimationSpec.timeline()`へ渡してください。保存済みRMSからモーションへ変換するときに、音楽や解析器を再参照しません。

```python
pulse = AnimationSpec.timeline(
    analysis.scale_track(min_scale=1.0, max_scale=1.4)
)
```

各RMSを解析内で最も大きい窓の振幅で割り、指定したスケール範囲へ対応付けます。無音は`min_scale`、ピークは`max_scale`に対応し、全体が無音なら`min_scale`のままです。ソース内での正規化なので、静かな録音と音量を上げた複製が同じ反応を作る場合があります。出力音量には依存しません。両端は有限の正の数で、`max_scale >= min_scale`が必要です。

各キーフレームは、短い最後の窓も含め、自分の20 ms窓の間だけ値を保持します。アタック前の補間はしません。ソースの正確な終了時刻にもう1つキーを置いて`min_scale`へ戻すため、最後の大きなパルスが静止区間や次のスライドに残りません。推定されるアニメーション長は`analysis.duration`です。明示する`TimingSpec`はこの全長を許容する必要があります。`start`は切り詰めではなく、ソース時刻全体をずらします。

生成されたトラックは通常の正規JSONです。`sample()`、`inspect_motion()`、ワーカー、出力処理は既存のスケールトラックとして扱います。動きを抑える設定ではこのトラックを抑制し、作成時の静的な形を保ちます。HTML/PPTXは宣言されたスケール対応範囲に従い、リアルタイムの音楽再生や同期が追加されるわけではありません。実行例はオンセットによる色変化と音量による拡縮を、元音声付きMP4にまとめます。

## 保存して再利用する { #store-and-reuse }

```python
from pathlib import Path
from quickthumb.audio import AudioAnalysis

Path("analysis.json").write_text(analysis.model_dump_json(), encoding="utf-8")
stored = AudioAnalysis.model_validate_json(Path("analysis.json").read_text())
```

レコードにはスキーマ・アルゴリズムのバージョン、ソースSHA-256、FFmpegのバージョン、サンプリングパラメーター、長さ、順序付きオンセット、RMS窓が含まれます。スキーマは`AudioAnalysis.model_json_schema()`で取得できます。サイドカーと文書JSONへ記録したモーションは、元音声やFFmpegなしで読み込み、サンプリングできます。音声の出力には引き続き元ファイルと通常のメディアツールが必要です。

`analyze_audio`自体にはFFmpegが必要で、`QUICKTHUMB_FFMPEG`でバイナリを指定できます。システム一時ディレクトリの`quickthumb-audio`か指定した`cache_dir`に、ソースのバイト、アルゴリズム、固定パラメーター、FFmpegのバージョンを識別情報としてキャッシュします。書き込みはアトミックです。ソースやデコーダー・アルゴリズムの版が変わると新しい項目になります。破損した項目では、削除すべきファイルを示すエラーになります。消去されうるキャッシュに頼らずサイドカーを保管すると、デコーダー更新後も制作結果を固定できます。

入力は64 MiB、デコード後の音声は10分までです。解析のタイムアウトは60秒です。ファイルなし、音声でない入力、未対応FFmpegフィルター、制限超過は、対処できるエラーとして失敗します。黙って解析を途中で切ることはありません。この制限は制作時の作業量を制限し、描画の長さを制限するものではありません。
