// jest-dom adds custom jest matchers for asserting on DOM nodes.
// https://github.com/testing-library/jest-dom
// Auto-loaded by react-scripts test (Create React App convention).
import "@testing-library/jest-dom";

// react-router@7's CJS build touches TextEncoder/TextDecoder at module-load
// time; CRA's bundled jsdom test environment doesn't provide them as
// globals by default (unlike real browsers or newer jsdom). Polyfill from
// Node's own util module before any test file's imports run.
if (typeof global.TextEncoder === "undefined") {
  const { TextEncoder, TextDecoder } = require("util");
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;
}

// jsdom does not implement Element.scrollIntoView at all; several pages
// (e.g. SparkInterview.jsx) call it on every render to keep the latest
// turn in view -- harmless no-op under test.
if (typeof window !== "undefined" && !window.HTMLElement.prototype.scrollIntoView) {
  window.HTMLElement.prototype.scrollIntoView = function scrollIntoView() {};
}
