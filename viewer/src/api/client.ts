import axios from 'axios'
import { serviceOptions } from './index'

/** 与 OneNote 面板共用后端时可读 `onenote_backend_url` */
export function getBackendBaseUrl(): string {
  if (typeof localStorage === 'undefined') return 'http://localhost:8000'
  return (
    localStorage.getItem('ai_backend_url') ||
    localStorage.getItem('onenote_backend_url') ||
    'http://localhost:8000'
  ).replace(/\/$/, '')
}

/** 供 swagger 生成的 Service 使用；需在调用 LlmService 前执行 */
export function syncApiClientFromStorage(): void {
  const baseURL = getBackendBaseUrl()
  if (!serviceOptions.axios) {
    serviceOptions.axios = axios.create({
      baseURL,
      timeout: 300_000,
    })
  } else {
    serviceOptions.axios.defaults.baseURL = baseURL
  }
}
