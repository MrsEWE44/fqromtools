#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import sys
import os
import update_metadata_pb2 as um
import img2sdat as img2sd
import sdat2img as sdat2im
import payload_dumper as payloaddumper

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='fqromtools')
    parser.add_argument('--inputfile',help='payload file name')
    parser.add_argument('--tool', required=True ,help='use tool payload/img2sdat/sdat2img')
    parser.add_argument('--out', default='output',help='output directory (defaul: output)')
    parser.add_argument('--diff',action='store_true',help='extract differential OTA, you need put original images to old dir')
    parser.add_argument('--old', default='old',help='directory with original images for differential OTA (defaul: old)')
    parser.add_argument('--images', default="",help='images to extract (default: empty)')
    parser.add_argument('--androidversion', help='transfer list androidversion number, will be asked by default - more info on xda thread)')
    parser.add_argument('--prefix', help='name of image (prefix.new.dat)')
    parser.add_argument('--transferlist', help='transfer list file')
    args = parser.parse_args()
    if args.tool == "payload":
       #Check for --out directory exists
        if not os.path.exists(args.out):
            os.makedirs(args.out)
        payloadfile=open(args.inputfile,'rb')
        magic = payloadfile.read(4)
        assert magic == b'CrAU'
        file_format_version = payloaddumper.u64(payloadfile.read(8))
        assert file_format_version == 2

        manifest_size = payloaddumper.u64(payloadfile.read(8))

        metadata_signature_size = 0

        if file_format_version > 1:
            metadata_signature_size = payloaddumper.u32(payloadfile.read(4))

        manifest = payloadfile.read(manifest_size)
        metadata_signature = payloadfile.read(metadata_signature_size)

        data_offset = payloadfile.tell()

        dam = um.DeltaArchiveManifest()
        dam.ParseFromString(manifest)
        block_size = dam.block_size

        if args.images == "":
            for part in dam.partitions:
                payloaddumper.dump_part(part,args,data_offset,block_size)
        else:
            images = args.images.split(",")
            for image in images:
                partition = [part for part in dam.partitions if part.partition_name == image]
                if partition:
                    payloaddumper.dump_part(partition[0],args,data_offset,block_size)
                else:
                    sys.stderr.write("Partition %s not found in payload!\n" % image)
    elif args.tool == "img2sdat":
        INPUT_IMAGE = args.inputfile
        if args.out:
            OUTDIR = args.out
        else:
            OUTDIR = '.'

        if args.androidversion:
            VERSION = int(args.androidversion)
        else:
            VERSION = None
        
        if args.prefix:
            PREFIX = args.prefix
        else:
            PREFIX = 'system'
        
        img2sd.main(INPUT_IMAGE, OUTDIR, VERSION, PREFIX)
    elif args.tool == "sdat2img":
        try:
            TRANSFER_LIST_FILE = args.transferlist
            NEW_DATA_FILE = args.inputfile
        except IndexError:
            print('\nUsage: sdat2img.py <transfer_list> <system_new_file> [system_img]\n')
            print('    <transfer_list>: transfer list file')
            print('    <system_new_file>: system new dat file')
            print('    [system_img]: output system image\n\n')
            print('Visit xda thread for more information.\n')
            try:
                input = raw_input
            except NameError: pass
            print('exit...')
            sys.exit()

        try:
            OUTPUT_IMAGE_FILE = args.out
        except IndexError:
            OUTPUT_IMAGE_FILE = 'system.img'

        sdat2im.main(TRANSFER_LIST_FILE, NEW_DATA_FILE, OUTPUT_IMAGE_FILE)
    else:
        print("please use -h");
