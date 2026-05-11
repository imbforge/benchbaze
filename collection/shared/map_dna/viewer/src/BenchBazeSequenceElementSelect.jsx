import React from "react";
import {
  Button,
  InputGroup,
  Menu,
  MenuItem,
  Popover,
  Position,
} from "@blueprintjs/core";
import BenchBazeSequenceElementDetailsPopover from "./BenchBazeSequenceElementDetailsPopover.jsx";
import { normalizeSequenceElementOptionsWithMetadata } from "./BenchBazeMapViewerUtils.jsx";
import { getSequenceFeatureValue } from "./BenchBazeMapViewerUtils.jsx";
import { SEQUENCE_FEATURE_OPTIONS_API_URL, SEQUENCE_FEATURE_DETAILS_API_URL, SEQUENCE_FEATURE_ADD_URL } from "./BenchBazeMapViewerUtils.jsx"; 

// Closes a select menu "popover" when another instance dispatches the same event with a
// different menuId, so only one popover is open at a time
function useCloseOnOtherOpen(eventName, menuId, setOpen) {
  React.useEffect(() => {
    const handler = (event) => {
      if (event.detail?.menuId !== menuId) {
        setOpen(false);
      }
    };
    window.addEventListener(eventName, handler);
    return () => window.removeEventListener(eventName, handler);
  }, [eventName, menuId, setOpen]);
}

// Closes a select menu "popover" when the user clicks outside both its trigger container
// and its portal element (identified by popoverClassName)
function useOutsideClick(isOpen, containerRef, popoverClassName, setOpen) {
  React.useEffect(() => {
    if (!isOpen) {
      return;
    }

    const handleMouseDown = (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      if (containerRef.current?.contains(target)) {
        return;
      }
      if (target.closest(`.${popoverClassName}`)) {
        return;
      }
      setOpen(false);
    };

    document.addEventListener("mousedown", handleMouseDown, true);
    return () =>
      document.removeEventListener("mousedown", handleMouseDown, true);
  }, [isOpen, containerRef, popoverClassName, setOpen]);
}

