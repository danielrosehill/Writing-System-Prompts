#!/usr/bin/env python3
import os
import re
import json
from pathlib import Path
from datetime import datetime

# Constants
README_PATH = "README.md"
INDEX_START_MARKER = "<!-- START_SYSTEM_PROMPT_INDEX -->"
INDEX_END_MARKER = "<!-- END_SYSTEM_PROMPT_INDEX -->"
METADATA_FILE = ".prompt_index_metadata.json"

def format_category_name(category_path):
    """Convert category path to human-readable format."""
    # Split path into components
    components = category_path.split(os.sep)
    
    # Convert each component from kebab/snake case to title case
    formatted_components = []
    for component in components:
        # Replace hyphens and underscores with spaces
        component = component.replace('-', ' ').replace('_', ' ')
        # Title case
        component = ' '.join(word.capitalize() for word in component.split())
        formatted_components.append(component)
    
    # Join components with slashes for nested categories
    return ' / '.join(formatted_components)

def extract_markdown_info(file_path):
    """Extract title and description from markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract title from first header
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else os.path.basename(file_path).replace('.md', '')
        
        # Extract description using multiple patterns
        description = ""
        
        # Pattern 1: Standard "## Description" section
        desc_match = re.search(r'^##\s+Description\s*\n\s*(.+?)(?:\n\n|\n##|$)', content, re.MULTILINE | re.DOTALL)
        if desc_match:
            description = desc_match.group(1).strip()
        
        # Pattern 2: Text immediately after the title (blockquote)
        if not description:
            desc_match = re.search(r'^#\s+.+\n\s*>\s*(.+?)(?:\n\n|\n##|$)', content, re.MULTILINE | re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip()
        
        # Pattern 3: Any paragraph after the title
        if not description:
            desc_match = re.search(r'^#\s+.+\n\n(.+?)(?:\n\n|\n##|$)', content, re.MULTILINE | re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip()
        
        # Pattern 4: Any text between title and next heading
        if not description:
            desc_match = re.search(r'^#\s+.+\n(.*?)(?:\n##|$)', content, re.MULTILINE | re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip()
        
        # Pattern 5: First paragraph of the system prompt section
        if not description:
            system_prompt_match = re.search(r'##\s+System\s+Prompt\s*\n\s*```\s*\n(.+?)(?:\n\n|\n```|$)', content, re.MULTILINE | re.DOTALL)
            if system_prompt_match:
                first_para = system_prompt_match.group(1).strip().split('\n\n')[0]
                description = first_para.strip()
        
        # Clean up description
        if description:
            # Remove markdown formatting
            description = re.sub(r'[*_`#>]', '', description)
            # Replace newlines with spaces
            description = re.sub(r'\n+', ' ', description)
            # Remove multiple spaces
            description = re.sub(r'\s+', ' ', description)
            
            # Truncate if too long
            if len(description) > 200:
                description = description[:197] + "..."
        
        return title, description
    except Exception as e:
        print(f"Error extracting info from {file_path}: {e}")
        return os.path.basename(file_path).replace('.md', ''), ""

def find_markdown_files(base_dir):
    """Find all markdown files in the repository."""
    markdown_files = []
    
    for root, _, files in os.walk(base_dir):
        # Skip hidden directories and files
        if any(part.startswith('.') for part in root.split(os.sep)):
            continue
            
        for file in files:
            if file.endswith('.md') and not file == README_PATH:
                full_path = os.path.join(root, file)
                markdown_files.append(full_path)
    
    return markdown_files

def load_metadata():
    """Load metadata from previous runs."""
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    return {"last_updated": "", "processed_files": {}}

def save_metadata(metadata):
    """Save metadata for future runs."""
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

def file_needs_processing(file_path, processed_files):
    """Check if a file needs to be processed based on modification time."""
    file_stat = os.stat(file_path)
    file_mtime = file_stat.st_mtime
    
    if file_path in processed_files:
        last_processed = processed_files[file_path]
        return file_mtime > last_processed
    
    return True

def generate_index(base_dir):
    """Generate an alphabetical index of all system prompts."""
    metadata = load_metadata()
    
    # Ensure the metadata has the right structure
    if "processed_files" not in metadata:
        metadata["processed_files"] = {}
    
    markdown_files = find_markdown_files(base_dir)
    
    # Collect information about all prompts
    prompts = []
    for file_path in markdown_files:
        try:
            title, description = extract_markdown_info(file_path)
            
            # Get category (parent folder name)
            rel_path = os.path.relpath(file_path, base_dir)
            category = os.path.dirname(rel_path)
            category_display = format_category_name(category) if category else "Uncategorized"
            
            prompts.append({
                "title": title,
                "description": description,
                "category": category_display,
                "path": rel_path,
                "file_path": file_path
            })
            
            # Update metadata
            metadata["processed_files"][file_path] = os.stat(file_path).st_mtime
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Sort prompts alphabetically by title
    prompts.sort(key=lambda x: x["title"].lower())
    
    # Generate markdown
    index_md = f"{INDEX_START_MARKER}\n\n"
    index_md += "# System Prompts Index\n\n"
    index_md += "_Last updated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "_\n\n"
    
    # Create alphabetical index
    index_md += "## Alphabetical Index\n\n"
    index_md += "| Title | Category | Description |\n"
    index_md += "|-------|----------|-------------|\n"
    
    for prompt in prompts:
        title_md = f"[{prompt['title']}]({prompt['path']})"
        index_md += f"| {title_md} | {prompt['category']} | {prompt['description']} |\n"
    
    index_md += f"\n{INDEX_END_MARKER}"
    
    # Update metadata
    metadata["last_updated"] = datetime.now().isoformat()
    save_metadata(metadata)
    
    return index_md

def update_readme(index_content):
    """Update the README.md file with the new index content."""
    if not os.path.exists(README_PATH):
        # Create a new README if it doesn't exist
        with open(README_PATH, 'w', encoding='utf-8') as f:
            f.write(f"# Writing System Prompts\n\nA collection of system prompts for various writing tasks.\n\n{index_content}\n")
        return
    
    with open(README_PATH, 'r', encoding='utf-8') as f:
        readme_content = f.read()
    
    # Check if markers exist
    if INDEX_START_MARKER not in readme_content:
        # Append to the end if markers don't exist
        readme_content += f"\n\n{index_content}\n"
    else:
        # Replace content between markers
        pattern = f"({re.escape(INDEX_START_MARKER)}).*?({re.escape(INDEX_END_MARKER)})"
        readme_content = re.sub(pattern, index_content, readme_content, flags=re.DOTALL)
    
    with open(README_PATH, 'w', encoding='utf-8') as f:
        f.write(readme_content)

def main():
    """Main function to generate the index and update README."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("Generating system prompts index...")
    index_content = generate_index(base_dir)
    
    print("Updating README.md...")
    update_readme(index_content)
    
    print("Done!")

if __name__ == "__main__":
    main()