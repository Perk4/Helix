# Bind reviews and approvals to artifact hashes

Each human review disposition binds to an exact Section Draft hash and Review Scaffold Revision and becomes stale when that section or a declared dependency changes. Final study approval binds to the complete release-candidate manifest and all included artifact hashes and becomes stale after any included artifact changes, preventing an approval from silently applying to content the reviewer did not see.
