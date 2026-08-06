# Cortex XDR Legacy Exception Rules — NICE-5CG40406JD

## Context

Endpoint NICE-5CG40406JD (user: RRL\dpullen) is experiencing high resource consumption caused by a cross-scanning loop between 5 concurrent security products. The Cortex XDR kernel driver (tedrdrv.sys) traces file and registry operations from Defender AV, Rapid7, BeyondTrust, and Sysmon, generating 443K file events and 790K registry events from cyserver.exe during an idle session.

The existing 29 legacy exception rules have zero Behavioral Threat Protection exclusions, no coverage of MsMpEng.exe (the #1 CPU consumer at 8.47%), and only partial coverage of Rapid7. All paths below are sourced from the msinfo32 running tasks list and energy report captured on 2026-07-30.

## Existing Coverage (Already Configured)

- MDE ATP processes (MsSense.exe, SenseCE.exe, etc.) — Operational Agent Exception, Global
- MDE DataCollection path — Endpoint Scanning, Profile
- FortiClient paths and processes — Endpoint Scanning + Process Exceptions
- CrowdStrike — Operational + Endpoint Scanning (not installed on this endpoint)
- SentinelOne — Operational Agent Exception (not installed on this endpoint)

## New Rules to Create

All rules created via Settings > Exception Configurations > Legacy Agent Exceptions > + Add Rule.

### Rule A — Behavioral Threat Protection: Defender AV

- **Platform**: Windows
- **Module**: Behavioral Threat Protection
- **Scope**: Global
- **Justification**: MsMpEng.exe is the #1 CPU consumer at 8.47%. Cortex XDR traces every file and registry operation it generates. Definition Updates folder produces high I/O during signature updates.

```
C:\ProgramData\Microsoft\Windows Defender\Platform\*\MsMpEng.exe
C:\ProgramData\Microsoft\Windows Defender\Platform\*\MpDefenderCoreService.exe
C:\ProgramData\Microsoft\Windows Defender\Platform\*\NisSrv.exe
C:\ProgramData\Microsoft\Windows Defender\Platform\*\MpCmdRun.exe
C:\ProgramData\Microsoft\Windows Defender\Platform\*\DlpUserAgent.exe
C:\ProgramData\Microsoft\Windows Defender\Definition Updates\*
C:\Program Files\Windows Defender Advanced Threat Protection\SenseTracer.exe
C:\Program Files\Windows Defender Advanced Threat Protection\SenseTVM.exe
```

### Rule B — Behavioral Threat Protection: Rapid7

- **Platform**: Windows
- **Module**: Behavioral Threat Protection
- **Scope**: Global
- **Justification**: Rapid7 runs 10 processes including a 90 MB Velociraptor binary. Only a partial Endpoint Scanning rule exists today. Version-numbered component directories require a single wildcard.

```
C:\Program Files\Rapid7\Insight Agent\ir_agent.exe
C:\Program Files\Rapid7\Insight Agent\components\velociraptor\*\rapid7_velociraptor.exe
C:\Program Files\Rapid7\Insight Agent\components\events_monitor\*\rapid7_events_monitor.exe
C:\Program Files\Rapid7\Insight Agent\components\endpoint_broker\*\rapid7_endpoint_broker.exe
C:\Program Files\Rapid7\Insight Agent\components\agent_core\*\rapid7_agent_core.exe
C:\Program Files\Rapid7\Insight Agent\components\insight_agent\*\ir_agent.exe
C:\Program Files\Rapid7\Insight Agent\components\sysmon_installer\*\rapid7_sysmon_installer.exe
C:\Program Files\Rapid7\Insight Agent\components\armor\common\armor\mvarmorservice32.exe
C:\Program Files\Rapid7\Insight Agent\components\armor\common\armor\mvarmorservice64.exe
C:\Program Files\Rapid7\Insight Agent\components\armor\common\armor\plugins\64bit\armorpluginhost64.exe
```

### Rule C — Behavioral Threat Protection: BeyondTrust

- **Platform**: Windows
- **Module**: Behavioral Threat Protection
- **Scope**: Global
- **Justification**: PGDriver.sys (BeyondTrust kernel driver) appears in kernel stacks of multiple unrelated processes in the energy report. No exception exists today.

```
C:\Program Files\Avecto\Privilege Guard Client\defendpointservice.exe
C:\Program Files\Avecto\Privilege Guard Client\PGSystemTray.exe
```

### Rule D — Behavioral Threat Protection: Management Agents

- **Platform**: Windows
- **Module**: Behavioral Threat Protection
- **Scope**: Global
- **Justification**: SCCM and Intune agents generate high I/O during policy sync and software deployment. No exceptions exist today.

```
C:\Windows\CCM\ccmexec.exe
C:\Windows\CCM\RemCtrl\CmRcService.exe
C:\Program Files (x86)\Microsoft Intune Management Extension\Microsoft.Management.Services.IntuneWindowsAgent.exe
C:\Program Files\Common Files\Microsoft Shared\ClickToRun\OfficeClickToRun.exe
```

### Rule E — Operational Agent Exception: Defender AV Engine

- **Platform**: Windows
- **Module**: Operational Agent Exceptions
- **Scope**: Global
- **Justification**: Existing MDE Operational exceptions cover ATP processes only. The antivirus engine (MsMpEng.exe) has no operational exception despite being the top CPU consumer. Wildcard in Platform path is required because Defender rotates version-numbered subdirectories on update.

```
C:\ProgramData\Microsoft\Windows Defender\Platform\*\MsMpEng.exe
C:\ProgramData\Microsoft\Windows Defender\Platform\*\MpDefenderCoreService.exe
C:\ProgramData\Microsoft\Windows Defender\Platform\*\NisSrv.exe
```

### Rule F — Operational Agent Exception: Rapid7

- **Platform**: Windows
- **Module**: Operational Agent Exceptions
- **Scope**: Global
- **Justification**: No operational exception exists for any Rapid7 process. These are the core agent and high-I/O components observed running on the endpoint.

```
C:\Program Files\Rapid7\Insight Agent\ir_agent.exe
C:\Program Files\Rapid7\Insight Agent\components\velociraptor\*\rapid7_velociraptor.exe
C:\Program Files\Rapid7\Insight Agent\components\events_monitor\*\rapid7_events_monitor.exe
C:\Program Files\Rapid7\Insight Agent\components\endpoint_broker\*\rapid7_endpoint_broker.exe
C:\Program Files\Rapid7\Insight Agent\components\agent_core\*\rapid7_agent_core.exe
C:\Program Files\Rapid7\Insight Agent\components\armor\common\armor\mvarmorservice64.exe
C:\Program Files\Rapid7\Insight Agent\components\armor\common\armor\mvarmorservice32.exe
```

### Rule G — Operational Agent Exception: BeyondTrust

- **Platform**: Windows
- **Module**: Operational Agent Exceptions
- **Scope**: Global
- **Justification**: defendpointservice.exe runs as a core system service with no operational exception. PGDriver.sys contributes to kernel-level overhead across multiple processes.

```
C:\Program Files\Avecto\Privilege Guard Client\defendpointservice.exe
```

### Rule H — Endpoint Scanning: Defender AV Folders

- **Platform**: Windows
- **Module**: Endpoint Scanning
- **Scope**: Global
- **Justification**: Existing Endpoint Scanning rule only covers the ATP DataCollection path. The Definition Updates and Platform subdirectories generate the highest I/O from Defender and are not covered.

```
C:\ProgramData\Microsoft\Windows Defender\Definition Updates\*
C:\ProgramData\Microsoft\Windows Defender\Platform\*
```

## Notes

- All paths sourced from msinfo32 running tasks list and energy report from diagnostic collection 2026-07-30.
- Wildcards used only where version-numbered directories rotate on product updates.
- Developer build path exclusions deferred pending confirmation of actual paths from the customer.
- Sysmon64.exe excluded from this list — low impact (0.40% CPU) and sits in a sensitive path (C:\Windows\). Can be added later if needed.
- Recommend piloting on 5-10 devices including NICE-5CG40406JD, then recapturing telemetry to validate reduction in cyserver.exe file/registry event counts before broad rollout.

## Existing Rules to Clean Up

- `win_exception_MDE_Common_FileScanning` — duplicated (2 copies)
- `win_exception_MDE_Workstations_operational` — duplicated (2 copies)
- `win_exception_MDE_Servers_operational` — duplicated (2 copies)
- `Imported from U42 Golden Image Malware Profile profile` — 8 identical rules
