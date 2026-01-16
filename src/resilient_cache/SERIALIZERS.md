# Serializers e Registry System

Este documento explica o sistema de serialização do resilient-cache e como usar o registro de serializers para adicionar suas próprias estratégias de serialização.

## Visão Geral

O resilient-cache usa serializers para converter objetos Python em bytes antes de armazená-los no cache L2 (Redis/Valkey). Por padrão, dois serializers estão disponíveis:

- **PickleSerializer**: Serializa usando o módulo `pickle` do Python (suporta qualquer objeto Python)
- **JsonSerializer**: Serializa usando JSON (apenas tipos JSON-safe: dict, list, str, int, float, bool, None)

## Serializers Padrão

### PickleSerializer

Usa o protocolo pickle do Python para serialização. Suporta praticamente qualquer objeto Python, incluindo classes customizadas, tuplas, sets, bytes, etc.

**Vantagens:**
- Suporta tipos complexos (dataclasses, bytes, sets, tuplas)
- Preserva tipos Python nativos
- Serialização eficiente

**Desvantagens:**
- Não é human-readable
- **AVISO DE SEGURANÇA**: Pickle pode executar código arbitrário durante desserialização. Use apenas com dados confiáveis.

**Exemplo:**
```python
from resilient_cache import CacheFactory, CacheFactoryConfig

factory = CacheFactory(CacheFactoryConfig())
cache = factory.create_cache(
    l2_key_prefix="myapp",
    l2_ttl=3600,
    l2_enabled=True,
    serializer="pickle"  # Padrão
)

# Pode armazenar tipos complexos
cache.set("data", {"bytes": b"binary", "tuple": (1, 2, 3)})
```

### JsonSerializer

Usa JSON para serialização. Apenas suporta tipos JSON-safe.

**Vantagens:**
- Human-readable (útil para debugging)
- Seguro (não executa código)
- Interoperável com outras linguagens

**Desvantagens:**
- Suporta apenas tipos básicos (dict, list, str, int, float, bool, None)
- Não preserva tuplas, sets, bytes nativos

**Exemplo:**
```python
cache = factory.create_cache(
    l2_key_prefix="myapp",
    l2_ttl=3600,
    l2_enabled=True,
    serializer="json"
)

# Apenas tipos JSON-safe
cache.set("data", {"name": "John", "age": 30, "items": [1, 2, 3]})
```

## Sistema de Registro (Registry)

O resilient-cache implementa um Registry Pattern que permite registrar serializers customizados dinamicamente.

### Funções Disponíveis

#### `list_serializers() -> list[str]`

Lista todos os serializers registrados.

```python
from resilient_cache import list_serializers

serializers = list_serializers()
print(serializers)  # ['pickle', 'json']
```

#### `get_serializer(name: str) -> CacheSerializer`

Obtém uma instância de serializer pelo nome.

```python
from resilient_cache import get_serializer

serializer = get_serializer('json')
data = serializer.serialize({"key": "value"})
```

**Raises:**
- `ValueError`: Se o serializer não estiver registrado

#### `register_serializer(name: str, serializer_class: type[CacheSerializer]) -> None`

Registra um serializer customizado.

```python
from resilient_cache import CacheSerializer, register_serializer

class MySerializer(CacheSerializer):
    def serialize(self, value):
        # Sua lógica aqui
        pass

    def deserialize(self, data):
        # Sua lógica aqui
        pass

register_serializer('myserializer', MySerializer)
```

**Raises:**
- `TypeError`: Se a classe não for subclasse de `CacheSerializer`

**Nota:**
- Se `name` já existir, o registro será sobrescrito.

## Criando Serializers Customizados

### Passo 1: Implementar a Interface CacheSerializer

Todos os serializers devem implementar a interface abstrata `CacheSerializer`:

```python
from typing import Any
from resilient_cache import CacheSerializer

class MyCustomSerializer(CacheSerializer):
    """Meu serializer customizado."""

    def __repr__(self) -> str:
        """Retorna representação string (opcional mas recomendado)."""
        return "MyCustomSerializer()"

    def serialize(self, value: Any) -> bytes:
        """
        Converte um valor Python para bytes.

        Args:
            value: Valor a ser serializado

        Returns:
            bytes: Valor serializado

        Raises:
            ValueError: Se a serialização falhar
        """
        try:
            # Sua lógica de serialização aqui
            # Deve retornar bytes
            pass
        except Exception as e:
            raise ValueError(f"Erro ao serializar: {e}") from e

    def deserialize(self, data: bytes) -> Any:
        """
        Converte bytes de volta para um valor Python.

        Args:
            data: Dados serializados (bytes)

        Returns:
            Any: Valor Python desserializado

        Raises:
            ValueError: Se a desserialização falhar
        """
        try:
            # Sua lógica de desserialização aqui
            pass
        except Exception as e:
            raise ValueError(f"Erro ao desserializar: {e}") from e
```

