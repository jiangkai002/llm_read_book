<script setup lang="ts">
import { PDFViewer } from '@embedpdf/vue-pdf-viewer'
</script>

<template>
  <div style="height: 100vh">
    <PDFViewer
      :config="{
        src: '/test.pdf',
        theme: { preference: 'light' },
      }"
      :style="{ width: '100%', height: '100%' }"
    />
  </div>
</template>
