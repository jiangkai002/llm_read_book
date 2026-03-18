<!-- ScreenCapture.vue -->
<template>
  <div class="screen-capture-container" ref="containerRef">
    <!-- 控制按钮 -->
    <button class="toggle-button" :class="{ active: isCaptureEnabled }" @click="toggleCapture">
      {{ isCaptureEnabled ? '关闭截图' : '开启截图' }}
    </button>

    <!-- 截图预览区域 -->
    <div v-if="screenshot" class="screenshot-preview">
      <div class="preview-content">
        <img :src="screenshot" alt="当前截取的屏幕画面" />
        <div class="preview-buttons">
          <button @click="clearScreenshot">清除截图</button>
          <button @click="saveScreenshot">保存到本地</button>
          <button @click="showDialog = true">对图片提问</button>
        </div>
      </div>
    </div>

    <!-- 框选区域 -->
    <div v-if="isSelecting" class="selection-box" :style="selectionStyle"></div>

    <!-- 提问对话框 -->
    <QuestionDialog
      v-model="showDialog"
      :screenshot="screenshot || ''"
      @generate-note="handleGenerateNote"
    />

    <!-- 笔记内容区域 -->
    <div v-if="noteContent" 
         class="note-container"
         ref="noteContainerRef"
         :style="{ 
           transform: `translate(${notePosition.x}px, ${notePosition.y}px)`,
           cursor: isDragging ? 'grabbing' : 'grab'
         }"
         @mousedown="startDragging">
      <div class="note-header">
        <h3>笔记内容</h3>
        <button class="close-note-btn" @click="clearNote">关闭笔记</button>
      </div>
      <div class="note-body">
        <div class="markdown-content" v-html="renderedNote"></div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, watch, onMounted, onUnmounted } from 'vue'
import html2canvas from 'html2canvas'
import { marked } from 'marked'
import QuestionDialog from './QuestionDialog.vue'

export default defineComponent({
  name: 'ScreenCapture',
  components: {
    QuestionDialog
  },
  props: {
    targetId: {
      type: String,
      default: '',
    },
    /** 由父组件传入，每次变化时开启截图模式（供右侧截图按钮触发） */
    captureTrigger: {
      type: Number,
      default: 0,
    },
  },
  emits: ['screenshot', 'text-select'],
  setup(props, { emit }) {
    const isSelecting = ref(false)
    const isCaptureEnabled = ref(false)
    const startX = ref(0)
    const startY = ref(0)
    const endX = ref(0)
    const endY = ref(0)
    const screenshot = ref<string | null>(null)
    const showDialog = ref(false)
    const noteContent = ref('')
    const isDragging = ref(false)
    const notePosition = ref({ x: 20, y: 20 })
    const dragOffset = ref({ x: 0, y: 0 })
    const containerRef = ref<HTMLElement | null>(null)
    const noteContainerRef = ref<HTMLElement | null>(null)

    const selectionStyle = computed(() => ({
      left: `${Math.min(startX.value, endX.value)}px`,
      top: `${Math.min(startY.value, endY.value)}px`,
      width: `${Math.abs(endX.value - startX.value)}px`,
      height: `${Math.abs(endY.value - startY.value)}px`,
    }))

    const renderedNote = computed(() => {
      if (!noteContent.value) return ''
      return marked(noteContent.value)
    })

    const toggleCapture = () => {
      isCaptureEnabled.value = !isCaptureEnabled.value
      if (!isCaptureEnabled.value) {
        isSelecting.value = false
        screenshot.value = null
      }
    }

    /** 右侧截图按钮通过 captureTrigger 触发时调用 */
    const enableCapture = () => {
      isCaptureEnabled.value = true
    }

    watch(
      () => props.captureTrigger,
      () => {
        if (props.captureTrigger > 0) enableCapture()
      }
    )

    const startSelection = (e: MouseEvent) => {
      if (!isCaptureEnabled.value || screenshot.value) return

      isSelecting.value = true
      startX.value = e.clientX
      startY.value = e.clientY
      endX.value = e.clientX
      endY.value = e.clientY

      document.addEventListener('mousemove', updateSelection)
      document.addEventListener('mouseup', endSelection)
    }

    const updateSelection = (e: MouseEvent) => {
      if (!isSelecting.value) return
      endX.value = e.clientX
      endY.value = e.clientY
    }

    const endSelection = async () => {
      isSelecting.value = false
      document.removeEventListener('mousemove', updateSelection)
      document.removeEventListener('mouseup', endSelection)

      try {
        let element: HTMLElement | null = document.body
        if (props.targetId) {
          element = document.getElementById(props.targetId)
        }

        if (!element) return

        const canvas = await html2canvas(element, {
          x: Math.min(startX.value, endX.value),
          y: Math.min(startY.value, endY.value),
          width: Math.abs(endX.value - startX.value),
          height: Math.abs(endY.value - startY.value),
          useCORS: true,
        })

        screenshot.value = canvas.toDataURL('image/png')
        emit('screenshot', screenshot.value)
      } catch (error) {
        console.error('截图失败:', error)
      }
    }

    const clearScreenshot = () => {
      screenshot.value = null
    }

    const saveScreenshot = () => {
      if (!screenshot.value) return

      const link = document.createElement('a')
      link.download = `screenshot-${new Date().toISOString().replace(/[:.]/g, '-')}.png`
      link.href = screenshot.value
      link.click()
    }

    const handleGenerateNote = (content: string) => {
      noteContent.value = content
    }

    const clearNote = () => {
      noteContent.value = ''
    }

    const startDragging = (e: MouseEvent) => {
      isDragging.value = true
      dragOffset.value = {
        x: e.clientX - notePosition.value.x,
        y: e.clientY - notePosition.value.y
      }
      document.addEventListener('mousemove', updateDragPosition)
      document.addEventListener('mouseup', stopDragging)
    }

    const updateDragPosition = (e: MouseEvent) => {
      if (!isDragging.value || !containerRef.value || !noteContainerRef.value) return

      const container = containerRef.value
      const noteContainer = noteContainerRef.value
      const containerRect = container.getBoundingClientRect()
      const noteRect = noteContainer.getBoundingClientRect()

      // 计算新位置
      let newX = e.clientX - dragOffset.value.x
      let newY = e.clientY - dragOffset.value.y

      // 限制在容器范围内
      newX = Math.max(0, Math.min(newX, containerRect.width - noteRect.width))
      newY = Math.max(0, Math.min(newY, containerRect.height - noteRect.height))

      notePosition.value = { x: newX, y: newY }
    }

    const stopDragging = () => {
      isDragging.value = false
      document.removeEventListener('mousemove', updateDragPosition)
      document.removeEventListener('mouseup', stopDragging)
    }

    onMounted(() => {
      document.addEventListener('mousedown', startSelection)
    })

    onUnmounted(() => {
      document.removeEventListener('mousedown', startSelection)
      document.removeEventListener('mousemove', updateDragPosition)
      document.removeEventListener('mouseup', stopDragging)
    })

    return {
      isSelecting,
      isCaptureEnabled,
      selectionStyle,
      screenshot,
      showDialog,
      noteContent,
      renderedNote,
      notePosition,
      isDragging,
      containerRef,
      noteContainerRef,
      toggleCapture,
      clearScreenshot,
      saveScreenshot,
      handleGenerateNote,
      clearNote,
      startDragging,
    }
  },
})
</script>

