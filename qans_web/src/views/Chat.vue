<template>
  <div class="chat-page">
    <el-row :gutter="16" class="chat-page__layout">
      <el-col :span="6">
        <el-card class="chat-page__card chat-page__sidebar" shadow="never">
          <div class="chat-page__header">
            <div class="chat-page__title">会话列表</div>
            <el-tooltip effect="dark" placement="top" content="新建会话">
              <el-button class="chat-page__new-btn" @click="openCreateDialog">
                <el-icon><Plus /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
          <el-scrollbar class="chat-page__session-scroll" v-loading="chatStore.loading">
            <el-menu
              class="chat-page__menu"
              :default-active="String(chatStore.currentSessionId || '')"
              @select="handleSelectSession"
            >
              <el-menu-item
                v-for="session in chatStore.sessions"
                :key="session.id"
                :index="String(session.id)"
              >
                <div
                  class="chat-page__session"
                  :class="{ 'chat-page__session--active': session.id === chatStore.currentSessionId }"
                >
                  <div class="chat-page__session-info">
                    <div
                      class="chat-page__session-title"
                      :title="session.title || `会话 ${session.id}`"
                    >
                      {{ session.title || `会话 ${session.id}` }}
                    </div>
                    <div class="chat-page__session-meta">
                      <span class="chat-page__session-meta-item">
                        {{ session.message_count || 0 }} 条消息
                      </span>
                      <span
                        v-if="session.knowledge_base_ids?.length"
                        class="chat-page__session-meta-item"
                      >
                        {{ session.knowledge_base_ids.length }} 个知识库
                      </span>
                    </div>
                  </div>
                  <div class="chat-page__session-actions">
                    <el-tooltip effect="dark" placement="top" content="删除会话">
                      <el-button
                        text
                        size="small"
                        class="chat-page__menu-delete"
                        @click.stop="handleDeleteSession(session)"
                      >
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </el-tooltip>
                  </div>
                </div>
              </el-menu-item>
            </el-menu>
            <div v-if="!chatStore.sessions.length && !chatStore.loading" class="chat-page__empty">
              <el-empty description="暂无会话，点击右上角创建一个新会话" />
            </div>
          </el-scrollbar>
        </el-card>
      </el-col>
      <el-col :span="18">
        <el-card class="chat-page__card chat-page__main" shadow="never">
          <div v-if="!chatStore.currentSessionId" class="chat-page__placeholder">
            请选择或创建一个会话开始聊天
          </div>
          <div v-else class="chat-page__conversation">
            <div class="chat-page__controls">
              <div class="chat-page__controls-label">检索范围</div>
              <el-select
                v-model="selectedKnowledgeBaseIds"
                multiple
                placeholder="选择知识库"
                class="chat-page__kb-select"
                @change="handleKbChange"
              >
                <el-option
                  v-for="kb in kbStore.list"
                  :key="kb.id"
                  :label="kb.name"
                  :value="kb.id"
                />
              </el-select>
            </div>
            <div class="chat-page__messages" ref="messageContainer">
              <div v-if="messages.length" class="chat-page__messages-list">
                <transition-group name="chat-message" tag="div">
                  <div
                    v-for="message in messages"
                    :key="message.id"
                    class="chat-page__message"
                    :class="[`chat-page__message--${message.role}`]"
                  >
                    <div class="chat-page__bubble">
                      <div class="chat-page__content" v-html="renderMarkdown(message.content)"></div>
                      <div v-if="getUniqueSources(message.sources)?.length" class="chat-page__sources">
                        <template v-for="(source, index) in getUniqueSources(message.sources)" :key="index">
                          <div class="chat-page__source">
                            [{{ index + 1 }}] {{ source.meta?.file_name || source.meta?.source || '文档' }}
                          </div>
                        </template>
                      </div>
                    </div>
                  </div>
                </transition-group>
              </div>
              <div v-else class="chat-page__messages-empty">
                <el-empty description="暂无消息，试着向助手提问吧" />
              </div>
            </div>
            <div class="chat-page__input">
              <el-input
                v-model="query"
                type="textarea"
                placeholder="请输入问题，按 Ctrl + Enter 发送"
                :autosize="{ minRows: 3, maxRows: 6 }"
                @keydown.native="handleKeyDown"
              />
              <div class="chat-page__actions">
                <span class="chat-page__hint">当前会话共 {{ messages.length }} 条消息</span>
                <el-button type="primary" :loading="sending" @click="handleSend">发送</el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="createDialogVisible" title="新建会话" width="420px">
      <el-form label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="createForm.title" placeholder="请输入会话标题（可选）" />
        </el-form-item>
        <el-form-item label="知识库">
          <el-select v-model="createForm.knowledgeBaseIds" multiple placeholder="请选择知识库">
            <el-option
              v-for="kb in kbStore.list"
              :key="kb.id"
              :label="kb.name"
              :value="kb.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreateSession">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref, watch, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus } from '@element-plus/icons-vue'
