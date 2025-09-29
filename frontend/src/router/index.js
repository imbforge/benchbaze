import AppLayout from "@/layout/AppLayout.vue";
import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      component: AppLayout,
      children: [
        {
          path: "/",
          name: "dashboard",
          component: () => import("@/views/Dashboard.vue")
        },
        {
          path: `/:appLabel/:modelName`,
          component: () => import(`@/views/ListView.vue`)
        },
        {
          path: "/:appLabel/:modelName/:id",
          name: "item",
          component: () => import("@/views/ItemChangeView.vue")
        }
      ]
    },
    {
      path: "/landing",
      name: "landing",
      component: () => import("@/views/pages/Landing.vue")
    },
    {
      path: "/pages/notfound",
      name: "notfound",
      component: () => import("@/views/pages/NotFound.vue")
    },

    {
      path: "/auth/login",
      name: "login",
      component: () => import("@/views/pages/auth/Login.vue")
    },
    {
      path: "/auth/access",
      name: "accessDenied",
      component: () => import("@/views/pages/auth/Access.vue")
    },
    {
      path: "/auth/error",
      name: "error",
      component: () => import("@/views/pages/auth/Error.vue")
    }
  ]
});

export default router;
