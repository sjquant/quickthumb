---
description: quickthumb 格式保真度与验证机制参考。
---

# 格式保真度与验证 { #format-fidelity-and-validation }

[导出参考](../exports.md) · [输出格式选择指南](../output-guide.md)

## 可选的静态 SVG 保真度报告 { #optional-static-svg-fidelity-report }

当当前任务有明确的验收指标要求时，可通过 `ExportPolicy` 请求进行 CairoSVG 对比校验。必须显式指定全部三项限制参数；系统不提供内置格式容差预算。下述示例要求可见 RGBA 完全精确一致，而非依赖特定应用针对边缘或字体的宽容度：

```python
from quickthumb import Canvas, ExportPolicy

policy = ExportPolicy(fidelity={"svg": {
    "pixel_tolerance": 0,
    "max_different_pixel_ratio": 0,
    "min_hash_similarity": 1,
}})
canvas = Canvas(160, 90).background(color="#123456")
result = canvas.export("checked.svg", policy=policy)
comparison = result.pixel_metrics.fidelity
print(comparison.verdict, comparison.pixel_diff_ratio, comparison.hash_similarity)
```

仅当所选 SVG 导出明确请求该校验时，才需要安装可选依赖 `quickthumb[svg]` 及系统级 Cairo。报告会记录 CairoSVG/Cairo 版本、规范渲染环境、应用的阈值以及实际光栅化尺寸。比对直接针对创作时的静态 `sample()` 静止帧进行，不作任何缩放。`exact` 表示所有可见 RGBA 通道完全匹配；`tolerated` 表示满足所给的相异像素比例与均值哈希限制；`out_of_policy` 表示超出阈值或尺寸不匹配。平均绝对误差（MAE）在四个通道上进行归一化计算，同时也会报告最大通道差值。完全透明的像素会忽略隐藏的 RGB 分量，因此这里的精确一致定义与规范原始像素 SHA-256 完全相等是有区别的。8×8 均值哈希在白色背景上合成；即使哈希值完全一致，RGBA 测量也能独立捕获 Alpha 通道丢失。

此功能仅用于生成报告：即便判定结论为 `out_of_policy`，原始 SVG 仍会正常写入磁盘。保真度诊断仅客观记录观测结果，不会自动触发新的光栅降级回退。若缺少基准渲染器或基准渲染失败，会在打开目标文件前抛出异常，从而完好保留已存在的文件。默认导出及非 SVG 导出不会执行此项比对。

