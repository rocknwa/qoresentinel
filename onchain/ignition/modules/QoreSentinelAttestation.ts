import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

export default buildModule("QoreSentinelAttestationModule", (m) => {
  // Default publisher = deployment signer, which must own the active EVM window.
  const publisher = m.getAccount(0);
  const attestation = m.contract("QoreSentinelAttestation", [publisher]);
  return { attestation };
});
