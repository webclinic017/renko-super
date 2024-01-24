#!/bin/env python

# program to convert XLS files to feather files
import pandas as pd
import sys
import os

# get input from command line
if len(sys.argv) < 2:
    print("Usage: convert_xls_to_feather.py file.xls")
    sys.exit(1)
else:
    xls_file = sys.argv[1]

# read xls file
df = pd.read_excel(xls_file)
# remove xls extension from xls file

# remove xls extension from xls file
file_name_without_extension = os.path.splitext(xls_file)[0]
# convert to feather
df.to_feather(file_name_without_extension + ".feather")
