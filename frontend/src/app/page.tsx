import type { Metadata } from 'next';
import Link from 'next/link';
import {
  ArrowRight, ArrowUpRight, Check, CheckCircle2, ChevronRight,
  Code2, Cpu, FileCheck2, FileCode2, Fingerprint, Github,
  LockKeyhole, Radar, Shield, ShieldCheck, ShieldHalf,
  Sparkles, TerminalSquare, Workflow, Zap
} from 'lucide-react';
import './landing.css';

export const metadata: Metadata = {
  title: 'QoreSentinel — Audit Smarter. Prove More.',
  description: 'AI-assisted Solidity security audits with 12 specialist perspectives, post-quantum readiness analysis, CycloneDX cryptographic inventories and on-chain report attestations on QoreChain Diana.',
  openGraph: {
    title: 'QoreSentinel — Audit Smarter. Prove More.',
    description: 'Security intelligence for smart contracts, from AI-assisted auditing to post-quantum readiness and verifiable on-chain report fingerprints.',
    type: 'website',
  },
};

const CONTRACT = '0x457962c68d6F3BeaAdAF47456402F57Fb40Fc6BF';
const ATTESTATION = '0x4ba2f6d45ce7afe5a0eef16c34f820d4528a29149890633860e38e79e9f2a958';

const features = [
  {
    number: '01', label: 'MULTI-AGENT ANALYSIS', icon: Cpu,
    title: 'Twelve perspectives. One clear report.',
    description: 'Go beyond a single AI pass. Twelve specialist security agents investigate Solidity source, with a final judge consolidating evidence-backed findings.',
    detail: 'Access control · Invariants · Execution traces',
    className: 'lp-feature-ai',
  },
  {
    number: '02', label: 'POST-QUANTUM READINESS', icon: Fingerprint,
    title: 'Know your cryptographic exposure.',
    description: 'Find cryptographic dependencies in Solidity projects with QoreScan. Export a CycloneDX 1.6 cryptographic bill of materials to support future migration planning.',
    detail: 'QoreScan · Cryptographic inventory · CBOM',
    className: 'lp-feature-pqc',
  },
  {
    number: '03', label: 'ON-CHAIN ATTESTATION', icon: FileCheck2,
    title: 'Turn an audit into verifiable evidence.',
    description: 'Request publication of the report fingerprint directly from your workspace. QoreSentinel anchors the SHA-256 digest to QoreChain Diana without putting your report on-chain.',
    detail: 'Hybrid authorization · SHA-256 · Diana',
    className: 'lp-feature-proof',
  },
] as const;

const steps = [
  { number: '01', title: 'Connect QoreX', copy: 'Authenticate your wallet to open a private, owner-scoped security workspace.' },
  { number: '02', title: 'Submit Solidity', copy: 'Paste your contract source or upload .sol files and ZIP archives.' },
  { number: '03', title: 'Understand the risks', copy: 'Review specialist analysis, report findings and cryptographic exposure.' },
  { number: '04', title: 'Anchor the evidence', copy: 'Request an optional on-chain fingerprint for a completed audit.' },
] as const;

function Brand({ compact = false }: { compact?: boolean }) {
  return <Link className="lp-brand" href="/" aria-label="QoreSentinel home">
    <span className="lp-brand-symbol"><ShieldHalf size={21} strokeWidth={2.1}/></span>
    <span className="lp-brand-word">Qore<span>Sentinel</span>{!compact && <small>SECURITY, WITHOUT THE BLIND SPOTS</small>}</span>
  </Link>;
}

