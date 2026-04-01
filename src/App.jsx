import * as React from "react";
import CircularView from "./CircularView/index.js";

export default function App({ sequenceData }) {

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
          sequenceData,
        }}
      />
    </div>
  );
}
