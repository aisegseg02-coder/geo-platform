import os
import re

directory = '/media/ali/c4aa7682-a327-4640-9138-741c48bc9fc2/home/ali/Downloads/t/geo-platform/frontend'

for filename in os.listdir(directory):
    if filename.endswith(".html") and filename not in ['index.html', 'search.html']:
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Fix gradients that start with white on light background
        content = content.replace('#ffffff 0%, var(--accent)', 'var(--ultra-accent) 0%, var(--accent)')
        content = content.replace('#fff 0%, var(--accent)', 'var(--ultra-accent) 0%, var(--accent)')
        
        # Ensure all H1s use Teko and Charcoal
        content = re.sub(r'h1\s*\{[^}]*\}', 'h1 { font-family: "Teko", sans-serif; color: var(--ultra-accent); font-weight: 600; text-transform: uppercase; }', content)

        # Fix transparency issues
        content = content.replace('rgba(255,255,255,0.08)', 'rgba(0,90,90,0.08)')
        content = content.replace('rgba(255, 255, 255, 0.08)', 'rgba(0, 90, 90, 0.08)')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

print("Final polish applied to gradient and transparency issues.")
