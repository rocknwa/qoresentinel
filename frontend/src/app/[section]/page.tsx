import Home from '../workspace-client';
import { WORKSPACE_SECTIONS } from '@/lib/routes';

// Render only known workspace sections; unknown slugs return a real 404.
export const dynamicParams = false;

export function generateStaticParams() {
  return WORKSPACE_SECTIONS.map(section => ({ section }));
}

export default function WorkspaceSectionPage() {
  return <Home />;
}
