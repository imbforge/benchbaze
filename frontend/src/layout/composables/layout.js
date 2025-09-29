import { computed, reactive } from "vue";
import axios from "axios";
import { primaryColors, surfaces } from "@/layout/composables/colours";

const layoutConfig = reactive({
  preset: "Aura",
  primary: "emerald",
  surface: null,
  darkTheme: false,
  menuMode: "static"
});

const layoutState = reactive({
  staticMenuDesktopInactive: false,
  overlayMenuActive: false,
  profileSidebarVisible: false,
  configSidebarVisible: false,
  staticMenuMobileActive: false,
  menuHoverActive: false,
  activeMenuItem: null
});

export function useLayout() {
  const setActiveMenuItem = (item) => {
    layoutState.activeMenuItem = item.value || item;
  };

  const toggleDarkMode = () => {
    if (!document.startViewTransition) {
      executeDarkModeToggle();

      return;
    }

    document.startViewTransition(() => executeDarkModeToggle(event));
  };

  const executeDarkModeToggle = () => {
    layoutConfig.darkTheme = !layoutConfig.darkTheme;
    document.documentElement.classList.toggle("app-dark");
    syncLayout({ theme: layoutConfig.darkTheme ? "dark" : "light" });
  };

  const toggleMenu = () => {
    if (layoutConfig.menuMode === "overlay") {
      layoutState.overlayMenuActive = !layoutState.overlayMenuActive;
    }

    if (window.innerWidth > 991) {
      layoutState.staticMenuDesktopInactive =
        !layoutState.staticMenuDesktopInactive;
    } else {
      layoutState.staticMenuMobileActive = !layoutState.staticMenuMobileActive;
    }
  };

  const getPresetExt = () => {
    const color = primaryColors.value.find(
      (c) => c.name === layoutConfig.primary
    );

    if (color.name === "noir") {
      return {
        semantic: {
          primary: {
            50: "{surface.50}",
            100: "{surface.100}",
            200: "{surface.200}",
            300: "{surface.300}",
            400: "{surface.400}",
            500: "{surface.500}",
            600: "{surface.600}",
            700: "{surface.700}",
            800: "{surface.800}",
            900: "{surface.900}",
            950: "{surface.950}"
          },
          colorScheme: {
            light: {
              primary: {
                color: "{primary.950}",
                contrastColor: "#ffffff",
                hoverColor: "{primary.800}",
                activeColor: "{primary.700}"
              },
              highlight: {
                background: "{primary.950}",
                focusBackground: "{primary.700}",
                color: "#ffffff",
                focusColor: "#ffffff"
              }
            },
            dark: {
              primary: {
                color: "{primary.50}",
                contrastColor: "{primary.950}",
                hoverColor: "{primary.200}",
                activeColor: "{primary.300}"
              },
              highlight: {
                background: "{primary.50}",
                focusBackground: "{primary.300}",
                color: "{primary.950}",
                focusColor: "{primary.950}"
              }
            }
          }
        }
      };
    } else {
      return {
        semantic: {
          primary: color.palette,
          colorScheme: {
            light: {
              primary: {
                color: "{primary.500}",
                contrastColor: "#ffffff",
                hoverColor: "{primary.600}",
                activeColor: "{primary.700}"
              },
              highlight: {
                background: "{primary.50}",
                focusBackground: "{primary.100}",
                color: "{primary.700}",
                focusColor: "{primary.800}"
              }
            },
            dark: {
              primary: {
                color: "{primary.400}",
                contrastColor: "{surface.900}",
                hoverColor: "{primary.300}",
                activeColor: "{primary.200}"
              },
              highlight: {
                background:
                  "color-mix(in srgb, {primary.400}, transparent 84%)",
                focusBackground:
                  "color-mix(in srgb, {primary.400}, transparent 76%)",
                color: "rgba(255,255,255,.87)",
                focusColor: "rgba(255,255,255,.87)"
              }
            }
          }
        }
      };
    }
  };

  // Sync layout changes back to the DB
  const syncLayout = async (payload) => {
    try {
      await axios.put("/api/layout/1/", payload);
    } catch (error) {
      console.log(error);
    }
  };

  const setLayoutInitial = async (primeTheme) => {
    try {
      // Get layout values stored in DB
      const response = await axios.get("/api/layout/1/");
      const data = response.data;

      // Set retrieved values in layoutConfig
      layoutConfig.primary = data.primary_colour;
      layoutConfig.surface = data.surface_colour;
      layoutConfig.darkTheme = data.theme === "dark";

      // Update primary colour in primeTheme
      const presetExt = getPresetExt({ primary: data.primary_colour });
      primeTheme.semantic.primary = presetExt.semantic.primary;
      primeTheme.semantic.colorScheme.light.primary =
        presetExt.semantic.colorScheme.light.primary;
      primeTheme.semantic.colorScheme.light.highlight =
        presetExt.semantic.colorScheme.light.highlight;
      primeTheme.semantic.colorScheme.dark.primary =
        presetExt.semantic.colorScheme.dark.primary;
      primeTheme.semantic.colorScheme.dark.highlight =
        presetExt.semantic.colorScheme.dark.highlight;

      // Update surface colour primeTheme
      const surface = surfaces.value.find(
        (s) => s.name === data.surface_colour
      );
      primeTheme.semantic.colorScheme.light.surface = surface.palette;
      primeTheme.semantic.colorScheme.dark.surface = surface.palette;

      // Update light/dark theme
      if (layoutConfig.darkTheme) {
        document.documentElement.classList.toggle("app-dark");
      }

      return data;
    } catch (error) {
      console.log(error);
    }
  };

  const isSidebarActive = computed(
    () => layoutState.overlayMenuActive || layoutState.staticMenuMobileActive
  );

  const isDarkTheme = computed(() => layoutConfig.darkTheme);

  const getPrimary = computed(() => layoutConfig.primary);

  const getSurface = computed(() => layoutConfig.surface);

  return {
    layoutConfig,
    layoutState,
    toggleMenu,
    isSidebarActive,
    isDarkTheme,
    getPrimary,
    getSurface,
    setActiveMenuItem,
    toggleDarkMode,
    getPresetExt,
    syncLayout,
    setLayoutInitial
  };
}
