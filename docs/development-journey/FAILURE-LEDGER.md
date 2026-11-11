# Retained nonzero-command attempts

This appendix indexes every nonzero top-level command receipt before the build cutoff. It does not classify all of them as product bugs. Intentional preimplementation failures, malformed verifier fixtures, environment/standby timeouts and genuine defects coexist here. Successful mutation harnesses usually have top-level exit0; their expected inner test failures remain inside their own receipts.

Up to three original diagnostic lines are shown per attempt. Long lines are explicitly clipped, and local paths/credential-shaped contexts are redacted. Full preserved review logs are linked; no private raw trace or hidden analysis is copied. Hashes of the quoted stdout/stderr files were checked against their owning receipts during generation.

## 20261108T035756286549Z-frontend-build

[Receipt](../../verification/receipts/20261108T035756286549Z-frontend-build.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T035756286549Z-frontend-build/stdout.log) · [stderr.log](../../verification/runs/20261108T035756286549Z-frontend-build/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T035832907961Z-api-process-integration

[Receipt](../../verification/receipts/20261108T035832907961Z-api-process-integration.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T035832907961Z-api-process-integration/stdout.log) · [stderr.log](../../verification/runs/20261108T035832907961Z-api-process-integration/stderr.log)

````text
E           AssertionError: assert 'queued' == 'completed'
E             
E             - completed
````

## 20261108T041037384744Z-full-core-api-worker-current

[Receipt](../../verification/receipts/20261108T041037384744Z-full-core-api-worker-current.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T041037384744Z-full-core-api-worker-current/stdout.log) · [stderr.log](../../verification/runs/20261108T041037384744Z-full-core-api-worker-current/stderr.log)

````text
E           AssertionError: assert 'running' == 'completed'
E             
E             - completed
````

## 20261108T042104411127Z-coherent-component-rerun

[Receipt](../../verification/receipts/20261108T042104411127Z-coherent-component-rerun.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T042104411127Z-coherent-component-rerun/stdout.log) · [stderr.log](../../verification/runs/20261108T042104411127Z-coherent-component-rerun/stderr.log)

````text
E           AssertionError: assert 'queued' == 'completed'
E             
E             - completed
````

## 20261108T042833278258Z-browser-real-stack

[Receipt](../../verification/receipts/20261108T042833278258Z-browser-real-stack.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T042833278258Z-browser-real-stack/stdout.log) · [stderr.log](../../verification/runs/20261108T042833278258Z-browser-real-stack/stderr.log)

````text
    Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8765/
    Error: locator.selectOption: Test timeout of 90000ms exceeded.
````

## 20261108T043845619606Z-chart-and-real-browser-regression

[Receipt](../../verification/receipts/20261108T043845619606Z-chart-and-real-browser-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T043845619606Z-chart-and-real-browser-regression/stdout.log) · [stderr.log](../../verification/runs/20261108T043845619606Z-chart-and-real-browser-regression/stderr.log)

````text
    Error: expect(locator).toBeVisible() failed
    Error: element(s) not found
````

## 20261108T044855305645Z-release-gate-open-requirements

[Receipt](../../verification/receipts/20261108T044855305645Z-release-gate-open-requirements.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T044855305645Z-release-gate-open-requirements/stdout.log) · [stderr.log](../../verification/runs/20261108T044855305645Z-release-gate-open-requirements/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T050042932904Z-independent-reference-first

[Receipt](../../verification/receipts/20261108T050042932904Z-independent-reference-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T050042932904Z-independent-reference-first/stdout.log) · [stderr.log](../../verification/runs/20261108T050042932904Z-independent-reference-first/stderr.log)

````text
E           AssertionError: ('/trades/0/net_pnl', -38.004024305555554, '-38.00399791666666666666666666666666666667')
E           assert Decimal('0.00002638888888733333333333333333') <= Decimal('1E-7')
E            +  where Decimal('0.00002638888888733333333333333333') = abs((Decimal('-38.004024305555554') - Decimal('-38.00399791666666666666666666666666666667')))
````

## 20261108T050203234162Z-independent-reference-oracle-corrected

[Receipt](../../verification/receipts/20261108T050203234162Z-independent-reference-oracle-corrected.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T050203234162Z-independent-reference-oracle-corrected/stdout.log) · [stderr.log](../../verification/runs/20261108T050203234162Z-independent-reference-oracle-corrected/stderr.log)

````text
E           AssertionError: ('/trades/0/net_pnl', -38.004024305555554, '-38.00399791666666666666666666666666666667')
E           assert Decimal('0.00002638888888733333333333333333') <= Decimal('1E-7')
E            +  where Decimal('0.00002638888888733333333333333333') = abs((Decimal('-38.004024305555554') - Decimal('-38.00399791666666666666666666666666666667')))
````

## 20261108T051014555486Z-decimal-execution-boundaries-first

[Receipt](../../verification/receipts/20261108T051014555486Z-decimal-execution-boundaries-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T051014555486Z-decimal-execution-boundaries-first/stdout.log) · [stderr.log](../../verification/runs/20261108T051014555486Z-decimal-execution-boundaries-first/stderr.log)

````text
E           AssertionError: ('/trades/0/entry_quantity', 28, '29')
E           assert Decimal('1') <= Decimal('1E-9')
E            +  where Decimal('1') = abs((Decimal('28') - Decimal('29')))
````

## 20261108T054154357014Z-family-discriminators-first

[Receipt](../../verification/receipts/20261108T054154357014Z-family-discriminators-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T054154357014Z-family-discriminators-first/stdout.log) · [stderr.log](../../verification/runs/20261108T054154357014Z-family-discriminators-first/stderr.log)

````text
E       assert [21, 22] == [21]
E         
E         Left contains one more item: 22
````

## 20261108T054717011927Z-overlap-priority-first

[Receipt](../../verification/receipts/20261108T054717011927Z-overlap-priority-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T054717011927Z-overlap-priority-first/stdout.log) · [stderr.log](../../verification/runs/20261108T054717011927Z-overlap-priority-first/stderr.log)

````text
E       AssertionError: assert (1 == 1 and -1 == 1)
E        +  where 1 = len([Signal(id='8b0c69ad06eab13ac7e2af50', symbol='SPY', available_at=Timestamp('2026-10-05 13:50:00+0000', tz='UTC'), sid...6768448946, target_swing=102.0, weight=1.0, setup_at=Timestamp('2026-10-05 13:50:00+0000', tz='UTC'), source_index=19)])
E        +  and   -1 = Signal(id='8b0c69ad06eab13ac7e2af50', symbol='SPY', available_at=Timestamp('2026-10-05 13:50:00+0000', tz='UTC'), side...76768448946, target_swing=102.0, weight=1.0, setup_at=Timestamp('2026-10-05 13:50:00+0000', tz='UTC'), source_index=19).side
````

## 20261108T055535304465Z-zone-return-and-expiry-boundaries

[Receipt](../../verification/receipts/20261108T055535304465Z-zone-return-and-expiry-boundaries.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T055535304465Z-zone-return-and-expiry-boundaries/stdout.log) · [stderr.log](../../verification/runs/20261108T055535304465Z-zone-return-and-expiry-boundaries/stderr.log)

````text
E       AssertionError: assert not [Signal(id='729100900c8166997ff725ea', symbol='SPY', available_at=Timestamp('2026-10-05 13:55:00+0000', tz='UTC'), sid...8746947233, target_swing=135.2, weight=1.0, setup_at=Timestamp('2026-10-05 13:55:00+0000', tz='UTC'), source_index=24)]
E        +  where [Signal(id='729100900c8166997ff725ea', symbol='SPY', available_at=Timestamp('2026-10-05 13:55:00+0000', tz='UTC'), sid...8746947233, target_swing=135.2, weight=1.0, setup_at=Timestamp('2026-10-05 13:55:00+0000', tz='UTC'), source_index=24)] = at(   symbol                 timestamp  ...             session_close  factor\n0     SPY 2026-10-05 13:30:00+00:00  ... 20...:00:00+00:00   [line clipped]
FAILED tests/test_family_boundaries.py::test_zone_age_expires_before_a_delayed_first_return[supply_demand-22-away0-returning0]
````

## 20261108T055652023853Z-current-full-component-and-matrix

[Receipt](../../verification/receipts/20261108T055652023853Z-current-full-component-and-matrix.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T055652023853Z-current-full-component-and-matrix/stdout.log) · [stderr.log](../../verification/runs/20261108T055652023853Z-current-full-component-and-matrix/stderr.log)

````text
E           AssertionError: Worker did not become ready within the diagnostic startup envelope.
E           assert (False)
E       AssertionError: assert not [Signal(id='729100900c8166997ff725ea', symbol='SPY', available_at=Timestamp('2026-10-05 13:55:00+0000', tz='UTC'), sid...8746947233, target_swing=135.2, weight=1.0, setup_at=Timestamp('2026-10-05 13:55:00+0000', tz='UTC'), source_index=24)]
````

## 20261108T061033647905Z-browser-current-reference-contract

[Receipt](../../verification/receipts/20261108T061033647905Z-browser-current-reference-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T061033647905Z-browser-current-reference-contract/stdout.log) · [stderr.log](../../verification/runs/20261108T061033647905Z-browser-current-reference-contract/stderr.log)

````text
    Error: browserType.launch: Chromium distribution 'chrome' is not found at <user-home>\AppData\Local\Google\Chrome\Application\chrome.exe
````

## 20261108T061535102105Z-browser-installed-chrome-current

[Receipt](../../verification/receipts/20261108T061535102105Z-browser-installed-chrome-current.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T061535102105Z-browser-installed-chrome-current/stdout.log) · [stderr.log](../../verification/runs/20261108T061535102105Z-browser-installed-chrome-current/stderr.log)

````text
    Error: expect(locator).toBeVisible() failed
    Error: element(s) not found
````

## 20261108T062735891290Z-current-release-gate-unmet

[Receipt](../../verification/receipts/20261108T062735891290Z-current-release-gate-unmet.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T062735891290Z-current-release-gate-unmet/stdout.log) · [stderr.log](../../verification/runs/20261108T062735891290Z-current-release-gate-unmet/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T064355480334Z-aggregate-entry-liquidity-first

[Receipt](../../verification/receipts/20261108T064355480334Z-aggregate-entry-liquidity-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T064355480334Z-aggregate-entry-liquidity-first/stdout.log) · [stderr.log](../../verification/runs/20261108T064355480334Z-aggregate-entry-liquidity-first/stderr.log)

````text
E       AssertionError: assert Decimal('58') == Decimal('29')
E        +  where Decimal('58') = sum(<generator object test_shared_symbol_volume_is_not_reused_by_multiple_rules.<locals>.<genexpr> at 0x000002965AE8F2E0>)
E        +  where Decimal('58') = sum(<generator object test_shared_symbol_volume_is_not_reused_by_multiple_rules.<locals>.<genexpr> at 0x000002965B004400>)
````

## 20261108T065143571629Z-single-and-portfolio-real-browser

[Receipt](../../verification/receipts/20261108T065143571629Z-single-and-portfolio-real-browser.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T065143571629Z-single-and-portfolio-real-browser/stdout.log) · [stderr.log](../../verification/runs/20261108T065143571629Z-single-and-portfolio-real-browser/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T070537086624Z-portfolio-level-range-ui-build

[Receipt](../../verification/receipts/20261108T070537086624Z-portfolio-level-range-ui-build.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T070537086624Z-portfolio-level-range-ui-build/stdout.log) · [stderr.log](../../verification/runs/20261108T070537086624Z-portfolio-level-range-ui-build/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T071006394373Z-visible-levels-browser-artifact-reconciliation

[Receipt](../../verification/receipts/20261108T071006394373Z-visible-levels-browser-artifact-reconciliation.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T071006394373Z-visible-levels-browser-artifact-reconciliation/stdout.log) · [stderr.log](../../verification/runs/20261108T071006394373Z-visible-levels-browser-artifact-reconciliation/stderr.log)

````text
Traceback (most recent call last):
AssertionError
````

## 20261108T071615628152Z-expanded-release-gate-unmet

[Receipt](../../verification/receipts/20261108T071615628152Z-expanded-release-gate-unmet.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T071615628152Z-expanded-release-gate-unmet/stdout.log) · [stderr.log](../../verification/runs/20261108T071615628152Z-expanded-release-gate-unmet/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T072556925891Z-current-numerical-coverage-gate-unmet

[Receipt](../../verification/receipts/20261108T072556925891Z-current-numerical-coverage-gate-unmet.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T072556925891Z-current-numerical-coverage-gate-unmet/stdout.log) · [stderr.log](../../verification/runs/20261108T072556925891Z-current-numerical-coverage-gate-unmet/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T073758032173Z-release-gate-fault-first

[Receipt](../../verification/receipts/20261108T073758032173Z-release-gate-fault-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T073758032173Z-release-gate-fault-first/stdout.log) · [stderr.log](../../verification/runs/20261108T073758032173Z-release-gate-fault-first/stderr.log)

````text
E       assert (0 == 1)
FAILED tests/test_release_evidence.py::test_incomplete_requirement_mapping_blocks[omitted]
FAILED tests/test_release_evidence.py::test_incomplete_requirement_mapping_blocks[duplicate]
````

## 20261108T074017990514Z-verification-contract-real-release-unmet

[Receipt](../../verification/receipts/20261108T074017990514Z-verification-contract-real-release-unmet.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T074017990514Z-verification-contract-real-release-unmet/stdout.log) · [stderr.log](../../verification/runs/20261108T074017990514Z-verification-contract-real-release-unmet/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T074245100094Z-statistics-contract-first

[Receipt](../../verification/receipts/20261108T074245100094Z-statistics-contract-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T074245100094Z-statistics-contract-first/stdout.log) · [stderr.log](../../verification/runs/20261108T074245100094Z-statistics-contract-first/stderr.log)

````text
E       assert [-1.0, inf] == [-1, None]
E         
E         At index 1 diff: inf != None
````

## 20261108T074619885437Z-passive-benchmark-contract-first

[Receipt](../../verification/receipts/20261108T074619885437Z-passive-benchmark-contract-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T074619885437Z-passive-benchmark-contract-first/stdout.log) · [stderr.log](../../verification/runs/20261108T074619885437Z-passive-benchmark-contract-first/stderr.log)

````text
E       AssertionError: Benchmark input contract must be implemented.
E       assert None is not None
E       ModuleNotFoundError: No module named 'backend.lab.benchmarks'
````

## 20261108T074815149299Z-passive-benchmark-contract-regression

[Receipt](../../verification/receipts/20261108T074815149299Z-passive-benchmark-contract-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T074815149299Z-passive-benchmark-contract-regression/stdout.log) · [stderr.log](../../verification/runs/20261108T074815149299Z-passive-benchmark-contract-regression/stderr.log)

````text
E           TypeError: Headers.update() got an unexpected keyword argument 'Origin'
FAILED tests/test_benchmarks.py::test_real_api_and_json_export - TypeError: H...
````

## 20261108T075122101861Z-metric-overflow-boundary-first

[Receipt](../../verification/receipts/20261108T075122101861Z-metric-overflow-boundary-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T075122101861Z-metric-overflow-boundary-first/stdout.log) · [stderr.log](../../verification/runs/20261108T075122101861Z-metric-overflow-boundary-first/stderr.log)

````text
E       Failed: DID NOT RAISE ValueError
FAILED tests/test_statistics_contract.py::test_extreme_finite_inputs_cannot_overflow_into_an_infinite_badge
````

## 20261108T075848249572Z-research-current-numerical-coverage-gate

[Receipt](../../verification/receipts/20261108T075848249572Z-research-current-numerical-coverage-gate.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T075848249572Z-research-current-numerical-coverage-gate/stdout.log) · [stderr.log](../../verification/runs/20261108T075848249572Z-research-current-numerical-coverage-gate/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T080446231829Z-current-seven-module-numerical-coverage

[Receipt](../../verification/receipts/20261108T080446231829Z-current-seven-module-numerical-coverage.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T080446231829Z-current-seven-module-numerical-coverage/stdout.log) · [stderr.log](../../verification/runs/20261108T080446231829Z-current-seven-module-numerical-coverage/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T080446611629Z-current-345-case-release-unmet

[Receipt](../../verification/receipts/20261108T080446611629Z-current-345-case-release-unmet.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T080446611629Z-current-345-case-release-unmet/stdout.log) · [stderr.log](../../verification/runs/20261108T080446611629Z-current-345-case-release-unmet/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T081622705818Z-random-controls-contract-first

[Receipt](../../verification/receipts/20261108T081622705818Z-random-controls-contract-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T081622705818Z-random-controls-contract-first/stdout.log) · [stderr.log](../../verification/runs/20261108T081622705818Z-random-controls-contract-first/stderr.log)

````text
E       assert None is not None
E       ModuleNotFoundError: No module named 'backend.lab.controls'
ERROR tests/test_random_controls.py::test_real_worker_accounts_match_independent_execution_and_saved_parts
````

## 20261108T081934278507Z-random-controls-initial-implementation

[Receipt](../../verification/receipts/20261108T081934278507Z-random-controls-initial-implementation.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T081934278507Z-random-controls-initial-implementation/stdout.log) · [stderr.log](../../verification/runs/20261108T081934278507Z-random-controls-initial-implementation/stderr.log)

````text
E       assert (1 == 0)
E       NameError: name 'create_app' is not defined
FAILED tests/test_random_controls.py::test_incompatible_symbol_time_volatility_or_duration_is_not_a_match[change1]
````

## 20261108T082021558850Z-controls-subject-contract-first

[Receipt](../../verification/receipts/20261108T082021558850Z-controls-subject-contract-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T082021558850Z-controls-subject-contract-first/stdout.log) · [stderr.log](../../verification/runs/20261108T082021558850Z-controls-subject-contract-first/stderr.log)

````text
E       AssertionError: assert '553bea79d81b...c3dfe7eaabbdf' == 'a5dcef0263f4...7073274fe001c'
E         
E         - a5dcef0263f418bbf4ba0ef93f705a530015b8c02ac45e2366b7073274fe001c
````

## 20261108T082734096743Z-controls-negative-api-and-weight-first

[Receipt](../../verification/receipts/20261108T082734096743Z-controls-negative-api-and-weight-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T082734096743Z-controls-negative-api-and-weight-first/stdout.log) · [stderr.log](../../verification/runs/20261108T082734096743Z-controls-negative-api-and-weight-first/stderr.log)

````text
E           assert (500 == 400)
E            +  where 500 = <Response [500 Internal Server Error]>.status_code
E       assert 1 == 0
````

## 20261108T082855174462Z-controls-boundaries-and-inventory

[Receipt](../../verification/receipts/20261108T082855174462Z-controls-boundaries-and-inventory.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T082855174462Z-controls-boundaries-and-inventory/stdout.log) · [stderr.log](../../verification/runs/20261108T082855174462Z-controls-boundaries-and-inventory/stderr.log)

````text
E           assert (409 == 400)
E            +  where 409 = <Response [409 Conflict]>.status_code
FAILED tests/test_random_controls.py::test_real_controls_api_exports_and_invalid_replicas
````

## 20261108T083257132426Z-controls-api-400-regression

[Receipt](../../verification/receipts/20261108T083257132426Z-controls-api-400-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T083257132426Z-controls-api-400-regression/stdout.log) · [stderr.log](../../verification/runs/20261108T083257132426Z-controls-api-400-regression/stderr.log)

````text
E           assert (409 == 400)
E            +  where 409 = <Response [409 Conflict]>.status_code
FAILED tests/test_random_controls.py::test_real_controls_api_exports_and_invalid_replicas
````

## 20261108T083434534372Z-matched-controls-eight-real-browser-journeys

[Receipt](../../verification/receipts/20261108T083434534372Z-matched-controls-eight-real-browser-journeys.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T083434534372Z-matched-controls-eight-real-browser-journeys/stdout.log) · [stderr.log](../../verification/runs/20261108T083434534372Z-matched-controls-eight-real-browser-journeys/stderr.log)

````text
    TimeoutError: locator.fill: Timeout 15000ms exceeded.
````

## 20261108T083953762430Z-controls-delayed-response-first-browser

[Receipt](../../verification/receipts/20261108T083953762430Z-controls-delayed-response-first-browser.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T083953762430Z-controls-delayed-response-first-browser/stdout.log) · [stderr.log](../../verification/runs/20261108T083953762430Z-controls-delayed-response-first-browser/stderr.log)

````text
    Error: expect(locator).toHaveCount(expected) failed
````

## 20261108T084204179937Z-eight-module-control-numerical-coverage

[Receipt](../../verification/receipts/20261108T084204179937Z-eight-module-control-numerical-coverage.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T084204179937Z-eight-module-control-numerical-coverage/stdout.log) · [stderr.log](../../verification/runs/20261108T084204179937Z-eight-module-control-numerical-coverage/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T084258173392Z-matched-controls-351-release-unmet

[Receipt](../../verification/receipts/20261108T084258173392Z-matched-controls-351-release-unmet.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T084258173392Z-matched-controls-351-release-unmet/stdout.log) · [stderr.log](../../verification/runs/20261108T084258173392Z-matched-controls-351-release-unmet/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T090255228332Z-behavior-contract-first

[Receipt](../../verification/receipts/20261108T090255228332Z-behavior-contract-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T090255228332Z-behavior-contract-first/stdout.log) · [stderr.log](../../verification/runs/20261108T090255228332Z-behavior-contract-first/stderr.log)

````text
E       assert None is not None
E       ModuleNotFoundError: No module named 'backend.lab.behavior'
E       TypeError: contexts() got an unexpected keyword argument 'observer'
````

## 20261108T091224678110Z-behavior-initial-service-integration

[Receipt](../../verification/receipts/20261108T091224678110Z-behavior-initial-service-integration.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T091224678110Z-behavior-initial-service-integration/stdout.log) · [stderr.log](../../verification/runs/20261108T091224678110Z-behavior-initial-service-integration/stderr.log)

````text
E       AssertionError: Internal ValidationError. See the failed job event; no result was certified.
E       assert 'failed' == 'completed'
E         
````

## 20261108T091242297122Z-behavior-valid-context-configuration

[Receipt](../../verification/receipts/20261108T091242297122Z-behavior-valid-context-configuration.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T091242297122Z-behavior-valid-context-configuration/stdout.log) · [stderr.log](../../verification/runs/20261108T091242297122Z-behavior-valid-context-configuration/stderr.log)

````text
E       AssertionError: Internal NameError. See the failed job event; no result was certified.
E       assert 'failed' == 'completed'
E         
````

## 20261108T091319535584Z-behavior-direct-diagnostic

[Receipt](../../verification/receipts/20261108T091319535584Z-behavior-direct-diagnostic.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T091319535584Z-behavior-direct-diagnostic/stdout.log) · [stderr.log](../../verification/runs/20261108T091319535584Z-behavior-direct-diagnostic/stderr.log)

````text
Traceback (most recent call last):
````

## 20261108T091606459611Z-behavior-window-and-uncertainty-first

[Receipt](../../verification/receipts/20261108T091606459611Z-behavior-window-and-uncertainty-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T091606459611Z-behavior-window-and-uncertainty-first/stdout.log) · [stderr.log](../../verification/runs/20261108T091606459611Z-behavior-window-and-uncertainty-first/stderr.log)

````text
E       AssertionError: assert (1.0 == 1 and {'low': 1.0, 'high': 1.0, 'method': 'IID whole sessions; paired real/control session draws', 'resamples': 2000, ...} is None)
E       AssertionError: assert {'timeframe':....}, ...], ...} == {'timeframe':....}, ...], ...}
E         
````

## 20261108T092003194990Z-behavior-causal-birth-and-invalidation-first

[Receipt](../../verification/receipts/20261108T092003194990Z-behavior-causal-birth-and-invalidation-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T092003194990Z-behavior-causal-birth-and-invalidation-first/stdout.log) · [stderr.log](../../verification/runs/20261108T092003194990Z-behavior-causal-birth-and-invalidation-first/stderr.log)

````text
E                   KeyError: '2026-10-05T13:45:00+00:00'
FAILED tests/test_behavior.py::test_shifted_geometry_already_invalid_at_birth_never_reopens
````

## 20261108T092125857899Z-behavior-invalid-birth-recovery-counterexample

[Receipt](../../verification/receipts/20261108T092125857899Z-behavior-invalid-birth-recovery-counterexample.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T092125857899Z-behavior-invalid-birth-recovery-counterexample/stdout.log) · [stderr.log](../../verification/runs/20261108T092125857899Z-behavior-invalid-birth-recovery-counterexample/stderr.log)

````text
E       AssertionError: assert not [{'id': 'd863a0e84e21b11be0cec559', 'feature_id': 'e4cb58adc73e8c723b709fd9', 'kind': 'gap', 'shape': 'zone', ...}]
FAILED tests/test_behavior.py::test_shifted_geometry_already_invalid_at_birth_never_reopens
````

## 20261108T093552008356Z-behavior-two-real-desktop-browser-journeys

[Receipt](../../verification/receipts/20261108T093552008356Z-behavior-two-real-desktop-browser-journeys.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T093552008356Z-behavior-two-real-desktop-browser-journeys/stdout.log) · [stderr.log](../../verification/runs/20261108T093552008356Z-behavior-two-real-desktop-browser-journeys/stderr.log)

````text
    Error: expect(received).toBe(expected) // Object.is equality
````

## 20261108T094138926614Z-nine-module-behavior-numerical-coverage

[Receipt](../../verification/receipts/20261108T094138926614Z-nine-module-behavior-numerical-coverage.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T094138926614Z-nine-module-behavior-numerical-coverage/stdout.log) · [stderr.log](../../verification/runs/20261108T094138926614Z-nine-module-behavior-numerical-coverage/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T095057611382Z-behavior-current-all-ten-real-browser-journeys

[Receipt](../../verification/receipts/20261108T095057611382Z-behavior-current-all-ten-real-browser-journeys.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T095057611382Z-behavior-current-all-ten-real-browser-journeys/stdout.log) · [stderr.log](../../verification/runs/20261108T095057611382Z-behavior-current-all-ten-real-browser-journeys/stderr.log)

````text
    Error: expect(locator).toBeVisible() failed
    Error: element(s) not found
````

## 20261108T095057678841Z-behavior-699-nine-module-final-coverage

[Receipt](../../verification/receipts/20261108T095057678841Z-behavior-699-nine-module-final-coverage.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T095057678841Z-behavior-699-nine-module-final-coverage/stdout.log) · [stderr.log](../../verification/runs/20261108T095057678841Z-behavior-699-nine-module-final-coverage/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T095413211090Z-behavior-378-case-release-still-unmet

[Receipt](../../verification/receipts/20261108T095413211090Z-behavior-378-case-release-still-unmet.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T095413211090Z-behavior-378-case-release-still-unmet/stdout.log) · [stderr.log](../../verification/runs/20261108T095413211090Z-behavior-378-case-release-still-unmet/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T095727515392Z-behavior-encoding-and-prior-inventory-first-failure

[Receipt](../../verification/receipts/20261108T095727515392Z-behavior-encoding-and-prior-inventory-first-failure.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T095727515392Z-behavior-encoding-and-prior-inventory-first-failure/stdout.log) · [stderr.log](../../verification/runs/20261108T095727515392Z-behavior-encoding-and-prior-inventory-first-failure/stderr.log)

````text
Traceback (most recent call last):
AssertionError: {'original351_catalog_unchanged': False, 'portfolio_separator_correct': False, 'rulebook_title_correct': False}
````

## 20261108T095833807535Z-behavior-encoding-and-exact-inventory-regression

[Receipt](../../verification/receipts/20261108T095833807535Z-behavior-encoding-and-exact-inventory-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T095833807535Z-behavior-encoding-and-exact-inventory-regression/stdout.log) · [stderr.log](../../verification/runs/20261108T095833807535Z-behavior-encoding-and-exact-inventory-regression/stderr.log)

````text
E       AssertionError: assert '51dc78805f29...26870bbba1ed4' == 'da886c4b84a8...56fff9499c86b'
E         
E         - da886c4b84a8f42ab68c34ec838d468188cefb7a6c955984e6656fff9499c86b
````

## 20261108T100650269793Z-utf8-restored-701-nine-module-coverage-gate

[Receipt](../../verification/receipts/20261108T100650269793Z-utf8-restored-701-nine-module-coverage-gate.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T100650269793Z-utf8-restored-701-nine-module-coverage-gate/stdout.log) · [stderr.log](../../verification/runs/20261108T100650269793Z-utf8-restored-701-nine-module-coverage-gate/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T101637931151Z-current-four-single-and-control-books-independent-proof

[Receipt](../../verification/receipts/20261108T101637931151Z-current-four-single-and-control-books-independent-proof.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T101637931151Z-current-four-single-and-control-books-independent-proof/stdout.log) · [stderr.log](../../verification/runs/20261108T101637931151Z-current-four-single-and-control-books-independent-proof/stderr.log)

````text
Traceback (most recent call last):
AssertionError
````

## 20261108T101741281653Z-current-four-single-and-control-independent-interval-regression

[Receipt](../../verification/receipts/20261108T101741281653Z-current-four-single-and-control-independent-interval-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T101741281653Z-current-four-single-and-control-independent-interval-regression/stdout.log) · [stderr.log](../../verification/runs/20261108T101741281653Z-current-four-single-and-control-independent-interval-regression/stderr.log)

````text
Traceback (most recent call last):
````

## 20261108T101846695615Z-current-378-case-release-not-ready

[Receipt](../../verification/receipts/20261108T101846695615Z-current-378-case-release-not-ready.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T101846695615Z-current-378-case-release-not-ready/stdout.log) · [stderr.log](../../verification/runs/20261108T101846695615Z-current-378-case-release-not-ready/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T103516330406Z-ablation-and-trial-ledger-contract-first-execution

[Receipt](../../verification/receipts/20261108T103516330406Z-ablation-and-trial-ledger-contract-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T103516330406Z-ablation-and-trial-ledger-contract-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T103516330406Z-ablation-and-trial-ledger-contract-first-execution/stderr.log)

````text
E       assert None is not None
E       ModuleNotFoundError: No module named 'backend.lab.ablations'
E       AttributeError: 'Store' object has no attribute 'registry'
````

## 20261108T103937852007Z-ablation-pair-and-registry-foundation-first-implementation

[Receipt](../../verification/receipts/20261108T103937852007Z-ablation-pair-and-registry-foundation-first-implementation.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T103937852007Z-ablation-pair-and-registry-foundation-first-implementation/stdout.log) · [stderr.log](../../verification/runs/20261108T103937852007Z-ablation-pair-and-registry-foundation-first-implementation/stderr.log)

````text
E       AttributeError: 'Lab' object has no attribute 'create_ablation'. Did you mean: 'create_behavior'?
FAILED tests/test_ablations.py::test_actual_ablation_worker_saves_frozen_arms_comparisons_and_trials
FAILED tests/test_ablations.py::test_ablation_payload_tamper_rejects_before_price_reads
````

## 20261108T105038919864Z-ledger-durability-and-ablation-recovery-first-boundaries

[Receipt](../../verification/receipts/20261108T105038919864Z-ledger-durability-and-ablation-recovery-first-boundaries.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T105038919864Z-ledger-durability-and-ablation-recovery-first-boundaries/stdout.log) · [stderr.log](../../verification/runs/20261108T105038919864Z-ledger-durability-and-ablation-recovery-first-boundaries/stderr.log)

````text
E       Failed: DID NOT RAISE StateError
FAILED tests/test_trial_registry.py::test_a_computed_but_unpublished_numeric_trial_cannot_complete_its_job
````

## 20261108T105837799313Z-no-match-control-ledger-resume-first-counterexample

[Receipt](../../verification/receipts/20261108T105837799313Z-no-match-control-ledger-resume-first-counterexample.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T105837799313Z-no-match-control-ledger-resume-first-counterexample/stdout.log) · [stderr.log](../../verification/runs/20261108T105837799313Z-no-match-control-ledger-resume-first-counterexample/stderr.log)

````text
E       AssertionError: Only an unstarted random replica without a matched source may be ungenerated.
E       assert 'failed' == 'completed'
E         
````

## 20261108T110238263734Z-streamed-ledger-thread-handoff-first-counterexample

[Receipt](../../verification/receipts/20261108T110238263734Z-streamed-ledger-thread-handoff-first-counterexample.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T110238263734Z-streamed-ledger-thread-handoff-first-counterexample/stdout.log) · [stderr.log](../../verification/runs/20261108T110238263734Z-streamed-ledger-thread-handoff-first-counterexample/stderr.log)

````text
E           sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread. The object was created in thread id 49252 and this is thread id 43900.
E       sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread. The object was created in thread id 49252 and this is thread id 43900.
FAILED tests/test_trial_registry.py::test_streamed_export_can_handoff_threads_and_keeps_one_read_snapshot
````

## 20261108T110713483345Z-paired-short-block-uncertainty-first-counterexample

[Receipt](../../verification/receipts/20261108T110713483345Z-paired-short-block-uncertainty-first-counterexample.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T110713483345Z-paired-short-block-uncertainty-first-counterexample/stdout.log) · [stderr.log](../../verification/runs/20261108T110713483345Z-paired-short-block-uncertainty-first-counterexample/stderr.log)

````text
E       AssertionError: assert (10.0 == 10 and {'low': 10.0, 'high': 10.0, 'unit': 'dollars', 'method': 'circular moving blocks of daily P&L', ...} is None)
FAILED tests/test_ablations.py::test_one_resampling_block_is_not_reported_as_precise_uncertainty
````

## 20261108T112823081358Z-four-historical-paired-accounts-independent-reference

[Receipt](../../verification/receipts/20261108T112823081358Z-four-historical-paired-accounts-independent-reference.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T112823081358Z-four-historical-paired-accounts-independent-reference/stdout.log) · [stderr.log](../../verification/runs/20261108T112823081358Z-four-historical-paired-accounts-independent-reference/stderr.log)

````text
Traceback (most recent call last):
````

## 20261108T112958130007Z-paired-ledger-two-real-desktop-browser-first

[Receipt](../../verification/receipts/20261108T112958130007Z-paired-ledger-two-real-desktop-browser-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T112958130007Z-paired-ledger-two-real-desktop-browser-first/stdout.log) · [stderr.log](../../verification/runs/20261108T112958130007Z-paired-ledger-two-real-desktop-browser-first/stderr.log)

````text
    Error: expect(locator).toBeChecked() failed
````

## 20261108T113834940927Z-paired-ledger-762-eleven-module-coverage-gate

[Receipt](../../verification/receipts/20261108T113834940927Z-paired-ledger-762-eleven-module-coverage-gate.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T113834940927Z-paired-ledger-762-eleven-module-coverage-gate/stdout.log) · [stderr.log](../../verification/runs/20261108T113834940927Z-paired-ledger-762-eleven-module-coverage-gate/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T115131252698Z-paired-ledger-current-780-numerical-coverage-gate

[Receipt](../../verification/receipts/20261108T115131252698Z-paired-ledger-current-780-numerical-coverage-gate.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T115131252698Z-paired-ledger-current-780-numerical-coverage-gate/stdout.log) · [stderr.log](../../verification/runs/20261108T115131252698Z-paired-ledger-current-780-numerical-coverage-gate/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T115131336333Z-current-397-case-release-not-ready

[Receipt](../../verification/receipts/20261108T115131336333Z-current-397-case-release-not-ready.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T115131336333Z-current-397-case-release-not-ready/stdout.log) · [stderr.log](../../verification/runs/20261108T115131336333Z-current-397-case-release-not-ready/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T115455903678Z-current-twelve-suite-five-symbol-behavior-independent-reference

[Receipt](../../verification/receipts/20261108T115455903678Z-current-twelve-suite-five-symbol-behavior-independent-reference.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T115455903678Z-current-twelve-suite-five-symbol-behavior-independent-reference/stdout.log) · [stderr.log](../../verification/runs/20261108T115455903678Z-current-twelve-suite-five-symbol-behavior-independent-reference/stderr.log)

````text
Traceback (most recent call last):
AssertionError
````

## 20261108T121855293651Z-confirmation-and-filter-authored-boundaries-first-execution

[Receipt](../../verification/receipts/20261108T121855293651Z-confirmation-and-filter-authored-boundaries-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T121855293651Z-confirmation-and-filter-authored-boundaries-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T121855293651Z-confirmation-and-filter-authored-boundaries-first-execution/stderr.log)

````text
E       AttributeError: 'Signal' object has no attribute 'target'
E       assert (0 == 1)
E        +  where 0 = len([])
````

## 20261108T121932120377Z-confirmation-filter-correct-signal-schema-day-boundary-counterexamples

[Receipt](../../verification/receipts/20261108T121932120377Z-confirmation-filter-correct-signal-schema-day-boundary-counterexamples.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T121932120377Z-confirmation-filter-correct-signal-schema-day-boundary-counterexamples/stdout.log) · [stderr.log](../../verification/runs/20261108T121932120377Z-confirmation-filter-correct-signal-schema-day-boundary-counterexamples/stderr.log)

````text
E       assert (0 == 1)
E        +  where 0 = len([])
E       AssertionError: assert (1 == 1 and Timestamp('2026-10-06 14:00:00+0000', tz='UTC') == Timestamp('2026-10-06 14:00:00+0000', tz='UTC') and 0.5 == 1)
````

## 20261108T122727849381Z-data-and-service-authored-input-history-and-integrity-first-execution

[Receipt](../../verification/receipts/20261108T122727849381Z-data-and-service-authored-input-history-and-integrity-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T122727849381Z-data-and-service-authored-input-history-and-integrity-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T122727849381Z-data-and-service-authored-input-history-and-integrity-first-execution/stderr.log)

````text
E   Failed: Unsupported news read prices before rejection
E                   backend.lab.store.StateError: This study job is already queued or running.
FAILED tests/test_data_service_boundaries.py::test_unsupported_control_news_rejects_before_raw_input_loading[skip]
````

## 20261108T124047826056Z-authored-overnight-ten-real-pipeline-api-and-independent-account-cases

[Receipt](../../verification/receipts/20261108T124047826056Z-authored-overnight-ten-real-pipeline-api-and-independent-account-cases.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T124047826056Z-authored-overnight-ten-real-pipeline-api-and-independent-account-cases/stdout.log) · [stderr.log](../../verification/runs/20261108T124047826056Z-authored-overnight-ten-real-pipeline-api-and-independent-account-cases/stderr.log)

````text
Traceback (most recent call last):
TypeError: Headers.update() got an unexpected keyword argument 'Origin'
````

## 20261108T124621719311Z-confirmation-calendar-397-case-release-not-ready

[Receipt](../../verification/receipts/20261108T124621719311Z-confirmation-calendar-397-case-release-not-ready.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T124621719311Z-confirmation-calendar-397-case-release-not-ready/stdout.log) · [stderr.log](../../verification/runs/20261108T124621719311Z-confirmation-calendar-397-case-release-not-ready/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T130944078582Z-trace-privacy-authored-contract-first-execution

[Receipt](../../verification/receipts/20261108T130944078582Z-trace-privacy-authored-contract-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T130944078582Z-trace-privacy-authored-contract-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T130944078582Z-trace-privacy-authored-contract-first-execution/stderr.log)

````text
E   ModuleNotFoundError: No module named 'verification.trace_privacy'
FAILED tests/test_trace_privacy.py::test_actual_named_credential_contexts_are_removed_without_touching_financial_values
FAILED tests/test_trace_privacy.py::test_deterministic_and_idempotent_review_archives
````

## 20261108T133317847384Z-verification-plan-v3-release-remains-incomplete

[Receipt](../../verification/receipts/20261108T133317847384Z-verification-plan-v3-release-remains-incomplete.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T133317847384Z-verification-plan-v3-release-remains-incomplete/stdout.log) · [stderr.log](../../verification/runs/20261108T133317847384Z-verification-plan-v3-release-remains-incomplete/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T133812880008Z-offline-presenter-authored-contract-first-execution

[Receipt](../../verification/receipts/20261108T133812880008Z-offline-presenter-authored-contract-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T133812880008Z-offline-presenter-authored-contract-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T133812880008Z-offline-presenter-authored-contract-first-execution/stderr.log)

````text
E       ModuleNotFoundError: No module named 'backend.lab.presenter'
E       ModuleNotFoundError: No module named 'backend.lab.presentation_audit'
FAILED tests/test_presenter.py::test_account_facts_and_private_projection - M...
````

## 20261108T134320435456Z-offline-presenter-first-adapter-and-independent-reader-execution

[Receipt](../../verification/receipts/20261108T134320435456Z-offline-presenter-first-adapter-and-independent-reader-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T134320435456Z-offline-presenter-first-adapter-and-independent-reader-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T134320435456Z-offline-presenter-first-adapter-and-independent-reader-execution/stderr.log)

````text
E       assert ("connect-src 'none'" in '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-...entListener(\'resize\',resize);addEventListener(\'hashchange\',jumpHash);resize();jumpHash();\n</script></body></html>')
FAILED tests/test_presenter.py::test_escaped_inert_offline_document_and_determinism
````

## 20261108T134919013313Z-offline-presenter-first-real-two-desktop-offline-pages

[Receipt](../../verification/receipts/20261108T134919013313Z-offline-presenter-first-real-two-desktop-offline-pages.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T134919013313Z-offline-presenter-first-real-two-desktop-offline-pages/stdout.log) · [stderr.log](../../verification/runs/20261108T134919013313Z-offline-presenter-first-real-two-desktop-offline-pages/stderr.log) · [runner-stderr.log](../../verification/runs/20261108T134919013313Z-offline-presenter-first-real-two-desktop-offline-pages/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261108T134919013313Z-offline-presenter-first-real-two-desktop-offline-pages/browser/runner-stdout.log)

````text
Traceback (most recent call last):
````

## 20261108T135115283446Z-offline-presenter-two-desktop-source-selection-and-offline-first-retry

[Receipt](../../verification/receipts/20261108T135115283446Z-offline-presenter-two-desktop-source-selection-and-offline-first-retry.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T135115283446Z-offline-presenter-two-desktop-source-selection-and-offline-first-retry/stdout.log) · [stderr.log](../../verification/runs/20261108T135115283446Z-offline-presenter-two-desktop-source-selection-and-offline-first-retry/stderr.log) · [runner-stderr.log](../../verification/runs/20261108T135115283446Z-offline-presenter-two-desktop-source-selection-and-offline-first-retry/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261108T135115283446Z-offline-presenter-two-desktop-source-selection-and-offline-first-retry/browser/runner-stdout.log)

````text
    Error: Page 158: Rule comparison
    Error: Page 159: Rule comparison
    Error: Page 160: Rule comparison
````

## 20261108T135815771439Z-offline-presenter-fixed-glyph-two-desktop-every-page-offline

[Receipt](../../verification/receipts/20261108T135815771439Z-offline-presenter-fixed-glyph-two-desktop-every-page-offline.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T135815771439Z-offline-presenter-fixed-glyph-two-desktop-every-page-offline/stdout.log) · [stderr.log](../../verification/runs/20261108T135815771439Z-offline-presenter-fixed-glyph-two-desktop-every-page-offline/stderr.log) · [runner-stderr.log](../../verification/runs/20261108T135815771439Z-offline-presenter-fixed-glyph-two-desktop-every-page-offline/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261108T135815771439Z-offline-presenter-fixed-glyph-two-desktop-every-page-offline/browser/runner-stdout.log)

````text
    Error: expect(received).toEqual(expected) // deep equality
````

## 20261108T135815795707Z-presenter-current-full-regression-and-numerical-coverage

[Receipt](../../verification/receipts/20261108T135815795707Z-presenter-current-full-regression-and-numerical-coverage.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T135815795707Z-presenter-current-full-regression-and-numerical-coverage/stdout.log) · [stderr.log](../../verification/runs/20261108T135815795707Z-presenter-current-full-regression-and-numerical-coverage/stderr.log)

````text
E       KeyError: 'id'
E       AssertionError: assert False
E        +  where False = <built-in method startswith of str object at 0x000001C9B97431E0>('# Numerical rulebook � version 0.11')
````

## 20261108T135933642335Z-sanitized-two-trace-installed-viewer-playback-first

[Receipt](../../verification/receipts/20261108T135933642335Z-sanitized-two-trace-installed-viewer-playback-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T135933642335Z-sanitized-two-trace-installed-viewer-playback-first/stdout.log) · [stderr.log](../../verification/runs/20261108T135933642335Z-sanitized-two-trace-installed-viewer-playback-first/stderr.log)

````text
locator.click: Timeout 30000ms exceeded.
````

## 20261108T140024490172Z-sanitized-trace-viewer-load-dialog-diagnostic

[Receipt](../../verification/receipts/20261108T140024490172Z-sanitized-trace-viewer-load-dialog-diagnostic.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T140024490172Z-sanitized-trace-viewer-load-dialog-diagnostic/stdout.log) · [stderr.log](../../verification/runs/20261108T140024490172Z-sanitized-trace-viewer-load-dialog-diagnostic/stderr.log)

````text
locator.click: Timeout 30000ms exceeded.
````

## 20261108T140127274867Z-sanitized-trace-viewer-local-file-route-playback

[Receipt](../../verification/receipts/20261108T140127274867Z-sanitized-trace-viewer-local-file-route-playback.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T140127274867Z-sanitized-trace-viewer-local-file-route-playback/stdout.log) · [stderr.log](../../verification/runs/20261108T140127274867Z-sanitized-trace-viewer-local-file-route-playback/stderr.log)

````text
Error: element(s) not found
````

## 20261108T140244647494Z-sanitized-trace-viewer-authored-action-source-and-network

[Receipt](../../verification/receipts/20261108T140244647494Z-sanitized-trace-viewer-authored-action-source-and-network.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T140244647494Z-sanitized-trace-viewer-authored-action-source-and-network/stdout.log) · [stderr.log](../../verification/runs/20261108T140244647494Z-sanitized-trace-viewer-authored-action-source-and-network/stderr.log)

````text
locator.click: Timeout 30000ms exceeded.
````

## 20261108T142817428557Z-presenter-current-397-case-release-remains-incomplete

[Receipt](../../verification/receipts/20261108T142817428557Z-presenter-current-397-case-release-remains-incomplete.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T142817428557Z-presenter-current-397-case-release-remains-incomplete/stdout.log) · [stderr.log](../../verification/runs/20261108T142817428557Z-presenter-current-397-case-release-remains-incomplete/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T144134668098Z-news-calendar-authored-clock-immutability-and-official-date-first-execution

[Receipt](../../verification/receipts/20261108T144134668098Z-news-calendar-authored-clock-immutability-and-official-date-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T144134668098Z-news-calendar-authored-clock-immutability-and-official-date-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T144134668098Z-news-calendar-authored-clock-immutability-and-official-date-first-execution/stderr.log)

````text
E       ModuleNotFoundError: No module named 'backend.lab.news'
FAILED tests/test_news.py::test_immutable_idempotent_versions_and_reordered_events
FAILED tests/test_news.py::test_invalid_calendar_contract[updates0] - ModuleN...
````

## 20261108T144412281144Z-news-calendar-first-immutable-store-clock-and-official-parser-implementation

[Receipt](../../verification/receipts/20261108T144412281144Z-news-calendar-first-immutable-store-clock-and-official-parser-implementation.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T144412281144Z-news-calendar-first-immutable-store-clock-and-official-parser-implementation/stdout.log) · [stderr.log](../../verification/runs/20261108T144412281144Z-news-calendar-first-immutable-store-clock-and-official-parser-implementation/stderr.log)

````text
E   RecursionError: maximum recursion depth exceeded
FAILED tests/test_news.py::test_immutable_idempotent_versions_and_reordered_events
FAILED tests/test_news.py::test_asof_clock_exact_knowledge_boundary[2022-01-12T14:30:00Z-2022-01-12T14:29:59.999999Z-False]
````

## 20261108T151434663364Z-news-calendar-first-real-official-import-account-and-offline-browser

[Receipt](../../verification/receipts/20261108T151434663364Z-news-calendar-first-real-official-import-account-and-offline-browser.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T151434663364Z-news-calendar-first-real-official-import-account-and-offline-browser/stdout.log) · [stderr.log](../../verification/runs/20261108T151434663364Z-news-calendar-first-real-official-import-account-and-offline-browser/stderr.log) · [runner-stderr.log](../../verification/runs/20261108T151434663364Z-news-calendar-first-real-official-import-account-and-offline-browser/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261108T151434663364Z-news-calendar-first-real-official-import-account-and-offline-browser/browser/runner-stdout.log)

````text
    Error: expect(locator).toBeVisible() failed
    Error: element(s) not found
````

## 20261108T152001524913Z-news-calendar-after-ordered-build-restart-real-browser

[Receipt](../../verification/receipts/20261108T152001524913Z-news-calendar-after-ordered-build-restart-real-browser.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T152001524913Z-news-calendar-after-ordered-build-restart-real-browser/stdout.log) · [stderr.log](../../verification/runs/20261108T152001524913Z-news-calendar-after-ordered-build-restart-real-browser/stderr.log) · [runner-stderr.log](../../verification/runs/20261108T152001524913Z-news-calendar-after-ordered-build-restart-real-browser/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261108T152001524913Z-news-calendar-after-ordered-build-restart-real-browser/browser/runner-stdout.log)

````text
    TimeoutError: locator.selectOption: Timeout 15000ms exceeded.
````

## 20261108T152242689821Z-news-calendar-complete-ui-navigation-account-and-offline-retry

[Receipt](../../verification/receipts/20261108T152242689821Z-news-calendar-complete-ui-navigation-account-and-offline-retry.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T152242689821Z-news-calendar-complete-ui-navigation-account-and-offline-retry/stdout.log) · [stderr.log](../../verification/runs/20261108T152242689821Z-news-calendar-complete-ui-navigation-account-and-offline-retry/stderr.log) · [runner-stderr.log](../../verification/runs/20261108T152242689821Z-news-calendar-complete-ui-navigation-account-and-offline-retry/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261108T152242689821Z-news-calendar-complete-ui-navigation-account-and-offline-retry/browser/runner-stdout.log)

````text
    Error: expect(locator).toBeVisible() failed
    Error: element(s) not found
````

## 20261108T153302065465Z-news-explicit-input-and-source-metadata-authored-counterexamples

[Receipt](../../verification/receipts/20261108T153302065465Z-news-explicit-input-and-source-metadata-authored-counterexamples.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T153302065465Z-news-explicit-input-and-source-metadata-authored-counterexamples/stdout.log) · [stderr.log](../../verification/runs/20261108T153302065465Z-news-explicit-input-and-source-metadata-authored-counterexamples/stderr.log)

````text
E           Failed: DID NOT RAISE ValueError
E       Failed: DID NOT RAISE ValueError
E       Failed: DID NOT RAISE DataError
````

## 20261108T153544815535Z-news-worker-recovery-final-transition-and-result-reuse-first-execution

[Receipt](../../verification/receipts/20261108T153544815535Z-news-worker-recovery-final-transition-and-result-reuse-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T153544815535Z-news-worker-recovery-final-transition-and-result-reuse-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T153544815535Z-news-worker-recovery-final-transition-and-result-reuse-first-execution/stderr.log)

````text
E       backend.lab.store.StateError: Results are available only after successful completion.
FAILED tests/test_news_integration.py::test_worker_revalidates_calendar_sources_before_reusing_saved_download_result
````

## 20261108T153621468193Z-news-saved-download-source-corruption-actual-reuse-counterexample

[Receipt](../../verification/receipts/20261108T153621468193Z-news-saved-download-source-corruption-actual-reuse-counterexample.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T153621468193Z-news-saved-download-source-corruption-actual-reuse-counterexample/stdout.log) · [stderr.log](../../verification/runs/20261108T153621468193Z-news-saved-download-source-corruption-actual-reuse-counterexample/stderr.log)

````text
E       AssertionError: assert 'completed' == 'failed'
E         
E         - failed
````

## 20261108T153751663209Z-release-gate-private-and-renamed-raw-trace-authored-counterexamples

[Receipt](../../verification/receipts/20261108T153751663209Z-release-gate-private-and-renamed-raw-trace-authored-counterexamples.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T153751663209Z-release-gate-private-and-renamed-raw-trace-authored-counterexamples/stdout.log) · [stderr.log](../../verification/runs/20261108T153751663209Z-release-gate-private-and-renamed-raw-trace-authored-counterexamples/stderr.log)

````text
E       assert (1 == 0)
FAILED tests/test_release_evidence.py::test_independently_audited_derived_trace_can_be_a_scoped_artifact
````

## 20261108T153816414203Z-release-gate-private-and-renamed-raw-traces-with-complete-log-counterexamples

[Receipt](../../verification/receipts/20261108T153816414203Z-release-gate-private-and-renamed-raw-traces-with-complete-log-counterexamples.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T153816414203Z-release-gate-private-and-renamed-raw-traces-with-complete-log-counterexamples/stdout.log) · [stderr.log](../../verification/runs/20261108T153816414203Z-release-gate-private-and-renamed-raw-traces-with-complete-log-counterexamples/stderr.log)

````text
E       assert (0 == 1)
FAILED tests/test_release_evidence.py::test_private_or_raw_trace_artifact_cannot_certify_even_with_valid_hash[private_root]
FAILED tests/test_release_evidence.py::test_private_or_raw_trace_artifact_cannot_certify_even_with_valid_hash[raw_zip]
````

## 20261108T154448769441Z-strict-news-current-411-release-remains-incomplete

[Receipt](../../verification/receipts/20261108T154448769441Z-strict-news-current-411-release-remains-incomplete.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T154448769441Z-strict-news-current-411-release-remains-incomplete/stdout.log) · [stderr.log](../../verification/runs/20261108T154448769441Z-strict-news-current-411-release-remains-incomplete/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T155946960245Z-borrow-authored-schema-clock-minute-weekend-recall-first-execution

[Receipt](../../verification/receipts/20261108T155946960245Z-borrow-authored-schema-clock-minute-weekend-recall-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T155946960245Z-borrow-authored-schema-clock-minute-weekend-recall-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T155946960245Z-borrow-authored-schema-clock-minute-weekend-recall-first-execution/stderr.log)

````text
E       ModuleNotFoundError: No module named 'backend.lab.borrow'
E       pydantic_core._pydantic_core.ValidationError: 1 validation error for Costs
E       borrow_scenario
````

## 20261108T160148835114Z-borrow-first-piecewise-clock-engine-and-independent-reference

[Receipt](../../verification/receipts/20261108T160148835114Z-borrow-first-piecewise-clock-engine-and-independent-reference.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T160148835114Z-borrow-first-piecewise-clock-engine-and-independent-reference/stdout.log) · [stderr.log](../../verification/runs/20261108T160148835114Z-borrow-first-piecewise-clock-engine-and-independent-reference/stderr.log)

````text
E           ValueError: Borrow decisions require an aware timestamp.
E       AssertionError: assert Decimal('1.11111111111E-30') < Decimal('1E-30')
E        +  where Decimal('1.11111111111E-30') = abs((Decimal('0.01701388888888888888888888888888888888889') - Decimal('0.01701388888888888888888888889')))
````

## 20261108T160849507956Z-borrow-api-scope-job-freeze-positive-account-final-and-presenter-first-integration

[Receipt](../../verification/receipts/20261108T160849507956Z-borrow-api-scope-job-freeze-positive-account-final-and-presenter-first-integration.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T160849507956Z-borrow-api-scope-job-freeze-positive-account-final-and-presenter-first-integration/stdout.log) · [stderr.log](../../verification/runs/20261108T160849507956Z-borrow-api-scope-job-freeze-positive-account-final-and-presenter-first-integration/stderr.log)

````text
E       assert 422 == 409
E        +  where 422 = <Response [422 Unprocessable Entity]>.status_code
E        +    where <Response [422 Unprocessable Entity]> = post('/api/borrow-scenarios/validate', content='{"name": "Authored borrowing", "start": "2026-11-02", "end": "2026-11-06", "symbols": ["SPY"], "complete": true, "mod...2026-11-04T09:31:00-05:00", "annual_rate": 0.365, "available": true, "recall": false}],"name":"conflicting duplicate"}')
````

## 20261108T161015505783Z-borrow-strict-rate-type-counterexamples-and-corrected-api-presenter-verifiers

[Receipt](../../verification/receipts/20261108T161015505783Z-borrow-strict-rate-type-counterexamples-and-corrected-api-presenter-verifiers.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T161015505783Z-borrow-strict-rate-type-counterexamples-and-corrected-api-presenter-verifiers/stdout.log) · [stderr.log](../../verification/runs/20261108T161015505783Z-borrow-strict-rate-type-counterexamples-and-corrected-api-presenter-verifiers/stderr.log)

````text
E       Failed: DID NOT RAISE ValueError
FAILED tests/test_borrow.py::test_invalid_borrow_schema[change13] - Failed: D...
FAILED tests/test_borrow.py::test_invalid_borrow_schema[change14] - Failed: D...
````

## 20261108T161413971812Z-borrowing-first-real-editor-weekend-recall-ledger-and-offline-two-desktop

[Receipt](../../verification/receipts/20261108T161413971812Z-borrowing-first-real-editor-weekend-recall-ledger-and-offline-two-desktop.json) · command exit `2` · [stdout.log](../../verification/runs/20261108T161413971812Z-borrowing-first-real-editor-weekend-recall-ledger-and-offline-two-desktop/stdout.log) · [stderr.log](../../verification/runs/20261108T161413971812Z-borrowing-first-real-editor-weekend-recall-ledger-and-offline-two-desktop/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T161708646055Z-borrowing-valid-json-error-editor-recall-and-offline-two-desktop

[Receipt](../../verification/receipts/20261108T161708646055Z-borrowing-valid-json-error-editor-recall-and-offline-two-desktop.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T161708646055Z-borrowing-valid-json-error-editor-recall-and-offline-two-desktop/stdout.log) · [stderr.log](../../verification/runs/20261108T161708646055Z-borrowing-valid-json-error-editor-recall-and-offline-two-desktop/stderr.log) · [runner-stderr.log](../../verification/runs/20261108T161708646055Z-borrowing-valid-json-error-editor-recall-and-offline-two-desktop/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261108T161708646055Z-borrowing-valid-json-error-editor-recall-and-offline-two-desktop/browser/runner-stdout.log)

````text
    Error: expect(received).toEqual(expected) // deep equality
````

## 20261108T162915222463Z-borrowing-current-full-regression-and-thirteen-module-coverage

[Receipt](../../verification/receipts/20261108T162915222463Z-borrowing-current-full-regression-and-thirteen-module-coverage.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T162915222463Z-borrowing-current-full-regression-and-thirteen-module-coverage/stdout.log) · [stderr.log](../../verification/runs/20261108T162915222463Z-borrowing-current-full-regression-and-thirteen-module-coverage/stderr.log)

````text
E       KeyError: 'costs'
FAILED tests/test_data_service_boundaries.py::test_unsupported_control_news_rejects_before_raw_input_loading[skip]
FAILED tests/test_data_service_boundaries.py::test_unsupported_control_news_rejects_before_raw_input_loading[dates]
````

## 20261108T164407419851Z-borrowing-current-422-release-remains-incomplete

[Receipt](../../verification/receipts/20261108T164407419851Z-borrowing-current-422-release-remains-incomplete.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T164407419851Z-borrowing-current-422-release-remains-incomplete/stdout.log) · [stderr.log](../../verification/runs/20261108T164407419851Z-borrowing-current-422-release-remains-incomplete/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T170710516095Z-four-rate-authored-transform-nonlinear-sizing-and-comparison-first-execution

[Receipt](../../verification/receipts/20261108T170710516095Z-four-rate-authored-transform-nonlinear-sizing-and-comparison-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T170710516095Z-four-rate-authored-transform-nonlinear-sizing-and-comparison-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T170710516095Z-four-rate-authored-transform-nonlinear-sizing-and-comparison-first-execution/stderr.log)

````text
E       ModuleNotFoundError: No module named 'backend.lab.sensitivity'
FAILED tests/test_borrow_sensitivity.py::test_fixed_four_cost_arms_preserve_every_nonrate_input_and_original[False]
FAILED tests/test_borrow_sensitivity.py::test_fixed_four_cost_arms_preserve_every_nonrate_input_and_original[True]
````

## 20261108T172753174434Z-four-rate-current-422-release-remains-incomplete

[Receipt](../../verification/receipts/20261108T172753174434Z-four-rate-current-422-release-remains-incomplete.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T172753174434Z-four-rate-current-422-release-remains-incomplete/stdout.log) · [stderr.log](../../verification/runs/20261108T172753174434Z-four-rate-current-422-release-remains-incomplete/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T173127982989Z-four-rate-current-fourteen-module-numerical-coverage-gate

[Receipt](../../verification/receipts/20261108T173127982989Z-four-rate-current-fourteen-module-numerical-coverage-gate.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T173127982989Z-four-rate-current-fourteen-module-numerical-coverage-gate/stdout.log) · [stderr.log](../../verification/runs/20261108T173127982989Z-four-rate-current-fourteen-module-numerical-coverage-gate/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T173845913350Z-four-rate-final-current-422-release-remains-incomplete

[Receipt](../../verification/receipts/20261108T173845913350Z-four-rate-final-current-422-release-remains-incomplete.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T173845913350Z-four-rate-final-current-422-release-remains-incomplete/stdout.log) · [stderr.log](../../verification/runs/20261108T173845913350Z-four-rate-final-current-422-release-remains-incomplete/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T174226243825Z-global-result-overlap-real-saved-accounts-first-reproduction

[Receipt](../../verification/receipts/20261108T174226243825Z-global-result-overlap-real-saved-accounts-first-reproduction.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T174226243825Z-global-result-overlap-real-saved-accounts-first-reproduction/stdout.log) · [stderr.log](../../verification/runs/20261108T174226243825Z-global-result-overlap-real-saved-accounts-first-reproduction/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T182121992027Z-portfolio-study-authored-mode-and-selection-unit-first-execution

[Receipt](../../verification/receipts/20261108T182121992027Z-portfolio-study-authored-mode-and-selection-unit-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T182121992027Z-portfolio-study-authored-mode-and-selection-unit-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T182121992027Z-portfolio-study-authored-mode-and-selection-unit-first-execution/stderr.log)

````text
E       pydantic_core._pydantic_core.ValidationError: 1 validation error for Study
E       study_mode
E         Extra inputs are not permitted [type=extra_forbidden, input_value='portfolio', input_type=str]
````

## 20261108T182341920641Z-portfolio-study-first-joint-screen-final-independent-book-and-freeze-integration

[Receipt](../../verification/receipts/20261108T182341920641Z-portfolio-study-first-joint-screen-final-independent-book-and-freeze-integration.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T182341920641Z-portfolio-study-first-joint-screen-final-independent-book-and-freeze-integration/stdout.log) · [stderr.log](../../verification/runs/20261108T182341920641Z-portfolio-study-first-joint-screen-final-independent-book-and-freeze-integration/stderr.log)

````text
E   RecursionError: maximum recursion depth exceeded
E       pydantic_core._pydantic_core.ValidationError: 1 validation error for Strategy
E       stop_buffer
````

## 20261108T182432742976Z-portfolio-study-canonicalization-recursion-fixed-joint-account-regression

[Receipt](../../verification/receipts/20261108T182432742976Z-portfolio-study-canonicalization-recursion-fixed-joint-account-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T182432742976Z-portfolio-study-canonicalization-recursion-fixed-joint-account-regression/stdout.log) · [stderr.log](../../verification/runs/20261108T182432742976Z-portfolio-study-canonicalization-recursion-fixed-joint-account-regression/stderr.log)

````text
E       pydantic_core._pydantic_core.ValidationError: 1 validation error for Strategy
E       stop_buffer
E         Input should be 0.0, 0.1 or 0.25 [type=literal_error, input_value=0.01, input_type=float]
````

## 20261108T182639673363Z-portfolio-study-explicit-early-target-geometry-and-valid-boundary-input-regression

[Receipt](../../verification/receipts/20261108T182639673363Z-portfolio-study-explicit-early-target-geometry-and-valid-boundary-input-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T182639673363Z-portfolio-study-explicit-early-target-geometry-and-valid-boundary-input-regression/stdout.log) · [stderr.log](../../verification/runs/20261108T182639673363Z-portfolio-study-explicit-early-target-geometry-and-valid-boundary-input-regression/stderr.log)

````text
E       AssertionError: assert 'no_candidates' == 'screened'
E         
E         - screened
````

## 20261108T182935497502Z-portfolio-study-real-negative-controls-and-preconsume-cancel-reservation-first

[Receipt](../../verification/receipts/20261108T182935497502Z-portfolio-study-real-negative-controls-and-preconsume-cancel-reservation-first.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T182935497502Z-portfolio-study-real-negative-controls-and-preconsume-cancel-reservation-first/stdout.log) · [stderr.log](../../verification/runs/20261108T182935497502Z-portfolio-study-real-negative-controls-and-preconsume-cancel-reservation-first/stderr.log)

````text
E       Failed: DID NOT RAISE any of (ResearchError, ValueError)
FAILED tests/test_portfolio_studies.py::test_final_job_reservation_survives_cancel_before_any_consumption
````

## 20261108T185046319958Z-portfolio-study-first-real-import-freeze-screen-final-cancel-resume-offline-two-desktop-journeys

[Receipt](../../verification/receipts/20261108T185046319958Z-portfolio-study-first-real-import-freeze-screen-final-cancel-resume-offline-two-desktop-journeys.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T185046319958Z-portfolio-study-first-real-import-freeze-screen-final-cancel-resume-offline-two-desktop-journeys/stdout.log) · [stderr.log](../../verification/runs/20261108T185046319958Z-portfolio-study-first-real-import-freeze-screen-final-cancel-resume-offline-two-desktop-journeys/stderr.log) · [runner-stderr.log](../../verification/runs/20261108T185046319958Z-portfolio-study-first-real-import-freeze-screen-final-cancel-resume-offline-two-desktop-journeys/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261108T185046319958Z-portfolio-study-first-real-import-freeze-screen-final-cancel-resume-offline-two-desktop-journeys/browser/runner-stdout.log)

````text
    TimeoutError: locator.selectOption: Timeout 15000ms exceeded.
````

## 20261108T185459288548Z-portfolio-study-opened-advanced-controls-real-two-desktop-journeys

[Receipt](../../verification/receipts/20261108T185459288548Z-portfolio-study-opened-advanced-controls-real-two-desktop-journeys.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T185459288548Z-portfolio-study-opened-advanced-controls-real-two-desktop-journeys/stdout.log) · [stderr.log](../../verification/runs/20261108T185459288548Z-portfolio-study-opened-advanced-controls-real-two-desktop-journeys/stderr.log) · [runner-stderr.log](../../verification/runs/20261108T185459288548Z-portfolio-study-opened-advanced-controls-real-two-desktop-journeys/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261108T185459288548Z-portfolio-study-opened-advanced-controls-real-two-desktop-journeys/browser/runner-stdout.log)

````text
    TimeoutError: locator.selectOption: Timeout 15000ms exceeded.
````

## 20261108T185756917317Z-portfolio-study-prespecified-historical-joint-screening-and-independent-accounts

[Receipt](../../verification/receipts/20261108T185756917317Z-portfolio-study-prespecified-historical-joint-screening-and-independent-accounts.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T185756917317Z-portfolio-study-prespecified-historical-joint-screening-and-independent-accounts/stdout.log) · [stderr.log](../../verification/runs/20261108T185756917317Z-portfolio-study-prespecified-historical-joint-screening-and-independent-accounts/stderr.log)

````text
Traceback (most recent call last):
````

## 20261108T185942939348Z-portfolio-study-first-fifteen-module-numerical-and-research-coverage-gate

[Receipt](../../verification/receipts/20261108T185942939348Z-portfolio-study-first-fifteen-module-numerical-and-research-coverage-gate.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T185942939348Z-portfolio-study-first-fifteen-module-numerical-and-research-coverage-gate/stdout.log) · [stderr.log](../../verification/runs/20261108T185942939348Z-portfolio-study-first-fifteen-module-numerical-and-research-coverage-gate/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T190405454361Z-browser-cli-npm-option-forwarding-first-focused-counterexample

[Receipt](../../verification/receipts/20261108T190405454361Z-browser-cli-npm-option-forwarding-first-focused-counterexample.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T190405454361Z-browser-cli-npm-option-forwarding-first-focused-counterexample/stdout.log) · [stderr.log](../../verification/runs/20261108T190405454361Z-browser-cli-npm-option-forwarding-first-focused-counterexample/stderr.log)

````text
E       AssertionError: assert [['exec', 'pl...m.config.ts']] == [['exec', '--...m.config.ts']]
E         
E         At index 0 diff: ['exec', 'playwright', 'test', '--project=desktop1280', '--config=custom.config.ts'] != ['exec', '--', 'playwright', 'test', '--project=desktop1280', '--config=custom.config.ts']
````

## 20261108T192130656769Z-portfolio-study-current-422-release-remains-incomplete

[Receipt](../../verification/receipts/20261108T192130656769Z-portfolio-study-current-422-release-remains-incomplete.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T192130656769Z-portfolio-study-current-422-release-remains-incomplete/stdout.log) · [stderr.log](../../verification/runs/20261108T192130656769Z-portfolio-study-current-422-release-remains-incomplete/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T193649066717Z-portfolio-era-eight-prescribed-source-mutation-domains

[Receipt](../../verification/receipts/20261108T193649066717Z-portfolio-era-eight-prescribed-source-mutation-domains.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T193649066717Z-portfolio-era-eight-prescribed-source-mutation-domains/stdout.log) · [stderr.log](../../verification/runs/20261108T193649066717Z-portfolio-era-eight-prescribed-source-mutation-domains/stderr.log) · [baseline-stderr.log](../../verification/runs/20261108T193649066717Z-portfolio-era-eight-prescribed-source-mutation-domains/baseline-stderr.log) · [baseline-stdout.log](../../verification/runs/20261108T193649066717Z-portfolio-era-eight-prescribed-source-mutation-domains/baseline-stdout.log) · [future-pivot-availability-stderr.log](../../verification/runs/20261108T193649066717Z-portfolio-era-eight-prescribed-source-mutation-domains/future-pivot-availability-stderr.log) · [future-pivot-availability-stdout.log](../../verification/runs/20261108T193649066717Z-portfolio-era-eight-prescribed-source-mutation-domains/future-pivot-availability-stdout.log)

````text
Traceback (most recent call last):
AssertionError: ('future-pivot-availability', {'exit_code': 0, 'tests': 101, 'failures': 0, 'errors': 0, 'skipped': 0})
````

## 20261108T195458151748Z-runtime-capacity-authored-contract-first-execution

[Receipt](../../verification/receipts/20261108T195458151748Z-runtime-capacity-authored-contract-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T195458151748Z-runtime-capacity-authored-contract-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T195458151748Z-runtime-capacity-authored-contract-first-execution/stderr.log)

````text
E           sqlite3.DatabaseError: access to jobs.payload is prohibited
E           AttributeError: 'Store' object has no attribute 'cancellation_requested'
E       AssertionError: ('Full plans were read in the per-bar/per-part control loop', 125, 3)
````

## 20261108T201100191762Z-runtime-capacity-current-main-prespecified-historical-joint-account-replay

[Receipt](../../verification/receipts/20261108T201100191762Z-runtime-capacity-current-main-prespecified-historical-joint-account-replay.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T201100191762Z-runtime-capacity-current-main-prespecified-historical-joint-account-replay/stdout.log) · [stderr.log](../../verification/runs/20261108T201100191762Z-runtime-capacity-current-main-prespecified-historical-joint-account-replay/stderr.log)

````text
Traceback (most recent call last):
````

## 20261108T203327442088Z-runtime-capacity-current-422-release-remains-incomplete

[Receipt](../../verification/receipts/20261108T203327442088Z-runtime-capacity-current-422-release-remains-incomplete.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T203327442088Z-runtime-capacity-current-422-release-remains-incomplete/stdout.log) · [stderr.log](../../verification/runs/20261108T203327442088Z-runtime-capacity-current-422-release-remains-incomplete/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T203846010487Z-runtime-capacity-current-code-fixture-build-and-twenty-receipt-recovery-checkpoint

[Receipt](../../verification/receipts/20261108T203846010487Z-runtime-capacity-current-code-fixture-build-and-twenty-receipt-recovery-checkpoint.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T203846010487Z-runtime-capacity-current-code-fixture-build-and-twenty-receipt-recovery-checkpoint/stdout.log) · [stderr.log](../../verification/runs/20261108T203846010487Z-runtime-capacity-current-code-fixture-build-and-twenty-receipt-recovery-checkpoint/stderr.log)

````text
Traceback (most recent call last):
````

## 20261108T205835949070Z-search-statistics-authored-independent-contract-first-execution

[Receipt](../../verification/receipts/20261108T205835949070Z-search-statistics-authored-independent-contract-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T205835949070Z-search-statistics-authored-independent-contract-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T205835949070Z-search-statistics-authored-independent-contract-first-execution/stderr.log)

````text
E       ImportError: cannot import name 'SearchStatistics' from 'backend.lab.models' (<workspace>\backend\lab\models.py)
E           KeyError: 'statistics'
FAILED tests/test_search_statistics.py::test_complete_cohort_empirical_dispersion_and_independent_probabilities
````

## 20261108T210716709776Z-search-statistics-actual-api-worker-recovery-full-csv-and-offline-first-integration

[Receipt](../../verification/receipts/20261108T210716709776Z-search-statistics-actual-api-worker-recovery-full-csv-and-offline-first-integration.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T210716709776Z-search-statistics-actual-api-worker-recovery-full-csv-and-offline-first-integration/stdout.log) · [stderr.log](../../verification/runs/20261108T210716709776Z-search-statistics-actual-api-worker-recovery-full-csv-and-offline-first-integration/stderr.log)

````text
E           assert 0 > 0
E            +  where 0 = sum(<generator object test_actual_nonempty_search_freezes_policy_and_exports_all_saved_values_offline.<locals>.<genexpr> at 0x000001BAFDB9BB90>)
FAILED tests/test_search_statistics_integration.py::test_actual_nonempty_search_freezes_policy_and_exports_all_saved_values_offline
````

## 20261108T211041835680Z-search-statistics-authored-descending-control-and-preserved-empty-case-integration

[Receipt](../../verification/receipts/20261108T211041835680Z-search-statistics-authored-descending-control-and-preserved-empty-case-integration.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T211041835680Z-search-statistics-authored-descending-control-and-preserved-empty-case-integration/stdout.log) · [stderr.log](../../verification/runs/20261108T211041835680Z-search-statistics-authored-descending-control-and-preserved-empty-case-integration/stderr.log)

````text
E           assert 0 > 0
E            +  where 0 = sum(<generator object test_actual_nonempty_search_freezes_policy_and_exports_all_saved_values_offline.<locals>.<genexpr> at 0x00000226DA05FAC0>)
FAILED tests/test_search_statistics_integration.py::test_actual_nonempty_search_freezes_policy_and_exports_all_saved_values_offline
````

## 20261108T211338360848Z-search-statistics-authored-skip-run-compatible-control-and-complete-exports

[Receipt](../../verification/receipts/20261108T211338360848Z-search-statistics-authored-skip-run-compatible-control-and-complete-exports.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T211338360848Z-search-statistics-authored-skip-run-compatible-control-and-complete-exports/stdout.log) · [stderr.log](../../verification/runs/20261108T211338360848Z-search-statistics-authored-skip-run-compatible-control-and-complete-exports/stderr.log)

````text
E           AssertionError: {"detail":"Saved output failed the independent presentation contract: Builder.page() got an unexpected keyword argument 'metrics'"}
E           assert 409 == 200
E            +  where 409 = <Response [409 Conflict]>.status_code
````

## 20261108T211645355813Z-search-statistics-correct-presenter-contract-and-complete-boundary-regression

[Receipt](../../verification/receipts/20261108T211645355813Z-search-statistics-correct-presenter-contract-and-complete-boundary-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T211645355813Z-search-statistics-correct-presenter-contract-and-complete-boundary-regression/stdout.log) · [stderr.log](../../verification/runs/20261108T211645355813Z-search-statistics-correct-presenter-contract-and-complete-boundary-regression/stderr.log)

````text
E           AssertionError: {"detail":"Saved output failed the independent presentation contract: Too many large statistics."}
E           assert 409 == 200
E            +  where 409 = <Response [409 Conflict]>.status_code
````

## 20261108T212531847400Z-search-statistics-current-main-two-desktop-workflows-first-execution

[Receipt](../../verification/receipts/20261108T212531847400Z-search-statistics-current-main-two-desktop-workflows-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T212531847400Z-search-statistics-current-main-two-desktop-workflows-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T212531847400Z-search-statistics-current-main-two-desktop-workflows-first-execution/stderr.log) · [runner-stderr.log](../../verification/runs/20261108T212531847400Z-search-statistics-current-main-two-desktop-workflows-first-execution/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261108T212531847400Z-search-statistics-current-main-two-desktop-workflows-first-execution/browser/runner-stdout.log)

````text
    TimeoutError: locator.fill: Timeout 15000ms exceeded.
````

## 20261108T212947517626Z-search-statistics-current-managed-main-source-assets-and-single-store-owner

[Receipt](../../verification/receipts/20261108T212947517626Z-search-statistics-current-managed-main-source-assets-and-single-store-owner.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T212947517626Z-search-statistics-current-managed-main-source-assets-and-single-store-owner/stdout.log) · [stderr.log](../../verification/runs/20261108T212947517626Z-search-statistics-current-managed-main-source-assets-and-single-store-owner/stderr.log)

````text
Traceback (most recent call last):
````

## 20261108T213032070779Z-search-statistics-current-managed-main-native-powershell-owner-and-assets

[Receipt](../../verification/receipts/20261108T213032070779Z-search-statistics-current-managed-main-native-powershell-owner-and-assets.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T213032070779Z-search-statistics-current-managed-main-native-powershell-owner-and-assets/stdout.log) · [stderr.log](../../verification/runs/20261108T213032070779Z-search-statistics-current-managed-main-native-powershell-owner-and-assets/stderr.log)

````text
Traceback (most recent call last):
````

## 20261108T213152712776Z-search-statistics-current-main-fourteen-existing-desktop-workflows

[Receipt](../../verification/receipts/20261108T213152712776Z-search-statistics-current-main-fourteen-existing-desktop-workflows.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T213152712776Z-search-statistics-current-main-fourteen-existing-desktop-workflows/stdout.log) · [stderr.log](../../verification/runs/20261108T213152712776Z-search-statistics-current-main-fourteen-existing-desktop-workflows/stderr.log) · [runner-stderr.log](../../verification/runs/20261108T213152712776Z-search-statistics-current-main-fourteen-existing-desktop-workflows/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261108T213152712776Z-search-statistics-current-main-fourteen-existing-desktop-workflows/browser/runner-stdout.log)

````text
    Error: expect(received).toBe(expected) // Object.is equality
````

## 20261108T213621148883Z-search-statistics-prespecified-historical-api-worker-preflight

[Receipt](../../verification/receipts/20261108T213621148883Z-search-statistics-prespecified-historical-api-worker-preflight.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T213621148883Z-search-statistics-prespecified-historical-api-worker-preflight/stdout.log) · [stderr.log](../../verification/runs/20261108T213621148883Z-search-statistics-prespecified-historical-api-worker-preflight/stderr.log)

````text
Traceback (most recent call last):
````

## 20261108T214726102429Z-search-statistics-current-422-release-remains-incomplete

[Receipt](../../verification/receipts/20261108T214726102429Z-search-statistics-current-422-release-remains-incomplete.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T214726102429Z-search-statistics-current-422-release-remains-incomplete/stdout.log) · [stderr.log](../../verification/runs/20261108T214726102429Z-search-statistics-current-422-release-remains-incomplete/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T220251678778Z-common-sampling-authored-grid-quota-and-gate-contract-first-execution

[Receipt](../../verification/receipts/20261108T220251678778Z-common-sampling-authored-grid-quota-and-gate-contract-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T220251678778Z-common-sampling-authored-grid-quota-and-gate-contract-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T220251678778Z-common-sampling-authored-grid-quota-and-gate-contract-first-execution/stderr.log)

````text
E       ModuleNotFoundError: No module named 'backend.lab.sampling'
E       TypeError: backend.lab.models.Search() got multiple values for keyword argument 'sampling_policy'
E       ImportError: cannot import name 'sampling' from 'backend.lab' (<workspace>\backend\lab\__init__.py)
````

## 20261108T220538009601Z-common-sampling-first-complete-grid-quota-and-discovery-boundary-regression

[Receipt](../../verification/receipts/20261108T220538009601Z-common-sampling-first-complete-grid-quota-and-discovery-boundary-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T220538009601Z-common-sampling-first-complete-grid-quota-and-discovery-boundary-regression/stdout.log) · [stderr.log](../../verification/runs/20261108T220538009601Z-common-sampling-first-complete-grid-quota-and-discovery-boundary-regression/stderr.log)

````text
E   pydantic_core._pydantic_core.ValidationError: 1 validation error for Search
E     Value error, Effective-trial assumptions cannot exceed this search configuration count. [type=value_error, input_value=Search(dataset_id='aaaaaa...30, minimum_sharpe=0.5)), input_type=Search]
E       For further information visit https://errors.pydantic.dev/2.14/v/value_error
````

## 20261108T221417593536Z-common-sampling-authored-late-window-excludes-warmup-signals-first-execution

[Receipt](../../verification/receipts/20261108T221417593536Z-common-sampling-authored-late-window-excludes-warmup-signals-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T221417593536Z-common-sampling-authored-late-window-excludes-warmup-signals-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261108T221417593536Z-common-sampling-authored-late-window-excludes-warmup-signals-first-execution/stderr.log)

````text
E               assert 24 == 8
FAILED tests/test_common_sampling_integration.py::test_complete_nonempty_common_grid_keeps_all_initial_grades_and_saved_only_exports
````

## 20261108T221659241541Z-common-sampling-window-qualified-signals-and-complete-grading-regression

[Receipt](../../verification/receipts/20261108T221659241541Z-common-sampling-window-qualified-signals-and-complete-grading-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T221659241541Z-common-sampling-window-qualified-signals-and-complete-grading-regression/stdout.log) · [stderr.log](../../verification/runs/20261108T221659241541Z-common-sampling-window-qualified-signals-and-complete-grading-regression/stderr.log)

````text
E       AssertionError: assert (2 == 2 and {'generated':...able': 1, ...} == {'generated':...able': 0, ...}
E        +  where 2 = len([{'family': 'break_of_structure', 'timeframe': '1m', 'counts': {'generated': 0, 'signal_qualified': 0, 'enough_trades'...ture', 'timeframe': '1h', 'counts': {'generated': 1, 'signal_qualified': 1, 'enough_trades': 1, 'profitable': 1, ...}}])
E         
````

## 20261108T223347459386Z-common-sampling-actual-saved-json-csv-offline-assumption-completeness-first-audit

[Receipt](../../verification/receipts/20261108T223347459386Z-common-sampling-actual-saved-json-csv-offline-assumption-completeness-first-audit.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T223347459386Z-common-sampling-actual-saved-json-csv-offline-assumption-completeness-first-audit/stdout.log) · [stderr.log](../../verification/runs/20261108T223347459386Z-common-sampling-actual-saved-json-csv-offline-assumption-completeness-first-audit/stderr.log)

````text
Traceback (most recent call last):
AssertionError: Saved assumptions are incomplete; do not certify the common-search export.
````

## 20261108T224144488455Z-common-sampling-first-108-synthetic-browser-accounts-independent-decimal-gates-csv-offline

[Receipt](../../verification/receipts/20261108T224144488455Z-common-sampling-first-108-synthetic-browser-accounts-independent-decimal-gates-csv-offline.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T224144488455Z-common-sampling-first-108-synthetic-browser-accounts-independent-decimal-gates-csv-offline/stdout.log) · [stderr.log](../../verification/runs/20261108T224144488455Z-common-sampling-first-108-synthetic-browser-accounts-independent-decimal-gates-csv-offline/stderr.log)

````text
Traceback (most recent call last):
AssertionError: (503.0801637573167, '503.08016375747934', '1e-10')
````

## 20261108T224339175224Z-common-sampling-108-account-derived-metric-original-tolerance-diagnostic

[Receipt](../../verification/receipts/20261108T224339175224Z-common-sampling-108-account-derived-metric-original-tolerance-diagnostic.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T224339175224Z-common-sampling-108-account-derived-metric-original-tolerance-diagnostic/stdout.log) · [stderr.log](../../verification/runs/20261108T224339175224Z-common-sampling-108-account-derived-metric-original-tolerance-diagnostic/stderr.log)

````text
Traceback (most recent call last):
AssertionError: ('e41eba3a9a0e46bb8a8001fa0bbcc641', 0, 'marked_sharpe', 503.0801637573167, '503.08016375747934', '1e-10')
````

## 20261108T230736884817Z-common-sampling-current-full-regression-and-seventeen-module-coverage

[Receipt](../../verification/receipts/20261108T230736884817Z-common-sampling-current-full-regression-and-seventeen-module-coverage.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T230736884817Z-common-sampling-current-full-regression-and-seventeen-module-coverage/stdout.log) · [stderr.log](../../verification/runs/20261108T230736884817Z-common-sampling-current-full-regression-and-seventeen-module-coverage/stderr.log)

````text
E           AssertionError: Worker did not become ready within the diagnostic startup envelope.
E           assert (False)
FAILED tests/test_api.py::test_actual_spawned_worker_process_and_clean_shutdown
````

## 20261108T232434909963Z-common-sampling-current-120-browser-accounts-independent-decimal-and-complete-export-assumptions

[Receipt](../../verification/receipts/20261108T232434909963Z-common-sampling-current-120-browser-accounts-independent-decimal-and-complete-export-assumptions.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T232434909963Z-common-sampling-current-120-browser-accounts-independent-decimal-and-complete-export-assumptions/stdout.log) · [stderr.log](../../verification/runs/20261108T232434909963Z-common-sampling-current-120-browser-accounts-independent-decimal-and-complete-export-assumptions/stderr.log)

````text
Traceback (most recent call last):
````

## 20261108T232958681507Z-common-sampling-current-422-release-remains-incomplete

[Receipt](../../verification/receipts/20261108T232958681507Z-common-sampling-current-422-release-remains-incomplete.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T232958681507Z-common-sampling-current-422-release-remains-incomplete/stdout.log) · [stderr.log](../../verification/runs/20261108T232958681507Z-common-sampling-current-422-release-remains-incomplete/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261108T234406438247Z-aggregate-provenance-authored-fresh-synthetic-job-api-csv-offline-first-contract

[Receipt](../../verification/receipts/20261108T234406438247Z-aggregate-provenance-authored-fresh-synthetic-job-api-csv-offline-first-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261108T234406438247Z-aggregate-provenance-authored-fresh-synthetic-job-api-csv-offline-first-contract/stdout.log) · [stderr.log](../../verification/runs/20261108T234406438247Z-aggregate-provenance-authored-fresh-synthetic-job-api-csv-offline-first-contract/stderr.log)

````text
Traceback (most recent call last):
AssertionError: Aggregate provenance contract is not implemented; do not certify it.
````

## 20261109T003445875947Z-dataset-context-authored-all-analysis-worker-study-whitelist-corruption-first-contract

[Receipt](../../verification/receipts/20261109T003445875947Z-dataset-context-authored-all-analysis-worker-study-whitelist-corruption-first-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T003445875947Z-dataset-context-authored-all-analysis-worker-study-whitelist-corruption-first-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T003445875947Z-dataset-context-authored-all-analysis-worker-study-whitelist-corruption-first-contract/stderr.log)

````text
E    KeyError: 'dataset_context'
E    AssertionError: {"detail":"Not Found"}
E    assert 404 == 202
````

## 20261109T003839770510Z-dataset-context-first-complete-backend-all-analysis-workers-studies-csv-offline

[Receipt](../../verification/receipts/20261109T003839770510Z-dataset-context-first-complete-backend-all-analysis-workers-studies-csv-offline.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T003839770510Z-dataset-context-first-complete-backend-all-analysis-workers-studies-csv-offline/stdout.log) · [stderr.log](../../verification/runs/20261109T003839770510Z-dataset-context-first-complete-backend-all-analysis-workers-studies-csv-offline/stderr.log)

````text
E           backend.lab.presentation_audit.PresentationAuditError: A displayed digit has no source.
E           backend.lab.presenter.PresentationError: Saved output failed the independent presentation contract: A displayed digit has no source.
E           backend.lab.presenter.PresentationError: Invalid presentation label.
````

## 20261109T004424071769Z-dataset-context-correct-digit-free-fact-label-complete-backend-regression

[Receipt](../../verification/receipts/20261109T004424071769Z-dataset-context-correct-digit-free-fact-label-complete-backend-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T004424071769Z-dataset-context-correct-digit-free-fact-label-complete-backend-regression/stdout.log) · [stderr.log](../../verification/runs/20261109T004424071769Z-dataset-context-correct-digit-free-fact-label-complete-backend-regression/stderr.log)

````text
E           backend.lab.presenter.PresentationError: Invalid presentation label.
FAILED tests/test_dataset_context.py::test_every_analysis_freezes_before_queue_and_publishes_exact_context[behavior]
````

## 20261109T010123557425Z-dataset-context-two-desktop-saved-label-switch-legacy-and-all-offline-pages-first-execution

[Receipt](../../verification/receipts/20261109T010123557425Z-dataset-context-two-desktop-saved-label-switch-legacy-and-all-offline-pages-first-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T010123557425Z-dataset-context-two-desktop-saved-label-switch-legacy-and-all-offline-pages-first-execution/stdout.log) · [stderr.log](../../verification/runs/20261109T010123557425Z-dataset-context-two-desktop-saved-label-switch-legacy-and-all-offline-pages-first-execution/stderr.log) · [runner-stderr.log](../../verification/runs/20261109T010123557425Z-dataset-context-two-desktop-saved-label-switch-legacy-and-all-offline-pages-first-execution/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261109T010123557425Z-dataset-context-two-desktop-saved-label-switch-legacy-and-all-offline-pages-first-execution/browser/runner-stdout.log)

````text
    TimeoutError: page.waitForResponse: Timeout 15000ms exceeded while waiting for event "response"
````

## 20261109T010305410408Z-dataset-context-original-fresh-job-api-csv-offline-contract-regression

[Receipt](../../verification/receipts/20261109T010305410408Z-dataset-context-original-fresh-job-api-csv-offline-contract-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T010305410408Z-dataset-context-original-fresh-job-api-csv-offline-contract-regression/stdout.log) · [stderr.log](../../verification/runs/20261109T010305410408Z-dataset-context-original-fresh-job-api-csv-offline-contract-regression/stderr.log)

````text
Traceback (most recent call last):
AssertionError: Aggregate provenance contract is not implemented; do not certify it.
````

## 20261109T010928980904Z-import-http-event-loop-authored-held-normalization-and-concurrent-publication-first-contract

[Receipt](../../verification/receipts/20261109T010928980904Z-import-http-event-loop-authored-held-normalization-and-concurrent-publication-first-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T010928980904Z-import-http-event-loop-authored-held-normalization-and-concurrent-publication-first-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T010928980904Z-import-http-event-loop-authored-held-normalization-and-concurrent-publication-first-contract/stderr.log)

````text
E                   TimeoutError
FAILED tests/test_import_responsiveness.py::test_health_responds_while_an_actual_import_is_blocked_in_normalization
````

## 20261109T012026007015Z-dataset-context-two-desktop-independent-manifest-account-csv-whole-list-and-offline-evidence

[Receipt](../../verification/receipts/20261109T012026007015Z-dataset-context-two-desktop-independent-manifest-account-csv-whole-list-and-offline-evidence.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T012026007015Z-dataset-context-two-desktop-independent-manifest-account-csv-whole-list-and-offline-evidence/stdout.log) · [stderr.log](../../verification/runs/20261109T012026007015Z-dataset-context-two-desktop-independent-manifest-account-csv-whole-list-and-offline-evidence/stderr.log)

````text
Traceback (most recent call last):
````

## 20261109T014029299230Z-dataset-context-current-existing-api-http-import-export-and-study-protocol-regression

[Receipt](../../verification/receipts/20261109T014029299230Z-dataset-context-current-existing-api-http-import-export-and-study-protocol-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T014029299230Z-dataset-context-current-existing-api-http-import-export-and-study-protocol-regression/stdout.log) · [stderr.log](../../verification/runs/20261109T014029299230Z-dataset-context-current-existing-api-http-import-export-and-study-protocol-regression/stderr.log)

````text
E       AssertionError: assert (35 > 0 and 8 == 4)
E        +  where 8 = len([{'section': 'Data provenance', 'title': 'Saved input classification', 'subtitle': 'Frozen dataset context', 'conclusi...'}], 'conclusion': 'The simulated account broke even. An empty or flat outcome is not evidence of an edge.', ...}, ...])
FAILED tests/test_presenter_api.py::test_saved_html_and_combined_export_read_no_prices_and_keep_identity
````

## 20261109T014932838757Z-dataset-context-authored-preexisting-twenty-one-instrument-universe-first-regression

[Receipt](../../verification/receipts/20261109T014932838757Z-dataset-context-authored-preexisting-twenty-one-instrument-universe-first-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T014932838757Z-dataset-context-authored-preexisting-twenty-one-instrument-universe-first-regression/stdout.log) · [stderr.log](../../verification/runs/20261109T014932838757Z-dataset-context-authored-preexisting-twenty-one-instrument-universe-first-regression/stderr.log)

````text
E    AssertionError: {"detail":"Dataset context is malformed or has unsupported fields."}
E    assert 409 == 202
E     +  where 409 = <Response [409 Conflict]>.status_code
````

## 20261109T020722031816Z-dataset-context-unrestricted-universe-managed-owner-exact-assets-and-duplicate-refusal

[Receipt](../../verification/receipts/20261109T020722031816Z-dataset-context-unrestricted-universe-managed-owner-exact-assets-and-duplicate-refusal.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T020722031816Z-dataset-context-unrestricted-universe-managed-owner-exact-assets-and-duplicate-refusal/stdout.log) · [stderr.log](../../verification/runs/20261109T020722031816Z-dataset-context-unrestricted-universe-managed-owner-exact-assets-and-duplicate-refusal/stderr.log)

````text
Traceback (most recent call last):
AssertionError
````

## 20261109T024000160751Z-job-status-authored-bounded-io-full-inputs-corruption-migration-first-contract

[Receipt](../../verification/receipts/20261109T024000160751Z-job-status-authored-bounded-io-full-inputs-corruption-migration-first-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T024000160751Z-job-status-authored-bounded-io-full-inputs-corruption-migration-first-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T024000160751Z-job-status-authored-bounded-io-full-inputs-corruption-migration-first-contract/stderr.log)

````text
E     AssertionError: assert ('configurations' not in {'core_hash': '68f174d42e19e785c75c14207cbaa9ae1e096ac9e84b8dddce5a07afe96a9f75', 'costs': {'borrow_annual': 0.03, 'bo...842d627ae65d9e8a9508a163247a425852b03ece60828cb13e4216c5fe', 'input_kind': 'synthetic', 'policy_version': 1, ...}, ...} and 'proposals' not in {'attempts': 10, 'duplicates': 0, 'method': 'Unique seeded family quotas with acce [line clipped]
E     assert 993758 <= 65536
E      +  where 993758 = len(b'{"id":"23a4fb9f4a6c4bef9e269aaa356f6e89","kind":"search","payload":{"core_hash":"68f174d42e19e785c75c14207cbaa9ae1e0...192005.8171988,"updated":1794192005.8171988,"progress":0.0,"checkpoint":0,"note":"","error":null,"cancel_requested":0}')
````

## 20261109T025454533364Z-job-status-expanded-registry-and-malformed-input-recovery-first-contract

[Receipt](../../verification/receipts/20261109T025454533364Z-job-status-expanded-registry-and-malformed-input-recovery-first-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T025454533364Z-job-status-expanded-registry-and-malformed-input-recovery-first-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T025454533364Z-job-status-expanded-registry-and-malformed-input-recovery-first-contract/stderr.log)

````text
E     AssertionError: {"detail":"Internal request failure. No result was certified."}
E     assert 500 == 200
E      +  where 500 = <Response [500 Internal Server Error]>.status_code
````

## 20261109T025940365031Z-job-status-cache-registry-and-malformed-input-recovery-regression

[Receipt](../../verification/receipts/20261109T025940365031Z-job-status-cache-registry-and-malformed-input-recovery-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T025940365031Z-job-status-cache-registry-and-malformed-input-recovery-regression/stdout.log) · [stderr.log](../../verification/runs/20261109T025940365031Z-job-status-cache-registry-and-malformed-input-recovery-regression/stderr.log)

````text
E     AssertionError: {"detail":"Internal request failure. No result was certified."}
E     assert 500 == 200
E      +  where 500 = <Response [500 Internal Server Error]>.status_code
````

## 20261109T032106182854Z-bounded-job-monitoring-current-full-regression-and-nineteen-module-coverage

[Receipt](../../verification/receipts/20261109T032106182854Z-bounded-job-monitoring-current-full-regression-and-nineteen-module-coverage.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T032106182854Z-bounded-job-monitoring-current-full-regression-and-nineteen-module-coverage/stdout.log) · [stderr.log](../../verification/runs/20261109T032106182854Z-bounded-job-monitoring-current-full-regression-and-nineteen-module-coverage/stderr.log)

````text
E       KeyError: 'cost_arms'
FAILED tests/test_borrow_sensitivity_integration.py::test_api_fixed_rate_policy_json_csv_and_parts
````

## 20261109T032156056473Z-job-status-independent-browser-input-fingerprints-proposals-and-complete-trial-exports

[Receipt](../../verification/receipts/20261109T032156056473Z-job-status-independent-browser-input-fingerprints-proposals-and-complete-trial-exports.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T032156056473Z-job-status-independent-browser-input-fingerprints-proposals-and-complete-trial-exports/stdout.log) · [stderr.log](../../verification/runs/20261109T032156056473Z-job-status-independent-browser-input-fingerprints-proposals-and-complete-trial-exports/stderr.log)

````text
Traceback (most recent call last):
AssertionError
````

## 20261109T040749358548Z-study-status-and-isolated-legacy-recovery-authored-first-contract

[Receipt](../../verification/receipts/20261109T040749358548Z-study-status-and-isolated-legacy-recovery-authored-first-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T040749358548Z-study-status-and-isolated-legacy-recovery-authored-first-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T040749358548Z-study-status-and-isolated-legacy-recovery-authored-first-contract/stderr.log)

````text
E     KeyError: 'configuration_count'
E     assert (201 in {200, 201} and 698867 <= 65536)
E      +  where 201 = <Response [201 Created]>.status_code
````

## 20261109T040830175546Z-study-status-correct-actual-spy-scope-and-isolated-legacy-first-contract

[Receipt](../../verification/receipts/20261109T040830175546Z-study-status-correct-actual-spy-scope-and-isolated-legacy-first-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T040830175546Z-study-status-correct-actual-spy-scope-and-isolated-legacy-first-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T040830175546Z-study-status-correct-actual-spy-scope-and-isolated-legacy-first-contract/stderr.log)

````text
E     KeyError: 'configuration_count'
E     assert (201 in {200, 201} and 698867 <= 65536)
E      +  where 201 = <Response [201 Created]>.status_code
````

## 20261109T041124853698Z-study-status-first-derived-projections-scopes-and-legacy-recovery-regression

[Receipt](../../verification/receipts/20261109T041124853698Z-study-status-first-derived-projections-scopes-and-legacy-recovery-regression.json) · command exit `4` · [stdout.log](../../verification/runs/20261109T041124853698Z-study-status-first-derived-projections-scopes-and-legacy-recovery-regression/stdout.log) · [stderr.log](../../verification/runs/20261109T041124853698Z-study-status-first-derived-projections-scopes-and-legacy-recovery-regression/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261109T041628298333Z-study-status-expanded-source-cache-lifecycle-legacy-partial-rollback-and-existing-protocol

[Receipt](../../verification/receipts/20261109T041628298333Z-study-status-expanded-source-cache-lifecycle-legacy-partial-rollback-and-existing-protocol.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T041628298333Z-study-status-expanded-source-cache-lifecycle-legacy-partial-rollback-and-existing-protocol/stdout.log) · [stderr.log](../../verification/runs/20261109T041628298333Z-study-status-expanded-source-cache-lifecycle-legacy-partial-rollback-and-existing-protocol/stderr.log)

````text
E           ValueError: Candidate evidence differs.
FAILED tests/test_portfolio_study_api.py::test_original_inputs_and_candidate_events_guard_queued_or_new_work_before_prices[final-candidate_event]
FAILED tests/test_portfolio_study_api.py::test_original_inputs_and_candidate_events_guard_queued_or_new_work_before_prices[final-candidate_hash_consistent]
````

## 20261109T042049439744Z-study-status-authored-nested-legacy-and-malformed-checksummed-cache-first-contract

[Receipt](../../verification/receipts/20261109T042049439744Z-study-status-authored-nested-legacy-and-malformed-checksummed-cache-first-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T042049439744Z-study-status-authored-nested-legacy-and-malformed-checksummed-cache-first-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T042049439744Z-study-status-authored-nested-legacy-and-malformed-checksummed-cache-first-contract/stderr.log)

````text
E           AttributeError: 'list' object has no attribute 'get'
E    assert (500 == 200)
E     +  where 500 = <Response [500 Internal Server Error]>.status_code
````

## 20261109T042446208980Z-legacy-original-blob-authored-failure-before-raw-byte-preservation-fix

[Receipt](../../verification/receipts/20261109T042446208980Z-legacy-original-blob-authored-failure-before-raw-byte-preservation-fix.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T042446208980Z-legacy-original-blob-authored-failure-before-raw-byte-preservation-fix/stdout.log) · [stderr.log](../../verification/runs/20261109T042446208980Z-legacy-original-blob-authored-failure-before-raw-byte-preservation-fix/stderr.log)

````text
E       backend.lab.store.StateError: Stored trial inputs must be an object.
E                   AttributeError: 'bytes' object has no attribute 'encode'. Did you mean: 'decode'?
FAILED tests/test_study_status_index.py::test_unreconstructible_legacy_plan_does_not_abort_valid_neighbors_or_fabricate_attempts[blob-input]
````

## 20261109T044803814532Z-study-status-two-desktop-original-download-repair-history-stale-response-and-long-refresh-first-browser

[Receipt](../../verification/receipts/20261109T044803814532Z-study-status-two-desktop-original-download-repair-history-stale-response-and-long-refresh-first-browser.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T044803814532Z-study-status-two-desktop-original-download-repair-history-stale-response-and-long-refresh-first-browser/stdout.log) · [stderr.log](../../verification/runs/20261109T044803814532Z-study-status-two-desktop-original-download-repair-history-stale-response-and-long-refresh-first-browser/stderr.log) · [runner-stderr.log](../../verification/runs/20261109T044803814532Z-study-status-two-desktop-original-download-repair-history-stale-response-and-long-refresh-first-browser/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261109T044803814532Z-study-status-two-desktop-original-download-repair-history-stale-response-and-long-refresh-first-browser/browser/runner-stdout.log)

````text
    Error: expect(locator).toBeVisible() failed
    Error: element(s) not found
````

## 20261109T060604749226Z-result-materialization-authored-worker-bounded-pages-streaming-original-corruption-and-legacy-first-contract

[Receipt](../../verification/receipts/20261109T060604749226Z-result-materialization-authored-worker-bounded-pages-streaming-original-corruption-and-legacy-first-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T060604749226Z-result-materialization-authored-worker-bounded-pages-streaming-original-corruption-and-legacy-first-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T060604749226Z-result-materialization-authored-worker-bounded-pages-streaming-original-corruption-and-legacy-first-contract/stderr.log)

````text
E    AssertionError: {"detail":"Not Found"}
E    assert 404 == 200
E     +  where 404 = <Response [404 Not Found]>.status_code
````

## 20261109T063712321696Z-result-materialization-authored-missing-artifact-malformed-derived-diagnostic-parity-and-publication-fault-contract

[Receipt](../../verification/receipts/20261109T063712321696Z-result-materialization-authored-missing-artifact-malformed-derived-diagnostic-parity-and-publication-fault-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T063712321696Z-result-materialization-authored-missing-artifact-malformed-derived-diagnostic-parity-and-publication-fault-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T063712321696Z-result-materialization-authored-missing-artifact-malformed-derived-diagnostic-parity-and-publication-fault-contract/stderr.log)

````text
E    AssertionError: assert 404 == 409
E     +  where 404 = <Response [404 Not Found]>.status_code
E     +    where <Response [404 Not Found]> = get((('/api/jobs/' + 'fe7943387ff241b5ba15ec99586755bf') + '/report?part=1'))
````

## 20261109T064911901934Z-result-materialization-current-boundaries-and-complete-funnel-groups

[Receipt](../../verification/receipts/20261109T064911901934Z-result-materialization-current-boundaries-and-complete-funnel-groups.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T064911901934Z-result-materialization-current-boundaries-and-complete-funnel-groups/stdout.log) · [stderr.log](../../verification/runs/20261109T064911901934Z-result-materialization-current-boundaries-and-complete-funnel-groups/stderr.log)

````text
E    KeyError: 'groups'
FAILED tests/test_result_materialization.py::test_summary_keeps_complete_forty_group_funnel_with_bounded_metadata
````

## 20261109T065200912807Z-result-materialization-first-two-desktop-actual-pages-and-history-ownership

[Receipt](../../verification/receipts/20261109T065200912807Z-result-materialization-first-two-desktop-actual-pages-and-history-ownership.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T065200912807Z-result-materialization-first-two-desktop-actual-pages-and-history-ownership/stdout.log) · [stderr.log](../../verification/runs/20261109T065200912807Z-result-materialization-first-two-desktop-actual-pages-and-history-ownership/stderr.log) · [runner-stderr.log](../../verification/runs/20261109T065200912807Z-result-materialization-first-two-desktop-actual-pages-and-history-ownership/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261109T065200912807Z-result-materialization-first-two-desktop-actual-pages-and-history-ownership/browser/runner-stdout.log)

````text
    Error: expect(locator).toBeVisible() failed
    Error: element(s) not found
````

## 20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations

[Receipt](../../verification/receipts/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/stdout.log) · [stderr.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/stderr.log) · [baseline-stderr.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/baseline-stderr.log) · [baseline-stdout.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/baseline-stdout.log) · [ignore-diagnostic-page-offset-stderr.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/ignore-diagnostic-page-offset-stderr.log) · [ignore-diagnostic-page-offset-stdout.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/ignore-diagnostic-page-offset-stdout.log) · [ignore-result-page-offset-stderr.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/ignore-result-page-offset-stderr.log) · [ignore-result-page-offset-stdout.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/ignore-result-page-offset-stdout.log) · [ignore-result-publication-cancel-stderr.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/ignore-result-publication-cancel-stderr.log) · [ignore-result-publication-cancel-stdout.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/ignore-result-publication-cancel-stdout.log) · [materialize-unrelated-input-json-stderr.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/materialize-unrelated-input-json-stderr.log) · [materialize-unrelated-input-json-stdout.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/materialize-unrelated-input-json-stdout.log) · [miscount-portfolio-projection-stderr.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/miscount-portfolio-projection-stderr.log) · [miscount-portfolio-projection-stdout.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/miscount-portfolio-projection-stdout.log) · [silently-break-legacy-build-path-stderr.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/silently-break-legacy-build-path-stderr.log) · [silently-break-legacy-build-path-stdout.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/silently-break-legacy-build-path-stdout.log) · [skip-original-input-byte-binding-stderr.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/skip-original-input-byte-binding-stderr.log) · [skip-original-input-byte-binding-stdout.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/skip-original-input-byte-binding-stdout.log) · [skip-original-root-integrity-stderr.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/skip-original-root-integrity-stderr.log) · [skip-original-root-integrity-stdout.log](../../verification/runs/20261109T071615969267Z-result-materialization-current-eight-isolated-critical-mutations/skip-original-root-integrity-stdout.log)

````text
Traceback (most recent call last):
AssertionError: ('ignore-result-publication-cancel', {'exit_code': 0, 'assertion_failures': 0, 'tests': 9, 'failures': 0, 'errors': 0, 'skipped': 0})
E     AssertionError: assert [{'config_id'...ons': 3, ...}] == [{'config_id'...ons': 3, ...}]
````

## 20261109T080533950973Z-evaluation-cache-authored-current-bytes-base-charts-context-protection-and-worker-first-contract

[Receipt](../../verification/receipts/20261109T080533950973Z-evaluation-cache-authored-current-bytes-base-charts-context-protection-and-worker-first-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T080533950973Z-evaluation-cache-authored-current-bytes-base-charts-context-protection-and-worker-first-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T080533950973Z-evaluation-cache-authored-current-bytes-base-charts-context-protection-and-worker-first-contract/stderr.log)

````text
E    AssertionError: Verified job-scoped evaluation cache is not implemented
E    assert None is not None
E     +  where None = <function find_spec at 0x000002387658B060>('backend.lab.evaluation_cache')
````

## 20261109T080803324584Z-evaluation-cache-first-verified-preparation-base-charts-and-live-guard-regression

[Receipt](../../verification/receipts/20261109T080803324584Z-evaluation-cache-first-verified-preparation-base-charts-and-live-guard-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T080803324584Z-evaluation-cache-first-verified-preparation-base-charts-and-live-guard-regression/stdout.log) · [stderr.log](../../verification/runs/20261109T080803324584Z-evaluation-cache-first-verified-preparation-base-charts-and-live-guard-regression/stderr.log)

````text
E     assert 3 == 2
E      +  where 3 = len([1, 1, 1])
FAILED tests/test_evaluation_cache.py::test_actual_lab_complete_cached_report_matches_uncached_and_guard_precedes_reuse
````

## 20261109T081113254151Z-evaluation-cache-authored-120-discriminating-signal-account-parity-and-stream-cancel-manifest-race

[Receipt](../../verification/receipts/20261109T081113254151Z-evaluation-cache-authored-120-discriminating-signal-account-parity-and-stream-cancel-manifest-race.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T081113254151Z-evaluation-cache-authored-120-discriminating-signal-account-parity-and-stream-cancel-manifest-race/stdout.log) · [stderr.log](../../verification/runs/20261109T081113254151Z-evaluation-cache-authored-120-discriminating-signal-account-parity-and-stream-cancel-manifest-race/stderr.log)

````text
E    pydantic_core._pydantic_core.ValidationError: 1 validation error for Strategy
E    trigger
E      Extra inputs are not permitted [type=extra_forbidden, input_value='1m', input_type=str]
````

## 20261109T083040515400Z-live-control-reader-authored-fresh-owner-cancel-readonly-isolation-and-cleanup-first-contract

[Receipt](../../verification/receipts/20261109T083040515400Z-live-control-reader-authored-fresh-owner-cancel-readonly-isolation-and-cleanup-first-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T083040515400Z-live-control-reader-authored-fresh-owner-cancel-readonly-isolation-and-cleanup-first-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T083040515400Z-live-control-reader-authored-fresh-owner-cancel-readonly-isolation-and-cleanup-first-contract/stderr.log)

````text
E    AssertionError: Job-local live control reader is not implemented
E    assert False
E     +  where False = callable(None)
````

## 20261109T083258105537Z-live-control-reader-first-readonly-fresh-authority-and-cache-reference-regression

[Receipt](../../verification/receipts/20261109T083258105537Z-live-control-reader-first-readonly-fresh-authority-and-cache-reference-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T083258105537Z-live-control-reader-first-readonly-fresh-authority-and-cache-reference-regression/stdout.log) · [stderr.log](../../verification/runs/20261109T083258105537Z-live-control-reader-first-readonly-fresh-authority-and-cache-reference-regression/stderr.log)

````text
E      sqlite3.IntegrityError: FOREIGN KEY constraint failed
FAILED tests/test_control_reader.py::test_external_ownership_or_terminal_transition_rejects_immediately[deleted]
````

## 20261109T084649710750Z-numerical-capacity-current-10000-real-one-session-execution

[Receipt](../../verification/receipts/20261109T084649710750Z-numerical-capacity-current-10000-real-one-session-execution.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T084649710750Z-numerical-capacity-current-10000-real-one-session-execution/stdout.log) · [stderr.log](../../verification/runs/20261109T084649710750Z-numerical-capacity-current-10000-real-one-session-execution/stderr.log)

````text
Traceback (most recent call last):
AssertionError: ('queued', None, 4663)
````

## 20261109T090433081941Z-numerical-capacity-owned-covering-control-index-and-update-scaling-probe

[Receipt](../../verification/receipts/20261109T090433081941Z-numerical-capacity-owned-covering-control-index-and-update-scaling-probe.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T090433081941Z-numerical-capacity-owned-covering-control-index-and-update-scaling-probe/stdout.log) · [stderr.log](../../verification/runs/20261109T090433081941Z-numerical-capacity-owned-covering-control-index-and-update-scaling-probe/stderr.log)

````text
Traceback (most recent call last):
AssertionError
````

## 20261109T090955696420Z-live-control-covering-index-authored-old-store-original-byte-query-plan-and-missing-index-first-contract

[Receipt](../../verification/receipts/20261109T090955696420Z-live-control-covering-index-authored-old-store-original-byte-query-plan-and-missing-index-first-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T090955696420Z-live-control-covering-index-authored-old-store-original-byte-query-plan-and-missing-index-first-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T090955696420Z-live-control-covering-index-authored-old-store-original-byte-query-plan-and-missing-index-first-contract/stderr.log)

````text
E     AssertionError: Existing stores did not acquire the required covering index
E     assert 'jobs_live_control' in {'jobs_pending', 'sqlite_autoindex_jobs_1'}
E     assert False
````

## 20261109T094355692297Z-evaluation-cache-current-twenty-two-module-coverage-gate

[Receipt](../../verification/receipts/20261109T094355692297Z-evaluation-cache-current-twenty-two-module-coverage-gate.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T094355692297Z-evaluation-cache-current-twenty-two-module-coverage-gate/stdout.log) · [stderr.log](../../verification/runs/20261109T094355692297Z-evaluation-cache-current-twenty-two-module-coverage-gate/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261109T101032684832Z-current-server-native-tree-root-cause-and-live-duplicate-start-refusal

[Receipt](../../verification/receipts/20261109T101032684832Z-current-server-native-tree-root-cause-and-live-duplicate-start-refusal.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T101032684832Z-current-server-native-tree-root-cause-and-live-duplicate-start-refusal/stdout.log) · [stderr.log](../../verification/runs/20261109T101032684832Z-current-server-native-tree-root-cause-and-live-duplicate-start-refusal/stderr.log)

````text
Traceback (most recent call last):
AssertionError: [{'pid': 34720, 'parent_pid': 23968, 'name': 'python.exe', 'creation_time_utc': '2026-11-09T09:43:57.0062230Z', 'project_uvicorn': True}, {'pid': 40760, 'parent_pid': 34720, 'name': 'python.exe', 'creation_time_utc': '2026-11-09T09:43:57.0384800Z', 'project_uvicorn': True}, {'pid': 20832, 'parent_pid': 40760, 'name': 'python.exe', 'creation_time_utc': '2026-11-09T09:43:59.4296160Z' [line clipped]
````

## 20261109T102237014227Z-current-clean-original-and-fresh-complete-offline-account-restart-and-uncached-provider-denial

[Receipt](../../verification/receipts/20261109T102237014227Z-current-clean-original-and-fresh-complete-offline-account-restart-and-uncached-provider-denial.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T102237014227Z-current-clean-original-and-fresh-complete-offline-account-restart-and-uncached-provider-denial/stdout.log) · [stderr.log](../../verification/runs/20261109T102237014227Z-current-clean-original-and-fresh-complete-offline-account-restart-and-uncached-provider-denial/stderr.log) · [original-stderr.log](../../verification/runs/20261109T102237014227Z-current-clean-original-and-fresh-complete-offline-account-restart-and-uncached-provider-denial/original-stderr.log) · [original-stdout.log](../../verification/runs/20261109T102237014227Z-current-clean-original-and-fresh-complete-offline-account-restart-and-uncached-provider-denial/original-stdout.log)

````text
Traceback (most recent call last):
AssertionError: ('original', 1, 'See retained sanitized stderr')
AssertionError
````

## 20261109T104029406130Z-spread-isolated-authored-exact-balance-freeze-qualification-replay-first-contract

[Receipt](../../verification/receipts/20261109T104029406130Z-spread-isolated-authored-exact-balance-freeze-qualification-replay-first-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T104029406130Z-spread-isolated-authored-exact-balance-freeze-qualification-replay-first-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T104029406130Z-spread-isolated-authored-exact-balance-freeze-qualification-replay-first-contract/stderr.log)

````text
E       ImportError: cannot import name 'spread' from 'backend.lab' (<workspace>\data\dev025\src\backend\lab\__init__.py)
ERROR tests/test_spread.py::test_host_defaults_and_explicit_distance_are_not_common_filter_quotas
ERROR tests/test_spread.py::test_seeded_all_chart_draws_valid_public_dials_and_conditional_universe[level_bounce]
````

## 20261109T104952434255Z-spread-isolated-authored-distinct-retry-attempts-current-plan-and-external-identity-adversarial-contract

[Receipt](../../verification/receipts/20261109T104952434255Z-spread-isolated-authored-distinct-retry-attempts-current-plan-and-external-identity-adversarial-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T104952434255Z-spread-isolated-authored-distinct-retry-attempts-current-plan-and-external-identity-adversarial-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T104952434255Z-spread-isolated-authored-distinct-retry-attempts-current-plan-and-external-identity-adversarial-contract/stderr.log)

````text
E       KeyError: 'total_probe_attempts'
E       Failed: DID NOT RAISE SpreadError
E       AttributeError: type object 'ProposalPlan' has no attribute 'open'
````

## 20261109T105402570644Z-spread-isolated-authored-actual-primary-signal-evidence-warmup-and-preprice-guard-contract

[Receipt](../../verification/receipts/20261109T105402570644Z-spread-isolated-authored-actual-primary-signal-evidence-warmup-and-preprice-guard-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T105402570644Z-spread-isolated-authored-actual-primary-signal-evidence-warmup-and-preprice-guard-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T105402570644Z-spread-isolated-authored-actual-primary-signal-evidence-warmup-and-preprice-guard-contract/stderr.log)

````text
E       AttributeError: 'Lab' object has no attribute 'spread_signal_probe'
FAILED tests/test_spread_probe.py::test_actual_probe_preserves_primary_warmup_full_signal_evidence_without_accounts
FAILED tests/test_spread_probe.py::test_probe_rejects_invalid_scope_before_price_load[unknown_primary]
````

## 20261109T105652473592Z-spread-isolated-authored-primary-only-protection-cache-separation-and-news-scope-before-implementation

[Receipt](../../verification/receipts/20261109T105652473592Z-spread-isolated-authored-primary-only-protection-cache-separation-and-news-scope-before-implementation.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T105652473592Z-spread-isolated-authored-primary-only-protection-cache-separation-and-news-scope-before-implementation/stdout.log) · [stderr.log](../../verification/runs/20261109T105652473592Z-spread-isolated-authored-primary-only-protection-cache-separation-and-news-scope-before-implementation/stderr.log)

````text
E       AttributeError: 'Lab' object has no attribute 'spread_signal_probe'
E           AttributeError: 'Lab' object has no attribute 'spread_signal_probe'
E       assert [1] == []
````

## 20261109T110135609527Z-spread-isolated-authored-complete-public-recipe-and-default-400-proposal-batch-contract

[Receipt](../../verification/receipts/20261109T110135609527Z-spread-isolated-authored-complete-public-recipe-and-default-400-proposal-batch-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T110135609527Z-spread-isolated-authored-complete-public-recipe-and-default-400-proposal-batch-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T110135609527Z-spread-isolated-authored-complete-public-recipe-and-default-400-proposal-batch-contract/stderr.log)

````text
E       KeyError: 'dial_rules'
FAILED tests/test_spread.py::test_recipe_publishes_every_public_field_domain_and_prerequisite
````

## 20261109T112033155557Z-spread-isolated-first-unrounded-95-90-core-coverage-gate

[Receipt](../../verification/receipts/20261109T112033155557Z-spread-isolated-first-unrounded-95-90-core-coverage-gate.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T112033155557Z-spread-isolated-first-unrounded-95-90-core-coverage-gate/stdout.log) · [stderr.log](../../verification/runs/20261109T112033155557Z-spread-isolated-first-unrounded-95-90-core-coverage-gate/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261109T113350822606Z-spread-preparation-authored-real-batch-crash-recovery-byte-integrity-and-no-redraw-contract

[Receipt](../../verification/receipts/20261109T113350822606Z-spread-preparation-authored-real-batch-crash-recovery-byte-integrity-and-no-redraw-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T113350822606Z-spread-preparation-authored-real-batch-crash-recovery-byte-integrity-and-no-redraw-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T113350822606Z-spread-preparation-authored-real-batch-crash-recovery-byte-integrity-and-no-redraw-contract/stderr.log)

````text
E       ImportError: cannot import name 'spread_preparation' from 'backend.lab' (<workspace>\data\dev025\src\backend\lab\__init__.py)
ERROR tests/test_spread_preparation.py::test_complete_preparation_has_every_proposal_and_requires_no_prices
ERROR tests/test_spread_preparation.py::test_batch_boundary_crash_does_not_redraw_committed_versions[False]
````

## 20261109T113904454005Z-spread-preparation-authored-current-batch-bytes-before-final-seal

[Receipt](../../verification/receipts/20261109T113904454005Z-spread-preparation-authored-current-batch-bytes-before-final-seal.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T113904454005Z-spread-preparation-authored-current-batch-bytes-before-final-seal/stdout.log) · [stderr.log](../../verification/runs/20261109T113904454005Z-spread-preparation-authored-current-batch-bytes-before-final-seal/stderr.log)

````text
E       Failed: DID NOT RAISE SpreadError
FAILED tests/test_spread_preparation.py::test_batch_changed_after_commit_validation_cannot_become_a_new_sealed_source
````

## 20261109T114003055461Z-spread-journal-authored-owned-chain-tail-corruption-staged-registry-and-attempt-contract

[Receipt](../../verification/receipts/20261109T114003055461Z-spread-journal-authored-owned-chain-tail-corruption-staged-registry-and-attempt-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T114003055461Z-spread-journal-authored-owned-chain-tail-corruption-staged-registry-and-attempt-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T114003055461Z-spread-journal-authored-owned-chain-tail-corruption-staged-registry-and-attempt-contract/stderr.log)

````text
E       ModuleNotFoundError: No module named 'backend.lab.spread_jobs'
ERROR tests/test_spread_journal.py::test_empty_spread_has_zero_financial_occurrences_and_an_original_frozen_plan
ERROR tests/test_spread_journal.py::test_journal_head_and_event_commit_are_one_owned_transaction
````

## 20261109T114643574329Z-spread-journal-authored-no-invented-attempts-owner-or-self-rehashed-parent-provenance

[Receipt](../../verification/receipts/20261109T114643574329Z-spread-journal-authored-no-invented-attempts-owner-or-self-rehashed-parent-provenance.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T114643574329Z-spread-journal-authored-no-invented-attempts-owner-or-self-rehashed-parent-provenance/stdout.log) · [stderr.log](../../verification/runs/20261109T114643574329Z-spread-journal-authored-no-invented-attempts-owner-or-self-rehashed-parent-provenance/stderr.log)

````text
E       Failed: DID NOT RAISE StateError
E           json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
FAILED tests/test_spread_journal.py::test_registry_details_must_reconcile_to_original_protocol_not_just_self_hashes[invented_attempt]
````

## 20261109T115306339289Z-spread-worker-authored-actual-qualification-cancel-attempt-reuse-and-corruption-contract

[Receipt](../../verification/receipts/20261109T115306339289Z-spread-worker-authored-actual-qualification-cancel-attempt-reuse-and-corruption-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T115306339289Z-spread-worker-authored-actual-qualification-cancel-attempt-reuse-and-corruption-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T115306339289Z-spread-worker-authored-actual-qualification-cancel-attempt-reuse-and-corruption-contract/stderr.log)

````text
E       AttributeError: 'Lab' object has no attribute 'create_spread'
FAILED tests/test_spread_worker.py::test_actual_worker_freezes_all_proposals_then_saves_primary_signals_without_pnl
FAILED tests/test_spread_worker.py::test_cancelled_preparation_resumes_committed_batches_without_any_early_price_read
````

## 20261109T120054197433Z-spread-worker-authored-late-evidence-publication-and-single-master-seed

[Receipt](../../verification/receipts/20261109T120054197433Z-spread-worker-authored-late-evidence-publication-and-single-master-seed.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T120054197433Z-spread-worker-authored-late-evidence-publication-and-single-master-seed/stdout.log) · [stderr.log](../../verification/runs/20261109T120054197433Z-spread-worker-authored-late-evidence-publication-and-single-master-seed/stderr.log)

````text
E       AssertionError: assert ('completed' == 'failed'
E         
E         - failed
````

## 20261109T120126098167Z-spread-api-authored-data-free-preview-bounded-status-event-pages-and-actual-worker-result

[Receipt](../../verification/receipts/20261109T120126098167Z-spread-api-authored-data-free-preview-bounded-status-event-pages-and-actual-worker-result.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T120126098167Z-spread-api-authored-data-free-preview-bounded-status-event-pages-and-actual-worker-result/stdout.log) · [stderr.log](../../verification/runs/20261109T120126098167Z-spread-api-authored-data-free-preview-bounded-status-event-pages-and-actual-worker-result/stderr.log)

````text
E           TypeError: Headers.update() got an unexpected keyword argument 'Origin'
E       AttributeError: 'Lab' object has no attribute 'spread_status'
FAILED tests/test_spread_api.py::test_preview_is_data_free_and_preserves_source_defaults_and_actual_work
````

## 20261109T120446451334Z-spread-api-preview-authored-corrected-header-harness-before-route-implementation

[Receipt](../../verification/receipts/20261109T120446451334Z-spread-api-preview-authored-corrected-header-harness-before-route-implementation.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T120446451334Z-spread-api-preview-authored-corrected-header-harness-before-route-implementation/stdout.log) · [stderr.log](../../verification/runs/20261109T120446451334Z-spread-api-preview-authored-corrected-header-harness-before-route-implementation/stderr.log)

````text
E           AssertionError: {"detail":"Not Found"}
E           assert 404 == 200
E            +  where 404 = <Response [404 Not Found]>.status_code
````

## 20261109T121356680219Z-spread-streaming-authored-lazy-invalid-prefix-and-large-nonfinancial-journal-heap-contract

[Receipt](../../verification/receipts/20261109T121356680219Z-spread-streaming-authored-lazy-invalid-prefix-and-large-nonfinancial-journal-heap-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T121356680219Z-spread-streaming-authored-lazy-invalid-prefix-and-large-nonfinancial-journal-heap-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T121356680219Z-spread-streaming-authored-lazy-invalid-prefix-and-large-nonfinancial-journal-heap-contract/stderr.log)

````text
E       assert 100001 <= 3
E        +  where 100001 = len([1, 1, 1, 1, 1, 1, ...])
E       TypeError: SpreadJournal.__init__() got an unexpected keyword argument 'stream'
````

## 20261109T123934068372Z-spread-durable-four-module-first-unrounded-95-90-gate

[Receipt](../../verification/receipts/20261109T123934068372Z-spread-durable-four-module-first-unrounded-95-90-gate.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T123934068372Z-spread-durable-four-module-first-unrounded-95-90-gate/stdout.log) · [stderr.log](../../verification/runs/20261109T123934068372Z-spread-durable-four-module-first-unrounded-95-90-gate/stderr.log)

````text
Traceback (most recent call last):
````

## 20261109T124047166381Z-spread-durable-four-module-corrected-schema-unrounded-95-90-gate

[Receipt](../../verification/receipts/20261109T124047166381Z-spread-durable-four-module-corrected-schema-unrounded-95-90-gate.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T124047166381Z-spread-durable-four-module-corrected-schema-unrounded-95-90-gate/stdout.log) · [stderr.log](../../verification/runs/20261109T124047166381Z-spread-durable-four-module-corrected-schema-unrounded-95-90-gate/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261109T124701043995Z-spread-worker-expanded-new-signal-validation-orphans-root-recovery-news-and-source-faults

[Receipt](../../verification/receipts/20261109T124701043995Z-spread-worker-expanded-new-signal-validation-orphans-root-recovery-news-and-source-faults.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T124701043995Z-spread-worker-expanded-new-signal-validation-orphans-root-recovery-news-and-source-faults/stdout.log) · [stderr.log](../../verification/runs/20261109T124701043995Z-spread-worker-expanded-new-signal-validation-orphans-root-recovery-news-and-source-faults/stderr.log)

````text
E       FileNotFoundError: [Errno 2] No such file or directory: '<user-home>\\AppData\\Local\\Temp\\pytest-of-user\\pytest-293\\test_saved_root_recovery_prese0\\data\\jobs\\5559957dcd7445458a45df22e28f80c6\\result.json.gz'
E       FileNotFoundError: [Errno 2] No such file or directory: '<user-home>\\AppData\\Local\\Temp\\pytest-of-user\\pytest-293\\test_saved_root_recovery_prese1\\data\\jobs\\8bdd87da723b40e7b290f40a808876d7\\result.json.gz'
E       FileNotFoundError: [Errno 2] No such file or directory: '<user-home>\\AppData\\Local\\Temp\\pytest-of-user\\pytest-293\\test_saved_root_recovery_prese2\\data\\jobs\\95185c23a8ea4f3aa06cc5c65d116939\\result.json.gz'
````

## 20261109T125844627745Z-spread-expanded-current-four-module-unrounded-gate

[Receipt](../../verification/receipts/20261109T125844627745Z-spread-expanded-current-four-module-unrounded-gate.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T125844627745Z-spread-expanded-current-four-module-unrounded-gate/stdout.log) · [stderr.log](../../verification/runs/20261109T125844627745Z-spread-expanded-current-four-module-unrounded-gate/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261109T125847546248Z-spread-expanded-current-final-257-focused-fault-cases-and-four-module-coverage

[Receipt](../../verification/receipts/20261109T125847546248Z-spread-expanded-current-final-257-focused-fault-cases-and-four-module-coverage.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T125847546248Z-spread-expanded-current-final-257-focused-fault-cases-and-four-module-coverage/stdout.log) · [stderr.log](../../verification/runs/20261109T125847546248Z-spread-expanded-current-final-257-focused-fault-cases-and-four-module-coverage/stderr.log)

````text
E           backend.lab.data.DataError: Dataset manifest hash mismatch.
FAILED tests/test_spread_worker_faults.py::test_manifest_changed_after_preparation_cannot_authorize_first_signal
````

## 20261109T130100304082Z-spread-durable-current-eight-isolated-original-guard-mutations

[Receipt](../../verification/receipts/20261109T130100304082Z-spread-durable-current-eight-isolated-original-guard-mutations.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T130100304082Z-spread-durable-current-eight-isolated-original-guard-mutations/stdout.log) · [stderr.log](../../verification/runs/20261109T130100304082Z-spread-durable-current-eight-isolated-original-guard-mutations/stderr.log) · [stderr.log](../../verification/runs/20261109T130100304082Z-spread-durable-current-eight-isolated-original-guard-mutations/baseline/stderr.log) · [stdout.log](../../verification/runs/20261109T130100304082Z-spread-durable-current-eight-isolated-original-guard-mutations/baseline/stdout.log)

````text
Traceback (most recent call last):
AssertionError
E           backend.lab.data.DataError: Dataset manifest hash mismatch.
````

## 20261109T130418977348Z-spread-account-continuation-authored-complete-parent-frozen-assumptions-corruption-primary-and-concurrency-contract

[Receipt](../../verification/receipts/20261109T130418977348Z-spread-account-continuation-authored-complete-parent-frozen-assumptions-corruption-primary-and-concurrency-contract.json) · command exit `2` · [stdout.log](../../verification/runs/20261109T130418977348Z-spread-account-continuation-authored-complete-parent-frozen-assumptions-corruption-primary-and-concurrency-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T130418977348Z-spread-account-continuation-authored-complete-parent-frozen-assumptions-corruption-primary-and-concurrency-contract/stderr.log)

````text
Traceback:
E   ModuleNotFoundError: No module named 'backend.lab.spread_jobs'
ERROR ..\..\..\verification\runs\spread_account_handoff_authored.py
````

## 20261109T130635969373Z-spread-account-continuation-owned-development-first-unimplemented-contract

[Receipt](../../verification/receipts/20261109T130635969373Z-spread-account-continuation-owned-development-first-unimplemented-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T130635969373Z-spread-account-continuation-owned-development-first-unimplemented-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T130635969373Z-spread-account-continuation-owned-development-first-unimplemented-contract/stderr.log)

````text
E    AttributeError: 'Lab' object has no attribute 'create_spread_accounts'
E   AttributeError: 'Lab' object has no attribute 'create_spread_accounts'
FAILED tests/test_spread_account_handoff.py::test_complete_parent_freezes_all_selected_financial_trials_and_original_assumptions_before_pnl
````

## 20261109T132736557736Z-spread-account-authored-api-override-atomic-link-corruption-and-committed-part-recovery-contract

[Receipt](../../verification/receipts/20261109T132736557736Z-spread-account-authored-api-override-atomic-link-corruption-and-committed-part-recovery-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T132736557736Z-spread-account-authored-api-override-atomic-link-corruption-and-committed-part-recovery-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T132736557736Z-spread-account-authored-api-override-atomic-link-corruption-and-committed-part-recovery-contract/stderr.log)

````text
E    Failed: DID NOT RAISE StateError
E     AssertionError: {"detail":"Not Found"}
E     assert 404 == 202
````

## 20261109T134050173383Z-spread-account-first-original-lineage-and-complete-independent-decimal-account-audit

[Receipt](../../verification/receipts/20261109T134050173383Z-spread-account-first-original-lineage-and-complete-independent-decimal-account-audit.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T134050173383Z-spread-account-first-original-lineage-and-complete-independent-decimal-account-audit/stdout.log) · [stderr.log](../../verification/runs/20261109T134050173383Z-spread-account-first-original-lineage-and-complete-independent-decimal-account-audit/stderr.log)

````text
Traceback (most recent call last):
````

## 20261109T134251599115Z-spread-account-authored-strict-seed-forty-floor-and-complete-loss-statistics-screen-csv-exports

[Receipt](../../verification/receipts/20261109T134251599115Z-spread-account-authored-strict-seed-forty-floor-and-complete-loss-statistics-screen-csv-exports.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T134251599115Z-spread-account-authored-strict-seed-forty-floor-and-complete-loss-statistics-screen-csv-exports/stdout.log) · [stderr.log](../../verification/runs/20261109T134251599115Z-spread-account-authored-strict-seed-forty-floor-and-complete-loss-statistics-screen-csv-exports/stderr.log)

````text
E    Failed: DID NOT RAISE ValidationError
E       AssertionError: {"detail":"This saved result has no supported search-statistic diagnostic. Original evidence is unchanged."}
E       assert 409 == 200
````

## 20261109T140443561688Z-spread-account-current-seven-isolated-original-guard-mutations

[Receipt](../../verification/receipts/20261109T140443561688Z-spread-account-current-seven-isolated-original-guard-mutations.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T140443561688Z-spread-account-current-seven-isolated-original-guard-mutations/stdout.log) · [stderr.log](../../verification/runs/20261109T140443561688Z-spread-account-current-seven-isolated-original-guard-mutations/stderr.log) · [stderr.log](../../verification/runs/20261109T140443561688Z-spread-account-current-seven-isolated-original-guard-mutations/baseline/stderr.log) · [stdout.log](../../verification/runs/20261109T140443561688Z-spread-account-current-seven-isolated-original-guard-mutations/baseline/stdout.log) · [stderr.log](../../verification/runs/20261109T140443561688Z-spread-account-current-seven-isolated-original-guard-mutations/original-replay/stderr.log) · [stdout.log](../../verification/runs/20261109T140443561688Z-spread-account-current-seven-isolated-original-guard-mutations/original-replay/stdout.log)

````text
Traceback (most recent call last):
AssertionError: ('original-replay', [None])
E    Failed: DID NOT RAISE StateError
````

## 20261109T142009156791Z-spread-account-corrected-junit-schema-seven-assertion-killed-guard-mutations

[Receipt](../../verification/receipts/20261109T142009156791Z-spread-account-corrected-junit-schema-seven-assertion-killed-guard-mutations.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T142009156791Z-spread-account-corrected-junit-schema-seven-assertion-killed-guard-mutations/stdout.log) · [stderr.log](../../verification/runs/20261109T142009156791Z-spread-account-corrected-junit-schema-seven-assertion-killed-guard-mutations/stderr.log) · [stderr.log](../../verification/runs/20261109T142009156791Z-spread-account-corrected-junit-schema-seven-assertion-killed-guard-mutations/baseline/stderr.log) · [stdout.log](../../verification/runs/20261109T142009156791Z-spread-account-corrected-junit-schema-seven-assertion-killed-guard-mutations/baseline/stdout.log) · [stderr.log](../../verification/runs/20261109T142009156791Z-spread-account-corrected-junit-schema-seven-assertion-killed-guard-mutations/original-link-event/stderr.log) · [stdout.log](../../verification/runs/20261109T142009156791Z-spread-account-corrected-junit-schema-seven-assertion-killed-guard-mutations/original-link-event/stdout.log) · [stderr.log](../../verification/runs/20261109T142009156791Z-spread-account-corrected-junit-schema-seven-assertion-killed-guard-mutations/original-replay/stderr.log) · [stdout.log](../../verification/runs/20261109T142009156791Z-spread-account-corrected-junit-schema-seven-assertion-killed-guard-mutations/original-replay/stdout.log) · [stderr.log](../../verification/runs/20261109T142009156791Z-spread-account-corrected-junit-schema-seven-assertion-killed-guard-mutations/reject-overrides/stderr.log) · [stdout.log](../../verification/runs/20261109T142009156791Z-spread-account-corrected-junit-schema-seven-assertion-killed-guard-mutations/reject-overrides/stdout.log)

````text
Traceback (most recent call last):
AssertionError: ('publication-parent', 0)
E    Failed: DID NOT RAISE StateError
````

## 20261109T142013687366Z-spread-account-current-first-unrounded-95-90-parent-module-gate

[Receipt](../../verification/receipts/20261109T142013687366Z-spread-account-current-first-unrounded-95-90-parent-module-gate.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T142013687366Z-spread-account-current-first-unrounded-95-90-parent-module-gate/stdout.log) · [stderr.log](../../verification/runs/20261109T142013687366Z-spread-account-current-first-unrounded-95-90-parent-module-gate/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261109T145625027908Z-spread-selection-pages-authored-original-envelope-bounds-index-and-saved-child-contract

[Receipt](../../verification/receipts/20261109T145625027908Z-spread-selection-pages-authored-original-envelope-bounds-index-and-saved-child-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T145625027908Z-spread-selection-pages-authored-original-envelope-bounds-index-and-saved-child-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T145625027908Z-spread-selection-pages-authored-original-envelope-bounds-index-and-saved-child-contract/stderr.log)

````text
E    AttributeError: 'Lab' object has no attribute 'spread_selections'
E     AssertionError: assert 'spread_selected_events' in {'events_entity', 'events_kind', 'jobs_live_control', 'jobs_pending', 'sqlite_autoindex_job_input_index_1', 'sqlite_autoindex_jobs_1', ...}
E     assert (404 == 200)
````

## 20261109T152554885958Z-spread-ui-actual-three-viewport-owned-synthetic-recon

[Receipt](../../verification/receipts/20261109T152554885958Z-spread-ui-actual-three-viewport-owned-synthetic-recon.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T152554885958Z-spread-ui-actual-three-viewport-owned-synthetic-recon/stdout.log) · [stderr.log](../../verification/runs/20261109T152554885958Z-spread-ui-actual-three-viewport-owned-synthetic-recon/stderr.log) · [runner-stderr.log](../../verification/runs/20261109T152554885958Z-spread-ui-actual-three-viewport-owned-synthetic-recon/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261109T152554885958Z-spread-ui-actual-three-viewport-owned-synthetic-recon/browser/runner-stdout.log)

````text
Traceback (most recent call last):
````

## 20261109T152816557771Z-spread-ui-real-three-viewport-qualification-account-exhaustion-and-offline-exports

[Receipt](../../verification/receipts/20261109T152816557771Z-spread-ui-real-three-viewport-qualification-account-exhaustion-and-offline-exports.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T152816557771Z-spread-ui-real-three-viewport-qualification-account-exhaustion-and-offline-exports/stdout.log) · [stderr.log](../../verification/runs/20261109T152816557771Z-spread-ui-real-three-viewport-qualification-account-exhaustion-and-offline-exports/stderr.log) · [runner-stderr.log](../../verification/runs/20261109T152816557771Z-spread-ui-real-three-viewport-qualification-account-exhaustion-and-offline-exports/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261109T152816557771Z-spread-ui-real-three-viewport-qualification-account-exhaustion-and-offline-exports/browser/runner-stdout.log)

````text
    Error: expect(received).toBe(expected) // Object.is equality
````

## 20261109T153453091038Z-spread-original-account-link-explicit-repair-authored-missing-contract

[Receipt](../../verification/receipts/20261109T153453091038Z-spread-original-account-link-explicit-repair-authored-missing-contract.json) · command exit `2` · [stdout.log](../../verification/runs/20261109T153453091038Z-spread-original-account-link-explicit-repair-authored-missing-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T153453091038Z-spread-original-account-link-explicit-repair-authored-missing-contract/stderr.log)

````text
E     File "<workspace>\verification\runs\spread-link-repair-authored.py", line 62
E       assert [s['account_job']['id'] for s in saved]==[child['id'],child['id']
E                                                       ^
````

## 20261109T153505419092Z-spread-original-account-link-explicit-repair-corrected-authored-missing-contract

[Receipt](../../verification/receipts/20261109T153505419092Z-spread-original-account-link-explicit-repair-corrected-authored-missing-contract.json) · command exit `2` · [stdout.log](../../verification/runs/20261109T153505419092Z-spread-original-account-link-explicit-repair-corrected-authored-missing-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T153505419092Z-spread-original-account-link-explicit-repair-corrected-authored-missing-contract/stderr.log)

````text
Traceback:
E   ModuleNotFoundError: No module named 'backend.lab.spread_jobs'
ERROR ..\..\..\verification\runs\spread-link-repair-authored.py
````

## 20261109T153534317623Z-spread-original-account-link-explicit-repair-owned-import-missing-contract

[Receipt](../../verification/receipts/20261109T153534317623Z-spread-original-account-link-explicit-repair-owned-import-missing-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T153534317623Z-spread-original-account-link-explicit-repair-owned-import-missing-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T153534317623Z-spread-original-account-link-explicit-repair-owned-import-missing-contract/stderr.log)

````text
E    AssertionError: Explicit original-account link repair is not implemented
E    assert False
E     +  where False = callable(None)
````

## 20261109T153725923362Z-spread-ui-current-real-three-viewport-accounts-reopen-exports-and-request-ownership

[Receipt](../../verification/receipts/20261109T153725923362Z-spread-ui-current-real-three-viewport-accounts-reopen-exports-and-request-ownership.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T153725923362Z-spread-ui-current-real-three-viewport-accounts-reopen-exports-and-request-ownership/stdout.log) · [stderr.log](../../verification/runs/20261109T153725923362Z-spread-ui-current-real-three-viewport-accounts-reopen-exports-and-request-ownership/stderr.log) · [runner-stderr.log](../../verification/runs/20261109T153725923362Z-spread-ui-current-real-three-viewport-accounts-reopen-exports-and-request-ownership/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261109T153725923362Z-spread-ui-current-real-three-viewport-accounts-reopen-exports-and-request-ownership/browser/runner-stdout.log)

````text
    Error: route.fulfill: Route is already handled!
    Error: expect(locator).toContainText(expected) failed
    Error: element(s) not found
````

## 20261109T154603431413Z-spread-original-child-orphan-double-parent-record-loss-authored-refusal-contract

[Receipt](../../verification/receipts/20261109T154603431413Z-spread-original-child-orphan-double-parent-record-loss-authored-refusal-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T154603431413Z-spread-original-child-orphan-double-parent-record-loss-authored-refusal-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T154603431413Z-spread-original-child-orphan-double-parent-record-loss-authored-refusal-contract/stderr.log)

````text
E    Failed: DID NOT RAISE StateError
FAILED ::test_both_parent_side_relationship_records_lost_still_preserve_original_child[status]
FAILED ::test_both_parent_side_relationship_records_lost_still_preserve_original_child[continue]
````

## 20261109T155108830745Z-spread-reverse-child-index-malformed-ids-bounded-two-row-seek-and-query-plan

[Receipt](../../verification/receipts/20261109T155108830745Z-spread-reverse-child-index-malformed-ids-bounded-two-row-seek-and-query-plan.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T155108830745Z-spread-reverse-child-index-malformed-ids-bounded-two-row-seek-and-query-plan/stdout.log) · [stderr.log](../../verification/runs/20261109T155108830745Z-spread-reverse-child-index-malformed-ids-bounded-two-row-seek-and-query-plan/stderr.log)

````text
E       backend.lab.store.StateError: Spread accounts require their original parent continuation binding.
FAILED ::test_reverse_index_rejects_malformed_child_id_before_any_account_work[bad]
FAILED ::test_reverse_index_rejects_malformed_child_id_before_any_account_work[gggggggggggggggggggggggggggggggg]
````

## 20261109T155138667234Z-spread-reverse-child-index-corrected-nonfinancial-metadata-fixture-malformed-ids-and-seek

[Receipt](../../verification/receipts/20261109T155138667234Z-spread-reverse-child-index-corrected-nonfinancial-metadata-fixture-malformed-ids-and-seek.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T155138667234Z-spread-reverse-child-index-corrected-nonfinancial-metadata-fixture-malformed-ids-and-seek/stdout.log) · [stderr.log](../../verification/runs/20261109T155138667234Z-spread-reverse-child-index-corrected-nonfinancial-metadata-fixture-malformed-ids-and-seek/stderr.log)

````text
E     sqlite3.IntegrityError: FOREIGN KEY constraint failed
FAILED ::test_reverse_index_rejects_malformed_child_id_before_any_account_work[bad]
FAILED ::test_reverse_index_rejects_malformed_child_id_before_any_account_work[gggggggggggggggggggggggggggggggg]
````

## 20261109T155419778701Z-spread-published-settings-run-and-empty-continuation-schema-authored-contract

[Receipt](../../verification/receipts/20261109T155419778701Z-spread-published-settings-run-and-empty-continuation-schema-authored-contract.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T155419778701Z-spread-published-settings-run-and-empty-continuation-schema-authored-contract/stdout.log) · [stderr.log](../../verification/runs/20261109T155419778701Z-spread-published-settings-run-and-empty-continuation-schema-authored-contract/stderr.log)

````text
E    AssertionError: Saved spread machine-readable contracts are missing or differ from actual models
E    assert {'spread_sett...uation': None} == {'spread_sett...uation', ...}}
E      
````

## 20261109T155641512018Z-spread-isolated-version025-rulebook-public-schema-and-partial-implementation-map-update

[Receipt](../../verification/receipts/20261109T155641512018Z-spread-isolated-version025-rulebook-public-schema-and-partial-implementation-map-update.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T155641512018Z-spread-isolated-version025-rulebook-public-schema-and-partial-implementation-map-update/stdout.log) · [stderr.log](../../verification/runs/20261109T155641512018Z-spread-isolated-version025-rulebook-public-schema-and-partial-implementation-map-update/stderr.log)

````text
Traceback (most recent call last):
AssertionError
````

## 20261109T160028053105Z-spread-version025-current-eighteen-browser-workflows-public-schema-and-owned-lifecycle

[Receipt](../../verification/receipts/20261109T160028053105Z-spread-version025-current-eighteen-browser-workflows-public-schema-and-owned-lifecycle.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T160028053105Z-spread-version025-current-eighteen-browser-workflows-public-schema-and-owned-lifecycle/stdout.log) · [stderr.log](../../verification/runs/20261109T160028053105Z-spread-version025-current-eighteen-browser-workflows-public-schema-and-owned-lifecycle/stderr.log) · [runner-stderr.log](../../verification/runs/20261109T160028053105Z-spread-version025-current-eighteen-browser-workflows-public-schema-and-owned-lifecycle/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261109T160028053105Z-spread-version025-current-eighteen-browser-workflows-public-schema-and-owned-lifecycle/browser/runner-stdout.log)

````text
    Error: expect(locator).toContainText(expected) failed
````

## 20261109T170744396194Z-spread-version025-first-current-twenty-seven-module-unrounded-numerical-gate

[Receipt](../../verification/receipts/20261109T170744396194Z-spread-version025-first-current-twenty-seven-module-unrounded-numerical-gate.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T170744396194Z-spread-version025-first-current-twenty-seven-module-unrounded-numerical-gate/stdout.log) · [stderr.log](../../verification/runs/20261109T170744396194Z-spread-version025-first-current-twenty-seven-module-unrounded-numerical-gate/stderr.log)

No recognized diagnostic signature selected; inspect the preserved logs.

## 20261109T171206679734Z-spread-version025-current-browser-original-bytes-complete-decimal-accounts-csv-and-presentation-fact-audit

[Receipt](../../verification/receipts/20261109T171206679734Z-spread-version025-current-browser-original-bytes-complete-decimal-accounts-csv-and-presentation-fact-audit.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T171206679734Z-spread-version025-current-browser-original-bytes-complete-decimal-accounts-csv-and-presentation-fact-audit/stdout.log) · [stderr.log](../../verification/runs/20261109T171206679734Z-spread-version025-current-browser-original-bytes-complete-decimal-accounts-csv-and-presentation-fact-audit/stderr.log)

````text
Traceback (most recent call last):
AssertionError
````

## 20261109T171348540412Z-spread-version025-valid-empty-interrupted-batch-and-duplicate-staged-plan-boundaries

[Receipt](../../verification/receipts/20261109T171348540412Z-spread-version025-valid-empty-interrupted-batch-and-duplicate-staged-plan-boundaries.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T171348540412Z-spread-version025-valid-empty-interrupted-batch-and-duplicate-staged-plan-boundaries/stdout.log) · [stderr.log](../../verification/runs/20261109T171348540412Z-spread-version025-valid-empty-interrupted-batch-and-duplicate-staged-plan-boundaries/stderr.log)

````text
E    KeyError: 'current_probe'
FAILED ::test_valid_empty_status_interrupted_batch_and_duplicate_trial_are_distinct
````

## 20261109T171431456524Z-spread-version025-current-twenty-seven-module-unchanged-95-90-passing-gate

[Receipt](../../verification/receipts/20261109T171431456524Z-spread-version025-current-twenty-seven-module-unchanged-95-90-passing-gate.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T171431456524Z-spread-version025-current-twenty-seven-module-unchanged-95-90-passing-gate/stdout.log) · [stderr.log](../../verification/runs/20261109T171431456524Z-spread-version025-current-twenty-seven-module-unchanged-95-90-passing-gate/stderr.log)

````text
Traceback (most recent call last):
````

## 20261109T172717134628Z-integrated-version025-twelve-existing-synthetic-desktop-compatibility-workflows

[Receipt](../../verification/receipts/20261109T172717134628Z-integrated-version025-twelve-existing-synthetic-desktop-compatibility-workflows.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T172717134628Z-integrated-version025-twelve-existing-synthetic-desktop-compatibility-workflows/stdout.log) · [stderr.log](../../verification/runs/20261109T172717134628Z-integrated-version025-twelve-existing-synthetic-desktop-compatibility-workflows/stderr.log) · [runner-stderr.log](../../verification/runs/20261109T172717134628Z-integrated-version025-twelve-existing-synthetic-desktop-compatibility-workflows/browser/runner-stderr.log) · [runner-stdout.log](../../verification/runs/20261109T172717134628Z-integrated-version025-twelve-existing-synthetic-desktop-compatibility-workflows/browser/runner-stdout.log)

````text
    TimeoutError: locator.selectOption: Timeout 15000ms exceeded.
````

## 20261109T181207112616Z-trade-twins-authored-complete-cohort-geometry-before-implementation-assertion-failure

[Receipt](../../verification/receipts/20261109T181207112616Z-trade-twins-authored-complete-cohort-geometry-before-implementation-assertion-failure.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T181207112616Z-trade-twins-authored-complete-cohort-geometry-before-implementation-assertion-failure/stdout.log) · [stderr.log](../../verification/runs/20261109T181207112616Z-trade-twins-authored-complete-cohort-geometry-before-implementation-assertion-failure/stderr.log)

````text
E                                                                        [100%]
E       AssertionError: D046 complete-cohort twin core has not been implemented.
E       assert None is not None
````

## 20261109T181222271493Z-trade-twins-authored-missing-complete-cohort-implementation-test-body-assertion

[Receipt](../../verification/receipts/20261109T181222271493Z-trade-twins-authored-missing-complete-cohort-implementation-test-body-assertion.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T181222271493Z-trade-twins-authored-missing-complete-cohort-implementation-test-body-assertion/stdout.log) · [stderr.log](../../verification/runs/20261109T181222271493Z-trade-twins-authored-missing-complete-cohort-implementation-test-body-assertion/stderr.log)

````text
E       AssertionError: D046 complete-cohort twin core has not been implemented.
E       assert None is not None
E        +  where None = <function find_spec at 0x000001F34104F060>('backend.lab.trade_twins')
````

## 20261109T182517310670Z-trade-twins-authored-original-entry-trace-red-against-unchanged-financial-oracle

[Receipt](../../verification/receipts/20261109T182517310670Z-trade-twins-authored-original-entry-trace-red-against-unchanged-financial-oracle.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T182517310670Z-trade-twins-authored-original-entry-trace-red-against-unchanged-financial-oracle/stdout.log) · [stderr.log](../../verification/runs/20261109T182517310670Z-trade-twins-authored-original-entry-trace-red-against-unchanged-financial-oracle/stderr.log)

````text
E       AssertionError: Original entry-time traces are not implemented.
E       assert False
E        +  where False = hasattr(Simulation(trades=[{'id': 'known', 'symbol': 'SPY', 'strategy_id': '1505c9f0c8c8bd8e3c7d080174163547dc173753d94d1f2ef5...xit; new orders use whole shares.', 'Borrow accrues on prior marked short notional over elapsed calendar time / 365.']), 'entry_traces')
````

## 20261109T182559468844Z-trade-twins-original-entry-traces-actual-reports-splits-and-unchanged-independent-execution-regression

[Receipt](../../verification/receipts/20261109T182559468844Z-trade-twins-original-entry-traces-actual-reports-splits-and-unchanged-independent-execution-regression.json) · command exit `1` · [stdout.log](../../verification/runs/20261109T182559468844Z-trade-twins-original-entry-traces-actual-reports-splits-and-unchanged-independent-execution-regression/stdout.log) · [stderr.log](../../verification/runs/20261109T182559468844Z-trade-twins-original-entry-traces-actual-reports-splits-and-unchanged-independent-execution-regression/stderr.log)

````text
E   dataclasses.FrozenInstanceError: cannot assign to field 'atr'
E           KeyError: 'entry_traces'
FAILED tests/test_entry_traces.py::test_entry_trace_is_not_changed_by_later_split_dividend_or_borrow[2.0-1]
````
