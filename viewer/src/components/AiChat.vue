<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue'
import { marked } from 'marked'
import { LlmService, LLMAsk } from '@/api/index'
import { syncApiClientFromStorage } from '@/api/client'

/** 无截图时占位，满足后端多模态请求（1×1 透明 PNG） */
const PLACEHOLDER_IMAGE_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='

function stripDataUrlBase64(dataUrl: string): string {
  const m = dataUrl.match(/^data:image\/\w+;base64,(.+)$/i)
  return m ? m[1] : dataUrl.replace(/^data:[^;]+;base64,/i, '')
}

/** 后端要求 OpenAI 兼容根路径，如 https://api.openai.com/v1 */
function normalizeOpenAIBaseUrl(endpoint: string): string {
  let u = endpoint.trim()
  if (!u) return 'https://api.openai.com/v1'
  u = u.replace(/\/chat\/completions\/?$/i, '').replace(/\/$/, '')
  return u || 'https://api.openai.com/v1'
}

const props = defineProps<{
  screenshot?: string | null
  selectedText?: string | null
  onRequestScreenshot?: () => void
  onSaveAsMarkdown?: (filename: string, content: string) => void
  onSaveToOnenote?: (title: string, content: string) => void
}>()

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  images?: string[]
  timestamp: Date
  isStreaming?: boolean
}

interface ApiConfig {
  /** 本机 FastAPI 等，如 http://localhost:8000 */
  backendUrl: string
  /** OpenAI 兼容 API 根地址，如 https://api.openai.com/v1 */
  endpoint: string
  apiKey: string
  model: string
  bookName: string
}

const messages = ref<Message[]>([])
const inputText = ref('')
const attachedImage = ref<string | null>(null)
const isLoading = ref(false)
const showConfig = ref(false)
const chatContainerRef = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)

const apiConfig = ref<ApiConfig>({
  backendUrl:
    localStorage.getItem('ai_backend_url') ||
    localStorage.getItem('onenote_backend_url') ||
    'http://localhost:8000',
  endpoint: normalizeOpenAIBaseUrl(
    localStorage.getItem('ai_endpoint') || 'https://api.openai.com/v1'
  ),
  apiKey: localStorage.getItem('ai_api_key') || '',
  model: localStorage.getItem('ai_model') || 'gpt-4o',
  bookName: localStorage.getItem('ai_book_name') || '当前书籍',
})

watch(
  () => props.screenshot,
  (val) => {
    if (val) attachedImage.value = val
  }
)

watch(
  () => props.selectedText,
  (val) => {
    if (val) {
      inputText.value = val
      nextTick(() => textareaRef.value?.focus())
    }
  }
)

const saveConfig = () => {
  const ep = normalizeOpenAIBaseUrl(apiConfig.value.endpoint)
  apiConfig.value.endpoint = ep
  localStorage.setItem('ai_backend_url', apiConfig.value.backendUrl.trim())
  localStorage.setItem('ai_endpoint', ep)
  localStorage.setItem('ai_api_key', apiConfig.value.apiKey)
  localStorage.setItem('ai_model', apiConfig.value.model)
  localStorage.setItem('ai_book_name', apiConfig.value.bookName.trim() || '当前书籍')
  syncApiClientFromStorage()
  showConfig.value = false
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainerRef.value) {
    chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight
  }
}

const clearAttachment = () => {
  attachedImage.value = null
}

const clearHistory = () => {
  messages.value = []
}

const handlePaste = (e: ClipboardEvent) => {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of Array.from(items)) {
    if (item.type.startsWith('image/')) {
      e.preventDefault()
      const file = item.getAsFile()
      if (!file) return
      const reader = new FileReader()
      reader.onload = (ev) => {
        attachedImage.value = ev.target?.result as string
      }
      reader.readAsDataURL(file)
      break
    }
  }
}

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

const autoResize = (e: Event) => {
  const el = e.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

const sendMessage = async () => {
  const text = inputText.value.trim()
  const image = attachedImage.value
  if (!text && !image) return
  if (isLoading.value) return

  const userMsg: Message = {
    id: Date.now().toString(),
    role: 'user',
    content: text,
    images: image ? [image] : [],
    timestamp: new Date(),
  }
  messages.value.push(userMsg)
  inputText.value = ''
  attachedImage.value = null
  if (textareaRef.value) textareaRef.value.style.height = 'auto'
  await scrollToBottom()

  const assistantMsg: Message = {
    id: (Date.now() + 1).toString(),
    role: 'assistant',
    content: '',
    timestamp: new Date(),
    isStreaming: true,
  }
  messages.value.push(assistantMsg)
  isLoading.value = true

  try {
    if (apiConfig.value.apiKey && apiConfig.value.endpoint) {
      await callBackendLLM(text, image, assistantMsg)
    } else {
      await simulateStream(assistantMsg)
    }
  } catch (err: any) {
    const detail = err?.response?.data
    const msg =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail?.detail)
          ? detail.detail.map((d: { msg?: string }) => d.msg || '').join('; ')
          : detail?.detail != null
            ? String(detail.detail)
            : err?.message || '未知错误'
    assistantMsg.content = `请求失败：${msg}。请确认后端已启动，并检查大模型 API 配置。`
  } finally {
    assistantMsg.isStreaming = false
    isLoading.value = false
    await scrollToBottom()
  }
}

