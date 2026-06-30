import React from "react";
import { Menu, MenuItem } from "@blueprintjs/core";
import { svgStylePropsToExport } from "./styleProperties";
import { toastr } from "./toaster";
import { getCookie } from "./App.helpers";

const SUPPORTED_FILE_FORMATS_SNAPGENE = [".dna"];
const SUPPORTED_FILE_FORMATS_GENBANK = [".gbk", ".gb"];
const SUPPORTED_FILE_FORMATS = [
  ...SUPPORTED_FILE_FORMATS_GENBANK,
  ...SUPPORTED_FILE_FORMATS_SNAPGENE,
];
const TYPE_COLOUR_MAP = {
  matched: "#55a768",
  original_only: "#dd8452",
  processed_only: "#4c72b0",
};

export const SEQUENCE_FEATURE_BASE_API_URL = "/api/formz/sequencefeature/";
export const SEQUENCE_FEATURE_OPTIONS_API_URL = `${SEQUENCE_FEATURE_BASE_API_URL}autocomplete/`;
export const SEQUENCE_FEATURE_DETAILS_API_URL = (id) =>
  `${SEQUENCE_FEATURE_BASE_API_URL}${id}/`;
export const SEQUENCE_FEATURE_DETAILS_FRONTEND_URL = (id) =>
  `/formz/sequencefeature/${id}/change/`;
export const SEQUENCE_FEATURE_ADD_URL = "/formz/sequencefeature/add/";

function normalizeFileFormat(fileFormat) {
  return String(fileFormat || "").toLowerCase();
}

function replaceFileExtension(fileName, extension) {
  const sanitizedName = sanitizeFileName(fileName || "sequence");
  const baseName = sanitizedName.replace(/\.[^.]+$/, "") || "sequence";

  return `${baseName}${extension}`;
}

function sanitizeFileName(name) {
  // Basic sanitization to ensure the file name is not empty and
  // does not contain only whitespace, if enabled

  const fileName = name || "sequence";

  // Optional sanitization to ensure the file name is safe for most file systems.
  // Uncomment if needed.
  // return fileName
  //   .replace(/[\\/:*?"<>]+/g, "_")
  //   .replace(/^_+|_+$/g, "");
  return fileName;
}

function triggerBlobDownload(blob, downloadName) {
  // Create a temporary link element and trigger its download

  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = downloadName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(blobUrl);
}

function parseContentDispositionFileName(header) {
  if (!header) {
    return null;
  }

  const match = header.match(/filename="([^\"]+)"/);
  return match ? match[1] : null;
}

function getFileNameFromPath(pathOrUrl) {
  // Extract the file name from a given path or URL, ignoring query
  // parameters and fragments

  if (!pathOrUrl) return "sequence";
  const cleanPath = String(pathOrUrl).split("?")[0].split("#")[0];
  const segments = cleanPath.split("/").filter(Boolean);
  return segments.length ? segments[segments.length - 1] : "sequence";
}

function getFileBaseNameFromPath(pathOrUrl) {
  // Extract the base file name (without extension) from a given path or URL

  const fileName = getFileNameFromPath(pathOrUrl);
  const lastDotIndex = fileName.lastIndexOf(".");
  if (lastDotIndex <= 0 || lastDotIndex === fileName.length - 1) {
    return fileName;
  }
  return fileName.slice(0, lastDotIndex);
}

function getFileExtensionFromPath(pathOrUrl) {
  // Extract the file extension from a given path or URL,
  // returning an empty string if none found

  const fileName = getFileNameFromPath(pathOrUrl);
  const lastDotIndex = fileName.lastIndexOf(".");
  if (lastDotIndex <= 0 || lastDotIndex === fileName.length - 1) {
    return "";
  }
  return fileName.slice(lastDotIndex);
}

export function getSequenceFeatureValue(feature, field) {
  // Helper function to get the value of a detected feature field from the feature notes,
  // handling the case where the field value may be an array or a single value.
  // For OVE JSON, this should always be an array

  const fieldValue = feature.notes?.[field];
  return Array.isArray(fieldValue) ? fieldValue[0] : fieldValue;
}

