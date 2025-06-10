# Style Guide

## Document Version

**Last Updated:** December 2024  
**Recent Changes:**
- Integrated API Documentation table standards (Request Arguments format)
- Added MDX example standards and best practices
- Consolidated multiple style documents into unified guide
- Updated KDF API Method Documentation Standard with table formatting requirements

---


# MDX File Requirements

- All MDX files, especially `index.mdx` files, must begin with `export const title = ...` and `export const description = ...` at the very top of the file. These are required for build and navigation. Never remove these fields.
- All anchor links and section slugs (e.g., for enums) must use kebab-case (lowercase, hyphen-separated).
- All enum section headings must use Bluebook title case, no spaces, and end with 'Enum' (e.g., EthPrivKeyActivationPolicyEnum). Anchor links must match this format.

Great documentation is critical for guiding those who will use our tech stack. It should be clear, easy to read, and as detailed as required while avoiding unnecessary verbosity.

From a user's perspective:
- If they can't find information about a feature in the documentation, it means that **the feature doesn't exist**.
- If there is information about a feature, but it's wrong or confusing, it means that **the feature is broken**.
- If the documentation is hard to read, it means that **the feature is hard to use**.

These guidelines are currently a work in progress. All new documentation should follow the guidelines below, and existing documentation should be updated to match when time permits.

## Structure

- Generally, individual API methods should be placed in their own `index.mdx` file, within a folder named after the method.
  - The `index.mdx` file should contain a heading with the method name and a description of the method.
  - After the main heading (`#`), include a method subheading (`##`) with the actual method name.
  - Each file should contain a code block with at least one example of how to make a complete request, including all required parameters.
  - Where a request includes optional parameters which will result in different response structures, the file should contain a code block for each possible request variation, followed by a code block for the response of each example.
  - Below the request/response examples, include code blocks for each potential error response, along with details on what causes the error and how it might be resolved.
  - Each request should be in a CodeGroup. Its response should be in a CollapsibleSection. There should only be one response per Collapsible section, but there may be multiple responses to a request. 
  - CollapsibleSection text should match the CodeGroup title for consistency (e.g., if CodeGroup title is "Method Name", CollapsibleSection should be "Hide/Show Method Name Response").
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

- Use `#` for page headings. These MUST match the text in `const title = ` at the top of the page. For KDF Methods, it should follow the format `Komodo DeFi Framework Method: stream::orderbook::enable`.
- Use `##` for subheadings. These are generally method names. This line should also include label/tag like `{{label : 'method_name', tag : 'API-v2'}}`.
- **IMPORTANT**: Method headings MUST use the complete API method name exactly as it appears in the request (e.g., `stream::orderbook::enable` not just `orderbook_enable`).
- Use `###` for request/response parameter table titles.
- Use `####` for request/response examples (like #### 📌 Examples and #### ⚠️ Error Responses)

- Use mdx comments like this: `{/* comment comment */}` . Markdown comments like `<!--- comment comment--->` doesn't work. Alternatively, you can use the `<DevComment>` component tags.
- No markdown/mdx comments in tables' rows

## Tables

### Request Parameter Tables

- Include a reference table listing all **request** parameters with the following 5 columns: Parameter, Type, Required, Default, Description
- **IMPORTANT**: If there are no optional parameters (all parameters are required), you can use a 4-column format: Parameter, Type, Required, Description (omitting the Default column)
- Parameters should be listed alphabetically within their groupings (required parameters first, then optional parameters)
- The Required column should contain "✓" for required parameters and "✗" for optional parameters (centered alignment)
- The Default column should contain the default value for optional parameters, or "-" for required parameters or optional parameters without defaults (centered alignment). All default values in parameter tables must be wrapped in backticks (e.g., `10`, `false`).
- If no default values are defined for any parameter, omit the Default column entirely. If any parameter has a default value, the Default column must be present and all default values must be wrapped in backticks (e.g., `10`, `false`).
- Where specific parameters only apply for a specific action, this should be identified at the start of the parameter's description
- Where a group of parameters are nested within a common structure, this should be given its own table, and linked to from the main parameter table
- Optional boolean parameters must always have a default value specified in the request parameter table, and it must be wrapped in backticks (e.g., `false`).

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

```mdx
<CollapsibleSection expandedText='Hide Response' collapsedText='Show Response'>

```json
{
   "mmrpc": "2.0",
   "result": "success",
   "id": null
}
```

</CollapsibleSection>

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

The `Tag` component is primarily used to display API versioning and deprecation status in documentation. Tags help users quickly identify the version of an API method or if a method is deprecated. You may also use tags for CRUD operations or to highlight statuses in tables and documentation.

**API versioning and deprecation examples:**

```mdx
<Tag type="api-version">API-v2</Tag>
<Tag type="deprecated">Deprecated</Tag>
```

## New Rule: Use of Common Objects and Enums

- Look for opportunities to use or create common objects and enums.
- Use enums for parameters or response values that have a fixed set of possible values (e.g., network, contract_type, status, etc.).
- Reference or define these enums in parameter/response tables and documentation where appropriate.

## Sidebar and Method Heading Naming Rules

- In `sidebar.json`, the `title` value for each method link must be the **exact API method name** (e.g., `lightning::payments::send_payment`), not a humanized or prettified version. The only exception is when the link does not point to a method (e.g., overview or non-method pages).
- The same rule applies to the `## MethodName` heading in each method MDX file: it must match the exact API method name.
- This is a strict requirement for all new and existing documentation.

## Overview Page Heading Hierarchy

- Use `#` for the page title (matches `export const title = ...`).
- Use `##` for the main group or overview section (e.g., `## Withdraw Tasks`).
- Use `###` for each sub-method or sub-section under that group (e.g., `### Task Withdraw Init`).
- This ensures a clear, consistent hierarchy and improves navigation and anchor generation.

**Example Structure:**

```mdx
# Komodo DeFi Framework Method: task::withdraw

## Withdraw Tasks

Overview of all withdraw task-managed methods. See below for details and cross-links to related wallet and transaction documentation.

### Task Withdraw Init
See [task::withdraw::init](/komodo-defi-framework/api/v20/wallet/task_managed/withdraw/init/) for preparing a withdrawal transaction.

### Task Withdraw Status
See [task::withdraw::status](/komodo-defi-framework/api/v20/wallet/task_managed/withdraw/status/) for checking the status of a withdrawal transaction.

### Task Withdraw User Action
See [task::withdraw::user_action](/komodo-defi-framework/api/v20/wallet/task_managed/withdraw/user_action/) for providing user action (e.g., Trezor PIN) during withdrawal.

### Task Withdraw Cancel
See [task::withdraw::cancel](/komodo-defi-framework/api/v20/wallet/task_managed/withdraw/cancel/) for cancelling a withdrawal transaction preparation.
```