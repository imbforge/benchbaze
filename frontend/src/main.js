import "@/assets/styles.scss";
import { useLayout } from "@/layout/composables/layout";
import getCookie from "@/utils/cookies";
import Aura from "@primeuix/themes/aura";
import axios from "axios";
import PrimeVue from "primevue/config";
import ConfirmationService from "primevue/confirmationservice";
import ToastService from "primevue/toastservice";
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { pinia } from "./stores/index.js";
import { getNavigationTree, getLoggedUser } from "./router/navigation";

// Get logged user info
const user = await getLoggedUser();

// Create a navigation tree from API and mount app
const navigationTree = await getNavigationTree();

// Set csrfToken app-wide, this is necessary for form submission
// app.provide("csrfToken", getCookie("csrftoken"));
axios.defaults.withCredentials = true;
axios.defaults.credentials = "same-origin";
axios.defaults.headers.common["X-CSRFToken"] = getCookie("csrftoken");

const app = createApp(App);

// Set layout based on values in DB
const { setLayoutInitial } = useLayout();
await setLayoutInitial(Aura);

app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: ".app-dark"
    }
  }
});
app.use(ToastService);
app.use(ConfirmationService);
app.use(pinia);
app.use(router);
app.mount("#app");

export { user, navigationTree, app };
