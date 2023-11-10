import * as fs from "fs";
import * as path from "path";


function walkDir(dirPath, callback, ...callbackArgs) {
    fs.readdirSync(dirPath).forEach((file) => {
        const filePath = path.join(dirPath, file);
        const stat = fs.statSync(filePath);
        if (stat.isDirectory()) {
            walkDir(filePath, callback, ...callbackArgs);
        } else {
            callback(filePath, ...callbackArgs);
        }
    });
}

function readFileAndAddContentToFIle(filePath, contentHolder) {
    const fileContent = fs.readFileSync(filePath, 'utf8')
    contentHolder.content += fileContent;
}

const pathsNames = [["", "all"], ["atomicdex", "atomicdex"], ["historical", "historical"], ["smart-chains", "smart-chains"], ["start-here", "start-here"]]

for (let index = 0; index < pathsNames.length; index++) {
    const element = pathsNames[index];
    let contentHolder = { content: "" };
    walkDir(`./src/pages/${element[0]}`, readFileAndAddContentToFIle, contentHolder)
    fs.writeFileSync(`./data-for-gpts/${element[1]}-content.txt`, contentHolder.content)
}

