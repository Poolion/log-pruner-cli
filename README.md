# Log Pruner - CLI Tool for Finding and Cleaning Old/Oversized Logs

CLI that scans directories and flags log files by size/age for review or deletion:

- **Size-based reporting**: Identify 10MB+ logs before they fill quota
- **Aged file detection**: Report logs older than rotation schedule
- **Summary mode**: Count candidates only, skip lengthy detail output
- **Deletion help**: Generate `rm` command lists for quick cleanup

Perfect for:
- Post-deployment checks (logs from builds still linger)
- CI/CD artifacts that need pruning before commit to repo
- Shared directories where log files accumulate without rotation
- Systems with strict storage quotas (cloud containers, VPS limits)

## Usage

```bash
# Basic scan and recommendations
python log-pruner.py -d /var/log [-l depth]

# Quick count only
python log-pruner.py -c -d /home/app/logs

# Scan multiple directories
python log-pruner.py -d /var/log -d /tmp/monitoring
```

### Options

| Option | Description                          |
|--------|--------------------------------------|
| `-d,--dirs` | Directory to scan (repeat as needed) |
| `-l,--depth` | Max traversal depth per dir         |
| `-r,--rotate` | Flag files >50MB for rotation       |
| `-c,--count`  | Only summary counts, no detail     |

### Command Examples

#### Full Detailed Report

```bash
python log-pruner.py -d /var/log -l 2 -r
```

Reports top 30 files needing attention:

```
daemon.log                       15.2MB (age=14d) RECOMMEND: review
system-auth.log                  28.7MB (age=62d) RECOMMEND: delete
nginx/access.log                 72.4MB (age=90d) RECOMMEND: delete
```

Color-coded by size and age helps spot candidates for immediate deletion or rotation:

- `review`: 5-10MB or aged files—likely temporary accumulation before rotation
- `delete`: >10MB or >30 days old without access review
- `skip`: smaller files (<1KB per example) that don't need attention

#### Quick Count Summary

```bash
python log-pruner.py -c -d /home/production/logs
```

Quick counts for CI/CD gates:

```
Total log-type files: 842
>10MB log files: 15
Review candidates (5-10MB): 6
Rotation candidates (>50MB): 2
```

Pipe summary into dashboards or logging systems. In automated environments, `count` output suffices for quotas compliance checks—no need to review each oversized file when total count exceeds policy threshold (e.g., >10MB logs not deleted within rotation window).

## Code Example

The scanner walks directories and accumulates log-file info:

```python
def scan_logs(directory, depth=2):
    logs = []
    
    def iterate(path, current=0):
        if os.path.isdir(path) and (depth == 0 or current < depth):
            for fname in os.listdir(path):
                fpath = os.path.join(path, fname)
                
                # Skip subdirectories if deep enough
                if os.path.isfile(fpath):
                    try:
                        stat_info = os.stat(fpath)
                        size = stat_info.st_size
                        mtime = stat_info.st_mtime
                        age_days = int((time.time() - mtime) / 86400)
                        
                        # Simple log file detection
                        name_lower = fname.lower()
                        is_log = (name_lower.endswith('.log') or 
                                  any(ext in name_lower for ext in ['_log', '.err']))
                        
                        # Recommendation based on size threshold
                        if size > 10 * 1024 * 1024:
                            recommendation = 'review'
                        elif size > 50 * 1024 * 1024:
                            recommendation = 'delete'
                        
                        logs.append({'name': fname, 'path': fpath, 'size': size,
                                     'age_days': age_days, 'is_log': is_log,
                                     'recommendation': recommendation})
                    except IOError:
                        continue
    
    iterate(os.path.abspath(directory), current)

```

Size detection uses `os.stat()` to get file byte count. Age in days comes from comparing modification timestamp against current time divided by seconds per day (86400). Recommendation thresholds are size-based: files larger than 10MB trigger review flag, those >50MB flagged for rotation/deletion.

Log detection uses simple pattern matching on filename strings—files ending with `.log` or containing `_log` markers count as log-type files. Config/backup files without common extensions aren't included in recommendations since those are handled separately (or should be excluded from scan).

## Use Cases

### CI/CD Cleanup Script

After a build pipeline fails to clean logs, find them automatically:

```bash
python log-pruner.py -c -d /tmp/build-artifacts
# Output feeds into GitHub Actions or GitLab CI cleanup scripts
```

Count output used in conditional logic—if review candidates > threshold, notify team to check rotation configuration. When reviewing build failures where logs aren't cleaned before artifacts are archived, automated scan flags directories with oversized files that would inflate download size. For large artifact pipelines, this catches issues before pushing to S3 or other remote storage where quota limits apply.

### Shared Directory Audit

Find log files shared across teams without proper rotation:

```bash
python log-pruner.py -d /home/shared/logs -l 2 -c
```

Team directories often accumulate `daemon.log`, `system-auth.log`, `nginx/access.log` without central management. When multiple services write logs to same directory and no rotation happens, size grows rapidly. Use `-r` flag to flag files for rotation with tools like `logrotate(8)` after manual inspection of oldest entries first. Before archiving or deleting, check if entries still relevant for debugging recent failures.

### Quota Compliance Check

Cloud containers and VPS environments have quotas that expire—find logs before hitting limits:

```bash
for dir in /var/container-logs/*; do \
    python log-pruner.py -d "$dir" -c 2>/dev/null; done
```

Aggregated counts across subdirectories help determine where rotation policies need tightening. If any single directory exceeds its quota, flag it immediately for team notice (especially when older entries from failed builds aren't cleaned).

### Production System Review

Scan application logs before scaling or migration:

```bash
python log-pruner.py -d /opt/app/logs -r -l 3
```

Deep scan includes nested subfolders where monitoring agents write intermediate outputs. Large files in `/var/lib/monitoring` often accumulate from metrics collection without rotation configured, causing space exhaustion when quota isn't raised or retention reduced. For services written with `stdout/err` redirection to files rather than journald/centralized logging, log file sizes grow unboundedly if application restarts don't truncate outputs.

## Alternatives Compared

| Tool              | Strength                  | Limitation                    |
|-------------------|---------------------------|-------------------------------|
| `du -sh *`        | Quick totals per dir      | No logs-specific detection    |
| `find -size +10M` | Finds large files         | No age/rotation context       |
| This tool         | Size + age, recommendations | Needs write permission check  |

Simple `find . -name "*.log" -delete` removes all logs without verifying relevance. When rotation isn't configured before deletion, valuable debug info from critical failures gets lost. This tool flags files based on size (for quota awareness) while still respecting retention policies by recommending human review first.

## Common Log Names Expected

- `system.log`, `daemon.log`: System-level activity
- `nginx/access.log`, `apache2/access_log`: Web server logs
- `application.log`, `app.log`: Service/application outputs
- `.err` files: Error output redirected from services
- `_log.txt`: Temporary log entries

Pattern matching catches common naming conventions (ending in `.log`, containing `_log`, or matching err extensions) without needing explicit file type detection beyond filename heuristics.

## Source Code

Public repo with examples and test cases suitable for security automation scripts or policy enforcement tools. Readable, dependency-free implementation using only standard library.

🔗 **Repo**: https://github.com/Poolion/log-pruner-cli

If you find this useful, you can support development: https://www.buymeacoffee.com/poolion