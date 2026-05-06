<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue'
import { marked } from 'marked'
import markedKatex from 'marked-katex-extension'
import 'katex/dist/katex.min.css'

import { useChatHistory } from '@/composables/useChatHistory'
import type { Message } from '@/composables/useChatHistory'
import { useApiConfig } from '@/composables/useApiConfig'
import { useLLM } from '@/composables/useLLM'
import ChatHistoryPanel from './chat/ChatHistoryPanel.vue'
import ChatInputArea from './chat/ChatInputArea.vue'

import newChat from '@/assets/chat/newChat.svg'
import onenoteIcon from '@/assets/onenote_icon.svg'
import mdIcon from '@/assets/markdown_icon.svg'
import configIcon from '@/assets/configIcon.svg'
import screenshotIcon from '@/assets/screenshotIcon.svg'
import chatHistory from '@/assets/chat/chatHistory.svg'

marked.use(markedKatex({ throwOnError: false, displayMode: false }))

// ── 类型 ──

interface AiNotePayload {
  question: string
  answer: string
  imageContent: string
  bookName: string
  apiKey: string
  baseUrl: string
  model: string
}

const props = defineProps<{
  screenshot?: string | null
  selectedText?: string | null
  onRequestScreenshot?: () => void
  onSaveAsMarkdown?: (filename: string, content: string) => void
  onSaveToOnenote?: (title: string, content: string) => void
  onSaveAsAiNote?: (payload: AiNotePayload) => void | Promise<void>
}>()

// ── 状态 ──

const messages = ref<Message[]>([])
const inputText = ref('')
const attachedImage = ref<string | null>(null)
const useImageUnderstanding = ref(localStorage.getItem('ai_use_image') !== 'false')
const isLoading = ref(false)
const showConfig = ref(false)
const chatContainerRef = ref<HTMLElement | null>(null)

// ── Composables ──

const { apiConfig, saveConfig: _saveConfig } = useApiConfig()

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainerRef.value) {
    chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight
  }
}

const {
  conversations,
  currentConvId,
  showHistory,
  groupedConversations,
  loadConversations,
  saveCurrentConversation,
  scheduleAutoSave,
  switchToConversation,
  deleteConversation,
} = useChatHistory(messages, () => scrollToBottom())

const { callBackendLLM } = useLLM(
  messages,
  () => props.selectedText,
  apiConfig,
  () => scrollToBottom(),
)

// ── 配置 ──

const saveConfig = () => {
  _saveConfig()
  showConfig.value = false
}

// ── 对话管理 ──

const startNewChat = () => {
  saveCurrentConversation()
  const id = Date.now().toString()
  currentConvId.value = id
  messages.value = []
  attachedImage.value = null
  inputText.value = ''
  messages.value.push({
    id: `${id}-welcome`,
    role: 'assistant',
    content:
      '你好！我是 AI 助手。你可以：\n- 粘贴 PDF 中复制的文字进行提问\n- 截取 PDF 截图后自动附加到此处\n\n请先点击 ⚙️ 配置后端地址与大模型 API（经服务端转发）。',
    timestamp: new Date(),
  })
}

const handleDeleteConversation = (id: string, e: Event) => {
  const wasCurrent = id === currentConvId.value
  deleteConversation(id, e)
  if (wasCurrent) startNewChat()
}

// ── 发送消息 ──

