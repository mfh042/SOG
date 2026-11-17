import request from './request'

export const listMaterials = (params) => request.get('/api/materials', { params })
export const getMaterial = (id) => request.get(`/api/materials/${id}`)
export const createMaterial = (data) => request.post('/api/materials', data)
export const updateMaterial = (id, data) => request.put(`/api/materials/${id}`, data)
export const deleteMaterial = (id) => request.delete(`/api/materials/${id}`)
export const inbound = (data) => request.post('/api/materials/inbound', data)
export const reserve = (data) => request.post('/api/materials/reserve', data)
export const releaseStock = (data) => request.post('/api/materials/release', data)
export const issue = (data) => request.post('/api/materials/issue', data)
export const scrapStock = (data) => request.post('/api/materials/scrap', data)
export const adjustStock = (data) => request.post('/api/materials/adjust', data)
export const listInventory = (params) => request.get('/api/materials/inventory', { params })
export const getInventory = (id) => request.get(`/api/materials/inventory/${id}`)
export const listTxn = (params) => request.get('/api/materials/transactions', { params })
export const lowStock = () => request.get('/api/materials/low-stock')
export const importMaterials = (file) => {
  const fd = new FormData()
  fd.append('file', file)
  return request.post('/api/materials/import', fd)
}