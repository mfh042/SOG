import request from './request'

export const overview = () => request.get('/api/dashboard/overview')
export const kitAlerts = () => request.get('/api/dashboard/kit-alerts')