#!/usr/bin/env python3
"""
Script to organize writing system prompts into subfolders using Ollama and Llama 3.2.
The script also converts filenames to kebab-case format.
"""

import os
import re
import json
import subprocess
import shutil
from pathlib import Path

# Repository base path
REPO_PATH = Path('/home/daniel/Development/git-repositories/My-Repos/Loose/Writing-System-Prompts')
PROMPTS_DIR = REPO_PATH / 'writing-tools'
FOLDER_LIST_FILE = REPO_PATH / 'folderlist.txt'

def to_kebab_case(filename):
    """Convert a filename to kebab-case format."""
    # Remove file extension
    name, ext = os.path.splitext(filename)
    
    # Replace special characters with spaces
    name = re.sub(r'[_&\(\)]', ' ', name)
    
    # Replace multiple spaces with a single space
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Convert to kebab-case
    kebab = name.lower().replace(' ', '-')
    
    # Return with original extension
    return f"{kebab}{ext}"

def read_folder_list():
    """Read the folder list from folderlist.txt."""
    with open(FOLDER_LIST_FILE, 'r') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def create_folders(folders):
    """Create the necessary subfolders if they don't exist."""
    for folder in folders:
        folder_path = REPO_PATH / folder
        if not folder_path.exists():
            folder_path.mkdir(parents=True)
            print(f"Created folder: {folder}")

def get_file_content(file_path):
    """Read the content of a markdown file."""
    with open(file_path, 'r') as f:
        return f.read()

def categorize_file(file_path, folders):
    """Use Ollama with Llama 3.2 to categorize a file into one of the folders."""
    content = get_file_content(file_path)
    filename = file_path.name
    
    prompt = f"""
You are a file categorization assistant. Your task is to categorize a system prompt file into the most relevant folder.

Here's the content of the file '{filename}':

{content}

Based on the content, please categorize this file into ONE of the following folders:
{', '.join(folders)}

Respond with ONLY the folder name, nothing else.
"""
    
    try:
        # Call Ollama with Llama 3.2
        result = subprocess.run(
            ["ollama", "run", "llama3.2", prompt],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Extract the folder name from the result
        output = result.stdout.strip()
        
        # Find the best matching folder from the output
        best_match = None
        for folder in folders:
            if folder.lower() in output.lower():
                best_match = folder
                break
        
        # If no match found, use a fallback approach
        if not best_match:
            # Try to find the closest match
            for folder in folders:
                folder_words = folder.replace('_', ' ').lower().split()
                for word in folder_words:
                    if word in output.lower():
                        best_match = folder
                        break
                if best_match:
                    break
        
        # If still no match, use a default folder
        if not best_match:
            best_match = "documentation"  # Default folder
            
        return best_match
        
    except subprocess.CalledProcessError as e:
        print(f"Error calling Ollama: {e}")
        print(f"Stderr: {e.stderr}")
        return "documentation"  # Default folder in case of error

def move_file(file_path, target_folder, kebab_case=True):
    """Move a file to the target folder with optional kebab-case conversion."""
    filename = file_path.name
    
    if kebab_case:
        new_filename = to_kebab_case(filename)
    else:
        new_filename = filename
    
    target_path = REPO_PATH / target_folder / new_filename
    
    # Create parent directory if it doesn't exist
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Move the file
    shutil.move(str(file_path), str(target_path))
    
    return new_filename

def main():
    """Main function to organize the prompts."""
    print("Starting organization of writing system prompts...")
    
    # Check if Ollama is installed
    try:
        subprocess.run(["ollama", "list"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Ollama is not installed or not working properly.")
        print("Please install Ollama from https://ollama.com/")
        return
    
    # Check if Llama 3.2 model is available
    try:
        models = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        if "llama3.2" not in models.stdout:
            print("Llama 3.2 model not found. Pulling it now...")
            subprocess.run(["ollama", "pull", "llama3.2"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error checking or pulling Llama 3.2 model: {e}")
        return
    
    # Read folder list
    folders = read_folder_list()
    if not folders:
        print("Error: No folders found in folderlist.txt")
        return
    
    # Create folders
    create_folders(folders)
    
    # Get all markdown files in the writing-tools directory
    md_files = list(PROMPTS_DIR.glob('*.md'))
    total_files = len(md_files)
    
    print(f"Found {total_files} markdown files to organize.")
    
    # Process each file
    for i, file_path in enumerate(md_files, 1):
        print(f"[{i}/{total_files}] Processing: {file_path.name}")
        
        # Categorize the file
        target_folder = categorize_file(file_path, folders)
        
        # Move the file with kebab-case conversion
        new_filename = move_file(file_path, target_folder)
        
        print(f"  → Moved to {target_folder}/{new_filename}")
    
    print("\nOrganization complete!")
    print(f"All files have been moved to their respective folders and converted to kebab-case.")

if __name__ == "__main__":
    main()
