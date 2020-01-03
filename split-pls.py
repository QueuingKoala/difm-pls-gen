#!/usr/bin/env python3

import configparser
import getpass
import xml.etree.ElementTree as ET
import sys

# Define general playlist vars of interest.

# This lists the servers by least-significant hostname:
hostList = ['prem1', 'prem4']

# This is the "quality" string to append to the channel-key:
qualitySuffix = '_hi'    # "high" quality, ie: 320 kbps MP3 format

# The server listen key is required; user to provide per account:
userApiKey = getpass.getpass( 'Enter your DI.fm listen key: ' )

# Now, parse the XML class list from the saved page element:

channels = ET.parse( 'channel-classes.xml' )
xmlRoot = channels.getroot()

# Iterate through all <option> tags, getting the 'value' (channel-keys)

for option in xmlRoot.iter(tag='option'):
    chanKey = option.get('value')
    chanText = option.text.strip()

    # "Placeholder" options declare no value: skip them:
    if chanKey == '': continue

    # A missing value attr on the other hand is unexpected: complain & skip:
    if chanKey is None:
        _attrMsg = ', '.join( f"{k}='{v}'" for k, v in option.items() )
        print( f'Unparsable option element, with attrs: {_attrMsg}', file=sys.stderr )
        continue

    print( f' .. processing: {chanText} ..' )

    # Build the INI file for writing.

    ini = configparser.ConfigParser( interpolation=None )

    # Override option handling function, to preserve passed case:
    ini.optionxform = lambda _opt: _opt

    # Header: the sole section is simply '[playlist]':
    ini.add_section( 'playlist' )

    # Each entry gets indexed, case-sensitive fields:
    for num, host in enumerate( hostList ):
        idx = num + 1   # PLS files are 1-indexed, not 0.
        ini.set( 'playlist', f'File{idx}',
                f'http://{host}.di.fm:80/{chanKey}{qualitySuffix}?{userApiKey}'
        )
        ini.set( 'playlist', f'Title{idx}', chanText )
        ini.set( 'playlist', f'Length{idx}', '-1' )

    # Footer:
    ini.set( 'playlist', 'NumberOfEntries', str(len(hostList)) )
    ini.set( 'playlist', 'Version', '2' )

    # Write out this playlist file, WITHOUT spacing delimiters!

    with open( f'pls/{chanKey}.pls', 'w') as plsFile:
        ini.write( plsFile, space_around_delimiters=False )

