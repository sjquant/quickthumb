---
description: 使用 quickthumb 从 JSON 规范渲染而成的 1080×1920 Shorts 封面，并附带生成该封面的完整规范定义。
---

# Shorts / 竖版封面 { #shorts-vertical-cover }

![竖版封面，带有倾斜的手机模型展示裁切照片，配有“Turn long videos into Shorts”文案](../assets/examples/shorts_cover_agent.png)

一款整套设计均使用 JSON 文件声明的 1080×1920 封面。Python 端仅负责加载并执行渲染，这正是通过大语言模型（LLM）或模板系统生成排版时的典型使用方式。

安装 [uv](https://docs.astral.sh/uv/) 并克隆代码仓库即可运行此示例：

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/shorts_cover_agent.py
```

该脚本将写入 `examples/shorts_cover_agent.png`，并覆盖同名旧文件。

## 构成方式 { #how-its-built }

- **同一张照片，复用两次。** 同一张图片分别以 16:9 横向裁切显示，并置于手机屏幕内部。`"fit": "cover"` 会将其自动裁切以适应各个画框的形状。
- **手机模型由两个图层构成。** 深色的圆角矩形作为机身外壳，上层的照片作为屏幕内容。两者以及屏幕上的三个标签均设置了 `"rotation": 3`，从而保持一致的倾斜角度。
- **素材路径相对于代码仓库根目录。** 例如 `assets/images/denise-jans-WIRvXd1PYlg-unsplash.jpg`。脚本在渲染前会自动切换至仓库根目录，因此支持在任意工作目录下运行。
- **背景添加了轻微胶片颗粒。** 使用带有固定 `seed` 的 `grain` 效果，确保每次渲染都能得到完全确定的颗粒质感。

## 规范定义 { #the-spec }

```json
--8<-- "examples/shorts_cover_agent.json"
```

## 脚本代码 { #the-script }

```python
--8<-- "examples/shorts_cover_agent.py"
```

`Canvas.from_json()` 会在绘制任何像素前严格校验规范，因此格式错误的规范会抛出指出具体错误字段的 `ValidationError`。规范支持的完整字段列表请参阅 [JSON Schema 与 AI 工作流](../json-schema.md)。
