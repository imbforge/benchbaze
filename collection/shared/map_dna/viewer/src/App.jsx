import React from "react";
import {
  Button,
  Icon,
  Position,
  Tooltip,
  Toaster,
  getPositionIgnoreAngles,
} from "@blueprintjs/core";
import store from "./store";
import "@blueprintjs/core/lib/css/blueprint.css";
import {
  downloadMapFile,
  downloadMapPreview,
  convertMapPathToOveJson,
  convertPostedMapFileToOveJson,
  getSequenceFeatureIds,
  saveToFile,
} from "./BenchBazeMapViewerUtils";
import { setToasterInstance, toastr } from "./toaster";
import ViewerErrorBoundary from "./AppErrorBoundary";
import {
  getPanelsShown,
  getLoadErrorMessage,
  getInitialTheme,
  getPostedPayloadFromWindow,
  isBlobPostedPayload,
  getFileFormatFromFileName,
  detectMapFeaturesOnServer,
} from "./App.helpers";
import BenchBazePropertiesPanel from "./BenchBazePropertiesPanel";
import BenchBazeAddOrEditPrimerDialogOverride from "./BenchBazeAddOrEditPrimerDialogOverride";

import "./App.css";

// Get OVE's Editor component as a lazily loaded module to reduce initial bundle size and load time
const oveModulePromise = import("@teselagen/ove");
const Editor = React.lazy(() =>
  oveModulePromise.then((module) => ({ default: module.Editor })),
);

// Key used for storing the user's theme preference
const THEME = {
  LIGHT: "light",
  DARK: "dark",
  AUTO: "auto",
};

// Other constants
const DEFAULT_LOAD_ERROR_MESSAGE = "The map cannot be loaded.";
const EDITOR_NAME = "BenchBazeMapViewerEditor";

function getPostedPayloadSignature(payload) {
  // Generate a simple signature string for the posted payload based on its file properties
  // This includes the file name, type, size, and last modified timestamp
  // This is used to detect if the same file has been posted again, to avoid reprocessing it
  // unnecessarily
  if (!isBlobPostedPayload(payload)) {
    return null;
  }

  const mapFile = payload.mapFile;
  const fileName = payload.fileName || mapFile.name || "";
  const fileType = mapFile.type || "";
  const fileSize = Number.isFinite(mapFile.size) ? mapFile.size : -1;
  const fileLastModified =
    typeof mapFile.lastModified === "number" ? mapFile.lastModified : -1;

  return [fileName, fileType, fileSize, fileLastModified].join("|");
}

function computeSequenceDataSignature(sequenceData) {
  // Create a stable string signature for the editor's sequence data
  // This is used to detect changes and manage unsaved-change state
  try {
    return sequenceData ? JSON.stringify(sequenceData) : null;
  } catch {
    return null;
  }
}

