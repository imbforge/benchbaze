import AppLayout from "@/layout/AppLayout.vue";
import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // {
    //   path: "/",
    //   component: AppLayout,
    //   children: [
    //     {
    //       path: "/",
    //       name: "dashboard",
    //       component: () => import("@/views/Dashboard.vue"),
    //       children: [
    //         {
    //           path: `:appLabel/:modelName`,
    //           component: () => import(`@/views/ListView.vue`),
    //           name: "listView",
    //           children: [
    //             {
    //               path: ":id",
    //               name: "changeView",
    //               component: () => import("@/views/ItemChangeView.vue")
    //             }
    //           ]
    //         }
    //       ]
    //     }
    //   ]
    // },
    {
      path: "/",
      component: AppLayout,
      children: [
        {
          path: "/",
          name: "dashboard",
          component: () => import("@/views/Home.vue")
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
      path: "/notfound",
      name: "notfound",
      component: () => import("@/views/pages/NotFound.vue")
    },

    {
      path: "/common/access",
      name: "accessDenied",
      component: () => import("@/views/pages/auth/Access.vue")
    },
    {
      path: "/commn/error",
      name: "error",
      component: () => import("@/views/pages/auth/Error.vue")
    }
  ]
});

export default router;
