<template>
  <div class="app-wrapper">
    <header class="app-header">
      <div class="app-header__brand" @click="goHome">
        <span class="app-header__logo">Q</span>
        <div>
          <div class="app-header__title">QAns 智能知识助手</div>
        </div>
      </div>
      <el-menu
        mode="horizontal"
        :default-active="activeMenu"
        class="app-header__menu"
        :ellipsis="false"
        @select="handleSelect"
      >
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item index="/knowledge-base">知识库</el-menu-item>
        <el-menu-item index="/chat">对话</el-menu-item>
      </el-menu>
      <div class="app-header__actions">
        <el-dropdown>
          <span class="app-header__avatar" translate="no">Q</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>当前用户：Admin</el-dropdown-item>
              <el-dropdown-item divided @click="goKnowledgeBase">管理知识库</el-dropdown-item>
              <el-dropdown-item @click="goChat">前往对话</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { RefreshRight } from '@element-plus/icons-vue'

import { useKnowledgeBaseStore } from '@/store/knowledgeBase'
import { useChatStore } from '@/store/chat'

const router = useRouter()
const route = useRoute()
const kbStore = useKnowledgeBaseStore()
const chatStore = useChatStore()

const activeMenu = computed(() => {
  if (route.path.startsWith('/knowledge-base')) return '/knowledge-base'
  if (route.path.startsWith('/chat')) return '/chat'
  return '/'
})

function handleSelect(path) {
  router.push(path)
}

function goHome() {
  router.push('/')
}

function goKnowledgeBase() {
  router.push('/knowledge-base')
}

function goChat() {
  router.push('/chat')
}

async function handleRefresh() {
  if (activeMenu.value === '/knowledge-base') {
    await kbStore.fetchList()
  } else if (activeMenu.value === '/chat') {
    await chatStore.fetchSessions()
  } else {
    await Promise.all([kbStore.fetchList(), chatStore.fetchSessions()])
  }
}
</script>

<style scoped>
.app-wrapper {
  min-height: 100vh;
  background: linear-gradient(180deg, #f8fbff 0%, #eef1ff 100%);
}

.app-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  padding: 16px 32px;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 10;
  box-shadow: 0 4px 16px rgba(31, 45, 61, 0.08);
}

.app-header__brand {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.app-header__logo {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #2f80ed, #56ccf2);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 20px;
}

.app-header__title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.app-header__subtitle {
  font-size: 12px;
  color: #909399;
}

.app-header__menu {
  justify-self: center;
  border-bottom: none !important;
}

.app-header__actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.app-header__avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ff9a9e, #fad0c4);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}

.app-main {
  padding: 32px;
  max-width: 1240px;
  margin: 0 auto;
}

@media (max-width: 960px) {
  .app-header {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 12px 16px;
  }

  .app-header__menu {
    justify-self: stretch;
  }

  .app-header__actions {
    justify-content: flex-end;
  }

  .app-main {
    padding: 24px 16px 48px;
  }
}
</style>

