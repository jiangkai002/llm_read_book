<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  modelValue: string
  isLoading: boolean
  attachedImage: string | null
  useImageUnderstanding: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: string): void
  (e: 'update:useImageUnderstanding', val: boolean): void
  (e: 'send'): void
  (e: 'paste-image', dataUrl: string): void
  (e: 'clear-attachment'): void
}>()

const textareaRef = ref<HTMLTextAreaElement | null>(null)

const handleInput = (e: Event) => {
  const el = e.target as HTMLTextAreaElement
  emit('update:modelValue', el.value)
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    emit('send')
  }
}

const handlePaste = (e: ClipboardEvent) => {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of Array.from(items)) {
    if (item.type.startsWith('image/')) {
      e.preventDefault()
      const file = item.getAsFile()
      if (!file) return
      const reader = new FileReader()
      reader.onload = (ev) => {
        emit('paste-image', ev.target?.result as string)
      }
      reader.readAsDataURL(file)
      break
    }
  }
}

const persistUseImage = (e: Event) => {
  const checked = (e.target as HTMLInputElement).checked
  localStorage.setItem('ai_use_image', checked ? 'true' : 'false')
  emit('update:useImageUnderstanding', checked)
}

defineExpose({ textareaRef })
</script>

<template>
  <div class="chat-input-area">
    <!-- 附图预览 -->
    <div v-if="attachedImage" class="attachment-preview">
      <img :src="attachedImage" alt="附加截图" />
      <button class="remove-attachment" @click="emit('clear-attachment')">✕</button>
    </div>

    <!-- 输入框 -->
    <div class="input-row">
      <textarea
        ref="textareaRef"
        :value="modelValue"
        placeholder="输入问题，或粘贴 PDF 文字 / 截图（Shift+Enter 换行）"
        rows="1"
        @input="handleInput"
        @keydown="handleKeydown"
        @paste="handlePaste"
      ></textarea>
      <button
        class="send-btn"
        :disabled="isLoading || (!modelValue.trim() && !attachedImage)"
        @click="emit('send')"
      >
        <svg v-if="!isLoading" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M2 21l21-9L2 3v7l15 2-15 2v7z" />
        </svg>
        <span v-else class="spin">⟳</span>
      </button>
    </div>

    <label
      class="use-image-option"
      :class="{ 'is-disabled': !attachedImage }"
      :title="attachedImage ? '关闭后仅根据文字回答，不读取截图像素' : '请先附加截图后再开启'"
    >
      <input
        type="checkbox"
        :checked="useImageUnderstanding"
        :disabled="!attachedImage"
        @change="persistUseImage"
      />
      <span>启用图片理解</span>
    </label>

    <div class="input-hint">Enter 发送 · Shift+Enter 换行 · 可直接粘贴截图</div>
  </div>
</template>

<style scoped>
.chat-input-area {
  background: #fff;
  border-top: 1px solid #e5e7eb;
  padding: 10px 12px 8px;
  flex-shrink: 0;
}
.attachment-preview {
  position: relative;
  display: inline-block;
  margin-bottom: 8px;
}
.attachment-preview img {
  height: 72px;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  display: block;
}
.remove-attachment {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #ef4444;
  color: #fff;
  border: none;
  cursor: pointer;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}
.input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
textarea {
  flex: 1;
  resize: none;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  padding: 9px 12px;
  font-family: 'Microsoft YaHei', '微软雅黑', sans-serif;
  font-size: 13.5px;
  line-height: 1.5;
  outline: none;
  color: #111;
  background: #f9fafb;
  transition: border-color 0.15s, box-shadow 0.15s;
  max-height: 160px;
  overflow-y: auto;
}
textarea:focus {
  border-color: #6366f1;
  background: #fff;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15);
}
textarea::placeholder {
  color: #9ca3af;
}
.send-btn {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  border: none;
  background: #6366f1;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s, transform 0.1s;
}
.send-btn:hover:not(:disabled) {
  background: #4f46e5;
  transform: scale(1.05);
}
.send-btn:disabled {
  background: #c4b5fd;
  cursor: not-allowed;
  transform: none;
}
.spin {
  display: inline-block;
  animation: spin 1s linear infinite;
  font-size: 16px;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.use-image-option {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  font-size: 12px;
  color: #4b5563;
  cursor: pointer;
  user-select: none;
}
.use-image-option input {
  width: 14px;
  height: 14px;
  accent-color: #6366f1;
  cursor: pointer;
}
.use-image-option.is-disabled {
  color: #9ca3af;
  cursor: not-allowed;
}
.use-image-option.is-disabled input {
  cursor: not-allowed;
}
.input-hint {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 5px;
  text-align: center;
}
</style>
