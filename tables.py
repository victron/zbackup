__author__ = 'vic'
# save outputs in objects for future collection and using
"""
Volume |Same snapshot|date_time          |new snapshot|estimated size
------------------------------------------------------------------------------------
zroot-n|20114-10-01  |2014-10-01_10:12:40|2014-10-02  |567 M
"""




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
    [ print ('| ' + '|'.join(line) + ' |') for line in table]


def split_len(seq, length):
    return [seq[i:i + length] for i in range(0, len(seq), length)]


def split_len_add_char(seq, length, char=' '):
    # split string on equal length of char list, to last list member attach <char>
    chars_to_add = length - len(seq) % length
    seq = seq + char * (chars_to_add // len(char)) + char[:chars_to_add % len(char)]
    return [seq[i:i + length] for i in range(0, len(seq), length)]


def refom_table_fixt_column(table, column_size: int):
    """
    :param table:  [('ssssssssss', 'ffff','ggggggggggg'),
                    ('ddd','eeee','hhhhhhhhhh'),('deeeeeeedd',
                    'eeeerrrrr','hhhhh')]
    :param column_size: max size of one column
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
    new_table = []
    for line in table:
        max_word = max([len(str(x)) for x in line])
        max_word += column_size - max_word % column_size
        new_line = []
        for word in line:
            new_word = split_len_add_char(str(word), column_size)
            new_word += [' ' * column_size for i in range(int(max_word / column_size - len(new_word)))] + [
                '-' * column_size]
            new_line.append(new_word)
        new_table += list(zip(*new_line))
    return new_table


"""
table = [('ssssssssss', 'ffff','ggggggggggg'),('ddd','eeee','hhhhhhhhhh'),('deeeeeeedd','eeeerrrrr','hhhhh')]
print_table(table)

print_table_as_is(refom_table_fixt_column(table, 4))
"""
