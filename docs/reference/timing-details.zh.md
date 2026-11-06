---
description: 规范采样、GIF/视频播放、Deck 旁白以及交互式 HTML 的时间轴处理机制。
---

# 动画时序参考 { #animation-timing-reference }

简要指南请参见[动画时序](../timing.md)。

对于创作动效、幻灯片持续时长、静止保持时间（hold）、视频放置以及字幕提示，统一采用以秒为单位的数值。`sample()` 观测规范基准时间轴；`export()` 报告实际编码的视觉时间轴。这两项度量具有不同用途。

## 选择时钟源 { #choose-the-clock }

| 输出或观测方式 | 时序契约 |
| --- | --- |
| 未指定时间或 fps 的 `sample()` | 每张 Canvas/页面捕获一帧创作时的静态画面，与光栅输出一致，无需定位动画终点；`duration=0`，帧 `time=None`。 |
| `sample(time=...)` | 观测显式指定的文档时间点。幻灯片时间窗口为 `[start, end)`；精确的分界点归属于新入场的幻灯片。超出终点的时间点显示最终定型的静止画面。 |
| `sample(fps=...)` | 观测时间轴终点之前的均匀网格 `0, 1/fps, 2/fps, …`。长度为 0 的时间轴仍会在时刻 0 观测一次。 |
| GIF | 无声，以 10 毫秒为步阶的可变帧时长；相同帧可被合并。默认采样帧率为 20 fps；受支持的帧率必须大于 0 且最高为 100 fps。 |
| MP4 / WebM / MOV | 恒定速率编码帧，包含重复填充的静止保持帧。默认 30 fps；受支持的帧率必须大于 0 且最高为 120 fps。 |
| HTML | 浏览器驱动的交互式提示与幻灯片页面导航。无编码 fps 或固定的总播放时长，且不播放 Deck 旁白语音。 |

`GifOptions.fps` 与 `VideoOptions.fps` 用于请求采样密度。运动跨度在其自身的时序边界内进行采样；静态跨度成为保持镜头。视频在累积帧时钟上分配重复帧，而 GIF 将累积时长量化为厘秒（10 毫秒）。因此，规范的均匀采样网格并非编码文件的帧索引：任意浮点时间跨度、调色板/有损编码以及重复帧合并均可能改变最终文件的帧位置或帧总数。

动画导出完成后，请查阅 `ExportResult.timing_metrics`：

| 字段 | 含义 |
| --- | --- |
| `fps` | 选定的采样帧率；对于 GIF 而言，该值并非存储的总帧数除以播放时长。 |
| `frame_count` | 实际编码的帧数（经过 GIF 帧合并或视频保持帧重复展开之后）。 |
| `duration` | 编码后的视觉播放秒数：即所有 GIF 延迟之和，或视频帧数除以 fps。音频容器的封装填充可能会产生微小出入。 |

`FrameSequence.duration` 描述的是未量化的规范时间轴。HTML 在 `timing_metrics` 中不返回固定播放时序；其返回的 0 持续时间并不代表其交互式动画不消耗时间。

```python
from quickthumb import AnimationSpec, Canvas, GifOptions

canvas = Canvas(160, 90).background(color="#000000").shape(
    "rectangle", (40, 20), 80, 50, "#FF0000",
    animation=AnimationSpec.fade(duration=1),
)
samples = canvas.sample(fps=7, hold=0.37)
result = canvas.export("timed.gif", animation=GifOptions(fps=7, hold=0.37))
print(samples.duration, len(samples.frames))
print(result.timing_metrics.model_dump())
```

## 时间曝光（动态模糊） { #temporal-exposure }

在导出 Canvas 或 Deck 时可选择开启居中动态模糊：

```python
from quickthumb import MotionBlur, VideoOptions

canvas.export(
    "exposure.mp4",
    animation=VideoOptions(fps=30, motion_blur=MotionBlur(samples=8, shutter_angle=180)),
)
```

