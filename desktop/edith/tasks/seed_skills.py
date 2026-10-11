"""Seed lifelong skills into EDITH SQLite memory store."""

from edith.memory.local_store import MEMORY

SKILLS = [
    (
        "get system ip address",
        "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.*' } | Select-Object -ExpandProperty IPAddress",
        "Query host IPv4 network configuration"
    ),
    (
        "flush dns cache",
        "Clear-DnsClientCache; 'DNS cache successfully flushed.'",
        "Clear Windows DNS resolver cache"
    ),
    (
        "empty recycle bin",
        "Clear-RecycleBin -Force -ErrorAction SilentlyContinue; 'Recycle Bin emptied.'",
        "Purge deleted files from Windows Recycle Bin"
    ),
    (
        "get battery health",
        "Get-CimInstance -ClassName Win32_Battery | Select-Object EstimatedChargeRemaining, BatteryStatus, EstimatedRunTime",
        "Check hardware battery status and remaining charge"
    ),
    (
        "list top memory processes",
        "Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 ProcessName, @{Name='RAM_MB';Expression={[math]::Round($_.WorkingSet64/1MB,1)}}",
        "Monitor top RAM consuming processes"
    ),
    (
        "list top cpu processes",
        "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 ProcessName, CPU",
        "Inspect top CPU consuming tasks"
    ),
    (
        "check disk space",
        "Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{Name='FreeGB';Expression={[math]::Round($_.Free/1GB,2)}}, @{Name='UsedGB';Expression={[math]::Round($_.Used/1GB,2)}}",
        "Report storage volume capacity and free space"
    ),
    (
        "restart audio service",
        "Restart-Service -Name Audiosrv -Force; 'Windows Audio service restarted.'",
        "Recover audio subsystem by restarting Audiosrv"
    ),
    (
        "list network adapters",
        "Get-NetAdapter | Select-Object Name, Status, LinkSpeed",
        "Check ethernet and Wi-Fi adapter states"
    ),
    (
        "check internet ping",
        "Test-Connection -ComputerName 1.1.1.1 -Count 2 -Quiet",
        "Verify internet packet routing connectivity"
    ),
    (
        "show system uptime",
        "((Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime).ToString()",
        "Measure elapsed Windows system runtime"
    ),
    (
        "test audio devices",
        "Get-CimInstance Win32_SoundDevice | Select-Object Name, Status",
        "Enumerate audio controllers and hardware health"
    ),
    (
        "list active services",
        "Get-Service | Where-Object Status -eq 'Running' | Select-Object -First 15 Name, DisplayName",
        "Inspect running Windows background services"
    ),
    (
        "show clipboard content",
        "Get-Clipboard",
        "Read text contents of Windows clipboard"
    ),
    (
        "clear clipboard",
        "Set-Clipboard -Value ''",
        "Wipe Windows clipboard sensitive data"
    ),
    (
        "get cpu load",
        "Get-CimInstance -ClassName Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, LoadPercentage",
        "Measure CPU load percentage and core counts"
    ),
    (
        "check wifi connection",
        "netsh wlan show interfaces",
        "Inspect active wireless SSID and signal quality"
    ),
    (
        "list available wifi networks",
        "netsh wlan show networks",
        "Scan wireless beacons and available access points"
    ),
    (
        "clean windows temp files",
        "Remove-Item -Path \"$env:TEMP\\*\" -Recurse -Force -ErrorAction SilentlyContinue; 'Temporary files cleaned.'",
        "Free disk space by wiping user temp directories"
    ),
    (
        "show power plan",
        "powercfg /getactivescheme",
        "Inspect Windows active power management profile"
    ),
]

def seed() -> int:
    count = 0
    for goal, cmd, desc in SKILLS:
        MEMORY.remember_skill(goal, cmd, desc)
        count += 1
    return count

if __name__ == "__main__":
    n = seed()
    print(f"Seeded {n} skills into lifelong memory.")
