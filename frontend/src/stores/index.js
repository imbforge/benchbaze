import { createPinia } from "pinia";

const pinia = createPinia();

const storeMap = new Map();

pinia.use(({ store }) => {
  storeMap.set(store.$id, store);
});

export { pinia, storeMap };
