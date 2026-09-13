# Demo 示例

本目录演示 AI Study Assistant 的输入与输出。

## 文件说明

| 文件 | 用途 |
|---|---|
| `input-machine-learning.md` | 用户输入资料示例（课堂讲义风格） |
| `output-machine-learning.md` | 模拟 `ai-study-assistant` 生成的笔记（展示样例） |

## 如何运行

1. 先完成项目配置（`config.yaml` + `.env`），见根目录 `README.md`。
2. 运行：

```bash
uv run ai-study-assistant demo/input-machine-learning.md -o notes/
```

3. 生成的笔记位于 `notes/input-machine-learning.md`。

## 注意

`output-machine-learning.md` **只是展示样例**，不是真实运行产物。
不同模型（provider/model）的输出结构、详略、措辞会有所不同，
请以你自己的运行结果为准。
