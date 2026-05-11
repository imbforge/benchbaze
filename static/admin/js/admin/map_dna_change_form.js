function updateDetectCommonFeaturesField(formElement, shouldDetectFeatures) {
  // Get or create hidden input field to indicate whether common features should be detected,
  // and set its value based on the user's choice in the modal
  // UNUSED, but keep for potential future use

  const hiddenFieldName = "detect_common_features";
  let hiddenField = formElement.querySelector(
    `input[name="${hiddenFieldName}"]`
  );

  if (hiddenField === null) {
    hiddenField = document.createElement("input");
    hiddenField.type = "hidden";
    hiddenField.name = hiddenFieldName;
    formElement.appendChild(hiddenField);
  }

  // Set to "1" if shouldDetectFeatures is true, otherwise set to empty string
  // In Django, bool("1") is True and bool("") is False
  hiddenField.value = shouldDetectFeatures ? "1" : "";
}

function clearMapDnaInputFile() {
  // Clear the file in the map_dna input field by setting its value to an empty string
  const mapDnaInput = document.getElementById("id_map_dna");
  if (mapDnaInput instanceof HTMLInputElement && mapDnaInput.type === "file") {
    mapDnaInput.value = "";
  }
}

function replaceMapDnaInputFile(mapFile) {
  // Replace the file in the map_dna input field with the given mapFile
  // This new mapFile comes from the map detect features popup
  const mapDnaInput = document.getElementById("id_map_dna");

  if (
    !(mapDnaInput instanceof HTMLInputElement) ||
    mapDnaInput.type !== "file"
  ) {
    throw new Error("Map DNA input field not found.");
  }

  if (!(mapFile instanceof File)) {
    throw new Error("Invalid edited map file.");
  }

  // Create a new DataTransfer to hold the new file, and set it as the files of the map_dna input
  const dataTransfer = new DataTransfer();
  dataTransfer.items.add(mapFile);
  mapDnaInput.files = dataTransfer.files;
}

function updateSequenceFeatureIdsField(formElement, sequenceFeatureIds) {
  // Get or create hidden input field to hold the sequence feature IDs detected in the map,
  // and set its value to the given sequenceFeatureIds (as a comma-separated string)
  const hiddenFieldName = "map_dna_sequence_feature_ids";
  let hiddenField = formElement.querySelector(
    `input[name="${hiddenFieldName}"]`
  );

  if (!sequenceFeatureIds) {
    if (hiddenField !== null) {
      hiddenField.remove();
    }
    return;
  }

  if (hiddenField === null) {
    hiddenField = document.createElement("input");
    hiddenField.type = "hidden";
    hiddenField.name = hiddenFieldName;
    formElement.appendChild(hiddenField);
  }

  hiddenField.value = String(sequenceFeatureIds);
}

function getDirectMapDnaUrl(url) {
  // If the URL has a "file_name" query parameter, use its value as the direct URL to the map_dna file,
  // otherwise return the original URL
  try {
    const parsedUrl = new URL(url, window.location.origin);
    const fileNameParam = parsedUrl.searchParams.get("file_name");
    if (fileNameParam) {
      return new URL(fileNameParam, window.location.origin).href;
    }
    return parsedUrl.href;
  } catch (error) {
    return url;
  }
}

function getFileNameFromUrl(url) {
  // Try to extract the file name from the URL by looking at the last segment of the path,
  // or return a default file name if that fails
  try {
    const directUrl = getDirectMapDnaUrl(url);
    const parsedUrl = new URL(directUrl, window.location.origin);
    const pathSegments = parsedUrl.pathname.split("/").filter(Boolean);
    return pathSegments.length > 0
      ? pathSegments[pathSegments.length - 1]
      : "map_dna_file";
  } catch (error) {
    return "map_dna_file";
  }
}

async function fetchMapFileFromUrl(mapUrl) {
  // Fetch the map_dna file from the given URL, and return it as a File object
  const directMapUrl = getDirectMapDnaUrl(mapUrl);
  const response = await fetch(directMapUrl, {
    credentials: "same-origin"
  });

  if (!response.ok) {
    throw new Error(`Failed to download map file (${response.status}).`);
  }

  const blob = await response.blob();
  const fileName = getFileNameFromUrl(mapUrl);

  return new File([blob], fileName, {
    type: blob.type || "application/octet-stream"
  });
}

