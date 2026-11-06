---
description: quickthumb 采样、资源管理与渲染复现性参考。
---

# 采样、资源与可复现性 { #samples-assets-and-reproducibility }

[导出参考](../exports.md) · [输出格式选择指南](../output-guide.md)

## 规范采样 { #canonical-samples }

`sample()` 方法以支持 JSON 序列化的 `FrameSequence` 形式返回与具体渲染器无关的基准参考，供导出结果进行比对。Canvas 与 Deck 遵循完全相同的契约，对单张 Canvas 进行采样与对仅包含该 Canvas 的单页 Deck 采样的观测结果完全一致。

```python
still = canvas.sample()                         # settled frame(s), as PNG/PDF/PPTX draw them
timed = deck.sample(fps=10)                     # uniform grid over the whole animated timeline
probe = deck.sample([0.0, 1.25, 4.0], hold=2.0) # explicit instants, ascending
```

- **图像帧**：每个 `CanonicalFrame` 将 `width * height` 个像素保存为原始 8 位 RGBA（自左上角起按行优先存储，sRGB 色彩空间，直通 Alpha），在 `data` 字段中进行 base64 编码，并附带这些字节的 `sha256` 摘要。`index` 表示该帧在序列中的位置，`slide` 标识其对应的幻灯片页码。若加载时帧的数据摘要或尺寸与实际数据不符，将被直接拒绝。
- **静止画面捕获**（`capture="still"`）：按幻灯片顺序为每页保留一帧画面，采用各页面自身的实际尺寸并完好保留透明度。此时 `time` 为 `None`，`duration` 为 `0`，`timeline` 为空列表。
- **时间轴捕获**（`capture="timeline"`）：观测动画 WebM/MP4 导出实际播放的时间轴：包含转场、Morph、图层动效、由旁白驱动的幻灯片时长，以及未显式指定时长的页面所保持的 `hold` 秒静止状态（默认为 3 秒）。帧按以秒为单位的递增 `time` 排序，共享第一页的舞台尺寸，并合成在不透明的 `matte` 底衬上（默认为黑色，报告为 `#RRGGBB`）。Deck 的 GIF 导出当前会忽略显式及旁白幻灯片时长，因此仅对不包含这些时长的 Deck 与此时间轴完全一致。
- **采样策略**：`fps=N`（最大为 120）观测在 `duration` 之前的所有 `k / N` 瞬时时刻；显式指定的时间点列表必须递增，大于或等于 `duration` 的时间点显示最终定型的静止画面。单次捕获最多观测 100,000 个瞬时点；超出该上限的显式列表或 fps 网格会在渲染任何帧之前抛出 `ValidationError` 予以拒绝。该网格仅为观测采样计划，并非导出器的编码帧计划：各导出器在其专属的帧网格上采样每个跨度，并将短于一帧的幻灯片拉伸为完整一帧。
- **时序语义**：`duration` 为时间轴的精确绝对长度，绝不受 `fps` 或所请求的具体采样点影响。每个 `TimelineSegment` 给出幻灯片精确到纳秒的绝对 `start`、`transition_end`、`animation_end` 及 `end`；幻灯片在 `[start, end)` 时间区间内呈现在屏幕上，因此处于分界点上的瞬间归属于新入场的幻灯片。
- **内存限制**：若捕获产生的去重帧所需的原始 RGBA 内存超过 768 MiB，将抛出 `ValidationError`；对于静止捕获中每页均超限或时间轴捕获中单帧即超限的情况，会在渲染任何帧前立即报错拒绝。请通过减少采样时间点、降低 `fps`、缩短 `hold` 或缩小文档尺寸来解决。
- **运行环境**：`sample()` 与 `export()` 会报告 quickthumb、Pillow、FreeType 版本、文本排版引擎（`basic` 或 `raqm`）、可用的 RAQM/HarfBuzz/FriBidi 版本，对于包含视频图层的文档还会报告 FFmpeg 版本。在缺少可用 FFmpeg 的环境中采样视频图层会在渲染任何帧之前抛出 `RenderingError`。`environment.fonts` 报告该操作实际选用的字形字节数据；资源清单则在独立字段中描述创作时的引用。

## 渲染可复现性 { #render-reproducibility }

字体家族名称与 `QUICKTHUMB_DEFAULT_FONT` 依赖于运行设备上的字体查找路径。请检查实际匹配解析的字体文件，而不要将这些名称视作全局通用的跨平台标识符：

```python
capture = canvas.sample()
for font in capture.environment.fonts:
    print(font.source, font.sha256, font.variations)
```

