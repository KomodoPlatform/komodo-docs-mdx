const https = require('https');
const fs = require('fs');
const path = require("path");
const child_process = require("child_process");
const spawnSync = child_process.spawnSync;

const authorsData = JSON.parse(fs.readFileSync("./authors.json", 'utf8'));
const fileData = {};

(async function () {
    const contributorsInfoUrl = "https://api.github.com/repos/komodoplatform/komodo-docs-mdx/contributors"

    const options = {
        headers: {
            'User-Agent': 'komodo-docs-mdx-ci'
        }
    };

    try {
        const { response } = await httpsGet(contributorsInfoUrl, options)
        const contributorData = JSON.parse(response)
        contributorData.forEach(contributor => {
            if (!authorsData[contributor.login]) {
                authorsData[contributor.login] = {
                    username: contributor.login,
                    commit_emails: [],
                    socials: {
                        twitter: "",
                        linkedin: ""
                    }
                }
            }
            authorsData[contributor.login].id = contributor.id
            authorsData[contributor.login].avatar_url = contributor.avatar_url
        });
    } catch (error) {
        console.error(error);
    }

    for (const username in authorsData) {
        const imageUrl = authorsData[username].avatar_url

        // const { response: imgResponse, headers: respHeaders } = await httpsGet(imageUrl, options)

        // const fileExt = respHeaders["content-type"].split("/")[1]
        // const imgFilename = `./src/images/authors/${username}.${fileExt}`
        // fs.writeFileSync(imgFilename, imgResponse)
        const imgName = await downloadImage(imageUrl, username)
        authorsData[username].image = imgName
    }

    fs.writeFileSync("authors.json", JSON.stringify(authorsData, null, 4))


    walkDir("./src/pages", getAllFileData);
    fs.writeFileSync("./utils/_fileData.json", JSON.stringify(fileData, null, 2));
})();

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

async function httpsGet(url, options) {
    return new Promise((resolve, reject) => {
        https.get(url, options, (resp) => {
            let data = '';

            // A chunk of data has been received.
            resp.on('data', (chunk) => {
                data += chunk;
            });

            // The whole response has been received. Resolve the promise.
            resp.on('end', () => {
                resolve({ response: data, headers: resp.headers });
            });

        }).on("error", (err) => {
            reject(err);
        });
    });
}

async function downloadImage(url, username) {
    const options = {
        headers: {
            'User-Agent': 'komodo-docs-mdx-ci'
        }
    };
    return new Promise((resolve, reject) => {
        let filename;
        https.get(url, options, (response) => {
            const fileExt = response.headers["content-type"].split("/")[1]
            filename = `./src/images/authors/${username}.${fileExt}`
            const file = fs.createWriteStream(filename);

            response.pipe(file);
            file.on('finish', () => {
                file.close();
                console.log('Image downloaded successfully: ' + filename);
                resolve(`${username}.${fileExt}`)
            });
        }).on('error', (error) => {
            fs.unlink(filename);
            reject(`Error downloading image for user, ${username}:`, error);
        });

    });

}

const getAllFileData = (filepath) => {
    //const gitDir = './komodo-docs-mdx'// path.join(__dirname, './komodo-docs-mdx')
    const getLastEditedTime = spawnSync("git", [
        "log",
        "-1",
        "--format=%ct",
        filepath,
    ]); //, { cwd: gitDir }

    const date = new Date(parseInt(getLastEditedTime.stdout.toString()) * 1000);

    const getContributors = spawnSync("git", [
        "log",
        '--format={"author": "%an", "email": "%ae"}',
        filepath,
    ]);

    let getLastContributor = spawnSync("git", [
        "log",
        "-n 1",
        '--format={"author": "%an", "email": "%ae"}',
        filepath,
    ]);
    if (
        date.toString() == "Invalid Date"
    ) {
        console.error(
            "Date is invalid:",
            date
        );
        throw new Error(
            "Date is invalid:",
            date
        );
    } else if (getLastEditedTime.error) {
        console.error(
            "An error occurred while executing the git command:",
            getLastEditedTime.error.message
        );
        throw new Error(
            `An error occurred while executing the git command: ${getLastEditedTime.error.message}`
        );
    } else if (getContributors.error) {
        console.error(
            "An error occurred while executing the git command:",
            getContributors.error.message
        );
        throw new Error(
            `An error occurred while executing the git command: ${getContributors.error.message}`
        );
    } else if (getLastContributor.error) {
        console.error(
            "An error occurred while executing the git command:",
            getLastContributor.error.message
        );
        throw new Error(
            `An error occurred while executing the git command: ${getLastContributor.error.message}`
        );
    } else {
        const contributorsList = getContributors.stdout
            .toString()
            .split("\n")
            .filter((el) => {
                return el !== "";
            });

        const updatedContributors = contributorsList.map((contributor) => {
            const parsedContributor = JSON.parse(contributor);
            return parsedContributor;
        });

        const contributorsArray = updatedContributors.filter((item, index) => {
            return index === updatedContributors.findIndex(obj => {
                return JSON.stringify(obj) === JSON.stringify(item);
            });
        });

        getLastContributor = JSON.parse(
            getLastContributor.stdout.toString().replace("\n", "")
        );

        fileData[filePathToRoute(filepath)] = {};
        fileData[filePathToRoute(filepath)]["dateModified"] = date.toISOString();
        fileData[filePathToRoute(filepath)]["contributors"] = contributorsArray;

        fileData[filePathToRoute(filepath)]["lastContributor"] =
            getLastContributor;
    }
};

function filePathToRoute(filePath) {
    // Convert Windows-style path separators to Unix-style
    // const normalizedPath = filePath.replace(/\\/g, "/");

    const route = filePath
        .replace(/(\/index)?\.[^.]+$/, "") // Remove the file extension and "index" suffix if present
        .replace(/^.*\/pages\/?/, ""); // Remove the "pages" directory prefix and add a leading slash
    return "/" + route;
}
