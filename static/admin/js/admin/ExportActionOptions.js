$(document).ready(function () {
  function removeCustomActionDropdown() {
    if ($("#changelist-form").find("label").length > 1) {
      $("#changelist-form").find("label")[1].remove();
    }
  }

  // Get the Action dropdown menu
  let actionDropDown = $("#changelist-form").find("select").first();

  // If export action is selected, add file type dropdown
  actionDropDown.change(function () {
    if ($(this).val().startsWith("export_")) {
      removeCustomActionDropdown();

      // Create new label for format selection dropdown
      let selectAttachElement = document.createElement("label");
      selectAttachElement.innerText = "Format: ";
      selectAttachElement.style.cssText = "padding-left: 1em;";

      // Create dropdown
      let selectAttachBox = document.createElement("select");
      selectAttachBox.name = "format";

      // Create options for dropdown
      let optionTsv = document.createElement("option");
      optionTsv.innerText = "Tab-separated values";
      optionTsv.value = "tsv";

      let optionXlsx = document.createElement("option");
      optionXlsx.innerText = "Excel";
      optionXlsx.value = "xlsx";

      // Add options to dropdown
      selectAttachBox.appendChild(optionXlsx);
      selectAttachBox.appendChild(optionTsv);

      // Add dropdown to label
      selectAttachElement.appendChild(selectAttachBox);

      // Add dropdown element to form
      $("#changelist-form").find("label")[0].append(selectAttachElement);
    } else if ($(this).val().startsWith("create_label")) {
      removeCustomActionDropdown();

      // Create new label for format selection dropdown
      let selectAttachElement = document.createElement("label");
      selectAttachElement.innerText = "Format: ";
      selectAttachElement.style.cssText = "padding-left: 1em;";

      // Create dropdown
      let selectAttachBox = document.createElement("select");
      selectAttachBox.name = "format";

      // Create options for dropdown
      let optionZebraN0JTT = document.createElement("option");
      optionZebraN0JTT.innerText = "Zebra, 25.4×12.7 + Ø9.5 mm";
      optionZebraN0JTT.value = "N0JTT-183C1-2WH";

      // Add options to dropdown
      selectAttachBox.appendChild(optionZebraN0JTT);

      // Add dropdown to label
      selectAttachElement.appendChild(selectAttachBox);

      // Add dropdown element to form
      $("#changelist-form").find("label")[0].append(selectAttachElement);
    } else {
      removeCustomActionDropdown();
    }
  });
});
