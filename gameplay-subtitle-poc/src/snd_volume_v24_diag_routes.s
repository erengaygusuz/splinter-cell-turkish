.intel_syntax noprefix
.data
.p2align 2
_v24_target_140:
    .long 0
_v24_target_146:
    .long 0
_v24_target_240:
    .long 0

.text

.globl _probe_volume_140
.def _probe_volume_140; .scl 2; .type 32; .endef
_probe_volume_140:
    pushfd
    pushad
    lea eax, [esp + 40]
    push eax
    push 140
    call _v24_volume_route
    add esp, 8
    mov dword ptr [_v24_target_140], eax
    popad
    popfd
    jmp dword ptr [_v24_target_140]

.globl _probe_volume_146
.def _probe_volume_146; .scl 2; .type 32; .endef
_probe_volume_146:
    pushfd
    pushad
    lea eax, [esp + 40]
    push eax
    push 146
    call _v24_volume_route
    add esp, 8
    mov dword ptr [_v24_target_146], eax
    popad
    popfd
    jmp dword ptr [_v24_target_146]

.globl _probe_volume_240
.def _probe_volume_240; .scl 2; .type 32; .endef
_probe_volume_240:
    pushfd
    pushad
    lea eax, [esp + 40]
    push eax
    push 240
    call _v24_volume_route
    add esp, 8
    mov dword ptr [_v24_target_240], eax
    popad
    popfd
    jmp dword ptr [_v24_target_240]
