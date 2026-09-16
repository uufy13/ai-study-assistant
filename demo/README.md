# Demo 示例

本目录演示 AI Study Assistant 的输入与输出。

所有示例内容均为虚构/脱敏，不包含真实教材、私人资料或真实密钥。

## 文件说明

| 文件 | 用途 |
|---|---|
| `input-machine-learning.md` | 用户输入资料示例（课堂讲义风格，Markdown） |
| `output-machine-learning.md` | 模拟 `ai-study-assistant` 生成的笔记（展示样例） |
| `input-example.docx` | DOCX 输入示例（标题/段落/列表/表格，虚构内容） |
| `input-example.pdf` | PDF 输入示例（两页文本，虚构内容） |
| `input-example.pptx` | PPTX 输入示例（标题/正文/表格，虚构内容） |

## 如何运行

1. 先完成项目配置（`config.yaml` + `.env`），见根目录 `README.md`。
2. 运行（任选其一）：

```bash
# Markdown
uv run ai-study-assistant demo/input-machine-learning.md -o notes/

# DOCX / PDF / PPTX
uv run ai-study-assistant demo/input-example.docx -o notes/
uv run ai-study-assistant demo/input-example.pdf -o notes/
uv run ai-study-assistant demo/input-example.pptx -o notes/
```

3. 生成的笔记位于 `notes/<输入文件名 stem>.md`，例如 `demo/input-example.docx` → `notes/input-example.md`。

## 注意

`output-machine-learning.md` **只是展示样例**，不是真实运行产物。
不同模型（provider/model）的输出结构、详略、措辞会有所不同，
请以你自己的运行结果为准。
