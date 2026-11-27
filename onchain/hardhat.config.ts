import hardhatToolboxViemPlugin from "@nomicfoundation/hardhat-toolbox-viem";
import { configVariable, defineConfig } from "hardhat/config";

try { process.loadEnvFile(); } catch { /* Use environment or Hardhat keystore. */ }

export default defineConfig({
  plugins: [hardhatToolboxViemPlugin],
  solidity: {
    profiles: {
      default: { version: "0.8.28" },
      production: { version: "0.8.28", settings: { optimizer: { enabled: true, runs: 200 } } },
    },
  },
  networks: {
    hardhatMainnet: { type: "edr-simulated", chainType: "l1" },
    qorechainTestnet: {
      type: "http", chainType: "l1", chainId: 9800,
      url: "https://evm-testnet.qore.host",
      accounts: [configVariable("PRIVATE_KEY")],
    },
  },
});
