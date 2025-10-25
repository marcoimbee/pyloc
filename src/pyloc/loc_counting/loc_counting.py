import re


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