每个字体记录其实际解析的文件路径（或 `pillow:default`）、SHA-256 哈希值以及按字体轴名称索引的应用的可变坐标。哈希值直接标识实际的字体字节。若 Pillow 内置字体的字节不可用，则不报告哈希值。文件路径仅供诊断参考：请跨设备比对哈希值与可变轴坐标。仅当前操作实际加载的字体会被报告；未使用的命名字体或此前操作加载的字体均会被排除。

远程字体及 Google 字体从解析字节的内容寻址副本中加载，因此其他文档刷新源 URL 不会改变已预取的字体文件。这些副本存放在资源缓存中，遵循由调用方主导的清理生命周期。在执行操作期间，请保持本地输入文件不变。

如需获得高度可重复的规范光栅输出，请确保文档数据、输入资源字节、选定字体及可变轴坐标、渲染选项和运行环境完全一致；并在受支持的程序化效果中显式指定随机种子。不同的字体、文字塑形或光栅化引擎版本可能会改变文字布局与边缘像素细节。该报告旨在完整解释这些输入参数，并不保证跨平台或跨原生输出查看器达到像素级绝对一致。在比对此类输出时，请采用针对具体格式制定的保真度容差标准。

## 远程资源与缓存机制 { #remote-assets-and-caching }

`render()` 与 `export()` 会自动将远程图片、SVG、文本填充及字体下载到共享缓存目录中，且 `export()` 会返回描述其使用过的全部资源的 `asset_manifest`。`prefetch_assets()` 为可选调用：它会提前执行相同的下载并在不执行渲染的情况下直接返回资源清单，以便你在耗时较长的导出任务开始前提前排查网络异常或过期条目，或为离线渲染预热缓存。每个 `AssetManifestEntry` 包含原样记录的 `source`、语义化的 `asset_type`、当前 `status` 以及其可用的标识信息：`source_key`（规范化 URL）、`cache_key` 与 `cache_path`、`content_hash`（所用字节的 SHA-256）以及 `fetched_at`（下载的 UTC 时间戳）。

| `status` | 含义 |
| --- | --- |
| `local` | 已存在的本地文件。 |
| `missing` | 不存在的本地文件路径。 |
| `network` | 本次新下载并写入缓存的资源。 |
| `fresh` | 从处于 `max_age` 有效期内的缓存条目中读取（未设置 `max_age` 时始终为此状态）。 |
| `stale` | 从已过期的缓存条目中读取，或在离线状态下因无法刷新而沿用。`stale_reason` 解释具体原因。 |
| `unresolved` | 尚未解析的远程引用。 |

缓存行为可通过环境变量进行控制：

- `QUICKTHUMB_ASSET_CACHE_DIR`：缓存目录路径（默认使用系统临时目录）。
- `QUICKTHUMB_ASSET_MAX_AGE`：缓存条目从网络刷新前的有效期秒数。当网络刷新失败时，将降级使用旧的缓存字节并报告为 `stale`。未设置时表示缓存条目永不过期。
- `QUICKTHUMB_ASSET_OFFLINE=1`：禁止发起任何网络请求。直接使用现有缓存条目，过期的条目报告为 `stale`。

## 资源所有权与复用 { #ownership-and-reuse }

在 `prefetch_assets()`、`sample()` 与多次导出之间复用相同的 `Canvas` 或 `Deck` 实例，可以实现资源解析结果的持久复用。每个 Canvas 均会保留其初次远程解析的结果与状态；Deck 则复用其各个幻灯片的结果。远程图片、文本填充及 SVG 均直接基于这些保留的字节进行渲染。远程字体（包括 Google 字体）从解析字节的内容寻址副本中加载，因此其他文档对相同 URL 的刷新不会破坏已预取的字体文件。在整个采样与导出期间，请确保这些缓存文件持续可用。如需在当前缓存策略下重新解析相同引用，请构建全新的文档实例。

`PrefetchResult` 与 `asset_manifest` 是支持 JSON 序列化的安全报告，并非操作系统层面的资源句柄。保存或加载它们的 JSON 不会转移实际字节，也不会在后台预加载其他文档。全新文档可以复用磁盘上持久化的缓存，当条目可用时报告为 `fresh`。本地图片、字体、视频及音频路径属于调用方拥有的文件：请确保它们在采样或导出期间持续存在且未被修改；预取操作不会冻结或复制本地文件。预取不会下载视频与音频源文件；远程视频在需要时由 FFmpeg 直接读取，不属于该缓存契约管辖。没有文件/URL 引用的生成式内容不会产生外部资源条目。