function getCurrentMapDnaFile() {
  // Get the current map_dna file either from the file input (if a new file was selected)
  // or by fetching it from the URL (if editing an existing map)
  const mapDnaInput = document.getElementById("id_map_dna");

  // If a new file was selected in the input, return that file
  if (mapDnaInput instanceof HTMLInputElement && mapDnaInput.files.length > 0) {
    return Promise.resolve(mapDnaInput.files[0]);
  }

  // Otherwise, try to fetch the existing map file from the URL provided in oveUrls["map_dna"]
  const mapDnaUrl = oveUrls["map_dna"];
  if (!mapDnaUrl) {
    return Promise.reject(
      new Error("No current map is available for editing.")
    );
  }

  return fetchMapFileFromUrl(mapDnaUrl);
}

function createReeditMapButton() {
  // If the map_dna input field exists and the re-edit button doesn't already exist,
  // create and insert a "Re-edit map" button next to the map_dna input field
  const mapDnaInput = document.getElementById("id_map_dna");
  if (!mapDnaInput || document.getElementById("id_map_dna_reedit_link")) {
    return;
  }

  // Create the button element with appropriate attributes
  const button = document.createElement("button");
  button.type = "button";
  button.id = "id_map_dna_reedit_link";
  button.className = "bb-admin-map-dna-reedit-link";
  button.title = "View/Edit map";
  button.setAttribute("aria-label", "View/Edit map");
  button.textContent = "✎";

  // Add click event listener to the button to open the map detect features popup with the current map file
  button.addEventListener("click", async function (event) {
    event.preventDefault();

    try {
      const mapFile = await getCurrentMapDnaFile();
      openMapDetectFeaturesPopup(mapFile, {
        detectFeatures: false
      });
    } catch (error) {
      console.error(error);
      alert(
        "Unable to open the current map for re-editing. Please add a map file or refresh the page."
      );
    }
  });

  const fileUploadParagraph = mapDnaInput.closest("p.file-upload");
  if (fileUploadParagraph && fileUploadParagraph.parentNode) {
    fileUploadParagraph.parentNode.insertBefore(button, fileUploadParagraph);
  } else {
    mapDnaInput.parentNode?.insertBefore(button, mapDnaInput);
  }
}

function updateReeditMapButtonState() {
  // Enable the "Re-edit map" button if there is a selected file in the map_dna input or
  // an existing map URL, otherwise disable it
  const button = document.getElementById("id_map_dna_reedit_link");
  if (!button) {
    return;
  }

  const mapDnaInput = document.getElementById("id_map_dna");
  const hasSelectedFile =
    mapDnaInput instanceof HTMLInputElement && mapDnaInput.files.length > 0;
  const hasExistingMap = Boolean(oveUrls["map_dna"]);

  button.setAttribute(
    "aria-disabled",
    String(!hasSelectedFile && !hasExistingMap)
  );
}

