<!-- ScreenCapture.vue -->
<template>
  <div class="screen-capture-container">
    <!-- 控制按钮 -->
    <button 
      class="toggle-button"
      :class="{ active: isCaptureEnabled }"
      @click="toggleCapture"
    >
      {{ isCaptureEnabled ? '关闭截图' : '开启截图' }}
    </button>

    <!-- 截图预览区域 -->
    <div v-if="screenshot" class="screenshot-preview">
      <img :src="screenshot" alt="Screenshot" />
      <div class="preview-buttons">
        <button @click="clearScreenshot">清除截图</button>
        <button @click="saveScreenshot">保存到本地</button>
      </div>
    </div>

    <!-- 框选区域 -->
    <div
      v-if="isSelecting"
      class="selection-box"
      :style="selectionStyle"
    ></div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, onMounted, onUnmounted } from 'vue'
import html2canvas from 'html2canvas'

export default defineComponent({
  name: 'ScreenCapture',
  props: {
    targetId: {
      type: String,
      default: ''
    }
  },
  setup(props) {
    const isSelecting = ref(false)
    const isCaptureEnabled = ref(false)
    const startX = ref(0)
    const startY = ref(0)
    const endX = ref(0)
    const endY = ref(0)
    const screenshot = ref<string | null>(null)

    const selectionStyle = computed(() => ({
      left: `${Math.min(startX.value, endX.value)}px`,
      top: `${Math.min(startY.value, endY.value)}px`,
      width: `${Math.abs(endX.value - startX.value)}px`,
      height: `${Math.abs(endY.value - startY.value)}px`
    }))

    const toggleCapture = () => {
      isCaptureEnabled.value = !isCaptureEnabled.value
      if (!isCaptureEnabled.value) {
        isSelecting.value = false
        screenshot.value = null
      }
    }

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
          useCORS: true
        })

        screenshot.value = canvas.toDataURL('image/png')
      } catch (error) {
        console.error('截图失败:', error)
      }
    }

    const clearScreenshot = () => {
      screenshot.value = null
    }

    // 新增：保存截图到本地
    const saveScreenshot = () => {
      if (!screenshot.value) return

      const link = document.createElement('a')
      link.download = `screenshot-${new Date().toISOString().replace(/[:.]/g, '-')}.png`
      link.href = screenshot.value
      link.click()
    }

    onMounted(() => {
      document.addEventListener('mousedown', startSelection)
    })

    onUnmounted(() => {
      document.removeEventListener('mousedown', startSelection)
    })

    return {
      isSelecting,
      isCaptureEnabled,
      selectionStyle,
      screenshot,
      toggleCapture,
      clearScreenshot,
      saveScreenshot
    }
  }
})
</script>

<style scoped>
.screen-capture-container {
  position: relative;
  width: 100%;
  height: 100%;
}

.toggle-button {
  position: fixed;
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
</style>