import request from './request'

export const listWorkOrders = (params) => request.get('/api/production/work-orders', { params })
export const getWorkOrder = (id) => request.get(`/api/production/work-orders/${id}`)
export const createWorkOrder = (data) => request.post('/api/production/work-orders', data)
export const updateWorkOrder = (id, data, version) =>
  request.put(`/api/production/work-orders/${id}`, data, { params: { version } })
export const transitionWo = (id, target) =>
  request.post(`/api/production/work-orders/${id}/transition`, null, { params: { target } })
export const listOperations = (id) => request.get(`/api/production/work-orders/${id}/operations`)
export const reportWo = (id, data) => request.post(`/api/production/work-orders/${id}/report`, data)
export const scrapWo = (id, data) => request.post(`/api/production/work-orders/${id}/scrap`, data)
export const listProgress = (params) => request.get('/api/production/progress', { params })
export const addInspection = (data) => request.post('/api/production/inspections', data)
export const listInspections = (params) => request.get('/api/production/inspections', { params })
export const qualityStats = () => request.get('/api/production/inspections/stats')
export const listTrace = (params) => request.get('/api/production/trace', { params })
export const forwardTrace = (product_batch) =>
  request.get(`/api/production/trace/forward/${encodeURIComponent(product_batch)}`)
export const backwardTrace = (material_batch) =>
  request.get(`/api/production/trace/backward/${encodeURIComponent(material_batch)}`)
export const traceTree = (product_batch) =>
  request.get(`/api/production/trace/tree/${encodeURIComponent(product_batch)}`)