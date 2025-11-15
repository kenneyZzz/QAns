import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue'),
  },
  {
    path: '/knowledge-base',
    name: 'KnowledgeBase',
    component: () => import('../views/KnowledgeBase.vue'),
  },
  {
    path: '/knowledge-base/:kbId/document/:docId/chunks',
    name: 'DocumentChunkPreview',
    component: () => import('../views/DocumentChunkPreview.vue'),
    props: true,
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('../views/Chat.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router