function App() {
  // Get any GET parameters from url and store them in a variable
  const search = window.location.search;
  const params = new URLSearchParams(search);
  const fileName = params.get("file_name");
  const title = params.get("title");
  const showOligos = params.get("show_oligos") ? true : false;
  // Detect if this is a post payload even before the payload is processed,
  // to determine whether to show edit controls during the initial load
  const forcePostMode = params.get("bb_post_mode") === "1";

  // Keep the original posted payload in a ref so that we can refer to it when saving the map
  const originalPostedPayloadRef = React.useRef(getPostedPayloadFromWindow());
  // Keep a ref of the last posted payload signature to detect duplicates
  const lastPostedPayloadSignatureRef = React.useRef(
    getPostedPayloadSignature(originalPostedPayloadRef.current),
  );
  const [postedPayload, setPostedPayload] = React.useState(
    originalPostedPayloadRef.current,
  );

  // State for managing map loading and errors
  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState(null);
  const [loadAttempt, setLoadAttempt] = React.useState(0);
  const [isSaving, setIsSaving] = React.useState(false);
  const [theme, setTheme] = React.useState(getInitialTheme);
  const [prefersDarkScheme, setPrefersDarkScheme] = React.useState(
    () => window.matchMedia("(prefers-color-scheme: dark)").matches,
  );

  // Resolve the final values for showOligos, fileName, title, and fileFormat
  // dependent on the precedence: posted payload > URL parameters > defaults
  const resolvedShowOligos = postedPayload?.showOligos || showOligos || false;
  const resolvedFileName = postedPayload?.fileName || fileName;
  const resolvedTitle =
    postedPayload?.title || title || resolvedFileName || "Untitled Map";
  const resolvedFileFormat = getFileFormatFromFileName(resolvedFileName);

  // Determine if we are in post payload mode, which must enable edit/save controls
  const isPostPayloadMode = forcePostMode || Boolean(postedPayload);

  // Determine if we should attempt to detect features on the posted map file
  const isDetectFeatures =
    postedPayload?.detectFeatures === true ||
    Boolean(originalPostedPayloadRef.current?.detectFeatures === true);

  // Read-only/edit state is determined by the presence of a posted payload
  const [isReadOnly, setIsReadOnly] = React.useState(() => !isPostPayloadMode);
  React.useEffect(() => {
    setIsReadOnly(!isPostPayloadMode);
  }, [isPostPayloadMode]);

  // Refs to track the original and last saved sequence data signatures for change detection
  const originalSequenceDataSignatureRef = React.useRef(null);
  const savedSequenceDataSignatureRef = React.useRef(null);
  const isSequenceDataDirtyRef = React.useRef(false);

  // Function to compute the current sequence data signature from the editor state
  const getCurrentSequenceDataSignature = React.useCallback(() => {
    const editorState = store.getState()?.VectorEditor?.[EDITOR_NAME];
    return computeSequenceDataSignature(editorState?.sequenceData);
  }, []);

  // Function to update the unsaved changes state by comparing the current editor state against the baseline
  const updateUnsavedChanges = React.useCallback(() => {
    // If in read-only mode, there can be no unsaved changes, so we can skip the comparison
    if (isReadOnly) {
      isSequenceDataDirtyRef.current = false;
      window.BB_MAP_DNA_HAS_UNSAVED_CHANGES = false;
      return false;
    }

    // Compare current editor state against the last saved baseline
    const currentSignature = getCurrentSequenceDataSignature();
    const baselineSignature =
      savedSequenceDataSignatureRef.current ??
      originalSequenceDataSignatureRef.current;

    // Check if the signatures are different, which indicates unsaved changes
    const hasChanges =
      Boolean(currentSignature) &&
      Boolean(baselineSignature) &&
      currentSignature !== baselineSignature;

    // Update the ref and global flag to indicate whether there are unsaved changes
    isSequenceDataDirtyRef.current = hasChanges;
    window.BB_MAP_DNA_HAS_UNSAVED_CHANGES = hasChanges;
    return hasChanges;
  }, [getCurrentSequenceDataSignature, isReadOnly]);

  // Function to set the baseline sequence data signature when the editor state is loaded or saved
  const setBaselineSequenceData = React.useCallback(
    (sequenceData) => {
      // Record the loaded/saved editor state as the clean baseline
      const signature = computeSequenceDataSignature(sequenceData);
      originalSequenceDataSignatureRef.current = signature;
      savedSequenceDataSignatureRef.current = signature;
      updateUnsavedChanges();
    },
    [updateUnsavedChanges],
  );

  // Determine whether dark theme is active
  const isDarkTheme =
    theme === THEME.DARK || (theme === THEME.AUTO && prefersDarkScheme);

  React.useEffect(() => {
    // Listen for changes in the system color scheme preference
    const mediaQueryList = window.matchMedia("(prefers-color-scheme: dark)");
    const handleThemeChange = (event) => {
      setPrefersDarkScheme(event.matches);
    };

    setPrefersDarkScheme(mediaQueryList.matches);
    mediaQueryList.addEventListener("change", handleThemeChange);

    return () => {
      mediaQueryList.removeEventListener("change", handleThemeChange);
    };
  }, []);

  React.useEffect(() => {
    // React to theme changes written by Django admin in other same-origin tabs/frames.
    const handleStorage = (event) => {
      if (event.key !== THEME_STORAGE_KEY) {
        return;
      }

      setTheme(getInitialTheme());
    };

    window.addEventListener("storage", handleStorage);

    return () => {
      window.removeEventListener("storage", handleStorage);
    };
  }, []);

  React.useEffect(() => {
    // Set up beforeunload handler to warn about unsaved changes when in post-payload mode/not read-only
    if (!isPostPayloadMode || isReadOnly) {
      // In non-post-payload/read-only mode, there are no unsaved changes to track,
      // so we can skip setting up the beforeunload handler and just set the global flags to false
      window.BB_MAP_DNA_HAS_UNSAVED_CHANGES = false;
      window.BB_MAP_DNA_SUPPRESS_BEFOREUNLOAD_PROMPT = false;
      return undefined;
    }

    // Keep a global unsaved-change flag for the parent popup to check
    window.BB_MAP_DNA_HAS_UNSAVED_CHANGES = false;
    window.BB_MAP_DNA_SUPPRESS_BEFOREUNLOAD_PROMPT = false;

    // Subscribe to editor state changes to update the unsaved changes flag
    const unsubscribe = store.subscribe(() => {
      updateUnsavedChanges();
    });

    // Beforeunload handler to prompt the user if they have unsaved changes
    const handleBeforeUnload = (event) => {
      if (
        isSequenceDataDirtyRef.current &&
        !window.BB_MAP_DNA_SUPPRESS_BEFOREUNLOAD_PROMPT
      ) {
        event.preventDefault();
        event.returnValue = "";
        return "";
      }
    };

    // Attach the beforeunload event listener to window to warn about unsaved changes
    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      unsubscribe();
      window.removeEventListener("beforeunload", handleBeforeUnload);
      window.BB_MAP_DNA_HAS_UNSAVED_CHANGES = false;
      window.BB_MAP_DNA_SUPPRESS_BEFOREUNLOAD_PROMPT = false;
    };
  }, [updateUnsavedChanges, isPostPayloadMode, isReadOnly]);

  // Function to retry loading the map, used in the error state
  const retryLoad = React.useCallback(() => {
    setLoadError(null);
    setLoading(true);
    setLoadAttempt((currentAttempt) => currentAttempt + 1);
  }, []);

  const saveMap = React.useCallback(async () => {
    // This function retrieves the edited map data from the editor,
    // generates a new map file, and sends it back to the parent window
    // using postMessage. It also handles loading state and error notifications

    // Set saving state to show loading indicator on the save button
    setIsSaving(true);

    try {
      const editorState = store.getState()?.VectorEditor?.[EDITOR_NAME];
      const editedSequenceData = editorState?.sequenceData;

      if (!editedSequenceData) {
        throw new Error("No map data available to save.");
      }

      if (!window.parent || window.parent === window) {
        throw new Error("No form detected to which to save the map.");
      }

      // Generate a new map file with the edited sequence data, using the original
      // posted file as a template if available to preserve file properties
      const { file: editedMapFile, sequenceFeatureIds } = await saveToFile(
        editedSequenceData,
        originalPostedPayloadRef.current?.mapFile || postedPayload?.mapFile,
      );

      if (!editedMapFile) {
        throw new Error("Error while preparing the map for saving.");
      }

      // Post the edited map file and the IDs of the sequence features back to the parent window
      window.parent.postMessage(
        {
          type: "BB_MAP_DNA_SAVE_RESULT",
          mapFile: editedMapFile,
          sequenceFeatureIds: sequenceFeatureIds,
        },
        window.location.origin,
      );

      // Notify the user of success and update the baseline signature to the newly saved state
      toastr.success("Saved map in the form");
      savedSequenceDataSignatureRef.current =
        computeSequenceDataSignature(editedSequenceData);
      updateUnsavedChanges();
    } catch (error) {
      toastr.error(getLoadErrorMessage(error));
    } finally {
      // Reset saving state to re-enable the save button
      setIsSaving(false);
    }
  }, [postedPayload, resolvedFileFormat, resolvedFileName, resolvedTitle]);

  // Function to render the load error message with a retry button
  const renderLoadError = React.useCallback(
    (error) => (
      <div className="load-state-panel tg-flex justify-center align-center">
        <div className="load-error-card" role="alert">
          <div className="load-error-eyebrow">Map loading error</div>
          <h1 className="load-error-title">Oops! Cannot load the map</h1>
          <p className="load-error-message">{getLoadErrorMessage(error)}</p>
          <button
            type="button"
            className="load-error-button"
            onClick={retryLoad}
          >
            Try again
          </button>
        </div>
      </div>
    ),
    [retryLoad],
  );

  React.useEffect(() => {
    // Accept sequence payload from a parent window/iframe flow

    // Listen for postMessage events containing the map file payload from the parent window
    const handlePostMessage = (event) => {
      
      // Only accept messages from the same origin
        if (event?.origin && event.origin !== window.location.origin) {
        return;
      }

      // Validate that the message data is an object with the expected type and structure
      const data = event?.data;
      if (!data || typeof data !== "object") {
        return;
      }

      // Accept messages with the specific type indicating a posted map payload
      if (data.type !== "BB_MAP_DNA_POST_RESULT") {
        return;
      }

      if (!isBlobPostedPayload(data)) {
        return;
      }

      // Generate a signature for the posted payload to detect duplicates
      // and avoid processing the same file twice
      const payloadSignature = getPostedPayloadSignature(data);

      // Send an acknowledgement back to the parent window to confirm receipt of the payload
      try {
        if (event.source && typeof event.source.postMessage === "function") {
          event.source.postMessage(
            {
              type: "BB_MAP_DNA_POST_ACKNOWLEDGEMENT",
            },
            event.origin || window.location.origin,
          );
        }
      } catch (error) {
        // Ignore acknowledgement failures; the posted payload still updates local state.
      }

      // Parent may retry posting the same payload until acknowledgement arrives.
      // Accept duplicates, but do not reprocess the same file
      if (
        payloadSignature &&
        payloadSignature === lastPostedPayloadSignatureRef.current
      ) {
        return;
      }
      // Update the posted payload state with the new data, which will trigger the re-loading and 
      // re-rendering of the new map file
      originalPostedPayloadRef.current = data;
      lastPostedPayloadSignatureRef.current = payloadSignature;
      setPostedPayload(data);
    };

    // Attach the message event listener to window to receive posted map payloads from the parent
    window.addEventListener("message", handlePostMessage);

    return () => {
      window.removeEventListener("message", handlePostMessage);
    };
  }, []);

  React.useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setLoadError(null);

    // Start downloading the heavy editor module as soon as the view mounts.
    // This keeps lazy loading benefits while reducing wait time before first render.
    void oveModulePromise;

    (async () => {
      try {
        let resolvedPostedPayload = postedPayload;

        // If the posted payload indicates that features should be detected, send the file
        // to the server for processing before loading it in the editor
        if (
          isBlobPostedPayload(postedPayload) &&
          postedPayload.detectFeatures !== false
        ) {
          resolvedPostedPayload =
            await detectMapFeaturesOnServer(postedPayload);
          if (!isMounted) {
            return;
          }
          setPostedPayload(resolvedPostedPayload);
        }

        // Get plasmid data and editor module in parallel to reduce startup latency
        const [incomingSeqData, oveModule] = await Promise.all([
          isBlobPostedPayload(resolvedPostedPayload)
            ? convertPostedMapFileToOveJson(
                resolvedPostedPayload.mapFile,
              )
            : convertMapPathToOveJson(resolvedFileName),
          oveModulePromise,
        ]);
        if (!isMounted) {
          return;
        }

        // If no sequence data could be loaded, throw an error to show the error state
        if (!incomingSeqData) {
          throw new Error(DEFAULT_LOAD_ERROR_MESSAGE);
        }

        // Get sequence data and process it to remove unwanted features before loading
        const seqData = { ...incomingSeqData }; // Shallow copy to avoid mutating original data used for change detection baseline
        const { updateEditor } = oveModule;
        seqData.name = resolvedTitle || seqData.name;
        const plasmidLength = seqData.size;

        // Remove features that do not need to be shown, ever!
        const featNameExclude = [
          "synthetic dna construct",
          "recombinant plasmid",
          "source",
        ];
        seqData.features = seqData.features.filter(
          (feat) =>
            !(
              featNameExclude.includes(feat.name.toLowerCase()) &&
              plasmidLength === feat.end - feat.start + 1
            ),
        );

        // Update the editor state with the loaded sequence data and other relevant properties
        updateEditor(store, EDITOR_NAME, {
          sequenceData: seqData,
          panelsShown: getPanelsShown(seqData.circular, isPostPayloadMode),
          readOnly: isReadOnly,
          annotationVisibility: {
            features: true,
            cutsites: false,
            primers: resolvedShowOligos,
            translations: !resolvedShowOligos,
          },
        });

        // Upon initial load, send the IDs of the sequence features back to the parent window
        // in case the user does not save the map, Django still expects to receive the detected 
        // feature IDs
        if (isDetectFeatures && window.parent && window.parent !== window) {
          const sequenceFeatureIds = getSequenceFeatureIds(seqData);
          window.parent.postMessage(
            {
              type: "BB_MAP_DNA_INITIAL_FEATURE_IDS",
              sequenceFeatureIds,
            },
            window.location.origin,
          );
        }

        setBaselineSequenceData(seqData);
        setLoading(false);
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setLoadError(error);
        setLoading(false);
      }
    })();

    return () => {
      isMounted = false;
    };
  }, [
    resolvedTitle,
    resolvedFileName,
    resolvedFileFormat,
    resolvedShowOligos,
    postedPayload,
    loadAttempt,
  ]);

  React.useEffect(() => {
    // Update the editor's read-only state when isReadOnly changes
    if (loading || loadError) {
      return;
    }

    void oveModulePromise.then((oveModule) => {
      const { updateEditor } = oveModule;
      updateEditor(store, EDITOR_NAME, {
        readOnly: isReadOnly,
      });
    });
  }, [isReadOnly, loading, loadError]);

  // Prepare the props for the Editor component
  const editorProps = {
    editorName: EDITOR_NAME,
    isFullscreen: true,
    showMenuBar: false,
    readOnly: isReadOnly,
    ToolBarProps: {
      toolList: [
        ...(isPostPayloadMode
          ? []
          : [
              {
                name: "downloadTool",
                tooltip: `Download Map File (.${resolvedFileFormat || "dna"})`,
                noDropdownIcon: true,
                Dropdown: null,
                onIconClick: () => {
                  downloadMapFile(resolvedFileName, resolvedTitle);
                },
              },
            ]),
        "cutsiteTool",
        "featureTool",
        "oligoTool",
        "orfTool",
        "visibilityTool",
        "findTool",
      ],
      // Modify the list of tools displayed in the toolbar to include custom save and
      // download preview button in post payload mode
      modifyTools: (tools) => [
        ...(isPostPayloadMode
          ? [
              <div key={isReadOnly ? "enableEditTool" : "saveMapTool"} style={{ display: "flex", alignItems: "center" }}>
                <div className="veToolbarItemOuter">
                  <Tooltip
                    content={
                      isReadOnly
                        ? "Enable editing"
                        : isSaving
                          ? "Saving map to form..."
                          : "Save Map to Form"
                    }
                  >
                    <Button
                      minimal
                      intent="primary"
                      loading={!isReadOnly && isSaving}
                      disabled={!isReadOnly && isSaving}
                      icon={
                        isReadOnly ? (
                          <Icon icon="edit" />
                        ) : !isSaving ? (
                          <Icon icon="floppy-disk" />
                        ) : undefined
                      }
                      onClick={isReadOnly ? () => setIsReadOnly(false) : saveMap}
                    />
                  </Tooltip>
                </div>
              </div>,
            ]
          : []),
        ...(isPostPayloadMode
          ? [
              <div
                key="cutsiteSpacer"
                style={{ display: "flex", alignItems: "center" }}
              >
                <div className="veToolbarSpacer" />
                {tools[0]}
              </div>,
            ]
          : [tools[0]]),
        <div key="downloadPreviewTool" style={{ display: "flex", alignItems: "center" }}>
          <div className="veToolbarSpacer" />
          <div className="veToolbarItemOuter ve-tool-container-downloadPreviewTool">
            <Tooltip content="Download Map Preview">
              <Button
                minimal
                intent="primary"
                icon={<Icon icon="media" />}
                onClick={() => downloadMapPreview(resolvedTitle)}
              />
            </Tooltip>
          </div>
        </div>,
        ...tools.slice(1),
      ],
    },
    // Specify which annotation types to show in the properties panel and other relevant props
    PropertiesProps: {
      propertiesList: [
        "features",
        "primers",
        "translations",
        "cutsites",
        "orfs",
      ],
    },
    AddOrEditPrimerDialogOverride: BenchBazeAddOrEditPrimerDialogOverride,
    isPostPayloadMode,
    isDetectFeatures:
      postedPayload?.detectFeatures === true ||
      Boolean(originalPostedPayloadRef.current?.detectFeatures === true),
    isDarkTheme,
    panelMap: {
      properties: {
        comp: BenchBazePropertiesPanel,
        panelSpecificProps: [
          "PropertiesProps",
          "isPostPayloadMode",
          "isDetectFeatures",
          "isDarkTheme",
        ],
      },
    },
    StatusBarProps: {
      showCircularity: true,
      showReadOnly: true,
      showAvailability: false,
    },
  };

  // Callback ref to get the Toaster instance from the Blueprint Toaster component
  const handleToasterRef = React.useCallback((instance) => {
    setToasterInstance(instance);
  }, []);

  // Render the app shell with conditional content based on loading and error state
  return (
    <div className={`app-shell ${isDarkTheme ? "bp3-dark" : ""}`}>
      <Toaster
        ref={handleToasterRef}
        className="bb-blueprint-toaster"
        position={Position.TOP_LEFT}
        usePortal
      />
      {/* Show loading spinner, error message, or the editor based on the current state */}
      {loadError ? (
        renderLoadError(loadError)
      ) : !loading ? (
        <ViewerErrorBoundary
          resetKey={loadAttempt}
          renderError={renderLoadError}
        >
          <React.Suspense fallback={<div></div>}>
            <Editor {...editorProps} />
          </React.Suspense>
        </ViewerErrorBoundary>
      ) : (
        <div className="tg-loader-container">
          <div className="loading-logo" aria-label="Loading map viewer" role="status">
            <img
              className="loading-logo-mark"
              src={`${import.meta.env.BASE_URL}logo-small.svg`}
              alt=""
              aria-hidden="true"
            />
          </div>
          <p className="loading-caption" aria-hidden="true">Please wait</p>
        </div>
      )}
    </div>
  );
}

export default App;
