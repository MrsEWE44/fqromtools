#!/usr/bin/env python3
import struct
import hashlib
import bz2
import sys
import argparse
import bsdiff4
import io
import os
try:
    import lzma
except ImportError:
    from backports import lzma

import update_metadata_pb2 as um

flatten = lambda l: [item for sublist in l for item in sublist]

def u32(x):
    return struct.unpack('>I', x)[0]

def u64(x):
    return struct.unpack('>Q', x)[0]

def verify_contiguous(exts):
    blocks = 0

    for ext in exts:
        if ext.start_block != blocks:
            return False

        blocks += ext.num_blocks

    return True

def data_for_op(op,out_file,old_file,args,data_offset,block_size):
    payloadfile=open(args.inputfile,'rb')
    payloadfile.seek(data_offset + op.data_offset)
    data = payloadfile.read(op.data_length)

    # assert hashlib.sha256(data).digest() == op.data_sha256_hash, 'operation data hash mismatch'

    if op.type == op.REPLACE_XZ:
        dec = lzma.LZMADecompressor()
        data = dec.decompress(data)
        out_file.seek(op.dst_extents[0].start_block*block_size)
        out_file.write(data)
    elif op.type == op.REPLACE_BZ:
        dec = bz2.BZ2Decompressor()
        data = dec.decompress(data)
        out_file.seek(op.dst_extents[0].start_block*block_size)
        out_file.write(data)
    elif op.type == op.REPLACE:
        out_file.seek(op.dst_extents[0].start_block*block_size)
        out_file.write(data)
    elif op.type == op.SOURCE_COPY:
        if not args.diff:
            print ("SOURCE_COPY supported only for differential OTA")
            sys.exit(-2)
        out_file.seek(op.dst_extents[0].start_block*block_size)
        for ext in op.src_extents:
            old_file.seek(ext.start_block*block_size)
            data = old_file.read(ext.num_blocks*block_size)
            out_file.write(data)
    elif op.type == op.SOURCE_BSDIFF:
        if not args.diff:
            print ("SOURCE_BSDIFF supported only for differential OTA")
            sys.exit(-3)
        out_file.seek(op.dst_extents[0].start_block*block_size)
        tmp_buff = io.BytesIO()
        for ext in op.src_extents:
            old_file.seek(ext.start_block*block_size)
            old_data = old_file.read(ext.num_blocks*block_size)
            tmp_buff.write(old_data)
        tmp_buff.seek(0)
        old_data = tmp_buff.read()
        tmp_buff.seek(0)
        tmp_buff.write(bsdiff4.patch(old_data, data))
        n = 0;
        tmp_buff.seek(0)
        for ext in op.dst_extents:
            tmp_buff.seek(n*block_size)
            n += ext.num_blocks
            data = tmp_buff.read(ext.num_blocks*block_size)
            out_file.seek(ext.start_block*block_size)
            out_file.write(data)
    elif op.type == op.ZERO:
        for ext in op.dst_extents:
            out_file.seek(ext.start_block*block_size)
            out_file.write(b'\x00' * ext.num_blocks*block_size)
    else:
        print ("Unsupported type = %d" % op.type)
        sys.exit(-1)

    return data

def dump_part(part,args,data_offset,block_size):
    sys.stdout.write("Processing %s partition" % part.partition_name)
    sys.stdout.flush()

    out_file = open('%s/%s.img' % (args.out, part.partition_name), 'wb')
    h = hashlib.sha256()

    if args.diff:
        old_file = open('%s/%s.img' % (args.old, part.partition_name), 'rb')
    else:
        old_file = None

    for op in part.operations:
        data = data_for_op(op,out_file,old_file,args,data_offset,block_size)
        sys.stdout.write(".")
        sys.stdout.flush()

    print("Done")
