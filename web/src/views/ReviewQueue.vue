<template>
  <div>
    <el-table :data="items" border>
      <el-table-column prop="name" label="文件名" />
      <el-table-column prop="type" label="类型" width="80" />
      <el-table-column label="域" width="160"><template #default="{ row }">{{ row.domains.join(', ') }}</template></el-table-column>
      <el-table-column label="操作" width="260">
        <template #default="{ row }">
          <el-button size="small" @click="edit(row.document_id)">编辑客户字段</el-button>
          <el-button size="small" type="primary" @click="act(row.document_id, 'approve')">通过</el-button>
          <el-button size="small" type="danger" @click="act(row.document_id, 'reject')">拒绝</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" title="编辑客户字段" width="520px">
      <el-form label-width="80px">
        <el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="公司"><el-input v-model="form.company" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
        <el-form-item label="城市"><el-input v-model="form.city" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { documentDetail, reviewDocument, reviewQueue, saveCustomerFields, type DocumentHit } from '../api/admin'

const items = ref<DocumentHit[]>([])
const dialog = ref(false)
const currentId = ref('')
const form = reactive({ name: '', company: '', phone: '', email: '', city: '' })

async function load() {
  items.value = await reviewQueue()
}

async function act(id: string, action: 'approve' | 'reject') {
  await reviewDocument(id, action)
  ElMessage.success('已处理')
  load()
}

async function edit(id: string) {
  currentId.value = id
  const detail = await documentDetail(id)
  const f: any = detail.content?.fields || {}
  form.name = first(f.name)
  form.company = first(f.company)
  form.phone = first(f.phone)
  form.email = first(f.email)
  form.city = first(f.city)
  dialog.value = true
}

function first(v: any) {
  return Array.isArray(v) ? (v[0] ?? '') : (v ?? '')
}

async function save() {
  await saveCustomerFields(currentId.value, {
    name: form.name,
    company: form.company,
    phone: form.phone,
    email: form.email,
    city: form.city
  })
  ElMessage.success('已保存')
  dialog.value = false
  load()
}

onMounted(load)
</script>