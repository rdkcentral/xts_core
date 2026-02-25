# XTS Core Test Specification #


This document defines the expected behavior of XTS core across different use cases, focusing on the new alias-only method of operation. All test case execution and command orchestration must be performed via registered aliases. Direct execution or discovery of .xts files in the current directory is no longer supported.

The test specification covers the following scenarios:

- Usage with aliases referencing structured and unstructured .xts files
- Operation when no alias is present


### Handling of Aliases and .xts Files ###

#### Structured .xts File via Alias ####

Preconditions: A valid .xts file with structured data is registered as an alias (e.g., `xts --alias /path/to/yourfile.xts --name myalias`).

Expected Behavior:

- XTS should correctly parse and load the .xts file via the alias.
- Execution should proceed without errors when invoked as `xts myalias <group> <command>`.
- The expected test cases should run and produce correct results.

#### Unstructured .xts File via Alias ####

Preconditions: A malformed or incorrectly structured .xts file is registered as an alias.

Expected Behavior:

- XTS should detect the malformed structure and log an appropriate error when the alias is used.
- Execution should fail gracefully without crashes.

#### No Alias Registered ####

Preconditions: No alias is registered for the desired .xts file.

Expected Behavior:

- XTS should log a clear error message indicating that the alias is missing.
- Execution of test cases should not proceed.
- AllocatorClient commands should remain functional and usable.

#### Multiple Aliases Registered ####

Preconditions: More than one alias is registered, each referencing a different .xts file.

Expected Behavior:

- XTS should allow the user to select the desired alias for execution.
- The user should be shown how to run each alias individually using the appropriate command (e.g., `xts myalias1 ...`, `xts myalias2 ...`).


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
