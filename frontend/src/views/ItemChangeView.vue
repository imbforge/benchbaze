<script setup>
import Breadcrumbs from "@/components/Breadcrumbs.vue";
import HistoryDialog from "@/components/HistoryDialog.vue";
import getCreateModelStore from "@/stores/modelStore.js";

import { getStore } from "@/stores/index.js";
import { Form } from "@primevue/forms";

import { useToast } from "primevue/usetoast";
import { onMounted, ref, useTemplateRef } from "vue";
import { useRoute, useRouter } from "vue-router";

// Set route details and get model
const router = useRouter();
const route = useRoute();
const appLabel = ref(route.params.appLabel);
const modelName = ref(route.params.modelName);

// Other variables
let store = ref({ currentPage: 0, pageCount: 0 });
const changeFormName = `change-form-${modelName.value}`;
const changeForm = useTemplateRef(changeFormName);
const initialData = ref({});
const mainBreadcrumbsItems = ref([]);
const isFormDisabled = ref(true);
const editDisabled = ref(true);
const showInfoSheetDialog = ref(false);
const showHistoryDialog = ref(false);
const history = ref();
const historyLoading = ref(false);
const historyBreadcrumbsItems = ref([]);
const modelIconName = ref();
const changeViewFieldSets = ref([
  { name: null, fields: [{ name: null, type: null, verbose_name: null }] }
]);
const readonlyFields = ref([]);
const hiddenFields = ref([]);

const toast = useToast();

const loadItem = async () => {
  store.value = getCreateModelStore(appLabel.value, modelName.value);
  try {
    // Load fields and item
    let promises = [];
    if (store.value.model.changeview_fields.length === 0) {
      promises.push(store.value.getChangeViewFields());
    }
    if (store.value.lastFetchedItem.id != route.params.id) {
      promises.push(store.value.getItem(route.params.id));
    }
    await Promise.all(promises);
    changeViewFieldSets.value = store.value.model.changeview_fields;
    readonlyFields.value = store.value.model.readonly_fields;
    modelIconName.value = store.value.iconName;

    //Breadcrumbs
    mainBreadcrumbsItems.value = [
      { icon: "pi pi-home" },
      { label: store.value.model.app_verbose_name },
      {
        icon: modelIconName.value,
        label: store.value.model.model_verbose_plural
      },
      {
        label: `${store.value.lastFetchedItem.id} - ${store.value.lastFetchedItem.name}`
      }
    ];

    // Edit button
    editDisabled.value = changeViewFieldSets.value
      .map((fieldset) => fieldset.fields)
      .map((field) => field.name)
      .every((fieldName) => readonlyFields.value.includes(fieldName));
  } catch (error) {
    console.error(error);
    toast.add({
      severity: "error",
      summary: "Error",
      detail: error,
      life: 3000
    });
  }
};

const setHistory = async () => {
  try {
    history.value = await store.value.getItemHistoryGrouped();
    historyBreadcrumbsItems.value = mainBreadcrumbsItems.value.map((b) => {
      return { ...b };
    });
    historyBreadcrumbsItems.value.push({ label: "History" });
  } catch (error) {
    toast.add({
      severity: "error",
      summary: "Error",
      detail: error,
      life: 3000
    });
  } finally {
    historyLoading.value = false;
  }
};

function toggleIsFormDisabled() {
  isFormDisabled.value = !isFormDisabled.value;
}

const toggleInfoSheetDialog = () => {
  showInfoSheetDialog.value = true;
};

const toggleHistoryDialog = () => {
  showHistoryDialog.value = true;
  historyLoading.value = true;
  setHistory();
};

const onFormSubmit = (event) => {
  const payload = event.values;
  console.log(payload);
  const saveItem = async () => {
    try {
      await store.value.saveItem(payload);
      toast.add({
        severity: "success",
        summary: "Success",
        detail: `The ${store.value.model.model_verbose_name} was saved`,
        life: 3000
      });
    } catch (error) {
      toast.add({
        severity: "error",
        summary: "Error",
        detail: error,
        life: 3000
      });
    }
  };
  // saveItem();
};

