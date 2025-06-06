# prcb-checks
![icon](../images/icon_small.png)

[日本語のドキュメントはこちら](README_ja.md)

Helper command to invoke GitHub Checks API when AWS CodeBuild is executed from GitHub via AWS CodeConnections

## Installation

```
pip install https://github.com/neruneruo/prcb-checks/releases/download/v0.1.3/prcb_checks-0.1.3.tar.gz
```

Alternatively, if installing in developer mode:

```
pip install -e ".[dev]"
```

## Prerequisites

Before using prcb-checks, you need:

1. A GitHub App with appropriate permissions:
   - Checks: Read & Write

2. The app installed on your GitHub repository

3. Private key for the GitHub App stored in AWS Secrets Manager

4. AWS CodeBuild project integrated with your GitHub repository

## Required Environment Variables

prcb-checks requires the following environment variables:

| Variable | Description |
|----------|-------------|
| GITHUB_APP_ID | Your GitHub App ID |
| GITHUB_APP_INSTALLATION_ID | Installation ID of your GitHub App |
| SECRETS_MANAGER_SECRETID | AWS Secrets Manager secret ID containing the GitHub App private key |
| AWS_REGION | AWS region for Secrets Manager |
| CODEBUILD_RESOLVED_SOURCE_VERSION | Git commit SHA (automatically set by CodeBuild) |
| CODEBUILD_INITIATOR | Source of the CodeBuild trigger (automatically set by CodeBuild) |
| CODEBUILD_SRC_DIR | Source directory (for GitHub-triggered builds) |
| CODEPIPELINE_FULL_REPOSITORY_NAME | Full repository name (for CodePipeline-triggered builds) |

## Usage

Basic command structure:

```
prcb-checks <name> [status] [conclusion] [title] [summary] [text] [annotations]
```

### Command Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| name | Yes | The name of the check. Example: "code-coverage" |
| status | No | Current status of the check run. Options: queued, in_progress, completed, waiting, requested, pending. Default: queued |
| conclusion | No | Final conclusion of the check (required if status is completed). Options: action_required, cancelled, failure, neutral, success, skipped, timed_out |
| title | No | Title of the check run |
| summary | No | Summary of the check run (supports Markdown) |
| text | No | Details of the check run (supports Markdown) |
| annotations | No | JSON array of annotation objects to highlight specific lines in files with issues (supports file:// prefix) |

### Options

| Option | Description |
|--------|-------------|
| -d, --debug | Enable debug mode with verbose output |

### Advanced Usage

#### Reading Text Content from Files

For long text content, you can reference a file using the `file://` prefix:

```
prcb-checks "Lint Report" completed failure "Lint Errors" "Found issues" file:///path/to/report.txt
```

This will read the contents of `/path/to/report.txt` and use it as the text parameter.

#### Using Annotations

Annotations allow you to highlight specific issues in files with line-level precision. You can provide annotations as a JSON array:

```
prcb-checks "Lint Check" completed failure "Lint Results" "Found issues" "Details here" '[{"path":"src/main.py","start_line":42,"end_line":42,"annotation_level":"warning","message":"Variable foo is not used"}]'
```

For multiple annotations, it's more convenient to use a file:

```
prcb-checks "Lint Check" completed failure "Lint Results" "Found issues" "Details here" file:///path/to/annotations.json
```

Example annotations.json file:
```json
[
  {
    "path": "src/main.py",
    "start_line": 42,
    "end_line": 42,
    "annotation_level": "warning",
    "message": "Variable 'foo' is not used",
    "title": "Unused Variable"
  },
  {
    "path": "src/utils.py",
    "start_line": 27,
    "end_line": 29,
    "annotation_level": "failure",
    "message": "Syntax error: missing closing parenthesis",
    "title": "Syntax Error",
    "raw_details": "Optional additional details about the error"
  }
]
```

Annotation properties:
- `path`: File path relative to repository root
- `start_line`: Starting line number for the annotation
- `end_line`: Ending line number for the annotation
- `annotation_level`: Severity level - "notice", "warning", or "failure"
- `message`: Short description of the issue
- `title` (optional): Title for the annotation
- `raw_details` (optional): Additional details about the issue

## Integration with AWS CodeBuild

### Basic Setup

1. Create a GitHub App and install it on your repository
2. Store the private key in AWS Secrets Manager
3. Add the required environment variables to your CodeBuild project
4. Include the prcb-checks command in your buildspec.yml

### Example buildspec.yml

```yaml
version: 0.2

phases:
  install:
    runtime-versions:
      python: 3.11
    commands:
      - pip install https://github.com/neruneruo/prcb-checks/releases/download/v0.1.3/prcb_checks-0.1.3.tar.gz
  
  pre_build:
    commands:
      - prcb-checks "Build Check" in_progress

  build:
    commands:
      - echo "Running build steps..."
      # Your build commands here
      
  post_build:
    commands:
      - |
        if [ $CODEBUILD_BUILD_SUCCEEDING -eq 1 ]; then
          prcb-checks "Build Check" completed success "Build Successful" "The build completed successfully."
        else
          prcb-checks "Build Check" completed failure "Build Failed" "The build encountered errors."
        fi
```

### CodePipeline Integration

When used with CodePipeline, ensure the `CODEPIPELINE_FULL_REPOSITORY_NAME` environment variable is set correctly. The tool automatically detects whether it's running from CodePipeline or direct CodeBuild execution and retrieves repository information accordingly.

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

## GitHub Checks API Integration

prcb-checks simplifies the process of creating GitHub Check Runs through the API. The tool handles:

1. Authentication with the GitHub API using your GitHub App
2. Retrieving the private key from AWS Secrets Manager
3. Creating a JWT token for GitHub API authorization
4. Submitting check information to the GitHub Checks API

For more information about the GitHub Checks API, see [GitHub's documentation](https://docs.github.com/en/rest/checks/runs).