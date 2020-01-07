#!/usr/bin/env python3

"""
Playlist generator interface & CLI frontend for DI.fm Premium.

Invoked at the CLI, produces playlist files, with multiple modes of
operation:
    * One playlist-per-channel
    * Single playlist containing all channels
    * Multiple server support in both output modes
    * Quality selection (default, low, & ultra bandwidth)

The PlaylistBuilder class supplies a lower-level interface to DI.fm Premium
playlist construction.
"""

import argparse
import configparser
import getpass
import os
import xml.etree.ElementTree as ET
import sys

class PlaylistBuilder:
    """
    Interface to build a PLS-format Playlist file.

    Constructor:
    PlaylistBuilder -- create & initialize a new Playlist.

    Methods:
    append    -- add a channel entry across requsted servers
    write     -- write constructed playlist to file
    zero_list -- clear playlist entries
    """

    def __init__(self, apiKey, servers=[], quality=''):
        """
        Prepare a playlist builder.

        The provided apiKey, list of servers, & quality suffix are stored
        per-instance for use as each playlist entry is appended.
        """

        self.apiKey = apiKey
        self.servers = servers
        self.quality = quality
        self.zero_list()        # prepare a zeroed out playlist

    def zero_list(self):
        """
        Zero out a playlist structure.
        """

        self.chanCount = 0  # track channel count, for footer

        # Create INI structure, perserving option case:
        self.ini = configparser.ConfigParser( interpolation=None )
        self.ini.optionxform = lambda opt: opt
        self.ini.add_section( 'playlist' )

    def append(self, chanKey, chanText):
        """
        Add a channel to playlist, across requested servers.
        """

        for num, host in enumerate( self.servers ):
            # Increment upfront as PLS files are 1-indexed:
            self.chanCount += 1
            idx = num + self.chanCount

            self.ini.set( 'playlist', f'File{idx}',
                    f'http://{host}.di.fm:80/{chanKey}{self.quality}?{self.apiKey}'
            )
            self.ini.set( 'playlist', f'Title{idx}', chanText )
            self.ini.set( 'playlist', f'Length{idx}', '-1' )

    def write(self, out):
        """
        Add footer and write this playlist to a file.
        """

        # Playlist footer:
        self.ini.set( 'playlist', 'NumberOfEntries', str(self.chanCount) )
        self.ini.set( 'playlist', 'Version', '2' )

        # Write out this playlist file, WITHOUT spacing delimiters!
        self.ini.write( out, space_around_delimiters=False )

def enumChannels(xmlRoot, *, verbose=True):
    """
    Generator producing per-channel tuples of: (key, text)

    Pass in xmlRoot, an ElementTree structure above channel <option> tags.
    """

    # Iterate over each <option> tag, which are the channel-selections:
    for option in xmlRoot.iter(tag='option'):

        chanKey = option.get('value')   # URI key is 'value' attribute.
        chanText = option.text.strip()  # Display text, sans whitespace.

        # "Placeholder" options declare no value: skip them:
        if chanKey == '': continue

        # A missing value attr on the other hand is unexpected: complain & skip:
        if chanKey is None:
            if verbose:
                _attrs = ', '.join( f"{k}='{v}'" for k, v in option.items() )
                print( f'Ignoring bad <option> tag, with attrs: {_attrs}',
                        file=sys.stderr
                )
            continue

        # Produce a (key, text) tuple:
        yield (chanKey, chanText)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument( '-l', '--low',
            action='store_const', dest='quality', const='_aac', default=''
    )
    parser.add_argument( '-u', '--ultra',
            action='store_const', dest='quality', const='_hi'
    )
    parser.add_argument( '-s', '--servers',
            action='append'
    )
    parser.add_argument( '-d', '--dir', default='',
            help='output directory (default: working-directory)'
    )
    parser.add_argument( '-m', '--max', type=int )
    parser.add_argument( '-f', '--file',
            help='single-file output filename (no extension.)'
    )
    parser.add_argument( 'xml_file' )

    args = parser.parse_args()

    # If servers wasn't defined, supply the (US) default:
    if not args.servers: args.servers = ['prem1', 'prem4']

    # When unset, max is server length, except 1 with --file
    if not args.max:
        args.max = 1 if args.file else len(args.servers)

    # Update servers to no more than max:
    args.servers = args.servers[0:args.max]

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

    playlist = PlaylistBuilder( userApiKey, args.servers, args.quality )

    def pls_write( basename ):
        plsPath = os.path.join( args.dir, basename )
        with open( plsPath, 'w' ) as plsFile:
            playlist.write( plsFile )

    # Iterate through channels

    for chanKey, chanText in enumChannels( xmlRoot ):
        print( f' .. processing: {chanText} ..' )

        if not args.file: playlist.zero_list()
        playlist.append( chanKey, chanText )

        # Write-out each channel if not in single-file mode:
        if not args.file: pls_write( f'{chanKey}.pls' )

    # Final write-out in single-file mode:
    if args.file: pls_write( f'{args.file}.pls' )

