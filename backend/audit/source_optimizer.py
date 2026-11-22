"""
source_optimizer.py — Compress/optimize contract source for large prompts.

When Groq free tier complains about "Request too large", we compress the
source code by:
1. Removing comments (// and /* */ style)
2. Collapsing excess whitespace
3. Removing unnecessary imports/pragmas (keeping only critical ones)
4. Optionally truncating if still too large
"""

import re


def remove_solidity_comments(source: str) -> str:
    """Remove // and /* */ style comments from Solidity code."""
    # Remove // comments (single-line)
    source = re.sub(r'//.*?(\n|$)', r'\1', source)
    # Remove /* */ comments (multi-line)
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)
    return source


def collapse_whitespace(source: str) -> str:
    """Collapse multiple blank lines and excess spaces."""
    # Replace multiple newlines with double newline
    source = re.sub(r'\n\n\n+', '\n\n', source)
    # Strip trailing whitespace from each line
    source = '\n'.join(line.rstrip() for line in source.split('\n'))
    return source


def trim_imports_and_pragmas(source: str) -> str:
    """Keep only essential pragmas and imports, drop redundant ones."""
    lines = source.split('\n')
    kept = []
    pragma_seen = set()
    
    for line in lines:
        # Keep pragma solidity version (first one only)
        if line.strip().startswith('pragma solidity'):
            if 'pragma' not in pragma_seen:
                kept.append(line)
                pragma_seen.add('pragma')
        # Drop SPDX/pragma comments (not essential for analysis)
        elif line.strip().startswith('// SPDX') or line.strip().startswith('pragma'):
            continue
        else:
            kept.append(line)
    
    return '\n'.join(kept)


def optimize_source_for_groq(source: str, target_tokens: int = 11000) -> str:
    """
    Compress source code to fit within Groq's token limits.
    
    Groq free tier: 12K TPM limit.
    Typical prompt structure: ~3K tokens (instructions + rules)
    Leaving ~9K tokens for source code (conservative estimate: 1 token ≈ 4 chars)
    
    Args:
        source: Full contract source code
        target_tokens: Target size in tokens (default 11K = ~44K chars)
    
    Returns:
        Optimized source code
    """
    # Step 1: Remove comments
    source = remove_solidity_comments(source)
    
    # Step 2: Collapse whitespace
    source = collapse_whitespace(source)
    
    # Step 3: Trim non-essential pragmas/imports
    source = trim_imports_and_pragmas(source)
    
    # Step 4: If still too large, truncate (keeping first 80% + last 20%)
    # This preserves contract definition start and end
    target_chars = target_tokens * 4  # rough: 1 token ≈ 4 chars
    if len(source) > target_chars:
        # Keep first 80% and last 20% to preserve structure
        keep_first = int(target_chars * 0.8)
        keep_last = int(target_chars * 0.2)
        truncated = source[:keep_first] + "\n\n[...truncated...]\n\n" + source[-keep_last:]
        source = truncated
    
    return source
