<script setup lang="ts">
import deleteIcon from '@/assets/delete.svg'
import type { Conversation } from '@/composables/useChatHistory'

defineProps<{
  conversations: Conversation[]
  currentConvId: string
  groupedConversations: { today: Conversation[]; earlier: Conversation[] }
}>()

const emit = defineEmits<{
  (e: 'switch', conv: Conversation): void
  (e: 'delete', id: string, event: Event): void
}>()

const formatConvDate = (ts: number): string => {
  const d = new Date(ts)
  const now = new Date()
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}
</script>

<template>
  <div class="history-panel">
    <div class="history-header">
      <span>历史对话</span>
      <span class="history-count">共 {{ conversations.length }} 条</span>
    </div>
    <div class="history-list">
      <template v-if="conversations.length === 0">
        <div class="history-empty">暂无历史对话</div>
      </template>
      <template v-else>
        <div v-if="groupedConversations.today.length" class="history-group-label">今天</div>
        <div
          v-for="conv in groupedConversations.today"
          :key="conv.id"
          class="history-item"
          :class="{ active: conv.id === currentConvId }"
          @click="emit('switch', conv)"
        >
          <div class="history-item-title">{{ conv.title }}</div>
          <div class="history-item-meta">{{ formatConvDate(conv.updatedAt) }}</div>
          <button class="history-item-del" title="删除" @click="emit('delete', conv.id, $event)">
            <img :src="deleteIcon" alt="" width="12" height="12" />
          </button>
        </div>
        <div v-if="groupedConversations.earlier.length" class="history-group-label">更早</div>
        <div
          v-for="conv in groupedConversations.earlier"
          :key="conv.id"
          class="history-item"
          :class="{ active: conv.id === currentConvId }"
          @click="emit('switch', conv)"
        >
          <div class="history-item-title">{{ conv.title }}</div>
          <div class="history-item-meta">{{ formatConvDate(conv.updatedAt) }}</div>
          <button class="history-item-del" title="删除" @click="emit('delete', conv.id, $event)">
            <img :src="deleteIcon" alt="" width="12" height="12" />
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.history-panel {
  flex-shrink: 0;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  max-height: 280px;
  overflow: hidden;
}
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px 6px;
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  border-bottom: 1px solid #f3f4f6;
  flex-shrink: 0;
}
.history-count {
  font-weight: 400;
  color: #9ca3af;
}
.history-list {
  overflow-y: auto;
  flex: 1;
  padding: 4px 0;
}
.history-list::-webkit-scrollbar {
  width: 3px;
}
.history-list::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}
.history-empty {
  padding: 20px;
  text-align: center;
  color: #9ca3af;
  font-size: 12px;
}
.history-group-label {
  padding: 4px 14px 2px;
  font-size: 11px;
  color: #9ca3af;
  font-weight: 500;
}
.history-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  cursor: pointer;
  border-radius: 6px;
  margin: 1px 6px;
  transition: background 0.12s;
  position: relative;
}
.history-item:hover {
  background: #f3f4f6;
}
.history-item.active {
  background: #ede9fe;
}
.history-item-title {
  flex: 1;
  font-size: 12.5px;
  color: #1a1a1a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.history-item.active .history-item-title {
  color: #4f46e5;
  font-weight: 500;
}
.history-item-meta {
  font-size: 11px;
  color: #9ca3af;
  flex-shrink: 0;
}
.history-item-del {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  flex-shrink: 0;
  opacity: 0.5;
  transition: opacity 0.12s;
}
.history-item:hover .history-item-del {
  display: flex;
  align-items: center;
  justify-content: center;
}
.history-item-del:hover {
  opacity: 1;
  background: #fee2e2;
}
</style>
