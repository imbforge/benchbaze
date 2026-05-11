import { Intent } from "@blueprintjs/core";

const DEFAULT_TOAST_DURATION_MS = 4000;

let appToaster = null;
const queuedToasts = [];

export function setToasterInstance(instance) {
  appToaster = instance;

  if (!appToaster || queuedToasts.length === 0) {
    return;
  }

  queuedToasts.splice(0).forEach((toastProps) => {
    appToaster.show(toastProps);
  });
}

function showToast(intent, message, fallbackMessage) {
  const toastProps = {
    message: String(message || fallbackMessage),
    intent,
    timeout: DEFAULT_TOAST_DURATION_MS
  };

  if (!appToaster) {
    queuedToasts.push(toastProps);
    return null;
  }

  return appToaster.show(toastProps);
}

export const toastr = {
  success: (message) => showToast(Intent.SUCCESS, message, "Success"),
  error: (message) => showToast(Intent.DANGER, message, "Error"),
  warning: (message) => showToast(Intent.WARNING, message, "Warning"),
  info: (message) => showToast(Intent.PRIMARY, message, "Info")
};

if (typeof window !== "undefined") {
  window.toastr = toastr;
}
