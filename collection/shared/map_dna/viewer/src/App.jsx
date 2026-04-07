import React from "react";
import { Button, Icon, Tooltip } from "@blueprintjs/core";
import store from "./store";
import "@blueprintjs/core/lib/css/blueprint.css";
import {
  downloadMapFile,
  downloadMapPreview,
  convertPlasmiMapToOveJson,
} from "./BenchBazeMapViewerUtils";

import "./App.css";

const oveModulePromise = import("@teselagen/ove");
const Editor = React.lazy(() =>
  oveModulePromise.then((module) => ({ default: module.Editor })),
);

const THEME_STORAGE_KEY = "theme";
const THEME = {
  LIGHT: "light",
  DARK: "dark",
  AUTO: "auto",
};

const DEFAULT_LOAD_ERROR_MESSAGE =
  "The map cannot be loaded.";

class ViewerErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidUpdate(prevProps) {
    if (
      prevProps.resetKey !== this.props.resetKey &&
      this.state.error !== null
    ) {
      this.setState({ error: null });
    }
  }

  render() {
    if (this.state.error) {
      return this.props.renderError(this.state.error);
    }

    return this.props.children;
  }
}

function getLoadErrorMessage(error) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return DEFAULT_LOAD_ERROR_MESSAGE;
}

function getInitialTheme() {
  try {
    const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (
      storedTheme === THEME.DARK ||
      storedTheme === THEME.LIGHT ||
      storedTheme === THEME.AUTO
    ) {
      return storedTheme;
    }
  } catch (error) {
    // Ignore storage read failures and continue with system/default theme.
  }

  if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return THEME.DARK;
  }

  return THEME.LIGHT;
}

function App() {
  // Get GET parameters from url and store them in a variable
  const search = window.location.search;
  const params = new URLSearchParams(search);
  const fileName = params.get("file_name");
  const title = params.get("title");
  const showOligos = params.get("show_oligos") ? true : false;
  const fileFormat = params.get("file_format");

  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState(null);
  const [loadAttempt, setLoadAttempt] = React.useState(0);
  const [theme, setTheme] = React.useState(getInitialTheme);
  const [prefersDarkScheme, setPrefersDarkScheme] = React.useState(() =>
    window.matchMedia("(prefers-color-scheme: dark)").matches,
  );
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

  const retryLoad = React.useCallback(() => {
    setLoadError(null);
    setLoading(true);
    setLoadAttempt((currentAttempt) => currentAttempt + 1);
  }, []);

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
    let isMounted = true;
    setLoading(true);
    setLoadError(null);

    // Start downloading the heavy editor module as soon as the view mounts.
    // This keeps lazy loading benefits while reducing wait time before first render.
    void oveModulePromise;

    //useEffect doesn't like top level async functions so we define one inline and immediately invoke it
    (async () => {
      try {
        // Get plasmid data and editor module in parallel to reduce startup latency.
        const [seqData, oveModule] = await Promise.all([
          convertPlasmiMapToOveJson(fileName, fileFormat),
          oveModulePromise,
        ]);
        if (!isMounted) {
          return;
        }

        if (!seqData) {
          throw new Error(DEFAULT_LOAD_ERROR_MESSAGE);
        }

        const { updateEditor } = oveModule;
        seqData.name = title;
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

        updateEditor(store, "DemoEditor", {
          sequenceData: seqData,
          circular: seqData.circular,
          annotationVisibility: {
            features: true,
            cutsites: false,
            primers: showOligos,
            translations: !showOligos,
          },
        });

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
  }, [title, fileName, fileFormat, showOligos, loadAttempt]);

  const editorProps = {
    editorName: "DemoEditor",
    isFullscreen: true,
    showMenuBar: false,
    readOnly: true,
    ToolBarProps: {
      toolList: [
        {
          name: "downloadTool",
          tooltip: `Download Map File (.${fileFormat})`,
          noDropdownIcon: true,
          Dropdown: null,
          onIconClick: () => {
            downloadMapFile(fileName, title);
          },
        },
        "cutsiteTool",
        "featureTool",
        "oligoTool",
        "orfTool",
        "visibilityTool",
        "findTool",
      ],
      modifyTools: (tools) => [
        tools[0],
        <div
          key="downloadPreviewTool"
          className="veToolbarItemOuter ve-tool-container-downloadPreviewTool"
          style={{ marginLeft: 6 }}
        >
          <Tooltip content="Download Map Preview">
            <Button
              minimal
              intent="primary"
              icon={<Icon icon="media" />}
              onClick={() => downloadMapPreview(title)}
            />
          </Tooltip>
        </div>,
        ...tools.slice(1),
      ],
    },
    PropertiesProps: {
      propertiesList: [
        "features",
        "primers",
        "translations",
        "cutsites",
        "orfs",
      ],
    },
    StatusBarProps: {
      showCircularity: true,
      showReadOnly: false,
      showAvailability: false,
    },
  };

  return (
    <div className={`app-shell ${isDarkTheme ? "bp3-dark" : ""}`}>
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
          <div
            className="loading-spinner"
            aria-label="Loading map viewer"
            role="status"
          >
            <div></div>
            <div></div>
            <div></div>
            <div></div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
