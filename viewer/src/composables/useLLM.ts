import type { Ref } from 'vue'
import type { Message } from './useChatHistory'
import type { ApiConfig } from './useApiConfig'
import { normalizeOpenAIBaseUrl } from './useApiConfig'

const PLACEHOLDER_IMAGE_BASE64 = ''

function stripDataUrlBase64(dataUrl: string): string {
  const m = dataUrl.match(/^data:image\/\w+;base64,(.+)$/i)
  return m ? m[1] : dataUrl.replace(/^data:[^;]+;base64,/i, '')
}

export function useLLM(
  messages: Ref<Message[]>,
  getSelectedText: () => string | null | undefined,
  apiConfig: Ref<ApiConfig>,
  onChunk: () => void | Promise<void>,
) {
  /** 构造历史消息列表（末尾 user+assistant 这轮不算历史） */
  const buildHistoryChatList = (): string[] => {
    const history = messages.value.slice(0, -2)
    return history
      .filter((m) => m.content.trim())
      .map((m) => {
        const roleLabel = m.role === 'user' ? 'user' : 'assistant'
        return `{"role": "${roleLabel}", "content": "${m.content.trim()}"}`
      })
  }

  const callBackendLLM = async (
    text: string,
    image: string | null,
    target: Message,
    useImage: boolean,
  ): Promise<void> => {
    const imageBase64 = image ? stripDataUrlBase64(image) : PLACEHOLDER_IMAGE_BASE64
    const question = text.trim() || (image ? '请结合截图内容回答。' : '请回答。')
    const body = {
      use_image: useImage,
      book_name: apiConfig.value.bookName.trim() || '当前书籍',
      question,
      image_base64: imageBase64,
      image_content: getSelectedText()?.trim() || '',
      api_key: apiConfig.value.apiKey,
      base_url: normalizeOpenAIBaseUrl(apiConfig.value.endpoint),
      model: apiConfig.value.model,
      history_chat_list: buildHistoryChatList(),
    }

    // 前后端同容器部署，使用相对路径；fetch 可保留 ReadableStream，axios 不行。
    const response = await fetch('/api/llm/llm_ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const errText = await response.text().catch(() => '')
      throw new Error(`HTTP ${response.status}: ${errText || response.statusText}`)
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buf = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() ?? ''
      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data: ')) continue
        const data = trimmed.slice(6)
        if (data === '[DONE]') return
        try {
          const parsed = JSON.parse(data) as { content?: string }
          if (parsed.content) {
            target.content += parsed.content
            await onChunk()
          }
        } catch {
          // 忽略非 JSON 行
        }
      }
    }
  }

  const simulateStream = async (target: Message): Promise<void> => {
    const text =
      '你好！我是 AI 助手。你可以：\n- 粘贴 PDF 中复制的文字进行提问\n- 截取 PDF 截图后自动附加到此处\n\n请先点击 ⚙️ 配置大模型 API。'
    for (const char of text) {
      target.content += char
      await new Promise((r) => setTimeout(r, 15))
      await onChunk()
    }
  }

  return { callBackendLLM, simulateStream, buildHistoryChatList }
}
