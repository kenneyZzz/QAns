import request from '@/utils/request'

export function createKnowledgeBase(data) {
  return request.post('/knowledge-bases', data)
}

export function getKnowledgeBaseList(params) {
  return request.get('/knowledge-bases', { params })
}

export function getKnowledgeBase(id) {
  return request.get(`/knowledge-bases/${id}`)
}

export function updateKnowledgeBase(id, data) {
  return request.put(`/knowledge-bases/${id}`, data)
}

export function deleteKnowledgeBase(id) {
  return request.delete(`/knowledge-bases/${id}`)
}

export function getKnowledgeBaseStats(id) {
  return request.get(`/knowledge-bases/${id}/stats`)
}

