#!/usr/bin/env python3
# Makes a Yandex KIT friendly copy of the shop feed. Read-only for the site.
# Usage: transform.py source.yml result.xml [--limit N] [--prev old.xml ...]
# Offers that vanished from the source (sold out) are kept from --prev files with stock 0.
import re, sys, xml.dom.minidom

MIN_OFFERS = 1000
CAT_ID, CAT_NAME = "900001", "Трикотаж"
DIMS = "43/31/10"  # shipping box, cm: length/width/height
WEIGHT = "0.8"  # kg, one item
W_JEWEL, JCATS = "0.2", ("154", "155", "160")  # light items weight, accessory categories
JEWEL = re.compile(r"серьг|серёг|чокер|браслет|\bтика\b|цепочк|перчатк|колготк|резинк|леггинс", re.I)
DROP = ("ДатаСоздания", "ДатаИзменения", "Новинка", "Новинка предложение",
        "Остаток", "НомерПредложения", "TSVET", "Картинки")
GROUPING = {"Цвет": "Цвет", "Размер RU": "Размер"}  # feed name -> KIT name
# seed line: id|group_id|url path|price|oldprice|categoryId|name|color|size
SEED = ('<offer id="%s" group_id="%s" available="true">\n<url>https://ln-family.com/shop/%s</url>\n'
        '<price>%s</price>\n<oldprice>%s</oldprice>\n<currencyId>RUB</currencyId>\n<categoryId>%s</categoryId>\n'
        '<vendor>LN Family</vendor>\n<count>0</count>\n<name>%s</name>\n'
        '<param name="Цвет" is_grouping="true">%s</param>\n<param name="Размер" is_grouping="true">%s</param>\n</offer>\n')
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

def code(m):  # vendorCode = offer id, so KIT can match prices and stock
    if "<vendorCode>" in m.group(2):
        return m.group(0)
    i = re.search(r'id="(\d+)"', m.group(1)).group(1)
    return m.group(1) + m.group(2).replace("</vendor>", "</vendor>\n<vendorCode>%s</vendorCode>" % i, 1) + "</offer>"

def wt(m):  # weight: jewelry is lighter than clothes
    b = re.sub(r"<weight>.*?</weight>\n", "", m.group(2))
    n, c = re.search(r"<name>(.*?)</name>", b), re.search(r"<categoryId>(\d+)</categoryId>", b)
    w = W_JEWEL if n and c and c.group(1) in JCATS and JEWEL.search(n.group(1)) else WEIGHT
    return m.group(1) + b.replace("<dimensions>", "<weight>%s</weight>\n<dimensions>" % w, 1) + "</offer>"

def main():
    src, dst = sys.argv[1], sys.argv[2]
    prev = sys.argv[sys.argv.index("--prev") + 1:] if "--prev" in sys.argv else []
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
    ids, kept0 = set(re.findall(r'<offer id="(\d+)"', text)), []
    for name in prev:
        old = open(name, encoding="utf-8").read()
        if name.endswith(".txt"):
            old = "".join(SEED % tuple(x.split("|")) for x in old.splitlines() if x.count("|") == 8)
        for m in OFFER.finditer(old):
            i = re.search(r'id="(\d+)"', m.group(1))
            if i and i.group(1) not in ids:
                ids.add(i.group(1))
                kept0.append(re.sub(r"<count>\d+</count>", "<count>0</count>", m.group(0)).replace("<oldprice></oldprice>\n", ""))
    if kept0:
        text = text.replace("</offers>", "\n".join(kept0) + "\n</offers>", 1)
    text = OFFER.sub(code, text)
    text = re.sub(r"(?<!</dimensions>)\n</offer>", "\n<dimensions>%s</dimensions>\n</offer>" % DIMS, text)
    text = OFFER.sub(wt, text)
    text = text.replace("</categories>", '<category id="%s">%s</category>\n</categories>' % (CAT_ID, CAT_NAME), 1)
    text = re.sub(r"<!DOCTYPE[^>]*>", "", text, count=1)
    xml.dom.minidom.parseString(text.encode("utf-8"))
    n = len(OFFER.findall(text))
    if text.count("<count>") != n or text.count('is_grouping="true"') != 2 * n or text.count("<vendorCode>") != n or text.count("<dimensions>") != n or text.count("<weight>") != n:
        sys.exit("ERROR: stock or grouping missing for some offers")
    open(dst, "w", encoding="utf-8").write(text)
    print("OK: %d offers, %d of them sold out (stock 0)" % (n, len(kept0)))

if __name__ == "__main__":
    main()
