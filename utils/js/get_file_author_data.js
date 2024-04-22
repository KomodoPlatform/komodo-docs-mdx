import fs from 'fs';
import https from 'https';
import path from 'path';
import { spawnSync } from 'child_process';
const authorsData = JSON.parse(fs.readFileSync("./authors.json", 'utf8'));
const oldFileData = JSON.parse(fs.readFileSync("./utils/_fileData_old_documentation_mod.json", 'utf8'));

const fileData = {};

(async function () {
    const allContributorsDataUrl = "https://api.github.com/repos/komodoplatform/komodo-docs-mdx/contributors"

    const options = {
        headers: {
            'User-Agent': 'komodo-docs-mdx-ci'
        }
    };

    try {
        const { response } = await httpsGet(allContributorsDataUrl, options)
        const contributorData = JSON.parse(response)
        for (const contributor of contributorData) {
            if (!authorsData[contributor.login]) {
                const { response } = await httpsGet(`https://api.github.com/repos/komodoplatform/komodo-docs-mdx/commits?author=${contributor.login}`, options)
                const contributorCommits = JSON.parse(response)
                console.log(contributorCommits)
                const commit_emails = new Set();
                contributorCommits.forEach(commit => {
                    if (commit.commit && commit.commit.author && commit.commit.author.email) {
                        commit_emails.add(commit.commit.author.email);
                    }
                });
                console.log(commit_emails)
                authorsData[contributor.login] = {
                    username: contributor.login,
                    commit_emails: Array.from(commit_emails),
                    socials: {
                        twitter: "",
                        linkedin: ""
                    }
                }
            }
            authorsData[contributor.login].id = contributor.id
            authorsData[contributor.login].avatar_url = contributor.avatar_url
        }
    } catch (error) {
        console.error(error);
    }

    for (const username in authorsData) {
        const imageUrl = authorsData[username].avatar_url
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

    const getCommitTimesInReverse = spawnSync("git", [
        "log",
        "--reverse",
        "--format=%ct",
        filepath,
    ]);

    if (getCommitTimesInReverse.error) {
        console.error(
            "An error occurred while executing the git command:",
            getCommitTimesInReverse.error.message
        );
        throw new Error(
            `An error occurred while executing the git command: ${getCommitTimesInReverse.error.message}`
        );
    }

    if (getLastEditedTime.error) {
        console.error(
            "An error occurred while executing the git command:",
            getLastEditedTime.error.message
        );
        throw new Error(
            `An error occurred while executing the git command: ${getLastEditedTime.error.message}`
        );
    }

    const firstCommitTime = getCommitTimesInReverse.stdout.toString().split("\n")[0]
    const firstCommitDate = new Date(parseInt(firstCommitTime) * 1000);

    if (
        firstCommitDate.toString() == "Invalid Date"
    ) {
        console.error(
            filepath + "firstCommitDate is invalid:",
            firstCommitDate
        );
        throw new Error(
            "firstCommitDate is invalid:",
            firstCommitDate
        );
    }

    const lastEditedDate = new Date(parseInt(getLastEditedTime.stdout.toString()) * 1000);

    if (
        lastEditedDate.toString() == "Invalid Date"
    ) {
        console.error(
            filepath + "lastEditedDate is invalid:",
            lastEditedDate
        );
        throw new Error(
            "lastEditedDate is invalid:",
            lastEditedDate
        );
    }

    let lastContributor = getLastContributor(filepath)
    let allContributors = getAllContributors(filepath)
    const fileRoute = filePathToRoute(filepath)
    fileData[fileRoute] = fileData[fileRoute] ? fileData[fileRoute] : {};
    fileData[fileRoute]["dateModified"] = lastEditedDate.toISOString();
    fileData[fileRoute]["contributors"] = allContributors;
    fileData[fileRoute]["dateCreated"] = firstCommitDate.toISOString();
    fileData[fileRoute]["lastContributor"] =
        lastContributor;

};

function filePathToRoute(filePath) {
    const route = filePath
        .replace(/(\/index)?\.[^.]+$/, "") // Remove the file extension and "index" suffix if present
        .replace(/^.*\/pages\/?/, ""); // Remove the "pages" directory prefix and add a leading slash
    return "/" + route;
}

function getLastContributor(filepath) {
    let nameCommand = spawnSync("git", [
        "log",
        "-n 1",
        '--format=%an',
        filepath,
    ]);
    if (nameCommand.error) {
        console.error(
            "An error occurred while executing the git command:",
            nameCommand.error.message
        );
        throw new Error(
            `An error occurred while executing the git command: ${nameCommand.error.message}`
        );
    }
    let emailCommand = spawnSync("git", [
        "log",
        "-n 1",
        '--format=%ae',
        filepath,
    ]);
    if (emailCommand.error) {
        console.error(
            "An error occurred while executing the git command:",
            emailCommand.error.message
        );
        throw new Error(
            `An error occurred while executing the git command: ${emailCommand.error.message}`
        );
    }
    let name = JSON.stringify(
        nameCommand.stdout.toString().replace("\n", "")
    );
    let email =
        emailCommand.stdout.toString().replace("\n", "")
    return { name, email }
}

function getAllContributors(filepath) {
    let nameCommand = spawnSync("git", [
        "log",
        '--format=%an',
        filepath,
    ]);
    if (nameCommand.error) {
        console.error(
            "An error occurred while executing the git command:",
            nameCommand.error.message
        );
        throw new Error(
            `An error occurred while executing the git command: ${nameCommand.error.message}`
        );
    }
    let emailCommand = spawnSync("git", [
        "log",
        '--format=%ae',
        filepath,
    ]);
    if (emailCommand.error) {
        console.error(
            "An error occurred while executing the git command:",
            emailCommand.error.message
        );
        throw new Error(
            `An error occurred while executing the git command: ${emailCommand.error.message}`
        );
    }
    let names =
        nameCommand.stdout.toString().split("\n").filter((el) => {
            return el !== "";
        }).map(name => JSON.stringify(name))

    let emails =
        emailCommand.stdout.toString().split("\n").filter((el) => {
            return el !== "";
        })
    if (names.length !== emails.length) {
        throw new Error("length of emails list and names list for allContributors isn't the same")
    }
    let contributorsArray = []
    for (let index = 0; index < names.length; index++) {
        let contributor = {
            name: names[index],
            email: emails[index]
        }
        contributorsArray.push(contributor)
    }
    let oldFileData_pathData = oldFileData[filepath.replace("/index.mdx", "").replace("src/pages", "")]
    let oldContributors = oldFileData_pathData ? oldFileData_pathData.contributors : []
    contributorsArray = [...contributorsArray, ...oldContributors]
    return contributorsArray.filter((item, index) => { //filter repeated entries
        return index === contributorsArray.findIndex(obj => {
            return JSON.stringify(obj) === JSON.stringify(item);
        });
    });
}