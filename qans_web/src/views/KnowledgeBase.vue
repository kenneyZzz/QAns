<template>
  <div class="kb-page">
    <!-- 主要内容区域：知识库列表和文档列表 -->
    <div class="kb-page__content">
      <!-- 左侧：知识库列表 -->
      <div class="kb-page__sidebar">
        <div class="kb-page__sidebar-header">
          <h2 class="kb-page__sidebar-title">知识库列表</h2>
          <div class="kb-page__sidebar-actions">
            <el-input
              v-model="search"
              clearable
              placeholder="搜索知识库"
              :suffix-icon="Search"
              style="width: 100%"
              size="small"
              @keyup.enter="handleSearch"
              @clear="handleSearch"
            />
            <el-button type="primary" size="small" @click="openCreateDialog">创建知识库</el-button>
          </div>
        </div>
        <div class="kb-page__list" v-loading="kbStore.loading">
          <template v-if="kbStore.list.length">
            <div
              v-for="kb in kbStore.list"
              :key="kb.id"
              class="kb-card"
              :class="{ 'kb-card--active': selectedId === kb.id }"
              @click="handleSelectKnowledgeBase(kb)"
            >
              <div class="kb-card__header">
                <div class="kb-card__icon">{{ initials(kb.name) }}</div>
                <div class="kb-card__info">
                  <div class="kb-card__name">{{ kb.name }}</div>
                  <div class="kb-card__desc">{{ kb.description || '暂无描述' }}</div>
                </div>
                <el-dropdown @click.stop trigger="click">
                  <el-icon class="kb-card__more"><MoreFilled /></el-icon>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item @click="handleEdit(kb)">编辑</el-dropdown-item>
                      <el-dropdown-item @click="handleDelete(kb)">删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
              <div class="kb-card__meta">
                <span class="kb-card__meta-item">
                  <el-icon><Document /></el-icon>
                  {{ kb.document_count || 0 }} 个文件
                </span>
                <span class="kb-card__meta-item">{{ formatDateShort(kb.create_time) }}</span>
              </div>
            </div>
          </template>
          <el-empty v-else description="暂无知识库，点击上方新建按钮创建" />
        </div>
        <div v-if="kbStore.total > kbStore.pageSize" class="kb-page__pagination">
          <el-pagination
            :current-page="kbStore.page"
            :page-size="kbStore.pageSize"
            :total="kbStore.total"
            layout="prev, pager, next"
            background
            @current-change="handlePageChange"
          />
        </div>
      </div>

      <!-- 右侧：文档列表 -->
      <div class="kb-page__main">
        <div v-if="selectedKnowledgeBase" class="kb-page__documents">
          <div class="kb-page__documents-header">
            <div class="kb-page__documents-title-group">
              <h2 class="kb-page__documents-title">{{ selectedKnowledgeBase.name }}</h2>
              <p class="kb-page__documents-desc">
                {{ selectedKnowledgeBase.description || '这个知识库尚未添加描述。' }}
              </p>
            </div>
            <div class="kb-page__documents-actions">
              <el-button plain @click="handleEdit(selectedKnowledgeBase)">编辑知识库</el-button>
              <el-button type="primary" :loading="uploading" @click="openUploadDialog">上传文档</el-button>
            </div>
          </div>
          <div class="kb-page__documents-table">
            <el-table :data="documentList" v-loading="documentLoading" stripe :max-height="tableMaxHeight">
              <el-table-column prop="file_name" label="文件名" min-width="200">
                <template #default="scope">
                  <div class="file-name-cell">{{ scope.row.file_name }}</div>
                </template>
              </el-table-column>
              <el-table-column prop="file_size" label="大小" width="100" align="right">
                <template #default="scope">{{ formatSize(scope.row.file_size) }}</template>
              </el-table-column>
              <el-table-column prop="chunk_count" label="分块数" width="80" align="center" />
              <el-table-column prop="status" label="解析状态" width="120" align="center">
                <template #default="scope">
                  <el-tag :type="statusTagType(scope.row.status)">{{ statusText(scope.row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="240" align="center" fixed="right">
                <template #default="scope">
                  <el-button
                    type="primary"
                    link
                    :loading="chunkingDocId === scope.row.id"
                    :disabled="scope.row.status === 'processing' || chunkingDocId === scope.row.id"
                    @click.stop="openChunkDialog(scope.row)"
                  >
                    分块
                  </el-button>
                  <el-button
                    type="primary"
                    link
                    :disabled="scope.row.chunk_count === 0"
                    @click.stop="goChunkPreview(scope.row)"
                  >
                    预览
                  </el-button>
                  <el-button type="primary" link @click.stop="handleDownloadDocument(scope.row)">
                    下载
                  </el-button>
                  <el-button type="danger" link @click="handleDeleteDocument(scope.row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div v-if="documentTotal > documentPageSize" class="kb-page__documents-pagination">
              <el-pagination
                :current-page="documentPage"
                :page-size="documentPageSize"
                :total="documentTotal"
                layout="prev, pager, next"
                background
                @current-change="handleDocumentPageChange"
              />
            </div>
          </div>
        </div>
        <div v-else class="kb-page__empty">
          <el-empty description="请选择左侧知识库查看文档列表" />
        </div>
      </div>
    </div>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="480px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="请输入名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" rows="3" placeholder="请输入描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
    <el-dialog
      v-model="chunkDialogVisible"
      title="配置分块参数"
      width="560px"
      @close="resetChunkDialog"
      class="chunk-dialog"
    >
      <template #default>
        <div v-if="currentChunkDocument" class="chunk-dialog__summary">
          <div class="chunk-dialog__summary-item">
            <el-icon class="chunk-dialog__summary-icon"><Document /></el-icon>
            <span class="chunk-dialog__summary-label">文件：</span>
            <span class="chunk-dialog__summary-value">{{ currentChunkDocument.file_name }}</span>
          </div>
          <div class="chunk-dialog__summary-item">
            <el-icon class="chunk-dialog__summary-icon"><InfoFilled /></el-icon>
            <span class="chunk-dialog__summary-label">类型：</span>
            <span class="chunk-dialog__summary-value">{{ currentChunkDocument.file_type || '未知' }}</span>
          </div>
        </div>
        <el-skeleton v-if="chunkConfigLoading" animated :rows="3" />
        <el-form v-else :model="chunkForm" label-width="100px" class="chunk-dialog__form">
          <el-form-item label="分块大小">
            <div class="chunk-dialog__form-item-wrapper">
              <el-input-number
                v-model="chunkForm.chunk_size"
                :min="1"
                :max="5000"
                :step="50"
                :precision="0"
                controls-position="right"
                style="width: 100%"
              />
              <span class="chunk-dialog__form-hint">字符数，建议范围：500-2000</span>
            </div>
          </el-form-item>
          <el-form-item label="文本重叠">
            <div class="chunk-dialog__form-item-wrapper">
              <el-input-number
                v-model="chunkForm.chunk_overlap"
                :min="0"
                :max="chunkForm.chunk_size - 1"
                :step="10"
                :precision="0"
                controls-position="right"
                style="width: 100%"
              />
              <span class="chunk-dialog__form-hint">字符数，建议为分块大小的10%-20%</span>
            </div>
          </el-form-item>
          <el-form-item label="分隔符">
            <div class="chunk-dialog__form-item-wrapper">
              <el-input
                v-model="chunkForm.separators"
                type="textarea"
                :rows="5"
                placeholder="每行一个分隔符，支持 \n, \t 等写法，留空则使用默认分隔符"
                class="chunk-dialog__textarea"
              />
              <span class="chunk-dialog__form-hint">用于分割文本的分隔符，每行一个</span>
            </div>
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <div class="chunk-dialog__footer">
          <el-button @click="chunkDialogVisible = false" :disabled="chunkDialogSubmitting" size="default">
            取消
          </el-button>
          <el-button type="primary" :loading="chunkDialogSubmitting" @click="submitChunkConfig" size="default">
            确定
          </el-button>
        </div>
      </template>
    </el-dialog>
    <el-dialog v-model="uploadDialogVisible" title="上传文件" width="600px" @close="resetUploadDialog">
      <template #default>
        <div class="upload-dialog__content">
          <div class="upload-dialog__info">
            <h4 class="upload-dialog__info-title">支持的文件类型</h4>
            <div class="upload-dialog__file-types">
              <el-tag v-for="type in supportedFileTypes" :key="type" class="upload-dialog__file-type-tag">
                {{ type }}
              </el-tag>
            </div>
            <div class="upload-dialog__size-limit">
              <el-icon><InfoFilled /></el-icon>
              <span>单个文件大小限制：<strong>10MB</strong></span>
            </div>
          </div>
          <el-upload
            ref="uploadRef"
            class="upload-dialog__uploader"
            drag
            :auto-upload="false"
            :accept="acceptFileTypes"
            :before-upload="beforeUpload"
            :on-remove="handleRemoveFile"
            :on-change="handleFileChange"
            :file-list="fileList"
            :disabled="uploading"
            :limit="1"
          >
            <el-icon class="upload-dialog__upload-icon"><UploadFilled /></el-icon>
            <div class="upload-dialog__upload-text">
              <p class="upload-dialog__upload-text-main">点击或拖拽文件至此区域即可上传</p>
              <p class="upload-dialog__upload-text-hint">支持单次上传一个文件</p>
            </div>
          </el-upload>
        </div>
      </template>
      <template #footer>
        <el-button @click="uploadDialogVisible = false" :disabled="uploading">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUploadSubmit" :disabled="fileList.length === 0">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { MoreFilled, Search, Document, UploadFilled, InfoFilled } from '@element-plus/icons-vue'

import { useKnowledgeBaseStore } from '@/store/knowledgeBase'
import { createKnowledgeBase, updateKnowledgeBase, deleteKnowledgeBase } from '@/api/knowledgeBase'
import {
  getDocumentList,
  uploadDocument,
  deleteDocument,
  chunkDocument,
  getChunkConfigs,
  downloadDocumentFile,
} from '@/api/document'

const kbStore = useKnowledgeBaseStore()
const search = ref('')
const dialogVisible = ref(false)
const dialogTitle = ref('新建知识库')
const editingId = ref(null)
const form = reactive({
  name: '',
  description: '',
})

const router = useRouter()
const selectedId = ref(null)
const documentList = ref([])
const documentLoading = ref(false)
const documentPage = ref(1)
const documentPageSize = ref(20)
const documentTotal = ref(0)
const uploading = ref(false)
const chunkingDocId = ref(null)
const chunkDialogVisible = ref(false)
const chunkDialogSubmitting = ref(false)
const chunkForm = reactive({
  chunk_size: 1000,
  chunk_overlap: 200,
  separators: '',
})
const chunkConfigs = ref(null)
const chunkConfigLoading = ref(false)
const currentChunkDocument = ref(null)
const uploadDialogVisible = ref(false)
const uploadRef = ref(null)
const fileList = ref([])

// 支持的文件类型（根据后端 document_loader.py 定义）
const supportedFileTypes = [
  '.txt',
  '.pdf',
  '.docx',
  '.md',
  '.markdown',
  '.xlsx',
  '.xls',
  '.html',
  '.htm',
  '.json',
]

// 用于 el-upload 的 accept 属性
const acceptFileTypes = supportedFileTypes.join(',')

// 文件大小限制：10MB
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB in bytes

const selectedKnowledgeBase = computed(() =>
  kbStore.list.find((item) => item.id === selectedId.value) || null
)

const totalDocuments = computed(() =>
  kbStore.list.reduce((sum, item) => sum + (item.document_count || 0), 0)
)
const averageDocuments = computed(() => {
  if (!kbStore.list.length) return 0
  return Math.round((totalDocuments.value / kbStore.list.length) * 10) / 10
})

watch(
  () => kbStore.list,
  (list) => {
    if (!list.length) {
      selectedId.value = null
      documentList.value = []
      return
    }
    if (!selectedId.value || !list.some((item) => item.id === selectedId.value)) {
      selectedId.value = list[0].id
    }
  },
  { immediate: true }
)

watch(
  selectedKnowledgeBase,
  (kb) => {
    if (kb) {
      documentPage.value = 1
      loadDocuments(kb.id)
    } else {
      documentList.value = []
      documentTotal.value = 0
    }
  },
  { immediate: false }
)

watch(
  () => chunkForm.chunk_size,
  (size) => {
    if (typeof size === 'number' && size > 0 && chunkForm.chunk_overlap >= size) {
      chunkForm.chunk_overlap = Math.max(size - 1, 0)
    }
  }
)

const isEdit = computed(() => editingId.value !== null)

function resetForm() {
  form.name = ''
  form.description = ''
  editingId.value = null
}

function openCreateDialog() {
  resetForm()
  dialogTitle.value = '新建知识库'
  dialogVisible.value = true
}

function handleEdit(row) {
  editingId.value = row.id
  form.name = row.name
  form.description = row.description || ''
  dialogTitle.value = '编辑知识库'
  dialogVisible.value = true
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除知识库「${row.name}」吗？`, '提示', {
      type: 'warning',
    })
    const deletedId = row.id
    await deleteKnowledgeBase(deletedId)
    ElMessage.success('删除成功')
    
    // 如果删除的是当前选中的知识库，清除选中状态
    if (selectedId.value === deletedId) {
      selectedId.value = null
      documentList.value = []
      documentTotal.value = 0
    }
    
    // 刷新列表
    await kbStore.fetchList()
    
    // 如果当前页没有数据了，且不是第一页，则回到上一页
    if (kbStore.list.length === 0 && kbStore.page > 1) {
      kbStore.setPagination(kbStore.page - 1, kbStore.pageSize)
      await kbStore.fetchList()
    }
    
    // 如果列表还有数据，且当前没有选中，则选中第一个
    if (kbStore.list.length > 0 && !selectedId.value) {
      selectedId.value = kbStore.list[0].id
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function handleSubmit() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入名称')
    return
  }

  try {
    if (isEdit.value) {
      await updateKnowledgeBase(editingId.value, {
        name: form.name,
        description: form.description,
      })
      ElMessage.success('更新成功')
    } else {
      await createKnowledgeBase({
        name: form.name,
        description: form.description,
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    kbStore.fetchList()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

function handleSearch() {
  kbStore.setSearch(search.value)
  kbStore.setPagination(1, kbStore.pageSize)
  kbStore.fetchList()
}

function handlePageChange(page) {
  kbStore.setPagination(page, kbStore.pageSize)
  kbStore.fetchList()
}

function handleSelectKnowledgeBase(kb) {
  selectedId.value = kb.id
}

async function loadDocuments(knowledgeBaseId) {
  if (!knowledgeBaseId) {
    documentList.value = []
    documentTotal.value = 0
    return
  }
  documentLoading.value = true
  try {
    const data = await getDocumentList({
      knowledge_base_id: knowledgeBaseId,
      page: documentPage.value,
      page_size: documentPageSize.value,
    })
    documentList.value = data.items || []
    documentTotal.value = data.total || 0
  } finally {
    documentLoading.value = false
  }
}

function handleDocumentPageChange(page) {
  documentPage.value = page
  if (selectedKnowledgeBase.value) {
    loadDocuments(selectedKnowledgeBase.value.id)
  }
}

function formatSize(size) {
  if (size === undefined || size === null) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let index = 0
  let value = size
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value.toFixed(2)} ${units[index]}`
}

function formatDate(value) {
  if (!value) return '未知'
  return new Date(value).toLocaleString()
}

function formatDateShort(value) {
  if (!value) return '未知'
  const date = new Date(value)
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function statusTagType(status) {
  switch (status) {
    case 'completed':
      return 'success'
    case 'chunked':
      return 'success'
    case 'failed':
      return 'danger'
    case 'processing':
      return 'warning'
    case 'uploaded':
    default:
      return 'info'
  }
}

function statusText(status) {
  switch (status) {
    case 'uploaded':
      return '已上传'
    case 'processing':
      return '处理中'
    case 'chunked':
      return '已分块'
    case 'completed':
      return '已向量化'
    case 'failed':
      return '失败'
    default:
      return '未知状态'
  }
}

function openUploadDialog() {
  if (!selectedKnowledgeBase.value) {
    ElMessage.warning('请先选择知识库')
    return
  }
  uploadDialogVisible.value = true
}

function resetUploadDialog() {
  fileList.value = []
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

function beforeUpload(file) {
  // 检查文件大小
  if (file.size > MAX_FILE_SIZE) {
    ElMessage.error(`文件大小不能超过 10MB，当前文件大小为 ${formatSize(file.size)}`)
    return false
  }

  // 检查文件类型
  const fileName = file.name.toLowerCase()
  const fileExt = fileName.substring(fileName.lastIndexOf('.'))
  if (!supportedFileTypes.includes(fileExt)) {
    ElMessage.error(`不支持的文件类型：${fileExt}，请上传支持的文件类型`)
    return false
  }

  return true
}

function handleFileChange(file, files) {
  // 文件选择后更新 fileList
  if (file.status === 'ready') {
    // 验证文件
    if (!beforeUpload(file.raw)) {
      // 如果验证失败，移除文件
      if (uploadRef.value) {
        uploadRef.value.handleRemove(file)
      }
      fileList.value = []
      return
    }
    // 验证通过，更新文件列表
    fileList.value = files
  }
}

function handleRemoveFile() {
  fileList.value = []
}

async function handleUploadSubmit() {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择要上传的文件')
    return
  }

  const file = fileList.value[0].raw || fileList.value[0]
  if (!file) {
    ElMessage.warning('文件无效')
    return
  }

  if (!selectedKnowledgeBase.value) {
    ElMessage.warning('请先选择知识库')
    return
  }

  // 再次验证文件
  if (!beforeUpload(file)) {
    return
  }

  const formData = new FormData()
  formData.append('knowledge_base_id', selectedKnowledgeBase.value.id)
  formData.append('file', file)

  uploading.value = true
  try {
    await uploadDocument(formData)
    ElMessage.success('上传成功，文件已保存')
    // 上传后跳转到第一页查看新文档
    documentPage.value = 1
    await loadDocuments(selectedKnowledgeBase.value.id)
    kbStore.fetchList()
    uploadDialogVisible.value = false
    resetUploadDialog()
  } catch (error) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

async function handleDeleteDocument(row) {
  try {
    await ElMessageBox.confirm(`确认删除文档「${row.file_name}」吗？`, '提示', {
      type: 'warning',
    })
    await deleteDocument(row.id)
    ElMessage.success('删除成功')
    if (selectedKnowledgeBase.value) {
      // 如果当前页删除后没有数据了，且不是第一页，则回到上一页
      if (documentList.value.length === 1 && documentPage.value > 1) {
        documentPage.value = documentPage.value - 1
      }
      loadDocuments(selectedKnowledgeBase.value.id)
    }
    kbStore.fetchList()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function ensureChunkConfigs() {
  if (chunkConfigs.value) return
  chunkConfigLoading.value = true
  try {
    chunkConfigs.value = await getChunkConfigs()
  } finally {
    chunkConfigLoading.value = false
  }
}

function resolveChunkConfig(fileType) {
  const map = chunkConfigs.value?.type_configs || {}
  const defaultConfig = chunkConfigs.value?.default || {
    chunk_size: 1000,
    chunk_overlap: 200,
    separators: null,
  }
  const key = (fileType || '').toLowerCase()
  return map[key] || defaultConfig
}

function formatSeparatorsForInput(separators) {
  if (!Array.isArray(separators) || !separators.length) {
    return ''
  }
  return separators
    .map((item) =>
      String(item)
        .replace(/\n/g, '\\n')
        .replace(/\t/g, '\\t')
    )
    .join('\n')
}

function parseSeparatorsFromInput(value) {
  if (value === undefined || value === null) return []
  if (value === '') return []
  return value.split('\n').map((item) =>
    item
      .replace(/\\n/g, '\n')
      .replace(/\\t/g, '\t')
  )
}

function resetChunkDialog() {
  chunkForm.chunk_size = 1000
  chunkForm.chunk_overlap = 200
  chunkForm.separators = ''
  currentChunkDocument.value = null
  chunkDialogSubmitting.value = false
  chunkingDocId.value = null
}

async function openChunkDialog(row) {
  if (!selectedKnowledgeBase.value) return
  chunkForm.chunk_size = 1000
  chunkForm.chunk_overlap = 200
  chunkForm.separators = ''
  currentChunkDocument.value = row
  chunkDialogVisible.value = true
  try {
    await ensureChunkConfigs()
  } catch {
    resetChunkDialog()
    chunkDialogVisible.value = false
    return
  }
  const config = resolveChunkConfig(row.file_type)
  chunkForm.chunk_size = config.chunk_size
  chunkForm.chunk_overlap = Math.min(
    config.chunk_overlap ?? 0,
    Math.max(config.chunk_size - 1, 0)
  )
  chunkForm.separators = formatSeparatorsForInput(config.separators)
}

async function submitChunkConfig() {
  if (!currentChunkDocument.value) return
  if (!chunkForm.chunk_size || chunkForm.chunk_size <= 0) {
    ElMessage.warning('分块大小需大于 0')
    return
  }
  if (chunkForm.chunk_overlap < 0) {
    ElMessage.warning('文本重叠不能为负数')
    return
  }
  if (chunkForm.chunk_overlap >= chunkForm.chunk_size) {
    ElMessage.warning('文本重叠需小于分块大小')
    return
  }

  const payload = {
    chunk_size: Math.floor(chunkForm.chunk_size),
    chunk_overlap: Math.floor(chunkForm.chunk_overlap),
  }
  const separators = parseSeparatorsFromInput(chunkForm.separators)
  if (Array.isArray(separators) && separators.length) {
    payload.separators = separators
  }

  chunkDialogSubmitting.value = true
  chunkingDocId.value = currentChunkDocument.value.id
  try {
    await chunkDocument(currentChunkDocument.value.id, payload)
    ElMessage.success('分块完成')
    chunkDialogVisible.value = false
    await loadDocuments(selectedKnowledgeBase.value.id)
  } catch {
    ElMessage.error('分块失败')
  } finally {
    chunkDialogSubmitting.value = false
    chunkingDocId.value = null
  }
}

async function handleDownloadDocument(row) {
  try {
    const blob = await downloadDocumentFile(row.id)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = row.file_name || `document-${row.id}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch {
    // 错误提示由请求拦截器处理
  }
}

function goChunkPreview(row) {
  if (!selectedKnowledgeBase.value) return
  router.push({
    name: 'DocumentChunkPreview',
    params: { kbId: selectedKnowledgeBase.value.id, docId: row.id },
  })
}

function initials(text) {
  if (!text) return 'KB'
  const trimmed = text.trim()
  if (!trimmed) return 'KB'
  return trimmed.slice(0, 2).toUpperCase()
}

onMounted(() => {
  kbStore.fetchList()
})
</script>

<style scoped>
.kb-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 200px);
  min-height: 600px;
  gap: 0;
}

/* 主要内容区域 */
.kb-page__content {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 0;
  flex: 1;
  overflow: hidden;
  background: #f5f7fa;
}

/* 左侧：知识库列表 */
.kb-page__sidebar {
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid #ebeef5;
  overflow: hidden;
}

.kb-page__sidebar-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid #ebeef5;
}

.kb-page__sidebar-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.kb-page__sidebar-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.kb-page__sidebar-actions .el-button {
  flex: 1;
  white-space: nowrap;
}

.kb-page__list {
  flex: 1;
  padding: 12px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.kb-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fff;
}

.kb-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.12);
  transform: translateY(-1px);
}

.kb-card--active {
  border-color: #409eff;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.06), rgba(64, 158, 255, 0.12));
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.15);
}

.kb-card__header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.kb-card__icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.kb-card__info {
  flex: 1;
  min-width: 0;
}

.kb-card__name {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
  color: #303133;
  line-height: 1.4;
  word-break: break-word;
}

.kb-card__desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.kb-card__meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #909399;
  padding-top: 8px;
  border-top: 1px solid #f5f7fa;
  gap: 8px;
}

.kb-card__meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.kb-card__more {
  cursor: pointer;
  color: #909399;
  padding: 6px;
  border-radius: 4px;
  transition: all 0.2s;
  flex-shrink: 0;
  font-size: 18px;
}

.kb-card__more:hover {
  color: #409eff;
  background: rgba(64, 158, 255, 0.1);
}

.kb-page__pagination {
  padding: 16px;
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: center;
}

/* 右侧：文档列表 */
.kb-page__main {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
}

.kb-page__documents {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.kb-page__documents-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 24px;
  border-bottom: 1px solid #ebeef5;
  gap: 24px;
}

.kb-page__documents-title-group {
  flex: 1;
  min-width: 0;
}

.kb-page__documents-title {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.kb-page__documents-desc {
  margin: 0;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.kb-page__documents-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-shrink: 0;
}

.kb-page__documents-stats {
  display: flex;
  gap: 24px;
  padding: 20px 24px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
}

.kb-page__documents-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.kb-page__documents-stat-label {
  font-size: 12px;
  color: #909399;
}

.kb-page__documents-stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.kb-page__documents-table {
  flex: 1;
  overflow: hidden;
  padding: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.kb-page__documents-pagination {
  padding: 16px;
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: center;
}

.kb-page__documents-table :deep(.el-table) {
  border: none;
}

.kb-page__documents-table :deep(.el-table__header) {
  background: #fafafa;
}

.kb-page__documents-table :deep(.el-table th) {
  background: #fafafa;
  border-bottom: 1px solid #ebeef5;
  color: #606266;
  font-weight: 600;
  font-size: 14px;
}

.kb-page__documents-table :deep(.el-table td) {
  font-size: 14px;
  color: #606266;
}

.kb-page__documents-table :deep(.el-table .cell) {
  font-size: 14px;
  line-height: 1.6;
}

.file-name-cell {
  word-break: break-all;
  word-wrap: break-word;
  white-space: normal;
  line-height: 1.6;
}

.kb-page__documents-table :deep(.el-table .el-button--text) {
  font-size: 14px;
}

.kb-page__documents-table :deep(.el-table .el-tag) {
  font-size: 13px;
  padding: 2px 10px;
}

.kb-page__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
}

/* 分块参数弹窗样式 */
.chunk-dialog :deep(.el-dialog__body) {
  padding: 24px;
}

.chunk-dialog__summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
  padding: 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #fafbfc 100%);
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.chunk-dialog__summary-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.chunk-dialog__summary-icon {
  color: #409eff;
  font-size: 16px;
  flex-shrink: 0;
}

.chunk-dialog__summary-label {
  color: #909399;
  font-weight: 500;
  min-width: 50px;
}

.chunk-dialog__summary-value {
  color: #303133;
  font-weight: 500;
  word-break: break-all;
  flex: 1;
}

.chunk-dialog__form {
  margin-top: 8px;
}

.chunk-dialog__form :deep(.el-form-item) {
  margin-bottom: 24px;
}

.chunk-dialog__form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
  font-size: 14px;
  padding-right: 16px;
}

.chunk-dialog__form-item-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.chunk-dialog__form :deep(.el-input-number) {
  width: 100%;
}

.chunk-dialog__form :deep(.el-input-number .el-input__inner) {
  text-align: left;
  padding-right: 80px;
}

.chunk-dialog__form :deep(.el-input-number .el-input__wrapper) {
  transition: all 0.3s ease;
}

.chunk-dialog__form :deep(.el-input-number .el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c0c4cc inset;
}

.chunk-dialog__form :deep(.el-input-number.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1px #409eff inset;
}

.chunk-dialog__form-hint {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.chunk-dialog__form-hint::before {
  content: '💡';
  font-size: 12px;
}

.chunk-dialog__textarea :deep(.el-textarea__inner) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: vertical;
  transition: all 0.3s ease;
}

.chunk-dialog__textarea :deep(.el-textarea__inner:hover) {
  border-color: #c0c4cc;
}

.chunk-dialog__textarea :deep(.el-textarea__inner:focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 1px #409eff inset;
}

.chunk-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 8px;
}

/* 上传弹出框样式 */
.upload-dialog__content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.upload-dialog__info {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.upload-dialog__info-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.upload-dialog__file-types {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.upload-dialog__file-type-tag {
  font-size: 12px;
}

.upload-dialog__size-limit {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
}

.upload-dialog__size-limit .el-icon {
  color: #409eff;
  font-size: 16px;
}

.upload-dialog__size-limit strong {
  color: #303133;
  font-weight: 600;
}

.upload-dialog__uploader {
  width: 100%;
}

.upload-dialog__uploader :deep(.el-upload) {
  width: 100%;
}

.upload-dialog__uploader :deep(.el-upload-dragger) {
  width: 100%;
  padding: 40px 20px;
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  background: #fafafa;
  transition: all 0.3s ease;
}

.upload-dialog__uploader :deep(.el-upload-dragger:hover) {
  border-color: #409eff;
  background: #f0f9ff;
}

.upload-dialog__upload-icon {
  font-size: 48px;
  color: #409eff;
  margin-bottom: 16px;
}

.upload-dialog__upload-text {
  text-align: center;
}

.upload-dialog__upload-text-main {
  margin: 0 0 8px;
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.upload-dialog__upload-text-hint {
  margin: 0;
  font-size: 12px;
  color: #909399;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .kb-page__content {
    grid-template-columns: 280px 1fr;
  }
}

@media (max-width: 1080px) {
  .kb-page__content {
    grid-template-columns: 1fr;
  }

  .kb-page__sidebar {
    border-right: none;
    border-bottom: 1px solid #ebeef5;
    max-height: 50vh;
  }

  .kb-page__documents-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .kb-page__documents-actions {
    width: 100%;
    justify-content: flex-end;
  }
}

@media (max-width: 768px) {
  .kb-page__sidebar-actions {
    flex-direction: column;
  }

  .kb-page__sidebar-actions .el-input {
    width: 100% !important;
  }
}

/* 滚动条样式 */
.kb-page__list::-webkit-scrollbar,
.kb-page__documents-table::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.kb-page__list::-webkit-scrollbar-track,
.kb-page__documents-table::-webkit-scrollbar-track {
  background: #f5f7fa;
}

.kb-page__list::-webkit-scrollbar-thumb,
.kb-page__documents-table::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 3px;
}

.kb-page__list::-webkit-scrollbar-thumb:hover,
.kb-page__documents-table::-webkit-scrollbar-thumb:hover {
  background: #a0a4ac;
}
</style>