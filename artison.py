#!/usr/bin/env python3

import yaml
import json

class artisan(object):
    """DSL for using packer."""
    def __init__(self, artisan_file = None, config_file="/etc/artisan/artisan.yml"):
        self.config = None
        self.data = None
        with open(config_file, 'r') as file:
            self.config = yaml.safe_load(file)
        if artisan_file:
            with open(artisan_file, 'r') as file:
                self.data = yaml.safe_load(file)

    def _to_json(self, data):
        return json.dumps(data)
