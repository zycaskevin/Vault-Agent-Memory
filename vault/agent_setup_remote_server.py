"""Self-hosted Vault Remote Server deployment template helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vault.agent_setup_templates import shell_join
from vault.gateway import gateway_openapi


def write_remote_server_deploy_templates(
    *,
    output_dir: str | Path,
    project_dir: str | Path,
    vault_executable: str = "vault",
) -> dict[str, str]:
    """Write inert self-hosted Vault Remote Server deployment templates."""
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    project_path = Path(project_dir).expanduser().resolve()
    command = [
        vault_executable,
        "remote-server",
        "serve",
        "--project-dir",
        str(project_path),
        "--host",
        "0.0.0.0",
    ]
    health_command = [
        vault_executable,
        "remote-server",
        "health",
        "--project-dir",
        str(project_path),
        "--json",
    ]
    openapi_command = [
        vault_executable,
        "remote-server",
        "openapi",
        "--project-dir",
        str(project_path),
        "--json",
    ]

    launchagent_path = out / "vault-remote-server.launchagent.plist"
    launchagent_path.write_text(_render_remote_server_launchagent(command), encoding="utf-8")

    env_path = out / "vault-remote-server.env.example"
    env_path.write_text(
        "\n".join(
            [
                "# Copy to a private env file, chmod 600, then replace the token.",
                "VAULT_GATEWAY_TOKEN=replace-with-stable-secret",
                "# Keep the server on a private network unless a reverse proxy adds TLS/auth/rate limits.",
                "VAULT_REMOTE_SERVER_BIND=127.0.0.1",
                "VAULT_REMOTE_SERVER_PORT=8789",
                "# Optional built-in HTTPS. For public endpoints, prefer a reverse proxy with managed certificates.",
                "VAULT_GATEWAY_TLS_CERT=",
                "VAULT_GATEWAY_TLS_KEY=",
                "VAULT_GATEWAY_RATE_LIMIT_PER_MINUTE=60",
                "VAULT_GATEWAY_TOKEN_RATE_LIMIT_PER_MINUTE=60",
                "VAULT_GATEWAY_AUTH_FAILURE_LIMIT=10",
                "VAULT_GATEWAY_AUTH_LOCKOUT_SECONDS=300",
                "# Optional comma-separated IP/CIDR lists, for example: 100.64.0.0/10,192.168.1.0/24",
                "VAULT_GATEWAY_IP_ALLOWLIST=",
                "VAULT_GATEWAY_IP_DENYLIST=",
                "",
            ]
        ),
        encoding="utf-8",
    )

    systemd_path = out / "vault-remote-server.service"
    systemd_path.write_text(
        "\n".join(
            [
                "[Unit]",
                "Description=Vault Agent Memory Remote Server",
                "After=network-online.target",
                "Wants=network-online.target",
                "",
                "[Service]",
                "Type=simple",
                f"EnvironmentFile={env_path}",
                f"ExecStart={shell_join(command)}",
                "Restart=on-failure",
                "RestartSec=5",
                "NoNewPrivileges=true",
                "PrivateTmp=true",
                "ProtectSystem=full",
                "",
                "[Install]",
                "WantedBy=multi-user.target",
                "",
            ]
        ),
        encoding="utf-8",
    )

    compose_path = out / "vault-remote-server.compose.yaml"
    compose_path.write_text(
        "\n".join(
            [
                "services:",
                "  vault-remote-server:",
                "    image: python:3.12-slim",
                "    working_dir: /vault-project",
                "    command:",
                "      - sh",
                "      - -lc",
                "      - >",
                "        python -m pip install --no-cache-dir 'vault-for-llm[mcp]' &&",
                f"        {shell_join(command)}",
                "    ports:",
                "      - \"8789:8789\"",
                "    environment:",
                "      VAULT_GATEWAY_TOKEN: ${VAULT_GATEWAY_TOKEN:?set a stable token}",
                "    env_file:",
                f"      - {env_path.name}",
                "    volumes:",
                f"      - {str(project_path)}:/vault-project",
                "",
            ]
        ),
        encoding="utf-8",
    )

    readme_path = out / "README-remote-server.md"
    readme_path.write_text(
        "\n".join(
            [
                "# Vault Remote Server Deployment",
                "",
                "Use this when the user wants one self-hosted central memory host instead of Supabase.",
                "",
                "Remote Server reuses the Gateway contract:",
                "",
                "- search active memory with read policy;",
                "- read bounded source ranges;",
                "- submit candidate memories;",
                "- never write active memory directly;",
                "- no offline active multi-master sync yet.",
                "",
                "Before serving, set a stable token:",
                "",
                "```bash",
                "export VAULT_GATEWAY_TOKEN=\"replace-with-stable-secret\"",
                "```",
                "",
                "Readiness checks:",
                "",
                "```bash",
                shell_join(health_command),
                shell_join(openapi_command),
                "```",
                "",
                "Run directly:",
                "",
                "```bash",
                shell_join(command),
                "```",
                "",
                "Generated deployment templates:",
                "",
                f"- environment example: `{env_path.name}`",
                f"- macOS LaunchAgent example: `{launchagent_path.name}`",
                f"- systemd service example: `{systemd_path.name}`",
                f"- Docker Compose example: `{compose_path.name}`",
                "- remote client examples: `README-remote-clients.md`",
                "- long-term hardening checklist: `REMOTE_SERVER_HARDENING.md`",
                "- operator schedule: `README-remote-server-operator-schedule.md`",
                "",
                "Network guidance:",
                "",
                "- Prefer a private network such as Tailscale, WireGuard, or LAN-only routing.",
                "- Do not expose this server publicly without TLS, firewalling, and a rotated token.",
                "- Keep remote writes candidate-first; promote from the trusted Vault review flow.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    hardening_path = out / "REMOTE_SERVER_HARDENING.md"
    hardening_path.write_text(_render_remote_server_hardening(), encoding="utf-8")
    operator_schedule = _write_remote_operator_schedule(
        out,
        project_path=project_path,
        vault_executable=vault_executable,
    )
    remote_client_templates = _write_remote_client_templates(out)
    return {
        "readme": str(readme_path),
        "env_example": str(env_path),
        "hardening": str(hardening_path),
        "health_command": shell_join(health_command),
        "openapi_command": shell_join(openapi_command),
        "serve_command": shell_join(command),
        "launchagent": str(launchagent_path),
        "systemd": str(systemd_path),
        "docker_compose": str(compose_path),
        "operator_schedule": operator_schedule,
        "remote_clients": remote_client_templates,
    }


def _write_remote_operator_schedule(
    out: Path,
    *,
    project_path: Path,
    vault_executable: str,
) -> dict[str, str]:
    """Write operator-side self-host maintenance schedule templates."""
    log_dir = project_path / "reports" / "remote-server-operator"
    cron_path = out / "vault-remote-server-operator.cron"
    readme_path = out / "README-remote-server-operator-schedule.md"

    jobs = _remote_operator_jobs(project_path=project_path, vault_executable=vault_executable)
    pull_dry_run_command = jobs["candidate_pull_dry_run"]["command"]
    launchagents = _write_remote_operator_launchagents(out, jobs, log_dir=log_dir)
    systemd = _write_remote_operator_systemd(out, jobs, log_dir=log_dir)

    cron_path.write_text(_render_remote_operator_cron(jobs, log_dir=log_dir), encoding="utf-8")
    readme_path.write_text(
        _render_remote_operator_schedule_readme(
            cron_path=cron_path,
            log_dir=log_dir,
            pull_dry_run_command=pull_dry_run_command,
            launchagents=launchagents,
            systemd=systemd,
        ),
        encoding="utf-8",
    )
    return {
        "cron": str(cron_path),
        "readme": str(readme_path),
        "launchagents": launchagents,
        "systemd": systemd,
        "pull_candidates_command": shell_join(jobs["candidate_pull"]["command"]),
        "pull_candidates_dry_run_command": shell_join(pull_dry_run_command),
        "daily_report_command": shell_join(jobs["daily_report"]["command"]),
        "backup_command": shell_join(jobs["backup"]["command"]),
        "audit_command": shell_join(jobs["audit"]["command"]),
        "security_doctor_command": shell_join(jobs["security_doctor"]["command"]),
    }


def _remote_operator_jobs(*, project_path: Path, vault_executable: str) -> dict[str, dict[str, Any]]:
    pull_command = [
        vault_executable,
        "memory-sync",
        "run-once",
        "--project-dir",
        str(project_path),
        "--central-backend",
        "self-host",
        "--pull-candidates",
        "--apply",
        "--json",
    ]
    pull_dry_run_command = [
        vault_executable,
        "memory-sync",
        "run-once",
        "--project-dir",
        str(project_path),
        "--central-backend",
        "self-host",
        "--pull-candidates",
        "--dry-run",
        "--json",
    ]
    daily_report_command = [
        vault_executable,
        "daily-loop",
        "report",
        "--project-dir",
        str(project_path),
        "--refresh",
        "--write-report",
        "--json",
    ]
    backup_command = [
        vault_executable,
        "db",
        "backup",
        "--db-path",
        str(project_path / "vault.db"),
        "--verify",
        "--json",
    ]
    audit_command = [
        vault_executable,
        "remote-server",
        "audit",
        "--project-dir",
        str(project_path),
        "--json",
    ]
    security_command = [
        vault_executable,
        "--project-dir",
        str(project_path),
        "security",
        "doctor",
        "--json",
    ]
    return {
        "candidate_pull": {
            "label": "Pull central candidates",
            "command": pull_command,
            "cron": "*/15 * * * *",
            "launchd": {"interval": 15 * 60},
            "systemd_on_calendar": "*-*-* *:0/15:00",
            "log_name": "candidate-pull.log",
            "unit_suffix": "candidate-pull",
        },
        "daily_report": {
            "label": "Daily report refresh",
            "command": daily_report_command,
            "cron": "0 9 * * *",
            "launchd": {"hour": 9, "minute": 0},
            "systemd_on_calendar": "*-*-* 09:00:00",
            "log_name": "daily-loop-report.log",
            "unit_suffix": "daily-report",
        },
        "backup": {
            "label": "Verified backup",
            "command": backup_command,
            "cron": "10 3 * * *",
            "launchd": {"hour": 3, "minute": 10},
            "systemd_on_calendar": "*-*-* 03:10:00",
            "log_name": "backup.log",
            "unit_suffix": "backup",
        },
        "audit": {
            "label": "Gateway audit summary",
            "command": audit_command,
            "cron": "30 8 * * 0",
            "launchd": {"weekday": 0, "hour": 8, "minute": 30},
            "systemd_on_calendar": "Sun *-*-* 08:30:00",
            "log_name": "audit.log",
            "unit_suffix": "audit",
        },
        "security_doctor": {
            "label": "Security doctor",
            "command": security_command,
            "cron": "45 8 * * 0",
            "launchd": {"weekday": 0, "hour": 8, "minute": 45},
            "systemd_on_calendar": "Sun *-*-* 08:45:00",
            "log_name": "security-doctor.log",
            "unit_suffix": "security-doctor",
        },
        "candidate_pull_dry_run": {
            "label": "Pull central candidates dry-run",
            "command": pull_dry_run_command,
            "log_name": "candidate-pull-dry-run.log",
            "unit_suffix": "candidate-pull-dry-run",
        },
    }


def _render_remote_operator_cron(jobs: dict[str, dict[str, Any]], *, log_dir: Path) -> str:
    return "\n".join(
        [
            "# Vault Remote Server operator schedule.",
            "# Install by copying selected lines into `crontab -e` on the trusted central host.",
            "# Candidate pull uses --apply, but writes local review candidates only; it never promotes active memory.",
            "# Run the dry-run command in README-remote-server-operator-schedule.md before enabling the candidate-pull line.",
            "",
            _cron_line(
                jobs["candidate_pull"]["cron"],
                jobs["candidate_pull"]["command"],
                log_dir=log_dir,
                log_name=jobs["candidate_pull"]["log_name"],
            ),
            _cron_line(
                jobs["daily_report"]["cron"],
                jobs["daily_report"]["command"],
                log_dir=log_dir,
                log_name=jobs["daily_report"]["log_name"],
            ),
            _cron_line(
                jobs["backup"]["cron"],
                jobs["backup"]["command"],
                log_dir=log_dir,
                log_name=jobs["backup"]["log_name"],
            ),
            _cron_line(
                jobs["audit"]["cron"],
                jobs["audit"]["command"],
                log_dir=log_dir,
                log_name=jobs["audit"]["log_name"],
            ),
            _cron_line(
                jobs["security_doctor"]["cron"],
                jobs["security_doctor"]["command"],
                log_dir=log_dir,
                log_name=jobs["security_doctor"]["log_name"],
            ),
            "",
        ]
    )


def _render_remote_operator_schedule_readme(
    *,
    cron_path: Path,
    log_dir: Path,
    pull_dry_run_command: list[str],
    launchagents: dict[str, str],
    systemd: dict[str, dict[str, str]],
) -> str:
    launchagent_names = ", ".join(f"`{Path(path).name}`" for path in launchagents.values())
    systemd_names = ", ".join(
        f"`{Path(paths['timer']).name}`" for paths in systemd.values() if isinstance(paths, dict)
    )
    return "\n".join(
        [
            "# Vault Remote Server Operator Schedule",
            "",
            "Use this on the trusted Self-host Central Memory Host, not on remote agent machines.",
            "",
            "Generated files:",
            "",
            f"- cron template: `{cron_path.name}`",
            f"- macOS LaunchAgent templates: {launchagent_names}",
            f"- systemd timer templates: {systemd_names}",
            f"- log directory: `{log_dir}`",
            "",
            "Safety boundary:",
            "",
            "- candidate pull imports central inbox rows into local review only;",
            "- candidate pull does not promote active memory;",
            "- daily-loop report refresh is report-first and does not capture new candidates;",
            "- backup uses the SQLite online backup API and verifies the result;",
            "- audit and security doctor jobs are read-only.",
            "",
            "Before enabling a schedule that uses `--apply`, run:",
            "",
            "```bash",
            shell_join(pull_dry_run_command),
            "```",
            "",
            "Then inspect the result for expected counts and no safety warnings.",
            "",
            "Operator jobs:",
            "",
            "| Job | Default cadence | Command class |",
            "|---|---:|---|",
            "| Pull central candidates | every 15 minutes | `vault memory-sync run-once --central-backend self-host --pull-candidates --apply` |",
            "| Daily report refresh | daily 09:00 | `vault daily-loop report --refresh --write-report` |",
            "| Verified backup | daily 03:10 | `vault db backup --verify` |",
            "| Gateway audit summary | weekly Sunday 08:30 | `vault remote-server audit --json` |",
            "| Security doctor | weekly Sunday 08:45 | `vault security doctor --json` |",
            "",
            "Install only one scheduler family. Do not install cron, LaunchAgent, and systemd timers together on the same host.",
            "",
        ]
    )


def _write_remote_operator_launchagents(
    out: Path,
    jobs: dict[str, dict[str, Any]],
    *,
    log_dir: Path,
) -> dict[str, str]:
    paths: dict[str, str] = {}
    for key in ["candidate_pull", "daily_report", "backup", "audit", "security_doctor"]:
        job = jobs[key]
        suffix = str(job["unit_suffix"])
        path = out / f"vault-remote-server-operator-{suffix}.launchagent.plist"
        path.write_text(_render_remote_operator_launchagent(job, log_dir=log_dir), encoding="utf-8")
        paths[key] = str(path)
    return paths


def _render_remote_operator_launchagent(job: dict[str, Any], *, log_dir: Path) -> str:
    suffix = str(job["unit_suffix"])
    label = f"com.zycaskevin.vault-for-llm.remote-server.operator.{suffix}"
    command = _operator_shell_command(job["command"], log_dir=log_dir, log_name=job["log_name"])
    schedule = job["launchd"]
    if "interval" in schedule:
        trigger = "\n".join(
            [
                "  <key>StartInterval</key>",
                f"  <integer>{int(schedule['interval'])}</integer>",
            ]
        )
    else:
        parts = ["  <key>StartCalendarInterval</key>", "  <dict>"]
        if "weekday" in schedule:
            parts.extend(["    <key>Weekday</key>", f"    <integer>{int(schedule['weekday'])}</integer>"])
        parts.extend(
            [
                "    <key>Hour</key>",
                f"    <integer>{int(schedule['hour'])}</integer>",
                "    <key>Minute</key>",
                f"    <integer>{int(schedule['minute'])}</integer>",
                "  </dict>",
            ]
        )
        trigger = "\n".join(parts)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{_xml_escape(label)}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string>
    <string>-lc</string>
    <string>{_xml_escape(command)}</string>
  </array>
{trigger}
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
"""


