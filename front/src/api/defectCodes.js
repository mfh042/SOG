import request from './request'

export const listDefectCodes = (params) => request.get('/api/defect-codes', { params })
export const getDefectCodeByCode = (code) => request.get(`/api/defect-codes/${encodeURIComponent(code)}`)
export const getDefectCode = (id) => request.get(`/api/defect-codes/${id}`)
export const createDefectCode = (data) => request.post('/api/defect-codes', data)
export const updateDefectCode = (id, data) => request.put(`/api/defect-codes/${id}`, data)
export const deactivateDefectCode = (id) => request.delete(`/api/defect-codes/${id}`)