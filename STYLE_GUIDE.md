# Style Guide

## Document Version

**Last Updated:** December 2024  
**Recent Changes:**
- Integrated API Documentation table standards (Request Arguments format)
- Added MDX example standards and best practices
- Consolidated multiple style documents into unified guide
- Updated KDF API Method Documentation Standard with table formatting requirements

---

Great documentation is critical for guiding those who will use our tech stack. It should be clear, easy to read, and as detailed as required while avoiding unnecessary verbosity.

From a user's perspective:
- If they can't find information about a feature in the documentation, it means that **the feature doesn't exist**.
- If there is information about a feature, but it's wrong or confusing, it means that **the feature is broken**.
- If the documentation is hard to read, it means that **the feature is hard to use**.

These guidelines are currently a work in progress. All new documentation should follow the guidelines below, and existing documentation should be updated to match when time permits.

## Structure

- Generally, individual API methods should be placed in their own `index.mdx` file, within a folder named after the method.
  - The `index.mdx` file should contain a heading with the method name and a description of the method.
  - Each file should contain a code block with at least one example of how to make a complete request, including all required parameters.
  - Where a request includes optional parameters which will result in different response structures, the file should contain a code block for each possible request variation, followed by a code block for the response of each example.
  - Below the request/response examples, include code blocks for each potential error response, along with details on what causes the error and how it might be resolved.
- In some cases, it may be appropriate to group related methods together in a single `index.mdx` file. For example, the `index.mdx` file within the `task_init_trezor` folder contains documentation for all methods for initialisation and authentication with a Trezor hardware wallet.
- Where common structures exist in the request or response of multiple methods, these should be documented in the `index.mdx` file in the base folder for a section (e.g. [src/pages/komodo-defi-framework/api/v20/index.mdx](src/pages/komodo-defi-framework/api/v20/index.mdx)), and linked to from request/response parameter tables where required.
- Where a method or parameter is deprecated, this should be communicated in the method heading or request parameters table.
- Separate sections of content with subheadings to make scanning and finding the information they need easier. Two line breaks should be used before and one line break after each subheading.

## General

