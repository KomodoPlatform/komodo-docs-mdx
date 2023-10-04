import * as acorn from "acorn";

import { SKIP, visit } from "unist-util-visit";

import { constants } from "fs";
import fs from "fs";
import http from "http";
import https from "https";
import { is } from "unist-util-is";
import { mdxAnnotations } from "mdx-annotations";
import path from "path";
import { remark } from "remark";
import remarkGfm from "remark-gfm";
import remarkMdx from "remark-mdx";
import { slugifyWithCounter } from "@sindresorhus/slugify";
import { toString } from "mdast-util-to-string";

const manualLinkFile = "links-to-manually-check";
if (fs.existsSync(manualLinkFile)) {
  fs.unlinkSync(manualLinkFile);
}

(async function () {
  try {
    let filepaths = [];
    walkDir("./src/pages", (filepath) => filepaths.push(filepath));
    //await createFileSlugs(filepaths);

    let filepathSlugs = JSON.parse(fs.readFileSync("filepathSlugs.json"));
    for (let index = 0; index < filepaths.length; index++) {
      const filePath = filepaths[index];
      await processFile(filePath, filepathSlugs);
    }
  } catch (error) {
    if (error) throw error;
  }
})();

async function createFileSlugs(filepaths) {
  const filepathSlugs = {};

  for (let index = 0; index < filepaths.length; index++) {
    const filePath = filepaths[index];
    try {
      await remark()
        .use(mdxAnnotations.remark)
        .use(remarkMdx)
        .use(() => (tree) => {
          const slugs = [];

          let slugify = slugifyWithCounter();
          // Visit all heading nodes and collect their values
          visit(tree, "heading", (node) => {
            const slug = slugify(toString(node));
            slugs.push(slug);
          });
          filepathSlugs[filePath] = slugs;
        })
        .process(fs.readFileSync(filePath, "utf-8"));
    } catch (error) {
      console.log(error);
      throw new Error(`filePath: ${filePath}`);
    }
  }

  fs.writeFileSync(
    "filepathSlugs.json",
    JSON.stringify(filepathSlugs, null, 2)
  );
}

