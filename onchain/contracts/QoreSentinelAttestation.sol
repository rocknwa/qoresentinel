// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/// @notice Publishes a timestamped SHA-256 digest of a completed audit report.
/// @dev The digest is calculated off-chain from the exact UTF-8 report bytes.
///      Only the publisher may anchor a digest; this proves publication by that
///      publisher, not the correctness of the underlying AI security report.
contract QoreSentinelAttestation {
    address public immutable publisher;
    mapping(bytes32 => uint64) private _attestedAt;

    error NotPublisher();
    error InvalidPublisher();
    error EmptyReportDigest();
    error AlreadyAttested();

    event ReportAttested(bytes32 indexed reportDigest, address indexed publisher, uint64 timestamp);

    constructor(address initialPublisher) {
        if (initialPublisher == address(0)) revert InvalidPublisher();
        publisher = initialPublisher;
    }

    function attest(bytes32 reportDigest) external {
        if (msg.sender != publisher) revert NotPublisher();
        if (reportDigest == bytes32(0)) revert EmptyReportDigest();
        if (_attestedAt[reportDigest] != 0) revert AlreadyAttested();
        uint64 timestamp = uint64(block.timestamp);
        _attestedAt[reportDigest] = timestamp;
        emit ReportAttested(reportDigest, msg.sender, timestamp);
    }

    function attestedAt(bytes32 reportDigest) external view returns (uint64) {
        return _attestedAt[reportDigest];
    }
}
