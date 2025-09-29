import { defineStore } from "pinia";
import axios from "axios";
import { ref } from "vue";
import { storeMap } from "@/stores/index.js";
import { navigationTree } from "@/main";
import { getNavigationModel } from "@/router/navigation";

export const getCreateModelStore = (appLabel, modelName) => {
  const model = getNavigationModel(navigationTree, appLabel, modelName);
  const storeName = `${model.app_label}-${model.model_class_name.toLowerCase()}`;

  if (storeMap.has(storeName)) {
    return storeMap.get(storeName);
  } else {
    let store = defineStore(storeName, {
      state: () => ({
        storeName: storeName,
        model: model,
        apiEndpoint: `/api/${model.app_label}/${model.model_class_name.toLowerCase()}`,
        iconName: `Icon${model.app_label.charAt(0).toUpperCase() + model.app_label.slice(1)}${model.model_class_name}`,
        currentPage: ref(1),
        pageCount: ref(0),
        itemsPerPage: ref(25),
        itemCount: ref(0),
        items: ref([]),
        lastFetchedItem: ref({ id: 0 }),
        itemHistory: ref({})
      }),
      actions: {
        async getItems(
          currentPage = this.currentPage,
          itemsPerPage = this.itemsPerPage
        ) {
          this.currentPage = currentPage;
          this.itemsPerPage = itemsPerPage;
          try {
            const response = await axios.get(`${this.apiEndpoint}/`, {
              params: { page: this.currentPage, limit: this.itemsPerPage }
            });
            const data = response.data;
            this.items = data.results;
            this.itemCount = data.count;
            this.pageCount = Math.floor(this.itemCount / this.itemsPerPage);
          } catch (error) {
            console.error(error);
            throw error;
          }
        },

        async getListViewFields() {
          try {
            const response = await axios.get(
              `/api/navigation/${this.model.id}/listview_fields/`
            );
            this.model.listview_fields_frozen = response.data[0];
            this.model.listview_fields = response.data[1];
          } catch (error) {
            console.log(error);
            throw error;
          }
        },

        async getChangeViewFields() {
          try {
            const response = await axios.get(
              `/api/navigation/${this.model.id}/changeview_fields/`
            );
            this.model.changeview_fields = response.data;
          } catch (error) {
            console.log(error);
            throw error;
          }
        },
        async getActions() {
          try {
            const response = await axios.get(
              `/api/navigation/${this.model.id}/action_list/`
            );
            this.model.actions = response.data;
          } catch (error) {
            console.log(error);
            throw error;
          }
        },

        async submitAction(actionName, selectedItemsIds) {
          try {
            // https://stackoverflow.com/questions/41938718
            // Download the file with Axios as a responseType: 'blob'
            const response = await axios.get(
              `/api/navigation/${this.model.id}/action/`,
              {
                params: { action_name: actionName, id: selectedItemsIds },
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
            console.log(error);
            throw error;
          }
        },

        async getItem(id) {
          try {
            const response = await axios.get(`${this.apiEndpoint}/${id}/`);
            this.lastFetchedItem = response.data;
            await this.getItemReadOnlyFields();
            return response.data;
          } catch (error) {
            console.log(error);
            throw error;
          }
        },

        async getItemReadOnlyFields() {
          try {
            const response = await axios.get(
              `${this.apiEndpoint}/${this.lastFetchedItem.id}/readonly_fields/`
            );
            this.model.readonly_fields = response.data;
          } catch (error) {
            console.log(error);
            throw error;
          }
        },

        async getItemHistory() {
          try {
            const response = await axios.get(
              `${this.apiEndpoint}/${this.lastFetchedItem.id}/history/`
            );
            this.itemHistory = response.data;
            return response.data;
          } catch (error) {
            console.log(error);
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
            console.log(error);
            throw error;
          }
        },
        async saveItem(payload) {
          try {
            await axios.put(
              `${this.apiEndpoint}/${this.lastFetchedItem.id}/`,
              payload
            );
          } catch (error) {
            console.log(error);
            throw error;
          }
        }
      }
    });
    return store();
  }
};

export default getCreateModelStore;
