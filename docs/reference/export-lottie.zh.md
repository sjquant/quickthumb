---
description: 制作矢量徽标动画、自绘轮廓和可复用的片头。
---

<a id="lottie-vectors"></a>

# Lottie 动画 { #lottie-animations }

[导出参考](../exports.md) · [输出格式选择](../output-guide.md)

制作变形徽标、逐步绘制的轮廓，或带标题与动态徽章的片头。
将 Canvas 导出为 `.lot`，即可通过 Lottie 播放器播放矢量图形，
无需分发渲染好的视频帧或查看端字体文件。

## 创建形状变换徽标 { #create-a-shape-changing-logo }

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

正方形在 1 秒内变成菱形，然后停顿 0.5 秒。修改两条路径、颜色、大小或 easing 即可制作自己的徽标。

<a id="playback-verification"></a>

## 在网页播放 { #play-it-on-the-web }

在网页项目中安装 `lottie-web@5.13.0`，添加
`<div id="logo" style="width:120px;height:120px"></div>` 这样的容器，
把 `logo.lot` 放入公开静态资源目录后播放：

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

使用 `renderer: "svg"` 保持填充、描边和图层不透明度的一致性。
lottie-web 5.12.2/5.13.0 的 Canvas 存在不透明度组合缺陷。
发布前在网站或应用的目标播放器中预览。参考版本和复现方法见
[开发者播放器检查](export-validation.md#lottie-reference-player)。

## 复用完整片头 { #reuse-a-complete-intro }

在仓库根目录运行，即可生成包含轮廓标题、自绘后变成圆形的徽标、旋转徽章的 2 秒片头：

```bash
pip install 'quickthumb[lottie]'
python -m examples.lottie_intro /tmp/intro.lot
```

片头最后停顿 0.5 秒。修改[片头示例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_intro.py)的
标题、颜色、路径和旋转即可复用。查看端无需安装字体。

## 选用图元与时序控制 { #choose-artwork-and-timing }

组合纯色背景和形状、带填充/描边/孔洞的 SVG Path，以及位置、缩放、旋转、不透明度轨道。
可从[静态形状](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_static.py)、
[曲线路径](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_paths.py)、
[动态图形](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_motion.py)示例入手。

`LottieOptions(fps=24, hold=0.5)` 按 24 fps 采样，并在末尾停顿 0.5 秒。
默认 30 fps，最高 120。更高的 fps 提供更细致的运动，也会增加文件大小。
每个姿态保持到下一采样点。导出结果报告帧数与时长。

## Lottie 路径变形 { #lottie-path-morph }

`PathMorphTrack` 可与填充、描边、不透明度、变换和修剪组合。
曲线图案可改编[徽标变形示例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_morph.py)。

保持所有路径的轮廓数和开放/闭合状态一致。为曲线、控制点和描边留出 `view_box` 空间，
带描边路径使用等比缩放。如遇几何或工作量错误，请按提示扩大 view box、简化路径或降低 fps。
制作规则见[路径变形](../api/path.md#path-morphing)。

## Lottie 描边修剪 { #lottie-stroke-trim }

使用 `TrimEndTrack` 逐步绘制轮廓。接着上面的徽标示例运行：

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

使用 `TrimStartTrack` 和 `TrimOffsetTrack` 移动可见片段，也可设置静态
`trim_start`、`trim_end`、`trim_offset`。0 到 1 按轮廓顺序映射到总路径长度，
变形时也保持此含义；偏移可双向环绕。0→1 绘制完整描边，同端点或 1→0 隐藏描边。
底部填充保持完整。使用纯色实线，用 `line_cap` 选择切口端点样式。
极短区间触发精度错误时，请增大区间。参见[修剪示例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_trim.py)。

## 形状组合协同联动 { #move-shapes-together }

将 Shape 通过 `parent` 连接到 Null，可让多个形状一起旋转或移动。
从[父级示例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_parenting.py)开始即可。
子图层保留独立绘制顺序和不透明度。整体淡出时，请为各可见子图层设置不透明度动画。
百分比位置以 Canvas 为准。无父级的动画形状在创作姿态下应位于画布内；
有父级的形状可从外部进入。父级连接可用于 Shape 和 Null。

## Lottie 轮廓化文本 { #lottie-outlined-text }

安装 `quickthumb[lottie]` 可将静态单行可打印 ASCII 标题转为矢量轮廓。
查看端无需字体；修改标题时编辑源文件并重新导出。
按[文本示例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_text.py)使用本地轮廓字体、
不透明文字颜色，并为多字符文本设置非零 `letter_spacing`。半透明使用图层 `opacity`。
标题保持无旋转、无父级连接。动态文字或多语言排版请选择[视频输出](../output-guide.md)。

## 导出前预先校验兼容性 { #check-compatibility-before-exporting }

整合现有设计前调用 `canvas.validate_export("lottie")`，查看需要调整的图层和字段，
例如渐变、图片、效果或文字动画。导出时还会在写入前检查采样几何与精度，
因此被拒绝的导出不会覆盖已有文件。

矢量 Lottie 请使用上述图元和轨道。保留图片、效果等内容时请选择
[视频输出](../output-guide.md)；Lottie 导出不会默默将其替换为图片。

静态版本可用正数 `hold` 配合 `ExportPolicy(reduced_motion=True)`。
这会导出创作时的图案，而非动画最终姿态。
