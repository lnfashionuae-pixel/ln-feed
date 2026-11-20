#!/usr/bin/env python3
# Makes a VK (ВКонтакте Маркет) copy of feed.xml. Read-only for the site.
# - product links get UTM tags; the description starts with a «buy on the site» link;
# - sold-out offers (count 0) are marked available="false";
# - VK allows max 50 values per property: rare colours are folded into a base colour
#   (only when that does not merge two variants of the same model).
# Usage: vk.py feed.xml feed-vk.xml
import re, sys, collections, xml.dom.minidom

UTM = "utm_source=vk&amp;utm_medium=market&amp;utm_campaign=catalog"
OFFER = re.compile(r"(<offer\b[^>]*>)(.*?)</offer>", re.S)
COLOR = re.compile(r'(<param name="Цвет"[^>]*>)(.*?)(</param>)', re.S)
SIZE = re.compile(r'<param name="Размер"[^>]*>(.*?)</param>', re.S)
MAXV = 50
SYN = {"бордовый": "Бордо", "вишневый": "Бордо", "фуксия темный": "Фуксия", "пудровый": "Пудра",
       "молочный шоколад": "Шоколадный", "какао": "Шоколадный", "капучино": "Кофейный",
       "кофейный": "Кофейный", "медовый": "Карамель", "чайная роза": "Пыльная роза",
       "персиковый": "Пыльная роза", "лиловый": "Розовый", "бирюзовый": "Голубой",
       "морская волна": "Голубой", "серо-голубой": "Голубой", "индиго": "Синий",
       "ярко-синий": "Синий", "темно-синий": "Синий", "темно-серый": "Серый",
       "дымчатый серый": "Серый", "графит": "Серый", "темно-зеленый": "Зеленый",
       "оливковый": "Зеленый", "фисташковый": "Зеленый", "изумрудный": "Зеленый",
       "жемчужный": "Молочный", "сливочный": "Молочный", "кремовый": "Молочный",
       "шампань": "Бежевый", "песочный": "Бежевый", "горчичный": "Желтый",
       "леопард": "Коричневый", "бронзовый": "Золотой"}


def url(m):
    u = m.group(1).strip()
    if "utm_source=" not in u:
        u += ("&amp;" if "?" in u else "?") + UTM
    return "<url>%s</url>" % u


def cap(s):
    return s[:1].upper() + s[1:]


def base(c, keep):
    low = c.strip().lower()
    if low in SYN:
        return SYN[low]
    first = re.split(r"\s*/\s*|\s+в\s+|-", low)[0].strip()
    for k in keep:
        if k.lower() == first:
            return k
    return SYN.get(first)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    text = open(src, encoding="utf-8").read()
    offers = OFFER.findall(text)
    n = len(offers)
    if n < 1000:
        sys.exit("ERROR: only %d offers" % n)
    # colour folding
    info = []
    for head, body in offers:
        g = re.search(r'group_id="([^"]+)"', head)
        c, s = COLOR.search(body), SIZE.search(body)
        info.append((g.group(1) if g else head, c.group(2).strip() if c else None, s.group(1).strip() if s else ""))
    cnt = collections.Counter(cap(c) for _, c, _ in info if c)
    keep = [c for c, _ in cnt.most_common()]
    mapping = {}
    for limit in range(MAXV, 0, -1):
        keep = [c for c, _ in cnt.most_common(limit)]
        mapping = {}
        for c in cnt:
            if c in keep:
                mapping[c] = c
            else:
                b = base(c, keep)
                mapping[c] = b if b in keep else c
        # do not merge two variants of one model
        seen = collections.defaultdict(set)
        bad = set()
        for g, c, s in info:
            if not c:
                continue
            key = (mapping[cap(c)], s)
            if key in seen[g] and mapping[cap(c)] != cap(c):
                bad.add(cap(c))
            seen[g].add(key)
        for c in bad:
            mapping[c] = c
        if len(set(mapping.values())) <= MAXV:
            break
    if len(set(mapping.values())) > MAXV:
        sys.exit("ERROR: still %d colours" % len(set(mapping.values())))

    def fix(m):
        head, body = m.group(1), m.group(2)
        body = re.sub(r"<url>(.*?)</url>", url, body, count=1, flags=re.S)
        u = re.search(r"<url>(.*?)</url>", body, re.S)
        if u:
            line = "Купить на сайте с примеркой: %s" % u.group(1).strip()
            if "<description>" in body:
                body = body.replace("<description>", "<description>" + line + "\n\n", 1)
            else:
                body = body.replace("</name>", "</name>\n<description>%s</description>" % line, 1)
        body = COLOR.sub(lambda c: c.group(1) + mapping.get(cap(c.group(2).strip()), c.group(2)) + c.group(3), body)
        if re.search(r"<count>0</count>", body):
            head = re.sub(r'available="[^"]*"', 'available="false"', head)
        return head + body + "</offer>"

    text = OFFER.sub(fix, text)
    xml.dom.minidom.parseString(text.encode("utf-8"))
    if len(re.findall(r"<url>[^<]*utm_source=vk", text)) != n:
        sys.exit("ERROR: UTM missing for some offers")
    open(dst, "w", encoding="utf-8").write(text)
    print("OK VK: %d offers, %d not available, %d colours" % (n, text.count('available="false"'), len(set(mapping.values()))))


if __name__ == "__main__":
    main()
