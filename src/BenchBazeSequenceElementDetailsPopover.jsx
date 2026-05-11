import React from "react";
import { Button, Popover, Position } from "@blueprintjs/core";
import {
  getSequenceFeatureValue,
  normalizeSequenceElementOptionsWithMetadata,
} from "./BenchBazeMapViewerUtils.jsx";
import { SEQUENCE_FEATURE_DETAILS_FRONTEND_URL } from "./BenchBazeMapViewerUtils.jsx";

export default function BenchBazeSequenceElementDetailsPopover({
  feature,
  hasSelectedItemMetadata,
  isOpen,
  onOpen,
  onClose,
  popoverClassName,
  detailsContainerRef,
  stopRowSelection,
}) {
  // Popover component that displays detailed information about a sequence element
  // when the user clicks the "View details"/✎ button in the properties panel.
  // It retrieves necessary data from the feature object, and constructs a link
  // to the feature details page if an ID is available

  // Determine the value to display for the sequence element
  const value =
    feature.benchBazeSequenceElement ||
    getSequenceFeatureValue(feature, "bb_feat_name") ||
    "";

  // Normalize the options and metadata for the sequence element to prepare for display
  const normalizedOptions = normalizeSequenceElementOptionsWithMetadata(
    feature.benchBazeSequenceElementOptions,
  );
  const selectedOptionMetadata =
    normalizedOptions.metadataByName[value] ||
    feature.benchBazeSequenceElementSelectedMetadata ||
    {};

  const featureId = getSequenceFeatureValue(feature, "bb_feat_id");
  const featureUrl = featureId
    ? SEQUENCE_FEATURE_DETAILS_FRONTEND_URL(featureId)
    : null;

  // Define the fields to display in the popover, along with their corresponding keys
  // in the metadata
  const fieldKeyLabelMappings = [
    { label: "Name", key: "bb_feat_name" },
    { label: "Donor", key: "bb_feat_org" },
    { label: "Donor risk", key: "bb_feat_org_risk" },
    { label: "Nucleic acid purity", key: "bb_feat_nuc_pur" },
    { label: "Nucleic acid risk", key: "bb_feat_nuc_risk" },
    { label: "Oncogene", key: "bb_feat_oncogene" },
  ];

  // Get field values for display, prioritizing selected option metadata, then detected
  // feature values, and defaulting to "none"
  const fieldValues = fieldKeyLabelMappings.map((field) => {
    return {
      ...field,
      value:
        selectedOptionMetadata[field.key] ||
        getSequenceFeatureValue(feature, field.key) ||
        "none",
    };
  });

  // Function to open the feature details page in a new popup window
  const openFeatureDetailsPopup = (url) => {
    const popupUrl = `${url}?_popup=1`;
    const name = "feature_details_popup";
    const specs = "width=800,height=500,resizable=yes,scrollbars=yes";

    window.open(popupUrl, name, specs);
  };

  // Function to render the value for each field in the popover
  const renderFieldValue = (field) => {
    if (!field.value) {
      return "none";
    }

    // For the "Name" field, if a feature URL is available, render it as a clickable link
    if (field.label === "Name" && featureUrl) {
      return (
        <a
          href={featureUrl}
          target="_blank"
          rel="noreferrer noopener"
          onClick={(event) => {
            event.preventDefault();
            openFeatureDetailsPopup(featureUrl);
          }}
        >
          {field.value}
        </a>
      );
    }

    // For the "Donor" field, render the value as HTML to allow for rich text formatting
    // because for Latin species names, they are passed as, for example, <i>Escherichia coli</i>
    if (field.label === "Donor") {
      return (
        <span
          dangerouslySetInnerHTML={{
            __html: field.value,
          }}
        />
      );
    }

    return field.value;
  };

  return (
    <Popover
      content={
        <div
          className="bb-detected-feature-popover-content"
          onMouseDown={stopRowSelection}
          onClick={stopRowSelection}
        >
          {fieldValues.map((field) => (
            <div className="bb-detected-feature-details-row" key={field.key}>
              <strong>{field.label}:</strong> {renderFieldValue(field)}
            </div>
          ))}

          <Button
            minimal
            small
            icon="cross"
            className="bb-detected-feature-popover-close-button"
            onMouseDown={stopRowSelection}
            onClick={(event) => {
              stopRowSelection(event);
              onClose();
            }}
          />
        </div>
      }
      minimal
      position={Position.RIGHT_TOP}
      interactionKind="CLICK"
      popoverClassName={popoverClassName}
      usePortal
      isOpen={isOpen}
      onInteraction={(nextOpen) => {
        if (!nextOpen) {
          onClose();
        }
      }}
    >
      <div ref={detailsContainerRef}>
        <Button
          minimal
          icon="edit"
          text={hasSelectedItemMetadata ? "Open" : undefined}
          title="View details"
          aria-label="View details"
          disabled={!value}
          onMouseDown={stopRowSelection}
          onClick={(e) => {
            e.stopPropagation();
            if (isOpen) {
              onClose();
              return;
            }
            onOpen();
          }}
        />
      </div>
    </Popover>
  );
}
