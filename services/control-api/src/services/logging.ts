type LogLevel = "info" | "warn" | "error";

export function logEvent(level: LogLevel, event: string, fields: Record<string, unknown> = {}): void {
  const payload = {
    timestamp: new Date().toISOString(),
    service: "control-api",
    level,
    event,
    ...fields,
  };

  const line = JSON.stringify(payload);
  if (level === "error") {
    console.error(line);
  } else if (level === "warn") {
    console.warn(line);
  } else {
    console.log(line);
  }
}

export function nowMs(): number {
  return Number(process.hrtime.bigint() / 1_000_000n);
}
