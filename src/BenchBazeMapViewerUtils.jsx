import React from "react";
import { Menu, MenuItem } from "@blueprintjs/core";
import { anyToJson } from "@teselagen/bio-parsers";
import { svgStylePropsToExport } from "./styleProperties";

function sanitizeFileName(name) {
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

function getFileNameFromPath(pathOrUrl) {
  // Extract the file name from a given path or URL, ignoring query
  // parameters and fragments
  if (!pathOrUrl) return "sequence";
  const cleanPath = String(pathOrUrl).split("?")[0].split("#")[0];
  const segments = cleanPath.split("/").filter(Boolean);
  return segments.length ? segments[segments.length - 1] : "sequence";
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

async function downloadOriginalMapFile(fileName, title) {
  // Download map file directly from a the original URL
  // supplied in the file_name GET parameter
  if (!fileName) {
    window.toastr?.error("Original file name not found");
    return;
  }

  const extension = getFileExtensionFromPath(fileName);
  const downloadName = `${sanitizeFileName(title || "sequence")}${extension}`;

  const link = document.createElement("a");
  link.href = fileName;
  link.download = downloadName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  window.toastr?.success("Original file downloaded");
}

function applyInlineSvgStyles(sourceNode, clonedNode) {
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

function downloadCircularViewSvg(title) {
  // Find the SVG element for the circular view
  const svgEl = document.querySelector(".veCircularView .circularViewSvg");
  if (!svgEl) {
    window.toastr?.error("Circular view element not found");
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

  // Convert the cloned SVG element to a string and create a Blob for downloading
  const svgText = new XMLSerializer().serializeToString(svgClone);
  const blob = new Blob([svgText], { type: "image/svg+xml;charset=utf-8" });
  triggerBlobDownload(
    blob,
    `${sanitizeFileName(title)} [preview-circular].svg`,
  );
  window.toastr?.success("Map preview downloaded");
}

function applyComputedStylesToElement(sourceNode, clonedNode) {
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
  // Find the root element of the linear view to clone
  const linearRoot = document.querySelector(".veLinearView");
  if (!linearRoot) {
    window.toastr?.error("Linear view element not found");
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
  triggerBlobDownload(blob, `${sanitizeFileName(title)} [preview-linear].html`);
  window.toastr?.success("Linear view HTML downloaded");
}

function downloadActiveView(title) {
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

  window.toastr?.error("No map view found to download");
}

export function DownloadDropdownWithSvg(props) {
  // Custom export menu
  const { sequenceData, toggleDropdown, title, fileName } = props;

  return (
    <Menu>
      <MenuItem
        text="Download Map File"
        onClick={async () => {
          await downloadOriginalMapFile(fileName, title || sequenceData?.name);
          toggleDropdown({ forceClose: true });
        }}
      />
      <MenuItem
        text="Download Map Preview"
        onClick={() => {
          downloadActiveView(title || sequenceData?.name);
          toggleDropdown({ forceClose: true });
        }}
      />
    </Menu>
  );
}

export async function convertPlasmiMapToOveJson(fileName, fileFormat) {
  let data = await fetch(
    new Request(fileName, {
      //probably don't need this header.. fetch should just work
      headers: { "X-Requested-With": "XMLHttpRequest" },
    }),
  )
    .then((response) => {
      if (fileFormat === "gbk") return response.text();
      else if (fileFormat === "dna") return response.blob();
    })
    .then((plasmidData) => anyToJson(plasmidData, { fileName })) //[0]["parsedSequence"])
    .catch(console.error);
  // console.log(`data:`, data); //is this defined and working?
  return data[0]["parsedSequence"];
}