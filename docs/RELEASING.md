# Releasing

1. Bump the version in `scrollgauge/__init__.py` and `packaging/scrollgauge.spec` (`Version:`), and add a `%changelog` entry to the spec. A test fails if the two versions differ.
2. Commit, then tag and push:

   ```bash
   git tag v0.1.2
   git push && git push --tags
   ```

3. The Release workflow publishes to PyPI and creates a GitHub release.
4. In COPR, open the `scrollgauge` package and click **Rebuild** to build the new version.
