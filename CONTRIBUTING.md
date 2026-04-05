# Contributing to EVE Co-Pilot

Thanks for your interest in contributing!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/eve-copilot.git`
3. Copy `.env.example` to `.env` and fill in your EVE SSO credentials
4. Start the stack: `docker compose up -d`
5. Create a feature branch: `git checkout -b feature/my-feature`

## Development

- **Backend:** Python 3.11+, FastAPI. Each microservice lives in `services/`.
- **Frontend:** React 19, TypeScript 5, Vite. See `public-frontend/`, `unified-frontend/`.
- **Tests:** `pytest` for backend, Playwright for e2e. Run `pytest` from the root.

## Pull Requests

- One feature/fix per PR
- Include tests for new functionality
- Keep PRs focused and small
- Update documentation if needed

## Code Style

- Follow existing patterns in the codebase
- Python: type hints, async/await
- TypeScript: strict mode

## Reporting Issues

Use [GitHub Issues](https://github.com/CytrexSGR/eve-copilot/issues) with the provided templates.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
