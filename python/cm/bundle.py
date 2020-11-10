# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import os.path
import hashlib
import tarfile
import shutil
import functools

from version_utils import rpm
from django.db import transaction
from django.db import IntegrityError

from adcm.settings import ADCM_VERSION
from cm.logger import log
import cm.config as config
import cm.stack
import cm.status_api
from cm.adcm_config import proto_ref, get_prototype_config, init_object_config, switch_config
from cm.errors import raise_AdcmEx as err
from cm.models import Cluster, Host, Upgrade, StageUpgrade, ADCM
from cm.models import Bundle, Prototype, Component, Action, SubAction, PrototypeConfig
from cm.models import StagePrototype, StageComponent, StageAction
from cm.models import StageSubAction, StagePrototypeConfig
from cm.models import PrototypeExport, PrototypeImport, StagePrototypeExport, StagePrototypeImport


STAGE = (
    StagePrototype, StageComponent, StageAction, StagePrototypeConfig,
    StageUpgrade, StagePrototypeExport, StagePrototypeImport
)


def load_bundle(bundle_file):
    log.info('loading bundle file "%s" ...', bundle_file)
    (bundle_hash, path) = process_file(bundle_file)

    try:
        check_stage()
        process_bundle(path, bundle_hash)
        bundle_proto = get_stage_bundle(bundle_file)
        second_pass()
    except:
        clear_stage()
        shutil.rmtree(path)
        raise

    try:
        bundle = copy_stage(bundle_hash, bundle_proto)
        order_versions()
        clear_stage()
        cm.status_api.post_event('create', 'bundle', bundle.id)
        return bundle
    except:
        clear_stage()
        raise


def update_bundle(bundle):
    try:
        check_stage()
        process_bundle(os.path.join(config.BUNDLE_DIR, bundle.hash), bundle.hash)
        get_stage_bundle(bundle.name)
        second_pass()
        update_bundle_from_stage(bundle)
        order_versions()
        clear_stage()
    except:
        clear_stage()
        raise


def order_model_versions(model):
    items = []
    for obj in model.objects.all():
        items.append(obj)
    ver = ""
    count = 0
    for obj in sorted(items, key=functools.cmp_to_key(
            lambda obj1, obj2: rpm.compare_versions(obj1.version, obj2.version)
    )):
        if ver != obj.version:
            count += 1
        # log.debug("MODEL %s count: %s, %s %s", model, count, obj.name, obj.version)
        obj.version_order = count
        ver = obj.version
    # Update all table in one time. That is much faster than one by one method
    model.objects.bulk_update(items, ['version_order'])


def order_versions():
    order_model_versions(Prototype)
    order_model_versions(Bundle)


def process_file(bundle_file):
    path = os.path.join(config.DOWNLOAD_DIR, bundle_file)
    bundle_hash = get_hash_safe(path)
    dir_path = untar_safe(bundle_hash, path)
    return (bundle_hash, dir_path)


def untar_safe(bundle_hash, path):
    try:
        dir_path = untar(bundle_hash, path)
    except tarfile.ReadError:
        err('BUNDLE_ERROR', "Can\'t open bundle tar file: {}".format(path))
    return dir_path


def untar(bundle_hash, bundle):
    path = os.path.join(config.BUNDLE_DIR, bundle_hash)
    if os.path.isdir(path):
        err('BUNDLE_ERROR', 'bundle directory "{}" already exists'.format(path))
    tar = tarfile.open(bundle)
    tar.extractall(path=path)
    tar.close()
    return path


def get_hash_safe(path):
    try:
        bundle_hash = get_hash(path)
    except FileNotFoundError:
        err('BUNDLE_ERROR', "Can\'t find bundle file: {}".format(path))
    except PermissionError:
        err('BUNDLE_ERROR', "Can\'t open bundle file: {}".format(path))
    return bundle_hash


def get_hash(bundle_file):
    sha1 = hashlib.sha1()
    with open(bundle_file, 'rb') as fp:
        for data in iter(lambda: fp.read(16384), b''):
            sha1.update(data)
    return sha1.hexdigest()


def load_adcm():
    check_stage()
    adcm_file = os.path.join(config.BASE_DIR, 'conf', 'adcm', 'config.yaml')
    conf = cm.stack.read_definition(adcm_file, 'yaml')
    if not conf:
        log.warning('Empty adcm config (%s)', adcm_file)
        return
    try:
        cm.stack.save_definition('', adcm_file, conf, {}, 'adcm', True)
        process_adcm()
    except:
        clear_stage()
        raise
    clear_stage()


