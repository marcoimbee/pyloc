def count_locs(
        target_file: str, 
        comment_signs: list[str] | None, 
        multi_line_comment_signs: dict | None
    ) -> tuple[int, int] | None:
    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[PYLOC] Error reading {target_file}: {e}")
        return None
    
    code_lines_count = 0

    # Handle multi-line comment blocks
    multi_line_comment_ranges = []      # Will contain tuples (start, end) of all the multi comment blocks
    if multi_line_comment_signs:
        start_mark = multi_line_comment_signs.get('start', '')      # Like '/*' for cpp, '<!--' for HTML
        end_mark = multi_line_comment_signs.get('end', '')          # Like '*/' for cpp, '-->' for HTML

        if start_mark and end_mark:
            inside_comment_block = False
            start_block_idx = None

            for i, line in enumerate(lines):            # Scan lines of the target file
                if not inside_comment_block and start_mark in line:      # Found a comment block start mark
                    inside_comment_block = True
                    start_block_idx = i         # Save idx of line
                elif inside_comment_block and end_mark in line:  # Found a comment block end mark
                    multi_line_comment_ranges.append((start_block_idx, i))   # Save end of comment block
                    inside_comment_block = False
                    start_block_idx = None

    # Normalize single line comment marks
    if isinstance(comment_signs, str):
        comment_signs = [comment_signs]
    elif comment_signs is None:
        comment_signs = []

    # Process each line
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue            # Skipping blank lines

        # Check if line is inside a multi-line comment block
        if any(start <= idx <= end for start, end in multi_line_comment_ranges):
            continue
        
        # Check if line is a full line comment
        if any(stripped.startswith(sign) for sign in comment_signs):
            continue

        # Check for inline comment
        has_inline_comment = any(sign in stripped for sign in comment_signs)
        if has_inline_comment:
            code_lines_count += 1
            continue

        # Fallback: pure code line
        code_lines_count += 1
        
    return code_lines_count
