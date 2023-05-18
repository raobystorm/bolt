import { createRouter, createWebHistory } from 'vue-router'
import Article from '@/views/ArticleView.vue'
import Timeline from '@/views/TimelineView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: 'home',
      components: {
        List: Timeline,
      }
    }
  ]
})

export default router
