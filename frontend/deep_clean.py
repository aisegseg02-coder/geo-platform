import os
import re

directory = '/media/ali/c4aa7682-a327-4640-9138-741c48bc9fc2/home/ali/Downloads/t/geo-platform/frontend'

for filename in os.listdir(directory):
    if filename.endswith(".html") and filename not in ['index.html']:
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Deep Clean Colors for Light Theme
        content = content.replace('rgba(0,0,0,0.3)', 'rgba(0,0,0,0.05)')
        content = content.replace('rgba(0, 0, 0, 0.3)', 'rgba(0, 0, 0, 0.05)')
        content = content.replace('rgba(0,0,0,0.4)', 'var(--surface-hover)')
        content = content.replace('rgba(255, 255, 255, 0.05)', 'rgba(0, 0, 0, 0.02)')
        content = content.replace('rgba(255,255,255,0.05)', 'rgba(0,0,0,0.02)')
        content = content.replace('background: #0', 'background: var(--surface)')
        content = content.replace('background:#0', 'background:var(--surface)')
        content = content.replace('color: white', 'color: var(--text)')
        content = content.replace('color:#fff', 'color:var(--text)')
        content = content.replace('color: #fff', 'color: var(--text)')
        
        # Specific fix for pre tags in light theme
        content = content.replace('pre {', 'pre { background: #f8f8f8; color: #333; ')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

print("Deep cleaned colors and fixed code blocks.")
