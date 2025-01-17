# coding=utf-8
"""
    @project: maxkb
    @Author：虎
    @file： provider_serializers.py
    @date：2023/11/2 14:01
    @desc:
"""
import json
import uuid
from typing import Dict

from django.db.models import QuerySet
from rest_framework import serializers

from application.models import Application
from common.exception.app_exception import AppApiException
from common.util.field_message import ErrMessage
from common.util.rsa_util import encrypt, decrypt
from setting.models.model_management import Model
from setting.models_provider.constants.model_provider_constants import ModelProvideConstants


class ModelSerializer(serializers.Serializer):
    class Query(serializers.Serializer):
        user_id = serializers.UUIDField(required=True, error_messages=ErrMessage.uuid("用户id"))

        name = serializers.CharField(required=False, max_length=20,
                                     error_messages=ErrMessage.char("模型名称"))

        model_type = serializers.CharField(required=False, error_messages=ErrMessage.char("模型类型"))

        model_name = serializers.CharField(required=False, error_messages=ErrMessage.char("基础模型"))

        provider = serializers.CharField(required=False, error_messages=ErrMessage.char("供应商"))

        def list(self, with_valid):
            if with_valid:
                self.is_valid(raise_exception=True)
            user_id = self.data.get('user_id')
            name = self.data.get('name')
            model_query_set = QuerySet(Model).filter(user_id=user_id)
            query_params = {}
            if name is not None:
                query_params['name__contains'] = name
            if self.data.get('model_type') is not None:
                query_params['model_type'] = self.data.get('model_type')
            if self.data.get('model_name') is not None:
                query_params['model_name'] = self.data.get('model_name')
            if self.data.get('provider') is not None:
                query_params['provider'] = self.data.get('provider')

            return [ModelSerializer.model_to_dict(model) for model in model_query_set.filter(**query_params)]

    class Edit(serializers.Serializer):
        user_id = serializers.CharField(required=False, error_messages=ErrMessage.uuid("用户id"))

        name = serializers.CharField(required=False, max_length=20,
                                     error_messages=ErrMessage.char("模型名称"))

        model_type = serializers.CharField(required=False, error_messages=ErrMessage.char("模型类型"))

        model_name = serializers.CharField(required=False, error_messages=ErrMessage.char("模型类型"))

        credential = serializers.DictField(required=False, error_messages=ErrMessage.dict("认证信息"))

        def is_valid(self, model=None, raise_exception=False):
            super().is_valid(raise_exception=True)
            filter_params = {'user_id': self.data.get('user_id')}
            if 'name' in self.data and self.data.get('name') is not None:
                filter_params['name'] = self.data.get('name')
                if QuerySet(Model).exclude(id=model.id).filter(**filter_params).exists():
                    raise AppApiException(500, f'模型名称【{self.data.get("name")}】已存在')

            ModelSerializer.model_to_dict(model)

            provider = model.provider
            model_type = self.data.get('model_type')
            model_name = self.data.get(
                'model_name')
            credential = self.data.get('credential')

            model_credential = ModelProvideConstants[provider].value.get_model_credential(model_type,
                                                                                          model_name)
            source_model_credential = json.loads(decrypt(model.credential))
            source_encryption_model_credential = model_credential.encryption_dict(source_model_credential)
            if credential is not None:
                for k in source_encryption_model_credential.keys():
                    if credential[k] == source_encryption_model_credential[k]:
                        credential[k] = source_model_credential[k]
                        # 校验模型认证数据
                model_credential.is_valid(
                    model_type,
                    model_name,
                    credential,
                    raise_exception=True)
            return credential

    class Create(serializers.Serializer):
        user_id = serializers.CharField(required=True, error_messages=ErrMessage.uuid("用户id"))

        name = serializers.CharField(required=True, max_length=20, error_messages=ErrMessage.char("模型名称"))

        provider = serializers.CharField(required=True, error_messages=ErrMessage.char("供应商"))

        model_type = serializers.CharField(required=True, error_messages=ErrMessage.char("模型类型"))

        model_name = serializers.CharField(required=True, error_messages=ErrMessage.char("基础模型"))

        credential = serializers.DictField(required=True, error_messages=ErrMessage.dict("认证信息"))

        def is_valid(self, *, raise_exception=False):
            super().is_valid(raise_exception=True)
            if QuerySet(Model).filter(user_id=self.data.get('user_id'),
                                      name=self.data.get('name')).exists():
                raise AppApiException(500, f'模型名称【{self.data.get("name")}】已存在')
            # 校验模型认证数据
            ModelProvideConstants[self.data.get('provider')].value.get_model_credential(self.data.get('model_type'),
                                                                                        self.data.get(
                                                                                            'model_name')).is_valid(
                self.data.get('model_type'),
                self.data.get('model_name'),
                self.data.get('credential'),
                raise_exception=True)

        def insert(self, user_id, with_valid=False):
            if with_valid:
                self.is_valid(raise_exception=True)
            credential = self.data.get('credential')
            name = self.data.get('name')
            provider = self.data.get('provider')
            model_type = self.data.get('model_type')
            model_name = self.data.get('model_name')
            model_credential_str = json.dumps(credential)
            model = Model(id=uuid.uuid1(), user_id=user_id, name=name,
                          credential=encrypt(model_credential_str),
                          provider=provider, model_type=model_type, model_name=model_name)
            model.save()
            return ModelSerializer.Operate(data={'id': model.id, 'user_id': user_id}).one(with_valid=True)

    @staticmethod
    def model_to_dict(model: Model):
        credential = json.loads(decrypt(model.credential))
        return {'id': str(model.id), 'provider': model.provider, 'name': model.name, 'model_type': model.model_type,
                'model_name': model.model_name,
                'credential': ModelProvideConstants[model.provider].value.get_model_credential(model.model_type,
                                                                                               model.model_name).encryption_dict(
                    credential)}

    class Operate(serializers.Serializer):
        id = serializers.UUIDField(required=True, error_messages=ErrMessage.uuid("模型id"))

        user_id = serializers.UUIDField(required=True, error_messages=ErrMessage.uuid("用户id"))

        def is_valid(self, *, raise_exception=False):
            super().is_valid(raise_exception=True)
            model = QuerySet(Model).filter(id=self.data.get("id"), user_id=self.data.get("user_id")).first()
            if model is None:
                raise AppApiException(500, '模型不存在')

        def one(self, with_valid=False):
            if with_valid:
                self.is_valid(raise_exception=True)
            model = QuerySet(Model).get(id=self.data.get('id'), user_id=self.data.get('user_id'))
            return ModelSerializer.model_to_dict(model)

        def delete(self, with_valid=True):
            if with_valid:
                self.is_valid(raise_exception=True)
            application_list = QuerySet(Application).filter(model_id=self.data.get('id')).all()
            if len(application_list) > 0:
                raise AppApiException(500, f"该模型关联了{len(application_list)} 个应用，无法删除该模型。")
            QuerySet(Model).filter(id=self.data.get('id')).delete()
            return True

        def edit(self, instance: Dict, user_id: str, with_valid=True):
            if with_valid:
                self.is_valid(raise_exception=True)
            model = QuerySet(Model).filter(id=self.data.get('id')).first()

            if model is None:
                raise AppApiException(500, '不存在的id')
            else:
                credential = ModelSerializer.Edit(data={**instance, 'user_id': user_id}).is_valid(model=model)
                update_keys = ['credential', 'name', 'model_type', 'model_name']
                for update_key in update_keys:
                    if update_key in instance and instance.get(update_key) is not None:
                        if update_key == 'credential':
                            model_credential_str = json.dumps(credential)
                            model.__setattr__(update_key, encrypt(model_credential_str))
                        else:
                            model.__setattr__(update_key, instance.get(update_key))
            model.save()
            return self.one(with_valid=False)


class ProviderSerializer(serializers.Serializer):
    provider = serializers.CharField(required=True, error_messages=ErrMessage.char("供应商"))

    method = serializers.CharField(required=True, error_messages=ErrMessage.char("执行函数名称"))

    def exec(self, exec_params: Dict[str, object], with_valid=False):
        if with_valid:
            self.is_valid(raise_exception=True)

        provider = self.data.get('provider')
        method = self.data.get('method')
        return getattr(ModelProvideConstants[provider].value, method)(exec_params)
