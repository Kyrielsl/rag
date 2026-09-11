<template>
  <div>
    <el-form inline>
      <el-form-item label="状态">
        <el-select v-model="status" clearable placeholder="全部" style="width:160px">
          <el-option label="CONFIRMED" value="CONFIRMED" />
          <el-option label="READY" value="READY" />
          <el-option label="FAILED" value="FAILED" />
          <el-option label="REJECTED" value="REJECTED" />
        </el-select>
      </el-form-item>
      <el-button type="primary" @click="load">查询</el-button>
    </el-form>

    <el-table :data="items" border>
      <el-table-column prop="name" label="文件名" />
      <el-table-column prop="type" label="类型" width="80" />
      <el-table-column prop="status" label="状态" width="120" />
      <el-table-column label="域" width="200"><template #default="{ row }">{{ row.domains.join(', ') }}</template></el-table-column>
      <el-table-column prop="created_at" label="上传时间" width="200" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }"><el-button link type="primary" @click="showDetail(row.document_id)">详情</el-button></template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" title="文档详情" width="720px">
      <template v-if="detail">
        <p>名称：{{ detail.name }}（{{ detail.type }}）</p>
        <p>状态：{{ detail.status }} / 提取：{{ detail.extracted_status }} / 待复核：{{ detail.needs_review }}</p>
        <p>域：<el-tag v-for="d in detail.domains" :key="d.domain">{{ d.domain }}（{{ d.source }}）</el-tag></p>
        <el-divider>提取内容</el-divider>
        <pre class="pre">{{ detail.content?.text || '（无文本）' }}</pre>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { documentDetail, listDocuments, type DocumentDetail, type DocumentHit } from '../api/admin'

const items = ref<DocumentHit[]>([])
const status = ref('')
const dialog = ref(false)
const detail = ref<DocumentDetail | null>(null)

async function load() {
  items.value = await listDocuments(status.value ? { status: status.value } : undefined)
}

async function showDetail(id: string) {
  detail.value = await documentDetail(id)
  dialog.value = true
}

onMounted(load)
</script>

<style scoped>
.pre { max-height: 320px; overflow: auto; background: #f5f5f5; padding: 12px; white-space: pre-wrap; }
</style>