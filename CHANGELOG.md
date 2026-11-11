# Changelog

## Unreleased

- Audio conversion before upload (new page "Conversion"): rules convert recordings of chosen file types (e.g. WAV, AIFF) to FLAC, MP3 or AAC (.m4a) with ffmpeg; bitrate (CBR/VBR for MP3), FLAC compression level and bit depth, sample rate and channels are configurable; the original can be uploaded as well; if a conversion fails, the original is uploaded instead. The installer now installs `ffmpeg`.
- File manager for the USB stick contents (FileGator, under /fm/, login shared with NetUSBFlash): read-only view while the host is connected, edit mode for managers that disconnects the host (30-minute timeout)
- Notification rules: custom subject and HTML text with placeholders, rich-text editor (Quill), preview and test mail; mails are sent as HTML with a plain-text part
- Updates page: NetUSBFlash updates from GitHub releases (checksum-verified, optional pre-releases, daily check) and Raspberry Pi OS package updates, with live log
- Backup page: download (passwords optionally encrypted with a passphrase), restore, scheduled upload to a storage target folder
- Release workflow: tags v* build netusbflash-<version>.tar.gz (FileGator bundled) with a SHA-256 file
- Navigation: administration pages grouped in a menu
- systemd: PrivateTmp/ProtectHome removed so the file manager's mount is visible to PHP-FPM

- Web interface: all pages load and save their data via AJAX; a loading spinner is shown during every request
- Setup wizard: page skeleton in HTML, steps loaded and submitted via AJAX
- Bootstrap 5.3.3 and Bootstrap Icons 1.11.3 are bundled in the repository
- Fix: PHP 8.5 deprecation warning (curl_close)
- Fix: time zone selection was empty when the current zone was not in the list

## 0.1.0-alpha.1 – 2026-10-26

First alpha.

- USB mass-storage gadget (configfs) with exFAT/FAT32 disk image and configurable identity
- Recording detection with idle wait; sync modes "detach" and "live"
- Upload queue with retries to SMB/CIFS, WebDAV/Nextcloud, FTP, FTPS, SFTP, SSHFS, SCP and local folders
- Email notifications via SMTP (instant or digest) for created, modified, deleted, uploaded and failed files
- Web interface in English and German with Bootstrap 5 (served locally), LAN-only access
- Users with four roles, lockout after failed logins, forced password change for new users
- Setup wizard protected by a one-time code
- Installer for Raspberry Pi OS, systemd service, nginx site, nftables rules, recovery CLI
- Development mode with a simulated USB stick; unit and API tests
