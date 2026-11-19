#!/usr/bin/env python3
# Makes a Yandex KIT friendly copy of the shop feed. Read-only for the site.
# Usage: transform.py source.yml result.xml [--limit N]
import re, sys, xml.dom.minidom

MIN_OFFERS = 1000
CAT_ID, CAT_NAME = "900001", "Трикотаж"
DROP = ("ДатаСоздания", "ДатаИзменения", "Новинка", "Новинка предложение",
        "Остаток", "НомерПредложения", "TSVET", "Картинки")
GROUPING = {"Цвет": "Цвет", "Размер RU": "Размер"}  # feed name -> KIT name
OFFER = re.compile(r"(<offer\b[^>]*>)(.*?)</offer>", re.S)

def par(name):
    return re.compile(r"<param name=(['\"])%s\1[^>]*>(.*?)</param>" % re.escape(name), re.S)

def fix(m):
    head, body = m.group(1), m.group(2)
    st = par("Остаток").search(body)
    cnt = max(0, int(st.group(2))) if st and st.group(2).strip().lstrip("-").isdigit() else None
    pics = re.findall(r"<picture>(.*?)</picture>", body, re.S)
    ex = par("Картинки").search(body)
    if ex:
        pics += [u.strip() for u in ex.group(2).split(",")]
    imgs = []
    for u in pics:
        if u.startswith("http") and u not in imgs:
            imgs.append(u)
    body = re.sub(r"<picture>.*?</picture>\s*", "", body, flags=re.S)
    for n in DROP:
        body = par(n).sub("", body)
    for old, new in GROUPING.items():
        body = body.replace('<param name="%s">' % old, '<param name="%s" is_grouping="true">' % new)
    body = re.sub(r"<categoryId>\s*</categoryId>|<categoryId\s*/>", "<categoryId>%s</categoryId>" % CAT_ID, body)
    add = "".join("<picture>%s</picture>\n" % u for u in imgs[:30]) + "<vendor>LN Family</vendor>\n"
    if cnt is not None:
        add += "<count>%d</count>\n" % cnt
    body = body.replace("</categoryId>", "</categoryId>\n" + add.rstrip("\n"), 1)
    return head + re.sub(r"\n\s*\n", "\n", body).rstrip() + "\n</offer>"

def main():
    src, dst = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    text = open(src, encoding="utf-8").read()
    n_in = len(OFFER.findall(text))
    if n_in < MIN_OFFERS:
        sys.exit("ERROR: only %d offers in source feed" % n_in)
    if limit:
        kept, groups = [], []
        for m in OFFER.finditer(text):
            g = re.search(r'group_id="(\d+)"', m.group(1))
            g = g.group(1) if g else m.group(1)
            if g not in groups:
                if len(kept) >= limit:
                    break
                groups.append(g)
            kept.append(m.group(0))
        a, b = text.index("<offers>") + 8, text.index("</offers>")
        text = text[:a] + "\n" + "\n".join(kept) + "\n" + text[b:]
    text = OFFER.sub(fix, text)
    text = text.replace("</categories>", '<category id="%s">%s</category>\n</categories>' % (CAT_ID, CAT_NAME), 1)
    text = re.sub(r"<!DOCTYPE[^>]*>", "", text, count=1)
    xml.dom.minidom.parseString(text.encode("utf-8"))
    n = len(OFFER.findall(text))
    if text.count("<count>") != n or text.count('is_grouping="true"') != 2 * n:
        sys.exit("ERROR: stock or grouping missing for some offers")
    open(dst, "w", encoding="utf-8").write(text)
    print("OK: %d offers" % n)

if __name__ == "__main__":
    main()
