import request from './request'

export function getIntegrationConfig() {
  return request.get('/api/integration/config')
}

export function saveIntegrationConfig(items) {
  return request.post('/api/integration/config', items)
}

export function resetIntegrationConfig(key) {
  return request.post(`/api/integration/config/${key}/reset`)
}

export function setDataSource(dataType, source) {
  return request.post('/api/integration/data-source', { data_type: dataType, source })
}

export function getIntegrationHealth() {
  return request.get('/api/integration/health')
}

export function listIntegrationSystems() {
  return request.get('/api/integration/systems')
}

export function syncSystem(system, dataType = null) {
  const path = dataType
    ? `/api/integration/sync/${system}/${dataType}`
    : `/api/integration/sync/${system}`
  return request.post(path)
}

export function syncAllEnabled() {
  return request.post('/api/integration/sync')
}

export function listSyncJobs(params = {}) {
  return request.get('/api/integration/jobs', { params })
}