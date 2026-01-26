# Contributing to Trade Auditor

First off, thank you for considering contributing to Trade Auditor! It's people like you that make this tool better for the trading community.

## How Can I Contribute?

### Reporting Bugs
* Use GitHub Issues to report bugs.
* Describe the steps to reproduce the issue and include your broker (Tastytrade/IBKR).

### Suggesting Enhancements
* Open an issue to discuss new screening strategies (e.g., new technical indicators or risk metrics).

### Pull Requests
1. Fork the repo and create your branch from `main`.
2. Ensure the backend tests pass: `pytest`.
3. If changing the frontend, ensure the build works: `cd frontend && npm run build`.
4. Update the documentation if you're adding a new strategy.

## Development Setup
Refer to the `README.md` for Docker and Local Development setup instructions. We use **Flask** for the backend and **React (Vite)** for the frontend.
