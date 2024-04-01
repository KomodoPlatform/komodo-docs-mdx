//import { visit, EXIT } from 'unist-util-visit'
import {EXIT, visitParents} from 'unist-util-visit-parents'

import { promises as fs } from 'fs';
import path from 'path'
import { remark } from 'remark'

(async function () {
    try {
        await walkDir("./src/pages", async (filePath) => {
            const markdown = await fs.readFile(filePath, 'utf-8');
            //console.log(filePath)
            const file = await remark()
                .use(() => (tree) => {
                    let documentContainsTitleHeading = false;
                    visitParents(tree, 'heading', (node, ancestors) => {                       
                        let nodeHasLinks = node.children.some(child => child.type === "link") 
                        if(nodeHasLinks){
                            throw new Error(`${JSON.stringify(node,null,2)} 
in file:${filePath} has a link. Please remove it.`)
                        }                                            
                        if (node.depth === 1 && !ancestors.some((ancestor) => ancestor.name === "DevComment")) {
                            documentContainsTitleHeading = true;
                            EXIT;
                        }
                    });
                    if (!documentContainsTitleHeading) {
                        throw new Error("Document must contain a <h1>: " + filePath);
                    }
                })
                .process(markdown);
        });
    } catch (error) {
        if (error) throw error;
    }
})()

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