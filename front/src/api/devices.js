import request from './request'

export const listDevices = (params) => request.get('/api/devices', { params })
export const createDevice = (data) => request.post('/api/devices', data)
export const getDeviceProtocols = () => request.get('/api/devices/protocols')