async function processFile(filePath, filepathSlugs) {
  if (!filePath.endsWith("/index.mdx")) {
    throw new Error("File path doesn't end with '/index.mdx': " + filePath);
  }
  // if (!filePath.includes("/non_fungible_token")) {
  //     return
  // }
  console.log("Processing: " + filePath);
  const file = await remark()
    .use(remarkGfm)
    .use(remarkMdx)
    .use(() => (tree) => {
      //console.log("Processing: " + filePath)
      const hasTitleAndDesc = tree.children.some(
        (node) =>
          node.type === "mdxjsEsm" && isValidTitleDescExports(node.value)
      );
      if (!hasTitleAndDesc) {
        throw new Error("File doesn't have title/description: " + filePath);
      }
    })
    .use(() => (tree) => {
      visit(tree, "link", async (node) => {
        //Process the link
        node.url = await processLink(node.url, filePath, filepathSlugs);
      });
    })
    .use(() => (tree) => {
      visit(tree, (node, nodeIndex, parentNode) => {
        if (!filePath.includes("src/pages/atomicdex")) {
          return SKIP;
        }
        // if (
        //     is(node, { name: "CodeGroup" })) {
        //     console.log(node)
        // }
        try {
          if (
            is(node, { name: "CodeGroup" }) &&
            node.attributes.some(
              (attr) =>
                attr.type === "mdxJsxAttribute" &&
                attr.name === "mm2MethodDecorate" &&
                attr.value === "true"
            )
          ) {
            // console.log(node)
            const originalChild = node.children[0];
            if (node.children.length !== 1 || originalChild.lang !== "json") {
              throw new Error(
                `unexpected code block in file ${filePath} : ` +
                JSON.stringify()
              );
            }
            const clonedChild = JSON.parse(JSON.stringify(originalChild));
            let methodObj = JSON.parse(clonedChild.value);
            methodObj.userpass = "testpsw";
            clonedChild.value = JSON.stringify(methodObj, null, 2);
            //console.log(clonedChild)
            node.children = [clonedChild];
            return SKIP;
          }
        } catch (error) {
          console.log(filePath);
          console.log(node);
          throw new Error(error);
        }
      });
    })
    .process(fs.readFileSync(filePath, "utf-8"));
  if (file) {
    fs.writeFileSync(filePath, String(file));
  }
}
// Function to process a link
async function processLink(link, currFilePath, filepathSlugs) {
  if (link.startsWith("mailto:")) {
    return link;
  }
  const isExternalURL = /^https?:\/\//;
  if (isExternalURL.test(link)) {
    await processExternalLink(link, currFilePath);
    return link;
  }

  let filePath = "src/pages";
  let strippedPath = link.split("#")[0]; // strips hash
  if (strippedPath.endsWith("/")) {
    strippedPath = strippedPath.slice(0, -1);
  }
  const hash = link.split("#")[1];
  let correctUrl;
  let currNormalisedDir;
  const currentWorkingDirectory = process.cwd();
  currNormalisedDir = currFilePath.replace("/index.mdx", "").split("/");
  currNormalisedDir.pop();
  currNormalisedDir = currNormalisedDir.join("/");
  if (
    strippedPath.endsWith(".md") ||
    strippedPath.endsWith(".html") ||
    strippedPath.endsWith(".mdx")
  ) {
    let newStrippedPart = strippedPath.split(".");
    newStrippedPart.pop();
    newStrippedPart = newStrippedPart.join(".");
    newStrippedPart = newStrippedPart.split("/");
    let fileName = newStrippedPart.pop();
    if (fileName !== "index") {
      correctUrl = strippedPath
        .replace(".html", "/")
        .replace(".md", "/")
        .replace(".mdx", "/");
      correctUrl =
        path.join(path.resolve(currNormalisedDir, correctUrl) + "/") +
        (hash ? `#${hash}` : "");
    }
    newStrippedPart = newStrippedPart.join("/");
    strippedPath = newStrippedPart;
  }
  if (!correctUrl) {
    if (strippedPath === "") {
      correctUrl =
        currFilePath
          .replace("index.mdx", "")
          .replace(path.join(filePath + "/").slice(0, -1), "") +
        (hash ? `#${hash}` : "");
    } else {
      correctUrl =
        path.join(path.resolve(currNormalisedDir, strippedPath), "/") +
        (hash ? `#${hash}` : "");
    }
  }
  correctUrl = correctUrl.replace(
    path.join(currentWorkingDirectory, filePath),
    ""
  );
  const correctUrlSplit = correctUrl.split("#");
  const internalLinkFile = path.join(
    filePath,
    correctUrlSplit[0] + "index.mdx"
  );
  let slug;
  if (correctUrlSplit[1]) {
    let slugify = slugifyWithCounter();
    slug = slugify(correctUrlSplit[1]);
    correctUrl = correctUrlSplit[0] + "#" + slug;
  }

  if (
    slug &&
    !filepathSlugs[internalLinkFile].some((slugO) => slug === slugO)
  ) {
    console.log("------------------------------------------------");
    console.log("currNormalisedDir: " + currNormalisedDir);
    console.log("currFilePath: " + currFilePath);
    console.log("hash: " + hash);
    console.log("strippedPath: " + strippedPath);
    console.log("link: " + link);
    console.log("correctUrl: " + correctUrl);
    console.log("internalLinkFile: " + internalLinkFile);
    console.log("slug: " + slug);
    console.log("------------------------------------------------");
    throw new Error(
      `Processing file: ${currFilePath}, slug: ${slug} (original slug: ${correctUrlSplit[1]} ) not present in file: ${internalLinkFile}`
    );
  }
  try {
    fs.accessSync(internalLinkFile, constants.F_OK);
  } catch (err) {
    console.log("currNormalisedDir:" + currNormalisedDir);
    console.log("currFilePath: " + currFilePath);
    console.log("hash: " + hash);
    console.log("strippedPath: " + strippedPath);
    console.log("link: " + link);
    console.log("correctUrl: " + correctUrl);
    console.log(
      "Internal link file doesn't exist/can't access it: " + internalLinkFile
    );
    throw new Error(err);
  }

  return correctUrl;
}

// needs import { promises as fs } from 'fs';
// async function asyncWalkDir(dir, callback) {
//     let files = await fs.readdir(dir);
//     await Promise.all(files.map(async (file) => {
//         const filePath = path.join(dir, file);
//         const stats = await fs.stat(filePath);
//         if (stats.isDirectory()) {
//             await walkDir(filePath, callback);
//         } else if (stats.isFile()) {
//             await callback(filePath);
//         }
//     }));
// }

