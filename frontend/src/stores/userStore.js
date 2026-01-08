import { defineStore } from "pinia";
import axios from "axios";
import { ref } from "vue";
import { storeMap } from "@/stores/index.js";

export const getCreateUserStore = () => {
  const appLabel = "common";
  const modelName = "user";
  const storeName = `${appLabel}-${modelName.toLowerCase()}`;

  if (storeMap.has(storeName)) {
    return storeMap.get(storeName);
  } else {
    let store = defineStore(storeName, {
      state: () => ({
        storeName: storeName,
        apiEndpoint: "/api/common/user/",
        itemCount: ref(0),
        items: ref([]),
        lastSynced: ref()
      }),
      actions: {
        async getItems(userIds) {
          try {
            userIds = [...new Set(userIds)];
            const newUserIds =
              userIds.length > 0 ? this.getArrayDiff(userIds) : [];
            if (newUserIds.length > 0) {
              const response = await axios.get(`${this.apiEndpoint}/`, {
                params: {
                  user_id: newUserIds
                },
                paramsSerializer: {
                  indexes: null
                }
              });
              this.items = [...this.items, ...response.data];
              this.itemCount = this.items.length;
              this.lastSynced = new Date();
            }
          } catch (error) {
            console.error(error);
            throw error;
          }
        },
        getArrayDiff(newUserIds) {
          const currentUserIds = this.items.map((user) => user.id);
          return newUserIds.filter((id) => !currentUserIds.includes(id));
        },
        findItemById(id) {
          return this.items.find((u) => u.id == id);
        }
      }
    });
    return store();
  }
};

export default getCreateUserStore;
