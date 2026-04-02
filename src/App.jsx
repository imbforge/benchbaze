import React from "react";
import store from "./store";
import {
  DownloadDropdownWithSvg,
  convertPlasmiMapToOveJson,
} from "./BenchBazeMapViewerUtils";

import "./App.css";

const oveModulePromise = import("@teselagen/ove");
const Editor = React.lazy(() =>
  oveModulePromise.then((module) => ({ default: module.Editor })),
);

function App() {
  // Get GET parameters from url and store them in a variable
  const search = window.location.search;
  const params = new URLSearchParams(search);
  const fileName = params.get("file_name");
  const title = params.get("title");
  const showOligos = params.get("show_oligos") ? true : false;
  const fileFormat = params.get("file_format");

  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let isMounted = true;

    // Start downloading the heavy editor module as soon as the view mounts.
    // This keeps lazy loading benefits while reducing wait time before first render.
    void oveModulePromise;

    //useEffect doesn't like top level async functions so we define one inline and immediately invoke it
    (async () => {
      // Get plasmid data and editor module in parallel to reduce startup latency.
      const [seqData, oveModule] = await Promise.all([
        convertPlasmiMapToOveJson(fileName, fileFormat),
        oveModulePromise,
      ]);
      if (!isMounted || !seqData) {
        return;
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
    })();

    return () => {
      isMounted = false;
    };
  }, [title, fileName]);

  const editorProps = {
    editorName: "DemoEditor",
    isFullscreen: true,
    showMenuBar: false,
    readOnly: true,
    ToolBarProps: {
      toolList: [
        {
          name: "downloadTool",
          Dropdown: (dropdownProps) => (
            <DownloadDropdownWithSvg
              {...dropdownProps}
              title={title}
              fileName={fileName}
            />
          ),
        },
        "cutsiteTool",
        "featureTool",
        "oligoTool",
        "orfTool",
        "visibilityTool",
        "findTool",
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

  return !loading ? (
    <div>
      <React.Suspense fallback={<div></div>}>
        <Editor {...editorProps} />
      </React.Suspense>
    </div>
  ) : (
    <div></div>
  );
}

export default App;
