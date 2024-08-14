import re


def parser(data):
    arr = []
    for i in data.split('\n'):
        try:
            mac = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2}....)', i).group()
            arr.append((mac.strip().replace('  ', ' ').split(' ')))
        except AttributeError:
            pass
    return arr


def zyxel(data):
    arr = []
    for i in data.split('\n'):
        k = i.strip()
        try:
            mac = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', k).group()
            arr.append([mac.upper().replace(':', '-'), k[:2].strip()])
        except AttributeError:
            pass
    return arr


def cisco(data):
    arr = []
    for i in data.split('\n'):
        try:
            mac = re.search(r'([0-9a-f]{4}[.]){2}([0-9A-Fa-f]{4})', i).group()
            mac = mac.upper().replace('.', '')
            reconstruct_mac = '-'.join([mac[i:i+2] for i in range(0, len(mac), 2)])
            if len(i) > 60:
                port = i[72:].strip()
            else:
                port = i[38:].strip()
            arr.append([reconstruct_mac, port])
        except AttributeError:
            pass
    return arr


def orion(data):
    arr = []
    for i in data.split('\n'):
        try:
            mac = re.search(r'([0-9A-F]{4}[.]){2}([0-9A-Fa-f]{4})', i).group()
            mac = mac.upper().replace('.', '')
            reconstruct_mac = '-'.join([mac[i:i + 2] for i in range(0, len(mac), 2)])
            if len(i) > 50:
                port = i[55:58].strip()
            else:
                port = i[18:21].strip()
            arr.append([reconstruct_mac, port])

        except AttributeError:
            pass
    return arr
