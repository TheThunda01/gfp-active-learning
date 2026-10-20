# Contributing

Please open an issue with the question, a small reproducible example, and the expected behavior. Corrections to scientific wording or attribution are welcome.

For code changes, run `python -m unittest discover -s tests -v` and `make reproduce`. Keep source-data checksums strict. If the experiment changes, document the new protocol and regenerate outputs; do not quietly adjust the reference results to make a check pass. New decisions guided by public test metrics count as benchmark development, so avoid describing them as evaluation on unseen outcomes.

Preserve original data attribution and separate code/data licenses. Keep this project focused on retrospective analysis of already measured GFP records.
