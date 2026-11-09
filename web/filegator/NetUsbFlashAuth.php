<?php

declare(strict_types=1);

namespace NetUsbFlash\FileGator;

use Filegator\Services\Auth\AuthInterface;
use Filegator\Services\Auth\User;
use Filegator\Services\Auth\UsersCollection;
use Filegator\Services\Service;

/**
 * FileGator auth adapter: the user comes from the NetUSBFlash login.
 *
 * nginx checks every file manager request with an auth subrequest against
 * the NetUSBFlash session (web/auth/filemanager.php) and passes the result as
 * NUF_USER and NUF_ROLE. There is no separate FileGator login.
 *
 * Write access needs the role "manager" or "admin" and a writable mount,
 * which only exists while the stick is opened for editing.
 */
final class NetUsbFlashAuth implements Service, AuthInterface
{
    private const READ = ['read', 'download', 'batchdownload'];
    private const WRITE = ['write', 'upload', 'zip'];
    private const WRITER_ROLES = ['manager', 'admin'];

    private string $root = '';

    public function init(array $config = [])
    {
        $this->root = (string) ($config['root'] ?? '');
    }

    public function user(): ?User
    {
        $username = (string) ($_SERVER['NUF_USER'] ?? '');
        $role = (string) ($_SERVER['NUF_ROLE'] ?? '');
        if ($username === '' || $role === '') {
            return $this->getGuest();
        }
        $permissions = self::READ;
        if (in_array($role, self::WRITER_ROLES, true) && $this->root !== '' && is_writable($this->root)) {
            $permissions = array_merge($permissions, self::WRITE);
        }
        $user = new User();
        $user->setUsername($username);
        $user->setName($username);
        $user->setRole('user');
        $user->setHomedir('/');
        $user->setPermissions($permissions);
        return $user;
    }

    public function authenticate($username, $password): bool
    {
        return false; // login happens in NetUSBFlash
    }

    public function forget()
    {
        return null;
    }

    public function find($username): ?User
    {
        return null;
    }

    public function store(User $user)
    {
        return null;
    }

    public function update($username, User $user, $password = ''): User
    {
        return $this->user() ?? $this->getGuest();
    }

    public function add(User $user, $password): User
    {
        return $user;
    }

    public function delete(User $user)
    {
        return true;
    }

    public function getGuest(): User
    {
        $guest = new User();
        $guest->setUsername('guest');
        $guest->setName('Guest');
        $guest->setRole('guest');
        $guest->setHomedir('/');
        $guest->setPermissions([]);
        return $guest;
    }

    public function allUsers(): UsersCollection
    {
        return new UsersCollection();
    }
}