`GifOptions` 与 `ImageSequenceOptions` 同样支持该配置。`None` 是唯一的关闭配置；`MotionBlur` 接收 2–64 个采样点以及最高 360 度的正数快门角度。快门跨度覆盖每个渲染帧周围 `(angle / 360) / fps` 秒的时间区间。落在文档时间轴之外的瞬间使用其边界状态。硬切转场将曝光限制在快门中心所在一侧的幻灯片；精确处于硬切点的瞬间归属于新入场的幻灯片。平滑转场参与曝光计算，包含其起始时刻两侧的采样点。视频与图像序列的曝光中心遵循输出网格 `index / fps`；GIF 中心遵循其可变时长的镜头时钟。在返回直通 RGBA 之前，先对编码 sRGB 预乘通道求平均，从而在透明拖尾中保留高饱和度色彩。

曝光还会将带时序的字幕与入场动效进行时间积分。它们可以在距离提示边界半个快门窗口的范围内产生影响。创作的提示时刻与播放总长度保持不变；GIF 延迟与视频帧数依然遵循各编解码器的时钟。在 hold 为 0 时，最后一帧仍处于动态曝光之中。如需展示完全静止的定型画面，请添加正数的 hold 时间。

该设置支持 Canvas 与 Deck 的 GIF/视频导出及图像序列（包含开启 `workers` 多进程的情况）。每个工作线程计算完整的曝光，采用与串行渲染完全一致的采样时间点与 Alpha 累积算法。直接返回字节的辅助方法不支持此设置。`sample()` 与 `render_frame()` 依然保持为瞬时规范观测。导出凭据在其功能报告中指明所请求的时间曝光；源文档检查无法推断仅在导出时生效的设置。

### 支持情况与凭据记录 { #support-and-receipts }

`capabilities_for(target)["motion_blur"]` 声明了时间曝光的支持情况：

| 目标系列 | 支持状态 | 含义 |
| --- | --- | --- |
| `video` | full（完全支持） | Canvas/Deck MP4、WebM、MOV 及图像序列均会积分时间曝光。 |
| `raster` | partial, static fallback（部分支持，静态降级） | 动画 GIF 会积分曝光；静态光栅文件没有曝光窗口。 |
| `html`, `pptx` | unsupported, static fallback（不支持，静态降级） | 忽略曝光设置；创作的浏览器/PowerPoint 动效保持不变。 |

`VideoOptions` / `GifOptions` 属于各自动画输出系列；将其传递给 HTML/PPTX 会抛出选项系列冲突错误。能力支持表并不意味着这些选项会被静默接受。`inspect_motion()` 报告源创作特性，不会声明启用了仅导出有效的模糊。在实际导出后，可在 `result.capability_report` 的 `motion_blur` 行中查看实际应用的采样数与快门角度；`timing_metrics` 保留编码后的播放数据。图像序列导出结果同样携带该生效配置行及其帧数/时长数据。

