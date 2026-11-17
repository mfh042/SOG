import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import './assets/main.css'

const pinia = createPinia()
const app = createApp(App)
for (const [key, comp] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, comp)
}
app.use(pinia)
app.use(router)
app.use(ElementPlus)

const auth = useAuthStore()
const existingUser = JSON.parse(localStorage.getItem('sog_user') || 'null')
if (auth.token && (!existingUser || existingUser.role === 'OPERATOR')) {
  auth.refreshUser().catch(() => {})
}

app.mount('#app')