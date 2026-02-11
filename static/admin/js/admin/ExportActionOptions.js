$(document).ready(function () {
  function removeCustomActionDropdown() {
    if ($("#changelist-form").find("label").length > 1) {
      $("#changelist-form").find("label")[1].remove();
    }
  }

  // Get the Action dropdown menu
  let actionDropDown = $("#changelist-form").find("select").first();

  actionDropDown.change(function () {
    if ($(this).val().startsWith("export_")) {
      // If export action is selected, add file type dropdown
      removeCustomActionDropdown();

      // Disable this for now, as there are separate export actions for
      // different formats
      return;

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
      // If create label action is selected, add label format dropdown
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
    } else if ($(this).val() == "formz_as_html") {
      // If formz_as_html action is selected, add dropdown for plasmid map attachment options
      if ($("#changelist-form").find("label").length > 1) {
        $("#changelist-form").find("label")[1].remove();
      }

      // Create new label for plasmid map attachment options
      var select_attach_element = document.createElement("label");
      select_attach_element.innerText = "Plasmid map attachment: ";
      select_attach_element.style.cssText = "padding-left: 1em;";

      // Create dropdown for plasmid map attachment options
      var select_attach_box = document.createElement("select");
      select_attach_box.name = "map_attachment_type";

      // Create options for dropdown
      var option_none = document.createElement("option");
      option_none.innerText = "None";
      option_none.value = "none";

      // Option for PNG attachment
      var option_png = document.createElement("option");
      option_png.innerText = ".png";
      option_png.value = "png";

      // Option for GBK attachment
      var option_gbk = document.createElement("option");
      option_gbk.innerText = ".gbk";
      option_gbk.value = "gbk";

      // Add options to dropdown
      select_attach_box.appendChild(option_none);
      select_attach_box.appendChild(option_png);
      select_attach_box.appendChild(option_gbk);

      // Add dropdown to label
      select_attach_element.appendChild(select_attach_box);
      $("#changelist-form").find("label")[0].append(select_attach_element);
    } else {
      removeCustomActionDropdown();
    }
  });
});
