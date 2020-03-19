import os
import re


def get_all_files(dir, match_pattern=None):
    arr = []
    for root, dirs, files in os.walk(dir, topdown=False):
        for name in files:
            if match_pattern is not None and re.match(match_pattern,
                                                      name) is None:
                continue
            arr.append(os.path.abspath(os.path.join(root, name)))
    return arr
