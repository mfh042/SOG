import request from './request'

export const listBoms = (params) => request.get('/api/boms', { params })
export const getBom = (id) => request.get(`/api/boms/${id}`)
export const createBom = (data) => request.post('/api/boms', data)
export const updateBom = (id, data) => request.put(`/api/boms/${id}`, data)
export const activateBom = (id) => request.post(`/api/boms/${id}/activate`)
export const bomShortage = (productMaterialId, qty) =>
  request.get(`/api/boms/shortage/${productMaterialId}`, { params: { qty } })