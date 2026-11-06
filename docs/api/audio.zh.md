---
description: 使用 quickthumb 分析音频起音（onsets）与 RMS 响度，将时间锚点和缩放轨道烘焙进可复用的动画 JSON 中。
---

# 音频响应式创作 { #audio-reactive-authoring }

`quickthumb.audio.analyze_audio(path, cache_dir=None)` 可在开始排版前预先分析本地音频素材；此功能需要系统安装 FFmpeg。该方法返回一个经过校验的 `AudioAnalysis` 数据记录，包含瞬态起音（onset）时刻列表以及相对于源音频的 RMS 振幅序列。起音检测的是响度的骤增点；它们**并非**音乐节拍网格（beat grid），也**不代表**曲目节奏（BPM）估计。

起音时间点可以直接作为常规数值传入 `TimingSpec.start`。这避免了在时间轴采样、反序列化 JSON 或在多进程渲染 worker 中运行时对原声音频选项产生实时依赖：

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

将 `motion` 绑定至图层的 `animation=` 属性。参考可直接运行的 [`examples/audio_onsets.py`](https://github.com/sjquant/quickthumb/blob/main/examples/audio_onsets.py)，了解如何编排场景、导出分析 sidecar 伴随文件、规范 JSON 以及使用该音频作为原声带导出的 MP4。烘焙出的数值动效还可以通过 `inspect_motion()` 进行检查，并利用各目标格式已有的颜色轨道支持或已声明的降级处理。HTML 演示文稿不会播放原声带；GIF 保持完全静音。烘焙的时间戳在上述两种格式中均不代表实时音频同步。

## 源音频时间轴与 RMS { #source-clock-and-rms }

所有时间点均以秒为单位，从解码后的第一个音频流开头算起。数值描述的是源音频的振幅；完全静音片段的 RMS 值为 0，且不包含任何起音锚点。在通过索引访问 `onsets` 前请先检查其长度，因为某段音频可能完全没有检测到起音点。

??? info "分析精度与起音检测机制"
    音频分析首先将音频重采样为 8 kHz 单声道，并划分为连续的 160 采样点（20 ms）时间窗口。`rms[i]` 即为起始于 `i * 0.02` 秒的时间窗口的线性 RMS 振幅；末尾的最后一个窗口可能会稍短。数值为源音频的绝对振幅，未经单曲归一化。静音具有零 RMS 且不产生起音。

    具有明确版本号的检测算法要求：RMS 突跃幅度（attack）必须大于 0.01，且同时达到前一个时间窗口以及前 10 个窗口均值的两倍以上，两个相邻起音锚点之间至少间隔 100 ms。基准瞬态突跃在一个 20 ms 窗口内部进行验证；平缓渐强的声音或弱拍上的音符不一定会产生锚点。列表中可能不包含任何起音点：通过下标索引前请务必检查 `onsets`。

导出增益、原声带循环/淡出、幻灯片旁白以及其他混音音频不会改变上述源分析结果。Deck 的时间轴以单页幻灯片为局部基准：需要手动将原声带中的全局起音时间换算成目标幻灯片内的局部时间。更改导出选项时，不会自动重复或移动这些时间锚点。

## 响度驱动的缩放 { #loudness-driven-scale }

`AudioAnalysis.scale_track(min_scale=1.0, max_scale=1.15)` 返回一个标准的 `ScaleTrack`。将其传入 `AnimationSpec.timeline()`；在将已存储的 RMS 转换为动效时，无需再次调用原声带或音频分析器：

```python
pulse = AnimationSpec.timeline(
    analysis.scale_track(min_scale=1.0, max_scale=1.4)
)
```

该辅助方法将每个时间窗口的 RMS 振幅除以本次分析中的最大峰值振幅，然后将该比例线性映射到指定的缩放区间。静音映射为 `min_scale`，峰值映射为 `max_scale`，完全静音的分析数据将始终保持 `min_scale`。这属于相对源音频的归一化：小音量录音与大音量版本能生成相同幅度的动态响应，导出音量大小也不会对其产生干扰。上下限均须为有限正数，且 `max_scale >= min_scale`。

每个关键帧在其对应的 20 ms 窗口期内保持当前数值（包括最后一个可能较短的窗口）；在突变到达前不进行插值。在源音频的精确结束点处，会追加一个返回 `min_scale` 的关键帧，确保定格停留期及后续幻灯片不会残留大音量下的放大状态。推导出的动画时长等于 `analysis.duration`。显式声明的 `TimingSpec` 必须允许容纳该完整时长；设置 `start` 会平移整个源时钟轴，而非截断它。

生成的轨道是标准的规范 JSON：`sample()`、`inspect_motion()`、后台 worker 和各导出器均直接复用现有的缩放轨道流水线。减弱动态效果策略会禁用此轨道并保留人工设定的静态几何尺寸。HTML/PPTX 遵循其声明的缩放支持范围，但不会因此获得实时原声音频播放或同步能力。可运行的示例展示了将起音触发的变色动效、基于响度的脉冲缩放与源音频一并封装进 MP4 视频。

## 存储与复用 { #store-and-reuse }

```python
from pathlib import Path
from quickthumb.audio import AudioAnalysis

Path("analysis.json").write_text(analysis.model_dump_json(), encoding="utf-8")
stored = AudioAnalysis.model_validate_json(Path("analysis.json").read_text())
```

数据记录中包含 Schema 与算法版本、源文件 SHA-256 哈希、FFmpeg 版本、采样参数、时长、排序后的起音时刻与逐窗口 RMS 序列。JSON Schema 可通过 `AudioAnalysis.model_json_schema()` 获取。记录在 sidecar 伴随文件与文档 JSON 中的动效，在没有原始音频文件或未安装 FFmpeg 的环境下依然能够被完整反序列化并进行帧采样。只有在实际执行包含音频的最终导出时，才需要源文件及常规多媒体系统工具。

`analyze_audio` 本身依赖 FFmpeg。可通过环境变量 `QUICKTHUMB_FFMPEG` 指定二进制可执行文件路径。工具以源文件字节哈希、算法、固定参数及 FFmpeg 版本作为联合缓存键，将记录缓存至系统临时目录下的 `quickthumb-audio` 文件夹或指定的 `cache_dir` 中。缓存写入具备原子性。若源文件字节或解码器/算法版本发生改变，将生成全新条目；若检测到缓存损坏，会抛出明确指出待清理损坏文件的可操作错误。相比依赖可能会被系统清理的临时缓存，更推荐妥善保存 sidecar JSON 伴随文件，从而在解码器升级后仍能锁定确定性的设计效果。

输入音频限制在 64 MiB 以内且解码后时长不超过 10 分钟。分析超时阈值为 60 秒。若文件不存在、非音频格式、FFmpeg 滤镜不受支持或输入超出上述限制，方法会抛出具有明确操作指引的异常，绝不会静默截断分析内容。此限制仅约束单次创作分析的规模，并不限制最终渲染视频的总时长。
