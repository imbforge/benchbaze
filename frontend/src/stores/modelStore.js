import { defineStore } from "pinia";
import axios from "axios";
import { ref } from "vue";
import { storeMap } from "@/stores/index.js";
import { navigationTree } from "@/main";
import { getNavigationModel } from "@/router/navigation";
import getCreateUserStore from "@/stores/userStore.js";

const userStore = getCreateUserStore();

// List of model properties that will be set later
// but should be initialized as empty arrays
const modelInitEmptyProps = [
  "listview_fields_frozen",
  "listview_fields",
  "addview_fields",
  "changeview_fields",
  "readonly_fields",
  "actions",
  "search_introspection"
];

export const getCreateModelStore = (appLabel, modelName) => {
  const model = getNavigationModel(navigationTree, appLabel, modelName);
  const storeName = `${model.app_label}-${model.model_class_name.toLowerCase()}`;

  if (storeMap.has(storeName)) {
    return storeMap.get(storeName);
  } else {
    // Initialize empty array properties
    modelInitEmptyProps.forEach((prop) => (model[prop] = []));
    let store = defineStore(storeName, {
      state: () => ({
        storeName: storeName,
        model: model,
        virgin: ref(true),
        api: {
          endpointMain: `/api/${model.app_label}/${model.model_class_name.toLowerCase()}`,
          endpointNavigation: `/api/navigation/${model.app_label}/${model.model_class_name.toLowerCase()}`,
          iconName: `Icon${model.app_label.charAt(0).toUpperCase() + model.app_label.slice(1)}${model.model_class_name}`
        },
        paginationOpts: ref({
          currentPage: 1,
          pageCount: 0,
          itemsPerPage: 25,
          itemCount: 0
        }),
        items: ref([]),
        lastFetchedItem: ref({ id: 0 }),
        itemHistory: ref({}),
        searchOpts: ref({
          advancedEnabled: false,
          query: "",
          ordering: [],
          ownRecords: false
        }),
        lastSynced: ref()
      }),
      actions: {
        async getItems(
          currentPage = this.paginationOpts.currentPage,
          searchQuery = this.searchOpts.query,
          itemsPerPage = this.paginationOpts.itemsPerPage,
          requestParams = {}
        ) {
          this.paginationOpts.currentPage =
            currentPage || this.paginationOpts.currentPage || 1;
          this.paginationOpts.itemsPerPage =
            itemsPerPage || this.paginationOpts.itemsPerPage;
          this.searchOpts.query =
            searchQuery === ""
              ? searchQuery
              : searchQuery || this.searchOpts.query;
          try {
            // Get data
            const response = await axios.get(`${this.api.endpointMain}/`, {
              params: {
                ...{
                  page: this.paginationOpts.currentPage,
                  limit: this.paginationOpts.itemsPerPage,
                  search: searchQuery
                },
                ...(this.searchOpts.advancedEnabled ? { q: "" } : {}),
                ...(this.searchOpts.ordering.length > 0
                  ? { ordering: this.searchOpts.ordering }
                  : {}),
                ...requestParams
              },
              paramsSerializer: {
                indexes: null
              }
            });
            const data = response.data.results;

            // If created_by is passed, get relevant users
            if (
              this.model.listview_fields
                .map((field) => field.name)
                .includes("created_by")
            ) {
              await userStore.getItems(data.map((item) => item.created_by));
              // Add user and path to each item
              data.forEach((item) => {
                item.user = userStore.items.find(
                  (user) => user.id == item.created_by
                );
              });
            }

            // Add path
            data.forEach((item) => {
              item.path = `/${this.model.app_label}/${this.model.model_class_name.toLowerCase()}/${item.id}`;
            });

            // Set relevant variables for the store
            this.items = data;
            this.paginationOpts.itemCount = response.data.count;
            this.paginationOpts.pageCount = Math.ceil(
              this.paginationOpts.itemCount / this.paginationOpts.itemsPerPage
            );
            if (this.paginationOpts.pageCount === 0) {
              this.paginationOpts.currentPage = 0;
            }
            this.lastSynced = new Date();
            this.virgin = false;
          } catch (error) {
            console.error(error);
            throw error;
          }
        },

        async search(textareaValue) {
          await this.getItems(1, textareaValue);
        },

        async getListViewFields() {
          try {
            const response = await axios.get(
              `${this.api.endpointNavigation}/listview_fields/`
            );
            this.model.listview_fields = response.data;
          } catch (error) {
            console.error(error);
            throw error;
          }
        },

        async getChangeViewFields() {
          try {
            const response = await axios.get(
              `${this.api.endpointNavigation}/changeview_fields/`
            );
            this.model.changeview_fields = response.data;
          } catch (error) {
            console.error(error);
            throw error;
          }
        },

        async getSearchIntrospection() {
          try {
            const response = await axios.get(
              `${this.api.endpointNavigation}/advanced_search_introspection/`
            );
            this.model.search_introspection = response.data;
          } catch (error) {
            console.error(error);
            throw error;
          }
        },

        async getActions() {
          try {
            const response = await axios.get(
              `${this.api.endpointNavigation}/action_list/`
            );
            this.model.actions = response.data;
          } catch (error) {
            console.error(error);
            throw error;
          }
        },

        async submitAction(actionName, selectedItemsIds, searchQuery) {
          try {
            // https://stackoverflow.com/questions/41938718
            // Download the file with Axios as a responseType: 'blob'
            const response = await axios.get(
              `${this.api.endpointNavigation}/action/`,
              {
                params: {
                  name: actionName,
                  id: selectedItemsIds,
                  search: searchQuery
                },
                paramsSerializer: {
                  indexes: null
                },
                responseType: "blob"
              }
            );
            // Get file name from response
            const fileName = response.headers["content-disposition"]
              .split('filename="')[1]
              .split(";")[0]
              .trim();
            // Create a file link using the blob in the response from Axios/Server
            const href = URL.createObjectURL(response.data);
            // Create <a> HTML element with a the href linked to the file link created in step 2 & click the link
            const link = document.createElement("a");
            link.href = href;
            link.setAttribute("download", fileName);
            document.body.appendChild(link);
            link.click();
            // Clean up the dynamically created file link and HTML element
            document.body.removeChild(link);
            URL.revokeObjectURL(href);
          } catch (error) {
            console.error(error);
            throw error;
          }
        },

        async getItem(id) {
          try {
            const response = await axios.get(`${this.api.endpointMain}/${id}/`);
            this.lastFetchedItem = response.data;
            await this.getItemReadOnlyFields();
            return response.data;
          } catch (error) {
            console.error(error);
            throw error;
          }
        },

        async getItemReadOnlyFields() {
          try {
            const response = await axios.get(
              `${this.api.endpointMain}/${this.lastFetchedItem.id}/readonly_fields/`
            );
            this.model.readonly_fields = response.data;
          } catch (error) {
            console.error(error);
            throw error;
          }
        },

        async getItemHistory() {
          try {
            const response = await axios.get(
              `${this.api.endpointMain}/${this.lastFetchedItem.id}/history/`
            );
            this.itemHistory = response.data;
            return response.data;
          } catch (error) {
            console.error(error);
            throw error;
          }
        },

        async getItemHistoryGrouped() {
          // Re-organize history to group field changes by record change
          // by setting  _grouper_activity_user

          try {
            const history = await this.getItemHistory();
            const createdRecord = history[0];
            const changedRecords = history
              .slice(1)
              .map((historyRecord, i) =>
                historyRecord.changes.map((fieldChange) => {
                  return {
                    timestamp: historyRecord.timestamp,
                    activity_user: historyRecord.activity_user,
                    _grouper_activity_user: i,
                    activity_user_pretty: historyRecord.activity_user_pretty,
                    activity_type: "changed",
                    field_name_verbose: fieldChange.field_name_verbose,
                    field_name: fieldChange.field_name,
                    new_value: fieldChange.new_value,
                    old_value: fieldChange.old_value
                  };
                })
              )
              .flat();

            return [...[createdRecord], ...changedRecords];
          } catch (error) {
            console.error(error);
            throw error;
          }
        },

        async saveItem(payload) {
          try {
            await axios.put(
              `${this.api.endpointMain}/${this.lastFetchedItem.id}/`,
              payload
            );
          } catch (error) {
            console.error(error);
            throw error;
          }
        }
      }
    });
    return store();
  }
};

export default getCreateModelStore;
