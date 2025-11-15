import request from '@/utils/request'

export function createSession(data) {
  return request.post('/chat/sessions', data)
}

export function getSessionList(params) {
  return request.get('/chat/sessions', { params })
}

export function getSessionDetail(id) {
  return request.get(`/chat/sessions/${id}`)
}

export function updateSession(id, data) {
  return request.put(`/chat/sessions/${id}`, data)
}

export function deleteSession(id) {
  return request.delete(`/chat/sessions/${id}`)
}

export function getSessionMessages(id, params) {
  return request.get(`/chat/sessions/${id}/messages`, { params })
}

export function sendMessage(data) {
  return request.post('/chat/messages', data)
}

export function streamMessage(data, { onChunk, onDone, onError, signal } = {}) {
  // 构建完整的 API URL
  const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  const apiPrefix = import.meta.env.VITE_API_PREFIX ?? '/api'
  const normalizedBaseUrl = rawBaseUrl.replace(/\/$/, '')
  const normalizedPrefix = apiPrefix.startsWith('/') ? apiPrefix : `/${apiPrefix}`
  const fullUrl = `${normalizedBaseUrl}${normalizedPrefix}/chat/messages/stream`
  
  console.log('流式请求 URL:', fullUrl)
  console.log('流式请求数据:', data)
  
  const controller = new AbortController()
  const abortSignal = signal || controller.signal

  fetch(fullUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
    signal: abortSignal,
  })
    .then((response) => {
      console.log('流式响应状态:', response.status, response.statusText)
      if (!response.ok) {
        throw new Error(`流式接口请求失败: ${response.status} ${response.statusText}`)
      }
      if (!response.body) {
        throw new Error('响应体为空')
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      let finished = false

      const processChunk = () =>
        reader.read().then(({ done, value }) => {
          if (done) {
            console.log('流式响应完成，剩余缓冲区:', buffer)
            // 处理剩余的缓冲区数据
            if (buffer.trim()) {
              const result = parseChunk(buffer, onChunk, onDone)
              finished = finished || result.finished
            }
            // 如果没有收到 done 事件，手动调用 onDone
            if (!finished) {
              console.log('未收到 done 事件，手动调用 onDone')
              onDone?.([])
            }
            return
          }
          // 解码新的数据块
          const decoded = decoder.decode(value, { stream: true })
          console.log('收到原始数据块:', decoded)
          buffer += decoded
          console.log('当前缓冲区:', buffer)
          // 解析缓冲区中的所有完整数据包
          const result = parseChunk(buffer, onChunk, onDone)
          buffer = result.buffer
          finished = finished || result.finished
          // 继续读取下一个数据块
          return processChunk()
        })

      return processChunk()
    })
    .catch((error) => {
      if (error.name === 'AbortError') {
        console.log('流式请求已取消')
        return
      }
      console.error('流式请求错误:', error)
      onError?.(error)
    })

  return {
    cancel: () => controller.abort(),
  }
}

function parseChunk(buffer, onChunk, onDone) {
  const delimiter = '\n\n'
  let index = buffer.indexOf(delimiter)
  let finished = false
  let remainingBuffer = buffer
  
  console.log('开始解析缓冲区，长度:', buffer.length, '内容:', JSON.stringify(buffer))
  
  // 处理所有完整的数据包（以 \n\n 分隔）
  while (index !== -1) {
    const packet = remainingBuffer.slice(0, index)
    remainingBuffer = remainingBuffer.slice(index + delimiter.length)
    
    console.log('解析数据包:', JSON.stringify(packet))
    
    // 提取 data: 开头的行
    const lines = packet.split('\n')
    console.log('数据包行数:', lines.length, '行内容:', lines)
    
    const dataLines = lines
      .filter((line) => {
        const trimmed = line.trim()
        const isDataLine = trimmed.startsWith('data:')
        console.log('检查行:', JSON.stringify(line), '是否为 data 行:', isDataLine)
        return isDataLine
      })
      .map((line) => {
        const trimmed = line.trim()
        const dataContent = trimmed.replace(/^data:\s*/, '')
        console.log('提取 data 内容:', JSON.stringify(dataContent))
        return dataContent
      })
    
    console.log('提取的 data 行:', dataLines)
    
    // 处理每个 data 行
    for (const dataLine of dataLines) {
      if (!dataLine) {
        console.log('跳过空的 data 行')
        continue
      }
      
      try {
        console.log('尝试解析 JSON:', dataLine)
        const payload = JSON.parse(dataLine)
        console.log('解析成功，payload:', payload)
        
        if (payload.type === 'chunk' && payload.content !== undefined) {
          console.log('调用 onChunk，内容:', payload.content)
          // 调用 onChunk 回调，传递内容块
          onChunk?.(payload.content)
        } else if (payload.type === 'done') {
          console.log('收到 done 信号，sources:', payload.sources)
          // 收到完成信号
          finished = true
          onDone?.(payload.sources || [])
        } else {
          console.log('未知的 payload 类型:', payload.type)
        }
      } catch (error) {
        console.error('解析流式响应失败:', error, '原始数据:', JSON.stringify(dataLine))
      }
    }

    index = remainingBuffer.indexOf(delimiter)
  }

  console.log('解析完成，剩余缓冲区:', JSON.stringify(remainingBuffer), 'finished:', finished)
  return { buffer: remainingBuffer, finished }
}

