import React from "react";
import BenchBazeSequenceElementSelect from "./BenchBazeSequenceElementSelect.jsx";

export default function createBenchBazeSequenceElementColumn(
  isPostPayloadMode = false,
) {
  // Factory function to create the custom column definition for sequence elements in the properties panel
  return {
    path: "benchBazeSequenceElement",
    displayName: "GMO compliance",
    type: "string",
    width: 160,
    show: true,
    isHidden: false,
    getValueToFilterOn: (feature) => {
      const detectedFeatureName = Array.isArray(feature.notes?.bb_feat_name)
        ? feature.notes.bb_feat_name[0]
        : feature.notes?.bb_feat_name;
      return feature.benchBazeSequenceElement ?? detectedFeatureName ?? "";
    },
    render: (_value, feature) => {
      return (
        <BenchBazeSequenceElementSelect
          feature={feature}
          isPostPayloadMode={isPostPayloadMode}
        />
      );
    },
  };
}
