import os
import re

directory = '/media/ali/c4aa7682-a327-4640-9138-741c48bc9fc2/home/ali/Downloads/t/geo-platform/frontend'

fonts_re = re.compile(r'<link href="https://fonts\.googleapis\.com.*?rel="stylesheet">')
new_fonts = '<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&family=Manrope:wght@400;500;600;700&family=Teko:wght@400;500;600;700&display=swap" rel="stylesheet">'

root_vars_re = re.compile(r':root\s*\{[^}]+\}', re.MULTILINE | re.DOTALL)
font_family_re1 = re.compile(r"font-family:\s*'[A-Za-z ]+',\s*(?:'?[A-Za-z ]+'?,\s*)?(?:sans-serif|monospace)")
font_family_re2 = re.compile(r"font-family:\s*'[A-Za-z ]+'")

for filename in os.listdir(directory):
    if filename.endswith(".html") and filename not in ['index.html', 'search.html']:
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Update Fonts Link
        content = fonts_re.sub(new_fonts, content)
        
        # Remove custom inline roots to fallback to theme.css (except in files we need it, but we want all to share theme.css)
        content = root_vars_re.sub('/* Inherit from theme.css */', content)

        # Update all border-radiuses to 0
        content = re.sub(r'border-radius:\s*\d+(?:px|rem|em|%);', 'border-radius: 0;', content)
        content = re.sub(r'border-radius:\s*99px;', 'border-radius: 0;', content)

        # Replace standard fonts with corporate fonts
        content = content.replace("'Outfit'", "'Teko'")
        content = content.replace("'Syne'", "'Teko'")
        content = content.replace("'Inter'", "'Manrope', 'Cairo'")
        content = content.replace("'IBM Plex Mono'", "'Manrope'")

        # Remove background grid patterns in body that cause dark mode feel
        content = re.sub(r'body::before\s*\{[^}]+\}', 'body::before { display: none; }', content)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

print("Updated all HTML files to corporate identity.")