export function normalizeSequenceElementOptionsWithMetadata(rawOptions) {
  // Normalizes a mixed array of string/object sequence element options into
  // a consistent { names, metadataByName } shape used for rendering and lookup.
  // Also supports paginated response shapes returned by the autocomplete API.

  if (!rawOptions || typeof rawOptions !== "object") {
    return { names: [], metadataByName: {} };
  }

  const options = Array.isArray(rawOptions)
    ? rawOptions
    : Array.isArray(rawOptions.results)
      ? rawOptions.results
      : Array.isArray(rawOptions.options)
        ? rawOptions.options
        : [];

  const names = [];
  const metadataByName = {};

  for (const option of options) {
    if (typeof option === "string") {
      names.push(option);
      continue;
    }

    if (!option || typeof option !== "object") {
      continue;
    }

    const name =
      option.name || option.value || option.label || option.representation;
    if (!name) {
      continue;
    }

    names.push(name);
    metadataByName[name] = option;
  }

  return { names, metadataByName };
}

export function downloadMapFile(fileOrUrl, title) {
  // Download map file directly from a File/Blob or from a URL.
  if (!fileOrUrl) {
    toastr.error("Map file not found");
    return;
  }

  let extension;
  let downloadName;
  let href;
  let revokeUrl = false;

  if (fileOrUrl instanceof Blob) {
    extension = getFileExtensionFromPath(fileOrUrl.name);
    href = URL.createObjectURL(fileOrUrl);
    revokeUrl = true;
  } else {
    extension = getFileExtensionFromPath(fileOrUrl);
    href = fileOrUrl;
  }

  downloadName = `${sanitizeFileName(title || "BenchBaze Map")} [imported-oligos]${extension}`;

  const link = document.createElement("a");
  link.href = href;
  link.download = downloadName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  if (revokeUrl) {
    URL.revokeObjectURL(href);
  }

  toastr.success("Map downloaded");
}

function applyInlineSvgStyles(sourceNode, clonedNode) {
  // This is for the circular/linear exporter
  // Recursively copy specific styles from the live SVG to the cloned SVG element
  // Ugly but ensures that the exported SVG looks correct
  // I tried copying all styles in a style tag, but the SVG then did not render

  // Only apply to element nodes
  if (!(sourceNode instanceof Element) || !(clonedNode instanceof Element)) {
    return;
  }

  // Copy only the style properties defined in svgStylePropsToExport
  // This appears to be sufficient
  const computedStyle = window.getComputedStyle(sourceNode);
  svgStylePropsToExport.forEach((propertyName) => {
    const propertyValue = computedStyle.getPropertyValue(propertyName);
    if (propertyValue) {
      clonedNode.style.setProperty(propertyName, propertyValue);
    }
  });

  // Recursively apply to all children
  Array.from(sourceNode.children).forEach((childNode, index) => {
    applyInlineSvgStyles(childNode, clonedNode.children[index]);
  });
}

function withForcedLightTheme(exportCallback) {
  // This is for the circular/linear exporter
  // Temporarily remove dark mode classes to ensure that computed styles
  // resolve to light mode for export output.
  // Ugly but it allows to reuse the existing styles without a separate set
  // of styles for export. This will change the style of the circular/linear
  // views briefly back to light, mostly the line colours. The export should
  // be fast enough that this is not noticeable.

  const darkThemeNodes = Array.from(document.querySelectorAll(".bp3-dark"));
  darkThemeNodes.forEach((node) => node.classList.remove("bp3-dark"));

  try {
    return exportCallback();
  } finally {
    darkThemeNodes.forEach((node) => node.classList.add("bp3-dark"));
  }
}

