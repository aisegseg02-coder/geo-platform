import os
import re

directory = '/media/ali/c4aa7682-a327-4640-9138-741c48bc9fc2/home/ali/Downloads/t/geo-platform/frontend'

# Standard Corporate Nav for all pages
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

# Standardized style block for subpages
style_overrides = '''
    body { background: var(--bg); color: var(--text); font-family: 'Manrope', 'Cairo', sans-serif; }
    nav { background: var(--ultra-accent); border-bottom: 1px solid var(--accent); padding: 0 60px; height: 70px; display: flex; align-items: center; position: fixed; top: 0; left: 0; right: 0; z-index: 1000; width: 100%; box-sizing: border-box; justify-content: space-between; }
    .nav-logo { font-family: 'Teko', sans-serif; font-size: 24px; font-weight: 600; color: #fff; text-decoration: none; letter-spacing: 1px; }
    .nav-logo span { color: var(--accent-secondary); }
    .nav-links { display: flex; gap: 30px; }
    .nav-links a { color: #f5f5f5; text-decoration: none; font-size: 13px; font-weight: 500; transition: all 0.3s; text-transform: uppercase; }
    .nav-links a:hover, .nav-links a.active { color: var(--accent-secondary); }
    .wrap { max-width: 1400px; margin: 0 auto; padding: 120px 40px 60px; }
    .panel, .card { background: var(--surface); border: 1px solid var(--border); border-top: 3px solid var(--accent); border-radius: 0; box-shadow: var(--card-shadow); color: var(--text); }
'''

nav_re = re.compile(r'<nav.*?>.*?</nav>', re.DOTALL)
wrap_padding_re = re.compile(r'<div class="wrap".*?>', re.DOTALL)

for filename in os.listdir(directory):
    if filename.endswith(".html") and filename not in ['index.html', 'search.html', 'ads.html', 'content_v2.html']:
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Update Nav
        content = nav_re.sub(new_nav, content)
        
        # Add Style Overrides at the beginning of the <style> tag
        if '<style>' in content:
            content = content.replace('<style>', '<style>' + style_overrides)
        
        # Fix wrap padding (internal pages need more top padding for fixed nav)
        content = content.replace('class="wrap"', 'class="wrap" style="padding-top:120px;"')
        content = content.replace('class="container"', 'class="container" style="padding-top:120px;"')

        # Clean up any leftover dark backgrounds in cards
        content = content.replace('background: rgba(0,0,0,0.4)', 'background: var(--surface)')
        content = content.replace('background:rgba(0,0,0,0.4)', 'background:var(--surface)')
        content = content.replace('background: rgba(255,255,255,0.05)', 'background: var(--surface-hover)')
        content = content.replace('color: white', 'color: var(--text)')
        content = content.replace('color:white', 'color:var(--text)')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

print("Standardized all internal subpages.")
