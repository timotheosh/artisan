#!/usr/bin/env python3
""" artisan
Usage:
    artisan.py <artisan_file>
    artisan.py (-h | --help)
    artisan.py --version
Options:
    <artisan_file>  Generate packer.json file and validate with packer.
    -h --help       Show this screen.
    --version       Show version.
"""

import yaml
import json
from os.path import exists, dirname
from functools import reduce
from operator import getitem
from docopt import docopt

def artisan_path(arg: str):
    return dirname(arg)

def filetype(file: str):
    suffix = file.split('.')[-1]
    if suffix == 'yml' or suffix == 'yaml':
        return 'yaml'
    elif suffix == 'json' or suffix == 'jsn':
        return 'json'
    else:
        raise Exception('Invalid filetype!')

def get_nested_item(data, keys):
    try:
        return reduce(getitem, keys, data)
    except (KeyError, IndexError):
        return None

class artisan(object):
    """Preprocessor for using packer."""
    def __init__(self, config_dir="/etc/artisan/"):
        self.config_dir = config_dir
        config_file = "{}/artisan.yml".format(self.config_dir)
        ftype = filetype(config_file)
        with open(config_file, 'r') as file:
            if ftype == 'yaml':
                self.config = yaml.safe_load(file)
            elif ftype == 'json':
                self.config = json.load(file)
            else:
                raise Exception("Invalid config file!")
        self.custom = None

    def load(self, config_file):
        suffix = filetype(config_file)
        with open(config_file, 'r') as file:
            if suffix == 'yaml':
                self.custom = yaml.safe_load(file)
            elif suffix == 'json':
                self.custom = json.load(file)
            else:
                raise Exception("Invalid custom config file!")

    def _get_merge_overrides(self):
        override_file = "{}/override.yml".format(self.config_dir)
        overrides = {}
        if exists(override_file):
            with open(override_file, 'r') as file:
                overrides = yaml.safe_load(file)
        return overrides

    def _get_merge_appends(self):
        appends_file = "{}/append.yml".format(self.config_dir)
        appends = {}
        if exists(appends_file):
            with open(appends_file, 'r') as file:
                appends = yaml.safe_load(file)
        return appends

    def merge_overrides(self):
        overrides = self._get_merge_overrides()

    def recursive_items(self, dictionary):
        for key, value in dictionary.items():
            if type(value) is dict:
                yield from self.recursive_items(value)
            else:
                yield (key, value)

    def _check_for_builders(self, builder):
        """ Checks that the configuration has an appropriate builders section. """
        if not self.config.get('builders'):
            raise Exception("No builder section in your artisan.yml!")
        elif not self.config['builders'].get(builder):
            raise Exception("No such builder '{}'!".format(builder))
        return True

    def _compile_builders(self, builder):
        if self._check_for_builders(builder):
            return self.config['builders'].get(builder)

    def _compile_provisioners(self, builder):
        rtn = []
        provisioners = self.config.get('provisioners')
        if provisioners and provisioners.get(builder):
            rtn.extend(provisioners[builder])
        return rtn

    def _compile_post_processors(self, builder):
        rtn = []
        if (self.config.get('post-processors')
                and self.config['post-processors'].get(builder)):
            rtn.extend(self.config['post-processors'].get(builder))
        return rtn

    def _compile_variables(self, builder):
        rtn = {}
        if self.config['variables'].get(builder):
            rtn.update(self.config['variables'][builder])
        return rtn

    def _compile_packer(self, builder):
        packer = {}
        packer['builders'] = self._compile_builders(builder)
        packer['provisioners'] = self._compile_provisioners(builder)
        packer['post-processors'] = self._compile_post_processors(builder)
        packer['variables'] = self._compile_variables(builder)
        return packer

    def _to_yaml(self, data):
        return yaml.dump(data)

    def _to_json(self, data):
        return json.dumps(data, indent=2)

    def to_json(self, builder):
        return self._to_json(self._compile_packer(builder))

    def write_packer(self, filepath, builder='ec2'):
        with open(filepath, 'w') as f:
            f.write(self._to_json(self._compile_packer(builder)))


if __name__ == "__main__":
    arguments = docopt(__doc__, version='Artisan 0.2')
    print(arguments)
    print(artisan_path(arguments['<artisan_file>']))
    d1 = artisan('conf/')
    d1.load('conf/test.yml')
    #print(d1.to_json("docker"))
    custom = d1.custom
    data = d1._get_merge_overrides()

    print(custom.keys())

    for key, value in d1.recursive_items(data):
        print(key, value)
        if custom.get(key):
            print(key, custom[key])
        else:
            print('MISSING KEY: {}'.format(key))
