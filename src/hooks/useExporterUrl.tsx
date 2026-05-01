import { useEffect, useState } from 'react';

const STORAGE_KEY = 'exporterUrl';

// Simple hook to manage exporter URL with localStorage persistence
export function useExporterUrl(): [string, (v: string) => void] {
  const [url, setUrl] = useState<string>((): string => {
    if (typeof localStorage !== 'undefined') {
      const v = localStorage.getItem(STORAGE_KEY);
      return v ?? '';
    }
    return '';
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, url);
    } catch {
      // ignore
    }
  }, [url]);

  const update = (v: string) => setUrl(v);
  return [url, update];
}