def process_adcm():
    sp = StagePrototype.objects.get(type='adcm')
    adcm = ADCM.objects.filter()
    if adcm:
        old_proto = adcm[0].prototype
        new_proto = sp
        if old_proto.version == new_proto.version:
            log.debug('adcm vesrion %s, skip upgrade', old_proto.version)
        elif rpm.compare_versions(old_proto.version, new_proto.version) < 0:
            bundle = copy_stage('adcm', sp)
            upgrade_adcm(adcm[0], bundle)
        else:
            msg = 'Current adcm version {} is more than or equal to upgrade version {}'
            err('UPGRADE_ERROR', msg.format(old_proto.version, new_proto.version))
    else:
        bundle = copy_stage('adcm', sp)
        init_adcm(bundle)


def init_adcm(bundle):
    proto = Prototype.objects.get(type='adcm', bundle=bundle)
    spec, _, conf, attr = get_prototype_config(proto)
    with transaction.atomic():
        obj_conf = init_object_config(spec, conf, attr)
        adcm = ADCM(prototype=proto, name='ADCM', config=obj_conf)
        adcm.save()
    log.info('init adcm object version %s OK', proto.version)
    return adcm


def upgrade_adcm(adcm, bundle):
    old_proto = adcm.prototype
    new_proto = Prototype.objects.get(type='adcm', bundle=bundle)
    if rpm.compare_versions(old_proto.version, new_proto.version) >= 0:
        msg = 'Current adcm version {} is more than or equal to upgrade version {}'
        err('UPGRADE_ERROR', msg.format(old_proto.version, new_proto.version))
    with transaction.atomic():
        adcm.prototype = new_proto
        adcm.save()
        switch_config(adcm, new_proto, old_proto)
    log.info('upgrade adcm OK from version %s to %s', old_proto.version, adcm.prototype.version)
    return adcm


def process_bundle(path, bundle_hash):
    obj_list = {}
    for conf_path, conf_file, conf_type in cm.stack.get_config_files(path, bundle_hash):
        conf = cm.stack.read_definition(conf_file, conf_type)
        if conf:
            cm.stack.save_definition(conf_path, conf_file, conf, obj_list, bundle_hash)


def check_stage():
    def count(model):
        if model.objects.all().count():
            err('BUNDLE_ERROR', 'Stage is not empty {}'.format(model))
    for model in STAGE:
        count(model)


def copy_obj(orig, clone, fields):
    obj = clone()
    for f in fields:
        setattr(obj, f, getattr(orig, f))
    return obj


def update_obj(dest, source, fields):
    for f in fields:
        setattr(dest, f, getattr(source, f))


def re_check_actions():
    for act in StageAction.objects.all():
        if not act.hostcomponentmap:
            continue
        hc = act.hostcomponentmap
        ref = 'in hc_acl of action "{}" of {}'.format(act.name, proto_ref(act.prototype))
        for item in hc:
            sp = StagePrototype.objects.filter(type='service', name=item['service'])
            if not sp:
                msg = 'Unknown service "{}" {}'
                err('INVALID_ACTION_DEFINITION', msg.format(item['service'], ref))
            if not StageComponent.objects.filter(prototype=sp[0], name=item['component']):
                msg = 'Unknown component "{}" of service "{}" {}'
                err('INVALID_ACTION_DEFINITION', msg.format(item['component'], sp[0].name, ref))


def re_check_components():
    for comp in StageComponent.objects.all():
        if not comp.requires:
            continue
        ref = 'in requires of component "{}" of {}'.format(comp.name, proto_ref(comp.prototype))
        req_list = comp.requires
        for i, item in enumerate(req_list):
            if 'service' in item:
                try:
                    service = StagePrototype.objects.get(name=item['service'], type='service')
                except StagePrototype.DoesNotExist:
                    msg = 'Unknown service "{}" {}'
                    err('COMPONENT_CONSTRAINT_ERROR', msg.format(item['service'], ref))
            else:
                service = comp.prototype
                req_list[i]['service'] = comp.prototype.name
            try:
                req_comp = StageComponent.objects.get(name=item['component'], prototype=service)
            except StageComponent.DoesNotExist:
                msg = 'Unknown component "{}" {}'
                err('COMPONENT_CONSTRAINT_ERROR', msg.format(item['component'], ref))
            if comp == req_comp:
                msg = 'Component can not require themself {}'
                err('COMPONENT_CONSTRAINT_ERROR', msg.format(ref))
        comp.requires = req_list
        comp.save()