调用方全权负责缓存目录的管理与其清理工作。Quickthumb 会原子化写入远程缓存文件与元数据，但不会自动主动淘汰它们。仅当文档和导出工作进程均不再使用该缓存时，方可清理无用条目；已生成的清单属于客观观测记录，并不保证其记录的 `cache_path` 永久存在。内存中缓存的远程结果无需显式调用关闭方法：它们会随文档对象的销毁自动释放。

当既不存在可用的缓存条目又无法获得网络响应时，资源解析将抛出 `RenderingError`，并明确指出发生故障的资源源、失败原因以及所搜索的缓存目录。若业务上需要严格拒绝陈旧过期的资源，可在渲染前检查清单：

```python
prefetched = canvas.prefetch_assets()
stale = [entry for entry in prefetched.asset_manifest if entry.status == "stale"]
if stale:
    raise SystemExit(f"stale assets: {[(e.source, e.stale_reason) for e in stale]}")
```

## 资源与插件生命周期测试固件 { #asset-and-plugin-lifecycle-fixtures }

`tests/test_asset_cache.py` 中的共享字体/纹理测试场景使用私有插件注册表、仓库内置 TTF 字体以及由临时本地 HTTP 服务器提供的生成式图像字节。它们全面验证了公开的 Canvas/Deck 操作与缓存环境变量配置。通过受控的标准虚拟时钟推进过期时刻，无需真实睡眠等待，也无需手动篡改缓存文件或元数据。无需连接公网服务，亦无需平台专属的像素截屏基线。

| 测试场景 | 观测证据 | 回归校验用例 |
| --- | --- | --- |
| 网络下载 → 全新文档有效复用 → 过期重新刷新 | 解析状态、获取时间戳、变更后的内容哈希、实际字体标识与解码后的 PNG 像素；原始文档保留其已解析字节 | `test_combined_resources_refresh_only_for_new_expired_documents`（`canvas`、`deck`） |
| 离线状态下遇到过期缓存 | 在插件执行或文件输出前，两种资源均报告 `stale`，并附带资源源、哈希、获取时间及离线/超时原因；调用方继续执行时无需网络请求即可获得原始 RGBA/字体字节 | `test_combined_offline_stale_evidence_precedes_optional_rendering`（`canvas`、`deck`） |
| 离线冷启动缺少字体或插件纹理缓存 | 公开预取准确定位到后续幻灯片、源 URL 及缓存目录；插件纹理错误同时标识图层/资源路径。不发生任何回调或文件写入 | `test_combined_cold_offline_failure_identifies_later_slide_resource`（`font`、`texture`） |
| 跨光栅与原生文档输出的预取资源 | Canvas/Deck 光栅输出一致性、实际字体 SHA、资源清单、原生 SVG 文本与精确的插件 PNG 降级 | `test_prefetched_font_and_private_plugin_keep_shared_export_evidence` |
| 缺少已声明的插件依赖 | 转义 JSON Pointer、图层标识及写入前失败 | `test_plugin_declared_missing_assets_fail_before_output_or_callback` |
| 插件原生匹配、容差范围内差异、不匹配或不支持的目标 | 实测本地 SVG 对比与所采用的原生/PNG 呈现；带说明的降级与严格拒绝策略 | `tests/test_plugin_svg.py`，`tests/test_plugin_runtime.py` 中的 `test_plugin_document_fallback_reports_and_preserves_output` |
| 默认字体、家族字体、本地文件与可变字体 | 采样/导出环境中实际选中的字体哈希与应用的可变轴坐标 | `tests/test_canonical_sampling.py` 中的字体标识用例 |

如前所述，是否拒绝陈旧过期资源是由调用方根据返回的清单自行决定的；系统不提供自动拒收过期资源的导出开关。离线测试固件验证了在触发任何插件回调或更改输出目标之前即可完整获取这些证据，随后分别验证调用方选择使用这些陈旧字节进行渲染时的行为。缺少缓存的冷启动会直接报错失败，绝不擅自替换为系统默认字体或空白插件纹理。

运行命令：`uv run --locked pytest tests/test_asset_cache.py tests/test_plugin_runtime.py tests/test_plugin_svg.py tests/test_canonical_sampling.py --no-cov -q`。这些测试均已纳入现有的自动化 `pytest tests/` 质量流水线。测试用例名称与参数化 ID 准确定位具体的资源/文档失败原因；预期哈希基于受控源字节计算得出，渲染采样在记录的相同字体与渲染环境中进行比对。这并不承诺在跨机器或跨原生查看器时字体像素绝对分毫不差。