import { useChatStore } from '@/store/chat'
import { useKnowledgeBaseStore } from '@/store/knowledgeBase'
import { getSessionDetail, getSessionMessages, streamMessage } from '@/api/chat'
import { marked } from 'marked'

const chatStore = useChatStore()
const kbStore = useKnowledgeBaseStore()

const query = ref('')
const messages = ref([])
const sending = ref(false)
const selectedKnowledgeBaseIds = ref([])
const messageContainer = ref(null)

const createDialogVisible = ref(false)
const createForm = reactive({
  title: '',
  knowledgeBaseIds: [],
})

let streamHandler = null

function openCreateDialog() {
  if (!kbStore.list.length) {
    kbStore.fetchList()
  }
  createForm.title = ''
  createForm.knowledgeBaseIds = kbStore.list.slice(0, 1).map((kb) => kb.id)
  createDialogVisible.value = true
}

async function handleCreateSession() {
  if (!createForm.knowledgeBaseIds.length) {
    ElMessage.warning('请至少选择一个知识库')
    return
  }
  const session = await chatStore.createSession(createForm.knowledgeBaseIds, createForm.title)
  createDialogVisible.value = false
}

function handleSelectSession(id) {
  const sessionId = Number(id)
  chatStore.setCurrentSession(sessionId)
  // loadSession 会由 watch 监听 currentSessionId 变化后自动调用，避免重复调用
}

async function loadSession(sessionId) {
  if (!sessionId) return
  const session = await getSessionDetail(sessionId)
  selectedKnowledgeBaseIds.value = session.knowledge_base_ids || []
  await loadMessages(sessionId)
  await nextTick()
  scrollToBottom()
}

async function loadMessages(sessionId) {
  const data = await getSessionMessages(sessionId, { limit: 200 })
  messages.value = data || []
}

function handleKbChange() {
  // 更新会话选择的知识库将在发送时使用
}

function handleKeyDown(event) {
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
    event.preventDefault()
    handleSend()
  }
}

async function handleSend() {
  if (!query.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }
  if (!selectedKnowledgeBaseIds.value.length) {
    ElMessage.warning('请选择知识库')
    return
  }
  if (!chatStore.currentSessionId) {
    ElMessage.warning('请先选择会话')
    return
  }

  const sessionId = chatStore.currentSessionId
  const question = query.value
  query.value = ''

  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: question,
  })
  const assistantMessage = {
    id: `${Date.now()}-assistant`,
    role: 'assistant',
    content: '',
    sources: [],
  }
  messages.value.push(assistantMessage)
  // 获取消息在数组中的索引，用于后续更新
  const assistantMessageIndex = messages.value.length - 1
  sending.value = true
  await nextTick()
  scrollToBottom()

  try {
    if (streamHandler) {
      streamHandler.cancel()
    }
    streamHandler = streamMessage(
      {
        session_id: sessionId,
        query: question,
        knowledge_base_ids: selectedKnowledgeBaseIds.value,
      },
      {
        onChunk: (chunk) => {
          console.log('收到流式数据块:', chunk, '当前消息内容:', assistantMessage.content)
          // 实时更新助手消息内容
          if (chunk) {
            // 确保更新的是数组中的消息对象
            if (messages.value[assistantMessageIndex]) {
              messages.value[assistantMessageIndex].content += chunk
              console.log('更新后消息内容:', messages.value[assistantMessageIndex].content)
            } else {
              assistantMessage.content += chunk
              console.log('更新后消息内容 (fallback):', assistantMessage.content)
            }
            nextTick(scrollToBottom)
          }
        },
        onDone: (sources) => {
          console.log('流式响应完成，sources:', sources)
          // 流式响应完成，设置引用来源
          if (messages.value[assistantMessageIndex]) {
            messages.value[assistantMessageIndex].sources = sources || []
          } else {
            assistantMessage.sources = sources || []
          }
          sending.value = false
          streamHandler = null
          // 不再调用 loadMessages，因为流式响应已经包含了新消息
          nextTick(scrollToBottom)
        },
        onError: (error) => {
          sending.value = false
          streamHandler = null
          console.error('流式响应错误:', error)
          ElMessage.error('生成回答失败')
          // 错误时也不重新加载消息，保持当前状态
        },
      }
    )
  } catch (error) {
    sending.value = false
    streamHandler = null
    console.error('发送消息错误:', error)
    ElMessage.error('发送失败')
  }
}

