global main
extern MessageBoxA

section .data
    title db "Helllooo", 0
    text  db "Hello, world!", 0

section .text
main:
    sub rsp, 40          ; Win64 shadow space + alignment
    xor rcx, rcx         ; hWnd = NULL
    lea rdx, [rel text]  ; lpText
    lea r8,  [rel title] ; lpCaption
    xor r9d, r9d         ; uType = MB_OK
    call MessageBoxA
    add rsp, 40
    xor eax, eax
    ret