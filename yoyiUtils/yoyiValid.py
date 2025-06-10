

# 判断合法性相关

import re

# 文件夹名字合法性判断
def isValidDirName(dirName):
    if len(dirName) > 255:
        return False
    
    if re.search(r'[<>:"/\\|?.*]', dirName):
        return False
    
    if re.search(r'\s', dirName):
        return False
    
    return True