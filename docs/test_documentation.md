# XTS Core Test Specification #

This document defines the expected behavior of XTS core across different use cases, including its interaction with .xts files and YAML file execution.

The test specification covers the following scenarios:

- Usage with structured and unstructured .xts files

- Operation without .xts files

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

- XTS should log a clear error message indicating the file is missing.
- Execution of test cases and allocator-related subcommands via `xts` should not proceed.
- This scenario validates correct error handling in alias-only mode; no allocator commands are expected to run when invoked through `xts` without a valid alias.

#### Multiple .xts Files ####

Preconditions: More than one .xts file is present in the working directory.

Expected Behavior:

- XTS should detect the presence of multiple .xts files.

- An error message should be logged, listing the found files.

- The user should be shown how to run each file individually using the appropriate command.


## XTS AllocatorClient Commands ##

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

#### Allocate Slot with Platform and No Tags ####

Command: allocate --platform linux --server http://allocator-server

Expected Result:

- The request is sent to http://allocator-server/allocate with payload { "platform": "linux" }

- The response contains slot_id.

- Rack configuration is retrieved and displayed.

### Deallocate Slot ###

Command: deallocate --id 123 --server http://allocator-server

Expected Result:

- The request is sent to http://allocator-server/deallocate with payload { "id": 123 }.

- The response confirms successful deallocation.

### Allocator Server Management ###

#### Add Allocator Server ####

Command: allocator add test_allocator http://allocator-server

Expected Result:

- The server is added to the configuration file under the name test_allocator.

- Success message is displayed.

#### Remove Allocator Server ####

Command: allocator remove test_allocator

Expected Result:

- The entry for test_allocator is removed from the configuration file.

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

- The request is sent to http://allocator-server/add_slot with payload { "rackName": R1, "slotName": "S1", "platform": "linux"}

- The response confirms slot creation.

#### Update Slot ####

Command: allocator update-slot --slot_id 123 --platform windows --server http://allocator-server

Expected Result:

- The request is sent to http://allocator-server/update_slot with payload { "slot_id": 123, "platform": "windows"}

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

- The request is sent to http://allocator-server/search with payload { "platform": "linux", "tags": ["gpu", "memory"] }

- Matching slots are displayed.

#### List All Allocator Slots ####

Command: allocator list --server http://allocator-server

Expected Result:

- The request is sent to http://allocator-server/list.

- The response contains all available slots known to the server.

### Error Handling Tests ###

TBD
