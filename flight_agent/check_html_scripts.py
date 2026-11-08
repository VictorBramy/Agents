import urllib.request
import re

url = "https://www.bluebirdair.com/"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=10) as r:
    html = r.read().decode("utf-8", errors="ignore")
    matches = re.findall(r'controllers/[^"\']+', html)
    print("Controllers in HTML:", set(matches))
    scripts = re.findall(r'src=["\']([^"\']+\.js)', html)
    print("Scripts in HTML:", scripts)

    # Find destinations json in HTML
    m_dest = re.search(r'var destinations = (\[.*?\]);', html)
    if m_dest:
        print("Destinations JSON:", m_dest.group(1)[:300])
    m_from = re.search(r'var origins = (\[.*?\]);', html)
    if m_from:
        print("Origins JSON:", m_from.group(1)[:300])
