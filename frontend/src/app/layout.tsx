import type { Metadata } from 'next';
import './globals.css';
export const metadata:Metadata={title:'QoreSentinel | Smart Contract Security',description:'AI-assisted smart contract auditing and post-quantum readiness'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
