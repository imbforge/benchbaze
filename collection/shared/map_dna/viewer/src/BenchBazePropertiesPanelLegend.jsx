import React from "react";

export default function BenchBazePropertiesPanelLegend({ onClose }) {
  // Simple legend component to explain the meaning of feature colors in the properties panel
  return (
    <div className="bb-properties-legend bp3-card bp3-elevation-1">
      <button
        type="button"
        aria-label="Close legend"
        className="bb-properties-legend-close"
        onClick={onClose}
      >
        ×
      </button>
      <div className="bb-properties-legend-title">Features colors:</div>
      <ul className="bb-properties-legend-list">
        <li>
          <span className="bb-properties-legend-color bb-properties-legend-color-both" />
          Original + Processed
        </li>
        <li>
          <span className="bb-properties-legend-color bb-properties-legend-color-original" />
          Original only
        </li>
        <li>
          <span className="bb-properties-legend-color bb-properties-legend-color-processed" />
          Processed only
        </li>
      </ul>
    </div>
  );
}