function openMapDetectFeaturesPopup(mapDnaFile, payloadOverrides = {}) {
  // Open a magnific popup with the map_dna file processing results

  if (!$.magnificPopup) {
    alert("Magnific popup is not available.");
    return;
  }

  if (!(mapDnaFile instanceof Blob)) {
    alert("Invalid map file.");
    return;
  }

  // Get relevant data for the map
  const fileName = mapDnaFile.name || "map_dna_file";

  const viewerBaseUrl = (
    oveUrls["map_dna"] ||
    (typeof OVE_URL !== "undefined" && OVE_URL ? OVE_URL : "/ove/")
  ).split("?")[0];
  // Append parameter bb_post_mode to viewer URL to tell the viewer
  // to expect a postMessage with the map file and switch to "edit"
  // mode (= not read-only)
  const viewerUrl = `${viewerBaseUrl}?bb_post_mode=1`;

  // Create the payload to post to the popup iframe.
  const viewerPayload = {
    type: "BB_MAP_DNA_POST_RESULT",
    fileName: fileName,
    mapFile: mapDnaFile,
    detectFeatures: true,
    ...payloadOverrides
  };

  let stopPostingPayload = null;
  let closeButtonHandler = null;
  let mapPayloadPosted = false;

  // Open the magnific popup with the viewerUrl, and post the viewerPayload to the iframe once it has loaded
  $.magnificPopup.open({
    items: {
      src: viewerUrl,
      type: "iframe"
    },
    mainClass: "mfp-iframe-detect-features-map-dna",
    closeOnBgClick: false,
    enableEscapeKey: false,
    callbacks: {
      open: function () {
        // Get the iframe element of the popup
        const iframe = document.querySelector(".mfp-iframe");
        if (!iframe) {
          return;
        }

        const iframeWindow = iframe.contentWindow;
        const closeButton = document.querySelector(".mfp-close");

        // Handle the case where the user tries to close the popup with unsaved changes
        // by showing a modal that informs them they must save before closing
        const suppressBeforeUnloadPrompt = function () {
          if (iframeWindow) {
            iframeWindow.BB_MAP_DNA_SUPPRESS_BEFOREUNLOAD_PROMPT = true;
          }
        };

        const handleCloseButtonClick = function (event) {
          event.preventDefault();
          event.stopPropagation();

          const hasUnsavedChanges =
            iframeWindow?.BB_MAP_DNA_HAS_UNSAVED_CHANGES === true;

          if (!mapPayloadPosted || !hasUnsavedChanges) {
            $.magnificPopup.close();
            return;
          }

          showSaveRequiredModal(suppressBeforeUnloadPrompt);
        };

        if (closeButton) {
          closeButtonHandler = handleCloseButtonClick;
          closeButton.addEventListener("click", handleCloseButtonClick);
        }

        // Set up the maximum number of attempts to post the payload
        const maxPostAttempts = 40;
        let postAttempts = 0;
        let postIntervalId = null;
        let hasAcknowledgement = false;

        // Clean up the event listeners and intervals related to posting the payload
        const cleanupPostFlow = function () {
          if (postIntervalId !== null) {
            window.clearInterval(postIntervalId);
            postIntervalId = null;
          }

          window.removeEventListener("message", handleAcknowledgementMessage);
          iframe.removeEventListener("load", postPayloadToIframe);
        };

        // Post the viewerPayload to the iframe, and set up retries
        // and acknowledgement handling
        const postPayloadToIframe = function () {
          if (hasAcknowledgement) {
            return;
          }

          const targetWindow = iframe.contentWindow;
          if (!targetWindow) {
            return;
          }

          try {
            targetWindow.postMessage(viewerPayload, window.location.origin);
            mapPayloadPosted = true;
            postAttempts += 1;

            if (postAttempts >= maxPostAttempts) {
              cleanupPostFlow();
              console.warn(
                "Map payload was not acknowledged by viewer in time."
              );
            }
          } catch (error) {
            cleanupPostFlow();
            console.error("Error posting message to iframe:", error);
          }
        };

        // Handle the acknowledgement message from the iframe
        const handleAcknowledgementMessage = function (event) {
          if (event.origin !== window.location.origin) {
            return;
          }

          if (event.source !== iframe.contentWindow) {
            return;
          }

          const data = event.data;
          if (!data || typeof data !== "object") {
            return;
          }

          if (data.type !== "BB_MAP_DNA_POST_ACKNOWLEDGEMENT") {
            return;
          }

          hasAcknowledgement = true;
          cleanupPostFlow();
        };

        stopPostingPayload = cleanupPostFlow;

        window.addEventListener("message", handleAcknowledgementMessage);
        iframe.addEventListener("load", postPayloadToIframe);

        // Try immediately and keep retrying for a short time to handle race conditions
        // between iframe load timing and message listener registration
        postPayloadToIframe();
        postIntervalId = window.setInterval(postPayloadToIframe, 250);
      },
      close: function () {
        if (closeButtonHandler) {
          const closeButton = document.querySelector(".mfp-close");
          if (closeButton) {
            closeButton.removeEventListener("click", closeButtonHandler);
          }
          closeButtonHandler = null;
        }

        if (typeof stopPostingPayload === "function") {
          stopPostingPayload();
          stopPostingPayload = null;
        }
      }
    }
  });
}

