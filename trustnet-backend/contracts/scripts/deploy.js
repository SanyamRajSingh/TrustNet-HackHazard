const hre = require('hardhat');

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log('Deploying with account:', deployer.address);

  const backendSigner = process.env.BACKEND_SIGNER_ADDRESS || deployer.address;
  console.log('Backend signer:', backendSigner);

  const TrustNetRegistry = await hre.ethers.getContractFactory('TrustNetRegistry');
  const registry = await TrustNetRegistry.deploy(backendSigner);
  await registry.waitForDeployment();

  const address = await registry.getAddress();
  console.log('TrustNetRegistry deployed to:', address);
  console.log('Network:', hre.network.name);
  console.log('Verify with: npx hardhat verify --network base_sepolia', address, backendSigner);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });