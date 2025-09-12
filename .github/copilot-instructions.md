# GitHub Copilot Instructions

## Python Version Requirements (IMPORTANT)
- Use Python 3.10+ features only where possible
- Prefer modern syntax and features (match statements, union types with |, etc.)
- Avoid deprecated or legacy Python patterns

## Documentation Standards
- Document all functions, classes, and modules using docstrings
- Use doxygen-compatible docstring format
- Include parameter types, return types, and descriptions
- Add @brief, @param, @return, and @throws tags where applicable
- Document complex logic with inline comments

## Portability Requirements
- Ensure code works on both BSD and Linux systems
- Use portable path handling (pathlib over os.path)
- Avoid platform-specific system calls or libraries
- Test compatibility across different Unix-like systems
- Use cross-platform libraries when system interaction is needed

## Code Quality
- Follow PEP 8 style guidelines
- Use type hints consistently
- Prefer composition over inheritance
- Keep functions small and focused
- Handle errors gracefully with appropriate exception handling
- Avoid creating summaries and lists
- All tests must pass before committing code
- Don't change tests to pass code; fix the code instead
- Don't run multiline code in the shell; use a script or a here-document. Make sure to clean up after yourself.

## Releasing/committing/pushing code
- The shell might not handle multiline commit messages well; use a single line summary followed by a detailed description in the body, or use a here-document for multiline messages.
- Ensure commit messages are clear and descriptive
- Avoid emojis and em-dashes in commit messages
- Use present tense in commit messages
- Reference relevant issue numbers in commit messages