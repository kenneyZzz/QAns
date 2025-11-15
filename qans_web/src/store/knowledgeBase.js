import { defineStore } from 'pinia'
import { getKnowledgeBaseList } from '@/api/knowledgeBase'

export const useKnowledgeBaseStore = defineStore('knowledgeBase', {
  state: () => ({
    list: [],
    total: 0,
    loading: false,
    page: 1,
    pageSize: 10,
    search: '',
  }),
  actions: {
    async fetchList(params = {}) {
      this.loading = true
      try {
        const query = {
          page: this.page,
          page_size: this.pageSize,
          search: this.search || undefined,
          ...params,
        }
        const data = await getKnowledgeBaseList(query)
        this.list = data.items || []
        this.total = data.total || 0
      } finally {
        this.loading = false
      }
    },
    setPagination(page, pageSize) {
      this.page = page
      this.pageSize = pageSize
    },
    setSearch(value) {
      this.search = value
    },
    reset() {
      this.page = 1
      this.pageSize = 10
      this.search = ''
      this.list = []
      this.total = 0
    },
  },
})

