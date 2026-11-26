/** Public workspace URLs. The authenticated data behind each view remains owner-scoped. */
export const VIEW_PATHS = {
  overview: '/overview',
  'new-audit': '/new-audit',
  'audit-progress': '/audit-progress',
  'audit-results': '/audit-results',
  'audit-history': '/audit-history',
  'transaction-history': '/transaction-history',
  assistant: '/ai-assistant',
  pqc: '/pqc-readiness',
  billing: '/billing',
  settings: '/settings',
} as const;

export type View = keyof typeof VIEW_PATHS;

export const WORKSPACE_SECTIONS = Object.values(VIEW_PATHS).map(path => path.slice(1));

export function viewFromPathname(pathname: string | null): View {
  const normalized = (pathname || '/').replace(/\/+$/, '') || '/';
  for (const [view, path] of Object.entries(VIEW_PATHS)) {
    if (path === normalized) return view as View;
  }
  return 'overview';
}
