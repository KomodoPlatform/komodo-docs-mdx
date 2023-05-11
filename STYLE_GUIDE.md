# Style Guide


<p align="center">
 <a href="https://xkcd.com/">
  <img src="https://user-images.githubusercontent.com/35845239/236310324-01dfb2b4-eba4-4e47-bd1b-b66689056de8.png" />
 </a>
</p>

Great documentation is critical for guiding those who will use our tech stack. It should be clear, easy to read, and as detailed as required while avoiding unneccessary verbosity. This way, developers can quickly understand how to use and what to expect from our products.

From a user's perspective:
 - If they can't find information about a feature in the documentation, it means that **the feature doesn't exist**.
 - If there is information about a feature, but it's wrong or confusing, it means that **the feature is broken**.
 - If the documentation is hard to read, it means that **the feature is hard to use**.

Be mindful of any feedback you receive from users, and let it guide you to improve the documentation. The eyes of the uninitiated are the best tool for identifying areas in need of enhancement. Though existing documentation may not yet conform to this standard, all new documentation should be written in accordance with the guidelines below, and existing documentation updated to match when time permits.

**These guidelines are currently a work in progress.** Please also refer to https://alistapart.com/article/the-ten-essentials-for-good-api-documentation/ as a good foundation.


## Structure

 - Generally, individual API methods should be placed in their own `index.mdx` file, within a folder named after the method.
    - The `index.mdx` file should contain a heading with the method name, and a description of the method.
    - Each file should contain a code block with at least one example of how to make a complete request, including all required parameters.
    - Where a request includes optional parameters which will result in different response structures, the file should contain a code block for each possible request variation, followed by a code block for the response of each example.
    - Below the request/response examples, include code blocks for each potential error response, along with details on what causes the error and how it might be resolved.
 - In some cases, it may be appropriate to group related methods together in a single `index.mdx` file. For example, the `index.mdx` file within the `trezor_initialisation` folder contains documentation for all methods for initialisation and authentication with a Trezor hardware wallet.
 - Where common structures exist in the request or response of mulitple methods, these should be documented in the `index.mdx` file in the base folder for a section (e.g. [src/pages/atomicdex/api/v20/index.mdx](src/pages/atomicdex/api/v20/index.mdx)), and linked to from request/response parameter tables where required.
 - Where a method or parameter is deprecated, this should be clearly communicated in the method heading or request parameters table. 
  - Separate sections of content with subheadings to make it easier to scan and find the information they need. Two line breaks should be used before and one line break after each subheading.


## General

 - Use [American English spelling](https://www.thefreedictionary.com/American-English-vs-British-English-Spelling.htm)
 - Use the [Oxford comma](https://www.youtube.com/watch?v=xUt7-B8IfxU)
 - Use [Bluebook title case](https://titlecaseconverter.com/rules/#BB) for headings and products.
 - Use [sentence case](https://titlecaseconverter.com/sentence-case/) for menu items, tabs, buttons, links, all other text.
 - Use a 4 space indent in code blocks for the request body and response. This will make the parameters and values easier to read.
 - Use images or diagrams to help explain complex concepts or processes. This will make the content more engaging and easier to understand. 
 - If a user action requires a sequence of steps, consider using a flowchart to illustrate the process.
 - Keep it concise: Stay on point. Avoid unnecessary words or phrases that do not add value to the content.
 - Don't skimp on important detail: If a feature is complex, it's better to provide too much information than not enough. Where appropriate it may be better to split the additional information into its own page and add a link to it for those who want to dig deeper.
 - Use simple language: Where possible, avoid jargon or technical terms that may be unfamiliar to the reader. When unavoidable, provide a link to a definition or explanation of the term.
 - Proofread and test your content: Make sure to proofread your MDX file for errors and test any code snippets or examples to ensure they work as expected.
 - Be generous with hyperlinks: Link to relevant documentation or resources, whether to somewhere else within our internal docs or to a respected external source. This will provide additional context and help users better understand the content.
 - Use absolute links for internal docs: The `pages` folder is the root directory for internal docs. Use absolute links to reference other pages within the `pages` folder, for example: `[AtomicDEX API methods](/atomicdex/api)`.
 - Use bullet points and numbered lists to break up long paragraphs to make the content more readable.


## Syntax

 - Use `#` for page headings.
 - Use `##` for subheadings.
 - Use `###` for request/response parameter tables.
 - Use `####` for request/response examples.
 - Use mdx comments like this: `{/* comment comment */}` . Markdown comments like `<!--- comment comment--->` don't work.
 - No markdown/mdx comments in tables' rows



## Tables

 - Include a reference table listing all **request** parameters, their type, a description, and whether it is required or optional.
 - Include a reference table listing all **response** parameters, their type, a description, and whether it is part of the standard response or only returned when using a specific request parameter value.
 - Optional parameters should be identified at the start of the parameter's description, along with the default value (if applicable).
 - Optional parameters should be listed at the bottom of the parameter table


## Variables

 - For AtomicDEX-API methods, the userpass variable should always be `MM2_RPC_PASSWORD`

## Templates

Use the linked templates below as a starting point for new documentation pages.

 - [AtomicDEX API methods](templates/atomicdex_method.mdx)


## Components

#### CodeGroup

AtomicDEX methods should be wrapped with `CodeGroup` tags, using the method name as the label value, and the tag value set to POST.
Use the `json {{ mm2MethodDecorate : true }}` decoration to generate code blocks for
 - JSON: The pure request body.
 - Python3: Using the requests library.
 - Bash: Using curl.
 - Javascript: using fetch.
 - PHP: Using curl.
 - GO: Using net/http. (need to confirm this is correct)
 - Ruby: Using net/http. 


#### CollapsibleSection

Each response should be wrapped with `CollapsibleSection` tags, for example:

    <CollapsibleSection expandedText='Hide Response' collapsedText='Show Response'>
    #### Response (ready, successful)

    ```json
    {
       "mmrpc": "2.0",
       "result": "success",
       "id": null
    }
    ```
    </CollapsibleSection>

The `CollapsibleSection` tags should also wrap all error responses (as a group), with the `expandedText` and `collapsedText` values set to 'Show Error Responses' and 'Hide Error Responses' respectively.


#### Note

Use `Note` tags to highlight important information, for example:

```mdx
<Note>
These methods (and others with a `task::` prefix) will be linked to a numeric `task_id` value
which is usedto query the status or outcome of the task.
</Note>
```


#### OptimizedImage

Images should be added to the related subfolder within the `src/images` folder, and referenced using the `OptimizedImage` component. At the top of the file which will include the image, import the image using the following syntax:

`import trezorpin from "@/images/api-images/trezor_pin.png";`

Now you can reference the image using the `OptimizedImage` component, for example:

`<OptimizedImage src={trezorpin} classNaming="w-full" alt="Trezor Pin" />`
