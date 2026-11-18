import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, getMe as apiGetMe } from '@/api/auth'

const ROLE_PERMISSIONS = {
  ADMIN: ['*'],
  MANAGER: [
    'material:read', 'material:create', 'material:update',
    'bom:read', 'bom:create', 'bom:update', 'bom:delete',
    'orders:read', 'orders:create', 'orders:release', 'orders:update', 'orders:cancel',
    'production:read', 'production:report', 'production:transition',
    'quality:read', 'quality:create', 'quality:update',
    'defect:read', 'defect:create', 'defect:update',
    'sop:read', 'sop:create', 'sop:update', 'sop:delete', 'sop:upload',
    'dashboard:read', 'trace:read', 'inventory:all', 'wip:read',
    'device:read', 'admin:audit',
  ],
  QUALITY: [
    'production:read',
    'quality:read', 'quality:create', 'quality:update',
    'defect:read', 'defect:create', 'defect:update',
    'sop:read', 'trace:read', 'dashboard:read',
  ],
  OPERATOR: [
    'production:read', 'production:report',
    'sop:read', 'trace:read', 'wip:read', 'inventory:read',
    'dashboard:read',
  ],
  PLANNER: [
    'orders:read', 'orders:create', 'orders:release',
    'bom:read', 'bom:create', 'bom:update',
    'material:read', 'material:create',
    'production:read', 'production:report',
    'quality:read',
    'sop:read', 'sop:create', 'sop:update', 'sop:upload',
    'dashboard:read', 'trace:read',
  ],
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('delv_sog_token') || '')
  const user = ref(JSON.parse(localStorage.getItem('delv_sog_user') || 'null'))

  const isLoggedIn = computed(() => !!token.value)

  function hasPerm(perm) {
    if (!user.value) return false
    const perms = ROLE_PERMISSIONS[user.value.role] || []
    return perms.includes('*') || perms.includes(perm)
  }

  async function login(username, password) {
    const res = await apiLogin({ username, password })
    token.value = res.access_token
    localStorage.setItem('delv_sog_token', res.access_token)
    await refreshUser()
    return res
  }

  async function refreshUser() {
    try {
      const me = await apiGetMe()
      user.value = {
        user_id: me.id,
        username: me.username,
        display_name: me.display_name || me.username,
        role: me.role,
        station_code: me.station_code,
      }
      localStorage.setItem('delv_sog_user', JSON.stringify(user.value))
    } catch (e) {
      user.value = null
      localStorage.removeItem('delv_sog_user')
      token.value = ''
      localStorage.removeItem('delv_sog_token')
      throw e
    }
  }

  function setUser(u) {
    user.value = u
    localStorage.setItem('delv_sog_user', JSON.stringify(u))
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('delv_sog_token')
    localStorage.removeItem('delv_sog_user')
  }

  return { token, user, isLoggedIn, hasPerm, login, setUser, refreshUser, logout }
})