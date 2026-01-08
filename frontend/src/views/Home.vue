<script setup>
import Breadcrumbs from "@/components/Breadcrumbs.vue";
import ColumnContentUser from "@/components/ColumnContentUser.vue";
import IconBase from "@/components/IconBase.vue";
import { navigationTree, user } from "@/main";
import getCreateRecentEventStore from "@/stores/recentEventStore.js";
import DataTable from "primevue/datatable";
import { useToast } from "primevue/usetoast";
import { onMounted, ref } from "vue";

// Others
const toast = useToast();

// Main store
let store = ref({ items: [] });
// Used 'local' selectedOwnRecords variable rather than
// store.selectedOwnRecords because changes in the latter
// do not trigger a re-rendering of the icon for the
// All/Own toggle button
const selectedOwnRecords = ref(false);

// Table
const loadingTable = ref(true);

// Breadcrumbs
const breadCrumbItems = ref([
  {
    icon: "pi pi-home",
    label: "Recent events"
  }
]);

// Load table data
const loadTable = async () => {
  try {
    loadingTable.value = true;
    store.value = getCreateRecentEventStore();
    if (store.value.itemCount === 0) {
      await store.value.getItems();
    }
    // Set value of selectedOwnRecords to decide which
    // user icon to show
    selectedOwnRecords.value = store.value.selectedOwnRecords;
  } catch (error) {
    toast.add({
      severity: "error",
      summary: "Error",
      detail: error,
      life: 3000
    });
  } finally {
    loadingTable.value = false;
  }
};

// Get Icon name from content type ID
const getIconName = (contentTypeId) => {
  const model = navigationTree.find((model) => model.id == contentTypeId);
  return `Icon${model.app_label.charAt(0).toUpperCase() + model.app_label.slice(1)}${model.model_class_name}`;
};

// Sync records
const syncRecords = async (clickEvent, toggleAllOwnRecords) => {
  loadingTable.value = true;
  try {
    await store.value.getItems(
      toggleAllOwnRecords
        ? selectedOwnRecords.value
          ? null
          : user
        : selectedOwnRecords.value
          ? user
          : null
    );
    selectedOwnRecords.value = toggleAllOwnRecords
      ? !selectedOwnRecords.value
      : selectedOwnRecords.value;
    store.value.selectedOwnRecords = selectedOwnRecords.value;
  } catch (error) {
    toast.add({
      severity: "error",
      summary: "Error",
      detail: error,
      life: 3000
    });
  } finally {
    loadingTable.value = false;
  }
};

// Main
onMounted(async () => {
  await loadTable();
});
</script>

<template>
  <div class="grid grid-cols-12 gap-x-4">
    <div class="col-span-11" style="height: calc(100vh - 8rem)">
      <DataTable
        :value="store.items"
        :totalRecords="store.itemCount"
        :loading="loadingTable"
        resizableColumns
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
        rowGroupMode="subheader"
        groupRowsBy="content_type"
      >
        <!-- Table header -->
        <template #header>
          <div>
            <Breadcrumbs :items="breadCrumbItems" />
          </div>
        </template>

        <!-- If empty -->
        <template #empty> No recent events. </template>

        <!-- columns -->
        <Column field="id" header="ID">
          <template #body="row">
            <Button variant="link" style="padding: 0">
              <RouterLink :to="`${row.data.model.path}/${row.data.id}`">
                {{ row.data.id }}
              </RouterLink>
            </Button>
          </template>
        </Column>

        <Column field="representation" header="Name"></Column>

        <Column field="change_message" header="Event">
          <template #body="row">
            <span v-if="row.data.action_flag == 1"
              ><i class="pi pi-plus" v-tooltip="'Added'"></i
            ></span>
            <span v-else-if="row.data.action_flag == 2"
              ><i class="pi pi-wave-pulse" v-tooltip="'Changed'"></i
            ></span>
            <span v-else-if="row.data.action_flag == 3"
              ><i class="pi pi-minus" v-tooltip="'Deleted'"></i
            ></span>
          </template>
        </Column>
        <Column field="user" header="User">
          <template #body="row">
            <ColumnContentUser
              :row="row"
              :model="row.data.model"
            ></ColumnContentUser>
          </template>
        </Column>

        <Column field="action_time" header="Timestamp">
          <template #body="row">
            <span>{{ new Date(row.data.action_time).toLocaleString() }}</span>
          </template>
        </Column>

        <Column field="content_type" header="Category"></Column>

        <template #groupheader="groupProps">
          <Button variant="link" style="padding: 0">
            <RouterLink
              class="flex flex-nowrap flex-none items-center gap-2"
              :to="
                navigationTree.find(
                  (model) => model.id == groupProps.data.content_type
                ).path
              "
            >
              <IconBase>
                <component :is="getIconName(groupProps.data.content_type)" />
              </IconBase>
              <span
                style="font-size: larger"
                v-html="
                  navigationTree.find(
                    (model) => model.id == groupProps.data.content_type
                  ).model_verbose_plural
                "
              >
              </span>
            </RouterLink>
          </Button>
        </template>
      </DataTable>
    </div>
    <div>
      <div
        class="flex flex-col h-screen items-start justify-start gap-2"
        style="height: calc(100vh - 8rem)"
      >
        <!-- Refresh -->
        <Button
          v-tooltip="'Refresh'"
          icon="pi pi-refresh"
          rounded
          raised
          @click="syncRecords(clickEvent, false)"
        />

        <!-- My records -->
        <Button
          v-tooltip="'All ⇄ Own'"
          :icon="selectedOwnRecords ? 'pi pi-user' : 'pi pi-asterisk'"
          rounded
          raised
          @click="syncRecords(clickEvent, true)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
::v-deep(.p-datatable-row-group-header) {
  background-color: var(--p-datatable-row-striped-background) !important;
}
</style>
