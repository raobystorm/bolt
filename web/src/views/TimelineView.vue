<template>
  <div class="Timeline">
    <h1>Timeline</h1>
    <ul>
      <div v-for="item in items" :key="item.title" class="card mb-3">
        <div class="row">
          <img v-bind:src="item.thumbnail_path" width="80" height="80" class="TimelineItemImage">
        </div>
      </div>
    </ul>
    <VueEternalLoading :load="load" />
  </div>
</template>

<style>
.h1 {
  font-size: large;
}
</style>

<script lang="ts" setup>
import { VueEternalLoading, type LoadAction } from "@ts-pro/vue-eternal-loading";
import { ref } from 'vue';
import type TimelineItem from "@/components/TimelineItem.vue";

const TIMELINE_URL = `http://127.0.0.1:3000/timeline`;
const PAGE_SIZE = 10;

let page = 0;
const lang = "zh-CN";
const items = ref<typeof TimelineItem[]>([]);

async function loadTimelineItems(page: Number, lang: String) {
  return fetch(`${TIMELINE_URL}/1?page=${page}&lang=${lang}`)
    .then(res => res.json());
}

async function load({ loaded, noMore }: LoadAction): Promise<void> {
  const loadedItems = await loadTimelineItems(page, lang);
  let count = 0;
  Object.keys(loadedItems).forEach(key => {
    count += loadedItems[key].length;
    items.value.push(...loadedItems[key]);
  })
  if (count < PAGE_SIZE) {
    noMore();
  } else {
    page += 1;
    loaded(loadedItems.length, PAGE_SIZE)
  }
}
</script>
