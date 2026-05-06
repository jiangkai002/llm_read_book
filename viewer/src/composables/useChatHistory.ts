import { ref, computed, nextTick, type Ref } from 'vue'

// ── 类型定义（与 AiChat.vue 保持一致，可按需从公共类型文件引入）──

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  images?: string[]
  /** 截图相关上下文文本（OCR / 选区文字） */
  imageContext?: string
  timestamp: Date
  isStreaming?: boolean
}

export interface Conversation {
  id: string
  title: string
  createdAt: number
  updatedAt: number
  messages: (Omit<Message, 'isStreaming'> & { images?: string[] })[]
}

// ── 常量 ──

const STORAGE_KEY = 'ai_conversations'
const MAX_CONV = 50

// ── Composable ──

export function useChatHistory(
  messages: Ref<Message[]>,
  onAfterSwitch?: () => void,
) {
  const conversations = ref<Conversation[]>([])
  const currentConvId = ref<string>('')
  const showHistory = ref(false)

  // ── 工具函数 ──

  const getConvTitle = (msgs: Message[]): string => {
    const first = msgs.find((m) => m.role === 'user' && m.content.trim())
    return first?.content.replace(/\n/g, ' ').slice(0, 30).trim() || '新对话'
  }

  const formatConvDate = (ts: number): string => {
    const d = new Date(ts)
    const now = new Date()
    if (d.toDateString() === now.toDateString()) {
      return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }
    return d.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
  }

  // ── 持久化 ──

  const loadConversations = (): void => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      conversations.value = raw ? JSON.parse(raw) : []
    } catch {
      conversations.value = []
    }
  }

  const persistConversations = (): void => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations.value))
    } catch {
      // 超出 quota 时保留最近 20 条
      conversations.value = conversations.value.slice(0, 20)
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations.value))
      } catch {}
    }
  }

  // ── 保存当前对话 ──

  let autoSaveTimer: ReturnType<typeof setTimeout> | null = null

  const saveCurrentConversation = (): void => {
    if (!currentConvId.value) return
    const msgs = messages.value
      .filter((m) => !m.isStreaming && (m.content || m.images?.length))
      .map((m) => ({ ...m, isStreaming: undefined, images: [] }))

    const title = getConvTitle(messages.value)
    const idx = conversations.value.findIndex((c) => c.id === currentConvId.value)
    if (idx >= 0) {
      conversations.value[idx] = {
        ...conversations.value[idx],
        title,
        updatedAt: Date.now(),
        messages: msgs,
      }
    } else {
      conversations.value.unshift({
        id: currentConvId.value,
        title,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messages: msgs,
      })
      if (conversations.value.length > MAX_CONV) {
        conversations.value = conversations.value.slice(0, MAX_CONV)
      }
    }
    persistConversations()
  }

  const scheduleAutoSave = (): void => {
    if (autoSaveTimer) clearTimeout(autoSaveTimer)
    autoSaveTimer = setTimeout(() => saveCurrentConversation(), 1200)
  }

  // ── 切换 / 删除对话 ──

  const switchToConversation = (conv: Conversation): void => {
    saveCurrentConversation()
    currentConvId.value = conv.id
    messages.value = conv.messages.map((m) => ({
      ...m,
      timestamp: new Date(m.timestamp),
    })) as Message[]
    showHistory.value = false
    nextTick(() => onAfterSwitch?.())
  }

  const deleteConversation = (id: string, e: Event): void => {
    e.stopPropagation()
    const idx = conversations.value.findIndex((c) => c.id === id)
    if (idx < 0) return
    conversations.value.splice(idx, 1)
    persistConversations()
  }

  // ── 计算属性：按日期分组 ──

  const groupedConversations = computed(() => {
    const today: Conversation[] = []
    const earlier: Conversation[] = []
    const now = new Date()
    for (const c of conversations.value) {
      if (new Date(c.updatedAt).toDateString() === now.toDateString()) today.push(c)
      else earlier.push(c)
    }
    return { today, earlier }
  })

  return {
    conversations,
    currentConvId,
    showHistory,
    groupedConversations,
    loadConversations,
    saveCurrentConversation,
    scheduleAutoSave,
    switchToConversation,
    deleteConversation,
    formatConvDate,
  }
}
