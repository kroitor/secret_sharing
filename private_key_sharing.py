from sympy import Symbol, invert
from functools import reduce
from operator import mul
from random import randrange, SystemRandom
from os import urandom
from argparse import ArgumentParser
import sys


class Argv(object):
    pass


random = SystemRandom()


# https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-4.pdf
prime_field = (2 ** 384) - (2 ** 128) - (2 ** 96) + (2 ** 32) - 1

SIZE = 8


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f'({hex(self.x)[2:]},\n {hex(self.y)[2:]})'


def encode_hex(key, shared_secrets: int, total_secrets: int):
    secret_integer = int(key, base=16) % prime_field
    assert shared_secrets <= total_secrets
    points = []
    # generate a random equation that is at most of degree shared_secrets - 1
    degree = shared_secrets - 1
    random_bytes = urandom(degree * 32)
    equation = []
    for i in range(0, len(random_bytes), 32):
        equation.append(int.from_bytes(random_bytes[i:i+32], 'big'))
    equation.append(secret_integer)
    for _ in range(total_secrets):
        x = randrange(0, prime_field)
        # apply the equation on each point
        y = sum(x ** (degree - i) * coefficient for i, coefficient in enumerate(equation))
        points.append(Point(x, y % prime_field))
    return [decode_point(point) for point in points]


def decode_hex(parts) -> str:
    def reduce_function(variable, xs):
        return reduce(mul, [variable - value for value in xs])
    secrets = [encode_point(part) for part in parts]
    secrets_by_x = {}
    for secret in secrets:
        assert secret.x > 0
        secrets_by_x[secret.x] = secret.y
    x_symbol = Symbol('x')
    equation = 0
    for x, y in secrets_by_x.items():
        copy = secrets_by_x.copy()
        del copy[x]
        equation = equation + reduce_function(x_symbol, copy) * invert(reduce_function(x, copy), prime_field) * y
    integer_solution = int(equation.subs(x_symbol, 0)) % prime_field
    bytes_solution = bin(integer_solution)[2:].rjust(256, '0')
    indexes = [int(bytes_solution[i:i + SIZE], base=2) for i in range(0, len(bytes_solution), SIZE)]
    return ''.join([hex(index)[2:].rjust(2, '0') for index in indexes])


def encode_point(string):
    indexes = [int(string[i:i + 2], base=16) for i,v in enumerate(string) if not i % 2]
    bytes_solution = ''.join(bin(index)[2:].rjust(SIZE, '0') for index in indexes)
    integer_solution = int(bytes_solution, base=2)
    mask = 2 ** 384 - 1
    x = integer_solution & mask
    y = integer_solution >> 384
    return Point(x, y)


def decode_point(point: Point) -> str:
    big_integer = point.x + (point.y << 384)
    padding = 384 * 2 // SIZE + 1
    bytes_solution = bin(big_integer)[2:].rjust(padding * SIZE, '0')
    indexes = [int(bytes_solution[i:i + SIZE], base=2) for i in range(0, len(bytes_solution), SIZE)]
    return ''.join([hex(i)[2:].rjust(2, '0') for i in indexes])


def print_usage():
    print('Usage:\n\tpython3 ' + sys.argv[0] + ' num_shared_keys num_total_keys key1 key2 ...\n')


if __name__ == '__main__':

    argv = Argv()
    parser = ArgumentParser()
    parser.add_argument('args', type=str, help='arguments', nargs='*')
    parser.parse_args(namespace=argv)
    args = argv.args

    if len(args) < 3:
        print_usage()
    else:
        num_shared_secrets = int(args[0])
        num_total_secrets = int(args[1])
        if len(args) == 3:
            key = args[2]
            encoded = encode_hex(key, num_shared_secrets, num_total_secrets)
            print("\n", *encoded, sep="\n")
        else:
            keys = args[2:]
            print("\n", decode_hex(keys))
