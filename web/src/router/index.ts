import { createRouter, createWebHistory } from 'vue-router'
import Article from '@/views/ArticleView.vue'
import Timeline from '@/views/TimelineView.vue'

const userId = 1
const lang = 'zh-CN'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: 'home',
      components: {
        LeftView: Timeline,
        RightView: Article,
      }
    }
  ]
})

export default router
