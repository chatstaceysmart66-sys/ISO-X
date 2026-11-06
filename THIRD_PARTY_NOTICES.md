# ISO-X — Third-party notices and integration decisions

This file records the reviewed upstream sources used to inform ISO-X's desktop usability. ISO-X is a Debian/Linux live-system project; it is not a Windows ISO and the Windows-specific presets below cannot be applied directly to a Linux filesystem.

## 1. RobertoBiundo/Windows10Lite

Source: https://github.com/RobertoBiundo/Windows10Lite

Files reviewed: `README.md` (3,110 characters), `NTLite.xml` (20,895 characters; 406 `<c>` removal entries), `Remove All User Folders From This PC 64-bit.reg` (3,620 characters; 24 registry-key deletion entries), and the repository listing.

The XML identifies Windows 10 Pro 64-bit build 16299.x and an NTLite 1.3.1-era preset dated 2017-10-24. Its removal list includes Windows Security/Defender (`Microsoft.Windows.SecHealthUI`), SmartScreen (`Microsoft.Windows.Apprep.ChxApp`), Microsoft Edge, Windows Store, accessibility tools, Action Center, many language packs and keyboard layouts including Arabic, and many device/driver components. The README explicitly warns that Windows Update is unavailable in the result, Windows Defender is absent, browsers are not included, drivers may need manual installation, and the preset is English/US-International only. The `.reg` file deletes Explorer namespace entries for user folders such as Desktop, Documents, Downloads, Music, Pictures and Videos from “This PC”; it is not a Linux desktop configuration.

**Integration decision:** the NTLite XML and its Windows component-removal list are not executed or copied into ISO-X. They are Windows-specific, old, and can remove protection, drivers, accessibility features, languages, and update functionality. ISO-X instead adapts general usability ideas using its own GTK/Openbox interface, launcher, desktop shortcuts, localized welcome panel, and existing `apply-windows-look.sh`. No claim is made that ISO-X contains or was built by NTLite.

## 2. windows10loud/Download-Windows-10-PRO-ISO-fast-and-lite

Source: https://github.com/windows10loud/Download-Windows-10-PRO-ISO-fast-and-lite

Files reviewed: `README.md` (5,636 characters), repository root listing, and metadata for `Windows 10 PRO x64.torrent` (12,347 bytes). The repository has no GitHub releases listing for a verified ISO asset; its README points to external file-hosting links and states that the described custom Windows image removes Windows Defender. The repository listing gives no checksum for a released ISO, and the source repository has no clearly established license for redistributing its Windows build.

**Integration decision:** the torrent, third-party Windows image, download links, and Windows binaries are not bundled into ISO-X. Their provenance, redistribution permission, integrity, and safety cannot be established by this project. ISO-X does not silently disable security protections or ship an unverified Windows image. For Windows installation media, obtain a genuine ISO from Microsoft and verify it separately. The torrent metadata itself was not downloaded or included.

## 3. ISO-X custom integration

The new ISO-X welcome app and shortcuts are original project integration. They use the ISO-X dragon assets, offer safe command-vector launching, display local machine information, and require confirmation before opening the disk installer. They do not send telemetry. Windows-like words such as “This PC” are user-interface labels; ISO-X remains Debian/Linux.

## Licensing and attribution

The above repositories remain credited as research references; their source files are not copied into ISO-X. Their licences and redistribution terms are separate from ISO-X's own source notice. Debian, kernel, GTK, Openbox, and other packages remain under their respective upstream licences. ISO-X's branding does not claim ownership of Microsoft's Windows trademarks or third-party software.
