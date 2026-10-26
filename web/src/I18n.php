<?php

declare(strict_types=1);

/**
 * Minimal translation layer. Language files live in web/lang/<locale>.php and
 * return a flat array of key => text. English is the fallback.
 */
final class I18n
{
    public const LOCALES = ['en' => 'English', 'de' => 'Deutsch'];

    private static string $locale = 'en';
    /** @var array<string, array<string, string>> */
    private static array $strings = [];

    public static function setLocale(string $locale): void
    {
        self::$locale = array_key_exists($locale, self::LOCALES) ? $locale : 'en';
    }

    public static function locale(): string
    {
        return self::$locale;
    }

    /** @return array<string, string> */
    public static function load(string $locale): array
    {
        if (!isset(self::$strings[$locale])) {
            $file = APP_ROOT . '/lang/' . $locale . '.php';
            self::$strings[$locale] = is_file($file) ? require $file : [];
        }
        return self::$strings[$locale];
    }

    public static function has(string $key): bool
    {
        return isset(self::load(self::$locale)[$key]) || isset(self::load('en')[$key]);
    }

    public static function t(string $key, array $params = []): string
    {
        $text = self::load(self::$locale)[$key] ?? self::load('en')[$key] ?? $key;
        foreach ($params as $name => $value) {
            $text = str_replace('{' . $name . '}', (string) $value, $text);
        }
        return $text;
    }

    public static function detect(?array $user): string
    {
        if ($user !== null && isset($user['locale'])) {
            return (string) $user['locale'];
        }
        if (isset($_SESSION['locale'])) {
            return (string) $_SESSION['locale'];
        }
        $header = strtolower((string) ($_SERVER['HTTP_ACCEPT_LANGUAGE'] ?? ''));
        return str_starts_with($header, 'de') ? 'de' : 'en';
    }
}
