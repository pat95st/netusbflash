# Changelog

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
