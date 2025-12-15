# nomad-simulation-entries 

This repository curates a small, representative set of public NOMAD entry IDs for testing and development. The goal is to maintain a stable, transparent "test corpus" that covers multiple simulation codes and avoids overrepresenting a single contributor or dataset. 

## How entries are selected (work in progress)

We use API queries to select entries in a way that is:

- **Code-specific** _(per simulation program/package)_

- **Main-author diverse** _(avoid picking everything from one person)_

- **Dataset-aware** _(optionally spread picks across multiple datasets owned by the same main author)_
