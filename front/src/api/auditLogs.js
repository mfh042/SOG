import request from './request'

export const listAuditLogs = (params) => request.get('/api/audit-logs', { params })
export const listAuditActions = () => request.get('/api/audit-logs/actions')
