# XTS Core Test Specification #

This document defines the expected behavior of XTS core across different use cases, including its interaction with .xts files and the allocator client.


The test specification covers the following scenarios:
- Usage with structured and unstructured .xts files

- Operation without .xts files

- Execution with and without the YAML runner

- Interaction with the allocator client

### Handling of .xts Files ###

#### Structured .xts File ####

Preconditions: A valid .xts file with structured data is available.

Expected Behavior:

- XTS should correctly parse and load the .xts file.

- Execution should proceed without errors.

- The expected test cases should run and produce correct results.

#### Unstructured .xts File ####

Preconditions: A malformed or incorrectly structured .xts file is present.

Expected Behavior:

- XTS should detect the malformed structure and log an appropriate error.

- Execution should fail gracefully without crashes.

#### No .xts File ####

Preconditions: No .xts file is provided.

Expected Behavior:

- XTS should handle the missing file gracefully.

- A clear error message should be logged.

- Execution should be halted or fallback behavior should be triggered.

### YAML Runner Usage ###

#### Execution with YAML Runner ####

Preconditions: The YAML runner is available and configured.

Expected Behavior:

- XTS should correctly interpret YAML test definitions.

- Test cases should execute as defined in the YAML files.

- Logs should indicate successful parsing and execution.

#### Execution without YAML Runner ####

Preconditions: YAML runner is not used.

Expected Behavior:

- XTS should operate without dependency on the YAML runner.

- Other test execution methods should remain functional.

### Allocator Client Interaction ###

#### Execution with Allocator Client ####

Preconditions: Allocator client is available and properly configured.

Expected Behavior:

- XTS should integrate with the allocator client correctly.

- Resource allocation should be managed efficiently.

- No resource leaks or mismanagement should occur.

#### Execution without Allocator Client ####

Preconditions: Allocator client is not used.

Expected Behavior:

- XTS should function without reliance on the allocator client.

- Tests should execute without resource allocation errors.


## XTSAllocatorClient Commands ##

The following test cases cover the XTSAllocatorClient command-line interface interactions. The tests ensure correct behavior for all supported commands, including slot allocation, deallocation, and allocator server management.

### Allocate Slot ###

#### Allocate Slot with ID ####

Command: allocate --id 123 --server http://allocator-server

Expected Result:

- The request is sent to http://allocator-server/allocate with payload { "id": 123 }.

- The response contains slot_id, indicating successful allocation.

- Rack configuration is retrieved and displayed.

#### Allocate Slot with Platform and Tags ####

Command: allocate --platform linux --tags gpu memory --server http://allocator-server

Expected Result:

- The request is sent to http://allocator-server/allocate with payload { "platform": "linux", "tags": ["gpu", "memory"] }.

- The response contains slot_id.

- Rack configuration is retrieved and displayed.

#### Allocation Failure ####

Command: allocate --platform linux --server http://allocator-server

Expected Result:

- If the server returns an error, the appropriate message is displayed.

- Exit with non-zero status.

### Deallocate Slot ###

#### Deallocate Slot by ID ####

Command: deallocate --id 123 --server http://allocator-server

Expected Result:

- The request is sent to http://allocator-server/deallocate with payload { "id": 123 }.

- The response confirms successful deallocation.

### Allocator Server Management ###

#### Add Allocator Server ####

Command: allocator add --server http://allocator-server

Expected Result:

- The server is added to the configuration file.

- Success message is displayed.

#### Remove Allocator Server ####

Command: allocator remove --server http://allocator-server

Expected Result:

- The server is removed from the configuration file.

- Success message is displayed.

#### List Allocator Servers ####

Command: allocator list

Expected Result:

- The configured allocator servers are displayed.

- If no servers exist, a warning message is shown.

### Slot Management ###

#### Add Slot ####

Command: allocator add-slot --rackName R1 --slotName S1 --platform linux --server http://allocator-server

Expected Result:

- The request is sent to http://allocator-server/add_slot with relevant payload.

- The response confirms slot creation.

#### Update Slot ####

Command: allocator update-slot --slot_id 123 --platform windows --server http://allocator-server

Expected Result:

- The request is sent to http://allocator-server/update_slot with updated fields.

- The response confirms slot update.

#### Remove Slot ####

Command: allocator remove-slot --slot_id 123 --server http://allocator-server

Expected Result:

- The request is sent to http://allocator-server/delete_slot.

- The response confirms slot removal.

### Search for Slots ###

#### Search for Slots by Platform and Tags ####

Command: allocator search --platform linux --tags gpu --server http://allocator-server

Expected Result:

- The request is sent to http://allocator-server/list_slots.

- Matching slots are displayed.

### Error Handling Tests ###

#### Missing Required Arguments ####

Command: allocate --tags gpu --server http://allocator-server

Expected Result:

- Error message: --platform is required when --tags is specified.

- Exit with non-zero status.

#### Invalid Server URL ####

Command: allocate --id 123 --server http://invalid-server

Expected Result:

- Request fails.

- Error message is displayed.

#### Command Not Found ####

Command: invalid-command

Expected Result:

- Error message: Command not recognized.

- Exit with non-zero status.
