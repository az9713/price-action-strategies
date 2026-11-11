# Next implementation work organization

After the0.24 source checkpoint, keep the managed0.24 app available while building the remaining research features in an isolated source copy with its own synthetic-only data store. Copy selected source/docs/test/fixture/frontend inputs explicitly; exclude every.env path, actual cached prices, live app database, credentials, raw traces, installed dependencies and process metadata. Use the existing locked Python environment with the development copy first on PYTHONPATH; resolve all numerical core/asset paths inside that copy.

Do not copy real protected data or reset viewed-date guards. Development uses visibly synthetic instruments/dates and preserves the real main store. Merge authorized source changes only after focused synthetic/source/reference checks pass, then verify main-store idleness and stop its managed session before replacing its loaded source. Run final coherent regression/browser/resource/acceptance evidence on the integrated source. No additional server against the main store or arbitrary process kill is required.

Source-page10 clarification is recorded in source-spread-screenshot-interpretation-correction.json:40k spread target/4k per setup,400 is each greedy proposal batch. Do not implement the erroneous older compressed-note400-target interpretation.
