import request from './request'

export const listSops = (params) => request.get('/api/sops', { params })
export const getSop = (id) => request.get(`/api/sops/${id}`)
export const createSop = (data) => request.post('/api/sops', data)
export const updateSop = (id, data) => request.put(`/api/sops/${id}`, data)
export const deleteSop = (id) => request.delete(`/api/sops/${id}`)
export const sopForOperation = (productCode, operationSeq) =>
  request.get(`/api/sops/for-operation/${encodeURIComponent(productCode)}/${operationSeq}`)