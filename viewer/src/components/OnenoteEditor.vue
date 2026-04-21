<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { marked } from 'marked'

interface Notebook {
  id: string
  displayName: string
}
interface Section {
  id: string
  displayName: string
}
interface Page {
  id: string
  title: string
  createdDateTime: string
}

const isAuthenticated = ref(false)
const userName = ref('')
const notebooks = ref<Notebook[]>([])
const sections = ref<Section[]>([])
const pages = ref<Page[]>([])
const selectedNotebook = ref<Notebook | null>(null)
const selectedSection = ref<Section | null>(null)
const selectedPage = ref<Page | null>(null)
const pageContent = ref('')

const showConfig = ref(false)
const isLoading = ref(false)
const statusMsg = ref('')
const createTitle = ref('')
const createContent = ref('')
const showCreatePanel = ref(false)
const viewMode = ref<'edit' | 'preview'>('edit')

let statusTimer: ReturnType<typeof setTimeout> | null = null

const backendUrl = ref(localStorage.getItem('onenote_backend_url') || 'http://localhost:8000')
const clientId = ref(localStorage.getItem('onenote_client_id') || '')

const renderedPreview = computed(() => marked(createContent.value) as string)
const renderedPageContent = computed(() => {
  if (!pageContent.value) return ''
  return pageContent.value
})

const showStatus = (msg: string, duration = 3000) => {
  statusMsg.value = msg
  if (statusTimer) clearTimeout(statusTimer)
  statusTimer = setTimeout(() => (statusMsg.value = ''), duration)
}

const saveConfig = () => {
  localStorage.setItem('onenote_backend_url', backendUrl.value)
  localStorage.setItem('onenote_client_id', clientId.value)
  showConfig.value = false
  showStatus('配置已保存')
}

// ── API 请求封装 ──

const api = async (path: string, options: RequestInit = {}) => {
  const res = await fetch(`${backendUrl.value}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers as any) },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`)
  }
  return res.json()
}

// ── OAuth 登录（弹窗方式，不丢失当前页面状态）──

const login = () => {
  if (!clientId.value) {
    showConfig.value = true
    showStatus('请先配置 Client ID')
    return
  }

  const redirectUri = `${backendUrl.value}/api/onenote/auth/callback`
  const scopes = 'openid profile offline_access User.Read Notes.ReadWrite.All'

  const authUrl =
    `https://login.microsoftonline.com/common/oauth2/v2.0/authorize` +
    `?client_id=${encodeURIComponent(clientId.value)}` +
    `&response_type=code` +
    `&redirect_uri=${encodeURIComponent(redirectUri)}` +
    `&response_mode=query` +
    `&scope=${encodeURIComponent(scopes)}` +
    `&state=${encodeURIComponent(window.location.origin)}`

  const popup = window.open(authUrl, 'onenote-auth', 'width=600,height=700,left=200,top=100')

  if (!popup) {
    showStatus('弹窗被阻止，请允许弹窗后重试')
    return
  }

  showStatus('正在等待登录...')
}

const onAuthMessage = async (event: MessageEvent) => {
  if (event.data === 'onenote_auth_success') {
    showStatus('登录成功')
    await checkAuthStatus()
    if (isAuthenticated.value) await fetchNotebooks()
  } else if (typeof event.data === 'string' && event.data.startsWith('onenote_auth_error:')) {
    showStatus('登录失败: ' + event.data.replace('onenote_auth_error:', ''))
  }
}

const checkAuthStatus = async () => {
  try {
    const data = await api('/api/onenote/auth/status')
    isAuthenticated.value = data.authenticated
    userName.value = data.user || ''
  } catch {
    isAuthenticated.value = false
  }
}

const logout = async () => {
  try {
    await api('/api/onenote/auth/logout', { method: 'POST' })
  } catch {
    // 即使请求失败也清除前端状态
  }
  isAuthenticated.value = false
  userName.value = ''
  notebooks.value = []
  sections.value = []
  pages.value = []
  selectedNotebook.value = null
  selectedSection.value = null
  selectedPage.value = null
  pageContent.value = ''
  showStatus('已退出登录')
}

// ── 笔记本操作 ──

const fetchNotebooks = async () => {
  isLoading.value = true
  try {
    const data = await api('/api/onenote/notebooks')
    notebooks.value = data.value || data || []
  } catch (e: any) {
    showStatus('获取笔记本失败: ' + e.message)
  } finally {
    isLoading.value = false
  }
}

