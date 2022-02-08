#!/bin/python3

# Pyhton Brainf**ck compiler
# Made by zzheki

TAPE_LENGTH = 800000

# Go-like enumerations
# Set new=True when you create a new enumeration
iota_counter = 0
def iota(new=False):
    global iota_counter
    iota_counter += 1
    if new:
        iota_counter = 0
    return iota_counter

OP_ADD = iota(new=True)    # add provided value to the value in a cell
OP_ACP = iota()            # add provided value to the cell pointer
OP_OUT = iota()            # output the byte at the cell
OP_INP = iota()            # save input char to the cell
OP_LBR = iota()            # left braket
OP_RBR = iota()            # right braket

def compile(path, tokens):
    # !!! IMPORTANT NOTICE:             !!!#
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
            if token['op'] == OP_ADD:
                f.write('   xor rax, rax\n')
                f.write('   mov ah, [rcx]\n')
                if token['value'] < 0:
                    f.write('   sub ah, %d\n' % abs(token['value']))
                else:
                    f.write('   add ah, %d\n' % token['value'])
                f.write('   mov [rcx], ah\n')
            elif token['op'] == OP_ACP:
                if token['value'] < 0:
                    f.write('   sub rcx, %d\n' % abs(token['value']))
                else:
                    f.write('   add rcx, %d\n' % token['value'])
            
            elif token['op'] == OP_LBR:
                f.write('   xor rax, rax\n')
                f.write('   mov ah, [rcx]\n')
                f.write('   cmp ah, 0\n')
                f.write('   je br_%d\n' % token['value'])
                f.write('br_%d:\n' % token['pos'])
            elif token['op'] == OP_RBR:
                (my_br_pos, matching_br_pos) = token['value']
                f.write('   xor rax, rax\n')
                f.write('   mov ah, [rcx]\n')
                f.write('   cmp ah, 0\n')
                f.write('   jne br_%d\n' % matching_br_pos)
                f.write('br_%d:\n' % my_br_pos)
            
            elif token['op'] == OP_OUT:
                f.write('   push rcx\n')
                f.write('   mov rax, 1\n')
                f.write('   mov rdi, 1\n')
                f.write('   mov rsi, rcx\n')
                f.write('   mov rdx, 1\n')
                f.write('   syscall\n')
                f.write('   pop rcx\n')
            elif token['op'] == OP_INP:
                f.write('   push rcx\n')
                f.write('   mov rax, 0\n')
                f.write('   mov rdi, 0\n')
                f.write('   mov rsi, rcx\n')
                f.write('   mov rdx, 1\n')
                f.write('   syscall\n')
                f.write('   pop rcx\n')

            else:
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
        if source[i] == '+':
            if current_word != OP_ADD:
                tokens.append({"op": current_word, "value": current_value, "pos": i})
                current_word = OP_ADD
                current_value = 1
            else:
                current_value += 1

        elif source[i] == '-':
            if current_word != OP_ADD:
                tokens.append({"op": current_word, "value": current_value, "pos": i})
                current_word = OP_ADD
                current_value = -1
            else:
                current_value -= 1

        elif source[i] == '>':
            if current_word != OP_ACP:
                tokens.append({"op": current_word, "value": current_value, "pos": i})
                current_word = OP_ACP
                current_value = 1
            else:
                current_value += 1

        elif source[i] == '<':
            if current_word != OP_ACP:
                tokens.append({"op": current_word, "value": current_value, "pos": i})
                current_word = OP_ACP
                current_value = -1
            else:
                current_value -= 1

        elif source[i] == '[':
            tokens.append({"op": current_word, "value": current_value, "pos": i})
            current_word = OP_LBR
            current_value = None

            tokens_pos = len(tokens)
            current_word = "Hey, closing braket, replace me with needed information!"
            left_brakets.append((brakets_counter, tokens_pos))
            brakets_counter +=1

        elif source[i] == ']':
            tokens.append({"op": current_word, "value": current_value, "pos": i})
            current_word = OP_RBR
            current_value = None

            if len(left_brakets) == 0:
                assert False, "ERROR: No matching left braket found."
            (matching_counter, matching_tokens) = left_brakets.pop()
            tokens[matching_tokens] = {"op": OP_LBR, "value": brakets_counter, "pos": matching_counter}
            current_word = OP_RBR
            current_value = (brakets_counter, matching_counter)
            brakets_counter += 1

        elif source[i] == '.':
            tokens.append({"op": current_word, "value": current_value, "pos": i})
            current_word = OP_OUT
            current_value = None
        elif source[i] == ',':
            tokens.append({"op": current_word, "value": current_value, "pos": i})
            current_word = OP_INP
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
compile(assembly_path, tokens)

import subprocess
print("INFO: Building x86_64 object file with nasm...")
subprocess.run(["nasm", "-felf64", assembly_path, "-o", object_path])
print("INFO: Linking binary with ld...")
subprocess.run(["ld", object_path, "-o", exec_path])

