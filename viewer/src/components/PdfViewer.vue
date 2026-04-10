<script setup lang="ts">
import { PDFViewer, type PluginRegistry } from '@embedpdf/vue-pdf-viewer'

const props = defineProps<{
  url: string
}>()

const emit = defineEmits<{
  ready: [registry: PluginRegistry]
}>()

const onReady = (registry: PluginRegistry) => {
  emit('ready', registry)
}
</script>

<template>
  <div style="height: 100%">
    <PDFViewer
      :config="{
        src: props.url,
        theme: { preference: 'light' },
      }"
      :style="{ width: '100%', height: '100%' }"
      @ready="onReady"
    />
  </div>
</template>