const selectNotebook = async (nb: Notebook) => {
  selectedNotebook.value = nb
  selectedSection.value = null
  selectedPage.value = null
  pages.value = []
  pageContent.value = ''
  isLoading.value = true
  try {
    const data = await api(`/api/onenote/sections?notebook_id=${nb.id}`)
    sections.value = data.value || data || []
  } catch (e: any) {
    showStatus('获取分区失败: ' + e.message)
  } finally {
    isLoading.value = false
  }
}

const selectSection = async (sec: Section) => {
  selectedSection.value = sec
  selectedPage.value = null
  pageContent.value = ''
  isLoading.value = true
  try {
    const data = await api(`/api/onenote/pages?section_id=${sec.id}`)
    pages.value = data.value || data || []
  } catch (e: any) {
    showStatus('获取页面失败: ' + e.message)
  } finally {
    isLoading.value = false
  }
}

const selectPage = async (page: Page) => {
  selectedPage.value = page
  isLoading.value = true
  try {
    const data = await api(`/api/onenote/pages/${page.id}/content`)
    pageContent.value = data.content || data || ''
  } catch (e: any) {
    showStatus('获取页面内容失败: ' + e.message)
  } finally {
    isLoading.value = false
  }
}

const goBackToNotebooks = () => {
  selectedNotebook.value = null
  selectedSection.value = null
  selectedPage.value = null
  sections.value = []
  pages.value = []
  pageContent.value = ''
}

const goBackToSections = () => {
  selectedSection.value = null
  selectedPage.value = null
  pages.value = []
  pageContent.value = ''
}

const goBackToPages = () => {
  selectedPage.value = null
  pageContent.value = ''
}

// ── 创建页面 ──

const openCreatePanel = () => {
  if (!selectedSection.value) {
    showStatus('请先选择一个分区')
    return
  }
  createTitle.value = ''
  createContent.value = ''
  showCreatePanel.value = true
  viewMode.value = 'edit'
}

const createPage = async () => {
  if (!selectedSection.value || !createTitle.value.trim()) {
    showStatus('请填写页面标题')
    return
  }
  isLoading.value = true
  try {
    const htmlContent = marked(createContent.value) as string
    await api('/api/onenote/pages', {
      method: 'POST',
      body: JSON.stringify({
        section_id: selectedSection.value.id,
        title: createTitle.value.trim(),
        html_content: htmlContent,
      }),
    })
    showStatus(`已创建页面: ${createTitle.value}`)
    showCreatePanel.value = false
    await selectSection(selectedSection.value)
  } catch (e: any) {
    showStatus('创建失败: ' + e.message)
  } finally {
    isLoading.value = false
  }
}

// ── 外部调用：保存到 OneNote ──

const saveToOnenote = async (title: string, mdContent: string): Promise<boolean> => {
  if (!isAuthenticated.value) {
    showStatus('请先登录 OneNote')
    return false
  }
  if (!selectedSection.value) {
    createTitle.value = title
    createContent.value = mdContent
    showCreatePanel.value = true
    viewMode.value = 'preview'
    showStatus('请选择一个分区后保存')
    return false
  }
  isLoading.value = true
  try {
    const htmlContent = marked(mdContent) as string
    await api('/api/onenote/pages', {
      method: 'POST',
      body: JSON.stringify({
        section_id: selectedSection.value.id,
        title,
        html_content: htmlContent,
      }),
    })
    showStatus(`已保存到 OneNote: ${title}`)
    await selectSection(selectedSection.value)
    return true
  } catch (e: any) {
    showStatus('保存失败: ' + e.message)
    return false
  } finally {
    isLoading.value = false
  }
}

defineExpose({ saveToOnenote })

// ── 生命周期 ──

onMounted(() => {
  window.addEventListener('message', onAuthMessage)
  checkAuthStatus().then(() => {
    if (isAuthenticated.value) fetchNotebooks()
  })
})

onUnmounted(() => {
  window.removeEventListener('message', onAuthMessage)
})
</script>