该观测结果仅适用于记录环境下的 Cairo 静态渲染。由于 Cairo 使用系统已安装字体且不解析嵌入的 CSS `@font-face`，因此相同的字体环境必须单独提供；详情请参见 [CairoSVG 官方文档](https://cairosvg.org/documentation/)。它不构成对浏览器、HTML 或动画保真度的保证。SVG 依然保持其原有的创作时静态动效行为。

## 可选的静态 PDF 保真度报告 { #optional-static-pdf-fidelity-report }

Canvas PDF 导出在 `"pdf"` 键下接收相同的三个明确限制参数：

```python
policy = ExportPolicy(fidelity={"pdf": {
    "pixel_tolerance": 0,
    "max_different_pixel_ratio": 0,
    "min_hash_similarity": 1,
}})
result = Canvas(160, 90).background(color="#123456").export("checked.pdf", policy=policy)
print(result.pixel_metrics.fidelity.verdict)
```

安装 `quickthumb[pdf]` 可获取 ReportLab 以及可选的 PDFium 观测工具。默认 PDF 导出不会导入 PDFium。请求比对时，会在透明 RGBA 底上以 1 倍缩放渲染实际生成的 PDF 字节：该导出器每个规范像素对应 1 个 PDF 点，而非按 96-DPI 进行打印尺寸换算。报告中记录了 PDFium 及其绑定库版本、以点为单位的实际页面尺寸、页数、渲染尺寸以及规范环境。原生的 PDFium 文档/渲染/清理调用在各线程间串行化执行；规范渲染与像素比对保持在该全局锁之外。校验要求刚好只有一页且具有预期的点尺寸；即便在宽松的像素阈值下，尺寸不匹配仍会被判为超出策略（`out_of_policy`）。系统绝不会通过缩放或强制压平到白色背景来掩盖 Alpha 或几何信息丢失。

此处同样适用前述可见 RGBA/哈希标准与纯报告行为。若 Canvas 输出意外产生了多页结果，测量指标仅针对第一页进行，而报告的页数会直接导致判定为超出策略。PDF 生成与所请求的比对均在打开目标路径前完成；若观测工具缺失或执行失败，已存在的目标文件将得到保留。无论保真度判定如何，原生文本/矢量图元以及带有原因说明的光栅切片均予保留。原生的 PDF 文本是可搜索的矢量内容；这并不承诺提供 PowerPoint 式的对象可编辑性。Deck PDF 的比对请求会被明确拒绝；如有需要请逐一导出其 Canvas 幻灯片。此观测结果同样不能用于证明 PPTX 或动画保真度。

## PPTX 兼容性 { #pptx-compatibility }

PPTX 会尽可能将受支持的文本与形状保持为可编辑状态。发光效果可作为固定图片与该可编辑内容并存；在编辑文字后需重新导出以更新发光图。带有外边框的内容可能需要将多个对象一同编辑或重新导出。

以下效果组合会将受影响的图层直接导出为图片：

- 带有描边/发光效果的半透明文本、形状或外边框。
- 带有描边/发光效果的渐变填充形状。
- 带有发光效果的富文本，或同时叠加发光与投影的内容。
- 发光扩散范围延伸超出幻灯片边缘的形状。

带有不透明线性渐变的文本可以保留其可编辑的填充与描边。仅每个文本片段实际使用的着色方案决定其是否为半透明；未生效或被覆盖的颜色设置不会破坏可编辑性。

在导出前可调用 `canvas.validate_export("pptx")` 检查兼容性，或在导出后检查返回凭据中的 `capability_report` 查看兼容决策。混合了可编辑前景与固定效果的对象标记为 `support="partial"`；完整的图层图片标记为 `support="fallback"`。返回凭据字段详见[文档图层路由机制](export-methods.md#document-layer-routing)。

`ExportPolicy(pptx={"title": "native"})` 会针对 ID 为 `title` 的图层拒绝此类效果图片或混合表示形式。`ExportPolicy(unsupported_motion="error")` 同样会拒绝这些效果降级。Canvas 与 Deck 的 `to_pptx(policy=...)` 会执行与文件导出相同的策略检查。默认配置允许带有原因说明的降级回退。

## HTML 浏览器验证工具套件 { #html-browser-validation-harness }

该仅供开发人员使用的测试套件借助显式指定的 Chrome 与 Node 内置 WebSocket，捕获实际导出的 Canvas 以及包含两张幻灯片的 Deck 舞台画面。它不会自动安装浏览器，也不会更改 `ExportPolicy`：

```bash
PYTHONPATH=. python scripts/check_html_fidelity.py \
  --chrome "/path/to/chrome" --output /tmp/quickthumb-html-observations
```

输出目录必须为新建目录。Chrome 在无头模式下使用临时用户配置和环回 CDP 运行；套件绝不会连接到已存在的浏览器会话。套件会等待字体、图片和幻灯片转场加载就绪，在 DPR 为 1 的条件下仅捕获原始尺寸的舞台，并在 0 秒、5 秒和 10 秒捕获由真实点击触发的 CSS 淡入淡出动画。报告中记录了浏览器/Node 版本、规范环境、输入资源哈希、执行路由诊断、尺寸、时间轴定位点、显式固件阈值、像素/哈希指标及判定结论。规范/浏览器生成的 PNG 图像一并保存在其同级目录下。

涵盖文本/形状/图像/遮罩的混合固件允许通道容差为 16，最多 8% 的相异像素，以及至少 0.94 的平均哈希相似度。每个组件还必须满足各自区域记录的标准：文本允许 20% 的相异像素且要求哈希相似度达到 0.95；原生椭圆允许 2% 且要求达到 0.98。嵌入图像必须完全一致；遮罩切片仅允许 1 个通道阶次的舍入误差。文本与椭圆的通道容差为 16。这些局部区域标准能够防止微小缺失被全舞台平均指标所掩盖。阴性对照组在宽屏 Canvas 与竖屏 Deck 中分别移除各个文本/图像/遮罩/椭圆元素，必须精确在该特定区域触发测试失败，而非仅仅在某个全局指标上体现。所有容差均为固件专属设定，绝非通用的文档预算。简单的淡入淡出动效仅允许 1 个通道阶次的舍入误差；故意损坏的文档必须在比对中失败。若出现预期外的判定结论，命令将报错退出并保留报告。不会执行任何自动光栅降级或浏览器/CI 安装操作。

该套件观测的是单一 Chrome/字体/平台环境以及一个受限的 CSS 动画，而非覆盖所有浏览器、所有动画、交互提示或 Deck 转场。CairoSVG 无法替代该浏览器观测套件。现有的 Node 运行时测试将调度与状态机行为与浏览器像素比对分开独立测试。

## 静态跨格式导出对比矩阵 { #static-cross-export-checks }

`tests/test_static_export_matrix.py` 将同一份创作内容输入公开的 Canvas 与 Deck 文件导出边界进行测试。首张 160×120 幻灯片组合了仓库内置字体文本、原生矩形、生成图像与椭圆遮罩；第二张 Deck 幻灯片包含透明画布上的半透明矩形。该测试清晰区分了实测外观与结构性证据：

| 格式 | Canvas | Deck | 功能支持与降级证据 |
| --- | --- | --- | --- |
| PNG | 解码后的 RGBA 与规范采样完全一致 | 各带编号幻灯片与各自规范采样一致 | 光栅输出；不对原生对象或文档查看器一致性作任何保证 |
| SVG | 实测 CairoSVG 观测记录，配合原生文本/矢量与 PNG 检查 | 单文件 Deck SVG 被直接拒绝；各 Canvas 幻灯片分别测量 | 执行源 ID、原生路由及带有原因说明的图像/遮罩 PNG 路由 |
| HTML | 舞台标记、原生文本/CSS 与精确遮罩 PNG | 舞台数量与幻灯片局部路由 | 仅作结构检查；此矩阵中不进行浏览器像素测量 |
| PDF | 实测 PDFium 观测记录、可搜索文本、矢量路径与图像对象 | 页数/几何尺寸、原生对象与渲染组件区域 | 报告 Canvas 路由；Deck 执行路由与凭据保真度暂未收集 |
| PPTX | 可编辑 OOXML 文本/形状与精确放置的遮罩 PNG | 幻灯片数量及每页原生/光栅对象 | 报告执行路由；PowerPoint/Keynote 实际呈现暂未测量 |

混合 SVG/PDF 测试固件采用明确的全图限制：0 通道容差，最多 8% 相异像素，以及至少 0.94 的哈希相似度。这些属于固件专用的字体/边缘预算，而非导出默认值。原生文本必须以文本实体存在，且小矩形、图像及遮罩内部区域必须完全精确匹配，确保缺失组件无法隐藏在全图平均预算中。文本区域还要求哈希相似度至少为 0.95，并在针对字体光栅化边缘应用 16 的通道容差后允许最多 30% 相异像素。包含可搜索白底白字的真实 Deck PDF 即使其文本对象与其余组件区域完好无损，也必须在该区域检查中报错失败。仅针对透明矩形，Alpha 通道必须完全精确匹配，而可见 RGB 因渲染器的预乘/反预乘舍入误差通道差值允许最多 2 个阶次。完全隐藏的 RGB 遵循现有的可见 RGBA 比对规则；PNG 依然精确保留原始 RGBA 数据。不会对任何输出进行尺寸缩放或压平到人为添加的底衬上。

运行命令：`uv run --locked pytest tests/test_static_export_matrix.py --no-cov -q`。现有质量工作流已在安装了 SVG/PDF/PPTX 可选依赖及原生 Cairo 的环境下，通过 `pytest tests/` 运行该测试文件。缺少可选观测工具的本地环境会标注依赖原因跳过对应用例。Pytest 用例 ID 标识格式与文档类型。每个用例在其临时目录中保留源 JSON、规范 PNG、实际导出文件及 JSON 凭据；测得的凭据包含渲染器版本、规范环境、限制参数与各项度量指标。测试失败可基于共享固件与指定格式检查完整复现，无需依赖平台相关的截屏基线。

这是一个受限的静态对比矩阵。它不会运行浏览器，不认证 PPTX 查看器的像素/字体/时序，也不增加 Deck PDF 保真度策略。独立的 HTML 浏览器测试套件与原生演示文稿查看器观测需要各自的执行过程与环境证据。结构检查的成功绝不能直接等同于已渲染像素保真度的判定结论。

## Lottie 参考播放器 { #lottie-reference-player }

验证范围和已知差异请参阅[播放验证](export-lottie.md#playback-verification)。

```bash
uv sync --locked --extra lottie --dev
npm ci --prefix tests/fixtures/lottie/player --ignore-scripts --no-audit --no-fund
PYTHONPATH=. uv run --locked python scripts/check_lottie_fidelity.py \
  --chrome /path/to/chrome \
  --player tests/fixtures/lottie/player/node_modules/lottie-web/build/player/lottie.min.js \
  --output /tmp/quickthumb-lottie-observations
```

### 重新运行 Android native graphics

使用网页检查的 manifest 以及现有 JDK 21、Maven 3.9+。Maven 会获取测试专用依赖。

```bash
PYTHONPATH=. uv run --locked python scripts/check_lottie_android.py \
  --maven /path/to/mvn --java-home /path/to/jdk-21 \
  --cases /tmp/quickthumb-lottie-observations/cases.json \
  --output /tmp/quickthumb-android-observations
```
