import React from "react";
import PropertiesDialog from "@teselagen/ove/src/helperComponents/PropertiesDialog/index.js";
import BenchBazePropertiesPanelLegend from "./BenchBazePropertiesPanelLegend.jsx";
import createBenchBazeSequenceElementColumn from "./createBenchBazeSequenceElementColumn.jsx";

export default function BenchBazePropertiesPanel(props) {
  // Custom properties panel that injects the sequence element column into 
  // the features section of the properties dialog
  const {
    PropertiesProps = {},
    isPostPayloadMode = false,
    isDetectFeatures = false,
    showLegend = false,
    onRestoreOriginalColors,
    ...rest
  } = props;
  const [isLegendVisible, setLegendVisible] = React.useState(
    () => isDetectFeatures || showLegend,
  );

  // Show the legend by default only when the posted payload is asking for
  // feature detection. The user can still hide it after it appears
  React.useEffect(() => {
    if (isDetectFeatures || showLegend) {
      setLegendVisible(true);
    }
  }, [isDetectFeatures, showLegend]);

  const defaultPropertiesList =
    PropertiesProps.propertiesList || [
      "features",
      "primers",
      "translations",
      "cutsites",
      "orfs",
    ];

  // Create the custom column for sequence elements, passing necessary props
  const benchBazeColumnSequenceElement = createBenchBazeSequenceElementColumn(
    isPostPayloadMode,
  );

  // Merge the custom column into the existing properties list,
  // ensuring it appears in the "features" section
  const propertiesListWithCustomColumns = defaultPropertiesList.map(item => {
    const name = typeof item === "string" ? item : item.name || item;
    if (name !== "features") {
      return item;
    }

    const existingAdditionalColumns =
      (typeof item === "object" && item.additionalColumns) || [];

    return {
      name: "features",
      ...((typeof item === "object" && item) || {}),
      additionalColumns: [
        ...existingAdditionalColumns,
        benchBazeColumnSequenceElement,
      ],
    };
  });

  const mergedPropertiesProps = {
    ...PropertiesProps,
    propertiesList: propertiesListWithCustomColumns,
  };

  const legend = (
    <BenchBazePropertiesPanelLegend
      onClose={() => {
        if (typeof onRestoreOriginalColors === "function") {
          onRestoreOriginalColors();
        }
        setLegendVisible(false);
      }}
    />
  );

  return (
    <div data-custom-properties-panel="true" className="bb-properties-panel">
      {isLegendVisible && legend}
      <PropertiesDialog {...rest} PropertiesProps={mergedPropertiesProps} />
    </div>
  );
}
