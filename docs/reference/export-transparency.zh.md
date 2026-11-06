---
description: quickthumb 透明视频导出方法、编解码器与 Alpha 通道支持细节参考。
---

# 透明视频 { #transparent-video }

[导出参考](../exports.md) · [输出格式选择指南](../output-guide.md)

## 透明 WebM { #transparent-webm }

VP9 WebM 可通过 `VideoOptions(transparent=True)` 或传递给 `Canvas.to_webm()` 与 `Deck.to_webm()` 的命名关键字参数 `transparent=True` 来保留 Alpha 通道。默认值为 `False`；现有不透明导出保持其底衬和编码器设置。该设置属于导出选项，而非图层或动效自身的属性，因此不会出现在 Canvas/Deck JSON 及 `inspect_motion()` 中；`VideoOptions.model_validate_json()` 及其模型 JSON Schema 暴露了此严格的布尔选项。`validate_export()` 继续描述文档动效能力，而 `render()` 会在不受支持的输出格式上拒绝透明选项。

```python
canvas.render("overlay.webm", animation=VideoOptions(transparent=True))
deck.render("overlay.webm", animation=VideoOptions(transparent=True, render_quality="high", workers=2))
webm_bytes = canvas.to_webm(transparent=True)
options = VideoOptions.model_validate_json('{"transparent": true, "fps": 24}')
```

仅导出的背景底衬被跳过。创作时定义的背景依然可见，空白区域及不同尺寸幻灯片的黑边区域保持透明，且第 0 页幻灯片的转场从透明状态开始呈现。淡入淡出及遮罩转场插值预乘颜色；覆盖与缩放幻灯片采用 source-over Alpha 进行合成。带有关键帧的 Morph 会先将不同尺寸的幻灯片归一化至第一张幻灯片的输出空间，随后对位置、尺寸以及半透明像素进行插值。原有的父级/字幕 Morph 降级限制依然适用。

两种合成渲染质量模式、进程派生工作线程、配乐音轨及 Deck 旁白均可与透明 WebM 协同工作。编码器使用无损 VP9 编码将 RGBA 流式输入 VP9 `yuva420p`，以保护 Alpha 平面。RGBA 到 YUV 的色彩转换可能会导致解码后的 Alpha 产生 1 个 8 位阶次的变动；RGB 仍采用色度抽样（4:2:0），因此源颜色像素并非无损。生成的文件体积可能会大于不透明 WebM。原有的受限帧批次与原子化目标文件替换机制依然有效。透明转场使用临时浮点平面实现高精度的预乘混合；内存占用会随帧尺寸与工作线程数量的增加而增长。MP4、GIF 及文档/光栅输出在写入目标文件前会拒绝此视频选项。PNG 动画序列请使用独立的 [`export_image_sequence()` API](export-frames.md#image-sequences)。

请使用支持 VP9 WebM Alpha 通道的播放器或视频编辑器。若需使用 FFmpeg 检查实际的 Alpha 平面，请务必在输入文件**之前**指定 libvpx 解码器：

```bash
ffmpeg -c:v libvpx-vp9 -i overlay.webm -frames:v 1 -pix_fmt rgba frame.png
```

原生的 VP9 解码器可能仅报告/解码色彩信息；单凭元数据中的 `alpha_mode` 并不能作为透明度得以正确保留的充分证据。回归测试通过 libvpx 解码 RGBA 并对透明、半透明与不透明像素进行严格比对。包含自定义半透明面板与透明四周的叠加层示例请参见 `examples/transparent_lower_third.py`。

## ProRes 4444 MOV { #prores-4444-mov }

Canvas 与 Deck 可使用 FFmpeg 的 `prores_ks` 编码器导出采用固定 ProRes 4444 配置文件的 `.mov` 文件。MOV 始终会播放动画时间轴，包含 Deck 转场与旁白。`transparent` 采用与 WebM 相同的严格布尔选项，默认为 `False`：常规 MOV 合成在底衬之上；启用 Alpha 选项仅会跳过该底衬。创作时的背景、黑边留白、转场、渲染质量模式与工作线程均遵循前述透明 WebM 的行为。

```python
canvas.render("overlay.mov", animation=VideoOptions(transparent=True, fps=24))
deck.export("overlay.mov", animation=VideoOptions(transparent=True, render_quality="high", workers=2))
mov_bytes = canvas.to_mov(hold=2.0, transparent=True)
mov_bytes = deck.to_mov(hold=2.0, transparent=True, soundtrack="music.wav")
```

MOV 保留精确的画布尺寸，无需裁切奇数宽度或奇数高度的画面帧。透明导出采用 4:4:4 色度及 16 位 Alpha 编码（`yuva444p10le`），为 Final Cut Pro、DaVinci Resolve 及 Adobe Premiere 等专业视频剪辑软件提供工业标准的 Alpha 通道保真度。

配乐音轨、每页旁白语音及嵌入的视频音频均编码为 AAC，遵循与动画 MP4 相同的调度、循环、补齐和裁剪规则。无音频输入的 Canvas MOV 仅包含纯视频轨道。Deck MOV 即使在所有幻灯片均无旁白时，依然保留现有旁白工作流的静音 AAC 底轨。固定的编解码器/配置文件及音频选择不提供外部配置接口。ProRes 文件的体积可能会显著大于 WebM/MP4，且需要支持 ProRes 的播放器或剪辑工具。编码分段保持受限尺寸，且只有在完整编码与混流成功后才会替换目标文件。若系统缺少 `prores_ks` 编码器，将抛出渲染错误并完整保留原有的目标文件。请直接解码像素来验证 Alpha 通道，而非依赖配置文件元数据：

```bash
ffmpeg -i overlay.mov -frames:v 1 -pix_fmt rgba frame.png
```

`examples/transparent_lower_third.py` 同时演示了 WebM 与 ProRes MOV 叠加层的导出。
