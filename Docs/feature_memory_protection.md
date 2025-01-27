# Memory Protections

The Memory Protection Settings add safety functionality such as page and pool guards, stack guard and 
null pointer detection. The settings are split between MM and DXE environments for modularity.
The target audience for this doc has intermediate knowledge of systems programming and working with EDK II.

## Useful Terms and Concepts (Linked in Text if Used)

### Option ROM
A driver that interfaces between BIOS services and hardware.

### Boot Strap Processor (BSP)
The bootstrap processor (BSP) handles initialization procedures for the system as a whole. These procedures include 
checking the integrity of memory, identifying properties of the system logic and starting the remaining processors.

### Application Processor (AP)
A system processor used for processing signals in embedded systems.

### Boot Loader
Places into working memory the required resources for runtime.

### Read Only (RO)
A bit used to mark certain areas of memory as non-writeable.

### No eXecute/eXecute Never/eXecute Disable Attribute (NX/XN/XD)
A bit used to mark certain areas of memory as non-executable. NX is a term usually used by AMD whereas 
XD is used by Intel and XN by Qualcomm. The only difference between NX, XD, and XN are their names.

### Physical/Page Address Extension
A memory management feature in x86 architecture which defines a page table heirarchy with table entries of 64 bits 
allowing CPUs to directly address physical address spaces larger than 32 bits (4 GB).

### Model-specific Register (MSR)
Any of the various control registers in the x86 instruction set used for debugging, execution tracing, performance 
monitoring and CPU feature toggling.

### EndOfDxe
The point at which the driver execution (DXE) phase has ended and all drivers provided by the mfg (as part of the 
built-in ROM or loaded directly from another driver) should be loaded now, or else they have failed their dependency 
expressions. UEFI drivers and OpROMs have not yet been started.

### Page Fault Exception (#PF)
An exception raised when EDK II code attempts to access memory which is not present or settings for the page make 
it invisible.

### Task State Segment (TSS)
A structure on x86-based CPUs which holds information about a unit of execution.

### Cpu Context Dump
A routine which prints to serial out the module in which the fault occurred, type of fault which occurred and 
contents of each CPU register.

### Memory Management Unit (MMU)
Hardware on a CPU which is primarily responsible for translating Virtual Memory addresses to Physical ones.

