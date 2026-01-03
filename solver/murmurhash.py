# murmurhash.py
def murmurhash64(key: bytes):
    m = 0xC6A4A7935BD1E995
    r = 47
    seed = 1203989050
    h = seed ^ (len(key) * m)
    data = bytearray(key)
    nblocks = len(data) // 8
    for i in range(nblocks):
        k = int.from_bytes(data[i * 8 : i * 8 + 8], "little")
        k *= m
        k ^= k >> r
        k *= m
        h ^= k
        h *= m
    tail = data[nblocks * 8 :]
    k = 0
    for i, b in enumerate(tail):
        k |= b << (i * 8)
    if k != 0:
        k *= m
        k ^= k >> r
        k *= m
        h ^= k
        h *= m
    h ^= h >> r
    h *= m
    h ^= h >> r
    return h & 0xFFFFFFFFFFFFFFFF