const onClickSave = () => {
  changeForm.value.submit();
};

async function onUpload() {}

const toLocaleDateTimeString = (fieldName) => {
  let value = store.value.lastFetchedItem[fieldName];
  let dateTime = value ? new Date(value) : value;
  changeForm.value.setFieldValue(
    fieldName,
    dateTime
      ? `${dateTime.toLocaleDateString()} ${dateTime.toLocaleTimeString()}`
      : value
  );
};

const hideField = async (fieldName) => {
  let value = await store.value.lastFetchedItem[fieldName];
  return value ? true : false;
};

const goUpNavigation = () => {
  var upperPath = route.path.split("/");
  if (upperPath.length > 2) {
    upperPath.splice(upperPath.length - 1);
    router.push(upperPath.join("/"));
  } else {
    router.push("/");
  }
};

const getRelatedModelOptions = (field) => {
  const relatedStore = ref(
    getStore(field.related_model.app_label, field.related_model.model_name)
  );
  const fieldValue = store.value.lastFetchedItem[field.name];
  relatedStore.value.getItems([fieldValue]);
  const obj = relatedStore.value.findItemById(fieldValue);
  if (obj) {
    return [{ id: obj.id, name: obj.representation }];
  }
};

onMounted(async () => {
  await loadItem();
  // Initial values must be set using setValues and not via initialValues,
  // https://github.com/primefaces/primevue/issues/6801
  changeForm.value.setValues(store.value.lastFetchedItem);
  hiddenFields.value = Object.keys(store.value.lastFetchedItem).filter(
    (key) => !store.value.lastFetchedItem[key]
  );
});
</script>

