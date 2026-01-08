<script setup>
import IconError from "@/components/icons/IconError.vue";
import IconHome from "@/components/icons/IconHome.vue";
import { app, navigationTree } from "@/main";
import { defineAsyncComponent, markRaw, ref } from "vue";
import AppMenuItem from "./AppMenuItem.vue";

var navigationItems = ref(navigationTree);
var model = ref([
  {
    label: "",
    items: [{ label: "Home", icon: markRaw(IconHome), to: "/" }]
  }
]);

// Create a navigation tree from API and mount app
try {
  // Get apps and models in an object that looks like
  // {
  //   app_verbose_name: [{
  //     app_label: 'App label',
  //     model_class_name: 'modelClassName',
  //     model_verbose_plural: 'Model names'
  //   }, ...
  //   ], ...
  // }

  let navList = {};
  navigationItems.value.forEach((e) => {
    let models =
      e.app_verbose_name in navList ? navList[e.app_verbose_name] : [];
    models.push({
      app_label: e.app_label,
      model_class_name: e.model_class_name,
      model_verbose_plural: e.model_verbose_plural
    });
    navList[e.app_verbose_name] = models;
  });

  // Convert navList into an array that looks like
  // [{
  //   label: 'App label', items: [
  //     {
  //       label: 'Model names',
  //       icon: 'modelClassName',
  //       to: `/app_label/modelclassname`
  //     }, ...
  // ]
  // }, ...]
  let appNames = Object.keys(navList);
  model.value = [
    ...model.value,
    ...appNames.map((appName) => {
      return {
        label: appName,
        items: navList[appName].map((e) => {
          const iconName = `Icon${e.app_label.charAt(0).toUpperCase() + e.app_label.slice(1)}${e.model_class_name}`;
          app.component(
            iconName,
            defineAsyncComponent({
              loader: () => import(`@/components/icons/${iconName}.vue`),
              errorComponent: IconError,
              timeout: 3000
            })
          );

          return {
            label: e.model_verbose_plural,
            icon: iconName,
            to: `/${e.app_label}/${e.model_class_name.toLowerCase()}`
          };
        })
      };
    })
  ];
} catch (error) {
  console.error(error);
  model.value = [];
}
</script>

<template>
  <ul class="layout-menu">
    <template v-for="(item, i) in model" :key="item">
      <app-menu-item
        v-if="!item.separator"
        :item="item"
        :index="i"
      ></app-menu-item>
      <li v-if="item.separator" class="menu-separator"></li>
    </template>
  </ul>
</template>

<style lang="scss" scoped></style>
