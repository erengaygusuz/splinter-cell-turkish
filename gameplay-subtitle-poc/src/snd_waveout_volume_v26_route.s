.intel_syntax noprefix
.data
.p2align 2
_v26_target_240:
    .long 0

.text

.globl _probe_volume_v26_240
.def _probe_volume_v26_240; .scl 2; .type 32; .endef
_probe_volume_v26_240:
    pushfd
    pushad
    lea eax, [esp + 40]
    push eax
    push 240
    call _v26_volume_route
    add esp, 8
    mov dword ptr [_v26_target_240], eax
    popad
    popfd
    jmp dword ptr [_v26_target_240]