const callBackendLLM = async (text: string, image: string | null, target: Message) => {
  syncApiClientFromStorage()
  const imageBase64 = image ? stripDataUrlBase64(image) : PLACEHOLDER_IMAGE_BASE64
  const question = text.trim() || (image ? '请结合截图内容回答。' : '请回答。')
  const body = new LLMAsk({
    book_name: apiConfig.value.bookName.trim() || '当前书籍',
    question,
    image_base64: imageBase64,
    image_content: (props.selectedText?.trim() || '') as string,
    api_key: apiConfig.value.apiKey,
    base_url: normalizeOpenAIBaseUrl(apiConfig.value.endpoint),
    model: apiConfig.value.model,
  })
  const res = await LlmService.llmAskApiLlmLlmAskPost({ body })
  const out = typeof res === 'string' ? res : res == null ? '' : String(res)
  target.content = out
  await scrollToBottom()
}

const simulateStream = async (target: Message) => {
  const text =
    '您好！当前处于**示例模式**（未配置大模型密钥）。\n\n请点击右上角 ⚙️ 填写：\n- **后端地址**（默认 `http://localhost:8000`）\n- **OpenAI 兼容 base URL**（如 `https://api.openai.com/v1`）\n- **API Key** 与 **模型名称**\n- **书名**（可选，用于读书场景提示）\n\n请求会经后端 `POST /api/llm/llm_ask` 转发至大模型。配置完成后即可截图或输入文字提问。'
  for (const char of text) {
    target.content += char
    await new Promise((r) => setTimeout(r, 15))
    await scrollToBottom()
  }
}

const renderedContent = (content: string) => marked(content) as string

const formatTime = (date: Date) =>
  date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })

