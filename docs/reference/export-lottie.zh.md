---
description: 将变换形状的徽标、自绘制轮廓以及动态图形导出为 Lottie 矢量动画文件。
---

<a id="lottie-vectors"></a>

# Lottie 动画 { #lottie-animations }

[导出参考](../exports.md) · [输出格式选择指南](../output-guide.md)

将变换形状的徽标、渐进自绘制的轮廓以及动态图形导出为适用于各类 Lottie 播放器的矢量动画。生成的 `.lot` 文件包含标准 Lottie JSON 数据，不包含任何嵌入的光栅帧图像或音频。

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

此代码创建了一个从正方形平滑变形为菱形（持续 1 秒），随后静止停顿 0.5 秒的动画。在正式发布之前，建议在目标 Lottie 播放器中实际预览效果。如需查看带有曲线、填充及描边的完整徽标示例，请运行[徽标变形示例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_morph.py)。

## 选用图元与时序控制 { #choose-artwork-and-timing }

单个 Canvas 可包含纯色背景、纯色几何形状、SVG 路径、位置/缩放/旋转/不透明度动画、描边修剪以及受支持的静态文本。形状包括矩形、圆角矩形、椭圆、胶囊形、三角形、星形及多边形。路径支持 `M/L/H/V/C/S/Q/T/A/Z` 指令、纯色填充/描边，以及基于奇偶填充规则的孔洞镂空。

`LottieOptions.fps` 默认为 30，最高支持 120。更高的 fps 可提供更平滑精细的运动步阶，但也会增加文件体积。系统按照设定的采样帧率并在创作的关键帧/事件边界上对动效进行离散采样；每个姿态画面保持显示直到下一次采样。播放器本身不会在这些采样点之间进行平滑插值。静态艺术图元同样保持纯矢量形态。

`hold` 以秒为单位指定末尾定型停顿时间，必须为非负数。最终总时长为最后动效结束时刻加上该停顿时间，并向上取整为整数帧。即便 hold 为 0 的纯静态 Canvas 也会占据 1 帧。导出凭据中会明确报告总帧数与持续时长。

参考示例：[静态形状](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_static.py)、[平滑曲线路径](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_paths.py)、[动态几何图形](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_motion.py)。

## Lottie 路径变形 { #lottie-path-morph }

