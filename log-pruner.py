#!/usr/bin/env python3
"""Log Pruner - Report and clean old log files by size or age."""

import os
import argparse
import time
import datetime


def scan_logs(directory, depth=2):
    """Scan directory tree and report oversized or aged log files.
    
    Args:
        directory: Starting path
        depth: Max traversal depth (default 2).
    
    Returns list of dicts with size, date, age_days, name, recommendation.
    """
    logs = []
    
    def iterate(path, current=0):
        if os.path.isdir(path) and (depth == 0 or current < depth):
            for fname in os.listdir(path):
                fpath = os.path.join(path, fname)
                
                # Skip subdirectories if below max_depth
                if not os.path.isdir(fpath) or (depth > 0 and current >= depth):
                    pass
                
                if os.path.isfile(fpath):
                    try:
                        stat_info = os.stat(fpath)
                        size = stat_info.st_size  # bytes
                        mtime = stat_info.st_mtime
                        age_days = int((time.time() - mtime) / 86400)
                        
                        # Simple pattern detection for logs
                        name_lower = fname.lower()
                        is_log = bool(name_lower.endswith('.log') or 
                                        any(ext in name_lower for ext in ['_log.txt', '.err']))
                        
                        recommendation = ''
                        if is_log:
                            if size > 10 * 1024 * 1024:  # >10MB
                                recommendation = 'review'
                            elif size > 50 * 1024 * 1024:  # >50MB
                                recommendation = 'rotate/delete'
                            else:
                                recommendation = 'ok'
                        else:
                            recommendation = skip if size > 5000 else ''
                        
                        logs.append({
                            'name': fname,
                            'path': fpath.replace(directory, ''),
                            'size': size,
                            'age_days': age_days,
                            'is_log': is_log,
                            'recommendation': recommendation
                        })
                    except (OSError, IOError):
                        continue
    
    try:
        iterate(os.path.abspath(directory))
    except OSError as e:
        print(f"Can't scan {directory}: {e}")

    
    return logs

def main():
    parser = argparse.ArgumentParser(
        description='Log Pruner - Report/log deletion for oversized or aged file files'
    )
    parser.add_argument('-d', '--dirs', action='append', 
                        dest='directories', required=True,
                        help='Directory to scan (can specify multiple)')
    parser.add_argument('--depth', '-l', type=int, default=1,
                        help='Max depth for each dir (default 1)')
    parser.add_argument('-r', '--rotate', action='store_true',
                        help='Flag files >50MB as candidates for rotation/deletion')
    parser.add_argument('-c', '--count', action='store_true',
                        help='Only count and summarize, no reports')
    
    args = parser.parse_args()
    
    all_logs = []
    
    for directory in args.directories:
        if not os.path.isdir(directory):
            print(f"Skipping {directory}: not a directory")
            continue

        logs = scan_logs(directory, args.depth)
        all_logs.extend(logs)

    # Group by recommendation
    reviewable = [x for x in all_logs if x['recommendation'] == 'review']
    deletable = [x for x in all_logs if x['recommendation'] == 'delete' or 
                 x['size'] > 10 * 1024 * 1024]  # Flag big files as delete-eligible

    print(f"\nScan complete: {len(all_logs)} files examined")
    
    if not args.count:
        print("\n" + "="*60)
        print("Files Review or Deletion:")
        
        for f in reviewable[:30]:  # Show top 30, truncate long result
            print(f"{f['name']:<50} {f['size']/1024:>7.1f}KB "
                  f"(age={f['age_days']:.0f}d) RECOMMEND: {f['recommendation']}")

        if len(reviewable) > 30:
            print(f"... and {len(reviewable) - 30} more files")

        print("\n" + "="*60)
        
    else:
        # Only summary
        total_files = sum(1 for x in all_logs if x['is_log'])
        large_files = sum(1 for x in all_logs if x['size'] > 10 * 1024 * 1024)
        
        print(f"Total log-type files: {total_files}")
        print(f">10MB log files: {large_files}")
        print(f"Review candidates (5-10MB): {len(reviewable)}")
        print(f"Rotation candidates (>50MB): {len(deletable)}")

    print("\nUse: rm " + ' '.join([f'"{x["name"]}"' for x in deletable[:3]]))
    
if __name__ == '__main__':
    main()