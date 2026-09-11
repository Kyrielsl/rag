<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="6"><el-card><div class="num">{{ data.documents }}</div><div>文档总数</div></el-card></el-col>
      <el-col :span="6"><el-card><div class="num">{{ data.needs_review }}</div><div>待复核</div></el-card></el-col>
      <el-col :span="6"><el-card><div class="num">{{ data.domains }}</div><div>域数量</div></el-card></el-col>
      <el-col :span="6"><el-card><div class="num">{{ data.api_keys }}</div><div>API Key</div></el-card></el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { dashboard } from '../api/admin'

const data = reactive({ documents: 0, needs_review: 0, domains: 0, api_keys: 0 })

onMounted(async () => {
  Object.assign(data, await dashboard())
})
</script>

<style scoped>
.num { font-size: 32px; font-weight: bold; }
</style>