export default function BenchBazeSequenceElementSelect({
  feature,
  showCurrentValueInSelect = true,
  isPostPayloadMode = false,
}) {
  const canSearchAndSelect = Boolean(isPostPayloadMode);

  // Determine the initial value to show in the select trigger:
  const initialSequenceFeatureName = getSequenceFeatureValue(
    feature,
    "bb_feat_name",
  );

  // If showCurrentValueInSelect is false and there is an initial detected feature name,
  // show an empty trigger, rather than showing the detected feature name as the current value.
  const isCurrentValueShownSeparately =
    !showCurrentValueInSelect && Boolean(initialSequenceFeatureName);

  // The value shown in the select trigger is determined as follows:
  // - If there is a value in feature.benchBazeSequenceElement, use that (this means the user has made a selection)
  // - Otherwise, if showCurrentValueInSelect is false and there is an initial detected feature name, show an empty trigger
  // - Otherwise, show the initial detected feature name (which may be empty if there isn't one)
  const defaultValue =
    feature.benchBazeSequenceElement ??
    (isCurrentValueShownSeparately ? "" : initialSequenceFeatureName) ??
    "";

  // Local state for the select component
  const [value, setValue] = React.useState(defaultValue);
  const [searchedFeatureName, setSearchedFeatureName] = React.useState("");
  const [apiOptions, setApiOptions] = React.useState(null);
  const [apiOptionMetadataByName, setApiOptionMetadataByName] = React.useState(
    {},
  );
  const [isLoading, setIsLoading] = React.useState(false);
  const [loadError, setLoadError] = React.useState(null);
  const [isMenuOpen, setIsMenuOpen] = React.useState(false);
  const [isDetailsPopoverOpen, setIsDetailsPopoverOpen] = React.useState(false);
  const containerRef = React.useRef(null);
  const detailsContainerRef = React.useRef(null);
  const popupWindowRef = React.useRef(null);

  // Generate unique class names for the popovers based on the menuId,
  // so that we can identify them in the outside click handler
  const menuIdRef = React.useRef(
    feature.id ||
      feature.notes?.id ||
      `${feature.name || "feature"}-${Math.random().toString(36).slice(2, 10)}`,
  );
  const menuId = menuIdRef.current;
  const popoverClassName = React.useMemo(
    () =>
      `bb-sequence-element-popover-${String(menuId).replace(/[^a-zA-Z0-9_-]/g, "-")}`,
    [menuId],
  );
  const detailsPopoverClassName = React.useMemo(
    () =>
      `bb-sequence-element-details-popover-${String(menuId).replace(/[^a-zA-Z0-9_-]/g, "-")}`,
    [menuId],
  );

  // Close this menu if another menu is opened, to ensure only one is open at a time
  useCloseOnOtherOpen("bb-sequence-element-menu-open", menuId, setIsMenuOpen);
  useCloseOnOtherOpen(
    "bb-sequence-element-details-popover-open",
    menuId,
    setIsDetailsPopoverOpen,
  );

  // Close the menu if the user clicks outside of it
  useOutsideClick(isMenuOpen, containerRef, popoverClassName, setIsMenuOpen);
  useOutsideClick(
    isDetailsPopoverOpen,
    detailsContainerRef,
    detailsPopoverClassName,
    setIsDetailsPopoverOpen,
  );

  // When the feature prop changes, we need to update the value shown in the select trigger
  React.useEffect(() => {
    setValue(
      feature.benchBazeSequenceElement ||
        (isCurrentValueShownSeparately ? "" : initialSequenceFeatureName) ||
        "",
    );
  }, [
    feature.benchBazeSequenceElement,
    initialSequenceFeatureName,
    isCurrentValueShownSeparately,
  ]);

  // When the detected feature name changes, we need to load new options from the API
  React.useEffect(() => {
    const trimmedSequenceFeatureName = searchedFeatureName.trim();

    if (!trimmedSequenceFeatureName) {
      setApiOptions(null);
      setApiOptionMetadataByName({});
      setIsLoading(false);
      setLoadError(null);
      return;
    }

    let isCancelled = false;
    setIsLoading(true);
    setLoadError(null);

    const loadOptions = async () => {
      try {
        const response = await fetch(
          `${SEQUENCE_FEATURE_OPTIONS_API_URL}?limit=10&search=${encodeURIComponent(
            trimmedSequenceFeatureName,
          )}`,
        );

        if (!response.ok) {
          throw new Error(`Failed to load options (${response.status})`);
        }

        const data = await response.json();
        if (isCancelled) {
          return;
        }

        const rawOptions = Array.isArray(data.results)
            ? data.results
            : [];

        const normalized =
          normalizeSequenceElementOptionsWithMetadata(rawOptions);

        setApiOptions(normalized.names);
        setApiOptionMetadataByName(normalized.metadataByName);
      } catch (error) {
        if (!isCancelled) {
          setApiOptionMetadataByName({});
          setLoadError(error.message || "Unable to load options.");
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    loadOptions();

    return () => {
      isCancelled = true;
    };
  }, [searchedFeatureName]);

  // The options to show in the menu are determined as follows:
  // - If there is an API-provided options list, use that. This means the user has entered a feature name and we have loaded options for it
  // - Otherwise, if there is a benchBazeSequenceElementOptions list on the feature, use the names from that. This means there are options provided in the data for this feature, but the user hasn't entered a feature name to load API options
  // - Otherwise, use an empty list (this means there are no options to show)
  const candidateOptions = React.useMemo(() => {
    const fallbackNormalized = normalizeSequenceElementOptionsWithMetadata(
      feature.benchBazeSequenceElementOptions,
    );
    const options = Array.isArray(apiOptions)
      ? [...apiOptions]
      : [...fallbackNormalized.names];

    const namesToPrepend = [];

    
    // Include the detected feature name as an option to select
    const sequenceFeatureName = getSequenceFeatureValue(
      feature,
      "bb_feat_name",
    );
    if (
        sequenceFeatureName &&
      !options.includes(sequenceFeatureName)
    ) {
      namesToPrepend.push(sequenceFeatureName);
    }

    if (namesToPrepend.length > 0) {
      options.unshift(...namesToPrepend.reverse());
    }

    return options;
  }, [
    apiOptions,
    feature.benchBazeSequenceElementOptions,
    feature.name,
    searchedFeatureName,
  ]);

  // Combine the metadata from the API options and the fallback options provided in the feature,
  // giving precedence to the API metadata when there are overlapping option names
  const localOptionMetadataByName = React.useMemo(() => {
    const normalized = normalizeSequenceElementOptionsWithMetadata(
      feature.benchBazeSequenceElementOptions,
    );
    return normalized.metadataByName;
  }, [feature.benchBazeSequenceElementOptions]);

  const allOptionMetadataByName = React.useMemo(
    () => ({
      ...localOptionMetadataByName,
      ...apiOptionMetadataByName,
    }),
    [apiOptionMetadataByName, localOptionMetadataByName],
  );

  const fetchSequenceFeatureDetailsUpdate = async (nextSequenceFeatureId, feature) => {
    // Fetch additional details for the a feature and store/update them in the feature notes

    try {
      const response = await fetch(
         `${SEQUENCE_FEATURE_DETAILS_API_URL(nextSequenceFeatureId)}`,
        {
          method: "GET",
        },
      );

      if (!response.ok) {
        throw new Error(
          `Failed to load sequence feature details (${response.status})`,
        );
      }

      const data = await response.json();

      const fieldMappings = [
        { field_map: "bb_feat_name", field_api: "name"},
        { field_map: "bb_feat_org", field_api: "donor_species_names_formatted"},
        { field_map: "bb_feat_org_risk", field_api: "donor_species_risk_groups" },
        { field_map: "bb_feat_nuc_pur", field_api: "nuc_acid_purity_formatted"},
        { field_map: "bb_feat_nuc_risk", field_api: "nuc_acid_risk_formatted"},
        { field_map: "bb_feat_oncogene", field_api: "zkbs_oncogene_formatted"},
      ];

      // Overwrite details in the feature notes
      fieldMappings.forEach((field) => {
          feature.notes[field.field_map] = [data[field.field_api]];
      });
    } catch (error) {
      console.error("Error loading sequence feature details:", error);
    }
  };

  const applySelectedOption = React.useCallback(
    async (nextValue, nextSelectedOptionMetadata = {}) => {
      if (!canSearchAndSelect) {
        return;
      }

      const nextSequenceFeatureId = nextSelectedOptionMetadata.id;

      feature.benchBazeSequenceElementSelectedMetadata =
        nextSelectedOptionMetadata;
      setValue(nextValue);
      feature.benchBazeSequenceElement = nextValue;
      feature.notes.bb_feat_name = [nextValue];

      // jsontoGenbank requires notes values to be an array of strings
      feature.notes.bb_feat_id =
        nextSequenceFeatureId != null ? [String(nextSequenceFeatureId)] : [];

      if (nextSequenceFeatureId) {
        await fetchSequenceFeatureDetailsUpdate(nextSequenceFeatureId, feature);
      }

      setSearchedFeatureName("");
      setApiOptions([nextValue]);
      setIsMenuOpen(false);
      setIsDetailsPopoverOpen(false);
      popupWindowRef.current = null;
    },
    [canSearchAndSelect, feature],
  );

  const handleSelectOption = (nextValue, feature) => {
    const nextSelectedOptionMetadata =
      allOptionMetadataByName[nextValue] || {};
    applySelectedOption(nextValue, nextSelectedOptionMetadata);
  };

  React.useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    if (!window.__bbSequenceElementSelectDismissHandlersInstalled) {
      const originalDismiss = window.dismissAddRelatedObjectPopup;

      window.dismissAddRelatedObjectPopup = function (popupWindow, newId, newRepr) {
        const event = new CustomEvent(
          "bb-sequence-element-popup-added",
          {
            detail: {
              popupWindow,
              newId,
              newRepr,
            },
          },
        );
        window.dispatchEvent(event);

        if (typeof originalDismiss === "function") {
          originalDismiss(popupWindow, newId, newRepr);
        }

        if (
          popupWindow &&
          typeof popupWindow.close === "function" &&
          !popupWindow.closed
        ) {
          popupWindow.close();
        }
      };

      window.__bbSequenceElementSelectDismissHandlersInstalled = true;
    }

    const handleAddedFromPopup = async (event) => {
      const { popupWindow, newId, newRepr } = event.detail || {};
      if (!popupWindow || popupWindow !== popupWindowRef.current) {
        return;
      }

      if (!newRepr) {
        return;
      }

      await applySelectedOption(newRepr, { id: newId });
    };

    window.addEventListener(
      "bb-sequence-element-popup-added",
      handleAddedFromPopup,
    );

    return () => {
      window.removeEventListener(
        "bb-sequence-element-popup-added",
        handleAddedFromPopup,
      );
    };
  }, [applySelectedOption]);

  // When the user selects an option, open the details popover for that option,
  // therefore dispatch a custom event that the popover listens for to know when
  // to open
  const openMenu = () => {
    if (!canSearchAndSelect) {
      return;
    }

    window.dispatchEvent(
      new CustomEvent("bb-sequence-element-menu-open", {
        detail: { menuId },
      }),
    );
    setIsMenuOpen(true);
  };

  // When the user selects an option, open the details popover for that option
  const openDetailsPopover = () => {
    window.dispatchEvent(
      new CustomEvent("bb-sequence-element-details-popover-open", {
        detail: { menuId },
      }),
    );
    setIsDetailsPopoverOpen(true);
  };

  const storePlannotPayload = (payload) => {
    if (typeof window === "undefined") {
      return null;
    }

    window.__bbSequenceElementPayloads =
      window.__bbSequenceElementPayloads || {};

    const token = window.crypto?.randomUUID
      ? window.crypto.randomUUID()
      : `${Date.now()}_${Math.random().toString(36).slice(2, 16)}`;

    window.__bbSequenceElementPayloads[token] = payload;
    return token;
  };

  const openAddFeaturePopup = (feature) => {
    // Open the "Add feature" popup and give it a unique name so that it doesn't get reused if another one is already open
    const popupName = `add_related_object_${window.crypto?.randomUUID ? window.crypto.randomUUID() : `${Date.now()}_${Math.random().toString(36).slice(2, 16)}`}`;
    const specs = "width=800,height=500,resizable=yes,scrollbars=yes";
    const url = new URL(SEQUENCE_FEATURE_ADD_URL, window.location.origin);
    url.searchParams.set("_popup", "1");

    const payload = {
      plannot_label: feature.name || "",
      ...Object.keys(feature.notes || {}).reduce((acc, key) => {
        if (!key.startsWith("plannot_")) {
          return acc;
        }

        const value = feature.notes[key];
        acc[key] = Array.isArray(value)
          ? value.map((item) => String(item)).join(", ")
          : String(value);
        return acc;
      }, {}),
    };

    const token = storePlannotPayload(payload);
    if (token) {
      url.searchParams.set("plannot_token", token);
    }

    popupWindowRef.current = window.open(url.toString(), popupName, specs);
    if (popupWindowRef.current && typeof popupWindowRef.current.focus === "function") {
      popupWindowRef.current.focus();
    }
  };

  // To prevent clicks inside the menu or popover from closing them,
  // stop propagation of click events on those elements
  const stopRowSelection = (event) => {
    event.stopPropagation();
  };

  // Determine whether the selected option has metadata to show in the details popover,
  // which enables/disables the "View details" button
  const hasSelectedItemMetadata =
    Object.keys(allOptionMetadataByName[value] || {}).length > 0;

  // Indicates no value is currently selected, which means the user should select an option 
  const hasMissingSelection = !value;

  // If are Plannotate notes in the feature, apply a special class to the add button to encourage users 
  // to add the detected feature to the options and select it
  const hasPlanotNotes = Object.keys(feature.notes || {}).some((key) =>
    key.startsWith("plannot_"),
  );
  const addButtonClassName =
    isPostPayloadMode && hasPlanotNotes
      ? "bb-sequence-element-add-button-missing"
      : undefined;
  // When the user changes the text in the search input, update the feature name in state,
  // without mutating the feature notes until an option is selected.
  const handleSearchChange = (event) => {
    const nextValue = event.target.value;
    setSearchedFeatureName(nextValue);
  };

  // The text to show in the select trigger
  const triggerText =
    value ||
    (isLoading
      ? "Loading options..."
      : isCurrentValueShownSeparately
        ? "Choose a different option..."
        : "");
  const buttonText = triggerText || " ";

  // The trigger should be disabled if we are not in post-payload mode,
  // or if we are currently loading options
  const isTriggerDisabled = !canSearchAndSelect || isLoading;

  const buttonClassName = [
    "bb-benchbaze-sequence-element-select",
    hasMissingSelection && isPostPayloadMode &&
      "bb-benchbaze-sequence-element-select-missing",
    !triggerText && "bb-benchbaze-sequence-element-select-empty",
  ]
    .filter(Boolean)
    .join(" ");

  // The content of the select menu popover
  const menuContent = (
    <Menu onMouseDown={stopRowSelection} onClick={stopRowSelection}>
      <div
        className="bb-sequence-element-search"
        onMouseDown={stopRowSelection}
        onClick={stopRowSelection}
      >
        <InputGroup
          leftIcon="search"
          placeholder="Search"
          value={searchedFeatureName}
          onChange={handleSearchChange}
          onKeyDown={stopRowSelection}
        />
      </div>

      {isLoading ? (
        <MenuItem disabled text="Loading options..." />
      ) : null}

      {candidateOptions.map((option) => (
        <MenuItem
          key={option}
          text={option}
          active={option === value}
          onClick={(e) => {
            stopRowSelection(e);
            handleSelectOption(option, feature);
          }}
        />
      ))}

      {!isLoading && candidateOptions.length === 0 ? (
        <MenuItem disabled text="No options available" />
      ) : null}
    </Menu>
  );

  return (
    <div className="bb-sequence-element-select-wrapper" ref={containerRef}>
      <Popover
        content={menuContent}
        minimal
        position={Position.BOTTOM_LEFT}
        interactionKind="CLICK"
        popoverClassName={popoverClassName}
        usePortal
        isOpen={isMenuOpen}
        onInteraction={(nextOpen) => {
          if (nextOpen) {
            if (!canSearchAndSelect) {
              return;
            }
            openMenu();
            return;
          }
          setIsMenuOpen(false);
        }}
      >
        <Button
          rightIcon="caret-down"
          text={buttonText}
          className={buttonClassName}
          disabled={isTriggerDisabled}
          alignText="left"
          style={{ minWidth: 180 }}
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => {
            e.stopPropagation();
            if (!canSearchAndSelect) {
              return;
            }
            if (isMenuOpen) {
              setIsMenuOpen(false);
              return;
            }
            openMenu();
          }}
        />
      </Popover>
      <div className="bb-sequence-element-details-actions">
        <BenchBazeSequenceElementDetailsPopover
          feature={feature}
          hasSelectedItemMetadata={hasSelectedItemMetadata}
          isOpen={isDetailsPopoverOpen}
          onOpen={openDetailsPopover}
          onClose={() => setIsDetailsPopoverOpen(false)}
          popoverClassName={detailsPopoverClassName}
          detailsContainerRef={detailsContainerRef}
          stopRowSelection={stopRowSelection}
        />
        {canSearchAndSelect && !hasSelectedItemMetadata && (
          <Button
            minimal
            icon="plus"
            className={addButtonClassName}
            title="Add new feature"
            aria-label="Add new feature"
            onMouseDown={stopRowSelection}
            onClick={(event) => {
              stopRowSelection(event);
              openAddFeaturePopup(feature);
            }}
          />
        )}
      </div>
    </div>
  );
}
