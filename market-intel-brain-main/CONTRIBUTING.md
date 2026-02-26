# 🤝 Contributing to Market Intel Brain

Thank you for your interest in contributing to Market Intel Brain! This document provides guidelines and best practices for contributors.

## 🚀 Quick Start

1. **Fork the repository**
   ```bash
   # Fork on GitHub and clone your fork
   git clone https://github.com/YOUR_USERNAME/market-intel-brain.git
   cd market-intel-brain
   ```

2. **Set up development environment**
   ```bash
   # Install dependencies
   make setup
   
   # Start development services
   make dev
   ```

3. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make your changes and test**
   ```bash
   # Run tests
   make test
   
   # Run linting
   make lint
   ```

5. **Submit a pull request**
   ```bash
   git push origin feature/your-feature-name
   # Create pull request on GitHub
   ```

## 🌳 Branch Strategy (GitFlow)

We follow GitFlow methodology for branch management:

### Main Branches
- **`main`** - Production-ready code
  - Only contains stable, tested code
  - Tagged with version numbers
  - Protected branch (requires PR review)

- **`develop`** - Integration branch
  - Contains the latest integrated features
  - All feature branches merge into develop
  - Used for testing and integration

### Supporting Branches
- **`feature/*`** - Feature development
  - Created from `develop`
  - Merge back into `develop` via PR
  - Naming: `feature/description-of-feature`

- **`hotfix/*`** - Production hotfixes
  - Created from `main`
  - Merge into both `main` and `develop`
  - Naming: `hotfix/description-of-fix`

- **`release/*`** - Release preparation
  - Created from `develop`
  - Merge into `main` and `develop`
  - Naming: `release/vX.Y.Z`

### Branch Protection Rules
- **Main branch**: Requires PR review, status checks, and admin approval
- **Develop branch**: Requires PR review and status checks
- **Feature branches**: No restrictions, but must follow naming convention

## 📝 Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/) specification for consistent commit messages:

### Format
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types
- **`feat`**: New feature or enhancement
- **`fix`**: Bug fix
- **`docs`**: Documentation changes
- **`style`**: Code style changes (formatting, missing semicolons, etc.)
- **`refactor`**: Code refactoring without functional changes
- **`test`**: Adding or updating tests
- **`chore`**: Maintenance tasks, dependency updates, configuration changes

### Examples
```bash
feat(api): add user authentication endpoint
fix(core): resolve memory leak in data processor
docs(readme): update installation instructions
style(go): format code with gofmt
refactor(rust): simplify error handling
test(integration): add e2e tests for user flow
chore(deps): update go dependencies
```

### Scopes
Common scopes include:
- **`api`**: API Gateway (Go)
- **`core`**: Core Engine (Rust)
- **`proto`**: Protobuf definitions
- **`docker`**: Docker configurations
- **`docs`**: Documentation
- **`ci`**: CI/CD pipelines
- **`deps`**: Dependencies

## 🧪 Development Guidelines