### Passo 2: Registrar o Serializer

Depois de implementar, registre seu serializer:

```python
from resilient_cache import register_serializer

register_serializer('mycustom', MyCustomSerializer)
```

### Passo 3: Usar com CacheFactory

Agora você pode usar seu serializer pelo nome:

```python
from resilient_cache import CacheFactory, CacheFactoryConfig

factory = CacheFactory(CacheFactoryConfig())
cache = factory.create_cache(
    l2_key_prefix="myapp",
    l2_ttl=3600,
    l2_enabled=True,
    serializer="mycustom"  # Seu serializer customizado!
)
```

Se preferir, você também pode passar a instância diretamente (sem registro):

```python
cache = factory.create_cache(
    l2_key_prefix="myapp",
    l2_ttl=3600,
    l2_enabled=True,
    serializer=MyCustomSerializer()
)
```

## Exemplos Completos

### Exemplo 1: MessagePack Serializer

MessagePack é mais eficiente que JSON e suporta mais tipos:

```python
import msgpack
from typing import Any
from resilient_cache import CacheSerializer, register_serializer

class MsgPackSerializer(CacheSerializer):
    """Serialização usando MessagePack (mais eficiente que JSON)."""

    def __repr__(self) -> str:
        return "MsgPackSerializer()"

    def serialize(self, value: Any) -> bytes:
        try:
            return msgpack.packb(value, use_bin_type=True)
        except Exception as e:
            raise ValueError(f"Erro ao serializar com msgpack: {e}") from e

    def deserialize(self, data: bytes) -> Any:
        try:
            return msgpack.unpackb(data, raw=False)
        except Exception as e:
            raise ValueError(f"Erro ao desserializar com msgpack: {e}") from e

# Registrar
register_serializer('msgpack', MsgPackSerializer)

# Usar
from resilient_cache import CacheFactory, CacheFactoryConfig

factory = CacheFactory(CacheFactoryConfig())
cache = factory.create_cache(
    l2_key_prefix="myapp",
    l2_ttl=3600,
    l2_enabled=True,
    serializer="msgpack"
)
```

### Exemplo 2: Serializer Comprimido

Para dados grandes, você pode criar um serializer com compressão:

```python
import pickle
import zlib
from typing import Any
from resilient_cache import CacheSerializer, register_serializer

class CompressedPickleSerializer(CacheSerializer):
    """Serializer pickle com compressão zlib."""

    def __repr__(self) -> str:
        return "CompressedPickleSerializer()"

    def serialize(self, value: Any) -> bytes:
        try:
            pickled = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
            compressed = zlib.compress(pickled, level=6)
            return compressed
        except Exception as e:
            raise ValueError(f"Erro ao serializar: {e}") from e

    def deserialize(self, data: bytes) -> Any:
        try:
            decompressed = zlib.decompress(data)
            return pickle.loads(decompressed)
        except Exception as e:
            raise ValueError(f"Erro ao desserializar: {e}") from e

# Registrar
register_serializer('compressed', CompressedPickleSerializer)

# Usar
cache = factory.create_cache(
    l2_key_prefix="myapp",
    l2_ttl=3600,
    l2_enabled=True,
    serializer="compressed"
)
```

### Exemplo 3: Serializer com Versionamento

Para garantir compatibilidade, você pode adicionar versionamento:

```python
import json
from typing import Any
from resilient_cache import CacheSerializer, register_serializer

class VersionedJsonSerializer(CacheSerializer):
    """JSON com versionamento para compatibilidade."""

    VERSION = 1

    def __repr__(self) -> str:
        return f"VersionedJsonSerializer(v{self.VERSION})"

    def serialize(self, value: Any) -> bytes:
        try:
            envelope = {
                "version": self.VERSION,
                "data": value
            }
            return json.dumps(envelope, ensure_ascii=False).encode('utf-8')
        except Exception as e:
            raise ValueError(f"Erro ao serializar: {e}") from e

    def deserialize(self, data: bytes) -> Any:
        try:
            envelope = json.loads(data.decode('utf-8'))
            version = envelope.get("version", 1)

            # Aqui você poderia ter lógica para migração entre versões
            if version != self.VERSION:
                # Migrar ou lançar erro
                pass

            return envelope["data"]
        except Exception as e:
            raise ValueError(f"Erro ao desserializar: {e}") from e

# Registrar
register_serializer('versioned', VersionedJsonSerializer)
```

