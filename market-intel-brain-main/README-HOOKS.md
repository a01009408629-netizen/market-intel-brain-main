# Git Hooks Setup Guide

## 🚀 Pre-Push Hook

This repository includes a Git pre-push hook that automatically runs `make fix` before allowing any push to the repository.

## 📋 How It Works

1. **Before Push**: When you run `git push`, the pre-push hook automatically runs
2. **Auto-Fix**: The hook executes `make fix` to resolve dependencies and linting issues
3. **Validation**: 
   - ✅ If `make fix` succeeds and makes no changes → Push continues
   - ⚠️ If `make fix` succeeds but makes changes → Push is canceled, you must commit changes first
   - ❌ If `make fix` fails → Push is canceled, you must fix errors manually

## 🔧 Installation

### For Windows
Run the setup script:
```bash
setup-hooks.bat
```

Or manually configure:
```bash
# The hook files are already in place:
.git/hooks/pre-push      # Unix/Linux version
.git/hooks/pre-push.bat   # Windows version
```

### For Linux/Mac
The hook should work automatically. If not, make it executable:
```bash
chmod +x .git/hooks/pre-push
```

## 🎯 Features

### Automatic Checks
- ✅ Makefile exists
- ✅ `make` command available
- ✅ `fix` target exists in Makefile
- ✅ Runs `make fix` automatically
- ✅ Checks for changes after fix
- ✅ Prevents push if fixes are needed

### Smart Behavior
- **No Changes**: If `make fix` makes no changes, push continues normally
- **Changes Made**: If `make fix` makes changes, you must commit them first
- **Fix Failed**: If `make fix` fails, you must fix errors manually

### Error Handling
- Clear error messages with colored output
- Helpful suggestions for resolution
- Prevents broken code from being pushed

## 🚨 Example Scenarios

### Scenario 1: Clean Push
```bash
git add .
git commit -m "feat: add new feature"
git push
# Output: ✅ 'make fix' completed successfully!
# Output: ✅ No changes made by 'make fix'. Push can continue.
# Push succeeds
```

### Scenario 2: Auto-Fix Makes Changes
```bash
git add .
git commit -m "feat: add new feature"
git push
# Output: ✅ 'make fix' completed successfully!
# Output: ⚠️ Changes were made by 'make fix'.
# Output: ❌ Push canceled. Please commit the changes and try again.
# Push is blocked
```

### Scenario 3: Fix Fails
```bash
git add .
git commit -m "feat: add new feature"
git push
# Output: ❌ 'make fix' failed!
# Output: ⚠️ Please fix the errors manually and try again.
# Push is blocked
```

## 🔄 Bypassing the Hook (Emergency)

If you need to bypass the hook in an emergency:

```bash
git push --no-verify
```

**⚠️ Warning**: Only use this in emergencies, as it can push broken code to the repository.

## 🛠️ Troubleshooting

### Hook Not Running
1. Ensure the hook file is executable (Linux/Mac: `chmod +x .git/hooks/pre-push`)
2. Check that Git is using the correct repository
3. Verify the hook file exists in `.git/hooks/`

### Make Command Not Found
1. Install Make for your platform
2. For Windows: Install WSL or use Windows Subsystem for Linux
3. For Mac: `brew install make`
4. For Linux: `sudo apt-get install build-essential`

### Permission Issues (Windows)
1. Run `setup-hooks.bat` as administrator
2. Or manually set permissions: `icacls .git/hooks/pre-push /grant "%USERNAME%:(OI)(CI)F"`

## 📝 Makefile Requirements

The hook expects a Makefile with a `fix` target that:
1. Runs `go mod tidy` and `go mod vendor`
2. Runs `golangci-lint run --fix`
3. Exits with 0 on success, non-zero on failure

Example:
```makefile
fix:
	@cd microservices/go-services/api-gateway && \
		go mod tidy && \
		go mod vendor && \
		golangci-lint run --fix && \
		echo "✅ Go dependencies and linting fixed"
```

## 🎉 Benefits

- **Prevents Broken Code**: Stops pushes with fixable issues
- **Automatic Quality**: Ensures code quality before push
- **Developer Friendly**: Clear error messages and guidance
- **Zero Friction**: Works automatically once set up
- **Team Consistency**: Ensures all developers follow same standards
