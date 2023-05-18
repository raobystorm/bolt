<template>
  <div class="Article">
    <div class="row">
      <div class="col-6">
        <h2 class="SectionTitle">Original Article</h2>
        <div v-if="isLoading2" class="d-flex justify-content-center">
          <div class="spinner-border m-5" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>
        <div v-else>
          <!-- your data display code here -->
        </div>
      </div>
      <div class="col-6">
        <h2 class="SectionTitle">Translated Article</h2>
        <div v-if="isLoading1" class="d-flex justify-content-center">
          <div class="spinner-border m-5" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>
        <div v-else>
          <!-- your data display code here -->
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
let isLoading1 = true;
let isLoading2 = true;
</script>

<style>
.SectionTitle {
  text-align: center;
}
</style>
