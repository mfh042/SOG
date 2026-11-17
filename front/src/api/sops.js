import request from './request'

export const listSops = (params) => request.get('/api/sops', { params })
export const getSop = (id) => request.get(`/api/sops/${id}`)
export const createSop = (data) => request.post('/api/sops', data)
export const updateSop = (id, data) => request.put(`/api/sops/${id}`, data)
export const deleteSop = (id) => request.delete(`/api/sops/${id}`)
export const sopForOperation = (productCode, operationSeq) =>
  request.get(`/api/sops/for-operation/${encodeURIComponent(productCode)}/${operationSeq}`)
export const dynamicSop = (productCode) =>
  request.get(`/api/sops/dynamic/${encodeURIComponent(productCode)}`)

export const uploadSopFile = (file) => {
  const fd = new FormData()
  fd.append('file', file)
  return request.post('/api/sops/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const listTemplates = (params) => request.get('/api/sops/templates/list', { params })
export const getTemplate = (id) => request.get(`/api/sops/templates/${id}`)
export const createTemplate = (data) => request.post('/api/sops/templates', data)
export const updateTemplate = (id, data) => request.put(`/api/sops/templates/${id}`, data)
export const deleteTemplate = (id) => request.delete(`/api/sops/templates/${id}`)
export const applyTemplate = (id, data) => request.post(`/api/sops/templates/${id}/apply`, data)