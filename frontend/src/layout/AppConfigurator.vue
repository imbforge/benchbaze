<script setup>
import { useLayout } from "@/layout/composables/layout";
import { primaryColors, surfaces } from "@/layout/composables/colours";

import { updatePreset, updateSurfacePalette } from "@primeuix/themes";

const { layoutConfig, isDarkTheme, getPresetExt, syncLayout } = useLayout();

function updateColors(type, color) {
  if (type === "primary") {
    layoutConfig.primary = color.name;
    syncLayout({ primary_colour: color.name });
  } else if (type === "surface") {
    layoutConfig.surface = color.name;
    syncLayout({ surface_colour: color.name });
  }

  applyTheme(type, color);
}

function applyTheme(type, color) {
  if (type === "primary") {
    updatePreset(getPresetExt());
  } else if (type === "surface") {
    updateSurfacePalette(color.palette);
  }
}
</script>

<template>
  <div
    class="config-panel hidden absolute top-[3.25rem] right-0 w-64 p-4 bg-surface-0 dark:bg-surface-900 border border-surface rounded-border origin-top shadow-[0px_3px_5px_rgba(0,0,0,0.02),0px_0px_2px_rgba(0,0,0,0.05),0px_1px_4px_rgba(0,0,0,0.08)]"
  >
    <div class="flex flex-col gap-4">
      <div>
        <span class="text-sm text-muted-color font-semibold">Primary</span>
        <div class="pt-2 flex gap-2 flex-wrap justify-between">
          <button
            v-for="primaryColor of primaryColors"
            :key="primaryColor.name"
            type="button"
            :title="primaryColor.name"
            @click="updateColors('primary', primaryColor)"
            :class="[
              'border-none w-5 h-5 rounded-full p-0 cursor-pointer outline-none outline-offset-1',
              { 'outline-primary': layoutConfig.primary === primaryColor.name }
            ]"
            :style="{
              backgroundColor: `${primaryColor.name === 'noir' ? 'var(--text-color)' : primaryColor.palette['500']}`
            }"
          ></button>
        </div>
      </div>
      <div>
        <span class="text-sm text-muted-color font-semibold">Surface</span>
        <div class="pt-2 flex gap-2 flex-wrap justify-between">
          <button
            v-for="surface of surfaces"
            :key="surface.name"
            type="button"
            :title="surface.name"
            @click="updateColors('surface', surface)"
            :class="[
              'border-none w-5 h-5 rounded-full p-0 cursor-pointer outline-none outline-offset-1',
              {
                'outline-primary': layoutConfig.surface
                  ? layoutConfig.surface === surface.name
                  : isDarkTheme
                    ? surface.name === 'zinc'
                    : surface.name === 'slate'
              }
            ]"
            :style="{ backgroundColor: `${surface.palette['500']}` }"
          ></button>
        </div>
      </div>
    </div>
  </div>
</template>
