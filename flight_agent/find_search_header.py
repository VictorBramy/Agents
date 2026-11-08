import urllib.request

content = urllib.request.urlopen('https://booking.bluebirdair.com/scripts/bookingProcess/header.js').read().decode('utf-8')
idx = 0
while True:
    idx = content.find('"search"', idx)
    if idx == -1:
        break
    print("--- MATCH AT", idx, "---")
    print(content[max(0, idx-200):min(len(content), idx+300)])
    idx += 8
