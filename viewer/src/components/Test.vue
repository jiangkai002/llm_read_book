<template>
  <div>
    <div v-for="page in numPages" :key="page" class="page">
      <canvas :ref="'canvas' + page"></canvas>
      <div :ref="'textLayer' + page" class="textLayer"></div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, watch } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { TextLayerBuilder } from 'pdfjs-dist/web/pdf_viewer'
// 设置本地 Worker 路径
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker

export default defineComponent({
  props: {
    src: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      numPages: 0,
    }
  },
  async mounted() {
    await this.loadPdf()
  },
  methods: {
    async loadPdf() {
      const loadingTask = pdfjsLib.getDocument(this.src)
      const pdf = await loadingTask.promise
      this.numPages = pdf.numPages
      for (let pageNum = 1; pageNum <= this.numPages; pageNum++) {
        const page = await pdf.getPage(pageNum)
        const scale = 1.5
        const viewport = page.getViewport({ scale })
        const canvas = this.$refs['canvas' + pageNum][0]
        const context = canvas.getContext('2d')
        canvas.height = viewport.height
        canvas.width = viewport.width
        const renderContext = {
          canvasContext: context,
          viewport: viewport,
        }
        await page.render(renderContext).promise
        const textContent = await page.getTextContent()
        const textLayerDiv = this.$refs['textLayer' + pageNum][0]
        const textLayerBuilder = new TextLayerBuilder({
          pdfPage: page,
        })
        await textLayerBuilder.render({
          viewport: viewport,
          textContentParams: { textContent }, // 显式传递 textContent
        })
      }
    },
  },
})
</script>

<style>
.page {
  position: relative;
  margin-bottom: 10px;
}

.textLayer {
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
  opacity: 0.2;
  line-height: 1;
}

.textLayer > div {
  color: transparent;
  position: absolute;
  white-space: pre;
  cursor: text;
  transform-origin: 0% 0%;
}
</style>