<template>
  <div class="onenote-editor">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <svg class="onenote-logo" width="18" height="18" viewBox="0 0 24 24">
          <rect width="24" height="24" rx="4" fill="#7719AA" />
          <text x="5" y="18" font-size="15" font-weight="bold" fill="white" font-family="Arial">
            N
          </text>
        </svg>
        <span class="toolbar-title">OneNote</span>
      </div>
      <div class="toolbar-right">
        <transition name="fade">
          <span v-if="statusMsg" class="status-msg">{{ statusMsg }}</span>
        </transition>
        <span v-if="userName" class="user-badge" :title="userName">{{ userName }}</span>
        <button class="tool-btn" title="配置" @click="showConfig = !showConfig">
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <circle cx="12" cy="12" r="3" />
            <path
              d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
            />
          </svg>
        </button>
      </div>
    </div>

    <!-- 配置面板 -->
    <transition name="slide">
      <div v-if="showConfig" class="config-panel">
        <div class="config-row">
          <label>后端地址</label>
          <input v-model="backendUrl" placeholder="http://localhost:8000" />
        </div>
        <div class="config-row">
          <label>Client ID</label>
          <input v-model="clientId" placeholder="Azure AD 应用的 Client ID" />
        </div>
        <div class="config-hint">
          需要在
          <a
            href="https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade"
            target="_blank"
            >Azure Portal</a
          >
          注册应用并配置回调地址为：<code>{{ backendUrl }}/api/onenote/auth/callback</code>
        </div>
        <button class="save-btn" @click="saveConfig">保存配置</button>
      </div>
    </transition>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 未登录 -->
      <div v-if="!isAuthenticated" class="empty-state">
        <div class="empty-icon">
          <svg width="52" height="52" viewBox="0 0 24 24" aria-hidden="true">
            <rect width="24" height="24" rx="4" fill="#ede9fe" stroke="#7719AA" stroke-width="0.5" />
            <text x="5" y="18" font-size="15" font-weight="bold" fill="#7719AA" font-family="Arial">N</text>
          </svg>
        </div>
        <p class="empty-title">连接 OneNote</p>
        <p class="empty-desc">登录 Microsoft 账号后，可以直接将 AI 生成的笔记保存到 OneNote</p>
        <button class="login-btn" @click="login">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
            <polyline points="10 17 15 12 10 7" />
            <line x1="15" y1="12" x2="3" y2="12" />
          </svg>
          登录 Microsoft 账号
        </button>
        <button class="config-link" @click="showConfig = true">配置后端地址和 Client ID</button>
      </div>

      <!-- 已登录：笔记本浏览 -->
      <div v-else class="browser">
        <!-- 面包屑导航 -->
        <div class="breadcrumb">
          <span class="crumb clickable" @click="goBackToNotebooks">笔记本</span>
          <template v-if="selectedNotebook">
            <span class="crumb-sep">›</span>
            <span class="crumb" :class="{ clickable: selectedSection }" @click="goBackToSections">{{
              selectedNotebook.displayName
            }}</span>
          </template>
          <template v-if="selectedSection">
            <span class="crumb-sep">›</span>
            <span class="crumb" :class="{ clickable: selectedPage }" @click="goBackToPages">{{
              selectedSection.displayName
            }}</span>
          </template>
          <template v-if="selectedPage">
            <span class="crumb-sep">›</span>
            <span class="crumb current">{{ selectedPage.title }}</span>
          </template>

          <div class="breadcrumb-actions">
            <button
              v-if="selectedSection && !selectedPage && !showCreatePanel"
              class="small-btn"
              @click="openCreatePanel"
            >
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              新建页面
            </button>
            <button class="small-btn danger" @click="logout">退出</button>
          </div>
        </div>

        <!-- 加载中 -->
        <div v-if="isLoading" class="loading-bar"><div class="loading-bar-inner" /></div>

        <!-- 创建页面面板 -->
        <div v-if="showCreatePanel" class="create-panel">
          <div class="create-header">
            <input v-model="createTitle" class="create-title-input" placeholder="页面标题" />
            <div class="create-actions">
              <button
                class="small-btn"
                :class="{ active: viewMode === 'edit' }"
                @click="viewMode = 'edit'"
              >
                编辑
              </button>
              <button
                class="small-btn"
                :class="{ active: viewMode === 'preview' }"
                @click="viewMode = 'preview'"
              >
                预览
              </button>
              <button
                class="small-btn primary"
                :disabled="!createTitle.trim() || isLoading"
                @click="createPage"
              >
                保存
              </button>
              <button class="small-btn" @click="showCreatePanel = false">取消</button>
            </div>
          </div>
          <textarea
            v-show="viewMode === 'edit'"
            v-model="createContent"
            class="create-editor"
            placeholder="用 Markdown 编写内容..."
            spellcheck="false"
          />
          <div v-show="viewMode === 'preview'" class="create-preview">
            <div v-if="createContent" class="markdown-body" v-html="renderedPreview" />
            <div v-else class="preview-empty">暂无内容</div>
          </div>
        </div>

        <!-- 列表视图 -->
        <div v-else-if="!selectedPage" class="item-list">
          <!-- 笔记本列表 -->
          <template v-if="!selectedNotebook">
            <div v-if="notebooks.length === 0 && !isLoading" class="list-empty">暂无笔记本</div>
            <div v-for="nb in notebooks" :key="nb.id" class="list-item" @click="selectNotebook(nb)">
              <svg
                class="item-icon notebook"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
              >
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
              </svg>
              <span class="item-name">{{ nb.displayName }}</span>
              <svg
                class="item-arrow"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </div>
          </template>

          <!-- 分区列表 -->
          <template v-else-if="!selectedSection">
            <div v-if="sections.length === 0 && !isLoading" class="list-empty">暂无分区</div>
            <div
              v-for="sec in sections"
              :key="sec.id"
              class="list-item"
              @click="selectSection(sec)"
            >
              <svg
                class="item-icon section"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
              >
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <line x1="9" y1="3" x2="9" y2="21" />
              </svg>
              <span class="item-name">{{ sec.displayName }}</span>
              <svg
                class="item-arrow"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </div>
          </template>

          <!-- 页面列表 -->
          <template v-else>
            <div v-if="pages.length === 0 && !isLoading" class="list-empty">暂无页面</div>
            <div v-for="p in pages" :key="p.id" class="list-item" @click="selectPage(p)">
              <svg
                class="item-icon page"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <div class="item-info">
                <span class="item-name">{{ p.title || '无标题' }}</span>
                <span class="item-date">{{
                  new Date(p.createdDateTime).toLocaleDateString('zh-CN')
                }}</span>
              </div>
              <svg
                class="item-arrow"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </div>
          </template>
        </div>

        <!-- 页面内容查看 -->
        <div v-else class="page-viewer">
          <div class="page-content" v-html="renderedPageContent" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.onenote-editor {
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
  padding: 8px 12px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 7px;
}

