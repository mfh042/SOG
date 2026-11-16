import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, register as apiRegister } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('sog_token') || '')
  const user = ref(JSON.parse(localStorage.getItem('sog_user') || 'null'))

  const isLoggedIn = computed(() => !!token.value)

  async function login(username, password) {
    const res = await apiLogin({ username, password })
    token.value = res.access_token
    localStorage.setItem('sog_token', res.access_token)
    if (!user.value || user.value.username !== username) {
      user.value = { username, display_name: username, role: 'OPERATOR' }
      localStorage.setItem('sog_user', JSON.stringify(user.value))
    }
    return res
  }

  async function register(payload) {
    return apiRegister(payload)
  }

  function setUser(u) {
    user.value = u
    localStorage.setItem('sog_user', JSON.stringify(u))
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('sog_token')
    localStorage.removeItem('sog_user')
  }

  return { token, user, isLoggedIn, login, register, setUser, logout }
})