function downloadCircularViewSvg(title) {
  // Download the circular view as an HTML file with embedded SVG content.

  withForcedLightTheme(() => {
    // Find the SVG element for the circular view
    const svgEl = document.querySelector(".veCircularView .circularViewSvg");
    if (!svgEl) {
      toastr.error("Map view not found");
      return;
    }

    // Clone the SVG element and ensure necessary namespaces and styles are included
    const svgClone = svgEl.cloneNode(true);
    applyInlineSvgStyles(svgEl, svgClone);
    if (!svgClone.getAttribute("xmlns")) {
      svgClone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    }
    if (!svgClone.getAttribute("xmlns:xlink")) {
      svgClone.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
    }

    // Ensure the cloned SVG has the correct styles for proper rendering when opened as a standalone file
    svgClone.setAttribute(
      "style",
      "overflow:visible;" +
        "display:block;" +
        "text-align:center;" +
        "font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Oxygen,Ubuntu,Cantarell,Fira Sans,Droid Sans,Helvetica Neue,sans-serif",
    );
    svgClone.setAttribute("class", "circularViewSvg");
    svgClone.setAttribute("width", "100%");
    svgClone.setAttribute("height", "100%");

    // Convert the cloned SVG element to a string
    const svgText = new XMLSerializer().serializeToString(svgClone);
    // Export an HTML file embedding the SVG for easier browser viewing/sharing
    const html = `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>${sanitizeFileName(title)} - Circular View</title>
<style>
  html, body {
    margin: 0;
    width: 100%;
    height: 100%;
    background: #ffffff;
  }
  body {
    display: grid;
    place-items: center;
    padding: 16px;
    box-sizing: border-box;
  }
  .circularViewExport {
    width: min(96vw, 1200px);
    height: min(96vh, 1200px);
  }
  .circularViewExport svg {
    width: 100%;
    height: 100%;
    display: block;
  }
</style>
</head>
<body>
  <div class="circularViewExport">${svgText}</div>
</body>
</html>`;
    const htmlBlob = new Blob([html], { type: "text/html;charset=utf-8" });

    triggerBlobDownload(
      htmlBlob,
      `${sanitizeFileName(title)} [preview-circular].html`,
    );
    toastr.success("Map preview downloaded");
  });
}

function applyComputedStylesToElement(sourceNode, clonedNode) {
  // This is for the circular/linear exporter
  // Recursively copy relevant styles from the live Linear View to the cloned one

  // Only apply to element nodes
  if (!(sourceNode instanceof Element) || !(clonedNode instanceof Element)) {
    return;
  }

  // Get computed styles of the source node and copy all properties that have a value
  const computedStyle = window.getComputedStyle(sourceNode);
  // Copy all style properties that are not default values
  for (let i = 0; i < computedStyle.length; i++) {
    const propertyName = computedStyle[i];
    const propertyValue = computedStyle.getPropertyValue(propertyName);
    // Skip properties that have no value or are default/neutral values that don't affect appearance
    if (
      propertyValue &&
      propertyValue !== "auto" &&
      propertyValue !== "0" &&
      propertyValue !== "none"
    ) {
      try {
        clonedNode.style.setProperty(
          propertyName,
          propertyValue,
          computedStyle.getPropertyPriority(propertyName),
        );
      } catch (e) {
        // Skip properties that can't be set
      }
    }
  }

  // Recursively apply to all children
  Array.from(sourceNode.children).forEach((childNode, index) => {
    if (clonedNode.children[index]) {
      applyComputedStylesToElement(childNode, clonedNode.children[index]);
    }
  });
}

function downloadLinearViewHtml(title) {
  // Download the linear view as an HTML file with embedded styles, to account for the fact
  // that the linear view relies on complex CSS for its layout and appearance

  withForcedLightTheme(() => {
    // Find the root element of the linear view to clone
    const linearRoot = document.querySelector(".veLinearView");
    if (!linearRoot) {
      toastr.error("Map view not found");
      return;
    }

    // Clone the root and apply computed styles
    const clonedRoot = linearRoot.cloneNode(true);

    // Remove the zoom slider from the cloned element
    const zoomSlider = clonedRoot.querySelector(".veZoomLinearSlider");
    if (zoomSlider) {
      zoomSlider.remove();
    }

    applyComputedStylesToElement(linearRoot, clonedRoot);

    // Clone the styles from the current document as a fallback
    const clonedHead = Array.from(
      document.querySelectorAll("head style, head link[rel='stylesheet']"),
    )
      .map((el) => el.outerHTML)
      .join("\n");

    // Create a wrapper div to hold the cloned linear view content and apply necessary styles
    const wrapper = document.createElement("div");
    wrapper.className = "veLinearViewExport";
    wrapper.style.padding = "16px";
    wrapper.style.background = "#fff";
    wrapper.style.width = "100%";
    wrapper.style.boxSizing = "border-box";
    wrapper.appendChild(clonedRoot);

    const html = `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>${sanitizeFileName(title)} - Linear View</title>
${clonedHead}
<style>
  html, body {
    margin: 0;
    background: #ffffff;
  }
  .veLinearViewExport {
    overflow: auto;
  }
</style>
</head>
<body>
${wrapper.outerHTML}
</body>
</html>`;

    // Create a Blob from the HTML string and trigger the download
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    triggerBlobDownload(
      blob,
      `${sanitizeFileName(title)} [preview-linear].html`,
    );
    toastr.success("Map preview downloaded");
  });
}