<template>
  <div class="grid grid-cols-12 gap-x-4">
    <div class="col-span-11" style="height: calc(100vh - 8rem)">
      <Card>
        <template #title>
          <Breadcrumbs :items="mainBreadcrumbsItems" />
        </template>

        <template #content>
          <Form
            :ref="changeFormName"
            v-slot="$form"
            @submit="onFormSubmit"
            class="flex flex-col gap-4 md:w-3/4 sm:w-full"
          >
            <!-- Loop through fieldsets  -->
            <div v-for="fieldSet in changeViewFieldSets">
              <!-- Fieldsets without title  -->
              <div
                v-if="!fieldSet.name"
                v-for="field in fieldSet.fields"
                v-show="!hiddenFields.includes(field.name) || !isFormDisabled"
                class="py-2"
              >
                <FloatLabel variant="on">
                  <InputText
                    v-if="field.type === 'CharField'"
                    :name="field.name"
                    type="text"
                    fluid
                    :disabled="
                      readonlyFields.includes(field.name)
                        ? true
                        : isFormDisabled
                    "
                  />

                  <Textarea
                    v-else-if="field.type === 'TextField'"
                    :name="field.name"
                    rows="5"
                    fluid
                    :disabled="
                      readonlyFields.includes(field.name)
                        ? true
                        : isFormDisabled
                    "
                  />

                  <div
                    v-else-if="field.type === 'BooleanField'"
                    class="flex items-center gap-2"
                  >
                    <label :for="field.name">{{ field.verbose_name }}?</label>
                    <Checkbox
                      v-if="!readonlyFields.includes(field.name)"
                      :name="field.name"
                      binary
                      :disabled="
                        readonlyFields.includes(field.name)
                          ? true
                          : isFormDisabled
                      "
                    />
                    <i v-else class="pi"></i>
                  </div>

                  <InputText
                    v-else-if="
                      field.type === 'DateTimeField' &&
                      readonlyFields.includes(field.name)
                    "
                    :name="field.name"
                    type="text"
                    fluid
                    :disabled="
                      readonlyFields.includes(field.name)
                        ? true
                        : isFormDisabled
                    "
                    :modelValue="toLocaleDateTimeString(field.name)"
                  />

                  <InputText
                    v-else="field.type === 'CharField'"
                    :name="field.name"
                    type="text"
                    fluid
                    :disabled="
                      readonlyFields.includes(field.name)
                        ? true
                        : isFormDisabled
                    "
                  />

                  <label
                    v-if="field.type !== 'BooleanField'"
                    :for="field.name"
                    >{{ field.verbose_name }}</label
                  >
                </FloatLabel>
              </div>

              <!-- Fieldsets with title  -->
              <Fieldset
                v-else
                :legend="fieldSet.name"
                :toggleable="true"
                :collapsed="true"
              >
                <div v-for="field in fieldSet.fields" class="p-2">
                  <FloatLabel variant="on">
                    <DatePicker
                      v-if="
                        field.type === 'DateTimeField' &&
                        readonlyFields.includes(field.name)
                      "
                      :name="field.name"
                      fluid
                      :disabled="
                        readonlyFields.includes(field.name)
                          ? true
                          : isFormDisabled
                      "
                      dateFormat="dd/mm/yy hh"
                      showTime
                      hourFormat="24"
                    />

                    <Select
                      v-else-if="'related_model' in field"
                      :name="field.name"
                      fluid
                      optionLabel="name"
                      optionValue="id"
                      :disabled="
                        readonlyFields.includes(field.name)
                          ? true
                          : isFormDisabled
                      "
                      :options="getRelatedModelOptions(field)"
                    >
                    </Select>

                    <InputText
                      v-else
                      :name="field.name"
                      type="text"
                      fluid
                      :disabled="
                        readonlyFields.includes(field.name)
                          ? true
                          : isFormDisabled
                      "
                    />

                    <label
                      v-if="field.type !== 'BooleanField'"
                      :for="field.name"
                      >{{ field.verbose_name }}</label
                    >
                  </FloatLabel>
                </div>
              </Fieldset>
            </div>

            <!-- <div class="flex items-center gap-2">
              <label for="info_sheet">Info sheet</label>
              <button v-if="initialData.info_sheet" @click="toggleInfoSheetDialog()" type="button">
                <i class="pi pi-file-pdf"></i>
              </button>
              <FileUpload v-if="!isFormDisabled" mode="basic" name="info_sheet" url="/api/upload" :maxFileSize="1000000"
                @upload="onUpload()" :auto="true" chooseLabel="Upload" />
            </div>
            <div class="flex items-center gap-2">
              <label for="availability">Available?</label>
              <Checkbox name="availability" binary :disabled="isFormDisabled" />
            </div> -->
          </Form>
        </template>
      </Card>
    </div>

    <div>
      <div
        class="flex flex-col h-screen items-start justify-start gap-2"
        style="height: calc(100vh - 8rem)"
      >
        <Button
          v-tooltip="'List view'"
          icon="pi pi-list"
          rounded
          raised
          @click="goUpNavigation"
        />
        <Button
          v-tooltip="'Edit'"
          icon="pi pi-pencil"
          rounded
          raised
          @click="toggleIsFormDisabled"
          :disabled="editDisabled"
        />
        <Button
          v-tooltip="'Save'"
          icon="pi pi-save"
          rounded
          raised
          @click="onClickSave"
          :disabled="isFormDisabled"
        />
        <Button
          v-tooltip="'History'"
          icon="pi pi-history"
          rounded
          raised
          @click="toggleHistoryDialog"
        />
      </div>
    </div>
  </div>

  <!-- <PdfDialog v-model:visible="showInfoSheetDialog" :iframeUrl="initialData.info_sheet" :breadcrumbItems="['Info sheet']"
    :breadcrumbItems="prefixBreadcrumb">
    <component :is="modelIconName" />
  </PdfDialog> -->

  <HistoryDialog
    v-model:visible="showHistoryDialog"
    :history
    :loading="historyLoading"
    :breadcrumbItems="historyBreadcrumbsItems"
  >
  </HistoryDialog>
</template>

<style scoped>
::v-deep(.p-dialog-content) {
  height: 100%;
}

::v-deep(.p-card-title) {
  padding-bottom: 5px;
}

::v-deep(.p-inputtext:disabled) {
  color: var(--p-inputtext-color) !important;
}

::v-deep(.p-floatlabel:has(input.p-filled) label) {
  color: var(--primary-color) !important;
}
</style>
