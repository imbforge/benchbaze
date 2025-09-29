<script setup>
import Breadcrumbs from "@/components/Breadcrumbs.vue";
import HistoryDialog from "@/components/HistoryDialog.vue";
import PdfDialog from "@/components/IFrameDialog.vue";
import getCreateModelStore from "@/stores/modelStore.js";
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
const prefixBreadcrumb = ref({ modelName: null, id: null, name: null });
const isFormDisabled = ref(true);
const editDisabled = ref(true);
const showInfoSheetDialog = ref(false);
const showHistoryDialog = ref(false);
const history = ref();
const historyLoading = ref(false);
const modelIconName = ref();
const changeViewFields = ref([[null, { fields: [] }]]);
const readonlyFields = ref([]);
const hiddenFields = ref([]);

const toast = useToast();

const loadItem = async () => {
  store = getCreateModelStore(appLabel.value, modelName.value);
  try {
    let promises = [];
    if (store.model.changeview_fields.length === 0) {
      promises.push(store.getChangeViewFields());
    }
    if (store.lastFetchedItem.id != route.params.id) {
      promises.push(store.getItem(route.params.id));
    }
    await Promise.all(promises);
    changeViewFields.value = store.model.changeview_fields;
    readonlyFields.value = store.model.readonly_fields;
    modelIconName.value = store.iconName;
    prefixBreadcrumb.value = {
      modelName: modelName,
      id: store.lastFetchedItem.id,
      name: store.lastFetchedItem.name
    };
    editDisabled.value = changeViewFields.value
      .map((fieldset) => fieldset[1])
      .map((field) => field.name)
      .every((fieldName) => readonlyFields.value.includes(fieldName));
  } catch (error) {
    toast.add({
      severity: "contrast",
      summary: "Error",
      detail: error,
      life: 3000
    });
  }
};

onMounted(async () => {
  await loadItem();
  // Initial values must be set using setValues and not via initialValues,
  // https://github.com/primefaces/primevue/issues/6801
  changeForm.value.setValues(store.lastFetchedItem);
  hiddenFields.value = Object.keys(store.lastFetchedItem).filter(
    (key) => !store.lastFetchedItem[key]
  );
  console.log(hiddenFields.value);
});

const setHistory = async () => {
  try {
    history.value = await store.getItemHistoryGrouped();
  } catch (error) {
    toast.add({
      severity: "contrast",
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
  const saveItem = async () => {
    try {
      await store.saveItem(payload);
      toast.add({
        severity: "success",
        summary: "Success",
        detail: `The ${store.model.model_verbose_name} was saved`,
        life: 3000
      });
    } catch (error) {
      toast.add({
        severity: "contrast",
        summary: "Error",
        detail: error,
        life: 3000
      });
    }
  };
  saveItem();
};

const onClickSave = () => {
  changeForm.value.submit();
};

async function onUpload() {
  console.log(hello);
}

const toLocaleDateTimeString = async (fieldName) => {
  let value = await store.lastFetchedItem[fieldName];
  let dateTime = value ? new Date(value) : value;
  changeForm.value.setFieldValue(
    fieldName,
    dateTime
      ? `${dateTime.toLocaleDateString()} ${dateTime.toLocaleTimeString()}`
      : value
  );
};

const hideField = async (fieldName) => {
  let value = await store.lastFetchedItem[fieldName];
  return value ? true : false;
};
</script>

<template>
  <div class="grid grid-cols-12 gap-x-4">
    <div class="col-span-11" style="height: calc(100vh - 8rem)">
      <Card>
        <template #title>
          <div class="flex flex-wrap items-center gap-2">
            <IconBase>
              <component :is="modelIconName" />
            </IconBase>
            <Breadcrumbs :prefix="prefixBreadcrumb" />
          </div>
        </template>

        <template #content>
          <Form
            :ref="changeFormName"
            v-slot="$form"
            @submit="onFormSubmit"
            class="flex flex-col gap-4 md:w-3/4 sm:w-full"
          >
            <div
              v-for="field in changeViewFields[0][1]['fields']"
              v-show="!hiddenFields.includes(field.name) || !isFormDisabled"
            >
              <FloatLabel variant="on">
                <InputText
                  v-if="field.field_type === 'CharField'"
                  :name="field.name"
                  type="text"
                  fluid
                  :disabled="
                    readonlyFields.includes(field.name) ? true : isFormDisabled
                  "
                />

                <Textarea
                  v-else-if="field.field_type === 'TextField'"
                  :name="field.name"
                  rows="5"
                  fluid
                  :disabled="
                    readonlyFields.includes(field.name) ? true : isFormDisabled
                  "
                />

                <div
                  v-else-if="field.field_type === 'BooleanField'"
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
                    field.field_type === 'DateTimeField' &&
                    readonlyFields.includes(field.name)
                  "
                  :name="field.name"
                  type="text"
                  fluid
                  :disabled="
                    readonlyFields.includes(field.name) ? true : isFormDisabled
                  "
                  :modelValue="toLocaleDateTimeString(field.name)"
                />

                <InputText
                  v-else="field.field_type === 'CharField'"
                  :name="field.name"
                  type="text"
                  fluid
                  :disabled="
                    readonlyFields.includes(field.name) ? true : isFormDisabled
                  "
                />

                <label
                  v-if="field.field_type !== 'BooleanField'"
                  :for="field.name"
                  >{{ field.verbose_name }}</label
                >
              </FloatLabel>
            </div>

            <Fieldset
              v-for="fieldset in changeViewFields.slice(1)"
              :legend="fieldset[0]"
              :toggleable="true"
              :collapsed="true"
            >
              <div v-for="field in fieldset[1]['fields']" class="p-2">
                <FloatLabel variant="on">
                  <InputText
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
                    v-if="field.field_type !== 'BooleanField'"
                    :for="field.name"
                    >{{ field.verbose_name }}</label
                  >
                </FloatLabel>
              </div>
            </Fieldset>

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
          @click="router.back()"
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

  <PdfDialog
    v-model:visible="showInfoSheetDialog"
    :iframeUrl="initialData.info_sheet"
    :breadcrumbItems="['Info sheet']"
    :prefixBreadcrumb="prefixBreadcrumb"
  >
    <component :is="modelIconName" />
  </PdfDialog>

  <HistoryDialog
    v-model:visible="showHistoryDialog"
    :history
    :loading="historyLoading"
    :prefixBreadcrumb="prefixBreadcrumb"
  >
    <component :is="modelIconName" />
  </HistoryDialog>
</template>

<style>
.p-dialog-content {
  height: 100%;
}

.p-card-title {
  padding-bottom: 5px;
}

.first-letter-capital::first-letter {
  text-transform: uppercase;
}

.p-inputtext:disabled {
  color: var(--p-inputtext-color) !important;
}

.p-floatlabel:has(input.p-filled) label {
  color: var(--primary-color) !important;
}
</style>
