$ErrorActionPreference = 'Stop'
$events = @(Get-WinEvent -FilterHashtable @{LogName='System';StartTime=[datetime]'2026-11-09T16:00:00Z';EndTime=[datetime]'2026-11-09T16:38:00Z';Id=506,507} |
    Where-Object {$_.ProviderName -eq 'Microsoft-Windows-Kernel-Power'} |
    Sort-Object TimeCreated |
    ForEach-Object {
        $message = $_.Message
        $action = if ($message -match '(?i)entering (connected|modern) standby') {'entering_standby'} elseif ($message -match '(?i)exiting (connected|modern) standby') {'exiting_standby'} else {'unclassified_power_event'}
        [pscustomobject]@{at_utc=$_.TimeCreated.ToUniversalTime().ToString('o');id=$_.Id;record_id=$_.RecordId;action=$action}
    })
$value = [ordered]@{scope='Bounded OS power-event metadata only; excludes account, computer and message details';events=$events;browser_receipt='20261109T160028053105Z-spread-version025-current-eighteen-browser-workflows-public-schema-and-owned-lifecycle';timing_result_accepted=$false;power_plan_changed=$false}
$value | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $env:PA_EVIDENCE_RUN_DIR 'verification-standby-gap.json') -Encoding utf8
$value | ConvertTo-Json -Depth 5