def _write_remote_operator_systemd(
    out: Path,
    jobs: dict[str, dict[str, Any]],
    *,
    log_dir: Path,
) -> dict[str, dict[str, str]]:
    paths: dict[str, dict[str, str]] = {}
    for key in ["candidate_pull", "daily_report", "backup", "audit", "security_doctor"]:
        job = jobs[key]
        suffix = str(job["unit_suffix"])
        service_path = out / f"vault-remote-server-operator-{suffix}.service"
        timer_path = out / f"vault-remote-server-operator-{suffix}.timer"
        service_name = service_path.name
        service_path.write_text(
            _render_remote_operator_systemd_service(job, log_dir=log_dir),
            encoding="utf-8",
        )
        timer_path.write_text(
            _render_remote_operator_systemd_timer(job, service_name=service_name),
            encoding="utf-8",
        )
        paths[key] = {"service": str(service_path), "timer": str(timer_path)}
    return paths


def _render_remote_operator_systemd_service(job: dict[str, Any], *, log_dir: Path) -> str:
    command = _operator_shell_command(job["command"], log_dir=log_dir, log_name=job["log_name"])
    return "\n".join(
        [
            "[Unit]",
            f"Description=Vault Remote Server operator: {job['label']}",
            "",
            "[Service]",
            "Type=oneshot",
            f"ExecStart=/bin/sh -lc {shell_join([command])}",
            "NoNewPrivileges=true",
            "PrivateTmp=true",
            "ProtectSystem=full",
            "",
        ]
    )


