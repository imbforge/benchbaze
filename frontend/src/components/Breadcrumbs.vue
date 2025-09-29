<script setup>
const props = defineProps({
  items: {
    type: Array,
    default: () => []
  },
  prefix: {
    type: Object,
    default: () => []
  }
});
</script>

<template>
  <div aria-label="breadcrumbs" class="breadcrumbs">
    <span class="first-letter-capital">{{ prefix.modelName }}</span>
    <i class="pi pi-chevron-right breadcrumb-separator" />
    <span>{{ prefix.id }}, {{ prefix.name }}</span>
    <span
      v-for="(item, index) in items"
      :key="index"
      :class="{ active: index === items.length - 1 }"
      class="breadcrumb-item"
      ><i class="pi pi-chevron-right breadcrumb-separator" />{{ item }}</span
    >
  </div>
</template>

<style scoped>
/* This is needed for first-letter to work with the spans above */
.first-letter-capital {
  display: inline-block;
}

.breadcrumb-separator {
  padding-left: 5px;
  padding-right: 5px;
  color: var(--primary-color);
}
</style>