def re_check_config():
    for c in StagePrototypeConfig.objects.filter(type='variant'):
        ref = proto_ref(c.prototype)
        if c.limits['source']['type'] != 'list':
            continue
        keys = c.limits['source']['name'].split('/')
        name = keys[0]
        subname = ''
        if len(keys) > 1:
            subname = keys[1]
        try:
            s = StagePrototypeConfig.objects.get(prototype=c.prototype, name=name, subname=subname)
        except StagePrototypeConfig.DoesNotExist:
            msg = f'Unknown config source name "{{}}" for {ref} config "{c.name}/{c.subname}"'
            err('INVALID_CONFIG_DEFINITION', msg.format(c.limits['source']['name']))
        if s == c:
            msg = f'Config parameter "{c.name}/{c.subname}" can not refer to itself ({ref})'
            err('INVALID_CONFIG_DEFINITION', msg)


def second_pass():
    re_check_actions()
    re_check_components()
    re_check_config()


def copy_stage_prototype(stage_prototypes, bundle):
    prototypes = []  # Map for stage prototype id: new prototype
    for sp in stage_prototypes:
        p = copy_obj(sp, Prototype, (
            'type', 'path', 'name', 'version', 'required', 'shared', 'monitoring',
            'display_name', 'description', 'adcm_min_version'
        ))
        p.bundle = bundle
        prototypes.append(p)
    Prototype.objects.bulk_create(prototypes)


def copy_stage_upgrade(stage_upgrades, bundle):
    upgrades = []
    for su in stage_upgrades:
        upg = copy_obj(su, Upgrade, (
            'name', 'description', 'min_version', 'max_version', 'min_strict', 'max_strict',
            'state_available', 'state_on_success', 'from_edition',
        ))
        upg.bundle = bundle
        upgrades.append(upg)
    Upgrade.objects.bulk_create(upgrades)


def prepare_bulk(origin_objects, Target, prototype, fields):
    target_objects = []
    for oo in origin_objects:
        to = copy_obj(oo, Target, fields)
        to.prototype = prototype
        target_objects.append(to)
    return target_objects


def copy_stage_actons(stage_actions, prototype):
    actions = prepare_bulk(
        stage_actions,
        Action,
        prototype,
        ('name', 'type', 'script', 'script_type', 'state_on_success',
         'state_on_fail', 'state_available', 'params', 'log_files',
         'hostcomponentmap', 'button', 'display_name', 'description', 'ui_options',
         'allow_to_terminate', 'partial_execution')
    )
    Action.objects.bulk_create(actions)


def copy_stage_sub_actons(bundle):
    sub_actions = []
    for ssubaction in StageSubAction.objects.all():
        action = Action.objects.get(
            prototype__bundle=bundle,
            prototype__type=ssubaction.action.prototype.type,
            prototype__name=ssubaction.action.prototype.name,
            prototype__version=ssubaction.action.prototype.version,
            name=ssubaction.action.name
        )
        sub = copy_obj(ssubaction, SubAction, (
            'name', 'display_name', 'script', 'script_type', 'state_on_fail', 'params'
        ))
        sub.action = action
        sub_actions.append(sub)
    SubAction.objects.bulk_create(sub_actions)


def copy_stage_component(stage_components, prototype):
    components = prepare_bulk(
        stage_components,
        Component,
        prototype,
        ('name', 'display_name', 'description', 'params', 'monitoring', 'requires', 'constraint')
    )
    Component.objects.bulk_create(components)


def copy_stage_import(stage_imports, prototype):
    imports = prepare_bulk(
        stage_imports, PrototypeImport, prototype, (
            'name', 'min_version', 'max_version', 'min_strict', 'max_strict',
            'default', 'required', 'multibind'
        )
    )
    PrototypeImport.objects.bulk_create(imports)


def copy_stage_config(stage_config, prototype):
    target_config = []
    for sc in stage_config:
        c = copy_obj(sc, PrototypeConfig, (
            'name', 'subname', 'default', 'type', 'description',
            'display_name', 'limits', 'required', 'ui_options'
        ))
        if sc.action:
            c.action = Action.objects.get(prototype=prototype, name=sc.action.name)
        c.prototype = prototype
        target_config.append(c)
    PrototypeConfig.objects.bulk_create(target_config)


def check_license(bundle):
    b = Bundle.objects.filter(license_hash=bundle.license_hash, license='accepted')
    if not b:
        return False
    return True


