<script setup lang="ts">
import { ref } from 'vue'
import PdfViewer from '@/components/PdfViewer.vue'
import ScreenCapture from '@/components/ScreenCapture.vue'
import AiChat from '@/components/AiChat.vue'

const capturedScreenshot = ref<string | null>(null)
const selectedText = ref<string | null>(null)
const captureTrigger = ref(0)

const handleScreenshot = (img: string) => {
  capturedScreenshot.value = img
  setTimeout(() => {
    capturedScreenshot.value = null
  }, 100)
}

const handleTextSelect = (text: string) => {
  selectedText.value = text
  setTimeout(() => {
    selectedText.value = null
  }, 100)
}

const requestScreenshot = () => {
  captureTrigger.value += 1
}
</script>

<template>
  <div class="app">
    <div class="pdf-area">
      <PdfViewer url="/test.pdf" id="pdf" />
      <ScreenCapture
        :capture-trigger="captureTrigger"
        targetId="pdf"
        @screenshot="handleScreenshot"
        @text-select="handleTextSelect"
      />
    </div>
    <div class="chat-area">
      <AiChat
        :screenshot="capturedScreenshot"
        :selected-text="selectedText"
        :on-request-screenshot="requestScreenshot"
      />
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