### Translation Lookaside Buffer (TLB)
A memory cache which is part of the CPUs [MMU](#memory-management-unit-mmu) and stores translations of Virtual 
Memory to Physical Memory. The addresses stored in the TLB are dictated by some algorithm intended to decrease 
amount of memory accesses for which the address translation is outside the TLB. 

### Nonstop Mode
In the case of Non-Stop mode being enabled for either [HeapGuardPolicy](#heapguardpolicy) or 
[NullPointerDetectionPolicy](#nullpointerdetectionpolicy), two exception handlers are registered. 
The first handler runs whenever the heap guard or null pointer page absences trigger a 
[#PF](#page-fault-exception-pf). If Non-Stop mode is enabled for this type of 
[#PF](#page-fault-exception-pf), the absent page(s) are temporarily set to be present and a 
[Cpu Context Dump](#cpu-context-dump) is run after which the second exception handler registered 
(the debug handler) is run. 
The debug handler sets the page to be present and clears the [TLB](#translation-lookaside-buffer-tlb) to 
remove the current translation for the page which caused the [#PF](#page-fault-exception-pf). Once these 
two handlers have run, code execution continues.

## Null Pointer Detection

### Summary
Pages are allocated in 4KB chunks. This policy marks the first 4KB page to be not present to
detect NULL pointer references in both/either UEFI and SMM.

### DXE Implementation Details

In PEI phase, Project Mu will set page zero (on x64, what a NULL pointer translates to) to be allocated in the
resource descriptor HOB but will not alter the present bit. DXE phase uses the memory descriptor HOB to create the
memory map, so we are safe to set page zero as read protected in DXE phase. Because page zero is not read protected
prior to DXE phase, any NULL accesses prior to this point will not cause a [#PF](#page-fault-exception-pf).

If DisableEndOfDxe or DisableReadyToBoot set, NULL pointer detection will be disabled for UEFI
once execution reaches the relevant phase. If both are enabled, NULL pointer
detection will be disabled at the earliest
event (EndOfDxe). This is a workaround in order to skip unfixable NULL pointer access issues
detected in legacy [Option ROM](#option-rom) or [boot loaders](#boot-loader).

**Available Settings:**
  
- UefiNullDetection  - Enable NULL pointer detection for DXE
- DisableEndOfDxe    - Disable NULL pointer detection just after [EndOfDxe](#endofdxe)
- DisableReadyToBoot - Disable NULL pointer detection just after ReadyToBoot

### MM Implementation Details
If NullPointerDetectionPolicy is TRUE, the present bit for the NULL page is cleared for SMM address space in the
[SMM initialization driver](https://github.com/tianocore/edk2/tree/master/UefiCpuPkg/PiSmmCpuDxeSmm).

## Image Protection Policy

### A note on SMM
In UEFI/PI firmware, the SMM image is a normal PE/COFF image loaded by the SmmCore. However, image protection in 
SMM is completely separate from this policy and is controlled by the static variable 
[mMemoryProtectionAttribute](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/PiSmmCore/MemoryAttributesTable.c)

### Summary

This policy enables an image to be protected by DxeCore if it is page-aligned, meaning
the code sections become read-only, and the data sections become non-executable. **This policy is only**
**available in the DXE environment.**
.

### DXE Implementation Details

There are 3 environment assumptions for enabling image protection:

1. The PE code section and data sections are not merged. If those 2 sections are merged, a 
[#PF](#page-fault-exception-(aka-#pf)) exception might be generated because the CPU may try to write read-only 
data in data section or execute a [NX](#no-executeexecute-neverexecute-disable-attribute-nxxnxd) instruction
in the code section.

2. The PE image can be protected if it is page aligned. This feature should **NOT** be used if there is any 
self-modifying code in the code region.

3. A platform may not disable the [NX](#no-executeexecute-neverexecute-disable-attribute-nxxnxd)) in the DXE phase.
If a platform disables the [NX](#no-executeexecute-neverexecute-disable-attribute-nxxnxd)) in the DXE
phase, the x86 page table will become invalid because the
[NX](#no-executeexecute-neverexecute-disable-attribute-nxxnxd)) bit in the page table becomes a RESERVED bit and a
[#PF](#page-fault-exception-pf) exception will be generated. If a platform wants to disable the
[XD](#no-executeexecute-neverexecute-disable-attribute-nxxnxd)) bit, it must happen in the PEI phase.

**Loading**

**NOTE:** If an image is loaded before CPU_ARCH protocol is ready, the DXE core skips the setting until
the CPU_ARCH notify function
[MemoryProtectionCpuArchProtocolNotify()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Misc/MemoryProtection.c) 
is invoked at which point the protection settings are applied to the image. When the ExitBootServices event is raised, 
[MemoryProtectionExitBootServicesCallback()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Misc/MemoryProtection.c) 
is invoked to unprotect runtime images to accomodate virtual address mapping.

The Project Mu DXE core image services load an image via
CoreLoadPeImage()
which allocated pages for the image of a memory type based on the image subsystem type:

- EFI_IMAGE_SUBSYSTEM_EFI_APPLICATION &rarr; EfiLoaderCode
- EFI_IMAGE_SUBSYSTEM_EFI_BOOT_SERVICE_DRIVER &rarr; EfiBootServicesCode
- EFI_IMAGE_SUBSYSTEM_EFI_RUNTIME_DRIVER &rarr; EfiRuntimeServicesCode
- EFI_IMAGE_SUBSYSTEM_SAL_RUNTIME_DRIVER &rarr; EfiRuntimeServicesCode

If the image does not indicate support via the NXCOMPAT DLL flag, we will cease to automatically set the
[NX](#no-executeexecute-neverexecute-disable-attribute-nxxnxd))
attribute on allocations of memory of type EfiLoaderCode, EfiBootServicesCode, and EfiRuntimeServicesCode. Using
the BlockImagesWithoutNxFlag will prevent images which don't support NXCOMPAT from loading. Once the image is loaded
and relocations are complete, the entire image region will be marked as
read-only
and [NX](#no-executeexecute-neverexecute-disable-attribute-nxxnxd)) for increased security.

After loading the image, Project Mu DXE core image services calls
[ProtectUefiImageMu()](https://github.com/microsoft/mu_basecore/blob/release/202202/MdeModulePkg/Core/Dxe/Misc/MemoryProtection.c)
which handles setting the appropriate attributes for the code and data sections. The function calls
[GetUefiImageProtectionPolicy()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Misc/MemoryProtection.c) 
to check the image source and protection policy (FromUnknown, FromFv), and parses PE alignment. If all checks pass, 
[SetUefiImageProtectionAttributes()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Misc/MemoryProtection.c) 
calls 
[SetUefiImageMemoryAttributes()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Misc/MemoryProtection.c). 
Finally, gCpu->[CpuSetMemoryAttributes()](https://github.com/tianocore/edk2/blob/master/UefiCpuPkg/CpuDxe/CpuDxe.c) 
updates attributes to remove [NX](#no-executeexecute-neverexecute-disable-attribute-nxxnxd))
from code regions and remove [RO](#read-only-ro) from data regions.

**Unloading**

The Project Mu DXE core image services calls 
[UnprotectUefiImage()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Image/Image.c) on image 
unload which calls 
[SetUefiImageMemoryAttributes()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Misc/MemoryProtection.c). 
with an empty attribute access mask to clear the attributes.

### Overhead
**O(n)** time and space overhead. Each image requires a 6K attributes header, so if there are **n** images the 
space overhead will be 6K\*n and thus O(n) time to populate the headers. In most cases the number of 
images is in the order of hundreds making this feature relatively inexpensive.

Because this feature requires aligned images, there will likely be an increased size footprint for each image.

**Available Settings:**
  
- FromUnknown                  - Protect images from unknown devices
- FromFv                       - Protect images from firmware volume
- RaiseErrorIfProtectionFails  - If set, images which fail to be protected will be unloaded. This excludes failure
because CPU Arch Protocol has not yet been installed
- BlockImagesWithoutNxFlag     - If set, attempts to load images of subsystem type EFI_APPLICATION which do not support
the NX_COMPAT DLL flag will be blocked
InstallMemoryAttributeProtocol - If set, the memory attribute protocol will be installed. This protocol enables
the setting and getting of page attributes from outside of CpuDxe.

## NX Memory Protection Policy

### Summary

This policy sets the [NX](#no-executeexecute-neverexecute-disable-attribute-nxxnxd)) attribute to memory of the
associated memory type. **This setting does not apply to SMM.**

Every active memory type will be mapped as non-executable.
**Note** that a portion of memory will only be marked as
non-executable once gEfiCpuArchProtocolGuid has been published. **Also note** that in order
to enable Data Execution Protection, the operating system needs to set the 
[IA32_EFER.NXE](#no-executeexecute-neverexecute-disable-attribute-nxxnxd)) bit in the IA32_EFER
[MSR](#model-specific-register-msr), 
and then set the [XD](#no-executeexecute-neverexecute-disable-attribute-nxxnxd)) bit in the CPU
[PAE](#physicalpage-address-extension) 
page table.

This policy is consumed by DXE Core through 
[ApplyMemoryProtectionPolicy()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Misc/MemoryProtection.c) 
which sets the NX attribute for allocated memory using the CPU_ARCH protocol (hence why gEfiCpuArchProtocolGuid 
must be published for this to work). Once gEfiCpuArchProtocolGuid is published, 
[MemoryProtectionCpuArchProtocolNotify()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Misc/MemoryProtection.c) 
is called and 
[InitializeDxeNxMemoryProtectionPolicy()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Misc/MemoryProtection.c) 
will get the current memory map and setup [NX](#no-executeexecute-neverexecute-disable-attribute-nxxnxd))
protection. Just prior to applying protection, memory mapped regions will be "merged" such that adjacent
entries with the same memory protection policy will become one entry.

### Overhead
**O(n)** time where n is the number of memory mapped regions. The number of actual set bits beyond one is 
inconsequential because every memory region must be checked if at least one bit is set. There is no extra space 
complexity due to using the already present [NX](#no-executeexecute-neverexecute-disable-attribute-nxxnxd)) bit.

**Available Settings:**

- EfiReservedMemoryType
- EfiLoaderCode
- EfiLoaderData
- EfiBootServicesCode
- EfiBootServicesData
- EfiRuntimeServicesCode
- EfiRuntimeServicesData
- EfiConventionalMemory
- EfiUnusableMemory
- EfiACPIReclaimMemory
- EfiACPIMemoryNVS
- EfiMemoryMappedIO
- EfiMemoryMappedIOPortSpace
- EfiPalCode
- EfiPersistentMemory
- OEMReserved
- OSReserved

## Page Guards

### Summary

The HeapGuardPageType policy implements guard pages on the specified memory types to detect heap overflow. If a bit
is set, a guard page will be added before and after the
corresponding type of page allocated if there's enough free pages for all of them. On the 
implementation side, the tail and guard pages are simply set to NOT PRESENT so any attempt 
to access them will cause a [#PF](#page-fault-exception-pf).

### DXE Implementation Details
I'll cover the DXE implementations only because the **MM specifics are similar.**
Whenever there is a call to allocate a page, if the 
[IsPageTypeToGuard()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Mem/HeapGuard.c) call 
returns TRUE, 
[CoreInternalAllocatePages()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Mem/Page.c) uses 
[CoreConvertPagesWithGuard()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Mem/HeapGuard.c) 
to allocate 2 extra pages and calls 
[SetGuardForMemory()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Mem/HeapGuard.c) 
which calls [SetGuardPage()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Mem/HeapGuard.c) 
twice to set the guard page before and after. 
[SetGuardPage()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Mem/HeapGuard.c) calls 
[CpuSetMemoryAttributes()](https://github.com/tianocore/edk2/blob/master/UefiCpuPkg/CpuDxe/CpuDxe.c) to clear the 
PRESENT flag. Finally, 
[SetGuardForMemory()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Mem/HeapGuard.c) 
calls [SetGuardedMemoryBits()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Mem/HeapGuard.c) 
to mark the memory range as guarded. This bitmask will be checked in 
[UnsetGuardForMemory()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Mem/HeapGuard.c) when 
[CoreInternalFreePages()](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Core/Dxe/Mem/Page.c) is called.

Pages can be freed partially while maintaining guard structure as shown in the following figure.

![Heap Guard Image](guardpages_mu.PNG)

### Overhead
**O(n)** time where n is the number of page allocations/frees. Because there are 2 extra pages allocated for 
every call to AllocatePages(), **O(n)** space is also required.

**Available Settings for DXE and MM:**

- EfiReservedMemoryType
- EfiLoaderCode
- EfiLoaderData
- EfiBootServicesCode
- EfiBootServicesData
- EfiRuntimeServicesCode
- EfiRuntimeServicesData
- EfiConventionalMemory
- EfiUnusableMemory
- EfiACPIReclaimMemory
- EfiACPIMemoryNVS
- EfiMemoryMappedIO
- EfiMemoryMappedIOPortSpace
- EfiPalCode
- EfiPersistentMemory
- OEMReserved
- OSReserved

## Pool Guards

### Summary

The HeapGuardPoolType policy is essentially the same as HeapGuardPageType policy.
For each active memory type, a head guard page and 
a tail guard page will be added just before and after the portion of memory which the 
allocated pool occupies. For brevity, I will not trace the calls here, but it's essentially the same as 
above. The only added complexity comes when the allocated pool is not a 
multiple of the size of a page. In this case, the pool must align with either the head or tail guard page, meaning
either overflow or underflow can be caught but not both. The head/tail alignment is set in
[HeapGuardPolicy](#heapguardpolicy) - look there for additional details.

### Overhead
Same as above: **O(n)** time and space for same reasons as [HeapGuardPageType](#heapguardpagetype). **Note** 
that this functionality requires creating guard pages, meaning that for n allocations, 4k \* (n + 1) (assuming 
each of the n pools is adjacent to another pool) additional space is required.

**Available Settings for DXE and MM:**

- EfiReservedMemoryType
- EfiLoaderCode
- EfiLoaderData
- EfiBootServicesCode
- EfiBootServicesData
- EfiRuntimeServicesCode
- EfiRuntimeServicesData
- EfiConventionalMemory
- EfiUnusableMemory
- EfiACPIReclaimMemory
- EfiACPIMemoryNVS
- EfiMemoryMappedIO
- EfiMemoryMappedIOPortSpace
- EfiPalCode
- EfiPersistentMemory
- OEMReserved
- OSReserved

## HeapGuardPolicy

### Summary

While the above two policies ([Pool Guards](#pool-guards) and 
[Page Guards](#page-guards)) act as a 
switch for each protectable memory type, this policy is an enable/disable switch for those 
two policies (ex. if UefiPageGuard is unset, page guards in DXE are inactive regardless
of the [Page Guard](#page-guards) settings).

The only aspect of this policy which should be elaborated upon is Direction. Direction dictates whether
an allocated pool which does not fit perfectly into a multiple of pages is aligned to the head or tail guard.
The following Figure shows examples of the two:

![Heap Guard Pool Alignment Image](alignment_mu.PNG)

### Overhead
Overhead is same as [Page Guards](#page-guards) and [Pool Guards](#pool-guards).

**DXE Available Settings:**

- UefiPageGuard - Enable UEFI page guard
- UefiPoolGuard - Enable UEFI pool guard
- UefiFreedMemoryGuard - Enable Use-After-Free memory detection
- Direction - Specifies the direction of Guard Page for Pool Guard. If 0, the returned
pool is near the tail guard page. If 1, the returned pool is near the head guard page. The
default value for this is 0

**MM Available Settings:**
- SmmPageGuard - Enable SMM page guard
- SmmPoolGuard - Enable SMM pool guard
- Direction - Specifies the direction of Guard Page for Pool Guard. If 0, the returned
pool is near the tail guard page. If 1, the returned pool is near the head guard page. The
default value for this is 0

## CPU Stack Guard

The CpuStackGuard policy indicates if UEFI Stack Guard will be enabled. 

### A note on SMM
An equivalent SMM stack guard feature is contained in 
[PiSmmCpuDxeSmm](https://github.com/tianocore/edk2/tree/master/UefiCpuPkg/PiSmmCpuDxeSmm) and is not dictated
by this policy.

### Implementation Details
The stack guards add two additional pages to the bottom of the stack(s). The first page is simply the guard page 
which is set to not present. However, a complexity arises when a page fault occurs due to the guard page being 
accessed. In this case, the current stack address is invalid and so it is not possible to push the error code and 
architecture status onto the current stack. For this reason, there is a special "Exception Stack" (described as a 
"Known Good Stack" in the codebase) which is the second page placed at the bottom of the stack. This page is 
reserved for use by the exception handler and ensures that a valid stack is always present when an exception occurs 
for error reporting.

**Note** that the UEFI
stack protection starts in DxeIpl, because the region is fixed, and requires 
[PcdDxeIplBuildPageTables](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/MdeModulePkg.dec) to be 
TRUE. In Project Mu, we have hard-coded CpuStackGuard to be TRUE in PEI phase, so we always set up a switch
stack, clear the PRESENT bit in the page table for the guard page of 
the Boot Strap Processor stack, and build the page tables. However, the stack switch handlers will still only be
installed in DXE phase if CpuStackGuard is TRUE.
The guard page of the Application Processor stack is initialized in CpuDxe driver by using the DXE service 
[CpuSetMemoryAttributes()](https://github.com/tianocore/edk2/blob/master/UefiCpuPkg/CpuDxe/CpuDxe.c). 

### Overhead
**O(1)** time and space.

**Setting:**

- If TRUE, UEFI Stack Guard will be enabled.

## How to Set the Memory Protection Policy

For DXE settings, add the following to the platform DSC file:

```C
[LibraryClasses.Common.DXE_DRIVER, LibraryClasses.Common.DXE_CORE, LibraryClasses.Common.UEFI_APPLICATION]
  DxeMemoryProtectionHobLib|MdeModulePkg/Library/MemoryProtectionHobLib/DxeMemoryProtectionHobLib.inf
```

For MM settings, add the following to the platform DSC file if the platform utilizes SMM:

```C
[LibraryClasses.common.SMM_CORE, LibraryClasses.common.DXE_SMM_DRIVER]
  MmMemoryProtectionHobLib|MdeModulePkg/Library/MemoryProtectionHobLib/SmmMemoryProtectionHobLib.inf
```

**or** the following if the platform utilizes Standalone MM:

```C
[LibraryClasses.common.MM_CORE_STANDALONE, LibraryClasses.common.MM_STANDALONE]
  MmMemoryProtectionHobLib|MdeModulePkg/Library/MemoryProtectionHobLib/StandaloneMmMemoryProtectionHobLib.inf
```

Create the HOB entry in any PEI module by adding the include:

```C
#include <Guid/DxeMemoryProtectionSettings.h>
#include <Guid/MmMemoryProtectionSettings.h>
```

and somewhere within the code doing something like:

```C
  DXE_MEMORY_PROTECTION_SETTINGS  DxeSettings;
  MM_MEMORY_PROTECTION_SETTINGS   MmSettings;

  DxeSettings = (DXE_MEMORY_PROTECTION_SETTINGS)DXE_MEMORY_PROTECTION_SETTINGS_DEBUG;
  MmSettings  = (MM_MEMORY_PROTECTION_SETTINGS)MM_MEMORY_PROTECTION_SETTINGS_DEBUG;

  BuildGuidDataHob (
    &gDxeMemoryProtectionSettingsGuid,
    &DxeSettings,
    sizeof (DxeSettings)
    );

  BuildGuidDataHob (
    &gMmMemoryProtectionSettingsGuid,
    &MmSettings,
    sizeof (MmSettings)
    );
```

This will also require you to add gMemoryProtectionSettingsGuid under the Guids section in the relevant INF.

If you want to deviate from one of the settings profile definitions in DxeMemoryProtectionSettings.h
and/or MmMemoryProtectionSettings, it is recommended
that you start with the one which most closely aligns with your desired settings and update from there in a
manner similar to below:

```C
  MmSettings.HeapGuardPolicy.Fields.MmPageGuard                    = 0;
  MmSettings.HeapGuardPolicy.Fields.MmPoolGuard                    = 0;
  DxeSettings.ImageProtectionPolicy.Fields.ProtectImageFromUnknown = 1;
```

before building the HOB.
