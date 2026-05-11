import React, { useCallback } from "react";
import AddOrEditPrimerDialog from "@teselagen/ove/src/helperComponents/AddOrEditPrimerDialog/index.js";

export default function BenchBazeAddOrEditPrimerDialogOverride(props) {
  const beforeAnnotationCreate = useCallback(
    async ({ annotation, annotationTypePlural, isEdit }) => {
      // Add a custom flag note to primers only when the user adds a new one or changes 
      // the start/end of an existing one.
      // Note: props.initialValues comes from the dialog/form state and is 1-based
      // The annotation value passed have been converted to 0-based
      const previousPrimer = props.initialValues || {};
      const startDiff = previousPrimer.start - annotation.start;
      const endDiff = previousPrimer.end - annotation.end;
      const isOneBasedOffset = startDiff === 1 && endDiff === 1;
      const hasPrimerPositionChanged =
        annotationTypePlural === "primers" &&
        annotation &&
        (!isEdit ||
          (!isOneBasedOffset &&
            (previousPrimer.start !== annotation.start ||
              previousPrimer.end !== annotation.end)));

      if (hasPrimerPositionChanged) {
        const notes = annotation.notes || {};
        const noteValues = Array.isArray(notes.bb_primer_ove)
          ? notes.bb_primer_ove
          : [];
        if (!noteValues.includes("true")) {
          noteValues.push("true");
        }
        annotation.notes = {
          ...notes,
          bb_primer_ove: noteValues,
        };
      }

      if (typeof props.beforeAnnotationCreate === "function") {
        return props.beforeAnnotationCreate({
          annotation,
          annotationTypePlural,
          props,
          isEdit,
        });
      }

      return true;
    },
    [props.beforeAnnotationCreate],
  );

  return (
    <AddOrEditPrimerDialog
      {...props}
      beforeAnnotationCreate={beforeAnnotationCreate}
    />
  );
}
