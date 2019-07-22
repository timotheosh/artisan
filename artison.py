#!/usr/bin/env python3

import yaml
import json


def filetype(file: str):
    suffix = file.split('.')[-1]
    if suffix == 'yml' or suffix == 'yaml':
        return 'yaml'
    elif suffix == 'json' or suffix == 'jsn':
        return 'json'
    else:
        raise Exception('Invalid filetype!')

class artisan(object):
    """Preprocessor for using packer."""
    def __init__(self, artisan_file=None,
                 config_file="/etc/artisan/artisan.yml"):
        print(config_file)
        self.config = None
        self.data = None
        ftype = filetype(config_file)
        with open(config_file, 'r') as file:
            if ftype == 'yaml':
                self.config = yaml.safe_load(file)
            elif ftype == 'json':
                self.config = json.load(file)
            else:
                "Invalid config file!"
        if artisan_file:
            with open(artisan_file, 'r') as file:
                self.data = yaml.safe_load(file)
        self.packer_file = None

    def load_packer_file(self, filepath):
        with open(filepath, 'r') as f:
            self.packer_file = json.load(f)

    def _compile_builders(self, builder):
        if not self.config.get('builders'):
            raise Exception("No builder section in your artisan.yml!")
        rtn = self.config['builders'].get(builder)
        if not rtn:
            raise Exception("No such builder '{}'!".format(builder))
        return rtn

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

    def write_packer(self, filepath, builder='ec2'):
        with open(filepath, 'w') as f:
            f.write(self._to_json(self._compile_packer(builder)))


if __name__ == "__main__":
    d1 = artisan(None, 'conf/artisan.yml')
    d1._to_json()