function showDetectCommonFeaturesModal(onChoice) {
  // Show an admin-style modal asking whether features should be detected in the map,
  // and call the onChoice callback with the user's choice

  // If a modal already exists (e.g. from a previous map_dna change), remove it before creating a new one
  const existingModal = document.getElementById(
    "bb-admin-map-dna-detect-features-modal-overlay"
  );
  if (existingModal !== null) {
    existingModal.remove();
  }

  // Create modal overlay with content and actions
  const overlay = document.createElement("div");
  overlay.id = "bb-admin-map-dna-detect-features-modal-overlay";
  overlay.className = "bb-admin-map-dna-detect-features-modal-overlay";

  overlay.innerHTML = `
    <div class="bb-admin-map-dna-detect-features-modal" role="dialog" aria-modal="true" aria-labelledby="bb-admin-map-dna-detect-features-modal-title">
      <h2 id="bb-admin-map-dna-detect-features-modal-title" class="bb-admin-map-dna-detect-features-modal-title">Map Processing</h2>
      <p class="bb-admin-map-dna-detect-features-modal-text">Before a new map can be added to the form, it must be processed, which can take a few seconds. Be patient!</p>
      <div class="bb-admin-map-dna-detect-features-modal-note">
      Once the processed map is loaded, edit it and save it before submitting the form.
      </div>
      <div class="bb-admin-map-dna-detect-features-modal-actions">
        <button type="button" class="button default" data-modal-action="ok">OK</button>
        <button type="button" class="button secondary" data-modal-action="cancel">Cancel</button>
      </div>
    </div>
  `;

  // Handle the different ways the user can close the modal:
  // clicking OK, clicking Cancel, clicking outside the modal, or pressing Escape
  const closeModal = function (wasConfirmed) {
    document.removeEventListener("keydown", handleKeyDown);
    document.body.classList.remove(
      "bb-admin-map-dna-detect-features-modal-open"
    );
    overlay.remove();
    onChoice(Boolean(wasConfirmed));
  };

  const handleKeyDown = function (event) {
    if (event.key === "Escape") {
      closeModal(false);
    }
  };

  overlay.addEventListener("click", function (event) {
    if (event.target === overlay) {
      closeModal(false);
    }
  });

  overlay
    .querySelector('[data-modal-action="ok"]')
    .addEventListener("click", function () {
      closeModal(true);
    });

  overlay
    .querySelector('[data-modal-action="cancel"]')
    .addEventListener("click", function () {
      closeModal(false);
    });

  document.body.classList.add("bb-admin-map-dna-detect-features-modal-open");
  document.body.appendChild(overlay);
  document.addEventListener("keydown", handleKeyDown);

  overlay.querySelector('[data-modal-action="ok"]').focus();
}

function showSaveRequiredModal(onCloseWithoutSaving) {
  // Show a modal that informs the user they must save before closing when changes exist

  const existingModal = document.getElementById(
    "bb-admin-map-dna-close-without-saving-modal-overlay"
  );

  // If a modal already exists (e.g. from a previous attempt to close without saving),
  // remove it before creating a new one
  if (existingModal !== null) {
    existingModal.remove();
  }

  const overlay = document.createElement("div");
  overlay.id = "bb-admin-map-dna-close-without-saving-modal-overlay";
  overlay.className = "bb-admin-map-dna-detect-features-modal-overlay";

  overlay.innerHTML = `
    <div class="bb-admin-map-dna-detect-features-modal" role="dialog" aria-modal="true" aria-labelledby="bb-admin-map-dna-close-without-saving-modal-title">
      <h2 id="bb-admin-map-dna-close-without-saving-modal-title" class="bb-admin-map-dna-detect-features-modal-title">Unsaved Changes</h2>
      <p class="bb-admin-map-dna-detect-features-modal-text">You have unsaved changes in the map viewer. Choose whether to continue editing or close without saving.</p>
      <div class="bb-admin-map-dna-detect-features-modal-actions">
        <button type="button" class="button default" data-modal-action="continue">Continue editing</button>
        <button type="button" class="button secondary" data-modal-action="close">Close without saving</button>
      </div>
    </div>
  `;

  // Handle the different ways the user can respond to the modal:
  // clicking "Continue editing", clicking "Close without saving", clicking outside the modal, or pressing Escape
  const closeModal = function () {
    document.removeEventListener("keydown", handleKeyDown);
    document.body.classList.remove(
      "bb-admin-map-dna-detect-features-modal-open"
    );
    overlay.remove();
  };

  const closePopupWithoutSaving = function () {
    if (typeof onCloseWithoutSaving === "function") {
      onCloseWithoutSaving();
    }
    closeModal();
    if (typeof $.magnificPopup === "object" && $.magnificPopup.close) {
      $.magnificPopup.close();
    }
  };

  const handleKeyDown = function (event) {
    if (event.key === "Escape") {
      closeModal();
    }
  };

  overlay.addEventListener("click", function (event) {
    if (event.target === overlay) {
      closeModal();
    }
  });

  overlay
    .querySelector('[data-modal-action="continue"]')
    .addEventListener("click", function () {
      closeModal();
    });

  overlay
    .querySelector('[data-modal-action="close"]')
    .addEventListener("click", function () {
      closePopupWithoutSaving();
    });

  document.body.classList.add("bb-admin-map-dna-detect-features-modal-open");
  document.body.appendChild(overlay);
  document.addEventListener("keydown", handleKeyDown);

  overlay.querySelector('[data-modal-action="continue"]').focus();
}

