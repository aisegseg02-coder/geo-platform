import os
import re

directory = '/media/ali/c4aa7682-a327-4640-9138-741c48bc9fc2/home/ali/Downloads/t/geo-platform/frontend'

for filename in os.listdir(directory):
    if filename.endswith(".html"):
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Branding Replacement
        content = content.replace('Zaher AI', 'Moharek Platform')
        content = content.replace('Zaher.ai', 'Moharek.ai')
        content = content.replace('ZAHIR', 'MOHAREK')
        content = content.replace('Zaher', 'Moharek')
        
        # Typos
        content = content.replace('استخبارat', 'استخبارات')
        content = content.replace('أسبوعي تقرير', 'تقرير أسبوعي')

        # Additional Premium Polish
        content = content.replace('Outfit', 'Teko')
        content = content.replace('Syne', 'Teko')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

print("Branding and typo fix complete.")
