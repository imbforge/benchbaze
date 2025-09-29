<script setup>
import IconBase from "@/components/IconBase.vue";
import IFrameDialog from "@/components/IFrameDialog.vue";
import getCreateModelStore from "@/stores/modelStore.js";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import { useToast } from "primevue/usetoast";
import { ref, toRaw, watch } from "vue";
import { useRoute } from "vue-router";

// Router
const route = useRoute();
const appLabel = ref(route.params.appLabel);
const modelName = ref(route.params.modelName);

// Store
let store = ref({ currentPage: 0, pageCount: 0 });
const storeDataKey = ref("id");
const modelIconName = ref();

// Table
const loadingTable = ref(true);
const listViewFieldsFrozen = ref([{}]);
const listViewFields = ref([]);
const selectedItems = ref();
const allRowsSelected = ref(false);
const selectAllCheckboxValue = ref(false);
const showSelectAllCheckbox = ref(false);

// Dialog
const showDialog = ref(false);
const dialogUrl = ref();
const dialogTitle = ref();
const dialogBreadcrumbItems = ref([]);

// Actions
const actionList = ref([]);
const actionMenu = ref();

// Others
const showMyItemsButton = ref(false);
const toast = useToast();

// Load table
const loadTable = async () => {
  try {
    loadingTable.value = true;
    store = getCreateModelStore(appLabel.value, modelName.value);
    let promises = [];
    if (store.model.listview_fields_frozen.length === 0) {
      promises.push(store.getListViewFields());
    }
    if (store.itemCount === 0) {
      promises.push(store.getItems());
    }
    await Promise.all(promises);
    listViewFieldsFrozen.value = store.model.listview_fields_frozen;
    listViewFields.value = store.model.listview_fields;
    modelIconName.value = store.iconName;
    showMyItemsButton.value = listViewFields.value
      .map((e) => e.name)
      .includes("created_by");
  } catch (error) {
    toast.add({
      severity: "contrast",
      summary: "Error",
      detail: error,
      life: 3000
    });
  } finally {
    loadingTable.value = false;
  }
};
loadTable();

// Load actions
const loadActions = async () => {
  try {
    if (store.model.actions.length === 0) {
      await store.getActions();
    }
  } catch (error) {
    toast.add({
      severity: "contrast",
      summary: "Error",
      detail: error,
      life: 3000
    });
  } finally {
    actionList.value = [
      {
        label: "Actions",
        items: store.model.actions.map((a) => {
          return {
            label: a.label,
            icon: a.icon,
            command: () => {
              submitAction(a.name);
            }
          };
        })
      }
    ];
  }
};
loadActions();

// Reload table when the route's app label and model
// name change
watch(route, async (oldRoute, newRoute) => {
  appLabel.value = newRoute.params.appLabel;
  modelName.value = newRoute.params.modelName;
  allRowsSelected.value = false;
  selectedItems.value = null;
  selectAllCheckboxValue.value = false;
  showSelectAllCheckbox.value = false;
  loadTable();
  loadActions();
});

// Toggle iFrame dialog
const toggleIframeDialog = (item, field) => {
  showDialog.value = true;
  dialogUrl.value = item[field.name];
  dialogBreadcrumbItems.value = [field.verbose_name];
  dialogTitle.value = {
    modelName: modelName,
    id: item[listViewFieldsFrozen.value[0].name],
    name: item[listViewFieldsFrozen.value[1].name]
  };
};

// Table navigation
const refreshStore = async (pageOffset) => {
  loadingTable.value = true;
  try {
    await store.getItems(store.currentPage + pageOffset);
  } catch (error) {
    toast.add({
      severity: "contrast",
      summary: "Error",
      detail: error,
      life: 3000
    });
  }
  loadingTable.value = false;
};

const selectAllRowsToggle = (event) => {
  const show = toRaw(event).checked;
  allRowsSelected.value = show;
  showSelectAllCheckbox.value = show;
  selectedItems.value = allRowsSelected.value ? store.items : [];
};

// Actions
const toggleActionMenu = (event) => {
  actionMenu.value.toggle(event);
};

const submitAction = async (actionName) => {
  loadingTable.value = true;
  try {
    await store.submitAction(
      actionName,
      selectAllCheckboxValue.value ? [0] : selectedItems.value.map((e) => e.id)
    );
  } catch (error) {
    toast.add({
      severity: "contrast",
      summary: "Error",
      detail: error,
      life: 3000
    });
  }
  loadingTable.value = false;
};
</script>

