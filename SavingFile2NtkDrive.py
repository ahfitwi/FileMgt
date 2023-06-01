"""
- Copy files to a Samba shared drive using Python and verify it.
- Use the shutil command to copy file to shared drive or conversely
- The Samba project provides file sharing and print services for 
   computers on a network. It uses the Server Message Block and 
   Common Internet File System (SMB/CIFS) protocol, so the 
   services created by running Samba are available to Linux, 
   macOS, and Windows clients.
- smb? cifs? Is this using smb or cifs as an underlying protocol 
  for the transfer? I find both of these protocols to have painful 
  latency and inherent slowness. I am looking for a module that 
  has this functionality but which works fast. I guess with 
  this module the windows user features for permissions is achieved.

Solution-I: 
- Mapping the shared drive to an unused drive letter by calling the 
  NET USE command using os.system (Windows):
  os.system(r"NET USE P: \\ComputerName\ShareName %s /USER:%s\%s" % (
     password, domain_name, user_name))
- After you mapped the share to a drive letter, you can use 
  shutil.copyfile to copy the file to the given drive. Finally, 
  you should unmount the share:
  
  os.system(r"NET USE P: /DELETE")
  
  This works only on Windows, and you will have to make sure that 
  the drive letter P is available. You can check the return code 
  of the NET USE command to see whether the mount succeeded; 
  if not, you can try a different drive letter until you succeed.
  
  - https://stackoverflow.com/questions/2625877/how-to-copy-files-to-network-path-or-drive-using-python
"""
from contextlib import contextmanager

@contextmanager
def network_share_auth(share, username=None, password=None, drive_letter='P'):
    """Context manager that mounts the given share using the given
    username and password to the given drive letter when entering
    the context and unmounts it when exiting."""
    cmd_parts = ["NET USE %s: %s" % (drive_letter, share)]
    if password:
        cmd_parts.append(password)
    if username:
        cmd_parts.append("/USER:%s" % username)
    os.system(" ".join(cmd_parts))
    try:
        yield
    finally:
        os.system("NET USE %s: /DELETE" % drive_letter)

with network_share_auth(r"\\ComputerName\ShareName", username, password):
     shutil.copyfile("foo.txt", r"P:\foo.txt")

"""
Solution -II: win32wnet

"""
import win32wnet
win32wnet.WNetAddConnection2(0, None, '\\\\'+host, None, username, password)
shutil.copy(source_file, '\\\\'+host+dest_share_path+'\\')
win32wnet.WNetCancelConnection2('\\\\'+host, 0, 0) # optional disconnect

"""
Full Code:
WINDOWS NETWORK FILE TRANSFERS (PYTHON RECIPE)
This module enables users on the windows platform to transfer files to 
remote hosts. Requires pywin32 extensions
"""
#!/usr/bin/env python
#win32wnetfile.py

import os
import os.path
import shutil
import sys
import win32wnet

def netcopy(host, source, dest_dir, username=None, password=None, move=False):
    """ Copies files or directories to a remote computer. """
    
    wnet_connect(host, username, password)
            
    dest_dir = covert_unc(host, dest_dir)

    # Pad a backslash to the destination directory if not provided.
    if not dest_dir[len(dest_dir) - 1] == '\\':
        dest_dir = ''.join([dest_dir, '\\'])

    # Create the destination dir if its not there.
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    else:
        # Create a directory anyway if file exists so as to raise an error.
         if not os.path.isdir(dest_dir):
             os.makedirs(dest_dir)

    if move:
        shutil.move(source, dest_dir)
    else:
        shutil.copy(source, dest_dir)

def netdelete(host, path, username=None, password=None):
    """ Deletes files or directories on a remote computer. """
    
    wnet_connect(host, username, password)

    path = covert_unc(host, path)
    if os.path.exists(path):
        # Delete directory tree if object is a directory.        
        if os.path.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path)
    else:
        # Remove anyway if non-existent so as to raise an error.        
        os.remove(path)

def netmove(host, source, dest_dir, username=None, password=None):
    return netcopy(host, source, dest_dir, username, password, True)

def covert_unc(host, path):
    """ Convert a file path on a host to a UNC path."""
    return ''.join(['\\\\', host, '\\', path.replace(':', '$')])
    
def wnet_connect(host, username, password):
    unc = ''.join(['\\\\', host])
    try:
        win32wnet.WNetAddConnection2(0, None, unc, None, username, password)
    except Exception, err:
        if isinstance(err, win32wnet.error):
            # Disconnect previous connections if detected, and reconnect.
            if err[0] == 1219:
                win32wnet.WNetCancelConnection2(unc, 0, 0)
                return wnet_connect(host, username, password)
        raise err

if __name__ == '__main__':

    # Copy "c:\documents" folder/file to "c:\transferred" on host "w0001".
    netcopy('w0001', 'c:\\documents', 'c:\\transferred')

    # Move with account credentials.
    netmove('w0001', 'c:\\documents', 'c:\\transferred', 'admin', 'adminpass')

    # Delete with another account.
    netdelete('w0001', 'c:\\transferred', 'testdom\\user1', 'user1pass')

    # Transfer files using different accounts, to multiple computers.    
    accounts = [
        ('administrator', 'adminpass'),
        ('desktopeng', 'depass'),
        ('testdom\\administrator', 'dompass')]
    
    computers = ['w0001', 'w0002', 'w0003', 'w0004', 'w0005', 'w0006']

    auth_failed = []
    transfer_failed = []
    
    for computer in computers:
        # Try to authenticate with the each account provided.
        for account in accounts:
            username, password = account
            try:
                wnet_connect(computer, username, password)
            except Exception, err:
                # Look for authentication failures.
                if isinstance(err, win32wnet.error) and err[0] == 1326:
                    if account == accounts[len(accounts) -1]:
                        auth_failed.append(computer)
                else:
                    transfer_failed.append(computer)
                    break
            else:
                try:
                    netcopy(computer, 'c:\\documents', 'c:\\transferred')
                except Exception, err:
                    print err
                    transfer_failed.append(computer)
                break

    # Status report
    print('Authentication failure: %s' % (str(auth_failed).strip("[]'")))
    print('Unknown failure: %s' % (str(transfer_failed).strip("[]'")))

"""
I think this is a useful contribution, though I ran in some problem. 
Especially when copying directories. The following solves that:
"""

# Create the destination dir if its not there.
#if not os.path.exists(dest_dir):
#    os.makedirs(dest_dir)
#else:
#    # Create a directory anyway if file exists so as to raise an error.
#     if not os.path.isdir(dest_dir):
#         os.makedirs(dest_dir)

if move:
    if os.path.isdir(source):
        shutil.copytree(source, destdir)
        shutil.rmtree(source)
    elif os.path.isfile(source):
        shutil.move(source, dest_dir)
    else:
        raise AssertionError, '%s is neither a file nor directory' % (source)
else:
    if os.path.isdir(source):
        shutil.copytree(source, dest_dir)
    elif os.path.isfile(source):
        shutil.copy(source, dest_dir)
    else:
        raise AssertionError, '%s is neither a file nor directory' % (source)
         
    
