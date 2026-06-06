<script setup lang="ts">
import { ref, nextTick } from 'vue'
import onenoteTabIcon from '@/assets/onenote_icon.svg'
import markdownIcon from '@/assets/markdown_icon.svg'
import PdfViewer from '@/components/PdfViewer.vue'
import AiChat from '@/components/AiChat.vue'
import MarkdownEditor from '@/components/MarkdownEditor.vue'
import OnenoteEditor from '@/components/OnenoteEditor.vue'
import { CapturePlugin, type PluginRegistry } from '@embedpdf/vue-pdf-viewer'

const capturedScreenshot = ref<string | null>(null)
const selectedText = ref<string | null>(null)
const chatCollapsed = ref(false)
const activeTab = ref<'chat' | 'markdown' | 'onenote'>('chat')
const mdEditorRef = ref<InstanceType<typeof MarkdownEditor> | null>(null)
const onenoteRef = ref<InstanceType<typeof OnenoteEditor> | null>(null)

// 笔记选择弹窗相关
interface NoteSummary {
  filename: string
  summary: string
}
const showNoteSelector = ref(false)
const noteSummaries = ref<NoteSummary[]>([])
const pendingAiNotePayload = ref<AiNotePayload | null>(null)
const isLoadingNotes = ref(false)
const selectedNoteFilename = ref<string | null>(null)

const onSaveAsMarkdown = async (filename: string, mdContent: string) => {
  activeTab.value = 'markdown'
  await mdEditorRef.value?.saveNewFile(filename, mdContent)
}

const onSaveToOnenote = async (title: string, mdContent: string) => {
  activeTab.value = 'onenote'
  await onenoteRef.value?.saveToOnenote(title, mdContent)
}

interface AiNotePayload {
  question: string
  answer: string
  imageContent: string
  bookName: string
  apiKey: string
  baseUrl: string
  model: string
  existingNoteFilename?: string
  existingNoteContent?: string
}

// 点击"AI笔记"时，先加载笔记列表，让用户选择
const onSaveAsAiNote = async (payload: AiNotePayload) => {
  activeTab.value = 'markdown'
  await nextTick()

  // 检查是否已选择笔记目录
  const summaries = await mdEditorRef.value?.getNotesSummary()
  if (!summaries || summaries.length === 0) {
    // 没有笔记目录或笔记为空，直接让后端决定新建
    pendingAiNotePayload.value = payload
    await mdEditorRef.value?.saveAiNote({ ...payload })
    pendingAiNotePayload.value = null
    return
  }

  // 有笔记，显示选择弹窗
  noteSummaries.value = summaries
  pendingAiNotePayload.value = payload
  showNoteSelector.value = true
}

// 选择新建笔记
const handleNewNote = async () => {
  showNoteSelector.value = false
  if (!pendingAiNotePayload.value) return
  const payload = { ...pendingAiNotePayload.value }
  pendingAiNotePayload.value = null
  await mdEditorRef.value?.saveAiNote(payload)
}

// 选择已有笔记
const handleSelectNote = async (filename: string) => {
  showNoteSelector.value = false
  if (!pendingAiNotePayload.value) return

  // 获取选中笔记的完整内容
  const content = await mdEditorRef.value?.getNoteContent(filename)
  const payload = {
    question: pendingAiNotePayload.value.question,
    answer: pendingAiNotePayload.value.answer,
    imageContent: pendingAiNotePayload.value.imageContent,
    bookName: pendingAiNotePayload.value.bookName,
    apiKey: pendingAiNotePayload.value.apiKey,
    baseUrl: pendingAiNotePayload.value.baseUrl,
    model: pendingAiNotePayload.value.model,
    existingNoteFilename: filename,
    existingNoteContent: content || '',
  }
  pendingAiNotePayload.value = null
  await mdEditorRef.value?.saveAiNoteWithExistingNote(payload)
}

// 关闭弹窗
const closeNoteSelector = () => {
  showNoteSelector.value = false
  pendingAiNotePayload.value = null
  selectedNoteFilename.value = null
}

const onPdfReady = (registry: PluginRegistry) => {
  const capturePlugin = registry.getPlugin<CapturePlugin>(CapturePlugin.id)
  if (!capturePlugin) return

  capturePlugin.ready().then(() => {
    const capability = capturePlugin.provides()
    capability.onCaptureArea((event) => {
      const reader = new FileReader()
      reader.onload = () => {
        capturedScreenshot.value = reader.result as string
        setTimeout(() => {
          capturedScreenshot.value = null
        }, 100)
      }
      reader.readAsDataURL(event.blob)
    })
  })
}

const toggleChat = () => {
  chatCollapsed.value = !chatCollapsed.value
}
</script>

