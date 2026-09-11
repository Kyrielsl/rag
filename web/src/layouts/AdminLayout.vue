<template>
  <el-container class="layout">
    <el-aside width="200px">
      <div class="logo">RAG 管理后台</div>
      <el-menu router :default-active="$route.path" background-color="#001529" text-color="#fff" active-text-color="#409eff">
        <el-menu-item index="/dashboard">仪表盘</el-menu-item>
        <el-menu-item index="/documents">文档列表</el-menu-item>
        <el-menu-item index="/review">复核队列</el-menu-item>
        <el-menu-item index="/domains">域管理</el-menu-item>
        <el-menu-item index="/api-keys">API Key</el-menu-item>
        <el-menu-item index="/audit">审计日志</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span>企业知识库</span>
        <el-button text @click="onLogout">退出登录</el-button>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

function onLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout { height: 100vh; }
.logo { color: #fff; padding: 16px; font-weight: bold; }
.header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; }
</style>