$(window).on("load", function () {
  // When the page loads, check if there is a formz feature warning and if so, uncollapse the formz fieldset,
  // highlight the formz feature field, and add a warning message about missing features

  // If there is a formz feature warning uncollapse formz section and highlight formz element field
  if (document.getElementsByClassName("missing-formz-features").length > 0) {
    // Get formz feature field, uncollapse fieldset and add error class to highlight it
    var sequence_feature_field = document.getElementsByClassName(
      "form-row field-sequence_features"
    )[0];
    sequence_feature_field.closest("fieldset").classList.remove("collapsed");
    sequence_feature_field.classList.add("errors");

    // Add warning message about missing features to formz feature field
    var warning_in_field = document.createElement("ul");
    var warning_message = document.createElement("li");
    warning_in_field.classList.add("errorlist");
    warning_message.innerText =
      "Missing elements: " +
      document.getElementsByClassName("missing-formz-features")[0].innerText;
    warning_message.style = "color: #efb829;";
    warning_in_field.appendChild(warning_message);
    sequence_feature_field.appendChild(warning_in_field);

    // Add highlight border to select2 element in formz feature field
    sequence_feature_field.getElementsByClassName(
      "select2-selection select2-selection--multiple"
    )[0].style = "border:solid 1px #efb829;";
  }
});

