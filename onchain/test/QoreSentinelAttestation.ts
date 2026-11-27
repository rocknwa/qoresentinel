import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { network } from "hardhat";

const digest = ("0x" + "11".repeat(32)) as `0x${string}`;
const digest2 = ("0x" + "22".repeat(32)) as `0x${string}`;
const zero = ("0x" + "00".repeat(32)) as `0x${string}`;

describe("QoreSentinelAttestation", async () => {
  const { viem } = await network.create();
  const [owner, stranger] = await viem.getWalletClients();

  async function setup() {
    return viem.deployContract("QoreSentinelAttestation", [owner.account.address]);
  }

  it("stores the publisher and starts with no attestations", async () => {
    const contract = await setup();
    assert.equal(String(await contract.read.publisher()).toLowerCase(), owner.account.address.toLowerCase());
    assert.equal(await contract.read.attestedAt([digest]), 0n);
  });

  it("anchors a report digest and emits the digest and publisher", async () => {
    const contract = await setup();
    await viem.assertions.emit(contract.write.attest([digest]), contract, "ReportAttested");
    assert.ok(BigInt(String(await contract.read.attestedAt([digest]))) > 0n);
    assert.equal(await contract.read.attestedAt([digest2]), 0n);
  });

  it("rejects repeat publication", async () => {
    const contract = await setup();
    await contract.write.attest([digest]);
    await assert.rejects(contract.write.attest([digest]));
  });

  it("rejects empty digest", async () => {
    const contract = await setup();
    await assert.rejects(contract.write.attest([zero]));
  });

  it("rejects non-publisher and zero publisher", async () => {
    const contract = await setup();
    await assert.rejects(contract.write.attest([digest], { account: stranger.account }));
    await assert.rejects(viem.deployContract("QoreSentinelAttestation", ["0x0000000000000000000000000000000000000000"]));
  });
});

