# Backend Tests

This directory contains all backend tests for the Grocy Reports application.

## Setup

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run tests with coverage report
```bash
pytest --cov=app --cov-report=html
```

### Run specific test file
```bash
pytest tests/services/test_grocy_api.py
```

### Run specific test class
```bash
pytest tests/services/test_grocy_api.py::TestGrocyAPIInit
```

### Run specific test function
```bash
pytest tests/services/test_grocy_api.py::TestGrocyAPIInit::test_init_strips_trailing_slash
```

### Run tests with markers
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Run tests in verbose mode
```bash
pytest -v
```

### Run tests and stop at first failure
```bash
pytest -x
```

## Test Coverage

After running tests with coverage, open the HTML report:

```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Test Structure

- `tests/services/` - Service layer tests
- `tests/api/` - API endpoint tests (to be added)
- `tests/models/` - Database model tests (to be added)
- `conftest.py` - Shared fixtures and configuration

## Writing Tests

### Example test structure:
```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def my_fixture():
    return SomeObject()

class TestMyFeature:
    def test_something(self, my_fixture):
        result = my_fixture.method()
        assert result == expected_value
```

### Mocking external dependencies:
```python
@patch('module.external_dependency')
def test_with_mock(mock_dependency):
    mock_dependency.return_value = "mocked value"
    # Your test here
```

## Best Practices

1. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification phases
2. **One assertion per test**: Focus each test on a single behavior
3. **Descriptive names**: Use clear test names that describe what is being tested
4. **Mock external dependencies**: Use mocks for external APIs, databases, etc.
5. **Clean fixtures**: Keep fixtures simple and reusable
6. **Test edge cases**: Include tests for error conditions and edge cases
