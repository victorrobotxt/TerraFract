#!/usr/bin/env python3
import os, fnmatch, argparse

def load_ignore_patterns(ignore_file_path):       
    dir_pats, file_pats = [], []
    if not os.path.exists(ignore_file_path):      
        return dir_pats, file_pats
    with open(ignore_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):  
                continue
            p = line.replace('\\', '/')
            if p.endswith('/'):
                dir_pats.append(p.rstrip('/'))    
            else:
                file_pats.append(p)
    return dir_pats, file_pats

def load_keep_patterns(keep_file_path):
    pats = []
    if not keep_file_path or not os.path.exists(keep_file_path):
        return pats
    with open(keep_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):  
                continue
            pats.append(line)
    return pats

def should_ignore(rel_path, dir_pats, file_pats): 
    norm = rel_path.replace(os.sep, '/')
    parts = norm.split('/')
    for d in dir_pats:
        if d in parts:
            return True
    name = parts[-1]
    for patt in file_pats:
        if fnmatch.fnmatch(name, patt) or fnmatch.fnmatch(norm, patt):
            return True
    return False

def should_keep(rel_path, keep_pats):
    if not keep_pats:
        return True
    norm = rel_path.replace(os.sep, '/')
    name = os.path.basename(norm)
    for patt in keep_pats:
        if fnmatch.fnmatch(name, patt) or fnmatch.fnmatch(norm, patt):
            return True
    return False

def process_folder(root_folder, output_file,      
                   ignore_file_path, keep_file_path=None):
    dir_pats, file_pats = load_ignore_patterns(ignore_file_path)
    keep_pats = load_keep_patterns(keep_file_path)
    output_path = os.path.abspath(output_file.name)

    for current_dir, dirnames, filenames in os.walk(root_folder):
        rel_dir = os.path.relpath(current_dir, root_folder)
        rel_dir = '' if rel_dir == '.' else rel_dir.replace(os.sep, '/')
        # still prune ignored dirs as before      
        dirnames[:] = [
            d for d in dirnames
            if not should_ignore(f"{rel_dir}/{d}" if rel_dir else d,
                                 dir_pats, file_pats)
        ]
        for fn in filenames:
            full = os.path.join(current_dir, fn)  
            if os.path.abspath(full) == output_path:
                continue
            rel_path = f"{rel_dir}/{fn}" if rel_dir else fn
            # NEW: skip anything not matching keepâ€‘patterns
            if not should_keep(rel_path, keep_pats):
                continue
            if os.path.getsize(full) == 0:        
                continue
            if should_ignore(rel_path, dir_pats, file_pats):
                continue

            output_file.write(f"{rel_path}:\n```\n")
            try:
                with open(full, 'r', encoding='utf-8') as f:
                    output_file.write(f.read())   
            except Exception as e:
                output_file.write("file content") 
            output_file.write("\n```\n\n")        

def main():
    p = argparse.ArgumentParser(
        description="Dump folder contents with code blocks.")
    p.add_argument("folder", help="Folder to process")
    p.add_argument("-o", "--output", default="output.txt",
                   help="Output file")
    p.add_argument("-i", "--ignore", default=".myignore",
                   help="Ignore file in root")    
    p.add_argument("-k", "--keep",
                   help="Optional keepâ€‘only file (one pattern per line)")
    args = p.parse_args()

    ignore_file = os.path.join(args.folder, args.ignore)
    keep_file = os.path.join(args.folder, args.keep) if args.keep else None

    with open(args.output, 'w', encoding='utf-8') as out:
        out.write("Here is the code so far:\n\n") 

        process_folder(args.folder, out, ignore_file, keep_file)
        
        out.write("\n\nNow implement ")

if __name__ == '__main__':
    main()