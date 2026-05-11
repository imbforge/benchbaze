(function ($) {
  $(document).ready(async function () {
    // Hydrate the form fields from a tokenized payload stored in the opener window.
    // This avoids sending the full plannot_description in the popup URL, which can
    // cause problems when fields, for example, the description field, are large
    const url = new URL(window.location.href);
    const params = new URLSearchParams(url.search);
    const token = params.get("plannot_token");

    const payload =
      token &&
      window.opener &&
      window.opener.__bbSequenceElementPayloads &&
      window.opener.__bbSequenceElementPayloads[token];

    // Utility function to set the value of a select2 field, which is required for the
    // donor organism field because it uses select2 with autocomplete.
    // N.B.: Must trigger the change event for select2 to make it recognize that the
    // value has been set
    const setSelect2Value = (select, value, text) => {
      // Set the value of a select2 field, adding the option if it doesn't already exist
      if (!select || !value) {
        return;
      }

      let option = select.querySelector(`option[value="${value}"]`);
      if (!option) {
        option = document.createElement("option");
        option.value = value;
        option.text = text || value;
        select.appendChild(option);
      }

      option.selected = true;
      select.dispatchEvent(new Event("change", { bubbles: true }));
    };

    const findSpeciesNameFromPayload = (payload) => {
      // Try to extract the species name from the plannot_description using regex patterns
      // This is database-specific because SwissProt and FPbase use different description formats
      // Swissprot example: "From Escherichia coli (strain K12)"
      // FPbase example: "derived from Escherichia coli str. K-12"

      const database = (payload.plannot_database || "").toLowerCase();
      const description = payload.plannot_description || "";
      if (!description) {
        return null;
      }

      const swissprotRegex =
        /From\s*([A-Za-z][A-Za-z0-9.\-]*(?:\s+[A-Za-z0-9.\-]+)*)(?=\s*(?:\(|,|;|\.|$))/;
      const fpbaseRegex =
        /derived from\s+([A-Za-z][A-Za-z0-9 .#\-]+?)(?=\s*\.(?:\s*\||\s+[A-Z]|\s*$))/;

      if (["swissprot", "snapgene"].includes(database)) {
        const match = description.match(swissprotRegex);
        return match ? match[1] : null;
      }

      if (database === "fpbase") {
        const match = description.match(fpbaseRegex);
        return match ? match[1] : null;
      }

      return null;
    };

    const getAutocompleteUrl = (select) => {
      // Construct the autocomplete URL for the donor organism field based on data attributes
      // set by Django's autocomplete view

      if (!select) {
        return null;
      }

      const urlBase =
        select.dataset.ajaxUrl || select.getAttribute("data-ajax--url");
      const appLabel =
        select.dataset.appLabel || select.getAttribute("data-app-label");
      const modelName =
        select.dataset.modelName || select.getAttribute("data-model-name");
      const fieldName =
        select.dataset.fieldName || select.getAttribute("data-field-name");

      if (!urlBase || !appLabel || !modelName || !fieldName) {
        return null;
      }

      const url = new URL(urlBase, window.location.origin);
      url.searchParams.set("app_label", appLabel);
      url.searchParams.set("model_name", modelName);
      url.searchParams.set("field_name", fieldName);
      return url.toString();
    };

    const fetchAutocompleteResult = async (select, searchTerm) => {
      // Fetch the autocomplete results for the donor organism field and return the first result,
      // which should be the best match for the species name

      const autocompleteUrl = getAutocompleteUrl(select);

      if (!autocompleteUrl || !searchTerm) {
        return null;
      }

      const url = new URL(autocompleteUrl, window.location.origin);
      url.searchParams.set("term", searchTerm);

      // Get options
      try {
        const response = await fetch(url.toString(), {
          headers: { Accept: "application/json" }
        });
        if (!response.ok) {
          return null;
        }
        const data = await response.json();
        if (Array.isArray(data.results) && data.results.length > 0) {
          return data.results[0];
        }
      } catch (error) {
        console.error(
          "Failed to load donor organism autocomplete result:",
          error
        );
      }
      return null;
    };

    // If there is a payload, use it to pre-fill the form fields. Only fill the fields
    // if they are empty to avoid overwriting any user input
    if (payload) {
      const nameInput = document.getElementById("id_name");
      if (nameInput && !nameInput.value && payload.plannot_label) {
        nameInput.value = payload.plannot_label.replace(/ \(fragment\)$/, "");
      }

      const aliasInput = document.getElementById("id_alias-0-label");
      if (aliasInput && !aliasInput.value && nameInput && nameInput.value) {
        aliasInput.value = nameInput.value;
      }

      // Add aliases in the inline
      const addAliasField = (value) => {
        const totalFormsInput = document.getElementById("id_alias-TOTAL_FORMS");
        const emptyRow = document.getElementById("alias-empty");
        if (!totalFormsInput || !emptyRow) {
          return;
        }

        // Clone the empty form, update the form index, and insert it into the DOM before the "Add another alias" row
        const newIndex = parseInt(totalFormsInput.value, 10);
        const clone = emptyRow.cloneNode(true);
        clone.id = `alias-${newIndex}`;
        clone.classList.remove("empty-form");
        clone.classList.add("dynamic-alias");

        clone.querySelectorAll("[id]").forEach((el) => {
          if (el.id) {
            el.id = el.id.replace("__prefix__", String(newIndex));
          }
        });
        clone.querySelectorAll("[name]").forEach((el) => {
          if (el.name) {
            el.name = el.name.replace("__prefix__", String(newIndex));
          }
        });
        clone.querySelectorAll("label[for]").forEach((el) => {
          if (el.htmlFor) {
            el.htmlFor = el.htmlFor.replace("__prefix__", String(newIndex));
          }
        });

        // Set the value of the label input in the new alias form
        const labelInputClone = clone.querySelector(
          `#id_alias-${newIndex}-label`
        );
        if (labelInputClone) {
          labelInputClone.value = value;
        }

        // Unhide the delete link in the cloned form
        const deleteLink = clone.querySelector(".inline-deletelink");
        if (deleteLink) {
          deleteLink.style.display = "";
        }

        // Insert the cloned form into the DOM before the "Add another alias" row
        const addRow = emptyRow.parentElement.querySelector("tr.add-row");
        if (addRow && addRow.parentElement) {
          addRow.parentElement.insertBefore(clone, addRow);
        }

        totalFormsInput.value = String(newIndex + 1);
      };

      // If the plannot_label is different from the name field and is not already included as an alias,
      // add it as a new alias
      if (
        payload.plannot_label &&
        nameInput &&
        nameInput.value &&
        payload.plannot_label !== nameInput.value
      ) {
        const existingAliasValues = Array.from(
          document.querySelectorAll('input[id^="id_alias-"][id$="-label"]')
        )
          .map((el) => el.value.trim())
          .filter(Boolean);
        if (!existingAliasValues.includes(payload.plannot_label)) {
          addAliasField(payload.plannot_label);
        }
      }

      // Description
      const descriptionInput = document.getElementById("id_description");
      if (
        descriptionInput &&
        !descriptionInput.value &&
        payload.plannot_description
      ) {
        descriptionInput.value = payload.plannot_description;
      }

      // Donor organism
      const donorSelect = document.getElementById("id_donor_organism");
      if (donorSelect && !donorSelect.value) {
        const speciesName = findSpeciesNameFromPayload(payload);
        if (speciesName) {
          const result = await fetchAutocompleteResult(
            donorSelect,
            speciesName
          );
          if (result && result.id) {
            setSelect2Value(donorSelect, result.id, result.text || speciesName);
          }
        }
      }

      delete window.opener.__bbSequenceElementPayloads[token];
    }

    // Before submitting the form, remove any query parameters from the form action URL that start with "plannot_"
    const form = document.getElementById("sequencefeature_form");
    if (form) {
      form.addEventListener("submit", function () {
        const actionUrl = new URL(window.location.href);
        const actionParams = new URLSearchParams(actionUrl.search);

        const keysToDelete = [];
        actionParams.forEach((value, key) => {
          if (key.startsWith("plannot_")) {
            keysToDelete.push(key);
          }
        });

        keysToDelete.forEach((key) => actionParams.delete(key));

        const newSearch = actionParams.toString();
        form.action = actionUrl.pathname + (newSearch ? "?" + newSearch : "");
      });
    }

    if (token) {
      params.delete("plannot_token");
      window.history.replaceState(
        null,
        "",
        url.pathname + (params.toString() ? "?" + params.toString() : "")
      );
    }
  });
})(django.jQuery);
