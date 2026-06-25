// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TrustNetRegistry
 * @notice On-chain scam registry for job fraud detection
 * @dev Stores flagged entity hashes with backend signature verification
 */
contract TrustNetRegistry {
    struct FlaggedEntity {
        bytes32 entityHash;      // keccak256(entityType + entityValue)
        uint8 entityType;        // 1=domain, 2=email, 3=phone, 4=company
        uint32 trustScore;       // 0-100
        uint32 reportCount;      // community reports
        uint64 firstFlaggedAt;   // unix timestamp
        uint64 lastUpdatedAt;    // unix timestamp
        bool isActive;
    }

    mapping(bytes32 => FlaggedEntity) public registry;
    address public owner;
    address public backendSigner;

    uint64 public totalEntities;
    uint64 public activeEntities;

    event EntityFlagged(
        bytes32 indexed entityHash,
        uint8 entityType,
        uint32 trustScore,
        uint64 timestamp
    );
    
    event EntityUnflagged(
        bytes32 indexed entityHash,
        uint64 timestamp
    );
    
    event BackendSignerChanged(
        address indexed oldSigner,
        address indexed newSigner
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor(address _backendSigner) {
        require(_backendSigner != address(0), "Invalid signer");
        owner = msg.sender;
        backendSigner = _backendSigner;
    }

    /**
     * @notice Flag an entity on-chain (requires backend signature)
     * @param entityHash keccak256 hash of entity type + value
     * @param entityType 1=domain, 2=email, 3=phone, 4=company
     * @param trustScore Current trust score (0-100)
     * @param reportCount Number of community reports
     * @param signature Backend EIP-191 signature
     */
    function flagEntity(
        bytes32 entityHash,
        uint8 entityType,
        uint32 trustScore,
        uint32 reportCount,
        bytes calldata signature
    ) external {
        require(entityType >= 1 && entityType <= 4, "Invalid entity type");
        require(entityHash != bytes32(0), "Invalid hash");

        // Verify signature from TrustNet backend
        bytes32 msgHash = keccak256(abi.encodePacked(
            entityHash, entityType, trustScore, reportCount
        ));
        address signer = recoverSigner(msgHash, signature);
        require(signer == backendSigner, "Invalid signature");

        FlaggedEntity storage e = registry[entityHash];
        
        if (!e.isActive) {
            e.entityHash = entityHash;
            e.entityType = entityType;
            e.firstFlaggedAt = uint64(block.timestamp);
            e.isActive = true;
            totalEntities++;
            activeEntities++;
        }
        
        e.trustScore = trustScore;
        e.reportCount = reportCount;
        e.lastUpdatedAt = uint64(block.timestamp);

        emit EntityFlagged(entityHash, entityType, trustScore, uint64(block.timestamp));
    }

    /**
     * @notice Check if an entity is flagged
     * @param entityHash The entity hash to check
     */
    function checkEntity(bytes32 entityHash) external view returns (FlaggedEntity memory) {
        return registry[entityHash];
    }

    /**
     * @notice Unflag an entity (owner only)
     */
    function unflagEntity(bytes32 entityHash) external onlyOwner {
        FlaggedEntity storage e = registry[entityHash];
        require(e.isActive, "Not flagged");
        e.isActive = false;
        activeEntities--;
        emit EntityUnflagged(entityHash, uint64(block.timestamp));
    }

    /**
     * @notice Update the backend signer address
     */
    function setBackendSigner(address _newSigner) external onlyOwner {
        require(_newSigner != address(0), "Invalid signer");
        address oldSigner = backendSigner;
        backendSigner = _newSigner;
        emit BackendSignerChanged(oldSigner, _newSigner);
    }

    /**
     * @notice Batch check multiple entities
     */
    function batchCheck(bytes32[] calldata entityHashes) external view returns (FlaggedEntity[] memory) {
        FlaggedEntity[] memory results = new FlaggedEntity[](entityHashes.length);
        for (uint i = 0; i < entityHashes.length; i++) {
            results[i] = registry[entityHashes[i]];
        }
        return results;
    }

    // ============ Signature Recovery ============

    function recoverSigner(bytes32 msgHash, bytes calldata sig) internal pure returns (address) {
        bytes32 ethHash = keccak256(abi.encodePacked(
            "\x19Ethereum Signed Message:\n32", msgHash
        ));
        (bytes32 r, bytes32 s, uint8 v) = splitSignature(sig);
        return ecrecover(ethHash, v, r, s);
    }

    function splitSignature(bytes calldata sig) internal pure returns (bytes32 r, bytes32 s, uint8 v) {
        require(sig.length == 65, "Invalid signature length");
        assembly {
            r := calldataload(sig.offset)
            s := calldataload(add(sig.offset, 32))
            v := byte(0, calldataload(add(sig.offset, 64)))
        }
    }
}