export function walkDir(dirPath, callback) {
  fs.readdirSync(dirPath).forEach((file) => {
    const filePath = path.join(dirPath, file);
    const stat = fs.statSync(filePath);
    if (stat.isDirectory()) {
      walkDir(filePath, callback);
    } else {
      callback(filePath);
    }
  });
}

function isValidTitleDescExports(str) {
  // console.log(str);
  try {
    const parsed = acorn.parse(str, {
      sourceType: "module",
      ecmaVersion: 2020,
    });

    let titleExported = false;
    let descriptionExported = false;
    for (const node of parsed.body) {
      if (node.type === "ExportNamedDeclaration") {
        if (node.declaration && node.declaration.declarations) {
          for (const declaration of node.declaration.declarations) {
            if (
              declaration.id.name === "title" &&
              declaration.init.type === "Literal"
            ) {
              titleExported = true;
              // let numChars = declaration.init.value.length;
              // if (numChars > 60) {
              //   throw new Error(`Title: "${declaration.init.value}" has ${numChars} characters, which is greater than 60`)
              // }
            }
            if (
              declaration.id.name === "description" &&
              declaration.init.type === "Literal"
            ) {
              descriptionExported = true;
              // let numChars = declaration.init.value.length;
              // if (numChars > 160 || numChars < 140) {
              //   throw new Error(`Description: "${declaration.init.value}" has ${numChars} characters, which is not between 140 and 160`)
              // }
            }
          }
        }
      }
    }

    return titleExported && descriptionExported;
  } catch (e) {
    throw new Error(e)
    //console.log(e)
    //return false; // Parsing error means the string is not valid JS
  }
}

function checkUrlStatusCode(url) {
  return new Promise((resolve, reject) => {
    let client;

    if (url.startsWith("https://")) {
      client = https;
    } else if (url.startsWith("http://")) {
      client = http;
    } else {
      reject(new Error("URL must start with http:// or https://"));
      return;
    }
    let requestOptions = new URL(url);
    requestOptions.headers = {
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
      Referer: "https://www.google.com/",
    };

    const req = client.get(requestOptions, (response) => {
      if (
        response.statusCode >= 300 &&
        response.statusCode < 400 &&
        response.headers.location
      ) {
        resolve({
          newLocation: response.headers.location,
          statusCode: response.statusCode,
        });
      } else {
        resolve({
          newLocation: "",
          statusCode: response.statusCode,
        });
      }
    });
    req.on("error", (err) => {
      reject(err);
    });
    req.setTimeout(5000, () => {
      req.destroy();
      reject(new Error("Request timed out " + url));
    });
  });
}

async function processExternalLink(link, currFilePath) {
  let IgnoreURLs = [
    "https://moralis-proxy.komodo.earth",
    "https://nft.antispam.dragonhound.info"
  ]
  if (
    link.startsWith("http://127.0.0.1") ||
    link.startsWith("https://127.0.0.1") ||
    link.startsWith("http://localhost") ||
    link.startsWith("https://localhost")
  ) {
    return;
  }
  if (
    link.startsWith("http://twitter.com") ||
    link.startsWith("https://twitter.com")
  ) {
    return;
  }
  if (
    link.startsWith("http://komodoplatform.com/discord") ||
    link.startsWith("https://komodoplatform.com/discord")
  ) {
    return;
  }
  try {
    const { newLocation, statusCode } = await checkUrlStatusCode(link);
    if (statusCode === 200) {
      //console.log("The external URL exists: " + link);
      return;
    } else if (
      statusCode === 301 ||
      statusCode === 302 ||
      statusCode === 308 ||
      statusCode === 307
    ) {
      throw new Error(
        `The link: ${link} has a ${statusCode} redirect to ${newLocation}`
      );
    } else if (statusCode === 403 || statusCode === 405 || statusCode === 500) {
      // console.log(
      //   `Check this link manually: [${link}] It responds with statuscode: ${statusCode} `
      // );
      fs.appendFileSync(manualLinkFile, link + "\n");
    } else if (IgnoreURLs.some(ignoreLink => link.includes(ignoreLink))) {
      fs.appendFileSync(manualLinkFile, link + "\n");
    } else {
      throw new Error(
        `The URL ${link} in the file ${currFilePath} returned a statuscode: ${statusCode}`
      );
    }
  } catch (err) {
    if (err.message.startsWith("Request timed out")) {
      console.log(`Request timed out when checking the URL ${link} in the file ${currFilePath}`);
      return;
    } else {
      throw new Error(err);
    }
  }
}
