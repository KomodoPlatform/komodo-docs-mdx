import * as fs from "fs";
import * as path from "path";

import axios from "axios";

const versionsFromJson = JSON.parse(fs.readFileSync("./utils/_changeLogVersions.json", 'utf8'));

const komodoLatestReleaseURL = "https://api.github.com/repos/komodoplatform/komodo/releases/latest"

const komodoDefiFrameworkLatestReleaseURL = "https://api.github.com/repos/komodoplatform/komodo-defi-framework/releases/latest"

async function fetchLatestRelease() {
    try {
        const komodoResponse = await axios.get(komodoLatestReleaseURL);
        if(komodoResponse.data.tag_name === versionsFromJson['komodo']){
             console.log("komodo changelog is upto date"); 
        } else {
            throw new Error("update komodo changelog in the file: ./src/pages/smart-chains/changelog/index.mdx and the release version in ./utils/_changeLogVersions.json")
        }
      } catch (error) {
        console.error('Error when comparing the komodo latest release info:', error);
      }


  try {
    const defiResponse = await axios.get(komodoDefiFrameworkLatestReleaseURL);
    if(defiResponse.data.tag_name === versionsFromJson['komodo-defi-framework']){
      console.log("komodo-defi-framework changelog is upto date"); 
    } else {
      throw new Error("update komodo changelog in the file: ./src/pages/atomicdex/changelog/index.mdx and the release version in ./utils/_changeLogVersions.json")
    }
  } catch (error) {
    console.error('Error when comparing the komodo defi framework latest release:', error);
  }
}


(async function() {
 await fetchLatestRelease()
})()
