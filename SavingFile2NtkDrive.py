"""
- Copy files to a Samba shared drive using Python and verify it.
- Use the shutil command to copy file to shared drive or conversely
- The Samba project provides file sharing and print services for 
   computers on a network. It uses the Server Message Block and 
   Common Internet File System (SMB/CIFS) protocol, so the 
   services created by running Samba are available to Linux, 
   macOS, and Windows clients.

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
 
