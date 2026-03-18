# LLM Read Book

一个基于大模型的 PDF 阅读辅助工具，支持截图提问、AI 对话、以及自动生成 OneNote 笔记。

## 功能特性

- **PDF 阅读器** — 内嵌高性能 PDF 渲染，支持翻页、缩放
- **区域截图** — 框选 PDF 任意区域截图，一键发送给 AI 分析
- **AI 对话** — 将截图或复制的文字发送给大模型提问，支持多轮对话与流式输出
- **笔记生成** — 调用 API 将对话内容自动整理并写入 OneNote

##  项目结构

```
llm_read_book/
├── viewer/          # 前端 (Vue 3 + Vite)
│   ├── src/
│   │   ├── components/
│   │   │   ├── PdfViewer.vue      # PDF 渲染组件
│   │   │   ├── ScreenCapture.vue  # 区域截图工具
│   │   │   ├── AiChat.vue         # AI 对话面板
│   │   │   └── QuestionDialog.vue # 提问弹窗
│   │   └── App.vue
│   └── public/
└── server/          # 后端 (Python + FastAPI)
    ├── app.py
    ├── config.py
    └── router/
        ├── llm_ask.py        # LLM 提问接口
        └── generate_note.py  # OneNote 笔记生成接口
```

##  技术栈

### 前端
| 技术 | 用途 |
|------|------|
| Vue 3 + Vite | 框架与构建工具 |
| TypeScript | 类型安全 |
| `@embedpdf` | PDF 渲染引擎 |
| `html2canvas` | 区域截图 |
| `marked` | Markdown 渲染 |

### 后端
| 技术 | 用途 |
|------|------|
| Python 3.10+ | 运行环境 |
| FastAPI | Web 框架 |
| `openai` SDK | 调用大模型 API（通义千问 / OpenAI 兼容） |
| Microsoft Graph API | OneNote 笔记写入（计划中）|

## 🚀 快速开始

### 前置要求

- Node.js >= 18
- Python >= 3.10
- 阿里云通义千问 API Key（或其他 OpenAI 兼容接口）

---

### 前端启动

```bash
cd viewer
npm install
npm run dev
```

访问 `http://localhost:5173`

---

### 后端启动

```bash
cd server
pip install fastapi uvicorn openai pydantic
```

配置 `config.py` 中的 API Key：

```python
config = Config(
    api_key="your-api-key-here",
    llm_model="qwen-vl-max-latest"
)
```

启动服务：

```bash
python app.py
```

服务运行于 `http://localhost:8000`

---

##  API 接口

### POST `/llm/llm_ask`

向大模型提问，支持图片（截图）和文字输入。

**请求体：**
```json
{
  "book_name": "书名",
  "question": "用户问题",
  "image_base64": "base64 编码的截图（可为空）"
}
```

**响应：** 大模型的回答文本（字符串）

---

### POST `/generate_note/generate_note`

将内容生成笔记并写入 OneNote（开发中）。

---

##  开发计划

- [x] PDF 渲染与翻页
- [x] 区域截图工具
- [x] AI 多轮对话面板（支持流式输出）
- [x] 截图自动传入 AI 对话
- [ ] 后端接口完善（PDF 文件管理）
- [ ] OneNote 笔记自动生成与写入
- [ ] Microsoft OAuth 登录（用于 OneNote 授权）
- [ ] 支持多本书管理与切换

## 📄 License

MIT