`PathMorphTrack` 在保持创作视口（view_box）不变的同时平滑改变路径几何形状。变形过程中可同步伴随填充、纯色描边、不透明度、变换以及描边修剪。在[路径变形限制](../api/path.md#path-morphing)范围内支持开放轮廓、闭合轮廓及嵌套孔洞。

创作的初始路径与所有变形关键帧必须具有相同的轮廓数量和开放/闭合状态。所有采样曲线、其控制点以及描边边缘必须完全容纳在 view_box 视口范围内。某些视觉上看似处于内部的曲线仍可能超出此几何边界；请相应重新缩放或调整其位置。带描边的路径要求使用各向同性的等比 view_box 缩放，且退化的描边轮廓会被拒绝。

规模庞大或结构极度复杂的动画可能会超出 Canvas 全局 100,000 次姿态与轮廓顶点观测上限。若导出报告触碰该上限，请调低 fps 或简化路径。中间过渡帧遵循与 Quickthumb 离线渲染帧相同的近似轮廓计算；精确的创作关键帧端点则精确保留其原始贝塞尔曲线。

## Lottie 描边修剪 { #lottie-stroke-trim }

使用 `TrimEndTrack` 可逐步绘制出轮廓线条，或使用 `TrimStartTrack` 与 `TrimOffsetTrack` 让可见线段沿路径流动。同样支持静态的 `trim_start`、`trim_end` 和 `trim_offset`。参见[描边修剪示例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_trim.py)。

修剪位置沿路径总长度按轮廓顺序从 0 映射至 1。偏移量（offset）支持环绕循环，取值可为负数或大于 1。0→1 的全区间保留完整描边（不受 offset 影响）；两端点重合或 1→0 会完全隐藏描边。底部的填充始终保持完整。闭合接缝保留其连接样式；被切断的端点使用指定的端点样式（cap）。暂不支持虚线及虚线偏移相位动画。若极小的修剪区间在播放器舍入后会被完全隐去或明显错位端点，可能会被拒绝。

## 形状组合协同联动 { #move-shapes-together }

使用 `parent` 属性可层级联动受支持的 Shape 与 Null 图层，参见[父级绑定示例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_parenting.py)。子图层跟随父级图层的变换运动，同时保持各自独立的绘制层级顺序与不透明度。父级图层的不透明度不会让子图层淡出。包括子图层在内的百分比坐标均相对于 Canvas 根画布进行解析。路径图层暂不支持父级绑定。

未绑定的动画形状在动画开始前必须完全处于 Canvas 边界之内。已建立绑定的形状可以在 Canvas 外部起始，只要父级变换最终将其带入可视区域即可。不支持非正数的各向同性 Shape/Null 缩放；独立轴缩放保留常规行为，包含镜像翻转与扁平塌陷。

## Lottie 轮廓化文本 { #lottie-outlined-text }

安装 `quickthumb[lottie]` 可将静态、单行且仅含可打印 ASCII 字符的文本纳入导出。文本会被整体转换为矢量轮廓：查看端无需安装对应字体，但无法作为文本进行编辑。纯形状与纯路径导出无需此项额外依赖。参见[轮廓化文本示例](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_text.py)。

请选用不透明文字着色方案，并使用包含所需全部字形的本地非可变、非彩色字体。遇到不受支持的字形将直接报错。暂不支持文本动画、父级绑定、旋转、自动折行/缩放自适应、富文本、动态计数器、图层效果、遮罩、渐变、远程字体以及复杂脚本文字塑形。在 RAQM 排版引擎下，多字符文本需显式指定非零的 `letter_spacing`；未指定字距的 BASIC 文本要求字符步进累计等于总宽度。每个图层最多允许 1024 个字符、65,536 个轮廓顶点以及 64 MiB 的字体源文件。

## 导出前预先校验兼容性 { #check-compatibility-before-exporting }

调用 `canvas.validate_export("lottie")` 可全面扫描并定位不受支持的图层与字段。导出流程在打开目标路径前即会拒绝不受支持的内容，从而完好保留已存在的目标文件。某些处于中间过渡态的变形错误、浮点精度异常或资源超限问题仅在正式编译动画时才能被发现。

渐变、图层效果/预设、stagger 交错动效、遮罩、视口裁剪、色彩/虚线轨道、运动路径、图片、插件以及 Deck 输出均不受支持。Lottie 导出绝不会自动替换为静态画面或光栅回退切片，即便导出策略中显式请求也是如此。系统不提供 Lottie 文件反向导入、ZIP 归档打包或对既有 Lottie 文件的二次编辑功能。

`ExportPolicy(reduced_motion=True)` 会将创作时的静态设计画面导出并保持 `hold` 秒。它不会自动选择动画的最终姿态，其余不受支持的功能特性仍需显式移除。

## 播放验证 { #playback-verification }

参考播放器是 **lottie-web 5.13.0 SVG** 和 **Lottie Android 6.7.1**。Android 检查
在 Robolectric 4.17、Android 15/API 35、mdpi、native graphics 中执行官方库的
software Drawable。这是 Linux/JVM native Skia 验证，不是真机、模拟器、ARM 或 GPU 测试。

保留原有 31 个正常帧和 13 个空白/冻结对照，新增 6 帧和 2 个对照，覆盖不同 contour
长度、空/完整/环绕区间、负 offset、morph 长度变化和重叠的半透明 stroke。
9 个文件须通过 schema 1.0.1 验证；每个播放器须通过 37 个正常帧和 15 个对照。

保持通道容差 32、差异像素不超过 8%、哈希相似度至少 0.93，同时检查整帧和绘图区域。
这些限制并不保证所有作品。额外探索中，一个带半透明 fill 的多 contour morph 帧
未通过 Android 区域哈希限制；长度变化和共用半透明 stroke 使用独立回归示例验证。

**网页请使用 SVG 渲染器。** Canvas 5.12.2/5.13.0 在部分半透明场景中仍有不透明度组合
差异。iOS native、Android 真机、ARM/GPU 和实际应用性能尚未验证。
参阅[重新运行检查](export-validation.md#lottie-reference-player)，发布前在目标播放器中预览。
