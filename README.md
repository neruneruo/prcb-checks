# prcb-checks
![icon](images/icon_small.png)

Helper command to invoke GitHub Checks API when AWS CodeBuild is executed from GitHub via AWS CodeConnections

## Installation

```
pip install prcb-checks
```

Alternatively, if installing in developer mode:

```
pip install -e ".[dev]"
```

## Usage

```
prcb-checks <name> <status> [conclusion] [title] [summary] [text]
```

## Development

### Installation

```
pip install -e ".[dev]"
```

### Running Tests

After installing in developer mode, you can run tests with the following command:

```
pytest
```

To generate a coverage report:

```
pytest --cov=prcb_checks --cov-report=term-missing
```

### Build

```
python -m build
```