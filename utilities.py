from bpy.types import Operator

class MY_OT_ReloadAddon(Operator):
    bl_idname = "wm.reload_addon"
    bl_label = "Reload Addon"
    
    def execute(self, context):
        import sys, importlib
        addon_name = "CodePY"
        # Unload modules
        for mod in list(sys.modules.keys()):
            if mod.startswith(addon_name):
                del sys.modules[mod]
        
        # Reload
        addon = __import__(addon_name)
        importlib.reload(addon)
        
        try:
            addon.unregister()
        except:
            pass
        
        addon.register()
        
        self.report({'INFO'}, f"{addon_name} reloaded!")
        return {'FINISHED'}