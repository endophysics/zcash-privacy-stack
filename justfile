bootstrap:
    cd "{{justfile_directory()}}" && ./scripts/bootstrap

status:
    cd "{{justfile_directory()}}" && ./scripts/check-components

inspect:
    cd "{{justfile_directory()}}" && ./scripts/inspect
