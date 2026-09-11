<template>
  <div>
    <el-form inline @submit.prevent="create">
      <el-form-item><el-input v-model="name" placeholder="Key 名称" /></el-form-item>
      <el-form-item>
        <el-select v-model="scope" style="width:120px">
          <el-option label="上传" value="upload" />
          <el-option label="检索" value="search" />
        </el-select>
      </el-form-item>
      <el-button type="primary" native-type="submit">创建</el-button>
    </el-form>

    <el-table :data="items" border>
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="scope" label="用途" width="100" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column prop="created_at" label="创建时间" width="220" />
    </el-table>

    <el-dialog v-model="dialog" title="新 Key（只显示一次）">
      <p>{{ createdKey }}</p>
      <el-button @click="dialog = false">关闭</el-button>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createApiKey, listApiKeys, type ApiKeyItem } from '../api/admin'

const items = ref<ApiKeyItem[]>([])
const name = ref('')
const scope = ref('search')
const dialog = ref(false)
const createdKey = ref('')

async function load() {
  items.value = await listApiKeys()
}

async function create() {
  const data = await createApiKey(name.value, scope.value)
  createdKey.value = data.key
  dialog.value = true
  name.value = ''
  load()
}

onMounted(load)
</script>