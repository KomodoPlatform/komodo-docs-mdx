const listOfAllowedElementsToCheck = [
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "a",
    "p",
    "li",
];

import { compile } from "@mdx-js/mdx";
import * as fs from "fs";
//import { mdxAnnotations } from "mdx-annotations";
import path from "path";
import { visit } from "unist-util-visit";
import { removedWords } from "./_removed_search_words.js";

const jsonFile = JSON.parse(fs.readFileSync("./src/data/sidebar.json"));

const extractSidebarTitles = (jsonData, linksArray = []) => {
    Object.values(jsonData).forEach((data) => {
        if (!data.links) {
            extractSidebarTitles(data, linksArray);
        } else {
            data.links.forEach((data) => {
                data.href = data.href.substr(1, data.href.length - 2);
            });
            linksArray.push(...data.links);
        }
    });
    return linksArray;
};
const sidebarData = extractSidebarTitles(jsonFile);
const sidebarSearchData = {};
sidebarData.forEach((data) => {
    // we're doing this so as to allow for key referencing without looping through
    // the entire list for every mdxPath where this sidebarSearchData is being used
    sidebarSearchData[data.href] = data;
});

function removeDuplicateWordsAndMerge(str1, str2) {
    // Split strings into arrays of words
    const words1 = str1.split(" ").map((word) => word.trim());
    const words2 = str2.split(" ").map((word) => word.trim());

    // Create a Set to store unique words
    const uniqueWords = new Set([...words1, ...words2]);

    // Convert Set back to an array and join words into a single string
    const mergedStr = Array.from(uniqueWords).join(" ");

    return mergedStr;
}

function getMDXFiles(dir, filesList = []) {
    const files = fs.readdirSync(dir);

    files.forEach((file) => {
        const filePath = path.join(dir, file);
        const isDirectory = fs.statSync(filePath).isDirectory();

        if (isDirectory) {
            getMDXFiles(filePath, filesList); // Recursively search through subdirectories
        } else if (filePath.endsWith(".mdx")) {
            filesList.push(filePath); // Add MDX files to the list
        }
    });

    return filesList;
}

function transformFilePath(filePath, start = "src/pages/", end = "/index.mdx") {
    // Remove the src/pages (start) prefix
    const startIndex = filePath.indexOf(start) + start.length;
    const trimmedPath = filePath.substring(startIndex);

    // Remove the /index.mdx (end) suffix
    const endIndex = trimmedPath.lastIndexOf(end);
    const finalPath = trimmedPath.substring(0, endIndex);

    return finalPath;
}

const mdxFileWordsResultsWithFilePaths = {};

const getStringContentFromElement = (elementTree, contentList = []) => {
    elementTree.forEach((node) => {
        if (node.children) {
            getStringContentFromElement(node.children);
        } else {
            if (node.type === "text" && node.value.trim() !== "") {
                contentList.push(node.value);
            }
        }
    });
    return contentList;
};

function elementTreeChecker(mdxFilePathToCompile) {
    return async (tree) => {
        let textContentOfElement = "";
        if (tree)
            visit(tree, ["element"], (node) => {
                if (listOfAllowedElementsToCheck.includes(node.tagName)) {
                    // getStringContentFromElement(node.children);
                    if (node.tagName === "h1") {
                        // grab page title and merge with respective sidebar title for absolute pages
                        const docsPageTitle = node.children[0].value;
                        const docPath = transformFilePath(mdxFilePathToCompile);
                        const sidebarTitle = sidebarSearchData[docPath]?.title ?? "";

                        mdxFileWordsResultsWithFilePaths[mdxFilePathToCompile] = {
                            searchTitle: removeDuplicateWordsAndMerge(
                                docsPageTitle,
                                sidebarTitle
                            ),
                            docsPageTitle,
                            path: docPath,
                        };
                    }
                    visit(node, "text", (text) => {
                        if (!!text.value.trim())
                            textContentOfElement = textContentOfElement.concat(
                                " ",
                                text.value
                            );
                    });
                }
            });
        const finalText = textContentOfElement
            .toLocaleLowerCase()
            .trim()
            .replace(/[.]+/gm, " ")
            .replace(/[^a-z _-]+/gm, " ")
            .split(" ");

        const wordCountObj = {};
        finalText.forEach((word) => {
            if (!removedWords.some((removedWord) => removedWord === word) && !hasOnlyHyphens(word))
                if (word.length > 1)
                    if (wordCountObj[word]) wordCountObj[word] = wordCountObj[word] + 1;
                    else wordCountObj[word] = 1;
        });
        mdxFileWordsResultsWithFilePaths[mdxFilePathToCompile].content =
            wordCountObj;
    };
}

function hasOnlyHyphens(str) {
    return /^-+$/.test(str);
}

async function compileMdxFile(mdxFilePathToCompile) {
    const mdxFileResultString = fs.readFileSync(mdxFilePathToCompile, "utf8");
    return await compile(mdxFileResultString, {
        //remarkPlugins: [mdxAnnotations.remark],
        rehypePlugins: [
            //     mdxAnnotations.rehype,
            () => elementTreeChecker(mdxFilePathToCompile),
        ],
        //recmaPlugins: [mdxAnnotations.recma],
    });
}

const runSearchIndexingOnAllMdxFiles = async () => {
    //     extractSidebarTitles(jsonFile);
    try {
        const mdxFiles = getMDXFiles("./src/pages")
        for (let index = 0; index < mdxFiles.length; index++) {
            const file = mdxFiles[index];
            try {
                await compileMdxFile(file);
            } catch (error) {
                throw new Error(`Processing file:${file}
Error: ${error}`);
            }
        }
        fs.writeFileSync("./utils/_searchIndex.json",
            JSON.stringify(mdxFileWordsResultsWithFilePaths))

    } catch (error) {
        throw new Error(error);
    }
};
runSearchIndexingOnAllMdxFiles();