const sendMessage = async () => {
  const text = inputText.value.trim()
  const image = attachedImage.value
  if (!text && !image) return
  if (isLoading.value) return

  const useImageForRequest = !!(image && useImageUnderstanding.value)

  messages.value.push({
    id: Date.now().toString(),
    role: 'user',
    content: text,
    images: image ? [image] : [],
    imageContext: props.selectedText?.trim() || '',
    timestamp: new Date(),
  })
  inputText.value = ''
  attachedImage.value = null
  await scrollToBottom()

  messages.value.push({ id: (Date.now() + 1).toString(), role: 'assistant', content: '', timestamp: new Date(), isStreaming: true })
  const reactiveAssistant = messages.value[messages.value.length - 1]
  isLoading.value = true

  try {
    await callBackendLLM(text, image, reactiveAssistant, useImageForRequest)
  } catch (err: any) {
    const detail = err?.response?.data
    const msg =
      typeof detail === 'string' ? detail
      : Array.isArray(detail?.detail) ? detail.detail.map((d: { msg?: string }) => d.msg || '').join('; ')
      : detail?.detail != null ? String(detail.detail)
      : err?.message || '未知错误'
    reactiveAssistant.content = `请求失败：${msg}。请确认后端已启动，并检查大模型 API 配置。`
  } finally {
    reactiveAssistant.isStreaming = false
    isLoading.value = false
    await scrollToBottom()
  }
}

// ── 消息操作 ──

const renderedContent = (content: string) => marked(content) as string
const formatTime = (date: Date) =>
  date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })

const saveToMarkdown = (msg: Message) => {
  if (!props.onSaveAsMarkdown) return
  const ts = new Date().toISOString().slice(0, 10)
  const slug = msg.content.slice(0, 20).replace(/[\\/:*?"<>|#\n]/g, '').trim() || 'note'
  props.onSaveAsMarkdown(`${ts}-${slug}.md`, msg.content)
}

const saveToOnenote = (msg: Message) => {
  if (!props.onSaveToOnenote) return
  const title = msg.content.split('\n')[0].replace(/^#+\s*/, '').slice(0, 50) || 'AI 笔记'
  props.onSaveToOnenote(title, msg.content)
}

const findPairedUserMessage = (assistantMsg: Message): Message | null => {
  const idx = messages.value.findIndex((m) => m.id === assistantMsg.id)
  if (idx < 0) return null
  for (let i = idx - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user') return messages.value[i]
  }
  return null
}

const saveAsAiNote = async (assistantMsg: Message) => {
  if (!props.onSaveAsAiNote || !assistantMsg.content || assistantMsg.isStreaming) return
  const userMsg = findPairedUserMessage(assistantMsg)
  await props.onSaveAsAiNote({
    question: userMsg?.content?.trim() || '',
    answer: assistantMsg.content.trim(),
    imageContent: userMsg?.imageContext?.trim() || '',
    bookName: apiConfig.value.bookName.trim() || '当前书籍',
    apiKey: apiConfig.value.apiKey,
    baseUrl: apiConfig.value.endpoint,
    model: apiConfig.value.model,
  })
}

// ── 生命周期 ──

watch(() => props.screenshot, (val) => { if (val) attachedImage.value = val })
watch(() => props.selectedText, (val) => { if (val) inputText.value = val })
watch(messages, () => {
  if (messages.value.some((m) => m.role === 'user' && m.content)) scheduleAutoSave()
}, { deep: true })

onMounted(() => {
  loadConversations()
  if (conversations.value.length > 0) {
    const latest = conversations.value[0]
    currentConvId.value = latest.id
    messages.value = latest.messages.map((m) => ({ ...m, timestamp: new Date(m.timestamp) })) as Message[]
    nextTick(() => scrollToBottom())
  } else {
    startNewChat()
  }
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
        <button class="icon-btn" title="截图" @click="props.onRequestScreenshot?.()">
          <img class="btn-icon" :src="screenshotIcon" alt="" width="18" height="18" />
        </button>
        <button class="icon-btn" title="新建对话" @click="startNewChat">
          <img class="btn-icon" :src="newChat" alt="" width="18" height="18" />
        </button>
        <button
          class="icon-btn"
          :class="{ active: showHistory }"
          title="历史对话"
          @click="showHistory = !showHistory; showConfig = false"
        >
          <img class="btn-icon" :src="chatHistory" alt="" width="18" height="18"/>
        </button>
        <button
          class="icon-btn"
          title="API 配置"
          @click="showConfig = !showConfig; showHistory = false"
        >
          <img class="btn-icon" :src="configIcon" alt="" width="18" height="18"/>
        </button>
      </div>
    </div>

    <!-- API 配置面板 -->
    <transition name="slide">
      <div v-if="showConfig" class="config-panel">
        <div class="config-row">
          <label>Base URL</label>
          <input v-model="apiConfig.endpoint" placeholder="https://api.openai.com/v1" />
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

    <!-- 历史对话面板 -->
    <transition name="history-slide">
      <ChatHistoryPanel
        v-if="showHistory"
        :conversations="conversations"
        :current-conv-id="currentConvId"
        :grouped-conversations="groupedConversations"
        @switch="switchToConversation"
        @delete="handleDeleteConversation"
      />
    </transition>

    <!-- 消息列表 -->
    <div class="chat-messages" ref="chatContainerRef">
      <div v-for="msg in messages" :key="msg.id" class="message-row" :class="msg.role">
        <div class="avatar">
          <span v-if="msg.role === 'assistant'">✦</span>
          <span v-else>你</span>
        </div>
        <div class="bubble-wrap">
          <div v-if="msg.images?.length" class="bubble-image">
            <img :src="msg.images[0]" alt="附加截图" />
          </div>
          <div class="bubble" :class="msg.role">
            <div v-if="msg.role === 'assistant'" class="markdown-body" v-html="renderedContent(msg.content)" />
            <span v-else>{{ msg.content }}</span>
            <span v-if="msg.isStreaming" class="cursor-blink">▋</span>
          </div>
          <div class="msg-meta">
            <span class="msg-time">{{ formatTime(msg.timestamp) }}</span>
            <button class="save-action-btn" title="保存为 Markdown" @click="saveToMarkdown(msg)">
              <img class="save-action-icon" :src="mdIcon" alt="" />Markdown
            </button>
            <button
              v-if="msg.role === 'assistant' && msg.content && !msg.isStreaming && props.onSaveAsAiNote"
              class="save-action-btn ai-note"
              title="由 AI 整理为笔记"
              @click="saveAsAiNote(msg)"
            >
              <span class="save-action-icon ai-note-icon">✦</span>AI 笔记
            </button>
            <button
              v-if="msg.role === 'assistant' && msg.content && !msg.isStreaming && props.onSaveToOnenote"
              class="save-action-btn onenote"
              title="保存到 OneNote"
              @click="saveToOnenote(msg)"
            >
              <img class="save-action-icon" :src="onenoteIcon" alt="" />OneNote
            </button>
          </div>
        </div>
      </div>
      <div v-if="isLoading && messages[messages.length - 1]?.isStreaming === false" class="loading-dots">
        <span /><span /><span />
      </div>
    </div>

    <!-- 输入区 -->
    <ChatInputArea
      v-model="inputText"
      v-model:use-image-understanding="useImageUnderstanding"
      :is-loading="isLoading"
      :attached-image="attachedImage"
      @send="sendMessage"
      @paste-image="(url) => (attachedImage = url)"
      @clear-attachment="attachedImage = null"
    />
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

/* ── 顶部栏 ── */
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
.ai-icon { color: #6366f1; font-size: 16px; }
.header-actions { display: flex; gap: 4px; }
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
.icon-btn:hover { background: #f3f4f6; color: #111; }
.icon-btn.active { color: #6366f1; background: #ede9fe; }
.btn-icon { display: block; object-fit: contain; }

/* ── 配置面板 ── */
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
.config-row label { width: 64px; font-size: 12px; color: #6b7280; flex-shrink: 0; }
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
.save-btn:hover { background: #4f46e5; }

/* ── 历史面板动画 ── */
.history-slide-enter-active,
.history-slide-leave-active {
  transition: max-height 0.22s ease, opacity 0.18s ease;
  overflow: hidden;
}
.history-slide-enter-from,
.history-slide-leave-to { max-height: 0; opacity: 0; }
.history-slide-enter-to,
.history-slide-leave-from { max-height: 280px; opacity: 1; }

/* ── 配置面板动画 ── */
.slide-enter-active,
.slide-leave-active { transition: all 0.2s ease; overflow: hidden; }
.slide-enter-from,
.slide-leave-to { max-height: 0; opacity: 0; padding-top: 0; padding-bottom: 0; }
.slide-enter-to,
.slide-leave-from { max-height: 200px; opacity: 1; }

/* ── 消息列表 ── */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  cursor: auto;
}
.chat-messages::-webkit-scrollbar { width: 4px; }
.chat-messages::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }

.message-row { display: flex; gap: 8px; align-items: flex-start; }
.message-row.user { flex-direction: row-reverse; }

.avatar {
  width: 30px; height: 30px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 600; flex-shrink: 0;
}
.message-row.assistant .avatar { background: #ede9fe; color: #6366f1; }
.message-row.user .avatar { background: #dbeafe; color: #2563eb; }

.bubble-wrap { max-width: 82%; display: flex; flex-direction: column; gap: 4px; }
.message-row.user .bubble-wrap { align-items: flex-end; }

.bubble-image { border-radius: 8px; overflow: hidden; max-width: 220px; border: 1px solid #e5e7eb; }
.bubble-image img { display: block; max-width: 100%; }

.bubble {
  padding: 10px 12px;
  border-radius: 12px;
  line-height: 1.6;
  word-break: break-word;
  outline: none;
  -webkit-user-select: text;
  user-select: text;
  caret-color: transparent;
}
.bubble.assistant { background: #fff; border: 1px solid #e5e7eb; border-top-left-radius: 4px; color: #1a1a1a; }
.bubble.user { background: #6366f1; color: #fff; border-top-right-radius: 4px; }

.msg-meta { display: flex; align-items: center; gap: 8px; padding: 0 4px; }
.msg-time { font-size: 11px; color: #9ca3af; }

.save-action-btn {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 2px 7px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: #fff;
  color: #9ca3af;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
}
.save-action-icon { width: 12px; height: 12px; display: block; object-fit: contain; flex-shrink: 0; }
.save-action-btn:hover { background: #ede9fe; border-color: #c4b5fd; color: #6366f1; }
.save-action-btn.onenote:hover { background: #f3e8ff; border-color: #d8b4fe; color: #7719aa; }
.save-action-btn.ai-note:hover { background: linear-gradient(90deg, #ede9fe 0%, #fce7f3 100%); border-color: #c4b5fd; color: #6d28d9; }
.ai-note-icon { display: inline-flex; align-items: center; justify-content: center; width: 12px; height: 12px; font-size: 11px; color: #6366f1; font-weight: 700; }

.cursor-blink { display: inline-block; animation: blink 0.8s step-end infinite; color: #6366f1; margin-left: 1px; }
@keyframes blink { 50% { opacity: 0; } }

.loading-dots { display: flex; gap: 5px; padding: 4px 12px; }
.loading-dots span { width: 7px; height: 7px; border-radius: 50%; background: #9ca3af; animation: dot-pulse 1.2s infinite ease-in-out; }
.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dot-pulse {
  0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
  40% { transform: scale(1.2); opacity: 1; }
}

/* ── Markdown ── */
.markdown-body :deep(p) { margin: 0 0 8px; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { margin: 6px 0; padding-left: 20px; }
.markdown-body :deep(li) { margin: 3px 0; }
.markdown-body :deep(strong) { font-weight: 600; color: #111; }
.markdown-body :deep(code) { background: #f3f4f6; padding: 1px 5px; border-radius: 4px; font-family: 'Fira Code', monospace; font-size: 12.5px; color: #7c3aed; }
.markdown-body :deep(pre) { background: #1e1e2e; color: #cdd6f4; padding: 12px; border-radius: 8px; overflow-x: auto; margin: 8px 0; font-size: 12.5px; }
.markdown-body :deep(pre code) { background: none; color: inherit; padding: 0; }
.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3) { margin: 10px 0 6px; font-weight: 600; line-height: 1.4; }
.markdown-body :deep(blockquote) { border-left: 3px solid #6366f1; padding-left: 10px; color: #6b7280; margin: 8px 0; }
.markdown-body :deep(hr) { border: none; border-top: 1px solid #e5e7eb; margin: 10px 0; }
</style>
