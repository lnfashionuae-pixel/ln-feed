#!/usr/bin/env python3
# Makes a VK (ВКонтакте Маркет) copy of feed.xml: product links get UTM tags,
# sold-out offers (count 0) are marked available="false". Read-only for the site.
# Usage: vk.py feed.xml feed-vk.xml
import re, sys, xml.dom.minidom

UTM = "utm_source=vk&amp;utm_medium=market&amp;utm_campaign=catalog"
OFFER = re.compile(r"(<offer\b[^>]*>)(.*?)</offer>", re.S)


def url(m):
    u = m.group(1).strip()
    if "utm_source=" not in u:
        u += ("&amp;" if "?" in u else "?") + UTM
    return "<url>%s</url>" % u


def fix(m):
    head, body = m.group(1), m.group(2)
    body = re.sub(r"<url>(.*?)</url>", url, body, count=1, flags=re.S)
    if re.search(r"<count>0</count>", body):
        head = re.sub(r'available="[^"]*"', 'available="false"', head)
    return head + body + "</offer>"


def main():
    src, dst = sys.argv[1], sys.argv[2]
    text = open(src, encoding="utf-8").read()
    n = len(OFFER.findall(text))
    if n < 1000:
        sys.exit("ERROR: only %d offers" % n)
    text = OFFER.sub(fix, text)
    xml.dom.minidom.parseString(text.encode("utf-8"))
    if text.count("utm_source=vk") != n:
        sys.exit("ERROR: UTM missing for some offers")
    open(dst, "w", encoding="utf-8").write(text)
    print("OK VK: %d offers, %d not available" % (n, text.count('available="false"')))


if __name__ == "__main__":
    main()
