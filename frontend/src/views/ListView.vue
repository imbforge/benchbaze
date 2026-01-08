<script setup>
import Breadcrumbs from "@/components/Breadcrumbs.vue";
import ColumnContentUser from "@/components/ColumnContentUser.vue";
import IFrameDialog from "@/components/IFrameDialog.vue";
import { user } from "@/main";
import getCreateModelStore from "@/stores/modelStore.js";
import DjangoQL from "@/utils/djangoql-completion/src/index.js";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import { useToast } from "primevue/usetoast";
import { onMounted, ref, toRaw } from "vue";
import { onBeforeRouteUpdate, useRoute } from "vue-router";

// ROUTER
const route = useRoute();
const appLabel = ref(route.params.appLabel);
const modelName = ref(route.params.modelName);

// OTHERS
const showMyItemsButton = ref(false);
const toast = useToast();
const mainBreadcrumbsItems = ref([]);

// STORE
const store = ref(getCreateModelStore("empty", "model"));
const storeDataKey = ref("id");
const modelIconName = ref();
const selectedOwnRecords = ref(false);

const changePage = async (direction) => {
  let pageNumber = 0;

  if (direction === "next") {
    pageNumber = store.value.paginationOpts.currentPage + 1;
  } else if (direction === "previous") {
    pageNumber = store.value.paginationOpts.currentPage - 1;
  } else if (direction === "first") {
    pageNumber = 1;
  } else if (direction === "last") {
    pageNumber = store.value.paginationOpts.pageCount;
  }

  loadingTable.value = true;
  try {
    await store.value.getItems(pageNumber);
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

// TABLE
const loadingTable = ref(true);
const listViewFields = ref([]);
const selectedItems = ref([]);
const allRowsSelected = ref(false);
const selectAllCheckboxValue = ref(false);
const showSelectAllCheckbox = ref(false);

const loadTable = async (routeQuery) => {
  try {
    loadingTable.value = true;

    // Get store
    store.value = getCreateModelStore(appLabel.value, modelName.value);

    let promises = [];

    // Load fields for list view
    if (store.value.model.listview_fields.length === 0) {
      promises.push(store.value.getListViewFields());
    }

    // If store is brand-new, check GET parameters and
    // load items accordingly
    if (store.value.virgin) {
      const currentPage =
        routeQuery.page || store.value.paginationOpts.currentPage;
      const searchQuery = routeQuery.search || store.value.searchOpts.query;
      searchAdvancedEnabled.value =
        "q" in routeQuery ? true : store.value.searchOpts.advancedEnabled;
      // // Check if only own records are to be shown
      if (
        searchAdvancedEnabled.value &&
        searchQuery.includes(`created_by.email = "${user.email}"`)
      ) {
        store.value.searchOpts.ownRecords = true;
      }
      store.value.searchOpts.advancedEnabled = searchAdvancedEnabled.value;
      promises.push(store.value.getItems(currentPage, searchQuery));
    }

    // Trigger all promises
    await Promise.all(promises);

    // Get gotten list view fields and icon name
    listViewFields.value = store.value.model.listview_fields;
    modelIconName.value = store.value.api.iconName;

    //Breadcrumbs
    mainBreadcrumbsItems.value = [
      { icon: "pi pi-home" },
      { label: store.value.model.app_verbose_name },
      {
        icon: modelIconName.value,
        label: store.value.model.model_verbose_plural
      }
    ];

    // Show All/Own button, if created_by is in listViewFields
    showMyItemsButton.value = listViewFields.value
      .map((e) => e.name)
      .includes("created_by");

    // Set value of selectedOwnRecords and relative icon to show
    selectedOwnRecords.value = store.value.searchOpts.ownRecords;
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

// ACTIONS
const actionList = ref([]);
const menuAction = ref();

// Load actions
const loadActions = async () => {
  try {
    if (store.value.model.actions.length === 0) {
      await store.value.getActions();
    }
  } catch (error) {
    toast.add({
      severity: "error",
      summary: "Error",
      detail: error,
      life: 3000
    });
  } finally {
    actionList.value = [
      {
        label: "Actions",
        items: store.value.model.actions.map((a) => {
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

// Toggle the actions popup menu
const menuActionToggle = (event) => {
  menuAction.value.toggle(event);
};

const submitAction = async (actionName) => {
  loadingTable.value = true;
  try {
    if (selectedItems.value.length === 0) {
      throw new Error("No items selected");
    }
    await store.value.submitAction(
      actionName,
      selectAllCheckboxValue.value ? [0] : selectedItems.value.map((e) => e.id),
      selectAllCheckboxValue.value ? store.value.searchOpts.query : null
    );
  } catch (error) {
    console.error(error);
    toast.add({
      severity: "error",
      summary: "Error",
      detail: error,
      life: 3000
    });
  }
  loadingTable.value = false;
};

// If selection checkbox in header is clicked, select all rows
const selectAllRowsToggle = (event) => {
  const show = toRaw(event).checked;
  allRowsSelected.value = show;
  showSelectAllCheckbox.value = show;
  if (!show) {
    selectAllCheckboxValue.value = false;
  }
  selectedItems.value = allRowsSelected.value ? store.value.items : [];
};

// When unselecting even one row, uncheck header Select all (rows) checkbox
// also hide Select all checkbox in paginator
const rowUnselect = (event) => {
  if (allRowsSelected.value) {
    allRowsSelected.value = false;
    showSelectAllCheckbox.value = false;
    selectAllCheckboxValue.value = false;
  }
};

// DIALOG
const showDialog = ref(false);
const dialogUrl = ref();
const dialogBreadcrumbItems = ref([]);

const iframeDialogToggle = (item, field) => {
  // Copy mainBreadcrumbsItems before appending to it
  dialogBreadcrumbItems.value = mainBreadcrumbsItems.value.map((b) => {
    return { ...b };
  });
  dialogBreadcrumbItems.value.push({ label: item["representation"] });
  dialogBreadcrumbItems.value.push({ label: field.verbose_name });
  dialogUrl.value = item[field.name];

  // Special case for DNA maps
  if (dialogUrl.value.endsWith(".dna")) {
    dialogUrl.value = `/ove/?file_name=${dialogUrl.value}&title=${item[listViewFields.value[1].name]}&file_format=dna`;
  }
  showDialog.value = true;
};

// SEARCH
const djangoQL = ref();
const searchAdvancedEnabled = ref(false);
const loadDjangoQL = async () => {
  try {
    if (store.value.model.search_introspection.length === 0) {
      await store.value.getSearchIntrospection();
    }
  } catch (error) {
    toast.add({
      severity: "error",
      summary: "Error",
      detail: error,
      life: 3000
    });
  } finally {
    searchAdvancedEnabled.value = store.value.searchOpts.advancedEnabled;
    djangoQL.value = new DjangoQL({
      completionEnabled: store.value.searchOpts.advancedEnabled,
      introspections: store.value.model.search_introspection,
      selector: "textarea[name=djangoql-textarea]",
      autoResize: true,
      syntaxHelp: null,
      initValue: store.value.searchOpts.query,
      onSubmit: async function (textareaValue) {
        loadingTable.value = true;
        try {
          await store.value.search(textareaValue);
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
      }
    });
  }
};

// Toggle to switch between simple and advanced search
const advancedSearchToggle = async () => {
  searchAdvancedEnabled.value
    ? djangoQL.value.enableCompletion()
    : djangoQL.value.disableCompletion();
  store.value.searchOpts.advancedEnabled = searchAdvancedEnabled.value;
  if (djangoQL.value.textarea.value) {
    loadingTable.value = true;
    djangoQL.value.textarea.value = "";
    try {
      await store.value.search("");
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
  }
};

// Button to clear search
const clearSearch = async () => {
  if (djangoQL.value.textarea.value) {
    loadingTable.value = true;
    try {
      djangoQL.value.textarea.value = "";
      await djangoQL.value.options.onSubmit(djangoQL.value.textarea.value);
      selectedOwnRecords.value = false;
      store.value.searchOpts.ownRecords = selectedOwnRecords.value;
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
  }
};

// Toggle between own and all records
const allOwnRecordsToggle = async () => {
  loadingTable.value = true;
  try {
    let query = "";
    if (!store.value.searchOpts.ownRecords) {
      query = `created_by.email = "${user.email}"`;
    }
    store.value.searchOpts.advancedEnabled = !store.value.searchOpts.ownRecords;
    await store.value.getItems(null, query);
    djangoQL.value.textarea.value = query;
    selectedOwnRecords.value = !store.value.searchOpts.ownRecords;
    searchAdvancedEnabled.value = store.value.searchOpts.advancedEnabled;

    // Store value of selectedOwnRecords in store to remember
    // it value
    store.value.searchOpts.ownRecords = !store.value.searchOpts.ownRecords;
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

// Copy advanced search query to clipboard
const copyQueryURL = async () => {
  try {
    const urlParams = {};
    if (store.value.paginationOpts.currentPage > 1) {
      urlParams.page = store.value.paginationOpts.currentPage;
    }
    if (store.value.searchOpts.query) {
      urlParams.search = store.value.searchOpts.query;
    }
    if (store.value.searchOpts.advancedEnabled) {
      urlParams.q = "";
    }
    if (Object.keys(urlParams).length) {
      const url = new URL(location);
      Object.keys(urlParams).map((key) => {
        url.searchParams.set(key, urlParams[key]);
      });
      await navigator.clipboard.writeText(url);
      toast.add({
        severity: "success",
        summary: "Copied",
        detail: `Search query URL has been copied to the clipboard`,
        life: 3000
      });
    } else {
      toast.add({
        severity: "warn",
        summary: "Warning",
        detail: `No search query is set`,
        life: 3000
      });
    }
  } catch (error) {
    toast.add({
      severity: "error",
      summary: "Error",
      detail: error,
      life: 3000
    });
  }
};

// Main view mounting event
onMounted(async () => {
  await Promise.all([loadTable(route.query), loadActions(), loadDjangoQL()]);

  // Remove any query parameters from url
  if (Object.keys(route.query).length) {
    const url = new URL(location);
    Object.keys(route.query).map((key) => {
      url.searchParams.delete(key);
    });
    history.pushState({}, "", url);
  }
});

// Navigate between different models
onBeforeRouteUpdate(async (newRoute) => {
  appLabel.value = newRoute.params.appLabel;
  modelName.value = newRoute.params.modelName;
  allRowsSelected.value = false;
  selectedItems.value = [];
  selectAllCheckboxValue.value = false;
  showSelectAllCheckbox.value = false;
  await loadTable({});
  djangoQL.value.deleteCompletion();
  await loadDjangoQL();
  await loadActions();
});

const sortingFields = ref([]);
const sortItems = async () => {
  loadingTable.value = true;
  try {
    store.value.searchOpts.ordering = sortingFields.value.map(
      (e) => `${e.order == -1 ? "-" : ""}${e.field}`
    );
    await store.value.getItems();
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
</script>

<template>
  <div class="grid grid-cols-12 gap-x-4">
    <div class="col-span-11" style="height: calc(100vh - 8rem)">
      <DataTable
        :value="store.items"
        :dataKey="storeDataKey"
        :rows="store.paginationOpts.itemsPerPage"
        :totalRecords="store.paginationOpts.itemCount"
        v-model:selection="selectedItems"
        :selectAll="allRowsSelected"
        @select-all-change="selectAllRowsToggle"
        @row-unselect="rowUnselect"
        :loading="loadingTable"
        sortMode="multiple"
        removableSort
        @sort="sortItems"
        v-model:multiSortMeta="sortingFields"
        lazy
        resizableColumns
        paginator
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
        <!-- Empty slot -->
        <template #empty>
          <span>No records</span>
        </template>

        <!-- Table header -->
        <template #header>
          <div class="flex items-center justify-between gap-2">
            <!-- Breadcrumbs -->
            <Breadcrumbs :items="mainBreadcrumbsItems"></Breadcrumbs>

            <!-- Search -->
            <div class="relative md:w-1/2 sm:w-full sm:w-full">
              <Textarea
                :modelValue="store.searchOpts.query"
                name="djangoql-textarea"
                rows="1"
                class="bb-djangoql-textarea size-full"
              />
              <div
                class="absolute top-1/2 left-0 -translate-y-1/2 bb-search-icon pl-2"
              >
                <div class="flex items-center justify-between gap-2 pr-2">
                  <ToggleSwitch
                    v-model="searchAdvancedEnabled"
                    v-tooltip.left="'Simple ⇄ Advanced'"
                    @change="advancedSearchToggle"
                  />
                  <i
                    v-tooltip="'Search'"
                    :class="
                      searchAdvancedEnabled
                        ? 'pi pi-search-plus'
                        : 'pi pi-search'
                    "
                    @click="djangoQL.options.onSubmit(djangoQL.textarea.value)"
                    @dblclick="console.log('double')"
                  ></i>
                </div>
              </div>
              <div class="absolute top-1/2 right-0 -translate-y-1/2">
                <div class="flex items-center justify-between gap-2 pr-2">
                  <i
                    class="pi pi-times bb-search-icon"
                    v-tooltip="'Clear search'"
                    @click="clearSearch"
                  ></i>
                  <i
                    class="pi pi-copy bb-search-icon"
                    v-tooltip="'Copy search query as URL to clipboard'"
                    @click="copyQueryURL"
                  ></i>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- Table paginator -->
        <template #paginatorcontainer>
          <div class="static">
            <div
              class="absolute left-0 flex items-center gap-2 bb-select-all-checkbox"
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
                >Select all {{ store.paginationOpts.itemCount }}
                <span v-html="store.model.model_verbose_plural"></span
              ></label>
            </div>

            <div class="flex items-center justify-between">
              <Button
                icon="pi pi-angle-double-left"
                v-tooltip="'First'"
                rounded
                text
                @click="changePage('first')"
                :disabled="store.paginationOpts.currentPage === 1"
              />
              <Button
                icon="pi pi-angle-left"
                v-tooltip="'Previous'"
                rounded
                text
                @click="changePage('previous')"
                :disabled="store.paginationOpts.currentPage === 1"
              />
              <div
                class="text-color font-medium grid grid-rows-2 justify-items-center"
              >
                <span class="block"
                  >Page {{ store.paginationOpts.currentPage }} of
                  {{ store.paginationOpts.pageCount }}</span
                >
                <div>
                  {{ store.paginationOpts.itemCount }}
                  <span v-html="store.model.model_verbose_plural"></span>
                </div>
              </div>
              <Button
                icon="pi pi-angle-right"
                v-tooltip="'Next'"
                rounded
                text
                @click="changePage('next')"
                :disabled="
                  store.paginationOpts.currentPage ===
                  store.paginationOpts.pageCount
                "
              />
              <Button
                icon="pi pi-angle-double-right"
                v-tooltip="'Last'"
                rounded
                text
                @click="changePage('last')"
                :disabled="
                  store.paginationOpts.currentPage ===
                  store.paginationOpts.pageCount
                "
              />
            </div>

            <div></div>
          </div>
        </template>

        <!-- Column for selection -->
        <Column
          selectionMode="multiple"
          headerStyle="width: 3rem"
          frozen
        ></Column>

        <!-- All other columns -->
        <Column
          v-for="field in listViewFields"
          :field="field.name"
          :key="field.name"
          :header="field.verbose_name"
          :sortable="field.search"
          :frozen="field.frozen"
          :headerClass="`column-${appLabel}-${modelName}-${field.name}`"
          style="max-width: 30rem"
        >
          <template #body="row">
            <!-- Link column, should be first and ID -->
            <Button
              v-if="field.link"
              v-slot="slotProps"
              variant="link"
              style="padding: 0"
            >
              <RouterLink :to="row.data.path" :class="slotProps.class"
                >{{ row.data.id }}
              </RouterLink>
            </Button>

            <!-- FileField -->
            <button
              v-else-if="field.type === 'FileField'"
              @click="iframeDialogToggle(row.data, field)"
            >
              <i v-if="row.data[field.name]" class="pi pi-external-link"></i>
            </button>

            <!-- BooleanField -->
            <i
              v-else-if="field.type === 'BooleanField'"
              class="pi"
              :class="{
                'pi-check-circle text-green-500': row.data[field.name],
                'pi-times-circle text-red-400': !row.data[field.name]
              }"
            ></i>

            <!-- BooleanField -->
            <div
              v-else-if="field.type === 'ArrayField'"
              class="text-wrap truncate"
            >
              {{ row.data[field.name].join(", ") }}
            </div>

            <!-- Created by field -->
            <ColumnContentUser
              v-else-if="field.name === 'created_by'"
              :row="row"
              :model="store.model"
            >
            </ColumnContentUser>

            <!-- all other fields -->
            <div v-else class="text-wrap truncate">
              {{ row.data[field.name] }}
            </div>
          </template>
        </Column>
      </DataTable>
    </div>
    <div>
      <!-- Tools panel -->
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
          @click="changePage(0)"
        />

        <!-- My records -->
        <Transition name="bb-bounce">
          <Button
            v-tooltip="'All ⇄ Own'"
            :icon="selectedOwnRecords ? 'pi pi-user' : 'pi pi-asterisk'"
            rounded
            raised
            v-show="showMyItemsButton"
            @click="allOwnRecordsToggle"
          />
        </Transition>

        <!-- Add new -->
        <Button v-tooltip="'Add new'" icon="pi pi-plus" rounded raised />

        <!-- Actions -->
        <Button
          v-tooltip="'Actions'"
          icon="pi pi-sparkles"
          rounded
          raised
          @click="menuActionToggle"
          aria-haspopup="true"
          aria-controls="menuAction"
        />
        <Menu
          ref="menuAction"
          id="menuAction"
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

  <!-- Dialog for iFrame -->
  <IFrameDialog
    v-model:visible="showDialog"
    :iframeUrl="dialogUrl"
    :breadcrumbItems="dialogBreadcrumbItems"
  >
  </IFrameDialog>
</template>

<style src="@/utils/djangoql-completion/dist/completion.css"></style>

<style scoped>
:deep(.p-toggleswitch-slider) {
  height: 5px !important;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

:deep(.p-toggleswitch.p-toggleswitch-checked .p-toggleswitch-handle) {
  background: var(--p-toggleswitch-handle-checked-color) !important;
}

:deep(.p-toggleswitch.p-toggleswitch-checked .p-toggleswitch-slider) {
  background: var(--p-toggleswitch-background) !important;
}
</style>
