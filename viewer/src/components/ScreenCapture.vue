<!-- ScreenCapture.vue -->
<template>
  <div class="screen-capture-container" ref="containerRef">
    <!-- 控制按钮 -->
    <button class="toggle-button" :class="{ active: isCaptureEnabled }" @click="toggleCapture">
      {{ isCaptureEnabled ? '关闭截图（ESC）' : '开启截图' }}
    </button>

    <!-- 半透明遮罩：截图模式下覆盖全屏，提示用户框选 -->
    <div v-if="isCaptureEnabled && !isSelecting" class="capture-overlay">
      <span class="capture-hint">拖拽框选截图区域</span>
    </div>

    <!-- 框选区域 -->
    <div v-if="isSelecting" class="selection-box" :style="selectionStyle"></div>

    <!-- DEBUG 预览窗口 -->
    <div v-if="debugPreview" class="debug-preview">
      <div class="debug-header">
        <span class="debug-title">DEBUG 预览</span>
        <button class="debug-close" @click="debugPreview = null">✕</button>
      </div>
      <div class="debug-info">{{ debugInfo }}</div>
      <img :src="debugPreview" alt="debug preview" />
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, watch, onMounted, onUnmounted } from 'vue'
import html2canvas from 'html2canvas'

export default defineComponent({
  name: 'ScreenCapture',
  props: {
    targetId: {
      type: String,
      default: '',
    },
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
    const containerRef = ref<HTMLElement | null>(null)
    const debugPreview = ref<string | null>(null)
    const debugInfo = ref('')

    const selectionStyle = computed(() => ({
      left: `${Math.min(startX.value, endX.value)}px`,
      top: `${Math.min(startY.value, endY.value)}px`,
      width: `${Math.abs(endX.value - startX.value)}px`,
      height: `${Math.abs(endY.value - startY.value)}px`,
    }))

    const toggleCapture = () => {
      isCaptureEnabled.value = !isCaptureEnabled.value
      if (!isCaptureEnabled.value) {
        isSelecting.value = false
      }
    }

    watch(
      () => props.captureTrigger,
      () => {
        if (props.captureTrigger > 0) isCaptureEnabled.value = true
      },
    )

    const handleKeydown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isCaptureEnabled.value) {
        isCaptureEnabled.value = false
        isSelecting.value = false
      }
    }

    const startSelection = (e: MouseEvent) => {
      if (!isCaptureEnabled.value) return

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

      const selLeft = Math.min(startX.value, endX.value)
      const selTop = Math.min(startY.value, endY.value)
      const selWidth = Math.abs(endX.value - startX.value)
      const selHeight = Math.abs(endY.value - startY.value)
      if (selWidth < 10 || selHeight < 10) return

      try {
        // 记录原始 canvas 元素，html2canvas 克隆 DOM 时 canvas 像素数据会丢失
        const originalCanvases = Array.from(document.querySelectorAll('canvas'))

        const fullCanvas = await html2canvas(document.body, {
          useCORS: true,
          allowTaint: true,
          width: window.innerWidth,
          height: window.innerHeight,
          x: 0,
          y: 0,
          scrollX: 0,
          scrollY: 0,
          onclone: (_doc: Document, clonedBody: HTMLElement) => {
            // 把原始 canvas 的像素数据手动画到克隆的 canvas 上
            const clonedCanvases = Array.from(clonedBody.querySelectorAll('canvas'))
            clonedCanvases.forEach((clonedCvs, i) => {
              const orig = originalCanvases[i]
              if (!orig || orig.width === 0 || orig.height === 0) return
              clonedCvs.width = orig.width
              clonedCvs.height = orig.height
              const ctx2d = clonedCvs.getContext('2d')
              if (ctx2d) ctx2d.drawImage(orig, 0, 0)
            })
          },
        })

        // 从实际 canvas 尺寸反推缩放比，不依赖 devicePixelRatio
        const scaleX = fullCanvas.width / window.innerWidth
        const scaleY = fullCanvas.height / window.innerHeight

        const cropCanvas = document.createElement('canvas')
        cropCanvas.width = Math.round(selWidth * scaleX)
        cropCanvas.height = Math.round(selHeight * scaleY)
        const ctx = cropCanvas.getContext('2d')
        if (!ctx) return

        ctx.drawImage(
          fullCanvas,
          Math.round(selLeft * scaleX),
          Math.round(selTop * scaleY),
          Math.round(selWidth * scaleX),
          Math.round(selHeight * scaleY),
          0,
          0,
          cropCanvas.width,
          cropCanvas.height,
        )

        const dataUrl = cropCanvas.toDataURL('image/png')

        // DEBUG 信息
        debugInfo.value = [
          `dpr=${window.devicePixelRatio}`,
          `viewport=${window.innerWidth}x${window.innerHeight}`,
          `fullCanvas=${fullCanvas.width}x${fullCanvas.height}`,
          `scale=${scaleX.toFixed(3)}x${scaleY.toFixed(3)}`,
          `sel=(${selLeft},${selTop}) ${selWidth}x${selHeight}`,
          `crop=(${Math.round(selLeft * scaleX)},${Math.round(selTop * scaleY)}) ${cropCanvas.width}x${cropCanvas.height}`,
        ].join(' | ')
        debugPreview.value = dataUrl

        emit('screenshot', dataUrl)
        isCaptureEnabled.value = false
      } catch (error) {
        console.error('截图失败:', error)
      }
    }

    onMounted(() => {
      document.addEventListener('mousedown', startSelection)
      document.addEventListener('keydown', handleKeydown)
    })

    onUnmounted(() => {
      document.removeEventListener('mousedown', startSelection)
      document.removeEventListener('keydown', handleKeydown)
    })

    return {
      isSelecting,
      isCaptureEnabled,
      selectionStyle,
      containerRef,
      toggleCapture,
      debugPreview,
      debugInfo,
    }
  },
})
</script>

<style scoped>
.screen-capture-container {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.toggle-button {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 6px 14px;
  background: #6366f1;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  z-index: 10000;
  font-size: 13px;
  pointer-events: auto;
  transition: background 0.15s;
}

.toggle-button.active {
  background: #ef4444;
}

.toggle-button:hover {
  opacity: 0.9;
}

.capture-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.15);
  z-index: 9998;
  cursor: crosshair;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: auto;
}

.capture-hint {
  padding: 8px 20px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  border-radius: 8px;
  font-size: 14px;
  pointer-events: none;
  user-select: none;
}

.selection-box {
  position: fixed;
  border: 2px solid #6366f1;
  background: rgba(99, 102, 241, 0.12);
  pointer-events: none;
  z-index: 9999;
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.25);
}

/* DEBUG 预览窗口 */
.debug-preview {
  position: fixed;
  bottom: 16px;
  left: 16px;
  max-width: 420px;
  background: #1e1e2e;
  border: 1px solid #444;
  border-radius: 8px;
  z-index: 10001;
  pointer-events: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  overflow: hidden;
}

.debug-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #2d2d3f;
}

.debug-title {
  color: #f59e0b;
  font-size: 12px;
  font-weight: 600;
  font-family: monospace;
}

.debug-close {
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  font-size: 14px;
  padding: 0 4px;
}

.debug-close:hover {
  color: #fff;
}

.debug-info {
  padding: 6px 10px;
  color: #a5f3fc;
  font-size: 11px;
  font-family: monospace;
  line-height: 1.6;
  word-break: break-all;
  border-bottom: 1px solid #333;
}

.debug-preview img {
  display: block;
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
}
</style>