def _render_remote_operator_systemd_timer(job: dict[str, Any], *, service_name: str) -> str:
    return "\n".join(
        [
            "[Unit]",
            f"Description=Schedule Vault Remote Server operator: {job['label']}",
            "",
            "[Timer]",
            f"OnCalendar={job['systemd_on_calendar']}",
            "Persistent=true",
            f"Unit={service_name}",
            "",
            "[Install]",
            "WantedBy=timers.target",
            "",
        ]
    )


def _cron_line(
    schedule: str,
    command: list[str],
    *,
    log_dir: Path,
    log_name: str,
) -> str:
    inner = _operator_shell_command(command, log_dir=log_dir, log_name=log_name)
    return f"{schedule} sh -lc {shell_join([inner])}"


def _operator_shell_command(command: list[str], *, log_dir: Path, log_name: str) -> str:
    log_path = log_dir / log_name
    return (
        f"mkdir -p {shell_join([str(log_dir)])} && "
        f"{shell_join(command)} >> {shell_join([str(log_path)])} 2>&1"
    )


def _render_remote_server_hardening() -> str:
    return "\n".join(
        [
            "# Vault Remote Server Hardening",
            "",
            "This server is a shared memory doorway. Treat it like a small private database endpoint, not a public website.",
            "",
            "## Safe Defaults",
            "",
            "- Keep `VAULT_GATEWAY_TOKEN` outside prompts, repository files, and workflow JSON.",
            "- Prefer `127.0.0.1`, LAN-only, Tailscale, WireGuard, or another private network.",
            "- Keep Gateway's built-in rate limit and auth lockout enabled; tune them in `vault-remote-server.env.example`.",
            "- Set `VAULT_GATEWAY_IP_ALLOWLIST` for LAN, VPN, or Tailscale ranges before opening cross-host access.",
            "- For direct HTTPS, set both `VAULT_GATEWAY_TLS_CERT` and `VAULT_GATEWAY_TLS_KEY`.",
            "- For internet-facing endpoints, prefer Caddy, Nginx, or another reverse proxy with managed TLS certificates.",
            "- Rotate the Gateway token when an Agent machine is lost or a workflow is shared.",
            "- Back up `vault.db` with `vault db backup` before upgrades and before changing sync topology.",
            "- Review `reports/gateway/audit.jsonl` for `auth_failed`, `request_blocked`, and unusual client IPs.",
            "- Prefer `vault remote-server audit --json` or the `vault_gateway_audit` MCP tool for compact audit summaries.",
            "",
            "## Memory Safety Boundary",
            "",
            "- Remote search returns compact metadata and snippets, not raw full memory dumps.",
            "- Remote reads should use bounded `/read-range` evidence after search.",
            "- Remote writes are candidate-first: they go to `/submit-candidate` and do not create active knowledge directly.",
            "- Promote candidates only from a trusted local review flow or a narrowly scoped automation policy.",
            "- This is centralized sharing, not offline active multi-master merge.",
            "",
            "## Deployment Checklist",
            "",
            "- [ ] Copy `vault-remote-server.env.example` to a private path and run `chmod 600`.",
            "- [ ] Replace `replace-with-stable-secret` with a long random token.",
            "- [ ] Run `vault remote-server health --json` before opening client access.",
            "- [ ] Use HTTPS for cross-host traffic: either built-in cert/key flags or a reverse proxy.",
            "- [ ] Run the generated `validate-vault-remote-client.py` from at least one client machine.",
            "- [ ] Confirm logs do not print tokens.",
            "- [ ] Confirm backups and restore verification exist.",
            "- [ ] Review `reports/gateway/audit.jsonl` during the first rollout week.",
            "- [ ] Add `vault remote-server audit --json` to the weekly operator check.",
            "- [ ] Review `README-remote-server-operator-schedule.md` before installing recurring jobs.",
            "",
            "## When Not To Use It",
            "",
            "- If all Agents run on one machine, local `vault-mcp` or `vault gateway` may be simpler.",
            "- If devices must write offline for days and later merge active memory, wait for the future revision/conflict resolver flow.",
            "- If hosted platforms cannot keep tokens private, expose only read-only remote reader paths.",
            "",
            "## Built-in HTTPS",
            "",
            "For private LAN, lab, or beta deployments where a reverse proxy is not available, Gateway can serve HTTPS directly:",
            "",
            "```bash",
            "vault remote-server serve --tls-cert /path/fullchain.pem --tls-key /path/privkey.pem",
            "```",
            "",
            "You can also set the same paths in the env file:",
            "",
            "```bash",
            "VAULT_GATEWAY_TLS_CERT=/path/fullchain.pem",
            "VAULT_GATEWAY_TLS_KEY=/path/privkey.pem",
            "```",
            "",
            "Use certificates trusted by the client machines. Self-signed certificates are acceptable for a private beta only when every client explicitly trusts them.",
            "",
            "## Reverse Proxy TLS",
            "",
            "A reverse proxy is the recommended production shape because it can manage certificates, renewals, access logs, and extra network controls.",
            "",
            "Caddy example:",
            "",
            "```caddyfile",
            "vault.example.internal {",
            "  reverse_proxy 127.0.0.1:8789",
            "}",
            "```",
            "",
            "Nginx sketch:",
            "",
            "```nginx",
            "server {",
            "  listen 443 ssl;",
            "  server_name vault.example.internal;",
            "  ssl_certificate /path/fullchain.pem;",
            "  ssl_certificate_key /path/privkey.pem;",
            "  location / { proxy_pass http://127.0.0.1:8789; }",
            "}",
            "```",
            "",
        ]
    )


