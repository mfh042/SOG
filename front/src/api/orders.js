import request from './request'

export const listOrders = (params) => request.get('/api/orders', { params })
export const getOrder = (id) => request.get(`/api/orders/${id}`)
export const createOrder = (data) => request.post('/api/orders', data)
export const updateOrder = (id, data, version) =>
  request.put(`/api/orders/${id}`, data, { params: { version } })
export const transitionOrder = (id, target) =>
  request.post(`/api/orders/${id}/transition`, null, { params: { target } })
export const releaseOrder = (id) => request.post(`/api/orders/${id}/release`)
export const getOrderByNo = (orderNo) => request.get(`/api/orders/no/${encodeURIComponent(orderNo)}`)
export const listOrderWorkOrders = (id) => request.get(`/api/orders/${id}/work-orders`)