- Use [American English spelling](https://www.thefreedictionary.com/American-English-vs-British-English-Spelling.htm)
- Use the [Oxford comma](https://www.youtube.com/watch?v=xUt7-B8IfxU)
- Use [Bluebook title case](https://titlecaseconverter.com/rules/#BB) for headings and products.
- Use [sentence case](https://titlecaseconverter.com/sentence-case/) for menu items, tabs, buttons, links, and all other text.
- Use a 4-space indent in code blocks for the request body and response. This will make the parameters and values easier to read.
- Use images or diagrams to help explain complex concepts or processes. This will make the content more engaging and easier to understand.
- If a user action requires a sequence of steps, consider using a flowchart to illustrate the process.
- Keep it concise: Stay on point. Avoid unnecessary words or phrases that do not add value to the content.
- Don't skimp on important detail: If a feature is complex, it's better to provide too much information than not enough. Where appropriate it may be better to split the additional information into its own page and add a link to it for those who want to dig deeper.
- Use simple language: Where possible, avoid jargon or technical terms that may be unfamiliar to the reader. When unavoidable, provide a link to a definition or explanation of the term.
- Proofread and test your content: Make sure to proofread your MDX file for errors and test any code snippets or examples to ensure they work as expected.
- Be generous with hyperlinks: Link to relevant documentation or resources, whether to somewhere else within our internal docs or to a respected external source. This will provide additional context and help users better understand the content.
- Use absolute links for internal docs: The `pages` folder is the root directory for internal docs. Use absolute links to reference other pages within the `pages` folder, for example: `[Komodo DeFi Framework API methods](/komodo-defi-framework/api/#sub-section-header)`. The url must end with a slash.
- Use bullet points and numbered lists to break up long paragraphs to make the content more readable.

## Syntax

- Use `#` for page headings.
- Use `##` for subheadings.
- Use `###` for request/response parameter tables.
- Use `####` for request/response examples.
- Use mdx comments like this: `{/* comment comment */}` . Markdown comments like `<!--- comment comment--->` doesn't work. Alternatively, you can use the `<DevComment>` component tags.
- No markdown/mdx comments in tables' rows

## Tables

### Request Parameter Tables

- Include a reference table listing all **request** parameters with the following 5 columns: Parameter, Type, Required, Default, Description
- Parameters should be listed alphabetically within their groupings (required parameters first, then optional parameters)
- The Required column should contain "✓" for required parameters and "✗" for optional parameters (centered alignment)
- The Default column should contain the default value for optional parameters, or "-" for required parameters or optional parameters without defaults (centered alignment)
- Where specific parameters only apply for a specific action, this should be identified at the start of the parameter's description
- Where a group of parameters are nested within a common structure, this should be given its own table, and linked to from the main parameter table

### Response Parameter Tables

- Include a reference table listing all **response** parameters with Parameter, Type, and Description columns
- Parameters should be listed alphabetically
- Where a group of parameters are nested within a common structure, this should be given its own table, and linked to from the main parameter table

### Common Structures

- Enums and common structures should be used or created wherever possible. Dot notation is to be avoided.
- Common structure objects should be listed alphabetically in the file which contains them. Links to all methods which use the structure should be listed under its table.

### Request Parameter Table Example:

| Parameter | Type    | Required | Default | Description                                                                                   |
| --------- | ------- | :------: | :-----: | --------------------------------------------------------------------------------------------- |
| coin      | string  | ✓        | -       | The name of the coin the user desires to activate.                                            |
| amount    | float   | ✗*       | -       | The amount of balance to send. Required unless `max` is `true`.                               |
| fee       | object  | ✗        | -       | A standard [FeeInfo](/komodo-defi-framework/api/common_structures/#FeeInfo) object.           |
| max       | boolean | ✗        | `false` | Send whole balance.                                                                           |
| memo      | string  | ✗        | -       | Used for ZHTLC and Tendermint coins only. Attaches a memo to the transaction.                |

## Variables

- For Komodo DeFi Framework API methods, the userpass variable should always be `RPC_UserP@SSW0RD`

## Templates

Use the linked templates below as a starting point for new documentation pages.

- [Komodo DeFi Framework API methods](templates/komodefi_method.mdx)

## How to contribute

Read the [Contribution guide](CONTRIBUTION_GUIDE.md) first.

Pages are heavily [**MDX**](https://mdxjs.com/) ("markdown extension") based, which allows us to use JSX in markdown content. You can have imported components (JSX) within your content and more. Read more about MDX here [https://mdxjs.com/docs/what-is-mdx/](https://mdxjs.com/docs/what-is-mdx/).

## Components

### Note

The `Note` component displays an info/warning/error styled message with predefined icons and colors:

```mdx
<Note type="info">
  Information message here.
</Note>

<Note type="warning">
  Warning message here.
</Note>

<Note type="error">
  Error message here.
</Note>
```

### CollapsibleSection

This renders a button with a specified text based on its state (expanded or collapsed). You'll mostly use this for API responses:

````mdx
<CollapsibleSection expandedText='Hide Response' collapsedText='Show Response'>

```json
{
   "mmrpc": "2.0",
   "result": "success",
   "id": null
}
```

</CollapsibleSection>
````

### Images

Images should be added to the related subfolder within the `src/images` folder, and rendered using the `OptimizedImage` component:

```jsx
import komodefiManiq from "@/public/images/docs/komodefi-maniq.webp";

<OptimizedImage title="Komodo DeFi Framework" src={komodefiManiq} alt="Komodo DeFi Framework" classNaming="w-full" />
```

### Heading

The `Heading` component functions like native heading tags but can be labelled and tagged:

```mdx
## How to get your tokens {{label : 'get_all_tokens', tag : 'API-v2'}}
```

### Tag

`Tag`s are used for tagging CRUD operations:

```mdx
<Tag>post</Tag>
<Tag>get</Tag>
<Tag>put</Tag>
<Tag>delete</Tag>
```

## Navigation

- **Top navbar**: Navigation data is in [src/data/navbar.json](src/data/navbar.json)
- **Left sidebar**: Navigation data is in [src/data/sidebar.json](src/data/sidebar.json). New pages should be added here.
- **Right sidebar**: Automatically populated based on the heading hierarchy of the current page.