运行[动态标记示例](https://github.com/sjquant/quickthumb/blob/main/examples/motion_blur.py)可生成对照的关闭/8采样 GIF 文件。该场景同时驱动了受控的[采样开销基准测试](https://github.com/sjquant/quickthumb/blob/main/benchmarks/README.md#temporal-exposure-cost)。

## 幻灯片持续时长与转场 { #slide-duration-and-transitions }

图层动效与新入场转场在同一幻灯片时钟上启动。对于非交互式媒体，`on_click` 提示会像 `after_previous` 一样依次顺畅执行；`with_previous` 提示同步重叠执行。延迟时间均属于这些时钟的一部分。转场在前一张幻灯片的静止画面之上播放；未显式指定转场的幻灯片在首页立即起始，后续幻灯片使用 0.5 秒淡入淡出转场。如需立即切换的硬切边界，请使用 `Cut()`。

幻灯片的离场时刻由适用的最晚时间边界决定：

- 既无指定时长又无 `advance_after` 时，转场与图层动效播放完毕后，静止定型画面保持 `hold` 秒（默认为 3 秒）。
- 对于 Deck 视频，`slide(duration=...)` 设定包含转场与动效在内的全局幻灯片窗口。未显式指定时长时，由旁白音频提供该窗口。二者都不会强制裁剪更长的视觉动画；幻灯片总时长足够容纳二者播放完毕。旁白自身会被裁剪或以静音补齐至其规划的时间窗口。
- 转场的 `advance_after` 替代 `hold`：其边界从新入场转场完成后开始起算。离场时刻取该边界、动效完成时刻与任何旁白/显式指定时长三者中的最晚时刻。例如，带有 `Cut(advance_after=0.1)` 的 1 秒动画在 `hold=3` 时仍会在 1 秒时刻准时结束，不会额外附加 3 秒尾巴。

GIF 会忽略 Deck 旁白及 `slide(duration=...)`；它直接基于动效、转场、`advance_after` 和 `hold` 推进。`Deck.sample()` 采用感知旁白的视频排期，因此带旁白的 Deck 所生成的 GIF 时长无需与其采样时长完全一致。

即使设置 `hold=0`，编码器也会展示定型静止状态，在需要时替换最后一个运动镜头，而非总是机械追加完整的保持帧。静态或短于一帧的幻灯片仍然需要一个能够表示的帧。因此，GIF 和视频的实际时长可能会与纯数学时间轴存在微小出入。Deck 视频当前要求对于既无旁白又无显式正数时长的幻灯片设置正数的 `hold`；零保持时间对于 Canvas 和 Deck GIF 依然完全有效。

## 音频、字幕与减弱动态效果 { #audio-captions-and-reduced-motion }

MP4/WebM/MOV 支持混音视频剪辑原生音频、Deck 旁白以及可选背景配乐。旁白从所在幻灯片的绝对时间偏移处开始播放。背景音乐会被裁剪至视觉时间轴总长度并支持循环；来自音频编解码器的封装填充不会延长报告的视觉播放时长。GIF 与图像序列不包含任何音频。当配乐或旁白必须伴随动效呈现时，请选用视频格式。MP4 导出在播放图层动画与转场的同时完整保留每页旁白。如需静态画面配旁白，请构建静态 Canvas 并设置 `deck.transition(Cut())`。

视频图层的 `start` 是幻灯片局部的。其 `trim_start`、`trim_end` 和 `speed` 决定源媒体时间的选取；字幕的 `start`/`end` 相对于放置后的剪辑片段计算，而非源文件绝对时间。字幕在 `[start, end)` 区间内激活，并直接烧录在受支持的光栅/视频输出的前景画面中。当开启减弱动效导致画面冻结时，字幕时序依然保持正常运作。

`ExportPolicy(reduced_motion=True)` 会抑制创作的图层动效与创作的幻灯片转场。它完好保留保持时间、旁白和字幕时序；幻灯片之间可保留默认的 Deck 淡入淡出转场。最终时长请以实际导出凭据为准，而非原有的动效时长。

HTML 保持 `on_click` 提示为交互式触发，`after_previous` 提示为自动触发。`advance_after` 支持在新入场转场完成后开启条件化自动切页；它并不会把演示文稿变成固定时长的视频。视频图层在 HTML 中使用静态降级回退，因此不会重现其播放/字幕时序。请通过 `validate_export()` 及返回的降级诊断查看目标格式的具体支持情况。GIF/视频选项系列冲突、不受支持的透明度以及编解码器帧率限制均会抛出具有明确指导意义的错误，绝不静默改选其他格式。

## 播放验证 { #verify-playback }

`tests/test_video_layers.py` 中的三页集成测试场景全面检验了实际的 GIF、MP4 与 WebM 输出：将选定像素与规范采样进行比对，验证新入场转场、字幕起始/结束时间窗口、编码时序以及解码后的背景配乐与旁白音频频率。减弱动态效果用例检验了冻结的画面图像与带时序的字幕。请在安装了 FFmpeg 和 ffprobe 的环境中运行：

```bash
uv run --locked pytest tests/test_video_layers.py -k motion_package --no-cov
```

现有的 HTML 时间轴测试在 Node 舞台固件中执行 JavaScript；针对特定浏览器的保真度检验属于独立的测试流程。
