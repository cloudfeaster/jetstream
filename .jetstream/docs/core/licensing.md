<!-- Written by `jetstream sync` from cloudfeaster/jetstream's docs; don't edit. -->

# Licensing

Cloudfeaster code may be open-sourced or sold, so every dependency's license has to allow both.

## Dependencies

- **Allowed** for any dependency: MIT, Apache-2.0 and the BSD licenses.
- **Allowed for a transitive dependency only**: MPL-2.0. It's weak copyleft that only covers changes to that package's own files, not the code that uses it.
- **Not allowed**: GPL, LGPL and AGPL, in any version, and any license not listed here.

A dependency that needs an exception is a decision for jetstream, not for one repo, because the allowed licenses are set in the configuration jetstream owns.

## Third-party data

A data file from a published dataset is never committed, whatever its license. A script builds it, it's gitignored, and code that needs it fails with a message saying how to build it. Tests use a small stand-in instead. The dataset's credit goes in the README next to the code that uses it.

## Copyright

Copyright is stated once, in the repo's `LICENSE`. Files don't have copyright headers.
