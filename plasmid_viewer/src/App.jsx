import React from "react";
import { Editor, updateEditor } from "@teselagen/ove";
import store from "./store";
import { anyToJson } from '@teselagen/bio-parsers';

import "./App.css";

async function convertPlasmiMapToOveJson(fileName, fileFormat) {
  let data = await fetch(
    new Request(fileName, {
      //probably don't need this header.. fetch should just work
      headers: { "X-Requested-With": "XMLHttpRequest" }
    })
  ) 
    .then((response) => {
      if (fileFormat === 'gbk') return response.text();
      else if (fileFormat === 'dna') return response.blob();
    }
    )
    .then((plasmidData) => anyToJson(plasmidData, {fileName})) //[0]["parsedSequence"])
    .catch(console.error);
  // console.log(`data:`, data); //is this defined and working?
  return data[0]['parsedSequence'];
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

  React.useEffect(() => {
    //useEffect doesn't like top level async functions so we define one inline and immediately invoke it
    (async () => {
      // Get plasmid as OVE JSON
      const seqData = await convertPlasmiMapToOveJson(fileName, fileFormat);
      setLoading(false);
      seqData.name = title;
      const plasmidLength = seqData.size;

      // Remove features that do not need to be shown, ever!
      const featNameExclude = ["synthetic dna construct", "recombinant plasmid", "source"];
      seqData.features = seqData.features.filter(feat =>
          !(featNameExclude.includes(feat.name.toLowerCase()) && plasmidLength === feat.end - feat.start + 1));

      updateEditor(store, "DemoEditor", {
        sequenceData: seqData,
        circular: seqData.circular,
        annotationVisibility: {
          features: true,
          cutsites: false,
          primers: showOligos,
          translations: !showOligos,
        }
      });
      
    })();
  }, [title, fileName]);

  const editorProps = {
    editorName: "DemoEditor",
    isFullscreen: true,
    showMenuBar: false,
    readOnly: true,
    ToolBarProps: {
      toolList: [
        "downloadTool",
        "cutsiteTool",
        "featureTool",
        "oligoTool",
        "orfTool",
        "visibilityTool",
        "findTool",
      ]
    },
    PropertiesProps: {
      propertiesList: [
        "features",
        "primers",
        "translations",
        "cutsites",
        "orfs",
      ]
    },
    StatusBarProps: {
      showCircularity: true,
      showReadOnly: false,
      showAvailability: false
    },
  };

  return !loading ? (
    <div>
      <Editor {...editorProps} />
    </div>
  ) : (
    <div></div>
  );
}

export default App;