// Get or create hidden input field to indicate whether common features should be detected,
// and set its value based on the user's choice in the modal
function updateDetectCommonFeaturesField(formElement, shouldDetectFeatures) {
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

// Show a modal asking the user whether common features should be detected in the map,
// and call the onChoice callback with the user's choice
function showDetectCommonFeaturesModal(onChoice) {
  // If a modal already exists (e.g. from a previous map_dna change), remove it before creating a new one
  const existingModal = document.getElementById("bb-map-dna-modal-overlay");
  if (existingModal !== null) {
    existingModal.remove();
  }

  // Create modal overlay with content and actions
  const overlay = document.createElement("div");
  overlay.id = "bb-map-dna-modal-overlay";
  overlay.className = "bb-admin-modal-overlay";

  overlay.innerHTML = `
    <div class="bb-admin-modal" role="dialog" aria-modal="true" aria-labelledby="bb-map-dna-modal-title">
      <h2 id="bb-map-dna-modal-title" class="bb-admin-modal-title">Map Processing</h2>
      <p class="bb-admin-modal-text">Detect common features in the map upon saving?</p>
      <div class="bb-admin-modal-actions">
        <button type="button" class="button default" data-modal-action="yes">Yes</button>
        <button type="button" class="button" data-modal-action="no">No</button>
      </div>
    </div>
  `;

  // Function to close the modal and call the onChoice callback with the user's choice
  const closeModal = function (choice) {
    document.removeEventListener("keydown", handleKeyDown);
    document.body.classList.remove("bb-admin-modal-open");
    overlay.remove();
    onChoice(choice);
  };

  // If the user presses the Escape key, close the modal and treat it as a "no" choice
  const handleKeyDown = function (event) {
    if (event.key === "Escape") {
      closeModal(false);
    }
  };

  // If the user clicks outside the modal content, close the modal and treat it as a "no" choice
  overlay.addEventListener("click", function (event) {
    if (event.target === overlay) {
      closeModal(false);
    }
  });

  // Add click event listeners to the "yes" and "no" buttons to close the modal and pass
  // the appropriate choice to the onChoice callback
  overlay
    .querySelector('[data-modal-action="yes"]')
    .addEventListener("click", function () {
      closeModal(true);
    });

  overlay
    .querySelector('[data-modal-action="no"]')
    .addEventListener("click", function () {
      closeModal(false);
    });

  // Add the modal overlay to the document and add a class to the body to prevent scrolling while the modal is open
  document.body.classList.add("bb-admin-modal-open");
  document.body.appendChild(overlay);
  document.addEventListener("keydown", handleKeyDown);

  overlay.querySelector('[data-modal-action="yes"]').focus();
}

// When the page loads, check if there is a formz feature warning and if so, uncollapse the formz fieldset,
// highlight the formz feature field, and add a warning message about missing features
$(window).on("load", function () {
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

// When the map_dna field changes, ask the user whether common features should be detected in the map upon saving,
// and set a hidden input field accordingly so the information is sent when the form is submitted
$(document).ready(function () {
  // If map_dna field changes, ask whether common features should be detected
  $("#id_map_dna").change(function () {
    const formElement = $(this).closest("form")[0];

    if (formElement === undefined) {
      return;
    }

    $(formElement).attr("onsubmit", "ShowLoading()");

    if (this.files.length < 1) {
      updateDetectCommonFeaturesField(formElement, false);
      return;
    }

    showDetectCommonFeaturesModal(function (shouldDetectFeatures) {
      updateDetectCommonFeaturesField(formElement, shouldDetectFeatures);
    });
  });

  // Add "button" to show map as an OVE preview in a magnific popup
  $(".field-map_dna").each((i, e) => {
    // Get the link element for the map_dna field
    let mapLinkElement = $(e).find("a")[0];

    // If the link element exists, add the "button" to show map as an OVE
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
          `<a class="magnific-popup-iframe-map-dna" style="padding-left:10px; padding-right:10px;" href=${mapBaseUrl}>⦾</a>`
        ).insertAfter(mapLinkElement);
      }
    }
  });
});

// Download map with imported oligos
function downloadMapWithImportedOligos(event) {
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
