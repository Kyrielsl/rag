<template>
  <div>
    <el-form inline>
      <el-form-item label="动作">
        <el-input v-model="action" placeholder="如 search / login / classify" style="width:220px" />
      </el-form-item>
      <el-button type="primary" @click="load">查询</el-button>
    </el-form>

    <el-table :data="items" border>
      <el-table-column prop="created_at" label="时间" width="220" />
      <el-table-column prop="action" label="动作" width="120" />
      <el-table-column prop="subject" label="主体" width="140" />
      <el-table-column prop="result" label="结果" width="90" />
      <el-table-column prop="hit_count" label="命中" width="80" />
      <el-table-column prop="query_summary" label="摘要" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listAudit, type AuditItem } from '../api/admin'

const items = ref<AuditItem[]>([])
const action = ref('')

async function load() {
  items.value = await listAudit(action.value ? { action: action.value } : undefined)
}

onMounted(load)
</script>