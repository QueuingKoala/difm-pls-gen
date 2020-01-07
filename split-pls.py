#!/usr/bin/env python3

import argparse
import configparser
import getpass
import os
import xml.etree.ElementTree as ET
import sys

class PlaylistWriter:
    def __init__(self, out, key, servers=[], quality=''):
        self.out = out          # output file path
        self.chanCount = 0      # track channel count, for footer
        self.key = key
        self.servers = servers
        self.quality = quality

        self.ini = configparser.ConfigParser( interpolation=None )
        self.ini.optionxform = lambda opt: opt
        self.ini.add_section( 'playlist' )

    def append(self, chanKey, chanText):
        for num, host in enumerate( self.servers ):
            idx = num + 1   # PLS files are 1-indexed, not 0.

            self.ini.set( 'playlist', f'File{idx}',
                    f'http://{host}.di.fm:80/{chanKey}{self.quality}?{self.key}'
            )
            self.ini.set( 'playlist', f'Title{idx}', chanText )
            self.ini.set( 'playlist', f'Length{idx}', '-1' )

            self.chanCount += 1

    def write(self):
        # Playlist footer:
        self.ini.set( 'playlist', 'NumberOfEntries', str(self.chanCount) )
        self.ini.set( 'playlist', 'Version', '2' )

        # Write out this playlist file, WITHOUT spacing delimiters!
        with open( self.out, 'w') as plsFile:
            self.ini.write( plsFile, space_around_delimiters=False )

# enumChannels() - generator producing tuples of (chanKey, chanText):
#
# chanKey: Channel-key name, suitable for use in URI construction.
# chanText: Human-readable channel display name.

def enumChannels(xmlRoot):
    # Iterate over each <option> tag, which are the channel-selections:
    for option in xmlRoot.iter(tag='option'):

        chanKey = option.get('value')   # URI key is 'value' attribute.
        chanText = option.text.strip()  # Display text, sans whitespace.

        # "Placeholder" options declare no value: skip them:
        if chanKey == '': continue

        # A missing value attr on the other hand is unexpected: complain & skip:
        if chanKey is None:
            _attrs = ', '.join( f"{k}='{v}'" for k, v in option.items() )
            print( f'Bad <option> tag, with attrs: {_attrs}', file=sys.stderr )
            continue

        # Produce a (key, text) tuple:
        yield (chanKey, chanText)

parser = argparse.ArgumentParser()
parser.add_argument( '-l', '--low', action='store_const', dest='quality', const='_aac', default='' )
parser.add_argument( '-u', '--ultra', action='store_const', dest='quality', const='_hi' )
parser.add_argument( '-s', '--servers', action='append', default=['prem1', 'prem4'] )
parser.add_argument( '-1', action='store_const', dest='max', const=1 )
parser.add_argument( '-m', '--max', type=int )
parser.add_argument( 'xml_file' )

args = parser.parse_args()

# If servers wasn't defined, supply the (US) default:
if not args.servers: args.servers = ['prem1', 'prem4']

# Ensure max is no bigger than the server-list, falling back to its length:
if not args.max or args.max >= len(args.servers): args.max = len(args.servers)

# Then build a final server-list, no more than arg-max:
servers = args.servers[0:args.max]

# DEBUG: show args attrs:
#print( dir(args), servers )

# The server listen key is required; user to provide their account key:
userApiKey = getpass.getpass( 'Enter your DI.fm listen key: ' )

# Now, parse the XML class list from the saved page element.
#
# This is expected to be the root XML-node saved from the browser's
# inspector, based on the element named 'hardware-channel-selector'. A stock
# example is provided in: samples/hardware-channel-selector.xml

with open( args.xml_file, 'r' ) as xml_file:
    channels = ET.parse( xml_file )
    xmlRoot = channels.getroot()

# Iterate through channels

for chanKey, chanText in enumChannels( xmlRoot ):

    print( f' .. processing: {chanText} ..' )

    # TODO: max the out-dir user-defined. Here it's 'pls':

    plsPath = os.path.join( 'pls', f'{chanKey}.pls' )
    playlist = PlaylistWriter( plsPath, userApiKey, servers, args.quality )

    playlist.append( chanKey, chanText )
    playlist.write()

