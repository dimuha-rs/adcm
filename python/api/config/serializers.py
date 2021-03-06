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

# pylint: disable=redefined-builtin

from rest_framework import serializers
from rest_framework.reverse import reverse

import logrotate
import cm.adcm_config
from cm.adcm_config import ui_config, restore_cluster_config
from cm.api import update_obj_config
from cm.errors import AdcmEx, AdcmApiEx
from api.api_views import get_api_url_kwargs, CommonAPIURL


class ConfigVersionURL(serializers.HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, format):
        kwargs = get_api_url_kwargs(self.context.get('object'), request)
        kwargs['version'] = obj.id
        return reverse(view_name, kwargs=kwargs, request=request, format=format)


class HistoryCurrentPreviousConfigSerializer(serializers.Serializer):
    history = CommonAPIURL(read_only=True, view_name='config-history')
    current = CommonAPIURL(read_only=True, view_name='config-current')
    previous = CommonAPIURL(read_only=True, view_name='config-previous')


class ObjectConfigSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    date = serializers.DateTimeField(read_only=True)
    description = serializers.CharField(required=False, allow_blank=True)
    config = serializers.JSONField()
    attr = serializers.JSONField(required=False)


class ObjectConfigUpdateSerializer(ObjectConfigSerializer):
    def update(self, instance, validated_data):
        try:
            conf = validated_data.get('config')
            attr = validated_data.get('attr', {})
            desc = validated_data.get('description', '')
            cl = update_obj_config(instance.obj_ref, conf, attr, desc)
            if validated_data.get('ui'):
                cl.config = ui_config(validated_data.get('obj'), cl)
            if hasattr(instance.obj_ref, 'adcm'):
                logrotate.run()
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code, e.adds) from e
        return cl


class ObjectConfigRestoreSerializer(ObjectConfigSerializer):
    config = serializers.JSONField(read_only=True)

    def update(self, instance, validated_data):
        try:
            cc = restore_cluster_config(
                instance.obj_ref,
                instance.id,
                validated_data.get('description', instance.description)
            )
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e
        return cc


class ConfigHistorySerializer(ObjectConfigSerializer):
    url = ConfigVersionURL(read_only=True, view_name='config-history-version')


class ConfigSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(required=False)
    display_name = serializers.CharField(required=False)
    subname = serializers.CharField()
    default = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    type = serializers.CharField()
    limits = serializers.JSONField(required=False)
    ui_options = serializers.JSONField(required=False)
    required = serializers.BooleanField()

    def get_default(self, obj):   # pylint: disable=arguments-differ
        return cm.adcm_config.get_default(obj)

    def get_value(self, obj):     # pylint: disable=arguments-differ
        proto = self.context.get('prototype', None)
        return cm.adcm_config.get_default(obj, proto)


class ConfigSerializerUI(ConfigSerializer):
    activatable = serializers.SerializerMethodField()

    def get_activatable(self, obj):
        return bool(cm.adcm_config.group_is_activatable(obj))