### Exemplo 4: Usando Instância Direta

Você também pode passar uma instância diretamente sem registrar:

```python
from resilient_cache import CacheFactory, CacheFactoryConfig, CacheSerializer

class MySerializer(CacheSerializer):
    def __init__(self, compression_level=6):
        self.compression_level = compression_level

    def serialize(self, value):
        # Implementação
        pass

    def deserialize(self, data):
        # Implementação
        pass

factory = CacheFactory(CacheFactoryConfig())

# Passar instância diretamente (não precisa registrar)
cache = factory.create_cache(
    l2_key_prefix="myapp",
    l2_ttl=3600,
    l2_enabled=True,
    serializer=MySerializer(compression_level=9)  # Instância customizada
)
```

## Boas Práticas

### 1. Sempre Implemente `__repr__`

Isso ajuda no debugging e em logs:

```python
def __repr__(self) -> str:
    return "MySerializer()"
```

Se você não implementar `__repr__`, o Python usa a representação padrão
(`<MySerializer object at 0x...>`), o que só afeta a legibilidade de logs e stats.

### 2. Lance ValueError com Mensagens Claras

Facilita o debugging quando algo dá errado:

```python
def serialize(self, value: Any) -> bytes:
    try:
        return my_serialize(value)
    except Exception as e:
        raise ValueError(f"Erro ao serializar com MySerializer: {e}") from e
```

### 3. Documente Limitações

Deixe claro quais tipos são suportados:

```python
class MySerializer(CacheSerializer):
    """Serializer customizado.

    Suporta:
    - dict, list, str, int, float

    Não suporta:
    - bytes, sets, tuplas
    """
```

### 4. Considere Compatibilidade

Se você planeja mudar o formato de serialização no futuro, considere adicionar versionamento desde o início.

### 5. Teste Serialização Round-Trip

Sempre teste que `deserialize(serialize(x)) == x`:

```python
def test_round_trip():
    serializer = MySerializer()
    original = {"key": "value"}

    serialized = serializer.serialize(original)
    deserialized = serializer.deserialize(serialized)

    assert deserialized == original
```

## Comparação de Serializers

| Serializer | Tipos Suportados | Performance | Segurança | Human-readable |
|------------|------------------|-------------|-----------|----------------|
| **pickle** | Todos Python | Alta | ⚠️ Baixa | Não |
| **json** | JSON-safe | Média | ✅ Alta | Sim |
| **msgpack** | Maioria Python | Alta | ✅ Alta | Não |
| **compressed** | Todos Python | Média* | ⚠️ Baixa | Não |

*Depende do nível de compressão

## Troubleshooting

### Erro: "Unknown serializer 'X'"

O serializer não foi registrado. Use `register_serializer()` ou verifique o nome:

```python
from resilient_cache import list_serializers

print(list_serializers())  # Ver quais estão disponíveis
```

### Erro: "must be a subclass of CacheSerializer"

Sua classe não herda de `CacheSerializer`:

```python
# ❌ Errado
class MySerializer:
    pass

# ✅ Correto
from resilient_cache import CacheSerializer

class MySerializer(CacheSerializer):
    pass
```

### Erro ao Desserializar

Verifique se você está usando o mesmo serializer para get/set:

```python
# ❌ Errado - serializers diferentes
cache1 = factory.create_cache(..., serializer="json")
cache2 = factory.create_cache(..., serializer="pickle")

cache1.set("key", value)
cache2.get("key")  # Vai falhar!

# ✅ Correto - mesmo serializer
cache1 = factory.create_cache(..., serializer="json")
cache2 = factory.create_cache(..., serializer="json")
```

## Referências

- [Módulo pickle do Python](https://docs.python.org/3/library/pickle.html)
- [Especificação JSON](https://www.json.org/)
- [MessagePack](https://msgpack.org/)
- [zlib - Compressão](https://docs.python.org/3/library/zlib.html)

## Contribuindo

Se você criou um serializer útil, considere contribuir com o projeto! Abra um PR no repositório.
