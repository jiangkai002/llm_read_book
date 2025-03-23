<!-- PdfViewer.vue -->
<template>
  <div class="pdf-viewer">
    <div class="controls">
      <button @click="prevPage" :disabled="pageNum <= 1">上一页</button>
      <span>第 {{ pageNum }} 页 / 共 {{ pageCount }} 页</span>
      <button @click="nextPage" :disabled="pageNum >= pageCount">下一页</button>
      <button @click="zoomIn">+</button>
      <button @click="zoomOut">-</button>
      <span>缩放: {{ (scale * 100).toFixed(0) }}%</span>
    </div>
    <canvas ref="pdfCanvas"></canvas>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, watch } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
// 设置本地 Worker 路径
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
    const pageNum = ref(1)
    const pageCount = ref(0)
    const scale = ref(1.0)
    let pdfDoc: pdfjsLib.PDFDocumentProxy | null = null

    // 加载PDF文档
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

    // 渲染页面
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

    // 上一页
    const prevPage = () => {
      if (pageNum.value <= 1) return
      pageNum.value -= 1
      renderPage(pageNum.value)
    }

    // 下一页
    const nextPage = () => {
      if (pageNum.value >= pageCount.value) return
      pageNum.value += 1
      renderPage(pageNum.value)
    }

    // 放大
    const zoomIn = () => {
      if (scale.value >= 2.0) return
      scale.value += 0.1
      renderPage(pageNum.value)
    }

    // 缩小
    const zoomOut = () => {
      if (scale.value <= 0.5) return
      scale.value -= 0.1
      renderPage(pageNum.value)
    }

    // 监听URL变化
    watch(
      () => props.url,
      () => {
        pageNum.value = 1
        loadPdf()
      },
    )

    // 监听页面变化
    watch(pageNum, (newPageNum) => {
      renderPage(newPageNum)
    })

    onMounted(() => {
      loadPdf()
    })

    return {
      pdfCanvas,
      pageNum,
      pageCount,
      scale,
      prevPage,
      nextPage,
      zoomIn,
      zoomOut,
    }
  },
})
</script>

<style scoped>
.pdf-viewer {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.controls {
  margin-bottom: 10px;
}

button {
  margin: 0 5px;
  padding: 5px 10px;
}

canvas {
  border: 1px solid #ccc;
}
</style>