.onenote-logo {
  flex-shrink: 0;
}

.toolbar-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
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

.tool-btn:hover {
  background: #f3f4f6;
  color: #111;
}

.user-badge {
  font-size: 11px;
  color: #7719aa;
  background: #f3e8ff;
  padding: 2px 7px;
  border-radius: 4px;
  max-width: 90px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

/* ── 配置面板 ── */
.config-panel {
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  padding: 12px 14px;
  flex-shrink: 0;
}

.config-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.config-row label {
  width: 64px;
  font-size: 12px;
  color: #6b7280;
  flex-shrink: 0;
}

.config-row input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  color: #111;
}

.config-row input:focus {
  border-color: #7719aa;
  box-shadow: 0 0 0 2px rgba(119, 25, 170, 0.12);
}

.config-hint {
  font-size: 11px;
  color: #9ca3af;
  margin-bottom: 10px;
  line-height: 1.5;
}

.config-hint a {
  color: #7719aa;
}

.config-hint code {
  background: #f3f4f6;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
  color: #7719aa;
}

.save-btn {
  width: 100%;
  padding: 7px;
  background: #7719aa;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.15s;
}

.save-btn:hover {
  background: #5b1382;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
}
.slide-enter-to,
.slide-leave-from {
  max-height: 250px;
  opacity: 1;
}

/* ── 主内容 ── */
.main-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* ── 空状态 / 登录 ── */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px;
}

.empty-icon {
  margin-bottom: 4px;
}

.empty-icon img {
  display: block;
  max-width: 80px;
  max-height: 80px;
  width: auto;
  height: auto;
  object-fit: contain;
}

.empty-title {
  font-size: 16px;
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

.login-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 10px 24px;
  background: #7719aa;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition:
    background 0.15s,
    transform 0.1s;
}

.login-btn:hover {
  background: #5b1382;
  transform: scale(1.02);
}

.config-link {
  margin-top: 4px;
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 12px;
  cursor: pointer;
  text-decoration: underline;
}

.config-link:hover {
  color: #7719aa;
}

