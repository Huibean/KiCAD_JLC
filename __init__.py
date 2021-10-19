try:
    from export_JLC_bom_and_pos import *
    export_JLC_bom_and_pos().register()
except Exception as e:
    import os
    plugin_dir = os.path.dirname(os.path.realpath(__file__))
    log_file = os.path.join(plugin_dir, 'KiCAD_JLC.log')
    with open(log_file, 'w') as f:
        f.write(repr(e))