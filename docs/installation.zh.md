---
description: 安装 quickthumb，添加针对 SVG、PDF、PPTX、视频、背景移除及 CLI 的可选额外依赖，并检查运行环境。
---

# 安装 { #installation }

quickthumb 需要 Python 3.11 或更高版本。

## 独立虚拟环境 { #isolated-environment }

在 quickthumb 源码仓库之外的独立虚拟环境中安装 quickthumb 0.8.0：

```bash
mkdir -p quickthumb-first-export
cd quickthumb-first-export
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "quickthumb==0.8.0"
```

在 Windows 上，请改用 `.venv\Scripts\activate` 激活虚拟环境。
上述 shell 命令适用于 Bash/Zsh。安装依赖需要连接 Python 包索引或事先准备好所需的本地缓存。在源码目录外运行可确保 Python 导入的是已安装的 wheel 包而非源码目录。

### 已有的 uv 项目 { #existing-uv-project }

```bash
uv add "quickthumb[cli]>=0.8.0"
```

基础包已足以满足 PNG、JPEG、WebP、GIF、SVG 输出以及 HTML 需求。
在添加可选渲染器之前，建议先尝试[渲染第一组卡片](getting-started.md)。安装完成后，该示例无需下载任何字体或图片。

## 可选额外依赖 { #optional-extras }

部分功能需要额外依赖包。可以通过名称安装，例如 `pip install "quickthumb[svg,pdf]"`。

| 额外依赖 | 用途 |
| --- | --- |
| `svg` | 将 SVG 文件绘制为图层。导出*为* SVG 不需要此额外依赖。 |
| `pdf` | PDF 导出以及可选的 PDF 保真度检查。 |
| `pptx` | PowerPoint 导出。 |
| `lottie` | 在 Canvas Lottie 导出中支持文字轮廓；仅包含形状的 Lottie 不需要此依赖。 |
| `rembg` | 移除图片背景。首次使用时会下载约 170 MB 的模型。 |
| `cli` | `quickthumb` 命令行工具，包括 `render`、`lint`、`watch` 和 `doctor`。 |

导出 MP4、WebM 和 MOV 还需要安装 [ffmpeg](https://ffmpeg.org/)，这是系统级程序而非 Python 包：

```bash
brew install ffmpeg      # macOS
sudo apt install ffmpeg  # Debian / Ubuntu
```

MOV 导出需要包含 `prores_ks` 编码器的 FFmpeg 构建版本。

SVG 图层还需要系统的原生 Cairo 库；Python 额外依赖不会安装系统级库。平台具体要求请参阅 [CairoSVG 安装指南](https://cairosvg.org/documentation/)。

## 检查运行环境 { #check-your-environment }

`quickthumb doctor`（来自 `cli` 额外依赖）可探测导出所需的各项依赖要求：

```bash
quickthumb doctor            # PNG, the default
quickthumb doctor mp4        # discover ffmpeg/ffprobe
quickthumb doctor pdf --spec card.json -o out/card.pdf
```

若某项必要检查未通过，命令将以状态码 1 退出，因此它也很适合作为 CI 检查步骤。该命令不会实际渲染测试文件，也不会保证原生库、编解码器支持或视觉保真度。请同时执行实际的导出任务。详情参阅[诊断与 CLI](diagnostics.md#quickthumb-doctor)。

## 开发源码安装 { #development-checkout }

如需体验未发布的改动，请在代码仓库中运行 `uv build`，然后使用绝对路径将生成的 wheel 包安装到独立虚拟环境中，例如 `python -m pip install "/path/to/dist/quickthumb-0.8.0-py3-none-any.whl[cli]"`。这样安装的是本地代码而非下载已发布的发行版。从 0.7.0 升级时请参阅 [0.8.0 迁移说明](releases/0.8.0.md#migration-from-v070)。

## 环境变量 { #environment-variables }

均为可选设置。

| 变量 | 作用 |
| --- | --- |
| `QUICKTHUMB_FONT_DIR` | 当 `font` 指定为字体家族名称时要搜索的字体文件目录 |
| `QUICKTHUMB_DEFAULT_FONT` | 文本图层未指定 `font` 时使用的默认字体 |
| `QUICKTHUMB_FONT_CACHE_DIR` | 下载字体的缓存目录（默认：系统临时文件夹） |
| `QUICKTHUMB_ASSET_CACHE_DIR` | 下载图片的缓存目录（默认：系统临时文件夹） |
| `QUICKTHUMB_ASSET_MAX_AGE` | 缓存下载项重新刷新的间隔秒数。未设置表示永不过期。 |
| `QUICKTHUMB_ASSET_OFFLINE` | 设为 `1` 时禁止网络下载；仅使用已缓存的文件 |
| `QUICKTHUMB_FFMPEG`, `QUICKTHUMB_FFPROBE` | 当 `ffmpeg` 和 `ffprobe` 不在 `PATH` 中时指定其路径 |

[远程资源与缓存](reference/export-assets.md#remote-assets-and-caching)更详细地说明了缓存机制。
