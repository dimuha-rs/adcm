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
import allure
import coreapi
import pytest
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.docker_utils import DockerWrapper

# pylint: disable=W0611, W0621
from tests.library import steps
from tests.library.errorcodes import TASK_ERROR, UPGRADE_ERROR
from tests.library.utils import get_action_by_name, wait_until


@pytest.fixture()
def adcm(image, request, adcm_credentials):
    repo, tag = image
    dw = DockerWrapper()
    adcm = dw.run_adcm(image=repo, tag=tag, pull=False)
    adcm.api.auth(**adcm_credentials)
    yield adcm
    adcm.stop()


@pytest.fixture()
def client(adcm):
    return adcm.api.objects


def test_action_shouldnt_be_run_while_cluster_has_an_issue(client):
    with allure.step('Create default cluster and get id'):
        bundle = utils.get_data_dir(__file__, "cluster")
        steps.upload_bundle(client, bundle)
        cluster_id = steps.create_cluster(client)['id']
    with allure.step(f'Run action with error for cluster {cluster_id}'):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            client.cluster.action.run.create(
                cluster_id=cluster_id,
                action_id=client.cluster.action.list(cluster_id=cluster_id)[0]['id'])
    with allure.step('Check if cluster action has issues'):
        TASK_ERROR.equal(e, 'action has issues')


def test_action_shouldnt_be_run_while_host_has_an_issue(client):
    with allure.step('Create default host and get id'):
        bundle = utils.get_data_dir(__file__, "host")
        steps.upload_bundle(client, bundle)
        provider_id = steps.create_hostprovider(client)['id']
        host_id = client.host.create(prototype_id=client.stack.host.list()[0]['id'],
                                     provider_id=provider_id,
                                     fqdn=utils.random_string())['id']
    with allure.step(f'Run action with error for host {host_id}'):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            client.host.action.run.create(
                host_id=host_id,
                action_id=client.host.action.list(host_id=host_id)[0]['id'])
    with allure.step('Check if host action has issues'):
        TASK_ERROR.equal(e, 'action has issues')


def test_action_shouldnt_be_run_while_hostprovider_has_an_issue(client):
    with allure.step('Create default hostprovider and get id'):
        bundle = utils.get_data_dir(__file__, "provider")
        steps.upload_bundle(client, bundle)
        provider_id = steps.create_hostprovider(client)['id']
    with allure.step(f'Run action with error for provider {provider_id}'):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            client.provider.action.run.create(
                provider_id=provider_id,
                action_id=client.provider.action.list(provider_id=provider_id)[0]['id'])
    with allure.step('Check if provider action has issues'):
        TASK_ERROR.equal(e, 'action has issues')


def test_when_cluster_has_issue_than_upgrade_locked(client):
    with allure.step('Create cluster and upload new one bundle'):
        bundledir = utils.get_data_dir(__file__, "cluster")
        upgrade_bundle = utils.get_data_dir(__file__, "upgrade", "cluster")
        steps.upload_bundle(client, bundledir)
        cluster = steps.create_cluster(client)
        steps.upload_bundle(client, upgrade_bundle)
    with allure.step('Upgrade cluster'):
        upgrade_list = client.cluster.upgrade.list(cluster_id=cluster['id'])
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            client.cluster.upgrade.do.create(
                cluster_id=cluster['id'],
                upgrade_id=upgrade_list[0]['id'])
    with allure.step('Check if cluster has issues'):
        UPGRADE_ERROR.equal(e, 'cluster ', ' has issue: ')


def test_when_hostprovider_has_issue_than_upgrade_locked(client):
    with allure.step('Create hostprovider'):
        bundledir = utils.get_data_dir(__file__, "provider")
        upgrade_bundle = utils.get_data_dir(__file__, "upgrade", "provider")
        steps.upload_bundle(client, bundledir)
        provider_id = steps.create_hostprovider(client)['id']
        steps.upload_bundle(client, upgrade_bundle)
    with allure.step('Upgrade provider'):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            client.provider.upgrade.do.create(
                provider_id=provider_id,
                upgrade_id=client.provider.upgrade.list(provider_id=provider_id)[0]['id'])
    with allure.step('Check if upgrade locked'):
        UPGRADE_ERROR.equal(e)


@allure.link('https://jira.arenadata.io/browse/ADCM-487')
def test_when_component_hasnt_constraint_then_cluster_doesnt_have_issues(client):
    with allure.step('Create cluster (component hasnt constraint)'):
        bundledir = utils.get_data_dir(__file__, "cluster_component_hasnt_constraint")
        steps.upload_bundle(client, bundledir)
        cluster = steps.create_cluster(client)
    with allure.step('Create service'):
        steps.create_random_service(client, cluster['id'])
    with allure.step('Run action: lock cluster'):
        action = get_action_by_name(client, cluster, 'lock-cluster')
        wait_until(
            client,
            task=client.cluster.action.run.create(cluster_id=cluster['id'], action_id=action['id'])
        )
    with allure.step('Check if state is always-locked'):
        assert client.cluster.read(cluster_id=cluster['id'])['state'] == 'always-locked'
