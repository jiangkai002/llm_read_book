<script setup lang="ts">
import { ref } from 'vue'
import PdfViewer from '@/components/PdfViewer.vue'
import AiChat from '@/components/AiChat.vue'
import { CapturePlugin, type PluginRegistry } from '@embedpdf/vue-pdf-viewer'

const capturedScreenshot = ref<string | null>(null)
const selectedText = ref<string | null>(null)

const onPdfReady = (registry: PluginRegistry) => {
  console.log('[App] onPdfReady fired, registry:', registry)

  const capturePlugin = registry.getPlugin<CapturePlugin>(CapturePlugin.id)
  console.log('[App] CapturePlugin.id =', CapturePlugin.id, ', plugin =', capturePlugin)

  if (!capturePlugin) {
    console.warn('[App] CapturePlugin not found! Available plugins:', registry)
    return
  }

  capturePlugin.ready().then(() => {
    const capability = capturePlugin.provides()
    console.log('[App] CapturePlugin ready, capability:', capability)

    capability.onCaptureArea((event) => {
      console.log('[App] onCaptureArea fired!', event)
      const reader = new FileReader()
      reader.onload = () => {
        console.log('[App] Blob converted to base64, length:', (reader.result as string).length)
        capturedScreenshot.value = reader.result as string
        setTimeout(() => {
          capturedScreenshot.value = null
        }, 100)
      }
      reader.readAsDataURL(event.blob)
    })
  })
}

const handleTextSelect = (text: string) => {
  selectedText.value = text
  setTimeout(() => {
    selectedText.value = null
  }, 100)
}
</script>

<template>
  <div class="app">
    <div class="pdf-area">
      <PdfViewer url="/jgs.pdf" id="pdf" @ready="onPdfReady" />
    </div>
    <div class="chat-area">
      <AiChat :screenshot="capturedScreenshot" :selected-text="selectedText" />
    </div>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: #f3f4f6;
}

.pdf-area {
  flex: 0 0 68%;
  height: 100%;
  position: relative;
  background: #f0f0f0;
  border-right: 1px solid #e5e7eb;
}

.chat-area {
  flex: 0 0 32%;
  height: 100%;
  overflow: hidden;
}
</style>