$(document).ready(function () {
  // When the map_dna field changes, ask the user whether features should be detected,
  // and set a hidden input field accordingly to indicate the user's choice.
  // If the user chooses to detect features, open a magnific popup to process the map_dna file
  const mapDnaInput = document.getElementById("id_map_dna");
  if (
    mapDnaInput instanceof HTMLInputElement &&
    (mapDnaInput.files.length > 0 || Boolean(oveUrls["map_dna"]))
  ) {
    createReeditMapButton();
    updateReeditMapButtonState();
  }

  window.addEventListener("message", function (event) {
    // Listen for the message from the map detect features popup with the processed map file,
    // and replace the file in the map_dna input field with the processed map file, so that
    // the edited map will be submitted with the form
    if (event.origin !== window.location.origin) {
      return;
    }

    const data = event.data;
    if (!data || typeof data !== "object") {
      return;
    }

    // Handle the initial message from the popup with the feature IDs detected and
    // set them in a hidden input field
    if (data.type === "BB_MAP_DNA_INITIAL_FEATURE_IDS") {
      const mapDnaInput = document.getElementById("id_map_dna");
      const formElement = mapDnaInput?.closest("form");

      if (formElement) {
        updateSequenceFeatureIdsField(formElement, data.sequenceFeatureIds);
      }
      return;
    }

    // Only handle messages from the popup with the processed map file
    if (data.type !== "BB_MAP_DNA_SAVE_RESULT") {
      return;
    }

    // Replace the file in the map_dna input field with the processed map file from the popup,
    // and update the hidden input field with the detected sequence feature IDs, if available,
    // so that the edited map and detected features will be submitted with the form
    try {
      replaceMapDnaInputFile(data.mapFile);

      const mapDnaInput = document.getElementById("id_map_dna");
      const formElement = mapDnaInput?.closest("form");

      if (formElement) {
        updateSequenceFeatureIdsField(formElement, data.sequenceFeatureIds);
      }

      updateReeditMapButtonState();
    } catch (error) {
      console.error(error.message || "Failed to attach edited map");
    }
  });

  $("#id_map_dna").change(function () {
    // If map_dna field changes, ask whether features should be detected

    // Get the form element containing the changed map_dna input field
    const formElement = $(this).closest("form")[0];

    if (formElement === undefined) {
      return;
    }

    $(formElement).attr("onsubmit", "ShowLoading()");

    // If no file was selected, update hidden input field to indicate that features
    // should not be detected and return
    if (this.files.length < 1) {
      // updateDetectCommonFeaturesField(formElement, false);
      updateSequenceFeatureIdsField(formElement, null);
      const existingButton = document.getElementById("id_map_dna_reedit_link");
      if (existingButton) {
        existingButton.remove();
      }
      return;
    }

    // Clear any stale sequenceFeatureIds when a new file is selected
    updateSequenceFeatureIdsField(formElement, null);
    createReeditMapButton();
    updateReeditMapButtonState();

    // Store reference to the map_dna file for passing to the popup
    const mapDnaFile = this.files[0];

    showDetectCommonFeaturesModal(function (shouldDetectFeatures) {
      // Show modal to ask user whether common features should be detected,
      // and update hidden input field based on the user's choice

      if (!shouldDetectFeatures) {
        clearMapDnaInputFile();
        // updateDetectCommonFeaturesField(formElement, false);
        updateSequenceFeatureIdsField(formElement, null);

        if (!Boolean(oveUrls["map_dna"])) {
          const existingButton = document.getElementById(
            "id_map_dna_reedit_link"
          );
          if (existingButton) {
            existingButton.remove();
          }
        }

        updateReeditMapButtonState();
        return;
      }

      // updateDetectCommonFeaturesField(formElement, true);

      if (mapDnaFile) {
        openMapDetectFeaturesPopup(mapDnaFile);
      }
    });
  });

  $(".field-map_dna")
    .has(".readonly")
    .each((i, e) => {
      // Add "button" to show map as an OVE preview in a magnific popup

      // Get the link element for the map_dna field
      let mapLinkElement = $(e).find("a")[0];

      // If the link element exists, add a clickable element to show map as an OVE
      // preview in a magnific popup
      if (mapLinkElement !== undefined) {
        const fieldName = $(e)
          .attr("class")
          .split(" ")
          .find((className) => className.startsWith("field-"))
          .replace("field-", "");
        let mapBaseUrl = oveUrls[fieldName];

        // If the mapBaseUrl exists, add the "button" to show map as an OVE preview in a magnific popup
        if (fieldName !== undefined && mapBaseUrl !== undefined) {
          $(
            `<a class="magnific-popup-iframe-map-dna viewlink" style="margin-left:10px; margin-right:10px;" href=${mapBaseUrl} title="View Map"></a>`
          ).insertAfter(mapLinkElement);
        }
      }
    });
});

function downloadMapWithImportedOligos(event) {
  // Download map with imported oligos

  // Make AJAX request to get map with imported oligos as a blob,
  // then create a link to download the file
  $.ajax({
    url: event.srcElement.attributes.download_url.value,
    cache: false,
    xhrFields: {
      responseType: "blob"
    },

    // Show loading spinner while waiting for response
    beforeSend: function (html) {
      ShowLoading();
    },

    // On success, create a link to download the file and click it,
    // then remove the link and revoke the object URL
    success: function (data, textStatus, jqXHR) {
      var a = document.createElement("a");
      var url = window.URL.createObjectURL(data);
      a.href = url;
      a.download = decodeURI(
        jqXHR
          .getResponseHeader("Content-Disposition")
          .match(/filename\*=utf-8''(.*)/)[1]
      );
      document.body.append(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      $(".spinner-loader").remove();
    }
  });
}
