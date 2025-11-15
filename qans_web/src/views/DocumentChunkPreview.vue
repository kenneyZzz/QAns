<template>
  <div class="chunk-preview">
    <el-page-header
      class="chunk-preview__header"
      @back="handleBack"
      content="文档分块预览"
    >
      <template #extra>
        <el-button
          type="primary"
          :disabled="!chunks.length || vectorizing"
          :loading="vectorizing"
          @click="handleVectorize"
        >
          文本块向量化
        </el-button>
      </template>
    </el-page-header>

    <el-card class="chunk-preview__card" v-loading="loading">
      <div class="chunk-preview__meta" v-if="documentInfo">
        <div class="chunk-preview__meta-item">
          <span class="label">文件名</span>
          <span class="value">{{ documentInfo.file_name }}</span>
        </div>
        <div class="chunk-preview__meta-item">
          <span class="label">状态</span>
          <el-tag :type="statusTagType(documentInfo.status)">
            {{ statusText(documentInfo.status) }}
          </el-tag>
        </div>
        <div class="chunk-preview__meta-item">
          <span class="label">分块数量</span>
          <span class="value">{{ documentInfo.chunk_count }}</span>
        </div>
        <div class="chunk-preview__meta-item">
          <span class="label">更新时间</span>
          <span class="value">{{ formatDate(documentInfo.update_time) }}</span>
        </div>
      </div>

      <el-divider content-position="left">分块详情</el-divider>

      <el-empty v-if="!chunks.length" description="暂无分块结果，请先在列表页执行分块操作" />
      <el-scrollbar v-else class="chunk-preview__list">
        <div v-for="item in chunks" :key="item.id" class="chunk-preview__chunk">
          <header class="chunk-preview__chunk-header">
            <span>块 {{ item.chunk_index }}</span>
            <span class="chunk-preview__chunk-length">长度：{{ item.content.length }}</span>
          </header>
          <pre class="chunk-preview__chunk-content">{{ item.content }}</pre>
          <details class="chunk-preview__chunk-meta" v-if="item.metadata && Object.keys(item.metadata).length">
            <summary>元数据</summary>
            <pre>{{ prettyMetadata(item.metadata) }}</pre>
          </details>
        </div>
      </el-scrollbar>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { getDocument, getDocumentChunks, vectorizeDocument } from '@/api/document'

const props = defineProps({
  kbId: {
    type: [String, Number],
    required: true,
  },
  docId: {
    type: [String, Number],
    required: true,
  },
})

const router = useRouter()
const documentInfo = ref(null)
const chunks = ref([])
const loading = ref(false)
const vectorizing = ref(false)

const docId = computed(() => Number(props.docId))

onMounted(() => {
  fetchData()
})

async function fetchData() {
  loading.value = true
  try {
    const [docRes, chunkRes] = await Promise.all([
      getDocument(docId.value),
      getDocumentChunks(docId.value),
    ])
    documentInfo.value = docRes
    chunks.value = chunkRes || []
  } catch (error) {
    ElMessage.error('获取文档信息失败')
  } finally {
    loading.value = false
  }
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

function formatDate(value) {
  if (!value) return '未知'
  return new Date(value).toLocaleString()
}

function prettyMetadata(meta) {
  try {
    return JSON.stringify(meta, null, 2)
  } catch (error) {
    return meta
  }
}

async function handleVectorize() {
  if (!chunks.value.length) {
    ElMessage.warning('暂无分块数据，无法向量化')
    return
  }
  vectorizing.value = true
  try {
    await vectorizeDocument(docId.value)
    ElMessage.success('向量化成功')
    await fetchData()
  } catch (error) {
    ElMessage.error('向量化失败')
  } finally {
    vectorizing.value = false
  }
}

function handleBack() {
  router.back()
}
</script>

<style scoped>
.chunk-preview {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: calc(100vh - 160px);
}

.chunk-preview__header {
  background: #fff;
  border-radius: 12px;
  padding: 12px 16px;
  box-shadow: 0 6px 18px rgba(31, 45, 61, 0.08);
}

.chunk-preview__card {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  border-radius: 16px;
  box-shadow: 0 12px 32px rgba(31, 45, 61, 0.08);
  height: calc(100vh - 220px);
  max-height: calc(100vh - 220px);
  overflow: hidden;
}

.chunk-preview__card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.chunk-preview__meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.chunk-preview__meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #606266;
}

.chunk-preview__meta-item .label {
  min-width: 72px;
  color: #909399;
}

.chunk-preview__meta-item .value {
  color: #1f2d3d;
  font-weight: 500;
}

.chunk-preview__list {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.chunk-preview__list :deep(.el-scrollbar__wrap) {
  height: 100%;
  max-height: 100%;
}

.chunk-preview__list :deep(.el-scrollbar__view) {
  min-height: 100%;
  padding-right: 8px;
}

.chunk-preview__list :deep(.el-scrollbar__bar.is-vertical) {
  right: 2px;
}

@media (max-width: 960px) {
  .chunk-preview {
    min-height: auto;
  }

  .chunk-preview__card {
    height: auto;
    max-height: none;
  }

  .chunk-preview__list {
    max-height: 60vh;
  }
}

.chunk-preview__chunk {
  border: 1px solid rgba(60, 138, 255, 0.2);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  background: rgba(60, 138, 255, 0.04);
}

.chunk-preview__chunk:last-child {
  margin-bottom: 0;
}

.chunk-preview__chunk-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #3c8aff;
  margin-bottom: 12px;
}

.chunk-preview__chunk-length {
  font-size: 12px;
  color: #606266;
}

.chunk-preview__chunk-content {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'JetBrains Mono', 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #1f2d3d;
  margin: 0;
}

.chunk-preview__chunk-meta {
  margin-top: 12px;
  font-size: 12px;
  color: #606266;
}

.chunk-preview__chunk-meta summary {
  cursor: pointer;
  color: #3c8aff;
}

.chunk-preview__chunk-meta pre {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 8px 0 0;
  font-family: 'JetBrains Mono', 'Courier New', Courier, monospace;
}
</style>

