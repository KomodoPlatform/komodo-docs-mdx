import * as fs from "fs";
import * as path from "path";

import axios from "axios";

const versionsFromJson = JSON.parse(fs.readFileSync("./utils/_changeLogVersions.json", 'utf8'));

const komodoLatestReleaseURL = "https://api.github.com/repos/komodoplatform/komodo/releases/latest"

const komodoDefiFrameworkLatestReleaseURL = "https://api.github.com/repos/komodoplatform/komodo-defi-framework/releases/latest"

async function fetchLatestRelease() {
    try {
        const response = await axios.get(komodoLatestReleaseURL);
        if(response.data.tag_name === versionsFromJson['komodo']){
            console.info('Both versions are same');
            // console.log(response.data.tag_name); // Process the response data as needed
        } else {
            console.error('update the latest version in changelog')
        }
      } catch (error) {
        console.error('Error fetching the komodo latest release:', error);
      }


  try {
    const response = await axios.get(komodoDefiFrameworkLatestReleaseURL);
    if(response.data.tag_name === versionsFromJson['komodo-defi-framework']){
    console.info('Both versions are same');
    //console.log(response.data.tag_name); // Process the response data as needed
    } else {
        console.error('update the latest version in changelog')
    }
  } catch (error) {
    console.error('Error fetching the komodo defi framework latest release:', error);
  }
}

fetchLatestRelease()