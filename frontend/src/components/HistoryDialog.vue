<script setup>
import Breadcrumbs from "@/components/Breadcrumbs.vue";
import { computed } from "vue";

const props = defineProps({
  breadcrumbItems: {
    type: Array,
    default: () => [{ label: "History" }]
  },
  visible: {
    type: Boolean,
    default: false
  },
  history: {
    type: Object,
    default: () => ({})
  },
  loading: {
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

    <DataTable
      :value="history"
      rowGroupMode="rowspan"
      :groupRowsBy="['timestamp', '_grouper_activity_user']"
      sortMode="single"
      sortField="timestamp"
      :sortOrder="-1"
      :loading
      columnResizeMode="fit"
      showGridlines
      tableStyle="min-width: 50rem"
      scrollable
      scrollHeight="flex"
      :pt="{
        column: {
          headerCell: {
            class: ['bb-table-header-titles']
          }
        }
      }"
    >
      <Column field="timestamp" header="Timestamp">
        <template #body="row">
          {{ new Date(row.data.timestamp).toLocaleString() }}
        </template>
      </Column>

      <Column field="_grouper_activity_user" header="User">
        <template #body="row">
          {{ row.data.activity_user_pretty }}
        </template>
      </Column>

      <Column
        field="_grouper_activity_user"
        header="Activity"
        class="first-letter-capital"
      >
        <template #body="row">
          {{ row.data.activity_type }}
        </template>
      </Column>

      <Column
        field="field_name_verbose"
        header="Field"
        class="first-letter-capital"
      ></Column>

      <Column field="old_value" header="Old">
        <template #body="row">
          <div v-html="row.data.old_value"></div>
        </template>
      </Column>

      <Column field="new_value" header="New">
        <template #body="row">
          <div v-html="row.data.new_value"></div>
        </template>
      </Column>
    </DataTable>
  </Dialog>
</template>
