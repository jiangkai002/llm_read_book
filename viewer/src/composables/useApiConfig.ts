import { ref } from 'vue'

export interface ApiConfig {
  /** 本机 FastAPI 等，如 http://localhost:8000 */
  backendUrl: string
  /** OpenAI 兼容 API 根地址，如 https://api.openai.com/v1 */
  endpoint: string
  apiKey: string
  model: string
  bookName: string
}

export function normalizeOpenAIBaseUrl(endpoint: string): string {
  let u = endpoint.trim()
  if (!u) return 'https://api.openai.com/v1'
  u = u.replace(/\/chat\/completions\/?$/i, '').replace(/\/$/, '')
  return u || 'https://api.openai.com/v1'
}

export function useApiConfig() {
  const apiConfig = ref<ApiConfig>({
    backendUrl:
      localStorage.getItem('ai_backend_url') ||
      localStorage.getItem('onenote_backend_url') ||
      'http://localhost:8000',
    endpoint: normalizeOpenAIBaseUrl(
      localStorage.getItem('ai_endpoint') || 'https://api.openai.com/v1',
    ),
    apiKey: localStorage.getItem('ai_api_key') || '',
    model: localStorage.getItem('ai_model') || 'gpt-4o',
    bookName: localStorage.getItem('ai_book_name') || '当前书籍',
  })

  const saveConfig = () => {
    const ep = normalizeOpenAIBaseUrl(apiConfig.value.endpoint)
    apiConfig.value.endpoint = ep
    localStorage.setItem('ai_backend_url', apiConfig.value.backendUrl.trim())
    localStorage.setItem('ai_endpoint', ep)
    localStorage.setItem('ai_api_key', apiConfig.value.apiKey)
    localStorage.setItem('ai_model', apiConfig.value.model)
    localStorage.setItem('ai_book_name', apiConfig.value.bookName.trim() || '当前书籍')
  }

  return { apiConfig, saveConfig }
}
