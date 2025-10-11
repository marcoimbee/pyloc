import argparse
import time
import os
import glob
import re
import json
from pathlib import Path


def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Simple line of code counter for coding projects')
    parser.add_argument('path', help='Path to the target directory')
    parser.add_argument('-e', '--extensions', nargs='+', default=[], help='File extensions to include')
    parser.add_argument('-g', '--use_gitignore', default=False, action='store_true',
                        help='Exclude from the count files that are included in the .gitignore file of the directory')
    parser.add_argument('-i', '--insights', default=False, action='store_true', help='Show insights')
    return parser

def count_locs(target_file: str, comment_signs: list[str] | None, multi_line_comment_signs: dict | None) -> int | None:
    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[PYLOC] Error reading {target_file}: {e}")
        return None

    # Remove multi-line comment blocks
    if multi_line_comment_signs is not None:
        start_mark = multi_line_comment_signs.get('start', '')      # Like /* for cpp
        end_mark = multi_line_comment_signs.get('end', '')          # Like */ for cpp

        if start_mark and end_mark:
            lines_multi_comment_mark = []       # Will contains couples of [start, end] of all the multi comment blocks
            inside_comment_block = False
            start_block_idx = None

            for i, line in enumerate(lines):            # Scan lines of the target file
                if not inside_comment_block and start_mark in line:      # Found a comment block start mark
                    start_block_idx = i         # Save idx of line
                    inside_comment_block = True
                elif inside_comment_block and end_mark in line:  # Found a comment block end mark
                    lines_multi_comment_mark.append([start_block_idx, i])   # Save end of comment block
                    inside_comment_block = False
                    start_block_idx = None

            for start, end in lines_multi_comment_mark:
                for i in range(start, end + 1):         # None-ifying the lines that are part of a multi line comment block
                    lines[i] = None

            # Finally remove block comments lines + handle also inline comment blocks (e.g., x = 1; /* init x */ b = x + 1;)
            cleaned_lines = []
            for line in lines:
                if line is None:
                    continue
                cleaned_line = re.sub(rf'{re.escape(start_mark)}.*?{re.escape(end_mark)}', '', line)
                cleaned_lines.append(cleaned_line)
            lines = cleaned_lines            

    # Normalize single line comment marks
    if isinstance(comment_signs, str):
        comment_signs = [comment_signs]
    elif comment_signs is None:
        comment_signs = []

    # Remove blank lines and single-line comments
    if len(comment_signs) > 0:
        lines = [
            line for line in lines
            if line.strip() and not any(line.strip().startswith(sign) for sign in comment_signs)
        ]
    else:
        lines = [line for line in lines if line.strip()]

    return len(lines)

def get_files_list(dir: str) -> set[str]:
    base = Path(dir)
    return set(str(p.relative_to(base)) for p in base.rglob('*') if p.is_file())

def parse_gitignore(path: str) -> set[str]:
    gitignore = Path(path)
    base_dir = gitignore.parent

    with gitignore.open("r", encoding="utf-8") as f:
        patterns = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]

    gitignore_files = set()

    for pattern in patterns:
        if pattern.endswith('/'):
            pattern += '**'

        full_pattern = str(base_dir / pattern)

        for match in glob.glob(full_pattern, recursive=True):
            p = Path(match)
            if p.is_file():
                relative_path = os.path.normpath(str(p.relative_to(base_dir)))
                gitignore_files.add(relative_path)

    return gitignore_files

def format_print(
        show_insights: bool, 
        locs: int, 
        time_val: float, 
        locs_per_ext_hmap: dict, 
        longest_file_per_ext_hmap: dict, 
        tot_files: int
    ) -> None:
    print('----- [PYLOC SUMMARY] ------')
    print(f'Files: \t\t{tot_files}')
    print(f'Lines of code: \t{locs}')
    print(f'Duration: \t{round(time_val, 2)} s')

    if show_insights:
        print('--- [LOCs per file type] ---')
        for ext, count in sorted(locs_per_ext_hmap.items(), key=lambda item: item[1], reverse=True):
            if count > 0:
                print(f".{ext}: \t\t{count} \tLongest file: {longest_file_per_ext_hmap[ext][0]} ({longest_file_per_ext_hmap[ext][1]} LOCs)")
            else:
                print(f".{ext}: \t\t{count}")

def main():
    start_time = time.time()
    locs_per_ext_hmap = {}
    longest_file_per_ext_hmap = {}

    parser = setup_parser()
    args = parser.parse_args()

    project_path = Path(args.path)
    extensions = args.extensions
    use_gitignore = args.use_gitignore
    show_insights = args.insights

    if not project_path.exists():
        print(f"[PYLOC] Error: path '{project_path}' does not exist")
        return

    target_files = get_files_list(project_path)
    target_files = set(os.path.normpath(p) for p in target_files)

    excluded_files = set()
    if use_gitignore:
        gitignore_path = Path(os.path.join(project_path, '.gitignore'))
        if not gitignore_path.is_file():
            print(f'-g/--use_gitignore was specified, but no .gitignore file is present in {project_path}')
            return
        try:
            excluded_files = parse_gitignore(gitignore_path)
        except Exception as e:
            print(f"[PYLOC] Error parsing .gitignore: {e}")
            return

    # Filter by extension if provided
    if extensions:
        extensions = [ext.lstrip('.') for ext in extensions]
        target_files = {f for f in target_files if os.path.splitext(f)[1].lstrip('.') in extensions}
        if show_insights:
            for ext in extensions:
                locs_per_ext_hmap[ext] = 0
                longest_file_per_ext_hmap[ext] = (None, -1)

    # Exclude .gitignored files
    target_files.difference_update(excluded_files)

    # Load prog lang commenting info
    comments_json = Path(__file__).parent / 'comments.json'
    with open(comments_json, 'r', encoding='utf-8') as f:
        comment_data = json.load(f)

    # Count LOCs
    total_locs = 0
    total_time = 0
    for f in target_files:
        abs_path = os.path.join(project_path, f)

        file_ext = os.path.splitext(f)[1]      # Get file extension

        file_comment_syntax = comment_data.get(file_ext)    # Get how comments are done in file based on its extension
        if file_comment_syntax is None:
            continue

        file_single_line_comment = file_comment_syntax.get('single_line', None)    # list or single str
        file_multi_line_comment = file_comment_syntax.get('multi_line', None)     # dict

        res = count_locs(abs_path, file_single_line_comment, file_multi_line_comment)
        if not res:
            continue
        f_locs = res
        total_locs += f_locs
        
        if show_insights:
            stripped_file_ext = file_ext.lstrip('.')
            if extensions:
                locs_per_ext_hmap[stripped_file_ext] += f_locs
                if longest_file_per_ext_hmap.get(stripped_file_ext):
                    if longest_file_per_ext_hmap[stripped_file_ext][1] < f_locs:  # Found new longest file of this type, update
                        longest_file_per_ext_hmap[stripped_file_ext] = (abs_path, f_locs)
                else:
                    longest_file_per_ext_hmap[stripped_file_ext] = (abs_path, f_locs)
            else:
                if locs_per_ext_hmap.get(stripped_file_ext):
                    locs_per_ext_hmap[stripped_file_ext] += f_locs
                else:
                    locs_per_ext_hmap[stripped_file_ext] = f_locs

    total_time = time.time() - start_time
    format_print(
        show_insights, 
        total_locs, 
        total_time, 
        locs_per_ext_hmap, 
        longest_file_per_ext_hmap, 
        len(target_files)
    )
