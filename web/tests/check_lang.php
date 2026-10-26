<?php

declare(strict_types=1);

/*
 * Checks that en.php and de.php have the same keys and that every
 * translation key used in the code exists. Run: php web/tests/check_lang.php
 */

$root = dirname(__DIR__);
$en = require $root . '/lang/en.php';
$de = require $root . '/lang/de.php';
$failures = [];

foreach (array_diff(array_keys($en), array_keys($de)) as $key) {
    $failures[] = "missing in de.php: $key";
}
foreach (array_diff(array_keys($de), array_keys($en)) as $key) {
    $failures[] = "missing in en.php: $key";
}

// Keys that are built at runtime from a prefix and a known set of values.
$dynamic = [
    'role.' => ['viewer', 'operator', 'manager', 'admin', 'viewer_help', 'operator_help', 'manager_help', 'admin_help'],
    'protocol.' => ['smb', 'webdav', 'ftp', 'ftps', 'sftp', 'sshfs', 'scp', 'local'],
    'monitor.' => ['idle', 'host_writing', 'waiting_idle', 'syncing'],
    'event.' => ['created', 'modified', 'deleted', 'uploaded', 'upload_failed'],
    'setup.step.' => ['admin', 'system', 'usb', 'target', 'smtp', 'finish'],
    'upload.status_' => ['pending', 'done', 'failed', 'discarded'],
    'usb.done_' => ['sync', 'attach', 'detach'],
    'usb.sync_' => ['detach', 'live', 'detach_help', 'live_help'],
    'system.' => ['reboot_started', 'poweroff_started'],
];
foreach ($dynamic as $prefix => $suffixes) {
    foreach ($suffixes as $suffix) {
        if (!isset($en[$prefix . $suffix])) {
            $failures[] = "dynamic key missing: $prefix$suffix";
        }
    }
}

$iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root, FilesystemIterator::SKIP_DOTS));
foreach ($iterator as $file) {
    if ($file->getExtension() !== 'php' || str_contains($file->getPathname(), '/lang/') || str_contains($file->getPathname(), '/tests/')) {
        continue;
    }
    preg_match_all("/(?<![A-Za-z_])t\\('([a-z_.0-9]+)'[,)]/", (string) file_get_contents($file->getPathname()), $m);
    foreach ($m[1] as $key) {
        if (!isset($en[$key])) {
            $failures[] = "used but not defined: $key (" . substr($file->getPathname(), strlen($root) + 1) . ')';
        }
    }
}

if ($failures) {
    fwrite(STDERR, implode("\n", array_unique($failures)) . "\n");
    exit(1);
}
echo 'Language files OK (' . count($en) . " keys)\n";
