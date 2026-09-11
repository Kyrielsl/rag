<template>
  <div>
    <el-table :data="items" border>
      <el-table-column prop="name" label="文件名" />
      <el-table-column prop="type" label="类型" width="80" />
      <el-table-column label="域" width="200"><template #default="{ row }">{{ row.domains.join(', ') }}</template></el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="act(row.document_id, 'approve')">通过</el-button>
          <el-button size="small" type="danger" @click="act(row.document_id, 'reject')">拒绝</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { reviewDocument, reviewQueue, type DocumentHit } from '../api/admin'

const items = ref<DocumentHit[]>([])

async function load() {
  items.value = await reviewQueue()
}

async function act(id: string, action: 'approve' | 'reject') {
  await reviewDocument(id, action)
  ElMessage.success('已处理')
  load()
}

onMounted(load)
</script>