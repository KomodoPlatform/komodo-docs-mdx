import * as fs from "fs";
import * as path from "path";

const sidebarNavData = JSON.parse(fs.readFileSync("./src/data/sidebar.json", 'utf8'))
const navbarNavData = JSON.parse(fs.readFileSync("./src/data/sidebar.json", 'utf8'))

function walkDir(dirPath, callback) {
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
const dirsWithNoIndex = [];
let filesOtherThanIndex = [];

function findMissingIndexInDirs(dirPath) {
  let foundIndexFile = false;
  let otherFilesInDir = [];
  const pathsInDir = fs.readdirSync(dirPath);
  for (let i = 0; i < pathsInDir.length; i++) {
    let curPath = path.join(dirPath, pathsInDir[i]);
    let stat = fs.statSync(curPath);
    if (stat.isDirectory()) {
      findMissingIndexInDirs(curPath);
    } else {
      if (curPath.endsWith("index.mdx")) {
        foundIndexFile = true;
      } else if (
        !(curPath.endsWith("/_app.tsx") || curPath.endsWith("/_document.tsx"))
      ) {
        otherFilesInDir.push(curPath);
      }
    }
  }
  if (!foundIndexFile) {
    dirsWithNoIndex.push(dirPath + "/");
  }
  if (otherFilesInDir.length > 0) {
    filesOtherThanIndex = [...filesOtherThanIndex, ...otherFilesInDir];
  }
}

findMissingIndexInDirs("./src/pages");

// check if every dir contains a index.mdx file and if every page is present in sidebar.json

const fileNames = [];
const getFileNames = (filepath) => {
  if (
    !(filepath.endsWith("/_app.tsx") || filepath.endsWith("/_document.tsx"))
  ) {
    let filePathURL = filepath
      .replace("src/pages", "")
      .replace("index.mdx", "");
    fileNames.push(filePathURL);
  }
};

walkDir("./src/pages", getFileNames);

const pagesArray = [];

function readTitleLinksAndHrefs(data) {
  Object.keys(data).forEach(function (key) {
    var navigation = data[key];
    Object.keys(navigation).forEach(function (navigationKey) {
      var sections = navigation[navigationKey];
      sections.forEach(function (page) {
        if (page.titleLink && page.links.length > 0) {
          throw new Error("To be able to have collapsible sections in left sidebar, title with titlelink can't have sub-items")
        }
        if (page.titleLink) {
          pagesArray.push(page.titleLink);
        }
        if (page.links) {
          for (const link of page.links) {
            pagesArray.push(link.href);
          }
        }
      });
    });
  });
}

// Read titleLinks and links.href values from antaraFrameworkPageNavigation

readTitleLinksAndHrefs(sidebarNavData);
readTitleLinksAndHrefs(navbarNavData);

function compareArrays(fileNames, pagesArray) {
  var differences = [];
  fileNames.forEach(function (element) {
    if (!pagesArray.includes(element)) {
      differences.push(element);
    }
  });

  return differences;
}

//pages present in the file system but not in sidebar
var pagesNotInSidebar = compareArrays(fileNames, pagesArray);
//pages present in the sidebar but not in file system
var pagesNotInFileSystem = compareArrays(pagesArray, fileNames);

function removeUndefinedStrings(array) {
  return array.filter(function (element) {
    return element !== undefined;
  });
}

let errorString = "";

if (pagesNotInSidebar.length > 0) {
  errorString =
    errorString +
    `\npages present in the file system but not in sidebar:
${pagesNotInSidebar.join("\n")}
`;
}

if (pagesNotInFileSystem.length > 0) {
  errorString =
    errorString +
    `\npages present in the sidebar but not in file system:
${pagesNotInFileSystem.join("\n")}
`;
}

if (dirsWithNoIndex.length > 0) {
  errorString =
    errorString +
    `\nDirectories without index file: 
${dirsWithNoIndex.join("\n")}
Create index.mdx files with the appropriate content for above directories.
`;
}

if (filesOtherThanIndex.length > 0) {
  errorString =
    errorString +
    `\nFiles other than index found:
${filesOtherThanIndex.join("\n")}
Replace these files with directories of same name and create index.mdx files inside them with the same content.\n
`;
}

if (errorString !== "") {
  throw new Error(errorString);
} else {
  console.log("file presence checker generated no errors.")
}