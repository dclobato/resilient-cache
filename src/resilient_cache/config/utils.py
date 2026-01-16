import ipaddress
import re
from typing import Any


def is_valid_ip(endereco: str) -> bool:
    """Valida se uma string é um endereço IP válido (IPv4 ou IPv6).

    Args:
        endereco: String contendo o possível endereço IP

    Returns:
        True se é um IP válido, False caso contrário

    Examples:
        >>> is_valid_ip('192.168.1.1')
        True
        >>> is_valid_ip('2001:0db8::1')
        True
        >>> is_valid_ip('256.1.1.1')
        False
    """
    try:
        ipaddress.ip_address(endereco)
        return True
    except ValueError:
        return False


def is_valid_fqdn(endereco: str) -> bool:
    """Valida se uma string é um FQDN (Fully Qualified Domain Name) válido.

    Implementação baseada em RFC 1123.

    Args:
        endereco: String contendo o possível FQDN

    Returns:
        True se é um FQDN válido, False caso contrário

    Examples:
        >>> is_valid_fqdn('example.com')
        True
        >>> is_valid_fqdn('sub.domain.example.com')
        True
        >>> is_valid_fqdn('-invalid.com')
        False
        >>> is_valid_fqdn('invalid-.com')
        False
    """
    if not endereco or len(endereco) > 253:
        return False

    # Regex baseada em RFC 1123
    fqdn_pattern = re.compile(
        r"^(?!-)"  # Não começa com hífen
        r"(?:[a-zA-Z0-9-]{1,63}\.)*"  # Labels intermediários
        r"[a-zA-Z0-9-]{1,63}"  # Label final
        r"(?<!-)$"  # Não termina com hífen
    )

    return bool(fqdn_pattern.match(endereco))


def is_valid_port(porta: int, exclude_zero: bool = False) -> bool:
    """Valida se um número é uma porta TCP/UDP válida.

    Args:
        porta: Número da porta a ser validada
        exclude_zero: Se True, porta 0 não é considerada válida

    Returns:
        True se é uma porta válida (0-65535), False caso contrário

    Examples:
        >>> is_valid_port(80)
        True
        >>> is_valid_port(65536)
        False
        >>> is_valid_port(-1)
        False
    """
    if exclude_zero:
        return 1 <= porta <= 65535
    return 0 <= porta <= 65535


# Validation helpers that raise exceptions


def validate_boolean(value: Any, field_name: str) -> None:
    """Validate that value is a boolean.

    Args:
        value: Value to validate
        field_name: Name of the field for error message

    Raises:
        ValueError: If value is not a boolean
    """
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")


def validate_int_min(value: Any, field_name: str, min_value: int) -> None:
    """Validate that value is an integer >= min_value.

    Args:
        value: Value to validate
        field_name: Name of the field for error message
        min_value: Minimum allowed value

    Raises:
        ValueError: If value is not an int or is below min_value
    """
    if not isinstance(value, int) or value < min_value:
        raise ValueError(f"{field_name} must be >= {min_value}")


def validate_string_not_empty(value: Any, field_name: str) -> str:
    """Validate that value is a non-empty string and return stripped version.

    Args:
        value: Value to validate
        field_name: Name of the field for error message

    Returns:
        Stripped string value

    Raises:
        ValueError: If value is not a string or is empty
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


def validate_string_in_choices(value: str, field_name: str, choices: tuple[str, ...]) -> str:
    """Validate that string value is in allowed choices.

    Args:
        value: Value to validate (should already be stripped/lowercased if needed)
        field_name: Name of the field for error message
        choices: Tuple of allowed values

    Returns:
        The validated value

    Raises:
        ValueError: If value is not in choices
    """
    if value not in choices:
        raise ValueError(f"{field_name} must be one of {choices}")
    return value


def validate_host(value: Any, field_name: str) -> str:
    """Validate that value is a valid host (IP or FQDN).

    Args:
        value: Value to validate
        field_name: Name of the field for error message

    Returns:
        Stripped host string

    Raises:
        ValueError: If value is not a valid IP or FQDN
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a valid string")
    host = value.strip()
    if not (is_valid_ip(host) or is_valid_fqdn(host)):
        raise ValueError(f"{field_name} must be a valid IP address or FQDN")
    return host


def validate_port_number(value: Any, field_name: str, exclude_zero: bool = True) -> None:
    """Validate that value is a valid port number.

    Args:
        value: Value to validate
        field_name: Name of the field for error message
        exclude_zero: If True, port 0 is not allowed

    Raises:
        ValueError: If value is not a valid port number
    """
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if not is_valid_port(value, exclude_zero=exclude_zero):
        if exclude_zero:
            raise ValueError(f"{field_name} must be between 1 and 65535")
        else:
            raise ValueError(f"{field_name} must be between 0 and 65535")


def validate_optional_string(value: Any, field_name: str) -> None:
    """Validate that value is either None or a string.

    Args:
        value: Value to validate
        field_name: Name of the field for error message

    Raises:
        ValueError: If value is not None and not a string
    """
    if value is not None and not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or None")
