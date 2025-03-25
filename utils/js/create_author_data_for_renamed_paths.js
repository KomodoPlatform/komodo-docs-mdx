import * as fs from "fs";
import dotenv from "dotenv";

dotenv.config();

const GITHUB_TOKEN = process.env.GITHUB_TOKEN; // Replace with your token
const REPO = "KomodoPlatform/komodo-docs-mdx";               // Replace with "owner/repository"
const PR_NUMBER = "391";         // Replace with the pull request number
const BASE_URL = `https://api.github.com/repos/${REPO}/pulls/${PR_NUMBER}/files`;

const fetchAllFiles = async () => {
    let page = 1;
    const perPage = 100;
    let allFiles = [];

    while (true) {
        const response = await fetch(`${BASE_URL}?per_page=${perPage}&page=${page}`, {
            headers: {
                "Authorization": `token ${GITHUB_TOKEN}`,
                "Accept": "application/vnd.github.v3+json",
            },
        });

        if (!response.ok) {
            console.error(`Error: ${response.status} - ${response.statusText}`);
            break;
        }

        const files = await response.json();

        // Break if no more files
        if (files.length === 0) break;

        allFiles = allFiles.concat(files);
        page++;
    }

    // Filter renamed files
    const renamedFiles = allFiles
        .filter(file => file.status === "renamed")
        .map(file => ({
            filename: file.filename,
            previous_filename: file.previous_filename,
        }));

    return renamedFiles;
};

function convertPathToRoute(filePath) {
    // Remove src/pages prefix and file extension, handle index files
    return '/' + filePath
        .replace(/^src\/pages\//, '')
        .replace(/(\/index)?\.mdx?$/, '');
}

(async () => {
    try {
        // Get list of renamed files from PR
        const renamedFiles = await fetchAllFiles();
        console.log("Renamed Files:", renamedFiles);

        // Read the current file data
        const fileData = JSON.parse(fs.readFileSync("./utils/_fileData.json", 'utf8'));
        const oldFileData = JSON.parse(fs.readFileSync("./utils/_fileData_old_documentation_mod.json", 'utf8'));

        // Create a new object to store the merged data for renamed files
        const renamedPathsData = {};

        // Process each renamed file
        for (const file of renamedFiles) {
            const newRoute = convertPathToRoute(file.filename);
            const oldRoute = convertPathToRoute(file.previous_filename);

            // Get old file data from both current and old file data
            const oldFileInfo = oldFileData[oldRoute] || {};
            const currentFileInfo = fileData[oldRoute] || {};

            // Store the mapping and merged data
            renamedPathsData[newRoute] = {
                oldRoute,
                contributors: [
                    ...(oldFileInfo.contributors || []),
                    ...(currentFileInfo.contributors || [])
                ].filter((contributor, index, self) =>
                    index === self.findIndex(c =>
                        c.name === contributor.name && c.email === contributor.email
                    )
                ),
                dateCreated: [
                    oldFileInfo.dateCreated,
                    currentFileInfo.dateCreated
                ].filter(Boolean).sort()[0] // Get earliest date if available
            };
        }

        // Save the renamed paths data to a new file
        fs.writeFileSync("./utils/_renamedPathsData.json", JSON.stringify(renamedPathsData, null, 2));
        console.log("Renamed paths data saved successfully!");

    } catch (error) {
        console.error("Error processing files:", error);
    }
})();


