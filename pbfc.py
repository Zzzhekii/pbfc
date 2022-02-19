#!/bin/python3.10

# Pyhton Brainf**ck compiler
# Made by zzheki

TAPE_LENGTH = 800000

from enum import Enum, auto
class Op(Enum):
    ADD = auto() # add provided value to the value in a cell
    ACP = auto() # add provided value to the cell pointer
    OUT = auto() # output the byte at the cell
    INP = auto() # save input char to the cell
    LBR = auto() # left braket
    RBR = auto() # right braket

def compile_linux_x86_64_nasm(path, tokens):
    # !!!           IMPORTANT           !!!#
    # !!! CELL POINTER IS STORED IN RCX !!!#

    with open(path, 'w') as f:
        # Start the assembly
        f.write('   BITS 64\n')
        f.write('   segment .text\n')
        f.write('   global _start\n')
        f.write('_start:\n')
        
        # Initialize RCX (see notice above)
        f.write('   xor rcx, rcx\n')
        f.write('   mov rcx, tape\n')

        # Compile opcodes
        for token in tokens:
            match token['op']:
                case Op.ADD:
                    f.write('   mov ah, [rcx]\n')
                    if token['value'] < 0:
                        f.write('   sub ah, %d\n' % abs(token['value']))
                    else:
                        f.write('   add ah, %d\n' % token['value'])
                    f.write('   mov [rcx], ah\n')
                case Op.ACP:
                    if token['value'] < 0:
                        f.write('   sub rcx, %d\n' % abs(token['value']))
                    else:
                        f.write('   add rcx, %d\n' % token['value'])
                
                case Op.LBR:
                    f.write('   mov ah, [rcx]\n')
                    f.write('   cmp ah, 0\n')
                    f.write('   je br_%d\n' % token['value'])
                    f.write('br_%d:\n' % token['pos'])
                case Op.RBR:
                    (my_br_pos, matching_br_pos) = token['value']
                    f.write('   mov ah, [rcx]\n')
                    f.write('   cmp ah, 0\n')
                    f.write('   jne br_%d\n' % matching_br_pos)
                    f.write('br_%d:\n' % my_br_pos)
                
                case Op.OUT:
                    f.write('   push rcx\n')
                    f.write('   mov rax, 1\n')
                    f.write('   mov rdi, 1\n')
                    f.write('   mov rsi, rcx\n')
                    f.write('   mov rdx, 1\n')
                    f.write('   syscall\n')
                    f.write('   pop rcx\n')
                case Op.INP:
                    f.write('   push rcx\n')
                    f.write('   mov rax, 0\n')
                    f.write('   mov rdi, 0\n')
                    f.write('   mov rsi, rcx\n')
                    f.write('   mov rdx, 1\n')
                    f.write('   syscall\n')
                    f.write('   pop rcx\n')

                case _:
                    assert False, "Unknown opcode has been provided to the compiler function. This is a bug."

        # Exit linux syscall
        f.write('   mov rax, 60\n')
        f.write('   mov rdi, 0\n')
        f.write('   syscall\n')

        # Make bss section
        f.write('\n   segment .bss\n')
        f.write('tape: resb %d\n' % TAPE_LENGTH)

def parse(source):
    tokens = []

    current_word = None
    current_value = None

    # Stores (current brakets_counter, position in the 'tokens' list)
    # First is needed for the closing braket to jump
    # Second is needed for the left braket to jump
    left_brakets = []
    brakets_counter = 0
    
    i = 0
    while i < len(source):
        match source[i]:
            case '+':
                if current_word != Op.ADD:
                    tokens.append({"op": current_word, "value": current_value, "pos": i})
                    current_word = Op.ADD
                    current_value = 1
                else:
                    current_value += 1

            case '-':
                if current_word != Op.ADD:
                    tokens.append({"op": current_word, "value": current_value, "pos": i})
                    current_word = Op.ADD
                    current_value = -1
                else:
                    current_value -= 1

            case '>':
                if current_word != Op.ACP:
                    tokens.append({"op": current_word, "value": current_value, "pos": i})
                    current_word = Op.ACP
                    current_value = 1
                else:
                    current_value += 1

            case '<':
                if current_word != Op.ACP:
                    tokens.append({"op": current_word, "value": current_value, "pos": i})
                    current_word = Op.ACP
                    current_value = -1
                else:
                    current_value -= 1

            case '[':
                tokens.append({"op": current_word, "value": current_value, "pos": i})
                current_word = Op.LBR
                current_value = None

                tokens_pos = len(tokens)
                current_word = "Hey, closing braket, replace me with nessesary information!"
                left_brakets.append((brakets_counter, tokens_pos))
                brakets_counter +=1

            case ']':
                tokens.append({"op": current_word, "value": current_value, "pos": i})
                current_word = Op.RBR
                current_value = None

                if len(left_brakets) == 0:
                    assert False, "ERROR: No matching left braket found."
                (matching_counter, matching_tokens) = left_brakets.pop()
                tokens[matching_tokens] = {"op": Op.LBR, "value": brakets_counter, "pos": matching_counter}
                current_word = Op.RBR
                current_value = (brakets_counter, matching_counter)
                brakets_counter += 1

            case '.':
                tokens.append({"op": current_word, "value": current_value, "pos": i})
                current_word = Op.OUT
                current_value = None
            case ',':
                tokens.append({"op": current_word, "value": current_value, "pos": i})
                current_word = Op.INP
                current_value = None
        i += 1

    if len(left_brakets) != 0:
        assert False, "ERROR: No matching right bracket found."

    # Append last token
    tokens.append({"op": current_word, "value": current_value, "pos": i})
    # If the length of a file is bigger then 0, parser will always append
    # 'None' token, which must be removed.
    if len(tokens) > 0:
        tokens.pop(0)

    return tokens

def load_from_file(path):
    return open(path, 'r').read()

import sys
if len(sys.argv) != 2:
    print("USAGE: pbfc [path_to_source]")
    exit(1)

source_path = sys.argv[1]
assembly_path = source_path + '.asm'
object_path = source_path + '.o'
exec_path = 'a.out'

source = load_from_file(source_path)
tokens = parse(source)
compile_linux_x86_64_nasm(assembly_path, tokens)

import subprocess
print("INFO: Building x86_64 object file using nasm...")
subprocess.run(["nasm", "-felf64", assembly_path, "-o", object_path])
print("INFO: Linking binary using ld...")
subprocess.run(["ld", object_path, "-o", exec_path])

print("INFO: Cleaning up compilation garbage...")
subprocess.run(["rm", "-f", object_path, assembly_path])
