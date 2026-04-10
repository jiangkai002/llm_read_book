<script setup lang="ts">
import { ref } from 'vue'
import PdfViewer from '@/components/PdfViewer.vue'
import AiChat from '@/components/AiChat.vue'
import { CapturePlugin, type PluginRegistry } from '@embedpdf/vue-pdf-viewer'

const capturedScreenshot = ref<string | null>(null)
const selectedText = ref<string | null>(null)
const chatCollapsed = ref(false)

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
        <AiChat :screenshot="capturedScreenshot" :selected-text="selectedText" />
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
