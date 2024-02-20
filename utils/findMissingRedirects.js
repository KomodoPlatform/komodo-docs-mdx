const oldDocsFileData = require("./_fileData_old_documentation.json");
const oldDocsPaths = Object.keys(oldDocsFileData);
let oldDocsURLs = oldDocsPaths.map((url) => url.replace("/docs", "") + ".html");

function ignoreOldDocsURLs(url) {
  return (
    url.startsWith("/mmV1") ||
    url.startsWith("/notary/deprecated") ||
    url.startsWith("/mmV2/LP") ||
    url.startsWith("/basic-docs/antara/antara-tutorials/gaming-sdk-tutorial") ||
    url.endsWith("README.html")
  );
}
let relevantOldDocsURLs = oldDocsURLs.filter((url) => !ignoreOldDocsURLs(url));
const redirectMap = require("./Redirect-map.json");
const oldRedirectURLs = Object.keys(redirectMap);
const missingRedirectURLs = relevantOldDocsURLs.filter(
  (item) => !oldRedirectURLs.includes(item)
);
console.log(JSON.stringify(missingRedirectURLs, null, 2));
