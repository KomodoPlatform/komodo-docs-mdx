# QA / Testing Guide



## Testing the docs locally
Please refer to the [deployment repo](https://github.com/gcharang/komodo-docs-revamp-2023#running-locally-to-preview-changes) for instructions on how to run the docs locally.


When testing a pull request, it is important to validate the content added to the docs. This includes:
- [ ] Spelling and grammar: check for typos, misspellings, and grammatical errors
- [ ] Code samples: Confirm that the generated code samples work as expected for all displayed languages (This will eventually be one via automated CI/CD). 
- [ ] Links: Confirm that all links work as expected. This includes links to other pages in the docs, links to external sites, and links to other repos. It is also helpful to suggest links to external pages which may offer a more detailed explanation of a topic, especially when it is highly technical in nature.
- [ ] Images: Confirm that all images are displaying correctly, and any text within an image is legible (when expanded).
- [ ] Sidebar & Navigation menus: Confirm any new pages are added to the appropriate sidebar and navigation menus, and displaying as expected.
- [ ] Search: Confirm that the new content is searchable, and that the search results are relevant to the content.
- [ ] Accessibility: Confirm that the new content is accessible to all users, including those using screen readers. This includes ensuring that all images have alt text, and that all code samples are formatted correctly.
- [ ] Content: Confirm that the content is accurate and relevant to the topic. If you have any suggestions for additional content, please add them as comments on the pull request. If the content does not make sense to you, it likely may also be confusing for the target audience. Please add comment to the pull request with your questions for clarification.


Whenever a new API method is added to the docs, those testing must:
- [ ] Download / launch the appropriate version of the API binary (this will normally be the latest buil from the `dev` branch)
- [ ] Test the API method to ensure it is working as expected. This includes testing all parameters and return values, as well as any error messages.
- [ ] If the API method is not working as expected, please add a comment to the pull request with details on the issue, and any suggestions for how to resolve it.
- [ ] Compare your responses to the responses in the docs. If there are any discrepancies, please add a comment to the pull request with details on the issue, and any suggestions for how to resolve it.
- [ ] If you encounter any error messages not yet documented, please add a comment to the pull request with the request / response json.
- [ ] If you encounter any responses to optional request parameter variations not yet documented, please add a comment to the pull request with the request / response json.