export default function LandingPage() {
  return <div className="lp-root">
    <div className="lp-mesh" aria-hidden="true"/>
    <header className="lp-header">
      <div className="lp-wrap lp-header-inner">
        <Brand/>
        <nav className="lp-nav" aria-label="Main navigation">
          <a href="#capabilities">Capabilities</a>
          <a href="#how-it-works">How it works</a>
          <a href="#proof">On-chain proof</a>
        </nav>
        <div className="lp-header-actions">
          <Link className="lp-header-login" href="/overview">Open workspace</Link>
          <Link className="lp-btn lp-btn-primary lp-btn-small" href="/new-audit">Launch app <ArrowUpRight size={16}/></Link>
        </div>
      </div>
    </header>

    <main id="main-content">
      <section className="lp-hero lp-wrap" aria-labelledby="lp-heading">
        <div className="lp-hero-copy">
          <div className="lp-eyebrow"><span className="lp-beacon"/> THE NEXT ERA OF SMART CONTRACT SECURITY</div>
          <h1 id="lp-heading">Audit smarter.<br/><span>Prove more.</span></h1>
          <p className="lp-hero-lede">AI-powered Solidity audits. Post-quantum readiness. Verifiable on-chain evidence. <strong>One powerful security workspace.</strong></p>
          <div className="lp-hero-actions">
            <Link className="lp-btn lp-btn-primary" href="/new-audit">Start your audit <ArrowUpRight size={19}/></Link>
            <a className="lp-btn lp-btn-outline" href="#how-it-works">Explore how it works <ArrowRight size={18}/></a>
          </div>
          <div className="lp-hero-trust">
            <span><CheckCircle2 size={16}/> Wallet-connected</span>
            <i aria-hidden="true"/>
            <span><CheckCircle2 size={16}/> Testnet-powered</span>
            <i aria-hidden="true"/>
            <span><CheckCircle2 size={16}/> Evidence-focused</span>
          </div>
        </div>
        <div className="lp-hero-art">
          <div className="lp-orbit lp-orbit-one" aria-hidden="true"/><div className="lp-orbit lp-orbit-two" aria-hidden="true"/>
          <div className="lp-preview">
            <div className="lp-preview-top"><span className="lp-preview-dots" aria-hidden="true"><b/><b/><b/></span><span>QORESENTINEL / SECURITY OPERATIONS</span><span className="lp-preview-live"><span/>DIANA TESTNET</span></div>
            <div className="lp-preview-body">
              <div className="lp-preview-side" aria-hidden="true">
                <div className="lp-preview-side-mark"><Shield size={21}/></div>
                <span className="lp-preview-side-active"><Radar size={18}/></span>
                <span><Fingerprint size={18}/></span>
                <span><FileCheck2 size={18}/></span>
                <span><Code2 size={18}/></span>
              </div>
              <div className="lp-preview-main">
                <div className="lp-preview-heading"><div><span className="lp-preview-kicker">AUDIT ENGINE / ANALYSIS</span><h2>Security intelligence</h2></div><span className="lp-preview-pill"><span/> Analysis view</span></div>
                <div className="lp-preview-grid">
                  <div className="lp-preview-code">
                    <div className="lp-preview-code-title"><span><FileCode2 size={15}/> Vault.sol</span><span>Solidity</span></div>
                    <div className="lp-code-line"><em>01</em><span><b>pragma</b> solidity ^0.8.20;</span></div>
                    <div className="lp-code-line"><em>02</em><span></span></div>
                    <div className="lp-code-line"><em>03</em><span><b>contract</b> Vault {'{'}</span></div>
                    <div className="lp-code-line"><em>04</em><span>  mapping(address =&gt; uint) balances;</span></div>
                    <div className="lp-code-line"><em>05</em><span></span></div>
                    <div className="lp-code-line lp-code-focus"><em>06</em><span>  <b>function</b> withdraw(uint amount)</span></div>
                    <div className="lp-code-line lp-code-focus"><em>07</em><span>    public {'{'}</span></div>
                    <div className="lp-code-line lp-code-focus"><em>08</em><span>    msg.sender.call{'{'}value: amount{'}'}(&quot;&quot;);</span></div>
                    <div className="lp-code-line"><em>09</em><span>    balances[msg.sender] -= amount;</span></div>
                    <div className="lp-code-line"><em>10</em><span>  {'}'}</span></div>
                    <div className="lp-code-line"><em>11</em><span>{'}'}</span></div>
                  </div>
                  <div className="lp-preview-insights">
                    <div className="lp-preview-insights-head"><span>ANALYSIS LAYERS</span><Sparkles size={14}/></div>
                    <div className="lp-insight-item"><span className="lp-insight-icon"><ShieldCheck size={16}/></span><span><b>Access control</b><small>Security specialist</small></span><Check size={14}/></div>
                    <div className="lp-insight-item"><span className="lp-insight-icon"><Workflow size={16}/></span><span><b>Execution trace</b><small>Security specialist</small></span><Check size={14}/></div>
                    <div className="lp-insight-item"><span className="lp-insight-icon"><Zap size={16}/></span><span><b>Economic security</b><small>Security specialist</small></span><Check size={14}/></div>
                    <div className="lp-preview-insights-bottom"><span className="lp-insight-pulse"/><span>12 specialist perspectives</span></div>
                  </div>
                </div>
                <div className="lp-preview-footer"><span><span className="lp-preview-footer-check"><Check size={13}/></span> Connected security workflow</span><span>QoreSentinel</span></div>
              </div>
            </div>
          </div>
          <div className="lp-float lp-float-left"><div><Fingerprint size={17}/></div><span><small>POST-QUANTUM READINESS</small><b>Cryptographic inventory</b></span><CheckCircle2 size={16}/></div>
          <div className="lp-float lp-float-right"><span className="lp-float-check"><Check size={17}/></span><span><small>ON-CHAIN EVIDENCE</small><b>Report fingerprint verified</b></span></div>
          <span className="lp-preview-note">Illustrative interface preview · not an actual audit result</span>
        </div>
      </section>

      <section className="lp-proofstrip" aria-label="Platform capabilities">
        <div className="lp-wrap lp-proofstrip-inner">
          <span className="lp-strip-label">BUILT FOR WHAT'S NEXT</span>
          <div><strong>12</strong><span>specialist AI perspectives</span></div>
          <span className="lp-strip-divider" aria-hidden="true"/>
          <div><strong>CycloneDX 1.6</strong><span>cryptographic bill of materials</span></div>
          <span className="lp-strip-divider" aria-hidden="true"/>
          <div><strong>Diana 9800</strong><span>on-chain attestation network</span></div>
        </div>
      </section>

      <section className="lp-section lp-features lp-wrap" id="capabilities">
        <div className="lp-section-head">
          <div><div className="lp-section-kicker"><span/> WHY QORESENTINEL</div><h2>All the intelligence.<br/><span>None of the blind spots.</span></h2></div>
          <p>Security means understanding the code, recognizing cryptographic dependencies, and preserving what was reviewed. We bring the three together.</p>
        </div>
        <div className="lp-feature-grid">
          {features.map(feature => <article className={'lp-feature-card ' + feature.className} key={feature.number}>
            <div className="lp-feature-top"><span>{feature.number} / {feature.label}</span><feature.icon size={21} strokeWidth={1.8}/></div>
            <div className="lp-feature-graphic" aria-hidden="true">
              {feature.number === '01' ? <div className="lp-graphic-nodes"><span/><span/><span/><span/><span/><span/><span/><span/><span/></div> :
               feature.number === '02' ? <div className="lp-graphic-rings"><Fingerprint size={58} strokeWidth={1.05}/></div> :
               <div className="lp-graphic-stamp"><FileCheck2 size={42} strokeWidth={1.2}/><span>CHAIN VERIFIED</span></div>}
            </div>
            <h3>{feature.title}</h3><p>{feature.description}</p>
            <div className="lp-feature-meta">{feature.detail}</div>
          </article>)}
        </div>
      </section>

      <section className="lp-section lp-process" id="how-it-works">
        <div className="lp-wrap">
          <div className="lp-section-head lp-section-head-center"><div><div className="lp-section-kicker"><span/> THE WORKFLOW</div><h2>From source code<br/><span>to security confidence.</span></h2></div><p>Move from your Solidity source to structured analysis and independently checkable report evidence in four clear steps.</p></div>
          <div className="lp-steps">
            {steps.map((step, i) => <div className="lp-step" key={step.number}><div className="lp-step-number">{step.number}<span>{i<3?<ChevronRight size={21}/>:<Check size={20}/>}</span></div><h3>{step.title}</h3><p>{step.copy}</p></div>)}
          </div>
          <div className="lp-process-footer"><Link className="lp-btn lp-btn-primary" href="/new-audit">Try the workflow <ArrowUpRight size={18}/></Link><span>No need to deploy your contract to run a source audit.</span></div>
        </div>
      </section>

      <section className="lp-section lp-chain lp-wrap" id="proof">
        <div className="lp-chain-copy">
          <div className="lp-section-kicker"><span/> PROOF, NOT PROMISES</div>
          <h2>Security findings are useful.<br/><span>Verifiable evidence is stronger.</span></h2>
          <p>QoreSentinel publishes the SHA-256 fingerprint of a completed audit report to QoreChain Diana. Anyone with the exact report bytes can check that fingerprint and its recorded time—without putting private report contents on-chain.</p>
          <div className="lp-chain-tags"><span><LockKeyhole size={15}/> Report remains private</span><span><ShieldCheck size={15}/> Publisher-authorized</span></div>
          <Link className="lp-text-link" href="/overview">Explore the on-chain workflow <ArrowUpRight size={18}/></Link>
        </div>
        <div className="lp-chain-card">
          <div className="lp-chain-card-top"><span><CheckCircle2 size={17}/> CONFIRMED ON DIANA</span><span>TESTNET / 9800</span></div>
          <div className="lp-chain-card-main"><div className="lp-chain-symbol"><ShieldCheck size={34}/></div><div><span>Recorded attestation</span><strong>Verified on-chain</strong></div></div>
          <div className="lp-chain-data"><div><span>Contract</span><code title={CONTRACT}>{CONTRACT.slice(0,12)}...{CONTRACT.slice(-8)}</code></div><div><span>Transaction</span><code title={ATTESTATION}>{ATTESTATION.slice(0,12)}...{ATTESTATION.slice(-8)}</code></div><div><span>Published (UTC)</span><strong>28 Nov 2026 · 09:06:22</strong></div></div>
          <div className="lp-chain-foot"><span><span/> Public Diana testnet evidence</span><a href="https://explore.qore.network/" target="_blank" rel="noreferrer">Open explorer <ArrowUpRight size={14}/></a></div>
        </div>
      </section>

      <section className="lp-cta-section lp-wrap">
        <div className="lp-cta-surface"><div className="lp-cta-grid" aria-hidden="true"/><div className="lp-cta-inner">
          <div className="lp-section-kicker"><span/> YOUR NEXT AUDIT STARTS HERE</div>
          <h2>Build boldly.<br/><span>Audit intelligently.</span></h2>
          <p>Bring contract auditing, quantum-readiness insights, and verifiable evidence into one place.</p>
          <div className="lp-cta-actions"><Link className="lp-btn lp-btn-primary" href="/new-audit">Launch QoreSentinel <ArrowUpRight size={19}/></Link><Link className="lp-btn lp-btn-outline" href="/overview">Explore workspace <ArrowRight size={17}/></Link></div>
        </div></div>
      </section>
    </main>

    <footer className="lp-footer"><div className="lp-wrap lp-footer-inner"><div><Brand compact/><p>Security intelligence for the next generation of on-chain builders.</p></div><div className="lp-footer-links"><a href="#capabilities">Capabilities</a><a href="#how-it-works">How it works</a><Link href="/overview">Workspace</Link><a href="https://github.com/rocknwa/qoresentinel" target="_blank" rel="noreferrer"><Github size={17}/> GitHub</a></div></div><div className="lp-wrap lp-footer-bottom"><span>© 2026 QoreSentinel. Independent project.</span><span>AI-assisted security analysis requires independent verification. Diana testnet assets have no real monetary value.</span></div></footer>
  </div>;
}
