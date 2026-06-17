import React from "react";
import AddOrEditFeatureDialog from "@teselagen/ove/src/helperComponents/AddOrEditFeatureDialog/index.js";

const HIDDEN_NOTE_PREFIXES = ["bb_", "plannot_"];

function isHiddenNoteKey(key) {
// Check if a key starts with any of the specified prefixes in HIDDEN_NOTE_PREFIXES
  if (typeof key !== "string") {
    return false;
  }
  return HIDDEN_NOTE_PREFIXES.some((prefix) => key.startsWith(prefix));
}

function splitHiddenNotes(notes = {}) {
  // Split notes into filtered and hidden categories based on the key prefixes defined 
  // in HIDDEN_NOTE_PREFIXES
  const filteredNotes = {};
  const hiddenNotes = {};

  Object.entries(notes).forEach(([key, value]) => {
    if (isHiddenNoteKey(key)) {
      hiddenNotes[key] = value;
    } else {
      filteredNotes[key] = value;
    }
  });

  return { filteredNotes, hiddenNotes };
}

export default function BenchBazeAddOrEditFeatureDialog(props) {
  // Override AddOrEditFeatureDialog to remove hidden notes from the initial values 
  // and ensure they are included back when saving the annotation
  const { initialValues = {}, beforeAnnotationCreate, ...rest } = props;
  const { filteredNotes, hiddenNotes } = splitHiddenNotes(initialValues.notes);

  const filteredInitialValues = {
    ...initialValues,
    notes: filteredNotes,
  };

  // Wrap the beforeAnnotationCreate function to ensure that hidden notes are 
  // included back in the annotation when a feature is saved
  const beforeAnnotationCreateWrapper = async (event) => {
    if (Object.keys(hiddenNotes).length > 0) {
      event.annotation.notes = {
        ...(event.annotation.notes || {}),
        ...hiddenNotes,
      };
    }

    if (typeof beforeAnnotationCreate === "function") {
      return beforeAnnotationCreate(event);
    }

    return true;
  };

  return (
    <AddOrEditFeatureDialog
      {...rest}
      initialValues={filteredInitialValues}
      beforeAnnotationCreate={beforeAnnotationCreateWrapper}
    />
  );
}
