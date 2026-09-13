export async function importBatch(files, {apiBase = ''} = {}) {
  const form = new FormData();
  for (const file of files) form.append('files', file, file.name);
  const response = await fetch(`${apiBase}/api/ingest`, {method: 'POST', body: form});
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `Import failed (${response.status})`);
  return payload.records;
}