<style scoped>
.screen-capture-container {
  position: relative;
  width: 100%;
  height: 100%;
}

.toggle-button {
  position: absolute;
  top: 20px;
  left: 20px;
  padding: 8px 16px;
  background-color: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  z-index: 10000;
}

.toggle-button.active {
  background-color: #f56c6c;
}

.toggle-button:hover {
  opacity: 0.9;
}

.selection-box {
  position: fixed;
  border: 2px dashed #409eff;
  background: rgba(64, 158, 255, 0.1);
  pointer-events: none;
  z-index: 9999;
}

.screenshot-preview {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 10000;
  max-width: 300px;
}

.screenshot-preview img {
  max-width: 100%;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.preview-buttons {
  margin-top: 10px;
  display: flex;
  gap: 10px;
}

.preview-buttons button {
  padding: 5px 10px;
  background-color: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.preview-buttons button:hover {
  background-color: #66b1ff;
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10001;
}

.dialog-content {
  background-color: rgb(255, 255, 255);
  padding: 20px;
  border-radius: 8px;
  width: 80%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
}

.dialog-title {
  color: #000;
  margin-bottom: 20px;
  font-size: 18px;
}

.dialog-body {
  margin: 20px 0;
  color: #000;
}

.image-preview {
  margin-bottom: 20px;
  text-align: center;
}

.image-preview img {
  max-width: 100%;
  max-height: 300px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.question-section {
  margin-bottom: 20px;
}

.dialog-body textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  resize: vertical;
  color: #000;
}

.dialog-body .answer {
  margin-top: 20px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
  color: #000;
}

.dialog-body .answer h4 {
  color: #000;
  margin-bottom: 10px;
}

.dialog-body .answer p {
  color: #000;
  line-height: 1.5;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.dialog-footer button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.dialog-footer button:first-child {
  background-color: #409eff;
  color: white;
}

.dialog-footer button:last-child {
  background-color: #909399;
  color: white;
}

.dialog-footer button:disabled {
  background-color: #c0c4cc;
  cursor: not-allowed;
}

.preview-content {
  background-color: white;
  padding: 10px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.note-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.generate-note-btn {
  background-color: #67c23a;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 15px;
}

.generate-note-btn:hover {
  background-color: #85ce61;
}

.generate-note-btn:disabled {
  background-color: #a8e6a8;
  cursor: not-allowed;
}

.note-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 400px;
  max-height: 80vh;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  z-index: 100;
  display: flex;
  flex-direction: column;
  user-select: none;
  touch-action: none;
}

.note-header {
  padding: 15px 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.note-header h3 {
  margin: 0;
  color: #000;
  font-size: 16px;
}

.close-note-btn {
  background-color: #909399;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.close-note-btn:hover {
  background-color: #a6a9ad;
}

.note-body {
  padding: 20px;
  overflow-y: auto;
  max-height: calc(80vh - 60px);
}

.note-body .markdown-content {
  color: #000;
  line-height: 1.6;
}

.markdown-content :deep(h1) {
  font-size: 24px;
  margin-bottom: 16px;
}

.markdown-content :deep(h2) {
  font-size: 20px;
  margin: 16px 0;
}

.markdown-content :deep(p) {
  margin-bottom: 12px;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 12px 0;
  padding-left: 24px;
}

.markdown-content :deep(li) {
  margin: 6px 0;
}

.markdown-content :deep(code) {
  background-color: #f1f1f1;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: monospace;
}

.markdown-content :deep(pre) {
  background-color: #f1f1f1;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 12px 0;
}
</style>
