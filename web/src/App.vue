<template>
  <div class="container-fluid">
    <div class="row">
      <div class="col-6">
        <RouterView name="List" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import '@/scss/styles.scss'
import 'bootstrap/dist/css/bootstrap.min.css'

</script>


<style scoped></style>
