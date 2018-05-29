
def to_uint_64(i, offset):
    return int.from_bytes(i[offset:offset+8], byteorder='little', signed=False)


def to_int_64(i, offset):
    return int.from_bytes(i[offset:offset+8], byteorder='little', signed=True)


def to_uint_32(i, offset):
    return int.from_bytes(i[offset:offset+4], byteorder='little', signed=False)


def to_int_32(i, offset):
    return int.from_bytes(i[offset:offset+4], byteorder='little', signed=True)


def to_int_16(i, offset):
    return int.from_bytes(i[offset:offset+2], byteorder='little', signed=True)
