#!/usr/bin/env python3

import os
import sys
import json
import yaml
import shutil
import tarfile

DIR_PATH = "/tmp/QQQ"


def err(code, msg):
    print(f'{code}: {msg}')
    sys.exit()


def untar_safe(path):
    try:
        untar(path)
    except tarfile.ReadError:
        err('BUNDLE_ERROR', "Can\'t open bundle tar file: {}".format(path))
    except FileNotFoundError as e:
        err('FILE_ERROR', str(e))


def untar(bundle):
    if os.path.isdir(DIR_PATH):
        err('BUNDLE_ERROR', 'bundle directory "{}" already exists'.format(DIR_PATH))
    tar = tarfile.open(bundle)
    tar.extractall(path=DIR_PATH)
    tar.close()


def get_config_files(path, bundle_hash):
    conf_list = []
    conf_types = [
        ('config.yaml', 'yaml'),
        ('config.yml', 'yaml'),
        ('config.toml', 'toml'),
        ('config.json', 'json'),
    ]
    if not os.path.isdir(path):
        return err('STACK_LOAD_ERROR', 'no directory: {}'.format(path))
    for root, _, files in os.walk(path):
        for conf_file, conf_type in conf_types:
            if conf_file in files:
                dirs = root.split('/')
                path = os.path.join('', *dirs[dirs.index(bundle_hash) + 1:])
                conf_list.append((path, root + '/' + conf_file, conf_type))
                break
    if not conf_list:
        msg = 'no config files in stack directory "{}"'
        return err('STACK_LOAD_ERROR', msg.format(path))
    return conf_list


def read_definition(conf_file, conf_type):
    parsers = {
        'yaml': yaml.safe_load,
        'json': json.load
    }
    fn = parsers[conf_type]
    if os.path.isfile(conf_file):
        with open(conf_file) as fd:
            try:
                conf = fn(fd)
            except yaml.parser.ParserError as e:
                err('STACK_LOAD_ERROR', 'YAML decode "{}" error: {}'.format(conf_file, e))
            except yaml.composer.ComposerError as e:
                err('STACK_LOAD_ERROR', 'YAML decode "{}" error: {}'.format(conf_file, e))
            except yaml.constructor.ConstructorError as e:
                err('STACK_LOAD_ERROR', 'YAML decode "{}" error: {}'.format(conf_file, e))
            except yaml.scanner.ScannerError as e:
                err('STACK_LOAD_ERROR', 'YAML decode "{}" error: {}'.format(conf_file, e))
        return conf
    return {}


def is_group(conf):
    if conf['type'] == 'group':
        return True
    return False


def check_list(name, subname, conf, res):
    if conf['type'] != 'map':
        return
    if 'default' not in conf:
        return
    for k in conf['default']:
        if not isinstance(k, str):
            res[f'{name}/{subname}'] = conf['default']


def check_config(conf_dict):
    res = {}
    if isinstance(conf_dict, dict):
        for (name, conf) in conf_dict.items():
            if 'type' in conf:
                check_list(name, '', conf, res)
            else:
                for (subname, subconf) in conf.items():
                    check_list(name, subname, subconf, res)
    else:
        for conf in conf_dict:
            name = conf['name']
            check_list(name, '', conf, res)
            if is_group(conf):
                for subconf in conf['subs']:
                    subname = subconf['name']
                    check_list(name, subname, subconf, res)
    return res


def check_obj(conf_path, conf_file, conf):
    def_type = conf['type']
    name = conf['name']
    if 'config' not in conf:
        return
    res = check_config(conf['config'])
    if res:
        print('{} {} {}'.format(def_type, name, conf_file))
        for k, v in res.items():
            print('  {}: {}'.format(k, v))


def check_bundle(fname):
    shutil.rmtree(DIR_PATH, ignore_errors=True)
    untar_safe(fname)
    for conf_path, conf_file, conf_type in get_config_files(DIR_PATH, 'QQQ'):
        conf = read_definition(conf_file, conf_type)
        if isinstance(conf, dict):
            check_obj(conf_path, conf_file, conf)
        else:
            for obj_def in conf:
                check_obj(conf_path, conf_file, obj_def)


def do():
    if len(sys.argv) < 2:
        print("\nUsage:\n{} bundle_file\n".format(os.path.basename(sys.argv[0])))
        sys.exit(4)
    else:
        check_bundle(sys.argv[1])


do()
