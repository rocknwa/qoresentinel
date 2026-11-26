# AI Usage and Development Disclosure

QoreSentinel uses AI as a core component of its smart-contract security analysis workflow and as an engineering aid during development.

This document describes where AI is used, how the AI components are orchestrated, the external projects acknowledged, and the engineering decisions and responsibilities retained by the developer.

## 1. AI in the QoreSentinel application

### Twelve-specialist smart-contract security analysis

QoreSentinel incorporates the twelve specialist-agent prompts and supporting auditor and judging guidance from [Pashov Audit Group's open-source `solidity-auditor` skill](https://github.com/pashov/skills/tree/main/solidity-auditor). These upstream materials are MIT-licensed.

The specialist approach divides smart-contract security analysis into focused areas rather than relying on one general-purpose AI prompt. The specialist analyses are consolidated through a final judge stage.

QoreSentinel adapts this foundation into its own application workflow, including:

- Solidity source ingestion through pasted code, `.sol` files and ZIP archives.
- Backend audit orchestration and execution tracking.
- Integration with configurable cloud LLM providers.
- Collection and presentation of specialist analysis results.
- Final judge synthesis, Markdown security reports and report-derived findings.
- Persistent audit history and wallet-scoped access.

Pashov Audit Group is credited for the upstream specialist prompts and auditing methodology. QoreSentinel's Python orchestration and surrounding application integration are developed independently.

### LLM providers

The backend supports a configurable provider fallback chain:

1. Anthropic
2. OpenRouter
3. Groq
4. AgentRouter

Provider selection depends on available credentials, model availability and runtime failures. The codebase also includes separate rule-based static scanning; the full twelve-specialist audit requires an available LLM provider and does not automatically substitute a rule-only report if all providers fail.

The specific model used may change as providers update their offerings.

### AI Security Assistant

QoreSentinel also provides an AI-powered security assistant that helps users understand their projects and audit results. Its purpose is to provide contextual explanations and additional security insight based on available project information.

## 2. Post-quantum readiness and QoreScan integration

QoreSentinel integrates QoreScan, a cryptographic inventory tool, for post-quantum readiness analysis. It runs separately from the LLM-based security audit.

QoreScan identifies cryptographic assets and their source locations, classifies relevant algorithms and generates a CycloneDX 1.6 Cryptographic Bill of Materials (CBOM).

QoreSentinel presents the audit and cryptographic inventory as complementary workflows, giving developers visibility into contract security findings and cryptographic exposure.

## 3. AI-assisted development

AI tools were used as engineering assistance during the development process, including:

- Exploring architecture and implementation approaches.
- Reviewing implementation ideas and identifying potential edge cases.
- Assisting with debugging and troubleshooting.
- Improving technical documentation and explanations.
- Supporting development and refinement of the application.

AI-generated suggestions were treated as assistance rather than authoritative engineering decisions. The developer remained responsible for selecting implementation approaches, integrating components, reviewing changes, testing functionality and validating the resulting application.

**Development tool:** ChatGPT.

## 4. Human engineering contributions

The project involves substantial engineering beyond model inference.

The developer designed and implemented the QoreSentinel application, including:

- Product architecture and frontend/backend integration.
- FastAPI backend and Next.js workspace.
- Wallet authentication and session management.
- Project and Solidity source ingestion.
- Audit job orchestration, persistence and reporting.
- LLM provider integration and fallback handling.
- QoreScan integration and CBOM presentation.
- QoreChain Diana testnet transaction verification.
- Native fUSD payment-intent and subscription verification.
- Database persistence, API authorization and automated tests.
- Deployment configuration and CI workflows.

AI tools do not independently own these engineering decisions or replace implementation, integration and testing.

## 5. Limitations and responsible use

AI-generated security findings can contain false positives, miss vulnerabilities or misinterpret contract behavior.

QoreSentinel is an automated security analysis aid, not a guarantee that a contract is secure or a replacement for a comprehensive manual security audit.

Users should independently validate findings, reproduce important issues and obtain qualified human review before relying on security conclusions or deploying contracts handling real assets.

Similarly, cryptographic inventory and readiness classifications indicate detected dependencies and potential exposure; they do not prove that a contract or system is quantum-safe.