/* ── 浏览器 ── */
.browser {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  background: #fff;
  border-bottom: 1px solid #f3f4f6;
  flex-shrink: 0;
  flex-wrap: wrap;
  min-height: 36px;
}

.crumb {
  font-size: 12px;
  color: #6b7280;
}

.crumb.clickable {
  cursor: pointer;
  color: #7719aa;
}

.crumb.clickable:hover {
  text-decoration: underline;
}

.crumb.current {
  color: #374151;
  font-weight: 500;
}

.crumb-sep {
  color: #d1d5db;
  font-size: 12px;
}

.breadcrumb-actions {
  margin-left: auto;
  display: flex;
  gap: 6px;
}

.small-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 4px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 5px;
  background: #fff;
  color: #6b7280;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.12s;
}

.small-btn:hover {
  background: #f3f4f6;
  color: #111;
}

.small-btn.active {
  background: #f3e8ff;
  border-color: #d8b4fe;
  color: #7719aa;
}

.small-btn.primary {
  background: #7719aa;
  border-color: #7719aa;
  color: #fff;
}

.small-btn.primary:hover {
  background: #5b1382;
}

.small-btn.primary:disabled {
  background: #d8b4fe;
  border-color: #d8b4fe;
  cursor: not-allowed;
}

.small-btn.danger {
  color: #ef4444;
  border-color: #fecaca;
}

.small-btn.danger:hover {
  background: #fef2f2;
}

/* ── 加载条 ── */
.loading-bar {
  height: 2px;
  background: #f3e8ff;
  flex-shrink: 0;
  overflow: hidden;
}

.loading-bar-inner {
  height: 100%;
  width: 30%;
  background: #7719aa;
  animation: loading-slide 1.2s ease-in-out infinite;
}

@keyframes loading-slide {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(400%);
  }
}

/* ── 列表 ── */
.item-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
}

.item-list::-webkit-scrollbar {
  width: 4px;
}
.item-list::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 4px;
}

.list-empty {
  padding: 32px 12px;
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
}

.list-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.12s;
}

.list-item:hover {
  background: #f3f4f6;
}

.item-icon {
  flex-shrink: 0;
}

.item-icon.notebook {
  color: #7719aa;
}

.item-icon.section {
  color: #0ea5e9;
}

.item-icon.page {
  color: #6b7280;
}

.item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.item-name {
  flex: 1;
  font-size: 13.5px;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-date {
  font-size: 11px;
  color: #9ca3af;
}

.item-arrow {
  flex-shrink: 0;
  color: #d1d5db;
}

/* ── 创建面板 ── */
.create-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.create-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #fff;
  border-bottom: 1px solid #f3f4f6;
  flex-shrink: 0;
}

.create-title-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  color: #111;
}

.create-title-input:focus {
  border-color: #7719aa;
  box-shadow: 0 0 0 2px rgba(119, 25, 170, 0.12);
}

.create-actions {
  display: flex;
  gap: 4px;
}

.create-editor {
  flex: 1;
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  padding: 12px;
  font-family: 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.7;
  color: #1a1a1a;
  background: #fafafa;
  box-sizing: border-box;
}

.create-editor::placeholder {
  color: #c0c7d0;
}

.create-preview {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  background: #fff;
}

.preview-empty {
  text-align: center;
  color: #9ca3af;
  padding-top: 40px;
}

/* ── 页面查看 ── */
.page-viewer {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  background: #fff;
}

.page-viewer::-webkit-scrollbar {
  width: 4px;
}
.page-viewer::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 4px;
}

.page-content {
  line-height: 1.7;
  color: #1a1a1a;
}

.page-content :deep(img) {
  max-width: 100%;
  border-radius: 4px;
}

/* ── Markdown 渲染 ── */
.markdown-body :deep(p) {
  margin: 0 0 10px;
  line-height: 1.7;
}
.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 14px 0 6px;
  font-weight: 600;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 6px 0;
  padding-left: 20px;
}
.markdown-body :deep(code) {
  background: #f3f4f6;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.88em;
  color: #7719aa;
}
.markdown-body :deep(pre) {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
  font-size: 12.5px;
}
.markdown-body :deep(pre code) {
  background: none;
  color: inherit;
  padding: 0;
}
.markdown-body :deep(blockquote) {
  border-left: 3px solid #7719aa;
  padding-left: 10px;
  color: #6b7280;
  margin: 8px 0;
}
</style>
