#!/usr/bin/env python
# -*- coding: utf-8 -*-
# bmconv.py - Read Delicious.com bookmark file and convert it into a list of dictionaries.
import re

bookmark_file = 'delicious.html'

def main():
    """Return a list of dictionaries of bookmarks."""
    lines_list = []
    with open(bookmark_file, 'r') as f:
        lines_list = f.readlines()
    entries_list = []
    for idx, line in enumerate(lines_list):
        entry = {}
        if re.match(r'^<DT>', line):
            entry['url'] = re.match(r'^.*HREF=\"([^\"]+)\"', line).group(1)
            entry['add_date'] = re.match(r'^.*ADD_DATE=\"([^\"]+)\"', line).group(1)
            entry['private'] = re.match(r'^.*PRIVATE=\"([^\"]*)\"', line).group(1)
            entry['tags'] = re.match(r'^.*TAGS=\"([^\"]*)\"', line).group(1).split(',')
            entry['title'] = re.match(r'^.*<A [^>]+>(.*)</A>', line).group(1)
            if re.match(r'^<DD>', lines_list[idx + 1]):
                dd_tmp = []
                increment = 1
                try:
                    while True:
                        if re.match(r'^<DT>', lines_list[idx + increment]):
                            break
                        dd_tmp.append(re.match(r'^(<DD>)?(.*)$', lines_list[idx + increment]).group(2))
                        increment += 1
                except:
                    pass
                entry['description'] = '\n'.join(dd_tmp)
            entries_list.append(entry)
    return entries_list

if __name__ == '__main__':
    print(main())

