#!/usr/bin/env python3

import json

def extract_methods_from_item(item, methods_set):
    """
    Recursively extracts 'method' names from Postman collection items.
    """
    if isinstance(item, dict):
        # Check if the item has a 'request' object
        if "request" in item and isinstance(item["request"], dict):
            request_obj = item["request"]
            # Check for 'body' and its 'raw' content
            if "body" in request_obj and isinstance(request_obj["body"], dict) and \
               request_obj["body"].get("mode") == "raw" and "raw" in request_obj["body"]:
                try:
                    # The raw body is expected to be a JSON string
                    raw_body_content = request_obj["body"]["raw"]
                    # Remove potential JavaScript comments from the JSON string
                    # This is a simplified comment removal, might need adjustment for complex cases
                    import re
                    raw_body_content_no_comments = re.sub(r'//.*?\n|/\*.*?\*/', '', raw_body_content, flags=re.S)
                    
                    body_json = json.loads(raw_body_content_no_comments)
                    if isinstance(body_json, dict) and "method" in body_json:
                        methods_set.add(body_json["method"])
                except json.JSONDecodeError:
                    # Handle cases where raw body is not valid JSON or doesn't have "method"
                    # print(f"Warning: Could not parse JSON from raw body: {request_obj['body']['raw'][:100]}...")
                    pass
                except Exception as e:
                    # print(f"Warning: An error occurred while processing a request body: {e}")
                    pass

        # If the item contains sub-items, recurse
        if "item" in item and isinstance(item["item"], list):
            for sub_item in item["item"]:
                extract_methods_from_item(sub_item, methods_set)

    elif isinstance(item, list):
        # If the current object is a list of items, iterate and recurse
        for sub_item in item:
            extract_methods_from_item(sub_item, methods_set)

def main():
    file_path = "./collections/komodo_defi.postman_collection.json"  # Path to the Postman collection file
    postman_methods = set()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            collection_data = json.load(f)
        
        # The top-level 'item' array contains the folders and requests
        if "item" in collection_data and isinstance(collection_data["item"], list):
            extract_methods_from_item(collection_data["item"], postman_methods)
        
        if postman_methods:
            print("Successfully extracted RPC methods from Postman collection:")
            for method in sorted(list(postman_methods)):
                print(method)
        else:
            print("No methods found. Check the collection structure or script logic.")

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{file_path}'. The file might be corrupted or not in valid JSON format.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
