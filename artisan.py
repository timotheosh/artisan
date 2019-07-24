#!/usr/bin/env python3
""" artisan
Usage:
    artisan <artisan_file>
    artisan --config <config_dir> <artisan_file>
    artisan (-h | --help)
    artisan --version
Options:
    <artisan_file>           Generate packer.json file and validate with packer.
    --config=<config_dir>    Directory where the main artisan configuratin files are.
    -h --help                Show this screen.
    --version                Show version.
"""

import yaml
import json
import subprocess
from os.path import exists, dirname
from docopt import docopt
import dpath


def path_ref(num):
    """ if num is a number, return an index [num] as a string, otherwise just return num."""
    if isinstance(num, int):
        num = '[{}]'.format(num)
    return num


def data_to_paths(data: dict):
    """Converts a dict data object (e.g. from yaml or json, for instance) and converts it into a list of paths, dpath
    can use."""
    paths = []
    for path_objects in dpath.path.paths(data):
        path = dpath.path.paths_only(path_objects)
        if path[-1] == True:
            paths.append('/'.join([path_ref(y) for y in path[:-1]]))
    return paths


def valid_path(data: dict, key: str):
    try:
        dpath.util.get(data, key)
        return True
    except KeyError:
        return False


def merge_data(data1, data2):
    rtn = data1.copy()
    if isinstance(rtn, dict):
        rtn.update(data2)
    elif isinstance(data1, list):
        rtn.extend(data2)
    else:
        raise Exception("Unknown data type!")
    return rtn


def filetype(file: str):
    """ Returns the file type based on the suffix of the filename."""
    suffix = file.split('.')[-1]
    if suffix == 'yml' or suffix == 'yaml':
        return 'yaml'
    elif suffix == 'json' or suffix == 'jsn':
        return 'json'
    else:
        raise Exception('Invalid filetype!')

class artisan(object):
    """Preprocessor for using packer."""
    def __init__(self, artisan_file, config_dir="conf"):
        self.packerfile = 'generate-packer.json'
        self.artisan = self._load(artisan_file)
        self.artisan_path = dirname(artisan_file)
        self.config_dir = config_dir
        self.config = self._load('{}/artisan.yml'.format(config_dir))

    def _load(self, config_file):
        suffix = filetype(config_file)
        with open(config_file, 'r') as file:
            if suffix == 'yaml':
                return yaml.safe_load(file)
            elif suffix == 'json':
                return json.load(file)
            else:
                raise Exception("Invalid file, cannot load!")

    def _get_merge_overrides(self):
        override_file = "{}/override.yml".format(self.config_dir)
        overrides = {}
        if exists(override_file):
            overrides = yaml.safe_load(open(override_file, 'r'))
        return data_to_paths(overrides)

    def _get_merge_appends(self):
        appends_file = "{}/append.yml".format(self.config_dir)
        appends = {}
        if exists(appends_file):
            appends = yaml.safe_load(open(appends_file, 'r'))
        return data_to_paths(appends)

    def _get_required(self):
        required_file = "{}/required.yml".format(self.config_dir)
        required = {}
        if exists(required_file):
            required = yaml.safe_load(open(required_file, 'r'))
        return data_to_paths(required)

    def parse(self):
        allowed_overrides = self._get_merge_overrides()
        allowed_appends = self._get_merge_appends()
        required_fields = self._get_required()
        new_data = self.config
        for required in required_fields:
            try:
                dpath.util.set(new_data, required,
                               dpath.util.get(self.artisan, required))
            except KeyError:
                raise Exception("Missing required field: {}!".format(required))
        for override in allowed_overrides:
            if valid_path(self.artisan, override):
                dpath.util.set(new_data, override,
                               dpath.util.get(self.artisan, override))
        for append in allowed_appends:
            if valid_path(self.artisan, append):
                dpath.util.set(new_data, append, merge_data(dpath.util.get(self.config, append),
                                                            dpath.util.get(self.artisan, append)))
        self.config = new_data

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
        packer = dict()
        packer['builders'] = self._compile_builders(builder)
        packer['provisioners'] = self._compile_provisioners(builder)
        packer['post-processors'] = self._compile_post_processors(builder)
        packer['variables'] = self._compile_variables(builder)
        return packer

    def _validate_packer_file(self):
        results = subprocess.run(["packer", "validate", 'deploy/{}'.format(self.packerfile)], cwd=dirname(self.artisan_path))
        if results.returncode != 0:
            raise Exception("An error occurred while validating the packer template. {}".format(results.stdout))
        else:
            print("Packer file is valid")  

    def _to_yaml(self, data):
        return yaml.dump(data)

    def _to_json(self, data):
        return json.dumps(data, indent=2)

    def to_json(self, builder):
        return self._to_json(self._compile_packer(builder))

    def write_packer(self, builder='ec2'):
        self.parse()
        with open('{}/{}'.format(self.artisan_path, self.packerfile), 'w') as f:
            f.write(self._to_json(self._compile_packer(builder)))
        self._validate_packer_file()


if __name__ == "__main__":
    arguments = docopt(__doc__, version='Artisan 0.2')
    config_dir = arguments['--config'] or "conf"
    artisan_file = arguments['<artisan_file>'] or "conf/test.yml"
    d1 = artisan(artisan_file, config_dir)
    d1.write_packer('docker')