def _write_remote_client_templates(out: Path) -> dict[str, str]:
    gateway_url = "https://vault.example.internal:8789"
    openapi = gateway_openapi(title="Vault Remote Server")
    openapi["servers"] = [{"url": gateway_url}]
    openapi.setdefault("x-vault-client-template", {})
    openapi["x-vault-client-template"] = {
        "gateway_url_env": "VAULT_REMOTE_URL",
        "token_env": "VAULT_GATEWAY_TOKEN",
        "agent_id_header": False,
        "remote_writes": "candidate_first",
        "active_multi_master_sync": False,
    }

    coze_openapi_path = out / "coze-vault-remote-openapi.json"
    coze_openapi_path.write_text(
        json.dumps(openapi, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    client_config = {
        "version": 1,
        "mode": "remote_gateway_client",
        "gateway_url_env": "VAULT_REMOTE_URL",
        "token_env": "VAULT_GATEWAY_TOKEN",
        "default_gateway_url": gateway_url,
        "auth_headers": {
            "Authorization": "Bearer ${VAULT_GATEWAY_TOKEN}",
            "X-Vault-Gateway-Token": "${VAULT_GATEWAY_TOKEN}",
        },
        "required_request_fields": ["agent_id"],
        "safe_first_requests": [
            {"method": "GET", "path": "/health"},
            {"method": "GET", "path": "/openapi.json"},
            {
                "method": "POST",
                "path": "/search",
                "body": {"agent_id": "<agent-id>", "query": "<task keyword>", "limit": 5},
            },
            {
                "method": "POST",
                "path": "/read-range",
                "body": {"agent_id": "<agent-id>", "knowledge_id": "<id>", "line_start": 1, "line_end": 40},
            },
            {
                "method": "POST",
                "path": "/submit-candidate",
                "body": {
                    "agent_id": "<agent-id>",
                    "title": "<memory proposal>",
                    "content": "<reviewable memory>",
                    "reason": "<why remember>",
                },
            },
        ],
        "clients": {
            "codex": {
                "target": "Project AGENTS.md or MCP/Gateway adapter note",
                "env": {"VAULT_REMOTE_URL": gateway_url, "VAULT_GATEWAY_TOKEN": "replace-with-stable-secret"},
                "startup_note": "Use the remote Gateway only when the local project vault is not available.",
            },
            "claude_code": {
                "target": "Project CLAUDE.md adapter note",
                "env": {"VAULT_REMOTE_URL": gateway_url, "VAULT_GATEWAY_TOKEN": "replace-with-stable-secret"},
                "startup_note": "Search remote memory first, then bounded read before citing.",
            },
            "hermes": {
                "target": "Hermes profile AGENTS.md or runtime bootstrap",
                "env": {"VAULT_REMOTE_URL": gateway_url, "VAULT_GATEWAY_TOKEN": "replace-with-stable-secret"},
                "startup_note": "Keep profile identity private; use remote shared memory for project knowledge.",
            },
            "openclaw": {
                "target": "OpenClaw workspace bootstrap or gateway plugin config",
                "env": {"VAULT_REMOTE_URL": gateway_url, "VAULT_GATEWAY_TOKEN": "replace-with-stable-secret"},
                "startup_note": "Read local latest-context first when present; use remote Gateway for shared Vault memory.",
            },
            "coze": {
                "target": coze_openapi_path.name,
                "mode": "openapi_connector",
                "warning": "Use a scoped Gateway token; never use Supabase service-role keys here.",
            },
            "n8n": {
                "target": "n8n-vault-remote-client.workflow.json",
                "mode": "http_request_workflow",
                "warning": "Store token in n8n credentials or environment variables, not inside workflow JSON.",
            },
        },
        "safety": {
            "candidate_first_writes": True,
            "search_returns_raw_content": False,
            "bounded_read_before_citation": True,
            "active_multi_master_sync": False,
        },
    }
    client_config_path = out / "vault-remote-client-config.json"
    client_config_path.write_text(
        json.dumps(client_config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    n8n_path = out / "n8n-vault-remote-client.workflow.json"
    n8n_path.write_text(
        json.dumps(_remote_n8n_workflow(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    validation_path = out / "validate-vault-remote-client.py"
    validation_path.write_text(_render_remote_client_validation_script(), encoding="utf-8")
    validation_path.chmod(0o755)

    snippets_path = out / "AGENT_REMOTE_GATEWAY_SNIPPETS.md"
    snippets_path.write_text(_render_remote_gateway_snippets(gateway_url), encoding="utf-8")

    readme_path = out / "README-remote-clients.md"
    readme_path.write_text(
        "\n".join(
            [
                "# Vault Remote Client Templates",
                "",
                "Use these templates when an Agent connects to a self-hosted Vault Remote Server.",
                "",
                "Set the same two variables in each client runtime:",
                "",
                "```bash",
                f"export VAULT_REMOTE_URL=\"{gateway_url}\"",
                "export VAULT_GATEWAY_TOKEN=\"replace-with-stable-secret\"",
                "```",
                "",
                "Client files:",
                "",
                f"- `{client_config_path.name}`: machine-readable Codex, Claude Code, Hermes, OpenClaw, Coze, and n8n hints",
                f"- `{snippets_path.name}`: short human/agent setup snippets",
                f"- `{coze_openapi_path.name}`: OpenAPI connector template for Coze or similar hosted tools",
                f"- `{n8n_path.name}`: n8n HTTP Request workflow template",
                f"- `{validation_path.name}`: smoke-test the remote endpoint from an Agent machine",
                "",
                "Validation:",
                "",
                "```bash",
                f"python {validation_path.name} --agent-id codex --query \"deployment SOP\"",
                f"python {validation_path.name} --agent-id codex --submit-candidate",
                "```",
                "",
                "Safety boundary:",
                "",
                "- every request must send `agent_id`;",
                "- remote search returns compact results, not raw full content;",
                "- remote reads should use `/read-range` after search;",
                "- remote writes go to `/submit-candidate`, not active knowledge;",
                "- this is not offline active multi-master sync.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "readme": str(readme_path),
        "client_config": str(client_config_path),
        "agent_snippets": str(snippets_path),
        "coze_openapi": str(coze_openapi_path),
        "n8n_workflow": str(n8n_path),
        "validation_script": str(validation_path),
    }


def _remote_n8n_workflow() -> dict[str, object]:
    return {
        "name": "Vault Remote Server Search",
        "nodes": [
            {
                "id": "vault-search",
                "name": "Vault Remote Search",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4,
                "position": [320, 240],
                "parameters": {
                    "method": "POST",
                    "url": "={{$env.VAULT_REMOTE_URL}}/search",
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": [
                            {"name": "Authorization", "value": "=Bearer {{$env.VAULT_GATEWAY_TOKEN}}"},
                            {"name": "Content-Type", "value": "application/json"},
                        ]
                    },
                    "sendBody": True,
                    "jsonBody": {
                        "agent_id": "n8n",
                        "query": "={{$json.query || $json.text || ''}}",
                        "limit": 5,
                    },
                },
            }
        ],
        "connections": {},
        "settings": {"executionOrder": "v1"},
        "vault_notes": {
            "token_storage": "Store VAULT_GATEWAY_TOKEN in environment variables or n8n credentials.",
            "writes": "Use /submit-candidate for proposed memory; do not bypass candidate review.",
        },
    }


def _render_remote_gateway_snippets(gateway_url: str) -> str:
    return "\n".join(
        [
            "# Agent Remote Gateway Snippets",
            "",
            "Use these snippets when the local runtime should read shared memory from a self-hosted Vault Remote Server.",
            "",
            "## Shared Environment",
            "",
            "```bash",
            f"export VAULT_REMOTE_URL=\"{gateway_url}\"",
            "export VAULT_GATEWAY_TOKEN=\"replace-with-stable-secret\"",
            "```",
            "",
            "## Minimal Search",
            "",
            "```bash",
            "curl -s \"$VAULT_REMOTE_URL/search\" \\",
            "  -H \"Authorization: Bearer $VAULT_GATEWAY_TOKEN\" \\",
            "  -H \"Content-Type: application/json\" \\",
            "  -d '{\"agent_id\":\"codex\",\"query\":\"deployment SOP\",\"limit\":5}'",
            "```",
            "",
            "## Codex / Claude Code",
            "",
            "Add a short project instruction: use `VAULT_REMOTE_URL` only when local `vault-mcp` is unavailable; search first, then bounded read before citing.",
            "",
            "## Hermes / OpenClaw",
            "",
            "Keep identity/personality memory in the runtime profile. Use the remote Gateway for shared project knowledge and candidate-first lessons.",
            "",
            "## Coze / n8n",
            "",
            "Use the generated OpenAPI or workflow template. Store the token in platform credentials or environment variables, not in public prompts.",
            "",
        ]
    )


def _render_remote_client_validation_script() -> str:
    return r'''#!/usr/bin/env python3
"""Smoke-test a Vault Remote Server client connection.

Reads VAULT_REMOTE_URL and VAULT_GATEWAY_TOKEN from the environment. The default
check is read-only: /health, /openapi.json, and /search. Pass
--submit-candidate when you also want to verify candidate-first remote writes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


def _request(base_url: str, token: str, method: str, path: str, body: dict | None = None) -> dict:
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Vault-Gateway-Token": token,
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = response.read().decode("utf-8")
            return {"ok": True, "status_code": response.status, "payload": json.loads(payload or "{}")}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "status_code": exc.code, "error": detail[:500]}
    except Exception as exc:
        return {"ok": False, "status_code": 0, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Vault Remote Server client connection.")
    parser.add_argument("--agent-id", default=os.environ.get("VAULT_AGENT_ID", "remote-smoke"))
    parser.add_argument("--query", default="vault")
    parser.add_argument("--submit-candidate", action="store_true")
    args = parser.parse_args()

    base_url = os.environ.get("VAULT_REMOTE_URL", "").strip()
    token = os.environ.get("VAULT_GATEWAY_TOKEN", "").strip()
    if not base_url or not token:
        print(json.dumps({
            "ok": False,
            "error": "Set VAULT_REMOTE_URL and VAULT_GATEWAY_TOKEN before running validation.",
        }, ensure_ascii=False, indent=2))
        return 2

    checks: list[dict] = []
    checks.append({"name": "health", **_request(base_url, token, "GET", "/health")})
    checks.append({"name": "openapi", **_request(base_url, token, "GET", "/openapi.json")})
    checks.append({
        "name": "search",
        **_request(base_url, token, "POST", "/search", {
            "agent_id": args.agent_id,
            "query": args.query,
            "limit": 5,
        }),
    })
    if args.submit_candidate:
        checks.append({
            "name": "submit_candidate",
            **_request(base_url, token, "POST", "/submit-candidate", {
                "agent_id": args.agent_id,
                "title": f"Remote client smoke {int(time.time())}",
                "content": "Remote client validation candidate. Safe to reject after smoke testing.",
                "reason": "Validate candidate-first remote writes.",
                "scope": "project",
                "sensitivity": "low",
                "tags": "smoke,remote-client",
                "source_ref": f"remote-client-smoke:{args.agent_id}",
            }),
        })

    ok = all(item.get("ok") and int(item.get("status_code") or 0) < 400 for item in checks)
    print(json.dumps({
        "ok": ok,
        "agent_id": args.agent_id,
        "remote_url": base_url,
        "submitted_candidate": bool(args.submit_candidate),
        "checks": checks,
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _render_remote_server_launchagent(command: list[str]) -> str:
    stdout_path = Path.home() / ".vault-for-llm" / "vault-remote-server.log"
    stderr_path = Path.home() / ".vault-for-llm" / "vault-remote-server.err.log"
    program = command[0]
    args = "\n".join(f"    <string>{_xml_escape(arg)}</string>" for arg in command[1:])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.zycaskevin.vault-for-llm.remote-server</string>
  <key>ProgramArguments</key>
  <array>
    <string>{_xml_escape(program)}</string>
{args}
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>VAULT_GATEWAY_TOKEN</key>
    <string>replace-with-stable-secret</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>{_xml_escape(str(stdout_path))}</string>
  <key>StandardErrorPath</key>
  <string>{_xml_escape(str(stderr_path))}</string>
</dict>
</plist>
"""


def _xml_escape(value: object) -> str:
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
