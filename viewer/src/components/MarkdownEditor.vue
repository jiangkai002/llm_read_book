<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { marked } from 'marked'
import directoryIcon from '@/assets/markdown/directoryIcon.svg'
import refreshIcon from '@/assets/markdown/refreshIcon.svg'
import newFileIcon from '@/assets/markdown/newFileIcon.svg'
import saveIcon from '@/assets/markdown/saveIcon.svg'
import editIcon from '@/assets/markdown/editIcon.svg'
import previewIcon from '@/assets/markdown/previewIcon.svg'
import fileListIcon from '@/assets/markdown/fileListIcon.svg'

interface MdFile {
  name: string
  path: string
  handle: FileSystemFileHandle
}

const content = ref('')
const currentFile = ref<MdFile | null>(null)
const files = ref<MdFile[]>([])
const isDirty = ref(false)
const isPreview = ref(false)
const showSidebar = ref(true)
const statusMsg = ref('')
const searchQuery = ref('')
const isScanning = ref(false)
const newFileName = ref('')
const showNewFileInput = ref(false)
const newFileInputRef = ref<HTMLInputElement | null>(null)

let dirHandle: FileSystemDirectoryHandle | null = null
let statusTimer: ReturnType<typeof setTimeout> | null = null
let skipDirtyFlag = false

const isApiSupported = computed(() => 'showDirectoryPicker' in window)
const renderedHtml = computed(() => marked(content.value) as string)
const dirName = computed(() => dirHandle?.name || '')

const filteredFiles = computed(() => {
  if (!searchQuery.value) return files.value
  const q = searchQuery.value.toLowerCase()
  return files.value.filter(
    (f) => f.name.toLowerCase().includes(q) || f.path.toLowerCase().includes(q),
  )
})

watch(content, () => {
  if (skipDirtyFlag) {
    skipDirtyFlag = false
    return
  }
  if (currentFile.value) isDirty.value = true
})

const showStatus = (msg: string, duration = 2500) => {
  statusMsg.value = msg
  if (statusTimer) clearTimeout(statusTimer)
  statusTimer = setTimeout(() => (statusMsg.value = ''), duration)
}

// ── IndexedDB ──

