// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/**
 * @title L28 Bridge Contract
 * @notice Lock/Release bridge for cross-chain transfers via L28
 * @dev Deploy on each EVM chain to enable bridging
 */
contract L28Bridge is ReentrancyGuard, Ownable, Pausable {
    
    // =========================================================================
    // STATE
    // =========================================================================
    
    // Bridge fee (0.1% = 10 basis points)
    uint256 public bridgeFee = 10;
    uint256 public constant FEE_DENOMINATOR = 10000;
    
    // Minimum/Maximum bridge amounts
    uint256 public minBridgeAmount = 0.001 ether;
    uint256 public maxBridgeAmount = 1000 ether;
    
    // Validators (multi-sig for release)
    mapping(address => bool) public validators;
    uint256 public validatorCount;
    uint256 public requiredSignatures = 2;
    
    // Nonces for replay protection
    mapping(bytes32 => bool) public processedNonces;
    
    // Locked funds tracking
    uint256 public totalLocked;
    
    // =========================================================================
    // EVENTS
    // =========================================================================
    
    event BridgeLock(
        address indexed sender,
        uint256 amount,
        uint256 fee,
        string destChain,
        string destAddress,
        bytes32 indexed lockId,
        uint256 timestamp
    );
    
    event BridgeRelease(
        address indexed recipient,
        uint256 amount,
        string sourceChain,
        bytes32 indexed releaseId,
        uint256 timestamp
    );
    
    event ValidatorAdded(address indexed validator);
    event ValidatorRemoved(address indexed validator);
    event FeeUpdated(uint256 oldFee, uint256 newFee);
    
    // =========================================================================
    // CONSTRUCTOR
    // =========================================================================
    
    constructor() Ownable(msg.sender) {
        validators[msg.sender] = true;
        validatorCount = 1;
    }
    
    // =========================================================================
    // BRIDGE FUNCTIONS
    // =========================================================================
    
    /**
     * @notice Lock native tokens for bridging to another chain
     * @param destChain Destination chain identifier (e.g., "polygon", "bsc")
     * @param destAddress Recipient address on destination chain
     */
    function lock(
        string calldata destChain,
        string calldata destAddress
    ) external payable nonReentrant whenNotPaused {
        require(msg.value >= minBridgeAmount, "Below minimum amount");
        require(msg.value <= maxBridgeAmount, "Exceeds maximum amount");
        require(bytes(destChain).length > 0, "Invalid dest chain");
        require(bytes(destAddress).length > 0, "Invalid dest address");
        
        // Calculate fee
        uint256 fee = (msg.value * bridgeFee) / FEE_DENOMINATOR;
        uint256 amountAfterFee = msg.value - fee;
        
        // Generate unique lock ID
        bytes32 lockId = keccak256(abi.encodePacked(
            msg.sender,
            msg.value,
            destChain,
            destAddress,
            block.timestamp,
            block.number
        ));
        
        require(!processedNonces[lockId], "Duplicate lock");
        processedNonces[lockId] = true;
        
        totalLocked += amountAfterFee;
        
        emit BridgeLock(
            msg.sender,
            amountAfterFee,
            fee,
            destChain,
            destAddress,
            lockId,
            block.timestamp
        );
    }
    
    /**
     * @notice Release tokens to recipient (called by validators)
     * @param recipient Address to receive tokens
     * @param amount Amount to release
     * @param sourceChain Source chain identifier
     * @param nonce Unique nonce from source chain
     * @param signatures Validator signatures
     */
    function release(
        address payable recipient,
        uint256 amount,
        string calldata sourceChain,
        bytes32 nonce,
        bytes[] calldata signatures
    ) external nonReentrant whenNotPaused {
        require(!processedNonces[nonce], "Already processed");
        require(signatures.length >= requiredSignatures, "Insufficient signatures");
        require(address(this).balance >= amount, "Insufficient liquidity");
        
        // Verify signatures
        bytes32 messageHash = keccak256(abi.encodePacked(
            recipient,
            amount,
            sourceChain,
            nonce,
            block.chainid
        ));
        bytes32 ethSignedHash = keccak256(abi.encodePacked(
            "\x19Ethereum Signed Message:\n32",
            messageHash
        ));
        
        address[] memory signers = new address[](signatures.length);
        for (uint256 i = 0; i < signatures.length; i++) {
            address signer = recoverSigner(ethSignedHash, signatures[i]);
            require(validators[signer], "Invalid validator");
            
            // Check for duplicate signers
            for (uint256 j = 0; j < i; j++) {
                require(signers[j] != signer, "Duplicate signer");
            }
            signers[i] = signer;
        }
        
        processedNonces[nonce] = true;
        totalLocked -= amount;
        
        // Transfer funds
        (bool success, ) = recipient.call{value: amount}("");
        require(success, "Transfer failed");
        
        emit BridgeRelease(
            recipient,
            amount,
            sourceChain,
            nonce,
            block.timestamp
        );
    }
    
    // =========================================================================
    // ADMIN FUNCTIONS
    // =========================================================================
    
    function addValidator(address validator) external onlyOwner {
        require(!validators[validator], "Already validator");
        validators[validator] = true;
        validatorCount++;
        emit ValidatorAdded(validator);
    }
    
    function removeValidator(address validator) external onlyOwner {
        require(validators[validator], "Not validator");
        require(validatorCount > requiredSignatures, "Would break threshold");
        validators[validator] = false;
        validatorCount--;
        emit ValidatorRemoved(validator);
    }
    
    function setRequiredSignatures(uint256 _required) external onlyOwner {
        require(_required > 0 && _required <= validatorCount, "Invalid threshold");
        requiredSignatures = _required;
    }
    
    function setFee(uint256 _fee) external onlyOwner {
        require(_fee <= 100, "Fee too high"); // Max 1%
        emit FeeUpdated(bridgeFee, _fee);
        bridgeFee = _fee;
    }
    
    function setLimits(uint256 _min, uint256 _max) external onlyOwner {
        require(_min < _max, "Invalid limits");
        minBridgeAmount = _min;
        maxBridgeAmount = _max;
    }
    
    function pause() external onlyOwner {
        _pause();
    }
    
    function unpause() external onlyOwner {
        _unpause();
    }
    
    function withdrawFees(address payable to) external onlyOwner {
        uint256 fees = address(this).balance - totalLocked;
        require(fees > 0, "No fees to withdraw");
        (bool success, ) = to.call{value: fees}("");
        require(success, "Withdraw failed");
    }
    
    // =========================================================================
    // HELPER FUNCTIONS
    // =========================================================================
    
    function recoverSigner(bytes32 hash, bytes memory signature) internal pure returns (address) {
        require(signature.length == 65, "Invalid signature length");
        
        bytes32 r;
        bytes32 s;
        uint8 v;
        
        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }
        
        if (v < 27) v += 27;
        require(v == 27 || v == 28, "Invalid signature v");
        
        return ecrecover(hash, v, r, s);
    }
    
    // Allow contract to receive ETH
    receive() external payable {
        totalLocked += msg.value;
    }
    
    // =========================================================================
    // VIEW FUNCTIONS
    // =========================================================================
    
    function getContractBalance() external view returns (uint256) {
        return address(this).balance;
    }
    
    function getAvailableLiquidity() external view returns (uint256) {
        return address(this).balance - totalLocked;
    }
    
    function isValidator(address account) external view returns (bool) {
        return validators[account];
    }
}