export function downloadMapPreview(title) {
  // Determine which view is currently active and trigger the appropriate download function
  const isLinearActive = Boolean(
    document.querySelector(".veTabActive.veTabLinearMap"),
  );
  const isCircularActive = Boolean(
    document.querySelector(".veTabActive.veTabCircularMap"),
  );

  if (isLinearActive) {
    downloadLinearViewHtml(title);
    return;
  }
  if (isCircularActive) {
    downloadCircularViewSvg(title);
    return;
  }

  // Fallback if active tab classes are unavailable.
  if (document.querySelector(".veCircularView .circularViewSvg")) {
    downloadCircularViewSvg(title);
    return;
  }
  if (document.querySelector(".veLinearView")) {
    downloadLinearViewHtml(title);
    return;
  }

  toastr.error("Map view not found");
}

// export function DownloadMapFileDropdown(props) {
//   // Single-action dropdown for downloading original map file
//   const { sequenceData, toggleDropdown, title, fileName } = props;

//   return (
//     <Menu>
//       <MenuItem
//         text="Download Map File"
//         onClick={() => {
//           downloadMapFile(fileName, title || sequenceData?.name);
//           toggleDropdown({ forceClose: true });
//         }}
//       />
//     </Menu>
//   );
// }

// export function DownloadMapPreviewDropdown(props) {
//   // Single-action dropdown for downloading currently active view preview
//   const { sequenceData, toggleDropdown, title } = props;

//   return (
//     <Menu>
//       <MenuItem
//         text="Download Map Preview"
//         onClick={() => {
//           downloadMapPreview(title || sequenceData?.name);
//           toggleDropdown({ forceClose: true });
//         }}
//       />
//     </Menu>
//   );
// }

function reformatMapFeatures(mapDnaJson) {
  // Reformat the features in the parsed sequence so that their colours are set
  // based on the detected feature type (matched, original only, processed only).

  if (!mapDnaJson || !Array.isArray(mapDnaJson.features)) {
    return mapDnaJson;
  }

  mapDnaJson.features.forEach((feature) => {
    if (!feature || typeof feature !== "object") return;

    // Determine the detected feature type from the notes
    const detectedTypeRaw = feature.notes?.bb_feat_type;
    const detectedType = Array.isArray(detectedTypeRaw)
      ? detectedTypeRaw[0]
      : detectedTypeRaw;

    // Get the corresponding color for the detected feature type
    const newColor = TYPE_COLOUR_MAP[detectedType];

    if (!newColor) return;
    // If the feature already has a color, move it to color_original
    if (feature.hasOwnProperty("color")) {
      if (!feature.hasOwnProperty("color_original")) {
        feature.color_original = feature.color;
      }
    }

    feature.color = newColor;
    feature.color_detected_feature = true;
    delete feature.notes.bb_feat_type;
  });

  return mapDnaJson;
}

export async function getMapFileWithOligos(fileName) {
  // Fetch the map file with oligos from the server
  const csrfToken = getCookie("csrftoken");
  const formData = new FormData();
  formData.append("map_file_path", fileName);

  const response = await fetch("/utils/map_dna/find_oligos_in_map/", {
    method: "POST",
    credentials: "same-origin",
    headers: csrfToken ? { "X-CSRFToken": csrfToken } : undefined,
    body: formData,
  });

  if (!response.ok) {
    throw new Error(
      `Failed to find oligos in map file (Error ${response.status}).`,
    );
  }

  const blob = await response.blob();
  const contentDisposition = response.headers.get("Content-Disposition");
  const fileNameFromHeader =
    parseContentDispositionFileName(contentDisposition);
  const finalFileName = fileNameFromHeader || getFileNameFromPath(fileName);

  return new File([blob], finalFileName, {
    type: "application/octet-stream",
  });
}

