<?php

declare(strict_types=1);

/**
 * Response from the local NetUSBFlash API.
 */
final class ApiResponse
{
    public function __construct(public readonly int $status, public readonly array $data)
    {
    }

    public function ok(): bool
    {
        return $this->status >= 200 && $this->status < 300;
    }

    public function error(): ?string
    {
        return $this->ok() ? null : (string) ($this->data['error'] ?? 'unknown');
    }

    /** @return array<string, string> field name => error code */
    public function fields(): array
    {
        $fields = $this->data['fields'] ?? [];
        return is_array($fields) ? $fields : [];
    }
}

/**
 * Talks to the service over its Unix socket. PHP never touches the system
 * directly; every action goes through this client.
 */
final class ApiClient
{
    public function __construct(private readonly string $socket)
    {
    }

    public function call(string $method, string $path, ?array $body = null, array $headers = []): ApiResponse
    {
        $ch = curl_init('http://localhost/api/v1' . $path);
        $httpHeaders = ['Accept: application/json'];
        foreach ($headers as $name => $value) {
            if ($value !== null && $value !== '') {
                $httpHeaders[] = $name . ': ' . str_replace(["\r", "\n"], '', (string) $value);
            }
        }
        $options = [
            CURLOPT_UNIX_SOCKET_PATH => $this->socket,
            CURLOPT_CUSTOMREQUEST => $method,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_TIMEOUT => 300,
        ];
        if ($body !== null) {
            $httpHeaders[] = 'Content-Type: application/json';
            // An empty PHP array would encode as [], but the API expects an object.
            $options[CURLOPT_POSTFIELDS] = $body === []
                ? '{}'
                : json_encode($body, JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
        }
        $options[CURLOPT_HTTPHEADER] = $httpHeaders;
        curl_setopt_array($ch, $options);
        $raw = curl_exec($ch);
        if ($raw === false) {
            $message = curl_error($ch);
            return new ApiResponse(503, ['error' => 'service_unavailable', 'message' => $message]);
        }
        $status = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $data = json_decode((string) $raw, true);
        if (!is_array($data)) {
            return new ApiResponse(502, ['error' => 'bad_response', 'message' => 'Invalid response from service']);
        }
        return new ApiResponse($status, $data);
    }
}
