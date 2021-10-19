import pcbnew
import logging
import os
import sys
import csv
import re

VERSION = '1.0.0' 

X_DIRECTION = 1
Y_DIRECTION = -1

# > V5.1.5 and V 5.99 build information
if hasattr(pcbnew, 'GetBuildVersion'):
    BUILD_VERSION = pcbnew.GetBuildVersion()
else:
    BUILD_VERSION = "Unknown"


board = pcbnew.GetBoard()
# go to the project folder - so that log will be in proper place
os.chdir(os.path.dirname(os.path.abspath(board.GetFileName())))

class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self, *args, **kwargs):
        """No-op for wrapper"""
        pass

# Remove all handlers associated with the root logger object.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
# set up logger
logging.basicConfig(level=logging.DEBUG,
                    filename="export_JLC_bom_and_pos.log",
                    filemode='w',
                    format='%(asctime)s %(name)s %(lineno)d:%(message)s',
                    datefmt='%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
logger.info("Plugin executed on: " + repr(sys.platform))
logger.info("Plugin executed with python version: " + repr(sys.version))
logger.info("KiCad build version: " + BUILD_VERSION)
logger.info("Export_JLC_bom_and_pos plugin version: " + VERSION + " started")

stdout_logger = logging.getLogger('STDOUT')
sl = StreamToLogger(stdout_logger, logging.INFO)
sys.stdout = sl

stderr_logger = logging.getLogger('STDERR')
sl = StreamToLogger(stderr_logger, logging.ERROR)
sys.stderr = sl

class export_JLC_bom_and_pos(pcbnew.ActionPlugin):

    def defaults(self):
        self.name = "Export JLC bom and pos"
        self.category = "Modify Drawing PCB and schematics"
        self.description = "Export JLC bom and pos"

    def Run(self):
        bom_items = []
        pos_items = []
        footprints = board.GetFootprints()
        footprint = footprints[0]
        for footprint in footprints:
            ref = str(footprint.GetReference())
            value = footprint.GetValue()
            position = list(footprint.GetPosition()) 
            fp = footprint.GetFPID()
            fp_name = fp.GetUniStringLibItemName()
            fp_name = re.sub(r"_\d+Metric", "", fp_name)
            rotation = footprint.GetOrientationDegrees() 
            if footprint.GetLayerName() == u'F.Cu':
                layer_name = 'T'
            else:
                layer_name = 'B'

            sub_uints = [] 
            footprint_properties = footprint.GetProperties()
            for k in footprint_properties.keys():
                if re.match("BOM_A\d+", k, flags=0):
                    sub_uints.append(k)
            
            if len(sub_uints) > 0:
                for item in footprint.GraphicalItems():
                    if item.GetClass() == "MTEXT":
                        text = str(item.Cast().GetText()) 
                        if text in sub_uints:
                            uint_fp = footprint_properties[text]
                            uint_position = item.GetPosition()
                            uint_ref = text.replace("BOM_", "")
                            uint_rotation = item.Cast().GetTextAngleDegrees() 

                            bom_items.append({"Comment": str(uint_fp), "Designator": str(uint_ref), "Footprint": str(uint_fp)})
                            pos_items.append({"Designator": str(uint_ref), "Mid X": "{0}mm".format(uint_position[0]/1000000.0*X_DIRECTION), "Mid Y": "{0}mm".format(uint_position[1]/1000000.0 * Y_DIRECTION), "Layer": layer_name, "Rotation": str(uint_rotation)})

            if str(ref) and value != "TestPoint":
                bom_items.append({"Comment": value, "Designator": str(ref), "Footprint": str(fp_name)})
                pos_items.append({"Designator": str(ref), "Mid X": "{0}mm".format(position[0]/1000000.0*X_DIRECTION), "Mid Y": "{0}mm".format(position[1]/1000000.0 * Y_DIRECTION), "Layer": layer_name, "Rotation": str(rotation)})
        
        bom_items_remap = {}
        for item in bom_items:
            value = item["Comment"]
            if value:
                if not bom_items_remap.get(value):
                    bom_items_remap[value] = {"Designator": [], "Footprint": item["Footprint"]} 
                
                bom_items_remap[value]["Designator"].append(item["Designator"])
        
        if not os.path.exists("JLC"):
            os.mkdir("JLC")

        with open('JLC/JLC_BOM.csv', 'w+') as csvfile:
            fieldnames = ["Comment", "Designator", "Footprint"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for k in bom_items_remap.keys(): 
                item = bom_items_remap[k] 
                data = {"Comment": k, "Designator": ",".join(item["Designator"]), "Footprint": item["Footprint"]} 
                try:
                    writer.writerow(data)
                except:
                    logger.error(item)

        with open('JLC/JLC_POS.csv', 'w+') as csvfile:
            fieldnames = ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for item in pos_items: 
                try:
                    writer.writerow(item)
                except:
                    logger.error(item)