### Code Quality
- **Rust**: Follow [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)
- **Go**: Follow [Effective Go](https://golang.org/doc/effective_go.html)
- **Testing**: Maintain >80% test coverage
- **Documentation**: Document all public APIs and complex logic

### Linting and Formatting
```bash
# Rust
cargo fmt --all
cargo clippy --all-targets --all-features -- -D warnings

# Go
gofmt -s -w .
golangci-lint run
```

### Testing
- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test service interactions
- **E2E Tests**: Test complete user workflows
- **Performance Tests**: Benchmark critical paths

### Security
- Follow security best practices
- Run security scans before committing
- Never commit secrets or sensitive data
- Use environment variables for configuration

## 🔄 Pull Request Process

### Before Submitting
1. **Ensure your branch is up to date**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout feature/your-feature
   git rebase develop
   ```

2. **Run all checks**
   ```bash
   make test      # Run all tests
   make lint      # Run linting
   make security  # Run security scans
   ```

3. **Update documentation**
   - Update README.md if needed
   - Update API documentation
   - Add comments to complex code

### PR Template
When creating a pull request, include:

```markdown
## 📋 Description
Brief description of the changes and their purpose.

## 🔄 Changes Made
- [ ] Feature implementation
- [ ] Bug fix
- [ ] Documentation update
- [ ] Test coverage

## 🧪 Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Performance impact assessed

## 📸 Screenshots (if applicable)
Add screenshots for UI changes.

## 🔗 Related Issues
Closes #issue-number

## ✅ Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review of the code completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] No security vulnerabilities
- [ ] Ready for review
```

### PR Review Process
1. **Automated Checks**: CI/CD pipeline runs automatically
2. **Code Review**: At least one maintainer must review
3. **Testing**: Reviewer tests the changes
4. **Approval**: Maintainer approves the PR
5. **Merge**: Squash and merge to target branch

## 🛠 Development Environment

### Prerequisites
- **Docker & Docker Compose**
- **Go 1.21+**
- **Rust 1.75+**
- **Buf** (for Protobuf)
- **Make**

### Setup Commands
```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/market-intel-brain.git
cd market-intel-brain

# Install dependencies
make setup

# Start development environment
make dev

# Verify setup
make check
```

### Make Commands
```bash
make help           # Show all commands
make setup          # Install dependencies
make dev            # Start development environment
make test           # Run all tests
make lint           # Run linting
make security        # Run security scans
make build          # Build all services
make clean          # Clean build artifacts
make check          # Verify environment setup
```

## 📊 Project Structure

```
market-intel-brain/
├── .github/
│   ├── workflows/          # CI/CD pipelines
│   └── ISSUE_TEMPLATE/     # Issue templates
├── microservices/
│   ├── go-services/        # Go microservices
│   │   └── api-gateway/
│   ├── rust-services/      # Rust microservices
│   │   └── core-engine/
│   ├── proto/             # Protobuf definitions
│   └── scripts/           # Utility scripts
├── docs/                 # Documentation
├── k8s/                  # Kubernetes manifests
├── deploy/                # Deployment configurations
├── tests/                 # Integration and E2E tests
├── Makefile              # Build automation
├── README.md             # Project documentation
├── CONTRIBUTING.md       # Contribution guidelines
├── LICENSE              # License file
└── .gitignore          # Git ignore rules
```

## 🔍 Code Review Guidelines

### For Reviewers
1. **Check functionality**: Does the code work as intended?
2. **Review security**: Are there any security concerns?
3. **Check performance**: Any performance implications?
4. **Verify tests**: Are tests comprehensive?
5. **Documentation**: Is the code well documented?
6. **Style**: Does it follow project conventions?

### For Contributors
1. **Be responsive**: Address review comments promptly
2. **Explain changes**: Provide context for complex changes
3. **Test thoroughly**: Ensure your changes work correctly
4. **Document**: Update documentation as needed
5. **Be patient**: Reviewers may need time to review

## 🚨 Issue Reporting

### Bug Reports
Use the bug report template for reporting issues:

```markdown
## 🐛 Bug Description
Clear description of the bug

## 🔄 Steps to Reproduce
1. Step one
2. Step two
3. Step three

## 🎯 Expected Behavior
What should happen

## 📸 Actual Behavior
What actually happens

## 🌍 Environment
- OS: [e.g., Ubuntu 20.04]
- Version: [e.g., v1.2.3]
- Browser/Client: [if applicable]

## 📝 Additional Context
Any additional information
```

### Feature Requests
Use the feature request template:

```markdown
## 🚀 Feature Description
Clear description of the feature

## 💡 Motivation
Why is this feature needed?

## 📋 Proposed Solution
How should this feature work?

## 🔄 Alternatives Considered
Other approaches you considered

## 📸 Additional Context
Any additional information
```

## 📚 Resources

### Documentation
- [Rust Book](https://doc.rust-lang.org/book/)
- [Go Documentation](https://golang.org/doc/)
- [Docker Documentation](https://docs.docker.com/)
- [Protobuf Documentation](https://developers.google.com/protocol-buffers)

### Tools
- [Rust Analyzer](https://rust-analyzer.github.io/)
- [GoLand](https://www.jetbrains.com/go/)
- [VS Code](https://code.visualstudio.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop)

### Community
- [Rust Users Forum](https://users.rust-lang.org/)
- [Go Forum](https://forum.golangbridge.org/)
- [Stack Overflow](https://stackoverflow.com/)
- [Discord/Slack] (if available)

## 🎉 Recognition

Contributors are recognized in:
- **README.md**: Contributors section
- **Release Notes**: Feature credits
- **Community**: Shoutouts in communications

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).

## 🤝 Code of Conduct

Please be respectful and professional in all interactions. See [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) for details.

---

Thank you for contributing to Market Intel Brain! 🚀
