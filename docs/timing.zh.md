---
description: 在 quickthumb 中控制动画时长、幻灯片转场、声音与回放。
---

# 动画时间控制 { #animation-timing }

以秒为单位设定动画和幻灯片的持续时间。可导出为无声循环的 GIF、带声音的动态视频，或具有交互性的 HTML 演示文稿。

## 场景动效与定格时长 { #animate-and-hold-a-scene }

以下示例让一个矩形在一秒内淡入，随后将最终画面定格两秒。脚本会在工作目录下写入 `timed.gif`，并覆盖同名旧文件：

```python
from quickthumb import AnimationSpec, Canvas, GifOptions

canvas = Canvas(320, 180).background(color="#102030").shape(
    "rectangle", (80, 40), 160, 100, "#42CEB7",
    animation=AnimationSpec.fade(duration=1),
)
canvas.export("timed.gif", animation=GifOptions(hold=2))
```

导出 MP4、WebM 或 MOV 时，请使用 `VideoOptions(hold=2)`。视频导出需要安装 FFmpeg。
`GifOptions` 和 `VideoOptions` 还支持通过 `fps` 设置帧率，默认值分别为 20 和 30。GIF 格式不包含音频。环境安装请参阅[输出格式](output-guide.md)。

## 幻灯片时长与转场 { #slide-duration-and-transitions }

Deck 会先播放每页幻灯片的图层动效及入场转场，随后在画面定格后停留 `hold` 秒（默认 3 秒）。后续幻灯片默认使用 0.5 秒的交叉淡入淡出（crossfade），除非指定其他转场；`Cut()` 则表示无过渡直接硬切。

对于 Deck 视频导出，`slide(duration=...)` 用于指定该页幻灯片的总时间窗口（包含入场转场与动画）。未显式提供时长时，可由旁白音频长度决定该时间窗口。若视觉动画较长，会允许其完整播放结束；旁白音频则会根据所排定的时间窗口进行裁剪或补齐静音。GIF 导出将忽略幻灯片旁白和 `slide(duration=...)`。

在转场上指定 `advance_after` 会取代常规的 hold 定格等待；幻灯片仍会等待自身的动画、视频旁白或显式时长执行完毕。关于精确的时间边界规则，请参阅[时间控制详解](reference/timing-details.md#slide-duration-and-transitions)。

## 音频、字幕与减弱动态效果 { #audio-captions-and-reduced-motion }

MP4、WebM 和 MOV 支持包含受支持的剪辑音频、幻灯片旁白以及背景音乐原声带。GIF 为完全静音。视频剪辑字幕使用相对于所放置剪辑的时间戳，并烧录进受支持的视频帧中。

使用 `ExportPolicy(reduced_motion=True)` 时，会禁用人工编写的图层动效与转场，但保留定格时长（holds）、旁白和字幕时间点。Deck 默认的交叉淡入淡出转场可能会保留。HTML 演示文稿保留交互点击提示，但不会播放 Deck 旁白，并将视频图层渲染为静态单帧。请务必在目标应用中测试导出文件。

## 时间曝光（动态模糊） { #temporal-exposure }

要为 GIF、视频或图像序列添加运动模糊效果，可向对应的导出选项传递 `MotionBlur`：

```python
from quickthumb import MotionBlur, VideoOptions

canvas.export(
    "exposure.mp4",
    animation=VideoOptions(fps=30, motion_blur=MotionBlur(samples=8, shutter_angle=180)),
)
```

运动模糊是一项导出设置；HTML 和 PowerPoint 不支持复现该效果。
`MotionBlur` 接受 2–64 次采样，快门角度须大于 0 且不超过 360 度。关于时间计算、格式支持和导出报告，请参阅[运动模糊参考](reference/timing-details.md#temporal-exposure)。

### 格式支持与导出报告 { #support-and-receipts }

导出后可读取 `result.capability_report` 检查实际应用的运动模糊情况，并通过 `result.timing_metrics` 查看编码后的回放指标。详情参阅[支持对照表](reference/timing-details.md#support-and-receipts)。

## 选择时钟基准 { #choose-the-clock }

`sample()` 观察的是原始设计的时间轴；由于格式特性的限制，编码后的 GIF 或视频在时长或总帧数上可能会有轻微偏差。HTML 是交互式播放而非固定时长视频。如果对精确帧时间或导出指标有严格要求，请参阅[采样与时间参考](reference/timing-details.md#choose-the-clock)。

## 验证回放效果 { #verify-playback }

导出完成后，请在目标分享应用中实际播放该文件，仔细核对幻灯片切换、字幕、声音以及结尾定格。如需检查精确时间，请查阅 `result.timing_metrics`；[时间控制参考](reference/timing-details.md#verify-playback)中也介绍了项目的回放测试方法。
