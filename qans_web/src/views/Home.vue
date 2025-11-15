<template>
  <div class="home-page">
    <section class="home-page__hero">
      <div class="home-page__hero-copy">
        <h1>QAns 智能知识助手</h1>
        <p>
          构建个人或企业专属知识库，搭配多轮对话和智能检索，快速获得可靠答案。
        </p>
      </div>
    </section>

    <section class="home-page__metrics">
      <el-row :gutter="16">
        <el-col :sm="8" :xs="24">
          <div class="home-page__metric-card">
            <h3>知识库</h3>
            <p>集中管理结构化与非结构化数据，支持批量导入与更新。</p>
            <strong>{{ knowledgeBaseCount }}</strong>
          </div>
        </el-col>
        <el-col :sm="8" :xs="24">
          <div class="home-page__metric-card">
            <h3>文档资源</h3>
            <p>多格式解析与分块存储，保证检索精准度与溯源能力。</p>
            <strong>{{ documentCount }}</strong>
          </div>
        </el-col>
        <el-col :sm="8" :xs="24">
          <div class="home-page__metric-card">
            <h3>对话会话</h3>
            <p>结合上下文记忆与知识库，持续优化问答体验。</p>
            <strong>{{ sessionCount }}</strong>
          </div>
        </el-col>
      </el-row>
    </section>

    <section class="home-page__features">
      <h2>核心能力</h2>
      <el-row :gutter="16">
        <el-col :md="8" :xs="24">
          <div class="home-page__feature-card">
            <h3>智能整理</h3>
            <p>自动拆分文档、抽取关键字段与标签。</p>
          </div>
        </el-col>
        <el-col :md="8" :xs="24">
          <div class="home-page__feature-card">
            <h3>高质量检索</h3>
            <p>混合检索策略结合 Embedding 与关键词。</p>
          </div>
        </el-col>
        <el-col :md="8" :xs="24">
          <div class="home-page__feature-card">
            <h3>可靠溯源</h3>
            <p>答案附加引用来源，便于校验与持续学习。</p>
          </div>
        </el-col>
      </el-row>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useKnowledgeBaseStore } from '@/store/knowledgeBase'
import { useChatStore } from '@/store/chat'

const kbStore = useKnowledgeBaseStore()
const chatStore = useChatStore()

const knowledgeBaseCount = computed(() => kbStore.total || kbStore.list.length)
const documentCount = computed(() =>
  kbStore.list.reduce((sum, item) => sum + (item.document_count || 0), 0)
)
const sessionCount = computed(() => chatStore.sessions.length || chatStore.total)

onMounted(async () => {
  const fetchers = []
  if (!kbStore.list.length) {
    fetchers.push(kbStore.fetchList({ page_size: 100 }))
  }
  if (!chatStore.sessions.length) {
    fetchers.push(chatStore.fetchSessions({ page_size: 100 }))
  }
  await Promise.all(fetchers)
})
</script>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  gap: 48px;
  padding: 8px 0 48px;
}

.home-page__hero {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  align-items: center;
  gap: 32px;
  padding: 40px;
  border-radius: 24px;
  background: linear-gradient(135deg, #1e90ff 0%, #6f7bff 45%, #ffffff 100%);
  color: #fff;
  position: relative;
  overflow: hidden;
}

.home-page__hero::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.12), transparent 60%);
  pointer-events: none;
}

.home-page__hero-copy {
  position: relative;
  z-index: 1;
  max-width: 580px;
}

.home-page__hero-copy h1 {
  font-size: 36px;
  margin-bottom: 16px;
}

.home-page__hero-copy p {
  margin-bottom: 24px;
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.7;
}

.home-page__hero-actions {
  display: flex;
  gap: 12px;
}

.home-page__hero-visual {
  display: flex;
  justify-content: flex-end;
  position: relative;
  z-index: 1;
}

.home-page__hero-card {
  width: 280px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 20px;
  padding: 24px;
  color: #303133;
  box-shadow: 0 20px 45px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(6px);
}

.home-page__hero-card header {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.home-page__hero-card ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.home-page__hero-card li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
}

.home-page__hero-card strong {
  font-size: 22px;
  color: #1f2d3d;
}

.home-page__metrics {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.home-page__metric-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 10px 30px rgba(31, 45, 61, 0.08);
  min-height: 180px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.home-page__metric-card h3 {
  font-size: 18px;
  margin-bottom: 12px;
}

.home-page__metric-card p {
  color: #606266;
  flex: 1;
  line-height: 1.6;
}

.home-page__metric-card strong {
  font-size: 28px;
  color: #1e90ff;
}

.home-page__features h2 {
  font-size: 24px;
  margin-bottom: 24px;
}

.home-page__feature-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  height: 100%;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.home-page__feature-card h3 {
  font-size: 18px;
  margin: 0;
}

.home-page__feature-card p {
  color: #606266;
  line-height: 1.6;
  margin: 0;
}

@media (max-width: 768px) {
  .home-page__hero {
    padding: 32px 24px;
  }

  .home-page__hero-copy h1 {
    font-size: 28px;
  }

  .home-page__metric-card,
  .home-page__feature-card {
    min-height: auto;
  }
}
</style>

