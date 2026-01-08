import { createPinia } from "pinia";

const pinia = createPinia();

const storeMap = new Map();

pinia.use(({ store }) => {
  storeMap.set(store.$id, store);
});

const getStore = (appLabel, modelName) => {
  const storeName = `${appLabel}-${modelName.toLowerCase()}`;

  if (storeMap.has(storeName)) {
    return storeMap.get(storeName);
  } else {
    return null;
  }
};

export { getStore, pinia, storeMap };
