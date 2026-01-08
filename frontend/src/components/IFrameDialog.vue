<script setup>
import Breadcrumbs from "@/components/Breadcrumbs.vue";
import { computed } from "vue";

const props = defineProps({
  breadcrumbItems: {
    type: Array,
    default: () => []
  },
  iframeUrl: {
    type: String,
    default: ""
  },
  visible: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(["update:visible"]);
const internalVisible = computed({
  get: () => props.visible,
  set: (value) => {
    emit("update:visible", value);
  }
});
</script>

<template>
  <Dialog
    v-model:visible="internalVisible"
    maximizable
    :style="{ width: '90%', height: '90%' }"
    :modal="true"
  >
    <template #header>
      <Breadcrumbs :items="breadcrumbItems" />
    </template>
    <iframe
      :src="iframeUrl"
      :style="{ width: '100%', height: '100%' }"
      frameborder="0"
    ></iframe>
  </Dialog>
</template>
