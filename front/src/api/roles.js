import request from './request'

export const listRoles = () => request.get('/api/auth/roles')
export const getCatalog = () => request.get('/api/auth/permissions/catalog')
export const saveRolePermissions = (role, permissions) =>
  request.put(`/api/auth/roles/${role}/permissions`, { permissions })
