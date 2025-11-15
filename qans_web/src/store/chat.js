import { defineStore } from 'pinia'
import { getSessionList, createSession, deleteSession as deleteSessionApi } from '@/api/chat'

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [],
    total: 0,
    page: 1,
    pageSize: 10,
    loading: false,
    currentSessionId: null,
  }),
  actions: {
    async fetchSessions(params = {}) {
      this.loading = true
      try {
        const query = {
          page: this.page,
          page_size: this.pageSize,
          ...params,
        }
        const data = await getSessionList(query)
        this.sessions = data.items || []
        this.total = data.total || 0
        if (!this.currentSessionId && this.sessions.length) {
          this.currentSessionId = this.sessions[0].id
        }
        if (this.currentSessionId && !this.sessions.find((item) => item.id === this.currentSessionId)) {
          this.currentSessionId = this.sessions[0]?.id || null
        }
      } finally {
        this.loading = false
      }
    },
    async createSession(knowledgeBaseIds, title) {
      const session = await createSession({ knowledge_base_ids: knowledgeBaseIds, title })
      this.currentSessionId = session.id
      await this.fetchSessions()
      return session
    },
    async removeSession(id) {
      await deleteSessionApi(id)
      if (this.currentSessionId === id) {
        this.currentSessionId = null
      }
      await this.fetchSessions()
    },
    setPagination(page, pageSize) {
      this.page = page
      this.pageSize = pageSize
    },
    setCurrentSession(id) {
      this.currentSessionId = id
    },
  },
})

