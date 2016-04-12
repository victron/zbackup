
__author__ = 'vic'
# functions for printing tables


def print_table(table):
    """
    :param table: [('ssssssssss', 'ffff','ggggggggggg'),('ddd','eeee','hhhhhhhhhh'),('deeeeeeedd','eeeerrrrr','hhhhh')]
    :return:
    print
| ssssssssss | ffff      | ggggggggggg |
| ---------- | --------- | ----------- |
| ddd        | eeee      | hhhhhhhhhh  |
| ---------- | --------- | ----------- |
| deeeeeeedd | eeeerrrrr | hhhhh       |
| ---------- | --------- | ----------- |
    """
    col_width = [max(len(str(x)) for x in col) for col in zip(*table)]
    for line in table:
        print("| " + " | ".join("{:{}}".format(str(x), col_width[i]) for i, x in enumerate(line)) + " |")
        print("| " + " | ".join("{:{}}".format('-' * col_width[i], col_width[i]) for i, x in enumerate(line)) + " |")


def print_table_as_is(table):
    [print('| ' + '|'.join(line) + ' |') for line in table]


def split_len(seq, length):
    return [seq[i:i + length] for i in range(0, len(seq), length)]


def split_len_add_char(seq, length, char=' '):
    # split string on equal length of char list, to last list member attach <char>
    chars_to_add = length - len(seq) % length
    if chars_to_add == length:
        chars_to_add = 0
    seq = seq + char * (chars_to_add // len(char)) + char[:chars_to_add % len(char)]
    return [seq[i:i + length] for i in range(0, len(seq), length)]


def reform_table_fix_columns_sizes(table, column_list: 'list or int') -> list:
    """
    :param table:  [('ssssssssss', 'ffff','ggggggggggg'),
                    ('ddd','eeee','hhhhhhhhhh'),('deeeeeeedd',
                    'eeeerrrrr','hhhhh')]
    :param column_list: list of max size of column, or int value for all columns
    :return: [('ssss', 'ffff', 'gggg'),
              ('ssss', '    ', 'gggg'),
              ('ss  ', '    ', 'ggg '),
              ('----', '----', '----'),
              ('ddd ', 'eeee', 'hhhh'),
              ('    ', '    ', 'hhhh'),
              ('    ', '    ', 'hh  '),
              ('----', '----', '----'),
              ('deee', 'eeee', 'hhhh'),
              ('eeee', 'rrrr', 'h   '),
              ('dd  ', 'r   ', '    '),
              ('----', '----', '----')]
    format table from:
    | ssssssssss | ffff      | ggggggggggg |
    | ddd        | eeee      | hhhhhhhhhh  |
    | deeeeeeedd | eeeerrrrr | hhhhh       |
    into
    | ssss | ffff | gggg |
    | ssss |      | gggg |
    | ss   |      | ggg  |
    | ---- | ---- | ---- |
    | ddd  | eeee | hhhh |
    |      |      | hhhh |
    |      |      | hh   |
    | ---- | ---- | ---- |
    | deee | eeee | hhhh |
    | eeee | rrrr | h    |
    | dd   | r    |      |
    | ---- | ---- | ---- |
    """
    if isinstance(column_list, int):
        # create list of int with same values from header
        # noinspection PyUnusedLocal
        column_list = [column_list for word in table[0]]
    new_table = []
    for line in table:
        new_line = []
        iter_column_size = iter(column_list)
        new_line += [split_len_add_char(str(word), next(iter_column_size)) for word in line]
        max_list = max([len(x) for x in new_line])  # find max list in new_line
        iter_column_size = iter(column_list)
        for lists in new_line:
            current_column_size = next(iter_column_size)
            # noinspection PyUnusedLocal
            lists += [' ' * current_column_size for i in range(max_list - len(lists))] + ['-' * current_column_size]
        new_table += list(zip(*new_line))
    return new_table


"""
table = [('ssssssssss', 'ffff','ggggggggggg'),('ddd','eeee','hhhhhhhhhh'),('deeeeeeedd','eeeerrrrr','hhhhh')]
print_table(table)
print_table_as_is(reform_table_fix_columns_sizes(table, [4,7,9]))
print_table_as_is(reform_table_fix_columns_sizes(table, 6))
print_table_as_is(reform_table_fix_columns_sizes(table, [15,15,10]))
"""
