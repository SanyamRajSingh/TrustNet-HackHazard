const { expect } = require('chai');
const { ethers } = require('hardhat');

describe('TrustNetRegistry', function () {
  let registry, owner, backendSigner, other;

  beforeEach(async () => {
    [owner, backendSigner, other] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory('TrustNetRegistry');
    registry = await Factory.deploy(backendSigner.address);
    await registry.waitForDeployment();
  });

  it('Should set correct owner and backend signer', async () => {
    expect(await registry.owner()).to.equal(owner.address);
    expect(await registry.backendSigner()).to.equal(backendSigner.address);
  });

  it('Should flag entity with valid signature', async () => {
    const entityHash = ethers.keccak256(ethers.toUtf8Bytes('domain:evil.com'));
    const entityType = 1;
    const trustScore = 15;
    const reportCount = 5;

    const msgHash = ethers.keccak256(
      ethers.solidityPacked(
        ['bytes32', 'uint8', 'uint32', 'uint32'],
        [entityHash, entityType, trustScore, reportCount]
      )
    );
    const signature = await backendSigner.signMessage(ethers.getBytes(msgHash));

    await registry.flagEntity(entityHash, entityType, trustScore, reportCount, signature);

    const result = await registry.checkEntity(entityHash);
    expect(result.isActive).to.be.true;
    expect(result.trustScore).to.equal(trustScore);
    expect(result.entityType).to.equal(entityType);
  });

  it('Should reject invalid signature', async () => {
    const entityHash = ethers.keccak256(ethers.toUtf8Bytes('domain:test.com'));
    const badSignature = '0x' + '00'.repeat(65);

    await expect(
      registry.flagEntity(entityHash, 1, 10, 1, badSignature)
    ).to.be.revertedWith('Invalid signature');
  });

  it('Should allow owner to unflag entity', async () => {
    const entityHash = ethers.keccak256(ethers.toUtf8Bytes('domain:temp.com'));
    const msgHash = ethers.keccak256(
      ethers.solidityPacked(
        ['bytes32', 'uint8', 'uint32', 'uint32'],
        [entityHash, 1, 10, 1]
      )
    );
    const sig = await backendSigner.signMessage(ethers.getBytes(msgHash));
    await registry.flagEntity(entityHash, 1, 10, 1, sig);

    await registry.unflagEntity(entityHash);
    const result = await registry.checkEntity(entityHash);
    expect(result.isActive).to.be.false;
  });
});