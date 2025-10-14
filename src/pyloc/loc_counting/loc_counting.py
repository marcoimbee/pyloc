import os
import re


def threaded_loc_computing(
        project_path: str, 
        target_files: list[str], 
        comment_data: dict, 
        show_insights: bool, 
        extensions: list[str]
    ) -> tuple:
    total_locs = 0
    thread_locs_per_ext_hmap = {}
    thread_longest_file_per_ext_hmap = {}

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
                if thread_locs_per_ext_hmap.get(stripped_file_ext):
                    thread_locs_per_ext_hmap[stripped_file_ext] += f_locs
                else:
                    thread_locs_per_ext_hmap[stripped_file_ext] = f_locs
                if thread_longest_file_per_ext_hmap.get(stripped_file_ext):
                    if thread_longest_file_per_ext_hmap[stripped_file_ext][1] < f_locs:  # Found new longest file of this type, update
                        thread_longest_file_per_ext_hmap[stripped_file_ext] = (abs_path, f_locs)
                else:
                    thread_longest_file_per_ext_hmap[stripped_file_ext] = (abs_path, f_locs)
            else:
                if thread_locs_per_ext_hmap.get(stripped_file_ext):
                    thread_locs_per_ext_hmap[stripped_file_ext] += f_locs
                else:
                    thread_locs_per_ext_hmap[stripped_file_ext] = f_locs

    return (total_locs, thread_locs_per_ext_hmap, thread_longest_file_per_ext_hmap)

def count_locs(
        target_file: str, 
        comment_signs: list[str] | None, 
        multi_line_comment_signs: dict | None
    ) -> int | None:
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
