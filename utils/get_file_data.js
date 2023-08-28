const https = require('https');
const fs = require('fs');
const authorsData = JSON.parse(fs.readFileSync("./authors.json", 'utf8'))

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
                resolve(true)
            });
        }).on('error', (error) => {
            fs.unlink(filename);
            reject(`Error downloading image for user, ${username}:`, error);
        });

    });

}

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
        fs.writeFileSync("authors.json", JSON.stringify(authorsData, null, 4))
    } catch (error) {
        console.error(error);
    }

    for (const username in authorsData) {
        const imageUrl = authorsData[username].avatar_url

        // const { response: imgResponse, headers: respHeaders } = await httpsGet(imageUrl, options)

        // const fileExt = respHeaders["content-type"].split("/")[1]
        // const imgFilename = `./src/images/authors/${username}.${fileExt}`
        // fs.writeFileSync(imgFilename, imgResponse)
        await downloadImage(imageUrl, username)
    }
})()

