# Komodo Developer Docs Content

Content for the Komodo Developer Docs lives in this repo in `.mdx` format. This repository is then used as a submodule to build and deploy the Komodo Developer Docs website.


## Adding new content

- Read the [Style guide](STYLE_GUIDE.md) to learn the basic standards of writing Komodo Documentation content. This guide also contains a list of components and how they should be used.
- Read the [Contribution guide](CONTRIBUTION_GUIDE.md) for details about submitting a pull request.
- Make sure each new page created is added to the [sidebar file](https://github.com/KomodoPlatform/komodo-docs-mdx/blob/main/src/data/sidebar.ts)
- Be mindful of the [Code of Conduct](CODE_OF_CONDUCT.md) when contributing to this repository. We value all contributors and believe that our community is stronger when everyone feels safe, respected, and valued.


## Running locally to preview changes

This repository is used as a submodule in [https://github.com/gcharang/komodo-docs-revamp-2023/](https://github.com/gcharang/komodo-docs-revamp-2023/). To preview changes locally, follow the steps below: 

 Clone [https://github.com/gcharang/komodo-docs-revamp-2023/](https://github.com/gcharang/komodo-docs-revamp-2023/) and create a new branch with the same name as the branch you are working on in this repository.
 ```
 git clone https://github.com/gcharang/komodo-docs-revamp-2023/
 cd komodo-docs-revamp-2023
 git checkout -b <your-branch-name>
 ```
 Update the submodule to point to your branch
 ```
 cd utils
 ./update_mdx_branch.sh <your-branch-name>
 ```
 Update the content files in this repository
 ```
 cd ..
 ./update_content.sh
 ```
 Run the website locally
 ```
 # Install dependencies
 yarn
 # Launch website on localhost
 yarn dev
 ```

Now you can open [http://localhost:3000](http://localhost:3000) in your browser to see how your changes will look on the website.