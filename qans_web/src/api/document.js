import request from '@/utils/request'

export function uploadDocument(formData) {
  return request.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getDocumentList(params) {
  return request.get('/documents', { params })
}

export function getDocument(id) {
  return request.get(`/documents/${id}`)
}

export function deleteDocument(id) {
  return request.delete(`/documents/${id}`)
}

export function getDocumentStatus(id) {
  return request.get(`/documents/${id}/status`)
}

export function chunkDocument(id, data) {
  return request.post(`/documents/${id}/chunk`, data)
}

export function getDocumentChunks(id) {
  return request.get(`/documents/${id}/chunks`)
}

export function vectorizeDocument(id) {
  return request.post(`/documents/${id}/vectorize`)
}

export function getChunkConfigs() {
  return request.get('/documents/chunk/configs')
}

export function downloadDocumentFile(id, config = {}) {
  return request.get(`/documents/${id}/download`, {
    ...config,
    responseType: config.responseType || 'blob',
  })
}

