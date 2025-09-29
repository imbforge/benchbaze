import axios from "axios";
import { defineStore } from "pinia";
import { ref } from "vue";

const name = "navigation";

export const useNavigationStore = defineStore(name, {
  state: () => ({
    storeName: name,
    totalItems: ref(0),
    items: ref([]),
    item: ref({ id: 0 })
  }),
  actions: {
    async getItems() {
      try {
        const response = await axios.get(`/api/${name}/`);
        const data = response.data;
        this.items = data;
        this.totalItems = this.items.length;
        return data;
      } catch (error) {
        console.error(error);
      }
    },
    async getItem(id) {
      try {
        const response = await axios.get(`/api/${name}/${id}/`);
        this.item = response.data;
        return response.data;
      } catch (error) {
        console.log(error);
        throw error;
      }
    },
    async getListViewFields(appLabel, modelName) {
      try {
        const model = this.getModel(appLabel, modelName);
        const response = await axios.get(
          `/api/${name}/${model.id}/listview_fields/`
        );
        return response.data;
      } catch (error) {
        console.log(error);
        throw error;
      }
    },
    getModel(appLabel, modelName) {
      return this.items.find(
        (e) =>
          e.app_label === appLabel &&
          e.model_class_name.toLowerCase() === modelName
      );
    }
  }
});
