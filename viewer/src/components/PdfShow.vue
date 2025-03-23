<!-- PdfViewer.vue -->
<template>
  <div class="pdf-viewer">
    <div class="controls">
      <button @click="prevPage" :disabled="pageNum <= 1">上一页</button>
      <span>第 {{ pageNum }} 页 / 共 {{ pageCount }} 页</span>
      <button @click="nextPage" :disabled="pageNum >= pageCount">下一页</button>
    </div>
    <div ref="pageContainer" class="page-container">
      <canvas ref="pdfCanvas"></canvas>
      <div ref="textLayer" class="text-layer"></div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, watch } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { TextLayerBuilder } from 'pdfjs-dist/web/pdf_viewer.mjs'

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
    const textLayer = ref<HTMLDivElement | null>(null)
    const pageContainer = ref<HTMLDivElement | null>(null)
    const pageNum = ref(1)
    const pageCount = ref(0)
    let pdfDoc: pdfjsLib.PDFDocumentProxy | null = null
    const scale = 2 // 调整缩放比例，避免过小

    // 加载 PDF
    const loadPdf = async () => {
      try {
        const loadingTask = pdfjsLib.getDocument(props.url)
        pdfDoc = await loadingTask.promise
        pageCount.value = pdfDoc.numPages
        renderPage(pageNum.value)
      } catch (error) {
        console.error('PDF 加载失败:', error)
      }
    }

    // 渲染页面
    const renderPage = async (num: number) => {
      if (!pdfDoc || !pdfCanvas.value || !textLayer.value) return

      try {
        const page = await pdfDoc.getPage(num)
        const viewport = page.getViewport({ scale })

        // 准备 canvas
        const canvas = pdfCanvas.value
        const context = canvas.getContext('2d')
        if (!context) return
        canvas.height = viewport.height
        canvas.width = viewport.width

        // 渲染 PDF 到 canvas
        const renderContext = {
          canvasContext: context,
          viewport: viewport,
        }
        const renderTask = page.render(renderContext)
        await renderTask.promise

        // 渲染文本层
        const textLayerDiv = textLayer.value
        console.log('textLayerDiv:', textLayerDiv)

        // 清空之前的文本层内容
        textLayerDiv.innerHTML = ''

        // 创建 TextLayerBuilder 实例
        const textLayerBuilder = new TextLayerBuilder({
          pdfPage: page,
        })

        // 设置文本层容器的基本样式
        textLayerDiv.style.width = `${viewport.width}px`
        textLayerDiv.style.height = `${viewport.height}px`
        textLayerDiv.style.position = 'absolute'
        textLayerDiv.style.top = '0'
        textLayerDiv.style.left = '0'
        //设置文本颜色黑色
        textLayerDiv.style.color = 'black'

        // 将 TextLayerBuilder 的 div 添加到 textLayer 容器中
        textLayerDiv.appendChild(textLayerBuilder.div)
        console.log('textLayerBuilder:', textLayerBuilder.div)

        // 获取文本内容并渲染文本层
        const textContent = await page.getTextContent()
        console.log('textContent:', textContent)
        await textLayerBuilder.render({
          viewport: viewport,
          textContentParams: { textContent }, // 显式传递 textContent
        })
      } catch (error) {
        console.error('页面渲染失败:', error)
      }
    }

    // 上一页
    const prevPage = () => {
      if (pageNum.value <= 1) return
      pageNum.value--
    }

    // 下一页
    const nextPage = () => {
      if (pageNum.value >= pageCount.value) return
      pageNum.value++
    }

    // 监听页码变化
    watch(pageNum, (newPage) => {
      renderPage(newPage)
    })

    // 监听 URL 变化
    watch(
      () => props.url,
      () => {
        pageNum.value = 1
        loadPdf()
      },
    )

    onMounted(() => {
      loadPdf()
    })

    return {
      pdfCanvas,
      textLayer,
      pageContainer,
      pageNum,
      pageCount,
      prevPage,
      nextPage,
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
  margin: 10px 0;
}

button {
  margin: 0 10px;
  padding: 5px 10px;
}

.page-container {
  position: relative;
}

canvas {
  border: 1px solid #ccc;
}

.text-layer {
  position: absolute;
  top: 0;
  left: 0;
  /* 移除可能干扰的样式 */
}

/* 文本层的子元素样式由 TextLayerBuilder 控制 */
.text-layer span {
  position: absolute;
  white-space: pre;
  cursor: text;
}
</style>
