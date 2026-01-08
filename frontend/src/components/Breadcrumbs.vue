<script setup>
import IconBase from "@/components/IconBase.vue";

const props = defineProps({
  items: {
    type: Array,
    default: () => []
  }
});
</script>

<template>
  <div
    aria-label="bb-breadcrumbs"
    class="bb-breadcrumbs flex flex-row items-center gap-2"
  >
    <span
      v-for="(item, index) in items"
      :key="index"
      class="bb-breadcrumbs-item flex flex-row items-center gap-2"
    >
      <i
        v-if="item.icon && item.icon.startsWith('pi')"
        :class="item.icon"
        class="bb-breadcrumbs-icon"
      />
      <IconBase
        v-else-if="item.icon && item.icon.startsWith('Icon')"
        height="1.125rem"
        width="1.125rem"
      >
        <component :is="item.icon" />
      </IconBase>
      <span
        v-if="item.label"
        class="bb-breadcrums-label"
        v-html="item.label"
      ></span>
      <i
        v-if="items.length !== 1 && index < items.length - 1"
        class="pi pi-chevron-right bb-breadcrumbs-separator"
      />
    </span>
  </div>
</template>

<style scoped>
.bb-breadcrums-label {
  font-size: 1.25rem;
}

.bb-breadcrumbs-icon {
  font-size: 1.125rem;
}

.bb-breadcrumbs-separator {
  color: var(--primary-color);
  font-size: 0.825rem;
}
</style>
