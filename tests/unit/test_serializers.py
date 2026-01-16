"""Testes para o módulo de serializers e registro de serializers."""
import pickle
from typing import Any

import pytest

from resilient_cache.serializers import (
    CacheSerializer,
    JsonSerializer,
    PickleSerializer,
    get_serializer,
    list_serializers,
    register_serializer,
)


class TestJsonSerializer:
    """Testes para JsonSerializer."""

    def test_serialize_dict(self):
        serializer = JsonSerializer()
        data = {"a": 1, "b": "test", "c": [1, 2, 3]}
        result = serializer.serialize(data)
        assert isinstance(result, bytes)
        assert serializer.deserialize(result) == data

    def test_serialize_list(self):
        serializer = JsonSerializer()
        data = [1, 2, 3, "test"]
        result = serializer.serialize(data)
        assert serializer.deserialize(result) == data

    def test_serialize_primitives(self):
        serializer = JsonSerializer()
        for value in [42, "string", 3.14, True, None]:
            result = serializer.serialize(value)
            assert serializer.deserialize(result) == value

    def test_serialize_non_json_safe_raises_error(self):
        serializer = JsonSerializer()
        # Objects não são JSON-safe
        with pytest.raises(ValueError, match="Erro ao serializar com JSON"):
            serializer.serialize({"obj": object()})

    def test_deserialize_invalid_json_raises_error(self):
        serializer = JsonSerializer()
        with pytest.raises(ValueError, match="Erro ao desserializar com JSON"):
            serializer.deserialize(b"not valid json")

    def test_repr(self):
        serializer = JsonSerializer()
        assert repr(serializer) == "JsonSerializer()"
        assert str(serializer) == "JsonSerializer()"


class TestPickleSerializer:
    """Testes para PickleSerializer."""

    def test_serialize_dict(self):
        serializer = PickleSerializer()
        data = {"a": 1, "b": "test", "c": [1, 2, 3]}
        result = serializer.serialize(data)
        assert isinstance(result, bytes)
        assert serializer.deserialize(result) == data

    def test_serialize_complex_objects(self):
        serializer = PickleSerializer()
        # Tuplas, sets, bytes - coisas que JSON não suporta
        data = {"tuple": (1, 2, 3), "set": {1, 2, 3}, "bytes": b"binary data"}
        result = serializer.serialize(data)
        deserialized = serializer.deserialize(result)
        assert deserialized == data

    def test_serialize_nested_complex_structures(self):
        """Testa serialização de estruturas mais complexas."""
        serializer = PickleSerializer()

        # Estrutura complexa com vários tipos aninhados
        data = {
            "nested_dict": {"level1": {"level2": {"level3": "value"}}},
            "mixed_list": [1, "two", 3.0, None, True, {"key": "value"}],
            "tuple_data": (1, 2, (3, 4, (5, 6))),
            "set_data": {1, 2, 3, 4, 5},
            "frozen_set": frozenset([1, 2, 3]),
            "bytes_data": b"binary content",
        }

        result = serializer.serialize(data)
        deserialized = serializer.deserialize(result)
        assert deserialized == data
        assert isinstance(deserialized["tuple_data"], tuple)
        assert isinstance(deserialized["set_data"], set)
        assert isinstance(deserialized["bytes_data"], bytes)

    def test_serialize_non_picklable_raises_error(self):
        serializer = PickleSerializer()
        # Lambdas não são pickláveis
        with pytest.raises(ValueError, match="Erro ao serializar com pickle"):
            serializer.serialize(lambda x: x)

    def test_deserialize_invalid_pickle_raises_error(self):
        serializer = PickleSerializer()
        with pytest.raises(ValueError, match="Erro ao desserializar com pickle"):
            serializer.deserialize(b"not valid pickle data")

    def test_uses_highest_protocol(self):
        serializer = PickleSerializer()
        data = {"test": "value"}
        result = serializer.serialize(data)
        # Verifica se está usando protocolo mais recente
        # Protocolos mais altos têm bytes específicos no início
        assert result[0:2] == pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)[0:2]

    def test_repr(self):
        serializer = PickleSerializer()
        assert repr(serializer) == "PickleSerializer()"
        assert str(serializer) == "PickleSerializer()"