const saveToMarkdown = (msg: Message) => {
  if (!props.onSaveAsMarkdown) return
  const ts = new Date().toISOString().slice(0, 10)
  const slug =
    msg.content
      .slice(0, 20)
      .replace(/[\\/:*?"<>|#\n]/g, '')
      .trim() || 'note'
  const filename = `${ts}-${slug}.md`
  props.onSaveAsMarkdown(filename, msg.content)
}

const saveToOnenote = (msg: Message) => {
  if (!props.onSaveToOnenote) return
  const title =
    msg.content
      .split('\n')[0]
      .replace(/^#+\s*/, '')
      .slice(0, 50) || 'AI 笔记'
  props.onSaveToOnenote(title, msg.content)
}

onMounted(() => {
  messages.value.push({
    id: '0',
    role: 'assistant',
    content:
      '你好！我是 AI 助手。你可以：\n- 粘贴 PDF 中复制的文字进行提问\n- 截取 PDF 截图后自动附加到此处\n\n请先点击 ⚙️ 配置后端地址与大模型 API（经服务端转发）。',
    timestamp: new Date(),
  })
})
</script>

<template>
  <div class="ai-chat">
    <!-- 顶部栏 -->
    <div class="chat-header">
      <div class="header-title">
        <span class="ai-icon">✦</span>
        <span>AI 助手</span>
      </div>
      <div class="header-actions">
        <button
          class="icon-btn"
          title="截图（请在左侧 PDF 区域框选）"
          @click="props.onRequestScreenshot?.()"
        >
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <circle cx="8.5" cy="8.5" r="1.5"></circle>
            <polyline points="21 15 16 10 5 21"></polyline>
          </svg>
        </button>
        <button class="icon-btn" title="清空对话" @click="clearHistory">
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6l-1 14H6L5 6"></path>
            <path d="M10 11v6M14 11v6"></path>
            <path d="M9 6V4h6v2"></path>
          </svg>
        </button>
        <button class="icon-btn" title="API 配置" @click="showConfig = !showConfig">
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <circle cx="12" cy="12" r="3"></circle>
            <path
              d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
            ></path>
          </svg>
        </button>
      </div>
    </div>

    <!-- API 配置面板 -->
    <transition name="slide">
      <div v-if="showConfig" class="config-panel">
        <div class="config-row">
          <label>后端地址</label>
          <input v-model="apiConfig.backendUrl" placeholder="http://localhost:8000" />
        </div>
        <div class="config-row">
          <label>大模型 Base URL</label>
          <input
            v-model="apiConfig.endpoint"
            placeholder="https://api.openai.com/v1"
          />
        </div>
        <div class="config-row">
          <label>API Key</label>
          <input v-model="apiConfig.apiKey" type="password" placeholder="sk-..." />
        </div>
        <div class="config-row">
          <label>模型</label>
          <input v-model="apiConfig.model" placeholder="gpt-4o" />
        </div>
        <div class="config-row">
          <label>书名</label>
          <input v-model="apiConfig.bookName" placeholder="当前阅读的书名" />
        </div>
        <button class="save-btn" @click="saveConfig">保存配置</button>
      </div>
    </transition>

    <!-- 消息列表 -->
    <div class="chat-messages" ref="chatContainerRef">
      <div v-for="msg in messages" :key="msg.id" class="message-row" :class="msg.role">
        <div class="avatar">
          <span v-if="msg.role === 'assistant'">✦</span>
          <span v-else>你</span>
        </div>
        <div class="bubble-wrap">
          <!-- 用户附图 -->
          <div v-if="msg.images?.length" class="bubble-image">
            <img :src="msg.images[0]" alt="附加截图" />
          </div>
          <!-- 气泡 -->
          <div class="bubble" :class="msg.role">
            <div
              v-if="msg.role === 'assistant'"
              class="markdown-body"
              v-html="renderedContent(msg.content)"
            ></div>
            <span v-else>{{ msg.content }}</span>
            <span v-if="msg.isStreaming" class="cursor-blink">▋</span>
          </div>
          <div class="msg-meta">
            <span class="msg-time">{{ formatTime(msg.timestamp) }}</span>
            <button
              v-if="
                msg.role === 'assistant' &&
                msg.content &&
                !msg.isStreaming &&
                props.onSaveAsMarkdown
              "
              class="save-action-btn"
              title="保存为 Markdown 文件"
              @click="saveToMarkdown(msg)"
            >
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              .md
            </button>
            <button
              v-if="
                msg.role === 'assistant' && msg.content && !msg.isStreaming && props.onSaveToOnenote
              "
              class="save-action-btn onenote"
              title="保存到 OneNote"
              @click="saveToOnenote(msg)"
            >
              <svg width="12" height="12" viewBox="0 0 24 24">
                <rect
                  width="24"
                  height="24"
                  rx="4"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.5"
                />
                <text
                  x="6"
                  y="17"
                  font-size="13"
                  font-weight="bold"
                  fill="currentColor"
                  font-family="Arial"
                >
                  N
                </text>
              </svg>
              OneNote
            </button>
          </div>
        </div>
      </div>

      <!-- 加载中 -->
      <div
        v-if="isLoading && messages[messages.length - 1]?.isStreaming === false"
        class="loading-dots"
      >
        <span></span><span></span><span></span>
      </div>
    </div>

    <!-- 底部输入区 -->
    <div class="chat-input-area">
      <!-- 附图预览 -->
      <div v-if="attachedImage" class="attachment-preview">
        <img :src="attachedImage" alt="附加截图" />
        <button class="remove-attachment" @click="clearAttachment">✕</button>
      </div>

      <!-- 输入框 -->
      <div class="input-row">
        <textarea
          ref="textareaRef"
          v-model="inputText"
          placeholder="输入问题，或粘贴 PDF 文字 / 截图（Shift+Enter 换行）"
          rows="1"
          @keydown="handleKeydown"
          @paste="handlePaste"
          @input="autoResize"
        ></textarea>
        <button
          class="send-btn"
          :disabled="isLoading || (!inputText.trim() && !attachedImage)"
          @click="sendMessage"
        >
          <svg v-if="!isLoading" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M2 21l21-9L2 3v7l15 2-15 2v7z" />
          </svg>
          <span v-else class="spin">⟳</span>
        </button>
      </div>

      <div class="input-hint">Enter 发送 · Shift+Enter 换行 · 可直接粘贴截图</div>
    </div>
  </div>
</template>

<style scoped>
.ai-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f9fafb;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 14px;
  color: #1a1a1a;
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}
.header-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 15px;
  color: #111;
}
.ai-icon {
  color: #6366f1;
  font-size: 16px;
}
.header-actions {
  display: flex;
  gap: 4px;
}
.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  background: none;
  border-radius: 6px;
  cursor: pointer;
  color: #6b7280;
  transition: background 0.15s, color 0.15s;
}
.icon-btn:hover {
  background: #f3f4f6;
  color: #111;
}
.config-panel {
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  padding: 12px 14px;
  flex-shrink: 0;
}
.config-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.config-row label {
  width: 64px;
  font-size: 12px;
  color: #6b7280;
  flex-shrink: 0;
}
.config-row input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  color: #111;
}
.config-row input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15);
}
.save-btn {
  width: 100%;
  padding: 7px;
  background: #6366f1;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.15s;
}
.save-btn:hover {
  background: #4f46e5;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.chat-messages::-webkit-scrollbar {
  width: 4px;
}
.chat-messages::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 4px;
}

