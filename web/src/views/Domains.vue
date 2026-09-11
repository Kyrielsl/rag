<template>
  <div>
    <el-form inline @submit.prevent="create">
      <el-form-item><el-input v-model="name" placeholder="新域名称" /></el-form-item>
      <el-form-item><el-checkbox v-model="sensitive">敏感域</el-checkbox></el-form-item>
      <el-button type="primary" native-type="submit">新增</el-button>
    </el-form>

    <el-table :data="items" border>
      <el-table-column prop="name" label="域" />
      <el-table-column label="敏感" width="120">
        <template #default="{ row }"><el-switch :model-value="row.is_sensitive" @change="(v:boolean) => update(row.id, { is_sensitive: v })" /></template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createDomain, listDomains, updateDomain, type DomainItem } from '../api/admin'

const items = ref<DomainItem[]>([])
const name = ref('')
const sensitive = ref(false)

async function load() {
  items.value = await listDomains()
}

async function create() {
  await createDomain(name.value, sensitive.value)
  ElMessage.success('已新增')
  name.value = ''
  sensitive.value = false
  load()
}

async function update(id: string, body: { enabled?: boolean; is_sensitive?: boolean }) {
  await updateDomain(id, body)
  load()
}

onMounted(load)
</script>