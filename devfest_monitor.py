"""DevFest Tarija 2026 - Network and application monitoring."""
import csv
import platform
import re
import subprocess
import time
from datetime import datetime
from turtle import stamp
from turtle import stamp
from urllib.request import urlopen
from urllib.error import HTTPError

PING_HOST = '172.66.147.243'
HTTP_URL = 'https://example.com/'
INTERVAL = 5


def check_ping(host):
    windows = platform.system() == 'Windows'
    if windows:
        command = ['ping', '-n', '3', '-w', '2000', host]
    else:
        command = ['ping', '-c', '3', host]
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                errors='replace', timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    # Match individual reply times, including localized Windows output.
    matches = re.findall(r'(?:=|<)\s*(\d+(?:[.,]\d+)?)\s*ms', result.stdout, re.I)
    # Windows summary also contains min/max/average; only inspect reply lines.
    if windows:
        matches = [m for line in result.stdout.splitlines() if 'TTL=' in line.upper()
                   for m in re.findall(r'(?:=|<)\s*(\d+(?:[.,]\d+)?)\s*ms', line, re.I)]
    else:
        matches = [m for line in result.stdout.splitlines() if 'icmp_seq=' in line
                   for m in re.findall(r'(?:=|<)\s*(\d+(?:[.,]\d+)?)\s*ms', line, re.I)]
    times = [float(m.replace(',', '.')) for m in matches]
    if not times and result.returncode == 0:
        return None, None  # Unrecognized output, not confirmed packet loss.
    loss = (3 - min(len(times), 3)) / 3 * 100
    return round(sum(times) / len(times), 2) if times else None, round(loss, 1)


def check_http(url):
    start = time.perf_counter()
    try:
        with urlopen(url, timeout=5) as response:
            status = response.status
    except HTTPError as error:
        status = error.code
        error.close()
    except (OSError, ValueError):
        return 'ERROR', None
    return status, round((time.perf_counter() - start) * 1000, 2)


def main():
    print('DevFest Network Monitor | Ctrl+C to stop')
    with open('monitor_log.csv', 'a+', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if file.tell() == 0:
            writer.writerow(['timestamp', 'ping_host', 'latency_ms', 'loss_percent',
                             'http_url', 'http_status', 'http_ms'])
        try:
            while True:
                latency, loss = check_ping(PING_HOST)
                status, http_ms = check_http(HTTP_URL)
                stamp = datetime.now().astimezone().isoformat(timespec='seconds')
                writer.writerow([stamp, PING_HOST, latency, loss, HTTP_URL, status, http_ms])
                file.flush()
                if loss is None:
                    ping_display = 'UNKNOWN'
                elif loss == 100:
                    ping_display = 'DOWN (100% loss)'
                elif loss > 0:
                    ping_display = f'DEGRADED ({latency} ms, {loss}% loss)'
                else:
                    ping_display = f'UP ({latency} ms, 0% loss)'

                if status == 'ERROR':
                    http_display = 'DOWN'
                elif 200 <= status < 300:
                    http_display = f'UP ({status}, {http_ms} ms)'
                else:
                    http_display = f'HTTP ERROR ({status}, {http_ms} ms)'

                print(f'[{stamp}] PING: {ping_display} | '
                      f'HTTP: {http_display}')
                time.sleep(INTERVAL)
        except KeyboardInterrupt:
            print('\nMonitoring stopped.')


if __name__ == '__main__':
    main()
