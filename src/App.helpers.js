const THEME_STORAGE_KEY = "theme";

export function getPanelsShown(isCircular, isPostPayloadMode) {
  // Determine which panels to show based on the map type and mode
  return [
    [
      {
        id: "circular",
        name: "Circular Map",
        active: Boolean(isCircular)
      },
      {
        id: "rail",
        name: "Linear Map",
        active: !isCircular
      },
      {
        id: "sequence",
        name: "Sequence Map"
      }
    ],
    [
      {
        id: "properties",
        name: "Properties",
        active: true
      }
    ]
  ];
}

export function getLoadErrorMessage(error) {
  // Extract a user-friendly error message from the error object
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "The map cannot be loaded.";
}

export function getInitialTheme() {
  // Determine the initial theme based on the pared theme from localStorage or the system preference
  try {
    const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (
      storedTheme === "dark" ||
      storedTheme === "light" ||
      storedTheme === "auto"
    ) {
      return storedTheme;
    }
  } catch (error) {
    // Ignore storage read failures and continue with system/default theme.
  }

  if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }

  return "light";
}

export function getPostedPayloadFromWindow() {
  // Check if there's a posted payload on the window object
  const payload = window.__BB_MAP_DNA_POST_RESULT__;
  return isBlobPostedPayload(payload) ? payload : null;
}

export function isBlobPostedPayload(payload) {
  // Check if the payload is an object containing a mapFile that is a Blob
  return Boolean(
    payload && typeof payload === "object" && payload.mapFile instanceof Blob
  );
}

export function getFileFormatFromFileName(fileName) {
  // Get the file format (extension) from the file name, ignoring query parameters and fragments
  if (!fileName) {
    return null;
  }

  const cleanedFileName = String(fileName).split("?")[0].split("#")[0];
  const lastDotIndex = cleanedFileName.lastIndexOf(".");

  if (lastDotIndex <= 0 || lastDotIndex === cleanedFileName.length - 1) {
    return null;
  }

  return cleanedFileName.slice(lastDotIndex + 1).toLowerCase();
}

export function getCookie(name) {
  // Retrieve the value of a cookie by name
  const cookieString = document.cookie || "";
  const cookies = cookieString.split(";");

  for (const cookie of cookies) {
    const [rawKey, ...rawValueParts] = cookie.trim().split("=");
    if (rawKey === name) {
      return decodeURIComponent(rawValueParts.join("="));
    }
  }

  return null;
}
