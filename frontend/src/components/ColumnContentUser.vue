<script setup>
import { ref } from "vue";

const props = defineProps({
  row: {
    type: Object,
    default: () => ({})
  },
  model: {
    type: Object,
    default: () => ({})
  }
});

const popOver = ref();
const baseUrl = ref();

const togglePopOver = (event) => {
  baseUrl.value = window.location.href;
  popOver.value.toggle(event);
};
</script>

<template>
  <Button
    variant="link"
    style="padding: 0"
    class="bb-user-column text-wrap truncate"
    @click="togglePopOver"
    >{{ row.data.user ? row.data.user.representation : "" }}</Button
  >
  <Popover ref="popOver">
    <div class="grid grid-cols-2 gap-1">
      <div class="font-bold">First name:</div>
      <div>
        {{ row.data.user.first_name }}
      </div>
      <div class="font-bold">Last name:</div>
      <div>
        {{ row.data.user.last_name }}
      </div>
      <div class="font-bold">Username:</div>
      <div>
        {{ row.data.user.username }}
      </div>
      <div v-if="row.data.user.is_active" class="font-bold">Email:</div>
      <a
        v-if="row.data.user.is_active"
        :href="
          `mailto:${row.data.user.email}?body=` +
          encodeURIComponent(
            `${model.model_verbose_name.replace(/<\/?[^>]+(>|$)/g, '')} ${row.data.representation}\n${baseUrl.replace(/\/$/, '')}/${row.data.id}`
          )
        "
        class="bb-user-column"
        >{{ row.data.user.email }}</a
      >
    </div>
  </Popover>
</template>