function idbOpen(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('md-editor-store', 1)
    req.onupgradeneeded = () => req.result.createObjectStore('handles')
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function idbSave(handle: FileSystemDirectoryHandle) {
  const db = await idbOpen()
  const tx = db.transaction('handles', 'readwrite')
  tx.objectStore('handles').put(handle, 'dir')
}

async function idbLoad(): Promise<FileSystemDirectoryHandle | null> {
  try {
    const db = await idbOpen()
    return new Promise((resolve) => {
      const tx = db.transaction('handles', 'readonly')
      const req = tx.objectStore('handles').get('dir')
      req.onsuccess = () => resolve(req.result || null)
      req.onerror = () => resolve(null)
    })
  } catch {
    return null
  }
}

// ── 目录扫描 ──

async function scanDir(handle: FileSystemDirectoryHandle, basePath = ''): Promise<MdFile[]> {
  const result: MdFile[] = []
  for await (const entry of (handle as any).values()) {
    const entryPath = basePath ? `${basePath}/${entry.name}` : entry.name
    if (entry.kind === 'file' && /\.(md|markdown)$/i.test(entry.name)) {
      result.push({ name: entry.name, path: entryPath, handle: entry })
    } else if (entry.kind === 'directory' && !entry.name.startsWith('.')) {
      result.push(...(await scanDir(entry, entryPath)))
    }
  }
  result.sort((a, b) => a.path.localeCompare(b.path))
  return result
}

async function refreshFiles() {
  if (!dirHandle) return
  isScanning.value = true
  try {
    files.value = await scanDir(dirHandle)
  } finally {
    isScanning.value = false
  }
}

// ── 选择目录 ──

const selectDirectory = async () => {
  if (!isApiSupported.value) return
  try {
    dirHandle = await (window as any).showDirectoryPicker({ mode: 'readwrite' })
    await idbSave(dirHandle!)
    await refreshFiles()
    showStatus(`已打开目录: ${dirHandle!.name}`)
  } catch (e: any) {
    if (e.name !== 'AbortError') showStatus('选择目录失败: ' + e.message)
  }
}

const tryRestoreDir = async () => {
  const cached = await idbLoad()
  if (!cached) return
  try {
    const perm = await (cached as any).requestPermission({ mode: 'readwrite' })
    if (perm === 'granted') {
      dirHandle = cached
      await refreshFiles()
      showStatus(`已恢复目录: ${cached.name}`)
    }
  } catch {
    // 用户拒绝或 handle 失效
  }
}

// ── 确认丢弃 ──

const confirmDiscard = (): boolean => {
  if (!isDirty.value) return true
  return window.confirm('当前文件有未保存的更改，是否丢弃？')
}

// ── 打开文件 ──

const openFile = async (file: MdFile) => {
  if (!confirmDiscard()) return
  try {
    const f = await file.handle.getFile()
    skipDirtyFlag = true
    content.value = await f.text()
    currentFile.value = file
    isDirty.value = false
    isPreview.value = false
  } catch (e: any) {
    showStatus('读取失败: ' + e.message)
  }
}

// ── 新建文件 ──

const startNewFile = async () => {
  showNewFileInput.value = true
  newFileName.value = ''
  await nextTick()
  newFileInputRef.value?.focus()
}

const createNewFile = async () => {
  let name = newFileName.value.trim()
  if (!name) {
    showNewFileInput.value = false
    return
  }
  if (!name.endsWith('.md') && !name.endsWith('.markdown')) name += '.md'

  if (!dirHandle) {
    showNewFileInput.value = false
    showStatus('请先选择笔记目录')
    return
  }
  if (!confirmDiscard()) return

  try {
    const fh = await dirHandle.getFileHandle(name, { create: true })
    const writable = await (fh as any).createWritable()
    await writable.write('')
    await writable.close()

    await refreshFiles()
    const newFile = files.value.find((f) => f.name === name)
    if (newFile) {
      skipDirtyFlag = true
      content.value = ''
      currentFile.value = newFile
      isDirty.value = false
      isPreview.value = false
    }
    showStatus(`已创建 ${name}`)
  } catch (e: any) {
    showStatus('创建失败: ' + e.message)
  } finally {
    showNewFileInput.value = false
  }
}

// ── 保存 ──

const saveFile = async () => {
  if (!currentFile.value) {
    showStatus('请先打开或新建一个文件')
    return
  }
  try {
    const writable = await (currentFile.value.handle as any).createWritable()
    await writable.write(content.value)
    await writable.close()
    isDirty.value = false
    showStatus(`已保存 ${currentFile.value.name}`)
  } catch (e: any) {
    showStatus('保存失败: ' + e.message)
  }
}

// ── 删除文件 ──

const deleteFile = async (file: MdFile) => {
  if (!dirHandle) return
  if (!window.confirm(`确定删除 ${file.path} 吗？`)) return

  try {
    if (file.path.includes('/')) {
      const parts = file.path.split('/')
      let dh: FileSystemDirectoryHandle = dirHandle
      for (let i = 0; i < parts.length - 1; i++) {
        dh = await dh.getDirectoryHandle(parts[i])
      }
      await dh.removeEntry(parts[parts.length - 1])
    } else {
      await dirHandle.removeEntry(file.name)
    }

    if (currentFile.value?.path === file.path) {
      currentFile.value = null
      skipDirtyFlag = true
      content.value = ''
      isDirty.value = false
    }
    await refreshFiles()
    showStatus(`已删除 ${file.name}`)
  } catch (e: any) {
    showStatus('删除失败: ' + e.message)
  }
}

// ── 外部调用：保存新 Markdown 文件 ──

const saveNewFile = async (filename: string, mdContent: string): Promise<boolean> => {
  if (!dirHandle) {
    showStatus('请先选择笔记目录', 3000)
    return false
  }
  try {
    let name = filename.trim()
    if (!name.endsWith('.md') && !name.endsWith('.markdown')) name += '.md'
    const fh = await dirHandle.getFileHandle(name, { create: true })
    const writable = await (fh as any).createWritable()
    await writable.write(mdContent)
    await writable.close()
    await refreshFiles()
    showStatus(`已保存 ${name}`)

    const created = files.value.find((f) => f.name === name)
    if (created) await openFile(created)
    return true
  } catch (e: any) {
    showStatus('保存失败: ' + e.message)
    return false
  }
}

defineExpose({ saveNewFile })

// ── 快捷键 ──

const handleKeydown = (e: KeyboardEvent) => {
  if (e.ctrlKey || e.metaKey) {
    if (e.key === 's') {
      e.preventDefault()
      saveFile()
    }
  }
}

const handleTab = (e: KeyboardEvent) => {
  if (e.key === 'Tab') {
    e.preventDefault()
    const ta = e.target as HTMLTextAreaElement
    const start = ta.selectionStart
    const end = ta.selectionEnd
    content.value = content.value.substring(0, start) + '  ' + content.value.substring(end)
    requestAnimationFrame(() => {
      ta.selectionStart = ta.selectionEnd = start + 2
    })
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  tryRestoreDir()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div class="md-editor">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <button class="tool-btn" title="选择笔记目录" @click="selectDirectory">
          <img :src="directoryIcon" alt="" width="15" height="15" />
        </button>
        <button class="tool-btn" title="刷新文件列表" :disabled="!dirHandle" @click="refreshFiles">
          <img :src="refreshIcon" alt="" width="15" height="15" />
        </button>
        <div class="separator" />
        <button class="tool-btn" title="新建文件" :disabled="!dirHandle" @click="startNewFile">
          <img :src="newFileIcon" alt="" width="15" height="15" />
        </button>
        <button class="tool-btn" title="保存 (Ctrl+S)" :disabled="!currentFile" @click="saveFile">
          <img :src="saveIcon" alt="" width="15" height="15" />
        </button>
        <div class="separator" />
        <button
          class="tool-btn"
          :class="{ active: !isPreview }"
          title="编辑"
          @click="isPreview = false"
        >
          <img :src="editIcon" alt="" width="15" height="15" />
        </button>
        <button
          class="tool-btn"
          :class="{ active: isPreview }"
          title="预览"
          @click="isPreview = true"
        >
          <img :src="previewIcon" alt="" width="15" height="15" />
        </button>
        <div class="separator" />
        <button
          class="tool-btn"
          :class="{ active: showSidebar }"
          title="文件列表"
          @click="showSidebar = !showSidebar"
        >
          <img :src="fileListIcon" alt="" width="15" height="15" />
        </button>
      </div>

      <div class="toolbar-right">
        <span v-if="dirName" class="dir-badge" :title="dirName">{{ dirName }}</span>
        <span v-if="currentFile" class="file-name">
          {{ currentFile.name }}<span v-if="isDirty" class="dirty-dot">●</span>
        </span>
        <transition name="fade">
          <span v-if="statusMsg" class="status-msg">{{ statusMsg }}</span>
        </transition>
      </div>
    </div>

    <!-- 不支持提示 -->
    <div v-if="!isApiSupported" class="unsupported-banner">
      当前浏览器不支持 File System Access API，请使用 Chrome / Edge 最新版本。
    </div>

    <!-- 主体区域 -->
    <div class="main-area">
      <!-- 左侧文件列表 -->
      <transition name="slide-sidebar">
        <div v-show="showSidebar && dirHandle" class="file-sidebar">
          <div class="sidebar-search">
            <input v-model="searchQuery" class="search-input" placeholder="搜索文件..." />
          </div>

          <!-- 新建文件输入 -->
          <div v-if="showNewFileInput" class="new-file-row">
            <input
              ref="newFileInputRef"
              v-model="newFileName"
              class="new-file-input"
              placeholder="文件名.md"
              @keydown.enter="createNewFile"
              @keydown.escape="showNewFileInput = false"
              @blur="createNewFile"
            />
          </div>

          <div class="file-list">
            <div v-if="isScanning" class="file-list-hint">扫描中...</div>
            <div v-else-if="filteredFiles.length === 0" class="file-list-hint">
              {{ searchQuery ? '无匹配文件' : '目录中暂无 .md 文件' }}
            </div>
            <div
              v-for="file in filteredFiles"
              :key="file.path"
              class="file-item"
              :class="{ active: currentFile?.path === file.path }"
              :title="file.path"
              @click="openFile(file)"
            >
              <svg
                class="file-icon"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <div class="file-info">
                <span class="file-item-name">{{ file.name }}</span>
                <span v-if="file.path.includes('/')" class="file-item-path">{{ file.path }}</span>
              </div>
              <button class="file-delete-btn" title="删除" @click.stop="deleteFile(file)">
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </transition>

      <!-- 未选择目录提示 -->
      <div v-if="!dirHandle" class="empty-state">
        <div class="empty-icon">
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#d1d5db"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <p class="empty-title">选择笔记目录开始使用</p>
        <p class="empty-desc">点击工具栏的文件夹图标，选择一个本地目录来管理 Markdown 笔记</p>
        <button class="select-dir-btn" @click="selectDirectory">选择目录</button>
      </div>

      <!-- 编辑器 -->
      <div v-else class="editor-area">
        <div v-if="!currentFile" class="empty-state small">
          <p class="empty-desc">从左侧选择一个文件，或新建文件开始编辑</p>
        </div>
        <textarea
          v-show="currentFile && !isPreview"
          v-model="content"
          class="editor-textarea"
          spellcheck="false"
          placeholder="在此编写 Markdown 内容..."
          @keydown="handleTab"
        />
        <div v-show="currentFile && isPreview" class="preview-pane">
          <div v-if="content" class="markdown-body" v-html="renderedHtml" />
          <div v-else class="preview-empty">暂无内容</div>
        </div>
      </div>
    </div>

    <!-- 底部状态栏 -->
    <div class="status-bar">
      <span v-if="dirHandle">{{ files.length }} 个文件</span>
      <span v-if="currentFile"
        >{{ content.length }} 字符 · {{ content.split('\n').length }} 行</span
      >
      <span v-if="isDirty" class="unsaved-hint">未保存</span>
    </div>
  </div>
</template>

<style scoped>
.md-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f9fafb;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 14px;
  color: #1a1a1a;
  overflow: hidden;
}

/* ── 工具栏 ── */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
  gap: 6px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 1px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.tool-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  border-radius: 5px;
  cursor: pointer;
  color: #6b7280;
  transition:
    background 0.15s,
    color 0.15s;
}

.tool-btn:hover:not(:disabled) {
  background: #f3f4f6;
  color: #111;
}

.tool-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.tool-btn.active {
  background: #ede9fe;
  color: #6366f1;
}

.separator {
  width: 1px;
  height: 18px;
  background: #e5e7eb;
  margin: 0 3px;
}

.dir-badge {
  font-size: 11px;
  color: #6366f1;
  background: #ede9fe;
  padding: 2px 7px;
  border-radius: 4px;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-name {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100px;
}

.dirty-dot {
  color: #f59e0b;
  margin-left: 3px;
  font-size: 10px;
}

.status-msg {
  font-size: 11px;
  color: #10b981;
  white-space: nowrap;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.unsupported-banner {
  padding: 10px 14px;
  background: #fef3c7;
  color: #92400e;
  font-size: 13px;
  border-bottom: 1px solid #fde68a;
  flex-shrink: 0;
}

/* ── 主体 ── */
.main-area {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* ── 文件侧栏 ── */
.file-sidebar {
  width: 180px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid #e5e7eb;
  overflow: hidden;
}

.slide-sidebar-enter-active,
.slide-sidebar-leave-active {
  transition:
    width 0.2s ease,
    opacity 0.15s ease;
}
.slide-sidebar-enter-from,
.slide-sidebar-leave-to {
  width: 0;
  opacity: 0;
}

.sidebar-search {
  padding: 8px;
  flex-shrink: 0;
}

.search-input {
  width: 100%;
  padding: 5px 8px;
  border: 1px solid #e5e7eb;
  border-radius: 5px;
  font-size: 12px;
  outline: none;
  color: #111;
  box-sizing: border-box;
}
.search-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.12);
}

.new-file-row {
  padding: 0 8px 6px;
}

.new-file-input {
  width: 100%;
  padding: 5px 8px;
  border: 1px solid #6366f1;
  border-radius: 5px;
  font-size: 12px;
  outline: none;
  color: #111;
  box-sizing: border-box;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.12);
}

.file-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 4px 8px;
}

