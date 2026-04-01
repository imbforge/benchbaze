import * as React from "react";
import { genbankToJson } from '@teselagen/bio-parsers';
import { tidyUpSequenceData } from "ve-sequence-utils";
import CircularView from "./CircularView/index.js";
import fs from "fs";
import path from "path";

export default function App({ params }) {

  // Get plasmid data
  let plasmidData = fs.readFileSync(path.resolve(params.plasmidFilePath)).toString();
  plasmidData = genbankToJson(plasmidData, {})[0]['parsedSequence'];
  plasmidData = tidyUpSequenceData(plasmidData);

  // Set plasmid name
  plasmidData.name = params.plasmidTitle;

  // Remove features that do not need to be shown, ever!
  const plasmidLength = plasmidData.size;
  const featNameExclude = ["synthetic dna construct", "recombinant plasmid", "source"];
  plasmidData.features = plasmidData.features.filter(feat =>
      !(featNameExclude.includes(feat.name.toLowerCase()) && plasmidLength === feat.end - feat.start + 1));

  return (
    <div>
      <CircularView
        {...{
          ...{editorName: "DemoEditor",},
          annotationVisibility: {
            featureTypesToHide: {},
            featureIndividualToHide: {},
            partIndividualToHide: {},
            features: true,
            warnings: false,
            assemblyPieces: true,
            chromatogram: false,
            lineageAnnotations: false,
            translations: false,
            parts: true,
            orfs: false,
            orfTranslations: false,
            cdsFeatureTranslations: false,
            axis: true,
            cutsites: false,
            cutsitesInSequence: false,
            primers: false,
            dnaColors: false,
            sequence: false,
            reverseSequence: false,
            fivePrimeThreePrimeHints: false,
            axisNumbers: true,
          },
          sequenceData: plasmidData,
        }}
      />
    </div>
  );
}