async function handleDeleteSession(session) {
  try {
    await ElMessageBox.confirm(`确认删除会话「${session.title || `会话 ${session.id}`}」吗？`, '提示', {
      type: 'warning',
    })
    await chatStore.removeSession(session.id)
    ElMessage.success('会话已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('删除失败')
    }
  }
}

function getUniqueSources(sources) {
  if (!sources || !Array.isArray(sources) || sources.length === 0) {
    return []
  }
  
  const seen = new Set()
  const uniqueSources = []
  
  for (const source of sources) {
    const fileName = source.meta?.file_name || source.meta?.source || ''
    // 如果文件名为空，使用 doc_id 作为唯一标识
    const key = fileName || source.doc_id || JSON.stringify(source)
    
    if (!seen.has(key)) {
      seen.add(key)
      uniqueSources.push(source)
    }
  }
  
  return uniqueSources
}

function renderMarkdown(content) {
  if (!content) return ''
  try {
    // 配置 marked 选项
    marked.setOptions({
      breaks: true, // 支持换行
      gfm: true, // 支持 GitHub Flavored Markdown
    })
    return marked.parse(content)
  } catch (error) {
    console.error('Markdown 渲染错误:', error)
    return content
  }
}

function scrollToBottom() {
  const container = messageContainer.value
  if (!container) return
  container.scrollTop = container.scrollHeight
}

onUnmounted(() => {
  if (streamHandler) {
    streamHandler.cancel()
  }
})

watch(
  () => chatStore.currentSessionId,
  (sessionId) => {
    if (sessionId) {
      loadSession(sessionId)
    } else {
      messages.value = []
    }
  },
  { immediate: true }
)

onMounted(async () => {
  await Promise.all([kbStore.fetchList(), chatStore.fetchSessions()])
  if (!chatStore.currentSessionId && chatStore.sessions.length) {
    chatStore.setCurrentSession(chatStore.sessions[0].id)
  }
})
</script>

