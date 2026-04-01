import path from "path";
import React from "react";
import ReactDOMServer from "react-dom/server";
import express from "express";
import fs from "fs";
import { anyToJson } from "@teselagen/bio-parsers";
import { tidyUpSequenceData } from "ve-sequence-utils";


import App from "../src/App";

const PORT = process.env.PORT || 3000;
const app = express();

const SUPPORTED_EXTENSIONS = ["gb", "gbk", "dna"];

app.get("/", async (req, res) => {
  try {
    const mapDnaPath = req.query.path;

    // Validate required parameter
    if (!mapDnaPath) {
      return res
        .status(400)
        .send("Missing required query parameter: path");
    }

    // Validate file extension
    const fileType = mapDnaPath.split(".").slice(-1)[0].toLowerCase();
    if (!SUPPORTED_EXTENSIONS.includes(fileType)) {
      return res
        .status(400)
        .send(
          `Unsupported file extension ".${fileType}". Supported: ${SUPPORTED_EXTENSIONS.join(", ")}`,
        );
    }

    // Validate file exists
    const resolvedPath = path.resolve(mapDnaPath);
    if (!fs.existsSync(resolvedPath)) {
      return res.status(404).send(`File not found: ${mapDnaPath}`);
    }

    let mapDnaData = fs.readFileSync(resolvedPath);

    // Parse the input file to extract sequence data
    // anyToJson handles all formats and is async
    let parsedResults = await anyToJson({ buffer: mapDnaData }, { fileName: resolvedPath });

    if (!parsedResults || parsedResults.length === 0) {
      return res
        .status(500)
        .send(`Parser returned no results for: ${mapDnaPath}`);
    }
    if (!parsedResults[0].parsedSequence) {
      const parseError = parsedResults[0].messages
        ?.map((m) => m.message)
        .join("; ");
      return res
        .status(500)
        .send(`Failed to parse file: ${parseError || "unknown parse error"}`);
    }

    const mapDnaJson = tidyUpSequenceData(parsedResults[0]["parsedSequence"]);

    // Set plasmid name
    mapDnaJson.name = req.query.title
      ? req.query.title
      : mapDnaJson.name || "Untitled Plasmid";

    // Remove features that do not need to be shown, ever!
    const plasmidLength = mapDnaJson.size;
    const featNameExclude = [
      "synthetic dna construct",
      "recombinant plasmid",
      "source",
    ];
    mapDnaJson.features = mapDnaJson.features.filter(
      (feat) =>
        !(
          featNameExclude.includes(feat.name.toLowerCase()) &&
          plasmidLength === feat.end - feat.start + 1
        ),
    );

    // Extract the SVG element from the rendered circular view
    const circularViewHtml = ReactDOMServer.renderToString(
      <App sequenceData={mapDnaJson} />,
    );
    const svgStartPos = circularViewHtml.indexOf("<svg");
    const svgEndPos = circularViewHtml.indexOf("</svg>") + "</svg>".length;

    // Validate that SVG tags were found
    if (svgStartPos === -1 || svgEndPos < svgStartPos) {
      return res.status(500).send("Rendering produced no SVG output");
    }

    // Extract and trim the SVG element
    const svgElement = circularViewHtml
      .substring(svgStartPos, svgEndPos)
      .trim();

    // Download file rather than displaying it
    res.attachment(
      `${req.query.title ? req.query.title : "plasmid"}.html`,
    );
    res.type("html");

    return res.send(svgElement);
  } catch (error) {
    console.error("Request handling error:", error);
    return res.status(500).send(error.toString());
  }
});

app.use(
  express.static(path.resolve(__dirname, ".", "dist"), { maxAge: "30d" }),
);

app.listen(PORT, () => {
  console.log(`Server is listening on port ${PORT}`);
});
