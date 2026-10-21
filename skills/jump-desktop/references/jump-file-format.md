# .jump / .jdz file format

Source: Jump Desktop support article "General: Jump Desktop file formats".

A `.jdz` is a zip containing `servers/*.jump`. Each `.jump` is one JSON object.

## Computer (`TypeCode: 1`)

| Key | Type | Notes |
| --- | --- | --- |
| `TypeCode` | int | always 1 |
| `ConnectionTypeCode` | int | always 0 for manual entries |
| `UniqueId` | string | unique across computers, SSH servers, gateways |
| `DisplayName` | string | name in the UI |
| `TcpHostName` | string | host or IP |
| `TcpPort` | int | 3389 RDP, 5900 VNC by default |
| `ProtocolTypeCode` | int | 0 RDP, 1 VNC |
| `Username` / `Domain` | string | login; leave password out |
| `Tags` | string[] | UI tags |
| `ColorDepthCode` | int | 0 8-bit, 2 16-bit, 3 24-bit, 4 b/w (VNC), 5 grey (VNC) |
| `ClipboardRedirection` | bool | |
| `MatchScreenResolution` | bool | ignore `ResolutionWidth`/`ResolutionHeight` |
| `UseDynamicResolutionUpdate` | bool | resize remote with window (RDP Win8+/Fluid) |
| `ChangeResolution` | bool | Fluid only |
| `StartInFullscreen` | bool | Mac/Windows viewer |
| `MouseCursorUpdates` | bool | Mac viewer |
| `SwapMouseButtons` | bool | |
| `MacAddresses` | string[] | `"00 0C 29 5A C6 79"`, used for Wake-on-LAN before connecting |
| `SshServerUniqueId` | string/null | tunnel through an SSH entry |
| `RDGatewayUniqueId` | string/null | RD Gateway entry |
| `SslCertificateFingerPrint` | string/null | base64 |
| `IgnoreCertificateErrors` | bool | RDP |
| `AudioPlaybackCode` | int | RDP: 0 off, 1 remote, 2 local |
| `RdpConsoleSession`, `RdpDisableNLA`, `RdpDriveRedirection`, `RdpPrinterRedirection`, `RdpUseUnicodeKeyboard`, `RdpDisableBitmapCaching`, `RdpDisableServerRedirection` | bool | RDP |
| `RdpPerformanceFlags` | int | bitfield: 0x01 wallpaper off, 0x02 no full drag, 0x04 no menu anim, 0x08 no theming, 0x80 font smoothing |
| `ResolutionWidth` / `ResolutionHeight` | int | RDP |
| `MonitorCount`, `UseAllMonitors` | int/bool | RDP |
| `DriveMappings` | object[] | `{DisplayName, Enabled, IsReadOnly, LocalPath, UniqueId}` |
| `KeyboardAutomaticLocaleDetection`, `KeyboardLocaleId` | bool/int | RDP and ARD |

## SSH server (`TypeCode: 2`)

`UniqueId`, `DisplayName`, `TcpHostName`, `TcpPort`, `Username`,
`AuthenticationTypeCode` (0 password, 1 public key), `PrivateSshKeyPath`,
`PublicKey` (server fingerprint, hex bytes). A computer references it through
`SshServerUniqueId`.

## RD Gateway (`TypeCode: 3`)

`UniqueId`, `DisplayName`, `TcpHostName`, `TcpPort`, `Username`, `Domain`
(null to reuse the computer's).

## jump:// URL scheme

`jump://?host=<host>&protocol=rdp|vnc|fluid&port=<port>&username=<user>` plus
any key above as a parameter. Connect hosts also print a LAN-only Fluid URL
with `JumpConnect --cloudlessurl`.
