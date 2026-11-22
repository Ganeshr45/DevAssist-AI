import './globals.css';
import './theme.css';
import './responsive.css';
import './workspace.css';
import type { Metadata } from 'next';
import { Providers } from '@/components/providers';
export const metadata: Metadata = { title: 'DevAssist AI', description: 'Grounded developer support for your code and docs.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body><Providers>{children}</Providers></body></html>; }
