<template>
  <div class="TimelineItem">
    <h1>Timeline item</h1>
  </div>
</template>

<script lang="ts">
export default {
  name: "TimelineItem",
  props: {
    title: String,
    media: String,
    thumbnailUrl: String,
  }
}
</script>