.message-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.message-row.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}
.message-row.assistant .avatar {
  background: #ede9fe;
  color: #6366f1;
}
.message-row.user .avatar {
  background: #dbeafe;
  color: #2563eb;
}

.bubble-wrap {
  max-width: 82%;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.message-row.user .bubble-wrap {
  align-items: flex-end;
}

.bubble-image {
  border-radius: 8px;
  overflow: hidden;
  max-width: 220px;
  border: 1px solid #e5e7eb;
}
.bubble-image img {
  display: block;
  max-width: 100%;
}

.bubble {
  padding: 10px 12px;
  border-radius: 12px;
  line-height: 1.6;
  word-break: break-word;
  position: relative;
}
.bubble.assistant {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-top-left-radius: 4px;
  color: #1a1a1a;
}
.bubble.user {
  background: #6366f1;
  color: #fff;
  border-top-right-radius: 4px;
}

.msg-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 4px;
}

.msg-time {
  font-size: 11px;
  color: #9ca3af;
}

.save-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 7px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: #fff;
  color: #9ca3af;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
}

.save-action-btn:hover {
  background: #ede9fe;
  border-color: #c4b5fd;
  color: #6366f1;
}

.save-action-btn.onenote:hover {
  background: #f3e8ff;
  border-color: #d8b4fe;
  color: #7719aa;
}

/* 光标闪烁 */
.cursor-blink {
  display: inline-block;
  animation: blink 0.8s step-end infinite;
  color: #6366f1;
  margin-left: 1px;
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}

/* 加载点 */
.loading-dots {
  display: flex;
  gap: 5px;
  padding: 4px 12px;
}
.loading-dots span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #9ca3af;
  animation: dot-pulse 1.2s infinite ease-in-out;
}
.loading-dots span:nth-child(2) {
  animation-delay: 0.2s;
}
.loading-dots span:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes dot-pulse {
  0%,
  80%,
  100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1.2);
    opacity: 1;
  }
}

/* ── 输入区 ── */
.chat-input-area {
  background: #fff;
  border-top: 1px solid #e5e7eb;
  padding: 10px 12px 8px;
  flex-shrink: 0;
}

.attachment-preview {
  position: relative;
  display: inline-block;
  margin-bottom: 8px;
}
.attachment-preview img {
  height: 72px;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  display: block;
}
.remove-attachment {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #ef4444;
  color: #fff;
  border: none;
  cursor: pointer;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
textarea {
  flex: 1;
  resize: none;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  padding: 9px 12px;
  font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
  font-size: 13.5px;
  line-height: 1.5;
  outline: none;
  color: #111;
  background: #f9fafb;
  transition: border-color 0.15s, box-shadow 0.15s;
  max-height: 160px;
  overflow-y: auto;
}
textarea:focus {
  border-color: #6366f1;
  background: #fff;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15);
}
textarea::placeholder {
  color: #9ca3af;
}

.send-btn {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  border: none;
  background: #6366f1;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s, transform 0.1s;
}
.send-btn:hover:not(:disabled) {
  background: #4f46e5;
  transform: scale(1.05);
}
.send-btn:disabled {
  background: #c4b5fd;
  cursor: not-allowed;
  transform: none;
}
.spin {
  display: inline-block;
  animation: spin 1s linear infinite;
  font-size: 16px;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.input-hint {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 5px;
  text-align: center;
}

/* ── 配置面板动画 ── */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
}
.slide-enter-to,
.slide-leave-from {
  max-height: 200px;
  opacity: 1;
}

/* ── Markdown 渲染样式 ── */
.markdown-body :deep(p) {
  margin: 0 0 8px;
}
.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 6px 0;
  padding-left: 20px;
}
.markdown-body :deep(li) {
  margin: 3px 0;
}
.markdown-body :deep(strong) {
  font-weight: 600;
  color: #111;
}
.markdown-body :deep(code) {
  background: #f3f4f6;
  padding: 1px 5px;
  border-radius: 4px;
  font-family: 'Fira Code', monospace;
  font-size: 12.5px;
  color: #7c3aed;
}
.markdown-body :deep(pre) {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
  font-size: 12.5px;
}
.markdown-body :deep(pre code) {
  background: none;
  color: inherit;
  padding: 0;
}
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 10px 0 6px;
  font-weight: 600;
  line-height: 1.4;
}
.markdown-body :deep(blockquote) {
  border-left: 3px solid #6366f1;
  padding-left: 10px;
  color: #6b7280;
  margin: 8px 0;
}
.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 10px 0;
}
</style>
