import os
import re
import random
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import subprocess


LOG_DIR = 'logs'  # <-- Specify the directory containing log files

def parse_timestamp(line):
    match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S,%f')
    return None

def extract_view(line):
    match = re.search(r"Current view: ({.*})", line)
    if match:
        try:
            return eval(match.group(1))
        except:
            pass
    return None

def count_pushes_and_pulls(lines):
    pulls = 0
    pushes = 0
    merges = 0
    for line in lines:
        if '[SEND pull to' in line:
            pulls += 1
        elif '[SEND push to' in line or '[SEND push reply' in line:
            pushes += 1
        elif '[MERGE]' in line:
            merges += 1
    return pulls, pushes, merges

def analyze_log(filepath, expected_node_count=None):
    with open(filepath) as f:
        lines = f.readlines()

    pulls, pushes, merges = count_pushes_and_pulls(lines)

    first_time = None
    complete_time = None
    last_known_view = {}

    for line in lines:
        ts = parse_timestamp(line)
        if '[STATE] Current view:' in line:
            view = extract_view(line)
            if view is not None:
                last_known_view = view
                if first_time is None:
                    first_time = ts
                if expected_node_count is None:
                    expected_node_count = max(view.values()) + 1  # fallback guess
                if len(view) >= expected_node_count and complete_time is None:
                    complete_time = ts

    return {
        'file': os.path.basename(filepath),
        'pulls': pulls,
        'pushes': pushes,
        'merges': merges,
        'first_time': first_time,
        'complete_time': complete_time,
        'duration_to_completion': (complete_time - first_time).total_seconds() if first_time and complete_time else None,
        'final_view': last_known_view,
        'node_count': len(last_known_view)
    }

def main():
    log_files = [os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR) if f.endswith('.txt') or f.endswith('.log')]
    names = [] 
    merge_times = []
    print(f"{'Log File':<25} | {'Pulls':<6} | {'Pushes':<7} | {'Merges':<7} | {'Complete in (s)':<15} | Nodes Seen")
    print('-' * 85)

    for log_file in log_files:
        result = analyze_log(log_file, len(log_files))
        names.append(result['file'])
        merge_times.append(result['duration_to_completion'])
        print(f"{result['file']:<25} | {result['pulls']:<6} | {result['pushes']:<7} | {result['merges']:<7} | {result['duration_to_completion'] or 'N/A':<15} | {result['node_count']}")

    #--------------create merge time graph----------------#
    chart_name = "merge_chart.png"
    colors = ["#" + ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])
          for _ in range(len(merge_times))]
    plt.title("Station Merge Times")
    plt.bar(names, merge_times, color=colors, width=0.9)
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.grid(axis='y', linestyle='--', alpha=0.3)  # horizontal dashed lines
    # Increase number of y-ticks
    plt.yticks(np.arange(0, max(merge_times)+1, 0.25), fontsize=5)  # e.g., every 2 units
    plt.ylabel('Merge Time (seconds)')
    plt.tight_layout()
    # Save as PNG
    plt.savefig(chart_name, dpi=300)  # dpi controls resolution

    # -----------------------------
    # Push to GitHub
    # -----------------------------
    repo_path = os.getcwd()
    try:
        subprocess.run(["git", "add", "bar_chart.png"], check=True, cwd=repo_path)
        subprocess.run(["git", "commit", "-m", "Add/update bar_chart.png"], check=True, cwd=repo_path)
        subprocess.run(["git", "push"], check=True, cwd=repo_path)
        print(f"Successfully pushed {chart_name} to GitHub!")
    except subprocess.CalledProcessError as e:
        print("Error during git operation:", e)
    exit()

if __name__ == '__main__':
    main()

