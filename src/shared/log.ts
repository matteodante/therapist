type Fields = Record<string, string | number | boolean | null | undefined>;

export function logEvent(event: string, fields: Fields = {}): void {
  const sanitized = Object.fromEntries(
    Object.entries(fields).filter(([, value]) => value !== undefined),
  );
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    event,
    ...sanitized,
  }));
}

export function logError(event: string, error: unknown, fields: Fields = {}): void {
  const message = error instanceof Error ? error.message : String(error);
  logEvent(event, { ...fields, error: message });
}
