.PHONY: help install install-dev test test-unit test-integration test-all test-cov test-cov-integration test-cov-all format lint type-check clean build upload docs

help:
	@echo "Resilient Cache - Makefile"
	@echo ""
	@echo "Comandos disponíveis:"
	@echo "  make install             - Sincroniza dependências"
	@echo "  make install-dev         - Sincroniza dependências de desenvolvimento"
	@echo "  make test                - Executa testes unitários (alias para test-unit)"
	@echo "  make test-unit           - Executa apenas testes unitários"
	@echo "  make test-integration    - Executa apenas testes de integração"
	@echo "  make test-all            - Executa todos os testes (unitários + integração)"
	@echo "  make test-cov            - Executa testes unitários com coverage"
	@echo "  make test-cov-integration - Executa testes de integração com coverage"
	@echo "  make test-cov-all        - Executa todos os testes com coverage"
	@echo "  make format              - Formata código com black e isort"
	@echo "  make lint                - Verifica código com flake8"
	@echo "  make type-check          - Verifica tipos com mypy"
	@echo "  make clean               - Limpa arquivos temporários"
	@echo "  make build               - Cria distribuição do pacote"
	@echo "  make upload              - Faz upload para PyPI (requer credenciais)"
	@echo "  make docs                - Gera documentação"

install:
	uv sync

install-dev:
	uv sync --extra dev

test-unit:
	uv run pytest tests/unit/ -v

test-integration:
	VALKEY_HOST=localhost VALKEY_PORT=6379 VALKEY_DB=0 uv run pytest tests/integration/ -v

test-all:
	VALKEY_HOST=localhost VALKEY_PORT=6379 VALKEY_DB=0 uv run pytest tests/ -v

test: test-unit

test-cov:
	uv run pytest tests/unit/ -v --cov=resilient_cache --cov-report=term-missing --cov-report=html

test-cov-integration:
	VALKEY_HOST=localhost VALKEY_PORT=6379 VALKEY_DB=0 uv run pytest tests/integration/ -v --cov=resilient_cache --cov-report=term-missing --cov-report=html

test-cov-all:
	VALKEY_HOST=localhost VALKEY_PORT=6379 VALKEY_DB=0 uv run pytest tests/ -v --cov=resilient_cache --cov-report=term-missing --cov-report=html

format:
	uv run black src/ tests/ examples/
	uv run isort src/ tests/ examples/

lint:
	uv run flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503,E501 --extend-select=B950

type-check:
	uv run mypy src/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

build: clean
	uv build

upload: build
	uv publish

docs:
	@echo "Documentação disponível no README.md"
	@echo "Para mais documentação, consulte a pasta docs/"

# Atalhos úteis
dev: install-dev

check: format lint type-check test-cov-all
	@echo "✅ Todas as verificações passaram!"