export async function convertMapToOveJson({
  fileName,
  payload,
  detectFeatures = false,
} = {}) {
  const formData = new FormData();

  // If a payload is provided (posted mode), append it to the form data
  if (payload) {
    const { mapFile } = payload;
    if (!(mapFile instanceof Blob)) {
      throw new Error("Missing posted map file object.");
    }

    const postedFileName = mapFile.name || "posted_map";
    const normalizedFileFormat = normalizeFileFormat(
      postedFileName ? getFileExtensionFromPath(postedFileName) : null,
    );
    if (!SUPPORTED_FILE_FORMATS.includes(normalizedFileFormat)) {
      throw new Error(
        `Unsupported posted file format "${normalizedFileFormat}". ` +
          `Supported formats: ${SUPPORTED_FILE_FORMATS.map((f) => `"${f}"`).join(", ")}.`,
      );
    }

    formData.append("map_file_content", mapFile);
    formData.append("map_file_name", postedFileName);
    formData.append("map_file_format", normalizedFileFormat);
  }
  // Otherwise append the file path
  else {
    if (!fileName) {
      throw new Error("Missing map file.");
    }

    formData.append("map_file_path", fileName);
  }

  if (detectFeatures) {
    formData.append("detect_features", "true");
  }

  // Send the form data to the server for conversion to OVE JSON
  const csrfToken = getCookie("csrftoken");
  const response = await fetch("/utils/map_dna/convert_any_to_ove_json/", {
    method: "POST",
    credentials: "same-origin",
    headers: csrfToken ? { "X-CSRFToken": csrfToken } : undefined,
    body: formData,
  });

  if (!response.ok) {
    throw new Error(
      `Failed to convert map file to OVE JSON (Error ${response.status}).`,
    );
  }

  // Parse the JSON response and extract the parsed sequence
  const responseJson = await response.json();
  const parsedSequence = responseJson?.[0]?.parsedSequence;

  if (!parsedSequence) {
    throw new Error(
      payload
        ? "Posted map file cannot be parsed."
        : "The map file cannot be parsed.",
    );
  }

  return payload ? reformatMapFeatures(parsedSequence) : parsedSequence;
}

function reformatProcessedMap(mapDnaJson) {
  //   Restore colors by moving any color_original values back to the color property and
  //   removing color if no original color exists.
  //   This removes any temporary color overrides applied to show detected features vs original features
  //   Also remove the following notes, if they still exist: bb_feat_type

  for (const feature of Object.values(mapDnaJson.features || {})) {
    if (!feature || typeof feature !== "object") continue;
    if (feature.hasOwnProperty("color_detected_feature")) {
      if (feature.hasOwnProperty("color_original")) {
        [feature.color, feature.color_original] = [
          feature.color_original,
          feature.color,
        ];
        delete feature.color_original;
      } else {
        delete feature.color;
      }
    }

    const notes = feature.notes || {};
    delete notes.bb_feat_type;
  }
  return mapDnaJson;
}

export function restoreOriginalFeatureColors(sequenceDataJson) {
  if (!sequenceDataJson || typeof sequenceDataJson !== "object") {
    return sequenceDataJson;
  }

  const clonedDataJson = structuredClone(sequenceDataJson);

  for (const feature of Object.values(clonedDataJson.features || {})) {
    if (!feature || typeof feature !== "object") continue;
    if (feature.hasOwnProperty("color_detected_feature")) {
      if (feature.hasOwnProperty("color_original")) {
        [feature.color, feature.color_original] = [
          feature.color_original,
          feature.color,
        ];
        delete feature.color_original;
      } else {
        delete feature.color;
      }
    }
  }

  return clonedDataJson;
}

function normalizeFeatureNoteValues(obj) {
  // Ensure that all note values are strings or arrays of strings, as expected by bio-parsers when exporting to GenBank.

  for (const entry of Object.values(obj.features || {})) {
    if (!entry || typeof entry !== "object") continue;

    const notes = entry.notes;
    if (!notes || typeof notes !== "object") continue;

    // Convert all note values to arrays of strings
    Object.keys(notes).forEach((key) => {
      const value = notes[key];

      // If the value is already an array, convert all items to strings
      if (Array.isArray(value)) {
        notes[key] = value.map((item) => {
          if (item === null || item === undefined) {
            return "";
          }
          if (typeof item === "object") {
            try {
              return JSON.stringify(item);
            } catch (e) {
              return String(item);
            }
          }
          return String(item);
        });
      } else if (value === null || value === undefined) {
        // If the value is a single item, convert it to a single-item array of string
        notes[key] = [""];
      } else {
        // If the value is an object, attempt to stringify it
        notes[key] = [String(value)];
      }
    });
  }

  return obj;
}

