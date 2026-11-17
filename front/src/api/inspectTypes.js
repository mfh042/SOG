import request from './request'

export const listInspectTypes = (params) => request.get('/api/inspect-types', { params })
export const getInspectType = (id) => request.get(`/api/inspect-types/${id}`)
export const createInspectType = (data) => request.post('/api/inspect-types', data)
export const updateInspectType = (id, data) => request.put(`/api/inspect-types/${id}`, data)
export const deactivateInspectType = (id) => request.delete(`/api/inspect-types/${id}`)