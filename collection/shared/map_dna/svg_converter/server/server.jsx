import path from "path";
import React from "react";
import ReactDOMServer from "react-dom/server";
import express from "express";

import App from "../src/App";

const PORT = process.env.PORT || 3000;
const app = express();

app.get("/", (req, res) => {

  try {

    // Extract the SVG element from the rendered circular view
    const circularViewHtml = ReactDOMServer.renderToString(<App params={req.query} />);
    const svgStartPos = circularViewHtml.indexOf('<svg');
    const svgEndPos = circularViewHtml.indexOf("</svg>") + "</svg>".length;
    const svgElement = circularViewHtml.substring(svgStartPos, svgEndPos).trim();

    // Download file rather than displaying it
    res.attachment(`${req.query.plasmidTitle ? req.query.plasmidTitle : 'plasmid'}.html`);
    res.type('html');

    return res.send(svgElement);

  } catch (error) {
    return res.status(500).send("An error occurred");
  }

});

app.use(
  express.static(path.resolve(__dirname, ".", "dist"), { maxAge: "30d" })
);

app.listen(PORT, () => {
  console.log(`Server is listening on port ${PORT}`);
});
