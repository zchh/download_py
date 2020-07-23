#! /usr/bin/env python3

"""Script to synchronize two source trees.

Invoke with two arguments:

python treesync.py subordinate main

The assumption is that "main" contains CVS administration while
subordinate doesn't.  All files in the subordinate tree that have a CVS/Entries
entry in the main tree are synchronized.  This means:

    If the files differ:
        if the subordinate file is newer:
            normalize the subordinate file
            if the files still differ:
                copy the subordinate to the main
        else (the main is newer):
            copy the main to the subordinate

    normalizing the subordinate means replacing CRLF with LF when the main
    doesn't use CRLF

"""

import os, sys, stat, getopt

# Interactivity options
default_answer = "ask"
create_files = "yes"
create_directories = "no"
write_subordinate = "ask"
write_main = "ask"

def main():
    global always_no, always_yes
    global create_directories, write_main, write_subordinate
    opts, args = getopt.getopt(sys.argv[1:], "nym:s:d:f:a:")
    for o, a in opts:
        if o == '-y':
            default_answer = "yes"
        if o == '-n':
            default_answer = "no"
        if o == '-s':
            write_subordinate = a
        if o == '-m':
            write_main = a
        if o == '-d':
            create_directories = a
        if o == '-f':
            create_files = a
        if o == '-a':
            create_files = create_directories = write_subordinate = write_main = a
    try:
        [subordinate, main] = args
    except ValueError:
        print("usage: python", sys.argv[0] or "treesync.py", end=' ')
        print("[-n] [-y] [-m y|n|a] [-s y|n|a] [-d y|n|a] [-f n|y|a]", end=' ')
        print("subordinatedir maindir")
        return
    process(subordinate, main)

def process(subordinate, main):
    cvsdir = os.path.join(main, "CVS")
    if not os.path.isdir(cvsdir):
        print("skipping main subdirectory", main)
        print("-- not under CVS")
        return
    print("-"*40)
    print("subordinate ", subordinate)
    print("main", main)
    if not os.path.isdir(subordinate):
        if not okay("create subordinate directory %s?" % subordinate,
                    answer=create_directories):
            print("skipping main subdirectory", main)
            print("-- no corresponding subordinate", subordinate)
            return
        print("creating subordinate directory", subordinate)
        try:
            os.mkdir(subordinate)
        except OSError as msg:
            print("can't make subordinate directory", subordinate, ":", msg)
            return
        else:
            print("made subordinate directory", subordinate)
    cvsdir = None
    subdirs = []
    names = os.listdir(main)
    for name in names:
        mainname = os.path.join(main, name)
        subordinatename = os.path.join(subordinate, name)
        if name == "CVS":
            cvsdir = mainname
        else:
            if os.path.isdir(mainname) and not os.path.islink(mainname):
                subdirs.append((subordinatename, mainname))
    if cvsdir:
        entries = os.path.join(cvsdir, "Entries")
        for e in open(entries).readlines():
            words = e.split('/')
            if words[0] == '' and words[1:]:
                name = words[1]
                s = os.path.join(subordinate, name)
                m = os.path.join(main, name)
                compare(s, m)
    for (s, m) in subdirs:
        process(s, m)

def compare(subordinate, main):
    try:
        sf = open(subordinate, 'r')
    except IOError:
        sf = None
    try:
        mf = open(main, 'rb')
    except IOError:
        mf = None
    if not sf:
        if not mf:
            print("Neither main nor subordinate exists", main)
            return
        print("Creating missing subordinate", subordinate)
        copy(main, subordinate, answer=create_files)
        return
    if not mf:
        print("Not updating missing main", main)
        return
    if sf and mf:
        if identical(sf, mf):
            return
    sft = mtime(sf)
    mft = mtime(mf)
    if mft > sft:
        # Main is newer -- copy main to subordinate
        sf.close()
        mf.close()
        print("Main             ", main)
        print("is newer than subordinate", subordinate)
        copy(main, subordinate, answer=write_subordinate)
        return
    # Subordinate is newer -- copy subordinate to main
    print("Subordinate is", sft-mft, "seconds newer than main")
    # But first check what to do about CRLF
    mf.seek(0)
    fun = funnychars(mf)
    mf.close()
    sf.close()
    if fun:
        print("***UPDATING MASTER (BINARY COPY)***")
        copy(subordinate, main, "rb", answer=write_main)
    else:
        print("***UPDATING MASTER***")
        copy(subordinate, main, "r", answer=write_main)

BUFSIZE = 16*1024

def identical(sf, mf):
    while 1:
        sd = sf.read(BUFSIZE)
        md = mf.read(BUFSIZE)
        if sd != md: return 0
        if not sd: break
    return 1

def mtime(f):
    st = os.fstat(f.fileno())
    return st[stat.ST_MTIME]

def funnychars(f):
    while 1:
        buf = f.read(BUFSIZE)
        if not buf: break
        if '\r' in buf or '\0' in buf: return 1
    return 0

def copy(src, dst, rmode="rb", wmode="wb", answer='ask'):
    print("copying", src)
    print("     to", dst)
    if not okay("okay to copy? ", answer):
        return
    f = open(src, rmode)
    g = open(dst, wmode)
    while 1:
        buf = f.read(BUFSIZE)
        if not buf: break
        g.write(buf)
    f.close()
    g.close()

def raw_input(prompt):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    return sys.stdin.readline()

def okay(prompt, answer='ask'):
    answer = answer.strip().lower()
    if not answer or answer[0] not in 'ny':
        answer = input(prompt)
        answer = answer.strip().lower()
        if not answer:
            answer = default_answer
    if answer[:1] == 'y':
        return 1
    if answer[:1] == 'n':
        return 0
    print("Yes or No please -- try again:")
    return okay(prompt)

if __name__ == '__main__':
    main()
