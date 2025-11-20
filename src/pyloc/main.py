import argparse
import time
import os
import glob
import json
from pathlib import Path

from .loc_counting.loc_counting import *


def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Simple line of code counter for coding projects')
    parser.add_argument('path', help='Path to the target directory')
    parser.add_argument('-e', '--extensions', nargs='+', default=[], help='File extensions to include')
    parser.add_argument('-g', '--use_gitignore', default=False, action='store_true',
                        help='Exclude from the count files that are included in the .gitignore file of the directory')
    parser.add_argument('-i', '--insights', default=False, action='store_true', help='Show insights. Only available if the -e flag is used')
    return parser

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

def loc_info_format_print(
        show_insights: bool, 
        locs: int, 
        time_val: float, 
        locs_per_ext_hmap: dict, 
        longest_file_per_ext_hmap: dict, 
        tot_files: int
    ) -> None:
    print('----- [PYLOC SUMMARY] ------')
    print(f'Duration: \t\t{round(time_val, 2)} s')
    print(f'Files: \t\t\t{tot_files}')
    print(f'Lines of code: \t\t{locs}')

    if show_insights:
        print('\n--- [LOCs per file type] ---')
        for ext, count in sorted(locs_per_ext_hmap.items(), key=lambda item: item[1], reverse=True):
            if count > 0:
                longest_file = longest_file_per_ext_hmap[ext]
                print(f".{ext}: \t{count} LOCs \tLongest file: {longest_file[0]} ({longest_file[1]} LOCs)")
            else:
                print(f".{ext}: \t{count} LOCs")

def main():
    parser = setup_parser()
    args = parser.parse_args()

    project_path = Path(args.path)
    extensions = args.extensions
    use_gitignore = args.use_gitignore
    show_insights = args.insights

    if not project_path.exists():
        print(f"[PYLOC] Error: path '{project_path}' does not exist")
        return
    
    if not extensions and show_insights:
        print(f'[PYLOC] Usage: -i/--insights is available only when specifying -e/--extensions')
        return

    start_time = time.time()

    target_files = get_files_list(project_path)
    target_files = set(os.path.normpath(p) for p in target_files)

    excluded_files = set()
    if use_gitignore:
        gitignore_path = Path(os.path.join(project_path, '.gitignore'))
        if not gitignore_path.is_file():
            print(f'[PYLOC] Error: -g/--use_gitignore was specified, but no .gitignore file is present in {project_path}')
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

    # Exclude .gitignored files
    target_files.difference_update(excluded_files)

    # Load prog lang commenting info
    comments_json = Path(__file__).parent / 'comments.json'
    with open(comments_json, 'r', encoding='utf-8') as f:
        comment_data = json.load(f)

    locs_per_ext_hmap = {}
    longest_file_per_ext_hmap = {}   # Will contain, for each extension, tuples like (filepath, #locs)

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
        file_locs = res                        # Currently analyzed file LOCs
        total_locs += file_locs                # Aggregated LOCs across all considered files
        
        if show_insights:
            # LOCs
            stripped_file_ext = file_ext.lstrip('.')
            if extensions:
                if locs_per_ext_hmap.get(stripped_file_ext):
                    locs_per_ext_hmap[stripped_file_ext] += file_locs
                else:
                    locs_per_ext_hmap[stripped_file_ext] = file_locs
                if longest_file_per_ext_hmap.get(stripped_file_ext):
                    if longest_file_per_ext_hmap[stripped_file_ext][1] < file_locs:  # Found new longest file of this type, update
                        longest_file_per_ext_hmap[stripped_file_ext] = (abs_path, file_locs)
                else:
                    longest_file_per_ext_hmap[stripped_file_ext] = (abs_path, file_locs)
            else:
                if locs_per_ext_hmap.get(stripped_file_ext):
                    locs_per_ext_hmap[stripped_file_ext] += file_locs
                else:
                    locs_per_ext_hmap[stripped_file_ext] = file_locs

    total_time = time.time() - start_time
    loc_info_format_print(
        show_insights, 
        total_locs, 
        total_time, 
        locs_per_ext_hmap, 
        longest_file_per_ext_hmap, 
        len(target_files)
    )
