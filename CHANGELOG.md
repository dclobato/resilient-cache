# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- TBD

## [1.1.0]
- Switch L2 client to Valkey with updated connection handling.
- Add serializer registry support and allow serializer instances in config.
- Implement `set_if_not_exist` with L2-first semantics and update delete ordering.
- Add integration tests for real Valkey/Redis and expand unit coverage.

## [0.1.0]
- Initial release

[Unreleased]: https://github.com/dclobato/resilient-cache/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/dclobato/resilient-cache/releases/tag/v1.1.0
[0.1.0]: https://github.com/dclobato/resilient-cache/releases/tag/v0.1.0
