"""Semantically identical guards with distinct line maps, all paths executed."""
from contextlib import nullcontext


def compact(value):
    with nullcontext():
        if value:raise ValueError('authored')
        return True


def expanded(value):
    with nullcontext():
        if value:
            raise ValueError('authored')
        return True


if __name__ == '__main__':
    for function in [compact,expanded]:
        assert function(False) is True
        try:
            function(True)
        except ValueError as error:
            assert str(error) == 'authored'
        else:
            raise AssertionError('Both guard paths must be executed.')