class TestSerializerRegistry:
    """Testes para o sistema de registro de serializers."""

    def test_list_serializers_returns_defaults(self):
        serializers = list_serializers()
        assert isinstance(serializers, list)
        assert "pickle" in serializers
        assert "json" in serializers
        assert len(serializers) >= 2

    def test_get_serializer_json(self):
        serializer = get_serializer("json")
        assert isinstance(serializer, JsonSerializer)
        assert isinstance(serializer, CacheSerializer)

    def test_get_serializer_pickle(self):
        serializer = get_serializer("pickle")
        assert isinstance(serializer, PickleSerializer)
        assert isinstance(serializer, CacheSerializer)

    def test_get_serializer_returns_new_instance_each_time(self):
        s1 = get_serializer("json")
        s2 = get_serializer("json")
        assert s1 is not s2
        assert type(s1) == type(s2)

    def test_get_serializer_unknown_raises_error(self):
        with pytest.raises(ValueError, match="Unknown serializer 'invalid'"):
            get_serializer("invalid")

    def test_get_serializer_error_shows_available_serializers(self):
        with pytest.raises(ValueError, match="Available serializers"):
            get_serializer("unknown")

    def test_register_custom_serializer(self):
        class CustomSerializer(CacheSerializer):
            def serialize(self, value: Any) -> bytes:
                return b"custom"

            def deserialize(self, data: bytes) -> Any:
                return "custom"

        # Registrar
        register_serializer("custom", CustomSerializer)

        # Verificar que foi registrado
        assert "custom" in list_serializers()

        # Obter instância
        serializer = get_serializer("custom")
        assert isinstance(serializer, CustomSerializer)
        assert serializer.serialize("anything") == b"custom"
        assert serializer.deserialize(b"anything") == "custom"

    def test_register_serializer_invalid_class_raises_error(self):
        class NotASerializer:
            pass

        with pytest.raises(TypeError, match="must be a subclass of CacheSerializer"):
            register_serializer("invalid", NotASerializer)

    def test_register_serializer_with_string_raises_error(self):
        with pytest.raises(TypeError):
            register_serializer("invalid", "not a class")  # type: ignore

    def test_register_serializer_can_override_existing(self):
        class CustomJsonSerializer(CacheSerializer):
            def serialize(self, value: Any) -> bytes:
                return b"custom_json"

            def deserialize(self, data: bytes) -> Any:
                return "custom_json"

        # Sobrescrever 'json'
        register_serializer("json", CustomJsonSerializer)

        # Verificar que foi sobrescrito
        serializer = get_serializer("json")
        assert isinstance(serializer, CustomJsonSerializer)
        assert serializer.serialize("anything") == b"custom_json"

        # Restaurar o original para não afetar outros testes
        register_serializer("json", JsonSerializer)


class TestSerializerIntegration:
    """Testes de integração entre serializers."""

    def test_json_and_pickle_produce_different_output(self):
        data = {"test": "value", "number": 42}

        json_ser = JsonSerializer()
        pickle_ser = PickleSerializer()

        json_bytes = json_ser.serialize(data)
        pickle_bytes = pickle_ser.serialize(data)

        # Devem ser diferentes
        assert json_bytes != pickle_bytes

        # Mas ambos devem deserializar corretamente
        assert json_ser.deserialize(json_bytes) == data
        assert pickle_ser.deserialize(pickle_bytes) == data

    def test_json_output_is_utf8_readable(self):
        data = {"test": "value"}
        serializer = JsonSerializer()
        result = serializer.serialize(data)

        # JSON deve ser decodificável como UTF-8
        decoded = result.decode("utf-8")
        assert "test" in decoded
        assert "value" in decoded

    def test_pickle_output_is_binary(self):
        data = {"test": "value"}
        serializer = PickleSerializer()
        result = serializer.serialize(data)

        # Pickle é binário - não deve ser UTF-8 válido
        # (ou pelo menos não deve ser human-readable)
        assert result.startswith(b"\x80")  # Pickle protocol marker

    def test_cross_serializer_incompatibility(self):
        data = {"test": "value"}

        json_ser = JsonSerializer()
        pickle_ser = PickleSerializer()

        # Serializar com JSON
        json_bytes = json_ser.serialize(data)

        # Tentar deserializar com Pickle deve falhar
        with pytest.raises(ValueError):
            pickle_ser.deserialize(json_bytes)

        # E vice-versa
        pickle_bytes = pickle_ser.serialize(data)
        with pytest.raises(ValueError):
            json_ser.deserialize(pickle_bytes)
