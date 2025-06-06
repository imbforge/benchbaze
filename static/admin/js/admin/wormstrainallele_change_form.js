// For /templates/admin/collection/wormstrainallele/change_form.html

$(window).on("load", function () {
  // If there is a formz feature warning uncollapse formz section and highlight formz element field
  if (document.getElementsByClassName("missing-formz-features").length > 0) {
    var sequence_feature_field = document.getElementsByClassName(
      "form-row field-sequence_features"
    )[0];
    sequence_feature_field.closest("fieldset").classList.remove("collapsed");
    sequence_feature_field.classList.add("errors");

    var warning_in_field = document.createElement("ul");
    var warning_message = document.createElement("li");
    warning_in_field.classList.add("errorlist");
    warning_message.innerText =
      "Missing elements: " +
      document.getElementsByClassName("missing-formz-features")[0].innerText;
    warning_message.style = "color: #efb829;";
    warning_in_field.appendChild(warning_message);
    sequence_feature_field.appendChild(warning_in_field);

    sequence_feature_field.getElementsByClassName(
      "select2-selection select2-selection--multiple"
    )[0].style = "border:solid 1px #efb829;";
  }
});

$(document).ready(function () {
  // If map field changes add ShowLoading to form onsubmit and show toggle to decide if common features should be detected
  $("#id_map,#id_map_gbk").change(function () {
    $("#wormstrainallele_form").attr("onsubmit", "ShowLoading()");

    const fieldName = $(this).attr("id").replace("id_", "");

    if ($(`#detect-common-features-dna_${fieldName}`).length < 1) {
      var dna_map_field_label = Array.from(
        document.getElementsByTagName("label")
      ).filter(function (e) {
        return e.htmlFor === `id_${fieldName}`;
      })[0];
      dna_map_field_label.innerHTML =
        dna_map_field_label.innerHTML + "<br><br>";

      var detect_common_features_toggle = document.createElement("input");
      detect_common_features_toggle.name = `detect_common_features_${fieldName}`;
      detect_common_features_toggle.id = `detect-common-features-dna_${fieldName}`;
      detect_common_features_toggle.type = "checkbox";
      detect_common_features_toggle.checked = true;

      var label_for_toggle = document.createElement("span");
      label_for_toggle.innerText = " Detect common features in this map?";
      label_for_toggle.style = "color: #efb829;";

      dna_map_field_label.appendChild(detect_common_features_toggle);
      dna_map_field_label.appendChild(label_for_toggle);
    }
  });

  // Add "button" to show map as OVE preview in a magnific popup

  $(".field-map,.field-map_gbk").each((i, e) => {
    let mapLinkElement = $(e).find("a")[0];
    if (mapLinkElement !== undefined) {
      const fieldName = $(e).attr("class").split(" ")[1].split("-")[1];
      if (fieldName !== undefined) {
        let mapBaseUrl = oveUrls[fieldName];
        $(
          `<a class="magnific-popup-iframe-map" style="padding-left:10px; padding-right:10px;" href=${mapBaseUrl}>⊙</a>`
        ).insertAfter(mapLinkElement);
      }
    }
  });

  // Show png map as a magnific popup

  let png_url = $(".field-map_png").find("a")[0];
  if (png_url !== undefined) png_url.classList.add("magnific-popup-img-map");
});

// Download map with imported oligos

function downloadMapWithImportedOligos(event) {
  $.ajax({
    url: event.srcElement.attributes.download_url.value,
    cache: false,
    xhrFields: {
      responseType: "blob"
    },

    beforeSend: function (html) {
      ShowLoading();
    },

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
