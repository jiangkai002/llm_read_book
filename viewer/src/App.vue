<script setup lang="ts">
import { ref } from 'vue'
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

const onSaveAsMarkdown = async (filename: string, mdContent: string) => {
  activeTab.value = 'markdown'
  await mdEditorRef.value?.saveNewFile(filename, mdContent)
}

const onSaveToOnenote = async (title: string, mdContent: string) => {
  activeTab.value = 'onenote'
  await onenoteRef.value?.saveToOnenote(title, mdContent)
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
      <PdfViewer url="/jgs.pdf" id="pdf" @ready="onPdfReady" />
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
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            AI 对话
          </button>
          <button
            class="panel-tab"
            :class="{ active: activeTab === 'markdown' }"
            @click="activeTab = 'markdown'"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            Markdown
          </button>
          <button
            class="panel-tab"
            :class="{ active: activeTab === 'onenote' }"
            @click="activeTab = 'onenote'"
          >
            <svg width="14" height="14" viewBox="0 0 24 24">
              <rect width="24" height="24" rx="4" fill="none" stroke="currentColor" stroke-width="2" />
              <text x="6" y="17" font-size="13" font-weight="bold" fill="currentColor" font-family="Arial">N</text>
            </svg>
            OneNote
          </button>
        </div>
        <div class="panel-content">
          <AiChat v-show="activeTab === 'chat'" :screenshot="capturedScreenshot" :selected-text="selectedText" :on-save-as-markdown="onSaveAsMarkdown" :on-save-to-onenote="onSaveToOnenote" />
          <MarkdownEditor v-show="activeTab === 'markdown'" ref="mdEditorRef" />
          <OnenoteEditor v-show="activeTab === 'onenote'" ref="onenoteRef" />
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
  transition: color 0.15s, box-shadow 0.15s;
  position: relative;
}

.panel-tab:hover {
  color: #6b7280;
}

.panel-tab.active {
  color: #6366f1;
  box-shadow: inset 0 -2px 0 #6366f1;
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
</style>
