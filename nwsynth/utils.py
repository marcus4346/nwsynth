from time import sleep

def linear_adsr(adsr: tuple[float, int, int, float, int]):
    def get_volume(status: int, ticks: int, ticks_since_released: int) -> float:
        if status == 1:
            if ticks < adsr[1]:
                volume = adsr[0] + (1 - adsr[0]) * ticks / adsr[1]
            elif ticks < adsr[2]:
                volume = 1 - (1 - adsr[3]) * (ticks - adsr[1]) / adsr[2]
            else:
                volume = adsr[3]
        else:
            if ticks_since_released < adsr[4]:
                volume = adsr[3] - ticks_since_released * adsr[3] / adsr[4]
            else:
                volume = 0
        return volume
    return get_volume

def whoami():
    def bytes_to_bool_matrix(data: bytes) -> list[list[bool]]:
        # Long live the Game Boy! Long live retrogaming!
        # https://gbdev.io/pandocs/The_Cartridge_Header.html#0104-0133--nintendo-logo
        assert len(data) == 48
        matrix = [[False for _ in range(48)] for _ in range(8)]
        for row_index, row in enumerate(matrix):
            # 一些中间值，放在内层for循环之外，避免重复运算
            a = row_index // 4 * 24
            b = row_index // 2 % 2
            c = row_index % 2 * 4
            for index in range(48):
                byte_index = a + index // 4 * 2 + b
                bit_position = 7 - c - index % 4
                byte = data[byte_index]
                bit = bool(byte & 1 << bit_position)
                row[index] = bit
        return matrix

    def print_rows(matrix: list[list[bool]], characters: str):
        for row_index, row in enumerate(matrix):
            str_row = []
            for index, bit in enumerate(row):
                # Two characters per "pixel"
                character_index = index * 2 + row_index
                first_character = characters[character_index % len(characters)]
                second_character = characters[(character_index + 1) % len(characters)]
                str_row.append(first_character + second_character if bit else '  ')
            print(''.join(str_row))
            sleep(0.05)

    data_str = (
        'CE FD 13 7D 88 89 00 0E 00 06 00 06 00 07 00 0D'
        '00 09 00 09 00 0F 33 33 CC CC 91 11 BB B9 33 3D'
        '76 66 80 00 CC C7 11 1C 99 BD B9 8B 0E 3E 33 03'
    )
    characters = '4346'

    print('\nPresented by:\n')
    data = bytes.fromhex(data_str)
    matrix = bytes_to_bool_matrix(data)
    print_rows(matrix, characters)
    print()
