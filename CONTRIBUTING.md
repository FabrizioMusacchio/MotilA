# How to Contribute

Thank you for your interest in contributing to MotilA. This project welcomes improvements to the code, documentation, examples, and usability. The goal is to maintain a clear, reliable, and reproducible workflow for microglial motility analysis in 3D and 4D multiphoton imaging data.

## Before you start
Please check the [GitHub issue tracker](https://github.com/FabrizioMusacchio/MotilA/issues) to see whether your idea, bug, or enhancement has already been reported.

- If a related issue exists, comment there to indicate your interest or to add relevant information.
- If no issue exists, open a new one with a short description of:
  * what you would like to change or add  
  * why it is useful for MotilA  
  * any ideas for implementation or testing

For small fixes (typos, minor documentation updates), opening a pull request directly is fine.

## Development environment
MotilA requires **Python 3.9 or newer** and builds on standard scientific Python packages such as NumPy, SciPy, scikit-image, tifffile, SimpleITK, and zarr.

A typical development setup using `conda`:

```sh
git clone https://github.com/FabrizioMusacchio/MotilA.git
cd MotilA

conda create -n motila-dev -c conda-forge python=3.9
conda activate motila-dev

pip install -e .
````

If you wish to install optional development dependencies (testing, linting):

```sh
pip install -e ".[dev]"
```

## Making changes and opening pull requests
All code contributions should be submitted as pull requests (PRs) against the `main` branch of the main repository.

A recommended workflow:

1. Create a new branch:

   ```sh
   git checkout -b feature/my-feature
   ```
2. Implement your changes and ensure any new functions or modules include clear docstrings.
3. Add tests for new functionality if applicable.
4. Push your branch and open a pull request with:

   * a concise, descriptive title
   * a short explanation of what you changed and why
   * references to related issues (e.g. “Closes #12”)

Draft PRs are welcome if you want feedback during development.

## Commit conventions
Clear commit messages help maintain a readable history. Prefixes inspired by Conventional Commits are encouraged:

* `feat:` new functionality
* `fix:` bug fix
* `docs:` documentation changes
* `refactor:` internal structural changes
* `test:` adding or modifying tests
* `chore:` maintenance tasks

Example:
`fix: correct handling of negative voxel intensities after registration`

## Testing
MotilA uses `pytest` for automated tests. To run the full test suite:

```sh
pytest
```

If you add new features or fix bugs, please add or adapt tests accordingly.

Tests should remain small and self-contained to avoid bundling large imaging datasets inside the repository.

## Reporting bugs
Please report bugs via the [GitHub issue tracker](https://github.com/FabrizioMusacchio/MotilA/issues) and include:

* MotilA version (`pip show motila`)
* Python version
* Operating system
* Minimal steps or code snippet to reproduce the issue
* If possible, a small synthetic or cropped dataset illustrating the problem

## License and contributions
By submitting a pull request, you agree that your contributions will be released under the [project's license](LICENSE) as specified in the repository.

If you have questions about contributing or are unsure how to begin, feel free to open an issue to start a discussion.