.file-list::-webkit-scrollbar {
  width: 3px;
}
.file-list::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.file-list-hint {
  padding: 12px 8px;
  color: #9ca3af;
  font-size: 12px;
  text-align: center;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 5px;
  cursor: pointer;
  transition: background 0.12s;
  position: relative;
}

.file-item:hover {
  background: #f3f4f6;
}

.file-item.active {
  background: #ede9fe;
}

.file-icon {
  flex-shrink: 0;
  color: #9ca3af;
}

.file-item.active .file-icon {
  color: #6366f1;
}

.file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.file-item-name {
  font-size: 12.5px;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-item.active .file-item-name {
  color: #4338ca;
  font-weight: 500;
}

.file-item-path {
  font-size: 10px;
  color: #9ca3af;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-delete-btn {
  display: none;
  width: 20px;
  height: 20px;
  border: none;
  background: none;
  border-radius: 4px;
  cursor: pointer;
  color: #9ca3af;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-item:hover .file-delete-btn {
  display: flex;
}

.file-delete-btn:hover {
  background: #fee2e2;
  color: #ef4444;
}

/* ── 空状态 ── */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px;
}

.empty-state.small {
  gap: 6px;
}

.empty-icon {
  margin-bottom: 4px;
}

.empty-title {
  font-size: 15px;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.empty-desc {
  font-size: 13px;
  color: #9ca3af;
  text-align: center;
  margin: 0;
  max-width: 240px;
  line-height: 1.5;
}

.select-dir-btn {
  margin-top: 6px;
  padding: 8px 20px;
  background: #6366f1;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.select-dir-btn:hover {
  background: #4f46e5;
}

/* ── 编辑器区域 ── */
.editor-area {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

.editor-textarea {
  width: 100%;
  height: 100%;
  border: none;
  outline: none;
  resize: none;
  padding: 14px;
  font-family: 'Fira Code', 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
  font-size: 13.5px;
  line-height: 1.7;
  color: #1a1a1a;
  background: #fafafa;
  tab-size: 2;
  box-sizing: border-box;
}

.editor-textarea::placeholder {
  color: #c0c7d0;
}

.preview-pane {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  padding: 14px;
  box-sizing: border-box;
  background: #fff;
}

.preview-pane::-webkit-scrollbar {
  width: 4px;
}
.preview-pane::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 4px;
}

.preview-empty {
  color: #9ca3af;
  font-size: 14px;
  text-align: center;
  padding-top: 60px;
}

/* ── 状态栏 ── */
.status-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 12px;
  background: #fff;
  border-top: 1px solid #e5e7eb;
  font-size: 11px;
  color: #9ca3af;
  flex-shrink: 0;
}

