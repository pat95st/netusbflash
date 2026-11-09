// Browser end-to-end test of the web UI with a simulated USB stick.
//
// Needs Node.js and Playwright (npm install -g playwright && npx playwright install chromium).
// Start a fresh development instance first, then run the test:
//
//   rm -rf .dev && PORT=8099 ./scripts/dev-server.sh &
//   node web/tests/e2e.js [screenshot-folder]
//
// It walks through the setup wizard, every page, a simulated recording and
// the role checks, and fails on any JavaScript error.
const { chromium } = require('playwright');
const fs = require('fs');
const os = require('os');
const path = require('path');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8099';
const HOME = process.env.NETUSBFLASH_HOME || path.join(__dirname, '..', '..', '.dev');
const OUT = process.argv[2] || fs.mkdtempSync(path.join(os.tmpdir(), 'nuf-e2e-'));
const problems = [];
function check(cond, msg) { if (!cond) { problems.push(msg); console.log('FAIL: ' + msg); } else { console.log('ok:   ' + msg); } }

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: 'en-US' });
  const page = await ctx.newPage();
  // HTTP error statuses are provoked on purpose (validation, last admin); only real JS errors count.
  page.on('console', m => { if (m.type() === 'error' && !m.text().startsWith('Failed to load resource')) problems.push('console: ' + m.text()); });
  page.on('pageerror', e => problems.push('pageerror: ' + e.message));
  page.on('dialog', d => d.accept());

  const spinnerHidden = () => page.waitForFunction(() =>
    [...document.querySelectorAll('[data-loading]')].every(el => el.hidden), null, { timeout: 15000 });

  // Slow down AJAX once to see the spinner.
  let slow = true;
  await page.route(/\/(ajax\/api|setup\/api)\//, async route => {
    if (slow) { await new Promise(r => setTimeout(r, 700)); }
    await route.continue();
  });

  // ---- Setup wizard
  await page.goto(BASE + '/setup');
  check(await page.locator('[data-loading]').first().isVisible(), 'setup: spinner visible while state loads');
  await spinnerHidden();
  check(await page.locator('[data-screen="code"]').isVisible(), 'setup: code screen shown');
  slow = false;
  await page.fill('#code', 'AAAA-BBBB-CCCC');
  await page.click('[data-screen="code"] button[type=submit]');
  await spinnerHidden();
  check(await page.locator('[data-screen="code"] .is-invalid').count() > 0, 'setup: wrong code is rejected with field error');
  const code = fs.readFileSync(HOME + '/etc/setup-token', 'utf8').trim();
  await page.fill('#code', code.toLowerCase());
  await page.click('[data-screen="code"] button[type=submit]');
  await page.locator('[data-screen="admin"]').waitFor({ state: 'visible' });
  check(true, 'setup: admin step shown after valid code');
  await page.fill('#admin_email', 'admin@example.com');
  await page.fill('#admin_password', 'short');
  await page.fill('#admin_password_confirm', 'short');
  await page.click('[data-screen="admin"] button[type=submit]');
  await spinnerHidden();
  check(await page.locator('[data-screen="admin"] .invalid-feedback').count() > 0, 'setup: short password shows error');
  await page.fill('#admin_password', 'correct-horse-battery');
  await page.fill('#admin_password_confirm', 'correct-horse-battery');
  await page.click('[data-screen="admin"] button[type=submit]');
  await page.locator('[data-screen="system"]').waitFor({ state: 'visible' });
  check(await page.locator('[data-screen="system"] select[name=timezone] option').count() > 0, 'setup: time zones loaded via AJAX');
  check((await page.inputValue('[data-screen="system"] [name=hostname]')) !== '', 'setup: hostname prefilled');
  check((await page.inputValue('[data-screen="system"] select[name=timezone]')) !== '', 'setup: current time zone preselected');
  await page.screenshot({ path: OUT + '/w_system.png', fullPage: true });
  await page.selectOption('[data-screen="system"] select[name=timezone]', 'UTC');
  await page.click('[data-screen="system"] button[type=submit]');
  await page.locator('[data-screen="usb"]').waitFor({ state: 'visible' });
  check((await page.inputValue('[data-screen="usb"] [name=label]')) === 'RECORDINGS', 'setup: USB defaults loaded');
  await page.fill('[data-screen="usb"] [name=size_mb]', '256');
  await page.fill('[data-screen="usb"] [name=idle_seconds]', '5');
  await page.click('[data-screen="usb"] button[type=submit]');
  await page.locator('[data-screen="target"]').waitFor({ state: 'visible' });
  const sec = '[data-screen="target"] ';
  await page.fill(sec + '[name=name]', 'Archive');
  await page.selectOption(sec + '[name=protocol]', 'local');
  await page.fill(sec + '[name=path]', HOME + '/dest');
  await page.fill(sec + '[name="options.subfolder"], ' + sec + '[name=opt_subfolder]', '');
  await page.click(sec + 'button[value=test]');
  await spinnerHidden();
  check(await page.locator(sec + '.alert-success').count() > 0, 'setup: target connection test succeeds');
  await page.click(sec + 'button[value=save]');
  await page.locator('[data-screen="smtp"]').waitFor({ state: 'visible' });
  await page.click('[data-screen="smtp"] button[value=skip]');
  await page.locator('[data-screen="finish"]').waitFor({ state: 'visible' });
  // Go back one step via the step list, then forward again.
  await page.click('[data-goto="smtp"]');
  await page.locator('[data-screen="smtp"]').waitFor({ state: 'visible' });
  check(true, 'setup: going back to an earlier step works');
  await page.click('[data-screen="smtp"] button[value=skip]');
  await page.locator('[data-screen="finish"]').waitFor({ state: 'visible' });
  await page.click('[data-screen="finish"] button[type=submit]');
  await page.waitForURL(BASE + '/login');
  check(true, 'setup: finish redirects to login');

  // ---- Login
  await page.fill('#username', 'admin');
  await page.fill('#password', 'correct-horse-battery');
  await page.click('button[type=submit]');
  await page.waitForURL(BASE + '/');

  // ---- Every page: spinner during load, hidden afterwards, data rendered
  slow = true;
  for (const [path, probe] of [
    ['/', '#dashboard'], ['/usb', '#usb'], ['/targets', '#targets'], ['/targets/new', '#target-form'],
    ['/uploads', '#uploads'], ['/notifications', '#notifications'], ['/logs', '#logs'],
    ['/logs?tab=audit', '#logs'], ['/users', '#users'], ['/system', '#system'], ['/profile', '#profile'],
    ['/files', '#files'], ['/updates', '#updates'], ['/backup', '#backup'],
  ]) {
    await page.goto(BASE + path);
    const visible = await page.locator('[data-loading]').first().isVisible();
    await spinnerHidden();
    check(visible, path + ': spinner shown while loading');
    check(await page.locator(probe).count() === 1, path + ': skeleton present');
    await page.screenshot({ path: OUT + '/p_' + path.replace(/[^a-z]/g, '_') + '.png', fullPage: true });
  }
  slow = false;

  // ---- Data checks
  await page.goto(BASE + '/system'); await spinnerHidden();
  check(await page.locator('#system select[name=timezone] option').count() > 0, 'system: time zones loaded');
  check((await page.inputValue('#system select[name=timezone]')) !== '', 'system: current time zone preselected');
  await page.click('#system [data-settings-form] button[type=submit]');
  await spinnerHidden();
  check((await page.locator('[data-notices] .alert-success').count()) > 0, 'system: saving unchanged settings works');
  check((await page.locator('#system [data-disk]').textContent()).includes('GB'), 'system: disk info loaded');
  await page.click('#system [data-action=generate_key]').catch(() => {});
  await spinnerHidden();
  const keyShown = (await page.inputValue('#system [data-public-key]')).startsWith('ssh-');
  const keyError = (await page.locator('[data-notices] .alert-danger').count()) > 0;
  check(keyShown || keyError, 'system: SSH key shown, or a clear error when ssh-keygen is missing (' + (keyShown ? 'key' : 'error') + ')');
  await page.fill('#system [name=hostname]', 'bad host!');
  await page.click('#system [data-settings-form] button[type=submit]');
  await spinnerHidden();
  check(await page.locator('#system [name=hostname].is-invalid').count() === 1, 'system: invalid hostname marked');

  await page.goto(BASE + '/users'); await spinnerHidden();
  check(await page.locator('#users [data-users] tr[data-id]').count() === 1, 'users: list loaded');
  await page.fill('#new_username', 'bob');
  await page.selectOption('#new_role', 'viewer');
  await page.click('#users [data-add-user] button[type=submit]');
  await spinnerHidden();
  const notice = await page.locator('[data-notices] .alert-success').last().textContent();
  const m = /: ([A-Za-z0-9]{16})/.exec(notice);
  check(m !== null, 'users: user created, temporary password shown');
  const bobPw = m ? m[1] : '';
  check(await page.locator('#users [data-users] tr[data-id]').count() === 2, 'users: list reloaded with new user');
  const bobRow = page.locator('#users tr[data-id]').filter({ has: page.locator('td:first-child', { hasText: /^\s*bob/ }) });
  await bobRow.locator('[name=role]').selectOption('operator');
  await bobRow.locator('[data-action=save]').click();
  await spinnerHidden();
  check((await bobRow.locator('[name=role]').inputValue()) === 'operator', 'users: role change saved');
  const adminRow = page.locator('#users tr[data-id]').filter({ has: page.locator('td:first-child', { hasText: /^\s*admin/ }) });
  check(await adminRow.locator('[data-action=delete]').isHidden(), 'users: own account cannot be deleted');
  await adminRow.locator('[name=role]').selectOption('viewer');
  await adminRow.locator('[data-action=save]').click();
  await spinnerHidden();
  check((await page.locator('[data-notices] .alert-danger').count()) > 0, 'users: last admin demotion refused');

  await page.goto(BASE + '/logs'); await spinnerHidden();
  check(await page.locator('#logs [data-events] tr[data-rendered]').count() > 0, 'logs: events loaded');
  await page.goto(BASE + '/logs?tab=audit'); await spinnerHidden();
  check(await page.locator('#logs [data-audit] tr[data-rendered]').count() > 0, 'logs: audit loaded');
  const csv = await page.request.get(BASE + '/logs?download=1&tab=audit');
  check(csv.ok() && (await csv.text()).startsWith('id,'), 'logs: CSV download works');

  // ---- Recording appears -> upload
  fs.writeFileSync(HOME + '/lib/usb-sim/TRACK01.WAV', Buffer.alloc(5000));
  await page.goto(BASE + '/usb'); await spinnerHidden();
  await page.click('#usb [data-action=sync]');
  await spinnerHidden();
  let uploaded = false;
  for (let i = 0; i < 40 && !uploaded; i++) { await page.waitForTimeout(500); uploaded = fs.existsSync(HOME + '/dest/TRACK01.WAV'); }
  check(uploaded, 'usb: new recording uploaded to target');
  await page.goto(BASE + '/uploads'); await spinnerHidden();
  check((await page.locator('#uploads').textContent()).includes('TRACK01.WAV'), 'uploads: upload listed');

  // ---- File manager (FileGator in a frame)
  await page.goto(BASE + '/files'); await spinnerHidden();
  await page.waitForFunction(() => document.querySelector('#files [data-frame-loading]').hidden, null, { timeout: 15000 });
  check((await page.getAttribute('#files [data-frame]', 'src')).startsWith('/fm/'), 'files: file manager frame opened in view mode');
  check(await page.locator('#files [data-mode=view].active').count() === 1, 'files: view mode active');
  const fm = page.frameLocator('#files [data-frame]');
  let listed = false;
  try { await fm.getByText('TRACK01.WAV').first().waitFor({ timeout: 15000 }); listed = true; } catch (e) { /* reported below */ }
  check(listed, 'files: recording listed in the file manager');
  await page.screenshot({ path: OUT + '/files_view.png', fullPage: true });
  await page.click('#files [data-mode=edit]');
  await spinnerHidden();
  check(await page.locator('#files [data-state-edit]').isVisible(), 'files: edit mode shows warning');
  await page.waitForTimeout(1200);
  check(/\d+:\d\d/.test(await page.locator('#files [data-countdown]').textContent()), 'files: edit countdown runs');
  await page.screenshot({ path: OUT + '/files_edit.png', fullPage: true });
  await page.click('#files [data-controls] [data-mode=view]');
  await spinnerHidden();
  check(await page.locator('#files [data-state-view]').isVisible(), 'files: back to view mode');
  const fmDirect = await (await browser.newContext()).request.get(BASE + '/fm/?r=/getuser');
  check(fmDirect.status() === 401, 'files: /fm/ refuses requests without login');

  // ---- Notification rule with subject/body template and preview
  await page.goto(BASE + '/notifications'); await spinnerHidden();
  await page.click('#notifications [data-action=add-rule]');
  await page.fill('#rule_name', 'Templated');
  await page.fill('#rule_recipients', 'ops@example.com');
  await page.fill('#rule_subject', 'Rec on ');
  await page.click('#rule_subject');
  await page.locator('#rule_subject').press('End');
  await page.click('#notifications [data-insert-placeholder=host]');
  check((await page.inputValue('#rule_subject')).endsWith('{{host}}'), 'rules: placeholder chip inserted into subject');
  await page.click('#notifications .ql-editor');
  await page.keyboard.type('Hello team, files: ');
  await page.click('#notifications [data-insert-placeholder=count]');
  check((await page.locator('#notifications .ql-editor').textContent()).includes('{{count}}'), 'rules: placeholder chip inserted into editor');
  await page.click('#notifications .ql-bold');
  await page.keyboard.type(' bold');
  await page.click('#notifications [data-action=preview]');
  await spinnerHidden();
  await page.locator('[data-preview-modal].show').waitFor({ timeout: 5000 });
  const subj = await page.locator('[data-preview-subject]').textContent();
  check(subj.startsWith('Rec on ') && !subj.includes('{{'), 'rules: preview renders the subject placeholders (' + subj + ')');
  const srcdoc = await page.getAttribute('[data-preview-frame]', 'srcdoc');
  check(srcdoc.includes('Hello team, files: 3<strong> bold</strong>') && !srcdoc.includes('{{'), 'rules: preview renders HTML body with placeholders');
  await page.screenshot({ path: OUT + '/rule_preview.png' });
  await page.click('[data-preview-modal] .btn-close');
  await page.locator('[data-preview-modal]').waitFor({ state: 'hidden' });
  await page.click('#notifications [data-rule-form] button[type=submit]');
  await spinnerHidden();
  const saved = page.locator('#notifications tr[data-id]').filter({ hasText: 'Templated' });
  check(await saved.count() === 1, 'rules: templated rule saved');
  await saved.locator('[data-action=edit-rule]').click();
  check((await page.locator('#notifications .ql-editor').innerHTML()).includes('<strong> bold</strong>'), 'rules: saved HTML body loaded into editor');
  check((await page.inputValue('#rule_subject')) === 'Rec on {{host}}', 'rules: saved subject loaded');
  await page.screenshot({ path: OUT + '/rule_editor.png', fullPage: true });

  // ---- Updates (simulation mode: nothing is installed)
  await page.goto(BASE + '/updates'); await spinnerHidden();
  check((await page.locator('#updates [data-bind=current]').textContent()).trim() !== '', 'updates: installed version shown');
  await page.click('#updates [data-action=check]'); await spinnerHidden();
  check(await page.locator('[data-notices] .alert').count() > 0, 'updates: release check answers (' +
    (await page.locator('[data-notices] .alert').last().textContent()).trim().slice(0, 60) + ')');
  await page.click('#updates [data-action="os-check"]'); await spinnerHidden();
  await page.waitForFunction(() => document.querySelector('#updates [data-os-count]').textContent.trim() === '1', null, { timeout: 10000 });
  check(true, 'updates: OS check lists upgradable packages');
  await page.click('#updates [data-action=os]'); await spinnerHidden();
  await page.waitForFunction(() => document.querySelector('#updates [data-log]').textContent.includes('Simulation'), null, { timeout: 10000 });
  check(true, 'updates: OS update job writes the log');
  await page.screenshot({ path: OUT + '/updates.png', fullPage: true });

  // ---- Backup: download, scheduled upload, restore
  await page.goto(BASE + '/backup'); await spinnerHidden();
  await page.fill('#download_passphrase', 'backup-passphrase');
  const [download] = await Promise.all([page.waitForEvent('download'), page.click('#backup [data-download-form] button[type=submit]')]);
  const backupFile = OUT + '/' + download.suggestedFilename();
  await download.saveAs(backupFile);
  const backupJson = JSON.parse(fs.readFileSync(backupFile, 'utf8'));
  check(backupJson.format === 'netusbflash-backup' && backupJson.secrets, 'backup: download contains settings and encrypted secrets');
  await page.check('#backup_enabled');
  await page.selectOption('#backup_target', await page.locator('#backup_target option').nth(1).getAttribute('value'));
  await page.fill('#backup_directory', 'settings-backups');
  await page.click('#backup [data-schedule-form] button[type=submit]'); await spinnerHidden();
  check(await page.locator('[data-notices] .alert-success').count() > 0, 'backup: schedule saved');
  check((await page.locator('#backup [data-next-run]').textContent()).trim() !== '', 'backup: next run shown');
  await page.click('#backup [data-action=run]'); await spinnerHidden();
  const uploadedBackups = fs.existsSync(HOME + '/dest/settings-backups') ? fs.readdirSync(HOME + '/dest/settings-backups') : [];
  check(uploadedBackups.some(f => f.endsWith('.json')), 'backup: run now uploads into the backup folder');
  await page.screenshot({ path: OUT + '/backup.png', fullPage: true });
  await page.setInputFiles('#restore_file', backupFile);
  await page.fill('#restore_passphrase', 'wrong-passphrase');
  await page.click('#backup [data-restore-form] button[type=submit]');
  check(await page.locator('#restore_passphrase.is-invalid').waitFor({ timeout: 10000 }).then(() => true, () => false),
    'backup: wrong passphrase refused');
  await page.fill('#restore_passphrase', 'backup-passphrase');
  await page.click('#backup [data-restore-form] button[type=submit]');
  await page.waitForURL(BASE + '/login');
  check(await page.locator('.alert-success').count() > 0, 'backup: restore logs out with a notice');
  await page.fill('#username', 'admin');
  await page.fill('#password', 'correct-horse-battery');
  await page.click('button[type=submit]');
  await page.waitForURL(BASE + '/');
  check(true, 'backup: login works after restore');

  // ---- Profile: language switch reloads the page in German
  await page.goto(BASE + '/profile'); await spinnerHidden();
  await page.selectOption('#locale', 'de');
  await page.click('#profile [data-profile-form] button[type=submit]');
  await page.waitForLoadState('load'); await spinnerHidden();
  check((await page.locator('h1').textContent()).includes('Profil'), 'profile: language switch to German');
  await page.selectOption('#locale', 'en');
  await page.click('#profile [data-profile-form] button[type=submit]');
  await page.waitForLoadState('load'); await spinnerHidden();

  // ---- New user must change password; viewer restrictions
  await page.click('.navbar a.dropdown-toggle:has(.bi-person-circle)'); await page.click('text=Log out');
  await page.waitForURL(BASE + '/login');
  await page.fill('#username', 'bob'); await page.fill('#password', bobPw); await page.click('button[type=submit]');
  await page.waitForURL(BASE + '/profile'); await spinnerHidden();
  check(await page.locator('#profile [data-forced]').isVisible(), 'profile: forced password change shown');
  await page.fill('#current', bobPw); await page.fill('#new', 'bobs-new-password'); await page.fill('#new_confirm', 'bobs-new-password');
  await page.click('#profile [data-password-form] button[type=submit]');
  await page.waitForURL(BASE + '/'); await spinnerHidden();
  check(true, 'profile: password changed, redirected to dashboard');
  const r = await page.goto(BASE + '/users');
  check(r.status() === 403, 'users: forbidden for operator');

  // Mobile layout of one page
  await page.setViewportSize({ width: 390, height: 800 });
  await page.goto(BASE + '/'); await spinnerHidden();
  await page.screenshot({ path: OUT + '/mobile.png', fullPage: true });

  await browser.close();
  console.log(problems.length ? '\nPROBLEMS:\n' + problems.join('\n') : '\nALL OK');
  process.exit(problems.length ? 1 : 0);
})().catch(e => { console.error(e); console.log(problems.join('\n')); process.exit(2); });