<style scoped>
.chat-page {
  min-height: calc(100vh - 120px);
  padding: 12px 0 24px;
  background: linear-gradient(160deg, #f8fbff 0%, #f2f3ff 40%, #ffffff 100%);
}

.chat-page__layout {
  width: 100%;
}

.chat-page__card {
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  box-shadow: 0 18px 40px rgba(15, 35, 95, 0.08);
  overflow: hidden;
}

.chat-page__card :deep(.el-card__body) {
  padding: 24px 24px 28px;
}

.chat-page__main :deep(.el-card__body) {
  padding: 24px 24px 12px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-page__sidebar :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  padding: 24px 12px 28px;
}

.chat-page__sidebar {
  height: calc(100vh - 200px);
  display: flex;
  flex-direction: column;
}

.chat-page__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.chat-page__title {
  font-size: 18px;
  font-weight: 600;
  color: #1f1f29;
}

.chat-page__new-btn {
  width: 28px;
  height: 28px;
  padding: 0;
  background: #f0f0f0;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  color: #4a4a4a;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-page__new-btn :deep(.el-icon) {
  font-size: 16px;
}

.chat-page__new-btn:hover {
  background: #e8e8e8;
  border-color: #d8d8d8;
  color: #333333;
}

.chat-page__new-btn:active {
  background: #e0e0e0;
  border-color: #d0d0d0;
  color: #1a1a1a;
}

.chat-page__session-scroll {
  flex: 1;
  min-height: 0;
  padding-right: 4px;
  overflow: hidden;
}

.chat-page__session-scroll :deep(.el-scrollbar__wrap) {
  max-height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
}

.chat-page__empty {
  margin-top: 48px;
}

.chat-page__menu {
  border: none;
  background: transparent;
}

.chat-page__menu :deep(.el-menu-item) {
  height: auto;
  padding: 0 0;
  margin-bottom: 12px;
  border-radius: 14px;
  background: transparent;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.chat-page__menu :deep(.el-menu-item:last-child) {
  margin-bottom: 0;
}

.chat-page__menu :deep(.el-menu-item.is-active) {
  background: transparent;
  box-shadow: none;
}

.chat-page__session {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 6px;
  border-radius: 14px;
  position: relative;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(109, 118, 255, 0.08);
  transition: all 0.28s ease;
  width: 100%;
  box-sizing: border-box;
}

.chat-page__session::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 14px;
  border: 1px solid transparent;
  transition: border-color 0.28s ease;
  pointer-events: none;
}

.chat-page__menu :deep(.el-menu-item:hover) .chat-page__session,
.chat-page__session--active {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(91, 141, 239, 0.14);
  background: rgba(255, 255, 255, 0.92);
}

.chat-page__menu :deep(.el-menu-item:hover) .chat-page__session::after,
.chat-page__session--active::after {
  border-color: rgba(122, 136, 255, 0.35);
}

.chat-page__session-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chat-page__session-title {
  width: 100%;
  font-size: 14px;
  font-weight: 600;
  color: #24283c;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.chat-page__session-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 12px;
  color: #8c8ea1;
}

.chat-page__session-meta-item {
  line-height: 1.2;
}

.chat-page__session-actions {
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-page__session-actions :deep(.el-button) {
  opacity: 1;
}

.chat-page__menu-delete {
  color: #f56c6c;
  padding: 0;
  min-height: auto;
}

.chat-page__menu-delete :deep(.el-icon) {
  font-size: 16px;
}

.chat-page__main {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 200px);
}

.chat-page__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: #9aa0b9;
  font-size: 15px;
}

.chat-page__conversation {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.chat-page__controls {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 18px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(117, 134, 255, 0.12);
  margin-bottom: 16px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

.chat-page__controls-label {
  font-size: 13px;
  font-weight: 600;
  color: #5a6199;
}

.chat-page__kb-select {
  flex: 1;
  max-width: 360px;
}

.chat-page__messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  background: linear-gradient(150deg, rgba(244, 246, 255, 0.8), rgba(255, 255, 255, 0.65));
  border-radius: 18px;
  padding: 24px;
  border: 1px solid rgba(121, 134, 255, 0.08);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.4);
}

.chat-page__messages-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding-right: 10px;
}

.chat-page__messages-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.chat-page__message {
  display: flex;
  margin-bottom: 18px;
}

.chat-page__message:last-child {
  margin-bottom: 0;
}

.chat-page__message--user {
  justify-content: flex-end;
}

.chat-page__message--assistant {
  justify-content: flex-start;
}

.chat-page__bubble {
  position: relative;
  max-width: 85%;
  width: fit-content;
  padding: 14px 18px;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 12px 26px rgba(56, 84, 170, 0.14);
  transition: transform 0.2s ease;
}

.chat-page__bubble::before {
  content: '';
  position: absolute;
  bottom: -6px;
  width: 14px;
  height: 14px;
  background: inherit;
  transform: rotate(45deg);
  box-shadow: inherit;
}

.chat-page__message--assistant .chat-page__bubble::before {
  left: 18px;
}

