import ipaddress
import re


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
            r'^(?!-)'  # Não começa com hífen
            r'(?:[a-zA-Z0-9-]{1,63}\.)*'  # Labels intermediários
            r'[a-zA-Z0-9-]{1,63}'  # Label final
            r'(?<!-)$'  # Não termina com hífen
            )

    return bool(fqdn_pattern.match(endereco))


def is_valid_port(porta: int,
                  exclude_zero: bool = False) -> bool:
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