def copy_stage(bundle_hash, bundle_proto):
    bundle = copy_obj(bundle_proto, Bundle, (
        'name', 'version', 'edition', 'license_path', 'license_hash', 'description'
    ))
    bundle.hash = bundle_hash
    check_license(bundle)
    if bundle.license_path:
        bundle.license = 'unaccepted'
        if check_license(bundle):
            bundle.license = 'accepted'
    try:
        bundle.save()
    except IntegrityError:
        msg = 'Bundle "{}" {} already installed'
        err('BUNDLE_ERROR', msg.format(bundle_proto.name, bundle_proto.version))

    stage_prototypes = StagePrototype.objects.all()
    copy_stage_prototype(stage_prototypes, bundle)

    for sp in stage_prototypes:
        p = Prototype.objects.get(name=sp.name, type=sp.type, bundle=bundle)
        copy_stage_actons(StageAction.objects.filter(prototype=sp), p)
        copy_stage_config(StagePrototypeConfig.objects.filter(prototype=sp), p)
        copy_stage_component(StageComponent.objects.filter(prototype=sp), p)
        for se in StagePrototypeExport.objects.filter(prototype=sp):
            pe = PrototypeExport(prototype=p, name=se.name)
            pe.save()
        copy_stage_import(StagePrototypeImport.objects.filter(prototype=sp), p)

    copy_stage_sub_actons(bundle)
    copy_stage_upgrade(StageUpgrade.objects.all(), bundle)
    return bundle


def update_bundle_from_stage(bundle):   # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    for sp in StagePrototype.objects.all():
        try:
            p = Prototype.objects.get(bundle=bundle, type=sp.type, name=sp.name, version=sp.version)
            p.path = sp.path
            p.version = sp.version
            p.description = sp.description
            p.display_name = sp.display_name
            p.required = sp.required
            p.shared = sp.shared
            p.monitoring = sp.monitoring
            p.adcm_min_version = sp.adcm_min_version
        except Prototype.DoesNotExist:
            p = copy_obj(sp, Prototype, (
                'type', 'path', 'name', 'version', 'required', 'shared', 'monitoring',
                'display_name', 'description', 'adcm_min_version'
            ))
            p.bundle = bundle
        p.save()
        for scomp in StageComponent.objects.filter(prototype=sp):
            try:
                comp = Component.objects.get(prototype=p, name=scomp.name)
                update_obj(comp, scomp, (
                    'display_name', 'description', 'params', 'monitoring', 'requires', 'constraint'
                ))
            except Component.DoesNotExist:
                comp = copy_obj(scomp, Component, (
                    'name', 'display_name', 'description', 'params', 'requires', 'constraint'
                ))
                comp.prototype = p
            comp.save()
        for saction in StageAction.objects.filter(prototype=sp):
            try:
                action = Action.objects.get(prototype=p, name=saction.name)
                update_obj(action, saction, (
                    'type', 'script', 'script_type', 'state_on_success',
                    'state_on_fail', 'state_available', 'params', 'log_files',
                    'hostcomponentmap', 'button', 'display_name', 'description', 'ui_options',
                    'allow_to_terminate', 'partial_execution'
                ))
            except Action.DoesNotExist:
                action = copy_obj(saction, Action, (
                    'name', 'type', 'script', 'script_type', 'state_on_success',
                    'state_on_fail', 'state_available', 'params', 'log_files',
                    'hostcomponentmap', 'button', 'display_name', 'description', 'ui_options',
                    'allow_to_terminate', 'partial_execution'
                ))
                action.prototype = p
            action.save()
            SubAction.objects.filter(action=action).delete()
            for ssubaction in StageSubAction.objects.filter(action=saction):
                sub = copy_obj(ssubaction, SubAction, (
                    'script', 'script_type', 'state_on_fail', 'params'
                ))
                sub.action = action
                sub.save()
        for sc in StagePrototypeConfig.objects.filter(prototype=sp):
            flist = (
                'default', 'type', 'description', 'display_name', 'limits', 'required', 'ui_options'
            )
            act = None
            if sc.action:
                act = Action.objects.get(prototype=p, name=sc.action.name)
            try:
                pconfig = PrototypeConfig.objects.get(
                    prototype=p, action=act, name=sc.name, subname=sc.subname
                )
                update_obj(pconfig, sc, flist)
            except PrototypeConfig.DoesNotExist:
                pconfig = copy_obj(sc, PrototypeConfig, ('name', 'subname') + flist)
                pconfig.action = act
                pconfig.prototype = p
            pconfig.save()

        PrototypeExport.objects.filter(prototype=p).delete()
        for se in StagePrototypeExport.objects.filter(prototype=sp):
            pe = PrototypeExport(prototype=p, name=se.name)
            pe.save()
        PrototypeImport.objects.filter(prototype=p).delete()
        for si in StagePrototypeImport.objects.filter(prototype=sp):
            pi = copy_obj(si, PrototypeImport, (
                'name', 'min_version', 'max_version', 'min_strict', 'max_strict',
                'default', 'required', 'multibind'
            ))
            pi.prototype = p
            pi.save()

    Upgrade.objects.filter(bundle=bundle).delete()
    for su in StageUpgrade.objects.all():
        upg = copy_obj(su, Upgrade, (
            'name', 'description', 'min_version', 'max_version', 'min_strict', 'max_strict',
            'state_available', 'state_on_success', 'from_edition'
        ))
        upg.bundle = bundle
        upg.save()


