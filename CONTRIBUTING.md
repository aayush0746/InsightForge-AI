# Contributing to InsightForge AI

Thank you for your interest in contributing to **InsightForge AI**! We welcome contributions from developers, researchers, and AI engineers.

## Code of Conduct
Please ensure all discussions and contributions are respectful, constructive, and adhere to standard open-source community standards.

## How to Contribute

### 1. Fork and Clone
```bash
git clone https://github.com/<your-username>/InsightForge-AI.git
cd InsightForge-AI
```

### 2. Set Up Local Development
Follow the setup instructions in the [README.md](README.md):
- Configure `.env` from `.env.example`.
- Install Python dependencies: `pip install -r backend/requirements.txt`
- Install Node dependencies: `cd frontend && npm install`

### 3. Branch Naming Convention
- `feat/feature-name` for new features
- `fix/bug-description` for bug fixes
- `docs/doc-update` for documentation changes
- `refactor/component-name` for code improvements

### 4. Running Tests
Before submitting any pull request, ensure all tests pass:
```bash
# Run backend tests
python -m pytest backend/tests/ -v

# Run frontend typecheck & build
npm --prefix frontend run build
```

### 5. Submitting a Pull Request
1. Commit your changes with conventional commit messages (`feat: ...`, `fix: ...`, `docs: ...`).
2. Push to your forked repository.
3. Open a Pull Request against the `main` branch with a clear description of changes.

## Reporting Issues
If you encounter a bug or have a feature idea, please open an issue using the appropriate template in the Issues tab.
