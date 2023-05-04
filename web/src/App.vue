<script setup lang="ts">
import { RouterView } from 'vue-router'
// import '@/scss/styles.scss'
// import * as bootstrap from 'bootstrap'

</script>

<template>
  <div class="background">
    <div class="timeline">
      <RouterView name="LeftView" />
    </div>
    <div class="article">
      <RouterView name="RightView" />
    </div>
  </div>
</template>

<style scoped>
.background {
  display: flex;
  flex-direction: row;
  width: 100%;
}

.timeline {
  width: 20%;
}

.article {
  width: 80%;
}
</style>
