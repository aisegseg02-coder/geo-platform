import os
import re

directory = '/media/ali/c4aa7682-a327-4640-9138-741c48bc9fc2/home/ali/Downloads/t/geo-platform/frontend'

new_nav = '''
  <nav>
    <a href="/" class="nav-logo">MOHAREK<span>.</span>GEO</a>
    <div class="nav-links">
      <a href="/jobs.html">المهام</a>
      <a href="/recommendations.html">التوصيات</a>
      <a href="/search.html">الذكاء</a>
      <a href="/content_v2.html">المحتوى</a>
      <a href="/ads.html">الإعلانات</a>
      <a href="/geo-toolkit.html">الخدمات</a>
    </div>
    <a href="/" class="nav-cta">الرئيسية</a>
  </nav>
'''

for filename in os.listdir(directory):
    if filename.endswith(".html") and filename not in ['index.html']:
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Insert Nav if missing
        if '<nav>' not in content and '<body>' in content:
            content = content.replace('<body>', '<body>\n' + new_nav)
        elif '<nav>' in content:
            # Refresh Nav to latest
            content = re.sub(r'<nav.*?>.*?</nav>', new_nav, content, flags=re.DOTALL)

        # Fix Modals and floating elements to be sharp
        content = content.replace('border-radius: 8px', 'border-radius: 0')
        content = content.replace('border-radius: 12px', 'border-radius: 0')
        content = content.replace('border-radius: 16px', 'border-radius: 0')
        content = content.replace('border-radius: 20px', 'border-radius: 0')
        content = content.replace('border-radius: 28px', 'border-radius: 0')
        
        # Ensure all links to other subpages work
        content = content.replace('href="/search"', 'href="/search.html"')
        content = content.replace('href="/content"', 'href="/content_v2.html"')
        content = content.replace('href="/recommendations"', 'href="/recommendations.html"')
        content = content.replace('href="/ads"', 'href="/ads.html"')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

print("Standardized Nav and Links across all subpages.")