.chat-page__message--user .chat-page__bubble::before {
  right: 18px;
}

.chat-page__message--user .chat-page__bubble {
  background: linear-gradient(135deg, #5b8def, #7c72ff);
  color: #fff;
  box-shadow: 0 14px 28px rgba(92, 135, 255, 0.28);
}

.chat-page__message--assistant .chat-page__bubble {
  background: #ffffff;
  color: #1f223a;
}

.chat-page__content {
  word-break: break-word;
  word-wrap: break-word;
  overflow-wrap: break-word;
  font-size: 14px;
  line-height: 1.65;
  max-width: 100%;
}

.chat-page__content :deep(h1),
.chat-page__content :deep(h2),
.chat-page__content :deep(h3),
.chat-page__content :deep(h4),
.chat-page__content :deep(h5),
.chat-page__content :deep(h6) {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: 600;
  line-height: 1.4;
}

.chat-page__content :deep(h1) {
  font-size: 1.5em;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  padding-bottom: 0.3em;
}

.chat-page__content :deep(h2) {
  font-size: 1.3em;
}

.chat-page__content :deep(h3) {
  font-size: 1.15em;
}

.chat-page__content :deep(p) {
  margin: 0.5em 0;
}

.chat-page__content :deep(ul),
.chat-page__content :deep(ol) {
  margin: 0.5em 0;
  padding-left: 1.5em;
}

.chat-page__content :deep(li) {
  margin: 0.25em 0;
}

.chat-page__content :deep(strong) {
  font-weight: 600;
}

.chat-page__content :deep(em) {
  font-style: italic;
}

.chat-page__content :deep(code) {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 0.9em;
  background-color: rgba(0, 0, 0, 0.05);
  border-radius: 3px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
}

.chat-page__content :deep(pre) {
  padding: 0.8em;
  margin: 0.8em 0;
  overflow: auto;
  background-color: rgba(0, 0, 0, 0.05);
  border-radius: 6px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
  font-size: 0.9em;
  line-height: 1.45;
}

.chat-page__content :deep(pre code) {
  padding: 0;
  background-color: transparent;
  border-radius: 0;
}

.chat-page__content :deep(blockquote) {
  margin: 0.5em 0;
  padding-left: 1em;
  border-left: 3px solid rgba(0, 0, 0, 0.2);
  color: rgba(0, 0, 0, 0.7);
}

.chat-page__content :deep(table) {
  border-collapse: collapse;
  margin: 0.8em 0;
  width: 100%;
}

.chat-page__content :deep(th),
.chat-page__content :deep(td) {
  border: 1px solid rgba(0, 0, 0, 0.1);
  padding: 0.4em 0.6em;
}

.chat-page__content :deep(th) {
  background-color: rgba(0, 0, 0, 0.05);
  font-weight: 600;
}

.chat-page__content :deep(hr) {
  margin: 1em 0;
  border: none;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.chat-page__sources {
  margin-top: 10px;
  font-size: 12px;
  color: rgba(102, 108, 160, 0.9);
  border-top: 1px dashed rgba(92, 135, 255, 0.2);
  padding-top: 8px;
}

.chat-page__source + .chat-page__source {
  margin-top: 4px;
}

.chat-page__input {
  margin-top: 12px;
  margin-bottom: 0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(121, 134, 255, 0.12);
  box-shadow: 0 18px 30px rgba(45, 72, 160, 0.14);
}

.chat-page__input :deep(.el-textarea__inner) {
  border-radius: 14px;
  border: 1px solid rgba(121, 134, 255, 0.2);
  background: rgba(255, 255, 255, 0.85);
  box-shadow: inset 0 2px 4px rgba(45, 72, 160, 0.06);
  font-size: 14px;
  line-height: 1.6;
}

.chat-page__actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-page__hint {
  font-size: 12px;
  color: #7d85b2;
}

.chat-message-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.chat-message-enter-active,
.chat-message-leave-active {
  transition: all 0.25s ease;
}

.chat-message-enter-to {
  opacity: 1;
  transform: translateY(0);
}
</style>