<template>
  <div class="app">
    <div class="pdf-area" :class="{ expanded: chatCollapsed }">
      <PdfViewer url="/paper.pdf" id="pdf" @ready="onPdfReady" />
    </div>

    <button class="collapse-btn" :class="{ collapsed: chatCollapsed }" @click="toggleChat">
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <polyline v-if="!chatCollapsed" points="9 18 15 12 9 6" />
        <polyline v-else points="15 18 9 12 15 6" />
      </svg>
    </button>

    <transition name="slide-chat">
      <div v-show="!chatCollapsed" class="chat-area">
        <div class="panel-tabs">
          <button
            class="panel-tab"
            :class="{ active: activeTab === 'chat' }"
            @click="activeTab = 'chat'"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            AI 对话
          </button>
          <button
            class="panel-tab"
            :class="{ active: activeTab === 'markdown' }"
            @click="activeTab = 'markdown'"
          >
            <img
              class="panel-tab-markdown-icon"
              :src="markdownIcon"
              alt=""
              width="14"
              height="14"
            />
            Markdown
          </button>
          <button
            class="panel-tab"
            :class="{ active: activeTab === 'onenote' }"
            @click="activeTab = 'onenote'"
          >
            <img
              class="panel-tab-onenote-icon"
              :src="onenoteTabIcon"
              alt=""
              width="14"
              height="14"
            />
            OneNote
          </button>
        </div>
        <div class="panel-content">
          <AiChat
            v-show="activeTab === 'chat'"
            :screenshot="capturedScreenshot"
            :selected-text="selectedText"
            :on-save-as-markdown="onSaveAsMarkdown"
            :on-save-to-onenote="onSaveToOnenote"
            :on-save-as-ai-note="onSaveAsAiNote"
          />
          <MarkdownEditor v-show="activeTab === 'markdown'" ref="mdEditorRef" />
          <OnenoteEditor v-show="activeTab === 'onenote'" ref="onenoteRef" />
        </div>

        <!-- 笔记选择弹窗 -->
        <div v-if="showNoteSelector" class="modal-overlay" @click.self="closeNoteSelector">
          <div class="note-selector-modal">
            <div class="modal-header">
              <h3>保存到笔记</h3>
              <button class="modal-close-btn" @click="closeNoteSelector">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            <div class="modal-body">
              <button class="note-option new-note-btn" @click="handleNewNote">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="12" y1="5" x2="12" y2="19"/>
                  <line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
                <span>新建笔记</span>
              </button>
              <div class="note-divider">
                <span>或选择已有笔记</span>
              </div>
              <div class="note-list">
                <button
                  v-for="note in noteSummaries"
                  :key="note.filename"
                  class="note-option existing-note-btn"
                  @click="handleSelectNote(note.filename)"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                  </svg>
                  <div class="note-info">
                    <span class="note-name">{{ note.filename }}</span>
                    <span v-if="note.summary" class="note-preview">{{ note.summary.slice(0, 60) }}{{ note.summary.length > 60 ? '...' : '' }}</span>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: #f3f4f6;
  position: relative;
}

.pdf-area {
  flex: 1;
  height: 100%;
  position: relative;
  background: #f0f0f0;
  transition: flex 0.3s ease;
}

.collapse-btn {
  position: absolute;
  right: 32%;
  top: 50%;
  transform: translateY(-50%);
  z-index: 100;
  width: 24px;
  height: 48px;
  border: 1px solid #d1d5db;
  border-radius: 6px 0 0 6px;
  background: #fff;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition:
    right 0.3s ease,
    background 0.15s,
    color 0.15s;
  box-shadow: -2px 0 6px rgba(0, 0, 0, 0.06);
}

.collapse-btn:hover {
  background: #f3f4f6;
  color: #111;
}

.collapse-btn.collapsed {
  right: 0;
  border-radius: 6px 0 0 6px;
}

.chat-area {
  flex: 0 0 32%;
  height: 100%;
  overflow: hidden;
  border-left: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
}

.panel-tabs {
  display: flex;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.panel-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 9px 0;
  border: none;
  background: none;
  font-size: 13px;
  font-weight: 500;
  color: #9ca3af;
  cursor: pointer;
  transition:
    color 0.15s,
    box-shadow 0.15s;
  position: relative;
}

.panel-tab:hover {
  color: #6b7280;
}

.panel-tab.active {
  color: #6366f1;
  box-shadow: inset 0 -2px 0 #6366f1;
}

.panel-tab-onenote-icon {
  display: block;
  flex-shrink: 0;
  object-fit: contain;
}

.panel-content {
  flex: 1;
  overflow: hidden;
}

.slide-chat-enter-active,
.slide-chat-leave-active {
  transition:
    flex 0.3s ease,
    opacity 0.2s ease;
}

.slide-chat-enter-from,
.slide-chat-leave-to {
  flex: 0 0 0%;
  opacity: 0;
}

/* ── 笔记选择弹窗 ── */
.modal-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.note-selector-modal {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
  width: 85%;
  max-height: 70%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111;
}

.modal-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  border-radius: 6px;
  cursor: pointer;
  color: #9ca3af;
  transition: background 0.15s, color 0.15s;
}

.modal-close-btn:hover {
  background: #f3f4f6;
  color: #111;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 18px;
}

.note-option {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
}

.note-option:hover {
  background: #f9fafb;
  border-color: #c4b5fd;
}

.new-note-btn {
  color: #6366f1;
  font-weight: 500;
  font-size: 14px;
}

.new-note-btn:hover {
  background: #ede9fe;
  border-color: #6366f1;
}

.note-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 14px 0;
  color: #9ca3af;
  font-size: 12px;
}

.note-divider::before,
.note-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #e5e7eb;
}

.note-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.existing-note-btn {
  color: #374151;
}

.existing-note-btn svg {
  flex-shrink: 0;
  color: #6366f1;
}

.note-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.note-name {
  font-size: 13px;
  font-weight: 500;
  color: #111;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.note-preview {
  font-size: 11px;
  color: #9ca3af;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
