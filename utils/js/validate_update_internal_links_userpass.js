import { visit, SKIP } from 'unist-util-visit'
import { is } from "unist-util-is";
import { promises as fs } from 'fs';
import { constants } from "fs"
import { remark } from 'remark'
import remarkMdx from 'remark-mdx'
import remarkGfm from 'remark-gfm'
import path from 'path'

(async function () {
    try {
        await walkDir("./src/pages", async (filePath) => {
            //console.log("Processing: " + filePath)
            if (!filePath.endsWith("/index.mdx")) {
                throw new Error("File path doesn't end with '/index.mdx': " + filePath)
            }
            const markdown = await fs.readFile(filePath, 'utf-8');
            const file = await remark()
                .use(remarkGfm)
                .use(remarkMdx)
                .use(() => (tree) => {
                    visit(tree, 'link', async (node) => {
                        //Process the link
                        node.url = await processLink(node.url, filePath);
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
                .process(markdown);
            if (file) {
                await fs.writeFile(filePath, String(file));
            }
        });
    } catch (error) {
        if (error) throw error;
    }
})()

// Function to process a link
async function processLink(link, currFilePath) {
    if (link.startsWith("mailto:")) {
        return link
    }
    const isExternalURL = /^https?:\/\//;
    if (isExternalURL.test(link)) return;
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
    try {
        await fs.access(internalLinkFile, constants.F_OK)
    } catch (err) {
        console.log("currNormalisedDir:" + currNormalisedDir)
        console.log(currFilePath)
        console.log(hash)
        console.log(strippedPath)

        console.log(link)
        console.log(correctUrl)

        console.error("Internal link doesn't exist: " + internalLinkFile);
        throw new Error(err)
    }

    return correctUrl;
}

async function walkDir(dir, callback) {
    let files = await fs.readdir(dir);
    await Promise.all(files.map(async (file) => {
        const filePath = path.join(dir, file);
        const stats = await fs.stat(filePath);
        if (stats.isDirectory()) {
            await walkDir(filePath, callback);
        } else if (stats.isFile()) {
            await callback(filePath);
        }
    }));
}
