<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const loading = ref(false)
const form = reactive({
  username: '',
  password: '',
})

async function submit() {
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.push(route.query.redirect || '/dashboard')
  } finally {
    loading.value = false
  }
}

function fillDemo(u, p) {
  form.username = u
  form.password = p
}
</script>

<template>
  <div class="login-page">
    <div class="bg-grid"></div>
    <div class="bg-glow"></div>

    <div class="login-card">
      <div class="brand">
        <img class="brand-mark" src="/logo.jpg" alt="DELV-SOG" />
        <div class="brand-text">
          <div class="brand-title">离散装配生产作业支援系统</div>
          <div class="brand-subtitle">Shop-floor Operation Guide</div>
        </div>
      </div>

      <div class="form-title">账号登录</div>

      <el-form :model="form" label-position="top" class="form" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" size="large" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password size="large" />
        </el-form-item>
        <el-button type="primary" size="large" class="submit" :loading="loading" @click="submit">
          登 录
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

      <div class="footer">© DELV-SOG · 离散装配生产作业支援系统</div>
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
  border-radius: 14px;
  object-fit: cover;
  box-shadow: 0 8px 24px rgba(43, 124, 255, 0.35);
}
.brand-title { font-size: 18px; font-weight: 700; color: #1b2a40; }
.brand-subtitle { font-size: 12px; color: #5a6d86; letter-spacing: 1px; }

.form-title {
  font-size: 16px;
  font-weight: 600;
  color: #1b2a40;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #eaf2ff;
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