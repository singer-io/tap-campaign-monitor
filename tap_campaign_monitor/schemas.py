import os.path
import singer.utils


def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)


def load_schema_by_name(name):
    return singer.utils.load_json(
        get_abs_path('schemas/{}.json'.format(name)))
