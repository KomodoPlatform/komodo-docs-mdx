import { visit, SKIP } from 'unist-util-visit'
import { is } from "unist-util-is";
import fs from 'fs';
import { constants } from "fs"
import { remark } from 'remark'
import remarkMdx from 'remark-mdx'
import remarkGfm from 'remark-gfm'
import path from 'path'
import { toString } from "mdast-util-to-string";

import { slugifyWithCounter } from "@sindresorhus/slugify";
import * as acorn from "acorn"

(async function () {
    try {
        let filepaths = []
        const filepathSlugs = {}
        walkDir("./src/pages", filepath => filepaths.push(filepath));
        console.log(filepaths.length)
        for (let index = 0; index < filepaths.length; index++) {
            const filePath = filepaths[index];
            await remark().use(() => (tree) => {
                const slugs = [];

                let slugify = slugifyWithCounter();
                // Visit all heading nodes and collect their values
                visit(tree, 'heading', (node) => {
                    const slug = slugify(toString(node));
                    slugs.push(slug);
                });
                filepathSlugs[filePath] = slugs
                // console.log(slugs);
            }).process(fs.readFileSync(filePath, 'utf-8'));
        }
        console.log(Object.keys(filepathSlugs).length)
        for (let index = 0; index < filepaths.length; index++) {
            const filePath = filepaths[index];
            await processFile(filePath, filepathSlugs)
        }
    } catch (error) {
        if (error) throw error;
    }
})()

async function processFile(filePath, filepathSlugs) {
    if (!filePath.endsWith("/index.mdx")) {
        throw new Error("File path doesn't end with '/index.mdx': " + filePath)
    }
    // if (!filePath.includes("/setup/ecosystem-launch-parameters/")) {
    //     return
    // }
    // console.log("Processing: " + filePath)
    const file = await remark()
        .use(remarkGfm)
        .use(remarkMdx)
        .use(() => (tree) => {
            //console.log("Processing: " + filePath)
            const hasTitleAndDesc = tree.children.some(node => node.type === 'mdxjsEsm' && isValidTitleDescExports(node.value))
            if (!hasTitleAndDesc) {
                throw new Error("File doesn't have title/description: " + filePath)
            }
        })
        .use(() => (tree) => {
            visit(tree, 'link', (node) => {
                //Process the link
                node.url = processLink(node.url, filePath, filepathSlugs);
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
                        node.attributes.some(attr => attr.type === 'mdxJsxAttribute' && attr.name === "mm2MethodDecorate" && attr.value === "true")
                    ) {
                        // console.log(node)
                        const originalChild = node.children[0];
                        if (node.children.length !== 1 || originalChild.lang !== "json") {
                            throw new Error(`unexpected code block in file ${filePath} : ` + JSON.stringify())
                        }
                        const clonedChild = JSON.parse(JSON.stringify(originalChild));
                        let methodObj = JSON.parse(clonedChild.value)
                        methodObj.userpass = "testpsw"
                        clonedChild.value = JSON.stringify(methodObj, null, 2)
                        //console.log(clonedChild)
                        node.children = [clonedChild];
                        return SKIP;
                    }
                } catch (error) {
                    throw new Error(error)
                }

            });
        })
        .process(fs.readFileSync(filePath, 'utf-8'));
    if (file) {
        fs.writeFileSync(filePath, String(file));
    }
}
// Function to process a link
function processLink(link, currFilePath, filepathSlugs) {
    if (link.startsWith("mailto:")) {
        return link
    }
    const isExternalURL = /^https?:\/\//;
    if (isExternalURL.test(link)) return link;
    let filePath = "src/pages";
    let strippedPath = link.split("#")[0]; // strips hash
    if (strippedPath.endsWith("/")) {
        strippedPath = strippedPath.slice(0, -1)
    }
    const hash = link.split("#")[1];
    let correctUrl;
    let currNormalisedDir
    const currentWorkingDirectory = process.cwd();
    currNormalisedDir = currFilePath.replace("/index.mdx", "").split("/")
    currNormalisedDir.pop()
    currNormalisedDir = currNormalisedDir.join("/")
    if (strippedPath.endsWith(".md") || strippedPath.endsWith(".html") || strippedPath.endsWith(".mdx")) {
        let newStrippedPart = strippedPath.split(".")
        newStrippedPart.pop()
        newStrippedPart = newStrippedPart.join(".")
        newStrippedPart = newStrippedPart.split("/")
        let fileName = newStrippedPart.pop()
        if (fileName !== "index") {
            correctUrl = strippedPath.replace(".html", "/").replace(".md", "/").replace(".mdx", "/")
            correctUrl = path.join(path.resolve(currNormalisedDir, correctUrl) + "/") + (hash ? `#${hash}` : "")
        }
        newStrippedPart = newStrippedPart.join("/")
        strippedPath = newStrippedPart
    }
    if (!correctUrl) {
        if (strippedPath === "") {
            correctUrl = currFilePath.replace("index.mdx", "").replace(path.join(filePath + "/").slice(0, -1), "") + (hash ? `#${hash}` : "")

        } else {
            correctUrl = path.join(path.resolve(currNormalisedDir, strippedPath), "/") + (hash ? `#${hash}` : "")
        }
    }
    correctUrl = correctUrl.replace(path.join(currentWorkingDirectory, filePath), "")

    // console.log("--------------------------------")
    // console.log("currNormalisedDir:" + currNormalisedDir)
    // console.log(currFilePath)
    // console.log(hash)
    // console.log(strippedPath)
    // console.log(link)
    // console.log(correctUrl)
    // console.log("--------------------------------")

    const internalLinkFile = path.join(filePath, correctUrl.split("#")[0] + "index.mdx")
    const slug = correctUrl.split("#")[1]
    try {
        fs.accessSync(internalLinkFile, constants.F_OK)
    } catch (err) {
        console.log("currNormalisedDir:" + currNormalisedDir)
        console.log(currFilePath)
        console.log(hash)
        console.log(strippedPath)

        console.log(link)
        console.log(correctUrl)

        console.error("Internal link file doesn't exist: " + internalLinkFile);
        throw new Error(err)
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
    try {
        const parsed = acorn.parse(str, {
            sourceType: 'module',
            ecmaVersion: 2020
        });

        let titleExported = false;
        let descriptionExported = false;
        for (const node of parsed.body) {
            if (node.type === 'ExportNamedDeclaration') {
                if (node.declaration && node.declaration.declarations) {
                    for (const declaration of node.declaration.declarations) {
                        if (
                            declaration.id.name === 'title' &&
                            declaration.init.type === 'Literal'
                        ) {
                            titleExported = true;
                        }
                        if (
                            declaration.id.name === 'description' &&
                            declaration.init.type === 'Literal'
                        ) {
                            descriptionExported = true;
                        }
                    }
                }
            }
        }

        return titleExported && descriptionExported;
    } catch (e) {
        //console.log(e)
        return false;  // Parsing error means the string is not valid JS
    }
}
