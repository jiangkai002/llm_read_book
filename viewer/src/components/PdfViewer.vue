<!-- PdfViewer.vue -->
<template>
  <div class="pdf-viewer" @wheel.prevent="handleWheel" ref="viewerContainer">
    <div class="controls">
      <button @click="prevPage" :disabled="pageNum <= 1">上一页</button>
      <span>第 {{ pageNum }} 页 / 共 {{ pageCount }} 页</span>
      <button @click="nextPage" :disabled="pageNum >= pageCount">下一页</button>
      <button @click="zoomIn">+</button>
      <button @click="zoomOut">-</button>
      <span>缩放: {{ (scale * 100).toFixed(0) }}%</span>
    </div>
    <div class="canvas-container" ref="canvasContainer">
      <canvas ref="pdfCanvas" class="canvas"></canvas>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, watch } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker

export default defineComponent({
  name: 'PdfViewer',
  props: {
    url: {
      type: String,
      required: true,
    },
  },

  setup(props) {
    const pdfCanvas = ref<HTMLCanvasElement | null>(null)
    const viewerContainer = ref<HTMLDivElement | null>(null)
    const canvasContainer = ref<HTMLDivElement | null>(null)
    const pageNum = ref(1)
    const pageCount = ref(0)
    const scale = ref(1)
    let pdfDoc: pdfjsLib.PDFDocumentProxy | null = null

    const loadPdf = async () => {
      try {
        const loadingTask = pdfjsLib.getDocument(props.url)
        pdfDoc = await loadingTask.promise
        pageCount.value = pdfDoc.numPages
        renderPage(pageNum.value)
      } catch (error) {
        console.error('PDF加载失败:', error)
      }
    }

    const renderPage = async (num: number) => {
      if (!pdfDoc || !pdfCanvas.value) return

      try {
        const page = await pdfDoc.getPage(num)
        const viewport = page.getViewport({ scale: scale.value })

        const canvas = pdfCanvas.value
        const context = canvas.getContext('2d')
        if (!context) return

        canvas.height = viewport.height
        canvas.width = viewport.width

        const renderContext = {
          canvasContext: context,
          viewport: viewport,
        }

        await page.render(renderContext).promise
      } catch (error) {
        console.error('页面渲染失败:', error)
      }
    }

    const prevPage = () => {
      if (pageNum.value <= 1) return
      pageNum.value -= 1
      renderPage(pageNum.value)
    }

    const nextPage = () => {
      if (pageNum.value >= pageCount.value) return
      pageNum.value += 1
      renderPage(pageNum.value)
    }

    const zoomIn = () => {
      if (scale.value >= 3.0) return
      scale.value += 0.1
      renderPage(pageNum.value)
    }

    const zoomOut = () => {
      if (scale.value <= 0.5) return
      scale.value -= 0.1
      renderPage(pageNum.value)
    }

    const handleWheel = (event: WheelEvent) => {
      event.preventDefault()

      if (event.ctrlKey) {
        // Ctrl + 滚轮用于缩放
        const zoomSpeed = 0.1
        const delta = event.deltaY > 0 ? -zoomSpeed : zoomSpeed
        const newScale = scale.value + delta

        if (newScale >= 0.5 && newScale <= 3.0) {
          scale.value = newScale
          renderPage(pageNum.value)
        }
      } else if (canvasContainer.value) {
        // 普通滚轮用于滚动
        const scrollSpeed = 50 // 控制滚动速度
        canvasContainer.value.scrollTop += (event.deltaY * scrollSpeed) / 100
        canvasContainer.value.scrollLeft += (event.deltaX * scrollSpeed) / 100
      }
    }

    watch(
      () => props.url,
      () => {
        pageNum.value = 1
        loadPdf()
      },
    )

    watch(pageNum, (newPageNum) => {
      renderPage(newPageNum)
    })

    onMounted(() => {
      loadPdf()
    })

    return {
      pdfCanvas,
      viewerContainer,
      canvasContainer,
      pageNum,
      pageCount,
      scale,
      prevPage,
      nextPage,
      zoomIn,
      zoomOut,
      handleWheel,
    }
  },
})
</script>

<style scoped>
.pdf-viewer {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.controls {
  margin-bottom: 10px;
  position: sticky;
  top: 0;
  background: white;
  z-index: 1;
  padding: 5px;
}

button {
  margin: 0 5px;
  padding: 5px 10px;
}

.canvas-container {
  width: 100%;
  height: calc(100% - 50px);
  overflow: auto;
  display: flex;
  justify-content: center;
  align-items: center;
}

.canvas {
  border: 1px solid #ca1a1a;
  display: block;
}
</style>
