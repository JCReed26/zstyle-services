#!/usr/bin/env python3
"""Fix openmemory-py package bug: BaseMessage not defined in except ImportError block."""
import os
import site

def main():
    # Find openmemory package
    for site_pkg in site.getsitepackages():
        langchain_file = os.path.join(site_pkg, 'openmemory', 'connectors', 'langchain.py')
        if os.path.exists(langchain_file):
            break
    else:
        print("Warning: openmemory package not found, skipping patch")
        return 0
    
    # Read file
    with open(langchain_file, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if 'BaseMessage = object' in content:
        print("openmemory already patched, skipping")
        return 0
    
    # Replace the except block
    old_block = """except ImportError:
    # Optional dependencies
    BaseChatMessageHistory = object
    BaseRetriever = object"""
    
    new_block = """except ImportError:
    # Optional dependencies
    BaseChatMessageHistory = object
    BaseRetriever = object
    BaseMessage = object
    HumanMessage = object
    AIMessage = object
    Document = object
    CallbackManagerForRetrieverRun = object"""
    
    if old_block in content:
        content = content.replace(old_block, new_block)
        with open(langchain_file, 'w') as f:
            f.write(content)
        print("Successfully patched openmemory package")
        return 0
    else:
        print(f"Warning: Could not find expected pattern in {langchain_file}")
        return 0

if __name__ == '__main__':
    exit(main())

