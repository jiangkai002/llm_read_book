<!-- QuestionDialog.vue -->
<template>
  <div v-if="modelValue" class="dialog-overlay">
    <div class="dialog-content">
      <h3 class="dialog-title">对图片提问</h3>
      <div class="dialog-body">
        <div class="image-preview">
          <img :src="screenshot || ''" alt="当前截取的屏幕画面" />
        </div>
        <div class="question-section">
          <textarea v-model="questionText" placeholder="请输入您的问题..." rows="4"></textarea>
        </div>
        <div class="answer" v-if="answer">
          <h4>回答：</h4>
          <p>{{ answer }}</p>
          <div class="note-section" v-if="answer">
            <button
              class="generate-note-btn"
              @click="handleGenerateNote"
              :disabled="isGeneratingNote"
            >
              {{ isGeneratingNote ? '生成中...' : '生成笔记' }}
            </button>
          </div>
        </div>
      </div>
      <div class="dialog-footer">
        <button @click="askQuestion" :disabled="!questionText.trim()">提问</button>
        <button @click="closeDialog">关闭</button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, watch } from 'vue'
import { marked } from 'marked'

export default defineComponent({
  name: 'QuestionDialog',
  props: {
    modelValue: {
      type: Boolean,
      required: true
    },
    screenshot: {
      type: String,
      required: true
    }
  },
  emits: ['update:modelValue', 'generate-note'],
  setup(props, { emit }) {
    const questionText = ref('')
    const answer = ref('')
    const isGeneratingNote = ref(false)

    const closeDialog = () => {
      emit('update:modelValue', false)
      questionText.value = ''
      answer.value = ''
    }

    const askQuestion = async () => {
      if (!questionText.value.trim() || !props.screenshot) return

      try {
        // TODO: 这里需要调用后端API来处理图片和问题
        // 示例代码：
        // const response = await fetch('/api/ask', {
        //   method: 'POST',
        //   body: JSON.stringify({
        //     image: props.screenshot,
        //     question: questionText.value
        //   })
        // })
        // const data = await response.json()
        // answer.value = data.answer

        // 临时模拟回答
        answer.value = '这是一个模拟的回答。实际使用时需要连接后端API来处理图片和问题。'
      } catch (error) {
        console.error('提问失败:', error)
        answer.value = '抱歉，处理您的问题时出现错误。'
      }
    }

    const handleGenerateNote = async () => {
      if (!answer.value || !props.screenshot) return
      
      isGeneratingNote.value = true
      try {
        // 临时模拟笔记内容
        const noteContent = `# 截图笔记

## 问题
${questionText.value}

## 回答
${answer.value}

## 总结
这是一个基于截图内容生成的笔记。实际使用时需要连接后端API来生成更详细的笔记内容。`

        emit('generate-note', noteContent)
        closeDialog()
      } catch (error) {
        console.error('生成笔记失败:', error)
      } finally {
        isGeneratingNote.value = false
      }
    }

    return {
      questionText,
      answer,
      isGeneratingNote,
      closeDialog,
      askQuestion,
      handleGenerateNote
    }
  }
})
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10001;
}
.dialog-content {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  width: 80%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
}
.dialog-title {
  color: #000;
  margin-bottom: 20px;
  font-size: 18px;
}
.dialog-body {
  margin: 20px 0;
  color: #000;
}
.image-preview {
  margin-bottom: 20px;
  text-align: center;
}
.image-preview img {
  max-width: 100%;
  max-height: 300px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.question-section {
  margin-bottom: 20px;
}
.dialog-body textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  resize: vertical;
  color: #000;
}
.dialog-body .answer {
  margin-top: 20px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
  color: #000;
}
.dialog-body .answer h4 {
  color: #000;
  margin-bottom: 10px;
}
.dialog-body .answer p {
  color: #000;
  line-height: 1.5;
}
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.dialog-footer button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.dialog-footer button:first-child {
  background-color: #409eff;
  color: white;
}
.dialog-footer button:last-child {
  background-color: #909399;
  color: white;
}
.dialog-footer button:disabled {
  background-color: #c0c4cc;
  cursor: not-allowed;
}
.note-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}
.generate-note-btn {
  background-color: #67c23a;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 15px;
}
.generate-note-btn:hover {
  background-color: #85ce61;
}
.generate-note-btn:disabled {
  background-color: #a8e6a8;
  cursor: not-allowed;
}
</style> 