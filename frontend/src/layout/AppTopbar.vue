<script setup>
import { useLayout } from "@/layout/composables/layout";
import { user } from "@/main";
import { djangoSettings } from "@/router/navigation";
import axios from "axios";
import { useToast } from "primevue/usetoast";
import AppConfigurator from "./AppConfigurator.vue";

const toast = useToast();
const { toggleMenu, toggleDarkMode, isDarkTheme } = useLayout();

const logout = async () => {
  try {
    await axios.post(
      djangoSettings.logout_url ? djangoSettings.logout_url : "/logout/",
      {},
      {
        headers: {
          "BenchBaze-Api": true
        }
      }
    );
    window.location.replace(import.meta.env.BASE_URL);
  } catch (error) {
    toast.add({
      severity: "error",
      summary: "Error",
      detail: error,
      life: 3000
    });
  }
};
</script>

<template>
  <div class="layout-topbar">
    <div class="layout-topbar-logo-container">
      <button
        class="layout-menu-button layout-topbar-action"
        @click="toggleMenu"
      >
        <i class="pi pi-bars"></i>
      </button>
      <router-link to="/" class="layout-topbar-logo">
        <svg viewBox="0 0 54 40" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M51.97 20H27L38.43 6.99c.82-.93 2.14-.93 2.97 0l9.94 11.31c.41.47.62 1.08.62 1.69ZM15.57 7 27 20.01H2.03c0-.61.2-1.22.61-1.69L12.6 7c.82-.93 2.14-.93 2.97 0"
            style="fill: var(--primary-color)"
          />
          <path
            d="M2.03 20c0-.61.2-1.22.61-1.69L12.6 7c.82-.93 2.14-.93 2.97 0L27 20.01 38.43 33c.82.93 2.14.93 2.97 0l9.94-11.31c.41-.46.62-1.07.62-1.68s-.21-1.22-.62-1.69L41.4 7.01c-.83-.93-2.15-.93-2.97 0L27 20.02 15.57 33.01c-.83.93-2.15.93-2.97 0L2.64 21.69c-.41-.46-.61-1.07-.61-1.68Z"
            style="
              fill: none;
              stroke-linejoin: round;
              stroke: var(--primary-color);
              stroke-width: 4px;
            "
          />
        </svg>
        <div class="flex flex-col justify-self-center">
          <span
            ><span class="bb-authentication-box-coloured-title">B</span
            >ENCH<span class="bb-authentication-box-coloured-title">B</span
            >AZE</span
          >
          <span v-if="djangoSettings.lab_name" class="text-xs"
            ><span class="bb-authentication-box-coloured-title">@</span>
            {{ djangoSettings.lab_name }}</span
          >
        </div>
      </router-link>
    </div>

    <div class="layout-topbar-actions">
      <button
        class="layout-topbar-menu-button layout-topbar-action"
        v-styleclass="{
          selector: '@next',
          enterFromClass: 'hidden',
          enterActiveClass: 'animate-scalein',
          leaveToClass: 'hidden',
          leaveActiveClass: 'animate-fadeout',
          hideOnOutsideClick: true
        }"
      >
        <i class="pi pi-ellipsis-v"></i>
      </button>

      <div class="layout-topbar-menu hidden lg:block">
        <div class="layout-topbar-menu-content">
          <Button variant="text" disabled class="bb-layout-topbar-user">
            <i class="pi pi-user"></i>
            <span>{{ user.representation }}</span>
          </Button>
          <button
            type="button"
            class="layout-topbar-action"
            @click="toggleDarkMode"
          >
            <i
              :class="[
                'pi',
                { 'pi-moon': isDarkTheme, 'pi-sun': !isDarkTheme }
              ]"
            ></i>
            <span>Theme</span>
          </button>
          <div class="relative">
            <button
              v-styleclass="{
                selector: '@next',
                enterFromClass: 'hidden',
                enterActiveClass: 'animate-scalein',
                leaveToClass: 'hidden',
                leaveActiveClass: 'animate-fadeout',
                hideOnOutsideClick: true
              }"
              type="button"
              class="layout-topbar-action"
            >
              <i class="pi pi-palette"></i>
              <span>Highlight color</span>
            </button>
            <AppConfigurator />
          </div>
          <Button
            as="a"
            :href="djangoSettings.docs_url"
            target="_blank"
            rel="noopener"
            class="layout-topbar-action"
          >
            <i class="pi pi-book"></i>
            <span>Docs</span>
          </Button>
          <Button class="layout-topbar-action" @click="logout()">
            <i class="pi pi-sign-out"></i>
            <span>Log out</span>
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>
