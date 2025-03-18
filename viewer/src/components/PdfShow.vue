<template>
  <div class="pdf-viewer">
    <div v-if="loading" class="loading">Loading PDF...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else class="pdf-container">
      <div class="toolbar">
        <button @click="prevPage" :disabled="currentPage <= 1">Previous</button>
        <span>Page {{ currentPage }} of {{ totalPages }}</span>
        <button @click="nextPage" :disabled="currentPage >= totalPages">Next</button>
        <input
          type="range"
          min="1"
          :max="totalPages"
          v-model.number="currentPage"
          class="page-slider"
        />
        <select v-model="scale">
          <option value="0.5">50%</option>
          <option value="0.75">75%</option>
          <option value="1">100%</option>
          <option value="1.25">125%</option>
          <option value="1.5">150%</option>
          <option value="2">200%</option>
        </select>
      </div>
      <canvas ref="pdfCanvas" class="pdf-canvas"></canvas>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue'
import * as pdfjs from 'pdfjs-dist'

// Set the worker source path
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`

export default {
  name: 'PdfShow',
  props: {
    src: {
      type: String,
      required: true,
    },
  },
  setup(props) {
    const pdfCanvas = ref(null)
    const pdfDoc = ref(null)
    const currentPage = ref(1)
    const totalPages = ref(0)
    const loading = ref(true)
    const error = ref(null)
    const scale = ref(1)

    const loadPdf = async () => {
      try {
        loading.value = true
        error.value = null

        const loadingTask = pdfjs.getDocument(props.src)
        pdfDoc.value = await loadingTask.promise
        totalPages.value = pdfDoc.value.numPages

        renderPage(currentPage.value)
        loading.value = false
      } catch (err) {
        console.error('Error loading PDF:', err)
        error.value = 'Failed to load PDF document.'
        loading.value = false
      }
    }

    const renderPage = async (pageNum) => {
      if (!pdfDoc.value) return

      try {
        const page = await pdfDoc.value.getPage(pageNum)
        const viewport = page.getViewport({ scale: parseFloat(scale.value) })

        const canvas = pdfCanvas.value
        const context = canvas.getContext('2d')

        canvas.height = viewport.height
        canvas.width = viewport.width

        const renderContext = {
          canvasContext: context,
          viewport,
        }

        await page.render(renderContext).promise
      } catch (err) {
        console.error('Error rendering page:', err)
        error.value = 'Failed to render PDF page.'
      }
    }

    const nextPage = () => {
      if (currentPage.value < totalPages.value) {
        currentPage.value++
      }
    }

    const prevPage = () => {
      if (currentPage.value > 1) {
        currentPage.value--
      }
    }

    watch(
      () => props.src,
      () => {
        if (props.src) {
          loadPdf()
        }
      },
      { immediate: true },
    )

    watch(currentPage, () => {
      renderPage(currentPage.value)
    })

    watch(scale, () => {
      renderPage(currentPage.value)
    })

    onMounted(() => {
      if (props.src) {
        loadPdf()
      }
    })

    return {
      pdfCanvas,
      currentPage,
      totalPages,
      loading,
      error,
      scale,
      nextPage,
      prevPage,
    }
  },
}
</script>

<style scoped>
.pdf-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

.loading,
.error {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  font-size: 18px;
}

.error {
  color: red;
}

.pdf-container {
  display: flex;
  flex-direction: column;
  flex-grow: 1;
  overflow: hidden;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background-color: #f0f0f0;
  border-bottom: 1px solid #ddd;
}

.page-slider {
  flex-grow: 1;
  margin: 0 10px;
}

.pdf-canvas {
  margin: 0 auto;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
  background-color: white;
  max-height: calc(100vh - 80px);
  overflow: auto;
}
</style>