<template>
  <div class="grid grid-cols-12 gap-x-4">
    <div class="col-span-11" style="height: calc(100vh - 8rem)">
      <DataTable
        :value="store.items"
        :dataKey="storeDataKey"
        :rows="store.itemsPerPage"
        :totalRecords="store.itemCount"
        :selection="selectedItems"
        :selectAll="allRowsSelected"
        @select-all-change="selectAllRowsToggle"
        :loading="loadingTable"
        removableSort
        lazy
        resizableColumns
        paginator
        columnResizeMode="fit"
        showGridlines
        tableStyle="min-width: 50rem"
        scrollable
        scrollHeight="flex"
        filterDisplay="menu"
        :pt="{
          column: {
            headerCell: {
              class: ['list-table-header']
            }
          }
        }"
      >
        <template #header>
          <div class="flex flex-nowrap items-center gap-2">
            <IconBase>
              <component :is="modelIconName" />
            </IconBase>
            <span
              v-html="store.model.model_verbose_plural"
              class="text-xl font-bold"
            ></span>
          </div>
        </template>

        <template #paginatorcontainer>
          <div class="static">
            <div
              class="absolute left-0 flex items-center gap-2 select-all-checkbox"
              v-show="showSelectAllCheckbox"
            >
              <Checkbox
                v-model="selectAllCheckboxValue"
                inputId="selectAllCheckbox"
                name="selectAllCheckbox"
                :binary="true"
                :defaultValue="'false'"
              />
              <label for="selectAllCheckbox"
                >Select all {{ store.itemCount }}
                <span v-html="store.model.model_verbose_plural"></span
              ></label>
            </div>
            <div class="flex items-center justify-between">
              <Button
                icon="pi pi-chevron-left"
                rounded
                text
                @click="refreshStore(-1)"
                :disabled="store.currentPage === 1"
              />
              <div
                class="text-color font-medium grid grid-rows-2 justify-items-center"
              >
                <span class="block"
                  >Page {{ store.currentPage }} of {{ store.pageCount }}</span
                >
                <div>
                  {{ store.itemCount }}
                  <span v-html="store.model.model_verbose_plural"></span>
                </div>
              </div>
              <Button
                icon="pi pi-chevron-right"
                rounded
                text
                @click="refreshStore(1)"
                :disabled="store.currentPage === store.pageCount"
              />
            </div>
            <div></div>
          </div>
        </template>

        <Column
          selectionMode="multiple"
          headerStyle="width: 3rem"
          frozen
        ></Column>

        <Column
          v-for="(field, index) in listViewFieldsFrozen"
          :field="field.name"
          :key="field.name"
          sortable
          frozen
          :header="field.verbose_name"
          :headerClass="`column-${appLabel}-${modelName}-${field.name}`"
        >
          <template v-if="index === 0" #body="row">
            <Button v-slot="slotProps" variant="link" style="padding: 0">
              <RouterLink
                :to="`/${appLabel}/${modelName}/${row.data.id}`"
                :class="slotProps.class"
                >{{ row.data.id }}
              </RouterLink>
            </Button>
          </template>
        </Column>

        <Column
          v-for="field in listViewFields"
          :field="field.name"
          :key="field.name"
          :header="field.verbose_name"
          :headerClass="`column-${appLabel}-${modelName}-${field.name}`"
          style="max-width: 30rem"
        >
          <template #body="row">
            <button
              v-if="field.field_type === 'FileField' && row.data.info_sheet"
              @click="toggleIframeDialog(row.data, field)"
            >
              <i
                v-if="row.data.info_sheet.endsWith('.pdf')"
                class="pi pi-file-pdf"
              ></i>
              <i v-else class="pi pi-file"></i>
            </button>

            <i
              v-else-if="field.field_type === 'BooleanField'"
              class="pi"
              :class="{
                'pi-check-circle text-green-500': row.data[field.name],
                'pi-times-circle text-red-400': !row.data[field.name]
              }"
            ></i>

            <div v-else class="text-wrap truncate">
              {{ row.data[field.name] }}
            </div>
          </template>
        </Column>
      </DataTable>
    </div>
    <div>
      <div
        class="flex flex-col h-screen items-start justify-start gap-2"
        style="height: calc(100vh - 8rem)"
      >
        <Button
          v-tooltip="'Search'"
          type="button"
          icon="pi pi-search"
          rounded
          raised
          v-styleclass="{
            selector: '@next',
            enterFromClass: 'hidden',
            enterActiveClass: 'animate-scalein',
            leaveToClass: 'hidden',
            leaveActiveClass: 'animate-fadeout',
            hideOnOutsideClick: true
          }"
        />
        <Button
          v-tooltip="'Refresh'"
          icon="pi pi-refresh"
          rounded
          raised
          @click="refreshStore(0)"
        />
        <Button
          v-tooltip="`My ${store.model.model_verbose_plural}`"
          icon="pi pi-user"
          rounded
          raised
          v-show="showMyItemsButton"
        />
        <Button
          v-tooltip="`Add new ${store.model.model_verbose_name}`"
          icon="pi pi-plus"
          rounded
          raised
        />
        <Button
          v-tooltip="'Actions'"
          icon="pi pi-sparkles"
          rounded
          raised
          @click="toggleActionMenu"
          aria-haspopup="true"
          aria-controls="overlay_menu"
        />
        <Menu
          ref="actionMenu"
          id="overlay_menu"
          :model="actionList"
          :popup="true"
        >
          <template #item="{ item, props }">
            <a v-ripple class="flex items-center" v-bind="props.action">
              <span :class="item.icon" />
              <span>{{ item.label }}</span>
              <Badge v-if="item.badge" class="ml-auto" :value="item.badge" />
              <span
                v-if="item.shortcut"
                class="ml-auto border border-surface rounded bg-emphasis text-muted-color text-xs p-1"
                >{{ item.shortcut }}</span
              >
            </a>
          </template>
        </Menu>
      </div>
    </div>
  </div>

  <IFrameDialog
    v-model:visible="showDialog"
    :iframeUrl="dialogUrl"
    :breadcrumbItems="dialogBreadcrumbItems"
    :prefixBreadcrumb="dialogTitle"
  >
    <component :is="modelIconName" />
  </IFrameDialog>
</template>

<style>
.p-datatable-header {
  border-top-left-radius: var(--content-border-radius);
  border-top-right-radius: var(--content-border-radius);
}

.p-paginator,
.p-datatable-paginator-bottom {
  border-radius: 0 0 var(--content-border-radius) var(--content-border-radius) !important;
}

.rounded-icon {
  font-size: 8px;
  color: white;
  border-radius: 50%;
  padding: 3px;
  display: inline-block;
  text-align: center;
}

.p-dialog-content {
  height: 100%;
}

.first-letter-capital::first-letter {
  text-transform: uppercase;
}

.select-all-checkbox {
  padding: var(--p-datatable-body-cell-padding);
}

.list-table-header {
  font-weight: bold;
  text-transform: uppercase;
  font-size: 12px;
}
</style>