def clear_stage():
    for model in STAGE:
        model.objects.all().delete()


def delete_bundle(bundle):
    hosts = Host.objects.filter(prototype__bundle=bundle)
    if hosts:
        h = hosts[0]
        msg = 'There is host #{} "{}" of bundle #{} "{}" {}'
        err('BUNDLE_CONFLICT', msg.format(h.id, h.fqdn, bundle.id, bundle.name, bundle.version))
    clusters = Cluster.objects.filter(prototype__bundle=bundle)
    if clusters:
        cl = clusters[0]
        msg = 'There is cluster #{} "{}" of bundle #{} "{}" {}'
        err('BUNDLE_CONFLICT', msg.format(cl.id, cl.name, bundle.id, bundle.name, bundle.version))
    adcm = ADCM.objects.filter(prototype__bundle=bundle)
    if adcm:
        msg = 'There is adcm object of bundle #{} "{}" {}'
        err('BUNDLE_CONFLICT', msg.format(bundle.id, bundle.name, bundle.version))
    if bundle.hash != 'adcm':
        shutil.rmtree(os.path.join(config.BUNDLE_DIR, bundle.hash))
    bundle_id = bundle.id
    bundle.delete()
    cm.status_api.post_event('delete', 'bundle', bundle_id)


def check_services():
    s = {}
    for p in StagePrototype.objects.filter(type='service'):
        if p.name in s:
            msg = 'There are more than one service with name {}'
            err('BUNDLE_ERROR', msg.format(p.name))
        s[p.name] = p.version


def check_adcm_version(bundle):
    if not bundle.adcm_min_version:
        return
    if rpm.compare_versions(bundle.adcm_min_version, ADCM_VERSION) > 0:
        msg = 'This bundle required ADCM version equal to {} or newer.'
        err('BUNDLE_VERSION_ERROR', msg.format(bundle.adcm_min_version))


def get_stage_bundle(bundle_file):
    clusters = StagePrototype.objects.filter(type='cluster')
    providers = StagePrototype.objects.filter(type='provider')
    if clusters:
        if len(clusters) > 1:
            msg = 'There are more than one ({}) cluster definition in bundle "{}"'
            err('BUNDLE_ERROR', msg.format(len(clusters), bundle_file))
        if providers:
            msg = 'There are {} host provider definition in cluster type bundle "{}"'
            err('BUNDLE_ERROR', msg.format(len(providers), bundle_file))
        hosts = StagePrototype.objects.filter(type='host')
        if hosts:
            msg = 'There are {} host definition in cluster type bundle "{}"'
            err('BUNDLE_ERROR', msg.format(len(hosts), bundle_file))
        check_services()
        bundle = clusters[0]
    elif providers:
        if len(providers) > 1:
            msg = 'There are more than one ({}) host provider definition in bundle "{}"'
            err('BUNDLE_ERROR', msg.format(len(providers), bundle_file))
        services = StagePrototype.objects.filter(type='service')
        if services:
            msg = 'There are {} service definition in host provider type bundle "{}"'
            err('BUNDLE_ERROR', msg.format(len(services), bundle_file))
        hosts = StagePrototype.objects.filter(type='host')
        if not hosts:
            msg = 'There isn\'t any host definition in host provider type bundle "{}"'
            err('BUNDLE_ERROR', msg.format(bundle_file))
        bundle = providers[0]
    else:
        msg = 'There isn\'t any cluster or host provider definition in bundle "{}"'
        err('BUNDLE_ERROR', msg.format(bundle_file))
    check_adcm_version(bundle)
    return bundle