export function getSequenceFeatureIds(mapDna) {
  // Extract the IDs of the sequence features from the map data
  const featureIds = [];
  for (const [key, feature] of Object.entries(mapDna.features || {})) {
    if (feature && feature.notes && feature.notes.bb_feat_id) {
      if (Array.isArray(feature.notes.bb_feat_id)) {
        featureIds.push(...feature.notes.bb_feat_id);
      } else {
        featureIds.push(feature.notes.bb_feat_id);
      }
    }
  }
  return featureIds;
}

export async function saveToFile(sequenceDataJson, originalFile) {
  // Save the edited sequence data as a new file .
  // For GenBank format we can create the final file directly with bio-parsers,
  // for SnapGene format we need to send the edited sequence data back to the server
  // to create a new .dna file with the original file's metadata (e.g. features,
  // primers, etc) intact.

  if (!sequenceDataJson || typeof sequenceDataJson !== "object") {
    throw new Error("Missing edited sequence data.");
  }

  let clonedDataJson = structuredClone(sequenceDataJson);
  const fileName = originalFile?.name || "edited_sequence";
  const normalizedFileFormat = normalizeFileFormat(
    originalFile?.name ? getFileExtensionFromPath(originalFile.name) : null,
  );
  if (!SUPPORTED_FILE_FORMATS.includes(normalizedFileFormat)) {
    throw new Error(
      `Unsupported save file format "${normalizedFileFormat}". ` +
        `Supported formats: ${SUPPORTED_FILE_FORMATS.map((f) => `".${f}"`).join(", ")}.`,
    );
  }

  // Get the  IDs of the BenchBaze sequence features
  const sequenceFeatureIds = getSequenceFeatureIds(sequenceDataJson);

  // Remove temporary colours used during feature detection
  clonedDataJson = reformatProcessedMap(clonedDataJson);

  // Ensure note values are strings before exporting to GenBank.
  // @teselagen/bio-parsers expects that
  clonedDataJson = normalizeFeatureNoteValues(clonedDataJson);

  const { jsonToGenbank } = await import("@teselagen/bio-parsers");

  // Create map file to save back to the parent form on the server
  const formData = new FormData();
  formData.append("map_file_name", fileName);
  formData.append("map_file_format", normalizedFileFormat);

  let contentType;

  // Genbank
  if (SUPPORTED_FILE_FORMATS_GENBANK.includes(normalizedFileFormat)) {
    // For GenBank convert clonedDataJson back to GenBank format first using bio-parsers,
    // then send the GenBank file back to the server to be re-saved as GenBank by
    // Biopython to ensure that the file is properly formatted
    const genBankData = await jsonToGenbank(clonedDataJson);
    const genBankBlob = new Blob([genBankData], {
      type: "text/plain;charset=utf-8",
    });
    formData.append("map_file_edited_gb", genBankBlob);

    contentType = "text/plain;charset=utf-8";
  }
  // SnapGene
  // Send the OVE JSON map back to the server along with the original .dna file,
  // then save the .dna file on the server using the original file as base and update its features,
  // primers and sequence based on the edited sequence data
  else if (SUPPORTED_FILE_FORMATS_SNAPGENE.includes(normalizedFileFormat)) {
    formData.append("map_file_original_sg", originalFile);
    formData.append("map_file_edited_json", JSON.stringify(clonedDataJson));
    contentType = "application/octet-stream";
  } else {
    throw new Error("Unsupported file format.");
  }

  // Create new file on the server
  const csrfToken = getCookie("csrftoken");
  const response = await fetch("/utils/map_dna/create_map_file/", {
    method: "POST",
    credentials: "same-origin",
    headers: csrfToken ? { "X-CSRFToken": csrfToken } : undefined,
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Failed to save map (Error ${response.status}).`);
  }

  // Get response file content as a Blob and create a new File object to return to the parent form
  const outMapData = await response.blob();

  const fileBaseName = getFileBaseNameFromPath(fileName);
  const exportedFileName = replaceFileExtension(
    fileBaseName.endsWith("_edited")
      ? fileName
      : fileBaseName + "_edited" + getFileExtensionFromPath(fileName),
    normalizedFileFormat,
  );

  return {
    file: new File([outMapData], exportedFileName, {
      type: contentType,
    }),
    sequenceFeatureIds: sequenceFeatureIds,
  };
}