.unsaved-hint {
  color: #f59e0b;
  font-weight: 500;
}

/* ── Markdown 渲染 ── */
.markdown-body :deep(p) {
  margin: 0 0 12px;
  line-height: 1.7;
}
.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown-body :deep(h1) {
  font-size: 1.5em;
  font-weight: 700;
  margin: 18px 0 8px;
  padding-bottom: 5px;
  border-bottom: 1px solid #e5e7eb;
}
.markdown-body :deep(h2) {
  font-size: 1.3em;
  font-weight: 600;
  margin: 16px 0 6px;
  padding-bottom: 3px;
  border-bottom: 1px solid #f3f4f6;
}
.markdown-body :deep(h3) {
  font-size: 1.1em;
  font-weight: 600;
  margin: 12px 0 5px;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 6px 0;
  padding-left: 20px;
}
.markdown-body :deep(li) {
  margin: 3px 0;
  line-height: 1.6;
}
.markdown-body :deep(strong) {
  font-weight: 600;
  color: #111;
}
.markdown-body :deep(code) {
  background: #f3f4f6;
  padding: 1px 5px;
  border-radius: 4px;
  font-family: 'Fira Code', monospace;
  font-size: 0.88em;
  color: #7c3aed;
}
.markdown-body :deep(pre) {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
  font-size: 12.5px;
  line-height: 1.5;
}
.markdown-body :deep(pre code) {
  background: none;
  color: inherit;
  padding: 0;
}
.markdown-body :deep(blockquote) {
  border-left: 3px solid #6366f1;
  padding-left: 10px;
  color: #6b7280;
  margin: 8px 0;
}
.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 14px 0;
}
.markdown-body :deep(a) {
  color: #6366f1;
  text-decoration: none;
}
.markdown-body :deep(a:hover) {
  text-decoration: underline;
}
.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 6px 10px;
  text-align: left;
  font-size: 13px;
}
.markdown-body :deep(th) {
  background: #f9fafb;
  font-weight: 600;
}
.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 6px;
}
</style>
