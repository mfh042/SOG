<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const mode = ref('login')
const loading = ref(false)
const form = reactive({
  username: '',
  display_name: '',
  password: '',
  role: 'OPERATOR',
})

async function submit() {
  loading.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(form.username, form.password)
      ElMessage.success('登录成功')
      router.push(route.query.redirect || '/dashboard')
    } else {
      await auth.register({
        username: form.username,
        display_name: form.display_name || form.username,
        password: form.password,
        role: form.role,
      })
      ElMessage.success('注册成功，已自动登录')
      await auth.login(form.username, form.password)
      router.push('/dashboard')
    }
  } finally {
    loading.value = false
  }
}

function fillDemo(u, p) {
  form.username = u
  form.password = p
  form.display_name = u
}
</script>

<template>
  <div class="login-page">
    <div class="bg-grid"></div>
    <div class="bg-glow"></div>

    <div class="login-card">
      <div class="brand">
        <div class="brand-mark">SOG</div>
        <div class="brand-text">
          <div class="brand-title">离散装配生产作业支援系统</div>
          <div class="brand-subtitle">Shop-floor Operation Guide</div>
        </div>
      </div>

      <div class="switch">
        <div class="switch-tab" :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</div>
        <div class="switch-tab" :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</div>
        <div class="switch-bar" :style="{ transform: mode === 'login' ? 'translateX(0)' : 'translateX(100%)' }"></div>
      </div>

      <el-form :model="form" label-position="top" class="form" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" size="large" />
        </el-form-item>
        <el-form-item v-if="mode === 'register'" label="显示名称">
          <el-input v-model="form.display_name" placeholder="可选，默认使用用户名" size="large" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password size="large" />
        </el-form-item>
        <el-form-item v-if="mode === 'register'" label="角色">
          <el-select v-model="form.role" size="large" style="width: 100%">
            <el-option label="管理员 ADMIN" value="ADMIN" />
            <el-option label="计划员 MANAGER" value="MANAGER" />
            <el-option label="操作工 OPERATOR" value="OPERATOR" />
          </el-select>
        </el-form-item>
        <el-button type="primary" size="large" class="submit" :loading="loading" @click="submit">
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </el-button>
      </el-form>

      <div class="demo">
        <div class="demo-title">演示账号（点击一键填入）</div>
        <div class="demo-list">
          <div class="demo-item" @click="fillDemo('admin','admin123')">
            <span class="demo-label">管理员</span>
            <span class="demo-acct">admin / admin123</span>
          </div>
          <div class="demo-item" @click="fillDemo('planner','planner123')">
            <span class="demo-label">计划员</span>
            <span class="demo-acct">planner / planner123</span>
          </div>
          <div class="demo-item" @click="fillDemo('operator','op123')">
            <span class="demo-label">操作工</span>
            <span class="demo-acct">operator / op123</span>
          </div>
          <div class="demo-item" @click="fillDemo('quality','qc123')">
            <span class="demo-label">质检员</span>
            <span class="demo-acct">quality / qc123</span>
          </div>
        </div>
      </div>

      <div class="footer">© SOG · 离散装配生产作业支援系统</div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  width: 100vw; height: 100vh;
  background: linear-gradient(135deg, #0a1a36 0%, #143a6e 50%, #0d2244 100%);
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
}
.bg-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(43, 124, 255, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(43, 124, 255, 0.06) 1px, transparent 1px);
  background-size: 40px 40px;
}
.bg-glow {
  position: absolute;
  width: 600px; height: 600px;
  background: radial-gradient(circle, rgba(43, 124, 255, 0.35) 0%, transparent 70%);
  top: -200px; right: -200px;
}

.login-card {
  position: relative;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 44px 48px 32px;
  width: 440px;
  box-shadow: 0 24px 64px rgba(10, 26, 54, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.2);
}

.brand { display: flex; align-items: center; gap: 14px; margin-bottom: 28px; }
.brand-mark {
  width: 52px; height: 52px;
  background: linear-gradient(135deg, #2b7cff, #6ca6ff);
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 800; font-size: 16px;
  box-shadow: 0 8px 24px rgba(43, 124, 255, 0.35);
}
.brand-title { font-size: 18px; font-weight: 700; color: #1b2a40; }
.brand-subtitle { font-size: 12px; color: #5a6d86; letter-spacing: 1px; }

.switch {
  position: relative;
  display: flex;
  background: #eaf2ff;
  border-radius: 10px;
  padding: 4px;
  margin-bottom: 24px;
}
.switch-tab {
  flex: 1;
  text-align: center;
  padding: 8px 0;
  font-size: 14px;
  font-weight: 500;
  color: #5a6d86;
  cursor: pointer;
  z-index: 1;
  transition: color 0.2s;
}
.switch-tab.active { color: #1a5cd8; }
.switch-bar {
  position: absolute;
  top: 4px; left: 4px;
  width: calc(50% - 4px);
  height: calc(100% - 8px);
  background: #fff;
  border-radius: 7px;
  box-shadow: 0 2px 8px rgba(27, 42, 64, 0.1);
  transition: transform 0.25s ease;
  z-index: 0;
}

.form :deep(.el-form-item__label) { font-size: 13px; color: #1b2a40; font-weight: 500; padding-bottom: 4px; }
.form :deep(.el-input__wrapper) { border-radius: 8px; padding: 4px 12px; box-shadow: 0 0 0 1px #dfe7f2 inset; transition: box-shadow 0.2s; }
.form :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 2px #2b7cff inset; }
.submit {
  width: 100%;
  height: 44px !important;
  border-radius: 10px !important;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 4px;
  margin-top: 8px;
}

.demo {
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px dashed #dfe7f2;
}
.demo-title { font-size: 12px; color: #9aa7ba; margin-bottom: 10px; }
.demo-list { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.demo-item {
  background: #f4f8ff;
  border: 1px solid #d6e3ff;
  border-radius: 8px;
  padding: 8px 10px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex; flex-direction: column; gap: 2px;
}
.demo-item:hover { background: #eaf2ff; border-color: #2b7cff; }
.demo-label { font-size: 12px; font-weight: 600; color: #1a5cd8; }
.demo-acct { font-size: 11px; color: #5a6d86; font-family: Consolas, monospace; }

.footer {
  margin-top: 18px;
  text-align: center;
  font-size: 11px;
  color: #9aa7ba;
}
</style>