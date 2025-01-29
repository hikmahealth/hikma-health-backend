# Contributing to Hikma Health Backend

We appreciate your interest in contributing to the Hikma Health Backend project. This document outlines our contribution process and guidelines.

## Development Workflow

We use a version of trunk-based development where the `dev` branch serves as our trunk. Here's an overview of our process:

1. All development work is done on feature branches created from the `dev` branch.
2. Pull requests are made against the `dev` branch, not the `main` branch.
3. Tests are run on the `dev` branch.
4. If tests pass, code is merged into the `dev` branch.
5. Periodically, after thorough testing, `dev` is merged into `main` for release.

## Pull Request Guidelines

- Always create pull requests against the `dev` branch.
- Ensure your code follows our style guide and passes all tests.
- Include a clear description of the changes and their purpose.
- Link any relevant issues in your pull request description.

To run the tests, run:

```bash
python3 -m pytest -vv tests
```

To test any of the api endpoints, make sure you have the appropriate credentials set in your environment variables. These will be in a `.env` file (or similar) located in the project root.

```bash
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<db>
APP_ENV=dev


### TEST DETAILS ###
TEST_EMAIL=....
TEST_PASSWORD=....
```

## Code Review Process

1. Submit your pull request against the `dev` branch.
2. Wait for review from the maintainers.
3. Address any feedback or comments.
4. Once approved, your code will be merged into `dev`.

Thank you for contributing to Hikma Health Backend!
