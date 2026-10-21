# Engineering standard

This is a Python 3.11 stdlib CLI in one process. service.py owns ticket operations;
cli.py parses arguments and renders results. Call service.list_tickets, not
service._rows. Existing accepted architecture is unchanged. Do not split this
small app into services. python3 check.py is the behavior acceptance command.
Import boundaries and maintainability are currently checked in review. No CI
line-count, complexity or import check exists. No file growth threshold has been
accepted. Existing source contains only one small function per module.
