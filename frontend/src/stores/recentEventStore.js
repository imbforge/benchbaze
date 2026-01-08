import { defineStore } from "pinia";
import axios from "axios";
import { ref } from "vue";
import { storeMap } from "@/stores/index.js";
import { navigationTree } from "@/main";
import getCreateUserStore from "@/stores/userStore.js";

const userStore = getCreateUserStore();

export const getCreateRecentEventStore = () => {
  const appLabel = "admin";
  const modelName = "LogEntry";
  const storeName = `${appLabel}-${modelName.toLowerCase()}`;

  if (storeMap.has(storeName)) {
    return storeMap.get(storeName);
  } else {
    let store = defineStore(storeName, {
      state: () => ({
        storeName: storeName,
        apiEndpoint: "/api/common/user/logged/recent_events",
        contentTypeIds: navigationTree.map((e) => e.id),
        itemCount: ref(0),
        items: ref([]),
        selectedOwnRecords: ref(false),
        lastSynced: ref()
      }),
      actions: {
        async getItems(user) {
          try {
            const response = await axios.get(`${this.apiEndpoint}/`, {
              params: {
                user_id: user ? user.id : null,
                content_type_id: this.contentTypeIds ? this.contentTypeIds : []
              },
              paramsSerializer: {
                indexes: null
              }
            });
            const data = response.data;
            // Get relevant users
            await userStore.getItems(data.map((e) => e.user));
            // Get model information from navigationTree
            // and user from userStore
            // and add it to the event
            data.forEach((event) => {
              event.model = navigationTree.find(
                (model) => model.id == event.content_type
              );
              event.user = userStore.items.find(
                (user) => user.id == event.user
              );
            });
            this.items = data;
            this.itemCount = data.count;
            this.lastSynced = new Date();
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

export default getCreateRecentEventStore;
