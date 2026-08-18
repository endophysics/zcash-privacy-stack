bootstrap:
    cd "{{justfile_directory()}}" && ./scripts/bootstrap

status:
    cd "{{justfile_directory()}}" && ./scripts/check-components

inspect:
    cd "{{justfile_directory()}}" && ./scripts/inspect

policy-example:
    cd "{{justfile_directory()}}" && uv run ./scripts/policy-example

policy-validate *args:
    cd "{{justfile_directory()}}" && uv run ./scripts/policy-validate {{args}}

interface-summary:
    cd "{{justfile_directory()}}" && uv run ./scripts/interface-summary
