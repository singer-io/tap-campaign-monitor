## 1.3.0
- HTTP 403 streams are excluded from the catalog during discovery instead of failing. Raises an error only if no parent streams are accessible.
- Updated `requests` dependency from `2.33.1` to `2.34.2`.

## 1.2.0
- Updated python version. [#11](https://github.com/singer-io/tap-campaign-monitor/pull/11)
- Added integration tests.

## 1.1.0
- Refactor Backoff implementation [#9](https://github.com/singer-io/tap-campaign-monitor/pull/9)
- Library version upgrade

## 0.1.4

- Fix timezone transform for python 3.5

## 0.1.3

- Use timezone from campaign monitor when transforming dates

## 0.1.2

- Update date-time schema entries
- Fix transform_record calls

## 0.1.1

- Fix setup.py to include all the relevant files

## 0.1.0

- Use metadata in catalog, instead of old style `inclusion` and `selected-by-default` fields ([#5](https://github.com/fishtown-analytics/tap-campaign-monitor/pull/5))

## 0.0.1

First version (no changes)
